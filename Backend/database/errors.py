import re

from rest_framework.exceptions import APIException


ORA_RE = re.compile(r"ORA-(\d{5})")


class OracleBusinessError(APIException):
    status_code = 400
    default_code = "oracle_business_rule"
    default_detail = "The database rejected the operation."


class OracleConflictError(OracleBusinessError):
    status_code = 409
    default_code = "conflict"


class OracleForbiddenError(OracleBusinessError):
    status_code = 403
    default_code = "forbidden"


def extract_ora_code(exc) -> int | None:
    text = " ".join(str(x) for x in getattr(exc, "args", (exc,)))
    match = ORA_RE.search(text)
    return int(match.group(1)) if match else None


def api_exception_from_oracle(exc):
    code = extract_ora_code(exc)
    text = " ".join(str(x) for x in getattr(exc, "args", (exc,)))

    # EduSphere authorization-related application error numbers.
    forbidden_codes = {
        20022, 20023, 20025, 20027,
        20410, 20411,
    }

    if code in forbidden_codes:
        err = OracleForbiddenError(text)
    elif code in {1, 2291, 2292}:
        err = OracleConflictError(text)
    else:
        err = OracleBusinessError(text)

    err.detail = {
        "code": f"ORA-{code:05d}" if code else "ORACLE_ERROR",
        "message": "The requested operation was rejected by the database.",
    }
    return err
