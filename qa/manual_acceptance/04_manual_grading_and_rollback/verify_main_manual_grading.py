"""EduSphere MAIN Oracle: controlled manual LONG_TEXT grading acceptance test.

Requires the merged backend, main EDUSPHERE_OWNER in XEPDB1, and API port 8002.
Creates new uniquely marked disposable academic records only after confirmation.
Oracle checks are SELECT-only; all writes occur via the authenticated Django API.
An optional --test-db-rollback deliberately triggers a too-long instructor note,
expects request failure, and proves that preceding question updates rolled back.
"""
import argparse
from datetime import date, timedelta
import sys
import uuid
from urllib.error import URLError

from verify_main_api_quiz_lifecycle import (
    BASE_URL, SCHEMA, StopTest, check, expected_http, http, item_by_username,
    login, preflight, sql_find_id,
)

CONFIRMATION = 'MAIN MANUAL REVIEW TEST DATA ONLY'
ROLLBACK_CONFIRMATION = 'TEST INTENTIONAL ORACLE ROLLBACK'


def sql_rows(conn, sql, params=()):
    if not sql.lstrip().upper().startswith('SELECT'):
        raise StopTest('Safety lock: verifier SQL must begin with SELECT')
    c = conn.cursor()
    try:
        c.execute(sql, params)
        return [tuple(r) for r in c.fetchall()]
    finally:
        c.close()


def roughly(value, expected):
    return value is not None and abs(float(value) - float(expected)) < 0.001


def create_fixture(conn, admin, instructor, student, username, tag):
    directory = expected_http('/api/admin/manage/directory/', admin, {200})
    check(bool(directory.get('programs')), 'Program exists for disposable test course')
    program = int(directory['programs'][0]['program_id'])
    instructor_id = int(item_by_username(directory['instructors'], username)['instructor_id'])
    code, year, title = 'QA'+tag, 'QA'+tag, 'QA Manual '+tag
    expected_http('/api/admin/manage/master/course/', admin, {200,201}, {
        'program_id': program, 'course_code': code,
        'course_name': 'Manual LONG_TEXT QA '+tag, 'credits': 3,
        'course_description': 'Disposable grading and transaction test'})
    expected_http('/api/admin/manage/master/semester/', admin, {200,201}, {
        'semester_name': 'Main QA', 'academic_year': year,
        'semester_start_date': (date.today()-timedelta(days=14)).isoformat(),
        'semester_end_date': (date.today()+timedelta(days=120)).isoformat()})
    course_id = sql_find_id(conn, 'COURSE', 'COURSE_ID', 'COURSE_CODE', code)
    semester_id = sql_find_id(conn, 'SEMESTER', 'SEMESTER_ID', 'ACADEMIC_YEAR', year)
    offering = expected_http('/api/admin/manage/offerings/', admin, {200,201}, {
        'course_id': course_id, 'semester_id': semester_id, 'section_code':'QA',
        'capacity':10, 'offering_status':'OPEN', 'instructor_ids':[instructor_id]})
    offering_id = int(offering['offering']['offering_id'])
    expected_http(f'/api/admin/manage/offerings/{offering_id}/grading-scheme/',admin,{200},{
        'scheme_name':'QA manual grading',
        'components':[{'component_name':'QA written quiz', 'component_type':'QUIZ',
                       'weight_percentage':100, 'max_marks':10}]},'PUT')
    scheme=expected_http(f'/api/admin/manage/offerings/{offering_id}/grading-scheme/',admin,{200})
    components=[c for c in scheme['components'] if c['component_type']=='QUIZ']
    check(len(components)==1, 'Exactly one test grading component created')
    component_id=int(components[0]['component_id'])
    expected_http('/api/quizzes/create/',instructor,{200,201},{
        'component_id':component_id,'quiz_title':title,'open_at':None,
        'close_at':None,'duration_minutes':30,'max_attempts':1})
    qrows=sql_rows(conn,f'''SELECT QUIZ_ID, ALLOW_MARK_VIEW, ALLOW_ANSWER_REVIEW, MAX_ATTEMPTS
        FROM {SCHEMA}.QUIZ WHERE COMPONENT_ID=? AND QUIZ_TITLE=?''', (component_id,title))
    check(len(qrows)==1 and str(qrows[0][1])=='N' and str(qrows[0][2])=='N'
          and int(qrows[0][3])==1,'Fresh quiz has N/N publication flags and one attempt')
    quiz_id=int(qrows[0][0])

    mcq=expected_http('/api/quizzes/questions/create/',instructor,{200,201},{
        'question_text':'QA auto check '+tag, 'question_type':'MCQ_SINGLE'})
    mcq_id=int(mcq['question_id'])
    for label,flag,n in [('YES-'+tag,'Y',1),('NO-'+tag,'N',2)]:
        expected_http('/api/quizzes/questions/options/create/',instructor,{200,201},{
            'question_id':mcq_id,'option_text':label,'is_correct':flag,'option_order':n})
    expected_http('/api/quizzes/questions/add/',instructor,{200,201},{
        'quiz_id':quiz_id,'question_id':mcq_id,'question_order':1,'question_marks':4})

    written=expected_http('/api/quizzes/questions/create/',instructor,{200,201},{
        'question_text':'Explain one benefit of relational normalization '+tag,
        'question_type':'LONG_TEXT'})
    written_id=int(written['question_id'])
    expected_http('/api/quizzes/questions/add/',instructor,{200,201},{
        'quiz_id':quiz_id,'question_id':written_id,'question_order':2,'question_marks':6})
    expected_http('/api/enrollments/',student,{200,201},{'offering_id':offering_id})
    print('QA FIXTURE:', 'tag='+tag, 'course='+str(course_id), 'semester='+str(semester_id),
          'offering='+str(offering_id), 'component='+str(component_id),
          'quiz='+str(quiz_id), 'mcq='+str(mcq_id), 'long_text='+str(written_id))
    return quiz_id,component_id,offering_id,mcq_id,written_id


