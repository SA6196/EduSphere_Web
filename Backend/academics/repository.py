from database.query import (
    fetch_all,
    fetch_one,
    execute,
    execute_procedure,
)
from django.conf import settings
from core.exceptions import NotFoundError, BusinessRuleError
from database.schema import object_name
from .quiz_visibility import quiz_marks_visible_sql, offering_has_hidden_quiz_sql



def student_dashboard(user_id: int):

    user_t = object_name("LMS_USER")
    student_t = object_name("STUDENT")
    enrollment_t = object_name("ENROLLMENT")
    offering_t = object_name("COURSE_OFFERING")
    course_t = object_name("COURSE")
    semester_t = object_name("SEMESTER")
    grade_t = object_name("COURSE_GRADE")

    fn_attendance = object_name(
        "FN_ATTENDANCE_PCT"
    )

    fn_percent = object_name(
        "FN_COURSE_PERCENT"
    )
    hidden_quiz = offering_has_hidden_quiz_sql("co", "e")

    fn_cgpa = object_name(
        "FN_CGPA"
    )


    profile = fetch_one(
        f"""
        SELECT
            s.Student_ID,
            s.Student_Name,
            s.Admission_No,
            s.Batch,
            s.Student_Status,
            {fn_cgpa}(s.Student_ID)
                AS CGPA
        FROM {student_t} s
        JOIN {user_t} u
          ON u.User_ID=s.User_ID
        WHERE u.User_ID=?
        """,
        (user_id,),
    )


    if not profile:
        return None


    courses = fetch_all(
        f"""
        SELECT
            e.Enrollment_ID,
            e.Enrollment_Status,
            co.Offering_ID,
            co.Section_Code,
            co.Offering_Status,
            c.Course_Code,
            c.Course_Name,
            c.Credits,
            sem.Semester_Name,
            sem.Academic_Year,
            CASE WHEN {hidden_quiz} THEN NULL
                 ELSE {fn_percent}(e.Enrollment_ID) END
                AS Course_Percentage,
            {fn_attendance}
                (
                    s.Student_ID,
                    co.Offering_ID
                )
                AS Attendance_Percentage,
            cg.Grade_Code

        FROM {student_t} s

        JOIN {enrollment_t} e
          ON e.Student_ID=s.Student_ID

        JOIN {offering_t} co
          ON co.Offering_ID=e.Offering_ID

        JOIN {course_t} c
          ON c.Course_ID=co.Course_ID

        JOIN {semester_t} sem
          ON sem.Semester_ID=co.Semester_ID

        LEFT JOIN {grade_t} cg
          ON cg.Enrollment_ID=e.Enrollment_ID

        WHERE s.Student_ID=?

        ORDER BY
            sem.Semester_Start_Date DESC,
            c.Course_Code
        """,
        (profile["student_id"],),
    )


    return {
        "profile": profile,
        "courses": courses,
    }

def instructor_offerings(user_id: int):

    return fetch_all(
        f"""
        SELECT

            co.Offering_ID,
            c.Course_Code,
            c.Course_Name,
            co.Section_Code,
            co.Offering_Status,
            co.Capacity

        FROM {object_name("INSTRUCTOR")} i

        JOIN {object_name("OFFERING_INSTRUCTOR")} oi
          ON oi.Instructor_ID=i.Instructor_ID

        JOIN {object_name("COURSE_OFFERING")} co
          ON co.Offering_ID=oi.Offering_ID

        JOIN {object_name("COURSE")} c
          ON c.Course_ID=co.Course_ID

        WHERE i.User_ID=?

        ORDER BY c.Course_Code
        """,
        (user_id,),
    )


