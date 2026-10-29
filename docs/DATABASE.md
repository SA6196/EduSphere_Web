# Oracle schema and SQL lifecycle

**Source of truth:** `Database/Schema_Fixed/01_create_tables.sql`. It defines exactly **37 tables**, unchanged from the tested application baseline. Oracle **21c XE / XEPDB1**, main owner `EDUSPHERE_OWNER`, runtime account `EDUSPHERE_APP`. The same layout can be installed into an *empty* disposable schema only after reviewing hard-coded guard conditions in installation/sample scripts; never run the fresh installer on existing course records.

## Domains (37 relations)

| Domain | Tables |
|---|---|
| Identity and academic (8) | `LMS_USER`, `DEPARTMENT`, `PROGRAM`, `SEMESTER`, `STUDENT`, `INSTRUCTOR`, `ADMIN`, `COURSE` |
| Delivery (7) | `COURSE_OFFERING`, `OFFERING_INSTRUCTOR`, `ENROLLMENT`, `COURSE_MATERIAL`, `ANNOUNCEMENT`, `CLASS_SESSION`, `ATTENDANCE` |
| Assessment (5) | `GRADING_SCHEME`, `ASSESSMENT_COMPONENT`, `ASSIGNMENT`, `ASSIGNMENT_SUBMISSION`, `EXAM` |
| Quiz core (7) | `QUESTION`, `QUESTION_OPTION`, `QUIZ`, `QUIZ_QUESTION`, `QUIZ_ATTEMPT`, `QUIZ_RESPONSE`, `QUIZ_RESPONSE_OPTION` |
| Automatic grading and review (6) | `QUESTION_NUMERIC_RULE`, `QUESTION_KEYWORD`, `QUIZ_RESPONSE_ORDER`, `QUIZ_RESPONSE_MATCH`, `QUIZ_GRADING`, `QUIZ_QUESTION_GRADE` |
| Results/audit (4) | `STUDENT_MARK`, `GRADE_SCALE`, `COURSE_GRADE`, `ACTIVITY_LOG` |

The provided SQL contains 37 PK, 56 FK, 29 named UNIQUE and 48 CHECK constraints (see the DDL itself for exact names), plus 5 SQL functions, 12 stored procedures, 3 cursor procedures and 40 trigger definitions. The expiry script replaces the required expiry objects; it does not change the table structure.

## Files and responsibilities

| File | Purpose |
|---|---|
| `Database/00_create_users_secure.sql` | Privileged setup of schema/runtime users; prompts for passwords |
| `Database/01_INSTALL_FRESH.sql` | **Destructive-risk context:** fresh-owner installation guarded against a nonempty owner; installs schema, routines, triggers, grants |
| `Database/02_VERIFY_FINAL_INSTALL.sql` | Read-only installation verification |
| `Database/Schema_Fixed/01_create_tables.sql` | Approved, immutable 37-table DDL |
| `02_functions.sql` | PL/SQL functions |
| `03_procedures.sql` | Business stored procedures |
| `04_cursor_procedures.sql` | Cursor/report routines |
| `05_triggers.sql` | Referential/business triggers, audit automation |
| `06_grants.sql`, `09_compliance_runtime_grants.sql` | Oracle runtime grants (development scope; review for production) |
| `08_finalize_expired_attempts.sql` | Quiz attempt timeout/finalization corrections |
| `Sample_Data/01_sample_catalog.sql` | Academic catalog and offerings |
| `Sample_Data/generate_demo_accounts.py` | Prompts for five distinct passwords; generates salted password-hash DML locally |
| `Sample_Data/03_sample_classes.sql` | Instructors/roster, assessments, attendance and quiz fixtures |
| `Sample_Data/04_VERIFY_SAMPLE_DATA.sql` | Read-only sample verification |

**Fresh development owner only:** in SQL*Plus from `Database/` as the verified owner in `XEPDB1`, `@01_INSTALL_FRESH.sql`. Before running any installer, inspect the script's owner/PDB/empty-schema guard and back up existing data. Use catalog → locally generated account SQL → sample classes → verification for optional sample data. Do not commit `02_accounts.generated.sql` or disclose generated password hashes.

For an **existing populated database**, install nothing: configure `Backend/.env` and verify `GET /api/db-health/` reports 37 expected/visible tables. The original unoptimized `EduSphere_Web` health check reported 31/31 because its Python manifest omitted six tables—not because the Oracle schema had only 31. The merged manifest correctly checks 37/37.

## Consistency rules

- All quiz attempt grades live in `QUIZ_GRADING` and per-question grades in `QUIZ_QUESTION_GRADE`.
- `STUDENT_MARK` carries the component mark; the verified multiple-attempt behavior keeps the **highest** eligible grade (10/10 then 0/10 still gives 10/10).
- Unreviewed long-text grading must not publish a component mark.
- Oracle SQL grants supplied for an academic environment may be too broad for a public service. Perform a separate privilege audit.
- This repository does not use `python manage.py migrate` to create or change the Oracle schema; `DATABASES` intentionally uses the dummy Django engine.
