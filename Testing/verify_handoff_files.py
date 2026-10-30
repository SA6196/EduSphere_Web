"""Read-only checksum verification for extracted handoff package."""
import hashlib
from pathlib import Path

root=Path(__file__).resolve().parents[1]
manifest=root/'FILE_SHA256SUMS.txt'
failed=[]; seen=0
for line in manifest.read_text(encoding='utf8').splitlines():
    if not line.strip():continue
    expected,name=line.split('  ',1)
    f=root/name
    if not f.exists():
        failed.append(f'MISSING {name}')
        continue
    actual=hashlib.sha256(f.read_bytes()).hexdigest()
    if actual!=expected:failed.append(f'CHANGED {name}')
    seen+=1
print(f'Package file checksums verified: {seen}')
if failed:
    print('\n'.join(failed));raise SystemExit(1)
print('PASS: extracted handoff matches published checksum manifest')
