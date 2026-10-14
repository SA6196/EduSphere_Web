"""
EduSphere LMS

Exam Schedule Service Layer
"""

import re
from datetime import date, datetime

from accounts.authorization import require_role
from core.audit import log_activity
from core.constants import ActivityTypes, Roles
from core.exceptions import NotFoundError, PermissionDeniedError, ValidationError
from core.validators import validate_positive_integer, validate_required

from .repository import (
    create_exam,
    get_component_context,
    get_exam,
    get_exam_by_component,
    get_offering_context,
    instructor_owns_offering,
    list_exams_for_offering,
    student_has_offering,
    student_upcoming_exams,
)


_ALLOWED_EXAM_TYPES = {
    "MIDTERM",
    "FINAL",
    "PRACTICAL",
    "INTERNAL",
    "MAKEUP",
    "OTHER",
}

_TIME_RE = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")


class ExamService:

    @staticmethod
    def _clean_title(value):
        if not isinstance(value, str) or not value.strip():
            raise ValidationError("exam_title is required.")
        value = value.strip()
        if len(value) > 200:
            raise ValidationError("exam_title must not exceed 200 characters.")
        return value

    @staticmethod
    def _clean_type(value):
        if not isinstance(value, str) or not value.strip():
            raise ValidationError("exam_type is required.")
        value = value.strip().upper()
        if value not in _ALLOWED_EXAM_TYPES:
            raise ValidationError(
                "exam_type must be one of MIDTERM, FINAL, PRACTICAL, "
                "INTERNAL, MAKEUP, OTHER."
            )
        return value

    @staticmethod
    def _clean_date(value):
        if not isinstance(value, str) or not value.strip():
            raise ValidationError("exam_date is required.")
        value = value.strip()
        try:
            parsed = datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError as exc:
            raise ValidationError("exam_date must use YYYY-MM-DD format.") from exc
        return value, parsed

    @staticmethod
    def _clean_time(value, field_name):
        if value is None or value == "":
            return None
        if not isinstance(value, str):
            raise ValidationError(f"{field_name} must use HH:MM 24-hour format.")
        value = value.strip()
        if not _TIME_RE.fullmatch(value):
            raise ValidationError(f"{field_name} must use HH:MM 24-hour format.")
        return value

    @staticmethod
    def _as_date(value):
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            return datetime.fromisoformat(value).date()
        raise ValidationError("Semester date could not be interpreted.")

    @staticmethod
    def _authorize_offering(user_role, student_id, instructor_id, offering_id):
        require_role(
            user_role,
            [Roles.STUDENT, Roles.INSTRUCTOR, Roles.ADMIN],
        )

        if user_role == Roles.ADMIN:
            return

        if user_role == Roles.INSTRUCTOR:
            if not instructor_id or not instructor_owns_offering(
                int(instructor_id), int(offering_id)
            ):
                raise PermissionDeniedError(
                    "Instructor is not assigned to this offering."
                )
            return

        if not student_id or not student_has_offering(
            int(student_id), int(offering_id)
        ):
            raise PermissionDeniedError(
                "Student is not enrolled in this offering."
            )

    @staticmethod
    def schedule(
        user_id,
        user_role,
        instructor_id,
        component_id,
        exam_title,
        exam_type,
        exam_date,
        start_time=None,
        end_time=None,
    ):
        require_role(user_role, [Roles.INSTRUCTOR, Roles.ADMIN])

        validate_required(component_id, "component_id")
        validate_positive_integer(component_id, "component_id")
        component_id = int(component_id)

        component = get_component_context(component_id)
        if not component:
            raise NotFoundError("Assessment component not found.")

        if component["component_type"] != "EXAM":
            raise ValidationError("Component_Type must be EXAM.")

        offering_id = int(component["offering_id"])

        if user_role == Roles.INSTRUCTOR:
            if not instructor_id or not instructor_owns_offering(
                int(instructor_id), offering_id
            ):
                raise PermissionDeniedError(
                    "Instructor is not assigned to this offering."
                )

        if get_exam_by_component(component_id):
            raise ValidationError(
                "An exam is already scheduled for this component."
            )

        exam_title = ExamService._clean_title(exam_title)
        exam_type = ExamService._clean_type(exam_type)
        exam_date_text, exam_date_value = ExamService._clean_date(exam_date)
        start_time = ExamService._clean_time(start_time, "start_time")
        end_time = ExamService._clean_time(end_time, "end_time")

        if start_time and end_time and end_time <= start_time:
            raise ValidationError("end_time must be later than start_time.")

        semester_start = ExamService._as_date(component["semester_start_date"])
        semester_end = ExamService._as_date(component["semester_end_date"])
        if exam_date_value < semester_start or exam_date_value > semester_end:
            raise ValidationError(
                "exam_date must lie inside the offering semester."
            )

        exam = create_exam(
            component_id=component_id,
            exam_title=exam_title,
            exam_type=exam_type,
            exam_date=exam_date_text,
            start_time=start_time,
            end_time=end_time,
        )

        if not exam:
            raise ValidationError(
                "Exam was scheduled but could not be loaded."
            )

        log_activity(
            user_id=user_id,
            activity_type=ActivityTypes.EXAM_SCHEDULED,
            activity_description=(
                f"Exam scheduled for component {component_id}: {exam_title}"
            ),
        )

        return exam

    @staticmethod
    def list_for_offering(
        user_role,
        student_id,
        instructor_id,
        offering_id,
    ):
        validate_required(offering_id, "offering_id")
        validate_positive_integer(offering_id, "offering_id")
        offering_id = int(offering_id)

        if not get_offering_context(offering_id):
            raise NotFoundError("Offering not found.")

        ExamService._authorize_offering(
            user_role,
            student_id,
            instructor_id,
            offering_id,
        )

        return list_exams_for_offering(offering_id)

    @staticmethod
    def detail(
        user_role,
        student_id,
        instructor_id,
        exam_id,
    ):
        validate_positive_integer(exam_id, "exam_id")
        exam = get_exam(int(exam_id))
        if not exam:
            raise NotFoundError("Exam not found.")

        ExamService._authorize_offering(
            user_role,
            student_id,
            instructor_id,
            int(exam["offering_id"]),
        )

        return exam

    @staticmethod
    def my_upcoming(user_role, student_id):
        require_role(user_role, [Roles.STUDENT])
        if not student_id:
            raise NotFoundError("Student profile not found.")
        return student_upcoming_exams(int(student_id))
