# EduSphere main Oracle — live acceptance status

**Observed from user-supplied Windows console output (17 October 2026)**, not executed by this assistant against the local Oracle server.

## Completed on main test database (port 8002)

- Strict Oracle preflight: EDUSPHERE_APP, XEPDB1, 37 owner tables, 2 valid quiz procedures, API health 200.
- Question-bank reads: **9 passed, 0 failed, 0 skipped**; instructor A/B isolation, admin union, student denial and unauthenticated 401.
- Controlled quiz lifecycle on unique fixture `E7808E9C43`: new offering 22, quiz 104, question 148, attempt 166, correct submitted MCQ score 10/10 persisted consistently in QUIZ_GRADING, QUIZ_QUESTION_GRADE and STUDENT_MARK.
- Key editing locked after start and after submission, for author and admin. Unauthorized instructor grading denied.
- Unreleased attempt-specific results/review, marks API, semester markbook, student dashboard and other-student access denied/redacted.
- Existing 37-table schema unchanged. Fixture intentionally remains in EDUSPHERE_OWNER.

## Next critical gate

Run `verify_main_visibility_matrix.py` from this updated package to test all four combinations of mark/review publication permissions, cross-student isolation and role-based write denial. Only this script's verified output can close the next gate; no live results claimed yet.

## Remaining after that

Manual LONG_TEXT review, other seven question types, multiple attempt highest-score synchronization, expiry/late answers, simulated write rollback, Windows frontend build/browser workflows, Oracle connection utilization and latency comparisons. The **85% acceptance requirement** cannot be concluded from the completed subset alone. Zero critical authorization, data confidentiality, or atomic-grade failures are permitted for promotion.
