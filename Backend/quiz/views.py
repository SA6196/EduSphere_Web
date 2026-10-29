"""EduSphere LMS - Quiz API Views."""

from accounts.authentication import LMSJWTAuthentication
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .services import QuizService
from accounts.permissions import IsAdmin, IsInstructor, IsStudent


class QuizCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        result = QuizService.create_quiz(
            user_id=request.user.user_id,
            instructor_id=request.user.instructor_id,
            user_role=request.user.role,
            component_id=request.data.get("component_id"),
            quiz_title=request.data.get("quiz_title"),
            open_at=request.data.get("open_at"),
            close_at=request.data.get("close_at"),
            duration_minutes=request.data.get("duration_minutes"),
            max_attempts=request.data.get("max_attempts"),
        )
        return Response({"success": True, "data": result})


class QuizListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        result = QuizService.list_quizzes(
            request.GET.get("component_id"),
            request.user.role,
            request.user.student_id,
            request.user.instructor_id,
        )
        return Response({"success": True, "data": result})


class QuizContentView(APIView):
    authentication_classes = [LMSJWTAuthentication]
    permission_classes = [IsStudent | IsInstructor | IsAdmin]

    def get(self, request, quiz_id):
        result = QuizService.quiz_content(
            user_role=request.user.role,
            student_id=request.user.student_id,
            instructor_id=request.user.instructor_id,
            quiz_id=quiz_id,
        )
        return Response({"success": True, "data": result})


class QuizVisibilityView(APIView):
    permission_classes = [IsInstructor | IsAdmin]

    def patch(self, request, quiz_id):
        result = QuizService.update_visibility(
            user_id=request.user.user_id,
            instructor_id=request.user.instructor_id,
            user_role=request.user.role,
            quiz_id=quiz_id,
            allow_mark_view=request.data.get("allow_mark_view"),
            allow_answer_review=request.data.get("allow_answer_review"),
        )
        return Response({"success": True, "data": result})


class QuizAttemptView(APIView):
    authentication_classes = [LMSJWTAuthentication]
    permission_classes = [IsStudent]

    def post(self, request, quiz_id):
        result = QuizService.start_attempt(
            user_id=request.user.user_id,
            student_id=request.user.student_id,
            user_role=request.user.role,
            quiz_id=quiz_id,
        )
        return Response({"success": True, "data": result})


class QuizResponseView(APIView):
    authentication_classes = [LMSJWTAuthentication]
    permission_classes = [IsStudent]

    def post(self, request, attempt_id):
        result = QuizService.submit_response(
            user_id=request.user.user_id,
            student_id=request.user.student_id,
            user_role=request.user.role,
            attempt_id=attempt_id,
            question_id=request.data.get("question_id"),
            response_text=request.data.get("response_text"),
            ordered_option_ids=request.data.get("ordered_option_ids"),
            matching_pairs=request.data.get("matching_pairs"),
            selected_option_ids=request.data.get("selected_option_ids"),
        )
        return Response({"success": True, "data": result})


class QuestionListView(APIView):
    authentication_classes = [LMSJWTAuthentication]
    permission_classes = [IsInstructor | IsAdmin]

    def get(self, request):
        return Response(
            {
                "success": True,
                "data": QuizService.question_bank(request.user.role, request.user.instructor_id, request.user.user_id),
            }
        )


class QuestionDetailView(APIView):
    authentication_classes = [LMSJWTAuthentication]
    permission_classes = [IsInstructor | IsAdmin]

    def get(self, request, question_id):
        return Response(
            {
                "success": True,
                "data": QuizService.question_detail(
                    request.user.role,
                    question_id,
                    request.user.instructor_id,
                    request.user.user_id,
                ),
            }
        )


class QuestionCreateView(APIView):
    authentication_classes = [LMSJWTAuthentication]
    permission_classes = [IsInstructor | IsAdmin]

    def post(self, request):
        result = QuizService.create_question(
            user_id=request.user.user_id,
            question_text=request.data.get("question_text"),
            question_type=request.data.get("question_type"),
            true_false_correct=request.data.get("true_false_correct"),
        )
        return Response({"success": True, "data": result})


class QuestionOptionCreateView(APIView):
    authentication_classes = [LMSJWTAuthentication]
    permission_classes = [IsInstructor | IsAdmin]

    def post(self, request):
        result = QuizService.add_option(
            user_id=request.user.user_id,
            question_id=request.data.get("question_id"),
            option_text=request.data.get("option_text"),
            is_correct=request.data.get("is_correct"),
            option_order=request.data.get("option_order"),
            match_side=request.data.get("match_side"),
            match_key=request.data.get("match_key"),
            user_role=request.user.role,
            instructor_id=request.user.instructor_id,
        )
        return Response({"success": True, "data": result})


class AddQuestionToQuizView(APIView):
    authentication_classes = [LMSJWTAuthentication]
    permission_classes = [IsInstructor | IsAdmin]

    def post(self, request):
        result = QuizService.add_question(
            user_id=request.user.user_id,
            user_role=request.user.role,
            instructor_id=request.user.instructor_id,
            quiz_id=request.data.get("quiz_id"),
            question_id=request.data.get("question_id"),
            question_order=request.data.get("question_order"),
            question_marks=request.data.get("question_marks"),
        )
        return Response({"success": True, "data": result})


