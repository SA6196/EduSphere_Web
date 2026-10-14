from django.urls import path
from .views import (
    StudentDashboardView,
    InstructorOfferingsView,
    AdminSummaryView,
    CourseListView,
    OfferingListView,
    OfferingDetailView,
    OfferingGradingView,
    InstructorOfferingRosterView,
    EnrollmentCreateView,
    MyEnrollmentView,
    RecordMarkView,
    PublishGradeView,
    StudentMarksView,
    StudentSemesterMarkbookView,
)

urlpatterns = [
    path("student/dashboard/", StudentDashboardView.as_view(), name="student-dashboard"),
    path("instructor/offerings/", InstructorOfferingsView.as_view(), name="instructor-offerings"),
    path(
        "instructor/offerings/<int:offering_id>/roster/",
        InstructorOfferingRosterView.as_view(),
        name="instructor-offering-roster",
    ),
    path("admin/summary/", AdminSummaryView.as_view(), name="admin-summary"),
    path("courses/", CourseListView.as_view(), name="courses"),
    path("offerings/", OfferingListView.as_view(), name="offerings"),
    path("offerings/<int:offering_id>/", OfferingDetailView.as_view(), name="offering-detail"),
    path(
        "offerings/<int:offering_id>/grading/",
        OfferingGradingView.as_view(),
        name="offering-grading",
    ),
    path("enrollments/", EnrollmentCreateView.as_view(), name="enrollment-create"),
    path("enrollments/my/", MyEnrollmentView.as_view(), name="my-enrollments"),
    path("marks/record/", RecordMarkView.as_view(), name="record-mark"),
    path("grades/publish/", PublishGradeView.as_view(), name="publish-grade"),
    path("marks/my/", StudentMarksView.as_view(), name="student-marks"),
    path("marks/my/semester-view/", StudentSemesterMarkbookView.as_view(), name="student-semester-markbook"),
]
