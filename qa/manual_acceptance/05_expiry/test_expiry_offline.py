"""Offline checks for the disposable main-schema expiry verifier (no network or Oracle)."""
import ast
import inspect
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

import verify_main_expiry as testee

SRC=Path(testee.__file__).read_text(encoding='utf-8')


class ExpiryVerifierOffline(unittest.TestCase):
    def test_python_parses(self):
        ast.parse(SRC)

    def test_locks_to_local_test_api(self):
        self.assertEqual(testee.BASE_URL, 'http://127.0.0.1:8002')

    def test_pins_main_schema(self):
        self.assertEqual(testee.SCHEMA, 'EDUSPHERE_OWNER')

    def test_uses_exact_write_confirmation(self):
        self.assertEqual(testee.CONFIRMATION, 'MAIN EXPIRY TEST DATA ONLY')
        self.assertLess(SRC.index('input(\'Type \'+CONFIRMATION'),SRC.index('create_fixture(conn,admin'))

    def test_fixture_created_only_after_preflight(self):
        self.assertLess(SRC.index('conn=preflight(args.main_backend)'), SRC.index('create_fixture(conn,admin'))

    def test_duration_is_one_minute(self):
        self.assertIn("'duration_minutes':1", SRC)

    def test_only_readonly_direct_oracle_queries(self):
        self.assertIn("startswith('SELECT')", SRC)
        self.assertNotIn('cursor.execute("UPDATE', SRC)
        self.assertNotIn('cursor.execute("DELETE', SRC)
        self.assertNotIn('cursor.execute("INSERT', SRC)

    def test_uses_oracle_clock_for_expiry(self):
        self.assertIn('SYSTIMESTAMP',inspect.getsource(testee.oracle_state))
        self.assertIn('NUMTODSINTERVAL',inspect.getsource(testee.oracle_state))

    def test_expiry_wait_returns_when_expired(self):
        with patch.object(testee,'oracle_state',side_effect=['READY','READY','DURATION_EXPIRED']):
            self.assertTrue(testee.wait_for_expiry(None,1,max_wait=80,
                sleep=lambda seconds:None,monotonic=iter([0,1,2,3]).__next__))

    def test_expiry_wait_rejects_unexpected_state(self):
        with patch.object(testee,'oracle_state',return_value='ALREADY_SUBMITTED'):
            with self.assertRaises(testee.StopTest):
                testee.wait_for_expiry(None,1,max_wait=80,monotonic=iter([0,1]).__next__)

    def test_expiry_wait_times_out(self):
        with patch.object(testee,'oracle_state',return_value='READY'):
            self.assertFalse(testee.wait_for_expiry(None,1,max_wait=3,
                sleep=lambda seconds:None,monotonic=iter([0,1,4]).__next__))

    def test_success_rejected_status_family(self):
        for s in [400,403,409,422]:
            with patch.object(testee,'check') as checker:
                testee.test_rejected(s,'late edit')
                self.assertTrue(checker.call_args.args[0])

    def test_failure_if_http_200(self):
        with self.assertRaises(testee.StopTest):
            testee.test_rejected(200,'late edit')

    def test_checks_expired_draft_content_and_response_writes(self):
        self.assertIn('Expired attempt cannot retrieve question content', SRC)
        self.assertIn('Expired attempt cannot overwrite saved answer', SRC)
        self.assertIn('Expired attempt cannot directly append option', SRC)

    def test_checks_no_data_leaks_or_multiple_submissions(self):
        for phrase in ('Unreleased quiz result remains hidden','Unreleased answer review remains hidden',
            'Already submitted attempt cannot submit twice','No additional attempt created'):
            self.assertIn(phrase,SRC)

    def test_distinct_student_is_denied(self):
        self.assertIn('Different student cannot submit expired QA attempt',SRC)
        self.assertIn('Other student cannot access expired attempt result',SRC)

    def test_no_existing_data_cleanup_or_schema_migrations(self):
        self.assertNotIn('DROP TABLE',SRC)
        self.assertNotIn('TRUNCATE TABLE',SRC)
        self.assertNotIn('DELETE FROM',SRC)


if __name__=='__main__':
    unittest.main()
