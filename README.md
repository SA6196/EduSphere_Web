# EduSphere LMS

**An Oracle-backed learning management system built with Vue 3, Django REST Framework, and Oracle Database 21c XE.** The project includes student, instructor, and administrator portals; a normalized 37-table schema; quizzes and automated/manual grading; attendance; academic records; and database auditing.

**Repository baseline:** tested merged build based on `EduSphere_Web` plus targeted connection, query, frontend and quiz-security improvements (October 2026). The existing Oracle schema, stored routines and sample SQL are preserved. This is a course-project/demo-ready **release candidate**, not a publicly hosted service or a claim of a completed production security audit.

## Highlights

- **Student:** course enrollment, guarded course withdrawal (**Drop Course**), dashboard, attendance and projections, assessments, quiz attempts, semester marks and GPA.
- **Instructor:** assigned offerings, rosters, attendance, question bank, quiz creation and grading, materials, assignments and exam management.
- **Administrator:** accounts, academic structure, offerings, reports and grade workflows.
- **Assessment safeguards:** ownership/RBAC checks, attempted-question answer-key locks, hidden unreleased marks and answers across API routes, expired-attempt locks, best-score preservation and transactional grading.
- **Efficiency:** thread-local Oracle ODBC connection reuse with request cleanup; batched question-bank/matching lookups; frontend deduplication of simultaneous identical GET requests; optional four-thread Waitress server.
- **Fixed database design:** 37 Oracle tables with SQL constraints, stored functions/procedures, triggers and audit facilities. Django ORM migrations do **not** manage these tables.

**Course Drop extension (candidate):** See [docs/COURSE_DROP.md](docs/COURSE_DROP.md). The existing Oracle schema is unchanged. The new action still requires live Windows/Django/Oracle acceptance testing before deployment.

## Architecture

```text
Browser (Vue 3 / Vite)
       |
       | HTTP + JWT; never Oracle credentials in browser
       v
Django REST (authentication -> views -> services -> repositories)
       |
       | pyodbc / ODBC, parameterized SQL, explicit commit/rollback
       v
Oracle XE 21c (XEPDB1)
  EDUSPHERE_APP  ->  EDUSPHERE_OWNER (37 fixed tables)
```

## Repository layout

```text
Backend/            Django REST, Oracle repositories, tests/audits and Windows startup
Frontend/           Vue 3 SPA, styles, API client and Node smoke/unit tests
Database/           37-table DDL, PL/SQL, fresh installation and optional demo seed
Testing/            Offline verification, source/hash and staging API verification
qa/manual_acceptance/  Explicit-opt-in live Oracle test tools (NOT part of CI)
docs/               Architecture, setup, database, tests, security and deployment
.github/workflows/  GitHub Actions: database-free code and frontend checks
scripts/            Repository integrity and Python test utilities
```

## Requirements

- **Windows 10/11** for the documented local setup; Python **3.12+** with pip and a virtual environment.
- **Node.js 22+**, npm, and a compatible Oracle **ODBC driver + DSN**.
- **Oracle Database 21c XE**, `XEPDB1`, preconfigured `EDUSPHERE_OWNER` (schema owner) and `EDUSPHERE_APP` (runtime account). Existing working databases should **not** be reinstalled.
- Git is optional for running; no cloud service, `.env` or database passwords are bundled.

## Quick start with an existing Oracle database (PowerShell)

The examples use port `8002` because ports `8000`/`8003` may be occupied by other local apps. A working database needs no schema changes.

```powershell
# Backend
cd Backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
# Edit .env: ODBC_DSN, ODBC_USER, ODBC_PASSWORD, ORACLE_SCHEMA,
# DJANGO_SECRET_KEY, JWT_SECRET and CORS_ALLOWED_ORIGINS.
python manage.py check
python scripts\test_odbc.py
.\serve-windows.ps1 -Port 8002 -Threads 4
```

In another terminal:

```powershell
cd Frontend
Copy-Item .env.example .env.local
# In .env.local use VITE_API_BASE_URL=http://127.0.0.1:8002/api
npm ci
npm run dev
```

Open `http://localhost:5173` and sign in with a locally created account. No default passwords are included. Check the API at `http://127.0.0.1:8002/api/health/` and `http://127.0.0.1:8002/api/db-health/`; the merged health check expects **37/37 tables**.

> **Windows note:** If `py -3.12` is not available, use the installed Python executable that works in your environment. Activate the virtual environment before running the commands. Do not start the Django development server for load testing or internet exposure.

