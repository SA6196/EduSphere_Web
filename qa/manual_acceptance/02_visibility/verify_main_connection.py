"""Read-only configuration, Oracle, and (optional) API preflight for merged EduSphere.

Does not mutate Oracle data. Supports exact main schema only; user must opt in to
subsequent write-based lifecycle verification. Requires python-dotenv and pyodbc.
"""
import argparse
import os
from pathlib import Path
from urllib.request import urlopen
import json

SCHEMA='EDUSPHERE_OWNER'
APP_USER='EDUSPHERE_APP'
BASE='http://127.0.0.1:8002'


def preflight(backend, require_api=False):
    from dotenv import dotenv_values
    import pyodbc
    backend=Path(backend).resolve()
    for p in ('manage.py','quiz/repository.py','quiz/services.py','academics/quiz_visibility.py','core/views.py'):
        if not (backend/p).is_file():
            raise RuntimeError(f'Merged backend missing required {p}: {backend}')
    if not (backend/'.env').is_file():
        raise RuntimeError('No .env in merged Backend folder. Copy local main DB .env to the candidate, not into this test package.')
    cfg=dotenv_values(backend/'.env')
    if cfg.get('ODBC_USER')!=APP_USER or cfg.get('ORACLE_SCHEMA')!=SCHEMA:
        raise RuntimeError(f'Refusing non-main credentials: must be ODBC_USER={APP_USER} and ORACLE_SCHEMA={SCHEMA}')
    if (cfg.get('ODBC_CONNECTION_STRING') or '').strip():
        raise RuntimeError('Refusing ODBC_CONNECTION_STRING override. Use DSN/UID/PWD to verify the actual account.')
    for key in ('ODBC_DSN','ODBC_USER','ODBC_PASSWORD','ORACLE_SCHEMA'):
        if not cfg.get(key):raise RuntimeError(f'Missing {key} in main candidate .env')
    for key in ('ODBC_DSN','ODBC_USER','ODBC_PASSWORD','ORACLE_SCHEMA','ODBC_CONNECTION_STRING'):
        if key in os.environ and os.environ[key] != (cfg.get(key) or ''):
            raise RuntimeError(f'Inherited PowerShell {key} conflicts with .env; clear it first.')
    repo=(backend/'quiz/repository.py').read_text('utf8')
    if 'EDUSPHERE_OWNER.PR_START_QUIZ_ATTEMPT' in repo or 'EDUSPHERE_OWNER.PR_SUBMIT_QUIZ_ATTEMPT' in repo:
        raise RuntimeError('Merged backend still hardcodes procedure owner')
    for routine in ('PR_START_QUIZ_ATTEMPT','PR_SUBMIT_QUIZ_ATTEMPT'):
        if '{object_name("'+routine+'")}' not in repo:
            raise RuntimeError('Expected configurable procedure not found: '+routine)
    services=(backend/'quiz/services.py').read_text('utf8')
    if '"grading": {"status": grading_state}' not in services:
        raise RuntimeError('Candidate submission redaction fix absent; refusing old backend')
    core=(backend/'core/views.py').read_text('utf8')
    if 'QUESTION_KEYWORD' not in core or 'QUIZ_GRADING' not in core or 'QUIZ_RESPONSE_MATCH' not in core:
        raise RuntimeError('37-table health manifest fix absent')
    conn=pyodbc.connect(f"DSN={cfg['ODBC_DSN']};UID={cfg['ODBC_USER']};PWD={cfg['ODBC_PASSWORD']}",timeout=8)
    try:
        c=conn.cursor()
        c.execute("SELECT USER, SYS_CONTEXT('USERENV','CON_NAME') FROM DUAL")
        usr,pdb=(str(x).upper() for x in c.fetchone())
        print('Connected Oracle account:',usr,'PDB:',pdb)
        if (usr,pdb)!=(APP_USER,'XEPDB1'):
            raise RuntimeError('Oracle connection does not use the intended main test account in XEPDB1')
        c.execute('SELECT COUNT(*) FROM ALL_TABLES WHERE OWNER=?',(SCHEMA,))
        count=int(c.fetchone()[0]);print('Original schema tables visible:',count)
        if count!=37:raise RuntimeError(f'Expected 37 main schema tables, got {count}')
        c.execute('SELECT COUNT(*) FROM ALL_OBJECTS WHERE OWNER=? AND OBJECT_TYPE=\'PROCEDURE\' AND OBJECT_NAME IN (\'PR_START_QUIZ_ATTEMPT\',\'PR_SUBMIT_QUIZ_ATTEMPT\') AND STATUS=\'VALID\'',(SCHEMA,))
        procedures=int(c.fetchone()[0]);print('Required quiz procedures VALID:',procedures,'of 2')
        if procedures!=2:raise RuntimeError('Quiz start/submit procedures are missing or invalid')
        c.close()
    finally:conn.close()
    if require_api:
        with urlopen(BASE+'/api/db-health/',timeout=12) as r:
            body=json.load(r)
            print('API health:',r.status, 'schema:',body.get('schema'),'visible:',body.get('visible_tables'))
            if r.status!=200 or body.get('status')!='ok' or body.get('schema')!=SCHEMA or body.get('expected_tables')!=37 or body.get('visible_tables')!=37 or body.get('missing_tables'):
                raise RuntimeError('Candidate API on port 8002 is not healthy EDUSPHERE_OWNER')
    print('PASS: main-schema preflight, no writes performed.')
    return 0

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--main-backend',required=True)
    p.add_argument('--api',action='store_true',help='Also verify candidate API on port 8002')
    a=p.parse_args()
    raise SystemExit(preflight(a.main_backend,a.api))
