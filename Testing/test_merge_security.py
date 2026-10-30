"""Fail-closed, database-free security regressions of the merged source.

Tests run actual service function bodies isolated from unavailable live Django/Oracle.
Use staging API tests before promoting this candidate.
"""
import ast
import pathlib
from types import SimpleNamespace
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
BACKEND = ROOT / 'Backend'

class Denied(Exception): pass
class NotFound(Exception): pass
class Business(Exception): pass


def source(rel):
    return (BACKEND / rel).read_text(encoding='utf8')


def method(rel, method_name, env, class_name='QuizService'):
    tree = ast.parse(source(rel))
    nodes = tree.body
    if class_name:
        nodes = next(n.body for n in nodes if isinstance(n, ast.ClassDef) and n.name == class_name)
    node = next(n for n in nodes if isinstance(n, ast.FunctionDef) and n.name == method_name)
    node.decorator_list = []
    local = dict(env)
    exec(compile(ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])), rel, 'exec'), local)
    return local[method_name]


def rolecheck(role, allowed):
    if role not in allowed: raise Denied('Forbidden role')

ROLES = SimpleNamespace(STUDENT='STUDENT', INSTRUCTOR='INSTRUCTOR', ADMIN='ADMIN')


def test_submission_never_serializes_marks_even_after_auto_grade():
    events = []
    f = method('quiz/services.py', 'submit_attempt', {
        'require_role': rolecheck, 'Roles': ROLES,
        'validate_positive_integer': lambda *args: None,
        'get_attempt': lambda a: {'student_id': 7},
        'get_attempt_submission_state': lambda a: {'submission_state': 'OPEN'},
        'submit_quiz_attempt': lambda a: events.append('submit'),
        'auto_grade_attempt': lambda a: {'auto_marks': 99, 'final_marks': 99, 'max_marks': 100, 'grading_id': 11},
        'log_activity': lambda **kw: events.append('audit'),
        'ActivityTypes': SimpleNamespace(QUIZ_ATTEMPT_SUBMITTED='submitted'),
        'NotFoundError': NotFound, 'PermissionDeniedError': Denied, 'BusinessRuleError': Business,
    })
    result = f(30, 7, 'STUDENT', 50)
    assert events == ['submit', 'audit']
    assert result['grading'] == {'status': 'PROCESSED'}
    assert all(forbidden not in repr(result).lower() for forbidden in ('auto_marks', 'final_marks', 'grading_id', '99'))


def test_submission_failure_never_discloses_internal_oracle_errors():
    def broken(*a): raise RuntimeError('ORA-SECRET-TEST 98 marks')
    f = method('quiz/services.py', 'submit_attempt', {
        'require_role': rolecheck, 'Roles': ROLES,
        'validate_positive_integer': lambda *args: None,
        'get_attempt': lambda a: {'student_id': 7},
        'get_attempt_submission_state': lambda a: {'submission_state': 'OPEN'},
        'submit_quiz_attempt': lambda a: None,
        'auto_grade_attempt': broken,
        'log_activity': lambda **kw: None,
        'ActivityTypes': SimpleNamespace(QUIZ_ATTEMPT_SUBMITTED='submitted'),
        'NotFoundError': NotFound, 'PermissionDeniedError': Denied, 'BusinessRuleError': Business,
    })
    response = f(30,7,'STUDENT',50)
    assert response['grading'] == {'status':'RETRY_REQUIRED'}
    assert 'SECRET' not in repr(response)


def test_student_cannot_submit_other_students_attempt():
    f=method('quiz/services.py','submit_attempt',{
        'require_role': rolecheck,'Roles':ROLES,'validate_positive_integer':lambda *a:None,
        'get_attempt':lambda a:{'student_id':8},
        'NotFoundError':NotFound,'PermissionDeniedError':Denied,
    })
    with pytest.raises(Denied): f(30,7,'STUDENT',50)


def test_student_cannot_get_unreleased_question_answer_review():
    context={'student_id':7,'submitted_at':'2026-10-17','allow_answer_review':'Y',
             'allow_mark_view':'N','review_allowed':True,'grading_status':'RELEASED'}
    f=method('quiz/services.py','attempt_review',{
        'require_role':rolecheck,'Roles':ROLES,'validate_positive_integer':lambda *a:None,
        'get_attempt_result_context':lambda a:context,
        'PermissionDeniedError':Denied,'BusinessRuleError':Business,'NotFoundError':NotFound,
    })
    with pytest.raises(Denied,match='marks'):
        f(7,'STUDENT',50)


