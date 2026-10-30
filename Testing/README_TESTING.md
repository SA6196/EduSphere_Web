# Testing & authorization

- `verify_question_bank_live.py`: *read-only* API test. Start the Django API and provide instructor/admin/student credentials at the prompt. No data is intentionally changed.
- `verify_question_bank_staging_writes.py`: **WRITES TEST DATA**. Only run against an isolated staging owner/PDB clone (e.g. `EDUSPHERE_STAGE_OWNER`), not the seeded `EDUSPHERE_OWNER` installation.
- `verify_staging_api_quiz_lifecycle.py`: **WRITES TEST DATA** and explicitly expects the separate verified staging backend. It can create course/quiz records and submissions.
- `audit_frontend_quiz_wiring.py`: static audit of Vue API paths against backend routes.
- `test_api_verifier_offline.py`, `test_question_bank_permissions_offline.py`: offline tests for the verifier / permission rules.

The previous project's live staging checks established read-permission isolation and attempted-question locks in that environment. This packaged copy needs **independent end-to-end testing** on the recipient's machine.

## Course Drop extension (offline-only acceptance)

- `python -m unittest discover -s Testing -p test_course_drop_backend.py -v` — isolated service/repository authorization, atomic audit, and guarded status transition tests. No Oracle/Django dependencies required.
- From `Frontend`: `node --test course_drop.test.mjs` — JS syntax, endpoint and UI confirmation logic tests.
- Live Django/Oracle and Vue browser checks are not yet passed; see `docs/COURSE_DROP.md`.
