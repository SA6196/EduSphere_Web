-- Run AFTER 01_sample_catalog.sql AND locally generated 02_accounts.generated.sql.
-- Demo offering rosters, attendance, schemes, examination/quiz and past marks.
SET DEFINE OFF
SET SERVEROUTPUT ON
WHENEVER SQLERROR EXIT SQL.SQLCODE ROLLBACK
DECLARE
  v_count NUMBER;
BEGIN
  IF USER <> 'EDUSPHERE_OWNER' OR SYS_CONTEXT('USERENV','CON_NAME') <> 'XEPDB1' THEN
    RAISE_APPLICATION_ERROR(-20994, 'STOP: sample data is only for EDUSPHERE_OWNER in XEPDB1.');
  END IF;
  SELECT COUNT(*) INTO v_count FROM LMS_USER WHERE USER_ID BETWEEN 920001 AND 920005;
  IF v_count <> 5 THEN
    RAISE_APPLICATION_ERROR(-20995,'STOP: generate and install all five demo accounts first.');
  END IF;
  SELECT COUNT(*) INTO v_count FROM OFFERING_INSTRUCTOR WHERE OFFERING_INSTRUCTOR_ID = 930001;
  IF v_count > 0 THEN
    RAISE_APPLICATION_ERROR(-20996,'STOP: sample classroom data already exists.');
  END IF;
END;
/

-- Offering instructor authorization controls quiz, material and attendance access.
INSERT INTO OFFERING_INSTRUCTOR (Offering_Instructor_ID,Offering_ID,Instructor_ID) VALUES (930001,910001,920001);
INSERT INTO OFFERING_INSTRUCTOR (Offering_Instructor_ID,Offering_ID,Instructor_ID) VALUES (930002,910002,920002);
INSERT INTO OFFERING_INSTRUCTOR (Offering_Instructor_ID,Offering_ID,Instructor_ID) VALUES (930003,910003,920002);
INSERT INTO OFFERING_INSTRUCTOR (Offering_Instructor_ID,Offering_ID,Instructor_ID) VALUES (930004,910004,920001);

-- Student IDs 920001 and 920002 are created by the local account generator.
INSERT INTO ENROLLMENT (Enrollment_ID,Student_ID,Offering_ID,Enrollment_Date,Enrollment_Status)
VALUES (930001,920001,910001,DATE '2026-07-15','ENROLLED');
INSERT INTO ENROLLMENT (Enrollment_ID,Student_ID,Offering_ID,Enrollment_Date,Enrollment_Status)
VALUES (930002,920002,910001,DATE '2026-07-15','ENROLLED');
INSERT INTO ENROLLMENT (Enrollment_ID,Student_ID,Offering_ID,Enrollment_Date,Enrollment_Status)
VALUES (930003,920001,910002,DATE '2026-07-15','ENROLLED');
INSERT INTO ENROLLMENT (Enrollment_ID,Student_ID,Offering_ID,Enrollment_Date,Enrollment_Status)
VALUES (930004,920001,910004,DATE '2025-07-15','COMPLETED');
-- Planned Winter offering intentionally not enrolled yet.

INSERT INTO CLASS_SESSION (Session_ID,Offering_ID,Session_Date,Start_Time,End_Time,Session_Type,Topic)
VALUES (930001,910001,DATE '2026-10-01','09:00','10:00','LECTURE','Keys and normalization');
INSERT INTO CLASS_SESSION (Session_ID,Offering_ID,Session_Date,Start_Time,End_Time,Session_Type,Topic)
VALUES (930002,910001,DATE '2026-10-05','09:00','10:00','LECTURE','SQL joins');
INSERT INTO CLASS_SESSION (Session_ID,Offering_ID,Session_Date,Start_Time,End_Time,Session_Type,Topic)
VALUES (930003,910001,DATE '2026-10-08','09:00','10:00','LAB','Transactions and rollback');
INSERT INTO CLASS_SESSION (Session_ID,Offering_ID,Session_Date,Start_Time,End_Time,Session_Type,Topic)
VALUES (930004,910002,DATE '2026-10-06','11:00','12:00','LECTURE','Classification metrics');
INSERT INTO CLASS_SESSION (Session_ID,Offering_ID,Session_Date,Start_Time,End_Time,Session_Type,Topic)
VALUES (930005,910002,DATE '2026-10-13','11:00','12:00','LECTURE','Decision trees');
INSERT INTO CLASS_SESSION (Session_ID,Offering_ID,Session_Date,Start_Time,End_Time,Session_Type,Topic)
VALUES (930006,910004,DATE '2025-10-09','10:00','11:00','LECTURE','Normal forms');

