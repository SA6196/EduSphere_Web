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
# Set before the first pyodbc connection. ODBC driver pooling remains enabled.
pyodbc.pooling = True
_POOL_LOCK = threading.Lock()
_CONNECTION_COUNTS = {"opened": 0, "reused": 0, "recycled": 0, "closed": 0}


def _count(event):
    with _POOL_LOCK:
        _CONNECTION_COUNTS[event] += 1


def connection_statistics():
    """Process-local diagnostics; does not expose DSN or Oracle credentials."""
    with _POOL_LOCK:
        return dict(_CONNECTION_COUNTS)


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
    now = time.monotonic()
    _CONNECTION_STATE.created_at = now
    _CONNECTION_STATE.last_used_at = now
    _count("opened")
    return conn


def _get_connection():
    """Reuse the connection on this worker thread across short operations.

    Long-lived bounded worker threads (e.g. Waitress) maximize reuse.
    Recycle idle/old sessions only outside an explicit transaction, never
    while the quiz/grading unit of work is running.
    """
    conn = getattr(_CONNECTION_STATE, "conn", None)
    now = time.monotonic()
    if conn is not None and not getattr(_CONNECTION_STATE, "tx_depth", 0):
        max_age = int(os.getenv("ODBC_CONNECTION_MAX_AGE_SECONDS", "1800"))
        max_idle = int(os.getenv("ODBC_CONNECTION_MAX_IDLE_SECONDS", "300"))
        age = now - getattr(_CONNECTION_STATE, "created_at", now)
        idle = now - getattr(_CONNECTION_STATE, "last_used_at", now)
        if (max_age > 0 and age > max_age) or (max_idle > 0 and idle > max_idle):
            close_thread_connection()
            _count("recycled")
            conn = None

    if conn is None:
        logger.debug("Opening Oracle connection for worker thread")
        conn = _new_connection()
        _CONNECTION_STATE.conn = conn
    else:
        _count("reused")
    return conn


def close_thread_connection():
    """Close only the current thread's Oracle handle (never another thread's)."""
    conn = getattr(_CONNECTION_STATE, "conn", None)
    if conn is not None:
        try:
            conn.close()
        finally:
            _CONNECTION_STATE.conn = None
            _CONNECTION_STATE.created_at = 0.0
            _CONNECTION_STATE.last_used_at = 0.0
            _count("closed")
            logger.debug("Oracle connection closed for worker thread")


@contextmanager
def oracle_request_scope():
    """Group independent ORM-free SELECTs into one request-scoped read unit.

    Django's middleware calls this once per request. A standalone command or
    background job still releases its own SELECT snapshots, and explicit
    oracle_transaction() blocks still control their own commit/rollback.
    No connection is opened merely by entering this scope.
    """
    depth = getattr(_CONNECTION_STATE, "request_depth", 0)
    _CONNECTION_STATE.request_depth = depth + 1
    try:
        yield
    finally:
        _CONNECTION_STATE.request_depth = depth
        if depth == 0 and not getattr(_CONNECTION_STATE, "tx_depth", 0):
            conn = getattr(_CONNECTION_STATE, "conn", None)
            if conn is not None:
                try:
                    conn.rollback()  # one cleanup for GET-heavy dashboards
                except pyodbc.Error:
                    close_thread_connection()
                    logger.exception("Oracle request cleanup discarded a broken session")


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
    """Use a thread-owned connection without leaving SELECT transactions open.

    Each standalone SELECT is rolled back at the end to clear its Oracle
    transaction/snapshot. Inside oracle_transaction() no implicit commit or
    rollback is performed; the outermost unit of work owns that decision.
    """
    conn = None
    try:
        conn = _get_connection()
        yield conn
        if not getattr(_CONNECTION_STATE, "tx_depth", 0):
            if commit:
                conn.commit()
                logger.debug("Oracle transaction committed")
            elif not getattr(_CONNECTION_STATE, "request_depth", 0):
                conn.rollback()
    except Exception as exc:
        in_transaction = bool(getattr(_CONNECTION_STATE, "tx_depth", 0))
        if in_transaction:
            _CONNECTION_STATE.tx_rollback_only = True
        elif conn is not None:
            try:
                conn.rollback()
            except Exception:
                logger.exception("Oracle rollback failed")
        # Never reuse a known-broken ODBC handle. We do NOT retry DML as doing
        # so could duplicate a write whose commit status is unknown.
        if isinstance(exc, pyodbc.Error):
            if in_transaction:
                _CONNECTION_STATE.discard_after_transaction = True
            else:
                close_thread_connection()
        message = _safe_db_error_message(exc)
        logger.exception("Oracle database operation failed: %s", message)
        raise DatabaseError(message) from exc
    finally:
        if conn is not None and getattr(_CONNECTION_STATE, "conn", None) is conn:
            _CONNECTION_STATE.last_used_at = time.monotonic()


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
            logger.debug("Oracle unit of work committed")
    except Exception as exc:
        _CONNECTION_STATE.tx_rollback_only = True
        if depth == 0:
            try:
                conn.rollback()
            except Exception:
                logger.exception("Oracle transaction rollback failed")
            if isinstance(exc, pyodbc.Error):
                # COMMIT may have failed after the server disconnected.
                # Never retry that transaction or reuse its old handle.
                _CONNECTION_STATE.discard_after_transaction = True
        raise
    finally:
        _CONNECTION_STATE.tx_depth = depth
        if depth == 0:
            _CONNECTION_STATE.tx_rollback_only = False
            if getattr(_CONNECTION_STATE, "discard_after_transaction", False):
                _CONNECTION_STATE.discard_after_transaction = False
                close_thread_connection()


def atomic_oracle(function):
    """Run a service operation and all of its repository writes atomically."""
    @wraps(function)
    def wrapped(*args, **kwargs):
        with oracle_transaction():
            return function(*args, **kwargs)
    return wrapped
