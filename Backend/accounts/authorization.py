from core.exceptions import PermissionDeniedError


def require_role(user_role, allowed_roles):
    """
    Validate role permission.
    """

    if user_role not in allowed_roles:
        raise PermissionDeniedError(
            "You do not have permission to perform this action."
        )

    return True

def require_instructor_ownership(
    instructor_id,
    resource_instructor_id,
):
    """
    Ensure instructor can modify only their own resources.
    """

    if instructor_id != resource_instructor_id:
        raise PermissionDeniedError(
            "Instructor does not own this resource."
        )

    return True