def admin_summary():

    return fetch_one(
        f"""
        SELECT

            (SELECT COUNT(*)
             FROM {object_name("LMS_USER")})
             AS Total_Users,


            (SELECT COUNT(*)
             FROM {object_name("STUDENT")})
             AS Total_Students,


            (SELECT COUNT(*)
             FROM {object_name("INSTRUCTOR")})
             AS Total_Instructors,


            (SELECT COUNT(*)
             FROM {object_name("COURSE")})
             AS Total_Courses,


            (SELECT COUNT(*)
             FROM {object_name("COURSE_OFFERING")})
             AS Total_Offerings,


            (SELECT COUNT(*)
             FROM {object_name("ENROLLMENT")}
             WHERE Enrollment_Status
             IN ('ENROLLED','COMPLETED'))
             AS Active_Or_Completed_Enrollments

        FROM DUAL
        """
    )


def list_courses():

    sql = f"""
        SELECT
            COURSE_ID,
            COURSE_CODE,
            COURSE_NAME,
            CREDITS
        FROM {settings.ORACLE_SCHEMA}.COURSE
        ORDER BY COURSE_ID
    """

    return fetch_all(sql)


def list_offerings():

    sql = f"""
        SELECT
            co.Offering_ID,
            c.Course_Code,
            c.Course_Name,
            sem.Semester_Name,
            sem.Academic_Year,
            co.Section_Code,
            co.Capacity,
            co.Offering_Status
        FROM {object_name("COURSE_OFFERING")} co
        JOIN {object_name("COURSE")} c
          ON c.Course_ID = co.Course_ID
        JOIN {object_name("SEMESTER")} sem
          ON sem.Semester_ID = co.Semester_ID
        ORDER BY c.Course_Code
    """

    return fetch_all(sql)


def get_offering(offering_id):

    return fetch_one(
        f"""
        SELECT
            co.Offering_ID,
            c.Course_Code,
            c.Course_Name,
            co.Section_Code,
            co.Capacity,
            co.Offering_Status
        FROM {object_name("COURSE_OFFERING")} co
        JOIN {object_name("COURSE")} c
          ON c.Course_ID = co.Course_ID
        WHERE co.Offering_ID = ?
        """,
        (offering_id,),
    )


# Module 2 - Enrollment
# Fixed: no manual __enter__() or conn.close()

def enroll_student(student_id, offering_id):

    offering = fetch_one(
        f"""
        SELECT
            OFFERING_ID,
            OFFERING_STATUS,
            CAPACITY
        FROM {object_name("COURSE_OFFERING")}
        WHERE OFFERING_ID = ?
        """,
        (offering_id,)
    )


    if offering is None:
        raise Exception(
            "Offering not found."
        )


    if offering["offering_status"] != "OPEN":
        raise Exception(
            "Offering is not open for enrollment."
        )


    existing = fetch_one(
        f"""
        SELECT
            ENROLLMENT_ID
        FROM {object_name("ENROLLMENT")}
        WHERE STUDENT_ID = ?
        AND OFFERING_ID = ?
        """,
        (
            student_id,
            offering_id
        )
    )


    if existing:
        raise Exception(
            "Student is already enrolled in this offering."
        )


    current = fetch_one(
        f"""
        SELECT
            COUNT(*) AS CNT
        FROM {object_name("ENROLLMENT")}
        WHERE OFFERING_ID = ?
        AND ENROLLMENT_STATUS
            IN ('ENROLLED','COMPLETED')
        """,
        (offering_id,)
    )


    if current and current["cnt"] >= offering["capacity"]:
        raise Exception(
            "Offering capacity reached."
        )


    execute_procedure(
        object_name("PR_ENROLL_STUDENT"),
        (
            student_id,
            offering_id,
        )
    )


    return {
        "message": "Enrollment successful",
        "student_id": int(student_id),
        "offering_id": int(offering_id),
    }




