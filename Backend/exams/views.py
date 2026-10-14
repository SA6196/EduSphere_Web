"""EduSphere LMS - Exam Schedule API Views."""

from rest_framework.views import APIView

from accounts.authentication import LMSJWTAuthentication
from accounts.permissions import IsAdmin, IsInstructor, IsStudent
from core.responses import success_response

from .services import ExamService


class ExamScheduleCreateView(APIView):
    authentication_classes = [LMSJWTAuthentication]
    permission_classes = [IsInstructor | IsAdmin]

    def post(self, request):
        user = request.user
        result = ExamService.schedule(
            user_id=user.user_id,
            user_role=user.role,
            instructor_id=user.instructor_id,
            component_id=request.data.get("component_id"),
            exam_title=request.data.get("exam_title"),
            exam_type=request.data.get("exam_type"),
            exam_date=request.data.get("exam_date"),
            start_time=request.data.get("start_time"),
            end_time=request.data.get("end_time"),
        )
        return success_response(data=result, status_code=201)


class ExamOfferingListView(APIView):
    authentication_classes = [LMSJWTAuthentication]
    permission_classes = [IsStudent | IsInstructor | IsAdmin]

    def get(self, request):
        user = request.user
        result = ExamService.list_for_offering(
            user_role=user.role,
            student_id=user.student_id,
            instructor_id=user.instructor_id,
            offering_id=request.GET.get("offering_id"),
        )
        return success_response(data=result)


class ExamDetailView(APIView):
    authentication_classes = [LMSJWTAuthentication]
    permission_classes = [IsStudent | IsInstructor | IsAdmin]

    def get(self, request, exam_id):
        user = request.user
        result = ExamService.detail(
            user_role=user.role,
            student_id=user.student_id,
            instructor_id=user.instructor_id,
            exam_id=exam_id,
        )
        return success_response(data=result)


class MyUpcomingExamsView(APIView):
    authentication_classes = [LMSJWTAuthentication]
    permission_classes = [IsStudent]

    def get(self, request):
        result = ExamService.my_upcoming(
            user_role=request.user.role,
            student_id=request.user.student_id,
        )
        return success_response(data=result)
