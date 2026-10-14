import jwt

from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed

from .principal import LMSPrincipal
from .repository import (
    get_user_by_id,
    get_student_id_by_user_id,
    get_instructor_id_by_user_id,
)
from .tokens import decode_token


class LMSJWTAuthentication(BaseAuthentication):
    keyword = b"Bearer"

    def authenticate_header(self, request):
        # Makes DRF return 401 (with WWW-Authenticate) rather than 403
        # when credentials are missing/invalid on an authenticated endpoint.
        return "Bearer"

    def authenticate(self, request):
        header = get_authorization_header(request).split()

        if not header:
            return None

        if len(header) != 2 or header[0].lower() != self.keyword.lower():
            raise AuthenticationFailed("Use Authorization: Bearer <token>.")

        try:
            token = header[1].decode("utf-8")
            payload = decode_token(token, "access")
            user = get_user_by_id(int(payload["sub"]))
        except (jwt.InvalidTokenError, KeyError, ValueError):
            raise AuthenticationFailed("Invalid or expired access token.")
        except Exception:
            raise AuthenticationFailed("Unable to validate the access token.")

        if not user:
            raise AuthenticationFailed("User no longer exists.")

        if user["account_status"] != "ACTIVE":
            raise AuthenticationFailed("This account is not active.")

        user_id = int(user["user_id"])
        student_id = None
        instructor_id = None

        if user["role"] == "STUDENT":
            student_id = get_student_id_by_user_id(user_id)
        elif user["role"] == "INSTRUCTOR":
            instructor_id = get_instructor_id_by_user_id(user_id)

        principal = LMSPrincipal(
            user_id=user_id,
            username=user["username"],
            email=user["email"],
            role=user["role"],
            account_status=user["account_status"],
            student_id=student_id,
            instructor_id=instructor_id,
        )

        return principal, payload
