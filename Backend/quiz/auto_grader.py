"""
EduSphere V7 automatic quiz grading.

The grading rules are unchanged. Data loading is batched to remove the
original N+1 query pattern.
"""

from decimal import Decimal, InvalidOperation
import json
import re

from database.query import fetch_all, fetch_one, execute, execute_procedure, execute_many
from database.connection import atomic_oracle
from database.schema import object_name


def _d(value):
    return Decimal(str(value))


def _normalize(text):
    return re.sub(r"\s+", " ", str(text or "").strip().casefold())


def _score_question(question, response, selected_ids, order_items, match_items):
    qtype = question["question_type"]
    max_marks = _d(question["question_marks"])
    selected = {int(x) for x in selected_ids}

    options = question.get("options", [])
    correct = {
        int(o["option_id"])
        for o in options
        if o.get("is_correct") == "Y"
    }

    if qtype in ("MCQ_SINGLE", "TRUE_FALSE", "MCQ_MULTI"):
        # An empty key must never make an empty student response 'correct'.
        # Single-choice and True/False have exactly one keyed correct option.
        if (qtype in ("MCQ_SINGLE", "TRUE_FALSE") and len(correct) != 1) or (qtype == "MCQ_MULTI" and not correct):
            return Decimal("0"), False, "Question has no valid configured correct-option key."
        ok = selected == correct
        return max_marks if ok else Decimal("0"), ok, (
            "Exact option-set match." if ok else
            "Selected option set differs from instructor answer."
        )

    if qtype == "ORDERING":
        expected = [
            int(o["option_id"])
            for o in sorted(
                options,
                key=lambda x: (int(x["option_order"]), int(x["option_id"]))
            )
        ]
        submitted = [
            int(x["option_id"])
            for x in sorted(order_items, key=lambda x: int(x["position_order"]))
        ]
        if not expected:
            return Decimal("0"), False, "No ordering options configured."
        if len(submitted) != len(expected):
            return Decimal("0"), False, "Submitted sequence is incomplete."
        correct_positions = sum(
            a == b for a, b in zip(expected, submitted)
        )
        awarded = (
            max_marks * Decimal(correct_positions) / Decimal(len(expected))
        ).quantize(Decimal("0.01"))
        return (
            awarded,
            awarded == max_marks,
            f"{correct_positions}/{len(expected)} sequence positions correct.",
        )

    if qtype == "MATCHING":
        pairs = question.get("matching_pairs", [])
        if not pairs:
            return Decimal("0"), False, "No matching pairs configured."

        expected_pairs = {
            (int(p["left_option_id"]), int(p["right_option_id"]))
            for p in pairs
        }
        submitted_pairs = [
            (int(x["left_option_id"]), int(x["right_option_id"]))
            for x in match_items
        ]

        # MATCHING is all-or-nothing. Every bipartite association must be
        # correct and there may be no missing, extra, or duplicate pairs.
        if len(submitted_pairs) != len(set(submitted_pairs)):
            return Decimal("0"), False, "Duplicate matching pairs submitted."

        submitted_pair_set = set(submitted_pairs)
        ok = (
            len(submitted_pairs) == len(expected_pairs)
            and submitted_pair_set == expected_pairs
        )
        return (
            max_marks if ok else Decimal("0"),
            ok,
            "All matching pairs are correct."
            if ok
            else "Submitted matching pairs do not exactly match the instructor answer.",
        )

    if qtype == "NUMERICAL":
        rule = question.get("numeric_rule")
        if not rule:
            return Decimal("0"), False, "No numerical grading rule configured."
        try:
            answer = _d(response.get("response_text"))
            expected = _d(rule["expected_value"])
            tolerance = _d(rule["tolerance"])
        except (InvalidOperation, TypeError, ValueError):
            return Decimal("0"), False, "Response is not a valid number."
        ok = abs(answer - expected) <= tolerance
        return max_marks if ok else Decimal("0"), ok, (
            f"Expected {expected} ± {tolerance}."
            if not ok else "Numerical answer is within tolerance."
        )

    if qtype == "SHORT_TEXT":
        keywords = question.get("keywords", [])
        text = _normalize(response.get("response_text"))
        if not keywords:
            return Decimal("0"), False, "No accepted keywords configured."

        accepted = {
            _normalize(row["keyword_text"])
            for row in keywords
            if _normalize(row.get("keyword_text"))
        }
        ok = text in accepted
        return (
            max_marks if ok else Decimal("0"),
            ok,
            "Response exactly matches an accepted keyword."
            if ok
            else "Response does not exactly match any accepted keyword.",
        )

    if qtype == "FILL_BLANK":
        keywords = sorted(
            question.get("keywords", []),
            key=lambda x: int(x["keyword_order"]),
        )
        if not keywords:
            return Decimal("0"), False, "No blank answer keys configured."

        raw_response = response.get("response_text")
        try:
            submitted = json.loads(raw_response)
        except (TypeError, json.JSONDecodeError):
            return (
                Decimal("0"),
                False,
                "FILL_BLANK response is not a valid ordered answer list.",
            )

        if not isinstance(submitted, list):
            return (
                Decimal("0"),
                False,
                "FILL_BLANK response must be an ordered answer list.",
            )

        if len(submitted) != len(keywords):
            return (
                Decimal("0"),
                False,
                "Number of submitted blanks does not match the answer key.",
            )

        for position, (answer, key) in enumerate(
            zip(submitted, keywords),
            start=1,
        ):
            if not isinstance(answer, str):
                return (
                    Decimal("0"),
                    False,
                    f"Blank {position} must contain a text answer.",
                )
            if _normalize(answer) != _normalize(key["keyword_text"]):
                return (
                    Decimal("0"),
                    False,
                    f"Blank {position} does not match the correct answer.",
                )

        return max_marks, True, "All blanks match their ordered answers."

    return Decimal("0"), False, "This question type requires instructor grading."


