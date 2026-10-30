"""Offline regression checks for safe quiz append without Oracle or Django.

Run from the Backend folder with:
python -m unittest discover -s quiz/tests -p 'test_append_questions_without_changing_answers.py'
"""
from pathlib import Path
import importlib.util
import sys
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]


def load_repository():
    database = types.ModuleType('database')
    database.__path__ = []
    query = types.ModuleType('database.query')
    query.fetch_one = lambda *_a, **_kw: None
    query.fetch_all = lambda *_a, **_kw: []
    query.execute = lambda *_a, **_kw: None
    schema = types.ModuleType('database.schema')
    schema.object_name = lambda x: x
    with patch.dict(sys.modules, {'database': database, 'database.query': query,
                                  'database.schema': schema}):
        spec = importlib.util.spec_from_file_location('append_repo_test', ROOT/'quiz/repository.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    return module


class SafeAppendQuestionsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo = load_repository()

    def test_no_attempts_allow_append(self):
        with patch.object(self.repo, 'fetch_one', return_value=None):
            self.assertFalse(self.repo.quiz_has_pending_attempts(42))

    def test_unfinished_attempt_blocks_append(self):
        with patch.object(self.repo, 'fetch_one', return_value={'blocked': 1}):
            self.assertTrue(self.repo.quiz_has_pending_attempts(42))

    def test_pending_query_requires_submitted_and_graded(self):
        seen = []
        with patch.object(self.repo, 'fetch_one', side_effect=lambda sql, params: seen.append((sql, params)) or None):
            self.repo.quiz_has_pending_attempts(42)
        self.assertIn('qa.SUBMITTED_AT IS NULL', seen[0][0])
        self.assertIn('NOT EXISTS', seen[0][0])
        self.assertIn('QUIZ_QUESTION_GRADE', seen[0][0])
        self.assertEqual(seen[0][1], (42,))

    def test_existing_answer_lock_remains(self):
        source = (ROOT/'quiz/services.py').read_text(encoding='utf-8')
        self.assertIn('question_has_attempts(int(question_id))', source)
        self.assertIn('Question answers are locked after an associated quiz has been attempted.', source)

    def test_regrade_uses_original_question_grade_snapshot(self):
        source = (ROOT/'quiz/auto_grader.py').read_text(encoding='utf-8')
        self.assertIn('qqg.QUESTION_ID=qq.QUESTION_ID', source)
        self.assertIn("qg.ATTEMPT_ID=qa.ATTEMPT_ID", source)
        self.assertIn('AND (NOT EXISTS (', source)

    def test_review_and_manual_review_use_original_question_set(self):
        repo_source = (ROOT/'quiz/repository.py').read_text(encoding='utf-8')
        self.assertIn('qqg.QUESTION_ID=qq.QUESTION_ID', repo_source)
        self.assertIn('qqg.GRADING_ID=qg.GRADING_ID AND qn.QUESTION_TYPE',
                      (ROOT/'quiz/auto_grader.py').read_text(encoding='utf-8'))

    def test_student_explanation_is_correct(self):
        frontend = (ROOT.parent/'Frontend/src/views/instructor/QuestionBankView.vue').read_text(encoding='utf-8')
        self.assertIn('You can append new questions after earlier attempts are submitted and graded.', frontend)
        self.assertIn('Existing answers remain locked', frontend)


if __name__ == '__main__':
    unittest.main()
