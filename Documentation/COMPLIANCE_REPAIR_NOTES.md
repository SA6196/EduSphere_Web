# EduSphere LMS — Backend and Frontend Compliance Repair

**Basis:** `final review 1.pdf`, fixed 37-table Oracle schema. This bundle builds upon `EduSphere_Attendance_Graphs_Predictor_Fixed.zip`. The nine original SQL files in `Fresh_Database_Install/` are unchanged. The new deployment scripts change existing Oracle *procedural objects/privileges*, **not** the table schema.

## Changes implemented

### Quiz integrity and student frontend

- Student responses can be **saved and replaced atomically** before the Oracle deadline. A parent-attempt row lock protects response updates from concurrent submission. The student client autosaves changes and restores saved selections after refresh; ordering/matching remain opaque and randomized.
- On timeout, the frontend submits only answers already saved to Oracle. The **new existing-object replacement SQL** lets an expired attempt be finalized while Oracle response triggers still prohibit changing answers after their deadline.
- Existing/saved ordering responses remain editable until submission/expiry, including after autosave.
- All response endpoints check ownership and submission state; invalid option IDs, matching-side errors, and repeated selected options are rejected.
- Question-bank reads are scoped to authored questions or offerings assigned to the instructor. Edits are limited to unused questions; **instructors and administrators are blocked from modifying answer keys and adding questions after any related attempt**. Unknown legacy authorship is restricted to admins for review.
- Question creation avoids guessing `MAX(QUESTION_ID)` across concurrent instructors. It uses an unguessable temporary CLOB marker to identify the inserted row within one transaction.
- Students only receive answer review when configured and after a quiz has closed or attempts are exhausted, and long-text auto-graded provisional results remain hidden.

### Instructor grading

- Individual `LONG_TEXT` responses and question-level marks are displayed in the instructor review interface.
- Instructor enters a mark within that question's maximum and rubric feedback. The final quiz total is computed from individual question grades; inconsistent header totals are rejected.
- Question marks, grade header, and course component best-attempt reconciliation execute atomically via existing tables.
- Instructor-owned offering workspaces expose grading scheme controls subject to ownership checks.

### Administration, accounts, attendance

- Admin can create/edit `PROGRAM`, `COURSE`, `SEMESTER` master data and view searchable `ACTIVITY_LOG` activity and rule-based alerts for ungraded attempts/pending essay review; no new alert table.
- Student self-registration creates **INACTIVE** LMS_USER and STUDENT rows. Admin manually verifies and activates the record; signup itself grants no privileged access. Signup is rate-limited at the Django API level.
- Attendance chart displays the official result of `FN_ATTENDANCE_PCT` (Oracle counts PRESENT+LATE over all recorded statuses). Predictor controls are separately labeled hypothetical. Default late/excused planning assumptions reflect the official formula; students can simulate alternative policies without writing Oracle data.

## Oracle deployment — REQUIRED for timeout support and restricted runtime users

1. **Back up** the database and test on a staging schema with a sample quiz before production. Stop the Django server for deployment.
2. Sign into the **existing `EDUSPHERE_OWNER` Oracle account in XEPDB1**, not EDUSPHERE_APP or `CDB$ROOT`.
3. Execute in this order:

   ```sql
   @Deployment_Security/17_finalize_expired_attempts_no_table_changes.sql
   @Deployment_Security/20_compliance_repair_runtime_grants.sql
   ```

   For SQL*Plus, run from the extracted project's root or use absolute Windows file paths in `@` commands. The first script uses `CREATE OR REPLACE` for **only** `PR_SUBMIT_QUIZ_ATTEMPT` and `TRG_QUIZ_ATTEMPT`, preserving Oracle-side locks on expired or submitted *responses*. The second grants only the relevant runtime DML and function execution permissions. Neither has a `CREATE TABLE`, `ALTER TABLE` or `DROP TABLE` statement.
4. Check compiled Oracle objects, including invalid/error status:

   ```sql
   SELECT OBJECT_NAME, OBJECT_TYPE, STATUS
   FROM USER_OBJECTS
   WHERE OBJECT_NAME IN ('PR_SUBMIT_QUIZ_ATTEMPT', 'TRG_QUIZ_ATTEMPT');

   SELECT NAME, TYPE, LINE, TEXT
   FROM USER_ERRORS
   WHERE NAME IN ('PR_SUBMIT_QUIZ_ATTEMPT', 'TRG_QUIZ_ATTEMPT');
   ```

5. Restart Django using the existing Oracle ODBC connection and run the backend check/test commands below.

**Important:** Do not rerun the fresh-install scripts against your live database. The SQL grant delta extends the permissions of the shared Django runtime Oracle user; ensure that the app's role-based API access and database credentials remain protected. No student or historical grading record is automatically rewritten by deployment.

