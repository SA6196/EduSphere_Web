"""
EduSphere LMS

Exam Schedule Repository

The EXAM table is authoritative for exam date/time data.  Django performs
SELECT/INSERT through the runtime Oracle account while the certified Oracle
triggers keep component type, semester-date and time constraints authoritative.
"""

from database.query import execute, fetch_all, fetch_one
from database.schema import object_name


def get_component_context(component_id):
    return fetch_one(
        f"""
        SELECT
            ac.COMPONENT_ID,
            ac.COMPONENT_NAME,
            ac.COMPONENT_TYPE,
            ac.MAX_MARKS,
            gs.SCHEME_ID,
            gs.OFFERING_ID,
            co.COURSE_ID,
            co.SEMESTER_ID,
            co.SECTION_CODE,
            co.OFFERING_STATUS,
            c.COURSE_CODE,
            c.COURSE_NAME,
            sem.SEMESTER_NAME,
            sem.ACADEMIC_YEAR,
            sem.SEMESTER_START_DATE,
            sem.SEMESTER_END_DATE
        FROM {object_name("ASSESSMENT_COMPONENT")} ac
        JOIN {object_name("GRADING_SCHEME")} gs
          ON gs.SCHEME_ID=ac.SCHEME_ID
        JOIN {object_name("COURSE_OFFERING")} co
          ON co.OFFERING_ID=gs.OFFERING_ID
        JOIN {object_name("COURSE")} c
          ON c.COURSE_ID=co.COURSE_ID
        JOIN {object_name("SEMESTER")} sem
          ON sem.SEMESTER_ID=co.SEMESTER_ID
        WHERE ac.COMPONENT_ID=?
        """,
        (component_id,),
    )


