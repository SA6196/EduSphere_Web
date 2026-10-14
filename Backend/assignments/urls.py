"""
EduSphere LMS

Assignment URL Configuration

Commit 6
"""


from django.urls import path


from .views import (
    AssignmentCreateView,
    AssignmentListView,
    AssignmentSubmissionView,
    InstructorSubmissionListView,
    StudentSubmissionListView,
)



urlpatterns = [

    path(
        "create/",
        AssignmentCreateView.as_view(),
        name="assignment-create",
    ),


    path(
        "",
        AssignmentListView.as_view(),
        name="assignment-list",
    ),


    path(
        "<int:assignment_id>/submit/",
        AssignmentSubmissionView.as_view(),
        name="assignment-submit",
    ),


    path(
        "<int:assignment_id>/submissions/",
        StudentSubmissionListView.as_view(),
        name="assignment-submissions",
    ),
    path(
        "<int:assignment_id>/review/",
        InstructorSubmissionListView.as_view(),
        name="assignment-review",
    ),

]