def drop_enrollment(student_id, offering_id):
    """Logical enrollment withdrawal, called inside an oracle_transaction().

    Lock the student's enrollment and refuse withdrawal once any academic work
    exists. Preserves all grading/attendance history and the UNIQUE key.
    """
    enrollment = fetch_one(
        f"""
        SELECT e.ENROLLMENT_ID, e.ENROLLMENT_STATUS, co.OFFERING_STATUS
        FROM {object_name('ENROLLMENT')} e
        JOIN {object_name('COURSE_OFFERING')} co ON co.OFFERING_ID=e.OFFERING_ID
        WHERE e.STUDENT_ID=? AND e.OFFERING_ID=?
        FOR UPDATE OF e.ENROLLMENT_STATUS
        """,
        (student_id, offering_id),
    )
    if not enrollment:
        # Do not disclose whether another student's enrollment exists.
        raise NotFoundError("Enrollment not found for this student.")
    if enrollment["enrollment_status"] != "ENROLLED":
        raise BusinessRuleError("Only an active enrollment can be dropped.")
    if enrollment["offering_status"] != "OPEN":
        raise BusinessRuleError("Course withdrawal is permitted only while the offering is OPEN.")

    # EXISTS stops at the first matching row. All joins and parameters are scoped
    # to this authenticated student/offering; no test data is altered here.
    activity = fetch_one(
        f"""
        SELECT CASE WHEN
            EXISTS (
                SELECT 1 FROM {object_name('ATTENDANCE')} a
                JOIN {object_name('CLASS_SESSION')} cs ON cs.SESSION_ID=a.SESSION_ID
                WHERE a.STUDENT_ID=? AND cs.OFFERING_ID=?
            ) OR EXISTS (
                SELECT 1 FROM {object_name('ASSIGNMENT_SUBMISSION')} sub
                JOIN {object_name('ASSIGNMENT')} a ON a.ASSIGNMENT_ID=sub.ASSIGNMENT_ID
                JOIN {object_name('ASSESSMENT_COMPONENT')} ac ON ac.COMPONENT_ID=a.COMPONENT_ID
                JOIN {object_name('GRADING_SCHEME')} gs ON gs.SCHEME_ID=ac.SCHEME_ID
                WHERE sub.STUDENT_ID=? AND gs.OFFERING_ID=?
            ) OR EXISTS (
                SELECT 1 FROM {object_name('QUIZ_ATTEMPT')} qa
                JOIN {object_name('QUIZ')} q ON q.QUIZ_ID=qa.QUIZ_ID
                JOIN {object_name('ASSESSMENT_COMPONENT')} ac ON ac.COMPONENT_ID=q.COMPONENT_ID
                JOIN {object_name('GRADING_SCHEME')} gs ON gs.SCHEME_ID=ac.SCHEME_ID
                WHERE qa.STUDENT_ID=? AND gs.OFFERING_ID=?
            ) OR EXISTS (
                SELECT 1 FROM {object_name('STUDENT_MARK')} sm
                WHERE sm.ENROLLMENT_ID=?
            ) OR EXISTS (
                SELECT 1 FROM {object_name('COURSE_GRADE')} cg
                WHERE cg.ENROLLMENT_ID=?
            ) THEN 1 ELSE 0 END AS HAS_ACTIVITY
        FROM DUAL
        """,
        (student_id, offering_id, student_id, offering_id,
         student_id, offering_id, enrollment["enrollment_id"], enrollment["enrollment_id"]),
    )
    if activity and activity["has_activity"]:
        raise BusinessRuleError(
            "Cannot drop this course after attendance, submissions, quiz attempts, or grades exist."
        )

    changed = execute(
        f"""
        UPDATE {object_name('ENROLLMENT')}
        SET ENROLLMENT_STATUS='DROPPED'
        WHERE ENROLLMENT_ID=? AND STUDENT_ID=? AND ENROLLMENT_STATUS='ENROLLED'
        """,
        (enrollment["enrollment_id"], student_id),
    )
    if changed != 1:
        raise BusinessRuleError("Enrollment status changed; please refresh and try again.")
    return {
        "message": "Course dropped successfully.",
        "enrollment_id": int(enrollment["enrollment_id"]),
        "offering_id": int(offering_id),
        "enrollment_status": "DROPPED",
    }


