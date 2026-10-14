# EduSphere Frontend

Vue 3 + Vite frontend for the verified EduSphere Django REST + Oracle LMS backend.

## Stack

- Vue 3 Composition API
- Vue Router
- Native `fetch` API with automatic JWT refresh, request timeout and safe error normalization
- Responsive CSS design system (no external UI framework)
- Django REST backend at `http://127.0.0.1:8000/api`

## Run

1. Start the verified Django backend on port 8000.
2. In this frontend folder:

```powershell
Copy-Item .env.example .env
npm install
npm run dev
```

Open `http://localhost:5173`.

The backend already permits the default Vite origin `http://localhost:5173`.

## Authentication

The login screen calls `POST /api/auth/login/` and stores access/refresh tokens in `sessionStorage` for the current browser session. Protected requests send `Authorization: Bearer <access>`. When a request returns 401, the API client uses a single shared refresh request, calls `POST /api/auth/refresh/`, and retries the original request once. Technical Oracle/ODBC/debug text is sanitized before any error is rendered to the user.

## Role portals

### Student

- Dashboard
- Course catalog and enrollment
- Offering workspace
- Materials and announcements
- Class sessions and own attendance
- Assignments and URL submission
- Quiz attempt flow
- Exams
- Marks, attendance, GPA and upcoming exams

### Instructor

- Assigned offering dashboard
- Offering roster and grading
- Materials
- Announcements
- Class-session creation
- Attendance recording
- Assignment creation/review
- Quiz creation and visibility controls
- Question bank, options and quiz mapping
- Exam scheduling
- Mark recording and final grade publication

### Administrator

- System overview
- Reports and semester lookup
- Offering workspace
- Roster access
- Announcements
- Session creation
- Exam scheduling
- Mark recording and grade publication
- Question bank authoring
- Student progress, GPA and upcoming-exam reports

## Important backend rules reflected in the UI

- The browser never connects to Oracle.
- Role access is enforced by Django and Oracle even if a frontend control is hidden.
- Student quiz content is loaded only after an attempt has started.
- Quiz results require `ALLOW_MARK_VIEW=Y`.
- Quiz answer review requires `ALLOW_ANSWER_REVIEW=Y`.
- GPA is derived from published course grades; it is not stored as a duplicate base-table value.
- Offering workspace uses the grading-discovery endpoint to resolve component IDs before authoring or grading.

## Main frontend routes

```text
/login
/profile
/catalog
/offerings/:offeringId
/student/dashboard
/student/performance
/student/quizzes/:quizId
/instructor/dashboard
/question-bank
/admin/dashboard
/admin/reports
```

## Environment

`.env`:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000/api
VITE_API_TIMEOUT_MS=20000
```

Do not put Oracle credentials, `JWT_SECRET`, Django secrets, or database passwords in the frontend environment.

## UX refactor update

The current revision adds enrollment-aware catalog state, named selectors instead of manual IDs, a modular offering workspace, searchable/sortable/paginated tables, confirmation/busy states, quiz draft/progress/timer UX, structured Student/Admin reporting, charts and calendars.

`FRONTEND_LIMITATIONS_V3.md` documents the current remaining limitations. It also distinguishes frontend-only limitations from items that require backend/API support.
