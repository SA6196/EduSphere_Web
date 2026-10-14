"""EduSphere LMS - GPA / SGPA / CGPA API Views."""

from rest_framework.views import APIView

from accounts.authentication import LMSJWTAuthentication
from accounts.permissions import IsAdmin, IsStudent
from core.responses import success_response

from .services import GPAService


class MyGPASummaryView(APIView):
    authentication_classes = [LMSJWTAuthentication]
    permission_classes = [IsStudent]

    def get(self, request):
        return success_response(
            data=GPAService.my_summary(
                request.user.role,
                request.user.student_id,
            )
        )


class MySemesterGPAView(APIView):
    authentication_classes = [LMSJWTAuthentication]
    permission_classes = [IsStudent]

    def get(self, request, semester_id):
        return success_response(
            data=GPAService.my_semester(
                request.user.role,
                request.user.student_id,
                semester_id,
            )
        )


class AdminStudentGPASummaryView(APIView):
    authentication_classes = [LMSJWTAuthentication]
    permission_classes = [IsAdmin]

    def get(self, request, student_id):
        return success_response(
            data=GPAService.admin_summary(
                request.user.role,
                student_id,
            )
        )


class AdminStudentSemesterGPAView(APIView):
    authentication_classes = [LMSJWTAuthentication]
    permission_classes = [IsAdmin]

    def get(self, request, student_id, semester_id):
        return success_response(
            data=GPAService.admin_semester(
                request.user.role,
                student_id,
                semester_id,
            )
        )
