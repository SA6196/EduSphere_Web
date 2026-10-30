"""Opt-in LIVE WRITE acceptance test for a disposable STAGING EduSphere Oracle DB.

No default writes; refusing to run unless --staging-write plus interactive confirmation.
Creates disposable questions and options permanently in STAGING; no automatic DELETE.
Use the separately bundled verify_question_bank_live.py on production (read-only).
"""
import argparse
import getpass
import json
import sys
import uuid
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


def request(base, path, token=None, body=None):
    headers = {'Accept': 'application/json'}
    data = None
    if body is not None:
        headers['Content-Type'] = 'application/json'
        data = json.dumps(body).encode('utf-8')
    if token:
        headers['Authorization'] = 'Bearer ' + token
    req = Request(base.rstrip('/') + path, data=data, headers=headers,
                  method='POST' if data is not None else 'GET')
    try:
        with urlopen(req, timeout=20) as r:
            content = r.read().decode('utf-8', 'replace')
            return r.status, json.loads(content) if content else {}
    except HTTPError as e:
        content = e.read().decode('utf-8', 'replace')
        try:
            payload = json.loads(content)
        except ValueError:
            payload = {'detail': content[:500]}
        return e.code, payload


def login(base, who, role, optional=False):
    print(f'\n{who} ({role})')
    username = input('Username' + (' [Enter to skip]' if optional else '') + ': ').strip()
    if not username and optional:
        return None
    if not username:
        raise RuntimeError(f'{who} is required')
    password = getpass.getpass('Password (hidden): ')
    status, result = request(base, '/api/auth/login/', body={'username':username,'password':password})
    if status != 200 or result.get('user', {}).get('role') != role:
        raise RuntimeError(f'Login failed for {who} (HTTP {status}, role={result.get("user", {}).get("role")})')
    return result['access']


def info(base, qid, token):
    return request(base, f'/api/quizzes/questions/{qid}/', token)


def question_id_of(result):
    return int(result.get('data', {}).get('question_id'))


def create_disposable(base, token, label):
    payload = {'question_text': f'STAGING DISPOSABLE QB WRITE TEST [{label}] [{uuid.uuid4().hex}]',
               'question_type': 'MCQ_SINGLE'}
    status, result = request(base, '/api/quizzes/questions/create/', token, payload)
    if status not in (200,201):
        raise RuntimeError(f'Could not create disposable {label} question: HTTP {status}: {result}')
    qid = question_id_of(result)
    print(f'Created disposable STAGING question #{qid} for {label}.')
    return qid


def add_option(base, token, qid, text, order, correct='N'):
    return request(base, '/api/quizzes/questions/options/create/', token,
                   {'question_id':qid, 'option_text':text,'is_correct':correct,
                    'option_order':order})


def run():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='http://127.0.0.1:8000')
    parser.add_argument('--staging-write', action='store_true',
                        help='Explicitly permit writes to your disposable STAGING database only')
    parser.add_argument('--attempted-question-id', type=int,
                        help='Existing attempted question ID IN STAGING ONLY, accessible to Instructor A')
    args = parser.parse_args()
    if not args.staging_write:
        print('READ-ONLY DEFAULT: no requests sent. For normal live reads run verify_question_bank_live.py.')
        print('For disposable STAGING write checks use --staging-write after verifying Django points to a clone.')
        return 0
    print('DANGER: the following test CREATES TWO questions and options in the DB connected to Django.')
    print('The script cannot determine whether your Oracle DSN is staging or production.')
    print('DO NOT use production. No cleanup or automatic rollback is performed.')
    phrase = input('Type exactly STAGING ORACLE DATA ONLY to continue: ').strip()
    if phrase != 'STAGING ORACLE DATA ONLY':
        print('Cancelled without API calls.'); return 3
    base = args.base_url.rstrip('/')
    try:
        a = login(base, 'Instructor A', 'INSTRUCTOR')
        b = login(base, 'Instructor B', 'INSTRUCTOR')
        admin = login(base, 'Administrator (optional)', 'ADMIN', optional=True)
    except (RuntimeError, URLError) as exc:
        print('Login error:', exc); return 2
    passed = failed = skipped = 0
    def record(title, actual, expected, detail=''):
        nonlocal passed, failed
        ok = actual in expected
        print(('PASS' if ok else 'FAIL') + f': {title}; expected {expected}, got {actual}', detail)
        passed += bool(ok)
        failed += not ok
        return ok
    try:
        qa = create_disposable(base, a, 'A')
        qb = create_disposable(base, b, 'B')
        s, _ = add_option(base, a, qa, 'A correct staging option',1,'Y')
        record('A may author answer key on A-owned unused question', s,(200,201))
        s, _ = add_option(base, b, qb, 'B correct staging option',1,'Y')
        record('B may author answer key on B-owned unused question', s,(200,201))
        for owner, intruder, qid, who in ((a,b,qa,'B against A'),(b,a,qb,'A against B')):
            original_status, original = info(base,qid,owner)
            if original_status != 200:
                raise RuntimeError(f'Owner cannot read newly created question {qid}; stop.')
            s, body = add_option(base,intruder,qid,'UNAUTHORIZED TEST OPTION',99,'N')
            record(who+' cannot add/alter answer options',s,(403,),str(body)[:120])
            check_status,after = info(base,qid,owner)
            record(who+' leaves answer metadata unchanged',
                   (check_status, after.get('data')),
                   ((original_status,original.get('data')),))
        if args.attempted_question_id:
            qid=args.attempted_question_id
            s,before=info(base,qid,a)
            if s!=200:
                raise RuntimeError(f'Attempted question {qid} must be accessible to A (got {s}); stop.')
            # Actual question must have a submitted/started attempt in the STAGING data.
            s,body=add_option(base,a,qid,'SHOULD NEVER BE SAVED',999,'N')
            record('Attempted question locks author answer change',s,(400,),str(body)[:160])
            check_s,after=info(base,qid,a)
            record('Attempted question keys unchanged',
                   (check_s,after.get('data')),((200,before.get('data')),))
            if admin:
                s,body=add_option(base,admin,qid,'SHOULD NEVER BE SAVED BY ADMIN',1000,'N')
                record('Attempted question locks admin answer change',s,(400,),str(body)[:160])
        else:
            skipped += 1
            print('SKIP attempted-question lock: supply --attempted-question-id for an attempted STAGING question.')
    except (RuntimeError,ValueError,KeyError,URLError) as exc:
        print('ERROR:',exc,'The test may already have created disposable staging data.')
        return 2
    print(f'\nSummary: {passed} passed, {failed} failed, {skipped} skipped.')
    print('Disposal: these staging questions remain in the staging database; reset the clone when finished.')
    return 1 if failed else 0

if __name__ == '__main__':
    sys.exit(run())