def grading_snapshot(conn,attempt_id):
    rows=sql_rows(conn,f'''SELECT g.GRADING_ID, g.AUTO_MARKS, g.FINAL_MARKS,
        g.MAX_MARKS, g.GRADING_STATUS, g.REVIEWED_BY_USER_ID, g.REVIEWED_AT,
        g.RELEASED_AT, g.INSTRUCTOR_NOTES
        FROM {SCHEMA}.QUIZ_GRADING g WHERE g.ATTEMPT_ID=?''',(attempt_id,))
    check(len(rows)==1, f'Exactly one grading record for attempt {attempt_id}')
    grading=tuple(rows[0])
    grades=sql_rows(conn,f'''SELECT qqg.QUESTION_ID, qqg.MARKS_AWARDED,
        qqg.MAX_MARKS, qqg.IS_CORRECT, qqg.GRADING_NOTE
        FROM {SCHEMA}.QUIZ_QUESTION_GRADE qqg
        WHERE qqg.GRADING_ID=? ORDER BY qqg.QUESTION_ID''',(int(grading[0]),))
    return grading,grades


def component_mark(conn,component_id,quiz_id):
    rows=sql_rows(conn,f'''SELECT sm.MARKS_OBTAINED
        FROM {SCHEMA}.STUDENT_MARK sm
        JOIN {SCHEMA}.ENROLLMENT e ON e.ENROLLMENT_ID=sm.ENROLLMENT_ID
        JOIN {SCHEMA}.QUIZ_ATTEMPT a ON a.STUDENT_ID=e.STUDENT_ID
        WHERE a.QUIZ_ID=? AND sm.COMPONENT_ID=?''',(quiz_id,component_id))
    return rows


def expect_hidden(student,attempt_id):
    status,_=http(f'/api/quizzes/attempt/{attempt_id}/result/',student)
    check(status==403,'Unreleased student result forbidden (403)')
    status,_=http(f'/api/quizzes/attempt/{attempt_id}/review/',student)
    check(status==403,'Unreleased student answer review forbidden (403)')


