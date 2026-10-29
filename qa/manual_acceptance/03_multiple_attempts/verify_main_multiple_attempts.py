"""Controlled main-Oracle acceptance: 2 attempts and highest-score persistence.

Creates one disposable course, semester, offering, component, quiz (max_attempts=2),
question, enrollment and two submitted attempts. ALL WRITES go via Django APIs;
Oracle is queried READ-ONLY for verification. No cleanup. Confirmation required.

Test order: first 10/10; second 0/10. STUDENT_MARK must remain 10/10.
Built for EduSphere_Merged_Candidate against MAIN EDUSPHERE_OWNER, port 8002.
"""
import argparse
from datetime import date, timedelta
import re
import sys
import uuid
from urllib.error import URLError
from verify_main_api_quiz_lifecycle import (
    APP_USER, BASE_URL, SCHEMA, StopTest, check, expected_http, http,
    item_by_username, login, preflight, sql_find_id,
)

CONFIRMATION = 'MAIN TWO ATTEMPT TEST DATA ONLY'


def sql_rows(conn, sql, params=()):
    if not sql.lstrip().upper().startswith('SELECT'):
        raise StopTest('Verifier Oracle access is read-only SELECT only')
    cur = conn.cursor()
    try:
        cur.execute(sql, params)
        return [tuple(row) for row in cur.fetchall()]
    finally:
        cur.close()


def find_quiz(conn, component_id, title):
    rows = sql_rows(conn,
        f'SELECT QUIZ_ID, MAX_ATTEMPTS, ALLOW_MARK_VIEW, ALLOW_ANSWER_REVIEW FROM {SCHEMA}.QUIZ WHERE COMPONENT_ID=? AND QUIZ_TITLE=?',
        (component_id, title))
    check(len(rows)==1, 'Disposable quiz found exactly once in Oracle')
    qid, maxi, mark, answer = rows[0]
    check(int(maxi)==2 and str(mark)=='N' and str(answer)=='N',
          'Quiz has exactly 2 attempts and both publication flags disabled')
    return int(qid)


def create_fixture(conn, admin, instructor, student, instructor_username, tag):
    directory = expected_http('/api/admin/manage/directory/', admin, {200})
    check(bool(directory.get('programs')), 'Existing program available')
    program_id = int(directory['programs'][0]['program_id'])
    instructor_id = int(item_by_username(directory['instructors'], instructor_username)['instructor_id'])
    course_code = 'QA'+tag
    academic_year = 'QA'+tag
    title = 'QA Multi '+tag

    expected_http('/api/admin/manage/master/course/', admin, {200,201}, {
        'program_id':program_id, 'course_code':course_code,
        'course_name':'Two attempts test '+tag, 'credits':3,
        'course_description':'Disposable highest-score sync test'})
    expected_http('/api/admin/manage/master/semester/', admin, {200,201}, {
        'semester_name':'Main QA', 'academic_year':academic_year,
        'semester_start_date':(date.today()-timedelta(days=14)).isoformat(),
        'semester_end_date':(date.today()+timedelta(days=120)).isoformat()})
    course_id = sql_find_id(conn,'COURSE','COURSE_ID','COURSE_CODE',course_code)
    semester_id = sql_find_id(conn,'SEMESTER','SEMESTER_ID','ACADEMIC_YEAR',academic_year)
    data = expected_http('/api/admin/manage/offerings/', admin, {200,201}, {
        'course_id':course_id,'semester_id':semester_id,'section_code':'QA',
        'capacity':10,'offering_status':'OPEN','instructor_ids':[instructor_id]})
    offering_id=int(data['offering']['offering_id'])
    expected_http(f'/api/admin/manage/offerings/{offering_id}/grading-scheme/',admin,{200},{
        'scheme_name':'QA highest attempt scheme',
        'components':[{'component_name':'QA Two Attempts','component_type':'QUIZ',
                       'weight_percentage':100,'max_marks':10}]}, 'PUT')
    scheme = expected_http(f'/api/admin/manage/offerings/{offering_id}/grading-scheme/',admin,{200})
    components = [x for x in scheme['components'] if x['component_type']=='QUIZ']
    check(len(components)==1, 'One QA grading component created')
    component_id=int(components[0]['component_id'])
    expected_http('/api/quizzes/create/', instructor,{200,201},{
        'component_id':component_id,'quiz_title':title,
        'open_at':None,'close_at':None,'duration_minutes':30,'max_attempts':2})
    quiz_id = find_quiz(conn,component_id,title)
    question=expected_http('/api/quizzes/questions/create/',instructor,{200,201},{
        'question_text':'Choose the QA correct answer '+tag,'question_type':'MCQ_SINGLE'})
    question_id=int(question['question_id'])
    for label,flag,n in [('RIGHT-'+tag,'Y',1),('WRONG-'+tag,'N',2)]:
        expected_http('/api/quizzes/questions/options/create/',instructor,{200,201},{
            'question_id':question_id,'option_text':label,'is_correct':flag,'option_order':n})
    expected_http('/api/quizzes/questions/add/',instructor,{200,201},{
        'quiz_id':quiz_id,'question_id':question_id,'question_order':1,'question_marks':10})
    expected_http('/api/enrollments/',student,{200,201},{'offering_id':offering_id})
    print(f'QA FIXTURE: tag={tag} course={course_id} semester={semester_id} '
          f'offering={offering_id} component={component_id} quiz={quiz_id} question={question_id}')
    return quiz_id, question_id, component_id, offering_id


