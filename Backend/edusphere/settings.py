import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-only-change-me")
DEBUG = os.getenv("DEBUG", "True").lower() == "true"

ALLOWED_HOSTS = [
    x.strip()
    for x in os.getenv("ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")
    if x.strip()
]

INSTALLED_APPS = [
    "corsheaders",
    "rest_framework",
    "core",
    "accounts",
    "academics",
    "assignments",
    "attendance",
    "quiz",
    "materials",
    "announcements",
    "exams",
    "gpa",
    "reports",
    "administration",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "edusphere.urls"

TEMPLATES = []

WSGI_APPLICATION = "edusphere.wsgi.application"
ASGI_APPLICATION = "edusphere.asgi.application"

# EduSphere application data is accessed through Oracle ODBC/pyodbc.
# Django's ORM is deliberately not allowed to create or migrate the
# already-certified 31-table Oracle schema.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.dummy",
    }
}

LANGUAGE_CODE = "en-us"

# The Oracle schema uses TIMESTAMP without time zone and the project
# operates in India. Keep application-local timestamps consistent.
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = False

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CORS_ALLOWED_ORIGINS = [
    x.strip()
    for x in os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:5173"
    ).split(",")
    if x.strip()
]

REST_FRAMEWORK = {

    "DEFAULT_AUTHENTICATION_CLASSES": [
        "accounts.authentication.LMSJWTAuthentication",
    ],

    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],

    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],

    "UNAUTHENTICATED_USER": None,

    "EXCEPTION_HANDLER":
        "core.exception_handler.edusphere_exception_handler",
}

ORACLE_SCHEMA = os.getenv("ORACLE_SCHEMA", "EDUSPHERE_OWNER").upper().strip()
if not ORACLE_SCHEMA.replace("_", "").isalnum():
    raise RuntimeError("ORACLE_SCHEMA must contain only letters, digits and underscores.")

JWT_SECRET = os.getenv("JWT_SECRET", SECRET_KEY)
JWT_ACCESS_MINUTES = int(os.getenv("JWT_ACCESS_MINUTES", "30"))
JWT_REFRESH_DAYS = int(os.getenv("JWT_REFRESH_DAYS", "7"))
# ---------------------------------------
# Commit 3.5
# Application Logging Configuration
# ---------------------------------------

LOGGING = {

    "version": 1,

    "disable_existing_loggers": False,


    "handlers": {

        "console": {
            "class": "logging.StreamHandler",
        },

    },


    "root": {

        "handlers": [
            "console"
        ],

        "level": "INFO",

    },

}
