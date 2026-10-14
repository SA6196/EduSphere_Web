# EduSphere Django Backend API Guide

**Version date:** 26 September 2026  
**Backend state:** Final hardened and regression-verified  
**Local base URL:** `http://127.0.0.1:8000`

This guide documents the current hardened EduSphere Django REST backend, including JWT token creation/refresh, role-based API access, endpoint reference, common payloads, PowerShell/cURL usage, error semantics, and the verified Student/Instructor/Admin workflows.

## 1. Architecture

```text
Client (Vue / Postman / PowerShell / curl)
        | HTTP + JSON + Bearer JWT
        v
Django REST Framework
        | pyodbc / ODBC
        v
EDUSPHERE_APP (restricted Oracle runtime user)
        | SELECT / EXECUTE / required repository DML
        v
EDUSPHERE_OWNER schema in XEPDB1
```

The client never connects directly to Oracle. Django is the API/application layer; Oracle remains the authoritative relational/integrity layer. The LMS schema is not recreated with Django migrations.

## 2. Start the backend

```powershell
cd "<path-to-extracted-package>\Backend"
.\.venv\Scripts\Activate.ps1
python scripts\test_odbc.py
python manage.py check
python manage.py runserver
```

Public checks:

- `GET /api/health/`
- `GET /api/db-health/`
- `GET /api/version/`

## 3. JWT authentication and token lifecycle

The backend issues two JWTs after a successful login:

- **Access token:** default lifetime 30 minutes; use this in `Authorization: Bearer ...`.
- **Refresh token:** default lifetime 7 days; send it only to `/api/auth/refresh/` to obtain a new access token.

The default lifetimes come from `JWT_ACCESS_MINUTES` and `JWT_REFRESH_DAYS` in `.env`. Tokens use HS256 with `JWT_SECRET`. The access token contains `sub`, `username`, `role`, `type=access`, `iat`, and `exp`; the refresh token contains `sub`, `type=refresh`, `iat`, and `exp`.

### 3.1 Set a password for an LMS user

If a FINAL dataset user does not yet have a Django-compatible password hash:

```powershell
python manage.py set_lms_password FINAL_S7 <student-password>
python manage.py set_lms_password FINAL_I1 <instructor-password>
python manage.py set_lms_password DEMO_ADMIN <admin-password>
```

Only the password hash is stored in Oracle. Do not put plaintext passwords in source control or documentation.

### 3.2 Create tokens by logging in (PowerShell)

```powershell
$BaseUrl = "http://127.0.0.1:8000"

function Login-EduSphere {
    param(
        [Parameter(Mandatory=$true)][string]$Username,
        [Parameter(Mandatory=$true)][string]$Password
    )

    $body = @{
        username = $Username
        password = $Password
    } | ConvertTo-Json

    Invoke-RestMethod `
        -Uri "$BaseUrl/api/auth/login/" `
        -Method POST `
        -ContentType "application/json" `
        -Body $body
}

$student = Login-EduSphere "FINAL_S7" "<student-password>"
$student_token   = $student.access
$student_refresh = $student.refresh

$instructor = Login-EduSphere "FINAL_I1" "<instructor-password>"
$instructor_token = $instructor.access

$admin = Login-EduSphere "DEMO_ADMIN" "<admin-password>"
$admin_token = $admin.access
```

The login response contains:

```json
{
  "access": "<access-jwt>",
  "refresh": "<refresh-jwt>",
  "user": {
    "user_id": 7,
    "username": "FINAL_S7",
    "email": "...",
    "phone": null,
    "role": "STUDENT",
    "account_status": "ACTIVE",
    "last_login": "..."
  }
}
```

### 3.3 Use an access token

```powershell
$headers = @{
    Authorization = "Bearer $student_token"
}

Invoke-RestMethod `
    -Uri "$BaseUrl/api/gpa/my/" `
    -Method GET `
    -Headers $headers |
ConvertTo-Json -Depth 12
```

Equivalent HTTP header:

```http
Authorization: Bearer <access-token>
```

### 3.4 Refresh an expired/expiring access token

```powershell
$body = @{
    refresh = $student_refresh
} | ConvertTo-Json

$r = Invoke-RestMethod `
    -Uri "$BaseUrl/api/auth/refresh/" `
    -Method POST `
    -ContentType "application/json" `
    -Body $body

