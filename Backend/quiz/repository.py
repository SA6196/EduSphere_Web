"""
EduSphere LMS

Quiz Repository Layer

Handles quiz authoring, delivery, attempts, responses and V6 result/review reads.
"""

from database.query import fetch_one, fetch_all, execute
from database.schema import object_name


# =====================================================
# QUIZ
# =====================================================

def create_quiz(
    component_id,
    quiz_title,
    open_at,
    close_at,
    duration_minutes,
    max_attempts,
):
    return execute(
        f"""
        INSERT INTO {object_name("QUIZ")}
        (
            COMPONENT_ID,
            QUIZ_TITLE,
            OPEN_AT,
            CLOSE_AT,
            DURATION_MINUTES,
            MAX_ATTEMPTS
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            component_id,
            quiz_title,
            open_at,
            close_at,
            duration_minutes,
            max_attempts,
        ),
    )


def get_quiz(quiz_id):
    return fetch_one(
        f"""
        SELECT
            QUIZ_ID,
            COMPONENT_ID,
            QUIZ_TITLE,
            OPEN_AT,
            CLOSE_AT,
            DURATION_MINUTES,
            MAX_ATTEMPTS,
            ALLOW_MARK_VIEW,
            ALLOW_ANSWER_REVIEW
        FROM {object_name("QUIZ")}
        WHERE QUIZ_ID=?
        """,
        (quiz_id,),
    )


def get_quiz_context(quiz_id):
    return fetch_one(
        f"""
        SELECT
            q.QUIZ_ID,
            q.COMPONENT_ID,
            q.QUIZ_TITLE,
            q.OPEN_AT,
            q.CLOSE_AT,
            q.DURATION_MINUTES,
            q.MAX_ATTEMPTS,
            q.ALLOW_MARK_VIEW,
            q.ALLOW_ANSWER_REVIEW,
            ac.COMPONENT_NAME,
            ac.MAX_MARKS,
            gs.OFFERING_ID,
            co.SECTION_CODE,
            c.COURSE_CODE,
            c.COURSE_NAME
        FROM {object_name("QUIZ")} q
        JOIN {object_name("ASSESSMENT_COMPONENT")} ac
          ON ac.COMPONENT_ID=q.COMPONENT_ID
        JOIN {object_name("GRADING_SCHEME")} gs
          ON gs.SCHEME_ID=ac.SCHEME_ID
        JOIN {object_name("COURSE_OFFERING")} co
          ON co.OFFERING_ID=gs.OFFERING_ID
        JOIN {object_name("COURSE")} c
          ON c.COURSE_ID=co.COURSE_ID
        WHERE q.QUIZ_ID=?
        """,
        (quiz_id,),
    )


def get_quizzes(component_id):
    return fetch_all(
        f"""
        SELECT
            QUIZ_ID,
            COMPONENT_ID,
            QUIZ_TITLE,
            OPEN_AT,
            CLOSE_AT,
            DURATION_MINUTES,
            MAX_ATTEMPTS,
            ALLOW_MARK_VIEW,
            ALLOW_ANSWER_REVIEW
        FROM {object_name("QUIZ")}
        WHERE COMPONENT_ID=?
        ORDER BY QUIZ_ID
        """,
        (component_id,),
    )


def update_quiz_visibility(quiz_id, allow_mark_view, allow_answer_review):
    return execute(
        f"""
        UPDATE {object_name("QUIZ")}
        SET
            ALLOW_MARK_VIEW=?,
            ALLOW_ANSWER_REVIEW=?
        WHERE QUIZ_ID=?
        """,
        (allow_mark_view, allow_answer_review, quiz_id),
    )


def quiz_exists_for_component(component_id):
    row = fetch_one(
        f"""
        SELECT QUIZ_ID
        FROM {object_name("QUIZ")}
        WHERE COMPONENT_ID=?
        """,
        (component_id,),
    )
    return row is not None


# =====================================================
# QUESTIONS / QUESTION BANK
# =====================================================

def get_question_by_text_type(question_text, question_type):
    return fetch_one(
        f"""
        SELECT QUESTION_ID, QUESTION_TEXT, QUESTION_TYPE
        FROM {object_name("QUESTION")}
        WHERE QUESTION_TEXT=?
          AND QUESTION_TYPE=?
        ORDER BY QUESTION_ID DESC
        FETCH FIRST 1 ROW ONLY
        """,
        (question_text, question_type),
    )


def get_question(question_id):
    return fetch_one(
        f"""
        SELECT
            QUESTION_ID,
            QUESTION_TEXT,
            QUESTION_TYPE
        FROM {object_name("QUESTION")}
        WHERE QUESTION_ID=?
        """,
        (question_id,),
    )


def list_questions():
    return fetch_all(
        f"""
        SELECT
            q.QUESTION_ID,
            q.QUESTION_TEXT,
            q.QUESTION_TYPE,
            (
                SELECT COUNT(*)
                FROM {object_name("QUESTION_OPTION")} qo
                WHERE qo.QUESTION_ID=q.QUESTION_ID
            ) AS OPTION_COUNT
        FROM {object_name("QUESTION")} q
        ORDER BY q.QUESTION_ID
        """
    )


def list_questions_for_instructor(user_id, instructor_id):
    """Fetch only questions an instructor may READ, in one scoped Oracle query.

    Same read policy as question_access_for_instructor: author OR linked to
    an offering taught by the instructor. Editing still uses the stricter
    original authorization check and locks attempted questions.
    """
    return fetch_all(
        f"""
        SELECT q.QUESTION_ID, q.QUESTION_TEXT, q.QUESTION_TYPE,
               (SELECT COUNT(*) FROM {object_name('QUESTION_OPTION')} opt
                WHERE opt.QUESTION_ID=q.QUESTION_ID) AS OPTION_COUNT
        FROM {object_name('QUESTION')} q
        WHERE EXISTS (
            SELECT 1 FROM {object_name('ACTIVITY_LOG')} a
            WHERE a.USER_ID=?
              AND a.ACTIVITY_DESCRIPTION='QUESTION_ID=' || TO_CHAR(q.QUESTION_ID) || ';CREATED'
        ) OR EXISTS (
            SELECT 1 FROM {object_name('QUIZ_QUESTION')} qq
            JOIN {object_name('QUIZ')} quiz ON quiz.QUIZ_ID=qq.QUIZ_ID
            JOIN {object_name('ASSESSMENT_COMPONENT')} ac ON ac.COMPONENT_ID=quiz.COMPONENT_ID
            JOIN {object_name('GRADING_SCHEME')} gs ON gs.SCHEME_ID=ac.SCHEME_ID
            JOIN {object_name('OFFERING_INSTRUCTOR')} oi ON oi.OFFERING_ID=gs.OFFERING_ID
            WHERE qq.QUESTION_ID=q.QUESTION_ID AND oi.INSTRUCTOR_ID=?
        )
        ORDER BY q.QUESTION_ID
        """,
        (int(user_id or 0), int(instructor_id or 0)),
    )


def get_question_options(question_id, include_correct=True):
    """Return options without forcing V7 metadata through ODBC for legacy types.

    MATCH_SIDE/MATCH_KEY are only needed by MATCHING questions.  Keeping the
    legacy SELECT for other question types avoids an ODBC/Oracle driver
    decoding failure from taking down the instructor question-bank endpoint.
    """
    correct_column = (
        "qo.IS_CORRECT AS IS_CORRECT"
        if include_correct
        else "CAST(NULL AS CHAR(1)) AS IS_CORRECT"
    )
    question = fetch_one(
        f"""
        SELECT QUESTION_TYPE
        FROM {object_name("QUESTION")}
        WHERE QUESTION_ID=?
        """,
        (question_id,),
    )
    if not question:
        return []

    if str(question["question_type"]).upper() == "MATCHING":
        return fetch_all(
            f"""
            SELECT
                qo.OPTION_ID,
                qo.QUESTION_ID,
                qo.OPTION_TEXT,
                qo.OPTION_ORDER,
                TO_CHAR(qo.MATCH_SIDE) AS MATCH_SIDE,
                TO_CHAR(qo.MATCH_KEY) AS MATCH_KEY,
                {correct_column}
            FROM {object_name("QUESTION_OPTION")} qo
            WHERE qo.QUESTION_ID=?
            ORDER BY qo.OPTION_ORDER, qo.OPTION_ID
            """,
            (question_id,),
        )

    return fetch_all(
        f"""
        SELECT
            qo.OPTION_ID,
            qo.QUESTION_ID,
            qo.OPTION_TEXT,
            qo.OPTION_ORDER,
            {correct_column}
        FROM {object_name("QUESTION_OPTION")} qo
        WHERE qo.QUESTION_ID=?
        ORDER BY qo.OPTION_ORDER, qo.OPTION_ID
        """,
        (question_id,),
    )


def get_option(option_id):
    return fetch_one(
        f"""
        SELECT
            OPTION_ID,
            QUESTION_ID,
            OPTION_TEXT,
            IS_CORRECT,
            OPTION_ORDER
        FROM {object_name("QUESTION_OPTION")}
        WHERE OPTION_ID=?
        """,
        (option_id,),
    )


def create_question(question_text, question_type):
    return execute(
        f"""
        INSERT INTO {object_name("QUESTION")}
        (QUESTION_TEXT, QUESTION_TYPE)
        VALUES (?, ?)
        """,
        (question_text, question_type),
    )


def create_question_option(
    question_id,
    option_text,
    is_correct,
    option_order,
    match_side=None,
    match_key=None,
):
    return execute(
        f"""
        INSERT INTO {object_name("QUESTION_OPTION")}
        (QUESTION_ID, OPTION_TEXT, IS_CORRECT, OPTION_ORDER, MATCH_SIDE, MATCH_KEY)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (question_id, option_text, is_correct, option_order, match_side, match_key),
    )


