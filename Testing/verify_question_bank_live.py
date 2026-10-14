"""Read-only EduSphere question-bank access acceptance test.

Prerequisites:
  - Latest compliance-repair Django backend running against Oracle.
  - Two ACTIVE instructor logins with different offering assignments.
  - Prefer at least one question visible only to each instructor.
  - Optional admin and student logins for extra checks.

Uses Python stdlib. Prompts for usernames and passwords without saving them.
Never creates/updates/deletes questions. Login may update last-login/audit logs.

Run: python verify_question_bank_live.py --base-url http://127.0.0.1:8000
"""
import argparse
import getpass
import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


def call(base, path, token=None, data=None):
    headers={'Accept':'application/json'}
    body=None
    if data is not None:
        body=json.dumps(data).encode('utf-8')
        headers['Content-Type']='application/json'
    if token:headers['Authorization']=f'Bearer {token}'
    req=Request(base.rstrip('/')+path, data=body,headers=headers,method='POST' if data is not None else 'GET')
    try:
        with urlopen(req,timeout=15) as resp:
            raw=resp.read().decode('utf-8','replace')
            return resp.status,json.loads(raw) if raw else {}
    except HTTPError as exc:
        raw=exc.read().decode('utf-8','replace')
        try: payload=json.loads(raw)
        except ValueError: payload={'detail':raw[:250]}
        return exc.code,payload


def login(base, label, expected_role, optional=False):
    print(f'\n{label} ({expected_role})')
    username=input('  Username'+(' [Enter to skip]' if optional else '')+': ').strip()
    if optional and not username:return None
    if not username:raise ValueError(f'{label} username is required')
    password=getpass.getpass('  Password (hidden): ')
    status,payload=call(base,'/api/auth/login/',data={'username':username,'password':password})
    if status!=200:
        print(f'  LOGIN FAILURE: HTTP {status}, {str(payload)[:180]}')
        raise RuntimeError(f'{label} login unsuccessful')
    role=payload.get('user',{}).get('role')
    if role!=expected_role:raise RuntimeError(f'{label}: expected {expected_role}, got {role}')
    print('  Logged in as role',role)
    return payload['access']


def qids(status,payload,label):
    if status!=200:
        print(f'FAIL {label}: HTTP {status}, {str(payload)[:160]}')
        return None
    data=payload.get('data')
    if not isinstance(data,list):
        print(f'FAIL {label}: list not returned, received {str(payload)[:160]}')
        return None
    return {int(q['question_id']) for q in data}


def check(name, expected, actual):
    ok=expected==actual
    print(f'{"PASS" if ok else "FAIL"}: {name} (expected HTTP {expected}, got {actual})')
    return ok


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url',default='http://127.0.0.1:8000')
    args=parser.parse_args()
    base=args.base_url.rstrip('/')
    print('EduSphere Question Bank — LIVE READ-ONLY acceptance test')
    print('Target:',base)
    print('No changes will be made to questions, options, attempts, or grades.')
    a=login(base,'Instructor A','INSTRUCTOR')
    b=login(base,'Instructor B','INSTRUCTOR')
    admin=login(base,'Administrator (optional)','ADMIN',optional=True)
    student=login(base,'Student (optional)','STUDENT',optional=True)
    passed=failed=skipped=0
    def record(condition):
        nonlocal passed,failed
        if condition:passed+=1
        else:failed+=1
    try:
        status,_=call(base,'/api/quizzes/questions/')
        record(check('Unauthenticated question list blocked',401,status))
        ast,ap=call(base,'/api/quizzes/questions/',a)
        bst,bp=call(base,'/api/quizzes/questions/',b)
        A=qids(ast,ap,'Instructor A list')
        B=qids(bst,bp,'Instructor B list')
        if A is None or B is None:
            print('Cannot continue; verify Oracle grants and service logs.')
            return 2
        print(f'Instructor A sees {len(A)} question(s), B sees {len(B)} question(s).')
        only_a=sorted(A-B)
        only_b=sorted(B-A)
        shared=sorted(A&B)
        print(f'Only A: {len(only_a)} | Only B: {len(only_b)} | Shared: {len(shared)}')
        if only_a:
            q=only_a[0]
            s,_=call(base,f'/api/quizzes/questions/{q}/',a)
            record(check(f'A can open question {q}',200,s))
            s,_=call(base,f'/api/quizzes/questions/{q}/',b)
            record(check(f'B cannot open A-only question {q}',403,s))
        else:
            skipped+=2
            print('SKIP A-only access/denial: no A-only question available.')
        if only_b:
            q=only_b[0]
            s,_=call(base,f'/api/quizzes/questions/{q}/',b)
            record(check(f'B can open question {q}',200,s))
            s,_=call(base,f'/api/quizzes/questions/{q}/',a)
            record(check(f'A cannot open B-only question {q}',403,s))
        else:
            skipped+=2
            print('SKIP B-only access/denial: no B-only question available.')
        if admin:
            status,payload=call(base,'/api/quizzes/questions/',admin)
            all_ids=qids(status,payload,'Administrator list')
            record(all_ids is not None and (A|B)<=all_ids)
            print(('PASS' if all_ids is not None and (A|B)<=all_ids else 'FAIL')+': admin sees union of both instructors\' question IDs')
            if only_a:
                s,_=call(base,f'/api/quizzes/questions/{only_a[0]}/',admin)
                record(check('Admin can open A-only question',200,s))
        else:skipped+=1
        if student:
            s,_=call(base,'/api/quizzes/questions/',student)
            record(check('Student question bank forbidden',403,s))
            if only_a:
                s,_=call(base,f'/api/quizzes/questions/{only_a[0]}/',student)
                record(check('Student cannot open answer metadata',403,s))
        else:skipped+=1
    except URLError as exc:
        print('Connection error:',exc)
        return 2
    print(f'\nSummary: {passed} passed, {failed} failed, {skipped} skipped.')
    if failed:return 1
    if skipped:print('Some tests require additional example questions/users before a complete verdict.')
    print('This was read-only. Mutating endpoints require a separate staging test.')
    return 0

if __name__=='__main__':
    raise SystemExit(main())
