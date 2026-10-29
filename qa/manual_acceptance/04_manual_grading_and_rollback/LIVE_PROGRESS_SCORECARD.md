# EduSphere merged candidate — main DB acceptance progress

Updated with user-reported results on 18 October 2026. Database `EDUSPHERE_OWNER`, Oracle XEPDB1, candidate API on port 8002.

| Acceptance area | Status | Evidence |
|---|---|---|
| Main Oracle/schema preflight | **PASS (live)** | EDUSPHERE_APP, XEPDB1, 37/37 tables, two quiz procedures VALID, API health 200 |
| Question-bank authorization | **PASS (live)** | 9/9; cross-instructor, admin, student and unauthenticated requests |
| Quiz attempt/MCQ submit | **PASS (live)** | Quiz 104, attempt 166, 10/10; protected submission payload |
| Attempt/question/component grade persistence | **PASS (live for MCQ)** | QUIZ_GRADING, QUIZ_QUESTION_GRADE and STUDENT_MARK all 10/10 |
| Hidden grades via alternate endpoints | **PASS (live for tested fixtures)** | Result, review, history, general marks, semester markbook and dashboard |
| All four publication flag combinations | **PASS (live)** | N/N, N/Y, Y/N, Y/Y; owner and cross-student authorization; flags restored to N/N |
| Two attempts, highest-grade sync | **PASS (live)** | Quiz 124, first attempt 186 10/10, second attempt 187 0/10, component mark remained 10/10 |
| Attempt limit & submitted-answer immutability | **PASS (live)** | Third attempt denied; no extra attempt persisted; further writes rejected |
| Manual LONG_TEXT and rubric grading | **PENDING LIVE** | Controlled standalone test package created; no live results yet |
| Intentional failed-statement rollback | **PENDING LIVE (optional separate run)** | Failure injection deliberately exceeds Oracle varchar limit; offline checks only |
| Expiry and late answer denial | **PENDING LIVE** | Requires short timed test |
| Other quiz question types | **PENDING LIVE** | Per-type grading cases |
| Concurrent write/attempt integrity | **PENDING LIVE** | Independent concurrency tests needed |
| Frontend production build and browser QA | **PENDING** | Requires Windows npm build and role workflows |
| Oracle session utilization and latency | **PENDING** | Requires original vs optimized side-by-side measurements |

**Release rule:** At least **85%** of agreed acceptance groups passed, with **zero** critical access-control, answer-key, hidden-grade, grade-consistency or transaction failures. Passing the earlier offline development gate alone is insufficient for release.

**Main DB QA fixtures retained:** quiz 104 / attempt 166 (tag E7808E9C43); quiz 124 / attempts 186 and 187 (tag CECE5E651A). Both sets remain unpublished according to user-reported final output. Do not delete them.