def expect_hidden_indirect(student,attempt_id,component_id,offering_id):
    history=expected_http('/api/quizzes/attempts/my/',student,{200})
    attempts=history.get('attempts',[]) if isinstance(history,dict) else []
    row=next((r for r in attempts if int(r.get('attempt_id',-1))==attempt_id),None)
    check(row is not None and row.get('marks_visible') is False
          and row.get('marks_obtained') is None and row.get('max_marks') is None,
          'Attempt history hides unpublished scores')
    marks=expected_http('/api/marks/my/',student,{200})
    check(isinstance(marks,list) and not any(int(m.get('component_id',-1))==component_id
          for m in marks),'General student marks exclude unreleased written-quiz component')
    semester=expected_http('/api/marks/my/semester-view/',student,{200})
    record=next((r for r in semester.get('components',[])
                 if int(r.get('component_id',-1))==component_id),None)
    check(record is not None and record.get('marks_obtained') is None
          and record.get('recorded_at') is None and record.get('mark_status')=='HIDDEN',
          'Semester markbook redacts score, time and status')
    dashboard=expected_http('/api/student/dashboard/',student,{200})
    course=next((r for r in dashboard.get('courses',[])
                 if int(r.get('offering_id',-1))==offering_id),None)
    check(course is not None and course.get('course_percentage') is None,
          'Student dashboard hides derivable unpublished course percentage')


