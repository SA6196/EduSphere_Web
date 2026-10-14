import jwt

from django.contrib.auth.hashers import check_password
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.throttling import AnonRateThrottle
from .registration import register_student, public_programs

from .repository import (
    get_user_by_username,
    get_user_by_id,
    update_last_login,
    log_activity,
)
from .serializers import LoginSerializer, RefreshSerializer
from .tokens import (
    create_access_token,
    create_refresh_token,
    decode_token,
)


def _client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _public_user(user):
    return {
        "user_id": int(user["user_id"]),
        "username": user["username"],
        "email": user["email"],
        "phone": user["phone"],
        "role": user["role"],
        "account_status": user["account_status"],
        "last_login": user["last_login"],
    }


class LoginView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = get_user_by_username(serializer.validated_data["username"])

        # Keep the same response for missing user and wrong password.
        if not user or not check_password(
            serializer.validated_data["password"],
            user["password_hash"],
        ):
            return Response(
                {"detail": "Invalid username or password."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if user["account_status"] != "ACTIVE":
            return Response(
                {"detail": "This account is not active."},
                status=status.HTTP_403_FORBIDDEN,
            )

        update_last_login(int(user["user_id"]))
        refreshed_user = get_user_by_id(int(user["user_id"]))

        try:
            log_activity(
                int(user["user_id"]),
                "LOGIN",
                "User authenticated through Django API.",
                _client_ip(request),
            )
        except Exception:
            # Login should not fail only because non-critical activity logging
            # could not be written.
            pass

        return Response({
            "access": create_access_token(refreshed_user),
            "refresh": create_refresh_token(refreshed_user),
            "user": _public_user(refreshed_user),
        })


class RefreshView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = RefreshSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            payload = decode_token(
                serializer.validated_data["refresh"],
                "refresh",
            )
            user = get_user_by_id(int(payload["sub"]))
        except (jwt.InvalidTokenError, KeyError, ValueError):
            return Response(
                {"detail": "Invalid or expired refresh token."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not user or user["account_status"] != "ACTIVE":
            return Response(
                {"detail": "User account is not active."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        return Response({
            "access": create_access_token(user),
        })


class MeView(APIView):
    def get(self, request):
        user = get_user_by_id(request.user.user_id)
        return Response(_public_user(user))


class SignupThrottle(AnonRateThrottle):
    rate = '5/hour'


class PublicProgramListView(APIView):
    authentication_classes = []
    permission_classes = []
    def get(self, request):
        return Response({'success':True,'data':public_programs()})


class StudentSignupView(APIView):
    authentication_classes = []
    permission_classes = []
    throttle_classes = [SignupThrottle]
    def post(self, request):
        result=register_student(request.data)
        return Response({'success':True,'data':result},status=status.HTTP_202_ACCEPTED)
