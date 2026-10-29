"""EduSphere main DB: controlled quiz-expiry acceptance test (API writes only).

Verifies live Oracle time expiry blocks quiz content, draft writes, and option
writes, but permits finalizing the previously saved answer. Uses ONLY unique
QA data, created via authenticated Django endpoints after explicit approval.
No schema migrations, direct Oracle DML, or cleanup; permanent QA records.
"""
from __future__ import annotations

import argparse
from datetime import date, timedelta
import sys
import time
import uuid
from urllib.error import URLError

from verify_main_api_quiz_lifecycle import (
    BASE_URL, SCHEMA, StopTest, check, expected_http, http, item_by_username,
    login, preflight, sql_find_id,
)

CONFIRMATION = 'MAIN EXPIRY TEST DATA ONLY'


def sql_rows(conn, sql, params=()):
    if not sql.strip().upper().startswith('SELECT'):
        raise StopTest('Only Oracle SELECT statements are permitted by this verifier')
    cursor = conn.cursor()
    try:
        cursor.execute(sql, params)
        return [tuple(row) for row in cursor.fetchall()]
    finally:
        cursor.close()


def create_fixture(conn, admin, instructor, student, username, tag):
    directory = expected_http('/api/admin/manage/directory/', admin, {200})
    check(bool(directory.get('programs')), 'Existing program available for QA course')
    program_id = int(directory['programs'][0]['program_id'])
    instructor_id = int(item_by_username(directory['instructors'], username)['instructor_id'])
    course_code = 'QEX'+tag
    academic_year = 'QEX'+tag
    title = 'QA Expiry '+tag
    expected_http('/api/admin/manage/master/course/', admin, {200, 201}, {
        'program_id':program_id, 'course_code':course_code,
        'course_name':title, 'credits':3,
        'course_description':'Disposable expiry-only acceptance fixture',
    })
    expected_http('/api/admin/manage/master/semester/', admin, {200, 201}, {
        'semester_name':'Main QA', 'academic_year':academic_year,
        'semester_start_date':(date.today()-timedelta(days=7)).isoformat(),
        'semester_end_date':(date.today()+timedelta(days=90)).isoformat(),
    })
    course_id = sql_find_id(conn, 'COURSE', 'COURSE_ID', 'COURSE_CODE', course_code)
    semester_id = sql_find_id(conn, 'SEMESTER', 'SEMESTER_ID', 'ACADEMIC_YEAR', academic_year)
    offering = expected_http('/api/admin/manage/offerings/', admin, {200, 201}, {
        'course_id':course_id, 'semester_id':semester_id,
        'section_code':'QA', 'capacity':10, 'offering_status':'OPEN',
        'instructor_ids':[instructor_id],
    })
    offering_id = int(offering['offering']['offering_id'])
    expected_http(f'/api/admin/manage/offerings/{offering_id}/grading-scheme/', admin, {200}, {
        'scheme_name':'QA expiry grading',
        'components':[{'component_name':'QA expiry quiz', 'component_type':'QUIZ',
                       'weight_percentage':100, 'max_marks':10}],
    }, method='PUT')
    scheme = expected_http(f'/api/admin/manage/offerings/{offering_id}/grading-scheme/', admin, {200})
    parts = [p for p in scheme['components'] if p['component_type']=='QUIZ']
    check(len(parts)==1, 'Exactly one QA QUIZ component created')
    component_id = int(parts[0]['component_id'])
    expected_http('/api/quizzes/create/', instructor, {200, 201}, {
        'component_id':component_id,'quiz_title':title,
        'open_at':None,'close_at':None,'duration_minutes':1,'max_attempts':1,
    })
    rows = sql_rows(conn, f'''SELECT QUIZ_ID,DURATION_MINUTES,MAX_ATTEMPTS,
                     ALLOW_MARK_VIEW,ALLOW_ANSWER_REVIEW FROM {SCHEMA}.QUIZ
                     WHERE COMPONENT_ID=? AND QUIZ_TITLE=?''', (component_id, title))
    check(len(rows)==1 and int(rows[0][1])==1 and int(rows[0][2])==1
          and str(rows[0][3])=='N' and str(rows[0][4])=='N',
          'Fresh 1-minute quiz has 1 attempt and N/N visibility')
    quiz_id = int(rows[0][0])
    question = expected_http('/api/quizzes/questions/create/', instructor, {200, 201}, {
        'question_text':'Expiry answer persistence '+tag,
        'question_type':'MCQ_SINGLE',
    })
    question_id = int(question['question_id'])
    for text, correct, ordinal in [('RIGHT-'+tag, 'Y', 1),('WRONG-'+tag,'N',2)]:
        expected_http('/api/quizzes/questions/options/create/', instructor, {200, 201}, {
            'question_id':question_id,'option_text':text,
            'is_correct':correct,'option_order':ordinal,
        })
    expected_http('/api/quizzes/questions/add/', instructor, {200, 201}, {
        'quiz_id':quiz_id,'question_id':question_id,
        'question_order':1,'question_marks':10,
    })
    expected_http('/api/enrollments/', student, {200,201}, {'offering_id':offering_id})
    print('QA FIXTURE: tag='+tag, 'course='+str(course_id),
          'semester='+str(semester_id), 'offering='+str(offering_id),
          'quiz='+str(quiz_id), 'component='+str(component_id),
          'question='+str(question_id))
    return quiz_id, component_id, question_id


