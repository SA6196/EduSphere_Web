"""EduSphere LMS - Attendance API Views."""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from accounts.permissions import IsStudent, IsInstructor, IsAdmin
from .services import AttendanceService


class SessionListView(APIView):
    permission_classes = [IsStudent | IsInstructor | IsAdmin]

    def get(self, request, offering_id):
        result = AttendanceService.list_sessions(
            request.user.role,
            offering_id,
        )
        return Response({"success": True, "data": result})


class SessionCreateView(APIView):
    permission_classes = [IsInstructor | IsAdmin]

    def post(self, request):
        result = AttendanceService.create_session(
            user_id=request.user.user_id,
            instructor_id=request.user.instructor_id,
            user_role=request.user.role,
            offering_id=request.data.get("offering_id"),
            session_date=request.data.get("session_date"),
            start_time=request.data.get("start_time"),
            end_time=request.data.get("end_time"),
            session_type=request.data.get("session_type", "LECTURE"),
            topic=request.data.get("topic"),
        )
        return Response(
            {"success": True, "data": result},
            status=status.HTTP_201_CREATED,
        )


class RecordAttendanceView(APIView):
    permission_classes = [IsInstructor | IsAdmin]

    def post(self, request):
        result = AttendanceService.record(
            user_id=request.user.user_id,
            instructor_id=request.user.instructor_id,
            user_role=request.user.role,
            session_id=request.data.get("session_id"),
            student_id=request.data.get("student_id"),
            attendance_status=request.data.get("attendance_status"),
            remarks=request.data.get("remarks"),
        )
        return Response(
            {"success": True, "data": result},
            status=status.HTTP_201_CREATED,
        )


class MyAttendanceView(APIView):
    permission_classes = [IsStudent]

    def get(self, request):
        result = AttendanceService.student_attendance(request.user.student_id)
        return Response({"success": True, "data": result})


class MyOfferingAttendanceView(APIView):
    permission_classes = [IsStudent]

    def get(self, request, offering_id):
        result = AttendanceService.student_offering_attendance(
            request.user.student_id,
            offering_id,
        )
        return Response({"success": True, "data": result})


class MySemesterAttendanceView(APIView):
    """Student-only, read-only attendance grouped by enrolled semester."""
    permission_classes = [IsStudent]

    def get(self, request):
        result = AttendanceService.student_semester_attendance(
            request.user.student_id
        )
        return Response({"success": True, "data": result})
