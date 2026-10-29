"""Offline tests for new controlled main-DB multiple-attempt verifier.
No Django/Oracle service required, and no real HTTP/SQL activity occurs.
"""
import ast
import inspect
from pathlib import Path
import unittest
from unittest.mock import patch

import verify_main_multiple_attempts as multi

SRC = Path(multi.__file__).read_text(encoding='utf-8')


class MultipleAttemptSafetyTests(unittest.TestCase):
    def test_script_python_parses(self):
        self.assertIsInstance(ast.parse(SRC), ast.Module)

    def test_endpoint_locked_localhost(self):
        self.assertIn('http://127.0.0.1:8002', multi.BASE_URL)
        self.assertIn("args.base_url.rstrip('/')!=BASE_URL", SRC)

    def test_requires_exact_confirmation(self):
        self.assertEqual(multi.CONFIRMATION,'MAIN TWO ATTEMPT TEST DATA ONLY')
        self.assertIn('input(f\'Type {CONFIRMATION}', SRC)

    def test_only_readonly_oracle_sql(self):
        tree=ast.parse(SRC)
        # Static invariant: Oracle queries in this script only use SELECT.
        # Data mutation occurs via the authenticated app API, not via cursor DML.
        calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='execute']
        self.assertEqual(len(calls),1)
        self.assertIn("sql.lstrip().upper().startswith('SELECT')",SRC)
        self.assertIn('cur.execute(sql, params)',SRC)
        self.assertNotIn('conn.commit(',SRC)
        self.assertNotIn('conn.rollback(',SRC)

    def test_best_mark_stays_ten_after_lower_attempt(self):
        def fake_sql(conn, query, params=()):
            if 'FROM EDUSPHERE_OWNER.QUIZ_ATTEMPT' in query:
                return [(70,1,'date'),(71,2,'date')]
            if 'FROM EDUSPHERE_OWNER.STUDENT_MARK' in query:
                return [(10.0,)]
            raise AssertionError(query)
        with patch.object(multi,'sql_rows',side_effect=fake_sql):
            rows=multi.verify_best_mark(None,104,22,10,2)
        self.assertEqual(len(rows),2)

    def test_best_mark_detects_last_attempt_overwrite(self):
        def fake_sql(conn,query,params=()):
            if 'FROM EDUSPHERE_OWNER.QUIZ_ATTEMPT' in query: return [(70,1,'date'),(71,2,'date')]
            if 'FROM EDUSPHERE_OWNER.STUDENT_MARK' in query: return [(0.0,)]
            raise AssertionError(query)
        with patch.object(multi,'sql_rows',side_effect=fake_sql):
            with self.assertRaises(multi.StopTest):
                multi.verify_best_mark(None,104,22,10,2)

    def test_grading_checks_both_levels(self):
        def fake_sql(conn,query,params=()):
            if 'FROM EDUSPHERE_OWNER.QUIZ_GRADING' in query: return [(10,10,10,'AUTO_GRADED',1234)]
            if 'FROM EDUSPHERE_OWNER.QUIZ_QUESTION_GRADE' in query: return [(10,10)]
            raise AssertionError(query)
        with patch.object(multi,'sql_rows',side_effect=fake_sql):
            multi.verify_grading(None,104,166,10)

    def test_grading_mismatch_fails(self):
        def fake_sql(conn,query,params=()):
            if 'FROM EDUSPHERE_OWNER.QUIZ_GRADING' in query: return [(0,10,10,'AUTO_GRADED',1234)]
            if 'FROM EDUSPHERE_OWNER.QUIZ_QUESTION_GRADE' in query: return [(10,10)]
            raise AssertionError(query)
        with patch.object(multi,'sql_rows',side_effect=fake_sql):
            with self.assertRaises(multi.StopTest):
                multi.verify_grading(None,104,166,10)

    def test_main_test_never_opens_marks(self):
        self.assertNotIn("'allow_mark_view':'Y'",SRC)
        self.assertNotIn("'allow_answer_review':'Y'",SRC)
        self.assertIn('while N/N',SRC)

    def test_test_attempt_order_intentionally_high_then_low(self):
        tree=ast.parse(inspect.getsource(multi.run))
        calls=[]
        for n in ast.walk(tree):
            if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='submit_attempt':
                kw={x.arg:x.value.value for x in n.keywords if isinstance(x.value,ast.Constant)}
                calls.append(kw.get('correct'))
        self.assertEqual(calls,[True,False])


if __name__=='__main__':
    unittest.main(verbosity=2)
