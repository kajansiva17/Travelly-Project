# Google sign-in and sign-up - 5 November 2026

## Completed scope

- Confirmed the existing official Google Identity Services script and rendered button are available on both Login and Register. The backend challenge supplies the public client ID, nonce and short-lived challenge; the browser sends the GIS credential to FastAPI without persisting it.
- The backend verifies the Google signature, audience, issuer, expiration, issue time, stable subject, nonce, and now the presence and boolean type of `email_verified`. Only verified Gmail/hosted-domain email is immediately authoritative; other Google email addresses continue through Travelly's existing email verification before a normal session.
- Existing Google-linked users are resolved by the stable Google subject. Matching email alone returns a conflict and never links accounts. Profile linking still requires the authenticated account, explicit confirmation, and the current password for password-based accounts.
- New Google registration requires the existing completion form, contact details and terms, and creates only an approved Passenger membership. It does not grant Owner, Driver, Admin or Super Admin access.
- The existing in-memory browser credentials, Redis-backed Travelly sessions, email OTP, password login, and password recovery remain in place.
- The existing `0004_auth_verification_google` migration already provides the nullable provider/subject pair and safe uniqueness/check constraints while preserving existing identities and roles. No extra migration/table was required.
- `PyJWT` and `cryptography` are already pinned in backend requirements; the frontend loads Google's official GIS client directly. No dependency installation was needed.
- No `.env` file or credential value was read, changed, or committed. GIS is initialized with the client ID returned by the backend challenge so its token audience matches backend verification.

## Changed files

- `Backend/app/services/auth_services.py` - require and type-check `email_verified`.
- `Backend/tests/test_auth_extension.py` - cover missing and malformed `email_verified` claims.
- `docs/00-READ-FIRST/Travelly_NBP_Codex_Context.md` - record completed work.
- This report.

The button, account-completion/linking routes, and existing migration were already present in the task worktree and were preserved.

## Verification

- Backend: `tests/test_auth_extension.py` and `tests/test_auth.py` — **80 passed**. This includes Google signature/claim/challenge/replay behavior, email conflicts, linking, Passenger-only role assertions, existing password/OTP/recovery behavior, and the migration checks.
- Frontend unit tests: **53 passed**.
- Frontend production build: **passed**. Vite reported the existing large-chunk advisory (>500 kB); the build completed successfully.
- Google and Chrome zoom browser tests: **9 passed**, including both Login and Register and actual Chrome zoom at 100%, 125%, and 200%.
- Authentication viewport-fit browser tests: **4 auth tests passed**, including no-scroll Login/Register desktop layouts. The fifth test in that file, which tests the unrelated landing booking panel, failed because its search panel extended to 987 px where the test expected at most 769 px. No booking code was changed.
- The full `auth-viewport-fit.spec.js` command therefore had one unrelated failure; this is not represented as a passing suite.

Automated browser tests mock GIS and use test credentials. A live Google account/provider round trip was not performed.

## Manual testing

1. Keep backend `GOOGLE_CLIENT_ID` set to the Google Web Client ID. The browser uses the public `client_id` returned by `POST /api/v1/auth/google/challenge`; the current GIS component does not read `VITE_GOOGLE_CLIENT_ID` directly, which keeps the GIS audience aligned with the backend verifier. If the frontend variable is retained, keep it equal to the backend value. Configure the authorized JavaScript origins in Google Cloud Console for the local frontend origin and the intended production origin. Do not commit either `.env` file.
2. Start PostgreSQL and Redis, then the FastAPI backend and Vite frontend using the project's normal local startup commands. Confirm `/api/v1/auth/google/challenge` returns a challenge rather than `GOOGLE_NOT_CONFIGURED`.
3. Open `/register`, choose **Continue with Google**, and complete the GIS prompt. Confirm Travelly asks for the remaining registration details and terms before creating the account. Verify a new account has Passenger access only; no Owner, Driver or Admin privileges are granted.
4. Open `/login` and sign in with that Google identity. Confirm the same Travelly account is used. For a third-party Google email, complete the existing Travelly email-verification step before expecting a normal session.
5. Try Google on an email already registered through password auth. Confirm Travelly reports that the account already exists instead of silently linking it. Sign in through the existing method and use Profile's explicit Google-link flow if desired; password accounts must confirm their current password.
6. Re-test email/password registration and login, email verification/resend, and forgot/reset-password flows. At 100% Chrome zoom, confirm Login and Register have no page scrolling on a desktop viewport such as 1366x768.

## Deferred scope and blockers

- No live provider interaction was performed; manual testing requires a valid Google account, allowed origin and configured credentials in the local environment.
- One unrelated landing booking viewport test remains failing as described above; it is outside this authentication change.

## Follow-up - 6 November 2026

The landing test above is now resolved: its first-viewport expectation predated the current explicit hero-then-content layout. The test now checks the panel follows the hero and its controls fit after scrolling, preserving overflow checks. The full five-test viewport file passed. Historical results above remain unchanged; see [the follow-up report](landing-viewport-follow-up-2026-11-06.md).
