"""Offline safety and logic checks for main Oracle manual grading verifier.

No live Oracle connection or HTTP service is contacted.
"""
import ast
from pathlib import Path
import unittest
from unittest.mock import patch

import verify_main_manual_grading as manual

SOURCE = Path(manual.__file__).read_text(encoding='utf-8')


class DummyCursor:
    def __init__(self, rows):
        self.rows=rows; self.sql=None; self.params=None; self.closed=False
    def execute(self,sql,params):
        self.sql=sql; self.params=params
    def fetchall(self):
        return self.rows
    def close(self):
        self.closed=True


class DummyConnection:
    def __init__(self, rows):
        self.cur=DummyCursor(rows)
    def cursor(self):
        return self.cur


class TestManualGradingVerifier(unittest.TestCase):
    def test_valid_python_syntax(self):
        self.assertIsInstance(ast.parse(SOURCE),ast.Module)

    def test_explicit_confirmation_before_writes(self):
        self.assertEqual(manual.CONFIRMATION,'MAIN MANUAL REVIEW TEST DATA ONLY')
        self.assertIn('Type {CONFIRMATION}',SOURCE)
        self.assertLess(SOURCE.index('Type {CONFIRMATION}'), SOURCE.index("admin,_=login"))

    def test_schema_unchanged_and_url_locked(self):
        self.assertEqual(manual.SCHEMA,'EDUSPHERE_OWNER')
        self.assertEqual(manual.BASE_URL,'http://127.0.0.1:8002')
        self.assertIn('args.base_url.rstrip(\'/\')!=BASE_URL',SOURCE)

    def test_oracle_queries_are_readonly(self):
        tree=ast.parse(SOURCE)
        calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and
               isinstance(n.func,ast.Attribute) and n.func.attr=='execute']
        self.assertEqual(len(calls),1)
        self.assertIn("sql.lstrip().upper().startswith('SELECT')",SOURCE)
        self.assertNotIn('conn.commit(',SOURCE)
        self.assertNotIn('conn.rollback(',SOURCE)

    def test_blocks_direct_dml(self):
        with self.assertRaises(manual.StopTest):
            manual.sql_rows(DummyConnection([]),'DELETE FROM EDUSPHERE_OWNER.QUIZ')

    def test_select_reads_rows_and_closes_cursor(self):
        conn=DummyConnection([(101,9)])
        result=manual.sql_rows(conn,'SELECT * FROM QA WHERE ID=?',(1,))
        self.assertEqual(result,[(101,9)])
        self.assertTrue(conn.cur.closed)
        self.assertEqual(conn.cur.params,(1,))

    def test_float_comparison_detects_mismatch(self):
        self.assertTrue(manual.roughly('9.00',9))
        self.assertFalse(manual.roughly('4',9))
        self.assertFalse(manual.roughly(None,9))

    def test_grading_snapshot_reads_question_rows(self):
        def sql(conn,query,params=()):
            if 'QUIZ_GRADING' in query:
                return [(77,4,4,10,'AUTO_GRADED',None,None,None,None)]
            if 'QUIZ_QUESTION_GRADE' in query:
                return [(202,4,4,'Y','auto'),(203,0,6,'N','manual')]
            raise AssertionError(query)
        with patch.object(manual,'sql_rows',side_effect=sql):
            grading,grades=manual.grading_snapshot(None,188)
        self.assertEqual(grading[4],'AUTO_GRADED')
        self.assertEqual(len(grades),2)

    def test_missing_grading_row_fails(self):
        with patch.object(manual,'sql_rows',return_value=[]):
            with self.assertRaises(manual.StopTest):
                manual.grading_snapshot(None,188)

    def test_hidden_result_and_review_required(self):
        with patch.object(manual,'http',side_effect=[(403,{}),(403,{})]) as h:
            manual.expect_hidden('student-access',188)
            self.assertEqual(h.call_count,2)

    def test_hidden_results_leak_is_fatal(self):
        with patch.object(manual,'http',side_effect=[(200,{'marks_obtained':9}),(403,{})]):
            with self.assertRaises(manual.StopTest):
                manual.expect_hidden('student-access',188)

    def test_rollback_test_needs_independent_opt_in(self):
        self.assertIn('if args.test_db_rollback:',SOURCE)
        self.assertEqual(manual.ROLLBACK_CONFIRMATION,'TEST INTENTIONAL ORACLE ROLLBACK')
        self.assertIn('args.test_db_rollback',SOURCE)
        self.assertIn("'notes':'X'*1300",SOURCE)

    def test_intentional_database_failure_checks_rollback(self):
        self.assertIn('ATOMIC ROLLBACK: neither question grade nor grading header changed',SOURCE)
        self.assertIn('ATOMIC ROLLBACK: no STUDENT_MARK was written',SOURCE)

    def test_success_requires_review_and_release_checks(self):
        self.assertIn("'REVIEWED'",SOURCE)
        self.assertIn("'RELEASED'",SOURCE)
        self.assertIn('Question grading persists 4/4 and 5/6',SOURCE)
        self.assertIn('STUDENT_MARK synchronized as 9/10',SOURCE)

    def test_all_direct_credentials_hidden_from_verifier(self):
        self.assertNotIn('password=',SOURCE)
        self.assertNotIn('ODBC_PASSWORD',SOURCE)
        self.assertNotIn('getpass',SOURCE)


if __name__=='__main__':
    unittest.main(verbosity=2)