INSERT INTO ATTENDANCE (Attendance_ID,Session_ID,Student_ID,Attendance_Status,Recorded_By_User_ID)
VALUES (930001,930001,920001,'PRESENT',920002);
INSERT INTO ATTENDANCE (Attendance_ID,Session_ID,Student_ID,Attendance_Status,Recorded_By_User_ID)
VALUES (930002,930002,920001,'ABSENT',920002);
INSERT INTO ATTENDANCE (Attendance_ID,Session_ID,Student_ID,Attendance_Status,Recorded_By_User_ID)
VALUES (930003,930003,920001,'LATE',920002);
INSERT INTO ATTENDANCE (Attendance_ID,Session_ID,Student_ID,Attendance_Status,Recorded_By_User_ID)
VALUES (930004,930001,920002,'PRESENT',920002);
INSERT INTO ATTENDANCE (Attendance_ID,Session_ID,Student_ID,Attendance_Status,Recorded_By_User_ID)
VALUES (930005,930002,920002,'PRESENT',920002);
INSERT INTO ATTENDANCE (Attendance_ID,Session_ID,Student_ID,Attendance_Status,Recorded_By_User_ID)
VALUES (930006,930004,920001,'PRESENT',920003);
INSERT INTO ATTENDANCE (Attendance_ID,Session_ID,Student_ID,Attendance_Status,Recorded_By_User_ID)
VALUES (930007,930006,920001,'PRESENT',920002);

INSERT INTO GRADING_SCHEME (Scheme_ID,Offering_ID,Scheme_Name) VALUES (940001,910001,'DBMS Assessment Plan');
INSERT INTO GRADING_SCHEME (Scheme_ID,Offering_ID,Scheme_Name) VALUES (940002,910002,'ML Assessment Plan');
INSERT INTO GRADING_SCHEME (Scheme_ID,Offering_ID,Scheme_Name) VALUES (940003,910004,'Previous DBMS Plan');
INSERT INTO ASSESSMENT_COMPONENT (Component_ID,Scheme_ID,Component_Name,Component_Type,Weight_Percentage,Max_Marks)
VALUES (940001,940001,'DBMS Practice Quiz','QUIZ',20,10);
INSERT INTO ASSESSMENT_COMPONENT (Component_ID,Scheme_ID,Component_Name,Component_Type,Weight_Percentage,Max_Marks)
VALUES (940002,940001,'DBMS Midterm','EXAM',30,50);
INSERT INTO ASSESSMENT_COMPONENT (Component_ID,Scheme_ID,Component_Name,Component_Type,Weight_Percentage,Max_Marks)
VALUES (940003,940001,'DBMS Assignment','ASSIGNMENT',20,20);
INSERT INTO ASSESSMENT_COMPONENT (Component_ID,Scheme_ID,Component_Name,Component_Type,Weight_Percentage,Max_Marks)
VALUES (940004,940001,'DBMS Final','EXAM',30,100);
INSERT INTO ASSESSMENT_COMPONENT (Component_ID,Scheme_ID,Component_Name,Component_Type,Weight_Percentage,Max_Marks)
VALUES (940005,940002,'ML Midterm','EXAM',50,50);
INSERT INTO ASSESSMENT_COMPONENT (Component_ID,Scheme_ID,Component_Name,Component_Type,Weight_Percentage,Max_Marks)
VALUES (940006,940002,'ML Project','ASSIGNMENT',50,100);
INSERT INTO ASSESSMENT_COMPONENT (Component_ID,Scheme_ID,Component_Name,Component_Type,Weight_Percentage,Max_Marks)
VALUES (940007,940003,'Previous DBMS Midterm','EXAM',100,50);

