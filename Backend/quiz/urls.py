"""EduSphere LMS - Quiz URL Configuration."""

from django.urls import path
from .views import (
    QuizCreateView,
    QuizListView,
    QuizContentView,
    QuizVisibilityView,
    QuizAttemptView,
    QuizResponseView,
    QuestionListView,
    QuestionDetailView,
    QuestionCreateView,
    QuestionOptionCreateView,
    AddQuestionToQuizView,
    ResponseOptionView,
    QuizSubmitView,
    StudentQuizAttemptsView,
    QuizAttemptResultView,
    QuizAttemptReviewView,
    QuizGradingListView,
    QuizGradingDetailView,
    QuizGradingReleaseView,
    QuizGradingRetryView,
    QuestionNumericRuleView,
    QuestionKeywordView,
)

urlpatterns = [
    path("create/", QuizCreateView.as_view(), name="quiz-create"),
    path("", QuizListView.as_view(), name="quiz-list"),
    path("<int:quiz_id>/content/", QuizContentView.as_view(), name="quiz-content"),
    path(
        "<int:quiz_id>/visibility/",
        QuizVisibilityView.as_view(),
        name="quiz-visibility",
    ),
    path("<int:quiz_id>/attempt/", QuizAttemptView.as_view(), name="quiz-attempt"),
    path(
        "attempt/<int:attempt_id>/response/",
        QuizResponseView.as_view(),
        name="quiz-response",
    ),
    path(
        "attempt/response/option/",
        ResponseOptionView.as_view(),
        name="quiz-response-option",
    ),
    path(
        "attempt/<int:attempt_id>/submit/",
        QuizSubmitView.as_view(),
        name="quiz-submit",
    ),
    path(
        "attempts/my/",
        StudentQuizAttemptsView.as_view(),
        name="student-quiz-attempts",
    ),
    path(
        "attempt/<int:attempt_id>/result/",
        QuizAttemptResultView.as_view(),
        name="quiz-attempt-result",
    ),
    path(
        "attempt/<int:attempt_id>/review/",
        QuizAttemptReviewView.as_view(),
        name="quiz-attempt-review",
    ),
    path(
        "<int:quiz_id>/grading/",
        QuizGradingListView.as_view(),
        name="quiz-grading-list",
    ),
    path(
        "attempt/<int:attempt_id>/grading/",
        QuizGradingDetailView.as_view(),
        name="quiz-grading-detail",
    ),
    path(
        "attempt/<int:attempt_id>/grading/retry/",
        QuizGradingRetryView.as_view(),
        name="quiz-grading-retry",
    ),
    path(
        "attempt/<int:attempt_id>/grading/release/",
        QuizGradingReleaseView.as_view(),
        name="quiz-grading-release",
    ),
    path("questions/", QuestionListView.as_view(), name="question-list"),
    path("questions/create/", QuestionCreateView.as_view(), name="question-create"),
    path(
        "questions/options/create/",
        QuestionOptionCreateView.as_view(),
        name="question-option-create",
    ),
    path("questions/add/", AddQuestionToQuizView.as_view(), name="question-add"),
    path(
        "questions/<int:question_id>/",
        QuestionDetailView.as_view(),
        name="question-detail",
    ),
    path(
        "questions/numeric-rule/",
        QuestionNumericRuleView.as_view(),
        name="question-numeric-rule",
    ),
    path(
        "questions/keywords/",
        QuestionKeywordView.as_view(),
        name="question-keyword",
    ),
]
