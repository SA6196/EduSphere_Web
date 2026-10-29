"""Bounded read-only HTTP performance benchmark for EduSphere main Oracle.

Never creates quizzes, changes flags, or issues DML. The only POST is a single
user-authorized login per target (which may create the normal authentication audit).
The report intentionally contains no account names, credentials, tokens or response bodies.
"""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, asdict
from getpass import getpass
import json
import math
import os
from pathlib import Path
import statistics
from threading import Barrier
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from verify_main_connection import preflight

CANDIDATE = 'http://127.0.0.1:8002'
BASELINE = 'http://127.0.0.1:8000'
MAX_WORKERS = 4
TIMEOUT = 20
MAX_BODY_BYTES = 3_000_000
PATHS = {
    'db_health': ('/api/db-health/', None),
    'student_identity': ('/api/auth/me/', 'student'),
    'student_attempt_history': ('/api/quizzes/attempts/my/', 'student'),
    'student_marks': ('/api/marks/my/', 'student'),
    'student_dashboard': ('/api/student/dashboard/', 'student'),
    'instructor_question_bank': ('/api/quizzes/questions/', 'instructor'),
}

@dataclass
class Sample:
    code: int
    milliseconds: float
    size_bytes: int
    error: str = ''


def percentile(values, percentile_number):
    """Nearest-rank percentile, suitable for small bounded acceptance samples."""
    if not values:
        raise ValueError('No samples for percentile')
    ordered = sorted(values)
    return ordered[max(0, math.ceil(len(ordered) * percentile_number / 100) - 1)]


def summarize(samples, wall_s):
    vals = [s.milliseconds for s in samples]
    failures = sum(s.code != 200 or bool(s.error) for s in samples)
    return {
        'requests': len(samples), 'passed_200': len(samples) - failures,
        'failed': failures, 'p50_ms': round(percentile(vals, 50), 2),
        'p95_ms': round(percentile(vals, 95), 2),
        'p99_ms': round(percentile(vals, 99), 2),
        'max_ms': round(max(vals), 2),
        'mean_ms': round(statistics.mean(vals), 2),
        'throughput_requests_per_sec': round(len(vals) / wall_s, 2) if wall_s else 0,
        'http_status_counts': {str(code): sum(s.code == code for s in samples) for code in sorted({s.code for s in samples})},
        'transport_errors': sorted({s.error for s in samples if s.error}),
    }


def request_bytes(base, path, token=None, method='GET', payload=None):
    if base not in (CANDIDATE, BASELINE):
        raise ValueError('Only local fixed EduSphere API ports are permitted')
    if not path.startswith('/api/'):
        raise ValueError('Only fixed /api paths are permitted')
    if method not in ('GET', 'POST'):
        raise ValueError('Unsupported method')
    if method == 'POST' and path != '/api/auth/login/':
        raise ValueError('POST permitted only for initial login')
    data = json.dumps(payload).encode('utf-8') if payload is not None else None
    headers = {'Accept': 'application/json'}
    if data is not None:
        headers['Content-Type'] = 'application/json'
    if token:
        headers['Authorization'] = 'Bearer ' + token
    req = Request(base + path, data=data, method=method, headers=headers)
    started = time.perf_counter()
    try:
        with urlopen(req, timeout=TIMEOUT) as r:
            # The +1 detects unexpectedly large responses without retaining data.
            body = r.read(MAX_BODY_BYTES + 1)
            elapsed = (time.perf_counter() - started) * 1000
            if len(body) > MAX_BODY_BYTES:
                return Sample(int(r.status), elapsed, len(body), 'response_over_size_limit'), b''
            return Sample(int(r.status), elapsed, len(body)), body
    except HTTPError as e:
        elapsed = (time.perf_counter() - started) * 1000
        e.close()
        return Sample(int(e.code), elapsed, 0, 'http_error'), b''
    except (URLError, OSError, TimeoutError) as e:
        elapsed = (time.perf_counter() - started) * 1000
        return Sample(0, elapsed, 0, type(e).__name__), b''


