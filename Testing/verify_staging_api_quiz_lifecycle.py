"""End-to-end API test, permanently creates disposable STAGING records.

All mutations are sent to the Django REST API. Read-only Oracle SELECTs resolve
IDs because the master-data creation endpoint currently omits new row IDs.
Strictly refuses to run without a staging-only local backend configuration,
a healthy staging API on 127.0.0.1:8001, and explicit consent.
"""
import argparse
from datetime import date, timedelta
import getpass
import json
import re
from pathlib import Path
import sys
import uuid
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

BASE_URL = 'http://127.0.0.1:8001'
SCHEMA = 'EDUSPHERE_STAGE_OWNER'
APP_USER = 'EDUSPHERE_STAGE_APP'

class StopTest(Exception):
    pass


def http(path, token=None, data=None, method=None):
    headers = {'Accept': 'application/json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    if data is not None:
        headers['Content-Type'] = 'application/json'
    content = None if data is None else json.dumps(data).encode('utf-8')
    req = Request(BASE_URL+path, content, headers, method=method or ('POST' if data is not None else 'GET'))
    try:
        with urlopen(req, timeout=20) as resp:
            payload = resp.read().decode('utf-8', 'replace')
            return resp.status, json.loads(payload) if payload else {}
    except HTTPError as exc:
        payload = exc.read().decode('utf-8', 'replace')
        try:
            return exc.code, json.loads(payload)
        except ValueError:
            return exc.code, {'detail':payload[:500]}


def expected_http(path, token, expected, payload=None, method=None):
    status, body = http(path, token, payload, method)
    if status not in expected:
        raise StopTest(f'HTTP {status} on {path}; expected {expected}; response={str(body)[:450]}')
    if isinstance(body,dict) and body.get('success') is False:
        raise StopTest(f'Application-reported failure on {path}: {str(body)[:300]}')
    return body.get('data',body) if isinstance(body,dict) else body


def check(condition, name):
    if not condition:
        raise StopTest('FAIL: '+name)
    print('PASS:', name)


def login(who, role):
    print(f'\nLogin {who} ({role})')
    username = input('Username: ').strip()
    password = getpass.getpass('Password (hidden): ')
    status, result = http('/api/auth/login/', data={'username':username,'password':password})
    if status != 200 or result.get('user',{}).get('role') != role or not result.get('access'):
        raise StopTest(f'Login failed for {who}: HTTP {status}. Check stage account, password and role.')
    check(username.startswith('STAGE_'), f'{who} uses a STAGE_ account')
    return result['access'], username


def preflight(stage_backend):
    from dotenv import dotenv_values
    import pyodbc
    backend = Path(stage_backend).resolve()
    if not backend.name.endswith('_STAGING') or not (backend/'manage.py').is_file():
        raise StopTest('Refusing: --staging-backend must be your _STAGING Django folder with manage.py.')
    conf = dotenv_values(backend/'.env')
    if conf.get('ODBC_USER') != APP_USER or conf.get('ORACLE_SCHEMA') != SCHEMA:
        raise StopTest('Refusing: staging .env Oracle account/schema does not match.');
    if conf.get('ODBC_CONNECTION_STRING','').strip():
        raise StopTest('Refusing: staging .env contains an ODBC_CONNECTION_STRING override.')
    repo = (backend/'quiz'/'repository.py').read_text(encoding='utf-8')
    dynamic_routines = all('{object_name("'+name+'")}' in repo for name in (
        'PR_START_QUIZ_ATTEMPT','PR_SUBMIT_QUIZ_ATTEMPT'))
    explicit_stage_routines = all('EDUSPHERE_STAGE_OWNER.'+name in repo for name in (
        'PR_START_QUIZ_ATTEMPT','PR_SUBMIT_QUIZ_ATTEMPT'))
    if 'EDUSPHERE_OWNER.PR_' in repo or not (dynamic_routines or explicit_stage_routines):
        raise StopTest('Refusing: backend quiz procedure calls are not staging-safe.')
    connstr = f"DSN={conf['ODBC_DSN']};UID={conf['ODBC_USER']};PWD={conf['ODBC_PASSWORD']}"
    cn = pyodbc.connect(connstr,timeout=6)
    try:
        cur = cn.cursor()
        cur.execute("SELECT USER, SYS_CONTEXT('USERENV','CON_NAME') FROM DUAL")
        db_user, pdb = [str(v).upper() for v in cur.fetchone()]
        check((db_user,pdb)==(APP_USER,'XEPDB1'), 'Oracle login is staging app in XEPDB1')
        cur.execute('SELECT COUNT(*) FROM ALL_TABLES WHERE OWNER=?',(SCHEMA,))
        check(int(cur.fetchone()[0])==37, 'Staging account sees exactly 37 staging tables')
        cur.execute("SELECT COUNT(*) FROM ALL_TABLES WHERE OWNER='EDUSPHERE_OWNER'")
        check(int(cur.fetchone()[0])==0, 'Staging Oracle account sees no original-owner tables')
        status, health = http('/api/db-health/')
        check(status==200 and health.get('schema')==SCHEMA and health.get('status')=='ok',
              'Django API on 8001 reports healthy staging schema')
        return cn
    except Exception:
        cn.close()
        raise


def sql_find_id(conn,table,id_column,column,value):
    # Every identifier is a constant from the internal call site; no untrusted SQL identifiers.
    assert table in ('COURSE','SEMESTER')
    assert (table,id_column,column) in (("COURSE","COURSE_ID","COURSE_CODE"),
                                        ("SEMESTER","SEMESTER_ID","ACADEMIC_YEAR"))
    cursor=conn.cursor()
    cursor.execute(f'SELECT {id_column} FROM {SCHEMA}.{table} WHERE {column}=?', (value,))
    rows=cursor.fetchall()
    if len(rows)!=1:
        raise StopTest(f'Expected exactly one staging {table} with {column}={value}, got {len(rows)}.')
    return int(rows[0][0])


def item_by_username(items,username):
    found=[x for x in items if str(x.get('username','')).upper()==username.upper()]
    if len(found)!=1: raise StopTest(f'{username} not found exactly once in admin directory')
    return found[0]


def assure_unchanged(qid,own_token,before):
    current=expected_http(f'/api/quizzes/questions/{qid}/',own_token,{200})
    check(current==before, f'Question #{qid} answer metadata unchanged after blocked write')



def exercise_attempt_lock(quiz_id, qid, unique, i1, i2, admin, student, details, course_id, semester_id, offering_id):
    started=expected_http(f'/api/quizzes/{quiz_id}/attempt/',student,{200,201},method='POST')
    attempt_id=int(started['attempt_id'])
    print('Started staging attempt:',attempt_id)
    locked_option={'question_id':qid,'option_text':'LOCK MUST BLOCK '+unique,
                   'is_correct':'N','option_order':99}
    for label,token in [('author',i1),('admin',admin)]:
        status,body=http('/api/quizzes/questions/options/create/',token,locked_option)
        check(status==400, f'Answer key locked against {label} immediately after attempt starts (400)')
        assure_unchanged(qid,i1,details)
    content=expected_http(f'/api/quizzes/{quiz_id}/content/',student,{200})
    question=next((x for x in content['questions'] if int(x['question_id'])==qid),None)
    check(bool(question), 'Student can retrieve question in their open attempt')
    check(all(not any(k in o for k in ('is_correct','option_order','match_key'))
              for o in question['options']), 'Student content does not expose answer keys/order')
    opts=question['options']
    correct=next((o['option_id'] for o in opts if o['option_text']=='Correct-'+unique),None)
    check(correct is not None, 'Student sees expected answer option ID')
    expected_http(f'/api/quizzes/attempt/{attempt_id}/response/',student,{200,201},{
        'question_id':qid,'selected_option_ids':[correct]})
    expected_http(f'/api/quizzes/attempt/{attempt_id}/submit/',student,{200,201},method='POST')
    print('Submitted staging attempt:',attempt_id)
    for label,token in [('author',i1),('admin',admin)]:
        status,_=http('/api/quizzes/questions/options/create/',token,locked_option)
        check(status==400, f'Answer key locked against {label} after SUBMISSION (400)')
        assure_unchanged(qid,i1,details)
    grading=expected_http(f'/api/quizzes/{quiz_id}/grading/',i1,{200})
    check(any(int(x['attempt_id'])==attempt_id for x in grading), 'Instructor can see submitted attempt for grading')
    status,_=http(f'/api/quizzes/{quiz_id}/grading/',i2)
    check(status==403, 'Unassigned instructor cannot retrieve grading list (403)')
    print('\nSUCCESS: staging API quiz lifecycle, question lock, isolation, and student submission passed.')
    print(f'STAGING IDs: course={course_id}, semester={semester_id}, offering={offering_id}, '
          f'quiz={quiz_id}, question={qid}, attempt={attempt_id}')
    print('Test fixture remains in staging. No original Oracle schema or records were modified by this script.')
    return 0



def resolve_staging_fixture(conn, unique, student_username):
    """Read-only lookup for a fixture created by a prior interrupted run.

    Limits reuse to the exact random 10-hex test marker and the original course,
    quiz and single question created under the staging owner.
    """
    if not re.fullmatch(r'[0-9A-F]{10}', unique):
        raise StopTest('The --resume-tag must be the exact 10-character uppercase hex test identifier.')
    cur = conn.cursor()
    cur.execute(f"""
        SELECT c.COURSE_ID, sm.SEMESTER_ID, off.OFFERING_ID, q.QUIZ_ID, qq.QUESTION_ID
          FROM {SCHEMA}.COURSE c
          JOIN {SCHEMA}.COURSE_OFFERING off ON off.COURSE_ID=c.COURSE_ID
          JOIN {SCHEMA}.SEMESTER sm ON sm.SEMESTER_ID=off.SEMESTER_ID
          JOIN {SCHEMA}.GRADING_SCHEME gs ON gs.OFFERING_ID=off.OFFERING_ID
          JOIN {SCHEMA}.ASSESSMENT_COMPONENT ac ON ac.SCHEME_ID=gs.SCHEME_ID
          JOIN {SCHEMA}.QUIZ q ON q.COMPONENT_ID=ac.COMPONENT_ID
          JOIN {SCHEMA}.QUIZ_QUESTION qq ON qq.QUIZ_ID=q.QUIZ_ID
         WHERE c.COURSE_CODE=? AND sm.ACADEMIC_YEAR=? AND q.QUIZ_TITLE=?
        """, ('QA'+unique, 'QA'+unique, 'API Attempted Lock '+unique))
    rows=cur.fetchall()
    if len(rows)!=1:
        raise StopTest(f'Resume requires exactly one complete staging quiz fixture, found {len(rows)}.')
    course_id, semester_id, offering_id, quiz_id, qid = [int(x) for x in rows[0]]
    cur.execute(f'SELECT COUNT(*) FROM {SCHEMA}.QUIZ_ATTEMPT WHERE QUIZ_ID=?', (quiz_id,))
    if int(cur.fetchone()[0])!=0:
        raise StopTest('Cannot resume: staging quiz already has an attempt. Refusing possible duplicate submissions.')
    cur.execute(f"""
        SELECT COUNT(*) FROM {SCHEMA}.ENROLLMENT e
        JOIN {SCHEMA}.STUDENT s ON s.STUDENT_ID=e.STUDENT_ID
        JOIN {SCHEMA}.LMS_USER u ON u.USER_ID=s.USER_ID
        WHERE e.OFFERING_ID=? AND UPPER(u.USERNAME)=UPPER(?)
          AND e.ENROLLMENT_STATUS='ENROLLED'
        """, (offering_id,student_username))
    if int(cur.fetchone()[0])!=1:
        raise StopTest('The staging student is not enrolled in this fixture.')
    return course_id, semester_id, offering_id, quiz_id, qid


def run(args):
    cn=preflight(args.staging_backend)
    try:
        if args.resume_tag:
            print('\nThis will START and SUBMIT the previously created disposable STAGING quiz.')
        else:
            print('\nThis will PERMANENTLY create disposable academic records, a quiz and a submitted attempt in STAGING.')
        print('There is no cleanup. Nothing will be written before you confirm.')
        confirm=input('Type STAGING API TEST DATA ONLY to continue: ').strip()
        if confirm!='STAGING API TEST DATA ONLY':
            print('Cancelled. No API writes.'); return 3
        admin,au=login('Administrator','ADMIN')
        i1,u1=login('Instructor A','INSTRUCTOR')
        i2,u2=login('Instructor B','INSTRUCTOR')
        student,us=login('Student','STUDENT')
        if args.resume_tag:
            unique=args.resume_tag
            course_id, semester_id, offering_id, quiz_id, qid = resolve_staging_fixture(cn, unique, us)
            print(f'\nResuming the existing STAGING fixture {unique}: quiz={quiz_id}, question={qid}')
            details=expected_http(f'/api/quizzes/questions/{qid}/',i1,{200})
            check(details['question']['question_text']=='Which staging option is correct? '+unique,
                  'Resumed question matches the original test identifier')
            check(details['question']['question_type']=='MCQ_SINGLE' and len(details['options'])==2,
                  'Resumed unused MCQ has exactly two options')
            return exercise_attempt_lock(quiz_id, qid, unique, i1, i2, admin, student, details,
                                         course_id, semester_id, offering_id)
        unique=uuid.uuid4().hex[:10].upper()
        print('\nTest identifier:',unique)
        directory=expected_http('/api/admin/manage/directory/',admin,{200})
        programs=directory['programs']
        if not programs: raise StopTest('Staging needs an existing program; run staging sample-accounts SQL first.')
        program_id=int(programs[0]['program_id'])
        instructor_id=int(item_by_username(directory['instructors'],u1)['instructor_id'])
        check(instructor_id>0, 'Instructor A resolved from STAGING directory')
        course_code=('QA'+unique)[:30]
        academic_year='QA'+unique
        semester_name='Staging QA'
        expected_http('/api/admin/manage/master/course/',admin,{200,201},{
            'program_id':program_id,'course_code':course_code,
            'course_name':'API lock test '+unique,'credits':3,
            'course_description':'Disposable staging question lock API fixture'})
        expected_http('/api/admin/manage/master/semester/',admin,{200,201},{
            'semester_name':semester_name,'academic_year':academic_year,
            'semester_start_date':(date.today()-timedelta(days=14)).isoformat(),
            'semester_end_date':(date.today()+timedelta(days=120)).isoformat()})
        course_id=sql_find_id(cn,'COURSE','COURSE_ID','COURSE_CODE',course_code)
        semester_id=sql_find_id(cn,'SEMESTER','SEMESTER_ID','ACADEMIC_YEAR',academic_year)
        print('Read-only Oracle ID lookup: course',course_id,'semester',semester_id)
        offering_data=expected_http('/api/admin/manage/offerings/',admin,{200,201},{
            'course_id':course_id,'semester_id':semester_id,
            'section_code':'QA','capacity':10,'offering_status':'OPEN',
            'instructor_ids':[instructor_id]})
        offering_id=int(offering_data['offering']['offering_id'])
        print('Created staging offering:',offering_id)
        scheme=expected_http(f'/api/admin/manage/offerings/{offering_id}/grading-scheme/',admin,{200},{
            'scheme_name':'API lock test scheme',
            'components':[{'component_name':'API Quiz','component_type':'QUIZ',
                           'weight_percentage':100,'max_marks':10}]},'PUT')
        scheme=expected_http(f'/api/admin/manage/offerings/{offering_id}/grading-scheme/',admin,{200})
        comps=[c for c in scheme.get('components',[]) if c['component_type']=='QUIZ']
        if len(comps)!=1: raise StopTest('Expected one QUIZ component after grading scheme save')
        comp_id=int(comps[0]['component_id'])
        expected_http('/api/quizzes/create/',i1,{200,201},{
            'component_id':comp_id,'quiz_title':'API Attempted Lock '+unique,
            'open_at':None,'close_at':None,'duration_minutes':30,'max_attempts':1})
        quizzes=expected_http(f'/api/quizzes/?component_id={comp_id}',i1,{200})
        if not isinstance(quizzes,list) or len(quizzes)!=1: raise StopTest('Expected one quiz after quiz create')
        quiz_id=int(quizzes[0]['quiz_id'])
        q=expected_http('/api/quizzes/questions/create/',i1,{200,201},{
            'question_text':'Which staging option is correct? '+unique,'question_type':'MCQ_SINGLE'})
        qid=int(q['question_id'])
        for text,correct,order in [('Correct-'+unique,'Y',1),('Incorrect-'+unique,'N',2)]:
            expected_http('/api/quizzes/questions/options/create/',i1,{200,201},{
                'question_id':qid,'option_text':text,'is_correct':correct,'option_order':order})
        details=expected_http(f'/api/quizzes/questions/{qid}/',i1,{200})
        check(len(details['options'])==2, 'Instructor created two answer options through API')
        status,_=http('/api/quizzes/questions/options/create/',i2,
            {'question_id':qid,'option_text':'Forbidden','is_correct':'Y','option_order':99})
        check(status==403, 'Other instructor denied BEFORE quiz attempt (403)')
        assure_unchanged(qid,i1,details)
        expected_http('/api/quizzes/questions/add/',i1,{200,201},{
            'quiz_id':quiz_id,'question_id':qid,'question_order':1,'question_marks':10})
        enrollment=expected_http('/api/enrollments/',student,{200,201},{'offering_id':offering_id})
        check(enrollment is not None, 'Student enrollment API succeeds')
        return exercise_attempt_lock(quiz_id, qid, unique, i1, i2, admin, student, details,
                                     course_id, semester_id, offering_id)
    finally:
        cn.close()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--staging-backend',required=True,help='Exact _STAGING backend folder containing manage.py and .env')
    p.add_argument('--base-url',default=BASE_URL,help='Must be exactly http://127.0.0.1:8001')
    p.add_argument('--resume-tag',help='Reuse a staging quiz from an interrupted run (10-character test identifier)')
    args=p.parse_args()
    if args.base_url.rstrip('/')!=BASE_URL:
        p.error('Refusing: this write test only permits http://127.0.0.1:8001')
    try:
        return run(args)
    except (StopTest,URLError,KeyError,ValueError,TypeError,ImportError) as exc:
        print('\nSTOPPED:',exc)
        print('If writes began, partial disposable staging records may remain. Do not rerun on production.')
        return 1

if __name__=='__main__':
    sys.exit(main())
