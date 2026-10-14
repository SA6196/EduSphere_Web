"""
EduSphere LMS

Audit Logging Service

Final hardening: all activity writes use the authoritative PR_LOG_ACTIVITY
entry point rather than direct ACTIVITY_LOG DML.
"""

from database.query import execute_procedure
from database.schema import object_name


def log_activity(
    user_id,
    activity_type,
    activity_description=None,
    ip_address=None,
):
    execute_procedure(
        object_name("PR_LOG_ACTIVITY"),
        (
            int(user_id),
            activity_type,
            activity_description,
            ip_address,
        ),
    )
