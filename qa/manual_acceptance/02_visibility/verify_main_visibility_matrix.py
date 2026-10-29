"""Live main-DB quiz visibility and forced-URL permissions acceptance test.

The script changes ONLY visibility flags for ONE previously created QA quiz, by
calling the application's instructor API, and tries to restore the original
flags in a finally block. It never writes SQL directly and never migrates a
schema. Login/audit entries may be created. Server must run at 127.0.0.1:8002.

If killed or the API goes offline while flags are changed, restore the prior
ALLOW_MARK_VIEW and ALLOW_ANSWER_REVIEW flags through the instructor UI/API.
"""
import argparse
from pathlib import Path
import re
import sys

from verify_main_api_quiz_lifecycle import (
    http, login, check, StopTest, preflight,
)

QUIZ_ID = 104
ATTEMPT_ID = 166
TAG = 'E7808E9C43'


def identify_fixture(conn, quiz_id, attempt_id, tag):
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT q.QUIZ_TITLE, q.ALLOW_MARK_VIEW, q.ALLOW_ANSWER_REVIEW,
                   q.MAX_ATTEMPTS, a.SUBMITTED_AT, a.ATTEMPT_NO,
                   c.COURSE_CODE, qa.QUESTION_ID
            FROM EDUSPHERE_OWNER.QUIZ q
            JOIN EDUSPHERE_OWNER.QUIZ_ATTEMPT a ON a.QUIZ_ID=q.QUIZ_ID
            JOIN EDUSPHERE_OWNER.QUIZ_QUESTION qa ON qa.QUIZ_ID=q.QUIZ_ID
            JOIN EDUSPHERE_OWNER.ASSESSMENT_COMPONENT ac ON ac.COMPONENT_ID=q.COMPONENT_ID
            JOIN EDUSPHERE_OWNER.GRADING_SCHEME gs ON gs.SCHEME_ID=ac.SCHEME_ID
            JOIN EDUSPHERE_OWNER.COURSE_OFFERING off ON off.OFFERING_ID=gs.OFFERING_ID
            JOIN EDUSPHERE_OWNER.COURSE c ON c.COURSE_ID=off.COURSE_ID
            WHERE q.QUIZ_ID=? AND a.ATTEMPT_ID=?
        """, (quiz_id, attempt_id))
        rows = cur.fetchall()
        if len(rows) != 1:
            raise StopTest('Exactly one QA fixture row must match the requested quiz and attempt IDs.')
        title, mark, answer, max_attempts, submitted, attempt_no, course_code, qid = rows[0]
        if title != 'API Main Lock '+tag or course_code != 'QA'+tag:
            raise StopTest('Fixture name/course marker mismatch. No changes were made.')
        if submitted is None or int(max_attempts) != 1 or int(attempt_no) != 1:
            raise StopTest('The QA fixture must have a submitted first attempt and max_attempts=1.')
        # Verify the exact test question, not merely a coincidental quiz name.
        cur.execute('SELECT QUESTION_TEXT FROM EDUSPHERE_OWNER.QUESTION WHERE QUESTION_ID=?', (qid,))
        row = cur.fetchone()
        if not row or row[0] != 'Which main-test option is correct? '+tag:
            raise StopTest('Question marker mismatch. No changes were made.')
        if mark not in ('Y','N') or answer not in ('Y','N'):
            raise StopTest('Unexpected current visibility flags. No changes were made.')
        return mark, answer
    finally:
        cur.close()


def verify_patched_flags(conn, quiz_id, mark, answer):
    cur = conn.cursor()
    try:
        cur.execute('SELECT ALLOW_MARK_VIEW, ALLOW_ANSWER_REVIEW FROM EDUSPHERE_OWNER.QUIZ WHERE QUIZ_ID=?', (quiz_id,))
        row = cur.fetchone()
        check(row is not None and (str(row[0]),str(row[1])) == (mark, answer),
              f'Oracle flags persisted as {mark}/{answer}')
    finally:
        cur.close()


def patch_visibility(quiz_id, instructor_token, mark, answer):
    status, body = http(f'/api/quizzes/{quiz_id}/visibility/', instructor_token,
                        {'allow_mark_view':mark, 'allow_answer_review':answer}, 'PATCH')
    check(status == 200 and body.get('success') is True,
          f'Assigned instructor may set marks={mark}, answer_review={answer}')


def verify_state(quiz_id, attempt_id, student, other_student, mark, answer):
    expect_result = 200 if mark == 'Y' else 403
    # This fixture has exactly one allowed/submitted attempt. Both controls
    # are needed for review; Y/Y should therefore unlock answer review.
    expect_review = 200 if mark == 'Y' and answer == 'Y' else 403
    status, result = http(f'/api/quizzes/attempt/{attempt_id}/result/', student)
    check(status == expect_result, f'Owner result endpoint honors marks={mark}, answer_review={answer} ({status})')
    if status == 200:
        result = result.get('data',result)
        check(int(result.get('attempt_id', -1)) == attempt_id and
              float(result.get('marks_obtained', -1)) == 10 and
              float(result.get('max_marks', -1)) == 10,
              'Published result shows expected 10/10 for the owning student')
    status, review = http(f'/api/quizzes/attempt/{attempt_id}/review/', student)
    check(status == expect_review, f'Owner answer review honors marks={mark}, answer_review={answer} ({status})')
    if status == 200:
        review = review.get('data',review)
        questions = review.get('questions', []) if isinstance(review,dict) else []
        check(bool(questions) and any(q.get('correct_answer') for q in questions),
              'Answer review includes solution only when both permissions are enabled')

    status, history = http('/api/quizzes/attempts/my/', student)
    history = history.get('data',history) if isinstance(history,dict) else history
    rows = history.get('attempts',[]) if isinstance(history,dict) else []
    mine = next((x for x in rows if int(x.get('attempt_id',-1))==attempt_id), None)
    check(status == 200 and mine is not None, 'Owner has attempt history record')
    if mark == 'N':
        check(mine.get('marks_obtained') is None and mine.get('max_marks') is None
              and mine.get('marks_visible') is False,
              'Attempt history hides unpublished score and maximum marks')
        status, body = http('/api/marks/my/', student)
        items = body.get('data',body) if isinstance(body,dict) else body
        component_id = int(mine['component_id'])
        check(status == 200 and isinstance(items,list) and not any(
            int(x.get('component_id',-1)) == component_id for x in items),
            'General marks API omits hidden quiz mark')
        status, book = http('/api/marks/my/semester-view/', student)
        book = book.get('data',book) if isinstance(book,dict) else book
        record = next((x for x in book.get('components',[]) if
                      int(x.get('component_id',-1))==component_id), None) if isinstance(book,dict) else None
        check(status == 200 and record is not None and
              record.get('marks_obtained') is None and record.get('recorded_at') is None
              and record.get('mark_status') == 'HIDDEN',
              'Semester marks API hides score, time and status')
    else:
        check(mine.get('marks_visible') is True and float(mine.get('marks_obtained',-1))==10,
              'Owner attempt history shows released score')

    if other_student:
        status, _ = http(f'/api/quizzes/attempt/{attempt_id}/result/', other_student)
        check(status == 403, 'Other student still blocked from result, even after release')
        status, _ = http(f'/api/quizzes/attempt/{attempt_id}/review/', other_student)
        check(status == 403, 'Other student still blocked from answer review, even after release')


def run(args):
    if args.quiz_id != QUIZ_ID or args.attempt_id != ATTEMPT_ID or args.tag != TAG:
        raise StopTest('This verifier is locked to the established QA fixture 104/166/E7808E9C43.')
    conn = preflight(args.main_backend)
    try:
        original = identify_fixture(conn, args.quiz_id, args.attempt_id, args.tag)
        print(f'Verified QA fixture: quiz={args.quiz_id}, attempt={args.attempt_id}, tag={args.tag}')
        print(f'Original flags: marks={original[0]}, answer_review={original[1]}')
        print('Only visibility flags on this QA quiz will change; they will be restored in a finally block.')
        print('If power/network fails, manually restore the original flag values above.')
        phrase = input('Type MAIN VISIBILITY MATRIX TEST to continue: ').strip()
        if phrase != 'MAIN VISIBILITY MATRIX TEST':
            print('Cancelled. No changes made.'); return 3
        instructor, _ = login('Assigned instructor (original quiz author)', 'INSTRUCTOR')
        other_instructor, _ = login('Unassigned instructor', 'INSTRUCTOR')
        student, _ = login('Owning student (attempt 166)', 'STUDENT')
        other_student, _ = login('Other student', 'STUDENT')
        # Prevent privilege confusion before changes.
        status, history = http('/api/quizzes/attempts/my/', student)
        history = history.get('data',history) if isinstance(history,dict) else history
        check(status==200 and any(int(x.get('attempt_id',-1))==args.attempt_id
              for x in history.get('attempts',[])), 'The logged-in student owns the QA attempt')
        status, history = http('/api/quizzes/attempts/my/', other_student)
        history = history.get('data',history) if isinstance(history,dict) else history
        check(status==200 and not any(int(x.get('attempt_id',-1))==args.attempt_id
              for x in history.get('attempts',[])), 'The other student does not own the QA attempt')
        # Even a forbidden write might succeed if there is a security regression.
        # Always attempt to restore after ANY mutation-capable request.
        changed = True
        try:
            status,_ = http(f'/api/quizzes/{args.quiz_id}/visibility/', other_instructor,
                {'allow_mark_view':'Y','allow_answer_review':'Y'},'PATCH')
            check(status==403,'Unassigned instructor cannot change visibility')
            status,_ = http(f'/api/quizzes/{args.quiz_id}/visibility/', student,
                {'allow_mark_view':'Y','allow_answer_review':'Y'},'PATCH')
            check(status==403,'Student cannot change visibility via forced API PATCH')
            status,_ = http(f'/api/quizzes/{args.quiz_id}/visibility/', None,
                {'allow_mark_view':'Y','allow_answer_review':'Y'},'PATCH')
            check(status==401,'Unauthenticated visibility update denied')
            verify_patched_flags(conn,args.quiz_id,*original)
            for mark,answer in [('N','N'),('N','Y'),('Y','N'),('Y','Y')]:
                # Set changed BEFORE API call so a partially successful call
                # still triggers restoration.
                changed = True
                patch_visibility(args.quiz_id,instructor,mark,answer)
                verify_patched_flags(conn,args.quiz_id,mark,answer)
                verify_state(args.quiz_id,args.attempt_id,student,other_student,mark,answer)
            print('\nPASS: four visibility combinations and role/owner checks.')
            return 0
        finally:
            if changed:
                print(f'\nRESTORING QA quiz visibility to marks={original[0]} / answer_review={original[1]}')
                try:
                    patch_visibility(args.quiz_id,instructor,*original)
                    verify_patched_flags(conn,args.quiz_id,*original)
                    status,_ = http(f'/api/quizzes/attempt/{args.attempt_id}/result/', student)
                    check(status == (200 if original[0]=='Y' else 403),
                          'Post-restore student result visibility correct')
                except Exception as exc:
                    print('CRITICAL: RESTORATION NOT VERIFIED:', repr(exc))
                    print('Manually restore the original visibility flags via the assigned instructor, immediately.')
                    raise
    finally:
        conn.close()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--main-backend', required=True)
    p.add_argument('--quiz-id', type=int, default=QUIZ_ID)
    p.add_argument('--attempt-id', type=int, default=ATTEMPT_ID)
    p.add_argument('--tag', default=TAG)
    args = p.parse_args()
    try:
        return run(args)
    except (StopTest, ValueError, KeyError, TypeError, OSError, ImportError) as exc:
        print('STOPPED:',str(exc))
        print('Review the last restoration message before closing this terminal.')
        return 1

if __name__ == '__main__':
    sys.exit(main())