def get_offering_context(offering_id):
    return fetch_one(
        f"""
        SELECT
            co.OFFERING_ID,
            co.COURSE_ID,
            co.SEMESTER_ID,
            co.SECTION_CODE,
            co.OFFERING_STATUS,
            c.COURSE_CODE,
            c.COURSE_NAME,
            sem.SEMESTER_NAME,
            sem.ACADEMIC_YEAR,
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


def instructor_owns_offering(instructor_id, offering_id):
    row = fetch_one(
        f"""
        SELECT OFFERING_INSTRUCTOR_ID
        FROM {object_name("OFFERING_INSTRUCTOR")}
        WHERE OFFERING_ID=?
          AND INSTRUCTOR_ID=?
        """,
        (offering_id, instructor_id),
    )
    return row is not None


def student_has_offering(student_id, offering_id):
    row = fetch_one(
        f"""
        SELECT ENROLLMENT_ID
        FROM {object_name("ENROLLMENT")}
        WHERE STUDENT_ID=?
          AND OFFERING_ID=?
          AND ENROLLMENT_STATUS IN ('ENROLLED','COMPLETED')
        """,
        (student_id, offering_id),
    )
    return row is not None


def get_exam(exam_id):
    return fetch_one(
        f"""
        SELECT
            ex.EXAM_ID,
            ex.COMPONENT_ID,
            ac.COMPONENT_NAME,
            ac.MAX_MARKS,
            gs.OFFERING_ID,
            co.SECTION_CODE,
            co.OFFERING_STATUS,
            c.COURSE_CODE,
            c.COURSE_NAME,
            sem.SEMESTER_ID,
            sem.SEMESTER_NAME,
            sem.ACADEMIC_YEAR,
            ex.EXAM_TITLE,
            ex.EXAM_TYPE,
            ex.EXAM_DATE,
            ex.START_TIME,
            ex.END_TIME
        FROM {object_name("EXAM")} ex
        JOIN {object_name("ASSESSMENT_COMPONENT")} ac
          ON ac.COMPONENT_ID=ex.COMPONENT_ID
        JOIN {object_name("GRADING_SCHEME")} gs
          ON gs.SCHEME_ID=ac.SCHEME_ID
        JOIN {object_name("COURSE_OFFERING")} co
          ON co.OFFERING_ID=gs.OFFERING_ID
        JOIN {object_name("COURSE")} c
          ON c.COURSE_ID=co.COURSE_ID
        JOIN {object_name("SEMESTER")} sem
          ON sem.SEMESTER_ID=co.SEMESTER_ID
        WHERE ex.EXAM_ID=?
        """,
        (exam_id,),
    )


def get_exam_by_component(component_id):
    return fetch_one(
        f"""
        SELECT EXAM_ID
        FROM {object_name("EXAM")}
        WHERE COMPONENT_ID=?
        """,
        (component_id,),
    )


def create_exam(
    component_id,
    exam_title,
    exam_type,
    exam_date,
    start_time=None,
    end_time=None,
):
    execute(
        f"""
        INSERT INTO {object_name("EXAM")}
        (
            COMPONENT_ID,
            EXAM_TITLE,
            EXAM_TYPE,
            EXAM_DATE,
            START_TIME,
            END_TIME
        )
        VALUES
        (
            ?,
            ?,
            ?,
            TO_DATE(?, 'YYYY-MM-DD'),
            ?,
            ?
        )
        """,
        (
            component_id,
            exam_title,
            exam_type,
            exam_date,
            start_time,
            end_time,
        ),
    )

    row = get_exam_by_component(component_id)
    if not row:
        return None

    return get_exam(row["exam_id"])


def list_exams_for_offering(offering_id):
    return fetch_all(
        f"""
        SELECT
            ex.EXAM_ID,
            ex.COMPONENT_ID,
            ac.COMPONENT_NAME,
            ac.MAX_MARKS,
            gs.OFFERING_ID,
            c.COURSE_CODE,
            c.COURSE_NAME,
            co.SECTION_CODE,
            ex.EXAM_TITLE,
            ex.EXAM_TYPE,
            ex.EXAM_DATE,
            ex.START_TIME,
            ex.END_TIME
        FROM {object_name("EXAM")} ex
        JOIN {object_name("ASSESSMENT_COMPONENT")} ac
          ON ac.COMPONENT_ID=ex.COMPONENT_ID
        JOIN {object_name("GRADING_SCHEME")} gs
          ON gs.SCHEME_ID=ac.SCHEME_ID
        JOIN {object_name("COURSE_OFFERING")} co
          ON co.OFFERING_ID=gs.OFFERING_ID
        JOIN {object_name("COURSE")} c
          ON c.COURSE_ID=co.COURSE_ID
        WHERE gs.OFFERING_ID=?
        ORDER BY ex.EXAM_DATE, ex.START_TIME, ex.EXAM_ID
        """,
        (offering_id,),
    )


def student_upcoming_exams(student_id):
    """Relational equivalent of PR_UPCOMING_EXAMS for the API layer."""
    return fetch_all(
        f"""
        SELECT
            ex.EXAM_ID,
            ex.COMPONENT_ID,
            ac.COMPONENT_NAME,
            co.OFFERING_ID,
            c.COURSE_CODE,
            c.COURSE_NAME,
            co.SECTION_CODE,
            ex.EXAM_TITLE,
            ex.EXAM_TYPE,
            ex.EXAM_DATE,
            ex.START_TIME,
            ex.END_TIME
        FROM {object_name("ENROLLMENT")} e
        JOIN {object_name("COURSE_OFFERING")} co
          ON co.OFFERING_ID=e.OFFERING_ID
        JOIN {object_name("COURSE")} c
          ON c.COURSE_ID=co.COURSE_ID
        JOIN {object_name("GRADING_SCHEME")} gs
          ON gs.OFFERING_ID=co.OFFERING_ID
        JOIN {object_name("ASSESSMENT_COMPONENT")} ac
          ON ac.SCHEME_ID=gs.SCHEME_ID
        JOIN {object_name("EXAM")} ex
          ON ex.COMPONENT_ID=ac.COMPONENT_ID
        WHERE e.STUDENT_ID=?
          AND e.ENROLLMENT_STATUS='ENROLLED'
          AND ex.EXAM_DATE >= TRUNC(SYSDATE)
        ORDER BY ex.EXAM_DATE, ex.START_TIME, ex.EXAM_ID
        """,
        (student_id,),
    )