def add_question_to_quiz(quiz_id, question_id, question_order, question_marks):
    return execute(
        f"""
        INSERT INTO {object_name("QUIZ_QUESTION")}
        (QUIZ_ID, QUESTION_ID, QUESTION_ORDER, QUESTION_MARKS)
        VALUES (?, ?, ?, ?)
        """,
        (quiz_id, question_id, question_order, question_marks),
    )


def get_quiz_content_rows(quiz_id, include_correct=False):
    """Load quiz content using the V6-compatible option query first.

    V7 matching metadata is fetched separately only for MATCHING questions.
    """
    correct_column = (
        "qo.IS_CORRECT AS IS_CORRECT"
        if include_correct
        else "CAST(NULL AS CHAR(1)) AS IS_CORRECT"
    )
    rows = fetch_all(
        f"""
        SELECT
            qq.QUIZ_ID,
            qq.QUESTION_ID,
            qq.QUESTION_ORDER,
            qq.QUESTION_MARKS,
            qu.QUESTION_TEXT,
            qu.QUESTION_TYPE,
            qo.OPTION_ID,
            qo.OPTION_TEXT,
            qo.OPTION_ORDER,
            {correct_column}
        FROM {object_name("QUIZ_QUESTION")} qq
        JOIN {object_name("QUESTION")} qu
          ON qu.QUESTION_ID=qq.QUESTION_ID
        LEFT JOIN {object_name("QUESTION_OPTION")} qo
          ON qo.QUESTION_ID=qu.QUESTION_ID
        WHERE qq.QUIZ_ID=?
        ORDER BY qq.QUESTION_ORDER, qo.OPTION_ORDER, qo.OPTION_ID
        """,
        (quiz_id,),
    )
    # One fetch for all MATCHING questions (rather than one per option).
    # Preserve answer-side filtering in the service layer. Never return keys
    # to students; the backend still needs them for matching option handles.
    matching_ids = sorted({
        int(r["question_id"]) for r in rows
        if str(r.get("question_type", "")).upper() == "MATCHING"
    })
    metadata = {}
    for offset in range(0, len(matching_ids), 900):
        # Oracle 21c limits ordinary IN lists to 1,000 values.
        batch = matching_ids[offset:offset + 900]
        placeholders = ",".join("?" for _ in batch)
        metadata_rows = fetch_all(
            f"""
            SELECT QUESTION_ID, OPTION_ID,
                   TO_CHAR(MATCH_SIDE) AS MATCH_SIDE,
                   TO_CHAR(MATCH_KEY) AS MATCH_KEY
            FROM {object_name("QUESTION_OPTION")}
            WHERE QUESTION_ID IN ({placeholders})
            """,
            tuple(batch),
        )
        for item in metadata_rows:
            metadata.setdefault(int(item["question_id"]), []).append(item)
    meta_by_id = {
        qid: {int(r["option_id"]): r for r in opts}
        for qid, opts in metadata.items()
    }
    for r in rows:
        qid=int(r["question_id"])
        oid=r.get("option_id")
        if oid is not None and qid in meta_by_id:
            m=meta_by_id[qid].get(int(oid), {})
            r["match_side"]=m.get("match_side")
            r["match_key"]=m.get("match_key")
        else:
            r["match_side"]=None
            r["match_key"]=None
    return rows


