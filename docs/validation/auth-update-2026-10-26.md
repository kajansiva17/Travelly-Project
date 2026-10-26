# Auth update validation - 26 October 2026

## Accepted scope

Implemented the supplied registration/login, email verification and Google sign-in task, including the owner's explicit choices to require **both email and phone for every new account** and to add **verified-email password recovery**. Existing accounts remain usable. Every new account starts with only APPROVED Passenger membership; Owner/Driver review and the frozen document checklist remain independent.

Authority was inspected and amended before dependent implementation: Final Decisions AU-01 through AU-09, Auth Milestone Contract, physical data dictionary and [03E Auth extension](../03-API/03E-TRAVELLY-AUTH-EXTENSION.md). Source PDFs were not changed. This adds no application table; the implemented inventory remains users, user_roles, vehicles and documents within the twenty-table design.

## Implementation and changed files

| Area | Files | Result |
|---|---|---|
| Approved rules | `docs/00-READ-FIRST/01-TRAVELLY-NBP-FINAL-DECISIONS.md`, `02-TRAVELLY-AUTH-MILESTONE-CONTRACT.md`, `docs/02-DATABASE/02C-TRAVELLY-PHYSICAL-DATA-DICTIONARY.md`, `docs/03-API/03E-TRAVELLY-AUTH-EXTENSION.md` | Explicit precedence for the approved new rules and transition/recovery decisions. |
| Validation/session integration | `Backend/app/schemas.py`, `api.py`, `security.py`, `main.py`, `review_api.py` | Public email validation, case-insensitive duplicates, required contacts/terms, new-password composition, existing-password compatibility, verification gating and authentication-version revocation. Errors omit submitted secrets. |
| Auth services | New `Backend/app/auth_services.py`, `auth_extension.py`; `config.py` | Purpose-bound Redis capabilities, private local capture/Brevo adapter, GIS signature/claim/nonce checks, completion, explicit linking, recovery. |
| Database | `Backend/app/models.py`, new `Backend/alembic/versions/0004_auth_verification_google.py` | Planned provider/subject pair, legacy marker, authentication version, terms timestamp, provider/account constraints; no identity table. |
| Dependencies/settings | `Backend/requirements.txt`, `requirements.lock.txt`, `.env.example` | Cryptography for RS256 verification; public client ID and private sender settings. Actual `.env` was not edited. |
| Browser UI | `Frontend/src/AuthPage.jsx`, `api.js`, `App.jsx`, `AccountPage.jsx`, `PassengerDashboard.jsx`, `auth.css`, `Frontend/index.html` | Registration/login integration, route handling, memory-only session/flow state, Profile verification/linking and referrer protection. |
| New UI components | `Frontend/src/authValidation.js`, `AuthFlows.jsx`, `GoogleSignIn.jsx`, `ProfileAuth.jsx` | Password hints/inline errors; Check email/resend; verify/reset/forgot pages; Google button on both auth pages; completion and Profile controls. |
| Backend tests | `Backend/tests/conftest.py`, `test_auth.py`, `test_security.py`, `test_international_phone.py`, `test_role_applications.py`, `test_admin_review.py`, new `test_auth_extension.py` | Fixtures verify through real captured links; edge cases, races, transition, recovery, cryptographic Google validation and role preservation. |
| Browser/unit tests | New `Frontend/tests/authValidation.test.js`, `tests/browser/auth-google.spec.js`, `tests/auth-live/auth.spec.js`, `playwright.auth-live.config.js`, `Backend/scripts/serve_auth_test.py`; updated old Admin upload test label | Desktop/mobile auth tests, isolated real-API journeys, Google UI fixtures and existing application regression checks. |
| Usage docs | `README.md`, `Frontend/README.md`, this report | Current account behavior, setup, test evidence and remaining external setup. |

The registration-page check caught and fixed a stale password-hint variable that caused a runtime error despite a successful bundle build. A clock-order regression guard also ensures `updated_at` cannot precede a database-generated timestamp on Windows.

## Fields and behavior

