# 03SV. Settings: two-step verification and closing the account

Owner decisions, 14 November 2026. Not in the original PRD; add to the PRD when it is next revised. Same endpoints for every role.
Bearer token on all calls except `/auth/2fa`. **POST with no fields must send `{}`** (JSON only). Migration `0014_two_factor_and_closure`.

## 1. Two-step verification (authenticator app)
Optional for everyone (not forced for Admin). 6-digit code, changes every 30 seconds (Google Authenticator and similar apps).

`GET /users/me/2fa` → `{ "enabled": false, "enabled_at": null, "backup_codes_left": 0 }`

Turn on, two steps:
1. `POST /users/me/2fa/setup` `{}` → `{ "secret": "JBSW…", "otpauth_uri": "otpauth://totp/Travelly:name@example.com?secret=…", "issuer": "Travelly", "message": "…" }`.
   Show the `secret` as text and the `otpauth_uri` as a QR code (the UI makes the QR) so the person can add it to the app. Calling it again before step 2 gives a new secret. 409 `TWO_FACTOR_ALREADY_ON`.
2. `POST /users/me/2fa/enable` `{ "code": "123456" }` → `{ "enabled": true, "enabled_at": "…", "backup_codes_left": 10, "backup_codes": ["ABCDE-FGHJK", …], "message": "…" }`.
   **The 10 backup codes are shown only here.** Make the person copy or download them (each works once, instead of an app code). 422 `TWO_FACTOR_CODE_WRONG`, 409 `TWO_FACTOR_SETUP_REQUIRED` (step 1 not done).

Turn off: `POST /users/me/2fa/disable` `{ "password": "…", "code": "123456" }` → status. `password` is needed only when the account has one (Google-only accounts leave it out). `code` is an app code or a backup code. 409 `TWO_FACTOR_NOT_ON`, 422 `CURRENT_PASSWORD_WRONG` / `TWO_FACTOR_CODE_WRONG`.
New backup codes: `POST /users/me/2fa/backup-codes` same body → status plus `backup_codes` (the old ones stop working).
A code can be used once; after a code is accepted wait for the next one (30 s) before using the app for another step.
5 wrong codes lock that person's second step for 15 minutes: 429 `RATE_LIMITED` (`Retry-After`).

### Signing in when it is on
`POST /auth/login` (and Google sign-in) no longer returns tokens, it returns:
```json
{ "status": "two_factor_required", "challenge": "…", "expires_in": 300, "message": "…" }
```
Show a "Enter your code" screen (app code or a backup code), then `POST /auth/2fa` `{ "challenge": "…", "code": "123456" }` → the usual token response (same as login). 401 `TWO_FACTOR_CHALLENGE_EXPIRED` → back to the sign-in form. Devices already signed in are not asked again.
Handle `status` on the login response the same way as the existing `status` answers (email verification, Google).

## 2. Close the account
Both actions need the person's open business to be finished first, so nobody can leave bookings, trips or money behind.

`GET /users/me/account-closure`
```json
{ "can_close": false, "delete_after_days": 30,
  "blockers": [ { "code": "OPEN_BOOKINGS_AS_PASSENGER", "message": "You have bookings that are not finished.", "count": 2 } ] }
```
Blocker codes: `OPEN_BOOKINGS_AS_PASSENGER`, `OPEN_BOOKINGS_AS_OWNER`, `OPEN_TRIPS_AS_DRIVER`, `OPEN_DEPARTURES`, `COMMISSION_DUE`, `OWNER_PAYOUT_PENDING`, `REFUND_PENDING`. The UI shows its own text per code (`message` is English fallback) and, when `can_close` is false, disables the buttons and lists the reasons.

- `POST /users/me/deactivate` `{ "confirm": true, "password": "…", "code": "123456" }` → `{ "status": "DEACTIVATED", "message": "…" }`. The person is signed out everywhere. Signing in again (password or Google) brings the account back.
- `POST /users/me/delete-request` same body → `{ "status": "DEACTIVATED", "delete_after": "<now + 30 days>", "message": "…" }`. Same as deactivate, plus the personal data is removed after 30 days. Signing in within the 30 days cancels the request (show "Welcome back, your account is active again").
- `password` is needed when the account has one; `code` only when two-step verification is on (422 `TWO_FACTOR_CODE_REQUIRED`).
- 409 `ACCOUNT_HAS_OPEN_ITEMS` (field_errors list the blocker codes) if something became open since the check.
- A deactivated Owner's vehicles and departures are not shown in search and take no new bookings.

### What is removed after 30 days (daily job `scripts/anonymize_deleted_accounts.py`)
Name becomes "Deleted user", email, phone, photo, password and Google link are removed, the account becomes `CLOSED` and can never sign in. Booking, payment, trip, review records stay (under "Deleted user"). Uploaded documents and vehicle files are not touched by this job. A request whose person has open business again is skipped until it is clear.