def test_student_cannot_review_other_student_even_with_release_flags():
    context={'student_id':8,'submitted_at':'2026-10-17','allow_answer_review':'Y','allow_mark_view':'Y',
             'review_allowed':True,'grading_status':'RELEASED'}
    f=method('quiz/services.py','attempt_review',{
        'require_role':rolecheck,'Roles':ROLES,'validate_positive_integer':lambda *a:None,
        'get_attempt_result_context':lambda a:context,
        'PermissionDeniedError':Denied,'BusinessRuleError':Business,'NotFoundError':NotFound,
    })
    with pytest.raises(Denied): f(7,'STUDENT',50)


def test_quiz_list_requires_enrollment_and_instructor_assignment():
    calls=[]
    f=method('quiz/services.py','list_quizzes',{
        'require_role':rolecheck,'Roles':ROLES,'validate_positive_integer':lambda *a:None,
        'get_component':lambda c:{'offering_id':99},
        'student_has_offering':lambda s,o:s==7,
        'instructor_owns_offering':lambda i,o:i==3,
        'get_quizzes':lambda c:calls.append(c) or [{'quiz_id':40}],
        'NotFoundError':NotFound,'PermissionDeniedError':Denied,
    })
    with pytest.raises(Denied): f(44,'STUDENT',student_id=88)
    with pytest.raises(Denied): f(44,'INSTRUCTOR',instructor_id=77)
    assert not calls
    assert f(44,'STUDENT',student_id=7)==[{'quiz_id':40}]
    assert f(44,'INSTRUCTOR',instructor_id=3)==[{'quiz_id':40}]
    assert f(44,'ADMIN')==[{'quiz_id':40}]


def test_student_markbook_sql_redacts_grade_time_and_status():
    sql_queries=[]
    func=method('academics/repository.py','student_semester_markbook',{
        'fetch_all': lambda sql, args: sql_queries.append(sql) or [],
        'object_name': lambda n:'EDUSPHERE_OWNER.'+n,
        'quiz_marks_visible_sql':lambda *args:'VERIFIED_QUIZ_RELEASE',
    },class_name=None)
    result=func(7)
    assert result=={'semesters':[],'components':[]}
    code=sql_queries[1]
    assert code.count('CASE WHEN ac.COMPONENT_TYPE=\'QUIZ\' AND NOT VERIFIED_QUIZ_RELEASE')==3
    assert "THEN NULL ELSE sm.MARKS_OBTAINED" in code
    assert "THEN NULL ELSE sm.RECORDED_AT" in code
    assert "THEN 'HIDDEN'" in code


def test_student_my_marks_query_requires_strict_release_predicate():
    queries=[]
    f=method('academics/repository.py','student_marks',{
        'fetch_all':lambda sql,p:queries.append(sql) or [],
        'object_name':lambda n:n,
        'quiz_marks_visible_sql':lambda *a:'VERIFIED_QUIZ_RELEASE',
    },class_name=None)
    f(7)
    assert "ac.COMPONENT_TYPE <> 'QUIZ' OR VERIFIED_QUIZ_RELEASE" in queries[0]


def test_offering_visibility_requires_grade_and_no_pending_essay():
    mod=ast.parse(source('academics/quiz_visibility.py'))
    mod.body=[node for node in mod.body if not isinstance(node,(ast.Import,ast.ImportFrom))]
    scope={'object_name': lambda n:'EDUSPHERE_OWNER.'+n}
    exec(compile(mod,'acad-visibility','exec'),scope)
    expr=scope['quiz_marks_visible_sql']('q','e')
    assert 'NVL(q.ALLOW_MARK_VIEW' in expr
    assert 'qa.STUDENT_ID=e.STUDENT_ID' in expr
    assert "g.GRADING_STATUS IN ('REVIEWED','RELEASED')" in expr
    assert "g.GRADING_STATUS='AUTO_GRADED'" in expr
    assert 'NOT EXISTS' in expr and "question.QUESTION_TYPE='LONG_TEXT'" in expr
    assert 'qa.SUBMITTED_AT IS NOT NULL' in expr


def test_derived_dashboard_grades_not_exposed_for_hidden_quiz():
    s=source('academics/repository.py')
    r=source('reports/repository.py')
    assert 'CASE WHEN {hidden_quiz} THEN NULL' in s
    assert 'CASE WHEN {hidden_quiz} THEN NULL' in r
    assert 'offering_has_hidden_quiz_sql' in r