- Email: trim only surrounding whitespace, reject internal whitespace, incomplete/public-invalid domains and invalid local dots; digits and plus tags remain valid. Normalize case; PostgreSQL CITEXT uniqueness resolves concurrent duplicates. Never treat format validation as verification.
- Password: 12-128 Unicode code points; uppercase, lowercase, decimal number and punctuation/symbol; no whitespace/control characters. Show the requirements before submission and specific missing requirements inline. No normalization, truncation or logging; Argon2id parameters are unchanged. Old hashes remain usable, including older passwords containing spaces.
- New account: full name, email, international mobile and explicit terms acceptance are required for both methods. Google supplies the email only from the verified server ticket. No caller-supplied subject, verification status or roles are trusted.
- Verification: single-use 30-minute links, replacement on resend, per-user/IP/send-day limits, explicit confirmation after opening. Link tokens are removed from browser history and never returned in API responses. Provider acceptance, local capture, failed submission and quota exhaustion are distinguished; none claims inbox delivery.
- Google: RS256 signature and issuer/audience/expiry/issued-at/subject/nonce checks, fixed trusted key endpoint. Authoritative verified Gmail/Workspace can proceed; third-party Google email requires Travelly verification. Matching email never links. Profile requires explicit confirmation, Google proof and current password where present; both methods retain the same user and roles.
- Recovery: only an already verified email on an eligible account receives a link. Generic 202 response for missing/unverified/restricted accounts and sender failures. Reset consumes the link, enforces the new password rules and invalidates all old sessions using `auth_version`. It can establish a password on the same Google account without unlinking it.

## Migration and endpoints

Applied **0004_auth_verification_google** to the configured local PostgreSQL database. `alembic current` reports that head and `alembic check` reports no new upgrade operations.

The migration backfills `email_login_required=false` for existing rows, then defaults new rows to true. Existing hashes, contacts, IDs and roles are preserved. It adds the previously planned unique provider/subject pair plus `auth_version` and `terms_accepted_at`; password hash can be null only with a provider identity. Automatic downgrade is intentionally unavailable because removing provider identity and transition state needs an explicit recovery plan.

All paths have prefix `/api/v1`:

| Method | Path | Purpose |
|---|---|---|
| POST | `/auth/register`, `/auth/login` | Updated validation and verification-aware results |
| POST | `/auth/email/resend`, `/auth/email/verify` | Resend capability; consume email link |
| POST | `/users/me/email-verification` | Authenticated existing-account verification path |
| POST | `/auth/password/forgot`, `/auth/password/reset` | Request/consume verified-email recovery |
| POST | `/auth/google/challenge`, `/auth/google` | GIS challenge and validated sign-in |
| POST | `/auth/google/complete` | Required details/terms before new account creation |
| POST | `/users/me/google/challenge`, `/users/me/google` | Session-bound challenge and explicit linking |
| GET | `/users/me/auth-methods` | Safe availability/verification flags |

Existing refresh and protected endpoints now check authentication version and the new-account email gate. Existing role/application/document authorization remains in force.

## Verification results

- Full backend suite: **164 passed, 2 failed** initially. Both failures were old fixtures: a cloned registration reused the now-required phone, and a suspension timestamp preceded PostgreSQL's timestamp by less than a millisecond. Corrected both; a focused run covering both failures, all auth-extension cases and security tests passed **51/51**.
- Added explicit old-schema-to-new-schema migration preservation, provider response/quota and monotonic timestamp tests: **7/7 passed**. The migration test verifies the table inventory and backfill/default behavior using real PostgreSQL.
- Final auth/international-phone integration rerun after polishing inline error wording: **39/39 passed**. All 173 backend cases have passing coverage across the full run and focused reruns; this is not a claim that the original full-suite invocation was clean.
- Frontend unit suite: **40/40 passed**.
- Real local API browser journeys: **6/6 passed**, desktop 1366x900 and mobile 360x640. Verified registration errors, saved unverified account, captured email, blocked pre-verification login, link consumption, login/dashboard/Profile, captured recovery link, password change and subsequent login. Also verified legacy password login, legacy verification path, absent Google configuration and expired-link guidance. These use isolated PostgreSQL schemas, Redis namespaces and local mail; no live applicant data is changed.
- Google browser scenarios: **10/10 passed**, on desktop and mobile: both entry pages, completion/terms, third-party verification, same-email conflict, invalid-token UI and Profile linking. GIS/API browser responses are mocked. Separate backend tests validate real RSA signatures with only Google's key fetch replaced by a test key.
- Existing Admin/document browser regression: initial run **39 passed, 3 failed**. Two failures were the old Admin upload test's former `Private file` label; corrected it to the current `Document file`. One vehicle-registration case stalled while entering the mocked login flow. All affected cases, including both desktop/mobile variants, passed a focused **4/4** rerun. All five document types and all three ownership cases retain passing desktop/mobile coverage; no role checklist was changed.
- Production build: passed. Existing Vite >500 kB bundle advisory remains; backend tests show the existing TestClient/httpx deprecation warning.
- Screenshots of desktop/mobile registration, login, expiry guidance and Google completion were inspected. Width assertions verify no horizontal overflow. Existing sticky navigation may appear partway through full-page captures made while a lower input has focus; it is not part of the form.

