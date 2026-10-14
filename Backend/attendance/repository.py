"""
EduSphere LMS

Attendance Repository

Handles:
- Class-session queries
- Attendance queries
- Attendance procedure calls
"""

from database.query import (
    fetch_one,
    fetch_all,
    execute_procedure,
    execute,
)

from database.schema import object_name


def get_sessions(
    offering_id,
):
    """
    Return class sessions for an offering.
    """

    return fetch_all(
        f"""
        SELECT
            SESSION_ID,
            OFFERING_ID,
            SESSION_DATE,
            START_TIME,
            END_TIME,
            SESSION_TYPE,
            TOPIC
        FROM {object_name("CLASS_SESSION")}
        WHERE OFFERING_ID = ?
        ORDER BY
            SESSION_DATE,
            SESSION_ID
        """,
        (
            offering_id,
        )
    )


def get_session(
    session_id,
):
    """
    Return one class session.
    """

    return fetch_one(
        f"""
        SELECT
            SESSION_ID,
            OFFERING_ID,
            SESSION_DATE,
            START_TIME,
            END_TIME,
            SESSION_TYPE,
            TOPIC
        FROM {object_name("CLASS_SESSION")}
        WHERE SESSION_ID = ?
        """,
        (
            session_id,
        )
    )


def instructor_owns_offering(
    instructor_id,
    offering_id,
):
    """
    Check whether an instructor is assigned
    to the offering.
    """

    row = fetch_one(
        f"""
        SELECT
            1 AS AUTHORIZED
        FROM {object_name("OFFERING_INSTRUCTOR")}
        WHERE OFFERING_ID = ?
          AND INSTRUCTOR_ID = ?
        """,
        (
            offering_id,
            instructor_id,
        )
    )

    return row is not None


def record_attendance(
    session_id,
    student_id,
    attendance_status,
    remarks,
    actor_user_id,
):
    """
    Record attendance through the Oracle
    attendance procedure.
    """

    execute_procedure(
        object_name("PR_RECORD_ATTENDANCE"),
        (
            session_id,
            student_id,
            attendance_status,
            remarks,
            actor_user_id,
        )
    )

    return {
        "message":
            "Attendance recorded successfully"
    }


def get_student_attendance(
    student_id,
):
    """
    Return attendance records belonging
    to the specified student.
    """

    return fetch_all(
        f"""
        SELECT
            a.ATTENDANCE_ID,
            a.SESSION_ID,
            cs.OFFERING_ID,
            cs.SESSION_DATE,
            cs.START_TIME,
            cs.END_TIME,
            cs.SESSION_TYPE,
            cs.TOPIC,
            a.ATTENDANCE_STATUS,
            a.REMARKS,
            a.RECORDED_BY_USER_ID,
            a.RECORDED_AT,
            a.UPDATED_BY_USER_ID,
            a.UPDATED_AT
        FROM {object_name("ATTENDANCE")} a
        JOIN {object_name("CLASS_SESSION")} cs
          ON cs.SESSION_ID = a.SESSION_ID
        WHERE a.STUDENT_ID = ?
        ORDER BY
            cs.SESSION_DATE DESC,
            a.ATTENDANCE_ID DESC
        """,
        (
            student_id,
        )
    )


def get_student_attendance_for_offering(
    student_id,
    offering_id,
):
    """
    Return attendance records for one
    student in one offering.
    """

    return fetch_all(
        f"""
        SELECT
            a.ATTENDANCE_ID,
            a.SESSION_ID,
            cs.OFFERING_ID,
            cs.SESSION_DATE,
            cs.START_TIME,
            cs.END_TIME,
            cs.SESSION_TYPE,
            cs.TOPIC,
            a.ATTENDANCE_STATUS,
            a.REMARKS,
            a.RECORDED_AT,
            a.UPDATED_AT
        FROM {object_name("ATTENDANCE")} a
        JOIN {object_name("CLASS_SESSION")} cs
          ON cs.SESSION_ID = a.SESSION_ID
        WHERE a.STUDENT_ID = ?
          AND cs.OFFERING_ID = ?
        ORDER BY
            cs.SESSION_DATE DESC,
            a.ATTENDANCE_ID DESC
        """,
        (
            student_id,
            offering_id,
        )
    )


def get_offering(offering_id):
    return fetch_one(
        f"""
        SELECT
            co.OFFERING_ID,
            co.OFFERING_STATUS,
            co.SEMESTER_ID,
            c.COURSE_CODE,
            c.COURSE_NAME,
            co.SECTION_CODE,
            sem.SEMESTER_START_DATE,
            sem.SEMESTER_END_DATE
        FROM {object_name("COURSE_OFFERING")} co
        JOIN {object_name("COURSE")} c
          ON c.COURSE_ID=co.COURSE_ID
        JOIN {object_name("SEMESTER")} sem
          ON sem.SEMESTER_ID=co.SEMESTER_ID
        WHERE co.OFFERING_ID=?
        """,
        (offering_id,),
    )


