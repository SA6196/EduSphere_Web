# Contributing to EduSphere

1. Create a feature branch from the reviewed baseline and document the behavior changed.
2. **Schema freeze:** do not modify the 37 existing `CREATE TABLE` definitions, constraints or original installer/data scripts without explicit design approval. Django ORM migrations do not manage Oracle LMS tables.
3. Put authorization in Django services, not solely in Vue; keep Oracle writes parameterized and transactional. Preserve the tested answer-key, mark-release, attempt ownership, expiry, grading and rollback protections.
4. Write focused tests first for security-sensitive changes (including unauthorized roles and forced direct API calls). Run `docs/TESTING.md` offline suite and Windows frontend build before a PR.
5. Live Oracle tests require permission, disposable fixtures and an explicit opt-in. Never run QA writes against real student data; avoid cleaning up other developers' fixtures.
6. Include reproduction steps, affected source files, expected/actual outcomes and performance numbers when relevant. Do not put real secrets, login tokens, student records or privileged connection logs in an issue or PR.
7. Request review from someone other than the author for auth, grading, database or release-policy changes. Update docs and the changelog when behavior changes.

Historical per-module READMEs may have stale counts/release metadata; the root README and `docs/` take precedence. Backups such as `repository_backup_commit43.py` are preserved as historical baseline files, not active router/service entrypoints; avoid importing them into production code.
