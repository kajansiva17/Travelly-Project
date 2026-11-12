# Travelly — Staying signed in (session cookie)

Status: built on `claude-work` (12 Nov 2026). Owner decision: a page reload must not sign the person out, and signing
in as a different person or role must never open the previous person's page.

## Backend

| Endpoint | Change |
|---|---|
| `POST /api/v1/auth/login` | New optional `remember_me` (boolean, default `false`). Sets the session cookie. |
| Google sign-in / email-verification sign-in | Set the session cookie (browser-session only). |
| `POST /api/v1/auth/refresh` | Body `{}` is enough: the token is read from the cookie. A body `refresh_token` still works and wins. The cookie rotates with the token. A refused token (401/403) also clears the cookie; 429/503 keep it. |
| `POST /api/v1/auth/logout` | Body `{}` is enough (Bearer access token still required). Always clears the cookie. |

Cookie `travelly_session`: `HttpOnly`, `SameSite=Strict`, `Path=/api/v1/auth`, `Secure` in production or behind an
https frontend. Without `remember_me` it is a browser-session cookie: it survives reloads but not a browser restart.
With `remember_me` it lasts until the session's fixed 7-day end (the refresh token carries `rm: true`, so rotation keeps
it). Page scripts never see the refresh token's cookie. The access token (15 min) stays in page memory only.

Replay protection is unchanged: presenting an already-rotated token ends the whole session.

## Web app (minimal plumbing, no screen changes)

- `services/api.js`: `restoreSession()` renews from the cookie on load (5 s limit). Every renewal sends `{}` so the
  newest cookie is used, and tabs take turns through `navigator.locks` so two tabs never present the same token.
  `clearSession(reason)` records `'logout'` or `'expired'`.
- `main.jsx`: waits for `restoreSession()` before the first render.
- `App.jsx` `ReturnToRequestedPage`: after a deliberate logout nothing is remembered. After an expired session or a
  signed-out private link, the page is reopened only if it belongs to the workspace the person signed in to.
- `routes/workspaceRoutes.js` `loginDestination`: plain sign-in (no Owner/Driver/Admin entry) opens the Passenger
  dashboard. Owner/Driver entries open that workspace (or its onboarding); the Admin entry opens the Admin dashboard.
- `AuthPage.jsx`: sends `remember_me`; the "Remember me" hint now says the session is kept for up to 7 days
  (string in `messages.trips.js`).
