# EduSphere merged candidate — QA and promotion gate

**Source:** EduSphere_Web baseline with selective optimizations. **No changes to main Oracle 37-table schema or data.**

## Offline results

| Test group | Result | Scope |
|---|---|---|
| Python backend source and security tests | 63/63 PASS | Mocked Oracle, AST-extracted service logic, repository SQL guards, connection UOW |
| Grading algorithm | 13/13 PASS | `_score_question` scoring cases; does not write Oracle |
| Attendance predictor | 16/16 PASS | Calculation and frontend wiring |
| HTTP coalescing | 4/4 PASS | GET dedup, POST not dedup, auth-token isolation, abort semantics |
| Frontend smoke | 4 suites PASS | General, cross-role, error, admin |
| Vue SFC compilation | 43/43 PASS | Source components, not a complete Vite bundle |
| Frontend→Django quiz routes | 17/17 PASS | Static endpoint/wrapper/caller mapping |
| Django code audits | 3 PASS | Admin audit has three explicitly skipped optional legacy SQL-file checks |
| Original SQL unchanged | 14/14 identical | Exact byte comparison against Web source |

**Offline change-group gate: 13/13 groups implemented and checked = 100%.** This exceeds the requested 85% *development* threshold. It does not supersede the *live staging* promotion requirement.

## Staging/production gate — NOT YET PASSED

- [ ] `python manage.py check` with Django dependencies installed in the merged staging backend.
- [ ] Oracle staging account verified as `EDUSPHERE_STAGE_APP`, 37 staging tables, 0 original tables visible.
- [ ] `GET /api/db-health/` reports expected_tables=37 on staging.
- [ ] Admin, instructor A, instructor B, student role isolation; both read and attempted-question write locks.
- [ ] Quiz start/save/autosave/expiry/submit, with blocked late answer writes and permitted expired finalization.
- [ ] Student grade release OFF: submission returns no grades; result/answer-review blocked; attempts, semester marks and dashboard reveal none.
- [ ] Student grade release ON: rightful student can view permitted result; other student blocked; answer review obeys separate switch and exhaustion/close rule.
- [ ] Manual LONG_TEXT grade held pending review; finalized grades and best-attempt synchronization correct; Oracle rollback on forced failure.
- [ ] All existing assessment types and numeric grading policies unchanged, with quiz/component maximum mismatch policy reviewed.
- [ ] Windows `npm ci`, `npm run build`, browser click-path smoke and staging API URL verification.
- [ ] Original vs merged Oracle session count/latency benchmark. No regression in p95 API times beyond agreed margin.
- [ ] Written backup/rollback plan and team approval.

**PROMOTION STATUS: BLOCKED until these checks pass.** A serious permission/grade leak prevents release even if >85% aggregate checks pass.
