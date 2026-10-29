# Changelog

## 2026-10-18 — GitHub handoff packaging (documentation only)

- Retained all bundled code, tested Oracle DDL/DML and Python/Node tests from the merged candidate without editing their runtime behavior.
- Added a GitHub README, architecture/DB/development/security/testing/deployment guides, CI workflow, contributor policy, file/API indexes and repository integrity verification.
- Included opt-in archived QA verifier source under `qa/manual_acceptance`; these scripts do not run in CI and may create database rows.
- Reconciled the main README's status with live October 18 Oracle acceptance results. Older in-package status documents are retained for traceability and may say 'staging candidate' or '31 tables'.

## 2026-10-17 — Web + Optimized security merge (baseline source)

- Oracle connection reuse, request read cleanup, idle/age recycling and diagnostics.
- Optimized matching and question-bank lookups, deduplicated simultaneous identical frontend GET requests and attendance grouping.
- Added full 37-table health check and configurable schema owner for quiz stored procedures.
- Closed student API leaks in grading submission, unreleased mark surfaces and expired attempt handling.
- Preserved Web baseline's typed business exceptions, Oracle schema and SQL installer.

See `00_START_HERE_MERGED.md` for the original candidate change log and offline QA notes.
