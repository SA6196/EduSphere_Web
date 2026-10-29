"""EduSphere MAIN Oracle: controlled, bounded concurrent save/submit API test.

Creates only new disposable QA data using authenticated Django API calls.
Direct Oracle access is SELECT-only; never alters the fixed 37-table schema.
The test intentionally sends 4 overlapping requests against its own attempts.
"""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
import sys
import uuid
from threading import Barrier
from urllib.error import URLError

from verify_main_api_quiz_lifecycle import (
    BASE_URL, SCHEMA, StopTest, check, expected_http, http,
    item_by_username, login, preflight, sql_find_id,
)

CONFIRMATION = 'MAIN CONCURRENT QUIZ TEST DATA ONLY'
MAX_WORKERS = 4


def select_rows(conn, sql, params=()):
    if not sql.lstrip().upper().startswith('SELECT'):
        raise StopTest('Oracle test connection is SELECT-only.')
    cur = conn.cursor()
    try:
        cur.execute(sql, params)
        return [tuple(x) for x in cur.fetchall()]
    finally:
        cur.close()


def fresh_quiz(conn, admin, instructor, student, username, tag):
    directory=expected_http('/api/admin/manage/directory/', admin, {200})
    check(bool(directory['programs']), 'Existing program for QA fixture')
    program_id=int(directory['programs'][0]['program_id'])
    instructor_id=int(item_by_username(directory['instructors'],username)['instructor_id'])
    title='QA Concurrent '+tag
    course_code='QCC'+tag
    year='QCC'+tag
    expected_http('/api/admin/manage/master/course/',admin,{200,201},{
        'program_id':program_id,'course_code':course_code,'course_name':title,
        'credits':3,'course_description':'Disposable concurrency API verification'
    })
    expected_http('/api/admin/manage/master/semester/',admin,{200,201},{
        'semester_name':'Main QA','academic_year':year,
        'semester_start_date':(date.today()-timedelta(days=7)).isoformat(),
        'semester_end_date':(date.today()+timedelta(days=90)).isoformat()
    })
    course_id=sql_find_id(conn,'COURSE','COURSE_ID','COURSE_CODE',course_code)
    semester_id=sql_find_id(conn,'SEMESTER','SEMESTER_ID','ACADEMIC_YEAR',year)
    offering=expected_http('/api/admin/manage/offerings/',admin,{200,201},{
        'course_id':course_id,'semester_id':semester_id,'section_code':'QA',
        'capacity':10,'offering_status':'OPEN','instructor_ids':[instructor_id]
    })
    offering_id=int(offering['offering']['offering_id'])
    expected_http(f'/api/admin/manage/offerings/{offering_id}/grading-scheme/',admin,{200},{
        'scheme_name':'QA concurrency grading',
        'components':[{'component_name':'QA concurrent quiz','component_type':'QUIZ',
                       'weight_percentage':100,'max_marks':10}]
    },method='PUT')
    scheme=expected_http(f'/api/admin/manage/offerings/{offering_id}/grading-scheme/',admin,{200})
    comps=[x for x in scheme['components'] if x['component_type']=='QUIZ']
    check(len(comps)==1,'One QA component created')
    component_id=int(comps[0]['component_id'])
    expected_http('/api/quizzes/create/',instructor,{200,201},{
        'component_id':component_id,'quiz_title':title,
        'open_at':None,'close_at':None,'duration_minutes':15,'max_attempts':2
    })
    rows=select_rows(conn,f'''SELECT QUIZ_ID,MAX_ATTEMPTS,ALLOW_MARK_VIEW,ALLOW_ANSWER_REVIEW
        FROM {SCHEMA}.QUIZ WHERE COMPONENT_ID=? AND QUIZ_TITLE=?''',(component_id,title))
    check(len(rows)==1 and int(rows[0][1])==2 and str(rows[0][2])=='N'
          and str(rows[0][3])=='N','Two-attempt QA quiz starts unpublished')
    quiz_id=int(rows[0][0])
    q=expected_http('/api/quizzes/questions/create/',instructor,{200,201},{
        'question_text':'Concurrency single choice '+tag,'question_type':'MCQ_SINGLE'
    })
    qid=int(q['question_id'])
    for caption,flag,order in [('RIGHT-'+tag,'Y',1),('WRONG-'+tag,'N',2)]:
        expected_http('/api/quizzes/questions/options/create/',instructor,{200,201},{
            'question_id':qid,'option_text':caption,'is_correct':flag,'option_order':order
        })
    expected_http('/api/quizzes/questions/add/',instructor,{200,201},{
        'quiz_id':quiz_id,'question_id':qid,'question_order':1,'question_marks':10
    })
    expected_http('/api/enrollments/',student,{200,201},{'offering_id':offering_id})
    print('QA FIXTURE tag='+tag, 'course='+str(course_id), 'offering='+str(offering_id),
          'quiz='+str(quiz_id), 'component='+str(component_id), 'question='+str(qid))
    return quiz_id, component_id, qid, offering_id


