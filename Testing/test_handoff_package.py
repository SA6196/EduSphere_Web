import base64
import hashlib
import importlib.util
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
SCHEMA=(ROOT/'Database'/'Schema_Fixed'/'01_create_tables.sql').read_text(encoding='utf8')

class HandoffPackageTests(unittest.TestCase):
    def test_fixed_schema_37(self):
        tables = re.findall(r'(?im)^CREATE\s+TABLE\s+([A-Z_]+)\s*\(',SCHEMA)
        self.assertEqual(len(tables),37)
        self.assertEqual(len(set(tables)),37)

    def test_sample_sql_columns_exist(self):
        table_col={}
        matches=list(re.finditer(r'(?im)^CREATE\s+TABLE\s+([A-Z_]+)\s*\(',SCHEMA))
        for match in matches:
            start=match.end()
            depth=1
            j=start
            while j<len(SCHEMA) and depth:
                if SCHEMA[j]=='(':depth+=1
                elif SCHEMA[j]==')':depth-=1
                j+=1
            definition=SCHEMA[start:j-1]
            # Each column starts a logical line, constraints start with CONSTRAINT.
            table_col[match.group(1)]={c.upper() for c in re.findall(r'(?m)^\s+([A-Za-z_]+)\s+(?:NUMBER|VARCHAR2|CHAR|DATE|TIMESTAMP|CLOB)\b',definition)}
        files=[ROOT/'Database'/'Sample_Data'/f for f in ('01_sample_catalog.sql','03_sample_classes.sql')]
        pattern=r'(?i)INSERT\s+INTO\s+([A-Za-z_]+)\s*\((.*?)\)\s*VALUES\s*\('
        for file in files:
            for tab, cols in re.findall(pattern,file.read_text(encoding='utf8'),re.DOTALL):
                self.assertIn(tab.upper(),table_col,(file.name,tab))
                for col in cols.split(','):
                    self.assertIn(col.strip().upper(),table_col[tab.upper()],(file.name,tab,col))

    def test_fresh_installer_has_no_default_admin_seed(self):
        sql=(ROOT/'Database'/'01_INSTALL_FRESH.sql').read_text(encoding='utf8')
        self.assertNotIn('07_seed_final_admin.sql',sql)
        self.assertIn('09_compliance_runtime_grants.sql',sql)
        self.assertIn('08_finalize_expired_attempts.sql',sql)

    def test_account_generator_creates_valid_hashes_and_no_cleartext(self):
        path=ROOT/'Database'/'Sample_Data'/'generate_demo_accounts.py'
        spec=importlib.util.spec_from_file_location('demo_accounts_test',path)
        module=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        pwds=[f'UniqueDemoPassword{i}!' for i in range(5)]
        replies=[]
        for p in pwds: replies.extend([p,p])
        with tempfile.TemporaryDirectory() as tmp:
            dest=Path(tmp)/'test_accounts.sql'
            with patch.object(module.getpass,'getpass',side_effect=replies):
                module.generate(dest)
            content=dest.read_text(encoding='utf8')
            self.assertEqual(content.count('INSERT INTO LMS_USER'),5)
            self.assertTrue(all(p not in content for p in pwds))
            hashes=re.findall(r"pbkdf2_sha256\$720000\$[A-Za-z0-9]+\$[A-Za-z0-9+/=]+",content)
            self.assertEqual(len(hashes),5)
            for hashval,password in zip(hashes,pwds):
                _,its,salt,encoded=hashval.split('$')
                calc=base64.b64encode(hashlib.pbkdf2_hmac('sha256',password.encode(),salt.encode(),int(its))).decode()
                self.assertEqual(calc,encoded)

if __name__=='__main__': unittest.main()