$student_token = $r.access
```

Do not use the refresh token as a Bearer token. The API authenticator accepts only tokens whose JWT `type` is `access`.

### 3.5 Verify the authenticated user

```powershell
Invoke-RestMethod -Uri "$BaseUrl/api/auth/me/" -Headers @{Authorization="Bearer $student_token"}
```

## 4. Role model

| Role | Typical access |
|---|---|
| STUDENT | Own dashboard, enrollment, own submissions/attendance/marks/GPA, student quiz attempts, accessible materials/announcements/exams. |
| INSTRUCTOR | Assigned offerings, assignment/material/quiz authoring, attendance, announcements, exams, marks and grade publication subject to ownership/database rules. |
| ADMIN | Administrative summaries/reports/GPA, announcements, exam scheduling, marks and grade publication. Some authoring services remain intentionally Instructor-only. |

A valid token with the wrong role normally returns **HTTP 403**. Missing or invalid credentials return **HTTP 401**.

## 5. Common headers and payload rules

Authenticated JSON request:

```http
Content-Type: application/json
Authorization: Bearer <access-token>
```

- **Roles:** STUDENT, INSTRUCTOR, ADMIN
- **Attendance status:** PRESENT, ABSENT, LATE, EXCUSED
- **Announcement priority:** LOW, NORMAL, HIGH, URGENT (default NORMAL)
- **Material type:** PDF, PPT, DOC, VIDEO, LINK, NOTE, LAB_MANUAL, OTHER
- **Exam type:** MIDTERM, FINAL, PRACTICAL, INTERNAL, MAKEUP, OTHER
- **Quiz question type:** MCQ_SINGLE, MCQ_MULTI, TRUE_FALSE, SHORT_TEXT, LONG_TEXT
- **Y/N fields:** allow_resubmission, allow_mark_view, allow_answer_review, is_correct use Y or N

Datetime inputs such as assignment due dates and quiz windows use ISO-style values such as `2026-10-15T23:59:00`. Exam dates use `YYYY-MM-DD`; exam times use 24-hour `HH:MM`.

## 6. Endpoint reference

### Core / Health

| Method | Endpoint | Effective role/access | Inputs / query | Notes |
|---|---|---|---|---|
| GET | `/api/health/` | Public | None | Service health/version summary. |
| GET | `/api/db-health/` | Public | None | Checks Oracle connection and visibility of the 31 expected LMS tables. |
| GET | `/api/version/` | Public | None | Application version and database schema identifier. |

### Authentication

| Method | Endpoint | Effective role/access | Inputs / query | Notes |
|---|---|---|---|---|
| POST | `/api/auth/login/` | Public | JSON: username, password | Returns access token, refresh token and public user data. |
| POST | `/api/auth/refresh/` | Public | JSON: refresh | Returns a new access token from a valid refresh token. |
| GET | `/api/auth/me/` | Any authenticated role | Bearer access token | Returns the authenticated LMS user profile. |

### Academics / Enrollment / Marks

| Method | Endpoint | Effective role/access | Inputs / query | Notes |
|---|---|---|---|---|
| GET | `/api/student/dashboard/` | Student | None | Student profile, enrolled courses, percentages, attendance and grade data. |
| GET | `/api/instructor/offerings/` | Instructor | None | Offerings assigned to the authenticated instructor. |
| GET | `/api/admin/summary/` | Admin | None | Basic LMS counts. |
| GET | `/api/courses/` | Student / Instructor / Admin | Query: page, page_size | Paginated course list. |
| GET | `/api/offerings/` | Student / Instructor / Admin | Query: page, page_size | Paginated offering list. |
| GET | `/api/offerings/<offering_id>/` | Student / Instructor / Admin | Path: offering_id | Offering detail. |
| GET | `/api/offerings/<offering_id>/grading/` | Student / Instructor / Admin (offering access enforced) | Path: offering_id | Grading scheme, component IDs/types/weights/max marks and child assignment/quiz/exam IDs. |
| GET | `/api/instructor/offerings/<offering_id>/roster/` | Instructor / Admin | Path: offering_id | Assigned-instructor/Admin roster including enrollment IDs for attendance and grading screens. |
| POST | `/api/enrollments/` | Student | JSON: offering_id | Enroll the authenticated student. Success: 201. |
| GET | `/api/enrollments/my/` | Student | None | Authenticated student enrollments. |
| POST | `/api/marks/record/` | Instructor / Admin | JSON: component_id, enrollment_id, marks_obtained, graded_submission_id? | Record or update a mark. |
| POST | `/api/grades/publish/` | Instructor / Admin | JSON: enrollment_id | Publish the final course grade after Oracle rules pass. |
| GET | `/api/marks/my/` | Student | None | Authenticated student marks. |

### Assignments

| Method | Endpoint | Effective role/access | Inputs / query | Notes |
|---|---|---|---|---|
| POST | `/api/assignments/create/` | Instructor | JSON: component_id, assignment_title, assignment_description?, due_date, allow_resubmission? | Create assignment on an ASSIGNMENT component. Success: 201. |
| GET | `/api/assignments/?component_id=<id>` | Student / Instructor / Admin | Query: component_id | List assignments for a grading component. |
| POST | `/api/assignments/<assignment_id>/submit/` | Student | JSON: file_url | Submit/resubmit assignment. Success: 201. |
| GET | `/api/assignments/<assignment_id>/submissions/` | Student | Path: assignment_id | Authenticated student submissions for that assignment. |
| GET | `/api/assignments/<assignment_id>/review/` | Instructor | Path: assignment_id | Instructor submission review list. |

### Attendance

| Method | Endpoint | Effective role/access | Inputs / query | Notes |
|---|---|---|---|---|
| POST | `/api/attendance/sessions/` | Instructor / Admin | JSON: offering_id, session_date, start_time, end_time?, session_type?, topic? | Create a class session for an assigned/managed offering. Success: 201. |
| GET | `/api/attendance/sessions/<offering_id>/` | Student / Instructor / Admin | Path: offering_id | List class sessions for an offering. |
| POST | `/api/attendance/record/` | Instructor / Admin | JSON: session_id, student_id, attendance_status, remarks? | Record/update attendance. Success: 201. |
| GET | `/api/attendance/my/` | Student | None | All attendance for authenticated student. |
| GET | `/api/attendance/my/<offering_id>/` | Student | Path: offering_id | Attendance for one offering. |

### Quiz

| Method | Endpoint | Effective role/access | Inputs / query | Notes |
|---|---|---|---|---|
| POST | `/api/quizzes/create/` | Instructor (service-enforced) | JSON: component_id, quiz_title, open_at?, close_at?, duration_minutes?, max_attempts | Create quiz on a QUIZ component. |
| GET | `/api/quizzes/?component_id=<id>` | Any authenticated role | Query: component_id | List quizzes for a component. |
| GET | `/api/quizzes/<quiz_id>/content/` | Student / Instructor / Admin | Path: quiz_id | Student must already have an open attempt; student payload never exposes `is_correct`. Assigned Instructor/Admin receive authoring content. |
| PATCH | `/api/quizzes/<quiz_id>/visibility/` | Instructor / Admin | JSON: allow_mark_view, allow_answer_review | Assigned instructor or Admin. Each visibility value must be Y or N. |
| POST | `/api/quizzes/<quiz_id>/attempt/` | Student | Path: quiz_id | Start a quiz attempt. |
| POST | `/api/quizzes/attempt/<attempt_id>/response/` | Student | JSON: question_id, response_text | Save a response and return `response_id` for MCQ option submission. |
| POST | `/api/quizzes/attempt/response/option/` | Student | JSON: response_id, option_id | Attach an option to a response. |
| POST | `/api/quizzes/attempt/<attempt_id>/submit/` | Student | Path: attempt_id | Finalize an owned quiz attempt. |
| GET | `/api/quizzes/attempt/<attempt_id>/result/` | Student | Path: attempt_id | Submitted owned attempt only; requires `ALLOW_MARK_VIEW=Y`. |
| GET | `/api/quizzes/attempt/<attempt_id>/review/` | Student | Path: attempt_id | Submitted owned attempt only; requires `ALLOW_ANSWER_REVIEW=Y`. |
| GET | `/api/quizzes/questions/` | Instructor / Admin | None | Reusable question-bank list with IDs/types/option counts. |
| GET | `/api/quizzes/questions/<question_id>/` | Instructor / Admin | Path: question_id | Question detail and authoring options including correct-answer metadata. |
| POST | `/api/quizzes/questions/create/` | Instructor / Admin | JSON: question_text, question_type | Create a reusable question. |
| POST | `/api/quizzes/questions/options/create/` | Instructor / Admin | JSON: question_id, option_text, is_correct, option_order | Create a question option. |
| POST | `/api/quizzes/questions/add/` | Instructor / Admin | JSON: quiz_id, question_id, question_order, question_marks | Attach a question to a quiz. |

### Course Materials

| Method | Endpoint | Effective role/access | Inputs / query | Notes |
|---|---|---|---|---|
| POST | `/api/materials/create/` | Instructor (service-enforced) | JSON: offering_id, material_title, material_type, material_url? | Create material for an owned offering. |
| GET | `/api/materials/?offering_id=<id>` | Student / Instructor / Admin | Query: offering_id | List materials for an offering. |
| GET | `/api/materials/<material_id>/` | Student / Instructor / Admin | Path: material_id | Material detail. |

### Announcements

| Method | Endpoint | Effective role/access | Inputs / query | Notes |
|---|---|---|---|---|
| POST | `/api/announcements/create/` | Instructor / Admin | JSON: offering_id, announcement_title, announcement_message, announcement_priority? | Post announcement. Instructor must be assigned to offering. |
| GET | `/api/announcements/?offering_id=<id>` | Student / Instructor / Admin (offering access enforced) | Query: offering_id | List announcements for an accessible offering. |
| GET | `/api/announcements/<announcement_id>/` | Student / Instructor / Admin (offering access enforced) | Path: announcement_id | Announcement detail. |

### Exam Schedule

| Method | Endpoint | Effective role/access | Inputs / query | Notes |
|---|---|---|---|---|
| POST | `/api/exams/schedule/` | Instructor / Admin | JSON: component_id, exam_title, exam_type, exam_date, start_time?, end_time? | Schedule an exam. Success: 201. |
| GET | `/api/exams/?offering_id=<id>` | Student / Instructor / Admin (offering access enforced) | Query: offering_id | List exams for offering. |
| GET | `/api/exams/my/upcoming/` | Student | None | Upcoming exams for current student. |
| GET | `/api/exams/<exam_id>/` | Student / Instructor / Admin (offering access enforced) | Path: exam_id | Exam detail. |

### GPA / SGPA / CGPA

| Method | Endpoint | Effective role/access | Inputs / query | Notes |
|---|---|---|---|---|
| GET | `/api/gpa/my/` | Student | None | CGPA plus per-semester SGPA, independently verified from published grades. |
| GET | `/api/gpa/my/semester/<semester_id>/` | Student | Path: semester_id | Detailed semester GPA and published course grades. |
| GET | `/api/gpa/student/<student_id>/` | Admin | Path: student_id | Admin view of student CGPA and semester SGPA values. |
| GET | `/api/gpa/student/<student_id>/semester/<semester_id>/` | Admin | Path: student_id, semester_id | Admin semester GPA detail. |

### Admin Reports

| Method | Endpoint | Effective role/access | Inputs / query | Notes |
|---|---|---|---|---|
| GET | `/api/reports/admin/overview/` | Admin | None | System overview counts. |
| GET | `/api/reports/semesters/` | Admin | None | Semester list. |
| GET | `/api/reports/offering/<offering_id>/roster/` | Admin | Path: offering_id | Offering roster. |
| GET | `/api/reports/student/<student_id>/progress/?semester_id=<id>` | Admin | Path: student_id; Query: semester_id | Student progress, percentages, attendance, grade, SGPA and CGPA. |
| GET | `/api/reports/student/<student_id>/upcoming-exams/` | Admin | Path: student_id | Upcoming exams for a selected student. |

## 7. Student workflow

1. **Who am I?:** `GET /api/auth/me/`
1. **Browse courses:** `GET /api/courses/?page=1&page_size=10`
1. **Browse offerings:** `GET /api/offerings/?page=1&page_size=10`
1. **Enroll:** `POST /api/enrollments/  {"offering_id": <id>}`
1. **My enrollments:** `GET /api/enrollments/my/`
1. **Dashboard:** `GET /api/student/dashboard/`
1. **Materials:** `GET /api/materials/?offering_id=<id>`
1. **Announcements:** `GET /api/announcements/?offering_id=<id>`
1. **Attendance:** `GET /api/attendance/my/`
1. **Assignments:** `GET /api/assignments/?component_id=<id>`
1. **Start quiz:** `POST /api/quizzes/<quiz_id>/attempt/`
1. **Upcoming exams:** `GET /api/exams/my/upcoming/`
1. **Marks:** `GET /api/marks/my/`
1. **GPA:** `GET /api/gpa/my/`

Example enrollment:

```powershell
$body = @{ offering_id = 3 } | ConvertTo-Json
Invoke-RestMethod -Uri "$BaseUrl/api/enrollments/" -Method POST -Headers @{Authorization="Bearer $student_token"} -ContentType "application/json" -Body $body
```

Example assignment submission:

```powershell
$body = @{ file_url = "https://example.com/submissions/dbms-assignment.pdf" } | ConvertTo-Json
Invoke-RestMethod -Uri "$BaseUrl/api/assignments/<assignment_id>/submit/" -Method POST -Headers @{Authorization="Bearer $student_token"} -ContentType "application/json" -Body $body
```

## 8. Instructor workflow

1. **Assigned offerings:** `GET /api/instructor/offerings/`
1. **Create assignment:** `POST /api/assignments/create/`
1. **Create material:** `POST /api/materials/create/`
1. **Post announcement:** `POST /api/announcements/create/`
1. **Create quiz:** `POST /api/quizzes/create/`
1. **Create question/options:** `POST /api/quizzes/questions/create/ and /questions/options/create/`
1. **Attach question to quiz:** `POST /api/quizzes/questions/add/`
1. **Record attendance:** `POST /api/attendance/record/`
1. **Schedule exam:** `POST /api/exams/schedule/`
1. **Record marks:** `POST /api/marks/record/`
1. **Publish grade:** `POST /api/grades/publish/`

Example announcement:

```powershell
$body = @{
    offering_id = 3
    announcement_title = "Runtime Test Notice"
    announcement_message = "Class material has been updated."
    announcement_priority = "HIGH"
} | ConvertTo-Json

