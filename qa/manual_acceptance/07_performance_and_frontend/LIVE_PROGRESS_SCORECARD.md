# EduSphere Main Oracle — Acceptance scorecard, updated October 18, 2026

**Candidate:** `EduSphere_Web_Optimized_Secure_Merge_STAGING_CANDIDATE`, port `8002`, main test database `EDUSPHERE_OWNER` / `XEPDB1`, 37 fixed tables unchanged.

| # | Acceptance area | Live status | Evidence |
|---|---|---|---|
| 1 | Oracle health and schema/procedure integrity | PASS | 37/37 tables; two valid procedures; API HTTP 200 |
| 2 | Question bank cross-role isolation | PASS | 9/9 reads; authors cannot access others; student denied |
| 3 | Quiz lifecycle, attempted-answer-key locking, grade persistence | PASS | quiz 104, attempt 166, persisted 10/10 |
| 4 | Marks/answer visibility matrix | PASS | all four N/N, N/Y, Y/N, Y/Y; flags restored N/N; cross-student denied |
| 5 | Multiple attempts/maximum/highest score | PASS | quiz 124, attempts 186/187, 10/10 then 0/10, final 10/10, third denied |
| 6 | Manual LONG_TEXT grading | PASS | quiz 125 attempt 188; auto 4/10, reviewed 9/10 |
| 7 | Atomic rollback on failed database write | PASS | quiz 126 attempt 189; failed oversized notes rolled back, then valid review 9/10 |
| 8 | Expiry and post-deadline finalization | PASS | quiz 127 attempt 190; expired writes blocked, saved answer 10/10 |
| 9 | Concurrency, autosave, submit, no duplicate marks | **PASS** | quiz 128; attempts 191 and 192; four simultaneous submits => one success, autosave race consistent; no 5xx |
| 10 | Oracle session count / latency benchmark | PENDING LIVE | Next package contains bounded GET benchmark, optional V$SESSION read-only sampling |
| 11 | Windows production Vue build + authenticated UI workflows | PENDING LIVE | Next package includes PowerShell build runner and manual checklist |

**Progress: 9/11 groups (81.8%).** Passing either remaining group reaches 10/11 (90.9% and exceeds the numerical 85% threshold), but this is **not permission to skip critical tests or promote immediately**. Frontend end-to-end security must also pass. Performance improvement requires measured baseline and/or Oracle session observations, not only HTTP success.

**No code or database schema changes were made in this testing step.**
