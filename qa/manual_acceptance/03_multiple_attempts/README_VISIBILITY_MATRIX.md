# Next live security gate — test released/unreleased marks and answer review

The prior live main-database checks **passed** for 37 visible tables, 9/9 question-bank permissions, the correct 10/10 MCQ grade persisted to all three grading/marks relations, question locking, cross-user isolation, and hidden results. The next untested dimension is **the publication policy once an instructor changes visibility controls**.

## Scope and safety

The `verify_main_visibility_matrix.py` verifier targets **only** the original disposable fixture (`quiz=104`, `attempt=166`, QA tag `E7808E9C43`) in **EDUSPHERE_OWNER**. The main Django candidate **must** run on `127.0.0.1:8002`. It uses the strict existing `verify_main_connection.py` preflight and checks the original quiz/course/question markers directly in Oracle before touching any data. It is not a general-purpose updater and it does not create any new academic, quiz, or grading rows.

It uses the instructor REST API to try **N/N**, **N/Y**, **Y/N**, **Y/Y** for `(ALLOW_MARK_VIEW, ALLOW_ANSWER_REVIEW)`. Before any change it asks for the exact confirmation `MAIN VISIBILITY MATRIX TEST`. It checks unauthorized instructor/student/anonymous PATCH requests first. The script checks the owning student and a different student, the quiz result, the answer review, attempts history, and (when marks are hidden) both marks endpoints. It never prints passwords or answer keys.

**After running, it attempts to restore the original Oracle visibility values in `finally`, and checks the actual persisted flags and resultant student visibility.** Login and flag updates may create audit events. If Windows is terminated or the server becomes unreachable midway, *automatic restoration is not guaranteed*. The terminal will print the original values at the beginning. In that case, restore them via the assigned instructor's visibility control after restoring service and confirm via Oracle `SELECT`. For the previous test these were N/N, but the script reads the values afresh.

## Run in Windows PowerShell

Keep the merged Django backend running on port 8002 in a separate console. Use the same PowerShell session where `$backend` points to the merged candidate's `Backend` folder:

```powershell
cd "C:\Users\hamza\Downloads\EduSphere_Main_DB_Merged_Acceptance_Tests"
python verify_main_visibility_matrix.py --main-backend "$backend"
```

The script prompts for:
- An assigned instructor (`FINAL_I2` from the prior test)
- An unassigned instructor (`FINAL_I3`)
- The owning student (`FINAL_S6`)
- Another student (`FINAL_S2`)

It collects passwords interactively, then executes its full visibility matrix. Do not rerun the earlier lifecycle script with `--resume-tag E7808E9C43`: attempt 166 is already submitted; no new attempt is needed here.

## Expected main-result matrix

| Mark visibility | Answer review | Owning student's result | Owning student's answer review |
|---|---|---|---|
| N | N | 403 | 403 |
| N | Y | 403 | 403 |
| Y | N | 200, 10/10 | 403 |
| Y | Y | 200, 10/10 | 200, since the fixture had one allowed attempt and it is submitted |

**Independent condition:** The other student must receive 403 for both attempt-specific endpoints in **every** row. Unassigned instructor/student/anonymous visibility changes must receive 403/403/401 respectively. Any mismatch is a **critical failure** regardless of the 85% overall threshold.

## After visibility gate

The following integration areas still require separate checks: manual LONG_TEXT pending → review → publish, the remaining seven question types, multiple-attempt best mark, expired attempt and late-answer write rejection, rollback under a forced Oracle write failure, browser UI path and Windows production build, plus before/after Oracle session count and p95 latency benchmarking. The 85% threshold is for the entire agreed live test plan, with **no critical authorization or grading failures**. Passing this visibility matrix does not by itself constitute production approval.
