-- EduSphere DEMO ONLY. Run once, on a freshly installed EDUSPHERE_OWNER.
-- Academic catalog first; account script follows. No user passwords here.
SET DEFINE OFF
SET SERVEROUTPUT ON
WHENEVER SQLERROR EXIT SQL.SQLCODE ROLLBACK
DECLARE
  v_count NUMBER;
BEGIN
  IF USER <> 'EDUSPHERE_OWNER' OR SYS_CONTEXT('USERENV','CON_NAME') <> 'XEPDB1' THEN
    RAISE_APPLICATION_ERROR(-20991, 'STOP: only a fresh EDUSPHERE_OWNER in XEPDB1.');
  END IF;
  SELECT COUNT(*) INTO v_count FROM USER_TABLES;
  IF v_count <> 37 THEN
    RAISE_APPLICATION_ERROR(-20992, 'STOP: expected the approved 37 tables first.');
  END IF;
  SELECT COUNT(*) INTO v_count FROM DEPARTMENT WHERE DEPARTMENT_ID = 910001;
  IF v_count > 0 THEN
    RAISE_APPLICATION_ERROR(-20993, 'Sample catalog already exists: do not run twice.');
  END IF;
END;
/

INSERT INTO DEPARTMENT (Department_ID, Department_Name)
VALUES (910001,'Computer Science and Engineering');
INSERT INTO PROGRAM (Program_ID, Department_ID, Program_Name, Program_Level)
VALUES (910001,910001,'B.Tech Computer Science','UNDERGRADUATE');

INSERT INTO SEMESTER (Semester_ID, Semester_Name, Academic_Year, Semester_Start_Date, Semester_End_Date)
VALUES (910001,'Fall Semester','2025-26',DATE '2025-07-01',DATE '2025-11-30');
INSERT INTO SEMESTER (Semester_ID, Semester_Name, Academic_Year, Semester_Start_Date, Semester_End_Date)
VALUES (910002,'Fall Semester','2026-27',DATE '2026-07-01',DATE '2026-11-30');
INSERT INTO SEMESTER (Semester_ID, Semester_Name, Academic_Year, Semester_Start_Date, Semester_End_Date)
VALUES (910003,'Winter Semester','2026-27',DATE '2026-12-01',DATE '2027-04-30');

INSERT INTO COURSE (Course_ID, Program_ID, Course_Code, Course_Name, Credits, Course_Description)
VALUES (910001,910001,'DEM-DBMS-26','Database Management Systems',4,'Relational modelling, SQL and transactions');
INSERT INTO COURSE (Course_ID, Program_ID, Course_Code, Course_Name, Credits, Course_Description)
VALUES (910002,910001,'DEM-ML-26','Introduction to Machine Learning',4,'Supervised learning and evaluation');
INSERT INTO COURSE (Course_ID, Program_ID, Course_Code, Course_Name, Credits, Course_Description)
VALUES (910003,910001,'DEM-CN-26','Computer Networks',3,'Network protocols and routing');

INSERT INTO COURSE_OFFERING (Offering_ID, Course_ID, Semester_ID, Section_Code, Slot_Day, Start_Time, End_Time, Capacity, Offering_Status)
VALUES (910001,910001,910002,'A','MONDAY','09:00','10:00',40,'OPEN');
INSERT INTO COURSE_OFFERING (Offering_ID, Course_ID, Semester_ID, Section_Code, Slot_Day, Start_Time, End_Time, Capacity, Offering_Status)
VALUES (910002,910002,910002,'A','TUESDAY','11:00','12:00',35,'OPEN');
INSERT INTO COURSE_OFFERING (Offering_ID, Course_ID, Semester_ID, Section_Code, Slot_Day, Start_Time, End_Time, Capacity, Offering_Status)
VALUES (910003,910003,910003,'A','WEDNESDAY','14:00','15:00',40,'PLANNED');
INSERT INTO COURSE_OFFERING (Offering_ID, Course_ID, Semester_ID, Section_Code, Slot_Day, Start_Time, End_Time, Capacity, Offering_Status)
VALUES (910004,910001,910001,'B','THURSDAY','10:00','11:00',40,'COMPLETED');

COMMIT;
PROMPT PASS: sample academic catalog created (3 semesters, 3 courses, 4 offerings).
