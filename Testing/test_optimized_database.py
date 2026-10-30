"""Offline connection/transaction regression tests. No Oracle installation needed."""
import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

BACKEND = Path(__file__).resolve().parents[1] / "Backend"


class ODBCFailure(Exception):
    pass


class AppDatabaseError(Exception):
    pass


class FakeCursor:
    description = [("ANSWER",)]
    rowcount = 1

    def __init__(self, connection):
        self.connection = connection
        self.closed = False

    def execute(self, sql, params=()):
        self.connection.statements.append((sql, params))
        if self.connection.fail:
            raise ODBCFailure("Simulated lost Oracle connection")
        return self

    def fetchone(self):
        return (42,)

    def fetchall(self):
        return [(42,)]

    def close(self):
        self.closed = True


class FakeConnection:
    def __init__(self):
        self.statements = []
        self.commits = 0
        self.rollbacks = 0
        self.closed = False
        self.fail = False

    def cursor(self):
        return FakeCursor(self)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.closed = True


@pytest.fixture
def oracle(monkeypatch):
    driver = ModuleType("pyodbc")
    driver.pooling = False
    driver.Error = ODBCFailure
    created = []

    def connect(*args, **kwargs):
        c = FakeConnection()
        created.append(c)
        return c

    driver.connect = connect
    core = ModuleType("core")
    core.__path__ = []
    exceptions = ModuleType("core.exceptions")
    exceptions.DatabaseError = AppDatabaseError
    monkeypatch.setitem(sys.modules, "pyodbc", driver)
    monkeypatch.setitem(sys.modules, "core", core)
    monkeypatch.setitem(sys.modules, "core.exceptions", exceptions)
    monkeypatch.setenv("ODBC_CONNECTION_STRING", "DSN=TEST;UID=STAGING;PWD=MOCK")
    monkeypatch.setenv("ODBC_CONNECTION_MAX_AGE_SECONDS", "1800")
    monkeypatch.setenv("ODBC_CONNECTION_MAX_IDLE_SECONDS", "300")
    path = BACKEND / "database" / "connection.py"
    spec = importlib.util.spec_from_file_location("test_scoped_oracle_connection", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    yield module, created, monkeypatch
    module.close_thread_connection()


def test_one_oracle_session_reused_for_separate_reads_and_writes(oracle):
    db, created, _ = oracle
    assert db.fetch_one("SELECT 42 FROM DUAL") == {"answer": 42}
    assert db.fetch_all("SELECT 42 FROM DUAL") == [{"answer": 42}]
    assert db.execute("UPDATE X SET Y=1") == 1
    assert len(created) == 1
    assert created[0].rollbacks == 2  # idle SELECT snapshots released
    assert created[0].commits == 1
    assert db.connection_statistics()["reused"] >= 2


def test_request_scope_uses_one_cleanup_rollback_for_many_reads(oracle):
    db, created, _ = oracle
    with db.oracle_request_scope():
        assert db.fetch_one("SELECT 42 FROM DUAL") == {"answer": 42}
        assert db.fetch_all("SELECT 42 FROM DUAL") == [{"answer": 42}]
        assert len(created) == 1
        assert created[0].rollbacks == 0
    assert created[0].rollbacks == 1
    assert created[0].commits == 0


def test_request_scope_still_commits_writes_before_request_ends(oracle):
    db, created, _ = oracle
    with db.oracle_request_scope():
        with db.oracle_transaction():
            db.execute("UPDATE QUIZ_GRADING SET FINAL_MARKS=1")
        assert created[0].commits == 1
        db.fetch_one("SELECT 42 FROM DUAL")
    assert created[0].commits == 1
    assert created[0].rollbacks == 1


def test_nested_atomic_grading_writes_only_commit_once(oracle):
    db, created, _ = oracle
    with db.oracle_transaction():
        db.execute("INSERT INTO QUIZ_GRADING VALUES (1)")
        with db.oracle_transaction():
            db.execute("INSERT INTO QUIZ_QUESTION_GRADE VALUES (1)")
            db.fetch_one("SELECT 42 FROM DUAL")
        assert created[0].commits == 0
        assert created[0].rollbacks == 0
    assert created[0].commits == 1
    assert created[0].rollbacks == 0


def test_nested_failure_forces_rollback(oracle):
    db, created, _ = oracle
    with pytest.raises(AppDatabaseError):
        with db.oracle_transaction():
            db.execute("INSERT INTO QUIZ_GRADING VALUES (1)")
            with pytest.raises(AppDatabaseError):
                with db.oracle_transaction():
                    created[0].fail = True
                    db.execute("INSERT INTO QUIZ_QUESTION_GRADE VALUES (1)")
    assert created[0].commits == 0
    assert created[0].rollbacks >= 1
    assert created[0].closed


def test_recycle_idle_session_only_outside_transaction(oracle):
    db, created, monkeypatch = oracle
    db.fetch_one("SELECT 42 FROM DUAL")
    monkeypatch.setenv("ODBC_CONNECTION_MAX_IDLE_SECONDS", "1")
    db._CONNECTION_STATE.last_used_at -= 100
    with db.oracle_transaction():
        db.execute("UPDATE X SET Y=1")
        assert len(created) == 2  # idle session safely recycled before UOW
        db._CONNECTION_STATE.last_used_at -= 100
        db.execute("UPDATE X SET Y=2")
        assert len(created) == 2  # never recycle in live UOW
    assert created[1].commits == 1
    assert db.connection_statistics()["recycled"] == 1


def test_broken_odbc_session_is_discarded_not_retried(oracle):
    db, created, _ = oracle
    db.fetch_one("SELECT 42 FROM DUAL")
    created[0].fail = True
    with pytest.raises(AppDatabaseError):
        db.execute("UPDATE SOMETHING SET X=1")
    assert created[0].closed
    assert len(created) == 1  # never retry potentially committed writes
    db.fetch_one("SELECT 42 FROM DUAL")
    assert len(created) == 2


def test_no_duplicate_matching_metadata_calls():
    import ast
    p = BACKEND / "quiz" / "repository.py"
    source = ast.parse(p.read_text(encoding="utf-8"))
    func = next(n for n in source.body if isinstance(n, ast.FunctionDef) and n.name == "get_quiz_content_rows")
    queries = []

    def fetch(sql, params):
        queries.append((sql, params))
        if "LEFT JOIN" in sql:
            return [
                {"question_id": 5, "question_type": "MATCHING", "option_id": 21},
                {"question_id": 5, "question_type": "MATCHING", "option_id": 22},
                {"question_id": 5, "question_type": "MATCHING", "option_id": 23},
                {"question_id": 6, "question_type": "MCQ_SINGLE", "option_id": 24},
            ]
        return [
            {"question_id": 5, "option_id": 21, "match_side": "L", "match_key": "abc"},
            {"question_id": 5, "option_id": 22, "match_side": "R", "match_key": "abc"},
            {"question_id": 5, "option_id": 23, "match_side": "L", "match_key": "def"},
        ]

    env = {"fetch_all": fetch, "object_name": lambda table: table}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[func], type_ignores=[])), str(p), 'exec'), env)
    rows = env['get_quiz_content_rows'](99)
    assert len(queries) == 2  # 1 quiz query + 1 batch instead of 1 per option
    assert queries[1][1] == (5,)
    assert rows[0]["match_side"] == "L"
    assert rows[1]["match_key"] == "abc"
    assert rows[3]["match_key"] is None


