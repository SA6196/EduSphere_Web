"""Offline verifier-only safety and race-evaluation tests; no Oracle writes."""
import ast
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import verify_main_concurrency as mod

SRC=Path(mod.__file__).read_text(encoding='utf-8')

class ConcurrencyOfflineTests(unittest.TestCase):
    def test_python_parses(self):
        ast.parse(SRC)
    def test_main_schema_and_api_pinned(self):
        self.assertEqual(mod.SCHEMA,'EDUSPHERE_OWNER')
        self.assertEqual(mod.BASE_URL,'http://127.0.0.1:8002')
    def test_confirmation_before_login_or_fixture(self):
        run=SRC.split('def run(args):')[1].split('def main():')[0]
        self.assertLess(run.index('CONFIRMATION'),run.index("login('Administrator'"))
        self.assertLess(run.index('CONFIRMATION'),run.index('fresh_quiz('))
    def test_no_database_mutation_sql(self):
        tree=ast.parse(SRC)
        calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call)]
        self.assertFalse(any(isinstance(x.func,ast.Attribute) and x.func.attr in
                             {'executemany','commit','rollback'} for x in calls))
        self.assertIn("sql.lstrip().upper().startswith('SELECT')",SRC)
    def test_four_workers_bounded(self):
        self.assertEqual(mod.MAX_WORKERS,4)
        self.assertIn('ThreadPoolExecutor(max_workers=MAX_WORKERS)',SRC)
    def test_over_limit_rejected(self):
        with self.assertRaises(mod.StopTest):
            mod.parallel_cases([('a','/path','token',None,'POST')]*5)
    def test_parallel_start_and_completion(self):
        calls=[]
        def fake_http(path,token,payload,method):
            calls.append((path,method))
            return 400, {'detail':'already submitted'}
        cases=[('submit'+str(i),'/api/submit','secret',None,'POST') for i in range(4)]
        with patch.object(mod,'http',side_effect=fake_http):
            out=mod.parallel_cases(cases)
        self.assertEqual(len(out),4)
        self.assertEqual(len(calls),4)
    def test_one_submit_succeeds(self):
        results=[('submit0',(200,{'data':{'grading':{'status':'PROCESSED'}}})),
                 ('submit1',(400,{})),('submit2',(400,{})),('submit3',(400,{}))]
        with patch.object(mod,'check',side_effect=lambda b,label: self.assertTrue(b,label)):
            mod.validate_concurrent_http(results,1,'test')
    def test_two_submits_fail_gate(self):
        results=[('submit0',(200,{})),('submit1',(200,{})),('submit2',(400,{})),('submit3',(400,{}))]
        with self.assertRaises(mod.StopTest):
            mod.validate_concurrent_http(results,1,'test')
    def test_http_500_fails(self):
        results=[('submit0',(200,{})),('submit1',(500,{})),('submit2',(400,{})),('submit3',(400,{}))]
        with self.assertRaises(mod.StopTest):
            mod.validate_concurrent_http(results,1,'test')
    def test_leaked_marks_fail(self):
        results=[('submit0',(200,{'data':{'final_marks':10}})),
                 ('submit1',(400,{})),('submit2',(400,{})),('submit3',(400,{}))]
        with self.assertRaises(mod.StopTest):
            mod.validate_concurrent_http(results,1,'test')
    def test_autosave_success_does_not_count_as_submission(self):
        results=[('save-correct',(201,{'data':{'response_id':123}})),
                 ('save-wrong',(400,{})),('submit0',(200,{})),('submit1',(400,{}))]
        with patch.object(mod,'check',side_effect=lambda b,label: self.assertTrue(b,label)):
            mod.validate_concurrent_http(results,1,'test')
    def test_grading_snapshot_missing_row_fails(self):
        with patch.object(mod,'select_rows',return_value=[]):
            with self.assertRaises(mod.StopTest): mod.grade_snapshot(object(),3)
    def test_single_response_row_enforced(self):
        with patch.object(mod,'select_rows',return_value=[(1,2,'Y'),(1,3,'N')]):
            with self.assertRaises(mod.StopTest): mod.saved_answer(object(),3,4)
    def test_explicit_role_and_ownership_verification(self):
        self.assertIn("login('Other student','STUDENT')",SRC)
        self.assertIn('check_private(student,other,a2)',SRC)
    def test_no_cleanup_and_no_release_flag_api(self):
        self.assertNotIn('/visibility/',SRC)
        self.assertNotIn('DELETE FROM',SRC.upper())
        self.assertNotIn('DROP TABLE',SRC.upper())
    def test_attempts_graded_independently(self):
        self.assertIn('grade_snapshot(cn,a1,10)',SRC)
        self.assertIn('grade_snapshot(cn,a2,expected)',SRC)
        self.assertIn("'Highest-score STUDENT_MARK remains 10/10",SRC)

if __name__=='__main__': unittest.main()