Invoke-RestMethod -Uri "$BaseUrl/api/announcements/create/" -Method POST -Headers @{Authorization="Bearer $instructor_token"} -ContentType "application/json" -Body $body
```

Example exam schedule:

```powershell
$body = @{
    component_id = <exam-component-id>
    exam_title = "Computer Networks Final"
    exam_type = "FINAL"
    exam_date = "2026-10-20"
    start_time = "10:00"
    end_time = "12:00"
} | ConvertTo-Json

Invoke-RestMethod -Uri "$BaseUrl/api/exams/schedule/" -Method POST -Headers @{Authorization="Bearer $instructor_token"} -ContentType "application/json" -Body $body
```

## 9. Admin workflow

1. **Basic summary:** `GET /api/admin/summary/`
1. **Full overview:** `GET /api/reports/admin/overview/`
1. **Semester report:** `GET /api/reports/semesters/`
1. **Roster:** `GET /api/reports/offering/<offering_id>/roster/`
1. **Student progress:** `GET /api/reports/student/<student_id>/progress/?semester_id=<id>`
1. **Student exams:** `GET /api/reports/student/<student_id>/upcoming-exams/`
1. **Student GPA:** `GET /api/gpa/student/<student_id>/`
1. **Schedule exam:** `POST /api/exams/schedule/`
1. **Post announcement:** `POST /api/announcements/create/`
1. **Record/publish grades:** `POST /api/marks/record/ and /api/grades/publish/`

Example student progress report:

```powershell
Invoke-RestMethod `
  -Uri "$BaseUrl/api/reports/student/7/progress/?semester_id=2" `
  -Method GET `
  -Headers @{Authorization="Bearer $admin_token"} |
ConvertTo-Json -Depth 12
```