def _in_clause(values):
    values = [int(v) for v in values]
    return ",".join("?" for _ in values), tuple(values)


def load_attempt_for_grading(attempt_id):
    return fetch_one(
        f"""
        SELECT
            qa.ATTEMPT_ID,
            qa.QUIZ_ID,
            qa.STUDENT_ID,
            qa.SUBMITTED_AT,
            q.COMPONENT_ID,
            ac.MAX_MARKS AS COMPONENT_MAX_MARKS,
            e.ENROLLMENT_ID,
            gs.OFFERING_ID
        FROM {object_name("QUIZ_ATTEMPT")} qa
        JOIN {object_name("QUIZ")} q ON q.QUIZ_ID=qa.QUIZ_ID
        JOIN {object_name("ASSESSMENT_COMPONENT")} ac
          ON ac.COMPONENT_ID=q.COMPONENT_ID
        JOIN {object_name("GRADING_SCHEME")} gs
          ON gs.SCHEME_ID=ac.SCHEME_ID
        LEFT JOIN {object_name("ENROLLMENT")} e
          ON e.STUDENT_ID=qa.STUDENT_ID
         AND e.OFFERING_ID=gs.OFFERING_ID
         AND e.ENROLLMENT_STATUS IN ('ENROLLED','COMPLETED')
        WHERE qa.ATTEMPT_ID=?
        """,
        (attempt_id,),
    )


def load_recorder_user_id(quiz_id, offering_id, preferred_user_id=None):
    """Resolve an instructor user allowed to record the quiz component mark.

    Do not use ACTIVITY_LOG text matching here.  Some Oracle/ODBC combinations
    can fail while decoding ACTIVITY_DESCRIPTION, which used to abort grading
    after the student attempt had already been submitted.
    """
    if preferred_user_id is not None:
        row = fetch_one(
            f"""
            SELECT u.USER_ID
            FROM {object_name("LMS_USER")} u
            JOIN {object_name("INSTRUCTOR")} i
              ON i.USER_ID=u.USER_ID
            JOIN {object_name("OFFERING_INSTRUCTOR")} oi
              ON oi.INSTRUCTOR_ID=i.INSTRUCTOR_ID
             AND oi.OFFERING_ID=?
            WHERE u.USER_ID=?
              AND u.ROLE='INSTRUCTOR'
              AND u.ACCOUNT_STATUS='ACTIVE'
            FETCH FIRST 1 ROW ONLY
            """,
            (offering_id, preferred_user_id),
        )
        if row is not None:
            return row["user_id"]

    row = fetch_one(
        f"""
        SELECT u.USER_ID
        FROM {object_name("LMS_USER")} u
        JOIN {object_name("INSTRUCTOR")} i
          ON i.USER_ID=u.USER_ID
        JOIN {object_name("OFFERING_INSTRUCTOR")} oi
          ON oi.INSTRUCTOR_ID=i.INSTRUCTOR_ID
         AND oi.OFFERING_ID=?
        WHERE u.ROLE='INSTRUCTOR'
          AND u.ACCOUNT_STATUS='ACTIVE'
        ORDER BY u.USER_ID
        FETCH FIRST 1 ROW ONLY
        """,
        (offering_id,),
    )
    if row is None:
        return None
    return row["user_id"]

