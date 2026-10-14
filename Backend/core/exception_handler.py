"""
EduSphere LMS

Global Exception Handler

Final hardening:
- authentication -> 401
- authorization -> 403
- missing resources -> 404
- validation/business-rule errors -> 400
- DRF status codes are preserved
"""

import logging
import re

from rest_framework import status
from rest_framework.views import exception_handler

from core.responses import error_response
from core.exceptions import (
    LMSException,
    AuthenticationError,
    PermissionDeniedError,
    NotFoundError,
    DatabaseError,
)


logger = logging.getLogger("edusphere")


def _drf_message(data):
    """Return a useful compact message for DRF detail/list/dict errors."""
    if isinstance(data, dict):
        if "detail" in data:
            return str(data["detail"])
        parts = []
        for field, value in data.items():
            if isinstance(value, (list, tuple)):
                text = "; ".join(str(item) for item in value)
            else:
                text = str(value)
            parts.append(f"{field}: {text}")
        return "; ".join(parts) or "Request failed."
    if isinstance(data, (list, tuple)):
        return "; ".join(str(item) for item in data) or "Request failed."
    return str(data) if data is not None else "Request failed."


def _database_status(exc):
    """Classify common Oracle failures without changing DB-side business rules."""
    message = str(exc)

    # Declarative/input/business-rule failures are client-side request failures.
    if "ORA-00001" in message or "ORA-02290" in message:
        return status.HTTP_400_BAD_REQUEST
    if re.search(r"ORA-20\d{3}", message):
        return status.HTTP_400_BAD_REQUEST

    # Connectivity / unavailable database.
    if any(code in message for code in (
        "ORA-12154", "ORA-12170", "ORA-12514", "ORA-12541",
        "ORA-12543", "ORA-03113", "ORA-03114",
    )):
        return status.HTTP_503_SERVICE_UNAVAILABLE

    # Privilege/schema/programming failures are server configuration errors.
    return status.HTTP_500_INTERNAL_SERVER_ERROR


def edusphere_exception_handler(exc, context):
    if isinstance(exc, LMSException):
        if isinstance(exc, AuthenticationError):
            status_code = status.HTTP_401_UNAUTHORIZED
        elif isinstance(exc, PermissionDeniedError):
            status_code = status.HTTP_403_FORBIDDEN
        elif isinstance(exc, NotFoundError):
            status_code = status.HTTP_404_NOT_FOUND
        elif isinstance(exc, DatabaseError):
            status_code = _database_status(exc)
        else:
            status_code = status.HTTP_400_BAD_REQUEST

        log_method = logger.error if status_code >= 500 else logger.warning
        log_method("LMS request error (%s): %s", status_code, str(exc))

        return error_response(
            message=str(exc),
            error_code=exc.__class__.__name__,
            status_code=status_code,
        )

    response = exception_handler(exc, context)
    if response is not None:
        return error_response(
            message=_drf_message(response.data),
            error_code=exc.__class__.__name__,
            status_code=response.status_code,
        )

    logger.exception("Unhandled exception", exc_info=exc)
    return response
