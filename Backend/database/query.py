"""
EduSphere LMS database query abstraction.

Repository SQL uses the shared per-thread Oracle connection so a request
does not repeatedly establish and tear down ODBC sessions.
"""

from .connection import (
    fetch_one,
    fetch_all,
    execute,
    execute_many,
    call_procedure_no_out,
)

__all__ = [
    "fetch_one",
    "fetch_all",
    "execute",
    "execute_many",
    "execute_procedure",
]


def execute_procedure(procedure_name, params=()):
    return call_procedure_no_out(procedure_name, params)
