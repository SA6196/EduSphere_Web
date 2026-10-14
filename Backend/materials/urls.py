"""
EduSphere LMS

Course Material URL Configuration

Commit 7
"""

from django.urls import path

from .views import (
    MaterialCreateView,
    MaterialListView,
    MaterialDetailView,
)


urlpatterns = [

    path(
        "create/",
        MaterialCreateView.as_view(),
        name="material-create",
    ),

    path(
        "",
        MaterialListView.as_view(),
        name="material-list",
    ),

    path(
        "<int:material_id>/",
        MaterialDetailView.as_view(),
        name="material-detail",
    ),

]