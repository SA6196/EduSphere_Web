"""Isolated tests for Course Drop. No Oracle, Django, or external packages required.

Executes the real drop_enrollment function and EnrollmentService.drop_student
from their Python AST definitions with mocked database/application boundaries.
"""
import ast
import contextlib
import pathlib
import unittest
from unittest.mock import Mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
REPO = ROOT / 'Backend/academics/repository.py'
SERVICE = ROOT / 'Backend/academics/services.py'

class NotFoundError(Exception): pass
class BusinessRuleError(Exception): pass
class PermissionDeniedError(Exception): pass


def extract(path, name):
    tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
    node = next(n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name == name)
    return compile(ast.Module(body=[node], type_ignores=[]), str(path), 'exec')

class DropRepoTests(unittest.TestCase):
    def setUp(self):
        self.enrollment = {'enrollment_id': 71, 'enrollment_status': 'ENROLLED', 'offering_status': 'OPEN'}
        self.activity = {'has_activity': 0}
        self.statements = []
        self.writes = []
        def fake_fetch(sql, params):
            self.statements.append((sql, params))
            if 'FOR UPDATE' in sql:
                return self.enrollment
            return self.activity
        def fake_execute(sql, params):
            self.writes.append((sql, params))
            return self.row_count
        self.row_count = 1
        env = {'fetch_one': fake_fetch, 'execute': fake_execute,
               'object_name': lambda n: 'EDUSPHERE_OWNER.'+n,
               'NotFoundError': NotFoundError, 'BusinessRuleError': BusinessRuleError}
        exec(extract(REPO,'drop_enrollment'),env)
        self.drop = env['drop_enrollment']

    def test_success_update_bound_to_student_and_id(self):
        r=self.drop(12,39)
        self.assertEqual(r['enrollment_status'],'DROPPED')
        self.assertEqual(r['enrollment_id'],71)
        self.assertEqual(len(self.writes),1)
        sql,params=self.writes[0]
        self.assertIn('ENROLLMENT_STATUS=\'DROPPED\'',sql)
        self.assertIn("ENROLLMENT_STATUS='ENROLLED'",sql)
        self.assertEqual(params,(71,12))
        self.assertNotIn('DELETE FROM',sql.upper())
        self.assertIn('FOR UPDATE OF e.ENROLLMENT_STATUS',self.statements[0][0])

    def test_no_enrollment(self):
        self.enrollment=None
        with self.assertRaises(NotFoundError): self.drop(12,39)
        self.assertEqual(self.writes,[])

    def test_already_dropped(self):
        self.enrollment['enrollment_status']='DROPPED'
        with self.assertRaises(BusinessRuleError): self.drop(12,39)
        self.assertEqual(self.writes,[])

    def test_completed_cannot_drop(self):
        self.enrollment['enrollment_status']='COMPLETED'
        with self.assertRaises(BusinessRuleError): self.drop(12,39)
        self.assertEqual(self.writes,[])

    def test_closed_offering(self):
        self.enrollment['offering_status']='CLOSED'
        with self.assertRaises(BusinessRuleError): self.drop(12,39)
        self.assertEqual(self.writes,[])

    def test_course_activity_rejection(self):
        self.activity['has_activity']=1
        with self.assertRaises(BusinessRuleError): self.drop(12,39)
        self.assertEqual(self.writes,[])

    def test_activity_query_covers_all_relations(self):
        self.drop(12,39)
        sql,params=self.statements[1]
        for table in ('ATTENDANCE','CLASS_SESSION','ASSIGNMENT_SUBMISSION','QUIZ_ATTEMPT','STUDENT_MARK','COURSE_GRADE'):
            self.assertIn(table,sql)
        self.assertEqual(params,(12,39,12,39,12,39,71,71))
        self.assertEqual(sql.count('EXISTS ('),5)

    def test_no_unexpected_update(self):
        self.row_count=0
        with self.assertRaises(BusinessRuleError): self.drop(12,39)
        self.assertEqual(len(self.writes),1)

    def test_database_function_never_commits_directly(self):
        self.drop(12,39)
        self.assertNotIn('COMMIT', '\n'.join(s for s,p in self.statements))

