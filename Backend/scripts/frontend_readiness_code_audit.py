"""Static audit for the EduSphere frontend-readiness API completion patch."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]

checks = []


def require(path, needle, label):
    text = (ROOT / path).read_text(encoding="utf-8")
    ok = needle in text
    checks.append((ok, label))


# App registration
for app in ["materials", "announcements", "exams", "gpa", "reports"]:
    require("edusphere/settings.py", f'"{app}"', f"INSTALLED_APPS contains {app}")

# New routes
for needle, label in [
    ('"offerings/<int:offering_id>/grading/"', "grading discovery route"),
    ('"instructor/offerings/<int:offering_id>/roster/"', "instructor roster route"),
]:
    require("academics/urls.py", needle, label)

require("attendance/urls.py", '"sessions/"', "class-session creation route")
for needle, label in [
    ('"<int:quiz_id>/content/"', "quiz content route"),
    ('"questions/"', "question-bank list route"),
    ('"questions/<int:question_id>/"', "question detail route"),
    ('"attempt/<int:attempt_id>/result/"', "quiz result route"),
    ('"attempt/<int:attempt_id>/review/"', "quiz review route"),
]:
    require("quiz/urls.py", needle, label)

# Security / behavior contracts
require(
    "quiz/services.py",
    "Start the quiz attempt before loading quiz content.",
    "student quiz content requires an open attempt",
)
require(
    "quiz/services.py",
    'if result["allow_mark_view"] != "Y"',
    "quiz result respects ALLOW_MARK_VIEW",
)
require(
    "quiz/services.py",
    'if context["allow_answer_review"] != "Y"',
    "quiz review respects ALLOW_ANSWER_REVIEW",
)
require(
    "quiz/services.py",
    '"response_id": int(response["response_id"])',
    "response creation returns response_id",
)
require(
    "academics/services.py",
    "Instructor is not assigned to this offering.",
    "instructor grading/roster ownership checks",
)
require(
    "attendance/services.py",
    "CLASS_SESSION_CREATED",
    "class-session creation is audited",
)
require(
    "sql/12_grant_runtime_access.sql",
    "GRANT INSERT ON CLASS_SESSION TO &APP_USER;",
    "canonical runtime grant includes CLASS_SESSION INSERT",
)
require(
    "sql/16_verify_runtime_privileges_and_audit.sql",
    "need_table_priv('CLASS_SESSION','INSERT');",
    "runtime verification checks CLASS_SESSION INSERT",
)

failures = [label for ok, label in checks if not ok]
for ok, label in checks:
    print(f"[{'PASS' if ok else 'FAIL'}] {label}")

if failures:
    print(f"FRONTEND READINESS CODE AUDIT: FAIL ({len(failures)} failure(s))")
    sys.exit(1)

print("FRONTEND READINESS CODE AUDIT: PASS")
