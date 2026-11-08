# Login Redis activation - 7 November 2026

## Completed scope

Started the existing local persistent Redis using `Backend/scripts/start_local_redis.py`. The sandbox invocation failed; the approved escalated invocation reported Redis ready. Existing persistent data was retained. No application code, `.env`, account, role, table or authentication rule changed.

Read the NBP context, latest login recovery report and saved relevant Auth milestone/API extension source (compilation pages 26, 27 and 224). This operational recovery requires no business or schema decision.

## Verification

- Live API (8000) and frontend proxy (5173): login with a deliberately unknown diagnostic identifier returned **401 INVALID_CREDENTIALS**, confirming normal credential validation instead of dependency failure. No customer credentials were used.
- Both endpoints returned **200** for the JSON Google challenge request; no challenge contents were printed. Full Google provider sign-in was not tested.
- Focused isolated PostgreSQL/Redis authentication tests: **3 passed, 20 deselected**, in 16.85 seconds. Covered registration/verification/login/profile/logout, refresh rotation/replay revocation and session dependency failure protection. One existing Starlette/httpx deprecation warning.

## Changed files

- This report.
- `docs/00-READ-FIRST/Travelly_NBP_Codex_Context.md`.

## Deferred scope, blockers and next dependency

No current Redis blocker remains. Retry login with valid credentials. Redis must stay running; automatic startup/service registration remains deferred. If Redis stops, use `.\.venv\Scripts\python.exe Backend\scripts\start_local_redis.py` from the project root in a normal terminal. Live user password login and full Google provider interaction were not performed.
