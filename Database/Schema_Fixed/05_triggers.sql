-- EduSphere LMS - TRIGGERS
-- Final trigger definitions consolidated from the project hardening/runtime rules.
-- No ALTER/DROP/upgrade operations.
SET DEFINE OFF
SET SERVEROUTPUT ON
WHENEVER SQLERROR EXIT SQL.SQLCODE

CREATE OR REPLACE TRIGGER TRG_ADMIN_ROLE
BEFORE INSERT OR UPDATE OF User_ID ON ADMIN
FOR EACH ROW
DECLARE
    v_role LMS_USER.Role%TYPE;
BEGIN
    SELECT Role INTO v_role FROM LMS_USER WHERE User_ID = :NEW.User_ID;
    IF v_role <> 'ADMIN' THEN
        RAISE_APPLICATION_ERROR(-20005, 'LMS_USER role must be ADMIN.');
    END IF;
EXCEPTION
    WHEN NO_DATA_FOUND THEN
        RAISE_APPLICATION_ERROR(-20006, 'Referenced LMS_USER does not exist.');
END;
/
/

CREATE OR REPLACE TRIGGER TRG_ANNOUNCE_AUTH
BEFORE INSERT OR UPDATE OF Offering_ID, Posted_By_User_ID
ON ANNOUNCEMENT
FOR EACH ROW
DECLARE
    v_role          LMS_USER.Role%TYPE;
    v_status        LMS_USER.Account_Status%TYPE;
    v_instructor_id NUMBER;
    v_count         NUMBER;
BEGIN
    SELECT Role, Account_Status
    INTO v_role, v_status
    FROM LMS_USER
    WHERE User_ID = :NEW.Posted_By_User_ID;

    IF v_status <> 'ACTIVE' THEN
        RAISE_APPLICATION_ERROR(-20309,
            'Only an ACTIVE LMS account can post announcements.');
    END IF;

    IF v_role = 'ADMIN' THEN
        NULL;
    ELSIF v_role = 'INSTRUCTOR' THEN
        SELECT Instructor_ID
        INTO v_instructor_id
        FROM INSTRUCTOR
        WHERE User_ID = :NEW.Posted_By_User_ID;

        SELECT COUNT(*)
        INTO v_count
        FROM OFFERING_INSTRUCTOR
        WHERE Offering_ID = :NEW.Offering_ID
          AND Instructor_ID = v_instructor_id;

        IF v_count = 0 THEN
            RAISE_APPLICATION_ERROR(-20024,
                'Instructor is not assigned to this offering.');
        END IF;
    ELSE
        RAISE_APPLICATION_ERROR(-20025,
            'Only an assigned instructor or admin can post announcements.');
    END IF;
END;
/
/

CREATE OR REPLACE TRIGGER TRG_ASSIGNMENT_SEMESTER_DATE
BEFORE INSERT OR UPDATE OF Component_ID, Due_Date ON ASSIGNMENT
FOR EACH ROW
DECLARE
    v_start DATE;
    v_end   DATE;
BEGIN
    SELECT s.Semester_Start_Date, s.Semester_End_Date
    INTO v_start, v_end
    FROM ASSESSMENT_COMPONENT ac
    JOIN GRADING_SCHEME gs ON gs.Scheme_ID = ac.Scheme_ID
    JOIN COURSE_OFFERING co ON co.Offering_ID = gs.Offering_ID
    JOIN SEMESTER s ON s.Semester_ID = co.Semester_ID
    WHERE ac.Component_ID = :NEW.Component_ID;

    IF CAST(:NEW.Due_Date AS DATE) < v_start
       OR CAST(:NEW.Due_Date AS DATE) >= v_end + 1 THEN
        RAISE_APPLICATION_ERROR(-20319,
            'Assignment Due_Date must lie inside the offering semester.');
    END IF;
END;
/
/

CREATE OR REPLACE TRIGGER TRG_ASSIGN_SUBMIT
BEFORE INSERT OR UPDATE OF Assignment_ID, Student_ID,
                           Submission_Version, Submitted_At,
                           Submission_Status
ON ASSIGNMENT_SUBMISSION
FOR EACH ROW
DECLARE
    v_offering_id NUMBER;
    v_allow       CHAR(1);
    v_due_date    ASSIGNMENT.Due_Date%TYPE;
    v_count       NUMBER;
BEGIN
    SELECT gs.Offering_ID, a.Allow_Resubmission, a.Due_Date
    INTO v_offering_id, v_allow, v_due_date
    FROM ASSIGNMENT a
    JOIN ASSESSMENT_COMPONENT ac
      ON ac.Component_ID = a.Component_ID
    JOIN GRADING_SCHEME gs
      ON gs.Scheme_ID = ac.Scheme_ID
    WHERE a.Assignment_ID = :NEW.Assignment_ID;

    SELECT COUNT(*)
    INTO v_count
    FROM ENROLLMENT
    WHERE Student_ID = :NEW.Student_ID
      AND Offering_ID = v_offering_id
      AND Enrollment_Status = 'ENROLLED';

    IF v_count = 0 THEN
        RAISE_APPLICATION_ERROR(-20014,
            'Student is not actively enrolled in the assignment offering.');
    END IF;

    IF :NEW.Submission_Version > 1 AND v_allow <> 'Y' THEN
        RAISE_APPLICATION_ERROR(-20015,
            'Resubmission is not allowed for this assignment.');
    END IF;

    IF :NEW.Submitted_At > SYSTIMESTAMP THEN
        RAISE_APPLICATION_ERROR(-20316,
            'Submitted_At cannot be in the future.');
    END IF;

    IF :NEW.Submitted_At > v_due_date THEN
        :NEW.Submission_Status := 'LATE';
    END IF;
END;
/
/

CREATE OR REPLACE TRIGGER TRG_ASSIGN_TYPE
BEFORE INSERT OR UPDATE OF Component_ID ON ASSIGNMENT
FOR EACH ROW
DECLARE
    v_type ASSESSMENT_COMPONENT.Component_Type%TYPE;
BEGIN
    SELECT Component_Type INTO v_type
    FROM ASSESSMENT_COMPONENT
    WHERE Component_ID = :NEW.Component_ID;

    IF v_type <> 'ASSIGNMENT' THEN
        RAISE_APPLICATION_ERROR(-20011, 'Component_Type must be ASSIGNMENT.');
    END IF;
END;
/
/

CREATE OR REPLACE TRIGGER TRG_ATTEMPT_SEQUENCE
FOR INSERT OR UPDATE OF Quiz_ID, Student_ID, Attempt_No OR DELETE
ON QUIZ_ATTEMPT
COMPOUND TRIGGER
    AFTER STATEMENT IS
        v_bad NUMBER;
    BEGIN
        SELECT COUNT(*)
        INTO v_bad
        FROM (
            SELECT Quiz_ID, Student_ID
            FROM QUIZ_ATTEMPT
            GROUP BY Quiz_ID, Student_ID
            HAVING MIN(Attempt_No) <> 1
               OR MAX(Attempt_No) <> COUNT(*)
        );

        IF v_bad > 0 THEN
            RAISE_APPLICATION_ERROR(-20314,
                'Quiz Attempt_No values must be continuous starting at 1.');
        END IF;
    END AFTER STATEMENT;
END TRG_ATTEMPT_SEQUENCE;
/
/

CREATE OR REPLACE TRIGGER TRG_ATTEND_ENROLL
BEFORE INSERT OR UPDATE
ON ATTENDANCE
FOR EACH ROW
DECLARE
    v_offering_id   NUMBER;
    v_count         NUMBER;
    v_actor         NUMBER;
    v_role          LMS_USER.Role%TYPE;
    v_account_status LMS_USER.Account_Status%TYPE;
    v_instructor_id NUMBER;
