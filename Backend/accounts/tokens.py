from datetime import datetime, timedelta, timezone

import jwt
from django.conf import settings


def _now():
    return datetime.now(timezone.utc)


def create_access_token(user):
    now = _now()
    payload = {
        "sub": str(int(user["user_id"])),
        "username": user["username"],
        "role": user["role"],
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.JWT_ACCESS_MINUTES),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def create_refresh_token(user):
    now = _now()
    payload = {
        "sub": str(int(user["user_id"])),
        "type": "refresh",
        "iat": now,
        "exp": now + timedelta(days=settings.JWT_REFRESH_DAYS),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def decode_token(token: str, expected_type: str):
    payload = jwt.decode(
        token,
        settings.JWT_SECRET,
        algorithms=["HS256"],
    )
    if payload.get("type") != expected_type:
        raise jwt.InvalidTokenError("Incorrect token type.")
    return payload
