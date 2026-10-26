# Travelly NBP Passenger Dashboard Contract

Version: 1.0 | Decisions frozen: 25 October 2026

Status: Passenger Dashboard rules and implementation scope frozen; documentation only. This document does not authorize coding or declare the later-module build gate passed.

## 1. Purpose, authority and boundaries

Define the Passenger Dashboard's route, access, content, workspace selection, application states and acceptance criteria before implementation.

Read this document with these higher-priority sources:

1. [Final Decisions and Supersession Register](../00-READ-FIRST/01-TRAVELLY-NBP-FINAL-DECISIONS.md): accepted conflict resolutions, document precedence and exclusions, especially D01, D02, D07, D10, D11 and D12.
2. [Backend Build Readiness Contract](../00-READ-FIRST/00-TRAVELLY-BACKEND-BUILD-READINESS.md): sections 1, 3, 4, 7, 8 and 11 govern account/role rules, statuses, permissions, privacy and build gates, subject to Final Decisions.
3. [Auth Milestone Contract](../00-READ-FIRST/02-TRAVELLY-AUTH-MILESTONE-CONTRACT.md): the 24 October implementation amendment and sections 3, 5, 6 and 7 govern existing identity, role applications, APIs, authorization and browser sessions.

This module contract refines dashboard behaviour; it does not supersede those sources, replace their complete specifications or alter an API payload. Existing database architecture and API authorities retain the precedence assigned by Final Decisions. Any unlisted disagreement must be resolved before affected implementation.

The planned application-table count remains exactly 20. No dashboard, workspace, application, preferences, session or audit table is added. No existing schema, API matrix, PDF or source document is changed by this contract.

## 2. Binding product decisions

1. Every registered account receives automatically APPROVED `PASSENGER` membership. Registration itself does not issue tokens; registration success goes to Login. Every successful login lands at `/dashboard` in Passenger workspace after authenticated profile/role hydration succeeds.
2. Passenger remains the default workspace at all times, including future logins. An optional working-context switch never changes that default or removes Passenger membership.
3. Contact verification is separate from role approval. `PENDING_VERIFICATION` is an account status, not a Passenger role status. Contact verification must not be inferred from role membership or application approval.
4. A Passenger can start an Owner application or Driver application from this dashboard using the same account.
5. A `PENDING`, `REJECTED` or `SUSPENDED` Owner/Driver application does not grant that workspace. The user stays in Passenger workspace for that application; no automatic switch occurs.
6. Only currently `APPROVED` Owner/Driver roles appear as selectable additional workspaces in the profile switcher.
7. Switching changes the working dashboard only. It neither creates another account nor changes/removes any role membership.
8. Dashboard home includes all eight content groups specified in section 4.
9. A user with no real journeys sees proper empty states, never fabricated bookings, trips, payment amounts, drivers or booking counts.
10. All personal dashboard data belongs to the authenticated user. Public-safe discovery content is distinguished from personal journey records.
11. Owner-ready and Driver-ready cards appear only after the corresponding Admin approval is reflected in the current server role state.
12. Telephony/IVR and general promotions/coupons are excluded from this dashboard and the current NBP.

## 3. Routes, access and session rules

| Entry or action | Required behaviour |
|---|---|
| Successful login | Validate the issued session, read `GET /api/v1/users/me` and `GET /api/v1/users/me/roles`, then show `/dashboard` in Passenger workspace. Previously selected Owner/Driver context must not override the login destination. |
| `/dashboard` | Protected Passenger Dashboard home. Require a valid session, eligible account and current APPROVED Passenger membership. An anonymous visit goes to `/login`; do not render private data first. |
| Registration success | Continue to `/login`, preserving the existing Auth contract; do not fabricate an authenticated dashboard session. |
| `PENDING_VERIFICATION` account | Permit dashboard/profile/role-state access and the existing authenticated application flow under the Auth contract. Show the verification reminder. Do not permit booking before trusted contact verification. |
| `ACTIVE` account | Permit dashboard access, subject to current session and membership checks. Other actions still require their own role, ownership, document and service eligibility. |
| Account `SUSPENDED`, `BLOCKED` or `CLOSED` | Deny protected dashboard access regardless of approved roles. Follow Auth errors/session revocation rules; own-session logout remains available as defined there. |
| Missing, expired or revoked session | Follow the existing serialized refresh/logout behaviour. If credentials cannot be restored, clear private client state and return to Login. Never persist tokens to add dashboard reload support. |
| Direct Owner/Driver route attempt | Enforce the required APPROVED role on the server and in the route guard. An ineligible role gets no private workspace data; the eligible signed-in user can return to `/dashboard`. Other workspace paths are outside this contract. |
| Logout or account change | Revoke/clear the session as specified by Auth and clear all user-specific dashboard data and working-context state. Browser Back must not reveal another session's cached private records. |

