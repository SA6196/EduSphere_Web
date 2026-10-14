# EduSphere API Endpoint Reference

Source: the actual Django URL/view files in the packaged project. Base URL examples assume `http://127.0.0.1:8000`.

## Authentication
Most endpoints use `Authorization: Bearer <access-token>`. Login and refresh are public. The access token is JWT-based; the frontend stores/refreshes it through the auth store.

### Login example
```http
POST /api/auth/login/
Content-Type: application/json

{"username":"DEMO_ADMIN","password":"<your locally generated demo password>"}
```

Successful login returns `access`, `refresh`, and `user`. Use the access token on subsequent authenticated calls.

## Complete endpoint catalogue

### CORE
- **GET `/api/health/`** — `HealthView` — **Public**
- **GET `/api/db-health/`** — `DatabaseHealthView` — **Public**
- **GET `/api/version/`** — `VersionView` — **Public**

### ACCOUNTS
- **POST `/api/auth/login/`** — `LoginView` — **Public**
- **POST `/api/auth/refresh/`** — `RefreshView` — **Public**
- **GET `/api/auth/me/`** — `MeView` — **Authenticated**

### ACADEMICS
- **GET `/api/student/dashboard/`** — `StudentDashboardView` — **STUDENT**
- **GET `/api/instructor/offerings/`** — `InstructorOfferingsView` — **INSTRUCTOR**
- **GET `/api/admin/summary/`** — `AdminSummaryView` — **ADMIN**
- **GET `/api/courses/`** — `CourseListView` — **STUDENT/INSTRUCTOR/ADMIN**
- **GET `/api/offerings/`** — `OfferingListView` — **STUDENT/INSTRUCTOR/ADMIN**
- **GET `/api/offerings/<offering_id>/`** — `OfferingDetailView` — **STUDENT/INSTRUCTOR/ADMIN**
- **GET `/api/offerings/<offering_id>/grading/`** — `OfferingGradingView` — **STUDENT/INSTRUCTOR/ADMIN**
- **GET `/api/instructor/offerings/<offering_id>/roster/`** — `InstructorOfferingRosterView` — **INSTRUCTOR/ADMIN**
- **POST `/api/enrollments/`** — `EnrollmentCreateView` — **STUDENT**
- **GET `/api/enrollments/my/`** — `MyEnrollmentView` — **STUDENT**
- **POST `/api/marks/record/`** — `RecordMarkView` — **INSTRUCTOR/ADMIN**
- **POST `/api/grades/publish/`** — `PublishGradeView` — **INSTRUCTOR/ADMIN**
- **GET `/api/marks/my/`** — `StudentMarksView` — **STUDENT**

### ADMINISTRATION
- **GET `/api/admin/manage/directory/`** — `AdminDirectoryView` — **ADMIN**
- **GET `/api/admin/manage/students/`** — `AdminStudentAccountsView` — **ADMIN**
- **POST `/api/admin/manage/students/`** — `AdminStudentAccountsView` — **ADMIN**
- **GET `/api/admin/manage/instructors/`** — `AdminInstructorAccountsView` — **ADMIN**
- **POST `/api/admin/manage/instructors/`** — `AdminInstructorAccountsView` — **ADMIN**
- **POST `/api/admin/manage/offerings/`** — `AdminOfferingCreateView` — **ADMIN**
- **GET `/api/admin/manage/offerings/<offering_id>/instructors/`** — `AdminOfferingInstructorView` — **ADMIN**
- **PUT `/api/admin/manage/offerings/<offering_id>/instructors/`** — `AdminOfferingInstructorView` — **ADMIN**
- **GET `/api/admin/manage/offerings/<offering_id>/grading-scheme/`** — `AdminGradingSchemeView` — **ADMIN**
- **PUT `/api/admin/manage/offerings/<offering_id>/grading-scheme/`** — `AdminGradingSchemeView` — **ADMIN**

### ANNOUNCEMENTS
- **POST `/api/announcements/create/`** — `AnnouncementCreateView` — **INSTRUCTOR/ADMIN**
- **GET `/api/announcements/`** — `AnnouncementListView` — **STUDENT/INSTRUCTOR/ADMIN**
- **GET `/api/announcements/<announcement_id>/`** — `AnnouncementDetailView` — **STUDENT/INSTRUCTOR/ADMIN**

### ASSIGNMENTS
- **POST `/api/assignments/create/`** — `AssignmentCreateView` — **INSTRUCTOR**
- **GET `/api/assignments/`** — `AssignmentListView` — **STUDENT/INSTRUCTOR/ADMIN**
- **POST `/api/assignments/<assignment_id>/submit/`** — `AssignmentSubmissionView` — **STUDENT**
- **GET `/api/assignments/<assignment_id>/submissions/`** — `StudentSubmissionListView` — **STUDENT**
- **GET `/api/assignments/<assignment_id>/review/`** — `InstructorSubmissionListView` — **INSTRUCTOR**

