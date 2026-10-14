"""
EduSphere LMS

Course Material Service Layer

Commit 7

Handles:
- Material creation
- Material listing
"""

from accounts.authorization import (
    require_role,
)

from core.constants import (
    Roles,
    ActivityTypes,
)

from core.validators import (
    validate_required,
    validate_positive_integer,
)

from core.exceptions import (
    ValidationError,
    PermissionDeniedError,
    NotFoundError,
)

from core.audit import log_activity


from .repository import (
    create_material,
    get_materials,
    get_material,
)


from academics.repository import (
    get_offering,
)

from assignments.repository import (
    instructor_owns_offering,
)

class MaterialService:


    @staticmethod
    def create_material(
        user_id,
        instructor_id,
        user_role,
        offering_id,
        title,
        material_type,
        material_url,
    ):


        # -------------------------
        # Validation
        # -------------------------

        validate_required(
            offering_id,
            "offering_id"
        )

        validate_positive_integer(
            offering_id,
            "offering_id"
        )


        validate_required(
            title,
            "material_title"
        )


        validate_required(
            material_type,
            "material_type"
        )


        # -------------------------
        # Authorization
        # -------------------------

        require_role(
            user_role,
            [
                Roles.INSTRUCTOR
            ]
        )


        # -------------------------
        # Offering Verification
        # -------------------------

        offering = get_offering(
            offering_id
        )


        if not offering:

            raise NotFoundError(
                "Offering not found."
            )


        # -------------------------
        # Instructor Ownership
        # -------------------------

        if not instructor_owns_offering(
            instructor_id,
            offering_id,
        ):

            raise PermissionDeniedError(
                "Instructor does not own this offering."
            )


        # -------------------------
        # Create Material
        # -------------------------

        create_material(
            offering_id,
            user_id,
            title,
            material_type,
            material_url,
        )


        # -------------------------
        # Audit
        # -------------------------

        log_activity(
            user_id=user_id,

            activity_type=(
                ActivityTypes.MATERIAL_CREATED
            ),

            activity_description=(
                f"Material created: {title}"
            ),
        )


        return {
            "message":
                "Material created successfully"
        }



    @staticmethod
    def list_materials(
        offering_id,
    ):


        validate_positive_integer(
            offering_id,
            "offering_id"
        )


        return get_materials(
            offering_id
        )



    @staticmethod
    def get_material(
        material_id,
    ):


        validate_positive_integer(
            material_id,
            "material_id"
        )


        material = get_material(
            material_id
        )


        if not material:

            raise NotFoundError(
                "Material not found."
            )


        return material