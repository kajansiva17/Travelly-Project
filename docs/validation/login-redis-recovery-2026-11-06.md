# Login dependency recovery - 6 November 2026

## Completed scope

### Repeat recovery after the latest login report

Rechecked the reported login issue on 6 November: PostgreSQL was healthy, Redis was unavailable, and both live API and frontend proxy returned 503. The existing Redis helper again failed inside the sandbox and succeeded with approved escalation. Existing persistent data was retained; no application source, `.env`, account or role was changed.

After recovery, both ports returned **401 INVALID_CREDENTIALS** for a deliberately unknown diagnostic account, and Google challenge returned **200** with the required JSON request body. An initial challenge probe without JSON returned the expected 415; correcting the probe required no application change. The focused registration/verification/login/profile/logout, refresh rotation/replay and dependency-failure tests passed again: **3 passed, 20 deselected**, in 13.78 seconds. Fixtures used an isolated PostgreSQL schema and Redis namespace. No customer credentials or live Google provider round trip were used.

Only this report and the NBP context were updated. Automatic Redis startup remains deferred; the next runtime dependency is keeping Redis available. A real user login can now be retried from the refreshed login page.

Reproduced `503 AUTH_DEPENDENCY_UNAVAILABLE` through both the API on port 8000 and frontend proxy on port 5173. PostgreSQL answered `SELECT 1`; configured Redis PING timed out. This matches the earlier dependency failure, not a rejected password or frontend form defect.

Ran the existing `Backend/scripts/start_local_redis.py`. Its sandboxed invocation failed; the approved escalated invocation restored Redis with its original configuration and persistent data. No account, credential, environment value, authorization behavior, table or application source was changed. Configuration was loaded programmatically for health checks without printing secrets. Authentication retains its required dependency-failure protection.

Consulted the current context, earlier recovery delivery report and relevant saved Auth contract/API extension (compilation pages 26 and 224). No business or data contract amendment was needed.

## Verification

- Live API and frontend proxy: Google challenge **200**; only status was printed, not challenge contents. Provider configuration is present now, unlike the earlier report. A live Google account round trip remains untested.
- Live API and frontend proxy: password login with a deliberately unknown test identifier returns **401 INVALID_CREDENTIALS**, replacing the dependency error.
- Focused real PostgreSQL/Redis tests: **3 passed** in 13.72 seconds. Covered successful registration/verification/login/profile/logout, refresh rotation/replay revocation, and session-store fail-closed behavior. Existing fixtures isolate their database schema and Redis namespace.
- Initial test invocation used an in-repository temporary directory and hit the deliberate private-storage boundary: three fixture setup errors. Reran with pytest's normal external temporary directory; all three passed. No storage boundary was weakened.

## Changed files

- `docs/00-READ-FIRST/Travelly_NBP_Codex_Context.md`
- This report.

## Deferred scope, blockers and next dependency

No current dependency blocker remains for password login. Reload `/login` and retry with valid account credentials; no customer password was used during diagnosis. Redis must stay running. After a local restart, run `.\.venv\Scripts\python.exe Backend\scripts\start_local_redis.py` from a normal terminal at the project root before using login. Automatic Windows boot/service registration was not installed. Full Google provider interaction remains separate.