## New *empty* Oracle installation

Do this **only** if no EduSphere tables exist in the target owner. The fresh installer refuses a nonempty owner. The project does not use Django migrations to construct the schema.

1. See [database installation guide](docs/DATABASE.md) and `Database/README_INSTALL.md` for Oracle user creation and grants.
2. Connect to **XEPDB1** as the correct owner; run `Database/01_INSTALL_FRESH.sql` using SQL*Plus from inside `Database/`.
3. Optionally run the catalog sample, locally generate salted-hash demo-account SQL, then classroom sample SQL. Choose your own passwords; never commit the generated SQL.
4. Configure backend `.env` with the matching runtime account; verify all 37 tables.

## Verify code without an Oracle server

```powershell
python -m pip install pytest
python -m pytest -q Testing/test_merge_security.py Testing/test_optimized_database.py Testing/test_handoff_package.py Testing/test_api_verifier_offline.py Testing/test_question_bank_permissions_offline.py
python Testing/check_actual_scoring_cases.py
python Testing/audit_frontend_quiz_wiring.py --project-root .
cd Frontend
npm ci
npm run build
node frontend_smoke_check.mjs
node frontend_cross_role_smoke_check.mjs
node frontend_admin_management_smoke_check.mjs
node frontend_error_smoke_check.mjs
node --test attendance_predictor.test.mjs request_coalescing.test.mjs
```

The automated checks are also defined in [.github/workflows/ci.yml](.github/workflows/ci.yml). The Oracle-dependent acceptance scripts require an actual server, named accounts, explicit confirmation and **create permanent disposable QA records**. Never run them against a database you cannot modify. See [Testing](docs/TESTING.md).

## Latest test evidence and limits

- **Offline:** 63/63 Python checks, 13/13 scoring cases, 17/17 checked quiz API routes, frontend smoke suites and 20/20 frontend unit tests.
- **Windows build:** `npm ci` and Vite production build succeeded (80 modules, 1.25 seconds in the reported run).
- **Oracle XEPDB1:** live question bank isolation, result visibility combinations, multiple attempts and best score, instructor manual grading, atomic rollback, expiry and four-request concurrency scenarios passed.
- **API reliability:** the original/merged benchmark recorded 288/288 HTTP 200 responses across both versions. The instructor question-bank p95 improved on the measured local runs; not every endpoint improved.
- **Still to validate:** routine browser acceptance across all roles, public deployment configuration/security review, backup/restore exercise and Oracle `V$SESSION` metrics. The application account intentionally cannot query privileged Oracle session views.

These are **sampled test results**, not evidence of 100% coverage or a universal concurrency guarantee. See [Live acceptance record](docs/ACCEPTANCE_RESULTS.md) for fixture references and limitations.

## Documentation

| Guide | Use |
|---|---|
| [Architecture](docs/ARCHITECTURE.md) | Request flow and module responsibilities |
| [Database](docs/DATABASE.md) | Schema domains, SQL files, installation and constraints |
| [Local development](docs/DEVELOPMENT.md) | Environment, commands and troubleshooting |
| [Tests](docs/TESTING.md) | CI, offline checks and opt-in live tests |
| [Live acceptance](docs/ACCEPTANCE_RESULTS.md) | Observed tests, metrics and unfinished gates |
| [API route index](docs/API_ROUTES.md) | Django paths mapped to their source |
| [Source file index](docs/FILE_INDEX.md) | Searchable backend and frontend module reference |
| [Deployment](docs/DEPLOYMENT.md) | Server and reverse-proxy checklist |
| [Security policy](SECURITY.md) | Reporting and authorization principles |
| [Contributing](CONTRIBUTING.md) | PR workflow and schema-freeze rule |
| [Changelog](CHANGELOG.md) | Merge changes and documentation release |
| [Publish to GitHub](docs/PUBLISH_TO_GITHUB.md) | Git initialization and safe push steps |

Legacy `Backend/README_SETUP.md`, `Backend/edusphere/version.py` and `00_START_HERE_MERGED.md` have older release metadata and should **not** replace this README as the current status record. Code paths remain unmodified to preserve the tested baseline.

## License

No open-source license was supplied by the project owners. **Do not assume permission to reuse or redistribute this project** beyond authorized team/course use. Repository maintainers should choose a license before publishing openly; see `LICENSE_NOTICE.md`.
