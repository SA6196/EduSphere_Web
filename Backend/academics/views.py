from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.responses import paginated_response
from accounts.permissions import IsStudent, IsInstructor, IsAdmin

from .repository import (
    student_dashboard,
    instructor_offerings,
    admin_summary,
    list_courses,
    list_offerings,
    get_offering,
    my_enrollments,
    student_marks,
    student_semester_markbook,
)
from .services import EnrollmentService, GradeService, OfferingService


class StudentDashboardView(APIView):
    permission_classes = [IsStudent]

    def get(self, request):
        data = student_dashboard(request.user.user_id)
        if not data:
            return Response(
                {"detail": "Student profile not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(data)


class InstructorOfferingsView(APIView):
    permission_classes = [IsInstructor]

    def get(self, request):
        data = instructor_offerings(request.user.user_id)
        if not data:
            return Response(
                {"detail": "Instructor profile not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(data)


class AdminSummaryView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        return Response(admin_summary())


class CourseListView(APIView):
    permission_classes = [IsStudent | IsInstructor | IsAdmin]

    def get(self, request):
        return paginated_response(
            list_courses(),
            request.query_params.get("page", 1),
            request.query_params.get("page_size", 10),
        )


class OfferingListView(APIView):
    permission_classes = [IsStudent | IsInstructor | IsAdmin]

    def get(self, request):
        return paginated_response(
            list_offerings(),
            request.query_params.get("page", 1),
            request.query_params.get("page_size", 10),
        )


class OfferingDetailView(APIView):
    permission_classes = [IsStudent | IsInstructor | IsAdmin]

    def get(self, request, offering_id):
        data = get_offering(offering_id)
        if not data:
            return Response(
                {"detail": "Offering not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(data)


class OfferingGradingView(APIView):
    permission_classes = [IsStudent | IsInstructor | IsAdmin]

    def get(self, request, offering_id):
        result = OfferingService.grading(
            user_role=request.user.role,
            student_id=request.user.student_id,
            instructor_id=request.user.instructor_id,
            offering_id=offering_id,
        )
        return Response({"success": True, "data": result})


class InstructorOfferingRosterView(APIView):
    permission_classes = [IsInstructor | IsAdmin]

    def get(self, request, offering_id):
        result = OfferingService.instructor_roster(
            user_role=request.user.role,
            instructor_id=request.user.instructor_id,
            offering_id=offering_id,
        )
        return Response({"success": True, "data": result})


class EnrollmentCreateView(APIView):
    permission_classes = [IsStudent]

    def post(self, request):
        result = EnrollmentService.enroll_student(
            request.user.user_id,
            request.user.student_id,
            request.data.get("offering_id"),
            request.user.role,
        )
        return Response(result, status=status.HTTP_201_CREATED)


class MyEnrollmentView(APIView):
    permission_classes = [IsStudent]

    def get(self, request):
        return Response(my_enrollments(request.user.student_id))


class RecordMarkView(APIView):
    permission_classes = [IsInstructor | IsAdmin]

    def post(self, request):
        result = GradeService.record_mark(
            user_id=request.user.user_id,
            user_role=request.user.role,
            instructor_id=request.user.instructor_id,
            component_id=request.data.get("component_id"),
            enrollment_id=request.data.get("enrollment_id"),
            marks_obtained=request.data.get("marks_obtained"),
            graded_submission_id=request.data.get("graded_submission_id"),
        )
        return Response({"success": True, "data": result})


class PublishGradeView(APIView):
    permission_classes = [IsInstructor | IsAdmin]

    def post(self, request):
        result = GradeService.publish_grade(
            user_id=request.user.user_id,
            user_role=request.user.role,
            instructor_id=request.user.instructor_id,
            enrollment_id=request.data.get("enrollment_id"),
        )
        return Response({"success": True, "data": result})


class StudentMarksView(APIView):
    permission_classes = [IsStudent]

    def get(self, request):
        return Response(
            {
                "success": True,
                "data": student_marks(request.user.student_id),
            }
        )


class StudentSemesterMarkbookView(APIView):
    permission_classes = [IsStudent]

    def get(self, request):
        return Response({
            "success": True,
            "data": student_semester_markbook(request.user.student_id),
        })
