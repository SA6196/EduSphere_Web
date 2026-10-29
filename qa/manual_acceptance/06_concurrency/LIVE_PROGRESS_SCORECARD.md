# EduSphere MAIN Oracle — Live Acceptance Scorecard (October 18, 2026)

**Baseline:** `EduSphere_Web_Optimized_Secure_Merge_STAGING_CANDIDATE` on localhost:8002, Oracle XEPDB1 / `EDUSPHERE_OWNER`, account `EDUSPHERE_APP`. Original fixed 37-table schema unchanged.

| Acceptance group | Status | Evidence from user-provided live logs |
|---|---|---|
| 1. Main database health and required procedures | **PASS** | 37/37 tables, two valid quiz procedures, HTTP 200 |
| 2. Role-based question-bank access | **PASS** | 9/9; cross-instructor isolation, admin, student denial |
| 3. Quiz submit, key lock, grading persistence | **PASS** | quiz 104 / attempt 166, 10/10, grade and component sync |
| 4. Visibility/release policy and alternate APIs | **PASS** | four N/N, N/Y, Y/N, Y/Y combinations; quiz flags restored N/N |
| 5. Multiple attempts, highest score, limit | **PASS** | quiz 124; 10/10 then 0/10, final 10/10; third attempt blocked |
| 6. Manual long-text review | **PASS** | quiz 125 / 188, auto 4/10, reviewed 9/10 |
| 7. Atomic rollback of partial manual grading | **PASS** | quiz 126 / 189; forced DB failure rolled back; valid 9/10 after |
| 8. Oracle-side expiry and post-expiry finalization | **PASS** | quiz 127 / 190; expired edits/content blocked, correct saved answer 10/10; 17/17 offline verifier checks |
| 9. Concurrent submit/autosave consistency | **PENDING LIVE** | New bounded 4-worker verifier supplied; 17/17 offline verifier checks |
| 10. Oracle session count and response-time benchmark | **PENDING** | Must measure real deployment configurations |
| 11. Windows Vue production build and UI workflows | **PENDING** | Require `npm ci`, `npm run build`, manual authenticated UI smoke |

**Current status:** 8 of 11 defined live acceptance groups passed (~73%). This is **not** the requested ≥85% full gate yet. At least 10 of 11 are required for that numeric threshold, and all critical security, transaction, grading, and concurrency checks must pass regardless of percentage.

**Next:** run `verify_main_concurrency.py` against the isolated new QA fixture. Never promote the candidate just because offline verifier checks pass.
