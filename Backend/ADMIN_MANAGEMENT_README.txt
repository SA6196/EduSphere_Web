EduSphere Admin Management Delta - 2026-09-27
================================================

New Admin-only API surface (base URL /api/admin/manage):
GET  /directory/
GET/POST /students/
GET/POST /instructors/
POST /offerings/
GET/PUT /offerings/<offering_id>/instructors/
GET/PUT /offerings/<offering_id>/grading-scheme/

Capabilities:
- Create Student accounts: LMS_USER + STUDENT in one transaction.
- Create Instructor accounts: LMS_USER + INSTRUCTOR in one transaction.
- Passwords are hashed with Django make_password before Oracle storage.
- Create class offerings from existing Course + Semester rows.
- Assign or replace one/many instructors for an offering.
- Create/update an offering grading scheme and assessment-component weightage.
- Component weights must total exactly 100% when saved.
- Existing components are not deleted through this API.
- Grading schemes are locked once any final COURSE_GRADE exists for the offering.
- New successful admin writes are audited through PR_LOG_ACTIVITY in the same transaction.

Oracle setup after copying the patch:
@...\sql\20_grant_admin_management_access.sql
@...\sql\21_verify_admin_management_access.sql

Then:
python -m py_compile administration\repository.py administration\services.py administration\views.py administration\urls.py
python manage.py check
python scripts\admin_management_code_audit.py