def my_enrollments(student_id):
    return fetch_all(
        f"""
        SELECT
            e.Enrollment_ID,
            c.Course_Code,
            c.Course_Name,
            e.Enrollment_Status
        FROM {object_name("ENROLLMENT")} e
        JOIN {object_name("COURSE_OFFERING")} co
          ON co.Offering_ID=e.Offering_ID
        JOIN {object_name("COURSE")} c
          ON c.Course_ID=co.Course_ID
        WHERE e.Student_ID=?
        ORDER BY c.Course_Code
        """,
        (student_id,),
    )


def get_student_id_by_user_id(user_id: int):
    row = fetch_one(
        f"""
        SELECT Student_ID
        FROM {object_name("STUDENT")}
        WHERE User_ID=?
        """,
        (user_id,),
    )

    return row["student_id"] if row else None


def get_instructor_id_by_user_id(user_id: int):
    row = fetch_one(
        f"""
        SELECT Instructor_ID
        FROM {object_name("INSTRUCTOR")}
        WHERE User_ID=?
        """,
        (user_id,),
    )

    return row["instructor_id"] if row else None

def record_mark(
    component_id,
    enrollment_id,
    marks_obtained,
    recorded_by_user_id,
    graded_submission_id=None,
):

    execute_procedure(
        object_name("PR_RECORD_MARK"),
        (
            component_id,
            enrollment_id,
            marks_obtained,
            recorded_by_user_id,
            graded_submission_id,
        )
    )

    return {
        "message": "Mark recorded successfully"
    }


def publish_grade(
    enrollment_id,
):

    execute_procedure(
        object_name("PR_PUBLISH_GRADE"),
        (
            enrollment_id,
        )
    )

    return {
        "message": "Grade published successfully"
    }
def student_marks(student_id):
    """Student's marks with semester/course metadata from the *fixed* schema.

    Semester is the semester of the associated course offering, not the month
    in which the mark was recorded. No Oracle DDL changes are needed.
    Quiz rows remain governed by ALLOW_MARK_VIEW.
    """
    can_show_quiz = quiz_marks_visible_sql('q', 'e')
    sql = f"""
        SELECT
            sm.MARK_ID,
            sm.COMPONENT_ID,
            ac.COMPONENT_NAME,
            ac.COMPONENT_TYPE,
            ac.MAX_MARKS,
            sm.MARKS_OBTAINED,
            sm.RECORDED_AT,
            sem.SEMESTER_ID,
            sem.SEMESTER_NAME,
            sem.ACADEMIC_YEAR,
            c.COURSE_CODE,
            c.COURSE_NAME,
            q.QUIZ_ID,
            q.ALLOW_MARK_VIEW
        FROM {object_name("STUDENT_MARK")} sm
        JOIN {object_name("ASSESSMENT_COMPONENT")} ac
          ON ac.COMPONENT_ID=sm.COMPONENT_ID
        JOIN {object_name("GRADING_SCHEME")} gs
          ON gs.SCHEME_ID=ac.SCHEME_ID
        JOIN {object_name("ENROLLMENT")} e
          ON e.ENROLLMENT_ID=sm.ENROLLMENT_ID
         AND e.OFFERING_ID=gs.OFFERING_ID
        JOIN {object_name("COURSE_OFFERING")} co
          ON co.OFFERING_ID=gs.OFFERING_ID
        JOIN {object_name("SEMESTER")} sem
          ON sem.SEMESTER_ID=co.SEMESTER_ID
        JOIN {object_name("COURSE")} c
          ON c.COURSE_ID=co.COURSE_ID
        LEFT JOIN {object_name("QUIZ")} q
          ON q.COMPONENT_ID=ac.COMPONENT_ID
        WHERE e.STUDENT_ID=?
          AND (ac.COMPONENT_TYPE <> 'QUIZ' OR {can_show_quiz})
        ORDER BY sem.SEMESTER_START_DATE DESC, c.COURSE_CODE, sm.COMPONENT_ID
    """
    return fetch_all(sql, (student_id,))



