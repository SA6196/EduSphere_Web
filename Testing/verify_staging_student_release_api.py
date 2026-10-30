"""Read-only (except login audit) staging API checks for student quiz release controls.

Run after applying the candidate to a *copy* of the Django staging backend.
Does not toggle release flags or change quiz records. If flags permit viewing,
the corresponding denial cases are skipped, not passed. Does not contact 8000.
"""
import argparse, getpass, json
from urllib.request import Request, urlopen
from urllib.error import HTTPError


def get(base, path, token=None, data=None):
    headers={'Accept':'application/json'}
    if token:headers['Authorization']='Bearer '+token
    body=json.dumps(data).encode('utf8') if data is not None else None
    if body is not None:headers['Content-Type']='application/json'
    req=Request(base+path,data=body,headers=headers,method='POST' if data is not None else 'GET')
    try:
        with urlopen(req, timeout=20) as response:
            raw=response.read().decode('utf8','replace')
            return response.status,json.loads(raw) if raw else {}
    except HTTPError as ex:
        raw=ex.read().decode('utf8','replace')
        try:return ex.code,json.loads(raw)
        except ValueError:return ex.code,{'message':raw[:100]}


def payload(value):
    return value.get('data', value) if isinstance(value,dict) else value


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url',default='http://127.0.0.1:8001')
    parser.add_argument('--attempt-id',type=int,required=True)
    args=parser.parse_args()
    base=args.base_url.rstrip('/')
    if base not in ('http://127.0.0.1:8001','http://localhost:8001'):
        parser.error('Refusing non-local or non-staging API port. Use port 8001.')
    status,health=get(base,'/api/db-health/')
    if status!=200 or health.get('schema')!='EDUSPHERE_STAGE_OWNER' or health.get('status')!='ok' or health.get('expected_tables')!=37:
        print('BLOCKED: staging health failed or expected 37 tables not confirmed:',status,health)
        return 2
    username=input('Staging student username: ').strip()
    if not username.startswith('STAGE_'):
        print('BLOCKED: staging-only username required');return 2
    password=getpass.getpass('Staging student password: ')
    status,identity=get(base,'/api/auth/login/',data={'username':username,'password':password})
    if status!=200 or identity.get('user',{}).get('role')!='STUDENT' or not identity.get('access'):
        print('BLOCKED: student login failed');return 2
    token=identity['access']
    passed=skipped=failed=0
    def check(label,condition,reason=None):
        nonlocal passed,failed
        if condition:passed+=1
        else:failed+=1
        print(('PASS' if condition else 'FAIL')+': '+label+((' :: '+reason) if reason else ''))
    status,history=get(base,'/api/quizzes/attempts/my/',token)
    rows=payload(history)
    if isinstance(rows,dict):rows=rows.get('attempts',[])
    if status!=200 or not isinstance(rows,list):
        print('BLOCKED: cannot retrieve student attempts');return 2
    chosen=next((x for x in rows if int(x.get('attempt_id',-1))==args.attempt_id),None)
    if not chosen:
        print('BLOCKED: attempt is not owned by logged-in staging student.');return 2
    quiz_id=int(chosen['quiz_id']);component_id=int(chosen['component_id']);offering_id=int(chosen['offering_id'])
    status,qlist=get(base,f'/api/quizzes/?component_id={component_id}',token)
    quizzes=payload(qlist)
    if status!=200 or not isinstance(quizzes,list):
        print('BLOCKED: scoped quiz listing failed.');return 2
    quiz=next((q for q in quizzes if int(q['quiz_id'])==quiz_id),None)
    if not quiz:
        print('BLOCKED: quiz absent from authorized student listing');return 2
    hidden_marks=str(quiz.get('allow_mark_view','N')).upper()!='Y'
    hidden_answers=str(quiz.get('allow_answer_review','N')).upper()!='Y'
    check('unauthenticated question bank denied',get(base,'/api/quizzes/questions/')[0]==401)
    check('student question bank denied',get(base,'/api/quizzes/questions/',token)[0]==403)
    check('student grading list denied',get(base,f'/api/quizzes/{quiz_id}/grading/',token)[0]==403)
    check('student grading detail denied',get(base,f'/api/quizzes/attempt/{args.attempt_id}/grading/',token)[0]==403)
    result_status,_=get(base,f'/api/quizzes/attempt/{args.attempt_id}/result/',token)
    review_status,_=get(base,f'/api/quizzes/attempt/{args.attempt_id}/review/',token)
    if hidden_marks:
        check('unreleased attempt marks denied at API',result_status==403)
        check('answer/response review denied when marks hidden',review_status==403)
        check('attempt listing redacts marks',chosen.get('marks_visible') is False and chosen.get('marks_obtained') is None)
        status,marks=get(base,'/api/marks/my/',token)
        values=payload(marks)
        check('general mark list excludes unreleased quiz',status==200 and isinstance(values,list) and not any(int(m.get('component_id',-1))==component_id for m in values))
        status,markbook=get(base,'/api/marks/my/semester-view/',token)
        values=payload(markbook)
        component=next((x for x in values.get('components',[]) if int(x.get('component_id',-1))==component_id),None) if isinstance(values,dict) else None
        check('semester markbook hides marks, time and status',status==200 and component is not None and component.get('marks_obtained') is None and component.get('recorded_at') is None and component.get('mark_status')=='HIDDEN')
        status,dashboard=get(base,'/api/student/dashboard/',token)
        values=payload(dashboard)
        courses=values.get('courses',[]) if isinstance(values,dict) else []
        course=next((x for x in courses if int(x.get('offering_id',-1))==offering_id),None)
        check('dashboard does not infer unreleased quiz from course percentage',status==200 and course is not None and course.get('course_percentage') is None)
    else:
        skipped+=6;print('SKIP: mark flag is Y; turn off mark visibility in staging to execute six denial cases.')
    if hidden_answers:
        check('answer key review denied while answer visibility is off',review_status==403)
    else:
        skipped+=1;print('SKIP: answer-review flag is Y; disable it in staging to test answer-key denial.')
    print(f'RESULT: {passed} passed, {failed} failed, {skipped} skipped. No quiz/mark data changed.')
    return 1 if failed else 0

if __name__=='__main__':raise SystemExit(main())
