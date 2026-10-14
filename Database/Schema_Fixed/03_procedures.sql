-- EduSphere LMS - PROCEDURES
-- Fresh-install object definitions; no migration logic.
SET DEFINE OFF
SET SERVEROUTPUT ON
WHENEVER SQLERROR EXIT SQL.SQLCODE

CREATE OR REPLACE PROCEDURE PR_CLOSE_OFFERING (
    p_Offering_ID IN NUMBER
)
IS
    v_status COURSE_OFFERING.Offering_Status%TYPE;
BEGIN
    SELECT Offering_Status
    INTO v_status
    FROM COURSE_OFFERING
    WHERE Offering_ID = p_Offering_ID
    FOR UPDATE;

    IF v_status = 'OPEN' THEN
        UPDATE COURSE_OFFERING
        SET Offering_Status = 'CLOSED'
        WHERE Offering_ID = p_Offering_ID;
    ELSIF v_status IN ('CLOSED','COMPLETED') THEN
        NULL;
    ELSE
        RAISE_APPLICATION_ERROR(-20324,
            'Only OPEN/CLOSED/COMPLETED offerings can use PR_CLOSE_OFFERING.');
    END IF;
END;
/
/

CREATE OR REPLACE PROCEDURE PR_COMPLETE_OFFERING (
    p_Offering_ID IN NUMBER
)
IS
    v_status       COURSE_OFFERING.Offering_Status%TYPE;
    v_unresolved    NUMBER;
    v_missing_grade NUMBER;
    v_open_attempts NUMBER;
BEGIN
    SELECT Offering_Status
    INTO v_status
    FROM COURSE_OFFERING
    WHERE Offering_ID=p_Offering_ID
    FOR UPDATE;

    IF v_status='COMPLETED' THEN
        RETURN;
    END IF;

    IF v_status<>'CLOSED' THEN
        RAISE_APPLICATION_ERROR(-20402,
            'Offering can be completed only from CLOSED status.');
    END IF;

    SELECT COUNT(*) INTO v_unresolved
    FROM ENROLLMENT
    WHERE Offering_ID=p_Offering_ID
      AND Enrollment_Status IN ('ENROLLED','WAITLISTED');

    IF v_unresolved>0 THEN
        RAISE_APPLICATION_ERROR(-20403,
            'Offering cannot be completed while ENROLLED or WAITLISTED records remain.');
    END IF;

    SELECT COUNT(*) INTO v_missing_grade
    FROM ENROLLMENT e
    WHERE e.Offering_ID=p_Offering_ID
      AND e.Enrollment_Status='COMPLETED'
      AND NOT EXISTS (
          SELECT 1 FROM COURSE_GRADE cg
          WHERE cg.Enrollment_ID=e.Enrollment_ID
      );

    IF v_missing_grade>0 THEN
        RAISE_APPLICATION_ERROR(-20417,
            'Every COMPLETED enrollment must have a published COURSE_GRADE before offering completion.');
    END IF;

    SELECT COUNT(*) INTO v_open_attempts
    FROM QUIZ_ATTEMPT qa
    JOIN QUIZ q ON q.Quiz_ID=qa.Quiz_ID
    JOIN ASSESSMENT_COMPONENT ac ON ac.Component_ID=q.Component_ID
    JOIN GRADING_SCHEME gs ON gs.Scheme_ID=ac.Scheme_ID
    WHERE gs.Offering_ID=p_Offering_ID
      AND qa.Submitted_At IS NULL;

    IF v_open_attempts>0 THEN
        RAISE_APPLICATION_ERROR(-20423,
            'Offering cannot be completed while quiz attempts are still open.');
    END IF;

    UPDATE COURSE_OFFERING
    SET Offering_Status='COMPLETED'
    WHERE Offering_ID=p_Offering_ID;
END;
/
/

