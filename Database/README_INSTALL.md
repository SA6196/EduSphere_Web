# Database installation (DEVELOPMENT / FRESH SCHEMA ONLY)

The exact approved **37-table DDL** is in `Schema_Fixed/01_create_tables.sql`. Do not change it.

## Files

- `00_create_users_secure.sql`: connect as SYSTEM to XEPDB1; prompt for new OWNER/APP Oracle passwords.
- `01_INSTALL_FRESH.sql`: connect as EDUSPHERE_OWNER to XEPDB1; hard-stops if ANY owner tables already exist. Runs DDL, functions, procedures, triggers, expiry corrections, grants and read-only verification. **No baked-in FINAL_ADMIN login.**
- `02_VERIFY_FINAL_INSTALL.sql`: read-only verification of 37 relations and PL/SQL object status.
- `Sample_Data/01_sample_catalog.sql`: academic catalog, semesters and offerings.
- `Sample_Data/generate_demo_accounts.py`: generate local salted Django-compatible passwords and admin/instructor/student insert SQL.
- `Sample_Data/03_sample_classes.sql`: assignments, attendance, grading components, quiz questions, exams and marks.
- `Sample_Data/04_VERIFY_SAMPLE_DATA.sql`: read-only fixture checks.

## Order

From `Database/` in SQL*Plus with fresh `EDUSPHERE_OWNER`:

```sql
@01_INSTALL_FRESH.sql
```

Then see `../00_START_HERE.md` for local account generation, DML sequencing, and backend/frontend startup.

## Warning

`EDUSPHERE_OWNER` is the exact default schema this package expects. Do not use the installation scripts to create or reset users on a computer with an existing EduSphere database. The app grant scripts retain broad development DML permissions; do not put this installation on a public server without a separate security audit.