## 10. Quiz authoring and attempt sequence

Instructor/admin question-bank authoring and the student attempt flow are intentionally separate:

```text
Instructor: create QUIZ component-backed quiz
    -> create question
    -> create options (when applicable)
    -> add question to quiz
    -> optionally update visibility

Student: start attempt
    -> GET quiz content (now allowed because the timer has started)
    -> save response and receive response_id
    -> attach selected option(s)
    -> submit attempt
    -> view result only when ALLOW_MARK_VIEW=Y
    -> view answer review only when ALLOW_ANSWER_REVIEW=Y
```

Question types: `MCQ_SINGLE`, `MCQ_MULTI`, `TRUE_FALSE`, `SHORT_TEXT`, `LONG_TEXT`. Oracle triggers remain authoritative for quiz semantics such as option/question consistency and attempt rules.

## 11. Error and status-code contract

| HTTP | Meaning in EduSphere | Typical example |
|---:|---|---|
| 200 | Successful read/update/general action | GPA summary, report, quiz update |
| 201 | Resource/workflow creation | enrollment, assignment create/submit, attendance record, exam schedule |
| 400 | Validation, duplicate or business-rule rejection | duplicate exam, invalid priority/type |
| 401 | Missing, invalid or expired access token | no Authorization header, malformed/expired JWT |
| 403 | Authenticated but not allowed | wrong role, unassigned instructor, inaccessible offering |
| 404 | Requested LMS resource does not exist | unknown exam/announcement/material/student/offering |
| 500 | Server/configuration/programming failure | unexpected DB/config error |
| 503 | Oracle connectivity/unavailable condition | selected Oracle connection errors |

