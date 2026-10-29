# Deployment checklist

**Status:** controlled course demo/local network ready after local browser checks; **not certified for public internet hosting**. Do not expose Oracle or the Django development server to browsers.

## Recommended topology

```text
HTTPS reverse proxy / static web server
   ├── /         => contents of Frontend/dist (Vue SPA fallback)
   └── /api/     => private Django + Waitress 127.0.0.1:8002
                                 |
                                 └── EDUSPHERE_APP (Oracle ODBC) => XEPDB1
```

Build the frontend with the correct API base URL. For same-origin deployment, verify how `VITE_API_BASE_URL` is set at build time and proxy `/api/` accordingly; the default in source targets localhost and is **not** an internet-ready setting. Allow SPA deep-link fallback to `index.html` in the reverse proxy.

## Before a publicly reachable deployment

- [ ] Set unique strong `DJANGO_SECRET_KEY`, **different** `JWT_SECRET`, `DEBUG=False`, restrictive `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS` and browser/HTTPS protection settings. Review session/token storage and refresh-token lifetime.
- [ ] Confirm HTTPS, reverse-proxy timeouts, request/body size limits, trusted proxy headers and no dev origins exposed.
- [ ] Add and verify brute-force/login rate controls and monitoring (not claimed as implemented).
- [ ] Review API permissions for *every* role; verify no pre-release answer, attempt, score or derived grade leakage.
- [ ] Restrict database network ingress; least-privilege Oracle runtime account; audit broad development grants.
- [ ] Back up Oracle data before every planned change and actually test restoration.
- [ ] Never execute `Database/01_INSTALL_FRESH.sql` against an already populated owner; no schema migrations for routine application deployments.
- [ ] Establish uptime/log monitoring and DBA-level Oracle session metrics; benchmark concurrent traffic on representative records.
- [ ] Serve compiled `Frontend/dist/`; use fixed-size Waitress workers for local Windows deployment. Do not use `manage.py runserver` for production.
- [ ] Perform browser UAT on all roles and refresh/network failures, then freeze a version/tag.

## Windows demo

```powershell
cd Backend
.\.venv\Scripts\Activate.ps1
.\serve-windows.ps1 -Port 8002 -Threads 4
# Frontend in another shell: npm ci, npm run build, then serve dist using a reviewed static web server.
```

Only bind Waitress to a public interface after configuring reverse-proxy HTTPS and a deployment review. The bundled script deliberately binds to loopback by default.