INSERT INTO EXAM (Exam_ID,Component_ID,Exam_Title,Exam_Type,Exam_Date,Start_Time,End_Time)
VALUES (940001,940002,'DBMS Midterm','MIDTERM',DATE '2026-10-22','10:00','11:30');
INSERT INTO EXAM (Exam_ID,Component_ID,Exam_Title,Exam_Type,Exam_Date,Start_Time,End_Time)
VALUES (940002,940004,'DBMS Final','FINAL',DATE '2026-11-20','09:00','11:00');
INSERT INTO EXAM (Exam_ID,Component_ID,Exam_Title,Exam_Type,Exam_Date,Start_Time,End_Time)
VALUES (940003,940005,'ML Midterm','MIDTERM',DATE '2026-10-23','10:00','11:30');
INSERT INTO EXAM (Exam_ID,Component_ID,Exam_Title,Exam_Type,Exam_Date,Start_Time,End_Time)
VALUES (940004,940007,'Previous DBMS Midterm','MIDTERM',DATE '2025-10-20','10:00','11:30');

INSERT INTO ASSIGNMENT (Assignment_ID,Component_ID,Assignment_Title,Assignment_Description,Due_Date,Allow_Resubmission)
VALUES (940001,940003,'Normalize a Student Database','Submit 1NF-3NF mapping and explanations',TIMESTAMP '2026-11-10 23:59:00','Y');
INSERT INTO ASSIGNMENT (Assignment_ID,Component_ID,Assignment_Title,Assignment_Description,Due_Date,Allow_Resubmission)
VALUES (940002,940006,'ML Mini Project','Compare two classifiers',TIMESTAMP '2026-11-15 23:59:00','Y');

-- A live quiz with two objective questions; all marks add up to the component max (10).
INSERT INTO QUESTION (Question_ID,Question_Text,Question_Type)
VALUES (940001,'Which normal form eliminates partial dependencies?','MCQ_SINGLE');
INSERT INTO QUESTION_OPTION (Option_ID,Question_ID,Option_Text,Is_Correct,Option_Order)
VALUES (940001,940001,'1NF','N',1);
INSERT INTO QUESTION_OPTION (Option_ID,Question_ID,Option_Text,Is_Correct,Option_Order)
VALUES (940002,940001,'2NF','Y',2);
INSERT INTO QUESTION_OPTION (Option_ID,Question_ID,Option_Text,Is_Correct,Option_Order)
VALUES (940003,940001,'3NF','N',3);
INSERT INTO QUESTION (Question_ID,Question_Text,Question_Type)
VALUES (940002,'A primary key must uniquely identify each table row.','TRUE_FALSE');
INSERT INTO QUESTION_OPTION (Option_ID,Question_ID,Option_Text,Is_Correct,Option_Order)
VALUES (940004,940002,'True','Y',1);
INSERT INTO QUESTION_OPTION (Option_ID,Question_ID,Option_Text,Is_Correct,Option_Order)
VALUES (940005,940002,'False','N',2);
INSERT INTO QUIZ (Quiz_ID,Component_ID,Quiz_Title,Open_At,Close_At,Duration_Minutes,Max_Attempts,Allow_Mark_View,Allow_Answer_Review)
VALUES (940001,940001,'DBMS Practice Quiz',TIMESTAMP '2026-10-01 08:00:00',TIMESTAMP '2026-11-28 23:00:00',30,2,'Y','N');
INSERT INTO QUIZ_QUESTION (Quiz_ID,Question_ID,Question_Order,Question_Marks)
VALUES (940001,940001,1,5);
INSERT INTO QUIZ_QUESTION (Quiz_ID,Question_ID,Question_Order,Question_Marks)
VALUES (940001,940002,2,5);

INSERT INTO STUDENT_MARK (Mark_ID,Component_ID,Enrollment_ID,Marks_Obtained,Recorded_By_User_ID)
VALUES (940001,940007,930004,41,920002);

COMMIT;
PROMPT PASS: courses, rosters, attendance, components, sample quiz and historical mark created.