Hardened exception responses normally use:

```json
{
  "success": false,
  "message": "Exam not found.",
  "error_code": "NotFoundError"
}
```

Some older academic endpoints still return direct DRF-style payloads for their explicit responses. Newer hardened modules predominantly use the standard `{success, message, data}` / `{success, message, error_code}` envelopes.

## 12. cURL example

```bat
curl.exe -X POST http://127.0.0.1:8000/api/auth/login/ ^
  -H "Content-Type: application/json" ^
  -d "{\"username\":\"FINAL_S7\",\"password\":\"<password>\"}"
```

Then copy the returned `access` token into:

```bat
curl.exe http://127.0.0.1:8000/api/gpa/my/ -H "Authorization: Bearer <access-token>"
```

## 13. Postman usage

1. Create a `POST` request to `http://127.0.0.1:8000/api/auth/login/`.
2. Body -> raw -> JSON: `{"username":"FINAL_S7","password":"<password>"}`.
3. Copy `access` from the response.
4. For protected requests choose Authorization -> Bearer Token and paste the access token.
5. When the access token expires, call `POST /api/auth/refresh/` with the refresh token and replace the Bearer token with the new access token.

## 14. Frontend/Vue integration

Default CORS origin is `http://localhost:5173`. A Vue frontend should store the current access token only as securely as the application design permits, send it in the Bearer header, and use the refresh endpoint when needed. Do not expose `JWT_SECRET`, Oracle credentials, or the runtime database account in the browser.

