"""Approved 37-table schema: administrative master data and monitoring."""
from datetime import date
from decimal import Decimal, InvalidOperation
from accounts.authorization import require_role
from core.constants import Roles
from core.exceptions import ValidationError, NotFoundError
from database.connection import atomic_oracle
from database.query import execute, fetch_one, fetch_all
from database.schema import object_name
from core.audit import log_activity

VALID_FIELDS = {
    "program": ("PROGRAM", "PROGRAM_ID", ("DEPARTMENT_ID", "PROGRAM_NAME", "PROGRAM_LEVEL")),
    "course": ("COURSE", "COURSE_ID", ("PROGRAM_ID", "COURSE_CODE", "COURSE_NAME", "CREDITS", "COURSE_DESCRIPTION")),
    "semester": ("SEMESTER", "SEMESTER_ID", ("SEMESTER_NAME", "ACADEMIC_YEAR", "SEMESTER_START_DATE", "SEMESTER_END_DATE")),
}


def validated(kind, payload):
    if kind not in VALID_FIELDS or not isinstance(payload, dict):
        raise ValidationError("Invalid master-data request.")
    table, key, allowed = VALID_FIELDS[kind]
    out = {}
    for column in allowed:
        name = column.lower()
        if name not in payload:
            continue
        value = payload[name]
        if column in ("DEPARTMENT_ID", "PROGRAM_ID"):
            try: value = int(value)
            except (ValueError, TypeError) as ex: raise ValidationError(name + " must be an integer.") from ex
            if value <= 0: raise ValidationError(name + " must be positive.")
        elif column == "CREDITS":
            try: value = Decimal(str(value))
            except (InvalidOperation, TypeError) as ex: raise ValidationError("Invalid course credits.") from ex
            if not value.is_finite() or value <= 0 or value > 99.9: raise ValidationError("Credits must be positive and finite.")
            value = float(value)
        elif column.endswith("_DATE"):
            try: value = date.fromisoformat(str(value))
            except (TypeError, ValueError) as ex: raise ValidationError("Use YYYY-MM-DD for " + name) from ex
        elif value is not None:
            value = str(value).strip()
            if not value and column != "COURSE_DESCRIPTION": raise ValidationError(name + " cannot be empty.")
        out[column] = value
    if "SEMESTER_START_DATE" in out and "SEMESTER_END_DATE" in out and out["SEMESTER_END_DATE"] < out["SEMESTER_START_DATE"]:
        raise ValidationError("Semester end date must not precede start date.")
    return out


@atomic_oracle
def save_master_data(actor_id, role, kind, payload, record_id=None):
    require_role(role, [Roles.ADMIN])
    values = validated(kind, payload)
    table, pk, allowed = VALID_FIELDS[kind]
    if record_id is None:
        if set(values) != set(allowed):
            missing = sorted(set(allowed)-set(values))
            raise ValidationError("Missing fields: " + ", ".join(missing))
        fields = list(values)
        execute(f"INSERT INTO {object_name(table)} ({', '.join(fields)}) VALUES ({', '.join('?' for _ in fields)})", tuple(values[f] for f in fields))
        log_activity(int(actor_id), "MASTER_DATA_CREATED", f"{kind.upper()} created")
        return {"message": kind + " created."}
    try: record_id = int(record_id)
    except (ValueError, TypeError) as ex: raise ValidationError("Invalid resource ID.") from ex
    if not values: raise ValidationError("No fields supplied for update.")
    if not fetch_one(f"SELECT {pk} FROM {object_name(table)} WHERE {pk}=?", (record_id,)):
        raise NotFoundError(kind + " not found.")
    fields=list(values)
    execute(f"UPDATE {object_name(table)} SET {', '.join(f + '=?' for f in fields)} WHERE {pk}=?",
            tuple(values[f] for f in fields)+(record_id,))
    log_activity(int(actor_id), "MASTER_DATA_UPDATED", f"{kind.upper()} id={record_id} updated")
    return {"message": kind + " updated.", "id": record_id}


def audit_overview(role, search="", limit=100):
    require_role(role, [Roles.ADMIN])
    try: limit=max(1,min(200,int(limit)))
    except (ValueError, TypeError): raise ValidationError("Invalid audit limit.")
    search=str(search or "").strip()[:100]
    if search:
        logs=fetch_all(
            f"""SELECT al.LOG_ID, al.ACTIVITY_DATE_TIME, al.ACTIVITY_TYPE, al.ACTIVITY_DESCRIPTION,
                       al.USER_ID, u.USERNAME, al.IP_ADDRESS
                FROM {object_name('ACTIVITY_LOG')} al
                JOIN {object_name('LMS_USER')} u ON u.USER_ID=al.USER_ID
                WHERE LOWER(al.ACTIVITY_TYPE) LIKE ? OR LOWER(al.ACTIVITY_DESCRIPTION) LIKE ?
                ORDER BY al.LOG_ID DESC FETCH FIRST {limit} ROWS ONLY""",
            ('%'+search.lower()+'%', '%'+search.lower()+'%'),
        )
    else:
        logs=fetch_all(
            f"""SELECT al.LOG_ID, al.ACTIVITY_DATE_TIME, al.ACTIVITY_TYPE, al.ACTIVITY_DESCRIPTION,
                       al.USER_ID, u.USERNAME, al.IP_ADDRESS
                FROM {object_name('ACTIVITY_LOG')} al
                JOIN {object_name('LMS_USER')} u ON u.USER_ID=al.USER_ID
                ORDER BY al.LOG_ID DESC FETCH FIRST {limit} ROWS ONLY""",
        )
    missing=fetch_all(
        f"""SELECT qa.ATTEMPT_ID, qa.QUIZ_ID, qa.STUDENT_ID
            FROM {object_name('QUIZ_ATTEMPT')} qa
            LEFT JOIN {object_name('QUIZ_GRADING')} g ON g.ATTEMPT_ID=qa.ATTEMPT_ID
            WHERE qa.SUBMITTED_AT IS NOT NULL AND g.GRADING_ID IS NULL
            ORDER BY qa.ATTEMPT_ID DESC FETCH FIRST 50 ROWS ONLY""",
    )
    pending=fetch_all(
        f"""SELECT g.GRADING_ID, qa.ATTEMPT_ID, qa.QUIZ_ID, qa.STUDENT_ID
            FROM {object_name('QUIZ_GRADING')} g
            JOIN {object_name('QUIZ_ATTEMPT')} qa ON qa.ATTEMPT_ID=g.ATTEMPT_ID
            WHERE g.GRADING_STATUS='AUTO_GRADED' AND EXISTS (
                SELECT 1 FROM {object_name('QUIZ_QUESTION')} qq
                JOIN {object_name('QUESTION')} qn ON qn.QUESTION_ID=qq.QUESTION_ID
                WHERE qq.QUIZ_ID=qa.QUIZ_ID AND qn.QUESTION_TYPE='LONG_TEXT'
            ) ORDER BY g.GRADING_ID DESC FETCH FIRST 50 ROWS ONLY""",
    )
    return {"logs":logs,"alerts": [{"kind":"MISSING_GRADING","attempt_id":x['attempt_id'],"quiz_id":x['quiz_id']} for x in missing]
        +[{"kind":"PENDING_ESSAY_REVIEW","attempt_id":x['attempt_id'],"quiz_id":x['quiz_id']} for x in pending]}
