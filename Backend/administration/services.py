from decimal import Decimal, InvalidOperation
import re

from django.contrib.auth.hashers import make_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email

from accounts.authorization import require_role
from core.constants import Roles
from core.exceptions import BusinessRuleError, NotFoundError, ValidationError, PermissionDeniedError

from assignments.repository import instructor_owns_offering

from .repository import (
    create_instructor_account,
    create_offering,
    create_student_account,
    get_active_instructors_by_ids,
    get_course,
    get_department,
    get_offering_admin,
    get_offering_instructors,
    get_program,
    get_semester,
    grading_scheme_admin,
    identity_conflicts,
    list_departments,
    list_instructors,
    list_programs,
    list_students,
    published_grade_count,
    replace_offering_instructors,
    save_grading_scheme,
)


ACCOUNT_STATUSES = {"ACTIVE", "INACTIVE", "LOCKED"}
STUDENT_STATUSES = {"ACTIVE", "INACTIVE", "GRADUATED", "SUSPENDED", "WITHDRAWN"}
OFFERING_STATUSES_CREATE = {"PLANNED", "OPEN"}
DAYS = {"MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"}
COMPONENT_TYPES = {"ASSIGNMENT", "QUIZ", "EXAM", "OTHER"}
TIME_RE = re.compile(r"^([01][0-9]|2[0-3]):[0-5][0-9]$")


def _required(data, field):
    value = data.get(field)
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ValidationError(f"{field} is required.")
    return value.strip() if isinstance(value, str) else value


def _positive_int(value, field):
    try:
        value = int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{field} must be an integer.") from exc
    if value <= 0:
        raise ValidationError(f"{field} must be positive.")
    return value


def _money_number(value, field, allow_zero=False):
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValidationError(f"{field} must be numeric.") from exc
    if result < 0 or (not allow_zero and result == 0):
        raise ValidationError(f"{field} must be {'zero or positive' if allow_zero else 'positive'}.")
    return result


def _password(password):
    if not isinstance(password, str) or len(password) < 6:
        raise ValidationError("password must contain at least 6 characters.")
    return password


def _email(email):
    email = str(email).strip().lower()
    try:
        validate_email(email)
    except DjangoValidationError as exc:
        raise ValidationError("email must be a valid email address.") from exc
    return email


def _ensure_unique_identity(username, email, admission_no=None):
    conflicts = identity_conflicts(username, email, admission_no)
    if conflicts["username"]:
        raise BusinessRuleError("Username is already in use.")
    if conflicts["email"]:
        raise BusinessRuleError("Email address is already in use.")
    if conflicts.get("admission_no"):
        raise BusinessRuleError("Admission number is already in use.")


class AdminIdentityService:
    @staticmethod
    def directory(user_role):
        require_role(user_role, [Roles.ADMIN])
        return {
            "students": list_students(),
            "instructors": list_instructors(),
            "departments": list_departments(),
            "programs": list_programs(),
        }

    @staticmethod
    def create_student(actor_user_id, user_role, data):
        require_role(user_role, [Roles.ADMIN])
        username = _required(data, "username")
        email = _email(_required(data, "email"))
        password = _password(_required(data, "password"))
        student_name = _required(data, "student_name")
        admission_no = _required(data, "admission_no")
        program_id = _positive_int(_required(data, "program_id"), "program_id")
        if not get_program(program_id):
            raise NotFoundError("Program not found.")
        _ensure_unique_identity(username, email, admission_no)

        account_status = str(data.get("account_status") or "ACTIVE").upper()
        student_status = str(data.get("student_status") or "ACTIVE").upper()
        if account_status not in ACCOUNT_STATUSES:
            raise ValidationError("Invalid account_status.")
        if student_status not in STUDENT_STATUSES:
            raise ValidationError("Invalid student_status.")

        clean = {
            "username": username,
            "email": email,
            "phone": (data.get("phone") or "").strip() or None,
            "student_name": student_name,
            "admission_no": admission_no,
            "batch": (data.get("batch") or "").strip() or None,
            "program_id": program_id,
            "account_status": account_status,
            "student_status": student_status,
        }
        return create_student_account(actor_user_id, make_password(password), clean)

    @staticmethod
    def create_instructor(actor_user_id, user_role, data):
        require_role(user_role, [Roles.ADMIN])
        username = _required(data, "username")
        email = _email(_required(data, "email"))
        password = _password(_required(data, "password"))
        instructor_name = _required(data, "instructor_name")
        department_id = _positive_int(_required(data, "department_id"), "department_id")
        if not get_department(department_id):
            raise NotFoundError("Department not found.")
        _ensure_unique_identity(username, email)

        account_status = str(data.get("account_status") or "ACTIVE").upper()
        if account_status not in ACCOUNT_STATUSES:
            raise ValidationError("Invalid account_status.")

        clean = {
            "username": username,
            "email": email,
            "phone": (data.get("phone") or "").strip() or None,
            "instructor_name": instructor_name,
            "designation": (data.get("designation") or "").strip() or None,
            "department_id": department_id,
            "account_status": account_status,
        }
        return create_instructor_account(actor_user_id, make_password(password), clean)