BEGIN
    SELECT Offering_ID INTO v_offering_id
    FROM CLASS_SESSION
    WHERE Session_ID=:NEW.Session_ID;

    SELECT COUNT(*) INTO v_count
    FROM ENROLLMENT
    WHERE Student_ID=:NEW.Student_ID
      AND Offering_ID=v_offering_id
      AND Enrollment_Status IN ('ENROLLED','COMPLETED');

    IF v_count=0 THEN
        RAISE_APPLICATION_ERROR(-20010,
            'Attendance cannot be recorded: student is not enrolled in this offering.');
    END IF;

    IF INSERTING THEN
        IF :NEW.Recorded_By_User_ID IS NULL THEN
            RAISE_APPLICATION_ERROR(-20410,
                'Recorded_By_User_ID is required for attendance creation.');
        END IF;
        v_actor:=:NEW.Recorded_By_User_ID;
        :NEW.Recorded_At:=NVL(:NEW.Recorded_At,SYSTIMESTAMP);
        :NEW.Updated_By_User_ID:=NULL;
        :NEW.Updated_At:=NULL;
    ELSE
        IF :NEW.Session_ID<>:OLD.Session_ID OR :NEW.Student_ID<>:OLD.Student_ID THEN
            RAISE_APPLICATION_ERROR(-20424,
                'Attendance Session_ID and Student_ID are immutable; update the status instead.');
        END IF;
        IF :NEW.Updated_By_User_ID IS NULL THEN
            RAISE_APPLICATION_ERROR(-20410,
                'Updated_By_User_ID is required for attendance changes.');
        END IF;
        -- Preserve who originally created the attendance record.
        :NEW.Recorded_By_User_ID:=:OLD.Recorded_By_User_ID;
        :NEW.Recorded_At:=:OLD.Recorded_At;
        v_actor:=:NEW.Updated_By_User_ID;
        :NEW.Updated_At:=SYSTIMESTAMP;
    END IF;

    SELECT Role,Account_Status
    INTO v_role,v_account_status
    FROM LMS_USER
    WHERE User_ID=v_actor;

    IF v_account_status<>'ACTIVE' THEN
        RAISE_APPLICATION_ERROR(-20411,
            'Attendance recorder/updater LMS account must be ACTIVE.');
    END IF;

    IF v_role='ADMIN' THEN
        NULL;
    ELSIF v_role='INSTRUCTOR' THEN
        SELECT Instructor_ID INTO v_instructor_id
        FROM INSTRUCTOR
        WHERE User_ID=v_actor;

        SELECT COUNT(*) INTO v_count
        FROM OFFERING_INSTRUCTOR
        WHERE Offering_ID=v_offering_id
          AND Instructor_ID=v_instructor_id;

        IF v_count=0 THEN
            RAISE_APPLICATION_ERROR(-20411,
                'Instructor is not assigned to this attendance offering.');
        END IF;
    ELSE
        RAISE_APPLICATION_ERROR(-20411,
            'Only an assigned instructor or admin may record attendance.');
    END IF;
END;
/
/

CREATE OR REPLACE TRIGGER TRG_COMPONENT_PARENT_GUARD
BEFORE UPDATE OF Component_Type, Max_Marks ON ASSESSMENT_COMPONENT
FOR EACH ROW
DECLARE
    v_assign NUMBER;
    v_quiz   NUMBER;
    v_exam   NUMBER;
    v_mark_max NUMBER;
    v_quiz_sum NUMBER;
BEGIN
    SELECT COUNT(*) INTO v_assign
    FROM ASSIGNMENT WHERE Component_ID=:OLD.Component_ID;

    SELECT COUNT(*) INTO v_quiz
    FROM QUIZ WHERE Component_ID=:OLD.Component_ID;

    SELECT COUNT(*) INTO v_exam
    FROM EXAM WHERE Component_ID=:OLD.Component_ID;

    IF UPDATING('Component_Type') THEN
        IF v_assign>0 AND :NEW.Component_Type <> 'ASSIGNMENT' THEN
            RAISE_APPLICATION_ERROR(-20331,
                'Component_Type cannot contradict an existing ASSIGNMENT child.');
        END IF;
        IF v_quiz>0 AND :NEW.Component_Type <> 'QUIZ' THEN
            RAISE_APPLICATION_ERROR(-20332,
                'Component_Type cannot contradict an existing QUIZ child.');
        END IF;
        IF v_exam>0 AND :NEW.Component_Type <> 'EXAM' THEN
            RAISE_APPLICATION_ERROR(-20333,
                'Component_Type cannot contradict an existing EXAM child.');
        END IF;
    END IF;

    IF UPDATING('Max_Marks') THEN
        SELECT NVL(MAX(Marks_Obtained),0)
        INTO v_mark_max
        FROM STUDENT_MARK
        WHERE Component_ID=:OLD.Component_ID;

        IF :NEW.Max_Marks < v_mark_max THEN
            RAISE_APPLICATION_ERROR(-20334,
                'Max_Marks cannot be reduced below an existing student mark.');
        END IF;

        IF v_quiz > 0 THEN
            SELECT NVL(SUM(qq.Question_Marks),0)
            INTO v_quiz_sum
            FROM QUIZ q
            LEFT JOIN QUIZ_QUESTION qq ON qq.Quiz_ID=q.Quiz_ID
            WHERE q.Component_ID=:OLD.Component_ID;

            IF :NEW.Max_Marks < v_quiz_sum THEN
                RAISE_APPLICATION_ERROR(-20335,
                    'Quiz component Max_Marks cannot be below total question marks.');
            END IF;
        END IF;
    END IF;
END;
/
/

CREATE OR REPLACE TRIGGER TRG_COMPONENT_WEIGHT_CAP
FOR INSERT OR UPDATE OF Scheme_ID, Weight_Percentage OR DELETE
ON ASSESSMENT_COMPONENT
COMPOUND TRIGGER

    TYPE t_scheme_set IS TABLE OF BOOLEAN INDEX BY VARCHAR2(100);
    g_schemes t_scheme_set;

    AFTER EACH ROW IS
        v_key VARCHAR2(100);
    BEGIN
        IF INSERTING OR UPDATING THEN
            v_key := TO_CHAR(:NEW.Scheme_ID);
            g_schemes(v_key) := TRUE;
        END IF;

        IF DELETING OR UPDATING THEN
            v_key := TO_CHAR(:OLD.Scheme_ID);
            g_schemes(v_key) := TRUE;
        END IF;
    END AFTER EACH ROW;

    AFTER STATEMENT IS
        v_key   VARCHAR2(100);
        v_total NUMBER;
    BEGIN
        v_key := g_schemes.FIRST;

        WHILE v_key IS NOT NULL LOOP
            SELECT NVL(SUM(Weight_Percentage), 0)
            INTO v_total
            FROM ASSESSMENT_COMPONENT
            WHERE Scheme_ID = TO_NUMBER(v_key);

            IF v_total > 100 THEN
                RAISE_APPLICATION_ERROR(
                    -20204,
                    'Total assessment-component weight cannot exceed 100 percent.'
                );
            END IF;

            v_key := g_schemes.NEXT(v_key);
        END LOOP;
    END AFTER STATEMENT;

END TRG_COMPONENT_WEIGHT_CAP;
/
/

CREATE OR REPLACE TRIGGER TRG_COURSE_GRADE_STATUS
BEFORE INSERT OR UPDATE OF Enrollment_ID, Grade_Code ON COURSE_GRADE
FOR EACH ROW
DECLARE
    v_status          ENROLLMENT.Enrollment_Status%TYPE;
    v_offering_id     ENROLLMENT.Offering_ID%TYPE;
    v_offering_status COURSE_OFFERING.Offering_Status%TYPE;
    v_percentage      NUMBER;
    v_expected        GRADE_SCALE.Grade_Code%TYPE;