def student_semester_markbook(student_id):
    """Read-only, student-scoped semester markbook using the fixed 37 relations.

    Include semesters in which the student is enrolled even when no marks
    have been recorded. Exams are shown independently of STUDENT_MARK.
    Hidden quiz marks are redacted by SQL, not just by the frontend.
    """
    semesters_sql = f"""
        SELECT DISTINCT
            sem.SEMESTER_ID, sem.SEMESTER_NAME, sem.ACADEMIC_YEAR,
            TO_CHAR(sem.SEMESTER_START_DATE, 'YYYY-MM-DD') AS SEMESTER_START_DATE
        FROM {object_name('ENROLLMENT')} e
        JOIN {object_name('COURSE_OFFERING')} co ON co.OFFERING_ID=e.OFFERING_ID
        JOIN {object_name('SEMESTER')} sem ON sem.SEMESTER_ID=co.SEMESTER_ID
        WHERE e.STUDENT_ID=?
        ORDER BY SEMESTER_START_DATE DESC, sem.SEMESTER_ID DESC
    """
    can_show_quiz = quiz_marks_visible_sql('q', 'e')
    quiz_hidden = f"ac.COMPONENT_TYPE='QUIZ' AND NOT {can_show_quiz}"
    assessments_sql = f"""
        SELECT
            e.ENROLLMENT_ID, co.OFFERING_ID,
            sem.SEMESTER_ID, sem.SEMESTER_NAME, sem.ACADEMIC_YEAR,
            c.COURSE_CODE, c.COURSE_NAME, co.SECTION_CODE,
            ac.COMPONENT_ID, ac.COMPONENT_NAME, ac.COMPONENT_TYPE,
            ac.WEIGHT_PERCENTAGE, ac.MAX_MARKS,
            CASE WHEN {quiz_hidden}
                 THEN NULL ELSE sm.MARKS_OBTAINED END AS MARKS_OBTAINED,
            CASE WHEN {quiz_hidden}
                 THEN NULL ELSE sm.RECORDED_AT END AS RECORDED_AT,
            CASE WHEN {quiz_hidden}
                 THEN 'HIDDEN'
                 WHEN sm.MARK_ID IS NOT NULL THEN 'RECORDED'
                 ELSE 'PENDING' END AS MARK_STATUS,
            ex.EXAM_ID, ex.EXAM_TITLE, ex.EXAM_TYPE,
            TO_CHAR(ex.EXAM_DATE, 'YYYY-MM-DD') AS EXAM_DATE,
            ex.START_TIME, ex.END_TIME,
            CASE WHEN ex.EXAM_ID IS NULL THEN NULL
                 WHEN TRUNC(ex.EXAM_DATE) < TRUNC(SYSDATE) THEN 'PAST_DATE'
                 WHEN TRUNC(ex.EXAM_DATE) = TRUNC(SYSDATE) THEN 'TODAY'
                 ELSE 'UPCOMING' END AS EXAM_STATUS
        FROM {object_name('ENROLLMENT')} e
        JOIN {object_name('COURSE_OFFERING')} co ON co.OFFERING_ID=e.OFFERING_ID
        JOIN {object_name('SEMESTER')} sem ON sem.SEMESTER_ID=co.SEMESTER_ID
        JOIN {object_name('COURSE')} c ON c.COURSE_ID=co.COURSE_ID
        JOIN {object_name('GRADING_SCHEME')} gs ON gs.OFFERING_ID=co.OFFERING_ID
        JOIN {object_name('ASSESSMENT_COMPONENT')} ac ON ac.SCHEME_ID=gs.SCHEME_ID
        LEFT JOIN {object_name('STUDENT_MARK')} sm
               ON sm.COMPONENT_ID=ac.COMPONENT_ID AND sm.ENROLLMENT_ID=e.ENROLLMENT_ID
        LEFT JOIN {object_name('QUIZ')} q ON q.COMPONENT_ID=ac.COMPONENT_ID
        LEFT JOIN {object_name('EXAM')} ex ON ex.COMPONENT_ID=ac.COMPONENT_ID
        WHERE e.STUDENT_ID=?
        ORDER BY sem.SEMESTER_ID, c.COURSE_CODE, co.SECTION_CODE,
                 ac.COMPONENT_TYPE, ex.EXAM_DATE, ac.COMPONENT_ID
    """
    return {
        'semesters': fetch_all(semesters_sql, (student_id,)),
        'components': fetch_all(assessments_sql, (student_id,)),
    }