## 15. Security and operational notes

- Keep `.env` out of version control. Replace development secrets before deployment.
- Set `DEBUG=False` outside development.
- Access tokens are short-lived; refresh tokens are longer-lived. There is currently no token blacklist endpoint in this backend.
- Authentication reloads the user from Oracle on each request, so deleted/inactive accounts are rejected even if a JWT has not yet expired.
- A password change does not itself blacklist already-issued JWTs; their normal expiration/account-status checks still apply.
- Use the restricted `EDUSPHERE_APP` runtime account. Do not connect the browser or frontend directly to Oracle.
- Successful application writes are audited through `PR_LOG_ACTIVITY`; the final hardening regression confirmed rejected invalid writes did not create false success audit rows.

## 16. Verified hardening status

The current backend was verified with:

- Runtime privilege + audit verification: PASS
- Python compile: PASS
- `python manage.py check`: PASS
- Static final code audit: PASS
- HTTP 401/403/404 mapping tests: PASS
- Final live regression: **19 PASS / 0 FAIL**
- Rejected-write database verification: all bad-row counters 0 and false-success-audit count 0

## 17. Current verified test account names

| Username | Role |
|---|---|
| `FINAL_S7` | STUDENT |
| `FINAL_I1` | INSTRUCTOR |
| `FINAL_I2` | INSTRUCTOR |
| `DEMO_ADMIN` | ADMIN |

Passwords are intentionally not included. Set/reset them with `python manage.py set_lms_password <username> <password>`.

---
This document reflects the final hardened source and verified runtime behavior as of the version date above.
## 18. Frontend-readiness API completion

The 2026-09-26 frontend-readiness patch closes the mandatory REST gaps identified before UI implementation: grading/component discovery, instructor roster access, class-session creation, safe quiz content delivery, question-bank reads, response identity, and V6 result/review reads. It also adds instructor ownership checks to mark recording, grade publication, and quiz-question attachment.

For an already-installed Oracle database, run `sql/18_grant_frontend_readiness_access.sql` and then `sql/19_verify_frontend_readiness_access.sql` because the new session-creation endpoint requires `INSERT` on `CLASS_SESSION` for `EDUSPHERE_APP`.

