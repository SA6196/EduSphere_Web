"""EduSphere LMS - GPA / SGPA / CGPA repository."""

from database.query import fetch_all, fetch_one
from database.schema import object_name


def get_student(student_id):
    return fetch_one(
        f"""
        SELECT
            s.STUDENT_ID,
            s.STUDENT_NAME,
            s.ADMISSION_NO,
            s.BATCH,
            s.STUDENT_STATUS,
            u.USERNAME
        FROM {object_name("STUDENT")} s
        JOIN {object_name("LMS_USER")} u
          ON u.USER_ID=s.USER_ID
        WHERE s.STUDENT_ID=?
        """,
        (student_id,),
    )


def get_semester(semester_id):
    return fetch_one(
        f"""
        SELECT
            SEMESTER_ID,
            SEMESTER_NAME,
            ACADEMIC_YEAR,
            SEMESTER_START_DATE,
            SEMESTER_END_DATE
        FROM {object_name("SEMESTER")}
        WHERE SEMESTER_ID=?
        """,
        (semester_id,),
    )


def get_cgpa(student_id):
    return fetch_one(
        f"""
        SELECT {object_name("FN_CGPA")}(?) AS CGPA
        FROM DUAL
        """,
        (student_id,),
    )


def get_sgpa(student_id, semester_id):
    return fetch_one(
        f"""
        SELECT {object_name("FN_SGPA")}(?, ?) AS SGPA
        FROM DUAL
        """,
        (student_id, semester_id),
    )


def get_sgpa_for_published_semesters(student_id):
    """Return all DB-calculated SGPA values in one round trip."""
    return fetch_all(
        f"""
        SELECT
            sem.SEMESTER_ID,
            {object_name("FN_SGPA")}(?, sem.SEMESTER_ID) AS SGPA
        FROM {object_name("SEMESTER")} sem
        WHERE EXISTS (
            SELECT 1
            FROM {object_name("COURSE_GRADE")} cg
            JOIN {object_name("ENROLLMENT")} e
              ON e.ENROLLMENT_ID=cg.ENROLLMENT_ID
            JOIN {object_name("COURSE_OFFERING")} co
              ON co.OFFERING_ID=e.OFFERING_ID
            WHERE e.STUDENT_ID=?
              AND co.SEMESTER_ID=sem.SEMESTER_ID
        )
        ORDER BY sem.SEMESTER_START_DATE, sem.SEMESTER_ID
        """,
        (student_id, student_id),
    )


def published_grade_rows(student_id, semester_id=None):
    sql = f"""
        SELECT
            cg.COURSE_GRADE_ID,
            cg.PUBLISHED_AT,
            e.ENROLLMENT_ID,
            e.ENROLLMENT_STATUS,
            co.OFFERING_ID,
            sem.SEMESTER_ID,
            sem.SEMESTER_NAME,
            sem.ACADEMIC_YEAR,
            c.COURSE_ID,
            c.COURSE_CODE,
            c.COURSE_NAME,
            c.CREDITS,
            cg.GRADE_CODE,
            g.GRADE_POINT,
            (c.CREDITS * g.GRADE_POINT) AS WEIGHTED_POINTS
        FROM {object_name("COURSE_GRADE")} cg
        JOIN {object_name("ENROLLMENT")} e
          ON e.ENROLLMENT_ID=cg.ENROLLMENT_ID
        JOIN {object_name("COURSE_OFFERING")} co
          ON co.OFFERING_ID=e.OFFERING_ID
        JOIN {object_name("SEMESTER")} sem
          ON sem.SEMESTER_ID=co.SEMESTER_ID
        JOIN {object_name("COURSE")} c
          ON c.COURSE_ID=co.COURSE_ID
        JOIN {object_name("GRADE_SCALE")} g
          ON g.GRADE_CODE=cg.GRADE_CODE
        WHERE e.STUDENT_ID=?
    """
    params = [student_id]

    if semester_id is not None:
        sql += " AND sem.SEMESTER_ID=?"
        params.append(semester_id)

    sql += " ORDER BY sem.SEMESTER_START_DATE, c.COURSE_CODE"
    return fetch_all(sql, tuple(params))
