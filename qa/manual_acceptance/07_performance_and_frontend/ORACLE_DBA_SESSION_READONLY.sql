-- Optional read-only diagnostic. Execute separately as an authorized DBA
-- in the XEPDB1 PDB; do not grant V$SESSION access to EDUSPHERE_APP.
-- Capture these results before, during and after a four-worker benchmark.
SELECT SYSTIMESTAMP AS SAMPLE_TIME FROM DUAL;
SELECT USERNAME, STATUS, MACHINE, PROGRAM, COUNT(*) AS SESSION_COUNT
FROM V$SESSION
WHERE USERNAME = 'EDUSPHERE_APP'
GROUP BY USERNAME, STATUS, MACHINE, PROGRAM
ORDER BY MACHINE, PROGRAM, STATUS;
SELECT COUNT(*) AS EDUSPHERE_APP_SESSION_TOTAL
FROM V$SESSION
WHERE USERNAME = 'EDUSPHERE_APP';
-- The total includes original app, merged app, CLI, diagnostic, and pools
-- using the same account; it is not a per-server physical connection count.