# =====================================================
# QUIZ ATTEMPTS
# =====================================================

def start_quiz_attempt(quiz_id, student_id):
    """Start an attempt through the authoritative Oracle procedure."""

    sql = f"""
        DECLARE
            v_attempt_id NUMBER;
        BEGIN
            {object_name("PR_START_QUIZ_ATTEMPT")}(
                ?,
                ?,
                v_attempt_id
            );
        END;
    """
    execute(sql, (quiz_id, student_id))

    return fetch_one(
        f"""
        SELECT
            ATTEMPT_ID,
            QUIZ_ID,
            STUDENT_ID,
            ATTEMPT_NO,
            STARTED_AT,
            SUBMITTED_AT
        FROM {object_name("QUIZ_ATTEMPT")}
        WHERE QUIZ_ID=?
          AND STUDENT_ID=?
          AND SUBMITTED_AT IS NULL
        ORDER BY STARTED_AT DESC, ATTEMPT_ID DESC
        FETCH FIRST 1 ROW ONLY
        """,
        (quiz_id, student_id),
    )


def get_attempt(attempt_id):
    return fetch_one(
        f"""
        SELECT
            ATTEMPT_ID,
            QUIZ_ID,
            STUDENT_ID,
            ATTEMPT_NO,
            STARTED_AT,
            SUBMITTED_AT
        FROM {object_name("QUIZ_ATTEMPT")}
        WHERE ATTEMPT_ID=?
        """,
        (attempt_id,),
    )



def question_belongs_to_quiz(quiz_id, question_id):
    return fetch_one(
        f"SELECT 1 AS FOUND FROM {object_name('QUIZ_QUESTION')} WHERE QUIZ_ID=? AND QUESTION_ID=?",
        (int(quiz_id), int(question_id)),
    ) is not None


def get_attempt_submission_state(attempt_id):
    """Return Oracle-evaluated submission guards before calling the procedure."""
    return fetch_one(
        f"""
        SELECT
            qa.ATTEMPT_ID,
            qa.QUIZ_ID,
            qa.STARTED_AT,
            qa.SUBMITTED_AT,
            q.DURATION_MINUTES,
            q.CLOSE_AT,
            CASE
                WHEN qa.SUBMITTED_AT IS NOT NULL THEN 'ALREADY_SUBMITTED'
                WHEN q.DURATION_MINUTES IS NOT NULL
                 AND SYSTIMESTAMP > qa.STARTED_AT
                    + NUMTODSINTERVAL(q.DURATION_MINUTES, 'MINUTE')
                    THEN 'DURATION_EXPIRED'
                WHEN q.CLOSE_AT IS NOT NULL
                 AND SYSTIMESTAMP > q.CLOSE_AT
                    THEN 'QUIZ_CLOSED'
                ELSE 'READY'
            END AS SUBMISSION_STATE
        FROM {object_name("QUIZ_ATTEMPT")} qa
        JOIN {object_name("QUIZ")} q
          ON q.QUIZ_ID=qa.QUIZ_ID
        WHERE qa.ATTEMPT_ID=?
        """,
        (attempt_id,),
    )


