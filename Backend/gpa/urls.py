from django.urls import path

from .views import (
    AdminStudentGPASummaryView,
    AdminStudentSemesterGPAView,
    MyGPASummaryView,
    MySemesterGPAView,
)


urlpatterns = [
    path("my/", MyGPASummaryView.as_view(), name="gpa-my"),
    path(
        "my/semester/<int:semester_id>/",
        MySemesterGPAView.as_view(),
        name="gpa-my-semester",
    ),
    path(
        "student/<int:student_id>/",
        AdminStudentGPASummaryView.as_view(),
        name="gpa-admin-student",
    ),
    path(
        "student/<int:student_id>/semester/<int:semester_id>/",
        AdminStudentSemesterGPAView.as_view(),
        name="gpa-admin-student-semester",
    ),
]
