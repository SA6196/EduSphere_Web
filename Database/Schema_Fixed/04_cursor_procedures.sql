-- EduSphere LMS - EXPLICIT CURSOR PROCEDURES
-- These procedures demonstrate/use explicit PL/SQL cursors.
SET DEFINE OFF
SET SERVEROUTPUT ON
WHENEVER SQLERROR EXIT SQL.SQLCODE

CREATE OR REPLACE PROCEDURE PR_COURSE_ROSTER (
    p_Offering_ID IN NUMBER
)
IS
    CURSOR c_roster IS
        SELECT s.Student_ID,
               s.Admission_No,
               s.Student_Name,
               e.Enrollment_Status
        FROM ENROLLMENT e
        JOIN STUDENT s ON s.Student_ID = e.Student_ID
        WHERE e.Offering_ID = p_Offering_ID
        ORDER BY s.Student_Name;
BEGIN
    DBMS_OUTPUT.PUT_LINE('Student ID | Admission No | Student Name | Status');
    DBMS_OUTPUT.PUT_LINE('---------------------------------------------------------------');

    FOR r IN c_roster LOOP
        DBMS_OUTPUT.PUT_LINE(
            RPAD(TO_CHAR(r.Student_ID), 10) || ' | ' ||
            RPAD(r.Admission_No, 12) || ' | ' ||
            RPAD(r.Student_Name, 25) || ' | ' ||
            r.Enrollment_Status
        );
    END LOOP;
END;
/
/

CREATE OR REPLACE PROCEDURE PR_STUDENT_PROGRESS (
    p_Student_ID IN NUMBER,
    p_Semester_ID IN NUMBER
)
IS
    CURSOR c_progress IS
        SELECT e.Enrollment_ID,
               co.Offering_ID,
               c.Course_Code,
               c.Course_Name,
               NVL(cg.Grade_Code, '-') AS Grade_Code
        FROM ENROLLMENT e
        JOIN COURSE_OFFERING co ON co.Offering_ID = e.Offering_ID
        JOIN COURSE c ON c.Course_ID = co.Course_ID
        LEFT JOIN COURSE_GRADE cg ON cg.Enrollment_ID = e.Enrollment_ID
        WHERE e.Student_ID = p_Student_ID
          AND co.Semester_ID = p_Semester_ID
        ORDER BY c.Course_Code;
BEGIN
    DBMS_OUTPUT.PUT_LINE('Course | Percentage | Attendance | Grade');
    DBMS_OUTPUT.PUT_LINE('---------------------------------------------------------------');

    FOR r IN c_progress LOOP
        DBMS_OUTPUT.PUT_LINE(
            RPAD(r.Course_Code, 12) || ' | ' ||
            LPAD(TO_CHAR(FN_COURSE_PERCENT(r.Enrollment_ID), '990.00'), 10) || ' | ' ||
            LPAD(TO_CHAR(FN_ATTENDANCE_PCT(p_Student_ID, r.Offering_ID), '990.00'), 10) || ' | ' ||
            r.Grade_Code
        );
    END LOOP;

    DBMS_OUTPUT.PUT_LINE(
        'SGPA = ' || NVL(
            TO_CHAR(FN_SGPA(p_Student_ID, p_Semester_ID), '990.00'),
            'Not available'
        )
    );
END;
/
/

CREATE OR REPLACE PROCEDURE PR_UPCOMING_EXAMS (
    p_Student_ID IN NUMBER
)
IS
    CURSOR c_exams IS
        SELECT c.Course_Code,
               ex.Exam_Title,
               ex.Exam_Type,
               ex.Exam_Date,
               ex.Start_Time,
               ex.End_Time
        FROM ENROLLMENT e
        JOIN COURSE_OFFERING co ON co.Offering_ID = e.Offering_ID
        JOIN COURSE c ON c.Course_ID = co.Course_ID
        JOIN GRADING_SCHEME gs ON gs.Offering_ID = co.Offering_ID
        JOIN ASSESSMENT_COMPONENT ac ON ac.Scheme_ID = gs.Scheme_ID
        JOIN EXAM ex ON ex.Component_ID = ac.Component_ID
        WHERE e.Student_ID = p_Student_ID
          AND e.Enrollment_Status = 'ENROLLED'
          AND ex.Exam_Date >= TRUNC(SYSDATE)
        ORDER BY ex.Exam_Date, ex.Start_Time;
BEGIN
    DBMS_OUTPUT.PUT_LINE('Course | Exam | Type | Date | Time');
    DBMS_OUTPUT.PUT_LINE('---------------------------------------------------------------');

    FOR r IN c_exams LOOP
        DBMS_OUTPUT.PUT_LINE(
            RPAD(r.Course_Code, 10) || ' | ' ||
            RPAD(r.Exam_Title, 20) || ' | ' ||
            RPAD(r.Exam_Type, 10) || ' | ' ||
            TO_CHAR(r.Exam_Date, 'DD-MON-YYYY') || ' | ' ||
            NVL(r.Start_Time, '--:--') || '-' || NVL(r.End_Time, '--:--')
        );
    END LOOP;
END;
/
/
