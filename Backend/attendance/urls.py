"""EduSphere LMS - Attendance URL Configuration."""

from django.urls import path
from .views import (
    SessionListView,
    SessionCreateView,
    RecordAttendanceView,
    MyAttendanceView,
    MyOfferingAttendanceView,
    MySemesterAttendanceView,
)

urlpatterns = [
    path("sessions/", SessionCreateView.as_view(), name="attendance-session-create"),
    path(
        "sessions/<int:offering_id>/",
        SessionListView.as_view(),
        name="attendance-session-list",
    ),
    path("record/", RecordAttendanceView.as_view(), name="attendance-record"),
    path("my/", MyAttendanceView.as_view(), name="attendance-my"),
    path("my/semester-view/", MySemesterAttendanceView.as_view(), name="attendance-my-semester"),
    path(
        "my/<int:offering_id>/",
        MyOfferingAttendanceView.as_view(),
        name="attendance-my-offering",
    ),
]
