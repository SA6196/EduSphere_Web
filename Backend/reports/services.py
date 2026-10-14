"""EduSphere LMS - Admin reporting service layer."""

from accounts.authorization import require_role
from core.constants import Roles
from core.exceptions import NotFoundError, ValidationError
from core.validators import validate_positive_integer, validate_required

from .repository import (
    admin_overview,
    get_offering,
    get_semester,
    get_student,
    list_semesters,
    offering_roster,
    student_cgpa,
    student_progress,
    student_sgpa,
    student_upcoming_exams,
)


class ReportService:

    @staticmethod
    def _admin(user_role):
        require_role(user_role, [Roles.ADMIN])

    @staticmethod
    def overview(user_role):
        ReportService._admin(user_role)
        return admin_overview()

    @staticmethod
    def semesters(user_role):
        ReportService._admin(user_role)
        return list_semesters()

    @staticmethod
    def roster(user_role, offering_id):
        ReportService._admin(user_role)
        validate_positive_integer(offering_id, "offering_id")
        offering_id = int(offering_id)
        offering = get_offering(offering_id)
        if not offering:
            raise NotFoundError("Offering not found.")
        rows = offering_roster(offering_id)
        return {
            "offering": offering,
            "roster_count": len(rows),
            "students": rows,
        }

    @staticmethod
    def progress(user_role, student_id, semester_id):
        ReportService._admin(user_role)
        validate_positive_integer(student_id, "student_id")
        validate_required(semester_id, "semester_id")
        validate_positive_integer(semester_id, "semester_id")

        student_id = int(student_id)
        semester_id = int(semester_id)
        student = get_student(student_id)
        if not student:
            raise NotFoundError("Student not found.")
        semester = get_semester(semester_id)
        if not semester:
            raise NotFoundError("Semester not found.")

        sgpa = student_sgpa(student_id, semester_id) or {}
        cgpa = student_cgpa(student_id) or {}
        rows = student_progress(student_id, semester_id)

        return {
            "student": student,
            "semester": semester,
            "sgpa": sgpa.get("sgpa"),
            "cgpa": cgpa.get("cgpa"),
            "course_count": len(rows),
            "courses": rows,
        }

    @staticmethod
    def upcoming_exams(user_role, student_id):
        ReportService._admin(user_role)
        validate_positive_integer(student_id, "student_id")
        student_id = int(student_id)
        student = get_student(student_id)
        if not student:
            raise NotFoundError("Student not found.")
        rows = student_upcoming_exams(student_id)
        return {
            "student": student,
            "exam_count": len(rows),
            "exams": rows,
        }
