# EduSphere · Tester's Handoff Package

**Contents:** the repaired Django REST backend, Vue 3/Vite frontend, the approved **37-table** Oracle schema, PL/SQL procedures and triggers, a fresh-install guide, safe sample data, and API testing utilities.

This is a **development/testing handoff**, not a ready-to-deploy public production service. Source code and demo fixtures are included; no real user database, Oracle credentials, `.env`, JWT keys, or generated passwords are included.

## Folder guide

| Folder | Purpose |
|---|---|
| `Backend/` | Django REST API (run `manage.py`) and `requirements.txt` |
| `Frontend/` | Vue 3 / Vite client, `package.json`, component smoke tests |
| `Database/` | New empty Oracle schema installer, fixed 37-table SQL, and sample records |
| `Database/Sample_Data/` | Three-stage academic/demo seed; local password-hash generator |
| `Testing/` | Read-only and *staging-only* security/API verification scripts |
| `Documentation/` | Final-review schema PDF and implementation reference |

## Suggested first-run workflow (Windows + Oracle XE XEPDB1)

1. Install Python 3.12 (or compatible 3.10+), Node.js 20+, Oracle XE 21c, and a matching **64-bit Oracle ODBC driver**. Configure a Windows System/User DSN pointing at XEPDB1 (for example `EduSphereOracle`).
2. **In a fresh Oracle PDB/schema only:** connect as `SYSTEM@//localhost:1521/XEPDB1` and run `Database/00_create_users_secure.sql`. The installer prompts for **two new distinct Oracle passwords** for `EDUSPHERE_OWNER` and `EDUSPHERE_APP`.
3. Connect as `EDUSPHERE_OWNER@//localhost:1521/XEPDB1`; from `Database/`, run `@01_INSTALL_FRESH.sql`. It refuses to run if the owner already has tables. This installs **37 tables**, all bundled stored functions/procedures/triggers, final expiry handling and application grants. Unlike older installers, it intentionally **does not seed a known-password admin**.
4. Still as owner, `cd Database/Sample_Data` in your command shell. Run `@01_sample_catalog.sql` from SQL*Plus, then generate account SQL locally via `python generate_demo_accounts.py`, then run `@02_accounts.generated.sql`, `@03_sample_classes.sql`, and `@04_VERIFY_SAMPLE_DATA.sql` (details below).
5. Create `Backend/.env` from `Backend/.env.example`, supply the DSN, **your new `EDUSPHERE_APP` password**, and two random Django/JWT secrets. Configure `Frontend/.env` from its `.env.example`.
6. In `Backend/`: `python -m venv .venv`; activate it; `pip install -r requirements.txt`; `python manage.py check`; `python manage.py runserver 127.0.0.1:8000`.
7. In `Frontend/`: `npm ci`; `npm run build`; `npm run dev`. Open `http://localhost:5173` and log in with the locally generated **DEMO** users.

> Never run `Database/01_INSTALL_FRESH.sql` or its sample-data scripts against an existing EduSphere database. The package is designed for an empty, disposable development environment. It does **not** upgrade your current database. Do not expose Django's development server outside localhost.

## Sample-data installation in SQL*Plus

Run from the `Database/Sample_Data/` directory (each `@` path is relative to your SQL*Plus working directory):

```powershell
# First run after installing 37 tables, while the terminal is in Database/Sample_Data
python generate_demo_accounts.py
sqlplus EDUSPHERE_OWNER@//localhost:1521/XEPDB1
```

```sql
@01_sample_catalog.sql
@02_accounts.generated.sql
@03_sample_classes.sql
@04_VERIFY_SAMPLE_DATA.sql
```

**The generated file is private to the tester**: it contains salted PBKDF2-SHA256 password hashes, not plaintext. Write down the passwords as you choose them; there is no default password. Do not email the generated SQL or a populated `.env` to others. To onboard another tester, give them a fresh copy of this ZIP so they can generate their own credentials.

### Sample logins (passwords chosen by the recipient)

| Username | Role | Demo use |
|---|---|---|
| `DEMO_ADMIN` | Admin | User approvals, academic records, instructor assignments and audit view |
| `DEMO_INSTRUCTOR_A` | Instructor | DBMS offerings, quiz and marks, attendance |
| `DEMO_INSTRUCTOR_B` | Instructor | Machine Learning and future Networks offerings |
| `DEMO_STUDENT_A` | Student | Enrolled in DBMS & ML (current) and a prior semester; attendance/grades |
| `DEMO_STUDENT_B` | Student | Enrolled in DBMS; attendance and quiz attempts |

### Demo content

Three academic semesters (2025–26 Fall; 2026–27 Fall; 2026–27 Winter), three courses, four offerings, two instructors, two students, seven attendance records, seven assessment components, four exam schedules, two assignments, one 10-mark MCQ/true-false quiz, and one historical exam mark. The quiz is intended to be **attempted by the tester**, not pre-submitted. All course descriptions and account names are fictitious.

## Test checklist

- Admin login works; browse the course catalog, create an offering, view the account directory and audit view.
- Instructor A sees DBMS, creates and manages a question/quiz; Instructor B should be denied access to Instructor A's exclusive question.
- Student A selects Fall 2025–26 vs Fall 2026–27 on **Performance** and **Attendance**, sees course-wise marks/attendance and the attendance predictor.
- Student A starts the seeded DBMS quiz, selects answers, saves and submits. Verify instructor grading list and per-attempt score. Repeat the attempt to verify best-attempt policy.
- Use `Testing/verify_question_bank_live.py` for read-only permission verification with two distinct instructors. The staging write scripts are **not intended for the seeded owner**: use only with a separate `EDUSPHERE_STAGE_OWNER` installation, verified on port 8001.

## Important limitations

- SQL installation and end-to-end Oracle testing were **not executed on the recipient's machine**. Recheck status with `Database/02_VERIFY_FINAL_INSTALL.sql` and inspect any `USER_ERRORS` before attempting quizzes.
- The inherited `06_grants.sql` gives the runtime database user broad table privileges for development compatibility. Django roles enforce per-user access; Oracle does **not** provide per-instructor row-level security in this build. Do not present it as production-hardened.
- Backend code still uses the fixed owner name `EDUSPHERE_OWNER` for two quiz procedures. This tester install intentionally uses that owner; staging/custom-owner setups require the separate patched staging workflow.
- Quiz/manual-grading and full browser behavior still need human acceptance testing; static/offline tests do not establish complete correctness in every case.
- Do not run `django manage.py migrate`: project tables are supplied by Oracle SQL rather than Django ORM migrations.
- The sample semester dates are fixed to the 2026–27 demonstration period. Once outside that period, update **sample data dates** (not schema) before attempting the quiz.
