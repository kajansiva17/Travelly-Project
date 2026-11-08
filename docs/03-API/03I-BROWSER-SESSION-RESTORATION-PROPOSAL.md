# Browser-session restoration proposal - 6 November 2026

Status: discussion draft, not implemented. The user requested discussion of session persistence during the role-navigation task, then selected **Page reloads only; sign in again after the browser session ends**. That behavior preference is confirmed; the cookie transport/implementation below is proposed.

## Existing contract and reason for revision

The relevant approved source recovered from the documentation collection, page 35 (`.tools/context-intake-2026-11-05/plan.txt`, around line 2626), says: "Persistent browser sign-in/cookie transport is outside this milestone and requires a contract revision."

Existing access/refresh credentials live only in browser memory, use Bearer/JSON transport and Redis-backed session rotation/revocation. The original navigation request explicitly excluded authentication changes; the follow-up authorized discussion. No authentication source has been changed as part of the navigation delivery.

## Proposed bounded implementation

1. Preserve in-memory access credentials and existing server-side current account/role checks. Never save credentials in localStorage, sessionStorage or a JavaScript-readable cookie. Do not persist an active-role preference or grant permissions from a role URL.
2. Introduce a host-only, HttpOnly, Secure-in-production, SameSite session cookie with no Expires/Max-Age. Use an opaque high-entropy restoration credential whose digest is bound to the existing Redis session; no application table or migration. Keep the existing server session expiry; do not extend lifetime implicitly.
3. Add narrowly scoped browser restore/renew/logout endpoints. Validate an explicit browser request header, exact allowed Origin, JSON content type and rate limits; deny absent/invalid/expired/revoked/restricted sessions. Use atomic Redis verification/renewal so legitimate simultaneous tabs/reloads do not invalidate each other through stale JSON refresh-token rotation.
4. Before rendering protected routes, attempt restoration once; wait for its outcome before redirecting. On success, retrieve current profile/memberships, preserve the existing URL and mount its authorized shell. On dependency failure, show a retry/error state without fabricating authentication or showing protected data. Missing/expired credentials lead to the existing sign-in flow.
5. Logout must revoke the same Redis session and remove the restoration cookie. Password changes, account restriction, existing expiry and revocation continue invalidating restored sessions. Existing JSON clients and Google/verification sign-in flows must retain their behavior, with browser cookie issuance only after actual session creation.
6. Keep Remember me as remembered identifier only; no browser-restart persistence option is introduced. Cross-origin deployments require explicit credentials/CORS support and HTTPS; do not loosen origins or change environment values silently.

## Browser lifecycle limitation

A session cookie normally ends with the browser session, but browsers can restore it when restoring previously open tabs. Thus **closing the browser cannot be guaranteed to revoke a server session**. Logout is the reliable explicit end-session action. Do not add unload/beacon-based logout, guess a new idle timeout, or claim stronger browser-close guarantees. Source: [MDN Set-Cookie, Expires](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Set-Cookie#expiresdate).

## Required validation before delivery

- Backend: cookie flags/host/path/lifetime, password/Google/verification issuance, allowed-origin/CSRF rejection, atomic renewal, expired/revoked/restricted/auth-version failures, Redis outage, logout deletion/revocation and legacy JSON transport.
- Browser: real HttpOnly cookie with no credential storage in JS-readable persistence; refresh/back/forward/deep links for all four roles on desktop/mobile; current role revocation; fresh browser context signed out; logout then reload signed out; concurrent tab renewal and unavailable-dependency handling.
- Update the authoritative context/API contract and report actual test evidence. No bypass, extra application table, role mutation or unrelated feature expansion.