class DropServiceTests(unittest.TestCase):
    def setUp(self):
        self.events=[]
        self.result={'enrollment_id':71,'enrollment_status':'DROPPED'}
        self.drop=Mock(side_effect=lambda sid, oid:(self.events.append('drop'),self.result)[1])
        def log_activity(**kwargs):
            self.events.append('audit')
            if getattr(self, 'fail_audit', False): raise RuntimeError('audit failed')
            self.audit=kwargs
        @contextlib.contextmanager
        def transaction():
            self.events.append('begin')
            try:
                yield
                self.events.append('commit')
            except Exception:
                self.events.append('rollback')
                raise
        def require_role(role, roles):
            if role not in roles: raise PermissionDeniedError('Forbidden')
        def positive(number,name):
            if isinstance(number,bool) or not str(number).isdigit() or int(number)<1:
                raise BusinessRuleError('Invalid '+name)
        def required(value,name):
            if value is None: raise BusinessRuleError('Missing '+name)
        env={'staticmethod':staticmethod, 'require_role':require_role,
             'validate_positive_integer':positive, 'validate_required':required,
             'oracle_transaction':transaction, 'log_activity':log_activity, 'drop_enrollment':self.drop,
             'Roles':type('Roles',(),{'STUDENT':'STUDENT'}),
             'ActivityTypes':type('ActivityTypes',(),{'ENROLLMENT_DROPPED':'ENROLLMENT_DROPPED'}),
             'PermissionDeniedError':PermissionDeniedError}
        exec(extract(SERVICE,'EnrollmentService'),env)
        self.service=env['EnrollmentService']

    def test_drop_and_audit_atomic(self):
        r=self.service.drop_student(5,12,39,'STUDENT')
        self.assertEqual(r,self.result)
        self.assertEqual(self.events,['begin','drop','audit','commit'])
        self.drop.assert_called_once_with(12,39)
        self.assertEqual(self.audit['activity_type'],'ENROLLMENT_DROPPED')
        self.assertEqual(self.audit['user_id'],5)

    def test_audit_failure_rolls_back(self):
        self.fail_audit=True
        with self.assertRaises(RuntimeError): self.service.drop_student(5,12,39,'STUDENT')
        self.assertEqual(self.events,['begin','drop','audit','rollback'])

    def test_student_role_required(self):
        with self.assertRaises(PermissionDeniedError): self.service.drop_student(5,12,39,'INSTRUCTOR')
        self.drop.assert_not_called()

    def test_missing_student_profile(self):
        with self.assertRaises(PermissionDeniedError): self.service.drop_student(5,None,39,'STUDENT')
        self.drop.assert_not_called()

    def test_invalid_offering_id(self):
        with self.assertRaises(BusinessRuleError): self.service.drop_student(5,12,-1,'STUDENT')
        self.drop.assert_not_called()

    def test_repo_failure_rolls_back_and_no_audit(self):
        def reject(sid, oid):
            self.events.append('drop')
            raise BusinessRuleError('has academic activity')
        self.drop.side_effect=reject
        with self.assertRaises(BusinessRuleError): self.service.drop_student(5,12,39,'STUDENT')
        self.assertEqual(self.events,['begin','drop','rollback'])

class ApiWiringTests(unittest.TestCase):
    def test_backend_route_is_student_only_post(self):
        urls=(ROOT/'Backend/academics/urls.py').read_text()
        views=(ROOT/'Backend/academics/views.py').read_text()
        self.assertIn('enrollments/<int:offering_id>/drop/',urls)
        self.assertIn('class EnrollmentDropView(APIView):',views)
        segment=views.split('class EnrollmentDropView(APIView):',1)[1].split('class MyEnrollmentView',1)[0]
        self.assertIn('permission_classes = [IsStudent]',segment)
        self.assertIn('def post(self, request, offering_id):',segment)
        self.assertIn('request.user.student_id',segment)
        self.assertNotIn('request.data.get("student_id")',segment)

if __name__=='__main__': unittest.main()
