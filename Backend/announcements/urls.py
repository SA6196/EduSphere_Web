"""
EduSphere LMS

Announcement URL Configuration
"""

from django.urls import path

from .views import (
    AnnouncementCreateView,
    AnnouncementDetailView,
    AnnouncementListView,
)


urlpatterns = [
    path(
        "create/",
        AnnouncementCreateView.as_view(),
        name="announcement-create",
    ),
    path(
        "",
        AnnouncementListView.as_view(),
        name="announcement-list",
    ),
    path(
        "<int:announcement_id>/",
        AnnouncementDetailView.as_view(),
        name="announcement-detail",
    ),
]
