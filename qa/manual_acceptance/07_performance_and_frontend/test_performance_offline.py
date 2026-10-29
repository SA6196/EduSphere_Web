"""Offline verification of the bounded, no-DML performance acceptance harness."""
import ast
from pathlib import Path
import unittest
from unittest.mock import patch
from urllib.error import URLError
import verify_main_performance as m

HERE=Path(__file__).resolve().parent

class PerformanceVerifierOffline(unittest.TestCase):
    def test_python_parses(self):
        ast.parse((HERE/'verify_main_performance.py').read_text(encoding='utf8'))
    def test_fixed_local_ports(self):
        self.assertEqual(m.CANDIDATE,'http://127.0.0.1:8002')
        self.assertEqual(m.BASELINE,'http://127.0.0.1:8000')
    def test_no_arbitrary_http_host(self):
        with self.assertRaises(ValueError):
            m.request_bytes('https://external.example','/api/health/')
    def test_get_only_except_login(self):
        with self.assertRaises(ValueError):
            m.request_bytes(m.CANDIDATE, '/api/quizzes/create/', method='POST')
    def test_no_put_patch_delete(self):
        for method in ('PUT','PATCH','DELETE'):
            with self.subTest(method=method),self.assertRaises(ValueError):
                m.request_bytes(m.CANDIDATE, '/api/db-health/', method=method)
    def test_no_arbitrary_path(self):
        with self.assertRaises(ValueError):
            m.request_bytes(m.CANDIDATE,'/admin/')
    def test_percentile_nearest_rank(self):
        self.assertEqual(m.percentile(list(range(1,21)),95),19)
        self.assertEqual(m.percentile(list(range(1,21)),50),10)
    def test_empty_percentile_refused(self):
        with self.assertRaises(ValueError):m.percentile([],95)
    def test_summary_success(self):
        out=m.summarize([m.Sample(200,10,5),m.Sample(200,20,5)],0.1)
        self.assertEqual(out['failed'],0)
        self.assertEqual(out['p95_ms'],20)
    def test_summary_server_error(self):
        out=m.summarize([m.Sample(200,10,5),m.Sample(500,20,0,'http_error')],0.1)
        self.assertEqual(out['failed'],1)
    def test_concurrency_four(self):
        self.assertEqual(m.MAX_WORKERS,4)
    def test_samples_bound(self):
        args=type('A',(),dict(samples=60,parallel=12,warmup=2,report='x.json'))()
        with self.assertRaises(ValueError):m.verify_settings(args)
    def test_parallel_divisible_by_four(self):
        args=type('A',(),dict(samples=12,parallel=7,warmup=2,report='x.json'))()
        with self.assertRaises(ValueError):m.verify_settings(args)
    def test_valid_arguments(self):
        args=type('A',(),dict(samples=12,parallel=12,warmup=2,report='x.json'))()
        m.verify_settings(args)
    def test_get_error_detected(self):
        with patch.object(m,'request_bytes',side_effect=[(m.Sample(200,10,1),b'{}'),(m.Sample(500,20,0,'http_error'),b'')]):
            with self.assertRaises(RuntimeError):m.run_endpoint(m.CANDIDATE,'x','/api/db-health/',None,1,False,1)
    def test_readonly_oracle_session_query(self):
        src=(HERE/'verify_main_performance.py').read_text(encoding='utf8').upper()
        self.assertIn('SELECT COUNT(*) FROM V$SESSION',src)
        self.assertNotIn('INSERT INTO',src)
        self.assertNotIn('UPDATE EDUSPHERE_OWNER.',src)
        self.assertNotIn('DELETE FROM EDUSPHERE_OWNER.',src)
    def test_secret_names_not_serialized(self):
        source=(HERE/'verify_main_performance.py').read_text(encoding='utf8')
        self.assertIn('report_file.write_text(json.dumps(report, indent=2)',source)
        self.assertNotIn("report['password']",source)
        self.assertNotIn("report['access']",source)
    def test_four_worker_bounded_execution(self):
        calls=[]
        def fake_request(base,path,token):
            calls.append((base,path))
            return m.Sample(200,1.0,5),b'{}'
        with patch.object(m,'request_bytes',side_effect=fake_request):
            out=m.run_endpoint(m.CANDIDATE,'health','/api/db-health/',None,8,True,1)
        self.assertEqual(out['requests'],8)
        self.assertEqual(out['failed'],0)
        self.assertEqual(len(calls),9)
    def test_all_measured_paths_are_get_endpoints(self):
        self.assertEqual(len(m.PATHS),6)
        for path,role in m.PATHS.values():
            self.assertTrue(path.startswith('/api/'))
            self.assertNotIn('/submit/',path)
            self.assertNotIn('/create/',path)
            self.assertNotIn('/record/',path)
    def test_windows_frontend_script_lock(self):
        source=(HERE/'Verify-FrontendBuild.ps1').read_text(encoding='utf8')
        self.assertIn('http://127.0.0.1:8002/api',source)
        self.assertIn('npm run build',source)
        self.assertIn('request_coalescing.test.mjs',source)

if __name__=='__main__':unittest.main(verbosity=2)