def get_pending_attempt_for_student_quiz(student_id, quiz_id):
    """Find an unfinished attempt even if its timer or quiz window expired.

    This intentionally returns metadata only, not quiz questions or answers.
    It is scoped to the authenticated student to prevent ID enumeration.
    """
    return fetch_one(
        f"""
        SELECT ATTEMPT_ID, QUIZ_ID, STUDENT_ID, ATTEMPT_NO, STARTED_AT
        FROM {object_name('QUIZ_ATTEMPT')}
        WHERE STUDENT_ID=? AND QUIZ_ID=? AND SUBMITTED_AT IS NULL
        ORDER BY ATTEMPT_ID DESC
        FETCH FIRST 1 ROW ONLY
        """,
        (int(student_id), int(quiz_id)),
    )


def get_open_attempt_for_student_quiz(student_id, quiz_id):
    """Only expose a student's active, not-expired quiz contents/draft.

    An expired attempt can still be finalized by PR_SUBMIT_QUIZ_ATTEMPT;
    it must not grant further question retrieval or answer editing.
    """
    return fetch_one(
        f"""
        SELECT qa.ATTEMPT_ID, qa.QUIZ_ID, qa.STUDENT_ID,
               qa.ATTEMPT_NO, qa.STARTED_AT, qa.SUBMITTED_AT
        FROM {object_name('QUIZ_ATTEMPT')} qa
        JOIN {object_name('QUIZ')} q ON q.QUIZ_ID=qa.QUIZ_ID
        WHERE qa.STUDENT_ID=? AND qa.QUIZ_ID=? AND qa.SUBMITTED_AT IS NULL
          AND (q.CLOSE_AT IS NULL OR SYSTIMESTAMP <= q.CLOSE_AT)
          AND (q.DURATION_MINUTES IS NULL OR SYSTIMESTAMP <= qa.STARTED_AT
               + NUMTODSINTERVAL(q.DURATION_MINUTES, 'MINUTE'))
        ORDER BY qa.ATTEMPT_ID DESC
        FETCH FIRST 1 ROW ONLY
        """,
        (student_id, quiz_id),
    )

# =====================================================
# QUIZ RESPONSES
# =====================================================

def get_response(response_id):
    return fetch_one(
        f"""
        SELECT
            qr.RESPONSE_ID,
            qr.ATTEMPT_ID,
            qr.QUESTION_ID,
            qr.RESPONSE_TEXT,
            qa.STUDENT_ID,
            qa.QUIZ_ID,
            qa.SUBMITTED_AT
        FROM {object_name("QUIZ_RESPONSE")} qr
        JOIN {object_name("QUIZ_ATTEMPT")} qa
          ON qa.ATTEMPT_ID=qr.ATTEMPT_ID
        WHERE qr.RESPONSE_ID=?
        """,
        (response_id,),
    )


def get_response_by_attempt_question(attempt_id, question_id):
    return fetch_one(
        f"""
        SELECT
            RESPONSE_ID,
            ATTEMPT_ID,
            QUESTION_ID,
            RESPONSE_TEXT
        FROM {object_name("QUIZ_RESPONSE")}
        WHERE ATTEMPT_ID=?
          AND QUESTION_ID=?
        """,
        (attempt_id, question_id),
    )


def create_response(attempt_id, question_id, response_text):
    execute(
        f"""
        INSERT INTO {object_name("QUIZ_RESPONSE")}
        (ATTEMPT_ID, QUESTION_ID, RESPONSE_TEXT)
        VALUES (?, ?, ?)
        """,
        (attempt_id, question_id, response_text),
    )
    return get_response_by_attempt_question(attempt_id, question_id)


def add_response_option(response_id, option_id):
    return execute(
        f"""
        INSERT INTO {object_name("QUIZ_RESPONSE_OPTION")}
        (RESPONSE_ID, OPTION_ID)
        VALUES (?, ?)
        """,
        (response_id, option_id),
    )


def add_response_order(response_id, position_order, option_id):
    return execute(
        f"""
        INSERT INTO {object_name("QUIZ_RESPONSE_ORDER")}
        (RESPONSE_ID, POSITION_ORDER, OPTION_ID)
        VALUES (?, ?, ?)
        """,
        (response_id, position_order, option_id),
    )


def add_response_match(response_id, left_option_id, right_option_id):
    return execute(
        f"""
        INSERT INTO {object_name("QUIZ_RESPONSE_MATCH")}
        (RESPONSE_ID, LEFT_OPTION_ID, RIGHT_OPTION_ID)
        VALUES (?, ?, ?)
        """,
        (response_id, left_option_id, right_option_id),
    )


def get_response_order_items(response_id):
    if response_id is None:
        return []
    return fetch_all(
        f"""
        SELECT
            qro.POSITION_ORDER,
            qo.OPTION_ID,
            qo.OPTION_TEXT,
            qo.OPTION_ORDER
        FROM {object_name("QUIZ_RESPONSE_ORDER")} qro
        JOIN {object_name("QUESTION_OPTION")} qo
          ON qo.OPTION_ID=qro.OPTION_ID
        WHERE qro.RESPONSE_ID=?
        ORDER BY qro.POSITION_ORDER
        """,
        (response_id,),
    )


