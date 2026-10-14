"""
EduSphere LMS

Course Material Views

Commit 7
"""

from rest_framework.views import APIView
from rest_framework import status

from accounts.permissions import (
    IsStudent,
    IsInstructor,
    IsAdmin,
)

from core.responses import success_response

from .services import (
    MaterialService,
)


class MaterialCreateView(APIView):

    def post(self, request):

        user = request.user

        result = MaterialService.create_material(
            user_id=user.user_id,
            instructor_id=user.instructor_id,
            user_role=user.role,

            offering_id=request.data.get(
                "offering_id"
            ),

            title=request.data.get(
                "material_title"
            ),

            material_type=request.data.get(
                "material_type"
            ),

            material_url=request.data.get(
                "material_url"
            ),
        )

        return success_response(
            data=result
        )


class MaterialListView(APIView):

    permission_classes = [
        IsStudent |
        IsInstructor |
        IsAdmin
    ]

    def get(self, request):

        materials = MaterialService.list_materials(
            request.GET.get(
                "offering_id"
            )
        )

        return success_response(
            data=materials
        )


class MaterialDetailView(APIView):

    permission_classes = [
        IsStudent |
        IsInstructor |
        IsAdmin
    ]

    def get(
        self,
        request,
        material_id
    ):

        material = MaterialService.get_material(
            material_id
        )

        return success_response(
            data=material
        )