Detailed backend logs are local, ignored files in `.tools/auth-update-tests.log`, `.tools/auth-final-tests.log` and `.tools/auth-validation-final.log`. Browser artifacts are under `Frontend/test-results/auth-live`, `auth-google-final`, `auth-regression` and `auth-regression-final`. Tests use test accounts/capabilities only. The separately completed document-form rules and previous test matrix are recorded in [document upload validation](document-upload-form-2026-10-26.md).

To repeat the local browser journey, run `..\.venv\Scripts\python.exe scripts/serve_auth_test.py` from Backend (isolated API on port 8001). In a separate Frontend terminal set `$env:VITE_API_URL='http://127.0.0.1:8001'` and run `npm.cmd run dev -- --port 5181 --strictPort`; then run `npx.cmd playwright test --config=playwright.auth-live.config.js`. The regular mocked browser suite uses port 5180 and `npx.cmd playwright test`. The isolated server's normal Ctrl+C shutdown drops its own schema and Redis namespace.

## Run locally and finish live provider setup

Use the working project Python environment, install `Backend/requirements.lock.txt`, run Alembic upgrade head and restart the backend. Start Vite normally on 127.0.0.1:5173. Do not overwrite an existing `.env` with the example.

Development defaults are `MAIL_BACKEND=capture` and `FRONTEND_URL=http://127.0.0.1:5173`. Mail is stored as `.eml` in the operating-system temporary directory's `travelly-mail` folder unless `MAIL_CAPTURE_DIR` is set. On Windows, open that local folder with `Invoke-Item (Join-Path $env:TEMP 'travelly-mail')`, open the newest message and use its link. No external message is sent and no public mailbox viewer is exposed. Browser test mail uses the ignored `.tools/auth-browser-mail` folder and is not the normal development inbox.

For Brevo, configure a verified sender/domain in your provider account; set `MAIL_BACKEND=brevo`, `BREVO_API_KEY`, `MAIL_FROM_EMAIL`, the actual `FRONTEND_URL`, and `MAIL_DAILY_LIMIT` within your provider allowance, in local environment settings. Keep the key out of source/chat. Restart the backend and test a real inbox/spam folder, resend and reset links. Production requires HTTPS and real delivery configuration; capture is rejected. The application observes submission acceptance only, not final inbox delivery/bounces. See [Brevo's transactional-email setup](https://developers.brevo.com/docs/send-a-transactional-email).

For Google, create a **Web application** OAuth client in Google Cloud/Google Auth Platform, configure its consent/branding/audience and authorized JavaScript origins (locally `http://127.0.0.1:5173`, plus `http://localhost:5173` only if used; production uses its exact HTTPS origin). Set `GOOGLE_CLIENT_ID` in backend environment settings and restart. This GIS ID-token callback flow does not require a client secret in the browser or a redirect-code exchange. Test a real consent/popup response, a first-time authoritative account, third-party email, and explicit linking from an existing account. See [GIS JavaScript configuration](https://developers.google.com/identity/gsi/web/reference/js-reference) and [Google token verification](https://developers.google.com/identity/gsi/web/guides/verify-google-id-token).

**Still external:** real Google client configuration and Brevo credentials/sender setup were absent, so real Google consent and actual inbox delivery have not been claimed as tested. Official Terms/Privacy destinations were also not supplied; existing explicit preview notices remain and need their actual destinations before public signup.
