"""
EduSphere LMS

Admin reporting repository.

The cursor-based Oracle reports use DBMS_OUTPUT for SQL*Plus.  The API layer
uses equivalent SELECT queries so JSON clients receive structured rows.
"""

from database.query import fetch_all, fetch_one
from database.schema import object_name


def admin_overview():
    return fetch_one(
        f"""
        SELECT
            (SELECT COUNT(*) FROM {object_name("LMS_USER")}) AS TOTAL_USERS,
            (SELECT COUNT(*) FROM {object_name("LMS_USER")}
             WHERE ACCOUNT_STATUS='ACTIVE') AS ACTIVE_USERS,
            (SELECT COUNT(*) FROM {object_name("STUDENT")}) AS TOTAL_STUDENTS,
            (SELECT COUNT(*) FROM {object_name("INSTRUCTOR")}) AS TOTAL_INSTRUCTORS,
            (SELECT COUNT(*) FROM {object_name("COURSE")}) AS TOTAL_COURSES,
            (SELECT COUNT(*) FROM {object_name("COURSE_OFFERING")}) AS TOTAL_OFFERINGS,
            (SELECT COUNT(*) FROM {object_name("COURSE_OFFERING")}
             WHERE OFFERING_STATUS='OPEN') AS OPEN_OFFERINGS,
            (SELECT COUNT(*) FROM {object_name("ENROLLMENT")}
             WHERE ENROLLMENT_STATUS='ENROLLED') AS ACTIVE_ENROLLMENTS,
            (SELECT COUNT(*) FROM {object_name("ENROLLMENT")}
             WHERE ENROLLMENT_STATUS='COMPLETED') AS COMPLETED_ENROLLMENTS,
            (SELECT COUNT(*) FROM {object_name("ASSIGNMENT")}) AS TOTAL_ASSIGNMENTS,
            (SELECT COUNT(*) FROM {object_name("QUIZ")}) AS TOTAL_QUIZZES,
            (SELECT COUNT(*) FROM {object_name("EXAM")}) AS TOTAL_EXAMS,
            (SELECT COUNT(*) FROM {object_name("COURSE_GRADE")}) AS PUBLISHED_GRADES,
            (SELECT COUNT(*) FROM {object_name("ANNOUNCEMENT")}) AS TOTAL_ANNOUNCEMENTS,
            (SELECT COUNT(*) FROM {object_name("COURSE_MATERIAL")}) AS TOTAL_MATERIALS
        FROM DUAL
        """
    )


def list_semesters():
    return fetch_all(
        f"""
        SELECT
            SEMESTER_ID,
            SEMESTER_NAME,
            ACADEMIC_YEAR,
            SEMESTER_START_DATE,
            SEMESTER_END_DATE
        FROM {object_name("SEMESTER")}
        ORDER BY SEMESTER_START_DATE, SEMESTER_ID
        """
    )


def get_offering(offering_id):
    return fetch_one(
        f"""
        SELECT
            co.OFFERING_ID,
            c.COURSE_CODE,
            c.COURSE_NAME,
            co.SECTION_CODE,
            co.OFFERING_STATUS,
            sem.SEMESTER_ID,
            sem.SEMESTER_NAME,
            sem.ACADEMIC_YEAR
        FROM {object_name("COURSE_OFFERING")} co
        JOIN {object_name("COURSE")} c
          ON c.COURSE_ID=co.COURSE_ID
        JOIN {object_name("SEMESTER")} sem
          ON sem.SEMESTER_ID=co.SEMESTER_ID
        WHERE co.OFFERING_ID=?
        """,
        (offering_id,),
    )


def offering_roster(offering_id):
    return fetch_all(
        f"""
        SELECT
            e.ENROLLMENT_ID,
            s.STUDENT_ID,
            s.ADMISSION_NO,
            s.STUDENT_NAME,
            s.BATCH,
            s.STUDENT_STATUS,
            e.ENROLLMENT_DATE,
            e.ENROLLMENT_STATUS
        FROM {object_name("ENROLLMENT")} e
        JOIN {object_name("STUDENT")} s
          ON s.STUDENT_ID=e.STUDENT_ID
        WHERE e.OFFERING_ID=?
        ORDER BY s.STUDENT_NAME, s.STUDENT_ID
        """,
        (offering_id,),
    )


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


def student_progress(student_id, semester_id):
    return fetch_all(
        f"""
        SELECT
            e.ENROLLMENT_ID,
            e.ENROLLMENT_STATUS,
            co.OFFERING_ID,
            co.OFFERING_STATUS,
            c.COURSE_CODE,
            c.COURSE_NAME,
            c.CREDITS,
            {object_name("FN_COURSE_PERCENT")}(e.ENROLLMENT_ID)
                AS COURSE_PERCENTAGE,
            {object_name("FN_ATTENDANCE_PCT")}(e.STUDENT_ID, co.OFFERING_ID)
                AS ATTENDANCE_PERCENTAGE,
            cg.GRADE_CODE,
            g.GRADE_POINT,
            cg.PUBLISHED_AT
        FROM {object_name("ENROLLMENT")} e
        JOIN {object_name("COURSE_OFFERING")} co
          ON co.OFFERING_ID=e.OFFERING_ID
        JOIN {object_name("COURSE")} c
          ON c.COURSE_ID=co.COURSE_ID
        LEFT JOIN {object_name("COURSE_GRADE")} cg
          ON cg.ENROLLMENT_ID=e.ENROLLMENT_ID
        LEFT JOIN {object_name("GRADE_SCALE")} g
          ON g.GRADE_CODE=cg.GRADE_CODE
        WHERE e.STUDENT_ID=?
          AND co.SEMESTER_ID=?
        ORDER BY c.COURSE_CODE
        """,
        (student_id, semester_id),
    )


def student_sgpa(student_id, semester_id):
    return fetch_one(
        f"""
        SELECT {object_name("FN_SGPA")}(?, ?) AS SGPA
        FROM DUAL
        """,
        (student_id, semester_id),
    )


def student_cgpa(student_id):
    return fetch_one(
        f"""
        SELECT {object_name("FN_CGPA")}(?) AS CGPA
        FROM DUAL
        """,
        (student_id,),
    )


def student_upcoming_exams(student_id):
    return fetch_all(
        f"""
        SELECT
            ex.EXAM_ID,
            co.OFFERING_ID,
            c.COURSE_CODE,
            c.COURSE_NAME,
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