def get_response_match_items(response_id):
    if response_id is None:
        return []
    return fetch_all(
        f"""
        SELECT
            qrm.LEFT_OPTION_ID,
            lo.OPTION_TEXT AS LEFT_OPTION_TEXT,
            qrm.RIGHT_OPTION_ID,
            ro.OPTION_TEXT AS RIGHT_OPTION_TEXT
        FROM {object_name("QUIZ_RESPONSE_MATCH")} qrm
        JOIN {object_name("QUESTION_OPTION")} lo
          ON lo.OPTION_ID=qrm.LEFT_OPTION_ID
        JOIN {object_name("QUESTION_OPTION")} ro
          ON ro.OPTION_ID=qrm.RIGHT_OPTION_ID
        WHERE qrm.RESPONSE_ID=?
        ORDER BY qrm.LEFT_OPTION_ID
        """,
        (response_id,),
    )


def list_student_quiz_attempts(student_id):
    return fetch_all(
        f"""
        SELECT
            qa.ATTEMPT_ID,
            qa.QUIZ_ID,
            qa.ATTEMPT_NO,
            qa.STARTED_AT,
            qa.SUBMITTED_AT,
            q.QUIZ_TITLE,
            q.ALLOW_MARK_VIEW,
            q.ALLOW_ANSWER_REVIEW,
            ac.COMPONENT_ID,
            ac.COMPONENT_NAME,
            ac.MAX_MARKS AS COMPONENT_MAX_MARKS,
            gs.OFFERING_ID,
            c.COURSE_CODE,
            c.COURSE_NAME,
            (SELECT COUNT(*) FROM {object_name('QUIZ_QUESTION_GRADE')} qqg
             JOIN {object_name('QUESTION')} qn ON qn.QUESTION_ID=qqg.QUESTION_ID
             WHERE qqg.GRADING_ID=qg.GRADING_ID AND qn.QUESTION_TYPE='LONG_TEXT') AS LONG_TEXT_COUNT,
            CASE WHEN (q.CLOSE_AT IS NOT NULL AND SYSTIMESTAMP > q.CLOSE_AT)
                 OR (SELECT COUNT(*) FROM {object_name('QUIZ_ATTEMPT')} qa2
                     WHERE qa2.QUIZ_ID=qa.QUIZ_ID AND qa2.STUDENT_ID=qa.STUDENT_ID) >= q.MAX_ATTEMPTS
                THEN 1 ELSE 0 END AS REVIEW_ALLOWED,
            qg.GRADING_ID,
            qg.GRADING_STATUS,
            qg.AUTO_MARKS,
            qg.FINAL_MARKS,
            qg.MAX_MARKS AS QUIZ_MAX_MARKS
        FROM {object_name("QUIZ_ATTEMPT")} qa
        JOIN {object_name("QUIZ")} q
          ON q.QUIZ_ID=qa.QUIZ_ID
        JOIN {object_name("ASSESSMENT_COMPONENT")} ac
          ON ac.COMPONENT_ID=q.COMPONENT_ID
        JOIN {object_name("GRADING_SCHEME")} gs
          ON gs.SCHEME_ID=ac.SCHEME_ID
        JOIN {object_name("COURSE_OFFERING")} co
          ON co.OFFERING_ID=gs.OFFERING_ID
        JOIN {object_name("COURSE")} c
          ON c.COURSE_ID=co.COURSE_ID
        LEFT JOIN {object_name("QUIZ_GRADING")} qg
          ON qg.ATTEMPT_ID=qa.ATTEMPT_ID
        WHERE qa.STUDENT_ID=?
        ORDER BY qa.SUBMITTED_AT DESC NULLS LAST, qa.ATTEMPT_ID DESC
        """,
        (student_id,),
    )

def get_numeric_rule(question_id):
    return fetch_one(
        f"""
        SELECT QUESTION_ID, EXPECTED_VALUE, TOLERANCE
        FROM {object_name("QUESTION_NUMERIC_RULE")}
        WHERE QUESTION_ID=?
        """,
        (question_id,),
    )


def set_numeric_rule(question_id, expected_value, tolerance):
    execute(
        f"""
        MERGE INTO {object_name("QUESTION_NUMERIC_RULE")} dst
        USING (SELECT ? AS QUESTION_ID, ? AS EXPECTED_VALUE, ? AS TOLERANCE FROM DUAL) src
        ON (dst.QUESTION_ID=src.QUESTION_ID)
        WHEN MATCHED THEN UPDATE SET
            EXPECTED_VALUE=src.EXPECTED_VALUE,
            TOLERANCE=src.TOLERANCE
        WHEN NOT MATCHED THEN INSERT
            (QUESTION_ID, EXPECTED_VALUE, TOLERANCE)
        VALUES
            (src.QUESTION_ID, src.EXPECTED_VALUE, src.TOLERANCE)
        """,
        (question_id, expected_value, tolerance),
    )


def get_keywords(question_id):
    return fetch_all(
        f"""
        SELECT QUESTION_ID, KEYWORD_ORDER, KEYWORD_TEXT
        FROM {object_name("QUESTION_KEYWORD")}
        WHERE QUESTION_ID=?
        ORDER BY KEYWORD_ORDER
        """,
        (question_id,),
    )


def add_keyword(question_id, keyword_order, keyword_text):
    return execute(
        f"""
        INSERT INTO {object_name("QUESTION_KEYWORD")}
        (QUESTION_ID, KEYWORD_ORDER, KEYWORD_TEXT)
        VALUES (?, ?, ?)
        """,
        (question_id, keyword_order, keyword_text),
    )


