from .compliance_views import MasterDataCollectionView, MasterDataDetailView, AdminAuditView, StudentApprovalView
from django.urls import path

from .views import (
    AdminDirectoryView,
    AdminGradingSchemeView,
    AdminInstructorAccountsView,
    AdminOfferingCreateView,
    AdminOfferingInstructorView,
    AdminStudentAccountsView,
)

urlpatterns = [
    path("students/<int:student_id>/approve/", StudentApprovalView.as_view(), name="admin-student-approve"),
    path("master/<str:kind>/", MasterDataCollectionView.as_view(), name="admin-master-create"),
    path("master/<str:kind>/<int:record_id>/", MasterDataDetailView.as_view(), name="admin-master-update"),
    path("audit/", AdminAuditView.as_view(), name="admin-audit"),
    path("directory/", AdminDirectoryView.as_view(), name="admin-directory"),
    path("students/", AdminStudentAccountsView.as_view(), name="admin-students"),
    path("instructors/", AdminInstructorAccountsView.as_view(), name="admin-instructors"),
    path("offerings/", AdminOfferingCreateView.as_view(), name="admin-offering-create"),
    path(
        "offerings/<int:offering_id>/instructors/",
        AdminOfferingInstructorView.as_view(),
        name="admin-offering-instructors",
    ),
    path(
        "offerings/<int:offering_id>/grading-scheme/",
        AdminGradingSchemeView.as_view(),
        name="admin-grading-scheme",
    ),
]
