"""Offline helper tests for the staging-only API acceptance runner."""
import unittest
from unittest.mock import patch
import verify_staging_api_quiz_lifecycle as x

class FakeCursor:
    def __init__(self,rows): self.rows=rows; self.sql=''; self.params=()
    def execute(self,sql,params): self.sql=sql;self.params=params
    def fetchall(self):return self.rows
class FakeConnection:
    def __init__(self,rows):self.cur=FakeCursor(rows)
    def cursor(self):return self.cur

class VerifierUnitTests(unittest.TestCase):
    def test_unambiguous_id_lookup(self):
        cn=FakeConnection([(17,)])
        self.assertEqual(x.sql_find_id(cn,'COURSE','COURSE_ID','COURSE_CODE','QA123'),17)
        self.assertIn('EDUSPHERE_STAGE_OWNER.COURSE',cn.cur.sql)
        self.assertEqual(cn.cur.params,('QA123',))
    def test_missing_id_is_not_guessed(self):
        with self.assertRaises(x.StopTest):x.sql_find_id(FakeConnection([]),'SEMESTER','SEMESTER_ID','ACADEMIC_YEAR','QA0')
    def test_duplicate_id_not_guessed(self):
        with self.assertRaises(x.StopTest):x.sql_find_id(FakeConnection([(1,),(2,)]),'SEMESTER','SEMESTER_ID','ACADEMIC_YEAR','QA0')
    def test_resolve_account_by_name(self):
        self.assertEqual(x.item_by_username([{'username':'STAGE_I1','instructor_id':4}], 'stage_i1')['instructor_id'],4)
    def test_bad_account_fails_closed(self):
        with self.assertRaises(x.StopTest):x.item_by_username([], 'STAGE_I1')
    def test_unexpected_http_denied(self):
        with patch.object(x,'http',return_value=(403,{'message':'denied'})):
            with self.assertRaises(x.StopTest):x.expected_http('/api/test/','token',{200})
    def test_expected_http_unwraps_data(self):
        with patch.object(x,'http',return_value=(200,{'success':True,'data':{'question_id':99}})):
            self.assertEqual(x.expected_http('/api/test/','token',{200}),{'question_id':99})
    def test_app_reported_failure_does_not_pass(self):
        with patch.object(x,'http',return_value=(200,{'success':False,'message':'bad'})):
            with self.assertRaises(x.StopTest):x.expected_http('/api/test/','token',{200})


class AttemptMethodRegressionTests(unittest.TestCase):
    def test_start_and_submit_use_post_without_request_body(self):
        methods=[]
        def fake_expected(path, token, expected, payload=None, method=None):
            methods.append((path,method))
            if path.endswith('/attempt/'):
                return {'attempt_id':77}
            if path.endswith('/content/'):
                return {'questions':[{'question_id':3,'options':[
                    {'option_id':100,'option_text':'Correct-10E51AF44E'},
                    {'option_id':101,'option_text':'Incorrect-10E51AF44E'}]}]}
            if path.endswith('/grading/'):
                return [{'attempt_id':77}]
            return {'message':'ok'}
        def fake_http(path, token, data=None, method=None):
            return (403,{}) if path.endswith('/grading/') else (400,{})
        detail={'question':{'question_id':3},'options':[{'option_id':100},{'option_id':101}]}
        with patch.object(x,'expected_http',side_effect=fake_expected), \
             patch.object(x,'http',side_effect=fake_http), \
             patch.object(x,'assure_unchanged'):
            result=x.exercise_attempt_lock(1,3,'10E51AF44E','I1','I2','ADMIN','STUDENT',detail,1,1,1)
        self.assertEqual(result,0)
        self.assertIn(('/api/quizzes/1/attempt/','POST'),methods)
        self.assertIn(('/api/quizzes/attempt/77/submit/','POST'),methods)
    def test_resume_rejects_invalid_tag_without_query(self):
        with self.assertRaises(x.StopTest):
            x.resolve_staging_fixture(object(),'QA123','STAGE_STUDENT')
    def test_resume_aborts_if_attempt_already_created(self):
        class FakeStageCursor:
            def execute(self,sql, params):
                self.sql=sql
                return self
            def fetchall(self):
                return [(1,1,1,1,3)]
            def fetchone(self):
                return (1,)
        class FakeStageConnection:
            def cursor(self): return FakeStageCursor()
        with self.assertRaisesRegex(x.StopTest,'already has an attempt'):
            x.resolve_staging_fixture(FakeStageConnection(),'10E51AF44E','STAGE_STUDENT')

if __name__=="__main__":
    unittest.main(verbosity=2)