def verify_grading(conn, quiz_id, attempt_id, expected_score):
    rows = sql_rows(conn,f'''SELECT g.AUTO_MARKS, g.FINAL_MARKS, g.MAX_MARKS, g.GRADING_STATUS,
                                   g.GRADING_ID
                            FROM {SCHEMA}.QUIZ_GRADING g
                            JOIN {SCHEMA}.QUIZ_ATTEMPT a ON a.ATTEMPT_ID=g.ATTEMPT_ID
                            WHERE a.QUIZ_ID=? AND a.ATTEMPT_ID=?''',
                    (quiz_id,attempt_id))
    check(len(rows)==1, f'One grading row persisted for attempt {attempt_id}')
    auto,final,maximum,status,gid=rows[0]
    check(float(auto)==expected_score and float(final)==expected_score and float(maximum)==10,
          f'Attempt {attempt_id} persisted {expected_score}/10')
    details=sql_rows(conn,f'SELECT MARKS_AWARDED,MAX_MARKS FROM {SCHEMA}.QUIZ_QUESTION_GRADE WHERE GRADING_ID=?',(int(gid),))
    check(len(details)==1 and float(details[0][0])==expected_score and float(details[0][1])==10,
          f'Question-grade detail persisted for attempt {attempt_id}')


def verify_best_mark(conn, quiz_id, component_id, expected, count):
    attempts = sql_rows(conn, f'SELECT ATTEMPT_ID,ATTEMPT_NO,SUBMITTED_AT FROM {SCHEMA}.QUIZ_ATTEMPT WHERE QUIZ_ID=? ORDER BY ATTEMPT_NO',(quiz_id,))
    check(len(attempts)==count and all(row[2] is not None for row in attempts),
          f'Exactly {count} submitted attempts in Oracle')
    rows = sql_rows(conn,f'''SELECT sm.MARKS_OBTAINED
                            FROM {SCHEMA}.STUDENT_MARK sm
                            JOIN {SCHEMA}.ENROLLMENT e ON e.ENROLLMENT_ID=sm.ENROLLMENT_ID
                            JOIN {SCHEMA}.QUIZ_ATTEMPT a ON a.STUDENT_ID=e.STUDENT_ID
                            WHERE a.QUIZ_ID=? AND sm.COMPONENT_ID=?
                            GROUP BY sm.MARKS_OBTAINED''',(quiz_id,component_id))
    check(len(rows)==1 and float(rows[0][0])==expected,
          f'Course component STUDENT_MARK remains highest {expected}/10')
    return attempts


