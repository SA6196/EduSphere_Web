# EduSphere — MAIN Oracle manual grading & transaction test

**Candidate:** `EduSphere_Web_Optimized_Secure_Merge_STAGING_CANDIDATE`, running on `127.0.0.1:8002` and connected to `EDUSPHERE_OWNER` in XEPDB1.

**Background (live results reported 18 Oct 2026):** 37 main tables and two quiz procedures verified; question-bank role tests 9/9; MCQ quiz 104 / attempt 166 graded 10/10 with results unpublished; N/N, N/Y, Y/N, Y/Y visibility matrix passed with original N/N restored; two-attempt quiz 124 succeeded, 10/10 followed by 0/10, `STUDENT_MARK` stayed at 10/10 and third attempt was denied. These are observed test logs, not an exhaustive security certification.

## What this package tests

A **new** course, semester, offering, 10-mark quiz (MCQ 4 marks + LONG_TEXT 6 marks), one student enrollment and one submitted attempt are created after confirmation. The automatic grader should store 4/10 with `AUTO_GRADED`, but **must not publish any course-component mark before instructor review**. Unassigned instructors and students must be unable to grade or release. The assigned instructor must receive HTTP 400 for invalid rubric scores, omitted review, and inconsistent final marks. A valid review awards 5/6 to the long-text response, bringing the final score to 9/10. Oracle should then contain the correct per-question, per-attempt and component marks. Releasing the grading event must not bypass the independent `ALLOW_MARK_VIEW=N` / `ALLOW_ANSWER_REVIEW=N` restrictions.

The **optional** `--test-db-rollback` mode creates the same disposable fixture and intentionally asks the backend to write instructor notes exceeding `VARCHAR2(1000)`, *after* changing the question-level grade. That request should fail and Oracle should retain its exact original grading snapshot. This mode may produce **one expected HTTP 500 and a server log exception**; it requires an additional confirmation. The test later submits the valid review so the new QA fixture finishes in a consistent state. If any rollback assertion fails, the script stops without attempting the valid review.

## Run on Windows PowerShell

Keep the merged backend running on **port 8002**, pointed to the original test database. Use the same activated `EduSphereVenv` as your earlier successful verifiers. Set `$backend` to the extracted merged `Backend` folder:

```powershell
$backend = "C:\Users\hamza\Downloads\EduSphere_Web_Optimized_Secure_Merge_STAGING_CANDIDATE\EduSphere_Merged_Candidate\Backend"
python verify_main_connection.py --main-backend "$backend" --api
python -m unittest -v test_manual_grading_offline.py
python verify_main_manual_grading.py --main-backend "$backend"
```

The `$backend` path is an **example**; preserve the actual path that worked in your earlier tests.

Optional separate failure/rollback test (**creates another distinct disposable quiz**, not a rerun of the already graded one):

```powershell
python verify_main_manual_grading.py --main-backend "$backend" --test-db-rollback
```

Both commands prompt for administrator, assigned instructor, unassigned instructor, owning student and another student. Any existing valid main test accounts may be used. The script needs exact confirmation `MAIN MANUAL REVIEW TEST DATA ONLY`; rollback mode also needs `TEST INTENTIONAL ORACLE ROLLBACK`.

**Important:** This script does **not** edit quiz 104, 124 or their attempts. Do not run on production or a database containing valuable records. It creates records permanently, has no cleanup step, and does not alter the fixed 37-table schema. All Oracle inspection queries are read-only `SELECT`, while actual mutations are authenticated HTTP API requests. If it stops midway, refer to the displayed `QA FIXTURE` IDs and new test tag; do not simply retry against partially created records.

## Interpreting failures

- If the initial automatic grading is not `AUTO_GRADED` 4/10, stop and check server logs (student submission can report a grading retry state rather than a score).
- If `STUDENT_MARK` exists before long-text review, this is a **critical grade-publication defect**.
- If any student result, history, semester markbook or dashboard leaks unreleased grades, this is a **critical privacy defect**.
- If the deliberate database error returns an HTTP error **but either the question-grade row or grading header changes**, the atomic rollback test **fails**; do not promote.
- If rubric scoring updates per-question marks but not `STUDENT_MARK`, grade synchronization failed.
- If a different student or instructor can edit/release the grade, access control failed.

## Release gate

This is another live acceptance stage, not deployment certification. Promote only after **at least 85% of the agreed test groups pass and 100% of critical security, grading consistency and transaction-integrity checks pass**. Remaining work after this test includes expiry, diverse question types, concurrency, production Vue build/browser checks, and live Oracle performance measurement.