### ATTENDANCE
- **POST `/api/attendance/sessions/`** — `SessionCreateView` — **INSTRUCTOR/ADMIN**
- **GET `/api/attendance/sessions/<offering_id>/`** — `SessionListView` — **STUDENT/INSTRUCTOR/ADMIN**
- **POST `/api/attendance/record/`** — `RecordAttendanceView` — **INSTRUCTOR/ADMIN**
- **GET `/api/attendance/my/`** — `MyAttendanceView` — **STUDENT**
- **GET `/api/attendance/my/<offering_id>/`** — `MyOfferingAttendanceView` — **STUDENT**

### EXAMS
- **POST `/api/exams/schedule/`** — `ExamScheduleCreateView` — **INSTRUCTOR/ADMIN**
- **GET `/api/exams/`** — `ExamOfferingListView` — **STUDENT/INSTRUCTOR/ADMIN**
- **GET `/api/exams/my/upcoming/`** — `MyUpcomingExamsView` — **STUDENT**
- **GET `/api/exams/<exam_id>/`** — `ExamDetailView` — **STUDENT/INSTRUCTOR/ADMIN**

### GPA
- **GET `/api/gpa/my/`** — `MyGPASummaryView` — **STUDENT**
- **GET `/api/gpa/my/semester/<semester_id>/`** — `MySemesterGPAView` — **STUDENT**
- **GET `/api/gpa/student/<student_id>/`** — `AdminStudentGPASummaryView` — **ADMIN**
- **GET `/api/gpa/student/<student_id>/semester/<semester_id>/`** — `AdminStudentSemesterGPAView` — **ADMIN**

### MATERIALS
- **POST `/api/materials/create/`** — `MaterialCreateView` — **INSTRUCTOR/ADMIN**
- **GET `/api/materials/`** — `MaterialListView` — **STUDENT/INSTRUCTOR/ADMIN**
- **GET `/api/materials/<material_id>/`** — `MaterialDetailView` — **STUDENT/INSTRUCTOR/ADMIN**

### QUIZ
- **POST `/api/quizzes/create/`** — `QuizCreateView` — **Authenticated**
- **GET `/api/quizzes/`** — `QuizListView` — **Authenticated**
- **GET `/api/quizzes/<quiz_id>/content/`** — `QuizContentView` — **STUDENT/INSTRUCTOR/ADMIN**
- **PATCH `/api/quizzes/<quiz_id>/visibility/`** — `QuizVisibilityView` — **INSTRUCTOR/ADMIN**
- **POST `/api/quizzes/<quiz_id>/attempt/`** — `QuizAttemptView` — **STUDENT**
- **POST `/api/quizzes/attempt/<attempt_id>/response/`** — `QuizResponseView` — **STUDENT**
- **POST `/api/quizzes/attempt/response/option/`** — `ResponseOptionView` — **STUDENT**
- **POST `/api/quizzes/attempt/<attempt_id>/submit/`** — `QuizSubmitView` — **STUDENT**
- **GET `/api/quizzes/attempt/<attempt_id>/result/`** — `QuizAttemptResultView` — **STUDENT**
- **GET `/api/quizzes/attempt/<attempt_id>/review/`** — `QuizAttemptReviewView` — **STUDENT**
- **GET `/api/quizzes/<quiz_id>/grading/`** — `QuizGradingListView` — **INSTRUCTOR/ADMIN**
- **GET `/api/quizzes/attempt/<attempt_id>/grading/`** — `QuizGradingDetailView` — **INSTRUCTOR/ADMIN**
- **PATCH `/api/quizzes/attempt/<attempt_id>/grading/`** — `QuizGradingDetailView` — **INSTRUCTOR/ADMIN**
- **POST `/api/quizzes/attempt/<attempt_id>/grading/release/`** — `QuizGradingReleaseView` — **INSTRUCTOR/ADMIN**
- **GET `/api/quizzes/questions/`** — `QuestionListView` — **INSTRUCTOR/ADMIN**
- **GET `/api/quizzes/questions/<question_id>/`** — `QuestionDetailView` — **INSTRUCTOR/ADMIN**
- **POST `/api/quizzes/questions/create/`** — `QuestionCreateView` — **INSTRUCTOR/ADMIN**
- **POST `/api/quizzes/questions/options/create/`** — `QuestionOptionCreateView` — **INSTRUCTOR/ADMIN**
- **POST `/api/quizzes/questions/add/`** — `AddQuestionToQuizView` — **INSTRUCTOR/ADMIN**
- **POST `/api/quizzes/questions/numeric-rule/`** — `QuestionNumericRuleView` — **INSTRUCTOR/ADMIN**
- **POST `/api/quizzes/questions/keywords/`** — `QuestionKeywordView` — **INSTRUCTOR/ADMIN**

### REPORTS
- **GET `/api/reports/admin/overview/`** — `AdminOverviewReportView` — **ADMIN**
- **GET `/api/reports/semesters/`** — `SemesterListReportView` — **ADMIN**
- **GET `/api/reports/offering/<offering_id>/roster/`** — `OfferingRosterReportView` — **ADMIN**
- **GET `/api/reports/student/<student_id>/progress/`** — `StudentProgressReportView` — **ADMIN**
- **GET `/api/reports/student/<student_id>/upcoming-exams/`** — `StudentUpcomingExamsReportView` — **ADMIN**

