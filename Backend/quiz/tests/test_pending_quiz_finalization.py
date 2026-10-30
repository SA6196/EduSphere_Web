"""Oracle-free tests of quiz-pending ownership and recovery metadata.

Run: python -m unittest discover -s quiz/tests -p 'test_pending_quiz_finalization.py'
"""
import ast
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]


def repository_module():
    db = types.ModuleType('database'); db.__path__ = []
    query = types.ModuleType('database.query')
    query.fetch_one = lambda *a, **kw: None
    query.fetch_all = lambda *a, **kw: []
    query.execute = lambda *a, **kw: None
    schema = types.ModuleType('database.schema')
    schema.object_name = lambda name: 'EDUSPHERE_OWNER.' + name
    with patch.dict(sys.modules, {'database': db, 'database.query': query, 'database.schema': schema}):
        spec = importlib.util.spec_from_file_location('test_pending_repository', ROOT/'quiz/repository.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module


def pending_method(namespace):
    """Compile just the real service method, avoiding Django/Oracle imports."""
    parsed = ast.parse((ROOT/'quiz/services.py').read_text(encoding='utf-8'))
    cls = next(node for node in parsed.body if isinstance(node, ast.ClassDef) and node.name == 'QuizService')
    method = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == 'pending_attempt')
    method.decorator_list = []
    module = ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[]))
    exec(compile(module, str(ROOT/'quiz/services.py'), 'exec'), namespace)
    return namespace['pending_attempt']


class PendingQuizTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo = repository_module()

    def test_query_is_scoped_to_student_and_quiz(self):
        calls = []
        def fake(sql, args):
            calls.append((sql, args)); return None
        with patch.object(self.repo, 'fetch_one', side_effect=fake):
            self.repo.get_pending_attempt_for_student_quiz(5, 84)
        sql, args = calls[0]
        self.assertIn('STUDENT_ID=? AND QUIZ_ID=? AND SUBMITTED_AT IS NULL', sql)
        self.assertNotIn('DURATION_MINUTES', sql)
        self.assertNotIn('CLOSE_AT', sql)
        self.assertEqual(args, (5, 84))
        self.assertNotIn('OPTION', sql)

    def test_no_existing_attempt_gives_no_id(self):
        namespace = self.namespace(state=None, pending=None)
        self.assertEqual(pending_method(namespace)(5, 'STUDENT', 84), {'attempt_id': None, 'submission_state': None})

    def test_expired_attempt_can_be_identified_without_questions(self):
        namespace = self.namespace(state='DURATION_EXPIRED')
        self.assertEqual(pending_method(namespace)(5, 'STUDENT', 84), {
            'attempt_id': 118, 'submission_state': 'DURATION_EXPIRED'
        })

    def test_closed_attempt_can_be_identified_without_questions(self):
        namespace = self.namespace(state='QUIZ_CLOSED')
        self.assertEqual(pending_method(namespace)(5, 'STUDENT', 84), {
            'attempt_id': 118, 'submission_state': 'QUIZ_CLOSED'
        })

    def test_ready_attempt_can_be_identified(self):
        namespace = self.namespace(state='READY')
        self.assertEqual(pending_method(namespace)(5, 'STUDENT', 84)['attempt_id'], 118)

    def test_submitted_attempt_does_not_appear_pending(self):
        namespace = self.namespace(state='ALREADY_SUBMITTED')
        self.assertIsNone(pending_method(namespace)(5, 'STUDENT', 84)['attempt_id'])

    def test_missing_quiz_rejected(self):
        namespace = self.namespace(quiz_exists=False)
        with self.assertRaisesRegex(LookupError, 'Quiz not found'):
            pending_method(namespace)(5, 'STUDENT', 84)

    def test_non_student_denied(self):
        namespace = self.namespace()
        with self.assertRaises(PermissionError):
            pending_method(namespace)(5, 'INSTRUCTOR', 84)

    @staticmethod
    def namespace(state='DURATION_EXPIRED', pending=None, quiz_exists=True):
        if pending is None and state is not None:
            pending = {'attempt_id': 118}
        def require_role(role, allowed):
            if role not in allowed: raise PermissionError('Student required')
        def validate_positive_integer(value, name):
            if not isinstance(value, int) or value < 1: raise ValueError(name)
        return {
            'require_role': require_role, 'validate_positive_integer': validate_positive_integer,
            'Roles': types.SimpleNamespace(STUDENT='STUDENT'),
            'get_quiz': lambda id: {'quiz_id': id} if quiz_exists else None,
            'NotFoundError': LookupError,
            'get_pending_attempt_for_student_quiz': lambda student, quiz: pending,
            'get_attempt_submission_state': lambda id: {'submission_state': state},
        }

    def test_student_only_endpoint_and_existing_submit_route(self):
        views = (ROOT/'quiz/views.py').read_text(encoding='utf8')
        urls = (ROOT/'quiz/urls.py').read_text(encoding='utf8')
        self.assertIn('class QuizPendingAttemptView(APIView):', views)
        self.assertIn('permission_classes = [IsStudent]', views.split('class QuizPendingAttemptView(APIView):')[1].split('class QuizAttemptView')[0])
        self.assertIn('"<int:quiz_id>/pending/"', urls)
        self.assertIn('"attempt/<int:attempt_id>/submit/"', urls)


if __name__ == '__main__':
    unittest.main()
