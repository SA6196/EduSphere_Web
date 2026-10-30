"""Read-only Oracle check for the MERGED candidate's configurable owner syntax.

Unlike the earlier staging verifier, this one accepts object_name(...) calls
instead of requiring hardcoded EDUSPHERE_STAGE_OWNER procedures.
"""
from pathlib import Path
import argparse, os, re


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('backend', help='Directory for your separate merged Django staging backend')
    args=parser.parse_args()
    backend=Path(args.backend).resolve()
    if not backend.name.endswith('_STAGING') and not backend.name.endswith('_STAGING_MERGED'):
        parser.error('Refusing non-staging backend directory.')
    if not (backend/'manage.py').is_file() or not (backend/'.env').is_file():
        parser.error('Missing manage.py or staging .env')
    from dotenv import dotenv_values
    config=dotenv_values(backend/'.env')
    if config.get('ODBC_USER')!='EDUSPHERE_STAGE_APP' or config.get('ORACLE_SCHEMA')!='EDUSPHERE_STAGE_OWNER':
        parser.error('Refusing non-staging Oracle account or schema.')
    if config.get('ODBC_CONNECTION_STRING','').strip():
        parser.error('Remove ODBC_CONNECTION_STRING override to enforce staged DSN/user.')
    for field in ('ODBC_DSN','ODBC_PASSWORD'):
        if not config.get(field):parser.error(f'Missing {field} in staging .env')
    for key in ('ODBC_USER','ORACLE_SCHEMA','ODBC_CONNECTION_STRING'):
        if os.environ.get(key) and os.environ[key]!=config.get(key,''):
            parser.error(f'Conflicting PowerShell {key} override. Clear it before starting Django.')
    repo=(backend/'quiz'/'repository.py').read_text('utf8')
    for routine in ('PR_START_QUIZ_ATTEMPT','PR_SUBMIT_QUIZ_ATTEMPT'):
        if '{object_name("'+routine+'")}' not in repo:
            parser.error(f'Missing configurable Oracle routine: {routine}')
    if re.search(r'EDUSPHERE_OWNER\.(?:PR_START_QUIZ_ATTEMPT|PR_SUBMIT_QUIZ_ATTEMPT)',repo):
        parser.error('Original-owner procedure hardcoding found.')
    import pyodbc
    conn=pyodbc.connect(f"DSN={config['ODBC_DSN']};UID={config['ODBC_USER']};PWD={config['ODBC_PASSWORD']}",timeout=6)
    try:
        cur=conn.cursor()
        cur.execute("SELECT USER, SYS_CONTEXT('USERENV','CON_NAME') FROM DUAL")
        user,pdb=tuple(str(v).upper() for v in cur.fetchone())
        print('Oracle account:',user,'PDB:',pdb)
        if (user,pdb)!=('EDUSPHERE_STAGE_APP','XEPDB1'):raise RuntimeError('Wrong Oracle staging account/PDB')
        cur.execute('SELECT COUNT(*) FROM ALL_TABLES WHERE OWNER=?',('EDUSPHERE_STAGE_OWNER',))
        stage_count=int(cur.fetchone()[0]);print('Staging tables visible:',stage_count)
        cur.execute("SELECT COUNT(*) FROM ALL_TABLES WHERE OWNER='EDUSPHERE_OWNER'")
        original_count=int(cur.fetchone()[0]);print('Original tables visible:',original_count)
        if stage_count!=37 or original_count!=0:raise RuntimeError('Staging isolation failed. Do not run write tests.')
        print('PASS: 37 staging tables, zero original-owner tables, configurable procedures.')
    finally:
        conn.close()

if __name__=='__main__':main()
