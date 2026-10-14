from django.urls import path

from .views import (
    AdminOverviewReportView,
    OfferingRosterReportView,
    SemesterListReportView,
    StudentProgressReportView,
    StudentUpcomingExamsReportView,
)


urlpatterns = [
    path("admin/overview/", AdminOverviewReportView.as_view(), name="report-admin-overview"),
    path("semesters/", SemesterListReportView.as_view(), name="report-semesters"),
    path(
        "offering/<int:offering_id>/roster/",
        OfferingRosterReportView.as_view(),
        name="report-offering-roster",
    ),
    path(
        "student/<int:student_id>/progress/",
        StudentProgressReportView.as_view(),
        name="report-student-progress",
    ),
    path(
        "student/<int:student_id>/upcoming-exams/",
        StudentUpcomingExamsReportView.as_view(),
        name="report-student-upcoming-exams",
    ),
]