class AdminOfferingService:
    @staticmethod
    def create(actor_user_id, user_role, data):
        require_role(user_role, [Roles.ADMIN])
        course_id = _positive_int(_required(data, "course_id"), "course_id")
        semester_id = _positive_int(_required(data, "semester_id"), "semester_id")
        section_code = _required(data, "section_code")
        capacity = _positive_int(data.get("capacity", 60), "capacity")
        status = str(data.get("offering_status") or "PLANNED").upper()
        if status not in OFFERING_STATUSES_CREATE:
            raise ValidationError("New offerings must start as PLANNED or OPEN.")
        if not get_course(course_id):
            raise NotFoundError("Course not found.")
        if not get_semester(semester_id):
            raise NotFoundError("Semester not found.")

        slot_day = str(data.get("slot_day") or "").upper() or None
        if slot_day and slot_day not in DAYS:
            raise ValidationError("Invalid slot_day.")
        start_time = str(data.get("start_time") or "").strip() or None
        end_time = str(data.get("end_time") or "").strip() or None
        if bool(start_time) != bool(end_time):
            raise ValidationError("start_time and end_time must be provided together.")
        if start_time:
            if not TIME_RE.match(start_time) or not TIME_RE.match(end_time):
                raise ValidationError("Times must use HH:MM in 24-hour format.")
            if end_time <= start_time:
                raise ValidationError("end_time must be later than start_time.")

        instructor_ids = data.get("instructor_ids") or []
        try:
            instructor_ids = sorted({int(x) for x in instructor_ids})
        except (TypeError, ValueError) as exc:
            raise ValidationError("instructor_ids must contain integer IDs.") from exc
        active = get_active_instructors_by_ids(instructor_ids)
        if len(active) != len(instructor_ids):
            raise ValidationError("Every assigned instructor must exist and have an ACTIVE account.")

        clean = {
            "course_id": course_id,
            "semester_id": semester_id,
            "section_code": section_code,
            "slot_day": slot_day,
            "start_time": start_time,
            "end_time": end_time,
            "capacity": capacity,
            "offering_status": status,
        }
        result = create_offering(actor_user_id, clean, instructor_ids)
        return {"offering": result, "instructors": get_offering_instructors(result["offering_id"])}

    @staticmethod
    def instructors(user_role, offering_id):
        require_role(user_role, [Roles.ADMIN])
        offering_id = _positive_int(offering_id, "offering_id")
        if not get_offering_admin(offering_id):
            raise NotFoundError("Offering not found.")
        return get_offering_instructors(offering_id)

    @staticmethod
    def replace_instructors(actor_user_id, user_role, offering_id, instructor_ids):
        require_role(user_role, [Roles.ADMIN])
        offering_id = _positive_int(offering_id, "offering_id")
        if not get_offering_admin(offering_id):
            raise NotFoundError("Offering not found.")
        if instructor_ids is None:
            raise ValidationError("instructor_ids is required.")
        try:
            instructor_ids = sorted({int(x) for x in instructor_ids})
        except (TypeError, ValueError) as exc:
            raise ValidationError("instructor_ids must contain integer IDs.") from exc
        active = get_active_instructors_by_ids(instructor_ids)
        if len(active) != len(instructor_ids):
            raise ValidationError("Every assigned instructor must exist and have an ACTIVE account.")
        return replace_offering_instructors(actor_user_id, offering_id, instructor_ids)