def get_grading_for_attempt(attempt_id):
    return fetch_one(
        f"""
        SELECT
            qg.GRADING_ID,
            qg.ATTEMPT_ID,
            qg.AUTO_MARKS,
            qg.FINAL_MARKS,
            qg.MAX_MARKS,
            qg.GRADING_STATUS,
            qg.AUTO_GRADED_AT,
            qg.REVIEWED_BY_USER_ID,
            qg.REVIEWED_AT,
            qg.RELEASED_AT,
            qg.INSTRUCTOR_NOTES,
            qa.QUIZ_ID,
            qa.STUDENT_ID,
            q.QUIZ_TITLE,
            q.COMPONENT_ID
        FROM {object_name("QUIZ_GRADING")} qg
        JOIN {object_name("QUIZ_ATTEMPT")} qa ON qa.ATTEMPT_ID=qg.ATTEMPT_ID
        JOIN {object_name("QUIZ")} q ON q.QUIZ_ID=qa.QUIZ_ID
        WHERE qg.ATTEMPT_ID=?
        """,
        (attempt_id,),
    )


def get_question_grades(grading_id):
    return fetch_all(
        f"""
        SELECT
            qqg.GRADING_ID,
            qqg.QUESTION_ID,
            qqg.MARKS_AWARDED,
            qqg.MAX_MARKS,
            qqg.IS_CORRECT,
            qqg.GRADING_NOTE,
            q.QUESTION_TEXT,
            q.QUESTION_TYPE,
            qr.RESPONSE_TEXT,
            qq.QUESTION_ORDER
        FROM {object_name("QUIZ_QUESTION_GRADE")} qqg
        JOIN {object_name("QUESTION")} q ON q.QUESTION_ID=qqg.QUESTION_ID
        JOIN {object_name('QUIZ_GRADING')} qg ON qg.GRADING_ID=qqg.GRADING_ID
        JOIN {object_name('QUIZ_ATTEMPT')} qa ON qa.ATTEMPT_ID=qg.ATTEMPT_ID
        JOIN {object_name('QUIZ_QUESTION')} qq ON qq.QUIZ_ID=qa.QUIZ_ID AND qq.QUESTION_ID=qqg.QUESTION_ID
        LEFT JOIN {object_name('QUIZ_RESPONSE')} qr ON qr.ATTEMPT_ID=qa.ATTEMPT_ID AND qr.QUESTION_ID=qqg.QUESTION_ID
        WHERE qqg.GRADING_ID=?
        ORDER BY qq.QUESTION_ORDER
        """,
        (grading_id,),
    )


def list_quiz_gradings(quiz_id):
    return fetch_all(
        f"""
        SELECT
            qg.GRADING_ID,
            qa.ATTEMPT_ID,
            qg.AUTO_MARKS,
            qg.FINAL_MARKS,
            qg.MAX_MARKS,
            COALESCE(qg.GRADING_STATUS, 'NOT_GRADED') AS GRADING_STATUS,
            qg.AUTO_GRADED_AT,
            qg.REVIEWED_AT,
            qg.RELEASED_AT,
            qa.STUDENT_ID,
            s.STUDENT_NAME,
            s.ADMISSION_NO,
            qa.ATTEMPT_NO,
            qa.SUBMITTED_AT
        FROM {object_name("QUIZ_ATTEMPT")} qa
        JOIN {object_name("STUDENT")} s ON s.STUDENT_ID=qa.STUDENT_ID
        LEFT JOIN {object_name("QUIZ_GRADING")} qg
          ON qg.ATTEMPT_ID=qa.ATTEMPT_ID
        WHERE qa.QUIZ_ID=?
          AND qa.SUBMITTED_AT IS NOT NULL
        ORDER BY s.STUDENT_NAME, qa.ATTEMPT_NO
        """,
        (quiz_id,),
    )

def update_grading_review(grading_id, final_marks, reviewer_user_id, notes=None):
    return execute(
        f"""
        UPDATE {object_name("QUIZ_GRADING")}
        SET FINAL_MARKS=?,
            GRADING_STATUS='REVIEWED',
            REVIEWED_BY_USER_ID=?,
            REVIEWED_AT=SYSTIMESTAMP,
            INSTRUCTOR_NOTES=?
        WHERE GRADING_ID=?
          AND GRADING_STATUS IN ('AUTO_GRADED','REVIEWED')
        """,
        (final_marks, reviewer_user_id, notes, grading_id),
    )


def release_grading(grading_id):
    return execute(
        f"""
        UPDATE {object_name("QUIZ_GRADING")}
        SET GRADING_STATUS='RELEASED',
            RELEASED_AT=SYSTIMESTAMP
        WHERE GRADING_ID=?
          AND GRADING_STATUS='REVIEWED'
        """,
        (grading_id,),
    )


# =====================================================
# RESULT / REVIEW READS
# =====================================================