Account restrictions are distinct from role restrictions. A suspended Driver role does not suspend an otherwise eligible account or its Passenger membership. If Passenger membership is unexpectedly missing or invalid, fail closed with a recoverable access/support state; never recreate or approve membership from the browser.

`/dashboard` always denotes Passenger home. Returning to it selects Passenger context. Owner/Driver workspace selection is an explicit user action, never an automatic consequence of submitting or approving an application. This contract does not add routes or specify dashboards for those workspaces.

## 4. Dashboard home sections

All sections participate in normal document flow and remain usable on desktop, tablet and mobile. Retain Travelly's established cream, burgundy and warm neutral visual style. Navigation, cards, buttons and status messages must be keyboard accessible and readable without relying only on colour. No fixed page height or clipped wrapper may hide lower sections or the footer.

| Section | Content and behaviour |
|---|---|
| Welcome/hero | Greet the current user using their own safe display name/full name. Identify Passenger as the current workspace. Do not claim a booking, reward balance, approval or verified contact that does not exist. |
| Quick actions | Provide Vehicle hire, Tickets and Rentals entries into their approved discovery/search flows. Starting discovery does not create a booking or payment. Where a service is not implemented, show an honest unavailable state instead of a non-working transaction or simulated success. Paths and transaction behaviour remain subject to the respective module/API contracts. |
| Next journey | Show the user's real current journey when active; otherwise the earliest upcoming confirmed journey, using authorized booking/trip data. Show only available, approved response fields and correct business status. Journey selection and date filtering must be consistent between client and server; exact query/payload mapping belongs to the corresponding frozen booking/trip contract. If no qualifying journey exists, show the empty state in section 5. |
| Upcoming bookings | Show only the user's real open booking records with clear service, itinerary/time and status where returned by the approved contract. Distinguish requests awaiting confirmation from confirmed journeys. Use canonical booking statuses from Readiness; completed, rejected and cancelled records are not presented as upcoming journeys. Overdue/unresolved records need an honest attention state, not automatic cancellation or a fabricated confirmation. Detailed history, filtering and pagination are later contract work. |
| Explore Sri Lanka | Present real, public-safe destination/discovery content using supplied assets or authorized public discovery data. This is discovery content, not evidence of the user's travel history or inventory availability. Do not expose other users' personal bookings, contact details, documents or tracking. |
| Profile/contact-verification reminder | Show when available contact verification is incomplete, or supported profile data genuinely requires attention. Read verification from the current profile's `email_verified_at` and `phone_verified_at`. A verified contact satisfies the Auth booking-contact prerequisite; do not falsely call the whole account unverified because a second contact is unverified. Identify any outstanding supplied contact accurately. Do not invent mandatory profile fields or claim successful verification from a click. |
| Owner/Driver application entry or status | Show separate entries/status cards for Owner and Driver, governed independently by section 7. Provide an application entry when no membership exists and appropriate status/reason information when it does. Do not imply that registering another account is necessary. |
| Approved-role readiness cards | Show Owner-ready only for APPROVED Owner membership and Driver-ready only for APPROVED Driver membership. They offer an explicit workspace entry. Approval does not by itself guarantee operational readiness: required documents, account eligibility, availability and action-specific checks still apply. |

Reminders may be placed near the welcome area. Application/status and approved-role cards may share one section, but their eligibility and meaning must remain distinct. Section content is not an authorization decision.

If journey, booking, verification or destination services are not yet available under their implementation gates, keep the relevant section honest and non-transactional. A section shell must not silently stand in for implemented business functionality.

## 5. Empty, loading and failure states

