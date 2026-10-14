"""
EduSphere LMS

Announcement API Views
"""

from rest_framework.views import APIView

from accounts.authentication import LMSJWTAuthentication
from accounts.permissions import IsAdmin, IsInstructor, IsStudent
from core.responses import success_response

from .services import AnnouncementService


class AnnouncementCreateView(APIView):
    authentication_classes = [LMSJWTAuthentication]
    permission_classes = [IsInstructor | IsAdmin]

    def post(self, request):
        user = request.user

        result = AnnouncementService.create(
            user_id=user.user_id,
            instructor_id=user.instructor_id,
            user_role=user.role,
            offering_id=request.data.get("offering_id"),
            title=request.data.get("announcement_title"),
            message=request.data.get("announcement_message"),
            priority=request.data.get("announcement_priority"),
        )

        return success_response(
            data=result
        )


class AnnouncementListView(APIView):
    authentication_classes = [LMSJWTAuthentication]
    permission_classes = [
        IsStudent | IsInstructor | IsAdmin
    ]

    def get(self, request):
        user = request.user

        result = AnnouncementService.list_for_offering(
            user_role=user.role,
            student_id=user.student_id,
            instructor_id=user.instructor_id,
            offering_id=request.GET.get("offering_id"),
        )

        return success_response(
            data=result
        )


class AnnouncementDetailView(APIView):
    authentication_classes = [LMSJWTAuthentication]
    permission_classes = [
        IsStudent | IsInstructor | IsAdmin
    ]

    def get(
        self,
        request,
        announcement_id,
    ):
        user = request.user

        result = AnnouncementService.detail(
            user_role=user.role,
            student_id=user.student_id,
            instructor_id=user.instructor_id,
            announcement_id=announcement_id,
        )

        return success_response(
            data=result
        )
