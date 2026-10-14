from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdmin, IsInstructor

from .services import AdminGradingService, AdminIdentityService, AdminOfferingService


class AdminDirectoryView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        return Response({"success": True, "data": AdminIdentityService.directory(request.user.role)})


class AdminStudentAccountsView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        return Response({"success": True, "data": AdminIdentityService.directory(request.user.role)["students"]})

    def post(self, request):
        result = AdminIdentityService.create_student(request.user.user_id, request.user.role, request.data)
        return Response({"success": True, "data": result}, status=status.HTTP_201_CREATED)


class AdminInstructorAccountsView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        return Response({"success": True, "data": AdminIdentityService.directory(request.user.role)["instructors"]})

    def post(self, request):
        result = AdminIdentityService.create_instructor(request.user.user_id, request.user.role, request.data)
        return Response({"success": True, "data": result}, status=status.HTTP_201_CREATED)


class AdminOfferingCreateView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request):
        result = AdminOfferingService.create(request.user.user_id, request.user.role, request.data)
        return Response({"success": True, "data": result}, status=status.HTTP_201_CREATED)


class AdminOfferingInstructorView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request, offering_id):
        result = AdminOfferingService.instructors(request.user.role, offering_id)
        return Response({"success": True, "data": result})

    def put(self, request, offering_id):
        result = AdminOfferingService.replace_instructors(
            request.user.user_id,
            request.user.role,
            offering_id,
            request.data.get("instructor_ids"),
        )
        return Response({"success": True, "data": result})


class AdminGradingSchemeView(APIView):
    permission_classes = [IsAdmin | IsInstructor]

    def get(self, request, offering_id):
        result = AdminGradingService.get(request.user.role, offering_id, request.user.instructor_id)
        return Response({"success": True, "data": result})

    def put(self, request, offering_id):
        result = AdminGradingService.save(
            request.user.user_id,
            request.user.role,
            offering_id,
            request.data,
            request.user.instructor_id,
        )
        return Response({"success": True, "data": result})