def load_questions(attempt_id):
    question_rows = fetch_all(
        f"""
        SELECT
            qq.QUESTION_ID,
            qq.QUESTION_ORDER,
            qq.QUESTION_MARKS,
            q.QUESTION_TEXT,
            q.QUESTION_TYPE
        FROM {object_name("QUIZ_ATTEMPT")} qa
        JOIN {object_name("QUIZ_QUESTION")} qq ON qq.QUIZ_ID=qa.QUIZ_ID
        JOIN {object_name("QUESTION")} q ON q.QUESTION_ID=qq.QUESTION_ID
        WHERE qa.ATTEMPT_ID=?
        ORDER BY qq.QUESTION_ORDER, qq.QUESTION_ID
        """,
        (attempt_id,),
    )

    if not question_rows:
        return []

    question_ids = [int(row["question_id"]) for row in question_rows]
    marks, params = _in_clause(question_ids)

    options = fetch_all(
        f"""
        SELECT OPTION_ID, QUESTION_ID, OPTION_TEXT, IS_CORRECT, OPTION_ORDER,
               TO_CHAR(MATCH_SIDE) AS MATCH_SIDE,
               TO_CHAR(MATCH_KEY) AS MATCH_KEY
        FROM {object_name("QUESTION_OPTION")}
        WHERE QUESTION_ID IN ({marks})
        ORDER BY QUESTION_ID, OPTION_ORDER, OPTION_ID
        """,
        params,
    )
    numeric_rules = fetch_all(
        f"""
        SELECT QUESTION_ID, EXPECTED_VALUE, TOLERANCE
        FROM {object_name("QUESTION_NUMERIC_RULE")}
        WHERE QUESTION_ID IN ({marks})
        """,
        params,
    )
    keywords = fetch_all(
        f"""
        SELECT QUESTION_ID, KEYWORD_ORDER, KEYWORD_TEXT
        FROM {object_name("QUESTION_KEYWORD")}
        WHERE QUESTION_ID IN ({marks})
        ORDER BY QUESTION_ID, KEYWORD_ORDER
        """,
        params,
    )
    matching_pairs = fetch_all(
        f"""
        SELECT
            l.QUESTION_ID,
            l.OPTION_ID AS LEFT_OPTION_ID,
            r.OPTION_ID AS RIGHT_OPTION_ID
        FROM {object_name("QUESTION_OPTION")} l
        JOIN {object_name("QUESTION_OPTION")} r
          ON r.QUESTION_ID=l.QUESTION_ID
         AND r.MATCH_SIDE='R'
         AND r.MATCH_KEY=l.MATCH_KEY
        WHERE l.QUESTION_ID IN ({marks})
          AND l.MATCH_SIDE='L'
        ORDER BY l.QUESTION_ID, l.OPTION_ORDER
        """,
        params,
    )

    by_q = {}
    for row in question_rows:
        q = dict(row)
        q["options"] = []
        q["numeric_rule"] = None
        q["keywords"] = []
        q["matching_pairs"] = []
        by_q[int(row["question_id"])] = q

    for row in options:
        by_q[int(row["question_id"])]["options"].append(dict(row))
    for row in numeric_rules:
        by_q[int(row["question_id"])]["numeric_rule"] = dict(row)
    for row in keywords:
        by_q[int(row["question_id"])]["keywords"].append(dict(row))
    for row in matching_pairs:
        by_q[int(row["question_id"])]["matching_pairs"].append(dict(row))

    return [by_q[qid] for qid in question_ids]


