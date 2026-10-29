# EduSphere Web + Optimized — Merged Candidate (17 October 2026)

**Status: STAGING CANDIDATE — DO NOT REPLACE MAIN EDUSPHERE_OWNER YET.**

This project starts from the uploaded `EduSphere_Web.zip` source, retains its original `quiz/auto_grader.py` typed business exceptions, and cherry-picks tested optimizations from `EduSphere_Optimized_Backend_Frontend_2026-10-14.zip`. Security fixes were added across *all* student-facing quiz grade surfaces. The approved **37-table schema and existing DDL/DML are unchanged**.

### Release policy requested by project owner

- Candidate changes remain separate from the original Web installation.
- A change is counted as complete only after source compilation and a relevant regression check pass.
- **13 of 13 planned change groups** passed the available *offline* checks (100%, exceeding the requested 85% development gate). This is a feature-check completion ratio, **not code coverage** and **not an Oracle integration pass**.
- Deployment/promotion remains **BLOCKED** until the merged candidate passes staging Oracle connection/isolation, quiz API lifecycle and role boundary tests, mark/answer-release tests, manual grading/transaction tests, a Windows frontend build, and a concurrency/connection-use comparison. A critical security regression is a blocker even when overall pass rate exceeds 85%.

## Core changes (13 groups)

| # | Change | Implementation | Offline evidence |
|---|---|---|---|
| 1 | Reuse and recycle Oracle connections; request-level cleanup, no unsafe write retry | Backend/database/connection.py, middleware.py, settings.py | Testing/test_optimized_database.py |
| 2 | Batch matching-option metadata SELECTs | Backend/quiz/repository.py | Matching-query test |
| 3 | Coalesce simultaneous identical frontend GET requests only | Frontend/src/services/http.js | request_coalescing.test.mjs |
| 4 | Pre-group attendance sessions instead of repeated filtering | StudentAttendanceView.vue | attendance_predictor.test.mjs; Vue compile |
| 5 | Fixed-thread Waitress startup option | Backend/serve-windows.ps1; requirements.txt | Configuration review; Windows live run pending |
| 6 | Health check verifies all approved 37 tables | Backend/core/views.py | test_merge_security.py |
| 7 | Configure both quiz PL/SQL procedure owners from ORACLE_SCHEMA | Backend/quiz/repository.py | test_merge_security.py |
| 8 | Replace N+1 instructor question listing with one scoped SELECT | Backend/quiz/services.py and repository.py | test_merge_security.py; existing question-bank checks |
| 9 | Stop submission endpoint returning raw grades, maximums, IDs, or grader errors | Backend/quiz/services.py | test_merge_security.py |
| 10 | Require both mark and answer-review release for review endpoint | Backend/quiz/services.py | test_merge_security.py |
| 11 | Limit student/instructor quiz lists to authorized offerings | Backend/quiz/services.py, views.py | test_merge_security.py |
| 12 | Redact unreleased quiz marks in general marks, semester marks, dashboard and report derived percentages | Backend/academics/quiz_visibility.py, repository.py, reports/repository.py | test_merge_security.py (SQL policy/source checks) |
| 13 | Block question/draft retrieval and edits after quiz expiry; keep finalization possible | Backend/quiz/repository.py, services.py | test_merge_security.py |

### Confirmed offline checks on this candidate

- Python unit/static tests: **63 passed**.
- Actual original scoring algorithm: **13 isolated cases passed** (not Oracle DML).
- Frontend attendance predictor: **16/16 passed**; HTTP coalescing: **4/4 passed**.
- Four frontend smoke suites passed (general, cross-role, error-handling, admin-management).
- **43/43 Vue components** parsed/compiled with Vue SFC compiler; **17/17** checked frontend→Django quiz route pairs matched.
- Three original backend audit scripts passed (admin audit reports three optional skips for missing legacy deployment files).
- Database schema/installation SQL unchanged (14/14 source SQL files byte-for-byte identical to Web archive); no migrations.

