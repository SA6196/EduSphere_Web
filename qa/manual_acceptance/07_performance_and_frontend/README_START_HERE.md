# EduSphere main DB — acceptance stage 10: read-only resource benchmark

**Scope:** Tests `EduSphere_Web_Optimized_Secure_Merge_STAGING_CANDIDATE` on `127.0.0.1:8002` against main testing schema `EDUSPHERE_OWNER` / `XEPDB1`. Existing 37 tables and all previous quiz fixtures are unchanged. No SQL migrations, DML, attempt creation, mark release, or deletion.

## Confirmed previous live results

- 37/37 tables and two valid start/submit procedures.
- Question-bank role isolation, correct quiz grading and attempted-key lock.
- All four marks/answer review publication combinations; other-student access denied.
- Highest score retained after 10/10 and 0/10 attempts; attempted third attempt denied.
- Manual `LONG_TEXT` grade persisted as 9/10; deliberate Oracle statement failure rolled back all partial writes.
- Oracle-side quiz expiry, saved-answer finalization, no post-expiry changes.
- Four-request duplicate-submit race and autosave-versus-submit race: one submit, one grade, no leak, consistent saved answer; quiz `128`, attempts `191` and `192`, QA tag `F5DEF20FB1`. **Status: 9 of 11 acceptance groups passed.**

## Run in PowerShell

Keep your existing environment and candidate backend on **port 8002**, preferably using the four-worker **Waitress** server in `Backend/serve-windows.ps1`. In a separate backend PowerShell window: `cd $backend` then `.\serve-windows.ps1 -Port 8002 -Threads 4` (or keep your existing Waitress instance if already running). **Only one** server should bind port 8002. Use a separate PowerShell terminal with your Python virtualenv active:

```powershell
$backend = 'C:\Users\hamza\Downloads\EduSphere_Web_Optimized_Secure_Merge_STAGING_CANDIDATE\EduSphere_Merged_Candidate\Backend'
# Adjust the above path to the working Backend folder you have actually configured.
python verify_main_connection.py --main-backend "$backend" --api
python -m unittest -v test_performance_offline.py
python verify_main_performance.py --main-backend "$backend" --report performance_results.json
```

The script asks for confirmation `RUN READONLY PERFORMANCE CHECK`, then the **student** and **instructor** logins once each. You can use your existing local `FINAL_S6` and `FINAL_I2` accounts. Passwords are entered through a hidden prompt, not saved. Normal login audit rows may be written by the application, and some Django GET endpoints may log access depending on the application configuration; **all measured API requests sent by the verifier are GET**, without explicit mutation calls.

Default test loads are intentionally bounded: six GET endpoints, two warmups per endpoint/mode, **12 sequential measured GET requests** and **12 measured requests arranged in bursts of four concurrent GETs** per endpoint. This is a small functional/resource acceptance benchmark, **not** a stress-test or SLA certification.

Monitored endpoints include database health, current user, student's attempt history, student's marks, student dashboard, and instructor's question bank. They use the existing backend permissions. The JSON output contains only aggregate timing/status metrics and Oracle session *counts* if authorized; it contains **no credentials, tokens, user IDs, question text or response bodies**. Send the `performance_results.json` and terminal output back for analysis.

### Optional comparison with previous build

If the earlier `EduSphere_Web` backend is still running safely on port 8000 against the same main testing schema, you **may** add `--baseline` to separately time the same read-only requests:

```powershell
python verify_main_performance.py --main-backend "$backend" --baseline --report comparison_results.json
```

This is optional. Do not start an additional old app or change its port/settings solely for this check if inconvenient. Both backends might share the same Oracle login, so the Oracle session count covers **all** `EDUSPHERE_APP` processes, not one Django server. Timing differences are observational; process load, Oracle cache state, table count in db-health, and app version can affect comparability. Do not interpret a faster run as proof of fewer physical Oracle connections.

## Oracle session measurement limitations

The benchmark attempts a read-only `SELECT COUNT(*) FROM V$SESSION WHERE USERNAME = 'EDUSPHERE_APP'` using the existing app account. If Oracle denies access (normal least-privilege configuration), the benchmark still times requests and labels the session metric **unavailable**. **Do not grant dictionary-wide privileges to the Django application.** Instead, an authorized DBA can use `ORACLE_DBA_SESSION_READONLY.sql` in SQL*Plus before, during, and after the run. A single before/after total is not conclusive when other applications share the account; monitor the trend over several batches, or isolate app processes temporarily if safe.

Recommended PowerShell memory snapshot during/after the benchmark (no third-party module needed):

```powershell
Get-NetTCPConnection -LocalPort 8002 -State Listen |
  Select-Object -ExpandProperty OwningProcess -Unique |
  ForEach-Object { Get-Process -Id $_ | Select-Object Id, ProcessName, WorkingSet64, PrivateMemorySize64 }
```

If this query is unavailable, use Windows Task Manager > Details and note the Python/Waitress PID and Working Set. Stable Oracle session counts *after warmup*, no persistent upward growth, no API errors, and acceptable p95 latencies under the same workload are the acceptance criteria. We should set numeric targets using your machine's actual baseline rather than invent a universal millisecond limit.

### Fail conditions and boundaries

HTTP codes other than 200, timeouts, transport errors, candidate not using `EDUSPHERE_OWNER`, a missing table, or unexplained session growth fail / block acceptance. If `V$SESSION` access is unavailable, **connection efficiency remains unverified**, even when HTTP tests pass. Credentials may produce ordinary login audit entries; there are no database writes from the measured GET requests. Leave previous QA data intact.

## Final frontend acceptance stage (11/11)

After the performance checks, run `Verify-FrontendBuild.ps1` from the same test package on Windows:

```powershell
.\Verify-FrontendBuild.ps1 -FrontendPath 'C:\path\to\EduSphere_Merged_Candidate\Frontend'
```

It runs `npm ci`, Vite production build with `VITE_API_BASE_URL=http://127.0.0.1:8002/api`, six JS smoke suites, and checks `dist/index.html`. `npm ci` intentionally replaces the local `node_modules` directory. It does not edit the application source or database. Then manually complete `WINDOWS_FRONTEND_MANUAL_CHECKLIST.md` for authenticated student, instructor and admin screens and verify an unreleased quiz does not leak marks, answers or course percentages.

**Do not promote the merged version automatically:** your ≥85% test-group gate requires 10/11 passing, but every critical security/grading/transaction check must pass. Full release still requires the Windows UI acceptance and a reviewed resource-efficiency measurement.
