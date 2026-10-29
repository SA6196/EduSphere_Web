"""
EduSphere LMS

Quiz Service Layer

Frontend-ready quiz authoring, delivery, attempt, result and review services.
"""

from datetime import datetime
from decimal import Decimal, InvalidOperation
import hashlib
import hmac
import json
import random
import uuid

from django.conf import settings

from database.connection import atomic_oracle
from database.query import execute

from accounts.authorization import require_role
from core.audit import log_activity
from core.constants import Roles, ActivityTypes
from core.exceptions import (
    ValidationError,
    PermissionDeniedError,
    NotFoundError,
    BusinessRuleError,
)
from core.validators import validate_required, validate_positive_integer
from assignments.repository import get_component, instructor_owns_offering
from academics.repository import student_has_offering

from .auto_grader import auto_grade_attempt, synchronize_quiz_component_mark, load_responses
from database.query import fetch_one
from database.schema import object_name
from .repository import (
    create_quiz,
    get_quiz,
    get_quiz_context,
    get_quizzes,
    update_quiz_visibility,
    quiz_exists_for_component,
    create_question,
    get_question,
    get_question_by_text_type,
    get_enrollment_context_for_quiz_attempt,
    list_questions,
    list_questions_for_instructor,
    get_question_options,
    get_option,
    add_question_to_quiz,
    create_question_option,
    get_quiz_content_rows,
    start_quiz_attempt,
    get_attempt,
    get_attempt_submission_state,
    question_belongs_to_quiz,
    get_open_attempt_for_student_quiz,
    get_response,
    get_response_by_attempt_question,
    create_response,
    add_response_option,
    add_response_order,
    add_response_match,
    get_grading_for_attempt,
    get_question_grades,
    list_quiz_gradings,
    update_grading_review,
    release_grading,
    get_numeric_rule,
    set_numeric_rule,
    get_keywords,
    add_keyword,
    get_attempt_result_context,
    get_attempt_review_questions,
    get_selected_options,
    get_response_order_items,
    get_response_match_items,
    list_student_quiz_attempts,
    question_access_for_instructor,
    lock_attempt_for_answer_update,
    replace_response_text,
    clear_response_children,
    set_question_grade,
    submit_quiz_attempt,
    quiz_has_attempts,
    question_has_attempts,
)


def _student_option_token(attempt_id, question_id, option_id):
    """Opaque, attempt-bound option handle (never reveal answer-order IDs)."""
    data = f"quiz-option:{int(attempt_id)}:{int(question_id)}:{int(option_id)}".encode()
    return hmac.new(settings.SECRET_KEY.encode(), data, hashlib.sha256).hexdigest()[:32]


def _student_option_shuffle(items, attempt_id, question_id):
    """Unpredictable but stable on refresh; no correct OPTION_ORDER is sent."""
    data = f"quiz-display:{int(attempt_id)}:{int(question_id)}".encode()
    seed = hmac.new(settings.SECRET_KEY.encode(), data, hashlib.sha256).digest()
    result = list(items)
    random.Random(int.from_bytes(seed, "big")).shuffle(result)
    if len(result) > 1 and result == items:
        result = result[1:] + result[:1]
    return result


def _resolve_student_option_ids(attempt_id, question_id, handles):
    """Translate student-visible opaque handles into real FK option IDs.

    Handles are bound to the attempt and question, cannot be replayed for other
    attempts, and do not encode the database's answer order or matching keys.
    """
    options = get_question_options(int(question_id))
    handles_to_ids = {
        _student_option_token(attempt_id, question_id, row["option_id"]): int(row["option_id"])
        for row in options
    }
    if not isinstance(handles, list):
        raise ValidationError("Options must be submitted as an ordered list.")
    result = []
    for handle in handles:
        if not isinstance(handle, str) or handle not in handles_to_ids:
            raise ValidationError("Invalid option for this quiz attempt.")
        result.append(handles_to_ids[handle])
    return result


