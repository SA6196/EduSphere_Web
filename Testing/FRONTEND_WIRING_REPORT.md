# Vue-to-Django quiz wiring report

Checked against `EduSphere_Final_Install_And_Question_Bank_Verification.zip` (the Compliance Repair build).

## Verified statically: 17 of 17

| Vue `api.quizzes` method | Django URL (all under `/api/quizzes/`) |
|---|---|
| `questions()` | GET `questions/` |
| `question(id)` | GET `questions/<question_id>/` |
| `createQuestion(payload)` | POST `questions/create/` |
| `createOption(payload)` | POST `questions/options/create/` |
| `addQuestion(payload)` | POST `questions/add/` |
| `create(payload)` | POST `create/` |
| `list(componentId)` | GET `?component_id=...` |
| `content(quizId)` | GET `<quiz_id>/content/` |
| `startAttempt(quizId)` | POST `<quiz_id>/attempt/` |
| `response(attemptId,payload)` | POST `attempt/<attempt_id>/response/` |
| `submitAttempt(attemptId)` | POST `attempt/<attempt_id>/submit/` |
| `result(attemptId)` | GET `attempt/<attempt_id>/result/` |
| `review(attemptId)` | GET `attempt/<attempt_id>/review/` |
| `grading(quizId)` | GET `<quiz_id>/grading/` |
| `gradingDetail(attemptId)` | GET `attempt/<attempt_id>/grading/` |
| `reviewGrading(attemptId,payload)` | PATCH `attempt/<attempt_id>/grading/` |
| `releaseGrading(attemptId)` | POST `attempt/<attempt_id>/grading/release/` |

The student MCQ form sends `selected_option_ids` to the correct answer-saving route. The existing `frontend_smoke_check.mjs`, `frontend_cross_role_smoke_check.mjs`, `frontend_error_smoke_check.mjs` all passed. Existing attendance predictor tests passed 16/16.

## Notes

- `src/services/http.js` defaults to **port 8000** unless `VITE_API_BASE_URL` is configured. For staging Vue UI only, use `http://127.0.0.1:8001/api` and a separate frontend session.
- `QuestionBankView.vue` does not know a question has already been attempted, so the Add option form can still be shown; Django rejects attempted-question edits. This is a frontend UX limitation, not a missing/wrong endpoint.
- These checks do **not** substitute for a full production frontend build and browser interactions.
