# EduSphere main Oracle — multiple-attempt acceptance test

## Verified prior steps (from user console output, not replayed here)

- EDUSPHERE_APP/XEPDB1/EDUSPHERE_OWNER: all 37 tables visible; required procedures valid; API health 200.
- Question bank: 9 passed, 0 failed, 0 skipped, including instructor ownership and student denial.
- Full API quiz fixture **E7808E9C43**: quiz **104**, question **148**, attempt **166**. Correct MCQ scored **10/10** in `QUIZ_GRADING`, `QUIZ_QUESTION_GRADE`, and `STUDENT_MARK`. Hidden mark/answer leaks denied.
- Visibility matrix: `N/N`, `N/Y`, `Y/N`, `Y/Y` all matched the intended API access rules. Forced updates by unassigned instructor, student and anonymous caller denied. **Original quiz visibility restored to N/N**, confirmed by Oracle and the result endpoint.

## Next live check: highest-scoring attempt wins

The new `verify_main_multiple_attempts.py` script is not the earlier one-attempt verifier. It **creates a fresh disposable quiz**, instead of editing quiz 104 or attempting to change its approved `MAX_ATTEMPTS=1` record. It creates one course, semester, offering, grading scheme/component, MCQ and student enrollment, with `MAX_ATTEMPTS=2`.

1. First attempt receives **10/10**.
2. Second attempt receives **0/10**.
3. Each attempt must have its own `QUIZ_GRADING` and `QUIZ_QUESTION_GRADE` rows.
4. The **single `STUDENT_MARK` row must stay 10/10**, not get overwritten with zero.
5. A third attempt must be denied without creating an extra Oracle row.
6. Saving a response to a submitted attempt must be denied.
7. Neither attempt may expose grades or answer reviews while `ALLOW_MARK_VIEW=N` and `ALLOW_ANSWER_REVIEW=N`.

All application writes use authenticated API endpoints. The script connects to Oracle only for `SELECT` verification. It requires an exact confirmation before writes, and is locked to `http://127.0.0.1:8002` with `EDUSPHERE_OWNER` as the target schema. It **does not delete data**. Oracle login/auth may create audit entries as a side effect.

## Windows steps

Ensure the merged Django candidate is running on port **8002** with the main-database `.env` (`EDUSPHERE_APP` connected to `EDUSPHERE_OWNER`). Do not accidentally run another backend on port 8002.

In PowerShell, using the same activated `EduSphereVenv` and the `$backend` variable from earlier acceptance testing:

```powershell
python verify_main_connection.py --main-backend "$backend" --api
python -m unittest -v test_multiple_attempts_offline.py
python verify_main_multiple_attempts.py --main-backend "$backend"
```

Type exactly **`MAIN TWO ATTEMPT TEST DATA ONLY`** after inspecting the printed warning. Log in with the existing main QA **ADMIN**, an **INSTRUCTOR**, and the **STUDENT** who should take both attempts. Credentials are entered locally and not echoed.

At success, the test prints the new QA `tag`, `quiz`, `attempt1`, `attempt2`, `component` and `offering` identifiers. **Copy that final line** into your testing log, and paste the full console output back into ChatGPT. If a failure occurs after writes start, the partial fixture remains in `EDUSPHERE_OWNER`; do not rerun with the assumption the old records were rolled back.

## Limitations and safety

- The 10 offline tests verify the test runner's conditions and failure detection, not actual Oracle behavior.
- The new workflow is **not counted as a live pass** until the Windows/Oracle output confirms it.
- No database DDL, triggers, procedures or application source code has been changed.
- Consider a database backup before running another persistent test fixture.
- If the server is unreachable during the test, stop and inspect the API/Oracle errors instead of modifying real academic data.
- Testing two MCQ attempts is not comprehensive: manual long-text review, other question types, expiry/late writes, rollback, concurrent submissions, and frontend production build remain outstanding.
- **Promotion remains blocked** until at least 85% of planned acceptance tests pass **and all critical security/data-integrity checks pass**. Offline code tests alone cannot satisfy that gate.