def create_class_session(
    offering_id,
    session_date,
    start_time,
    end_time,
    session_type,
    topic,
):
    execute(
        f"""
        INSERT INTO {object_name("CLASS_SESSION")}
        (
            OFFERING_ID,
            SESSION_DATE,
            START_TIME,
            END_TIME,
            SESSION_TYPE,
            TOPIC
        )
        VALUES
        (
            ?,
            TO_DATE(?, 'YYYY-MM-DD'),
            ?,
            ?,
            ?,
            ?
        )
        """,
        (
            offering_id,
            session_date,
            start_time,
            end_time,
            session_type,
            topic,
        ),
    )

    # V3 hardening defines a unique class-session slot by
    # (Offering_ID, Session_Date, Start_Time), so this lookup is deterministic.
    return fetch_one(
        f"""
        SELECT
            SESSION_ID,
            OFFERING_ID,
            SESSION_DATE,
            START_TIME,
            END_TIME,
            SESSION_TYPE,
            TOPIC
        FROM {object_name("CLASS_SESSION")}
        WHERE OFFERING_ID=?
          AND SESSION_DATE=TO_DATE(?, 'YYYY-MM-DD')
          AND START_TIME=?
        """,
        (offering_id, session_date, start_time),
    )


def get_student_semester_attendance(student_id):
    """Return the student's semesters, enrolled offerings and attendance sessions.

    Attendance records are LEFT JOINed by *both* session and authenticated
    student's STUDENT_ID.  Missing attendance is not inferred as ABSENT.
    Past enrollments remain available after the semester ends.  This only
    reads existing relations in the approved 37-table schema.
    """
    scope = f"""
        FROM {object_name('ENROLLMENT')} e
        JOIN {object_name('COURSE_OFFERING')} co
          ON co.OFFERING_ID = e.OFFERING_ID
        JOIN {object_name('SEMESTER')} sem
          ON sem.SEMESTER_ID = co.SEMESTER_ID
        WHERE e.STUDENT_ID = ?
          AND e.ENROLLMENT_STATUS IN ('ENROLLED', 'COMPLETED', 'DROPPED')
    """
    semesters = fetch_all(
        f"""
        SELECT DISTINCT sem.SEMESTER_ID, sem.SEMESTER_NAME,
            sem.ACADEMIC_YEAR,
            TO_CHAR(sem.SEMESTER_START_DATE, 'YYYY-MM-DD') AS SEMESTER_START_DATE
        {scope}
        ORDER BY SEMESTER_START_DATE DESC, sem.SEMESTER_ID DESC
        """, (student_id,)
    )
    courses = fetch_all(
        f"""
        SELECT e.ENROLLMENT_ID, e.ENROLLMENT_STATUS, co.OFFERING_ID,
            sem.SEMESTER_ID, c.COURSE_CODE, c.COURSE_NAME, co.SECTION_CODE,
            {object_name('FN_ATTENDANCE_PCT')}(e.STUDENT_ID, co.OFFERING_ID) AS OFFICIAL_ATTENDANCE_PCT
        FROM {object_name('ENROLLMENT')} e
        JOIN {object_name('COURSE_OFFERING')} co
          ON co.OFFERING_ID = e.OFFERING_ID
        JOIN {object_name('SEMESTER')} sem
          ON sem.SEMESTER_ID = co.SEMESTER_ID
        JOIN {object_name('COURSE')} c ON c.COURSE_ID = co.COURSE_ID
        WHERE e.STUDENT_ID = ?
          AND e.ENROLLMENT_STATUS IN ('ENROLLED', 'COMPLETED', 'DROPPED')
        ORDER BY sem.SEMESTER_START_DATE DESC,
                 c.COURSE_CODE, co.SECTION_CODE, co.OFFERING_ID
        """, (student_id,)
    )
    sessions = fetch_all(
        f"""
        SELECT cs.SESSION_ID, co.OFFERING_ID, sem.SEMESTER_ID,
            TO_CHAR(cs.SESSION_DATE, 'YYYY-MM-DD') AS SESSION_DATE,
            cs.START_TIME, cs.END_TIME, cs.SESSION_TYPE, cs.TOPIC,
            a.ATTENDANCE_ID, a.ATTENDANCE_STATUS, a.REMARKS,
            CASE WHEN cs.SESSION_DATE > TRUNC(SYSDATE) THEN 'UPCOMING'
                 ELSE 'PAST_OR_TODAY' END AS SESSION_TIMING
        FROM {object_name('ENROLLMENT')} e
        JOIN {object_name('COURSE_OFFERING')} co
          ON co.OFFERING_ID = e.OFFERING_ID
        JOIN {object_name('SEMESTER')} sem
          ON sem.SEMESTER_ID = co.SEMESTER_ID
        JOIN {object_name('CLASS_SESSION')} cs
          ON cs.OFFERING_ID = co.OFFERING_ID
        LEFT JOIN {object_name('ATTENDANCE')} a
          ON a.SESSION_ID = cs.SESSION_ID AND a.STUDENT_ID = e.STUDENT_ID
        WHERE e.STUDENT_ID = ?
          AND e.ENROLLMENT_STATUS IN ('ENROLLED', 'COMPLETED', 'DROPPED')
        ORDER BY cs.SESSION_DATE DESC, cs.START_TIME DESC, cs.SESSION_ID DESC
        """, (student_id,)
    )
    return {'semesters': semesters, 'courses': courses, 'sessions': sessions}
