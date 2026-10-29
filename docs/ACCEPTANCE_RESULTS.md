# Recorded acceptance results — 18 October 2026

These observations are from the team's supplied Windows/Oracle terminal outputs, **not a rerun from GitHub Actions or this repository environment**. They apply to the exact tested merged build. All main-database QA rows were disposable; no cleanup was performed.

| Scope | Observed results / fixture |
|---|---|
| Main DB preflight | XEPDB1, EDUSPHERE_OWNER, 37 visible tables, two required quiz procedures VALID |
| Question-bank API roles | 9/9 live read-only checks passed (author-only IDs, cross-instructor 403, admin, student denial) |
| First quiz lifecycle | tag `E7808E9C43`, quiz 104, attempt 166: 10/10 persisted in question/header/component grades, hidden until released, answer keys locked |
| Visibility matrix | Quiz 104/attempt 166: N/N, N/Y, Y/N, Y/Y expected result/review statuses; cross-student denial and restoration to N/N passed |
| Multiple attempts | tag `CECE5E651A`, quiz 124, attempts 186/187: 10/10 then 0/10; component mark remained 10/10; third attempt rejected |
| Manual grading | quiz 125 / attempt 188, quiz 126 / attempt 189: auto 4/10, reviewed final 9/10, rubric feedback and role checks passed |
| Atomic rollback | Quiz 126 / attempt 189: intentionally oversized notes rejected; header/question/component marks unchanged, then valid review succeeded |
| Expiry | tag `E55F3A934B`, quiz 127/attempt 190: expired reads/writes denied; pre-expiry draft finalized and graded 10/10 |
| Concurrency | tag `F5DEF20FB1`, quiz 128/attempts 191/192: only one of four concurrent submits succeeded; autosave/submit race produced one grade per attempt; best mark stayed 10/10 |
| Frontend | Windows Vite build passed (80 modules); four frontend smoke suites, 16 predictor and 4 HTTP-coalescing tests passed |
| Local API benchmark | Same student/instructor on both versions; 288/288 GET requests HTTP 200 (144 per version); four-thread Waitress comparison |

## Measured performance (p95 milliseconds)

These are **12 observations per endpoint and mode per server** plus warmups; numbers vary between runs. Smaller is faster. Original server port 8003; merged port 8002.

| Endpoint/mode | Original | Merged |
|---|---:|---:|
| Instructor question bank, sequential | 63.3 | 33.1 |
| Instructor question bank, four-worker | 61.5 | 31.2 |
| Attempt history, four-worker | 29.9 | 17.2 |
| Student marks, sequential | 28.5 | 28.6 |
| Student dashboard, sequential | 26.8 | 31.0 |
| Student marks, four-worker | 6.3 | 22.8 |
| DB health, sequential | 193.8 | 224.7 |

The query-batching improvement is supported by repeated question-bank timings. **Not all endpoints improved.** DB health performs a different check in each version (31 versus 37 names); not an apples-to-apples measure. Do not state an overall application speedup from this table.

## Remaining gates / limitations

- `EDUSPHERE_APP` does not have `V$SESSION` access. **Actual Oracle connection/session-count reductions are unverified.** Use an authorized DBA for a separate read-only capture.
- The team's automated Windows frontend build passed; complete manual browser acceptance across student/instructor/admin workflows is still outstanding.
- The project has not undergone a full internet-facing security audit, backup-restore exercise or sustained multi-user load test.
- The agreed 85% *test-group* threshold was exceeded; it is **not** 85% code coverage. Critical authorization and transaction checks passed in the tested fixtures only.

**Release recommendation:** Good course project and controlled demonstration build. Review deployment checklist and outstanding gates before public hosting.