| Situation | Required presentation |
|---|---|
| Successful own-record query returns no next journey | “No upcoming journey yet” with a discovery action. Never show a sample journey as real. |
| Successful own-record query returns no upcoming bookings | “You have no upcoming bookings” with Vehicle hire/Tickets/Rentals discovery entries as available. Any displayed count is derived from actual authorized data. |
| New account with no journeys | Keep welcome, discovery, reminders and application entries useful. Show both relevant empty states rather than seeded demonstration bookings. |
| Personal data is loading | Use a clearly temporary loading state; no invented passenger itinerary, booking reference, fare or driver detail. |
| Request fails or a dependency is unavailable | Show a safe error/unavailable message and a retry where appropriate. Do not label failure as an empty result or erase a known booking's status. |
| Module is not implemented | Say the service/section is not yet available. Do not call a nonexistent endpoint, invent a successful response or claim that the user has zero records. |
| Role/profile state cannot be verified | Do not show additional workspaces or ready cards based on stale/default assumptions. Retain a safe loading/error state and retry; fail closed for protected actions. |
| No discoverable destinations | Show a discovery empty/unavailable state; do not fabricate live vehicle availability or offers. |

No demo records may appear as live data in a normal user's dashboard. Test fixtures remain isolated from real account records. Do not treat an unavailable booking service as proof that the user has no bookings.

## 6. Profile workspace switcher

- Passenger is always the default and remains selectable for an eligible account with its valid Passenger membership.
- Additional options are Owner and/or Driver only when that membership's current server `approval_status` is exactly `APPROVED`. Do not list PENDING, REJECTED or SUSPENDED roles as selectable workspaces, even disabled; show their application state in the dashboard instead.
- If neither additional role is approved, show Passenger as the sole workspace or a non-interactive Passenger indicator; do not imply a hidden operational workspace is available.
- Use the current `/me` and `/me/roles` responses together: `approved_roles` identifies approved memberships, while the complete own-role list supplies application statuses. Do not infer approval from the existence of a role row, role_profile, contact verification, a local flag or a JWT claim.
- An explicit switch changes the active working context/dashboard. It does not mutate `users`, change approval, remove Passenger membership or issue another account/session.
- Passenger remains the default after switching. Selecting Passenger returns to `/dashboard`; a new successful login also returns there, regardless of previous selection. Do not introduce persisted default-workspace preferences or another storage table.
- Approval received while viewing Passenger updates the switcher and relevant ready card after a successful role-state reload. It does not navigate automatically. No polling/realtime infrastructure is required by this contract.
- Re-evaluate role state on workspace entry and after an authorization failure. If an active Owner/Driver role becomes unavailable, deny its subsequent protected operations, remove its switcher option/ready card after authoritative refresh and return the eligible account to Passenger context. Server enforcement must not wait for UI refresh.
- A PENDING/REJECTED/SUSPENDED Driver application does not revoke a separately APPROVED Owner role, and vice versa. The unapproved role cannot be entered; independently approved workspaces remain available by explicit selection. This preserves the higher-priority independent-role rule.
- Admin membership is controlled administration and does not create an Admin option or application flow in this Passenger contract.

## 7. Owner and Driver applications

The same state rules apply independently to `OWNER` and `DRIVER`. “Not applied” below is a presentation state meaning no matching `user_roles` row; it is not a new database approval value.

| Current role state | Passenger dashboard behaviour | Workspace/ready card | Submission behaviour |
|---|---|---|---|
| No membership / not applied | Offer “Become an Owner” or “Drive with Travelly” application entry using the existing account. | Neither available for that role. | Existing authenticated application operation creates PENDING. |
| PENDING | Show “Application pending” and accurate next-step information. Keep Passenger as default. | Neither available for that role. | Duplicate request is 409 `ROLE_ALREADY_REQUESTED`; do not create another membership. |
| APPROVED | Show approval and the relevant Owner-ready/Driver-ready card. | Additional workspace selectable; no automatic switch. | Duplicate request is 409; do not offer another application for that role. |
| REJECTED | Show the user's authorized rejection reason and a reapplication entry. Keep Passenger as default. | Neither available for that role. | The existing operation may move the same membership back to PENDING, following the Auth contract's version/evidence rules. |
| SUSPENDED | Show the user's authorized suspension reason and an honest support/review message. Keep Passenger as default. | Neither available for that role. | No self-reinstatement or new duplicate request. Existing duplicate request is 409; reinstatement is not authorized here. |