CREATE OR REPLACE PROCEDURE PR_ENROLL_STUDENT (
    p_Student_ID  IN NUMBER,
    p_Offering_ID IN NUMBER
)
IS
    v_status          COURSE_OFFERING.Offering_Status%TYPE;
    v_capacity        COURSE_OFFERING.Capacity%TYPE;
    v_student_status  STUDENT.Student_Status%TYPE;
    v_account_status  LMS_USER.Account_Status%TYPE;
    v_count           NUMBER;
BEGIN
    -- Parent-row lock serializes the final-seat decision.
    SELECT Offering_Status, Capacity
    INTO v_status, v_capacity
    FROM COURSE_OFFERING
    WHERE Offering_ID = p_Offering_ID
    FOR UPDATE;

    IF v_status <> 'OPEN' THEN
        RAISE_APPLICATION_ERROR(-20301,
            'Course offering is not open for enrollment.');
    END IF;

    SELECT s.Student_Status, u.Account_Status
    INTO v_student_status, v_account_status
    FROM STUDENT s
    JOIN LMS_USER u
      ON u.User_ID = s.User_ID
    WHERE s.Student_ID = p_Student_ID;

    IF v_student_status <> 'ACTIVE' THEN
        RAISE_APPLICATION_ERROR(-20302,
            'Only an ACTIVE student may enroll.');
    END IF;

    IF v_account_status <> 'ACTIVE' THEN
        RAISE_APPLICATION_ERROR(-20303,
            'Student LMS account must be ACTIVE to enroll.');
    END IF;

    -- COMPLETED remains part of the historical roster and still
    -- consumes the offering's configured capacity.
    SELECT COUNT(*)
    INTO v_count
    FROM ENROLLMENT
    WHERE Offering_ID = p_Offering_ID
      AND Enrollment_Status IN ('ENROLLED','COMPLETED');

    IF v_count >= v_capacity THEN
        RAISE_APPLICATION_ERROR(-20304,
            'Course offering capacity has been reached.');
    END IF;

    SELECT COUNT(*)
    INTO v_count
    FROM ENROLLMENT
    WHERE Student_ID = p_Student_ID
      AND Offering_ID = p_Offering_ID;

    IF v_count > 0 THEN
        RAISE_APPLICATION_ERROR(-20103,
            'Student already has an enrollment record for this offering.');
    END IF;

    INSERT INTO ENROLLMENT (
        Student_ID, Offering_ID, Enrollment_Date, Enrollment_Status
    )
    VALUES (
        p_Student_ID, p_Offering_ID, SYSDATE, 'ENROLLED'
    );
END;
/
/

CREATE OR REPLACE PROCEDURE PR_LOG_ACTIVITY (
    p_User_ID      IN NUMBER,
    p_Activity_Type IN VARCHAR2,
    p_Description  IN VARCHAR2 DEFAULT NULL,
    p_IP_Address   IN VARCHAR2 DEFAULT NULL
)
IS
    v_count NUMBER;
BEGIN
    SELECT COUNT(*) INTO v_count
    FROM LMS_USER
    WHERE User_ID=p_User_ID;

    IF v_count=0 THEN
        RAISE_APPLICATION_ERROR(-20422,
            'Cannot log activity for a nonexistent LMS user.');
    END IF;

    INSERT INTO ACTIVITY_LOG(
        User_ID,Activity_Type,Activity_Description,
        Activity_Date_Time,IP_Address
    ) VALUES (
        p_User_ID,UPPER(p_Activity_Type),p_Description,
        SYSTIMESTAMP,p_IP_Address
    );
END;
/
/

CREATE OR REPLACE PROCEDURE PR_POST_ANNOUNCEMENT (
    p_Offering_ID IN NUMBER,
    p_User_ID IN NUMBER,
    p_Title IN VARCHAR2,
    p_Message IN VARCHAR2,
    p_Priority IN VARCHAR2 DEFAULT 'NORMAL'
)
IS
BEGIN
    INSERT INTO ANNOUNCEMENT (
        Offering_ID, Posted_By_User_ID, Announcement_Title,
        Announcement_Message, Announcement_Priority, Posted_At
    ) VALUES (
        p_Offering_ID, p_User_ID, p_Title,
        p_Message, UPPER(p_Priority), SYSTIMESTAMP
    );
