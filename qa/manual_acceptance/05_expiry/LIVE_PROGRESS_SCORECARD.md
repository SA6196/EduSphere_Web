# EduSphere MAIN Oracle live acceptance scorecard — October 18, 2026

**Candidate:** `EduSphere_Web_Optimized_Secure_Merge_STAGING_CANDIDATE` deployed as test API on port 8002, connected to `EDUSPHERE_OWNER` in `XEPDB1` as `EDUSPHERE_APP`. Fixed 37-table design unchanged.

## Passed live stages (user-supplied command outputs)

| Stage | Actual result | Evidence / QA fixture |
| --- | --- | --- |
| Main schema + backend health | PASS: 37 tables, 2/2 quiz procedures VALID, health 200 | Repeated main preflight |
| Question-bank read permissions | PASS: 9/9; owner isolation, admin union, student denial | `FINAL_I2` / `FINAL_I3`, student `FINAL_S6` |
| Quiz lifecycle and score persistence | PASS: submitted attempt and 10/10 in grading/question-grade/component marks; hidden results | quiz 104 / attempt 166, tag `E7808E9C43` |
| Visibility release matrix | PASS: all 4 flag configurations, cross-role and cross-student guards; flags restored N/N | quiz 104 / attempt 166 |
| Multiple attempts | PASS: 10/10 then 0/10, best component mark 10/10, 3rd attempt blocked | quiz 124 / attempts 186,187, tag `CECE5E651A` |
| Manual LONG_TEXT grading | PASS: auto 4/10, instructor review final 9/10, rubric persistence, release, denial/visibility | quiz 125 / attempt 188, tag `9B1E829D84` |
| Manual grading with intentional Oracle statement failure | PASS: no partial grading header/question/`STUDENT_MARK`; valid subsequent review final 9/10 | quiz 126 / attempt 189, tag `2BC8204D10` |

## Pending live stages

| Stage | Offline readiness | Live status |
| --- | --- | --- |
| Attempt expiry (1-minute quiz, late-write denial, post-expiry finalize) | New verifier offline 17/17 PASS | **NOT RUN** |
| Concurrent submit/autosave request races | Test package not yet provided | **NOT RUN** |
| Oracle session count, load/latency, connection lifecycle | Benchmark not yet provided | **NOT RUN** |
| Full Windows Vue production build and interactive UI smoke | Pending on user's local environment | **NOT RUN** |

**Release rule:** At least 85% of explicitly planned acceptance groups passing is necessary, but **all critical security, transaction atomicity, and grading correctness checks must pass**, with no unresolved severe regression. Passing script safeguards or isolated unit tests does not replace live coverage. Do not promote automatically.
