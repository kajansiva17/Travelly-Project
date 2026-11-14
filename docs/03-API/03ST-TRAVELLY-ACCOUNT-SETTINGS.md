# 03ST. Settings: Account security (sessions, password, notification preferences)

Owner decisions, 14 November 2026. Not in the original PRD; add to the PRD when it is next revised. One set of endpoints for every role (Passenger, Owner, Driver, Admin): they belong to the user. The UI shows them in the Settings page of every workspace.
All calls need the Bearer token. **POST/PUT with no fields must still send `{}`** (JSON only).

## 1. Sessions (devices that are signed in)
`GET /users/me/sessions`
```json
{ "items": [ { "id": "…", "current": true, "device": "Chrome on Windows", "ip_hint": "203.94.x.x",
               "signed_in_at": "2026-11-14T03:10:00+00:00", "last_active_at": "2026-11-14T03:40:00+00:00" } ] }
```
- This device (`current: true`) is first, then newest first. `ip_hint` hides the last two parts and may be `null`. `device` is "Browser on System" or "Unknown device".
- Sessions that were signed in before this release may be missing from the list until the person signs in again.

`DELETE /users/me/sessions/{id}` → 204 signs that device out. 409 `USE_LOGOUT_FOR_THIS_DEVICE` for the current one (use Log out). 404 `SESSION_NOT_FOUND` if it is not the person's or already ended.

`POST /users/me/sessions/revoke-others` body `{}` → `{ "signed_out": 2 }`. Everything except this device.

An ended device gets 401 on its next call and goes to the sign-in screen as usual.

## 2. Change password
`POST /users/me/password` `{ "current_password": "…", "new_password": "…" }` (same rules as sign-up).
- 200 returns **new tokens** in the same shape as login plus `message`. Replace the stored tokens: the old ones stop working, other devices are signed out, this device stays signed in.
- 422 `CURRENT_PASSWORD_WRONG` (show on the current-password field), 422 `PASSWORD_UNCHANGED`, 422 validation for a weak new password.
- 5 wrong current passwords lock this form for 15 minutes: 429 `RATE_LIMITED` (`Retry-After`).
- 409 `NO_PASSWORD_SET`: the account signs in with Google only. Point the person to "Reset password using a verified email" (it sets a password).

## 3. Notification preferences
`GET /users/me/notification-preferences`
```json
{ "items": [ { "notification_type": "ROAD_ALERT", "can_turn_off": true, "enabled": true },
             { "notification_type": "PAYMENT", "can_turn_off": false, "enabled": true } ] }
```
`PUT /users/me/notification-preferences` `{ "muted": ["ROAD_ALERT"] }` replaces the list of turned-off types and returns the same shape as GET.
- Only `ROAD_ALERT` and `MAINTENANCE_DUE` can be turned off. Booking, payment, refund, trip, replacement, document expiry, commission reminders and Admin actions always arrive. 422 `NOTIFICATION_CANNOT_BE_TURNED_OFF` otherwise.
- Show a switch only when `can_turn_off` is true; show the others as "Always on".
- A turned-off type no longer appears in `GET /notifications`.
- Role matters only for what the person ever receives: a Passenger never sees maintenance reminders, so the UI may hide a type that does not apply to the workspace.

## Database
Migration `0013_account_settings` adds `users.notification_preferences` (JSONB, `{"muted": [...]}`).
