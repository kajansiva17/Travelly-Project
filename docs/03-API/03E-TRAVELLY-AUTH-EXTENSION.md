# Travelly auth extension — 26 October 2026

Authority: user-approved auth task and Final Decisions AU-01–AU-07. This amends the former six-operation milestone; role and account restriction rules stay unchanged. AU-08/AU-09 below require both contacts for new accounts and authorize verified-email recovery.

## Validation and transition

Email uses email-validator without DNS deliverability claims; require public fully qualified domain syntax, reject whitespace inside email and invalid dot usage, allow digits/plus tags in usernames. Trim outer email whitespace and normalize case; PostgreSQL CITEXT UNIQUE remains authoritative for races. Do not conflate Gmail variants. Validate new/changed passwords as 12–128 Unicode code points with uppercase, lowercase, decimal digit and punctuation/symbol, no whitespace/control characters. Existing-password login accepts the existing 1–128 range and hashing policy. Terms acceptance is a strict true registration input for both methods, not a role grant.

The existing PENDING_VERIFICATION enum represents an unverified account. A users.email_login_required Boolean migration marker is false for all existing accounts and true for newly created email accounts. This permanently preserves legacy login access while gating new unverified accounts at login, refresh and protected-user checks. A valid verification only updates the matching email timestamp and activates PENDING_VERIFICATION; it never clears a restricted account state.

## Storage without another table

Implement the existing planned external_auth_provider VARCHAR(40), external_auth_subject VARCHAR(255), nullable pair and UNIQUE pair constraint. Only GOOGLE is supported. password_hash becomes nullable only for an account with a provider identity; otherwise it remains an Argon2id hash. Add users.email_login_required Boolean and auth_version INTEGER >=0 (default 0), and terms_accepted_at TIMESTAMPTZ nullable for legacy accounts. No provider token is stored in SQL. No new application table, common_profile auth state or role_profile dossier is allowed.

Redis holds purpose-bound hashed opaque tokens, short-lived Google challenges and completion tickets, send quotas and existing sessions. Verification tokens: 32 random bytes, 30-minute expiry, atomic consume, bound to user and exact normalized email. Resend invalidates the previous link, limited to one/60 seconds and five/hour/account plus bounded IP controls. Daily sender quota is configurable and counts attempted provider submissions conservatively; exhaustion fails honestly. Purpose separation prevents swapping verification, resend, Google completion or reset credentials. SQL row locks and current contact/state checks protect concurrent use. Email link tokens use URL fragments, are removed from browser history on arrival, submitted only in POST bodies and never logged; the verification page requires an explicit action to avoid link-preview consumption.

## Delivery and verification API

- POST `/auth/register`: existing profile fields plus `verification_required`, `verification_ticket` (resend-only capability), `email_delivery` and safe `message`; no login tokens. Account creation remains successful even when subsequent mail submission fails; UI must offer resend, not repeat registration.
- POST `/auth/login`: existing TokenResponse for eligible accounts; after a correct password, new unverified accounts instead receive `{status: 'verification_required', verification_ticket, message}` without access/refresh tokens. Wrong/unknown/restricted credentials remain generic 401.
- POST `/auth/email/resend`: `{ticket}`; explicit captured/provider_accepted/failed/daily_limit outcomes for the capability holder, 429 on per-user throttle. A capability never authorizes login or reads.
- POST `/auth/email/verify`: `{token}`; successful one-time consumption verifies only the bound email and returns a login instruction. Used, expired, mismatched and malformed tokens share a safe invalid-link error; no automatic session.
- POST `/users/me/email-verification`: authenticated legacy account request; same delivery response and resend ticket. Already verified email is a no-op. Phone-only legacy accounts cannot fabricate an email-verification target.

Local capture writes private `.eml` files outside the served frontend and is forbidden in production. Brevo uses its fixed HTTPS transactional endpoint and an environment API key/from address. Accepted by the provider is not delivered. Transport/provider failures return safe codes, never raw provider errors or credentials. No external email sends are used in automated tests.

## Google API and linking

- POST `/auth/google/challenge`: issue short-lived random challenge/nonce and configured public client ID, purpose sign-in. Disabled configuration yields an honest unavailable state.
- POST `/auth/google`: `{credential, challenge}`. Verify RS256 signature using fixed Google keys, exact issuer, audience, exp/iat, subject and nonce; consume challenge once. Stable subject already linked: normal account restrictions and verification gate, then existing session protocol. Unlinked matching email: explicit existing-account link-required response; never create/merge. New identity: return short-lived completion ticket and suggested name/email, no account/session yet.
- POST `/auth/google/complete`: `{ticket, full_name, phone_e164, preferred_language, accept_terms}`; email/provider identity come only from the validated ticket. Subject/email/phone unique constraints decide concurrent collisions. No arbitrary role/verification/client-subject fields.
- POST `/users/me/google/challenge`: authenticated, session-bound link challenge.
- POST `/users/me/google`: explicit confirmation plus fresh credential/challenge; password accounts also provide current password, checked with rate limits. Confirmed subject must be unlinked or already linked to this same user. Never replace an existing different provider identity, move accounts, rewrite email from Google or grant roles.
- GET `/users/me/auth-methods`: safe flags for password/Google availability and email verification. Provider subject/token never appears in profile DTOs.

Google is authoritative only when email_verified is true and email ends in @gmail.com or the signed hd claim is present. A third-party-email Google account gets the same Travelly verification requirement and no normal session until verified. GIS browser callback keeps credentials in memory; no local/session storage. Linking requires an explicit confirmation in the current authenticated Profile, not a shared-email shortcut. Google-only existing identities always authenticate by subject even if Google's email later changes; the Travelly contact is not silently rewritten.

## Validation plan and provider references

Test malformed emails and duplicates/races, every password requirement and legacy hashes, email-link expiry/replay/purpose mismatch/concurrency, sender failure/quota, legacy transition, Google signature/issuer/audience/expiry/nonce rejection, authoritative email rules, incomplete Google signup, same-email conflicts, authenticated linking and role preservation. Use real PostgreSQL/Redis and local email capture for integration. Browser tests cover desktop/mobile. Apply and check migration without introducing another table.

Implementation references: [Google server token verification](https://developers.google.com/identity/gsi/web/guides/verify-google-id-token), [GIS JavaScript API](https://developers.google.com/identity/gsi/web/reference/js-reference), [Brevo transactional email](https://developers.brevo.com/docs/send-a-transactional-email).


### Owner clarification accepted 26 October 2026 - AU-08 / AU-09

The owner explicitly selected: **Require email and phone for all new accounts** and **Add verified-email password recovery**. These choices resolve the pending conflicts above and supersede older email-only/phone-only NEW registration and recovery-deferral wording. Existing accounts remain usable regardless of missing contacts; neither login nor migration invents or verifies contacts. Both new registration methods require normalized email, valid international phone, full name and explicit terms acceptance.

Recovery: POST /api/v1/auth/password/forgot accepts email and always returns the same non-enumerating 202 response regardless of existence, verification, throttled recipient or provider outcome. It never claims delivery. Only an eligible account's already verified email receives a single-use 30-minute link. POST /api/v1/auth/password/reset accepts token and new password under AU-02, atomically consumes the token and locks the bound user; it updates the hash, clears password failure state, increments auth_version to revoke all old access/refresh sessions and requires a fresh login. Verified-email ownership can establish a password on the same Google account as well; it never unlinks Google, changes roles or creates a replacement account. Unverified-email/phone-only accounts cannot recover through this channel; the UI states this limitation without revealing account existence. Invalid/used/expired links share a safe response. Provider outages/quota handling never reveals whether an email exists.
