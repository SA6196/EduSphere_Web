EduSphere Django backend - Exam Schedule + GPA Verification + Admin Reports patch

Copy/merge this patch into the current project root.

New Python packages:
  exams/
  gpa/
  reports/

Modified Python files:
  core/constants.py
  edusphere/urls.py

SQL requirement for the CURRENT database:
  Run sql/14_grant_exam_schedule_dml.sql as EDUSPHERE_OWNER in XEPDB1.
  This is required only for POST /api/exams/schedule/ because the current
  EDUSPHERE_APP runtime grants are SELECT-only on EXAM.

The clean-install sql/12_grant_runtime_access.sql is also updated so future
installs include the same INSERT privilege.

Endpoints
---------
Exam schedule:
  POST /api/exams/schedule/
  GET  /api/exams/?offering_id=<id>
  GET  /api/exams/my/upcoming/
  GET  /api/exams/<exam_id>/

GPA verification:
  GET /api/gpa/my/
  GET /api/gpa/my/semester/<semester_id>/
  GET /api/gpa/student/<student_id>/                          [Admin]
  GET /api/gpa/student/<student_id>/semester/<semester_id>/   [Admin]

Admin reports:
  GET /api/reports/admin/overview/
  GET /api/reports/semesters/
  GET /api/reports/offering/<offering_id>/roster/
  GET /api/reports/student/<student_id>/progress/?semester_id=<id>
  GET /api/reports/student/<student_id>/upcoming-exams/
