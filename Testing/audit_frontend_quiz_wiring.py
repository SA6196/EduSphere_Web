"""Read-only static check that Vue quiz actions map to Django URLs/views.

No HTTP requests and no file edits. This validates source wiring, not browser execution.
"""
from pathlib import Path
import argparse
import re
import sys

MAPPING = [
    ('questions', 'questions/', 'QuestionListView', 'api.quizzes.questions()'),
    ('question', 'questions/<int:question_id>/', 'QuestionDetailView', 'api.quizzes.question('),
    ('createQuestion','questions/create/','QuestionCreateView','api.quizzes.createQuestion('),
    ('createOption','questions/options/create/','QuestionOptionCreateView','api.quizzes.createOption('),
    ('addQuestion','questions/add/','AddQuestionToQuizView','api.quizzes.addQuestion('),
    ('create','create/','QuizCreateView','api.quizzes.create('),
    ('list','', 'QuizListView','api.quizzes.list('),
    ('content','<int:quiz_id>/content/','QuizContentView','api.quizzes.content('),
    ('startAttempt','<int:quiz_id>/attempt/','QuizAttemptView','api.quizzes.startAttempt('),
    ('response','attempt/<int:attempt_id>/response/','QuizResponseView','api.quizzes.response('),
    ('submitAttempt','attempt/<int:attempt_id>/submit/','QuizSubmitView','api.quizzes.submitAttempt('),
    ('result','attempt/<int:attempt_id>/result/','QuizAttemptResultView','api.quizzes.result('),
    ('review','attempt/<int:attempt_id>/review/','QuizAttemptReviewView','api.quizzes.review('),
    ('grading','<int:quiz_id>/grading/','QuizGradingListView','api.quizzes.grading('),
    ('gradingDetail','attempt/<int:attempt_id>/grading/','QuizGradingDetailView','api.quizzes.gradingDetail('),
    ('reviewGrading','attempt/<int:attempt_id>/grading/','QuizGradingDetailView','api.quizzes.reviewGrading('),
    ('releaseGrading','attempt/<int:attempt_id>/grading/release/','QuizGradingReleaseView','api.quizzes.releaseGrading('),
]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--project-root', required=True, help='The extracted EduSphere_Compliance_Repair_Fixed root')
    args=p.parse_args()
    root=Path(args.project_root)
    f=root/'EduSphere_Frontend'/'src'
    choices=list(root.glob('EduSphere_Django_Backend*/quiz/urls.py'))
    if len(choices)!=1:
        p.error('Expected one Django backend quiz/urls.py under project root')
    backend=choices[0]
    api=(f/'services/api.js').read_text(encoding='utf-8')
    urls=backend.read_text(encoding='utf-8')
    usage='\n'.join((f/x).read_text(encoding='utf-8') for x in [
        'views/instructor/QuestionBankView.vue',
        'components/workspace/WorkspaceQuizzesTab.vue',
        'views/student/QuizAttemptView.vue',
        'views/instructor/QuizGradingView.vue',
    ])
    failures=[]
    print('EduSphere frontend -> Django quiz routing (static read-only):')
    for name,path,view,call in MAPPING:
        # Require a named API wrapper, a Vue caller and actual Django URL/view name.
        ok_api=bool(re.search(r'\b'+re.escape(name)+r'\s*:',api))
        ok_vue=call in usage
        # Exact snippets accept Django multiline formatting.
        ok_url=(f'"{path}"' in urls or f"'{path}'" in urls) and view in urls
        ok=ok_api and ok_vue and ok_url
        print(('PASS' if ok else 'FAIL'),name, '--',path)
        if not ok:failures.append((name,ok_api,ok_vue,ok_url))
    httpjs=(f/'services/http.js').read_text(encoding='utf-8')
    if "'http://127.0.0.1:8000/api'" in httpjs:
        print('NOTE: Default frontend API URL is port 8000 (ORIGINAL).')
        print('For staging UI only, set VITE_API_BASE_URL=http://127.0.0.1:8001/api in a staging-specific frontend .env.local.')
    opts=(f/'views/student/QuizAttemptView.vue').read_text(encoding='utf-8')
    if 'payload.selected_option_ids' in opts and 'api.quizzes.response(attemptId.value,payload)' in opts:
        print('PASS: Student MCQ answers are sent as selected_option_ids to response endpoint.')
    else:
        failures.append(('MCQ response payload',False,False,False))
    if failures:
        print('FAILED:',failures)
        return 1
    print(f'PASS: all {len(MAPPING)} checked API call-to-route pairs are connected.')
    print('LIMITATION: this is a static source check, not a Vue browser build or UI click test.')
    return 0

if __name__=='__main__':sys.exit(main())
