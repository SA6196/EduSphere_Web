# EduSphere MAIN Oracle — Concurrent Autosave & Submit Acceptance

## Purpose

Use this package **after the successful main-DB expiry verifier** on the merged EduSphere Django candidate running on `127.0.0.1:8002`. It creates a single disposable main-schema quiz with `max_attempts=2` and a 15-minute duration, then tests two narrowly bounded client races using **four simultaneous authenticated requests** each. The project schema stays at 37 tables; no application source is modified.

## Previously verified stages (user's real Oracle output)

1. Main schema health, Oracle procedures.
2. Instructor question-bank isolation and student denial (9/9).
3. Quiz lifecycle, grading persistence, answer-key lock.
4. Four release-flag combinations and indirect mark leakage prevention.
5. Two-attempt maximum and highest-score preservation.
6. Manual `LONG_TEXT` grading and unauthorized review rejection.
7. Deliberate Oracle grading rollback and subsequent valid review.
8. One-minute expiry, frozen answers, finalization, correct 10/10 grading, no unpublished result exposure (live PASS: quiz 127, attempt 190, tag `E55F3A934B`; offline verifier 17/17).

## Test design

**Phase A: duplicate submit race.** One correct answer is saved. Four requests concurrently call `/api/quizzes/attempt/{id}/submit/`. Exactly one must succeed and three must be rejected (HTTP 400/403/409/422). Verify one submitted attempt, one grading header, one question-grade record, retained 10/10, and private results.

**Phase B: autosave versus submit race.** A second attempt starts with the correct answer saved. Two autosaves (one correct, one incorrect) and two submits race. Only one submit may succeed. An autosave may succeed *before* submission or be rejected *after* submission. Once submitted, the stored answer must contain exactly one selected option; final auto marks and question marks must match its actual correctness (10/10 or 0/10). The final component mark must retain the first attempt's 10/10. Neither attempt may be edited afterward.

**Fail conditions** include HTTP 5xx, request timeout, two successful submissions, partial/duplicate grading, missing grade, a marks leak in the submit response, a lost or multiply selected option, incorrect grading for final saved state, or a submitted attempt that remains editable. If a failure happens, **do not promote this candidate**; save both Python and Django outputs for diagnosis. This test does not make code changes automatically.

## Run on Windows

Leave the merged candidate backend running on **port 8002**, using the **main test-only** `EDUSPHERE_OWNER` schema. Recommended: a four-thread Waitress instance; ensure no other server is bound to port 8002.

In PowerShell from the extracted test directory, and with `$backend` set to the merged candidate `Backend` path used previously:

```powershell
python verify_main_connection.py --main-backend "$backend" --api
python -m unittest -v test_concurrency_offline.py
python verify_main_concurrency.py --main-backend "$backend"
```

Enter `MAIN CONCURRENT QUIZ TEST DATA ONLY` *exactly* to authorize the new disposable fixture. Then enter `FINAL_ADMIN`, assigned instructor `FINAL_I2`, owning student `FINAL_S6`, and a different student such as `FINAL_S2` when prompted, with their existing local passwords. Only user-provided identities are used; credentials aren't recorded in files.

It makes two saved/submitted student attempts, but **does not modify the previous QA quizzes**. A unique uppercase 10-hex QA tag and new quiz and attempt IDs are printed. The test data remain in Oracle, and both release flags remain `N/N`.

## Safety and limitations

- Oracle access by this verifier is **SELECT-only**. Data creation and student write operations happen via the standard authenticated Django API only, after exact confirmation. No direct DML, DDL, migration, cleanup, or flags update.
- The test uses **at most four simultaneous HTTP requests per phase**; it is deliberately not a high-load or DoS benchmark.
- Two autosaves in Phase B have no predefined winner. The verifier reads the authoritative final Oracle state and checks that grading matches it. This avoids false failures caused solely by request scheduling.
- The four-request test should be run with stable worker threads. Django development server may behave differently from Waitress; record which server was used.
- The test runner cannot access the user's local Oracle instance remotely. A successful offline 17/17 verifier run establishes only script behavior, **not** live DB correctness.
- If Oracle returns a transient lock/deadlock error, preserve traceback and transaction details. A severe failure blocks promotion even if 85% of other groups pass.

## After this passes

Run a controlled Oracle session/latency comparison (original vs merged) followed by `npm ci`, `npm run build` and the interactive end-to-end Vue smoke checklist on Windows. All critical security, grading, and transaction tests must pass before production adoption.