## Run backend on Windows

From the `EduSphere_Django_Backend_V1_1_Module2_student_identity_fix_v4_capacity_fix` folder, with the existing `EduSphereVenv` activated and ODBC configured:

```powershell
pip install -r requirements.txt
python manage.py check
python manage.py runserver
```

The current execution sandbox does **not** have Django installed or your Oracle ODBC database; `manage.py check`, live endpoints and SQL compilation were **not** executed here. Check Oracle grants in the actual database before testing new admin and signup functions.

## Run frontend

From `EduSphere_Frontend`:

```powershell
npm ci
npm run build
npm run dev
```

The frontend bundle cannot be production-built offline here because Node package dependencies were not cached. All 43 extracted Vue script blocks passed `node --check`; the older smoke tests also pass, except for one **preexisting stale admin class-form label** assertion.

## Tests performed offline

```powershell
# From project root (pytest must be installed)
python -m pytest -q tests test_priority_1_2.py test_semester_and_question_types.py test_vtop_semester_markbook.py

# From EduSphere_Frontend
node --test attendance_predictor.test.mjs
node frontend_smoke_check.mjs
node frontend_cross_role_smoke_check.mjs
node frontend_error_smoke_check.mjs
```

- 50 Python offline/unit/static regression checks passed (including 13 new security, review, signup, and schema checks).
- 16 JavaScript predictor checks passed.
- 43 Vue script blocks passed static JavaScript syntax checks.
- Nine original `Fresh_Database_Install/*.sql` files were compared byte-for-byte with the input project; all nine match.
- **Not verified:** live Oracle DML/trigger/procedure execution, full Django startup, production Vue build, and browser-level end-to-end tests.

## Live acceptance checklist

1. As a student, start a timed quiz, save and change an MCQ and ordering answer, refresh, verify saved answers reappear, and submit. Confirm further edits are denied.
2. Let a timed quiz expire; verify unsaved changes are rejected and existing saved answers can be finalized. Check `QUIZ_ATTEMPT.SUBMITTED_AT` and `QUIZ_GRADING` and their totals.
3. Try instructor B accessing instructor A's unshared question bank and offering; expect denied. Verify both instructor and admin cannot alter a question after attempts exist.
4. Submit a quiz containing long text. Student must see **pending**, not an auto-graded zero as final. Instructor reviews each long-text answer with feedback, and student can see results only when released/configured.
5. Submit multiple attempts and check each `QUIZ_GRADING` score and the highest eligible `STUDENT_MARK` aggregate, including manual review increases.
6. As admin create/update a program/course/semester, approve an inactive signup and inspect audit alerts. Confirm student cannot approve themself.
7. Check recorded attendance's official Oracle rate against Attendance page, then change predictor assumptions and confirm official rate stays constant.

## Known remaining policy/data decisions

- Historical audit: attempt **106** was missing a `QUIZ_GRADING` record and **19** records had quiz-vs-component maximum discrepancies. This repair does not fabricate past grades, rescale marks or change the approved schema. Reconcile only after review and backups.
- `FILL_BLANK` uses ordered per-token matching but awards all-or-nothing marks; the final-review PDF does not unambiguously mandate partial credit. Decide with the course instructor before changing existing grading policy.
- The long-text rubric is instructor-entered question-level feedback, **not** a structured rubric-definition system (no new schema tables allowed).
- Audit **alerts are currently computed on demand** for the administrator, not pushed as emails or persisted as an additional alert entity.
- Historical legacy questions without recorded author ownership may require administrator reassignment/recreation to become instructor-editable.
- A safe submission flow depends on the two Oracle object changes above; installing only the Python/JavaScript code will leave timeout behavior broken.

## Tracked important files

Backend: `quiz/services.py`, `quiz/repository.py`, `quiz/auto_grader.py`, `quiz/views.py`, `accounts/registration.py`, `accounts/views.py`, `administration/compliance.py`, `administration/compliance_views.py`, `administration/services.py`, `administration/views.py`, `administration/urls.py`, `attendance/repository.py`, `database/connection.py` (previous transaction support retained).

Frontend: `src/views/student/QuizAttemptView.vue`, `src/views/instructor/QuizGradingView.vue`, `src/components/workspace/WorkspaceSchemeEditorTab.vue`, `src/views/OfferingWorkspaceView.vue`, `src/views/admin/AdminManagementView.vue`, `src/views/SignupView.vue`, `src/components/AttendanceAnalytics.vue`, `src/router/index.js`, `src/services/api.js`.

Deployment: `Deployment_Security/17_finalize_expired_attempts_no_table_changes.sql`, `Deployment_Security/20_compliance_repair_runtime_grants.sql`.
