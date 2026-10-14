"""
EduSphere LMS

Validation Utilities

Commit 5.6
"""

from core.exceptions import ValidationError



def validate_required(
    value,
    field_name
):

    if value is None or value == "":
        raise ValidationError(
            f"{field_name} is required."
        )

    return True



def validate_positive_integer(
    value,
    field_name
):

    try:
        value = int(value)

    except (TypeError, ValueError):

        raise ValidationError(
            f"{field_name} must be an integer."
        )


    if value <= 0:

        raise ValidationError(
            f"{field_name} must be positive."
        )


    return True



def validate_role(
    role,
    allowed_roles
):

    if role not in allowed_roles:

        raise ValidationError(
            "Invalid role."
        )

    return True