"""Read-only, database-free regression checks of actual EduSphere question-bank functions.
Run from the delivered folder with:
    python -m pytest -q test_question_bank_permissions_offline.py
Set EDUSPHERE_BACKEND to the extracted Django backend directory if needed.
"""
import ast
import os
from pathlib import Path
from types import SimpleNamespace
import pytest

def find_backend():
    override = os.environ.get('EDUSPHERE_BACKEND')
    if override:
        return Path(override)
    # Works if the test is put alongside the backend directory or into a
    # Question_Bank_Verification folder next to that directory.
    here = Path(__file__).resolve()
    for parent in (here.parent, here.parent.parent, here.parent.parent.parent):
        if (parent / 'quiz' / 'repository.py').exists():
            return parent
        matches = [d for d in parent.glob('EduSphere_Django_Backend*') if (d / 'quiz' / 'repository.py').exists()]
        if matches:
            return matches[0]
        matches = list(parent.glob('EduSphere_*/EduSphere_Django_Backend*'))
        for match in matches:
            if (match / 'quiz' / 'repository.py').exists():
                return match
    raise RuntimeError('Could not find the Django backend. Set EDUSPHERE_BACKEND to the backend folder.')

PROJECT = find_backend()

class PermissionDeniedError(Exception): pass
class NotFoundError(Exception): pass
class BusinessRuleError(Exception): pass


def method(path, name, env, cls=None):
    tree = ast.parse((PROJECT/path).read_text(encoding='utf-8'))
    nodes = tree.body
    if cls:
        nodes = next(n.body for n in nodes if isinstance(n, ast.ClassDef) and n.name == cls)
    selected = next(n for n in nodes if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name)
    selected.decorator_list=[]
    scope=dict(env)
    exec(compile(ast.fix_missing_locations(ast.Module(body=[selected],type_ignores=[])),str(PROJECT/path),'exec'),scope)
    return scope[name]

class FakeOracle:
    # question 1 by user 11 (instructor 101), question 2 by user 22 (instructor 202)
    # question 3 is a legacy unowned question linked ONLY to offering 501 (instructor 101)
    # question 4 shared across offerings 501 and 502; question 5 is unowned/unattached
    authors={1:11,2:22}
    linked={3:[501],4:[501,502]}
    assigned={(501,101),(502,202)}
    attempted={4}
    def fetch_one(self, sql, vals):
        if 'ACTIVITY_DESCRIPTION=?' in sql:
            user_id, description=vals
            qid=int(description.split('=')[1].split(';')[0])
            return {'ok':1} if self.authors.get(qid)==user_id else None
        if 'OFFERING_INSTRUCTOR' in sql:
            offering,instructor=vals
            return {'ok':1} if (offering,instructor) in self.assigned else None
        if 'JOIN' in sql and 'QUIZ_ATTEMPT' in sql:
            return {'ok':1} if vals[0] in self.attempted else None
        raise AssertionError('Unexpected SQL in fake Oracle: '+sql)
    def fetch_all(self,sql,vals):
        if 'QUIZ_QUESTION' in sql and 'GRADING_SCHEME' in sql:
            return [{'offering_id': x} for x in self.linked.get(vals[0],[])]
        raise AssertionError('Unexpected SQL in fake Oracle: '+sql)

@pytest.fixture
def access():
    fake=FakeOracle()
    return method('quiz/repository.py','question_access_for_instructor',{
        'fetch_one':fake.fetch_one,'fetch_all':fake.fetch_all,'object_name':lambda x:x})

def test_author_can_read_and_edit_unattached_unattempted_question(access):
    assert access(1,101,11,edit=False)
    assert access(1,101,11,edit=True)

def test_foreign_unshared_question_is_hidden_and_uneditable(access):
    assert not access(1,202,22,edit=False)
    assert not access(1,202,22,edit=True)

def test_linked_own_offering_question_visible(access):
    assert access(3,101,11,edit=False)
    assert not access(3,202,22,edit=False)

def test_legacy_unattached_question_is_admin_only(access):
    assert not access(5,101,11,edit=False)
    assert not access(5,202,22,edit=False)

