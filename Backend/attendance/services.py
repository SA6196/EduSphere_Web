"""
EduSphere LMS

Attendance Services

Handles:
- Session access and creation
- Instructor/admin authorization
- Attendance recording
- Student attendance retrieval
"""

from datetime import date, datetime

from accounts.authorization import require_role
from core.audit import log_activity
from core.constants import Roles, ActivityTypes
from core.exceptions import (
    ValidationError,
    PermissionDeniedError,
    NotFoundError,
    BusinessRuleError,
)
from core.validators import validate_positive_integer, validate_required

from .repository import (
    get_sessions,
    get_session,
    get_offering,
    instructor_owns_offering,
    create_class_session,
    record_attendance,
    get_student_attendance,
    get_student_attendance_for_offering,
    get_student_semester_attendance,
)


class AttendanceService:

    @staticmethod
    def list_sessions(user_role, offering_id):
        require_role(
            user_role,
            (Roles.STUDENT, Roles.INSTRUCTOR, Roles.ADMIN),
        )
        validate_required(offering_id, "offering_id")
        validate_positive_integer(offering_id, "offering_id")
        return get_sessions(int(offering_id))

    @staticmethod
    def create_session(
        user_id,
        instructor_id,
        user_role,
        offering_id,
        session_date,
        start_time,
        end_time=None,
        session_type="LECTURE",
        topic=None,
    ):
        require_role(user_role, (Roles.INSTRUCTOR, Roles.ADMIN))

        validate_required(offering_id, "offering_id")
        validate_positive_integer(offering_id, "offering_id")
        validate_required(session_date, "session_date")
        validate_required(start_time, "start_time")

        offering_id = int(offering_id)
        offering = get_offering(offering_id)
        if not offering:
            raise NotFoundError("Offering not found.")

        if user_role == Roles.INSTRUCTOR:
            if not instructor_owns_offering(instructor_id, offering_id):
                raise PermissionDeniedError(
                    "Instructor is not assigned to this offering."
                )

        if offering["offering_status"] not in ("PLANNED", "OPEN"):
            raise BusinessRuleError(
                "Class sessions can only be created for PLANNED or OPEN offerings."
            )

        try:
            parsed_date = date.fromisoformat(str(session_date))
        except (TypeError, ValueError) as exc:
            raise ValidationError(
                "session_date must use YYYY-MM-DD format."
            ) from exc

        def parse_time(value, field_name):
            if value in (None, ""):
                return None
            try:
                return datetime.strptime(str(value), "%H:%M").time()
            except (TypeError, ValueError) as exc:
                raise ValidationError(
                    f"{field_name} must use HH:MM 24-hour format."
                ) from exc

        start_obj = parse_time(start_time, "start_time")
        end_obj = parse_time(end_time, "end_time")
        if end_obj is not None and end_obj <= start_obj:
            raise ValidationError("end_time must be later than start_time.")

        session_type = str(session_type or "LECTURE").strip().upper()
        allowed_types = {
            "LECTURE",
            "LAB",
            "TUTORIAL",
            "SEMINAR",
            "REVISION",
            "OTHER",
        }
        if session_type not in allowed_types:
            raise ValidationError(
                "session_type must be one of LECTURE, LAB, TUTORIAL, "
                "SEMINAR, REVISION, OTHER."
            )

        # Give a clearer application error while the Oracle semester-date
        # trigger remains the authoritative integrity layer.
        sem_start = offering.get("semester_start_date")
        sem_end = offering.get("semester_end_date")
        if sem_start is not None:
            sem_start_date = sem_start.date() if hasattr(sem_start, "date") else sem_start
            if parsed_date < sem_start_date:
                raise ValidationError(
                    "session_date cannot be before the semester start date."
                )
        if sem_end is not None:
            sem_end_date = sem_end.date() if hasattr(sem_end, "date") else sem_end
            if parsed_date > sem_end_date:
                raise ValidationError(
                    "session_date cannot be after the semester end date."
                )

        created = create_class_session(
            offering_id=offering_id,
            session_date=parsed_date.isoformat(),
            start_time=start_obj.strftime("%H:%M"),
            end_time=end_obj.strftime("%H:%M") if end_obj else None,
            session_type=session_type,
            topic=topic,
        )

        if not created:
            raise ValidationError(
                "Class session was created but could not be reloaded."
            )

        log_activity(
            user_id=user_id,
            activity_type=ActivityTypes.CLASS_SESSION_CREATED,
            activity_description=(
                f"Class session {int(created['session_id'])} created "
                f"for offering {offering_id}"
            ),
        )

        return created

    @staticmethod
    def record(
        user_id,
        instructor_id,
        user_role,
        session_id,
        student_id,
        attendance_status,
        remarks=None,
    ):
        require_role(user_role, (Roles.INSTRUCTOR, Roles.ADMIN))

        validate_required(session_id, "session_id")
        validate_positive_integer(session_id, "session_id")
        validate_required(student_id, "student_id")
        validate_positive_integer(student_id, "student_id")
        validate_required(attendance_status, "attendance_status")

        attendance_status = str(attendance_status).strip().upper()
        if attendance_status not in ("PRESENT", "ABSENT", "LATE", "EXCUSED"):
            raise ValidationError(
                "attendance_status must be PRESENT, ABSENT, LATE, or EXCUSED."
            )

        session = get_session(session_id)
        if not session:
            raise NotFoundError("Class session not found.")

        if user_role == Roles.INSTRUCTOR:
            if not instructor_owns_offering(
                instructor_id,
                session["offering_id"],
            ):
                raise PermissionDeniedError(
                    "Instructor is not assigned to this offering."
                )

        return record_attendance(
            session_id,
            student_id,
            attendance_status,
            remarks,
            user_id,
        )

    @staticmethod
    def student_attendance(student_id):
        if student_id is None:
            raise NotFoundError("Student profile not found.")
        return get_student_attendance(student_id)

    @staticmethod
    def student_semester_attendance(student_id):
        if student_id is None:
            raise NotFoundError("Student profile not found.")
        return get_student_semester_attendance(student_id)

    @staticmethod
    def student_offering_attendance(student_id, offering_id):
        if student_id is None:
            raise NotFoundError("Student profile not found.")

        validate_required(offering_id, "offering_id")
        validate_positive_integer(offering_id, "offering_id")
        return get_student_attendance_for_offering(student_id, offering_id)