Application submission references the existing `POST /api/v1/users/me/role-requests` operation in the Auth implementation amendment. Only `OWNER` or `DRIVER` can be requested; no Passenger/Admin application or self-approval is permitted. A successful submission returns the existing 201 RoleResponse with PENDING status. Reload authoritative profile/role state after success or a duplicate/conflict response; do not optimistically label the role APPROVED.

Supporting-document submission remains subject to the document module gate. Until that module exists, `supporting_document_ids` must be empty as specified in the Auth amendment. An application entry does not authorize new upload/review features or a document-verification bypass. Admin review retains the existing approved-document and authorized-reviewer requirements; this contract adds no Admin UI or review API.

Owner self-drive still requires an independently APPROVED Driver role and all operational eligibility checks. Owner approval never implies Driver approval. Application rejection/suspension affects only the reviewed role, unless an independent account restriction also applies.

## 8. Frontend and backend responsibilities

| Frontend responsibilities | Backend responsibilities |
|---|---|
| Route eligible successful logins to `/dashboard` and guard private rendering during profile/role hydration. | Validate the current session and current account/role state using the established Auth mechanism. |
| Render the sections, real-data states, reminders, switcher and application status from allowlisted responses. | Return the authenticated user's allowlisted profile and membership data only; retain authoritative role decisions. |
| Keep tokens in memory and serialize refresh exactly as Auth requires. Clear user-specific state on logout/session/account changes. | Retain existing expiry, rotation, reuse detection and revocation. No extra dashboard/session application table. |
| Use workspace context for presentation only; never self-approve a role or treat hiding a button as security. | Authorize every protected read/action independently of client workspace flags, URLs or claimed user IDs. |
| Invoke existing application APIs, handle validation/conflict/rate/auth errors and refresh role state. | Enforce uniqueness, permitted application transitions and existing error/status contracts. |
| Use discovery links without simulating booking, payment, tracking or verification completion. | Keep business operations behind their respective module gates and authorization rules. |
| Distinguish public-safe exploration from private personalized data; clear stale data when switching accounts. | Scope personal journey/booking queries and joins to the authenticated Passenger identity. Never trust a caller-supplied owner/passenger ID to widen visibility; filter before aggregating counts or returning results. |

Existing `users` and `user_roles` remain the identity/membership sources. Later journey/booking reads must use the appropriate existing entities in the approved 20-table architecture once their physical dictionaries and APIs are frozen. This contract adds no columns, enum values, indexes, migrations, tables, dashboard aggregation endpoint or new API response envelope.

Preserve canonical booking/trip/payment statuses in later dashboard displays. Passenger payment state must remain separate from Owner settlement state. A protected-departure deadline must not trigger dashboard-driven cancellation/refund; show the authorized state and Admin escalation under Final Decisions D08. Private documents and live location require their own authorization and must not leak into discovery/profile cards.

## 9. Acceptance scenarios

These are required future acceptance tests, not claims that code has been built or tests executed by this documentation task.