BEGIN
    SELECT Enrollment_Status, Offering_ID
    INTO v_status, v_offering_id
    FROM ENROLLMENT
    WHERE Enrollment_ID = :NEW.Enrollment_ID;

    IF v_status <> 'COMPLETED' THEN
        RAISE_APPLICATION_ERROR(-20207,
            'Final course grade requires Enrollment_Status = COMPLETED.');
    END IF;

    SELECT Offering_Status
    INTO v_offering_status
    FROM COURSE_OFFERING
    WHERE Offering_ID = v_offering_id;

    IF INSERTING AND v_offering_status NOT IN ('CLOSED','COMPLETED') THEN
        RAISE_APPLICATION_ERROR(-20328,
            'New final grade requires a CLOSED or COMPLETED offering.');
    END IF;

    v_percentage := FN_COURSE_PERCENT(:NEW.Enrollment_ID);

    SELECT Grade_Code
    INTO v_expected
    FROM (
        SELECT Grade_Code
        FROM GRADE_SCALE
        WHERE v_percentage BETWEEN Min_Percentage AND Max_Percentage
        ORDER BY Min_Percentage DESC
    )
    WHERE ROWNUM = 1;

    IF :NEW.Grade_Code <> v_expected THEN
        RAISE_APPLICATION_ERROR(-20329,
            'Grade_Code does not match the current calculated course percentage.');
    END IF;
END;
/
/

CREATE OR REPLACE TRIGGER TRG_ENROLLMENT_GUARD
FOR INSERT OR UPDATE OF Student_ID, Offering_ID,
                         Enrollment_Date, Enrollment_Status
ON ENROLLMENT
COMPOUND TRIGGER

    TYPE t_offer_set IS TABLE OF BOOLEAN INDEX BY VARCHAR2(100);
    g_offers t_offer_set;

    BEFORE EACH ROW IS
        v_status          COURSE_OFFERING.Offering_Status%TYPE;
        v_capacity        COURSE_OFFERING.Capacity%TYPE;
        v_sem_end         SEMESTER.Semester_End_Date%TYPE;
        v_student_status  STUDENT.Student_Status%TYPE;
        v_account_status  LMS_USER.Account_Status%TYPE;
        v_key             VARCHAR2(100);
    BEGIN
        IF :NEW.Enrollment_Status IN ('ENROLLED','COMPLETED') THEN
            SELECT co.Offering_Status,
                   co.Capacity,
                   s.Semester_End_Date
            INTO v_status, v_capacity, v_sem_end
            FROM COURSE_OFFERING co
            JOIN SEMESTER s ON s.Semester_ID=co.Semester_ID
            WHERE co.Offering_ID=:NEW.Offering_ID
            FOR UPDATE;

            IF :NEW.Enrollment_Status='ENROLLED'
               AND v_status<>'OPEN' THEN
                RAISE_APPLICATION_ERROR(-20202,
                    'Direct enrollment is allowed only for an OPEN course offering.');
            END IF;

            SELECT st.Student_Status,u.Account_Status
            INTO v_student_status,v_account_status
            FROM STUDENT st
            JOIN LMS_USER u ON u.User_ID=st.User_ID
            WHERE st.Student_ID=:NEW.Student_ID;

            IF :NEW.Enrollment_Status='ENROLLED'
               AND v_student_status<>'ACTIVE' THEN
                RAISE_APPLICATION_ERROR(-20305,
                    'Only an ACTIVE student may have an ENROLLED record.');
            END IF;

            IF :NEW.Enrollment_Status='ENROLLED'
               AND v_account_status<>'ACTIVE' THEN
                RAISE_APPLICATION_ERROR(-20306,
                    'Student LMS account must be ACTIVE for enrollment.');
            END IF;

            -- V5: registration before Semester_Start_Date is allowed.
            -- Only a registration dated after the semester has ended is invalid.
            IF TRUNC(:NEW.Enrollment_Date)>TRUNC(v_sem_end) THEN
                RAISE_APPLICATION_ERROR(-20307,
                    'Enrollment_Date cannot be after the offering semester end date.');
            END IF;

            v_key:=TO_CHAR(:NEW.Offering_ID);
            g_offers(v_key):=TRUE;
        END IF;
    END BEFORE EACH ROW;

    AFTER STATEMENT IS
        v_key      VARCHAR2(100);
        v_capacity COURSE_OFFERING.Capacity%TYPE;
        v_count    NUMBER;
        v_offer    NUMBER;
    BEGIN
        v_key:=g_offers.FIRST;
        WHILE v_key IS NOT NULL LOOP
            v_offer:=TO_NUMBER(v_key);

            SELECT Capacity INTO v_capacity
            FROM COURSE_OFFERING
            WHERE Offering_ID=v_offer;

            SELECT COUNT(*) INTO v_count
            FROM ENROLLMENT
            WHERE Offering_ID=v_offer
              AND Enrollment_Status IN ('ENROLLED','COMPLETED');

            IF v_count>v_capacity THEN
                RAISE_APPLICATION_ERROR(-20203,
                    'Enrollment would exceed COURSE_OFFERING capacity.');
            END IF;

            v_key:=g_offers.NEXT(v_key);
        END LOOP;
    END AFTER STATEMENT;
END TRG_ENROLLMENT_GUARD;
/
/

CREATE OR REPLACE TRIGGER TRG_EXAM_SEMESTER_DATE
BEFORE INSERT OR UPDATE OF Component_ID, Exam_Date ON EXAM
FOR EACH ROW
DECLARE
    v_start DATE;
    v_end   DATE;
BEGIN
    SELECT s.Semester_Start_Date, s.Semester_End_Date
    INTO v_start, v_end
    FROM ASSESSMENT_COMPONENT ac
    JOIN GRADING_SCHEME gs ON gs.Scheme_ID = ac.Scheme_ID
    JOIN COURSE_OFFERING co ON co.Offering_ID = gs.Offering_ID
    JOIN SEMESTER s ON s.Semester_ID = co.Semester_ID
    WHERE ac.Component_ID = :NEW.Component_ID;

    IF TRUNC(:NEW.Exam_Date) < TRUNC(v_start)
       OR TRUNC(:NEW.Exam_Date) > TRUNC(v_end) THEN
        RAISE_APPLICATION_ERROR(-20318,
            'Exam_Date must lie inside the offering semester.');
    END IF;
END;
/
/

CREATE OR REPLACE TRIGGER TRG_EXAM_TYPE
BEFORE INSERT OR UPDATE OF Component_ID ON EXAM
FOR EACH ROW
DECLARE
    v_type ASSESSMENT_COMPONENT.Component_Type%TYPE;
BEGIN
    SELECT Component_Type INTO v_type
    FROM ASSESSMENT_COMPONENT
    WHERE Component_ID = :NEW.Component_ID;

    IF v_type <> 'EXAM' THEN
        RAISE_APPLICATION_ERROR(-20013, 'Component_Type must be EXAM.');
    END IF;
END;
/
/

CREATE OR REPLACE TRIGGER TRG_GRADE_SCALE_COMPLETE_IN_USE
FOR INSERT OR UPDATE OF Min_Percentage, Max_Percentage OR DELETE
ON GRADE_SCALE
COMPOUND TRIGGER
    AFTER STATEMENT IS
        v_grade_count NUMBER;
        v_band_count  NUMBER;
        v_min_all     NUMBER;
        v_max_all     NUMBER;
        v_gap_count   NUMBER;
    BEGIN
        SELECT COUNT(*) INTO v_grade_count FROM COURSE_GRADE;

        IF v_grade_count > 0 THEN
            SELECT COUNT(*), MIN(Min_Percentage), MAX(Max_Percentage)
            INTO v_band_count, v_min_all, v_max_all
            FROM GRADE_SCALE;

            IF v_band_count = 0
               OR v_min_all <> 0
               OR v_max_all <> 100 THEN
                RAISE_APPLICATION_ERROR(-20322,
                    'An in-use grade scale must cover 0 through 100.');
            END IF;

            SELECT COUNT(*)
            INTO v_gap_count
            FROM (
                SELECT Min_Percentage,
                       LAG(Max_Percentage) OVER (ORDER BY Min_Percentage) AS Prev_Max
                FROM GRADE_SCALE
            )
            WHERE Prev_Max IS NOT NULL
              AND Min_Percentage > Prev_Max + 0.01;

            IF v_gap_count > 0 THEN
                RAISE_APPLICATION_ERROR(-20323,
                    'An in-use grade scale cannot contain percentage gaps.');
            END IF;
        END IF;
    END AFTER STATEMENT;