def new_attempt(student, quiz_id, qid, tag):
    started=expected_http(f'/api/quizzes/{quiz_id}/attempt/',student,{200,201},method='POST')
    aid=int(started['attempt_id'])
    content=expected_http(f'/api/quizzes/{quiz_id}/content/',student,{200})
    questions=[x for x in content.get('questions',[]) if int(x['question_id'])==qid]
    check(len(questions)==1,'QA question available in attempt '+str(aid))
    opts=questions[0]['options']
    check(all('is_correct' not in x and 'option_order' not in x and 'match_key' not in x
              for x in opts),'Student content does not expose answer metadata')
    good=next((x for x in opts if x['option_text']=='RIGHT-'+tag),None)
    bad=next((x for x in opts if x['option_text']=='WRONG-'+tag),None)
    check(good is not None and bad is not None,'QA answer handles available')
    return aid,int(good['option_id']),int(bad['option_id'])


def saved_answer(conn, attempt_id, qid):
    rows=select_rows(conn,f'''SELECT qr.RESPONSE_ID, ro.OPTION_ID, o.IS_CORRECT
        FROM {SCHEMA}.QUIZ_RESPONSE qr
        LEFT JOIN {SCHEMA}.QUIZ_RESPONSE_OPTION ro ON ro.RESPONSE_ID=qr.RESPONSE_ID
        LEFT JOIN {SCHEMA}.QUESTION_OPTION o ON o.OPTION_ID=ro.OPTION_ID
        WHERE qr.ATTEMPT_ID=? AND qr.QUESTION_ID=?''',(attempt_id,qid))
    check(len(rows)==1 and rows[0][1] is not None,
          f'Attempt {attempt_id}: exactly one response and one selected option')
    return rows[0]


def grade_snapshot(conn, attempt_id, expected=None):
    rows=select_rows(conn,f'''SELECT g.GRADING_ID,g.AUTO_MARKS,g.FINAL_MARKS,g.MAX_MARKS
        FROM {SCHEMA}.QUIZ_GRADING g WHERE g.ATTEMPT_ID=?''',(attempt_id,))
    check(len(rows)==1, f'Attempt {attempt_id}: exactly one grading header')
    gid,auto,final,maximum=rows[0]
    marks=float(final)
    check(abs(float(auto)-marks)<0.001 and abs(float(maximum)-10)<0.001,
          f'Attempt {attempt_id}: consistent auto/final/max marks')
    details=select_rows(conn,f'''SELECT MARKS_AWARDED,MAX_MARKS
        FROM {SCHEMA}.QUIZ_QUESTION_GRADE WHERE GRADING_ID=?''',(int(gid),))
    check(len(details)==1 and abs(float(details[0][0])-marks)<0.001
          and abs(float(details[0][1])-10)<0.001,
          f'Attempt {attempt_id}: one consistent question grading row')
    if expected is not None:
        check(abs(marks-expected)<0.001,f'Attempt {attempt_id}: expected {expected}/10 grading')
    return marks


def parallel_cases(cases):
    """Exactly four independently authenticated HTTP requests start together."""
    if len(cases)!=MAX_WORKERS:
        raise StopTest('Safety limit: exactly four concurrent requests.')
    barrier=Barrier(MAX_WORKERS)
    def do(case):
        label,path,token,payload,method=case
        barrier.wait(timeout=12)
        return label, http(path,token,payload,method)
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures=[pool.submit(do,case) for case in cases]
        return [future.result(timeout=45) for future in futures]


def validate_concurrent_http(results, submit_count, label):
    for task,(status,body) in results:
        print('  ',task,'HTTP',status)
        check(status in {200,201,400,403,409,422},
              label+' '+task+' returned acceptable status (not HTTP 5xx)')
        if status in {200,201}:
            body=body.get('data',body) if isinstance(body,dict) else body
            check('marks' not in str(body).lower() and 'score' not in str(body).lower(),
                  label+' '+task+' did not leak grading information')
    successes=sum(status in {200,201} for task,(status,_) in results if task.startswith('submit'))
    check(successes==submit_count,
          label+f' exactly {submit_count} successful submission(s), got {successes}')


def attempt_submitted(conn, attempt_id):
    rows=select_rows(conn,f'''SELECT SUBMITTED_AT FROM {SCHEMA}.QUIZ_ATTEMPT
                             WHERE ATTEMPT_ID=?''',(attempt_id,))
    check(len(rows)==1 and rows[0][0] is not None,
          f'Attempt {attempt_id}: single submitted attempt exists')


def check_private(student,other,attempt_id):
    for suffix in ('result','review'):
        path=f'/api/quizzes/attempt/{attempt_id}/{suffix}/'
        status,_=http(path,student)
        check(status==403,f'Owner denied unreleased {suffix} (403)')
        status,_=http(path,other)
        check(status==403,f'Other student denied {suffix} (403)')


