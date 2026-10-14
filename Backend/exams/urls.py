from django.urls import path

from .views import (
    ExamDetailView,
    ExamOfferingListView,
    ExamScheduleCreateView,
    MyUpcomingExamsView,
)


urlpatterns = [
    path("schedule/", ExamScheduleCreateView.as_view(), name="exam-schedule"),
    path("", ExamOfferingListView.as_view(), name="exam-list"),
    path("my/upcoming/", MyUpcomingExamsView.as_view(), name="exam-my-upcoming"),
    path("<int:exam_id>/", ExamDetailView.as_view(), name="exam-detail"),
]
