"""Network-free static/AST guardrails for the main-schema release matrix verifier."""
from pathlib import Path
import ast
import unittest

ROOT=Path(__file__).resolve().parent
FILE=ROOT/'verify_main_visibility_matrix.py'

class TestVisibilityMatrixStatic(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=FILE.read_text(encoding='utf-8')
        cls.tree=ast.parse(cls.source)
    def test_confirmation_required(self):
        self.assertIn('MAIN VISIBILITY MATRIX TEST',self.source)
    def test_limited_to_one_known_fixture(self):
        self.assertIn('E7808E9C43',self.source)
        self.assertIn('QUIZ_ID = 104',self.source)
        self.assertIn('ATTEMPT_ID = 166',self.source)
        self.assertIn("'API Main Lock '+tag",self.source)
    def test_all_four_cases_and_denials(self):
        self.assertIn("[('N','N'),('N','Y'),('Y','N'),('Y','Y')]",self.source)
        self.assertIn("check(status==403,'Student cannot change visibility via forced API PATCH')",self.source)
        self.assertIn("check(status==401,'Unauthenticated visibility update denied')",self.source)
    def test_restoration_in_finally(self):
        self.assertIn('RESTORING QA quiz visibility',self.source)
        self.assertIn('patch_visibility(args.quiz_id,instructor,*original)',self.source)
        self.assertIn('verify_patched_flags(conn,args.quiz_id,*original)',self.source)
        fin_nodes=[x for x in ast.walk(self.tree) if isinstance(x,ast.Try) and x.finalbody]
        self.assertTrue(any('patch_visibility(args.quiz_id, instructor, *original)' in ast.unparse(n)
                            for n in fin_nodes))
    def test_no_database_writes(self):
        self.assertNotIn('INSERT INTO',self.source)
        self.assertNotIn('UPDATE EDUSPHERE_OWNER.',self.source)
        self.assertNotIn('DELETE FROM',self.source)
        self.assertNotIn('DROP TABLE',self.source)

if __name__=='__main__':unittest.main()
