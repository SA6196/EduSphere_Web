"""Read-only source integrity check; safe in GitHub Actions without Oracle."""
import json, hashlib, pathlib, re, sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
manifest=json.loads((ROOT/'Testing/BASELINE_SQL_SHA256.json').read_text(encoding='utf8'))
errors=[]
for short, expected in manifest.items():
 p=ROOT/'Database'/short
 if not p.is_file(): errors.append('MISSING: '+short); continue
 actual=hashlib.sha256(p.read_bytes()).hexdigest()
 if actual!=expected: errors.append('CHANGED SQL: '+short)
sql=(ROOT/'Database/Schema_Fixed/01_create_tables.sql').read_text(encoding='utf8')
tables=re.findall(r'(?im)^CREATE\s+TABLE\s+([A-Z_]+)\s*\(',sql)
if len(tables)!=37 or len(set(tables))!=37: errors.append(f'Expected 37 unique table definitions, found {len(tables)}')
for rel in ('Backend/.env','Frontend/.env','Frontend/.env.local'):
 if (ROOT/rel).exists():errors.append('LOCAL SECRET FILE present in repo root: '+rel)
for item in errors:print('FAIL:',item)
if errors:sys.exit(1)
print(f'PASS: original {len(manifest)} SQL checksums unchanged; 37 unique tables; no committed runtime .env')
