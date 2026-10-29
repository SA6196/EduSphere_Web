# Security policy and reporting

This is a university course-project release candidate. **Do not send credentials, connection strings, student private records, access/refresh tokens or live Oracle data in GitHub issues.** For a potential vulnerability, contact the repository maintainers privately through an approved project-team channel; do not publish exploit details until the issue is fixed.

## Protected surfaces

- JWT authentication and role checks are enforced in Django, not just Vue menus.
- Question-bank access is scoped by instructor ownership and assigned offerings.
- Student quiz attempts must be owned by the caller. Question answer keys are not serialized to active attempt content.
- Mark release requires `ALLOW_MARK_VIEW=Y`; solution review additionally requires eligible review and `ALLOW_ANSWER_REVIEW=Y`.
- General marks, semester marks and dashboard-derived values redact unpublished quiz grades.
- Draft answer edits are blocked after expiry or submission; multi-step scoring uses transaction rollback.

These were exercised on selected live QA fixtures. They are not a guarantee of complete penetration-test coverage. API changes must add deny-case regression tests. Do not add privileged Oracle session views or credential-bearing diagnostics to student-accessible endpoints.

## Dependencies, secrets and deployment

- Keep runtime `.env` local; `.env.example` must contain placeholders only.
- Never commit `Database/Sample_Data/02_accounts.generated.sql` or sample-user passwords/hashes.
- Run CI checks before merging; scan new contributions for secrets; enable protected branches and dependency alerts on GitHub when configured.
- Public deployment requires a separate review of HTTPS, CSRF/CORS, login rate limits, permissions, runtime database grants and backup restoration.
