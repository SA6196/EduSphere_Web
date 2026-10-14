-- EduSphere LMS - FUNCTIONS
-- Fresh-install object definitions; no migration logic.
SET DEFINE OFF
SET SERVEROUTPUT ON
WHENEVER SQLERROR EXIT SQL.SQLCODE

CREATE OR REPLACE FUNCTION FN_ATTENDANCE_PCT (
    p_Student_ID  IN NUMBER,
    p_Offering_ID IN NUMBER
) RETURN NUMBER
IS
    v_total NUMBER;
    v_attended NUMBER;
BEGIN
    SELECT COUNT(*),
           NVL(SUM(CASE WHEN a.Attendance_Status IN ('PRESENT','LATE')
                        THEN 1 ELSE 0 END), 0)
    INTO v_total, v_attended
    FROM ATTENDANCE a
    JOIN CLASS_SESSION cs ON cs.Session_ID = a.Session_ID
    WHERE a.Student_ID = p_Student_ID
      AND cs.Offering_ID = p_Offering_ID;

    IF v_total = 0 THEN
        RETURN 0;
    END IF;

    RETURN ROUND((v_attended / v_total) * 100, 2);
END;
/
/

CREATE OR REPLACE FUNCTION FN_CGPA (
    p_Student_ID IN NUMBER
) RETURN NUMBER
IS
    v_points NUMBER;
    v_credits NUMBER;
BEGIN
    SELECT NVL(SUM(c.Credits * g.Grade_Point), 0),
           NVL(SUM(c.Credits), 0)
    INTO v_points, v_credits
    FROM COURSE_GRADE cg
    JOIN ENROLLMENT e ON e.Enrollment_ID = cg.Enrollment_ID
    JOIN COURSE_OFFERING co ON co.Offering_ID = e.Offering_ID
    JOIN COURSE c ON c.Course_ID = co.Course_ID
    JOIN GRADE_SCALE g ON g.Grade_Code = cg.Grade_Code
    WHERE e.Student_ID = p_Student_ID;

    IF v_credits = 0 THEN
        RETURN NULL;
    END IF;

    RETURN ROUND(v_points / v_credits, 2);
END;
/
/

CREATE OR REPLACE FUNCTION FN_COURSE_PERCENT (
    p_Enrollment_ID IN NUMBER
) RETURN NUMBER
IS
    v_percentage NUMBER;
BEGIN
    SELECT NVL(SUM((NVL(sm.Marks_Obtained, 0) / ac.Max_Marks)
                   * ac.Weight_Percentage), 0)
    INTO v_percentage
    FROM ENROLLMENT e
    JOIN GRADING_SCHEME gs ON gs.Offering_ID = e.Offering_ID
    JOIN ASSESSMENT_COMPONENT ac ON ac.Scheme_ID = gs.Scheme_ID
    LEFT JOIN STUDENT_MARK sm
      ON sm.Component_ID = ac.Component_ID
     AND sm.Enrollment_ID = e.Enrollment_ID
    WHERE e.Enrollment_ID = p_Enrollment_ID;

    RETURN ROUND(v_percentage, 2);
END;
/
/

CREATE OR REPLACE FUNCTION FN_SCHEME_WEIGHT (
    p_Scheme_ID IN NUMBER
) RETURN NUMBER
IS
    v_total NUMBER;
BEGIN
    SELECT NVL(SUM(Weight_Percentage), 0)
    INTO v_total
    FROM ASSESSMENT_COMPONENT
    WHERE Scheme_ID = p_Scheme_ID;

    RETURN ROUND(v_total, 2);
END;
/
/

CREATE OR REPLACE FUNCTION FN_SGPA (
    p_Student_ID  IN NUMBER,
    p_Semester_ID IN NUMBER
) RETURN NUMBER
IS
    v_points NUMBER;
    v_credits NUMBER;
BEGIN
    SELECT NVL(SUM(c.Credits * g.Grade_Point), 0),
           NVL(SUM(c.Credits), 0)
    INTO v_points, v_credits
    FROM COURSE_GRADE cg
    JOIN ENROLLMENT e ON e.Enrollment_ID = cg.Enrollment_ID
    JOIN COURSE_OFFERING co ON co.Offering_ID = e.Offering_ID
    JOIN COURSE c ON c.Course_ID = co.Course_ID
    JOIN GRADE_SCALE g ON g.Grade_Code = cg.Grade_Code
    WHERE e.Student_ID = p_Student_ID
      AND co.Semester_ID = p_Semester_ID;

    IF v_credits = 0 THEN
        RETURN NULL;
    END IF;

    RETURN ROUND(v_points / v_credits, 2);
END;
/
/