def submit_attempt(student, quiz_id, question_id, tag, correct):
    started=expected_http(f'/api/quizzes/{quiz_id}/attempt/',student,{200,201},method='POST')
    attempt_id=int(started['attempt_id'])
    content=expected_http(f'/api/quizzes/{quiz_id}/content/',student,{200})
    questions=[q for q in content.get('questions',[]) if int(q['question_id'])==question_id]
    check(len(questions)==1,f'Attempt {attempt_id} has QA question')
    q=questions[0]
    check(all('is_correct' not in x and 'option_order' not in x for x in q['options']),
          f'Attempt {attempt_id} does not expose answer metadata')
    expected_label=('RIGHT-' if correct else 'WRONG-')+tag
    options=[x for x in q['options'] if x.get('option_text')==expected_label]
    check(len(options)==1,'Expected answer option is available to student')
    expected_http(f'/api/quizzes/attempt/{attempt_id}/response/',student,{200,201},{
        'question_id':question_id,'selected_option_ids':[options[0]['option_id']]})
    submitted=expected_http(f'/api/quizzes/attempt/{attempt_id}/submit/',student,{200,201},method='POST')
    safe=str(submitted).lower()
    check(all(key not in safe for key in ('auto_marks','final_marks','max_marks','marks_obtained')),
          'Submission response contains no hidden grade values')
    return attempt_id


def run(args):
    conn=preflight(args.main_backend)
    try:
        print('\nWill create a NEW disposable course, semester, offering, quiz and TWO graded attempts.')
        print('The original QA fixture 104/166 and all original course records remain untouched.')
        print('No cleanup. A fresh random 10-hex tag will identify these QA records.')
        if input(f'Type {CONFIRMATION} to continue: ').strip()!=CONFIRMATION:
            print('Cancelled: no test writes executed.'); return 3
        admin,_=login('Administrator','ADMIN')
        instructor,instructor_username=login('Assigned Instructor','INSTRUCTOR')
        student,_=login('QA Student','STUDENT')
        tag=uuid.uuid4().hex[:10].upper()
        quiz_id,qid,component_id,offering_id=create_fixture(conn,admin,instructor,student,instructor_username,tag)
        a1=submit_attempt(student,quiz_id,qid,tag,correct=True)
        verify_grading(conn,quiz_id,a1,10)
        verify_best_mark(conn,quiz_id,component_id,10,1)
        status,_=http(f'/api/quizzes/attempt/{a1}/response/',student,
                      {'question_id':qid,'selected_option_ids':[]})
        check(status in (400,409), 'Submitted first attempt rejects further answer writes')
        a2=submit_attempt(student,quiz_id,qid,tag,correct=False)
        check(a1!=a2, 'Two different attempt IDs created')
        verify_grading(conn,quiz_id,a2,0)
        verify_best_mark(conn,quiz_id,component_id,10,2)
        status,body=http(f'/api/quizzes/{quiz_id}/attempt/',student,method='POST')
        check(status in (400,409),'Third attempt rejected after reaching max_attempts=2')
        check(len(sql_rows(conn,f'SELECT ATTEMPT_ID FROM {SCHEMA}.QUIZ_ATTEMPT WHERE QUIZ_ID=?',(quiz_id,)))==2,
              'Third start did not create a hidden extra attempt')
        for aid in (a1,a2):
            status,_=http(f'/api/quizzes/attempt/{aid}/result/',student)
            check(status==403,f'Attempt {aid} marks remain hidden while N/N')
            status,_=http(f'/api/quizzes/attempt/{aid}/review/',student)
            check(status==403,f'Attempt {aid} answer review remains hidden while N/N')
        print(f'\nSUCCESS: highest-score synchronization and max_attempts gate passed.')
        print(f'MAIN QA TEST RECORDS tag={tag} quiz={quiz_id} attempt1={a1} attempt2={a2} '
              f'component={component_id} offering={offering_id}')
        print('Results remain UNRELEASED (marks=N / answer_review=N). Do not delete test records.')
        return 0
    finally:
        conn.close()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--main-backend',required=True)
    p.add_argument('--base-url',default=BASE_URL)
    args=p.parse_args()
    if args.base_url.rstrip('/')!=BASE_URL:
        p.error('Write test is locked to http://127.0.0.1:8002')
    try:
        return run(args)
    except (StopTest,URLError,KeyError,ValueError,TypeError,ImportError,OSError) as e:
        print('\nTEST STOPPED:',str(e))
        print('If fixture creation began, partial disposable rows may remain in EDUSPHERE_OWNER.')
        print('The record tag and newly created identifiers printed above will aid review.')
        return 1

if __name__=='__main__':
    sys.exit(main())