END TRG_GRADE_SCALE_COMPLETE_IN_USE;
/
/

CREATE OR REPLACE TRIGGER TRG_GRADE_SCALE_NO_OVERLAP
FOR INSERT OR UPDATE OF Min_Percentage, Max_Percentage ON GRADE_SCALE
COMPOUND TRIGGER

    AFTER STATEMENT IS
        v_count NUMBER;
    BEGIN
        SELECT COUNT(*)
        INTO v_count
        FROM GRADE_SCALE a
        JOIN GRADE_SCALE b
          ON a.Grade_Code < b.Grade_Code
         AND a.Min_Percentage <= b.Max_Percentage
         AND b.Min_Percentage <= a.Max_Percentage;

        IF v_count > 0 THEN
            RAISE_APPLICATION_ERROR(
                -20206,
                'GRADE_SCALE percentage bands cannot overlap.'
            );
        END IF;
    END AFTER STATEMENT;

END TRG_GRADE_SCALE_NO_OVERLAP;
/
/

CREATE OR REPLACE TRIGGER TRG_INSTRUCTOR_ROLE
BEFORE INSERT OR UPDATE OF User_ID ON INSTRUCTOR
FOR EACH ROW
DECLARE
    v_role LMS_USER.Role%TYPE;
BEGIN
    SELECT Role INTO v_role FROM LMS_USER WHERE User_ID = :NEW.User_ID;
    IF v_role <> 'INSTRUCTOR' THEN
        RAISE_APPLICATION_ERROR(-20003, 'LMS_USER role must be INSTRUCTOR.');
    END IF;
EXCEPTION
    WHEN NO_DATA_FOUND THEN
        RAISE_APPLICATION_ERROR(-20004, 'Referenced LMS_USER does not exist.');
END;
/
/

CREATE OR REPLACE TRIGGER TRG_LMS_USER_ROLE_LOCK
BEFORE UPDATE OF Role ON LMS_USER
FOR EACH ROW
DECLARE
    v_count NUMBER;
BEGIN
    IF :OLD.Role <> :NEW.Role THEN
        SELECT
            (SELECT COUNT(*) FROM STUDENT    WHERE User_ID = :OLD.User_ID) +
            (SELECT COUNT(*) FROM INSTRUCTOR WHERE User_ID = :OLD.User_ID) +
            (SELECT COUNT(*) FROM ADMIN      WHERE User_ID = :OLD.User_ID)
        INTO v_count
        FROM DUAL;

        IF v_count > 0 THEN
            RAISE_APPLICATION_ERROR(
                -20201,
                'Role cannot be changed while a STUDENT/INSTRUCTOR/ADMIN subtype row exists.'
            );
        END IF;
    END IF;
END;
/
/

CREATE OR REPLACE TRIGGER TRG_MARK_GRADE_SYNC
FOR INSERT OR UPDATE OF Marks_Obtained, Component_ID, Enrollment_ID
ON STUDENT_MARK
COMPOUND TRIGGER
    TYPE t_enroll_set IS TABLE OF BOOLEAN INDEX BY VARCHAR2(100);
    g_ids t_enroll_set;

    AFTER EACH ROW IS
    BEGIN
        g_ids(TO_CHAR(:NEW.Enrollment_ID)) := TRUE;
        IF UPDATING AND :OLD.Enrollment_ID <> :NEW.Enrollment_ID THEN
            g_ids(TO_CHAR(:OLD.Enrollment_ID)) := TRUE;
        END IF;
    END AFTER EACH ROW;

    AFTER STATEMENT IS
        v_key       VARCHAR2(100);
        v_has_grade NUMBER;
        v_pct       NUMBER;
        v_code      GRADE_SCALE.Grade_Code%TYPE;
    BEGIN
        v_key := g_ids.FIRST;
        WHILE v_key IS NOT NULL LOOP
            SELECT COUNT(*)
            INTO v_has_grade
            FROM COURSE_GRADE
            WHERE Enrollment_ID = TO_NUMBER(v_key);

            IF v_has_grade > 0 THEN
                v_pct := FN_COURSE_PERCENT(TO_NUMBER(v_key));

                SELECT Grade_Code
                INTO v_code
                FROM (
                    SELECT Grade_Code
                    FROM GRADE_SCALE
                    WHERE v_pct BETWEEN Min_Percentage AND Max_Percentage
                    ORDER BY Min_Percentage DESC
                )
                WHERE ROWNUM = 1;

                UPDATE COURSE_GRADE
                SET Grade_Code = v_code,
                    Published_At = SYSTIMESTAMP
                WHERE Enrollment_ID = TO_NUMBER(v_key);
            END IF;

            v_key := g_ids.NEXT(v_key);
        END LOOP;
    END AFTER STATEMENT;
END TRG_MARK_GRADE_SYNC;
/
/

CREATE OR REPLACE TRIGGER TRG_MATERIAL_AUTH
BEFORE INSERT OR UPDATE OF Offering_ID, Uploaded_By_User_ID
ON COURSE_MATERIAL
FOR EACH ROW
DECLARE
    v_role          LMS_USER.Role%TYPE;
    v_status        LMS_USER.Account_Status%TYPE;
    v_instructor_id NUMBER;
    v_count         NUMBER;
BEGIN
    SELECT Role, Account_Status
    INTO v_role, v_status
    FROM LMS_USER
    WHERE User_ID = :NEW.Uploaded_By_User_ID;

    IF v_status <> 'ACTIVE' THEN
        RAISE_APPLICATION_ERROR(-20310,
            'Only an ACTIVE LMS account can upload course material.');
    END IF;

    IF v_role = 'ADMIN' THEN
        NULL;
    ELSIF v_role = 'INSTRUCTOR' THEN
        SELECT Instructor_ID
        INTO v_instructor_id
        FROM INSTRUCTOR
        WHERE User_ID = :NEW.Uploaded_By_User_ID;

        SELECT COUNT(*)
        INTO v_count
        FROM OFFERING_INSTRUCTOR
        WHERE Offering_ID = :NEW.Offering_ID
          AND Instructor_ID = v_instructor_id;

        IF v_count = 0 THEN
            RAISE_APPLICATION_ERROR(-20026,
                'Instructor is not assigned to this offering.');
        END IF;
    ELSE
        RAISE_APPLICATION_ERROR(-20027,
            'Only an assigned instructor or admin can upload course material.');
    END IF;
END;
/
/

CREATE OR REPLACE TRIGGER TRG_OFFERING_CAPACITY_GUARD
BEFORE UPDATE OF Capacity ON COURSE_OFFERING
FOR EACH ROW
DECLARE
    v_count NUMBER;
BEGIN
    SELECT COUNT(*)
    INTO v_count
    FROM ENROLLMENT
    WHERE Offering_ID = :OLD.Offering_ID
      AND Enrollment_Status IN ('ENROLLED','COMPLETED');

    IF :NEW.Capacity < v_count THEN
        RAISE_APPLICATION_ERROR(-20308,
            'Capacity cannot be reduced below current/complete roster size.');
    END IF;
END;
/
/

CREATE OR REPLACE TRIGGER TRG_OFFERING_SEMESTER_GUARD
BEFORE UPDATE OF Semester_ID ON COURSE_OFFERING
FOR EACH ROW
DECLARE
    v_children NUMBER;
BEGIN
    IF :OLD.Semester_ID <> :NEW.Semester_ID THEN
        SELECT
            (SELECT COUNT(*) FROM ENROLLMENT
             WHERE Offering_ID=:OLD.Offering_ID) +
            (SELECT COUNT(*) FROM CLASS_SESSION
             WHERE Offering_ID=:OLD.Offering_ID) +
            (SELECT COUNT(*) FROM GRADING_SCHEME
             WHERE Offering_ID=:OLD.Offering_ID)
        INTO v_children
        FROM DUAL;

        IF v_children>0 THEN
            RAISE_APPLICATION_ERROR(-20338,
                'Offering semester cannot change after enrollment/session/grading children exist.');
        END IF;
    END IF;