class QuizService:

    @staticmethod
    def create_quiz(
        user_id,
        instructor_id,
        user_role,
        component_id,
        quiz_title,
        open_at,
        close_at,
        duration_minutes,
        max_attempts,
    ):
        validate_required(component_id, "component_id")
        validate_positive_integer(component_id, "component_id")
        validate_required(quiz_title, "quiz_title")
        validate_required(max_attempts, "max_attempts")
        validate_positive_integer(max_attempts, "max_attempts")

        require_role(user_role, [Roles.INSTRUCTOR])

        component = get_component(component_id)
        if not component:
            raise NotFoundError("Assessment component not found.")
        if component["component_type"] != "QUIZ":
            raise ValidationError("Component type must be QUIZ.")
        if not instructor_owns_offering(
            instructor_id,
            component["offering_id"],
        ):
            raise PermissionDeniedError(
                "Instructor does not own this offering."
            )

        try:
            if open_at:
                open_at = datetime.fromisoformat(open_at)
            if close_at:
                close_at = datetime.fromisoformat(close_at)
        except Exception as exc:
            raise ValidationError(
                "Invalid quiz date format. Use YYYY-MM-DDTHH:MM:SS."
            ) from exc

        if quiz_exists_for_component(component_id):
            raise ValidationError("Quiz already exists for this component.")

        create_quiz(
            component_id,
            quiz_title,
            open_at,
            close_at,
            duration_minutes,
            max_attempts,
        )

        log_activity(
            user_id=user_id,
            activity_type=ActivityTypes.QUIZ_CREATED,
            activity_description=f"Quiz created: {quiz_title}",
        )
        return {"message": "Quiz created successfully"}

    @staticmethod
    def list_quizzes(component_id, user_role, student_id=None, instructor_id=None):
        require_role(user_role, [Roles.STUDENT, Roles.INSTRUCTOR, Roles.ADMIN])
        validate_positive_integer(component_id, "component_id")
        component = get_component(int(component_id))
        if not component:
            raise NotFoundError("Assessment component not found.")
        if user_role == Roles.STUDENT and not student_has_offering(
            int(student_id or 0), int(component["offering_id"])
        ):
            raise PermissionDeniedError("This quiz belongs to another course.")
        if user_role == Roles.INSTRUCTOR and not instructor_owns_offering(
            int(instructor_id or 0), int(component["offering_id"])
        ):
            raise PermissionDeniedError("Instructor is not assigned to this course.")
        return get_quizzes(int(component_id))

    @staticmethod
    def update_visibility(
        user_id,
        instructor_id,
        user_role,
        quiz_id,
        allow_mark_view,
        allow_answer_review,
    ):
        require_role(user_role, [Roles.INSTRUCTOR, Roles.ADMIN])
        validate_positive_integer(quiz_id, "quiz_id")

        quiz = get_quiz_context(int(quiz_id))
        if not quiz:
            raise NotFoundError("Quiz not found.")

        if user_role == Roles.INSTRUCTOR:
            if not instructor_owns_offering(
                instructor_id,
                quiz["offering_id"],
            ):
                raise PermissionDeniedError(
                    "Instructor does not own this quiz."
                )

        if allow_mark_view not in ("Y", "N"):
            raise ValidationError("Invalid mark visibility value.")
        if allow_answer_review not in ("Y", "N"):
            raise ValidationError("Invalid answer visibility value.")

        update_quiz_visibility(
            int(quiz_id),
            allow_mark_view,
            allow_answer_review,
        )
        log_activity(
            user_id=user_id,
            activity_type=ActivityTypes.QUIZ_VISIBILITY_UPDATED,
            activity_description=f"Quiz {int(quiz_id)} visibility updated",
        )
        return {"message": "Quiz visibility updated successfully"}

    @staticmethod
    @atomic_oracle
    def create_question(user_id, question_text, question_type, true_false_correct=None):
        validate_required(question_text, "question_text")
        validate_required(question_type, "question_type")

        question_type = str(question_type).strip().upper()
        allowed_types = {
            "MCQ_SINGLE",
            "MCQ_MULTI",
            "TRUE_FALSE",
            "MATCHING",
            "ORDERING",
            "NUMERICAL",
            "SHORT_TEXT",
            "FILL_BLANK",
            "LONG_TEXT",
        }
        if question_type not in allowed_types:
            raise ValidationError(
                "Unsupported question type."
            )

        # Validate BEFORE any write, and identify the inserted CLOB row without
        # SELECT MAX(ID), which can return another instructor's concurrent row.
        if question_type == "TRUE_FALSE" and str(true_false_correct or "").strip().upper() not in ("YES", "NO"):
            raise ValidationError("true_false_correct must be YES or NO.")
        marker = "[EDUSPHERE-TEMP-" + uuid.uuid4().hex + "]"
        create_question(str(question_text) + "\n" + marker, question_type)
        created = fetch_one(
            f"SELECT QUESTION_ID FROM {object_name('QUESTION')} "
            "WHERE QUESTION_TYPE=? AND DBMS_LOB.INSTR(QUESTION_TEXT, ?) > 0",
            (question_type, marker),
        )
        if not created:
            raise BusinessRuleError("Question could not be safely identified.")
        question_id = int(created["question_id"])
        execute(
            f"UPDATE {object_name('QUESTION')} SET QUESTION_TEXT=? WHERE QUESTION_ID=?",
            (str(question_text), question_id),
        )

        # TRUE/FALSE is always authored as exactly two options.
        if question_type == "TRUE_FALSE":
            correct = str(true_false_correct or "").strip().upper()
            if correct not in ("YES", "NO"):
                raise ValidationError("true_false_correct must be YES or NO.")
            create_question_option(
                question_id=question_id,
                option_text="Yes",
                is_correct="Y" if correct == "YES" else "N",
                option_order=1,
            )
            create_question_option(
                question_id=question_id,
                option_text="No",
                is_correct="Y" if correct == "NO" else "N",
                option_order=2,
            )

        log_activity(
            user_id=user_id,
            activity_type=ActivityTypes.QUESTION_CREATED,
            activity_description=f"QUESTION_ID={question_id};CREATED",
        )
        return {"message": "Question created successfully", "question_type": question_type, "question_id": question_id}

    @staticmethod
    def question_bank(user_role, instructor_id=None, user_id=None):
        require_role(user_role, [Roles.INSTRUCTOR, Roles.ADMIN])
        if user_role == Roles.ADMIN:
            return list_questions()
        return list_questions_for_instructor(user_id, instructor_id)

    @staticmethod
    def question_detail(user_role, question_id, instructor_id=None, user_id=None):
        require_role(user_role, [Roles.INSTRUCTOR, Roles.ADMIN])
        validate_positive_integer(question_id, "question_id")
        question_id = int(question_id)

        question = get_question(question_id)
        if not question:
            raise NotFoundError("Question not found.")
        if user_role == Roles.INSTRUCTOR and not question_access_for_instructor(
            question_id, instructor_id, user_id, edit=False
        ):
            raise PermissionDeniedError("Question is outside your authorized question bank.")

        return {
            "question": question,
            "options": get_question_options(question_id, include_correct=True),
            "numeric_rule": get_numeric_rule(question_id),
            "keywords": get_keywords(question_id),
        }

    @staticmethod
    def add_question(
        user_id,
        user_role,
        instructor_id,
        quiz_id,
        question_id,
        question_order,
        question_marks,
    ):
        require_role(user_role, [Roles.INSTRUCTOR, Roles.ADMIN])
        validate_positive_integer(quiz_id, "quiz_id")
        validate_positive_integer(question_id, "question_id")
        validate_positive_integer(question_order, "question_order")

        try:
            question_marks = float(question_marks)
        except (TypeError, ValueError) as exc:
            raise ValidationError("question_marks must be numeric.") from exc
        if question_marks <= 0:
            raise ValidationError("question_marks must be positive.")

        quiz = get_quiz_context(int(quiz_id))
        if not quiz:
            raise NotFoundError("Quiz not found.")
        if not get_question(int(question_id)):
            raise NotFoundError("Question not found.")
        if quiz_has_attempts(int(quiz_id)):
            raise BusinessRuleError("Quiz questions are locked after the first attempt. Create a new quiz for revisions.")
        if user_role == Roles.INSTRUCTOR and not question_access_for_instructor(
            int(question_id), instructor_id, user_id, edit=False
        ):
            raise PermissionDeniedError("Question is outside your authorized question bank.")

        if user_role == Roles.INSTRUCTOR:
            if not instructor_owns_offering(
                instructor_id,
                quiz["offering_id"],
            ):
                raise PermissionDeniedError(
                    "Instructor does not own this quiz."
                )

        add_question_to_quiz(
            int(quiz_id),
            int(question_id),
            int(question_order),
            question_marks,
        )
        log_activity(
            user_id=user_id,
            activity_type=ActivityTypes.QUIZ_QUESTION_ADDED,
            activity_description=(
                f"Question {int(question_id)} added to quiz {int(quiz_id)}"
            ),
        )
        return {"message": "Question added successfully"}

    @staticmethod
    def add_option(
        user_id,
        question_id,
        option_text,
        is_correct,
        option_order,
        match_side=None,
        match_key=None,
        user_role=None,
        instructor_id=None,
    ):
        require_role(user_role, [Roles.INSTRUCTOR, Roles.ADMIN])
        validate_positive_integer(question_id, "question_id")
        validate_required(option_text, "option_text")
        validate_positive_integer(option_order, "option_order")

        is_correct = str(is_correct).strip().upper() if is_correct is not None else None
        if is_correct not in ("Y", "N"):
            raise ValidationError("is_correct must be Y or N.")
        if not get_question(int(question_id)):
            raise NotFoundError("Question not found.")

        question = get_question(int(question_id))
        if question_has_attempts(int(question_id)):
            raise BusinessRuleError("Question answers are locked after an associated quiz has been attempted.")
        if user_role == Roles.INSTRUCTOR and not question_access_for_instructor(
            int(question_id), instructor_id, user_id, edit=True
        ):
            raise PermissionDeniedError("You may only modify your own unused questions.")
        if question["question_type"] == "MATCHING":
            match_side = str(match_side or "").strip().upper()
            if match_side not in ("L", "R"):
                raise ValidationError("MATCHING options require match_side L or R.")
            if not str(match_key or "").strip():
                raise ValidationError("MATCHING options require a shared match_key.")
        else:
            match_side = None
            match_key = None

        create_question_option(
            int(question_id),
            option_text,
            is_correct,
            int(option_order),
            match_side,
            match_key,
        )
        log_activity(
            user_id=user_id,
            activity_type=ActivityTypes.QUESTION_OPTION_CREATED,
            activity_description=(
                f"Option {int(option_order)} created for question {int(question_id)}"
            ),
        )
        return {"message": "Option added successfully"}

    @staticmethod
    def configure_numeric_rule(user_role, question_id, expected_value, tolerance, instructor_id=None, user_id=None):
        require_role(user_role, [Roles.INSTRUCTOR, Roles.ADMIN])
        validate_positive_integer(question_id, "question_id")
        question = get_question(int(question_id))
        if not question:
            raise NotFoundError("Question not found.")
        if question_has_attempts(int(question_id)):
            raise BusinessRuleError("Question answers are locked after an associated quiz has been attempted.")
        if user_role == Roles.INSTRUCTOR and not question_access_for_instructor(
            int(question_id), instructor_id, user_id, edit=True
        ):
            raise PermissionDeniedError("You may only modify your own unused questions.")
        if question["question_type"] != "NUMERICAL":
            raise ValidationError("Numeric grading rules are only valid for NUMERICAL questions.")
        try:
            expected_value = float(expected_value)
            tolerance = float(tolerance)
        except (TypeError, ValueError) as exc:
            raise ValidationError("expected_value and tolerance must be numeric.") from exc
        if tolerance < 0:
            raise ValidationError("tolerance cannot be negative.")
        set_numeric_rule(int(question_id), expected_value, tolerance)
        return {"message": "Numeric grading rule saved."}

    @staticmethod
    def add_question_keyword(user_role, question_id, keyword_order, keyword_text, instructor_id=None, user_id=None):
        require_role(user_role, [Roles.INSTRUCTOR, Roles.ADMIN])
        validate_positive_integer(question_id, "question_id")
        validate_positive_integer(keyword_order, "keyword_order")
        validate_required(keyword_text, "keyword_text")
        question = get_question(int(question_id))
        if not question:
            raise NotFoundError("Question not found.")
        if question_has_attempts(int(question_id)):
            raise BusinessRuleError("Question answers are locked after an associated quiz has been attempted.")
        if user_role == Roles.INSTRUCTOR and not question_access_for_instructor(
            int(question_id), instructor_id, user_id, edit=True
        ):
            raise PermissionDeniedError("You may only modify your own unused questions.")
        if question["question_type"] not in ("SHORT_TEXT", "FILL_BLANK"):
            raise ValidationError(
                "Keywords are only valid for SHORT_TEXT or FILL_BLANK questions."
            )
        add_keyword(int(question_id), int(keyword_order), str(keyword_text).strip())
        return {"message": "Keyword added."}

    @staticmethod
    def quiz_content(
        user_role,
        student_id,
        instructor_id,
        quiz_id,
    ):
        require_role(
            user_role,
            [Roles.STUDENT, Roles.INSTRUCTOR, Roles.ADMIN],
        )
        validate_positive_integer(quiz_id, "quiz_id")
        quiz_id = int(quiz_id)

        quiz = get_quiz_context(quiz_id)
        if not quiz:
            raise NotFoundError("Quiz not found.")

        include_correct = False
        attempt = None

        if user_role == Roles.STUDENT:
            attempt = get_open_attempt_for_student_quiz(student_id, quiz_id)
            if not attempt:
                raise BusinessRuleError(
                    "Start the quiz attempt before loading quiz content."
                )
        elif user_role == Roles.INSTRUCTOR:
            if not instructor_owns_offering(
                instructor_id,
                quiz["offering_id"],
            ):
                raise PermissionDeniedError(
                    "Instructor is not assigned to this quiz offering."
                )
            include_correct = True
        else:
            include_correct = True

        rows = get_quiz_content_rows(quiz_id, include_correct=include_correct)
        questions = []
        by_id = {}

        for row in rows:
            question_id = int(row["question_id"])
            question = by_id.get(question_id)
            if question is None:
                question = {
                    "question_id": question_id,
                    "question_order": row["question_order"],
                    "question_marks": row["question_marks"],
                    "question_text": row["question_text"],
                    "question_type": row["question_type"],
                    "options": [],
                }
                if str(row["question_type"]).upper() == "FILL_BLANK":
                    keyword_rows = get_keywords(question_id)
                    # Students need only the number and positions of blanks.
                    # KEYWORD_TEXT is an instructor-only answer key.
                    question["keywords"] = (
                        keyword_rows if include_correct else
                        [{"keyword_order": k["keyword_order"]} for k in keyword_rows]
                    )
                by_id[question_id] = question
                questions.append(question)

            if row.get("option_id") is not None:
                qtype = str(row["question_type"]).upper()
                secret_option = not include_correct and qtype in ("ORDERING", "MATCHING")
                option = {
                    "option_id": (
                        _student_option_token(attempt["attempt_id"], question_id, row["option_id"])
                        if secret_option else int(row["option_id"])
                    ),
                    "option_text": row["option_text"],
                }
                if include_correct:
                    option.update({
                        "option_order": row["option_order"],
                        "match_side": row.get("match_side"),
                        "match_key": row.get("match_key"),
                        "is_correct": row["is_correct"],
                    })
                elif qtype == "MATCHING":
                    # Side is necessary for the UI, but the matching key is secret.
                    option["match_side"] = row.get("match_side")
                question["options"].append(option)

        if not include_correct:
            for question in questions:
                qtype = str(question["question_type"]).upper()
                if qtype in ("ORDERING", "MATCHING"):
                    question["options"] = _student_option_shuffle(
                        question["options"], attempt["attempt_id"], question["question_id"]
                    )

        saved_responses = {}
        if attempt:
            saved_by_question = load_responses(int(attempt["attempt_id"]))
            for q in questions:
                qid = int(q["question_id"])
                saved = saved_by_question.get(qid)
                if not saved:
                    continue
                qtype = str(q["question_type"]).upper()
                if qtype == "MCQ_MULTI":
                    answer = [str(n) for n in saved["selected_ids"]]
                elif qtype in ("MCQ_SINGLE", "TRUE_FALSE"):
                    answer = str(saved["selected_ids"][0]) if saved["selected_ids"] else ""
                elif qtype == "ORDERING":
                    answer = [_student_option_token(attempt["attempt_id"], qid, x["option_id"])
                              for x in sorted(saved["order_items"], key=lambda x: int(x["position_order"]))]
                elif qtype == "MATCHING":
                    answer = [{"left_option_id": _student_option_token(attempt["attempt_id"], qid, x["left_option_id"]),
                               "right_option_id": _student_option_token(attempt["attempt_id"], qid, x["right_option_id"])}
                              for x in saved["match_items"]]
                elif qtype == "FILL_BLANK":
                    try:
                        answer = json.loads(saved["response_text"] or "[]")
                    except (ValueError, TypeError):
                        answer = []
                else:
                    answer = saved["response_text"] or ""
                saved_responses[qid] = answer

        quiz_data = dict(quiz)
        # Correct-answer visibility is never implied by metadata; student content
        # deliberately contains no IS_CORRECT values.
        return {
            "quiz": quiz_data,
            "attempt_id": attempt["attempt_id"] if attempt else None,
            "attempt_started_at": attempt.get("started_at") if attempt else None,
            "saved_responses": saved_responses,
            "question_count": len(questions),
            "questions": questions,
        }

    @staticmethod
    def start_attempt(user_id, student_id, user_role, quiz_id):
        require_role(user_role, [Roles.STUDENT])
        validate_positive_integer(quiz_id, "quiz_id")

        quiz = get_quiz(quiz_id)
        if not quiz:
            raise NotFoundError("Quiz not found.")

        attempt = start_quiz_attempt(int(quiz_id), int(student_id))
        if not attempt:
            raise ValidationError(
                "Quiz attempt was created but could not be loaded."
            )

        log_activity(
            user_id=user_id,
            activity_type=ActivityTypes.QUIZ_ATTEMPT_STARTED,
            activity_description=(
                f"Quiz attempt started: {int(quiz_id)} "
                f"attempt {int(attempt['attempt_no'])}"
            ),
        )
        return {
            "message": "Quiz attempt started successfully",
            "attempt_id": int(attempt["attempt_id"]),
            "attempt_no": int(attempt["attempt_no"]),
        }

    @staticmethod
    @atomic_oracle
    def submit_response(
        user_id,
        student_id,
        user_role,
        attempt_id,
        question_id,
        response_text,
        ordered_option_ids=None,
        matching_pairs=None,
        selected_option_ids=None,
    ):
        require_role(user_role, [Roles.STUDENT])
        validate_positive_integer(attempt_id, "attempt_id")
        validate_positive_integer(question_id, "question_id")

        # Serializes student autosave and submission under the same parent row.
        attempt = lock_attempt_for_answer_update(int(attempt_id))
        if not attempt:
            raise NotFoundError("Quiz attempt not found.")
        if int(attempt["student_id"]) != int(student_id):
            raise PermissionDeniedError(
                "This quiz attempt belongs to another student."
            )
        if attempt.get("submitted_at") is not None:
            raise BusinessRuleError("This quiz attempt has already been submitted.")
        state = get_attempt_submission_state(int(attempt_id))
        if not state or state.get("submission_state") != "READY":
            raise BusinessRuleError("This quiz attempt has expired or closed. Submit it to finalize saved answers.")

        q = get_question(int(question_id))
        if not q:
            raise NotFoundError("Question not found.")

        if not question_belongs_to_quiz(int(attempt["quiz_id"]), int(question_id)):
            raise ValidationError("Question does not belong to this quiz.")

        # FILL_BLANK answers are stored in the existing RESPONSE_TEXT column
        # as an ordered JSON array.  Each array element represents one blank.
        if q["question_type"] == "FILL_BLANK":
            if not isinstance(response_text, list):
                raise ValidationError(
                    "FILL_BLANK response_text must be an ordered list of answers."
                )
            if any(not isinstance(value, str) for value in response_text):
                raise ValidationError(
                    "Each FILL_BLANK answer must be text."
                )
            response_text = json.dumps(
                response_text,
                ensure_ascii=False,
                separators=(",", ":"),
            )

        # The student endpoint accepts opaque handles for these two types;
        # only server-side code translates them into Oracle OPTION_ID values.
        if q["question_type"] == "ORDERING":
            ordered_option_ids = _resolve_student_option_ids(
                attempt_id, question_id, ordered_option_ids or []
            )
            if len(set(ordered_option_ids)) != len(ordered_option_ids):
                raise ValidationError("An ordering option cannot appear more than once.")
        elif q["question_type"] == "MATCHING":
            raw_pairs = matching_pairs or []
            if not isinstance(raw_pairs, list) or any(not isinstance(p, dict) for p in raw_pairs):
                raise ValidationError("matching_pairs must be a list of left/right option objects.")
            left = _resolve_student_option_ids(
                attempt_id, question_id, [p.get("left_option_id") for p in raw_pairs]
            )
            right = _resolve_student_option_ids(
                attempt_id, question_id, [p.get("right_option_id") for p in raw_pairs]
            )
            matching_pairs = [
                {"left_option_id": l, "right_option_id": r}
                for l, r in zip(left, right)
            ]
            if len(set(left)) != len(left) or len(set(right)) != len(right):
                raise ValidationError("Each left/right matching option may occur only once.")
            sides = {int(o["option_id"]): o.get("match_side") for o in get_question_options(int(question_id))}
            if any(sides.get(l) != "L" or sides.get(r) != "R" for l, r in zip(left, right)):
                raise ValidationError("Each match must pair a left option with a right option.")

        if q["question_type"] in ("MCQ_SINGLE", "MCQ_MULTI", "TRUE_FALSE"):
            if selected_option_ids is None:
                selected_option_ids = []
            if not isinstance(selected_option_ids, list):
                raise ValidationError("selected_option_ids must be a list.")
            allowed = {int(o["option_id"]) for o in get_question_options(int(question_id))}
            try:
                selections = [int(value) for value in selected_option_ids]
            except (TypeError, ValueError) as exc:
                raise ValidationError("Selected option IDs must be integers.") from exc
            if len(selections) != len(set(selections)) or any(i not in allowed for i in selections):
                raise ValidationError("Duplicate or invalid selected option.")
            if q["question_type"] != "MCQ_MULTI" and len(selections) > 1:
                raise ValidationError("Only one option can be selected for this question.")
        else:
            selections = []

        existing = get_response_by_attempt_question(int(attempt_id), int(question_id))
        if existing:
            response = existing
            replace_response_text(int(existing["response_id"]), response_text)
            clear_response_children(int(existing["response_id"]))
        else:
            response = create_response(int(attempt_id), int(question_id), response_text)
        if not response:
            raise ValidationError(
                "Quiz response was created but could not be reloaded."
            )

        for option_id in selections:
            add_response_option(int(response["response_id"]), option_id)

        if q["question_type"] == "ORDERING":
            for pos, option_id in enumerate(ordered_option_ids or [], start=1):
                add_response_order(int(response["response_id"]), pos, int(option_id))

        if q["question_type"] == "MATCHING":
            for pair in matching_pairs or []:
                add_response_match(
                    int(response["response_id"]),
                    int(pair["left_option_id"]),
                    int(pair["right_option_id"]),
                )

        log_activity(
            user_id=user_id,
            activity_type=ActivityTypes.QUIZ_RESPONSE_SUBMITTED,
            activity_description=(
                f"Response submitted for question {int(question_id)} "
                f"in attempt {int(attempt_id)}"
            ),
        )
        return {
            "message": "Response submitted successfully",
            "response_id": int(response["response_id"]),
            "attempt_id": int(response["attempt_id"]),
            "question_id": int(response["question_id"]),
        }

    @staticmethod
    def add_response_option(
        student_id,
        user_role,
        response_id,
        option_id,
    ):
        require_role(user_role, [Roles.STUDENT])
        validate_positive_integer(response_id, "response_id")
        validate_positive_integer(option_id, "option_id")

        response = get_response(response_id)
        if not response:
            raise NotFoundError("Quiz response not found.")
        if int(response["student_id"]) != int(student_id):
            raise PermissionDeniedError(
                "This quiz response belongs to another student."
            )
        if response.get("submitted_at") is not None:
            raise BusinessRuleError("This quiz attempt has already been submitted.")
        state = get_attempt_submission_state(int(response["attempt_id"]))
        if not state or state.get("submission_state") != "READY":
            raise BusinessRuleError("This quiz attempt has expired or closed.")

        option = get_option(int(option_id))
        if not option:
            raise NotFoundError("Question option not found.")
        if int(option["question_id"]) != int(response["question_id"]):
            raise ValidationError(
                "Selected option does not belong to the response question."
            )

        add_response_option(response_id, option_id)
        return {"message": "Response option added successfully"}

    @staticmethod
    def submit_attempt(user_id, student_id, user_role, attempt_id):
        require_role(user_role, [Roles.STUDENT])
        validate_positive_integer(attempt_id, "attempt_id")

        attempt = get_attempt(attempt_id)
        if not attempt:
            raise NotFoundError("Quiz attempt not found.")
        if int(attempt["student_id"]) != int(student_id):
            raise PermissionDeniedError(
                "This quiz attempt belongs to another student."
            )

        # Preflight the same Oracle rules used by PR_SUBMIT_QUIZ_ATTEMPT.
        # This avoids the misleading UTF-16/SystemError produced when some
        # Oracle ODBC driver versions cannot decode a raised application error.
        state = get_attempt_submission_state(int(attempt_id))
        if not state:
            raise NotFoundError("Quiz attempt not found.")
        submission_state = state["submission_state"]
        if submission_state == "ALREADY_SUBMITTED":
            raise BusinessRuleError("Quiz attempt has already been submitted.")
        # Expiry locks *answers*, not finalization. The approved database tables
        # remain unchanged; deploy the companion PR_SUBMIT_QUIZ_ATTEMPT patch.

        submit_quiz_attempt(attempt_id)
        try:
            # Internal grade values must NEVER be serialized in a student
            # submission response. The flag may still prohibit mark viewing.
            auto_grade_attempt(int(attempt_id))
            grading_state = "PROCESSED"
        except Exception:
            # Submission is authoritative. Grading can be retried by an
            # instructor; do not disclose Oracle errors to the student.
            grading_state = "RETRY_REQUIRED"
        log_activity(
            user_id=user_id,
            activity_type=ActivityTypes.QUIZ_ATTEMPT_SUBMITTED,
            activity_description=f"Quiz attempt submitted: {int(attempt_id)}",
        )
        return {
            "message": "Quiz attempt submitted successfully",
            "grading": {"status": grading_state},
        }

    @staticmethod
    def attempt_result(student_id, user_role, attempt_id):
        require_role(user_role, [Roles.STUDENT])
        validate_positive_integer(attempt_id, "attempt_id")
        attempt_id = int(attempt_id)

        result = get_attempt_result_context(attempt_id)
        if not result:
            raise NotFoundError("Quiz attempt not found.")
        if int(result["student_id"]) != int(student_id):
            raise PermissionDeniedError(
                "This quiz attempt belongs to another student."
            )
        if result["submitted_at"] is None:
            raise BusinessRuleError(
                "Quiz result is available only after the attempt is submitted."
            )
        if result["allow_mark_view"] != "Y":
            raise PermissionDeniedError(
                "Quiz marks are not currently visible."
            )
        # Auto-graded quizzes are immediately viewable when the instructor
        # enables mark visibility. Manual-review quizzes remain hidden until
        # an instructor has reviewed them.
        if result.get("grading_status") not in ("AUTO_GRADED", "REVIEWED", "RELEASED") or (
            int(result.get("long_text_count") or 0) and result.get("grading_status") == "AUTO_GRADED"
        ):
            raise PermissionDeniedError("Quiz marks are pending instructor review.")

        return {
            "attempt_id": result["attempt_id"],
            "attempt_no": result["attempt_no"],
            "quiz_id": result["quiz_id"],
            "quiz_title": result["quiz_title"],
            "component_id": result["component_id"],
            "component_name": result["component_name"],
            "offering_id": result["offering_id"],
            "submitted_at": result["submitted_at"],
            "max_marks": result["max_marks"],
            "grading_id": result["grading_id"],
            "mark_id": None,  # No single STUDENT_MARK row belongs to this attempt.
            "marks_obtained": result["final_marks"],
            "recorded_at": result["graded_at"],
            "mark_scope": "QUIZ_ATTEMPT_FINAL_MARK",
        }

    @staticmethod
    def retry_auto_grading(user_id, instructor_id, user_role, attempt_id):
        require_role(user_role, [Roles.INSTRUCTOR, Roles.ADMIN])
        validate_positive_integer(attempt_id, "attempt_id")

        attempt = get_attempt(int(attempt_id))
        if not attempt:
            raise NotFoundError("Quiz attempt not found.")
        if attempt["submitted_at"] is None:
            raise BusinessRuleError("Only successfully submitted attempts can be auto-graded.")

        quiz = get_quiz_context(int(attempt["quiz_id"]))
        if not quiz:
            raise NotFoundError("Quiz not found.")
        if user_role == Roles.INSTRUCTOR and not instructor_owns_offering(
            instructor_id, quiz["offering_id"]
        ):
            raise PermissionDeniedError("Instructor is not assigned to this quiz offering.")

        grading = auto_grade_attempt(
            int(attempt_id),
            recorder_user_id=int(user_id) if user_role == Roles.INSTRUCTOR else None,
        )
        return grading

    @staticmethod
    def instructor_grading_list(user_role, instructor_id, quiz_id):
        require_role(user_role, [Roles.INSTRUCTOR, Roles.ADMIN])
        quiz = get_quiz_context(int(quiz_id))
        if not quiz:
            raise NotFoundError("Quiz not found.")
        if user_role == Roles.INSTRUCTOR and not instructor_owns_offering(
            instructor_id, quiz["offering_id"]
        ):
            raise PermissionDeniedError("Instructor is not assigned to this quiz offering.")
        return list_quiz_gradings(int(quiz_id))

    @staticmethod
    def instructor_grading_detail(user_role, instructor_id, attempt_id):
        require_role(user_role, [Roles.INSTRUCTOR, Roles.ADMIN])
        grading = get_grading_for_attempt(int(attempt_id))
        if not grading:
            raise NotFoundError("Automatic grading record not found.")
        quiz = get_quiz_context(int(grading["quiz_id"]))
        if user_role == Roles.INSTRUCTOR and not instructor_owns_offering(
            instructor_id, quiz["offering_id"]
        ):
            raise PermissionDeniedError("Instructor is not assigned to this quiz offering.")
        return {
            "grading": grading,
            "question_grades": get_question_grades(int(grading["grading_id"])),
        }

    @staticmethod
    @atomic_oracle
    def review_grading(
        user_id,
        instructor_id,
        user_role,
        attempt_id,
        final_marks=None,
        notes=None,
        question_reviews=None,
    ):
        require_role(user_role, [Roles.INSTRUCTOR, Roles.ADMIN])
        grading = get_grading_for_attempt(int(attempt_id))
        if not grading:
            raise NotFoundError("Automatic grading record not found.")
        quiz = get_quiz_context(int(grading["quiz_id"]))
        if user_role == Roles.INSTRUCTOR and not instructor_owns_offering(
            instructor_id, quiz["offering_id"]
        ):
            raise PermissionDeniedError("Instructor is not assigned to this quiz offering.")

        if grading.get("grading_status") not in ("AUTO_GRADED", "REVIEWED"):
            raise BusinessRuleError("This grading record is not open for review.")
        grades = get_question_grades(int(grading["grading_id"]))
        long_text = {int(g["question_id"]): g for g in grades if g["question_type"] == "LONG_TEXT"}
        if question_reviews is None:
            question_reviews = []
        if not isinstance(question_reviews, list):
            raise ValidationError("question_reviews must be a list.")
        new_scores = {int(g["question_id"]): Decimal(str(g["marks_awarded"])) for g in grades}
        updated = set()
        for item in question_reviews:
            if not isinstance(item, dict):
                raise ValidationError("Each question review must be an object.")
            try:
                qid = int(item["question_id"])
                marks = Decimal(str(item["marks_awarded"]))
            except (KeyError, TypeError, ValueError, InvalidOperation) as exc:
                raise ValidationError("Invalid question review marks or question ID.") from exc
            if qid not in long_text or qid in updated:
                raise ValidationError("Each long-text question may be reviewed once.")
            if not marks.is_finite() or marks < 0 or marks > Decimal(str(long_text[qid]["max_marks"])):
                raise ValidationError("Long-text marks must be within the question maximum.")
            feedback = str(item.get("feedback") or "").strip()
            if not feedback or len(feedback) > 1000:
                raise ValidationError("Provide up to 1000 characters of rubric feedback per long-text answer.")
            updated.add(qid)
            new_scores[qid] = marks
        if long_text and set(long_text) != updated:
            raise ValidationError("Every long-text question needs marks and rubric feedback before review.")
        computed_total = sum(new_scores.values(), Decimal("0"))
        if not computed_total.is_finite() or computed_total > Decimal(str(grading["max_marks"])):
            raise ValidationError("Question-level marks exceed the quiz maximum.")
        # With no manual questions, the grade is fixed by the automatic grader.
        # A changed total without corresponding question grades is inconsistent.
        if final_marks is not None and abs(Decimal(str(final_marks)) - computed_total) > Decimal("0.011"):
            raise ValidationError("Final marks must equal the sum of question-level marks.")
        final_marks = float(computed_total)

        enrollment = get_enrollment_context_for_quiz_attempt(int(attempt_id))
        if not enrollment:
            raise BusinessRuleError("Quiz enrollment not found.")
        from .auto_grader import lock_quiz_enrollment
        lock_quiz_enrollment(int(enrollment["enrollment_id"]))

        for item in question_reviews:
            qid = int(item["question_id"])
            mark = new_scores[qid]
            changed_row = set_question_grade(
                int(grading["grading_id"]), qid, mark,
                "Y" if mark == Decimal(str(long_text[qid]["max_marks"])) else "N",
                str(item["feedback"]).strip(),
            )
            if changed_row != 1:
                raise BusinessRuleError("Unable to update the question's grading record.")

        changed = update_grading_review(
            int(grading["grading_id"]),
            final_marks,
            int(user_id),
            notes,
        )
        if changed == 0:
            raise BusinessRuleError("Only AUTO_GRADED attempts can be reviewed.")

        # The one STUDENT_MARK row represents the highest graded attempt.
        # Do not overwrite it blindly with the attempt just reviewed.
        synchronize_quiz_component_mark(
            int(grading["component_id"]),
            int(enrollment["enrollment_id"]),
            int(grading["quiz_id"]),
            int(grading["student_id"]),
            int(user_id),
        )
        return {"message": "Question-level review and final mark stored atomically.", "final_marks": final_marks}

    @staticmethod
    def release_grading(
        user_id,
        instructor_id,
        user_role,
        attempt_id,
    ):
        require_role(user_role, [Roles.INSTRUCTOR, Roles.ADMIN])
        grading = get_grading_for_attempt(int(attempt_id))
        if not grading:
            raise NotFoundError("Automatic grading record not found.")
        quiz = get_quiz_context(int(grading["quiz_id"]))
        if user_role == Roles.INSTRUCTOR and not instructor_owns_offering(
            instructor_id, quiz["offering_id"]
        ):
            raise PermissionDeniedError("Instructor is not assigned to this quiz offering.")

        changed = release_grading(int(grading["grading_id"]))
        if changed == 0:
            raise BusinessRuleError("Review the automatic grade before releasing it.")

        return {"message": "Quiz marks released. Student visibility still follows the quiz mark-view control."}

    @staticmethod
    def student_attempts(student_id, user_role):
        require_role(user_role, [Roles.STUDENT])
        rows = list_student_quiz_attempts(int(student_id))
        attempts = []
        for row in rows:
            allow_marks = str(row.get("allow_mark_view", "N")).upper() == "Y"
            status = row.get("grading_status")
            marks_available = allow_marks and status in ("AUTO_GRADED", "REVIEWED", "RELEASED") and not (
                status == "AUTO_GRADED" and int(row.get("long_text_count") or 0) > 0
            )
            attempts.append({
                "attempt_id": row["attempt_id"],
                "quiz_id": row["quiz_id"],
                "attempt_no": row["attempt_no"],
                "quiz_title": row["quiz_title"],
                "component_id": row["component_id"],
                "component_name": row["component_name"],
                "component_max_marks": row["component_max_marks"],
                "quiz_max_marks": row["quiz_max_marks"],
                "course_code": row["course_code"],
                "course_name": row["course_name"],
                "offering_id": row["offering_id"],
                "started_at": row["started_at"],
                "submitted_at": row["submitted_at"],
                "grading_status": status,
                "marks_visible": marks_available,
                "marks_obtained": row["final_marks"] if marks_available else None,
                "max_marks": row["quiz_max_marks"] if marks_available else None,
                "answer_review_visible": (
                    str(row.get("allow_answer_review", "N")).upper() == "Y"
                    and bool(row.get("review_allowed")) and marks_available
                ),
            })
        return {"attempts": attempts}

    @staticmethod
    def attempt_review(student_id, user_role, attempt_id):
        require_role(user_role, [Roles.STUDENT])
        validate_positive_integer(attempt_id, "attempt_id")
        attempt_id = int(attempt_id)

        context = get_attempt_result_context(attempt_id)
        if not context:
            raise NotFoundError("Quiz attempt not found.")
        if int(context["student_id"]) != int(student_id):
            raise PermissionDeniedError(
                "This quiz attempt belongs to another student."
            )
        if context["submitted_at"] is None:
            raise BusinessRuleError(
                "Quiz review is available only after the attempt is submitted."
            )
        # Review includes per-question marks and correctness. Never expose it
        # while the separate mark-publication control is disabled.
        if context.get("allow_mark_view") != "Y":
            raise PermissionDeniedError("Quiz marks are not currently visible.")
        if context["allow_answer_review"] != "Y" or not context.get("review_allowed"):
            raise PermissionDeniedError(
                "Answer keys are hidden until all attempts are used or the quiz closes."
            )
        if context.get("grading_status") not in ("REVIEWED", "RELEASED") and (
            int(context.get("long_text_count") or 0) or context.get("grading_status") != "AUTO_GRADED"
        ):
            raise PermissionDeniedError("Quiz answers are pending instructor review.")

        question_rows = get_attempt_review_questions(attempt_id)
        grading = get_grading_for_attempt(attempt_id)
        grade_rows = (
            {int(row["question_id"]): row for row in get_question_grades(int(grading["grading_id"]))}
            if grading
            else {}
        )
        questions = []

        for row in question_rows:
            qid = int(row["question_id"])
            qtype = str(row["question_type"]).upper()
            selected_rows = get_selected_options(row.get("response_id"))
            selected_ids = {int(x["option_id"]) for x in selected_rows}
            options = []

            for option in get_question_options(qid, include_correct=True):
                option_data = dict(option)
                option_data["is_selected"] = int(option["option_id"]) in selected_ids
                options.append(option_data)

            correct_answer = None
            if qtype in ("MCQ_SINGLE", "MCQ_MULTI", "TRUE_FALSE"):
                correct_options = [o for o in options if str(o.get("is_correct", "N")).upper() == "Y"]
                correct_answer = {
                    "type": "options",
                    "options": [
                        {"option_id": int(o["option_id"]), "option_text": o["option_text"]}
                        for o in correct_options
                    ],
                }
            elif qtype == "ORDERING":
                correct_answer = {
                    "type": "ordering",
                    "options": [
                        {"position": index + 1, "option_id": int(o["option_id"]), "option_text": o["option_text"]}
                        for index, o in enumerate(sorted(options, key=lambda x: (int(x["option_order"]), int(x["option_id"]))))
                    ],
                }
            elif qtype == "MATCHING":
                left = {str(o.get("match_key")): o for o in options if str(o.get("match_side", "")).upper() == "L"}
                right = {str(o.get("match_key")): o for o in options if str(o.get("match_side", "")).upper() == "R"}
                correct_answer = {
                    "type": "matching",
                    "pairs": [
                        {
                            "left_option_id": int(left[key]["option_id"]),
                            "left_option_text": left[key]["option_text"],
                            "right_option_id": int(right[key]["option_id"]),
                            "right_option_text": right[key]["option_text"],
                        }
                        for key in sorted(set(left) & set(right))
                    ],
                }
            elif qtype == "NUMERICAL":
                rule = get_numeric_rule(qid)
                correct_answer = {
                    "type": "numerical",
                    "expected_value": rule["expected_value"] if rule else None,
                    "tolerance": rule["tolerance"] if rule else None,
                }
            elif qtype in ("SHORT_TEXT", "FILL_BLANK"):
                keywords = sorted(get_keywords(qid), key=lambda x: int(x["keyword_order"]))
                correct_answer = {
                    "type": "text",
                    "keywords": [
                        {"order": int(k["keyword_order"]), "text": k["keyword_text"]}
                        for k in keywords
                    ],
                }

            response_order = get_response_order_items(row.get("response_id"))
            response_matches = get_response_match_items(row.get("response_id"))
            grade = grade_rows.get(qid)

            questions.append(
                {
                    "question_id": qid,
                    "question_order": row["question_order"],
                    "question_marks": row["question_marks"],
                    "question_text": row["question_text"],
                    "question_type": qtype,
                    "response_id": row["response_id"],
                    "response_text": row["response_text"],
                    "options": options,
                    "response_order": response_order,
                    "response_matches": response_matches,
                    "correct_answer": correct_answer,
                    "marks_awarded": grade["marks_awarded"] if grade else None,
                    "is_correct": grade["is_correct"] if grade else None,
                    "grading_note": grade["grading_note"] if grade else None,
                }
            )

        return {
            "attempt_id": context["attempt_id"],
            "attempt_no": context["attempt_no"],
            "quiz_id": context["quiz_id"],
            "quiz_title": context["quiz_title"],
            "submitted_at": context["submitted_at"],
            "question_count": len(questions),
            "grading_status": context.get("grading_status"),
            "questions": questions,
        }
