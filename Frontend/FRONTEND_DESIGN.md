# EduSphere Frontend Design — UX Refactor

## Architecture

The Vue 3 frontend remains a role-based SPA backed by the hardened Django REST API. The frontend does not duplicate Oracle business rules; it improves discoverability, validation and presentation while leaving final authorization/integrity to Django/Oracle.

## Role surfaces

- **Student:** dashboard, enrollment-aware catalog, offering workspace, assignments, quizzes, attendance, exams, GPA/performance.
- **Instructor:** assigned offerings, modular course workspace, roster/grading, attendance, content, assignment/quiz/exam authoring, question bank.
- **Admin:** system dashboard, reports, offering workspace operations and question-bank access allowed by the backend.

## Component structure

`OfferingWorkspaceView.vue` is now an orchestration shell. Individual domains live under `src/components/workspace/`, including Overview, Materials, Announcements, Sessions, Assignments, Quizzes, Exams, Attendance, Roster/Grading and Record Attendance.

Shared UX components include `ConfirmDialog`, `LoadingState`, `DataTable`, `BarChart`, `CalendarMonth` and `FileUrlField`.

## Design rules

- Use names/labels in controls; IDs remain internal values.
- Disable duplicate/invalid actions when the frontend already has sufficient state.
- Show busy state for network mutations.
- Confirm irreversible/high-impact actions.
- Keep Oracle/Django as the authoritative rule layer.
- Prefer structured tables/charts/calendar views to raw JSON.
- Keep charts and calendars dependency-free for portability.
