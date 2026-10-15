from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
EXCLUDE = {".venv", "__pycache__"}

def pyfiles():
    for p in ROOT.rglob("*.py"):
        if not any(part in EXCLUDE for part in p.parts):
            yield p

errors = []

# ActivityTypes references must exist.
constants = (ROOT / "core" / "constants.py").read_text(encoding="utf-8")
defined = set(re.findall(r"^\s{4}([A-Z][A-Z0-9_]+)\s*=", constants, re.M))
refs = set()
for p in pyfiles():
    refs.update(re.findall(r"ActivityTypes\.([A-Z0-9_]+)", p.read_text(encoding="utf-8", errors="ignore")))
missing = sorted(refs - defined)
if missing:
    errors.append(f"Missing ActivityTypes constants: {missing}")

# Activity log writes must use PR_LOG_ACTIVITY, not direct table INSERT.
for p in pyfiles():
    text = p.read_text(encoding="utf-8", errors="ignore")
    if re.search(r"INSERT\s+INTO\s+[^\n]*ACTIVITY_LOG", text, re.I):
        errors.append(f"Direct ACTIVITY_LOG INSERT found: {p.relative_to(ROOT)}")

# Service layer must not leak built-in permission/value exceptions.
for p in ROOT.rglob("services.py"):
    if any(part in EXCLUDE for part in p.parts):
        continue
    text = p.read_text(encoding="utf-8", errors="ignore")
    if "raise PermissionError(" in text:
        errors.append(f"Built-in PermissionError found: {p.relative_to(ROOT)}")
    if "raise ValueError(" in text:
        errors.append(f"Built-in ValueError found: {p.relative_to(ROOT)}")

print("Referenced ActivityTypes:", sorted(refs))
print("Missing ActivityTypes:", missing)
print("Direct ACTIVITY_LOG inserts: none" if not any("ACTIVITY_LOG" in e for e in errors) else "Direct ACTIVITY_LOG inserts: FOUND")

if errors:
    print("FINAL CODE AUDIT: FAIL")
    for e in errors:
        print(" -", e)
    sys.exit(1)

print("FINAL CODE AUDIT: PASS")