def load_responses(attempt_id):
    rows = fetch_all(
        f"""
        SELECT RESPONSE_ID, QUESTION_ID, RESPONSE_TEXT
        FROM {object_name("QUIZ_RESPONSE")}
        WHERE ATTEMPT_ID=?
        """,
        (attempt_id,),
    )
    if not rows:
        return {}

    response_ids = [int(row["response_id"]) for row in rows]
    marks, params = _in_clause(response_ids)

    selected_rows = fetch_all(
        f"""
        SELECT RESPONSE_ID, OPTION_ID
        FROM {object_name("QUIZ_RESPONSE_OPTION")}
        WHERE RESPONSE_ID IN ({marks})
        ORDER BY RESPONSE_ID, OPTION_ID
        """,
        params,
    )
    order_rows = fetch_all(
        f"""
        SELECT RESPONSE_ID, POSITION_ORDER, OPTION_ID
        FROM {object_name("QUIZ_RESPONSE_ORDER")}
        WHERE RESPONSE_ID IN ({marks})
        ORDER BY RESPONSE_ID, POSITION_ORDER
        """,
        params,
    )
    match_rows = fetch_all(
        f"""
        SELECT RESPONSE_ID, LEFT_OPTION_ID, RIGHT_OPTION_ID
        FROM {object_name("QUIZ_RESPONSE_MATCH")}
        WHERE RESPONSE_ID IN ({marks})
        ORDER BY RESPONSE_ID, LEFT_OPTION_ID
        """,
        params,
    )

    out = {}
    by_response = {int(row["response_id"]): row for row in rows}
    for row in rows:
        response_id = int(row["response_id"])
        out[int(row["question_id"])] = {
            "response_id": response_id,
            "response_text": row["response_text"],
            "selected_ids": [],
            "order_items": [],
            "match_items": [],
        }

    for row in selected_rows:
        response = by_response[int(row["response_id"])]
        out[int(response["question_id"])]["selected_ids"].append(
            int(row["option_id"])
        )
    for row in order_rows:
        response = by_response[int(row["response_id"])]
        out[int(response["question_id"])]["order_items"].append(dict(row))
    for row in match_rows:
        response = by_response[int(row["response_id"])]
        out[int(response["question_id"])]["match_items"].append(dict(row))

    return out


def lock_quiz_enrollment(enrollment_id):
    """Serialize updates to the shared STUDENT_MARK for a student/offering.

    Both automatic grading and instructor review lock the same existing row;
    no new table or column is required.
    """
    row = fetch_one(
        f"SELECT ENROLLMENT_ID FROM {object_name('ENROLLMENT')} WHERE ENROLLMENT_ID=? FOR UPDATE",
        (int(enrollment_id),),
    )
    if row is None:
        raise ValueError("Quiz enrollment not found.")


def synchronize_quiz_component_mark(component_id, enrollment_id, quiz_id, student_id, recorder_user_id):
    """One component row = BEST completed/graded attempt (tie: latest).

    The attempt-level QUIZ_GRADING rows retain independent scores. This function
    must run after lock_quiz_enrollment and inside atomic_oracle.
    """
    best = fetch_one(
        f"""
        SELECT qg.FINAL_MARKS, qg.REVIEWED_BY_USER_ID
        FROM {object_name('QUIZ_GRADING')} qg
        JOIN {object_name('QUIZ_ATTEMPT')} qa ON qa.ATTEMPT_ID=qg.ATTEMPT_ID
        WHERE qa.QUIZ_ID=? AND qa.STUDENT_ID=?
          AND qa.SUBMITTED_AT IS NOT NULL
          AND qg.GRADING_STATUS IN ('AUTO_GRADED','REVIEWED','RELEASED')
          AND (qg.GRADING_STATUS <> 'AUTO_GRADED' OR NOT EXISTS (
              SELECT 1 FROM {object_name('QUIZ_QUESTION')} qq
              JOIN {object_name('QUESTION')} qn ON qn.QUESTION_ID=qq.QUESTION_ID
              WHERE qq.QUIZ_ID=qa.QUIZ_ID AND qn.QUESTION_TYPE='LONG_TEXT'
          ))
        ORDER BY qg.FINAL_MARKS DESC, qa.ATTEMPT_NO DESC, qa.ATTEMPT_ID DESC
        FETCH FIRST 1 ROW ONLY
        """,
        (int(quiz_id), int(student_id)),
    )
    if best is None:
        return None
    # Attribute reviewed grades to their actual reviewer when available.
    marker = best.get("reviewed_by_user_id") or recorder_user_id
    if marker is None:
        raise ValueError("An authorized instructor is required to record quiz marks.")
    execute_procedure(
        object_name("PR_RECORD_MARK"),
        (int(component_id), int(enrollment_id), float(best["final_marks"]), int(marker), None),
    )
    return best["final_marks"]


