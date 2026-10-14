"""EduSphere LMS - Admin Report API Views."""

from rest_framework.views import APIView

from accounts.authentication import LMSJWTAuthentication
from accounts.permissions import IsAdmin
from core.responses import success_response

from .services import ReportService


class AdminOverviewReportView(APIView):
    authentication_classes = [LMSJWTAuthentication]
    permission_classes = [IsAdmin]

    def get(self, request):
        return success_response(
            data=ReportService.overview(request.user.role)
        )


class SemesterListReportView(APIView):
    authentication_classes = [LMSJWTAuthentication]
    permission_classes = [IsAdmin]

    def get(self, request):
        return success_response(
            data=ReportService.semesters(request.user.role)
        )


class OfferingRosterReportView(APIView):
    authentication_classes = [LMSJWTAuthentication]
    permission_classes = [IsAdmin]

    def get(self, request, offering_id):
        return success_response(
            data=ReportService.roster(
                request.user.role,
                offering_id,
            )
        )


class StudentProgressReportView(APIView):
    authentication_classes = [LMSJWTAuthentication]
    permission_classes = [IsAdmin]

    def get(self, request, student_id):
        return success_response(
            data=ReportService.progress(
                request.user.role,
                student_id,
                request.GET.get("semester_id"),
            )
        )


class StudentUpcomingExamsReportView(APIView):
    authentication_classes = [LMSJWTAuthentication]
    permission_classes = [IsAdmin]

    def get(self, request, student_id):
        return success_response(
            data=ReportService.upcoming_exams(
                request.user.role,
                student_id,
            )
        )
