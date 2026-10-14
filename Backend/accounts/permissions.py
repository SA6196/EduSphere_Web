from rest_framework.permissions import BasePermission


class HasRole(BasePermission):
    allowed_roles = set()

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        return bool(
            user
            and getattr(user, "is_authenticated", False)
            and getattr(user, "role", None) in self.allowed_roles
        )


class IsStudent(HasRole):
    allowed_roles = {"STUDENT"}


class IsInstructor(HasRole):
    allowed_roles = {"INSTRUCTOR"}


class IsAdmin(HasRole):
    allowed_roles = {"ADMIN"}


class IsInstructorOrAdmin(HasRole):
    allowed_roles = {"INSTRUCTOR", "ADMIN"}
