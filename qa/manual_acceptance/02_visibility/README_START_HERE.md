# EduSphere merged candidate — MAIN Oracle test database acceptance

This package is **only verification code**. It does not install, alter or migrate the fixed 37-table SQL design. It targets the **merged candidate** from `EduSphere_Web_Optimized_Secure_Merge_STAGING_CANDIDATE.zip`, connected to your `EDUSPHERE_OWNER` test schema in Oracle XEPDB1. Do **not** run the earlier staging-only scripts on the main schema, and do not run the fresh database installer over this schema.

## What is different about this main-database run?

- Your application data is disposable, so you authorized integration writes against `EDUSPHERE_OWNER`.
- Existing application and main database remain in place. The **candidate source** runs as a separate Django process on **127.0.0.1:8002**, rather than replacing your known-good backend on 8000.
- Controlled write test creates a unique `QA<10hex>` course and semester, an offering, a quiz, question/options, enrollment and a submitted attempt. **Records remain afterward**. It does not drop, truncate, recreate or migrate tables or modify existing questions/grades. Authenticated requests may add audit records.
- `verify_main_connection.py` and `verify_main_question_bank_reads.py` perform **no quiz / mark write operations** (login may update audit records).
- A fail-fast assertion means a real test failure. **Do not count skipped tests as passing.** Security/grade leaks and failed transactions block promotion even if >=85% of checks pass.

## 0. Backup first

Take and verify a backup of the current `EDUSPHERE_OWNER` schema (for example, using a properly provisioned Oracle Data Pump export) and record the working application's location. Avoid running writes while the original port 8000 process is serving other users. Keep a copy of the currently working backend and `.env`.

## 1. Extract the candidate separately

Extract the already provided merged-candidate ZIP to a **new folder** (for example `C:\EduSphere_Merged_Test`); do not overwrite the original EduSphere_Web installation. The backend folder is `...\EduSphere_Merged_Candidate\Backend`.

In your existing PowerShell `EduSphereVenv`, copy your local main database `.env` **only** into this separate candidate's `Backend\.env`. Verify these values, without sharing the file:

```dotenv
ODBC_DSN=EduSphereOracle
ODBC_USER=EDUSPHERE_APP
ODBC_PASSWORD=<your-existing-Oracle-app-password>
ODBC_CONNECTION_STRING=
ORACLE_SCHEMA=EDUSPHERE_OWNER
ALLOWED_HOSTS=127.0.0.1,localhost
```

Use different random `DJANGO_SECRET_KEY` and `JWT_SECRET` in the candidate to isolate test login tokens. No account passwords are bundled in this package. If PowerShell overrides `ODBC_*` or `ORACLE_SCHEMA`, clear those environment variables first.

## 2. Read-only Oracle preflight (before starting Django)

Run these from the extracted **test package** directory (with your virtual environment activated), replacing the backend path:

```powershell
python verify_main_connection.py --main-backend "C:\EduSphere_Merged_Test\EduSphere_Merged_Candidate\Backend"
```

Expected: Oracle user `EDUSPHERE_APP`, PDB `XEPDB1`, 37 main owner tables, two VALID quiz procedures, **PASS**. If any value differs, stop.

## 3. Start the merged candidate on port 8002

Open **another** activated PowerShell terminal:

```powershell
cd "C:\EduSphere_Merged_Test\EduSphere_Merged_Candidate\Backend"
python manage.py check
python manage.py runserver 127.0.0.1:8002 --noreload
```

Keep that terminal open. With the test tools folder as your working directory, run:

```powershell
python verify_main_connection.py --main-backend "C:\EduSphere_Merged_Test\EduSphere_Merged_Candidate\Backend" --api
```

Expected public health check: owner `EDUSPHERE_OWNER`, `expected_tables=37`, `visible_tables=37`, status `ok`. Avoid starting the frontend during these API-only acceptance tests.

## 4. Read-only authorization checks

```powershell
python verify_main_question_bank_reads.py --main-backend "C:\EduSphere_Merged_Test\EduSphere_Merged_Candidate\Backend"
```

Use your existing main test users, for example `FINAL_I2`, `FINAL_I3`, `FINAL_ADMIN`, and `FINAL_S6`. Enter passwords locally. Expect both directions of instructor isolation, student 403s and admin full reads.

## 5. Controlled main-schema API lifecycle + grade/response privacy test

**Only run after backup and successful preflight, on the candidate server at port 8002.** This WILL create disposable records in `EDUSPHERE_OWNER`:

```powershell
python verify_main_api_quiz_lifecycle.py --main-backend "C:\EduSphere_Merged_Test\EduSphere_Merged_Candidate\Backend"
```

At the prompt, confirm precisely `MAIN EDUSPHERE TEST DATA ONLY`. Log in as a main test admin, instructor A, instructor B, and student. You can optionally log in as a second student to test attempt-level cross-user access. All four primary roles are required for the lifecycle.

It checks quiz/course creation and enrollment, both sides of question locking, student-safe quiz content, POST answer save and submit, grade write to `QUIZ_GRADING`, `QUIZ_QUESTION_GRADE`, `STUDENT_MARK` (expected 10/10), blocked unreleased result/review, redacted attempt history, general marks, semester markbook, and dashboard percentages. It **explicitly sets visibility N/N for the new quiz** and leaves it hidden. No existing quiz visibility is changed.

If it fails **before** an attempt was started, the script prints a 10-character `Test identifier`. You can retry only that fixture with:

```powershell
python verify_main_api_quiz_lifecycle.py --main-backend "C:\EduSphere_Merged_Test\EduSphere_Merged_Candidate\Backend" --resume-tag YOUR10HEX
```

Resume mode refuses to duplicate a started attempt. If the fixture has already been attempted, inspect existing data instead of retrying it blindly. The script never automatically deletes data.

## 6. Windows frontend production build (code smoke, optional after API checks)

```powershell
cd "C:\EduSphere_Merged_Test\EduSphere_Merged_Candidate\Frontend"
npm ci
npm run build
```

The frontend should later point to `http://127.0.0.1:8002/api`, not the original port 8000, for browser-level checks. A production build alone does not demonstrate secure backend enforcement.

## 7. Promotion policy

Offline checks previously passed 13/13 planned change groups, but **live checks have not been run by this assistant**. Require >=85% of planned integration cases passed *and* 100% of critical authorization, unreleased-mark confidentiality, rollback/grade consistency and core submission cases passed. A failed critical test blocks promotion. Do not replace the original app automatically. Benchmark the merged build under Waitress and compare response time / Oracle session counts before declaring a performance gain.

## Troubleshooting

- `ModuleNotFoundError: dotenv` / `pyodbc` → activate your `EduSphereVenv`.
- `IM002` → use the actual Windows DSN **`EduSphereOracle`** (not `YOUR_ODBC_DSN`).
- `HTTP 405` → attempt start and submit use **POST**, not GET; the main lifecycle script uses POST.
- `403` on instructor quiz creation → check offering assignment and role; the script creates its own offering for instructor A.
- `Could not reach port 8002` → start the candidate backend on that port, not 8000/8001.
- `ORA-00942` or health missing tables → check candidate `.env`, grants, correct connection and 37-table owner before any writes.
- `RETRY_REQUIRED` grading status → capture the Django traceback *without credentials*; do not assume grades persisted. Our grade assertion is designed to fail safely in that case.