def test_health_covers_exact_approved_37_tables():
    tree=ast.parse(source('core/views.py'))
    node=next(x for x in tree.body if isinstance(x,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='EXPECTED_TABLES' for t in x.targets))
    actual=ast.literal_eval(node.value)
    ddl=(ROOT/'Database/Schema_Fixed/01_create_tables.sql').read_text()
    import re
    expected=set(re.findall(r'CREATE TABLE\s+([A-Z_]+)\s*\(',ddl,re.I))
    assert actual==expected and len(actual)==37


def test_procedures_use_current_configured_owner():
    s=source('quiz/repository.py')
    assert 'EDUSPHERE_OWNER.PR_START_QUIZ_ATTEMPT' not in s
    assert 'EDUSPHERE_OWNER.PR_SUBMIT_QUIZ_ATTEMPT' not in s
    assert '{object_name("PR_START_QUIZ_ATTEMPT")}' in s
    assert '{object_name("PR_SUBMIT_QUIZ_ATTEMPT")}' in s


def test_question_bank_listing_filtered_server_side_in_single_select():
    sqls=[]
    f=method('quiz/repository.py','list_questions_for_instructor',{
        'fetch_all':lambda sql,params:sqls.append((sql,params)) or [],
        'object_name':lambda n:n,
    },class_name=None)
    f(12,34)
    assert len(sqls)==1
    sql,params=sqls[0]
    assert params==(12,34)
    assert 'OFFERING_INSTRUCTOR' in sql and 'ACTIVITY_LOG' in sql
    assert 'WHERE qq.QUESTION_ID=q.QUESTION_ID AND oi.INSTRUCTOR_ID=?' in sql


def test_grading_uses_original_typed_business_exceptions():
    s=source('quiz/auto_grader.py')
    assert 'from core.exceptions import NotFoundError, BusinessRuleError' in s
    assert 'raise BusinessRuleError(' in s


def test_frontend_only_combines_identical_get_never_mutations():
    s=(ROOT/'Frontend/src/services/http.js').read_text()
    assert "method === 'GET'" in s
    assert 'pendingGets' in s
    assert '!options.signal' in s


def test_database_install_scripts_identical_to_original_web_source():
    import json, hashlib
    manifest=json.loads((ROOT/'Testing/BASELINE_SQL_SHA256.json').read_text())
    current={str(p.relative_to(ROOT/'Database')):hashlib.sha256(p.read_bytes()).hexdigest()
             for p in (ROOT/'Database').rglob('*.sql')}
    assert len(current)==len(manifest)==14
    assert current==manifest

@pytest.mark.parametrize('changes,expected_exception', [
    ({'student_id':8},Denied),
    ({'submitted_at':None},Business),
    ({'allow_mark_view':'N'},Denied),
    ({'grading_status':'AUTO_GRADED','long_text_count':2},Denied),
    ({'grading_status':None},Denied),
])
def test_attempt_result_rejects_unauthorized_or_provisional(changes,expected_exception):
    context={
        'student_id':7,'submitted_at':'2026-10-17','allow_mark_view':'Y',
        'grading_status':'AUTO_GRADED','long_text_count':0,
    }
    context.update(changes)
    f=method('quiz/services.py','attempt_result',{
        'require_role':rolecheck,'Roles':ROLES,'validate_positive_integer':lambda *a:None,
        'get_attempt_result_context':lambda a:context,
        'PermissionDeniedError':Denied,'BusinessRuleError':Business,'NotFoundError':NotFound,
    })
    with pytest.raises(expected_exception):f(7,'STUDENT',50)


def test_student_content_does_not_return_answer_keys_or_option_order():
    row={'question_id':3,'question_order':1,'question_marks':10,'question_text':'Which?',
         'question_type':'MATCHING','option_id':11,'option_text':'Left',
         'match_side':'L','match_key':'secret answer','is_correct':'Y','option_order':1}
    f=method('quiz/services.py','quiz_content',{
        'require_role':rolecheck,'Roles':ROLES,'validate_positive_integer':lambda *a:None,
        'get_quiz_context':lambda q:{'quiz_id':q,'offering_id':30},
        'get_open_attempt_for_student_quiz':lambda s,q:{'attempt_id':99,'started_at':'2026-10-17'},
        'get_quiz_content_rows':lambda *args,**kw:[row],
        'get_keywords':lambda q:[],
        'load_responses':lambda a:{},
        '_student_option_token':lambda *a:'opaque-token',
        '_student_option_shuffle':lambda items,*a:items,
        'PermissionDeniedError':Denied,'BusinessRuleError':Business,'NotFoundError':NotFound,
    })
    data=f('STUDENT',7,None,44)
    assert data['questions'][0]['options']==[{'option_id':'opaque-token','option_text':'Left','match_side':'L'}]
    assert 'secret answer' not in repr(data)
    assert 'is_correct' not in repr(data)
    assert 'option_order' not in repr(data)


