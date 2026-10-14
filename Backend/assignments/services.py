"""
EduSphere LMS

Assignment Service Layer

Commit 6

Handles:
- Assignment creation
- Assignment submission
"""

from datetime import datetime


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
    get_component,
    create_assignment,
    get_assignments,
    get_assignment,
    get_latest_submission_version,
    create_submission,
    get_student_submissions,
    instructor_owns_offering,
    assignment_exists_for_component,
    get_assignment_submissions,
)



class AssignmentService:


    @staticmethod
    def create_assignment(
        user_id,
        instructor_id,
        user_role,
        component_id,
        title,
        description,
        due_date,
        allow_resubmission,
    ):


        # -------------------------
        # Validation
        # -------------------------

        validate_required(
            component_id,
            "component_id"
        )


        validate_positive_integer(
            component_id,
            "component_id"
        )


        validate_required(
            title,
            "assignment_title"
        )


        validate_required(
            due_date,
            "due_date"
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
        # Component Verification
        # -------------------------

        component = get_component(
            component_id
        )


        if not component:

            raise NotFoundError(
                "Assessment component not found."
            )


        if component["component_type"] != "ASSIGNMENT":

            raise ValidationError(
                "Component type must be ASSIGNMENT."
            )


        # -------------------------
        # Instructor Ownership
        # -------------------------

        offering_id = component[
            "offering_id"
        ]


        if not instructor_owns_offering(
            instructor_id,
            offering_id,
        ):

            raise PermissionDeniedError(
                "Instructor does not own this offering."
            )


        # -------------------------
        # Duplicate Assignment Check
        # -------------------------

        if assignment_exists_for_component(
            component_id
        ):

            raise ValidationError(
                "Assignment already exists for this component."
            )


        # -------------------------
        # Convert Due Date
        # -------------------------

        try:

            due_date = datetime.fromisoformat(
                due_date
            )

        except Exception:

            raise ValidationError(
                "Invalid due_date format. Use YYYY-MM-DDTHH:MM:SS."
            )


        # -------------------------
        # Create Assignment
        # -------------------------

        create_assignment(
            component_id,
            title,
            description,
            due_date,
            allow_resubmission,
        )


        # -------------------------
        # Audit
        # -------------------------

        log_activity(
            user_id=user_id,

            activity_type=(
                ActivityTypes.ASSIGNMENT_CREATED
            ),

            activity_description=(
                f"Assignment created: {title}"
            ),
        )


        return {
            "message":
                "Assignment created successfully"
        }



    @staticmethod
    def list_assignments(
        component_id,
    ):


        validate_positive_integer(
            component_id,
            "component_id"
        )


        return get_assignments(
            component_id
        )



    @staticmethod
    def submit_assignment(
        user_id,
        student_id,
        user_role,
        assignment_id,
        file_url,
    ):


        # -------------------------
        # Validation
        # -------------------------

        validate_required(
            assignment_id,
            "assignment_id"
        )


        validate_positive_integer(
            assignment_id,
            "assignment_id"
        )


        validate_required(
            file_url,
            "file_url"
        )


        # -------------------------
        # Authorization
        # -------------------------

        require_role(
            user_role,
            [
                Roles.STUDENT
            ]
        )


        assignment = get_assignment(
            assignment_id
        )


        if not assignment:

            raise NotFoundError(
                "Assignment not found."
            )


        # -------------------------
        # Submission Version
        # -------------------------

        previous_version = (
            get_latest_submission_version(
                assignment_id,
                student_id,
            )
        )


        if (
            previous_version > 0
            and
            assignment[
                "allow_resubmission"
            ] == "N"
        ):

            raise PermissionDeniedError(
                "Resubmission is not allowed."
            )


        version = previous_version + 1


        create_submission(
            assignment_id,
            student_id,
            file_url,
            version,
        )


        # -------------------------
        # Audit
        # -------------------------

        log_activity(
            user_id=user_id,

            activity_type=(
                ActivityTypes.ASSIGNMENT_SUBMITTED
            ),

            activity_description=(
                f"Assignment {assignment_id} "
                f"submitted version {version}"
            ),
        )


        return {
            "message":
                "Assignment submitted successfully",

            "submission_version":
                version,
        }



    @staticmethod
    def student_submissions(
        assignment_id,
        student_id,
    ):

        return get_student_submissions(
            assignment_id,
            student_id,
        )
    @staticmethod
    def instructor_submissions(
        assignment_id,
    ):

        return get_assignment_submissions(
            assignment_id,
        )