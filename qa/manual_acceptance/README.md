# Historical live acceptance verifiers — OPT-IN ONLY

These packages come from the team's **October 2026 main-database acceptance tests** and are included as reproducibility references. They are **not generic first-run scripts**, **not part of GitHub Actions**, and **may create persistent test records**. Several assume `EDUSPHERE_OWNER`, localhost port 8002, fixture IDs or account names that do not exist on another machine. Some tests deliberately trigger rejected writes to check rollback.

Before any live run: inspect the whole verifier and its README; verify the exact target schema, Oracle backup, roles, fixture IDs, user permission, no personal records and explicit confirmation string. Use a disposable Oracle clone rather than a classroom production owner. Scripts intentionally do not clean up existing QA records. For a new installation, adapt fixture lookup and owner guards only after code review; do not disable authorization checks.

Folders: `01_question_bank_and_lifecycle`, `02_visibility`, `03_multiple_attempts`, `04_manual_grading_and_rollback`, `05_expiry`, `06_concurrency`, `07_performance_and_frontend`.

Read `docs/ACCEPTANCE_RESULTS.md` for the previously observed outputs; do not mistake an old PASS log for tests performed on a new fork.
