# Verification strategy

## CI-safe / offline checks

From repo root with Python and `pytest`:

```bash
python -m pytest -q Testing/test_merge_security.py Testing/test_optimized_database.py Testing/test_handoff_package.py Testing/test_api_verifier_offline.py Testing/test_question_bank_permissions_offline.py
python Testing/check_actual_scoring_cases.py
python Testing/audit_frontend_quiz_wiring.py --project-root .
python scripts/verify_repository.py
```

From `Frontend/` with Node/npm:

```bash
npm ci
npm run build
node frontend_smoke_check.mjs
node frontend_cross_role_smoke_check.mjs
node frontend_admin_management_smoke_check.mjs
node frontend_error_smoke_check.mjs
node --test attendance_predictor.test.mjs request_coalescing.test.mjs
```

The CI workflow in `.github/workflows/ci.yml` runs those checks without any Oracle secrets. These are primarily source-based and mocked tests, not full browser or Oracle integration coverage.

## Existing backend audits

```bash
python Backend/scripts/admin_management_code_audit.py
python Backend/scripts/final_code_audit.py
python Backend/scripts/frontend_readiness_code_audit.py
```

Some older optional checks are marked SKIP by the scripts when non-bundled deployment SQL is absent. Such skips are not runtime failures.

## Live Oracle API acceptance

`qa/manual_acceptance/` contains copies of **explicitly opt-in**, historically main-database-oriented verifier scripts. Some scripts are pinned to fixture IDs or `EDUSPHERE_OWNER` and local port 8002. They are *not generic automated integration tests*: do not run them during CI, on public deployments, or on a database with real student data. Many **permanently create sample records** and intentionally inject invalid writes after a typed confirmation. Read each package README and inspect parameters/fixture guards before use.

Scopes exercised in the supplied Windows results:

1. Login and cross-instructor question-bank ownership.
2. Quiz lifecycle and immediate attempted-question answer-key lock.
3. Marks/answer-review visibility combinations and cross-student isolation.
4. Max-attempt gating and highest component grade.
5. Long-text grading, rubric validation, atomic rollback and release restrictions.
6. Expired attempt draft/read/write blocks and finalization.
7. Four-request submission and autosave/submit races.
8. Frontend production build and role-specific smoke tests.
9. GET performance under sequential/four-worker load.

See `docs/ACCEPTANCE_RESULTS.md`. **A passed fixture is not a claim that all possible races/security exploits have been excluded.**
