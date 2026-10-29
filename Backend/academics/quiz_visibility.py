"""Server-side quiz result visibility rules shared by student read APIs.

No new schema objects. The SQL is composed only from trusted source literals.
Never use frontend hiding as authorization. Applied to existing enrollments.
"""
from database.schema import object_name


def quiz_marks_visible_sql(quiz_alias="q", enrollment_alias="e"):
    """Predicate for a student's synchronized QUIZ STUDENT_MARK.

    Require a real quiz, explicit mark release, at least one eligible graded
    submitted attempt, and no outstanding provisional long-text review.
    Historical ungraded attempts and premature essay scores never become
    public by changing a URL or loading the semester markbook directly.
    """
    q, e = quiz_alias, enrollment_alias
    attempts = object_name("QUIZ_ATTEMPT")
    grading = object_name("QUIZ_GRADING")
    quiz_questions = object_name("QUIZ_QUESTION")
    questions = object_name("QUESTION")
    long_text = f"EXISTS (SELECT 1 FROM {quiz_questions} qq JOIN {questions} question ON question.QUESTION_ID=qq.QUESTION_ID WHERE qq.QUIZ_ID={q}.QUIZ_ID AND question.QUESTION_TYPE='LONG_TEXT')"
    base = f"qa.QUIZ_ID={q}.QUIZ_ID AND qa.STUDENT_ID={e}.STUDENT_ID AND qa.SUBMITTED_AT IS NOT NULL"
    return f"""(
        {q}.QUIZ_ID IS NOT NULL AND NVL({q}.ALLOW_MARK_VIEW, 'N')='Y'
        AND EXISTS (
            SELECT 1 FROM {attempts} qa
            JOIN {grading} g ON g.ATTEMPT_ID=qa.ATTEMPT_ID
            WHERE {base}
              AND (g.GRADING_STATUS IN ('REVIEWED','RELEASED')
                   OR (g.GRADING_STATUS='AUTO_GRADED' AND NOT {long_text}))
        )
        AND NOT EXISTS (
            SELECT 1 FROM {attempts} qa
            JOIN {grading} g ON g.ATTEMPT_ID=qa.ATTEMPT_ID
            WHERE {base} AND g.GRADING_STATUS='AUTO_GRADED'
              AND {long_text}
        )
    )"""


def offering_has_hidden_quiz_sql(offering_alias='co', enrollment_alias='e'):
    """Correlated predicate used to redact derived course percentages."""
    q = 'q_visibility'
    allowed = quiz_marks_visible_sql(q, enrollment_alias)
    return f"""EXISTS (
        SELECT 1 FROM {object_name('GRADING_SCHEME')} gs_visibility
        JOIN {object_name('ASSESSMENT_COMPONENT')} ac_visibility ON ac_visibility.SCHEME_ID=gs_visibility.SCHEME_ID
        JOIN {object_name('QUIZ')} {q} ON {q}.COMPONENT_ID=ac_visibility.COMPONENT_ID
        WHERE gs_visibility.OFFERING_ID={offering_alias}.OFFERING_ID
          AND NOT {allowed}
    )"""