class ResponseOptionView(APIView):
    authentication_classes = [LMSJWTAuthentication]
    permission_classes = [IsStudent]

    def post(self, request):
        result = QuizService.add_response_option(
            student_id=request.user.student_id,
            user_role=request.user.role,
            response_id=request.data.get("response_id"),
            option_id=request.data.get("option_id"),
        )
        return Response({"success": True, "data": result})


class QuizSubmitView(APIView):
    authentication_classes = [LMSJWTAuthentication]
    permission_classes = [IsStudent]

    def post(self, request, attempt_id):
        result = QuizService.submit_attempt(
            user_id=request.user.user_id,
            student_id=request.user.student_id,
            user_role=request.user.role,
            attempt_id=attempt_id,
        )
        return Response({"success": True, "data": result})


class StudentQuizAttemptsView(APIView):
    authentication_classes = [LMSJWTAuthentication]
    permission_classes = [IsStudent]

    def get(self, request):
        result = QuizService.student_attempts(
            student_id=request.user.student_id,
            user_role=request.user.role,
        )
        return Response({"success": True, "data": result})


class QuizAttemptResultView(APIView):
    authentication_classes = [LMSJWTAuthentication]
    permission_classes = [IsStudent]

    def get(self, request, attempt_id):
        result = QuizService.attempt_result(
            student_id=request.user.student_id,
            user_role=request.user.role,
            attempt_id=attempt_id,
        )
        return Response({"success": True, "data": result})


class QuizAttemptReviewView(APIView):
    authentication_classes = [LMSJWTAuthentication]
    permission_classes = [IsStudent]

    def get(self, request, attempt_id):
        result = QuizService.attempt_review(
            student_id=request.user.student_id,
            user_role=request.user.role,
            attempt_id=attempt_id,
        )
        return Response({"success": True, "data": result})


class QuizGradingListView(APIView):
    authentication_classes = [LMSJWTAuthentication]
    permission_classes = [IsInstructor | IsAdmin]

    def get(self, request, quiz_id):
        result = QuizService.instructor_grading_list(
            user_role=request.user.role,
            instructor_id=request.user.instructor_id,
            quiz_id=quiz_id,
        )
        return Response({"success": True, "data": result})


class QuizGradingDetailView(APIView):
    authentication_classes = [LMSJWTAuthentication]
    permission_classes = [IsInstructor | IsAdmin]

    def get(self, request, attempt_id):
        result = QuizService.instructor_grading_detail(
            user_role=request.user.role,
            instructor_id=request.user.instructor_id,
            attempt_id=attempt_id,
        )
        return Response({"success": True, "data": result})

    def patch(self, request, attempt_id):
        result = QuizService.review_grading(
            user_id=request.user.user_id,
            instructor_id=request.user.instructor_id,
            user_role=request.user.role,
            attempt_id=attempt_id,
            final_marks=request.data.get("final_marks"),
            notes=request.data.get("notes"),
            question_reviews=request.data.get("question_reviews"),
        )
        return Response({"success": True, "data": result})


class QuizGradingRetryView(APIView):
    authentication_classes = [LMSJWTAuthentication]
    permission_classes = [IsInstructor | IsAdmin]

    def post(self, request, attempt_id):
        result = QuizService.retry_auto_grading(
            user_id=request.user.user_id,
            instructor_id=request.user.instructor_id,
            user_role=request.user.role,
            attempt_id=attempt_id,
        )
        return Response({"success": True, "data": result})


class QuizGradingReleaseView(APIView):
    authentication_classes = [LMSJWTAuthentication]
    permission_classes = [IsInstructor | IsAdmin]

    def post(self, request, attempt_id):
        result = QuizService.release_grading(
            user_id=request.user.user_id,
            instructor_id=request.user.instructor_id,
            user_role=request.user.role,
            attempt_id=attempt_id,
        )
        return Response({"success": True, "data": result})


class QuestionNumericRuleView(APIView):
    authentication_classes = [LMSJWTAuthentication]
    permission_classes = [IsInstructor | IsAdmin]

    def post(self, request):
        result = QuizService.configure_numeric_rule(
            user_role=request.user.role,
            question_id=request.data.get("question_id"),
            expected_value=request.data.get("expected_value"),
            tolerance=request.data.get("tolerance", 0),
            instructor_id=request.user.instructor_id,
            user_id=request.user.user_id,
        )
        return Response({"success": True, "data": result})


class QuestionKeywordView(APIView):
    authentication_classes = [LMSJWTAuthentication]
    permission_classes = [IsInstructor | IsAdmin]

    def post(self, request):
        result = QuizService.add_question_keyword(
            user_role=request.user.role,
            question_id=request.data.get("question_id"),
            keyword_order=request.data.get("keyword_order"),
            keyword_text=request.data.get("keyword_text"),
            instructor_id=request.user.instructor_id,
            user_id=request.user.user_id,
        )
        return Response({"success": True, "data": result})
