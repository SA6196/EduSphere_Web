# EduSphere MAIN Oracle — Expiry Acceptance (Next Stage)

## Purpose

The merged backend has passed live question-bank isolation, attempted-question locks, result-visibility matrix, two-attempt highest-score grading, manual LONG_TEXT grading, and deliberately induced Oracle rollback. This package tests **attempt expiry** on the MAIN test-only Oracle schema without changing the fixed 37-table schema or any existing QA fixtures.

The test creates **a fresh quiz with a 1-minute duration** and one MCQ for 10 marks. It saves the correct answer, waits until **Oracle** reports `DURATION_EXPIRED` (normally about 60 seconds), and verifies:

1. Expired student question/draft retrieval is blocked.
2. An expired student's response autosave and direct option-add API are blocked.
3. The previously saved answer remains unchanged in Oracle.
4. Another student cannot submit the owner's attempt.
5. The owner can finalize **previously saved answers** after expiry.
6. Exactly one submitted attempt and grading record exist; the saved correct answer receives 10/10.
7. A second submit, extra attempt, and unauthorized results/answers are blocked.
8. Unreleased mark and solution flags remain N/N.

## Folder contents

- `verify_main_connection.py` — existing main-DB read-only preflight (copied unchanged).
- `verify_main_api_quiz_lifecycle.py` — existing helper library (copied unchanged), not invoked as a standalone test.
- `verify_main_expiry.py` — new end-to-end expiry verifier.
- `test_expiry_offline.py` — verifier safeguards and control-flow unit tests.
- `LIVE_PROGRESS_SCORECARD.md` — evidence status through October 18.
- `SHA256SUMS.txt` — hashes for the package files.

## Windows instructions

Keep the merged backend running on port 8002 and the main database connected to `EDUSPHERE_OWNER` using `EDUSPHERE_APP`. Use the **same** `$backend` path as the earlier successful test runs.

```powershell
python verify_main_connection.py --main-backend "$backend" --api
python -m unittest -v test_expiry_offline.py
python verify_main_expiry.py --main-backend "$backend"
```

Enter the exact confirmation `MAIN EXPIRY TEST DATA ONLY` to allow creation of disposable data. Log in with an ADMIN, an assigned INSTRUCTOR, the owning STUDENT, and a DIFFERENT STUDENT. Enter account names and passwords interactively; none are stored in the ZIP.

If the quiz expires during slow manual login, no issue: the attempt countdown begins only after the logins and creation are complete. The test waits up to 115 seconds for Oracle to report expiration; it does not rely on workstation time. On slow systems you may use `--max-wait 150` (allowed range 70–180 seconds). Do not use other tests or browsers to submit the same new quiz simultaneously.

## Safety and limitations

- **Only Django authenticated APIs create or modify QA records.** All direct Oracle access by the verifier is read-only `SELECT`.
- New QA records are permanent until manually cleaned; no cleanup or schema changes occur.
- Every new fixture has a unique 10-character hexadecimal tag and uses its own course, semester, offering, component, quiz, question, and attempt.
- Existing quizzes `104`, `124`, `125`, and `126`, or attempts `166`, `186`, `187`, `188`, `189` are not touched by design.
- An interrupted run may leave a partly created, disposable fixture. Use the printed tag and IDs to inspect it before deciding whether to clean up.
- **Do not claim this test passed live until it has run against the real Oracle system.** The ZIP's 17/17 result is offline verification of the test script, not proof of Oracle runtime behavior.
- An expiry failure involving post-deadline submit must be investigated together with the Oracle `PR_SUBMIT_QUIZ_ATTEMPT` patch. Do not automatically change tables or procedures just to make the test pass.
- Once expiry passes, prioritize concurrent submit/autosave races and actual Oracle session count/latency measurements under Waitress.