class AdminGradingService:
    @staticmethod
    def get(user_role, offering_id, instructor_id=None):
        require_role(user_role, [Roles.ADMIN, Roles.INSTRUCTOR])
        offering_id = _positive_int(offering_id, "offering_id")
        if user_role == Roles.INSTRUCTOR and not instructor_owns_offering(instructor_id, offering_id):
            raise PermissionDeniedError("Instructor does not teach this offering.")
        offering = get_offering_admin(offering_id)
        if not offering:
            raise NotFoundError("Offering not found.")
        result = grading_scheme_admin(offering_id)
        total = sum(Decimal(str(c["weight_percentage"])) for c in result["components"])
        result.update({
            "offering": offering,
            "total_weight": float(total),
            "is_valid": total == Decimal("100"),
            "published_grade_count": published_grade_count(offering_id),
        })
        return result

    @staticmethod
    def save(actor_user_id, user_role, offering_id, data, instructor_id=None):
        require_role(user_role, [Roles.ADMIN, Roles.INSTRUCTOR])
        offering_id = _positive_int(offering_id, "offering_id")
        if user_role == Roles.INSTRUCTOR and not instructor_owns_offering(instructor_id, offering_id):
            raise PermissionDeniedError("Instructor does not teach this offering.")
        offering = get_offering_admin(offering_id)
        if not offering:
            raise NotFoundError("Offering not found.")
        if published_grade_count(offering_id) > 0:
            raise BusinessRuleError(
                "Grading scheme cannot be changed after a final course grade has been published for this offering."
            )

        scheme_name = _required(data, "scheme_name")
        components = data.get("components")
        if not isinstance(components, list) or not components:
            raise ValidationError("components must contain at least one assessment component.")

        current = grading_scheme_admin(offering_id)
        existing_ids = {int(c["component_id"]) for c in current["components"]}
        supplied_existing_ids = set()
        names = set()
        cleaned = []
        total = Decimal("0")

        for index, component in enumerate(components, start=1):
            if not isinstance(component, dict):
                raise ValidationError(f"Component {index} is invalid.")
            component_id = component.get("component_id")
            if component_id not in (None, ""):
                component_id = _positive_int(component_id, f"components[{index}].component_id")
                if component_id not in existing_ids:
                    raise ValidationError(f"Component {component_id} does not belong to this offering.")
                supplied_existing_ids.add(component_id)

            name = _required(component, "component_name")
            name_key = name.casefold()
            if name_key in names:
                raise ValidationError("Assessment component names must be unique within the scheme.")
            names.add(name_key)

            component_type = str(_required(component, "component_type")).upper()
            if component_type not in COMPONENT_TYPES:
                raise ValidationError("Invalid component_type.")
            weight = _money_number(_required(component, "weight_percentage"), "weight_percentage", allow_zero=True)
            max_marks = _money_number(_required(component, "max_marks"), "max_marks")
            if weight > 100:
                raise ValidationError("Each weight_percentage must be between 0 and 100.")
            total += weight
            cleaned.append({
                "component_id": component_id,
                "component_name": name,
                "component_type": component_type,
                "weight_percentage": float(weight),
                "max_marks": float(max_marks),
            })

        if existing_ids != supplied_existing_ids:
            raise ValidationError(
                "All existing assessment components must remain in the submitted scheme; existing components are not deleted through this screen."
            )
        if total != Decimal("100"):
            raise ValidationError(f"Assessment component weights must total exactly 100. Current total = {total}.")

        result = save_grading_scheme(actor_user_id, offering_id, scheme_name, cleaned)
        result["total_weight"] = 100.0
        result["is_valid"] = True
        return result