def test_unstarted_attempt_cannot_force_question_content():
    f=method('quiz/services.py','quiz_content',{
        'require_role':rolecheck,'Roles':ROLES,'validate_positive_integer':lambda *a:None,
        'get_quiz_context':lambda q:{'quiz_id':q},
        'get_open_attempt_for_student_quiz':lambda s,q:None,
        'BusinessRuleError':Business,'NotFoundError':NotFound,
    })
    with pytest.raises(Business):f('STUDENT',7,None,44)


def test_review_denied_until_remaining_attempts_exhausted_or_closed():
    context={'student_id':7,'submitted_at':'2026-10-17','allow_answer_review':'Y',
             'allow_mark_view':'Y','review_allowed':False,'grading_status':'RELEASED'}
    f=method('quiz/services.py','attempt_review',{
        'require_role':rolecheck,'Roles':ROLES,'validate_positive_integer':lambda *a:None,
        'get_attempt_result_context':lambda a:context,
        'PermissionDeniedError':Denied,'BusinessRuleError':Business,'NotFoundError':NotFound,
    })
    with pytest.raises(Denied):f(7,'STUDENT',50)

@pytest.mark.parametrize('state',['DURATION_EXPIRED','QUIZ_CLOSED','ALREADY_SUBMITTED'])
def test_no_quiz_response_autosave_after_deadline(state):
    f=method('quiz/services.py','submit_response',{
        'require_role':rolecheck,'Roles':ROLES,'validate_positive_integer':lambda *a:None,
        'lock_attempt_for_answer_update':lambda a:{'student_id':7,'submitted_at':None},
        'get_attempt_submission_state':lambda a:{'submission_state':state},
        'PermissionDeniedError':Denied,'BusinessRuleError':Business,
        'NotFoundError':NotFound,
    })
    with pytest.raises(Business,match='expired or closed'):
        f(10,7,'STUDENT',40,20,'fake')


def test_no_old_response_option_endpoint_after_deadline():
    f=method('quiz/services.py','add_response_option',{
        'require_role':rolecheck,'Roles':ROLES,'validate_positive_integer':lambda *a:None,
        'get_response':lambda r:{'student_id':7,'submitted_at':None,'attempt_id':40},
        'get_attempt_submission_state':lambda a:{'submission_state':'QUIZ_CLOSED'},
        'PermissionDeniedError':Denied,'BusinessRuleError':Business,
        'NotFoundError':NotFound,
    })
    with pytest.raises(Business,match='expired or closed'):
        f(7,'STUDENT',20,30)


def test_expired_attempt_does_not_return_questions_or_saved_responses():
    queries=[]
    f=method('quiz/repository.py','get_open_attempt_for_student_quiz',{
        'fetch_one':lambda sql,params:queries.append((sql,params)) or None,
        'object_name':lambda name:name,
    },class_name=None)
    f(7,44)
    assert len(queries)==1
    sql,params=queries[0]
    assert params==(7,44)
    assert 'qa.SUBMITTED_AT IS NULL' in sql
    assert 'SYSTIMESTAMP <= q.CLOSE_AT' in sql
    assert "NUMTODSINTERVAL(q.DURATION_MINUTES, 'MINUTE')" in sql


def test_expired_attempt_can_still_be_submitted_without_exposing_marks():
    f=method('quiz/services.py','submit_attempt',{
        'require_role':rolecheck,'Roles':ROLES,'validate_positive_integer':lambda *a:None,
        'get_attempt':lambda a:{'student_id':7},
        'get_attempt_submission_state':lambda a:{'submission_state':'DURATION_EXPIRED'},
        'submit_quiz_attempt':lambda a:None,
        'auto_grade_attempt':lambda a:{'auto_marks':90,'final_marks':90},
        'log_activity':lambda **kw:None,
        'ActivityTypes':SimpleNamespace(QUIZ_ATTEMPT_SUBMITTED='submitted'),
        'NotFoundError':NotFound,'PermissionDeniedError':Denied,'BusinessRuleError':Business,
    })
    response=f(5,7,'STUDENT',40)
    assert response['grading']=={'status':'PROCESSED'}
    assert '90' not in repr(response)
