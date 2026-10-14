# EduSphere Django Backend - Current Final Hardened State

Current package date: **2026-09-26**.

This backend is the application layer for the current EduSphere Oracle database in `XEPDB1`.

## Architecture

```text
Vue / Postman / PowerShell
          | HTTP JSON + JWT
          v
Django REST Framework
          | pyodbc / ODBC
          v
EDUSPHERE_APP
          | least-privilege SELECT/DML/EXECUTE
          v
EDUSPHERE_OWNER schema in XEPDB1
```

The Oracle LMS schema has 31 base tables. Django does **not** recreate them with migrations.

## Current modules

- JWT authentication and role permissions
- academics / courses / offerings / enrollment
- assignments and submissions
- attendance
- quizzes, questions, options, attempts, submission and visibility controls
- materials
- announcements
- exam scheduling
- marks and grade publication
- GPA / SGPA / CGPA verification
- admin reports
- audit logging through `PR_LOG_ACTIVITY`

## Current database requirements

- Oracle 21c XE PDB: `XEPDB1`
- owner: `EDUSPHERE_OWNER`
- runtime: `EDUSPHERE_APP`
- V6 columns: `QUIZ.ALLOW_MARK_VIEW`, `QUIZ.ALLOW_ANSWER_REVIEW`

For a current database package, see the parent project's `Database/`, `Deployment_Security/`, and `Final_Audit/` folders.

## Configure `.env`

Set at minimum:

```text
ORACLE_SCHEMA=EDUSPHERE_OWNER
ODBC_DSN=EduSphereOracle
ODBC_USER=EDUSPHERE_APP
ODBC_PASSWORD=<runtime-password>
DJANGO_SECRET_KEY=<secret>
JWT_SECRET=<secret>
```

Do not commit real secrets.

## Start

```powershell
.venv\Scripts\activate
python scripts\test_odbc.py
python manage.py check
python manage.py runserver
```

## Authentication

```http
POST /api/auth/login/
Content-Type: application/json

{
  "username": "FINAL_S7",
  "password": "<password>"
}
```

Use the returned access token as:

```http
Authorization: Bearer <access-token>
```

Full token/API documentation:

- `EduSphere_Django_Backend_API_Guide.docx`
- `EDUSPHERE_DJANGO_API_GUIDE.md`
- `EduSphere_API_Quickstart.ps1`

## Final verified status

- `python manage.py check`: PASS
- static final code audit: PASS
- no direct Django `ACTIVITY_LOG` inserts
- runtime privilege/audit verification: PASS
- final live API regression: **19 PASS / 0 FAIL**
- rejected hardening writes: **0 bad rows / 0 false success audits**
- HTTP semantics: `401` auth, `403` permission, `404` missing resource, `400` validation/duplicate