END;
/
/

CREATE OR REPLACE PROCEDURE PR_PUBLISH_GRADE (
    p_Enrollment_ID IN NUMBER
)
IS
    v_percentage      NUMBER;
    v_grade_code      GRADE_SCALE.Grade_Code%TYPE;
    v_count           NUMBER;
    v_missing_marks   NUMBER;
    v_scheme_id       NUMBER;
    v_offering_id     NUMBER;
    v_offering_status COURSE_OFFERING.Offering_Status%TYPE;
    v_enroll_status   ENROLLMENT.Enrollment_Status%TYPE;
BEGIN
    -- Serialize publication for this enrollment.
    SELECT e.Enrollment_Status, e.Offering_ID
    INTO v_enroll_status, v_offering_id
    FROM ENROLLMENT e
    WHERE e.Enrollment_ID = p_Enrollment_ID
    FOR UPDATE;

    SELECT Offering_Status
    INTO v_offering_status
    FROM COURSE_OFFERING
    WHERE Offering_ID = v_offering_id;

    IF v_offering_status NOT IN ('CLOSED','COMPLETED') THEN
        RAISE_APPLICATION_ERROR(-20325,
            'Final grade can be published only after the offering is CLOSED or COMPLETED.');
    END IF;

    SELECT Scheme_ID
    INTO v_scheme_id
    FROM GRADING_SCHEME
    WHERE Offering_ID = v_offering_id;

    IF FN_SCHEME_WEIGHT(v_scheme_id) <> 100 THEN
        RAISE_APPLICATION_ERROR(-20326,
            'Final grade requires a grading scheme totaling exactly 100 percent.');
    END IF;

    SELECT COUNT(*)
    INTO v_missing_marks
    FROM ASSESSMENT_COMPONENT ac
    WHERE ac.Scheme_ID = v_scheme_id
      AND ac.Weight_Percentage > 0
      AND NOT EXISTS (
          SELECT 1
          FROM STUDENT_MARK sm
          WHERE sm.Component_ID = ac.Component_ID
            AND sm.Enrollment_ID = p_Enrollment_ID
      );

    IF v_missing_marks > 0 THEN
        RAISE_APPLICATION_ERROR(-20327,
            'Final grade cannot be published while weighted component marks are missing.');
    END IF;

    v_percentage := FN_COURSE_PERCENT(p_Enrollment_ID);

    SELECT Grade_Code
    INTO v_grade_code
    FROM (
        SELECT Grade_Code
        FROM GRADE_SCALE
        WHERE v_percentage BETWEEN Min_Percentage AND Max_Percentage
        ORDER BY Min_Percentage DESC
    )
    WHERE ROWNUM = 1;

    IF v_enroll_status = 'ENROLLED' THEN
        UPDATE ENROLLMENT
        SET Enrollment_Status = 'COMPLETED'
        WHERE Enrollment_ID = p_Enrollment_ID;
    ELSIF v_enroll_status <> 'COMPLETED' THEN
        RAISE_APPLICATION_ERROR(-20208,
            'Only ENROLLED or already COMPLETED enrollment can receive a final grade.');
    END IF;

    UPDATE COURSE_GRADE
    SET Grade_Code = v_grade_code,
        Published_At = SYSTIMESTAMP
    WHERE Enrollment_ID = p_Enrollment_ID;

    IF SQL%ROWCOUNT = 0 THEN
        BEGIN
            INSERT INTO COURSE_GRADE (
                Enrollment_ID, Grade_Code, Published_At
            )
            VALUES (
                p_Enrollment_ID, v_grade_code, SYSTIMESTAMP
            );
        EXCEPTION
            WHEN DUP_VAL_ON_INDEX THEN
                UPDATE COURSE_GRADE
                SET Grade_Code = v_grade_code,
                    Published_At = SYSTIMESTAMP
                WHERE Enrollment_ID = p_Enrollment_ID;
        END;
    END IF;
