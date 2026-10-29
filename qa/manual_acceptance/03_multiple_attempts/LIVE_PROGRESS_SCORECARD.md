# EduSphere merged candidate — main database acceptance scorecard

Status updated from Windows output provided by the user on 18 October 2026.

| Test group | Status | Evidence |
|---|---|---|
| Main schema/API preflight | PASS live | EDUSPHERE_APP, XEPDB1, EDUSPHERE_OWNER, 37 owner tables, 2 valid quiz procedures, health 200 |
| Question-bank read RBAC | PASS live | 9/9 checks; cross-instructor isolation and student denial |
| Main single-attempt MCQ lifecycle | PASS live | Quiz 104, attempt 166, submitted 10/10 |
| Atomic grade persistence | PASS for exercised MCQ | 10/10 in QUIZ_GRADING, QUIZ_QUESTION_GRADE, STUDENT_MARK; rollback not yet tested |
| Hidden results and alternate mark routes | PASS live for exercised fixture | Result/review/marks/semester/dashboard denied or redacted |
| Cross-student confidentiality | PASS live | Both result and answer review denied |
| Visibility matrix | PASS live | N/N, N/Y, Y/N, Y/Y all correct; original N/N restored |
| Unauthorized visibility modification | PASS live | Unassigned instructor, student and unauthenticated callers denied |
| Multiple attempts/highest grade | **PENDING live** | New controlled verifier; 10/10 then 0/10 expected and STUDENT_MARK must stay 10/10 |
| Manual LONG_TEXT review | PENDING | Needs separate controlled quiz fixture |
| Other question types | PENDING | Requires independent answer/grade fixtures |
| Expiry and late answer denial | PENDING | Requires short timed quiz or controlled test clock |
| Rollback and concurrency | PENDING | Requires failure-injection/concurrent API test |
| Windows frontend build/browser UX | PENDING | Vue production build and user workflows |
| Oracle session utilization/latency | PENDING | Live comparison against previous app |

**Release rule:** minimum 85% planned acceptance pass **and zero critical failed authorization/confidentiality/transaction/data-integrity tests**. This is **not yet** a production release decision.

Original QA fixture: `E7808E9C43` / quiz `104` / attempt `166`. It remains in `EDUSPHERE_OWNER` with `ALLOW_MARK_VIEW=N` and `ALLOW_ANSWER_REVIEW=N` restored according to the latest user output.