@atomic_oracle
def auto_grade_attempt(attempt_id, recorder_user_id=None):
    attempt = load_attempt_for_grading(attempt_id)
    if not attempt:
        raise ValueError("Quiz attempt not found.")

    # Lock before reading/writing grading state. Concurrent attempts and
    # reviews for this enrollment cannot overwrite a higher component mark.
    if attempt.get("enrollment_id") is None:
        raise ValueError("No active quiz enrollment found for the student.")
    lock_quiz_enrollment(int(attempt["enrollment_id"]))

    attempt["recorder_user_id"] = load_recorder_user_id(
        int(attempt["quiz_id"]),
        int(attempt["offering_id"]),
        recorder_user_id,
    )
    if attempt["recorder_user_id"] is None:
        raise ValueError("No active instructor is assigned to this quiz offering for mark recording.")

    if attempt["submitted_at"] is None:
        raise ValueError("Quiz must be submitted before grading.")

    questions = load_questions(attempt_id)
    responses = load_responses(attempt_id)

    details = []
    total = Decimal("0")
    max_total = Decimal("0")

    for q in questions:
        response = responses.get(
            int(q["question_id"]),
            {
                "response_text": None,
                "selected_ids": [],
                "order_items": [],
                "match_items": [],
            },
        )
        awarded, correct, note = _score_question(
            q,
            response,
            response["selected_ids"],
            response["order_items"],
            response["match_items"],
        )
        max_marks = _d(q["question_marks"])
        total += awarded
        max_total += max_marks
        details.append((q, awarded, correct, note))

    if max_total <= 0:
        raise ValueError("Cannot grade a quiz with no configured questions.")

    existing = fetch_one(
        f"""
        SELECT GRADING_ID, GRADING_STATUS
        FROM {object_name("QUIZ_GRADING")}
        WHERE ATTEMPT_ID=?
        """,
        (attempt_id,),
    )

    if existing and existing["grading_status"] in ("REVIEWED", "RELEASED"):
        # Never replace instructor-reviewed marks with a later auto-grade.
        synchronize_quiz_component_mark(
            attempt["component_id"], attempt["enrollment_id"],
            attempt["quiz_id"], attempt["student_id"], attempt["recorder_user_id"],
        )
        return {
            "grading_id": existing["grading_id"],
            "status": existing["grading_status"],
            "auto_marks": total,
            "max_marks": max_total,
            "locked": True,
        }

    if existing:
        grading_id = int(existing["grading_id"])
        execute(
            f"""
            UPDATE {object_name("QUIZ_GRADING")}
            SET AUTO_MARKS=?, FINAL_MARKS=?, MAX_MARKS=?,
                GRADING_STATUS='AUTO_GRADED',
                AUTO_GRADED_AT=SYSTIMESTAMP
            WHERE GRADING_ID=?
            """,
            (float(total), float(total), float(max_total), grading_id),
        )
        execute(
            f"DELETE FROM {object_name('QUIZ_QUESTION_GRADE')} WHERE GRADING_ID=?",
            (grading_id,),
        )
    else:
        execute(
            f"""
            INSERT INTO {object_name("QUIZ_GRADING")}
            (ATTEMPT_ID, AUTO_MARKS, FINAL_MARKS, MAX_MARKS,
             GRADING_STATUS, AUTO_GRADED_AT)
            VALUES (?, ?, ?, ?, 'AUTO_GRADED', SYSTIMESTAMP)
            """,
            (attempt_id, float(total), float(total), float(max_total)),
        )
        row = fetch_one(
            f"""
            SELECT GRADING_ID
            FROM {object_name('QUIZ_GRADING')}
            WHERE ATTEMPT_ID=?
            """,
            (attempt_id,),
        )
        grading_id = int(row["grading_id"])

    if details:
        execute_many(
            f"""
            INSERT INTO {object_name("QUIZ_QUESTION_GRADE")}
            (GRADING_ID, QUESTION_ID, MARKS_AWARDED, MAX_MARKS,
             IS_CORRECT, GRADING_NOTE)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    grading_id,
                    int(q["question_id"]),
                    float(awarded),
                    float(q["question_marks"]),
                    "Y" if correct else "N",
                    note,
                )
                for q, awarded, correct, note in details
            ],
        )

    # All three writes (grading header, question grades, component mark)
    # commit together. A failure anywhere rolls all of them back.
    synchronize_quiz_component_mark(
        attempt["component_id"], attempt["enrollment_id"],
        attempt["quiz_id"], attempt["student_id"], attempt["recorder_user_id"],
    )

    return {
        "grading_id": grading_id,
        "status": "AUTO_GRADED",
        "auto_marks": total,
        "final_marks": total,
        "max_marks": max_total,
        "question_count": len(details),
    }
