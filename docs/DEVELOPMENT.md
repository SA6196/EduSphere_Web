# Local development and troubleshooting

## Setup

See root `README.md` for full installation steps. Keep `Backend/.env` and `Frontend/.env.local` on your machine, outside Git. The committed `.env.example` files only contain placeholders. Generate two distinct strong Django/JWT secrets for local use.

Example backend values:

```dotenv
ODBC_DSN=EduSphereOracle
ODBC_USER=EDUSPHERE_APP
ODBC_PASSWORD=YOUR_LOCAL_PASSWORD
ODBC_CONNECTION_STRING=
ORACLE_SCHEMA=EDUSPHERE_OWNER
DJANGO_SECRET_KEY=YOUR_UNIQUE_RANDOM_SECRET
JWT_SECRET=YOUR_OTHER_RANDOM_SECRET
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
ODBC_CONNECTION_MAX_IDLE_SECONDS=300
ODBC_CONNECTION_MAX_AGE_SECONDS=1800
```

The frontend `.env.local` uses `VITE_API_BASE_URL=http://127.0.0.1:8002/api`. Never put database/JWT secrets in a Vite variable: `VITE_` variables are exposed to browser bundles.

## Common PowerShell commands

```powershell
# With the backend venv active, inside Backend/
python manage.py check
python scripts\test_odbc.py
.\serve-windows.ps1 -Port 8002 -Threads 4

# In a second terminal, inside Frontend/
npm ci
npm run dev
npm run build
```

For `waitress-serve` missing: `python -m pip install -r Backend/requirements.txt` while the correct environment is active; call `& 'C:\path\to\venv\Scripts\waitress-serve.exe' ...` when shell PATH is incorrect.

## Common issues

| Symptom | Check |
|---|---|
| `python` resolves to another person's missing path | Recreate the venv on this machine; don't copy `venv/` from a teammate. Check `Get-Command python`. |
| Port 8000 returns Uvicorn JSON `{"detail":"Not Found"}` | Port may belong to an unrelated WSL relay. Use another port (e.g. 8002/8003); inspect `Get-NetTCPConnection`. |
| `expected_tables: 31` on old backend | Outdated manifest in old Python code. Oracle still has 37; use the merged health view. |
| ODBC cannot connect | Check DSN's architecture (64-bit), installed Oracle driver, credentials, `XEPDB1`, `ODBC_CONNECTION_STRING` override and `python scripts/test_odbc.py`. |
| Student cannot see answer key or grade | Expected before publication; use instructor-controlled flags and legitimate student role/session to test. Do not remove authorization guards. |
| Original and merged server performance differs | Use the same instructor/student accounts, four-thread workers, warmups, and quiet database; database-health checks have different work (31 vs 37 names). |
| npm `esbuild` install-scripts warning | Confirm `npm run build` succeeds. Do not blanket-approve unknown install scripts without reviewing package provenance. |

## Before committing

Run offline tests, frontend smoke/build, and schema checksum verification. Do not commit passwords, tokens, `.env`, generated Oracle account SQL, raw production logs, virtual environments or `node_modules`.
