# Architecture and source ownership

EduSphere has three explicit layers: Vue SPA, Django REST API, Oracle SQL. No frontend component can call the database directly. JWT authentication is implemented in `Backend/accounts`; role- and ownership-aware services are the main authorization boundary; Oracle constraints/triggers provide relational integrity but do not substitute for row-level API authorization.

## Django layering

| Folder | Role |
|---|---|
| `edusphere/` | Django settings, root URL configuration, WSGI/ASGI entrypoints; `version.py` carries older metadata |
| `accounts/` | JWT login/refresh, password handling, user profile and role authorization |
| `core/` | Response format, exceptions, validators, API health/version and audit helpers |
| `database/` | pyodbc sessions, transactions, request middleware, SQL helpers, Oracle schema qualification |
| `academics/` | Departments/programs/semesters, offerings, enrollments and student marks/visibility |
| `attendance/` | Sessions and attendance workflows |
| `quiz/` | Question bank, attempts, answer privacy, grading and instructor release |
| `assignments/`, `exams/` | Assessment content, scheduling, submissions |
| `materials/`, `announcements/` | Course workspace content |
| `administration/` | Administrative management and compliance workflows |
| `gpa/`, `reports/` | Derived academic outputs, dashboards and report-specific redaction |

For domain modules, `urls.py` connects `views.py` (HTTP/serialization) to `services.py` (authorization/business rules), then to `repository.py` (Oracle operations). Not all domains have all three files. Read the relevant service before adjusting a repository query; SQL constraints alone are insufficient to prevent data exposure.

## Data-access lifecycle

`database/connection.py` uses a per-worker-thread pyodbc connection and ODBC pooling. `database/middleware.py` provides a request read scope. `oracle_transaction()` controls commits/rollbacks for multi-statement writes; failed writes are not transparently retried because commit state may be uncertain. Optional age/idle recycling settings are in `Backend/.env.example`.

Bounded fixed worker threads (e.g. Waitress four threads) improve connection reuse. This does **not** guarantee four total Oracle sessions if other applications/processes use the same Oracle account. Capture privileged `V$SESSION` separately to validate actual session counts.

## Frontend layout

| Folder | Role |
|---|---|
| `src/router/` | Routes and role navigation |
| `src/stores/auth.js` | Login state in the browser |
| `src/services/http.js` | Authenticated HTTP requests, refresh, timeout and GET coalescing |
| `src/services/api.js` | API endpoint wrappers consumed by views/components |
| `src/views/student/` | Student quiz, attendance, marks and dashboard |
| `src/views/instructor/` | Instructor dashboard, question bank, grading |
| `src/views/admin/` | Admin management and reports |
| `src/components/workspace/` | Offering workspace tabs with module-specific views |
| `src/utils/attendancePredictor.js` | Pure client-side attendance projections (no database writes) |

## High-risk change boundaries

- Quiz submission must not serialize unreleased scores; only the authorized result endpoint may expose marks.
- Correct answers must remain hidden unless `ALLOW_MARK_VIEW=Y`, `ALLOW_ANSWER_REVIEW=Y` and the review is eligible; the instructor question-bank has separate access rules.
- Attempt ownership and enrollment/teaching assignment are checked in backend services; a caller-controlled ID alone is never authorization.
- `STUDENT_MARK` is an assessment-component result, not an attempt-history substitute. Synchronization preserves the best valid attempt.
- `LONG_TEXT` must be reviewed before publication; invalid rubric/marks changes must not partially persist.
- Do not change the Oracle 37-table structure to implement frontend features. Add regressions for every access-control or transaction change.
