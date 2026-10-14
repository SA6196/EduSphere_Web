"""EduSphere LMS - GPA verification service layer."""

from collections import defaultdict

from accounts.authorization import require_role
from core.constants import Roles
from core.exceptions import NotFoundError, ValidationError
from core.validators import validate_positive_integer

from .repository import (
    get_cgpa,
    get_semester,
    get_sgpa,
    get_sgpa_for_published_semesters,
    get_student,
    published_grade_rows,
)


class GPAService:

    @staticmethod
    def _number(value):
        if value is None:
            return None
        return float(value)

    @staticmethod
    def _manual_gpa(rows):
        if not rows:
            return None, 0.0, 0.0

        total_credits = sum(float(row["credits"]) for row in rows)
        total_points = sum(float(row["weighted_points"]) for row in rows)

        if total_credits == 0:
            return None, total_credits, total_points

        return round(total_points / total_credits, 2), total_credits, total_points

    @staticmethod
    def _verification(db_value, manual_value):
        db_value = GPAService._number(db_value)
        if db_value is None and manual_value is None:
            return "NO_PUBLISHED_GRADES"
        if db_value is None or manual_value is None:
            return "MISMATCH"
        return "MATCH" if abs(db_value - manual_value) <= 0.01 else "MISMATCH"

    @staticmethod
    def _validate_student(student_id):
        validate_positive_integer(student_id, "student_id")
        student = get_student(int(student_id))
        if not student:
            raise NotFoundError("Student not found.")
        return student

    @staticmethod
    def summary(student_id):
        student = GPAService._validate_student(student_id)
        student_id = int(student_id)

        rows = published_grade_rows(student_id)
        db_cgpa_row = get_cgpa(student_id) or {}
        db_cgpa = GPAService._number(db_cgpa_row.get("cgpa"))
        manual_cgpa, total_credits, total_points = GPAService._manual_gpa(rows)

        grouped = defaultdict(list)
        semester_meta = {}
        for row in rows:
            sid = int(row["semester_id"])
            grouped[sid].append(row)
            semester_meta[sid] = {
                "semester_id": sid,
                "semester_name": row["semester_name"],
                "academic_year": row["academic_year"],
            }

        db_sgpa_rows = get_sgpa_for_published_semesters(student_id)
        db_sgpa_by_semester = {
            int(row["semester_id"]): GPAService._number(row.get("sgpa"))
            for row in db_sgpa_rows
        }

        semesters = []
        for semester_id in sorted(grouped):
            semester_rows = grouped[semester_id]
            db_sgpa = db_sgpa_by_semester.get(semester_id)
            manual_sgpa, credits, points = GPAService._manual_gpa(semester_rows)
            semesters.append(
                {
                    **semester_meta[semester_id],
                    "sgpa": db_sgpa,
                    "verified_sgpa": manual_sgpa,
                    "verification": GPAService._verification(db_sgpa, manual_sgpa),
                    "graded_course_count": len(semester_rows),
                    "graded_credits": credits,
                    "weighted_grade_points": round(points, 2),
                }
            )

        return {
            "student": student,
            "cgpa": db_cgpa,
            "verified_cgpa": manual_cgpa,
            "cgpa_verification": GPAService._verification(db_cgpa, manual_cgpa),
            "published_course_count": len(rows),
            "total_graded_credits": total_credits,
            "total_weighted_grade_points": round(total_points, 2),
            "semesters": semesters,
        }

    @staticmethod
    def semester(student_id, semester_id):
        student = GPAService._validate_student(student_id)
        validate_positive_integer(semester_id, "semester_id")
        semester_id = int(semester_id)

        semester = get_semester(semester_id)
        if not semester:
            raise NotFoundError("Semester not found.")

        rows = published_grade_rows(int(student_id), semester_id)
        db_sgpa_row = get_sgpa(int(student_id), semester_id) or {}
        db_sgpa = GPAService._number(db_sgpa_row.get("sgpa"))
        manual_sgpa, credits, points = GPAService._manual_gpa(rows)

        return {
            "student": student,
            "semester": semester,
            "sgpa": db_sgpa,
            "gpa": db_sgpa,
            "verified_sgpa": manual_sgpa,
            "verification": GPAService._verification(db_sgpa, manual_sgpa),
            "graded_course_count": len(rows),
            "graded_credits": credits,
            "weighted_grade_points": round(points, 2),
            "courses": rows,
        }

    @staticmethod
    def my_summary(user_role, student_id):
        require_role(user_role, [Roles.STUDENT])
        if not student_id:
            raise NotFoundError("Student profile not found.")
        return GPAService.summary(int(student_id))

    @staticmethod
    def my_semester(user_role, student_id, semester_id):
        require_role(user_role, [Roles.STUDENT])
        if not student_id:
            raise NotFoundError("Student profile not found.")
        return GPAService.semester(int(student_id), semester_id)

    @staticmethod
    def admin_summary(user_role, student_id):
        require_role(user_role, [Roles.ADMIN])
        return GPAService.summary(student_id)

    @staticmethod
    def admin_semester(user_role, student_id, semester_id):
        require_role(user_role, [Roles.ADMIN])
        return GPAService.semester(student_id, semester_id)
