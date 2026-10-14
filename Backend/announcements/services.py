"""
EduSphere LMS

Announcement Service Layer

Authorization rules:
- post: assigned instructor or admin
- read: enrolled/completed student, assigned instructor, or admin

Oracle remains authoritative for write authorization through
PR_POST_ANNOUNCEMENT + TRG_ANNOUNCE_AUTH.
"""

from accounts.authorization import require_role
from core.audit import log_activity
from core.constants import ActivityTypes, Roles
from core.exceptions import NotFoundError, PermissionDeniedError, ValidationError
from core.validators import (
    validate_positive_integer,
    validate_required,
)

from academics.repository import get_offering
from assignments.repository import instructor_owns_offering

from .repository import (
    get_announcement,
    list_announcements,
    post_announcement,
    student_has_offering,
)


_ALLOWED_PRIORITIES = {
    "LOW",
    "NORMAL",
    "HIGH",
    "URGENT",
}


class AnnouncementService:

    @staticmethod
    def _clean_title(title):
        if not isinstance(title, str) or not title.strip():
            raise ValidationError("announcement_title is required.")

        title = title.strip()

        if len(title) > 200:
            raise ValidationError(
                "announcement_title must not exceed 200 characters."
            )

        return title

    @staticmethod
    def _clean_message(message):
        if not isinstance(message, str) or not message.strip():
            raise ValidationError("announcement_message is required.")

        return message.strip()

    @staticmethod
    def _clean_priority(priority):
        if priority is None or priority == "":
            return "NORMAL"

        if not isinstance(priority, str):
            raise ValidationError(
                "announcement_priority must be a string."
            )

        priority = priority.strip().upper()

        if priority not in _ALLOWED_PRIORITIES:
            raise ValidationError(
                "announcement_priority must be one of "
                "LOW, NORMAL, HIGH, URGENT."
            )

        return priority

    @staticmethod
    def _get_verified_offering(offering_id):
        validate_required(
            offering_id,
            "offering_id",
        )

        validate_positive_integer(
            offering_id,
            "offering_id",
        )

        offering = get_offering(
            int(offering_id)
        )

        if not offering:
            raise NotFoundError(
                "Offering not found."
            )

        return offering

    @staticmethod
    def _authorize_read(
        user_role,
        student_id,
        instructor_id,
        offering_id,
    ):
        require_role(
            user_role,
            [
                Roles.STUDENT,
                Roles.INSTRUCTOR,
                Roles.ADMIN,
            ],
        )

        if user_role == Roles.ADMIN:
            return

        if user_role == Roles.INSTRUCTOR:
            if (
                not instructor_id
                or not instructor_owns_offering(
                    instructor_id,
                    offering_id,
                )
            ):
                raise PermissionDeniedError(
                    "Instructor is not assigned to this offering."
                )
            return

        if (
            not student_id
            or not student_has_offering(
                student_id,
                offering_id,
            )
        ):
            raise PermissionDeniedError(
                "Student is not enrolled in this offering."
            )

    @staticmethod
    def create(
        user_id,
        instructor_id,
        user_role,
        offering_id,
        title,
        message,
        priority=None,
    ):
        require_role(
            user_role,
            [
                Roles.INSTRUCTOR,
                Roles.ADMIN,
            ],
        )

        AnnouncementService._get_verified_offering(
            offering_id
        )

        offering_id = int(offering_id)

        if user_role == Roles.INSTRUCTOR:
            if (
                not instructor_id
                or not instructor_owns_offering(
                    instructor_id,
                    offering_id,
                )
            ):
                raise PermissionDeniedError(
                    "Instructor is not assigned to this offering."
                )

        title = AnnouncementService._clean_title(
            title
        )
        message = AnnouncementService._clean_message(
            message
        )
        priority = AnnouncementService._clean_priority(
            priority
        )

        post_announcement(
            offering_id,
            user_id,
            title,
            message,
            priority,
        )

        log_activity(
            user_id=user_id,
            activity_type=ActivityTypes.ANNOUNCEMENT_POSTED,
            activity_description=(
                f"Announcement posted to offering {offering_id}: {title}"
            ),
        )

        return {
            "message": "Announcement posted successfully",
            "offering_id": offering_id,
            "announcement_priority": priority,
        }

    @staticmethod
    def list_for_offering(
        user_role,
        student_id,
        instructor_id,
        offering_id,
    ):
        AnnouncementService._get_verified_offering(
            offering_id
        )

        offering_id = int(offering_id)

        AnnouncementService._authorize_read(
            user_role,
            student_id,
            instructor_id,
            offering_id,
        )

        return list_announcements(
            offering_id
        )

    @staticmethod
    def detail(
        user_role,
        student_id,
        instructor_id,
        announcement_id,
    ):
        validate_positive_integer(
            announcement_id,
            "announcement_id",
        )

        announcement = get_announcement(
            int(announcement_id)
        )

        if not announcement:
            raise NotFoundError(
                "Announcement not found."
            )

        AnnouncementService._authorize_read(
            user_role,
            student_id,
            instructor_id,
            int(announcement["offering_id"]),
        )

        return announcement