END;
/
/

CREATE OR REPLACE TRIGGER TRG_OFFERING_STATUS_LIFECYCLE
BEFORE UPDATE OF Offering_Status ON COURSE_OFFERING
FOR EACH ROW
BEGIN
    IF :NEW.Offering_Status=:OLD.Offering_Status THEN
        NULL;
    ELSIF :OLD.Offering_Status='PLANNED'
       AND :NEW.Offering_Status IN ('OPEN','CANCELLED') THEN
        NULL;
    ELSIF :OLD.Offering_Status='OPEN'
       AND :NEW.Offering_Status IN ('CLOSED','CANCELLED') THEN
        NULL;
    ELSIF :OLD.Offering_Status='CLOSED'
       AND :NEW.Offering_Status='COMPLETED' THEN
        NULL;
    ELSE
        RAISE_APPLICATION_ERROR(-20401,
            'Invalid offering-status transition: '
            ||:OLD.Offering_Status||' -> '||:NEW.Offering_Status||'.');
    END IF;
END;
/
/

CREATE OR REPLACE TRIGGER TRG_OPTION_QUESTION_TYPE
BEFORE INSERT OR UPDATE OF Question_ID ON QUESTION_OPTION
FOR EACH ROW
DECLARE
    v_type QUESTION.Question_Type%TYPE;
BEGIN
    SELECT Question_Type
      INTO v_type
      FROM QUESTION
     WHERE Question_ID = :NEW.Question_ID;

    IF v_type NOT IN ('MCQ_SINGLE','MCQ_MULTI','TRUE_FALSE','MATCHING','ORDERING') THEN
        RAISE_APPLICATION_ERROR(
            -20211,
            'QUESTION_OPTION is allowed only for MCQ, TRUE_FALSE, MATCHING, or ORDERING questions.'
        );
    END IF;
END;
/
/

CREATE OR REPLACE TRIGGER TRG_QUESTION_OPTION_SEMANTICS
FOR INSERT OR UPDATE OF Question_ID, Is_Correct, Option_Order OR DELETE
ON QUESTION_OPTION
COMPOUND TRIGGER
    AFTER STATEMENT IS
        v_bad NUMBER;
    BEGIN
        -- Used MCQ_SINGLE questions must have exactly one correct option.
        SELECT COUNT(*)
        INTO v_bad
        FROM (
            SELECT q.Question_ID
            FROM QUESTION q
            JOIN QUIZ_QUESTION qq ON qq.Question_ID=q.Question_ID
            LEFT JOIN QUESTION_OPTION qo ON qo.Question_ID=q.Question_ID
            WHERE q.Question_Type='MCQ_SINGLE'
            GROUP BY q.Question_ID
            HAVING NVL(SUM(CASE WHEN qo.Is_Correct='Y' THEN 1 ELSE 0 END),0) <> 1
        );

        IF v_bad>0 THEN
            RAISE_APPLICATION_ERROR(-20343,
                'A quiz-used MCQ_SINGLE must have exactly one correct option.');
        END IF;

        -- Used TRUE_FALSE questions must have exactly 2 options and 1 correct.
        SELECT COUNT(*)
        INTO v_bad
        FROM (
            SELECT q.Question_ID
            FROM QUESTION q
            JOIN QUIZ_QUESTION qq ON qq.Question_ID=q.Question_ID
            LEFT JOIN QUESTION_OPTION qo ON qo.Question_ID=q.Question_ID
            WHERE q.Question_Type='TRUE_FALSE'
            GROUP BY q.Question_ID
            HAVING COUNT(qo.Option_ID)<>2
                OR NVL(SUM(CASE WHEN qo.Is_Correct='Y' THEN 1 ELSE 0 END),0)<>1
        );

        IF v_bad>0 THEN
            RAISE_APPLICATION_ERROR(-20344,
                'A quiz-used TRUE_FALSE must have exactly two options and one correct.');
        END IF;
    END AFTER STATEMENT;
END TRG_QUESTION_OPTION_SEMANTICS;
/
/

CREATE OR REPLACE TRIGGER TRG_QUESTION_TYPE_PARENT
BEFORE UPDATE OF Question_Type ON QUESTION
FOR EACH ROW
DECLARE
    v_options NUMBER;
    v_correct NUMBER;
BEGIN
    SELECT COUNT(*), NVL(SUM(CASE WHEN Is_Correct='Y' THEN 1 ELSE 0 END),0)
    INTO v_options, v_correct
    FROM QUESTION_OPTION
    WHERE Question_ID=:OLD.Question_ID;

    IF :NEW.Question_Type IN ('SHORT_TEXT','LONG_TEXT')
       AND v_options>0 THEN
        RAISE_APPLICATION_ERROR(-20340,
            'Text questions cannot retain QUESTION_OPTION rows.');
    END IF;

    IF :NEW.Question_Type='MCQ_SINGLE'
       AND v_options>0
       AND v_correct<>1 THEN
        RAISE_APPLICATION_ERROR(-20341,
            'MCQ_SINGLE must have exactly one correct option.');
    END IF;

    IF :NEW.Question_Type='TRUE_FALSE'
       AND v_options>0
       AND (v_options<>2 OR v_correct<>1) THEN
        RAISE_APPLICATION_ERROR(-20342,
            'TRUE_FALSE must have exactly two options and one correct option.');
    END IF;
END;
/
/

CREATE OR REPLACE TRIGGER TRG_QUIZ_ATTEMPT
BEFORE INSERT OR UPDATE
ON QUIZ_ATTEMPT
FOR EACH ROW
DECLARE
    v_offering_id   NUMBER;
    v_max_attempts  QUIZ.Max_Attempts%TYPE;
    v_open_at       QUIZ.Open_At%TYPE;
    v_close_at      QUIZ.Close_At%TYPE;
    v_duration      QUIZ.Duration_Minutes%TYPE;
    v_count         NUMBER;
    v_st_status     STUDENT.Student_Status%TYPE;
    v_acct_status   LMS_USER.Account_Status%TYPE;
    v_deadline      TIMESTAMP;
