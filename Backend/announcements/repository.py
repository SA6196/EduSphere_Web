"""
EduSphere LMS

Announcement Repository Layer

Handles:
- announcement posting through Oracle PR_POST_ANNOUNCEMENT
- offering announcement reads
- enrollment access checks
"""

from database.query import (
    fetch_all,
    fetch_one,
    execute_procedure,
)
from database.schema import object_name


def post_announcement(
    offering_id,
    user_id,
    title,
    message,
    priority,
):
    """Use the authoritative Oracle procedure for announcement writes."""

    execute_procedure(
        object_name("PR_POST_ANNOUNCEMENT"),
        (
            offering_id,
            user_id,
            title,
            message,
            priority,
        ),
    )


def list_announcements(offering_id):
    return fetch_all(
        f"""
        SELECT
            a.ANNOUNCEMENT_ID,
            a.OFFERING_ID,
            co.COURSE_ID,
            c.COURSE_CODE,
            c.COURSE_NAME,
            a.POSTED_BY_USER_ID,
            u.USERNAME AS POSTED_BY_USERNAME,
            a.ANNOUNCEMENT_TITLE,
            a.ANNOUNCEMENT_MESSAGE,
            a.ANNOUNCEMENT_PRIORITY,
            a.POSTED_AT
        FROM {object_name("ANNOUNCEMENT")} a
        JOIN {object_name("COURSE_OFFERING")} co
          ON co.OFFERING_ID=a.OFFERING_ID
        JOIN {object_name("COURSE")} c
          ON c.COURSE_ID=co.COURSE_ID
        JOIN {object_name("LMS_USER")} u
          ON u.USER_ID=a.POSTED_BY_USER_ID
        WHERE a.OFFERING_ID=?
        ORDER BY a.POSTED_AT DESC, a.ANNOUNCEMENT_ID DESC
        """,
        (offering_id,),
    )


def get_announcement(announcement_id):
    return fetch_one(
        f"""
        SELECT
            a.ANNOUNCEMENT_ID,
            a.OFFERING_ID,
            co.COURSE_ID,
            c.COURSE_CODE,
            c.COURSE_NAME,
            a.POSTED_BY_USER_ID,
            u.USERNAME AS POSTED_BY_USERNAME,
            a.ANNOUNCEMENT_TITLE,
            a.ANNOUNCEMENT_MESSAGE,
            a.ANNOUNCEMENT_PRIORITY,
            a.POSTED_AT
        FROM {object_name("ANNOUNCEMENT")} a
        JOIN {object_name("COURSE_OFFERING")} co
          ON co.OFFERING_ID=a.OFFERING_ID
        JOIN {object_name("COURSE")} c
          ON c.COURSE_ID=co.COURSE_ID
        JOIN {object_name("LMS_USER")} u
          ON u.USER_ID=a.POSTED_BY_USER_ID
        WHERE a.ANNOUNCEMENT_ID=?
        """,
        (announcement_id,),
    )


def student_has_offering(student_id, offering_id):
    row = fetch_one(
        f"""
        SELECT e.ENROLLMENT_ID
        FROM {object_name("ENROLLMENT")} e
        WHERE e.STUDENT_ID=?
          AND e.OFFERING_ID=?
          AND e.ENROLLMENT_STATUS IN ('ENROLLED','COMPLETED')
        """,
        (
            student_id,
            offering_id,
        ),
    )

    return row is not None