def authenticate(base, role):
    print(f'Authenticate the {role} account on local port {base.rsplit(":",1)[-1]}.')
    username = input('Username: ').strip()
    password = getpass('Password (hidden): ')
    if not username or not password:
        raise RuntimeError('Missing login credentials')
    sample, body = request_bytes(base, '/api/auth/login/', method='POST',payload={
        'username': username, 'password': password})
    password = None  # never save, print or serialize it
    if sample.code != 200 or sample.error:
        raise RuntimeError(f'{role} login rejected (HTTP {sample.code}); benchmark stopped')
    obj = json.loads(body)
    if obj.get('user', {}).get('role') != role.upper() or not obj.get('access'):
        raise RuntimeError(f'{role} login did not return the expected role/token')
    print(f'  {role}: role verified; credentials omitted from all reports')
    return obj['access']


def check_server(base, candidate=False):
    sample, body = request_bytes(base, '/api/db-health/')
    if sample.code != 200 or sample.error:
        raise RuntimeError(f'Server on {base} is unavailable/unhealthy (HTTP {sample.code})')
    obj = json.loads(body)
    if obj.get('schema') != 'EDUSPHERE_OWNER' or obj.get('status') != 'ok':
        raise RuntimeError(f'Server on {base} is not a healthy EDUSPHERE_OWNER API')
    if candidate and (obj.get('expected_tables') != 37 or obj.get('visible_tables') != 37):
        raise RuntimeError('Candidate must see all 37 tables')
    return {'schema': obj.get('schema'), 'expected_tables': obj.get('expected_tables'), 'visible_tables': obj.get('visible_tables')}


def session_probe_from_env(backend):
    """Optional read-only V$SESSION access. Never grants new privileges."""
    from dotenv import dotenv_values
    import pyodbc
    cfg = dotenv_values(Path(backend) / '.env')
    try:
        cn = pyodbc.connect('DSN={};UID={};PWD={}'.format(cfg['ODBC_DSN'],cfg['ODBC_USER'],cfg['ODBC_PASSWORD']),timeout=8,autocommit=False)
    except Exception:
        return None, 'Oracle session probe connection unavailable; HTTP tests may still run'
    try:
        cursor = cn.cursor()
        try:
            cursor.execute('SELECT COUNT(*) FROM V$SESSION WHERE USERNAME = ?', ('EDUSPHERE_APP',))
            cursor.fetchone()
        finally:
            cursor.close()
        return cn, None
    except Exception:
        cn.close()
        return None, 'V$SESSION access unavailable to EDUSPHERE_APP (normal for least-privilege users); use optional DBA worksheet'


def session_count(cn):
    if cn is None:
        return None
    cur = cn.cursor()
    try:
        cur.execute('SELECT COUNT(*) FROM V$SESSION WHERE USERNAME = ?', ('EDUSPHERE_APP',))
        return int(cur.fetchone()[0])
    finally:
        cur.close()