BEGIN
    IF INSERTING AND :NEW.Submitted_At IS NOT NULL THEN
        RAISE_APPLICATION_ERROR(-20405,
            'A quiz attempt must be created open; submit it separately.');
    END IF;

    IF INSERTING AND :NEW.Started_At>SYSTIMESTAMP THEN
        RAISE_APPLICATION_ERROR(-20418,
            'Quiz Started_At cannot be in the future.');
    END IF;

    IF UPDATING THEN
        IF :NEW.Quiz_ID<>:OLD.Quiz_ID
           OR :NEW.Student_ID<>:OLD.Student_ID
           OR :NEW.Attempt_No<>:OLD.Attempt_No
           OR :NEW.Started_At<>:OLD.Started_At THEN
            RAISE_APPLICATION_ERROR(-20406,
                'Quiz identity, student, attempt number and start time are immutable after creation.');
        END IF;

        IF :OLD.Submitted_At IS NOT NULL THEN
            RAISE_APPLICATION_ERROR(-20419,
                'A submitted quiz attempt is immutable.');
        END IF;

        -- The database owns the final submission time. This prevents a
        -- client from backdating Submitted_At to bypass duration/Close_At.
        IF :OLD.Submitted_At IS NULL AND :NEW.Submitted_At IS NOT NULL THEN
            :NEW.Submitted_At:=SYSTIMESTAMP;
        END IF;
    END IF;

    SELECT gs.Offering_ID,q.Max_Attempts,q.Open_At,q.Close_At,q.Duration_Minutes
    INTO v_offering_id,v_max_attempts,v_open_at,v_close_at,v_duration
    FROM QUIZ q
    JOIN ASSESSMENT_COMPONENT ac ON ac.Component_ID=q.Component_ID
    JOIN GRADING_SCHEME gs ON gs.Scheme_ID=ac.Scheme_ID
    WHERE q.Quiz_ID=:NEW.Quiz_ID;

    IF INSERTING THEN
        IF v_open_at IS NOT NULL AND SYSTIMESTAMP<v_open_at THEN
            RAISE_APPLICATION_ERROR(-20311,'Quiz attempt cannot begin before Open_At.');
        END IF;
        IF v_close_at IS NOT NULL AND SYSTIMESTAMP>v_close_at THEN
            RAISE_APPLICATION_ERROR(-20312,'Quiz attempt cannot begin after Close_At.');
        END IF;

        SELECT s.Student_Status,u.Account_Status
        INTO v_st_status,v_acct_status
        FROM STUDENT s
        JOIN LMS_USER u ON u.User_ID=s.User_ID
        WHERE s.Student_ID=:NEW.Student_ID;

        IF v_st_status<>'ACTIVE' OR v_acct_status<>'ACTIVE' THEN
            RAISE_APPLICATION_ERROR(-20313,
                'Student and LMS account must both be ACTIVE to attempt a quiz.');
        END IF;

        SELECT COUNT(*) INTO v_count
        FROM ENROLLMENT
        WHERE Student_ID=:NEW.Student_ID
          AND Offering_ID=v_offering_id
          AND Enrollment_Status='ENROLLED';

        IF v_count=0 THEN
            RAISE_APPLICATION_ERROR(-20016,
                'Student is not actively enrolled in the quiz offering.');
        END IF;

        IF :NEW.Attempt_No>v_max_attempts THEN
            RAISE_APPLICATION_ERROR(-20017,'Quiz attempt exceeds Max_Attempts.');
        END IF;
    END IF;

    IF :NEW.Submitted_At IS NOT NULL THEN
        IF :NEW.Submitted_At>SYSTIMESTAMP THEN
            RAISE_APPLICATION_ERROR(-20420,
                'Submitted_At cannot be in the future.');
        END IF;

        IF v_duration IS NOT NULL THEN
            v_deadline:=:NEW.Started_At+NUMTODSINTERVAL(v_duration,'MINUTE');
            IF SYSTIMESTAMP>v_deadline THEN
                RAISE_APPLICATION_ERROR(-20407,
                    'Quiz duration has expired; this attempt can no longer be submitted.');
            END IF;
        END IF;

        IF v_close_at IS NOT NULL AND SYSTIMESTAMP>v_close_at THEN
            RAISE_APPLICATION_ERROR(-20408,
                'Quiz Close_At has passed; this attempt can no longer be submitted.');
        END IF;
    END IF;
END;
/
/

CREATE OR REPLACE TRIGGER TRG_QUIZ_MAX_ATTEMPTS_PARENT
BEFORE UPDATE OF Max_Attempts ON QUIZ
FOR EACH ROW
DECLARE
    v_max_existing NUMBER;
BEGIN
    SELECT NVL(MAX(Attempt_No),0)
    INTO v_max_existing
    FROM QUIZ_ATTEMPT
    WHERE Quiz_ID = :OLD.Quiz_ID;

    IF :NEW.Max_Attempts < v_max_existing THEN
        RAISE_APPLICATION_ERROR(-20315,
            'Max_Attempts cannot be reduced below an existing Attempt_No.');
    END IF;
END;
/
/

CREATE OR REPLACE TRIGGER TRG_QUIZ_QUESTION_SEMANTICS
BEFORE INSERT OR UPDATE OF Question_ID ON QUIZ_QUESTION
FOR EACH ROW
DECLARE
    v_type    QUESTION.Question_Type%TYPE;
    v_options NUMBER;
    v_correct NUMBER;
BEGIN
    SELECT Question_Type
    INTO v_type
    FROM QUESTION
    WHERE Question_ID=:NEW.Question_ID;

    SELECT COUNT(*), NVL(SUM(CASE WHEN Is_Correct='Y' THEN 1 ELSE 0 END),0)
    INTO v_options, v_correct
    FROM QUESTION_OPTION
    WHERE Question_ID=:NEW.Question_ID;

    IF v_type='MCQ_SINGLE' AND v_correct<>1 THEN
        RAISE_APPLICATION_ERROR(-20345,
            'MCQ_SINGLE must have exactly one correct option before quiz use.');
    ELSIF v_type='TRUE_FALSE'
          AND (v_options<>2 OR v_correct<>1) THEN
        RAISE_APPLICATION_ERROR(-20346,
            'TRUE_FALSE must have exactly two options and one correct option before quiz use.');
    ELSIF v_type IN ('SHORT_TEXT','LONG_TEXT') AND v_options>0 THEN
        RAISE_APPLICATION_ERROR(-20347,
            'Text questions cannot have options when attached to a quiz.');
    END IF;
END;
/
/

CREATE OR REPLACE TRIGGER TRG_QUIZ_RESPONSE
BEFORE INSERT OR UPDATE
ON QUIZ_RESPONSE
FOR EACH ROW
DECLARE
    v_quiz_id      NUMBER;
    v_submitted_at QUIZ_ATTEMPT.Submitted_At%TYPE;
    v_started_at   QUIZ_ATTEMPT.Started_At%TYPE;
    v_duration     QUIZ.Duration_Minutes%TYPE;
    v_close_at     QUIZ.Close_At%TYPE;
    v_deadline     TIMESTAMP;
    v_count        NUMBER;
BEGIN
    SELECT qa.Quiz_ID,qa.Submitted_At,qa.Started_At,
           q.Duration_Minutes,q.Close_At
    INTO v_quiz_id,v_submitted_at,v_started_at,v_duration,v_close_at
    FROM QUIZ_ATTEMPT qa
    JOIN QUIZ q ON q.Quiz_ID=qa.Quiz_ID
    WHERE qa.Attempt_ID=:NEW.Attempt_ID
    FOR UPDATE OF qa.Submitted_At;

    IF v_submitted_at IS NOT NULL THEN
        RAISE_APPLICATION_ERROR(-20409,
            'Responses cannot be inserted or changed after quiz submission.');
    END IF;

    IF v_duration IS NOT NULL THEN
        v_deadline:=v_started_at+NUMTODSINTERVAL(v_duration,'MINUTE');
        IF SYSTIMESTAMP>v_deadline THEN
            RAISE_APPLICATION_ERROR(-20407,
                'Quiz duration has expired; responses are locked.');
        END IF;
    END IF;

    IF v_close_at IS NOT NULL AND SYSTIMESTAMP>v_close_at THEN
        RAISE_APPLICATION_ERROR(-20408,
            'Quiz Close_At has passed; responses are locked.');
    END IF;

    SELECT COUNT(*) INTO v_count
    FROM QUIZ_QUESTION
    WHERE Quiz_ID=v_quiz_id
      AND Question_ID=:NEW.Question_ID;

    IF v_count=0 THEN
        RAISE_APPLICATION_ERROR(-20018,
            'Question does not belong to the attempted quiz.');
    END IF;
END;
/
/

CREATE OR REPLACE TRIGGER TRG_QUIZ_SEMESTER_WINDOW
BEFORE INSERT OR UPDATE OF Component_ID, Open_At, Close_At ON QUIZ
FOR EACH ROW
DECLARE
    v_start DATE;
    v_end   DATE;
BEGIN
    SELECT s.Semester_Start_Date, s.Semester_End_Date
    INTO v_start, v_end
    FROM ASSESSMENT_COMPONENT ac
    JOIN GRADING_SCHEME gs ON gs.Scheme_ID = ac.Scheme_ID
    JOIN COURSE_OFFERING co ON co.Offering_ID = gs.Offering_ID
    JOIN SEMESTER s ON s.Semester_ID = co.Semester_ID
    WHERE ac.Component_ID = :NEW.Component_ID;

    IF :NEW.Open_At IS NOT NULL
       AND (CAST(:NEW.Open_At AS DATE) < v_start
            OR CAST(:NEW.Open_At AS DATE) >= v_end + 1) THEN
        RAISE_APPLICATION_ERROR(-20320,
            'Quiz Open_At must lie inside the offering semester.');
    END IF;

    IF :NEW.Close_At IS NOT NULL
       AND (CAST(:NEW.Close_At AS DATE) < v_start
            OR CAST(:NEW.Close_At AS DATE) >= v_end + 1) THEN
        RAISE_APPLICATION_ERROR(-20321,
            'Quiz Close_At must lie inside the offering semester.');
    END IF;