def oracle_state(conn, attempt_id):
    rows = sql_rows(conn, f'''SELECT CASE
        WHEN qa.SUBMITTED_AT IS NOT NULL THEN 'ALREADY_SUBMITTED'
        WHEN q.DURATION_MINUTES IS NOT NULL AND SYSTIMESTAMP >
             qa.STARTED_AT + NUMTODSINTERVAL(q.DURATION_MINUTES, 'MINUTE')
             THEN 'DURATION_EXPIRED'
        WHEN q.CLOSE_AT IS NOT NULL AND SYSTIMESTAMP > q.CLOSE_AT
             THEN 'QUIZ_CLOSED'
        ELSE 'READY' END
        FROM {SCHEMA}.QUIZ_ATTEMPT qa
        JOIN {SCHEMA}.QUIZ q ON q.QUIZ_ID=qa.QUIZ_ID
        WHERE qa.ATTEMPT_ID=?''', (attempt_id,))
    if len(rows)!=1:
        raise StopTest('Expected exactly one QA attempt row')
    return str(rows[0][0])


def wait_for_expiry(conn, attempt_id, max_wait=115, sleep=time.sleep, monotonic=time.monotonic):
    start = monotonic()
    while monotonic()-start < max_wait:
        state = oracle_state(conn, attempt_id)
        if state=='DURATION_EXPIRED':
            return True
        if state!='READY':
            raise StopTest('Unexpected state while waiting for expiry: '+state)
        sleep(2)
    return False


def test_rejected(status, label):
    check(status in {400, 403, 409, 422}, label+' (blocked HTTP '+str(status)+')')


def verify_grade(conn, attempt_id):
    rows = sql_rows(conn, f'''SELECT g.AUTO_MARKS,g.FINAL_MARKS,g.MAX_MARKS,g.GRADING_ID
                        FROM {SCHEMA}.QUIZ_GRADING g WHERE g.ATTEMPT_ID=?''', (attempt_id,))
    check(len(rows)==1, 'Exactly one grading row persisted after expiry submission')
    row=rows[0]
    check(all(v is not None and abs(float(v)-10)<.001 for v in row[:3]),
          'Saved correct answer graded as 10/10 after expiry')
    detail=sql_rows(conn, f'''SELECT MARKS_AWARDED,MAX_MARKS FROM {SCHEMA}.QUIZ_QUESTION_GRADE
                              WHERE GRADING_ID=?''', (int(row[3]),))
    check(len(detail)==1 and all(abs(float(v)-10)<.001 for v in detail[0]),
          'Question-level grading synchronized 10/10')


