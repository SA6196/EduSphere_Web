"""
EduSphere LMS

Assignment API Views

Commit 6
"""


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status


from accounts.permissions import (
    IsStudent,
    IsInstructor,
    IsInstructorOrAdmin,
)


from .services import AssignmentService



class AssignmentCreateView(APIView):

    permission_classes = [
        IsInstructor
    ]


    def post(
        self,
        request
    ):

        result = AssignmentService.create_assignment(

            user_id=request.user.user_id,

            instructor_id=request.user.instructor_id,

            user_role=request.user.role,

            component_id=request.data.get(
                "component_id"
            ),

            title=request.data.get(
                "assignment_title"
            ),

            description=request.data.get(
                "assignment_description"
            ),

            due_date=request.data.get(
                "due_date"
            ),

            allow_resubmission=request.data.get(
                "allow_resubmission",
                "N"
            ),
        )


        return Response(
            result,
            status=status.HTTP_201_CREATED
        )



class AssignmentListView(APIView):

    permission_classes = [
        IsStudent |
        IsInstructor |
        IsInstructorOrAdmin
    ]


    def get(
        self,
        request
    ):

        component_id = request.query_params.get(
            "component_id"
        )


        result = AssignmentService.list_assignments(
            component_id
        )


        return Response(
            result
        )



class AssignmentSubmissionView(APIView):

    permission_classes = [
        IsStudent
    ]


    def post(
        self,
        request,
        assignment_id
    ):

        result = AssignmentService.submit_assignment(

            user_id=request.user.user_id,

            student_id=request.user.student_id,

            user_role=request.user.role,

            assignment_id=assignment_id,

            file_url=request.data.get(
                "file_url"
            ),

        )


        return Response(
            result,
            status=status.HTTP_201_CREATED
        )



class StudentSubmissionListView(APIView):

    permission_classes = [
        IsStudent
    ]


    def get(
        self,
        request,
        assignment_id
    ):

        result = AssignmentService.student_submissions(

            assignment_id,

            request.user.student_id

        )


        return Response(
            result
        )

class InstructorSubmissionListView(APIView):

    permission_classes = [
        IsInstructor
    ]

    def get(
        self,
        request,
        assignment_id
    ):

        result = AssignmentService.instructor_submissions(
            assignment_id
        )

        return Response(
            result
        )