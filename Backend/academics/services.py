"""
EduSphere LMS

Academic Service Layer

Enrollment, grading and frontend-readiness offering services.
"""

from accounts.authorization import require_role
from core.constants import Roles, ActivityTypes
from core.exceptions import (
    OfferingNotFoundError,
    DuplicateEnrollmentError,
    CapacityExceededError,
    BusinessRuleError,
    ValidationError,
    PermissionDeniedError,
    NotFoundError,
)
from core.validators import validate_required, validate_positive_integer
from core.audit import log_activity

from .repository import (
    enroll_student,
    get_offering,
    record_mark,
    publish_grade,
    instructor_owns_offering,
    student_has_offering,
    get_grading_scheme,
    get_assessment_components,
    offering_roster,
    get_enrollment_context,
    get_component_context,
)


class EnrollmentService:

    @staticmethod
    def enroll_student(user_id, student_id, offering_id, user_role):
        validate_required(offering_id, "offering_id")
        validate_positive_integer(offering_id, "offering_id")

        require_role(user_role, [Roles.STUDENT])

        offering = get_offering(offering_id)
        if not offering:
            raise OfferingNotFoundError("Offering not found.")

        try:
            result = enroll_student(int(student_id), int(offering_id))
        except Exception as e:
            message = str(e)
            lower = message.lower()

            if "already enrolled" in lower:
                raise DuplicateEnrollmentError(message) from e
            if "capacity" in lower:
                raise CapacityExceededError(message) from e
            if "not open" in lower:
                raise BusinessRuleError(message) from e
            raise

        log_activity(
            user_id=user_id,
            activity_type=ActivityTypes.ENROLLMENT_CREATED,
            activity_description=(
                f"Student {int(student_id)} enrolled in offering {int(offering_id)}"
            ),
        )
        return result


class OfferingService:
    """Read-only offering data required by the frontend."""

    @staticmethod
    def grading(user_role, student_id, instructor_id, offering_id):
        validate_required(offering_id, "offering_id")
        validate_positive_integer(offering_id, "offering_id")
        offering_id = int(offering_id)

        require_role(
            user_role,
            [Roles.STUDENT, Roles.INSTRUCTOR, Roles.ADMIN],
        )

        offering = get_offering(offering_id)
        if not offering:
            raise OfferingNotFoundError("Offering not found.")

        if user_role == Roles.STUDENT:
            if not student_has_offering(student_id, offering_id):
                raise PermissionDeniedError(
                    "Student is not enrolled in this offering."
                )
        elif user_role == Roles.INSTRUCTOR:
            if not instructor_owns_offering(instructor_id, offering_id):
                raise PermissionDeniedError(
                    "Instructor is not assigned to this offering."
                )

        scheme = get_grading_scheme(offering_id)
        components = get_assessment_components(offering_id) if scheme else []

        return {
            "offering": offering,
            "grading_scheme": scheme,
            "component_count": len(components),
            "components": components,
        }

    @staticmethod
    def instructor_roster(user_role, instructor_id, offering_id):
        validate_required(offering_id, "offering_id")
        validate_positive_integer(offering_id, "offering_id")
        offering_id = int(offering_id)

        require_role(user_role, [Roles.INSTRUCTOR, Roles.ADMIN])

        offering = get_offering(offering_id)
        if not offering:
            raise OfferingNotFoundError("Offering not found.")

        if user_role == Roles.INSTRUCTOR:
            if not instructor_owns_offering(instructor_id, offering_id):
                raise PermissionDeniedError(
                    "Instructor is not assigned to this offering."
                )

        rows = offering_roster(offering_id)
        return {
            "offering": offering,
            "roster_count": len(rows),
            "students": rows,
        }


class GradeService:

    @staticmethod
    def record_mark(
        user_id,
        user_role,
        component_id,
        enrollment_id,
        marks_obtained,
        graded_submission_id=None,
        instructor_id=None,
    ):
        validate_required(component_id, "component_id")
        validate_required(enrollment_id, "enrollment_id")
        validate_required(marks_obtained, "marks_obtained")
        validate_positive_integer(component_id, "component_id")
        validate_positive_integer(enrollment_id, "enrollment_id")

        try:
            marks_obtained = float(marks_obtained)
        except (TypeError, ValueError) as exc:
            raise ValidationError("marks_obtained must be numeric.") from exc

        if marks_obtained < 0:
            raise ValidationError("marks_obtained cannot be negative.")

        require_role(user_role, [Roles.INSTRUCTOR, Roles.ADMIN])

        component_id = int(component_id)
        enrollment_id = int(enrollment_id)

        component = get_component_context(component_id)
        if not component:
            raise NotFoundError("Assessment component not found.")

        enrollment = get_enrollment_context(enrollment_id)
        if not enrollment:
            raise NotFoundError("Enrollment not found.")

        if int(component["offering_id"]) != int(enrollment["offering_id"]):
            raise ValidationError(
                "Assessment component and enrollment belong to different offerings."
            )

        if user_role == Roles.INSTRUCTOR:
            if not instructor_owns_offering(
                instructor_id,
                component["offering_id"],
            ):
                raise PermissionDeniedError(
                    "Instructor is not assigned to this offering."
                )

        # A quiz component's STUDENT_MARK is derived from its highest graded
        # attempt; independent manual writes here would corrupt that policy.
        # Instructors should use the quiz grading/review endpoint instead.
        if str(component.get("component_type", "")).upper() == "QUIZ":
            raise BusinessRuleError(
                "Quiz marks are synchronized from quiz attempts. Review the quiz grading instead."
            )

        result = record_mark(
            component_id,
            enrollment_id,
            marks_obtained,
            int(user_id),
            graded_submission_id,
        )

        log_activity(
            user_id=user_id,
            activity_type=ActivityTypes.MARK_RECORDED,
            activity_description=(
                f"Mark recorded for component {component_id} "
                f"and enrollment {enrollment_id}"
            ),
        )
        return result

    @staticmethod
    def publish_grade(
        user_id,
        user_role,
        enrollment_id,
        instructor_id=None,
    ):
        validate_required(enrollment_id, "enrollment_id")
        validate_positive_integer(enrollment_id, "enrollment_id")
        require_role(user_role, [Roles.INSTRUCTOR, Roles.ADMIN])

        enrollment_id = int(enrollment_id)
        enrollment = get_enrollment_context(enrollment_id)
        if not enrollment:
            raise NotFoundError("Enrollment not found.")

        if user_role == Roles.INSTRUCTOR:
            if not instructor_owns_offering(
                instructor_id,
                enrollment["offering_id"],
            ):
                raise PermissionDeniedError(
                    "Instructor is not assigned to this offering."
                )

        result = publish_grade(enrollment_id)

        log_activity(
            user_id=user_id,
            activity_type=ActivityTypes.GRADE_PUBLISHED,
            activity_description=(
                f"Course grade published for enrollment {enrollment_id}"
            ),
        )
        return result