def run(args):
    conn=preflight(args.main_backend)
    try:
        print('\nThis test CREATES a disposable 1-minute quiz in EDUSPHERE_OWNER.')
        print('It waits for expiration, rejects late edits, and finalizes saved answers.')
        print('No existing QA fixture is modified and no QA records are deleted.')
        print('The Django API does all writes. Oracle verification uses SELECT only.')
        if input('Type '+CONFIRMATION+' to continue: ').strip()!=CONFIRMATION:
            print('Cancelled before writes.'); return 3
        admin,_=login('Administrator','ADMIN')
        instructor,username=login('Assigned instructor','INSTRUCTOR')
        student,_=login('QA student','STUDENT')
        other,_=login('Different student','STUDENT')
        tag=uuid.uuid4().hex[:10].upper()
        quiz_id,component_id,question_id=create_fixture(conn,admin,instructor,student,username,tag)
        started=expected_http(f'/api/quizzes/{quiz_id}/attempt/', student,
                              {200,201}, method='POST')
        attempt_id=int(started['attempt_id'])
        print('MAIN EXPIRY QA ATTEMPT:',attempt_id)
        content=expected_http(f'/api/quizzes/{quiz_id}/content/', student, {200})
        questions=[q for q in content.get('questions',[]) if int(q['question_id'])==question_id]
        check(len(questions)==1 and all('is_correct' not in o and 'option_order' not in o
              for o in questions[0].get('options',[])), 'Student gets sanitized active questions')
        correct=next((o for o in questions[0]['options'] if o['option_text']=='RIGHT-'+tag),None)
        check(correct is not None,'Correct option handle available before expiry')
        reply=expected_http(f'/api/quizzes/attempt/{attempt_id}/response/',student,{200,201},{
            'question_id':question_id,'selected_option_ids':[correct['option_id']]})
        response_id=int(reply['response_id'])
        check(oracle_state(conn,attempt_id)=='READY', 'Answer saved while attempt is READY')
        late_payload={'question_id':question_id,'selected_option_ids':[]}
        print('Waiting for Oracle-side duration expiry (normally ~60 seconds)...')
        check(wait_for_expiry(conn,attempt_id,args.max_wait),
              'Oracle marks QA attempt DURATION_EXPIRED before test timeout')
        status,_=http(f'/api/quizzes/{quiz_id}/content/',student)
        test_rejected(status,'Expired attempt cannot retrieve question content or draft')
        status,_=http(f'/api/quizzes/attempt/{attempt_id}/response/',student,late_payload)
        test_rejected(status,'Expired attempt cannot overwrite saved answer')
        status,_=http('/api/quizzes/attempt/response/option/',student,{
            'response_id':response_id,'option_id':int(correct['option_id'])})
        test_rejected(status,'Expired attempt cannot directly append option')
        saved=sql_rows(conn,f'''SELECT qr.RESPONSE_ID,qo.OPTION_ID
            FROM {SCHEMA}.QUIZ_RESPONSE qr
            LEFT JOIN {SCHEMA}.QUIZ_RESPONSE_OPTION ro ON ro.RESPONSE_ID=qr.RESPONSE_ID
            LEFT JOIN {SCHEMA}.QUESTION_OPTION qo ON qo.OPTION_ID=ro.OPTION_ID
            WHERE qr.ATTEMPT_ID=? AND qr.QUESTION_ID=?''',(attempt_id,question_id))
        check(len(saved)==1 and int(saved[0][0])==response_id
              and int(saved[0][1])==int(correct['option_id']),
              'Late writes did not alter saved option in Oracle')
        status,_=http(f'/api/quizzes/attempt/{attempt_id}/submit/',other,method='POST')
        check(status==403,'Different student cannot submit expired QA attempt')
        submitted=expected_http(f'/api/quizzes/attempt/{attempt_id}/submit/',student,{200,201},method='POST')
        check('marks' not in str(submitted).lower() and 'score' not in str(submitted).lower(),
              'Expiry submission response contains no marks or scores')
        attempt_rows=sql_rows(conn,f'''SELECT SUBMITTED_AT FROM {SCHEMA}.QUIZ_ATTEMPT
                                  WHERE ATTEMPT_ID=?''',(attempt_id,))
        check(len(attempt_rows)==1 and attempt_rows[0][0] is not None,
              'Expired attempt finalized with SUBMITTED_AT')
        verify_grade(conn,attempt_id)
        status,_=http(f'/api/quizzes/attempt/{attempt_id}/submit/',student,method='POST')
        test_rejected(status,'Already submitted attempt cannot submit twice')
        status,_=http(f'/api/quizzes/attempt/{attempt_id}/result/',student)
        check(status==403,'Unreleased quiz result remains hidden after expired submission')
        status,_=http(f'/api/quizzes/attempt/{attempt_id}/review/',student)
        check(status==403,'Unreleased answer review remains hidden after expired submission')
        status,_=http(f'/api/quizzes/attempt/{attempt_id}/result/',other)
        check(status==403,'Other student cannot access expired attempt result')
        status,_=http(f'/api/quizzes/{quiz_id}/attempt/',student,method='POST')
        test_rejected(status,'Additional attempt denied by max_attempts=1')
        rows=sql_rows(conn,f'''SELECT COUNT(*) FROM {SCHEMA}.QUIZ_ATTEMPT
                              WHERE QUIZ_ID=?''',(quiz_id,))
        check(int(rows[0][0])==1,'No additional attempt created')
        print('\nSUCCESS: expiry read/write lock, preserved draft, finalization, grading, and isolation passed.')
        print('QA RECORDS: tag='+tag, 'quiz='+str(quiz_id), 'attempt='+str(attempt_id),
              'component='+str(component_id))
        print('QA quiz visibility remains N/N. No existing records modified. No cleanup.')
        return 0
    finally:
        conn.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--main-backend',required=True,help='Path to merged Backend folder using main Oracle .env')
    parser.add_argument('--base-url',default=BASE_URL)
    parser.add_argument('--max-wait',type=int,default=115,
                        help='Oracle-side expiry poll timeout in seconds (default 115)')
    args=parser.parse_args()
    if args.base_url.rstrip('/')!=BASE_URL:
        parser.error('Verifier is locked to main QA API '+BASE_URL)
    if not (70<=args.max_wait<=180):
        parser.error('--max-wait must be between 70 and 180 seconds')
    try:
        return run(args)
    except (StopTest,URLError,KeyError,ValueError,TypeError,ImportError,OSError) as exc:
        print('\nTEST STOPPED:',exc)
        print('If the disposable fixture was created, its rows remain for inspection.')
        return 1


if __name__=='__main__':
    sys.exit(main())