def get_attempt_result_context(attempt_id):
    """Attempt-level result; STUDENT_MARK may represent a different best attempt."""
    return fetch_one(
        f"""
        SELECT
            qa.ATTEMPT_ID,
            qa.QUIZ_ID,
            qa.STUDENT_ID,
            qa.ATTEMPT_NO,
            qa.STARTED_AT,
            qa.SUBMITTED_AT,
            q.QUIZ_TITLE,
            q.COMPONENT_ID,
            q.ALLOW_MARK_VIEW,
            q.ALLOW_ANSWER_REVIEW,
            ac.COMPONENT_NAME,
            ac.MAX_MARKS AS COMPONENT_MAX_MARKS,
            gs.OFFERING_ID,
            q.MAX_ATTEMPTS,
            q.CLOSE_AT,
            (SELECT COUNT(*) FROM {object_name('QUIZ_QUESTION_GRADE')} qqg
             JOIN {object_name('QUESTION')} qn ON qn.QUESTION_ID=qqg.QUESTION_ID
             WHERE qqg.GRADING_ID=qg.GRADING_ID AND qn.QUESTION_TYPE='LONG_TEXT') AS LONG_TEXT_COUNT,
            CASE WHEN (q.CLOSE_AT IS NOT NULL AND SYSTIMESTAMP > q.CLOSE_AT)
                 OR (SELECT COUNT(*) FROM {object_name('QUIZ_ATTEMPT')} qa2
                     WHERE qa2.QUIZ_ID=qa.QUIZ_ID AND qa2.STUDENT_ID=qa.STUDENT_ID) >= q.MAX_ATTEMPTS
                THEN 1 ELSE 0 END AS REVIEW_ALLOWED,
            qg.GRADING_ID,
            qg.FINAL_MARKS,
            qg.MAX_MARKS,
            qg.GRADING_STATUS,
            COALESCE(qg.REVIEWED_AT, qg.AUTO_GRADED_AT) AS GRADED_AT
        FROM {object_name("QUIZ_ATTEMPT")} qa
        JOIN {object_name("QUIZ")} q
          ON q.QUIZ_ID=qa.QUIZ_ID
        JOIN {object_name("ASSESSMENT_COMPONENT")} ac
          ON ac.COMPONENT_ID=q.COMPONENT_ID
        JOIN {object_name("GRADING_SCHEME")} gs
          ON gs.SCHEME_ID=ac.SCHEME_ID
        LEFT JOIN {object_name("QUIZ_GRADING")} qg
          ON qg.ATTEMPT_ID=qa.ATTEMPT_ID
        WHERE qa.ATTEMPT_ID=?
        """,
        (attempt_id,),
    )


def get_attempt_review_questions(attempt_id):
    return fetch_all(
        f"""
        SELECT
            qq.QUESTION_ID,
            qq.QUESTION_ORDER,
            qq.QUESTION_MARKS,
            qn.QUESTION_TEXT,
            qn.QUESTION_TYPE,
            qr.RESPONSE_ID,
            qr.RESPONSE_TEXT
        FROM {object_name("QUIZ_ATTEMPT")} qa
        JOIN {object_name("QUIZ_QUESTION")} qq
          ON qq.QUIZ_ID=qa.QUIZ_ID
        JOIN {object_name("QUESTION")} qn
          ON qn.QUESTION_ID=qq.QUESTION_ID
        LEFT JOIN {object_name("QUIZ_RESPONSE")} qr
          ON qr.ATTEMPT_ID=qa.ATTEMPT_ID
         AND qr.QUESTION_ID=qq.QUESTION_ID
        WHERE qa.ATTEMPT_ID=?
          AND EXISTS (
              SELECT 1 FROM {object_name('QUIZ_GRADING')} qg
              JOIN {object_name('QUIZ_QUESTION_GRADE')} qqg
                ON qqg.GRADING_ID=qg.GRADING_ID
              WHERE qg.ATTEMPT_ID=qa.ATTEMPT_ID
                AND qqg.QUESTION_ID=qq.QUESTION_ID
          )
        ORDER BY qq.QUESTION_ORDER, qq.QUESTION_ID
        """,
        (attempt_id,),
    )


def get_selected_options(response_id):
    if response_id is None:
        return []
    return fetch_all(
        f"""
        SELECT
            qo.OPTION_ID,
            qo.OPTION_TEXT,
            qo.OPTION_ORDER
        FROM {object_name("QUIZ_RESPONSE_OPTION")} qro
        JOIN {object_name("QUESTION_OPTION")} qo
          ON qo.OPTION_ID=qro.OPTION_ID
        WHERE qro.RESPONSE_ID=?
        ORDER BY qo.OPTION_ORDER, qo.OPTION_ID
        """,
        (response_id,),
    )


def submit_quiz_attempt(attempt_id):
    return execute(
        f"""
        BEGIN
            {object_name("PR_SUBMIT_QUIZ_ATTEMPT")}(?);
        END;
        """,
        (attempt_id,),
    )


def get_enrollment_context_for_quiz_attempt(attempt_id):
    return fetch_one(
        f"""
        SELECT
            e.ENROLLMENT_ID,
            e.STUDENT_ID,
            e.OFFERING_ID
        FROM {object_name("QUIZ_ATTEMPT")} qa
        JOIN {object_name("QUIZ")} q ON q.QUIZ_ID=qa.QUIZ_ID
        JOIN {object_name("ASSESSMENT_COMPONENT")} ac ON ac.COMPONENT_ID=q.COMPONENT_ID
        JOIN {object_name("GRADING_SCHEME")} gs ON gs.SCHEME_ID=ac.SCHEME_ID
        JOIN {object_name("ENROLLMENT")} e
          ON e.STUDENT_ID=qa.STUDENT_ID
         AND e.OFFERING_ID=gs.OFFERING_ID
        WHERE qa.ATTEMPT_ID=?
        """,
        (attempt_id,),
    )


