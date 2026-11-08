# Login dependency recovery - 5 November 2026

## Completed scope and cause

The supplied Login screenshot showed `The service is temporarily unavailable` for password login and Google preparation. The live API and Vite proxy both returned `503 AUTH_DEPENDENCY_UNAVAILABLE` for the Google challenge. PostgreSQL answered `SELECT 1`, but the configured local Redis was unavailable and port 6379 was closed.

Redis is required for auth rate limits, login sessions, token revocation/rotation and Google challenge state. Returning 503 while it was unavailable was the required fail-closed behavior, not a form-layout or credential-validation defect.

Restarted the existing bundled local Redis with its existing configuration and AOF data directory. The first sandboxed start could read the AOF but could not open it for writing and exited with Permission denied. The approved restart outside the sandbox succeeded. No file ACL, persistent data, session policy, password, account, environment secret or application table was changed.

Added `Backend/scripts/start_local_redis.py`, a repeatable hidden background startup helper. It reads the app configuration, limits itself to local port 6379, reuses existing persistence, checks readiness and leaves an already running Redis untouched. The Python entry point avoids the machine's restriction on executing PowerShell script files. README now documents this command and distinguishes dependency failure from missing Google configuration.

## Verification

- Redis PING succeeds after restart.
- API and Vite proxy Google challenge now return `503 GOOGLE_NOT_CONFIGURED`, rather than dependency failure. This is the existing honest disabled-provider state.
- Real Chrome through the running Vite frontend: Login shows `Google sign-in will be available soon`; the dependency-error message is absent. One deliberately unknown, syntactically valid test identifier receives `401 INVALID_CREDENTIALS`, proving normal password validation is reachable. No customer credentials were read or supplied.
- Focused real PostgreSQL/Redis tests: **3 passed**. Covered successful registration/login/profile/logout, session-store fail-closed behavior/bad bearer handling, and refresh rotation/replay revocation. Tests use their existing isolated schema and Redis namespace.
- Startup helper executed twice against the restored service: both report already ready and start no additional process.
- No frontend source changed, so frontend build and unrelated suites were not rerun.

## Changed files

- `Backend/scripts/start_local_redis.py`
- `README.md`
- This report
- `docs/00-READ-FIRST/Travelly_NBP_Codex_Context.md`

## Deferred scope, blockers and next dependency

- Password-login dependency recovery is complete; no current blocker remains for retrying it with valid credentials.
- Google provider configuration remains separate pending setup. No placeholder client ID or bypass was introduced.
- Redis must remain running during development. The helper is an explicit startup command, not a Windows service or boot-time task.
- The previously existing `docs` directory was absent at task start. Current auth requirements were consulted in the saved user-supplied PDF extraction under `.tools/context-intake-2026-11-05/pages.json`, including the Auth contract and extension. This task recreates only this report and a concise continuity context; it does not restore or rewrite the missing full contract collection.
- Next action: reload `/login` and retry. A previously displayed form error remains until reload or another submission.
