"""
EduSphere LMS

Base Service Utilities

Commit 5.7
"""


from core.validators import (
    validate_required,
)


class BaseService:


    @staticmethod
    def require_id(
        value,
        field_name
    ):

        validate_required(
            value,
            field_name
        )


    @staticmethod
    def normalize_id(value):

        return int(value)