from django.conf import settings


def object_name(name: str) -> str:
    """
    Return a schema-qualified Oracle object name.

    Object names are constants from backend source code, never user input.
    """
    if not name.replace("_", "").isalnum():
        raise ValueError("Invalid Oracle object name.")
    return f"{settings.ORACLE_SCHEMA}.{name.upper()}"
