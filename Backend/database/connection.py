import os
import logging
import threading
import time
from functools import wraps
from contextlib import contextmanager

import pyodbc

from core.exceptions import DatabaseError

logger = logging.getLogger(__name__)

# Reuse one pyodbc connection per Django worker thread.  The original V7
# opened and closed a Python/ODBC connection for every SQL statement.
_CONNECTION_STATE = threading.local()
pyodbc.pooling = True


def _connection_string() -> str:
    explicit = os.getenv("ODBC_CONNECTION_STRING", "").strip()
    if explicit:
        return explicit

    dsn = os.getenv("ODBC_DSN", "").strip()
    user = os.getenv("ODBC_USER", "").strip()
    password = os.getenv("ODBC_PASSWORD", "")

    if not dsn or not user or not password:
        raise RuntimeError("Oracle ODBC is not configured.")

    return f"DSN={dsn};UID={user};PWD={password}"


def _new_connection():
    timeout = int(os.getenv("ODBC_TIMEOUT_SECONDS", "5"))
    conn = pyodbc.connect(
        _connection_string(),
        autocommit=False,
        timeout=timeout,
    )
    _CONNECTION_STATE.created_at = time.monotonic()
    return conn


def _get_connection():
    conn = getattr(_CONNECTION_STATE, "conn", None)
    max_age = int(os.getenv("ODBC_CONNECTION_MAX_AGE_SECONDS", "1800"))

    if conn is not None and max_age > 0:
        created_at = getattr(_CONNECTION_STATE, "created_at", 0.0)
        if not getattr(_CONNECTION_STATE, "tx_depth", 0) and time.monotonic() - created_at > max_age:
            try:
                conn.close()
            except Exception:
                pass
            conn = None
            _CONNECTION_STATE.conn = None

    if conn is None:
        logger.info("Opening Oracle connection")
        conn = _new_connection()
        _CONNECTION_STATE.conn = conn

    return conn


def close_thread_connection():
    """Close the persistent connection owned by the current thread."""
    conn = getattr(_CONNECTION_STATE, "conn", None)
    if conn is not None:
        try:
            conn.close()
        finally:
            _CONNECTION_STATE.conn = None
            _CONNECTION_STATE.created_at = 0.0
            logger.info("Oracle connection closed")


def _safe_db_error_message(exc):
    """Avoid turning an ODBC driver's malformed error text into another error."""
    candidates = [
        exc,
        getattr(exc, "__cause__", None),
        getattr(exc, "__context__", None),
    ]
    for candidate in candidates:
        if candidate is None:
            continue
        try:
            message = str(candidate)
        except Exception:
            continue
        if message and "returned a result with an exception set" not in message:
            return message
    return (
        "Oracle database operation failed. "
        "Check the server log for the underlying ODBC/Oracle error."
    )


@contextmanager
def oracle_connection(commit=False):
    conn = None
    try:
        conn = _get_connection()
        yield conn

        # Inside an explicit unit of work, only the outermost transaction
        # may commit. This includes stored procedure calls on this connection.
        if commit and not getattr(_CONNECTION_STATE, "tx_depth", 0):
            conn.commit()
            logger.info("Oracle transaction committed")

    except Exception as exc:
        if getattr(_CONNECTION_STATE, "tx_depth", 0):
            _CONNECTION_STATE.tx_rollback_only = True
        elif conn is not None:
            try:
                conn.rollback()
            except Exception:
                logger.exception("Oracle rollback failed")

        message = _safe_db_error_message(exc)
        logger.exception("Oracle database operation failed: %s", message)
        raise DatabaseError(message) from exc


def row_to_dict(cursor, row):
    columns = [col[0].lower() for col in cursor.description]
    return dict(zip(columns, row))


def fetch_one(sql, params=()):
    with oracle_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(sql, params)
            row = cursor.fetchone()
            if row is None:
                return None
            return row_to_dict(cursor, row)
        finally:
            cursor.close()


def fetch_all(sql, params=()):
    with oracle_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            return [row_to_dict(cursor, row) for row in rows]
        finally:
            cursor.close()


def execute(sql, params=()):
    with oracle_connection(commit=True) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(sql, params)
            return cursor.rowcount
        finally:
            cursor.close()


def execute_many(sql, seq_of_params):
    with oracle_connection(commit=True) as conn:
        cursor = conn.cursor()
        try:
            cursor.fast_executemany = False
            cursor.executemany(sql, seq_of_params)
            return cursor.rowcount
        finally:
            cursor.close()


def call_procedure_no_out(qualified_name, params=()):
    markers = ",".join("?" for _ in params)
    statement = f"{{CALL {qualified_name}({markers})}}"

    with oracle_connection(commit=True) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(statement, params)
        finally:
            cursor.close()


@contextmanager
def oracle_transaction():
    """One Oracle commit for an entire multi-statement business operation.

    Existing fetch/execute/execute_many/procedure helpers all reuse the same
    thread-local connection. Nested transactions join the outer transaction;
    an error anywhere prevents committing a partially completed grade.
    """
    depth = getattr(_CONNECTION_STATE, "tx_depth", 0)
    if depth == 0:
        conn = _get_connection()
        _CONNECTION_STATE.tx_rollback_only = False
    else:
        conn = _get_connection()
    _CONNECTION_STATE.tx_depth = depth + 1
    try:
        yield
        if depth == 0:
            if getattr(_CONNECTION_STATE, "tx_rollback_only", False):
                raise DatabaseError("Database transaction rolled back after a failed statement.")
            conn.commit()
            logger.info("Oracle unit of work committed")
    except Exception:
        _CONNECTION_STATE.tx_rollback_only = True
        if depth == 0:
            try:
                conn.rollback()
            except Exception:
                logger.exception("Oracle transaction rollback failed")
        raise
    finally:
        _CONNECTION_STATE.tx_depth = depth
        if depth == 0:
            _CONNECTION_STATE.tx_rollback_only = False


def atomic_oracle(function):
    """Run a service operation and all of its repository writes atomically."""
    @wraps(function)
    def wrapped(*args, **kwargs):
        with oracle_transaction():
            return function(*args, **kwargs)
    return wrapped
