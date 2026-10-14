import os
from pathlib import Path

from dotenv import load_dotenv
import pyodbc

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

explicit = os.getenv("ODBC_CONNECTION_STRING", "").strip()
if explicit:
    connection_string = explicit
else:
    dsn = os.getenv("ODBC_DSN", "").strip()
    user = os.getenv("ODBC_USER", "").strip()
    password = os.getenv("ODBC_PASSWORD", "")
    connection_string = f"DSN={dsn};UID={user};PWD={password}"

schema = os.getenv("ORACLE_SCHEMA", "EDUSPHERE_OWNER").upper().strip()

conn = pyodbc.connect(connection_string, timeout=5)
try:
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM DUAL")
    print("Oracle ping:", cur.fetchone()[0])

    cur.execute(
        """
        SELECT COUNT(*)
        FROM ALL_TABLES
        WHERE OWNER=?
          AND TABLE_NAME='LMS_USER'
        """,
        (schema,),
    )
    print("LMS_USER visible:", cur.fetchone()[0] == 1)
finally:
    conn.close()
