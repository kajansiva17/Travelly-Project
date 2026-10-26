# Travelly - Auth and Admin Application Review

Travelly's first runnable milestone uses FastAPI, SQLAlchemy, Alembic, Pydantic and PostgreSQL, with a React + Vite JavaScript/JSX frontend. The current migration creates `users`, `user_roles`, `vehicles` and `documents`, all from the approved twenty-table design. The latter two are private-evidence dependencies, not a vehicle operations module. Alembic also maintains its infrastructure `alembic_version` record. No SQLite, booking, fleet, ticket, payment, IVR, subscription or other later-module implementation is included.

Current Admin Review setup, restricted writer/provisioning/recovery and deployment checks: [Backend/ADMIN_REVIEW.md](Backend/ADMIN_REVIEW.md). The dated validation notes below describe the earlier Auth baseline; the current application-table inventory is four.

Current authentication rules and endpoints: [Auth extension contract](docs/03-API/03E-TRAVELLY-AUTH-EXTENSION.md). Provider setup, migration details and current test results: [26 October auth validation](docs/validation/auth-update-2026-10-26.md).

## Requirements

- Python 3.12+ and Node.js 20.19+ (Node 22.12+ or 24 also supported).
- PostgreSQL 16, database **travelly_dev**, application role **travelly_app**. Configuration rejects another database/user or SQLite.
- Redis 7+ for persistent session/revocation/rotation/rate-limit infrastructure. No session application table or in-memory production fallback.

The database owner must grant travelly_app CONNECT and CREATE on travelly_dev and USAGE/CREATE on the public schema. CITEXT is a trusted extension; an administrator can preinstall it with `CREATE EXTENSION IF NOT EXISTS citext WITH SCHEMA public` if application extension creation is restricted. Do not give the application superuser privileges. No PostgreSQL administrator credentials belong in application configuration.

## Local setup (PowerShell, from D:\Travelly)

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r Backend\requirements.lock.txt
Copy-Item Backend\.env.example Backend\.env
```

Edit Backend/.env with the real application password (URL-encode special characters such as @, %, # and /). Generate independent secrets using Python's `secrets.token_urlsafe(48)`; place them in JWT_SECRET and JWT_REFRESH_SECRET. Never commit .env. Do not copy .env.example over an already configured .env.

For an existing local Redis, set REDIS_URL. Bind development Redis to loopback; configure `appendonly yes`, `appendfsync always`, `maxmemory-policy noeviction`. Production requires authenticated TLS (`rediss://`), secure hosting and HTTPS. Test fixtures require an actual Redis instance, not a fake/in-process substitute.

If Docker is available, a local Redis can be started using:

```powershell
docker run --name travelly-redis -p 127.0.0.1:6379:6379 -v travelly-redis-data:/data -d redis:8 redis-server --appendonly yes --appendfsync always --maxmemory-policy noeviction
```

This workspace's Windows development Redis, when downloaded, is under ignored `.tools/redis`. It is a community Windows build from https://github.com/redis-windows/redis-windows, compiled from Redis source; production deployments should use the official Redis distribution on Linux. Its source release SHA256 is `6de5cc7f5adbf97b5928b13766383d4ad424626ef3d8b313ffff12d820ec6fc1` for Redis 8.10.2 Windows x64 Cygwin. It is not a project dependency or checked-in binary. To restart the downloaded local development server:

```powershell
& .\.tools\redis\Redis-8.10.2-Windows-x64-cygwin\redis-server.exe /cygdrive/d/Travelly/.tools/redis-dev.conf --dir /cygdrive/d/Travelly/.tools/redis-data
```

If the local PostgreSQL log reports `Role "travelly_app" does not exist`, run this once in your own terminal:

```powershell
.\.venv\Scripts\python.exe Backend\scripts\setup_local_postgres.py
```

It prompts for your PostgreSQL administrator username/password locally, creates the missing application login using the password already in Backend/.env, creates travelly_dev if missing, and grants the permissions needed for migrations/tests. It does not save the administrator password, reset an existing role password, change an existing database owner, or create application tables.

Run the migration and API:

```powershell
.\.venv\Scripts\python.exe -m alembic -c Backend\alembic.ini upgrade head
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir Backend --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000/docs for API documentation. In a second terminal:

```powershell
Set-Location Frontend
npm.cmd ci
npm.cmd run dev
```

Open http://127.0.0.1:5173. Vite proxies /api to 127.0.0.1:8000. For separate hosting, copy Frontend/.env.example and set VITE_API_URL to the API origin and add the frontend origin to Backend's CORS_ORIGINS JSON list. A production host must serve index.html for client routes and proxy /api or configure VITE_API_URL before building. .env files and local binaries are gitignored.

## API and account behaviour

| Method | Endpoint | Behaviour |
|---|---|---|
| POST | /api/v1/auth/register | Atomically create account and APPROVED Passenger membership; return 201 safe profile, no tokens |
| POST | /api/v1/auth/login | Email/international phone + password; return signed access and refresh JWTs |
| POST | /api/v1/auth/refresh | Rotate both tokens atomically; retain absolute expiry; reuse revokes the session family |
| POST | /api/v1/auth/logout | Matching access + refresh credentials; revoke current session, return empty 204 |
| GET | /api/v1/users/me | Current allowlisted profile and approved roles |
| GET | /api/v1/users/me/roles | All own memberships with independent approval states |
| POST | /api/v1/users/me/role-requests | Authenticated OWNER/DRIVER application; PENDING, no second account |

New registration requires full_name, email, phone_e164, password and accept_terms=true; preferred_language defaults to en (en/ta/si supported). Trim only outer email whitespace, validate a public email format and use case-insensitive uniqueness without Gmail alias rewriting. New/changed passwords require 12-128 Unicode characters, uppercase, lowercase, number and symbol, with no whitespace; passwords are never trimmed or truncated. Argon2id remains 64 MiB, 3 iterations, parallelism 1. Existing passwords still work. International phone country code is required. Duplicate normalized contacts return helpful 409 registration errors. Invalid fields return 422, malformed JSON/duplicate keys 400, unsupported type 415, oversized body 413. Errors use code/message/field_errors/trace_id, never secrets. Login failures are generic 401; temporary locks/throttles use 429 with Retry-After; dependency failures deny authorization with 503.

Contact verification is independent from Passenger membership. New password accounts are PENDING_VERIFICATION and must consume a valid email link before normal login/dashboard access. Existing accounts remain usable and can request verification from Profile. Registration returns the safe profile plus a resend capability and honest email-submission status, never login tokens. GIS Google sign-in supports completion and explicit authenticated Profile linking; only authoritative verified Google email skips Travelly email verification. Both signup methods create only the same APPROVED Passenger membership. Owner/Driver access requires its separate approved application and Admin Review; the frozen document checklist is unchanged. No public route grants ADMIN or approves roles. See the linked current contracts for the implemented document and review operations.

Access JWTs last at most 15 minutes; refresh JWTs use a different signing secret and audience, are accepted only by refresh/logout, and retain a seven-day absolute session lifetime. Only SHA256 refresh digests/session identifiers are stored in Redis. Redis atomically compares/replaces the current digest; stale signed refresh reuse revokes that sid. Database account/role state and authentication version are checked on protected reads, not trusted from JWT role claims. Logout invalidates that sid's access/refresh credentials. Verified-email password recovery uses single-use, expiring links and revokes all previous sessions without changing Google identity or roles. Client refresh requests are serialized. Tokens live only in browser memory: reloading/closing the page requires sign-in again. Remember me stores only the identifier.

The frontend now follows the supplied Passenger, Owner, Driver, Register and Login visual blueprints in Frontend/design-reference. It uses the supplied public/images assets intact, a cream/deep-burgundy/warm-neutral palette, responsive React layouts and the existing account/role-application integration. These are public informational pages; no later-module backend was added. See Frontend/README.md for routes, asset handling and the 25 October frontend verification results.

## Verification

```powershell
.\.venv\Scripts\python.exe -m alembic -c Backend\alembic.ini current
.\.venv\Scripts\python.exe -m pytest -c Backend\pytest.ini Backend\tests -q
npm.cmd --prefix Frontend run build
```

The integration suite runs the actual Alembic migration in a new random `travelly_test_<uuid>` schema **inside travelly_dev as travelly_app**, then drops only that schema. It never truncates public application data. Redis tests use a random namespace and remove only their own keys, never FLUSHDB. The application role therefore needs CREATE SCHEMA permission on travelly_dev for tests. Security tests cover hashing, input boundaries and JWT claim/type/signature/expiry validation. Integration tests cover registration atomicity/races, constraints, generic login/lockout, refresh replay/concurrency, session-specific logout, live account restrictions, independent roles and fail-closed dependencies.

Validation on 24 October 2026:

| Check | Result |
|---|---|
| Configured PostgreSQL service, localhost:5432, travelly_dev / travelly_app | PASS: revision 0001_auth applied |
| Alembic schema check on the configured service | PASS: no new upgrade operations detected |
| Backend suite against configured PostgreSQL and Redis | PASS: 35 tests; fresh test-schema migration/auth journey also rechecked after the extension-comparison adjustment |
| Frontend production build | PASS |
| Browser Register → Login → Profile → Owner/Driver PENDING applications → Logout | PASS against the restarted backend and configured PostgreSQL service; desktop/mobile layout checks also pass |

The earlier connection blocker was a missing PostgreSQL travelly_app login; provisioning that login resolved it. Final verification uses the live Backend/.env and the configured localhost:5432 service. The earlier isolated cluster under ignored `.tools/test-postgres` was test infrastructure only. The temporary account created by the final browser check was removed after logout. No existing PostgreSQL password or server authentication rule was changed by the implementation.

The configured database already contains PostGIS's extension-owned spatial_ref_sys table. It is infrastructure, not a Travelly application table. Alembic compares the application schema while excluding tables PostgreSQL identifies as extension-owned, so it does not propose dropping shared extension infrastructure. The final catalogue check confirms exactly users/user_roles as application tables, plus Alembic metadata and that pre-existing PostGIS table. The backend test suite has one non-failing upstream TestClient/httpx deprecation warning.

Source authority: docs/00-READ-FIRST/00-TRAVELLY-BACKEND-BUILD-READINESS.md, 01-TRAVELLY-NBP-FINAL-DECISIONS.md and 02-TRAVELLY-AUTH-MILESTONE-CONTRACT.md. The 24 October 2026 implementation amendment records the user's explicit JWT-refresh and role-application scope update; source PDFs remain unchanged. The other eighteen application tables are not migrated.