# ----------------------- compliance hardening -----------------------
def question_access_for_instructor(question_id, instructor_id, user_id, edit=False):
    """Ownership from existing OFFERING_INSTRUCTOR and ACTIVITY_LOG relations.

    Unattached legacy questions with unknown authors are admin-only. A question
    already attempted cannot be edited by an instructor; create a fresh copy.
    """
    author = fetch_one(
        f"SELECT 1 AS OK FROM {object_name('ACTIVITY_LOG')} "
        "WHERE USER_ID=? AND ACTIVITY_DESCRIPTION=? FETCH FIRST 1 ROW ONLY",
        (int(user_id or 0), f"QUESTION_ID={int(question_id)};CREATED"),
    )
    linked = fetch_all(
        f"""SELECT DISTINCT gs.OFFERING_ID
        FROM {object_name('QUIZ_QUESTION')} qq
        JOIN {object_name('QUIZ')} q ON q.QUIZ_ID=qq.QUIZ_ID
        JOIN {object_name('ASSESSMENT_COMPONENT')} ac ON ac.COMPONENT_ID=q.COMPONENT_ID
        JOIN {object_name('GRADING_SCHEME')} gs ON gs.SCHEME_ID=ac.SCHEME_ID
        WHERE qq.QUESTION_ID=?""",
        (int(question_id),),
    )
    owns = [bool(fetch_one(
        f"SELECT 1 AS OK FROM {object_name('OFFERING_INSTRUCTOR')} "
        "WHERE OFFERING_ID=? AND INSTRUCTOR_ID=?",
        (int(row['offering_id']), int(instructor_id or 0)),
    )) for row in linked]
    if not edit:
        return bool(author) or any(owns)
    if not (bool(author) or bool(linked and all(owns))):
        return False
    if linked and not all(owns):
        return False
    attempted = fetch_one(
        f"""SELECT 1 AS OK FROM {object_name('QUIZ_QUESTION')} qq
        JOIN {object_name('QUIZ_ATTEMPT')} qa ON qa.QUIZ_ID=qq.QUIZ_ID
        WHERE qq.QUESTION_ID=? FETCH FIRST 1 ROW ONLY""",
        (int(question_id),),
    )
    return attempted is None


def quiz_has_attempts(quiz_id):
    return bool(fetch_one(
        f"SELECT 1 AS OK FROM {object_name('QUIZ_ATTEMPT')} "
        "WHERE QUIZ_ID=? FETCH FIRST 1 ROW ONLY", (int(quiz_id),)
    ))

def quiz_has_pending_attempts(quiz_id):
    """Do not append questions while any started attempt is unsubmitted/ungraded.

    Existing QUIZ_QUESTION_GRADE rows are the immutable question-set snapshot
    for previously graded attempts. There is no new Oracle table or column.
    """
    return bool(fetch_one(
        f"""SELECT 1 AS BLOCKED FROM {object_name('QUIZ_ATTEMPT')} qa
        WHERE qa.QUIZ_ID=?
          AND (qa.SUBMITTED_AT IS NULL
               OR NOT EXISTS (
                   SELECT 1 FROM {object_name('QUIZ_GRADING')} qg
                   JOIN {object_name('QUIZ_QUESTION_GRADE')} qqg
                     ON qqg.GRADING_ID=qg.GRADING_ID
                   WHERE qg.ATTEMPT_ID=qa.ATTEMPT_ID
               ))
        FETCH FIRST 1 ROW ONLY""",
        (int(quiz_id),),
    ))


def question_has_attempts(question_id):
    return bool(fetch_one(
        f"""SELECT 1 AS OK FROM {object_name('QUIZ_QUESTION')} qq
             JOIN {object_name('QUIZ_ATTEMPT')} qa ON qa.QUIZ_ID=qq.QUIZ_ID
             WHERE qq.QUESTION_ID=? FETCH FIRST 1 ROW ONLY""",
        (int(question_id),)
    ))


def lock_attempt_for_answer_update(attempt_id):
    return fetch_one(
        f"SELECT ATTEMPT_ID, QUIZ_ID, STUDENT_ID, SUBMITTED_AT "
        f"FROM {object_name('QUIZ_ATTEMPT')} WHERE ATTEMPT_ID=? FOR UPDATE",
        (int(attempt_id),),
    )


def replace_response_text(response_id, value):
    return execute(
        f"UPDATE {object_name('QUIZ_RESPONSE')} SET RESPONSE_TEXT=? WHERE RESPONSE_ID=?",
        (value, int(response_id)),
    )


def clear_response_children(response_id):
    for name in ('QUIZ_RESPONSE_OPTION', 'QUIZ_RESPONSE_ORDER', 'QUIZ_RESPONSE_MATCH'):
        execute(f"DELETE FROM {object_name(name)} WHERE RESPONSE_ID=?", (int(response_id),))


def set_question_grade(grading_id, question_id, marks, is_correct, feedback):
    return execute(
        f"""UPDATE {object_name('QUIZ_QUESTION_GRADE')}
            SET MARKS_AWARDED=?, IS_CORRECT=?, GRADING_NOTE=?
            WHERE GRADING_ID=? AND QUESTION_ID=?""",
        (float(marks), is_correct, feedback, int(grading_id), int(question_id)),
    )
