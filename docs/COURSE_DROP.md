# Course Drop (frontend + backend candidate)

Source baseline: `EduSphere_LMS_GitHub_Ready_2026-10-18.zip` (the source available to this session). This feature has **not** been applied to the user's local `C:\Users\hamza\Downloads\EduSphere_DB` directory.

## User flow

Student → Course Catalog → an **ENROLLED** offering that is **OPEN** → **Drop Course** → confirmation → updated **Withdrawn** badge. The backend does not accept a user-supplied student ID: ownership comes only from the authenticated JWT principal.

The action is a **logical withdrawal**, not SQL DELETE. It changes `ENROLLMENT.ENROLLMENT_STATUS` from `ENROLLED` to `DROPPED`, retains the existing enrollment ID and history, and logs `ENROLLMENT_DROPPED` with `PR_LOG_ACTIVITY` in the same Oracle transaction.

Endpoint: `POST /api/enrollments/<offering_id>/drop/` (student role only).

## Withdrawal policy

- Only the owning student, on an `OPEN` offering with status `ENROLLED`.
- Block once **any** attendance, assignment submission, quiz attempt, component mark or published course grade exists. This avoids orphaned/hidden grading and assessment states.
- Repeated withdrawals, completed enrollments and CLOSED offerings are rejected.
- `DROPPED` enrollments do **not** count toward active seat capacity (existing count predicates already handle this).
- Unique `(Student_ID, Offering_ID)` means re-enrollment after `DROPPED` remains unavailable without a separate, reviewed reinstatement workflow. The frontend displays **Withdrawn**, not Enroll.
- No DDL, table changes, triggers or procedures have been changed.

## Tests completed in offline packaging environment

- `python -m unittest discover -s Testing -p test_course_drop_backend.py -v`: 16/16 mocked repository/service/API-wiring tests.
- `node --test course_drop.test.mjs`: 7/7 frontend/static/JS-syntax tests (run from Frontend).
- All 43 `.vue` components compiled using `@vue/compiler-sfc` borrowed temporarily from the user's previously uploaded application package; the dependency was **not included** in this ZIP.
- Existing 4 Node smoke suites, 20 predictor/request tests, 13 grading examples and 17 Vue/API route mappings passed.
- Python syntax compilation passed.

**Not yet verified:** live Oracle transaction behavior, Django REST endpoint against your local Windows environment, and a fresh Vite production bundle. External Django and npm dependencies could not be fetched from this offline environment. Do not promote until those checks and a real student UI click test pass.

## Local verification on Windows

After making a backup of the currently used project and copying the patch into the matching baseline:

```powershell
cd Backend
python manage.py check
cd ..\Frontend
npm ci
npm run build
node --test course_drop.test.mjs
```

Use an existing **empty, active test enrollment** in an `OPEN` offering: drop once, observe **Withdrawn** and confirm a second drop is refused. Also test another student's offering and an enrollment with existing quiz/attendance; each must be rejected. Keep prior tested quiz fixtures untouched.

## Changed source

- `Backend/academics/{repository,services,views,urls}.py`
- `Backend/core/constants.py`
- `Frontend/src/services/api.js`
- `Frontend/src/views/CatalogView.vue`
- New regression tests: `Testing/test_course_drop_backend.py`, `Frontend/course_drop.test.mjs`.