EXCEPTION
    WHEN NO_DATA_FOUND THEN
        RAISE_APPLICATION_ERROR(-20130,
            'Required enrollment, grading scheme, or grade-scale band is missing.');
END;
/
/

CREATE OR REPLACE PROCEDURE PR_RECORD_ATTENDANCE (
    p_Session_ID       IN NUMBER,
    p_Student_ID       IN NUMBER,
    p_Attendance_Status IN VARCHAR2,
    p_Remarks          IN VARCHAR2,
    p_Actor_User_ID    IN NUMBER
)
IS
BEGIN
    UPDATE ATTENDANCE
    SET Attendance_Status=UPPER(p_Attendance_Status),
        Remarks=p_Remarks,
        Updated_By_User_ID=p_Actor_User_ID,
        Updated_At=SYSTIMESTAMP
    WHERE Session_ID=p_Session_ID
      AND Student_ID=p_Student_ID;

    IF SQL%ROWCOUNT=0 THEN
        BEGIN
            INSERT INTO ATTENDANCE(
                Session_ID,Student_ID,Attendance_Status,Remarks,
                Recorded_By_User_ID,Recorded_At
            ) VALUES (
                p_Session_ID,p_Student_ID,UPPER(p_Attendance_Status),p_Remarks,
                p_Actor_User_ID,SYSTIMESTAMP
            );
        EXCEPTION
            WHEN DUP_VAL_ON_INDEX THEN
                UPDATE ATTENDANCE
                SET Attendance_Status=UPPER(p_Attendance_Status),
                    Remarks=p_Remarks,
                    Updated_By_User_ID=p_Actor_User_ID,
                    Updated_At=SYSTIMESTAMP
                WHERE Session_ID=p_Session_ID
                  AND Student_ID=p_Student_ID;
        END;
    END IF;
END;
/
/

CREATE OR REPLACE PROCEDURE PR_RECORD_MARK (
    p_Component_ID          IN NUMBER,
    p_Enrollment_ID         IN NUMBER,
    p_Marks_Obtained        IN NUMBER,
    p_Recorded_By_User_ID   IN NUMBER,
    p_Graded_Submission_ID  IN NUMBER DEFAULT NULL
)
IS
BEGIN
    UPDATE STUDENT_MARK
    SET Marks_Obtained=p_Marks_Obtained,
        Recorded_By_User_ID=p_Recorded_By_User_ID,
        Recorded_At=SYSTIMESTAMP,
        Graded_Submission_ID=p_Graded_Submission_ID
    WHERE Component_ID=p_Component_ID
      AND Enrollment_ID=p_Enrollment_ID;

    IF SQL%ROWCOUNT=0 THEN
        BEGIN
            INSERT INTO STUDENT_MARK(
                Component_ID,Enrollment_ID,Marks_Obtained,
                Recorded_By_User_ID,Recorded_At,Graded_Submission_ID
            ) VALUES (
                p_Component_ID,p_Enrollment_ID,p_Marks_Obtained,
                p_Recorded_By_User_ID,SYSTIMESTAMP,p_Graded_Submission_ID
            );
        EXCEPTION
            WHEN DUP_VAL_ON_INDEX THEN
                UPDATE STUDENT_MARK
                SET Marks_Obtained=p_Marks_Obtained,
                    Recorded_By_User_ID=p_Recorded_By_User_ID,
                    Recorded_At=SYSTIMESTAMP,
                    Graded_Submission_ID=p_Graded_Submission_ID
                WHERE Component_ID=p_Component_ID
                  AND Enrollment_ID=p_Enrollment_ID;
        END;
    END IF;
END;
/
/

CREATE OR REPLACE PROCEDURE PR_START_QUIZ_ATTEMPT (
    p_Quiz_ID     IN  NUMBER,
    p_Student_ID  IN  NUMBER,
    p_Attempt_ID  OUT NUMBER
)
IS
    v_open_at       QUIZ.Open_At%TYPE;
    v_close_at      QUIZ.Close_At%TYPE;
    v_max_attempts  QUIZ.Max_Attempts%TYPE;
    v_offering_id   NUMBER;
    v_enrollment_id NUMBER;
    v_attempt_no    NUMBER;
    v_open_attempts NUMBER;
