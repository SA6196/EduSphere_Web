
from django.urls import (
    path,
    include,
)


urlpatterns = [
    path("api/", include("core.urls")),
    path("api/", include("academics.urls")),
    path(
        "api/auth/",
        include("accounts.urls"),
    ),

    path(
        "api/assignments/",
        include("assignments.urls"),
    ),

    path(
        "api/materials/",
        include("materials.urls"),
    ),

    path(
        "api/quizzes/",
        include("quiz.urls"),
    ),
    path(
        "api/attendance/",
        include("attendance.urls"),
    ),
    path(
        "api/announcements/",
        include("announcements.urls"),
    ),

    path(
        "api/exams/",
        include("exams.urls"),
    ),
    path(
        "api/gpa/",
        include("gpa.urls"),
    ),
    path(
        "api/reports/",
        include("reports.urls"),
    ),
    path(
        "api/admin/manage/",
        include("administration.urls"),
    ),

]