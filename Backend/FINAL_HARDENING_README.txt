EduSphere Final Hardening Patch

Changes:
1. Custom PermissionDeniedError now maps to HTTP 403.
2. Custom AuthenticationError maps to HTTP 401.
3. JWT authenticator exposes Bearer authenticate_header so missing credentials return 401.
4. NotFoundError added and missing resources return HTTP 404.
5. DRF validation messages are preserved in the standard error envelope.
6. Attendance built-in PermissionError/ValueError leaks removed.
7. Audit logging now goes through PR_LOG_ACTIVITY instead of direct ACTIVITY_LOG INSERT.
8. Quiz question/option/mapping validation hardened and those authoring actions are audited.
9. Canonical runtime grant script updated; script 15 grants the direct repository DML actually needed.
10. Script 16 verifies runtime privileges + PR_LOG_ACTIVITY validity.
11. final_code_audit.py performs static hardening checks.
12. final_regression.ps1 performs the final API regression sweep.
13. script 17 verifies rejected hardening tests produced no rows or false success audits.

Apply:
- Extract this patch into the current project root and overwrite matching files.
- In SQL*Plus as EDUSPHERE_OWNER in XEPDB1 run:
  @<project>\sql\15_grant_runtime_dml_hardening.sql
  @<project>\sql\16_verify_runtime_privileges_and_audit.sql
- In activated .venv run:
  python -m py_compile core\exceptions.py core\exception_handler.py core\audit.py accounts\authentication.py academics\services.py attendance\services.py assignments\services.py materials\services.py announcements\services.py quiz\repository.py quiz\services.py quiz\views.py exams\services.py gpa\services.py reports\services.py
  python manage.py check
  python scripts\final_code_audit.py
- Then run scripts\final_regression.ps1 with the four tokens and finally SQL script 17.
