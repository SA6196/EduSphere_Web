"""
EduSphere LMS

Application Exceptions

Final hardening: explicit HTTP semantics are mapped in core.exception_handler.
"""


class LMSException(Exception):
    """Base LMS application exception."""
    pass


class AuthenticationError(LMSException):
    pass


class PermissionDeniedError(LMSException):
    pass


class NotFoundError(LMSException):
    """Requested LMS resource does not exist."""
    pass


class DatabaseError(LMSException):
    pass


class ValidationError(LMSException):
    """Input validation failure."""
    pass


class BusinessRuleError(LMSException):
    """General LMS business rule violation."""
    pass


class EnrollmentError(LMSException):
    """Base enrollment/business rule exception."""
    pass


class OfferingNotFoundError(NotFoundError):
    pass


class DuplicateEnrollmentError(EnrollmentError):
    pass


class CapacityExceededError(EnrollmentError):
    pass