def run(args):
    cn=preflight(args.main_backend)
    try:
        print('\nCreates ONE disposable quiz with TWO attempts in EDUSPHERE_OWNER.')
        print('Exactly four concurrent client requests per race; uses localhost:8002.')
        print('No cleanup, direct Oracle DML, schema changes, or touching prior QA records.')
        print('Keep the merged backend on a bounded >=4-thread Waitress instance.')
        if input('Type '+CONFIRMATION+' to continue: ').strip()!=CONFIRMATION:
            print('Cancelled before writes.'); return 3
        admin,_=login('Administrator','ADMIN')
        instructor,username=login('Assigned instructor','INSTRUCTOR')
        student,_=login('QA student','STUDENT')
        other,_=login('Other student','STUDENT')
        check(student!=other,'Test users must be two separate students')
        tag=uuid.uuid4().hex[:10].upper()
        quiz,component,qid,offering=fresh_quiz(cn,admin,instructor,student,username,tag)
        submit_path=lambda aid:f'/api/quizzes/attempt/{aid}/submit/'
        save_path=lambda aid:f'/api/quizzes/attempt/{aid}/response/'

        print('\nPHASE A — four simultaneous submit requests (one saved correct answer)')
        a1,right,wrong=new_attempt(student,quiz,qid,tag)
        expected_http(save_path(a1),student,{200,201},{
            'question_id':qid,'selected_option_ids':[right]})
        results=parallel_cases([(f'submit{i}',submit_path(a1),student,None,'POST')
                                for i in range(MAX_WORKERS)])
        validate_concurrent_http(results,1,'Concurrent submit')
        attempt_submitted(cn,a1)
        saved=saved_answer(cn,a1,qid)
        check(int(saved[1])==right, 'Parallel submits did not modify previously saved option')
        grade_snapshot(cn,a1,10)
        check_private(student,other,a1)

        print('\nPHASE B — autosaves and submits competing on the second attempt')
        a2,right,wrong=new_attempt(student,quiz,qid,tag)
        expected_http(save_path(a2),student,{200,201},{
            'question_id':qid,'selected_option_ids':[right]})
        cases=[
            ('save-correct',save_path(a2),student,{'question_id':qid,'selected_option_ids':[right]},'POST'),
            ('save-wrong',save_path(a2),student,{'question_id':qid,'selected_option_ids':[wrong]},'POST'),
            ('submit0',submit_path(a2),student,None,'POST'),
            ('submit1',submit_path(a2),student,None,'POST'),
        ]
        results=parallel_cases(cases)
        validate_concurrent_http(results,1,'Submit-autosave race')
        attempt_submitted(cn,a2)
        final_saved=saved_answer(cn,a2,qid)
        check(str(final_saved[2]) in ('Y','N'), 'Saved answer has a valid correctness flag')
        expected=10.0 if str(final_saved[2])=='Y' else 0.0
        grade_snapshot(cn,a2,expected)
        check_private(student,other,a2)
        mark=select_rows(cn,f'''SELECT sm.MARKS_OBTAINED FROM {SCHEMA}.STUDENT_MARK sm
            JOIN {SCHEMA}.ENROLLMENT e ON e.ENROLLMENT_ID=sm.ENROLLMENT_ID
            JOIN {SCHEMA}.ASSESSMENT_COMPONENT ac ON ac.COMPONENT_ID=sm.COMPONENT_ID
            JOIN {SCHEMA}.GRADING_SCHEME gs ON gs.SCHEME_ID=ac.SCHEME_ID
            WHERE e.OFFERING_ID=? AND ac.COMPONENT_ID=?''',(offering,component))
        check(len(mark)==1 and abs(float(mark[0][0])-10)<0.001,
              'Highest-score STUDENT_MARK remains 10/10 after both races')
        for aid in (a1,a2):
            status,_=http(save_path(aid),student,
                {'question_id':qid,'selected_option_ids':[wrong]})
            check(status in {400,403,409,422},f'Attempt {aid}: post-submit autosave denied')
        check(len(select_rows(cn,f'''SELECT ATTEMPT_ID FROM {SCHEMA}.QUIZ_ATTEMPT
                  WHERE QUIZ_ID=?''',(quiz,)))==2,'No duplicate or hidden extra attempt')
        print('\nSUCCESS: bounded concurrency, single submission/grading, saved-answer integrity,')
        print('highest-score preservation, and unpublished-result security all passed.')
        print(f'QA RECORDS: tag={tag} quiz={quiz} attempt1={a1} attempt2={a2} component={component}')
        print('Visibility stays N/N. No cleanup, no existing QA records altered.')
        return 0
    finally:
        cn.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--main-backend',required=True)
    parser.add_argument('--base-url',default=BASE_URL)
    args=parser.parse_args()
    if args.base_url.rstrip('/')!=BASE_URL:
        parser.error('Only localhost main QA server '+BASE_URL+' is permitted.')
    try:
        return run(args)
    except (StopTest, URLError, KeyError, ValueError, TypeError, ImportError, OSError, TimeoutError) as e:
        print('\nTEST STOPPED:',e)
        print('If a new fixture was created it remains in Oracle for inspection.')
        print('A failure does not authorize a production deployment or automatic cleanup.')
        return 1


if __name__=='__main__':
    sys.exit(main())
