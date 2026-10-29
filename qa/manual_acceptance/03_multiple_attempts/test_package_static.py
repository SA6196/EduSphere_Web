"""Static safety checks: no DB/API writes. Run: python -m unittest test_package_static.py"""
import ast
import pathlib
import unittest

BASE=pathlib.Path(__file__).resolve().parent

class TestMainVerifierPackage(unittest.TestCase):
    def test_all_scripts_parse(self):
        for name in ('verify_main_connection.py','verify_main_question_bank_reads.py','verify_main_api_quiz_lifecycle.py'):
            with self.subTest(name=name):
                ast.parse((BASE/name).read_text(encoding='utf8'))

    def test_main_preflight_is_strict(self):
        text=(BASE/'verify_main_connection.py').read_text(encoding='utf8')
        for token in ('EDUSPHERE_APP','EDUSPHERE_OWNER','XEPDB1','COUNT(*)','37','expected_tables','visible_tables','ODBC_CONNECTION_STRING','require_api'):
            self.assertIn(token,text)
        self.assertNotIn('EDUSPHERE_STAGE_APP',text)

    def test_live_scripts_only_target_local_port_8002(self):
        for name in ('verify_main_question_bank_reads.py','verify_main_api_quiz_lifecycle.py'):
            s=(BASE/name).read_text(encoding='utf8')
            self.assertIn('http://127.0.0.1:8002',s)
            self.assertNotIn('http://127.0.0.1:8000',s)
            self.assertNotIn('http://127.0.0.1:8001',s)

    def test_main_write_requires_confirmation_and_uses_post_submit(self):
        s=(BASE/'verify_main_api_quiz_lifecycle.py').read_text(encoding='utf8')
        self.assertIn('MAIN EDUSPHERE TEST DATA ONLY',s)
        self.assertGreaterEqual(s.count("method='POST'"),2)
        self.assertIn("method='PATCH'",s)
        self.assertIn('QUIZ_QUESTION_GRADE',s)
        self.assertIn('STUDENT_MARK',s)
        self.assertIn("'HIDDEN'",s)
        self.assertIn("'N','allow_answer_review':'N'",s)
        for kw in ('DROP TABLE','TRUNCATE TABLE','DELETE FROM','ALTER TABLE','CREATE TABLE'):
            self.assertNotIn(kw,s.upper())

if __name__=='__main__':unittest.main()
