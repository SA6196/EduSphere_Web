from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
checks = {
    "administration app registered": (ROOT / "edusphere/settings.py", '"administration"'),
    "administration URLs mounted": (ROOT / "edusphere/urls.py", 'include("administration.urls")'),
    "student account API": (ROOT / "administration/urls.py", 'path("students/"'),
    "instructor account API": (ROOT / "administration/urls.py", 'path("instructors/"'),
    "offering creation API": (ROOT / "administration/urls.py", 'path("offerings/"'),
    "instructor assignment API": (ROOT / "administration/urls.py", 'instructors/"'),
    "grading scheme API": (ROOT / "administration/urls.py", 'grading-scheme/"'),
    "atomic Oracle transaction use": (ROOT / "administration/repository.py", 'oracle_connection(commit=True)'),
    "password hashing": (ROOT / "administration/services.py", 'make_password(password)'),
    "published-grade grading lock": (ROOT / "administration/services.py", 'published_grade_count(offering_id) > 0'),
    "canonical LMS_USER INSERT grant": (ROOT / "sql/12_grant_runtime_access.sql", 'GRANT INSERT ON LMS_USER TO &APP_USER;'),
    "admin grant delta": (ROOT / "sql/20_grant_admin_management_access.sql", 'GRANT INSERT ON COURSE_OFFERING TO EDUSPHERE_APP;'),
    "admin privilege verification": (ROOT / "sql/21_verify_admin_management_access.sql", 'ADMIN-MANAGEMENT PRIVILEGE VERIFICATION: PASS'),
}

failed = 0
for label, (path, needle) in checks.items():
    ok = path.exists() and needle in path.read_text(encoding="utf-8")
    print(f"[{'PASS' if ok else 'FAIL'}] {label}")
    failed += 0 if ok else 1

if failed:
    print(f"ADMIN MANAGEMENT CODE AUDIT: FAIL ({failed})")
    sys.exit(1)
print("ADMIN MANAGEMENT CODE AUDIT: PASS")