END;
/
/

CREATE OR REPLACE TRIGGER TRG_QUIZ_TOTAL_MARKS
FOR INSERT OR UPDATE OF Quiz_ID, Question_Marks OR DELETE
ON QUIZ_QUESTION
COMPOUND TRIGGER

    AFTER STATEMENT IS
        v_count NUMBER;
    BEGIN
        SELECT COUNT(*)
        INTO v_count
        FROM (
            SELECT q.Quiz_ID
            FROM QUIZ q
            JOIN ASSESSMENT_COMPONENT ac
              ON ac.Component_ID = q.Component_ID
            LEFT JOIN QUIZ_QUESTION qq
              ON qq.Quiz_ID = q.Quiz_ID
            GROUP BY q.Quiz_ID, ac.Max_Marks
            HAVING NVL(SUM(qq.Question_Marks), 0) > ac.Max_Marks
        );

        IF v_count > 0 THEN
            RAISE_APPLICATION_ERROR(
                -20210,
                'Total QUIZ_QUESTION marks cannot exceed the quiz component Max_Marks.'
            );
        END IF;
    END AFTER STATEMENT;

END TRG_QUIZ_TOTAL_MARKS;
/
/

CREATE OR REPLACE TRIGGER TRG_QUIZ_TYPE
BEFORE INSERT OR UPDATE OF Component_ID ON QUIZ
FOR EACH ROW
DECLARE
    v_type ASSESSMENT_COMPONENT.Component_Type%TYPE;
BEGIN
    SELECT Component_Type INTO v_type
    FROM ASSESSMENT_COMPONENT
    WHERE Component_ID = :NEW.Component_ID;

    IF v_type <> 'QUIZ' THEN
        RAISE_APPLICATION_ERROR(-20012, 'Component_Type must be QUIZ.');
    END IF;
END;
/
/

CREATE OR REPLACE TRIGGER TRG_RESPONSE_OPTION
BEFORE INSERT OR UPDATE
ON QUIZ_RESPONSE_OPTION
FOR EACH ROW
DECLARE
    v_attempt_id       NUMBER;
    v_response_question NUMBER;
    v_option_question   NUMBER;
    v_submitted_at      QUIZ_ATTEMPT.Submitted_At%TYPE;
    v_started_at        QUIZ_ATTEMPT.Started_At%TYPE;
    v_duration          QUIZ.Duration_Minutes%TYPE;
    v_close_at          QUIZ.Close_At%TYPE;
    v_deadline          TIMESTAMP;
BEGIN
    SELECT qr.Attempt_ID,qr.Question_ID
    INTO v_attempt_id,v_response_question
    FROM QUIZ_RESPONSE qr
    WHERE qr.Response_ID=:NEW.Response_ID;

    SELECT qa.Submitted_At,qa.Started_At,q.Duration_Minutes,q.Close_At
    INTO v_submitted_at,v_started_at,v_duration,v_close_at
    FROM QUIZ_ATTEMPT qa
    JOIN QUIZ q ON q.Quiz_ID=qa.Quiz_ID
    WHERE qa.Attempt_ID=v_attempt_id
    FOR UPDATE OF qa.Submitted_At;

    IF v_submitted_at IS NOT NULL THEN
        RAISE_APPLICATION_ERROR(-20409,
            'Response options cannot be changed after quiz submission.');
    END IF;

    IF v_duration IS NOT NULL THEN
        v_deadline:=v_started_at+NUMTODSINTERVAL(v_duration,'MINUTE');
        IF SYSTIMESTAMP>v_deadline THEN
            RAISE_APPLICATION_ERROR(-20407,
                'Quiz duration has expired; response options are locked.');
        END IF;
    END IF;

    IF v_close_at IS NOT NULL AND SYSTIMESTAMP>v_close_at THEN
        RAISE_APPLICATION_ERROR(-20408,
            'Quiz Close_At has passed; response options are locked.');
    END IF;

    SELECT Question_ID INTO v_option_question
    FROM QUESTION_OPTION
    WHERE Option_ID=:NEW.Option_ID;

    IF v_response_question<>v_option_question THEN
        RAISE_APPLICATION_ERROR(-20019,
            'Selected option does not belong to the response question.');
    END IF;
END;
/
/

CREATE OR REPLACE TRIGGER TRG_RESPONSE_SINGLE_CARDINALITY
FOR INSERT OR UPDATE OF Response_ID, Option_ID OR DELETE
ON QUIZ_RESPONSE_OPTION
COMPOUND TRIGGER
    AFTER STATEMENT IS
        v_bad NUMBER;
    BEGIN
        SELECT COUNT(*)
        INTO v_bad
        FROM (
            SELECT qro.Response_ID
            FROM QUIZ_RESPONSE_OPTION qro
            JOIN QUIZ_RESPONSE qr ON qr.Response_ID=qro.Response_ID
            JOIN QUESTION q ON q.Question_ID=qr.Question_ID
            WHERE q.Question_Type IN ('MCQ_SINGLE','TRUE_FALSE')
            GROUP BY qro.Response_ID
            HAVING COUNT(*)>1
        );

        IF v_bad>0 THEN
            RAISE_APPLICATION_ERROR(-20348,
                'MCQ_SINGLE/TRUE_FALSE response can select only one option.');
        END IF;
    END AFTER STATEMENT;
END TRG_RESPONSE_SINGLE_CARDINALITY;
/
/

CREATE OR REPLACE TRIGGER TRG_SEMESTER_PARENT_GUARD
BEFORE UPDATE OF Semester_Start_Date, Semester_End_Date ON SEMESTER
FOR EACH ROW
DECLARE
    v_bad NUMBER;
BEGIN
    SELECT COUNT(*)
    INTO v_bad
    FROM COURSE_OFFERING co
    JOIN CLASS_SESSION cs ON cs.Offering_ID=co.Offering_ID
    WHERE co.Semester_ID=:OLD.Semester_ID
      AND (TRUNC(cs.Session_Date)<TRUNC(:NEW.Semester_Start_Date)
           OR TRUNC(cs.Session_Date)>TRUNC(:NEW.Semester_End_Date));

    IF v_bad>0 THEN
        RAISE_APPLICATION_ERROR(-20336,
            'Semester date change would invalidate existing class sessions.');
    END IF;

    SELECT COUNT(*)
    INTO v_bad
    FROM COURSE_OFFERING co
    JOIN GRADING_SCHEME gs ON gs.Offering_ID=co.Offering_ID
    JOIN ASSESSMENT_COMPONENT ac ON ac.Scheme_ID=gs.Scheme_ID
    JOIN EXAM ex ON ex.Component_ID=ac.Component_ID
    WHERE co.Semester_ID=:OLD.Semester_ID
      AND (TRUNC(ex.Exam_Date)<TRUNC(:NEW.Semester_Start_Date)
           OR TRUNC(ex.Exam_Date)>TRUNC(:NEW.Semester_End_Date));

    IF v_bad>0 THEN
        RAISE_APPLICATION_ERROR(-20337,
            'Semester date change would invalidate existing exams.');
    END IF;
END;
/
/

CREATE OR REPLACE TRIGGER TRG_SESSION_SEMESTER_DATE
BEFORE INSERT OR UPDATE OF Offering_ID, Session_Date ON CLASS_SESSION
FOR EACH ROW
DECLARE
    v_start SEMESTER.Semester_Start_Date%TYPE;
    v_end   SEMESTER.Semester_End_Date%TYPE;