BEGIN
    SELECT q.Open_At,q.Close_At,q.Max_Attempts,gs.Offering_ID
    INTO v_open_at,v_close_at,v_max_attempts,v_offering_id
    FROM QUIZ q
    JOIN ASSESSMENT_COMPONENT ac ON ac.Component_ID=q.Component_ID
    JOIN GRADING_SCHEME gs ON gs.Scheme_ID=ac.Scheme_ID
    WHERE q.Quiz_ID=p_Quiz_ID;

    IF v_open_at IS NOT NULL AND SYSTIMESTAMP<v_open_at THEN
        RAISE_APPLICATION_ERROR(-20110,'Quiz has not opened yet.');
    END IF;
    IF v_close_at IS NOT NULL AND SYSTIMESTAMP>v_close_at THEN
        RAISE_APPLICATION_ERROR(-20111,'Quiz is already closed.');
    END IF;

    -- Serialize attempt allocation through the student's enrollment row.
    SELECT Enrollment_ID INTO v_enrollment_id
    FROM ENROLLMENT
    WHERE Student_ID=p_Student_ID
      AND Offering_ID=v_offering_id
      AND Enrollment_Status='ENROLLED'
    FOR UPDATE;

    SELECT COUNT(*) INTO v_open_attempts
    FROM QUIZ_ATTEMPT
    WHERE Quiz_ID=p_Quiz_ID
      AND Student_ID=p_Student_ID
      AND Submitted_At IS NULL;

    IF v_open_attempts>0 THEN
        RAISE_APPLICATION_ERROR(-20404,
            'Student already has an open attempt for this quiz.');
    END IF;

    SELECT NVL(MAX(Attempt_No),0)+1 INTO v_attempt_no
    FROM QUIZ_ATTEMPT
    WHERE Quiz_ID=p_Quiz_ID
      AND Student_ID=p_Student_ID;

    IF v_attempt_no>v_max_attempts THEN
        RAISE_APPLICATION_ERROR(-20113,
            'Maximum quiz attempts have been used.');
    END IF;

    BEGIN
        INSERT INTO QUIZ_ATTEMPT(Quiz_ID,Student_ID,Attempt_No,Started_At)
        VALUES(p_Quiz_ID,p_Student_ID,v_attempt_no,SYSTIMESTAMP)
        RETURNING Attempt_ID INTO p_Attempt_ID;
    EXCEPTION
        WHEN DUP_VAL_ON_INDEX THEN
            RAISE_APPLICATION_ERROR(-20404,
                'Student already has an open attempt for this quiz.');
    END;
EXCEPTION
    WHEN NO_DATA_FOUND THEN
        RAISE_APPLICATION_ERROR(-20112,
            'Student is not enrolled in this quiz offering.');
END;
/
/

CREATE OR REPLACE PROCEDURE PR_SUBMIT_ASSIGNMENT (
    p_Assignment_ID IN  NUMBER,
    p_Student_ID    IN  NUMBER,
    p_File_URL      IN  VARCHAR2,
    p_Submission_ID OUT NUMBER
)
IS
    v_due_date       ASSIGNMENT.Due_Date%TYPE;
    v_allow_resub    ASSIGNMENT.Allow_Resubmission%TYPE;
    v_offering_id    NUMBER;
    v_enrollment_id  NUMBER;
    v_version        NUMBER;
    v_status         VARCHAR2(20);
