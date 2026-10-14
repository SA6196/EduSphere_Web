-- EduSphere R8 timeout reconciliation (run as EDUSPHERE_OWNER)
-- NO CREATE/ALTER/DROP TABLE. Changes only the two existing PL/SQL objects.
-- Take a backup and test on staging before applying to production.
-- On expiry, student answers remain locked by TRG_QUIZ_RESPONSE and child triggers.
-- Existing submission procedure still requires an open and valid attempt.

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

    -- Finalization can happen after the deadline. TRG_QUIZ_RESPONSE and
    -- the response-child triggers still reject late answer modifications.
    -- Only previously saved answers are graded on expiry.

    UPDATE QUIZ_ATTEMPT
    SET Submitted_At=SYSTIMESTAMP
    WHERE Attempt_ID=p_Attempt_ID;
END;
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

        -- Deadline applies to response changes, not finalization.
        -- The submitted timestamp remains Oracle-generated.
    END IF;
END;
/