BEGIN
    SELECT s.Semester_Start_Date, s.Semester_End_Date
    INTO v_start, v_end
    FROM COURSE_OFFERING co
    JOIN SEMESTER s
      ON s.Semester_ID = co.Semester_ID
    WHERE co.Offering_ID = :NEW.Offering_ID;

    IF TRUNC(:NEW.Session_Date) < TRUNC(v_start)
       OR TRUNC(:NEW.Session_Date) > TRUNC(v_end) THEN
        RAISE_APPLICATION_ERROR(
            -20205,
            'Class-session date must fall inside the offering semester.'
        );
    END IF;
END;
/
/

CREATE OR REPLACE TRIGGER TRG_SINGLE_MCQ_ONE_CORRECT
FOR INSERT OR UPDATE OF Question_ID, Is_Correct OR DELETE
ON QUESTION_OPTION
COMPOUND TRIGGER

    AFTER STATEMENT IS
        v_count NUMBER;
    BEGIN
        SELECT COUNT(*)
        INTO v_count
        FROM (
            SELECT qo.Question_ID
            FROM QUESTION_OPTION qo
            JOIN QUESTION q
              ON q.Question_ID = qo.Question_ID
            WHERE q.Question_Type = 'MCQ_SINGLE'
              AND qo.Is_Correct = 'Y'
            GROUP BY qo.Question_ID
            HAVING COUNT(*) > 1
        );

        IF v_count > 0 THEN
            RAISE_APPLICATION_ERROR(
                -20212,
                'MCQ_SINGLE cannot contain more than one correct option.'
            );
        END IF;
    END AFTER STATEMENT;

END TRG_SINGLE_MCQ_ONE_CORRECT;
/
/

CREATE OR REPLACE TRIGGER TRG_STUDENT_MARK
BEFORE INSERT OR UPDATE OF Component_ID,Enrollment_ID,Marks_Obtained,
                           Recorded_By_User_ID,Graded_Submission_ID
ON STUDENT_MARK
FOR EACH ROW
DECLARE
    v_component_offering NUMBER;
    v_component_type     ASSESSMENT_COMPONENT.Component_Type%TYPE;
    v_enroll_offering    NUMBER;
    v_enroll_status      ENROLLMENT.Enrollment_Status%TYPE;
    v_student_id         ENROLLMENT.Student_ID%TYPE;
    v_max_marks          NUMBER;
    v_role               LMS_USER.Role%TYPE;
    v_account_status     LMS_USER.Account_Status%TYPE;
    v_instructor_id      NUMBER;
    v_count              NUMBER;
BEGIN
    SELECT gs.Offering_ID,ac.Max_Marks,ac.Component_Type
    INTO v_component_offering,v_max_marks,v_component_type
    FROM ASSESSMENT_COMPONENT ac
    JOIN GRADING_SCHEME gs ON gs.Scheme_ID=ac.Scheme_ID
    WHERE ac.Component_ID=:NEW.Component_ID;

    -- V4 race fix retained: every mark write locks the same ENROLLMENT row
    -- used by PR_PUBLISH_GRADE.
    SELECT Offering_ID,Enrollment_Status,Student_ID
    INTO v_enroll_offering,v_enroll_status,v_student_id
    FROM ENROLLMENT
    WHERE Enrollment_ID=:NEW.Enrollment_ID
    FOR UPDATE;

    IF v_component_offering<>v_enroll_offering THEN
        RAISE_APPLICATION_ERROR(-20020,
            'Assessment component and enrollment belong to different offerings.');
    END IF;

    IF v_enroll_status NOT IN ('ENROLLED','COMPLETED') THEN
        RAISE_APPLICATION_ERROR(-20209,
            'Marks can be recorded only for ENROLLED or COMPLETED enrollment.');
    END IF;

    IF :NEW.Marks_Obtained>v_max_marks THEN
        RAISE_APPLICATION_ERROR(-20021,
            'Marks_Obtained cannot exceed component Max_Marks.');
    END IF;

    IF v_component_type='ASSIGNMENT' THEN
        IF :NEW.Graded_Submission_ID IS NULL THEN
            RAISE_APPLICATION_ERROR(-20412,
                'Assignment marks must identify the graded submission version.');
        END IF;

        SELECT COUNT(*) INTO v_count
        FROM ASSIGNMENT_SUBMISSION su
        JOIN ASSIGNMENT a ON a.Assignment_ID=su.Assignment_ID
        WHERE su.Submission_ID=:NEW.Graded_Submission_ID
          AND a.Component_ID=:NEW.Component_ID
          AND su.Student_ID=v_student_id
          AND su.Submission_Version=(
              SELECT MAX(su2.Submission_Version)
              FROM ASSIGNMENT_SUBMISSION su2
              WHERE su2.Assignment_ID=su.Assignment_ID
                AND su2.Student_ID=su.Student_ID
          );

        IF v_count=0 THEN
            RAISE_APPLICATION_ERROR(-20413,
                'Graded_Submission_ID must be the latest submission for this student and assignment.');
        END IF;
    ELSIF :NEW.Graded_Submission_ID IS NOT NULL THEN
        RAISE_APPLICATION_ERROR(-20414,
            'Graded_Submission_ID is valid only for ASSIGNMENT components.');
    END IF;

    SELECT Role,Account_Status
    INTO v_role,v_account_status
    FROM LMS_USER
    WHERE User_ID=:NEW.Recorded_By_User_ID;

    IF v_account_status<>'ACTIVE' THEN
        RAISE_APPLICATION_ERROR(-20330,
            'Mark recorder LMS account must be ACTIVE.');
    END IF;

    IF v_role='ADMIN' THEN
        NULL;
    ELSIF v_role='INSTRUCTOR' THEN
        SELECT Instructor_ID INTO v_instructor_id
        FROM INSTRUCTOR
        WHERE User_ID=:NEW.Recorded_By_User_ID;

        SELECT COUNT(*) INTO v_count
        FROM OFFERING_INSTRUCTOR
        WHERE Offering_ID=v_component_offering
          AND Instructor_ID=v_instructor_id;

        IF v_count=0 THEN
            RAISE_APPLICATION_ERROR(-20022,
                'Instructor is not assigned to this offering.');
        END IF;
    ELSE
        RAISE_APPLICATION_ERROR(-20023,
            'Only an assigned instructor or admin can record marks.');
    END IF;
END;
/
/

CREATE OR REPLACE TRIGGER TRG_STUDENT_ROLE
BEFORE INSERT OR UPDATE OF User_ID ON STUDENT
FOR EACH ROW
DECLARE
    v_role LMS_USER.Role%TYPE;
BEGIN
    SELECT Role INTO v_role FROM LMS_USER WHERE User_ID = :NEW.User_ID;
    IF v_role <> 'STUDENT' THEN
        RAISE_APPLICATION_ERROR(-20001, 'LMS_USER role must be STUDENT.');
    END IF;
EXCEPTION
    WHEN NO_DATA_FOUND THEN
        RAISE_APPLICATION_ERROR(-20002, 'Referenced LMS_USER does not exist.');
END;
/
/

CREATE OR REPLACE TRIGGER TRG_SUBMISSION_VERSION_SEQUENCE
FOR INSERT OR UPDATE OF Assignment_ID, Student_ID, Submission_Version OR DELETE
ON ASSIGNMENT_SUBMISSION
COMPOUND TRIGGER
    AFTER STATEMENT IS
        v_bad NUMBER;
    BEGIN
        SELECT COUNT(*)
        INTO v_bad
        FROM (
            SELECT Assignment_ID, Student_ID
            FROM ASSIGNMENT_SUBMISSION
            GROUP BY Assignment_ID, Student_ID
            HAVING MIN(Submission_Version) <> 1
               OR MAX(Submission_Version) <> COUNT(*)
        );

        IF v_bad > 0 THEN
            RAISE_APPLICATION_ERROR(-20317,
                'Submission_Version values must be continuous starting at 1.');
        END IF;
    END AFTER STATEMENT;
END TRG_SUBMISSION_VERSION_SEQUENCE;
/
/