| ID | Given / action | Expected result |
|---|---|---|
| PD-01 | Register a valid new account, then log in successfully. | One account and APPROVED Passenger membership remain; registration goes to Login, then successful authenticated hydration lands at `/dashboard` in Passenger context. |
| PD-02 | New Passenger has no real journeys/bookings and both authorized queries succeed empty. | Welcome/discovery/application entries remain usable; next journey and upcoming bookings show honest empty states with no fake records/counts. |
| PD-03 | Visit `/dashboard` anonymously or with a revoked/expired session that cannot refresh. | No personal content is exposed; return to Login under the existing session rules. |
| PD-04 | Signed-in PENDING_VERIFICATION Passenger opens the dashboard. | Passenger membership remains APPROVED; show accurate contact reminder, allow own profile/role access, and do not permit booking or pretend a contact is verified. |
| PD-05 | A contact becomes trusted-verified, or only one of two supplied contacts is verified. | Refresh profile state; reflect verified versus outstanding contacts accurately. Do not change Passenger membership or infer approval for another role. |
| PD-06 | Passenger starts separate Owner and Driver applications. | Each valid first submission creates PENDING under the same user; Passenger remains the working/default context and neither pending workspace is selectable. |
| PD-07 | Owner or Driver application is PENDING, REJECTED or SUSPENDED. | Show the correct own application status/reason; no role-specific ready card or switcher option; no operational access. Duplicate/reapply rules match section 7. |
| PD-08 | Authorized Admin approval changes Owner or Driver to APPROVED and client reloads roles. | Only the approved role gains its ready card/switcher entry; no automatic navigation. No approval is fabricated while the role read is loading/failing. |
| PD-09 | Approved multi-role user manually switches workspaces, returns to Passenger, logs out and logs in again. | Working dashboards change only on explicit selection; account/memberships remain intact; returning to `/dashboard` and every new login use Passenger. |
| PD-10 | Owner is APPROVED while Driver is PENDING/REJECTED/SUSPENDED, or the reverse. | Only the independently approved extra workspace is selectable; the other application's status does not revoke Passenger or the approved role. |
| PD-11 | Role is suspended while its workspace is open. | Backend denies later role operations immediately; authoritative UI refresh removes its option/card and returns an otherwise eligible user to Passenger. |
| PD-12 | Account becomes SUSPENDED/BLOCKED/CLOSED after login. | Protected dashboard access is denied regardless of role approvals; existing Auth 403/revocation/subsequent-401 behaviour applies. Own-session logout remains allowed. |
| PD-13 | Two users have different bookings; one tampers with a URL, payload or client workspace flag. | Personal data and aggregates include only the authenticated user's records. Other users' booking, contact, document and location data remain inaccessible. |
| PD-14 | A personal data request fails, a role read fails, or a later module is not implemented. | Show the appropriate loading/error/unavailable state, not a fabricated empty result, approval or successful transaction. |
| PD-15 | User attempts direct Owner/Driver entry without the APPROVED role, self-approval, duplicate membership or suspended-role resubmission. | No workspace data or operational permission is granted; server rejects invalid actions under the existing contract; Passenger membership is unchanged. |
| PD-16 | Logout, browser reload, browser Back or another account signs in. | Follow memory-only Auth rules; clear prior private state and working context; never show the previous user's records. |
| PD-17 | Test home at desktop, tablet and mobile portrait with keyboard/touch and reduced motion. | All required sections and controls remain reachable; no clipped lower content; switcher/status semantics remain clear and accessible. |
| PD-18 | Review discovery, quick actions and a protected-departure attention state. | Public-safe discovery is distinct from personal records; no fabricated availability, automatic cancellation/refund, IVR action or promotion/coupon UI is introduced. |

## 10. Deferred items, non-goals and implementation gate

Explicit non-goals for this documentation task and the Passenger home scope:

- Dashboard application code, routing changes, migrations, schema changes, API matrix edits and edits to existing source documents.
- Owner/Driver/Admin dashboard implementation, document upload/review, Admin approval UI, role reinstatement and secondary-owner delegation.
- Implementing booking creation/checkout/cancellation, seat holds, payment/refund/settlement processing, live tracking or vehicle management inside this home contract. Their later modules supply authorized data/actions under their own contracts.
- Contact-verification delivery/provider flows, profile editing APIs, password recovery/change, MFA, persistent sign-in and changed token transport. Reminders do not implement those workflows.
- New dashboard tables/columns, stored workspace defaults, a new dashboard API, new approval statuses, notifications/polling infrastructure, sample-booking seeds or a general configuration engine.
- Telephony/IVR, subscriptions and general promotions/coupons. These are excluded from the current NBP, as is secondary-owner delegation; do not add UI, callbacks, pricing plans or runtime behaviour for them.

The dashboard section and workspace rules above are frozen. Detailed journey query mappings, booking DTOs, pagination/history, destinations/inventory contracts, verification workflow destinations and Owner/Driver workspace route contracts remain dependencies to be specified by their respective modules; no missing endpoint or physical field is invented here.

Readiness section 11 Stage B remains binding: other Travelly modules may begin only after the complete 20-table physical PostgreSQL dictionary and corresponding API contracts are frozen. Passing the isolated Auth gate or freezing this Passenger Dashboard document does not satisfy that gate. Verify affected authorization rules and acceptance tests against those artifacts before later coding. This document neither opens that gate nor claims the remaining contracts are already frozen.
