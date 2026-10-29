"""Request-level lifecycle for the shared Oracle ODBC worker-thread connection."""
from database.connection import oracle_request_scope


class OracleRequestScopeMiddleware:
    """Close the Oracle read transaction at request end, not after each SELECT.

    No connect/disconnect is forced here. Per-thread sessions and explicit
    grading transactions remain owned by database.connection.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        with oracle_request_scope():
            return self.get_response(request)
