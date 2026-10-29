# Provenance and reproducibility

The `Backend/`, `Frontend/`, `Database/` and `Testing/` trees were copied unchanged from `EduSphere_Web_Optimized_Secure_Merge_STAGING_CANDIDATE.zip` (the version whose live checks were reported October 17–18). **Packaging adds** README, docs, git config, GitHub Actions, integrity utilities and a historical opt-in QA archive under `qa/`.

To detect accidental changes, `docs/ORIGINAL_SOURCE_SHA256.json` records a SHA-256 for every shipped file inside those four source trees. `Testing/BASELINE_SQL_SHA256.json` specifically checks the original SQL installation/data files; run `python scripts/verify_repository.py` (checks SQL hashes and 37 tables).

Older files are retained deliberately, including older `Backend/README_SETUP.md`, `Backend/edusphere/version.py` and historical backup `repository_backup_commit*.py`, so there is no silent source deletion. Some contain outdated 31-table or staging-only labels: the current status is the root `README.md` and `docs/ACCEPTANCE_RESULTS.md`. These old comments are documentation debt, not permission to modify the schema.

Never include files from your local `.env`, generated demo accounts, `.git`, `node_modules`, `dist`, `.venv`, personal data or raw secrets in repository commits.