def test_shared_question_read_if_any_offering_assigned_but_edit_denied(access):
    assert access(4,101,11,edit=False)
    assert access(4,202,22,edit=False)
    assert not access(4,101,11,edit=True)
    assert not access(4,202,22,edit=True)

def test_edit_rights_on_unattempted_legacy_question_linked_to_owned_offering(access):
    # Current implementation permits the assigned instructor to edit unowned legacy questions.
    assert access(3,101,11,edit=True)

def test_question_bank_list_filters_and_admin_sees_all(access):
    access_fake={1:True,2:False,3:True}
    def rolecheck(role,allowed):
        if role not in allowed:raise PermissionDeniedError('Forbidden role')
    roles=SimpleNamespace(INSTRUCTOR='INSTRUCTOR',ADMIN='ADMIN')
    f=method('quiz/services.py','question_bank',{
        'require_role':rolecheck,'Roles':roles,
        'list_questions':lambda:[{'question_id':n} for n in access_fake],
        'question_access_for_instructor':lambda q,i,u,edit=False:access_fake[q],
    },cls='QuizService')
    assert [q['question_id'] for q in f('INSTRUCTOR',101,11)]==[1,3]
    assert [q['question_id'] for q in f('ADMIN')]==[1,2,3]
    with pytest.raises(PermissionDeniedError):f('STUDENT',0,0)

def test_detail_checks_permission_before_returning_keys(access):
    roles=SimpleNamespace(INSTRUCTOR='INSTRUCTOR',ADMIN='ADMIN')
    calls=[]
    def require_role(role,allowed):
        if role not in allowed:raise PermissionDeniedError()
    f=method('quiz/services.py','question_detail',{
        'Roles':roles,'require_role':require_role,
        'validate_positive_integer':lambda val,name:None,
        'get_question':lambda q:{'question_id':q},
        'question_access_for_instructor':access,
        'get_question_options':lambda q,include_correct=True:calls.append('options') or [{'is_correct':'Y'}],
        'get_numeric_rule':lambda q:None,'get_keywords':lambda q:[],
        'PermissionDeniedError':PermissionDeniedError,'NotFoundError':NotFoundError,
    },cls='QuizService')
    with pytest.raises(PermissionDeniedError):f('INSTRUCTOR',1,202,22)
    assert calls==[] # no answer metadata fetched
    assert f('INSTRUCTOR',1,101,11)['options'][0]['is_correct']=='Y'


def test_add_option_denies_foreign_unshared_question(access):
    roles=SimpleNamespace(INSTRUCTOR='INSTRUCTOR',ADMIN='ADMIN')
    def require_role(role,allowed):
        if role not in allowed:raise PermissionDeniedError()
    f=method('quiz/services.py','add_option',{
        'Roles':roles,'require_role':require_role,
        'validate_positive_integer':lambda val,name:None,
        'validate_required':lambda val,name:None,
        'get_question':lambda q:{'question_id':q,'question_type':'MCQ_SINGLE'},
        'question_has_attempts':lambda q:False,
        'question_access_for_instructor':access,
        'PermissionDeniedError':PermissionDeniedError,
    },cls='QuizService')
    with pytest.raises(PermissionDeniedError):f(22,1,'wrong','Y',2,user_role='INSTRUCTOR',instructor_id=202)


def test_attempted_question_cannot_be_changed_even_by_author(access):
    roles=SimpleNamespace(INSTRUCTOR='INSTRUCTOR',ADMIN='ADMIN')
    def require_role(role,allowed):
        if role not in allowed:raise PermissionDeniedError()
    f=method('quiz/services.py','add_option',{
        'Roles':roles,'require_role':require_role,
        'validate_positive_integer':lambda val,name:None,
        'validate_required':lambda val,name:None,
        'get_question':lambda q:{'question_id':q,'question_type':'MCQ_SINGLE'},
        'question_has_attempts':lambda q:True,
        'question_access_for_instructor':access,
        'BusinessRuleError':BusinessRuleError,
    },cls='QuizService')
    with pytest.raises(BusinessRuleError):f(11,4,'wrong','Y',2,user_role='INSTRUCTOR',instructor_id=101)
    with pytest.raises(BusinessRuleError):f(99,4,'wrong','Y',2,user_role='ADMIN')
