from django.urls import path
from .views import (
    HealthView,
    DatabaseHealthView,
    VersionView,
)

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("db-health/", DatabaseHealthView.as_view(), name="db-health"),
    path(
        "version/",
        VersionView.as_view()
    ),
]