def run_endpoint(base, label, path, token, samples, parallel, warmup):
    for _ in range(warmup):
        got, _ = request_bytes(base, path, token)
        if got.code != 200 or got.error:
            raise RuntimeError(f'Warmup for {label} failed; HTTP {got.code}, {got.error}')
    if not parallel:
        t0 = time.perf_counter()
        records = [request_bytes(base, path, token)[0] for _ in range(samples)]
        duration = time.perf_counter() - t0
    else:
        if samples % MAX_WORKERS:
            raise ValueError('Parallel sample count must be divisible by four')
        records = []
        t0 = time.perf_counter()
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            for _ in range(samples // MAX_WORKERS):
                barrier = Barrier(MAX_WORKERS)
                def one():
                    barrier.wait(timeout=10)
                    return request_bytes(base, path, token)[0]
                futures = [pool.submit(one) for _ in range(MAX_WORKERS)]
                records.extend(f.result(timeout=TIMEOUT + 15) for f in futures)
        duration = time.perf_counter() - t0
    stats = summarize(records, duration)
    if stats['failed']:
        raise RuntimeError(f'{label} had {stats["failed"]} unsuccessful/unsafe responses; candidate cannot pass')
    return stats


def benchmark_base(base, student, instructor, args, cn):
    output = {'base_port': int(base.rsplit(':', 1)[-1]),
              'server_health': check_server(base, candidate=(base == CANDIDATE)),
              'oracle_sessions_before': session_count(cn), 'measurements': {}, 'oracle_sessions_after_each_endpoint': {}}
    for label, (path, required) in PATHS.items():
        token = {'student': student, 'instructor': instructor}.get(required)
        for mode, count in [('sequential', args.samples), ('four_worker', args.parallel)]:
            stats = run_endpoint(base, label, path, token, count, mode=='four_worker', args.warmup)
            output['measurements'][f'{label}.{mode}'] = stats
            print(f'  {label:<27} {mode:<11} n={stats["requests"]:>2}  p50={stats["p50_ms"]:>7.1f}ms  p95={stats["p95_ms"]:>7.1f}ms  HTTP200={stats["passed_200"]}')
        output['oracle_sessions_after_each_endpoint'][label] = session_count(cn)
    output['oracle_sessions_after'] = session_count(cn)
    return output


def verify_settings(args):
    if not (5 <= args.samples <= 50 and 4 <= args.parallel <= 40 and args.parallel % 4 == 0 and 0 <= args.warmup <= 5):
        raise ValueError('Bounded limits: 5<=samples<=50, parallel multiple of four 4..40, warmup 0..5')
    if Path(args.report).suffix.lower() != '.json':
        raise ValueError('Report path must end in .json')


def main(args):
    verify_settings(args)
    preflight(args.main_backend,require_api=True)
    cn, reason = session_probe_from_env(args.main_backend)
    if reason:
        print('ORACLE SESSION COUNT:', reason)
    print('This benchmark performs GETs only after two ordinary login requests; no DML/DDL or quiz writes.')
    print('Measured requests per endpoint/server:', args.samples, 'sequential +', args.parallel, 'four-worker; warmups:', args.warmup)
    print('Oracle V$SESSION totals, if available, include other sessions using EDUSPHERE_APP, not just this server.')
    if args.baseline:
        check_server(BASELINE)  # ensure correct main schema before asking credentials
    if input('Type RUN READONLY PERFORMANCE CHECK to proceed: ').strip() != 'RUN READONLY PERFORMANCE CHECK':
        print('Cancelled before login and measured requests.')
        return 2
    report = {'test': 'EduSphere main database read-only acceptance',
              'candidate_port': 8002, 'baseline_enabled': args.baseline,
              'limits': {'sequential_samples': args.samples, 'four_worker_samples': args.parallel,'warmup_per_mode': args.warmup},
              'oracle_session_count_available': cn is not None,
              'oracle_session_count_note': 'Totals are across processes for EDUSPHERE_APP, including the diagnostic connection.' if cn is not None else reason,
              'runs': {}}
    failure = None
    try:
        print('\nCandidate API (port 8002)')
        student = authenticate(CANDIDATE, 'student')
        instructor = authenticate(CANDIDATE, 'instructor')
        report['runs']['candidate'] = benchmark_base(CANDIDATE, student, instructor, args, cn)
        if args.baseline:
            print('\nOptional original API comparison (port 8000): no writes other than normal login audit')
            old_student = authenticate(BASELINE, 'student')
            old_instructor = authenticate(BASELINE, 'instructor')
            report['runs']['baseline'] = benchmark_base(BASELINE, old_student, old_instructor, args, cn)
    except Exception as exc:
        # Keep the diagnostic summary on failure; never include credentials or token.
        failure = f'{type(exc).__name__}: {exc}'
        report['failure'] = failure
    finally:
        if cn is not None:
            cn.close()
    # Save only sanitized aggregate statistics (no credentials, tokens, bodies, usernames).
    report_file = Path(args.report).resolve()
    report_file.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('Aggregate report:', report_file)
    if failure:
        print('FAIL / INCOMPLETE:', failure)
        return 1
    print('\nPASS: all measured HTTP requests returned 200 and no transport errors occurred.')
    if not report['oracle_session_count_available']:
        print('SESSION COUNT INCOMPLETE: have an authorized DBA capture the V$SESSION worksheet; do not assert verified connection efficiency.')
    print('Compare p95 latency and session totals before accepting a resource-efficiency claim; endpoint timings alone prove reliability, not improvement.')
    return 0


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--main-backend',required=True)
    p.add_argument('--samples',type=int,default=12)
    p.add_argument('--parallel',type=int,default=12,help='Multiple of four, max 40')
    p.add_argument('--warmup',type=int,default=2)
    p.add_argument('--baseline',action='store_true',help='Optional same-schema original API on 127.0.0.1:8000')
    p.add_argument('--report',default='performance_results.json')
    a=p.parse_args()
    try:
        raise SystemExit(main(a))
    except (RuntimeError,ValueError,TimeoutError) as e:
        print('FAIL / INCOMPLETE:', str(e))
        raise SystemExit(1)