def run(args):
    conn=preflight(args.main_backend)
    try:
        print('\nWill create a new disposable course, semester, offering and quiz with MCQ (4) + LONG_TEXT (6).')
        print('All existing QA fixtures (including quiz 104 and quiz 124) remain untouched.')
        print('Writes occur only after exact confirmation. Test records will NOT be deleted.')
        if input(f'Type {CONFIRMATION} to continue: ').strip()!=CONFIRMATION:
            print('Cancelled before writes.'); return 3
        admin,_=login('Administrator','ADMIN')
        instructor,instructor_username=login('Assigned instructor','INSTRUCTOR')
        other_instructor,_=login('Unassigned instructor','INSTRUCTOR')
        student,_=login('QA student','STUDENT')
        other_student,_=login('Different student','STUDENT')
        tag=uuid.uuid4().hex[:10].upper()
        quiz_id,component_id,offering_id,mcq_id,written_id=create_fixture(
            conn,admin,instructor,student,instructor_username,tag)

        started=expected_http(f'/api/quizzes/{quiz_id}/attempt/',student,{200,201},method='POST')
        attempt=int(started['attempt_id'])
        content=expected_http(f'/api/quizzes/{quiz_id}/content/',student,{200})
        questions={int(q['question_id']):q for q in content['questions']}
        check(set(questions)=={mcq_id,written_id},'Both quiz questions visible in open attempt')
        check(all(not any(k in opt for k in ('is_correct','option_order','match_key'))
                  for q in questions.values() for opt in q.get('options',[])),
              'Student question content excludes answer keys and ordering')
        correct=next((o for o in questions[mcq_id]['options']
                      if o['option_text']=='YES-'+tag),None)
        check(correct is not None,'Student can choose QA MCQ option')
        expected_http(f'/api/quizzes/attempt/{attempt}/response/',student,{200,201},{
            'question_id':mcq_id,'selected_option_ids':[correct['option_id']]})
        expected_http(f'/api/quizzes/attempt/{attempt}/response/',student,{200,201},{
            'question_id':written_id,
            'response_text':'Normalization avoids redundancy and update anomalies.'})
        submitted=expected_http(f'/api/quizzes/attempt/{attempt}/submit/',student,{200,201},method='POST')
        check(isinstance(submitted,dict) and all(x not in str(submitted).lower()
              for x in ('auto_marks','final_marks','max_marks','marks_obtained')),
              'Submission API exposes no hidden grading totals')
        before=grading_snapshot(conn,attempt)
        g,details=before
        check(roughly(g[1],4) and roughly(g[2],4) and roughly(g[3],10)
              and str(g[4])=='AUTO_GRADED','Auto-grade 4/10, pending manual long-text review')
        by_q={int(r[0]):r for r in details}
        check(len(by_q)==2 and roughly(by_q[mcq_id][1],4)
              and roughly(by_q[written_id][1],0),'MCQ 4/4 and LONG_TEXT 0/6 before review')
        check(component_mark(conn,component_id,quiz_id)==[],
              'Pending long-text review not published into STUDENT_MARK')
        expect_hidden(student,attempt)
        expect_hidden_indirect(student,attempt,component_id,offering_id)
        # Even an incorrect visibility configuration must not expose unreviewed long text.
        status,_=http(f'/api/quizzes/attempt/{attempt}/grading/',student)
        check(status==403,'Student forbidden from instructor grading endpoint')
        status,_=http(f'/api/quizzes/attempt/{attempt}/grading/',other_instructor)
        check(status==403,'Unassigned instructor denied grading details')
        status,_=http(f'/api/quizzes/attempt/{attempt}/grading/',instructor)
        check(status==200,'Assigned instructor may view grading details')
        release_url=f'/api/quizzes/attempt/{attempt}/grading/release/'
        status,_=http(release_url,student,method='POST')
        check(status==403,'Student forbidden from instructor release endpoint')
        status,_=http(release_url,other_instructor,method='POST')
        check(status==403,'Unassigned instructor forbidden from release endpoint')
        status,_=http(release_url,instructor,method='POST')
        check(status in (400,409),'Cannot release unreviewed long-text grading')
        check(grading_snapshot(conn,attempt)==before,'Premature release changed no grading values')

        good_reviews=[{'question_id':written_id,'marks_awarded':5,
                       'feedback':'Clear explanation with a relevant update-anomaly example.'}]
        invalid_reviews=[{'question_id':written_id,'marks_awarded':7,
                          'feedback':'This score exceeds the question maximum.'}]
        review_url=f'/api/quizzes/attempt/{attempt}/grading/'
        status,_=http(review_url,student,{'final_marks':9,'question_reviews':good_reviews},'PATCH')
        check(status==403,'Student cannot force manual grade update')
        status,_=http(review_url,other_instructor,
                      {'final_marks':9,'question_reviews':good_reviews},'PATCH')
        check(status==403,'Unassigned instructor cannot review')
        status,_=http(review_url,instructor,
                      {'final_marks':11,'question_reviews':invalid_reviews},'PATCH')
        check(status in (400,422),'Manual score above 6/6 rejected')
        status,_=http(review_url,instructor,
                      {'final_marks':9,'question_reviews':[]},'PATCH')
        check(status in (400,422),'Long-text review without rubric feedback rejected')
        status,_=http(review_url,instructor,
                      {'final_marks':8,'question_reviews':good_reviews},'PATCH')
        check(status in (400,422),'Mismatched sum of question-level marks rejected')
        check(grading_snapshot(conn,attempt)==before,
              'Invalid/unauthorized reviews left grading + question marks unchanged')
        check(component_mark(conn,component_id,quiz_id)==[],
              'Invalid review attempts cannot create component mark')

        if args.test_db_rollback:
            print('\nOPTIONAL ROLLBACK TEST: deliberately submit instructor notes longer than Oracle VARCHAR2(1000).')
            print('The server may produce one expected 500 error. All question updates must roll back.')
            if input(f'Type {ROLLBACK_CONFIRMATION} to continue: ').strip()!=ROLLBACK_CONFIRMATION:
                raise StopTest('Rollback subtest confirmation declined. No valid review was submitted.')
            status,_=http(review_url,instructor,{
                'final_marks':9,'question_reviews':good_reviews,'notes':'X'*1300},'PATCH')
            check(status in (400,413,422,500),
                  'Oracle or service rejects oversized notes instead of succeeding')
            check(grading_snapshot(conn,attempt)==before,
                  'ATOMIC ROLLBACK: neither question grade nor grading header changed')
            check(component_mark(conn,component_id,quiz_id)==[],
                  'ATOMIC ROLLBACK: no STUDENT_MARK was written')
            expect_hidden(student,attempt)

        expected_http(review_url,instructor,{200},{
            'final_marks':9,'notes':'QA manual evaluation '+tag,
            'question_reviews':good_reviews},'PATCH')
        reviewed=grading_snapshot(conn,attempt)
        g,details=reviewed
        by_q={int(r[0]):r for r in details}
        check(str(g[4])=='REVIEWED' and roughly(g[1],4) and roughly(g[2],9),
              'Manual review preserved 4 auto marks and set final 9/10')
        check(roughly(by_q[mcq_id][1],4) and roughly(by_q[written_id][1],5),
              'Question grading persists 4/4 and 5/6')
        check('Clear explanation' in str(by_q[written_id][4]),
              'Instructor rubric feedback persisted')
        marks=component_mark(conn,component_id,quiz_id)
        check(len(marks)==1 and roughly(marks[0][0],9),
              'STUDENT_MARK synchronized as 9/10 only after instructor review')
        expect_hidden(student,attempt)
        expect_hidden_indirect(student,attempt,component_id,offering_id)
        status,_=http(f'/api/quizzes/attempt/{attempt}/result/',other_student)
        check(status==403,'Different student cannot access graded result')
        status,_=http(f'/api/quizzes/attempt/{attempt}/review/',other_student)
        check(status==403,'Different student cannot access answer review')

        expected_http(release_url,instructor,{200},method='POST')
        released=grading_snapshot(conn,attempt)
        check(str(released[0][4])=='RELEASED' and roughly(released[0][2],9),
              'Instructor release persisted without changing final grade')
        check(len(component_mark(conn,component_id,quiz_id))==1
              and roughly(component_mark(conn,component_id,quiz_id)[0][0],9),
              'Released grading keeps STUDENT_MARK at 9/10')
        expect_hidden(student,attempt)
        expect_hidden_indirect(student,attempt,component_id,offering_id)
        status,_=http(f'/api/quizzes/attempt/{attempt}/grading/',instructor,
                      {'final_marks':7,'question_reviews':good_reviews},'PATCH')
        check(status in (400,409),'Released grading cannot be silently re-reviewed')
        check(grading_snapshot(conn,attempt)==released,'Denied post-release edit leaves data unchanged')
        print('\nSUCCESS: manual grading, rubric persistence, release, role isolation and hidden marks passed.')
        print('MAIN QA RECORDS:', 'tag='+tag, 'quiz='+str(quiz_id), 'attempt='+str(attempt),
              'component='+str(component_id), 'offering='+str(offering_id))
        if args.test_db_rollback:
            print('SUCCESS: intentional Oracle statement failure rolled back earlier question updates.')
        else:
            print('Optional write-failure rollback injection NOT TESTED (rerun on a new QA fixture with --test-db-rollback).')
        print('Visibility remains N/N. Existing QA fixtures unchanged. No cleanup performed.')
        return 0
    finally:
        conn.close()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--main-backend',required=True,help='Path to merged Backend folder with main DB .env')
    p.add_argument('--base-url',default=BASE_URL)
    p.add_argument('--test-db-rollback',action='store_true',
                   help='Optional: deliberately send one too-long Oracle instructor note (expected server error)')
    args=p.parse_args()
    if args.base_url.rstrip('/')!=BASE_URL:
        p.error('Refusing alternate URL; this main QA verifier is locked to http://127.0.0.1:8002')
    try:
        return run(args)
    except (StopTest,URLError,KeyError,ValueError,TypeError,ImportError,OSError) as e:
        print('\nTEST STOPPED:',str(e))
        print('Partial disposable QA rows may remain. Use the printed QA tag and IDs to inspect them.')
        return 1


if __name__=='__main__':
    sys.exit(main())
