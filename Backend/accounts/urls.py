from django.urls import path
from .views import LoginView, RefreshView, MeView, StudentSignupView, PublicProgramListView

urlpatterns = [
    path("signup/", StudentSignupView.as_view(), name="student-signup"),
    path("public-programs/", PublicProgramListView.as_view(), name="public-programs"),
    path("login/", LoginView.as_view(), name="login"),
    path("refresh/", RefreshView.as_view(), name="refresh"),
    path("me/", MeView.as_view(), name="me"),
]