**Not run here:** live Windows `manage.py check`, full `npm ci && npm run build`, real Oracle SQL execution, staging API flow, concurrency benchmark. No claim of live performance gains or production readiness.

## Application layout

- `Backend/`: Django REST, service/repository modules, Oracle ODBC access and business rules.
- `Frontend/`: Vue application, quiz and mark views, attendance analytics, HTTP helpers and frontend tests.
- `Database/`: **unchanged** 37-table Oracle installer, procedures, triggers, sample data.
- `Testing/`: static/offline and staging-only API acceptance scripts.
- `MERGE_RELEASE_GATE.md`: detailed results, blockers and continuation plan.

## Safe staging test sequence (Windows PowerShell)

1. Keep the main `EDUSPHERE_OWNER` Django backend untouched. Take a fresh copy of `Backend/` named e.g. `EduSphere_MERGED_STAGING`.
2. Copy only the previously **verified STAGING** `.env` into that new folder. It must use `ODBC_USER=EDUSPHERE_STAGE_APP`, `ORACLE_SCHEMA=EDUSPHERE_STAGE_OWNER`, your existing staging DSN, and **no** connection-string override. Do not copy original-owner credentials.
3. Run `python Testing/verify_staging_connection_dynamic.py "C:\\...\\EduSphere_MERGED_STAGING"`. It checks current account, PDB, 37 stage tables, zero visible original tables, and owner-independent procedure calls.
4. Run `python manage.py check` in the staging backend; start `python manage.py runserver 127.0.0.1:8001` or `./serve-windows.ps1 -Port 8001 -Threads 4` (PowerShell). Run the staging API health check and the existing staging lifecycle script from `Testing/` with explicit confirmation. **It creates disposable staging data; do not run it on port 8000.**
5. For a submitted staging quiz attempt where both release flags are set to `N`, run `python Testing/verify_staging_student_release_api.py --attempt-id <STAGING_ATTEMPT_ID>`. The script is read-only except authentication audit. With flags enabled it skips the corresponding denial checks.
6. Test full auto-grading/manual grading, failed writes/rollback, best-attempt component marks, answer release after attempt exhaustion/closure, and instructor visibility toggling. Validate all nine supported question types on staging.
7. From `Frontend/`: `npm ci`, `npm run build`; for browser testing configure `VITE_API_BASE_URL=http://127.0.0.1:8001/api` in a staging-only `.env.local`, then `npm run dev`.
8. Measure Oracle sessions and response times under the original and merged builds on the *same* staging test set; inspect process-local `connection_statistics()` and Oracle V$SESSION if permitted.
9. Promote only after ≥85% of all *planned* checks pass, every P0/P1 authorization/release/transaction test passes, and a backup plus rollback plan exists. Do not modify the 37 tables.

### Design notes and known issues

- The Web original's `BusinessRuleError`/`NotFoundError` behavior was retained; generic `ValueError` substitutions from the optimized source were **not** imported.
- Quiz `QUIZ_GRADING.MAX_MARKS` can differ from `ASSESSMENT_COMPONENT.MAX_MARKS` in historical records. This candidate intentionally does not rewrite/scalemark historical results or choose a new grading policy.
- Author-only/question-linked read semantics are preserved for instructor question bank. Editing remains governed by existing stricter `question_access_for_instructor` and attempted-question lock.
- Student self-view of a **live open attempt** may include that student's *own draft responses* to let them resume. This does not grant access to other students' responses, correct keys, expired drafts, or unreleased marks.
- Staging tools from older packages requiring hardcoded `EDUSPHERE_STAGE_OWNER.PR_*` in source will falsely fail this candidate because it correctly uses `object_name(...)`. Use the included dynamic staging connection checker and updated lifecycle script.
- Credentials are not bundled in this source-only candidate. Keep your original .env locally; do not share it.
