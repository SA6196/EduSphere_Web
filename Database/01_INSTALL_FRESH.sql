-- EduSphere tester package: clean install for EMPTY EDUSPHERE_OWNER in XEPDB1.
-- Approved 37-table DDL is copied verbatim. No built-in account/password seed.
-- NEVER RUN ON THE EXISTING DATABASE THAT HAS STUDENTS / GRADES.
SET SERVEROUTPUT ON SIZE UNLIMITED
SET SQLBLANKLINES ON
SET DEFINE OFF
WHENEVER OSERROR EXIT FAILURE
WHENEVER SQLERROR EXIT SQL.SQLCODE
DECLARE
  v_count NUMBER;
BEGIN
  IF USER <> 'EDUSPHERE_OWNER' THEN
    RAISE_APPLICATION_ERROR(-20661,'Connect as EDUSPHERE_OWNER.');
  END IF;
  IF SYS_CONTEXT('USERENV','CON_NAME') <> 'XEPDB1' THEN
    RAISE_APPLICATION_ERROR(-20662,'Connect specifically to XEPDB1.');
  END IF;
  SELECT COUNT(*) INTO v_count FROM USER_TABLES;
  IF v_count <> 0 THEN
    RAISE_APPLICATION_ERROR(-20663,'STOP: nonempty schema ('||v_count||' tables).');
  END IF;
END;
/
PROMPT [1/8] Approved 37 tables
@@Schema_Fixed/01_create_tables.sql
PROMPT [2/8] Functions
@@Schema_Fixed/02_functions.sql
PROMPT [3/8] Stored procedures
@@Schema_Fixed/03_procedures.sql
PROMPT [4/8] Cursor procedures
@@Schema_Fixed/04_cursor_procedures.sql
PROMPT [5/8] Triggers
@@Schema_Fixed/05_triggers.sql
PROMPT [6/8] Final quiz-expiry procedure and trigger
@@Schema_Fixed/08_finalize_expired_attempts.sql
PROMPT [7/8] Compatibility runtime grants
@@Schema_Fixed/06_grants.sql
PROMPT [8/8] Compliance runtime grants
@@Schema_Fixed/09_compliance_runtime_grants.sql
@@02_VERIFY_FINAL_INSTALL.sql
PROMPT Installed. Next: run the Sample_Data scripts in documented order.