## Request-field reference

| Operation | JSON/query fields |
|---|---|
| POST /api/auth/login/ | `username`, `password` |
| POST /api/auth/refresh/ | `refresh` |
| POST /api/admin/manage/students/ | `username`, `email`, `password`, `student_name`, `admission_no`, `program_id`; optional `phone`, `batch`, `account_status`, `student_status` |
| POST /api/admin/manage/instructors/ | `username`, `email`, `password`, `instructor_name`, `department_id`; optional `phone`, `designation`, `account_status` |
| POST /api/admin/manage/offerings/ | `course_id`, `semester_id`, `section_code`; optional schedule/capacity/status and `instructor_ids` |
| PUT /api/admin/manage/offerings/<offering_id>/instructors/ | `instructor_ids` array |
| PUT /api/admin/manage/offerings/<offering_id>/grading-scheme/ | `scheme_name`, `components[]` |
| POST /api/assignments/create/ | `component_id`, `assignment_title`, `assignment_description`, `due_date`, `allow_resubmission` |
| POST /api/assignments/<assignment_id>/submit/ | `file_url` |
| POST /api/attendance/sessions/ | `offering_id`, `session_date`, optional times/type/topic |
| POST /api/attendance/record/ | `session_id`, `student_id`, `attendance_status`, optional `remarks` |
| POST /api/announcements/create/ | `offering_id`, `announcement_title`, `announcement_message`, optional priority |
| POST /api/materials/create/ | `offering_id`, `material_title`, `material_type`, optional `material_url` |
| POST /api/exams/schedule/ | `component_id`, `exam_title`, `exam_type`, `exam_date`, optional times |
| POST /api/enrollments/ | `offering_id` |
| POST /api/marks/record/ | `component_id`, `enrollment_id`, `marks_obtained`, optional `graded_submission_id` |
| POST /api/grades/publish/ | `enrollment_id` |
| POST /api/quizzes/create/ | `component_id`, `quiz_title`, optional timing/attempt fields |
| PATCH /api/quizzes/<quiz_id>/visibility/ | `allow_mark_view`, `allow_answer_review` |
| POST /api/quizzes/<quiz_id>/attempt/ | no body |
| POST /api/quizzes/attempt/<attempt_id>/response/ | `question_id`, `response_text`, optional `ordered_option_ids`, `matching_pairs` |
| POST /api/quizzes/attempt/response/option/ | `response_id`, `option_id` |
| POST /api/quizzes/questions/create/ | `question_text`, `question_type`, optional `true_false_correct` |
| POST /api/quizzes/questions/options/create/ | `question_id`, `option_text`, `is_correct`, `option_order`, optional matching fields |
| POST /api/quizzes/questions/add/ | `quiz_id`, `question_id`, `question_order`, `question_marks` |
| POST /api/quizzes/questions/numeric-rule/ | `question_id`, `expected_value`, `tolerance` |
| POST /api/quizzes/questions/keywords/ | `question_id`, `keyword_order`, `keyword_text` |
| PATCH /api/quizzes/attempt/<attempt_id>/grading/ | `final_marks`, `notes` |

## Quiz answer formats

- **MCQ_SINGLE / TRUE_FALSE:** use `ordered_option_ids`/`response option` with exactly the permitted option selection.
- **MCQ_MULTI:** all correct options are required; extra options produce zero.
- **SHORT_TEXT:** `response_text` is normalized and compared exactly against any accepted keyword.
- **NUMERICAL:** numeric answer is accepted within the stored tolerance.
- **FILL_BLANK:** `response_text` is an ordered JSON array/list of blank answers; each position is checked against `QUESTION_KEYWORD.KEYWORD_ORDER`.
- **MATCHING:** `matching_pairs` contains left/right option IDs; the set must exactly match the correct associations, with duplicates rejected.
- **LONG_TEXT:** stored for manual/instructor grading.

## Typical invocation flow
1. `POST /api/auth/login/` → obtain access token.
2. `GET /api/courses/` and `GET /api/offerings/` → discover academic data.
3. Role-specific dashboard endpoint → load the role workspace.
4. Instructor/admin creates/configures assessment data.
5. Student enrolls with `POST /api/enrollments/`.
6. Student starts a quiz with `POST /api/quizzes/<quiz_id>/attempt/`.
7. Student sends responses, then `POST /api/quizzes/attempt/<attempt_id>/submit/`.
8. Student reads result/review; instructor/admin reads grading and releases reviewed marks.

## Error/auth behavior
- Missing/invalid Bearer token → authentication failure (normally HTTP 401).
- Valid token with wrong role → permission denial (normally HTTP 403).
- Validation/business-rule failures are raised by the service layer and returned through the project exception handler.
- Database constraints/triggers enforce a second layer of integrity.
