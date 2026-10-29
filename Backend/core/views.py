from django.conf import settings
from rest_framework.response import Response
from rest_framework.views import APIView
from edusphere.version import (
    APP_NAME,
    VERSION,
    COMMIT,
    DATABASE_SCHEMA,
)
from database.connection import oracle_connection


EXPECTED_TABLES = {
    "LMS_USER", "STUDENT", "INSTRUCTOR", "ADMIN",
    "DEPARTMENT", "PROGRAM", "SEMESTER", "COURSE",
    "COURSE_OFFERING", "OFFERING_INSTRUCTOR", "ENROLLMENT",
    "COURSE_MATERIAL", "ANNOUNCEMENT", "CLASS_SESSION",
    "ATTENDANCE", "GRADING_SCHEME", "ASSESSMENT_COMPONENT",
    "ASSIGNMENT", "ASSIGNMENT_SUBMISSION", "QUESTION",
    "QUESTION_OPTION", "QUIZ", "QUIZ_QUESTION", "QUIZ_ATTEMPT",
    "QUIZ_RESPONSE", "QUIZ_RESPONSE_OPTION", "EXAM",
    "STUDENT_MARK", "GRADE_SCALE", "COURSE_GRADE", "ACTIVITY_LOG",
    "QUESTION_KEYWORD", "QUESTION_NUMERIC_RULE", "QUIZ_GRADING",
    "QUIZ_QUESTION_GRADE", "QUIZ_RESPONSE_MATCH", "QUIZ_RESPONSE_ORDER",
}


class HealthView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        return Response({
            "status": "ok",
            "service": "edusphere-django-backend",
            "version": VERSION,
            "commit": COMMIT,
        })


class DatabaseHealthView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        owner = settings.ORACLE_SCHEMA

        with oracle_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT 1 FROM DUAL")
            ping = cursor.fetchone()[0]

            placeholders = ",".join("?" for _ in EXPECTED_TABLES)
            sql = f"""
                SELECT TABLE_NAME
                FROM ALL_TABLES
                WHERE OWNER = ?
                  AND TABLE_NAME IN ({placeholders})
            """
            params = [owner, *sorted(EXPECTED_TABLES)]
            cursor.execute(sql, params)
            visible = {row[0] for row in cursor.fetchall()}

        missing = sorted(EXPECTED_TABLES - visible)

        return Response({
            "status": "ok" if ping == 1 and not missing else "degraded",
            "oracle_connected": ping == 1,
            "schema": owner,
            "expected_tables": len(EXPECTED_TABLES),
            "visible_tables": len(visible),
            "missing_tables": missing,
        })
class VersionView(APIView):

    authentication_classes = []
    permission_classes = []

    def get(self, request):

        return Response(
            {
                "application": APP_NAME,
                "version": VERSION,
                "commit": COMMIT,
                "database_schema": DATABASE_SCHEMA,
            }
        )