BEGIN
    SELECT a.Due_Date, a.Allow_Resubmission, gs.Offering_ID
    INTO v_due_date, v_allow_resub, v_offering_id
    FROM ASSIGNMENT a
    JOIN ASSESSMENT_COMPONENT ac
      ON ac.Component_ID = a.Component_ID
    JOIN GRADING_SCHEME gs
      ON gs.Scheme_ID = ac.Scheme_ID
    WHERE a.Assignment_ID = p_Assignment_ID;

    -- Lock enrollment to serialize version allocation.
    SELECT Enrollment_ID
    INTO v_enrollment_id
    FROM ENROLLMENT
    WHERE Student_ID = p_Student_ID
      AND Offering_ID = v_offering_id
      AND Enrollment_Status = 'ENROLLED'
    FOR UPDATE;

    SELECT NVL(MAX(Submission_Version),0) + 1
    INTO v_version
    FROM ASSIGNMENT_SUBMISSION
    WHERE Assignment_ID = p_Assignment_ID
      AND Student_ID = p_Student_ID;

    IF v_version > 1 AND v_allow_resub <> 'Y' THEN
        RAISE_APPLICATION_ERROR(-20121,
            'Resubmission is not allowed for this assignment.');
    END IF;

    IF SYSTIMESTAMP > v_due_date THEN
        v_status := 'LATE';
    ELSE
        v_status := 'SUBMITTED';
    END IF;

    INSERT INTO ASSIGNMENT_SUBMISSION (
        Assignment_ID, Student_ID, Submission_Version,
        Submitted_At, File_URL, Submission_Status
    )
    VALUES (
        p_Assignment_ID, p_Student_ID, v_version,
        SYSTIMESTAMP, p_File_URL, v_status
    )
    RETURNING Submission_ID INTO p_Submission_ID;
EXCEPTION
    WHEN NO_DATA_FOUND THEN
        RAISE_APPLICATION_ERROR(-20120,
            'Student is not enrolled in this assignment offering.');
END;
/
/

CREATE OR REPLACE PROCEDURE PR_SUBMIT_QUIZ_ATTEMPT (
    p_Attempt_ID IN NUMBER
)
IS
    v_started_at   QUIZ_ATTEMPT.Started_At%TYPE;
    v_submitted_at QUIZ_ATTEMPT.Submitted_At%TYPE;
    v_duration     QUIZ.Duration_Minutes%TYPE;
    v_close_at     QUIZ.Close_At%TYPE;
    v_deadline     TIMESTAMP;
BEGIN
    SELECT qa.Started_At,qa.Submitted_At,q.Duration_Minutes,q.Close_At
    INTO v_started_at,v_submitted_at,v_duration,v_close_at
    FROM QUIZ_ATTEMPT qa
    JOIN QUIZ q ON q.Quiz_ID=qa.Quiz_ID
    WHERE qa.Attempt_ID=p_Attempt_ID
    FOR UPDATE OF qa.Submitted_At;

    IF v_submitted_at IS NOT NULL THEN
        RAISE_APPLICATION_ERROR(-20421,
            'Quiz attempt has already been submitted.');
    END IF;

    IF v_duration IS NOT NULL THEN
        v_deadline:=v_started_at+NUMTODSINTERVAL(v_duration,'MINUTE');
        IF SYSTIMESTAMP>v_deadline THEN
            RAISE_APPLICATION_ERROR(-20407,
                'Quiz duration has expired; this attempt can no longer be submitted.');
        END IF;
    END IF;

    IF v_close_at IS NOT NULL AND SYSTIMESTAMP>v_close_at THEN
        RAISE_APPLICATION_ERROR(-20408,
            'Quiz Close_At has passed; this attempt can no longer be submitted.');
    END IF;

    UPDATE QUIZ_ATTEMPT
    SET Submitted_At=SYSTIMESTAMP
    WHERE Attempt_ID=p_Attempt_ID;
END;
/
/

CREATE OR REPLACE PROCEDURE PR_VALIDATE_SCHEME (
    p_Scheme_ID IN NUMBER
)
IS
    v_total NUMBER;
BEGIN
    v_total := FN_SCHEME_WEIGHT(p_Scheme_ID);

    IF v_total <> 100 THEN
        RAISE_APPLICATION_ERROR(-20104,
            'Assessment component weights must total 100. Current total = ' ||
            TO_CHAR(v_total));
    END IF;

    DBMS_OUTPUT.PUT_LINE('Grading scheme is valid. Total weight = 100.');
END;
/
/