# -------------------------------------------------
# Frontend-readiness offering / grading helpers
# -------------------------------------------------

def instructor_owns_offering(instructor_id, offering_id):
    if instructor_id is None:
        return False

    row = fetch_one(
        f"""
        SELECT 1 AS AUTHORIZED
        FROM {object_name("OFFERING_INSTRUCTOR")}
        WHERE OFFERING_ID=?
          AND INSTRUCTOR_ID=?
        """,
        (offering_id, instructor_id),
    )
    return row is not None


def student_has_offering(student_id, offering_id):
    if student_id is None:
        return False

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


def get_grading_scheme(offering_id):
    return fetch_one(
        f"""
        SELECT
            gs.SCHEME_ID,
            gs.OFFERING_ID,
            gs.SCHEME_NAME
        FROM {object_name("GRADING_SCHEME")} gs
        WHERE gs.OFFERING_ID=?
        """,
        (offering_id,),
    )


def get_assessment_components(offering_id):
    return fetch_all(
        f"""
        SELECT
            ac.COMPONENT_ID,
            ac.SCHEME_ID,
            ac.COMPONENT_NAME,
            ac.COMPONENT_TYPE,
            ac.WEIGHT_PERCENTAGE,
            ac.MAX_MARKS,
            a.ASSIGNMENT_ID,
            q.QUIZ_ID,
            ex.EXAM_ID,
            CASE
                WHEN ac.COMPONENT_TYPE='ASSIGNMENT' AND a.ASSIGNMENT_ID IS NOT NULL THEN 'Y'
                WHEN ac.COMPONENT_TYPE='QUIZ' AND q.QUIZ_ID IS NOT NULL THEN 'Y'
                WHEN ac.COMPONENT_TYPE='EXAM' AND ex.EXAM_ID IS NOT NULL THEN 'Y'
                WHEN ac.COMPONENT_TYPE='OTHER' THEN 'Y'
                ELSE 'N'
            END AS CONFIGURED
        FROM {object_name("GRADING_SCHEME")} gs
        JOIN {object_name("ASSESSMENT_COMPONENT")} ac
          ON ac.SCHEME_ID=gs.SCHEME_ID
        LEFT JOIN {object_name("ASSIGNMENT")} a
          ON a.COMPONENT_ID=ac.COMPONENT_ID
        LEFT JOIN {object_name("QUIZ")} q
          ON q.COMPONENT_ID=ac.COMPONENT_ID
        LEFT JOIN {object_name("EXAM")} ex
          ON ex.COMPONENT_ID=ac.COMPONENT_ID
        WHERE gs.OFFERING_ID=?
        ORDER BY ac.COMPONENT_ID
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


def get_enrollment_context(enrollment_id):
    return fetch_one(
        f"""
        SELECT
            e.ENROLLMENT_ID,
            e.STUDENT_ID,
            e.OFFERING_ID,
            e.ENROLLMENT_STATUS
        FROM {object_name("ENROLLMENT")} e
        WHERE e.ENROLLMENT_ID=?
        """,
        (enrollment_id,),
    )


def get_component_context(component_id):
    return fetch_one(
        f"""
        SELECT
            ac.COMPONENT_ID,
            ac.COMPONENT_NAME,
            ac.COMPONENT_TYPE,
            ac.MAX_MARKS,
            gs.OFFERING_ID
        FROM {object_name("ASSESSMENT_COMPONENT")} ac
        JOIN {object_name("GRADING_SCHEME")} gs
          ON gs.SCHEME_ID=ac.SCHEME_ID
        WHERE ac.COMPONENT_ID=?
        """,
        (component_id,),
    )
