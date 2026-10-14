from database.connection import (
    fetch_all,
    fetch_one,
    execute,
    call_procedure_no_out,
)
from database.schema import object_name


def student_dashboard(user_id: int):
    user_t = object_name("LMS_USER")
    student_t = object_name("STUDENT")
    enrollment_t = object_name("ENROLLMENT")
    offering_t = object_name("COURSE_OFFERING")
    course_t = object_name("COURSE")
    semester_t = object_name("SEMESTER")
    session_t = object_name("CLASS_SESSION")
    attendance_t = object_name("ATTENDANCE")
    grade_t = object_name("COURSE_GRADE")
    fn_attendance = object_name("FN_ATTENDANCE_PCT")
    fn_percent = object_name("FN_COURSE_PERCENT")
    fn_cgpa = object_name("FN_CGPA")

    profile = fetch_one(
        f"""
        SELECT
            s.Student_ID,
            s.Student_Name,
            s.Admission_No,
            s.Batch,
            s.Student_Status,
            {fn_cgpa}(s.Student_ID) AS CGPA
        FROM {student_t} s
        JOIN {user_t} u ON u.User_ID=s.User_ID
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
            sem.Semester_ID,
            sem.Semester_Name,
            sem.Academic_Year,
            {fn_percent}(e.Enrollment_ID) AS Course_Percentage,
            {fn_attendance}(s.Student_ID, co.Offering_ID) AS Attendance_Percentage,
            cg.Grade_Code
        FROM {student_t} s
        JOIN {enrollment_t} e ON e.Student_ID=s.Student_ID
        JOIN {offering_t} co ON co.Offering_ID=e.Offering_ID
        JOIN {course_t} c ON c.Course_ID=co.Course_ID
        JOIN {semester_t} sem ON sem.Semester_ID=co.Semester_ID
        LEFT JOIN {grade_t} cg ON cg.Enrollment_ID=e.Enrollment_ID
        WHERE s.Student_ID=?
        ORDER BY sem.Semester_Start_Date DESC, c.Course_Code
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
        SELECT *
        FROM {object_name("COURSE_OFFERING")}
        """
    )


def admin_summary():
    return fetch_one(
        f"""
        SELECT
            (SELECT COUNT(*) FROM {object_name("LMS_USER")}) AS Total_Users,
            (SELECT COUNT(*) FROM {object_name("STUDENT")}) AS Total_Students,
            (SELECT COUNT(*) FROM {object_name("INSTRUCTOR")}) AS Total_Instructors,
            (SELECT COUNT(*) FROM {object_name("COURSE")}) AS Total_Courses,
            (SELECT COUNT(*) FROM {object_name("COURSE_OFFERING")}) AS Total_Offerings,
            (SELECT COUNT(*) FROM {object_name("ENROLLMENT")}
             WHERE Enrollment_Status IN ('ENROLLED','COMPLETED'))
             AS Active_Or_Completed_Enrollments
        FROM DUAL
        """
    )


def list_courses():
    return fetch_all(
        f"""
        SELECT Course_ID, Course_Code, Course_Name, Credits
        FROM {object_name("COURSE")}
        ORDER BY Course_Code
        """
    )


def list_offerings():
    return fetch_all(
        f"""
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
          ON c.Course_ID=co.Course_ID
        JOIN {object_name("SEMESTER")} sem
          ON sem.Semester_ID=co.Semester_ID
        ORDER BY c.Course_Code
        """
    )


def get_offering(offering_id):
    rows = fetch_all(
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
          ON c.Course_ID=co.Course_ID
        WHERE co.Offering_ID=?
        """,
        (offering_id,),
    )

    return rows[0] if rows else None


# Module 2 - Enrollment
# Fixed: no manual __enter__() or conn.close()
def enroll_student(student_id, offering_id):

    offering = fetch_one(
        """
        SELECT OFFERING_ID,OFFERING_STATUS,CAPACITY
        FROM EDUSPHERE_OWNER.COURSE_OFFERING
        WHERE OFFERING_ID = ?
        """,
        (offering_id,)
    )

    if offering is None:
        raise Exception(
            "Offering not found."
        )
    if offering["offering_status"] != "OPEN":
        raise Exception("Offering is not open for enrollment.")


    existing = fetch_one(
        """
        SELECT ENROLLMENT_ID
        FROM EDUSPHERE_OWNER.ENROLLMENT
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
        """
        SELECT COUNT(*) AS CNT
        FROM EDUSPHERE_OWNER.ENROLLMENT
        WHERE OFFERING_ID = ?
        AND ENROLLMENT_STATUS IN ('ENROLLED','COMPLETED')
        """,
        (offering_id,)
    )

    if current and current["cnt"] >= offering["capacity"]:
        raise Exception(
            "Offering capacity reached."
        )


    call_procedure_no_out(
        "EDUSPHERE_OWNER.PR_ENROLL_STUDENT",
        (
            student_id,
            offering_id,
        )
    )


    return {
        "message": "Enrollment successful",
        "student_id": student_id,
        "offering_id": offering_id
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
