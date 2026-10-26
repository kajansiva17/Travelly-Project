# Travelly NBP Admin Application Review Contract

Version: 1.1 | Final business/API freeze: 25 October 2026

Status: FINAL limited Admin Application Review business/API contract. All nine Business Decision Gate recommendations and the Vehicle Document UI rule are accepted and incorporated. No unresolved business decision remains; section 11 records technical prerequisites and the unchanged Readiness Stage B gate.

## 1. Purpose, authority and scope

Define the limited Admin module for finding, inspecting and deciding existing Owner and Driver applications. This is an application-review queue and detail workflow, not a general Admin dashboard.

Use these authorities in their existing precedence:

1. [Final Decisions](../00-READ-FIRST/01-TRAVELLY-NBP-FINAL-DECISIONS.md), especially project D01/D02/D07/D10/D11/D12/D13 and Admin Review AR-D01-AR-D09/AR-VUI.
2. [Readiness Contract](../00-READ-FIRST/00-TRAVELLY-BACKEND-BUILD-READINESS.md), sections 1, 3, 4, 5, 6, 8 and 11.
3. [Auth Milestone Contract](../00-READ-FIRST/02-TRAVELLY-AUTH-MILESTONE-CONTRACT.md), including the implementation amendment and sections 2.2, 3, 5, 6 and 7.
4. [Passenger Dashboard Contract](01-PASSENGER-DASHBOARD.md), especially sections 3, 6 and 7.
5. [Owner and Driver Applications Contract](02-OWNER-DRIVER-APPLICATIONS.md), especially sections 4-9 and 12.

This document refines the Admin review module without overriding those authorities or replacing their complete specifications. Existing database and API sources retain the precedence assigned by Final Decisions. Unlisted disagreements must be resolved before affected implementation. This finalization updates Final Decisions and module contracts 02/03/04 only; the API matrix, other contracts, original PDFs and application artifacts remain unchanged. [Admin Review Prerequisites](04-ADMIN-REVIEW-PREREQUISITES.md) sections 2-7 is the exact accepted mapping/HTTP/audit specification for this module, subject to Final Decisions.

There remain exactly 20 planned application tables. Reuse `users` and `user_roles` for identity, memberships and current decisions. Private evidence belongs to the already planned `documents` module after its physical/API freeze. AR-D08 requires restricted durable infrastructure outside application tables for full historical decisions; ordinary logs remain metadata-only; no review, application-history, notes, audit, permission-catalogue or session table is added.

## 2. Admin access and planned frontend routes

These are planned frontend routes defined for this module, not claims that they exist or new API endpoints:

| Route or operation | Access and behaviour |
|---|---|
| `/admin/applications` | Limited review queue. Require a valid session, an eligible current Admin account, current APPROVED `ADMIN` membership. Every eligible APPROVED Admin may review others; no additional reviewer flag. |
| `/admin/applications/{role_id}` | Review one existing OWNER or DRIVER membership identified by its `user_roles.id`. Apply the same Admin authorization before returning applicant information or evidence; own application detail is 403 REVIEW_FORBIDDEN. |
| Existing `PATCH /api/v1/admin/role-requests/{role_id}/review` | Admin-only decision operation. Recheck current authorization, target role, permitted transition, evidence requirements and expected version on the server. Exact request/response/error and JSON version transport are frozen in prerequisites sections 3-6. No self-review for any action. |
| Related document metadata/file access | Require authorized verification access to the relevant evidence on every request. Access to the route or possession of a role/document ID is insufficient. |
| Anonymous access | Do not render or return review data. Frontend goes to `/login`; protected APIs reject missing/invalid credentials under the existing Auth security rules. |
| Authenticated non-Admin access | Deny queue, review detail and review decisions, including direct URLs and handcrafted requests. Show a safe access-denied state with a route back to `/dashboard`; do not expose applicant counts, names or evidence first. |
| Restricted/revoked Admin account or role | Deny further protected review access immediately, regardless of cached UI or JWT claims. Clear private client state and follow existing Auth restriction/session rules. |

Admin assignment is controlled administration/bootstrap, never public registration or an applicant-selectable role. Do not invent a new permission field/table or a second Admin login. Reuse the existing authentication/session mechanism and current database role checks. AR-D06 settles reviewer eligibility: every valid-session, eligible-account, currently APPROVED Admin may review other applicants. There is no finer reviewer subset or new permission bit. Self-review is forbidden, not merely self-approval: no own application detail or any self approve/reject/suspend/document-verification action. Own applications are excluded before queue search/count/pagination. Separate own-file metadata/streaming reads remain permitted by ownership.

Passenger remains every user's default workspace, including a registered account with Admin membership. This module does not change successful-login routing, add Admin to the Passenger workspace switcher, remove Passenger membership or persist a new default workspace. Authorized Admins enter these review routes explicitly.

The non-Admin restriction applies to review functionality and other applicants' private evidence. It does **not** revoke an authenticated applicant's existing right to their own profile, role status/reasons and personal documents under Final Decisions D11. Approved Owners retain authorized access to owned vehicle documents. These are separate ownership-authorized operations, not access to the Admin queue.

## 3. Review queue

List existing `user_roles` records whose `role_code` is OWNER or DRIVER, joined to the relevant existing applicant identity; exclude the current reviewer's own applications and counts. Do not list automatic Passenger memberships or expose Admin bootstrap as an application. An applicant with both roles appears as two independent applications, not a combined approval decision.

| Queue information | Existing source and meaning |
|---|---|
| Application identifier | `user_roles.id`, used for opening the correct review detail. |
| Application type | `user_roles.role_code`: Owner or Driver. |
| Applicant identity | `users.full_name` and `public_user_reference`; use existing internal identity linkage for authorization, not an editable applicant ID. |
| Submitted date | `user_roles.requested_at`, displayed with a clear timezone. For rejected resubmission this is the current submission date, not an invented original-submission timestamp. |
| Current status | `user_roles.approval_status`, using only PENDING, APPROVED, REJECTED, SUSPENDED. |

Provide separate status and application-type filters. Status choices are exactly PENDING, APPROVED, REJECTED, SUSPENDED, with PENDING as the initial queue view. Type choices are Owner, Driver or both. A UI option for all statuses means no status restriction; it is not another stored status. Viewing/filtering/opening an application never moves it into UNDER_REVIEW or changes `requested_at`.

Safe search is limited to applicant name and public user reference. Bound and validate search length, pagination and filter values on the server; use parameterized queries and a documented literal-search policy rather than executable SQL/regex or unbounded exports. Do not search document contents, document numbers, storage keys or unrestricted profile JSON. No email/phone bulk-search feature is required here.

Apply Admin authorization before filtering, aggregating counts or returning results. Sort by `requested_at` oldest first with immutable role ID as a deterministic tie-breaker; paginate with bounded results. AR-D09 adds GET /api/v1/admin/role-requests; prerequisites section 4.1 freezes exact query names, bounds, pagination and ApplicationSummary allowlist. These documentation additions supplement the old matrix without claiming it has been edited. Queue URLs/history must not contain private document links or decision text.

| Queue state | Required presentation |
|---|---|
| Initial loading | Clearly temporary loading state; no fabricated applicants or counts. |
| Successful empty PENDING query | "No pending applications"; retain useful status/type navigation. |
| Successful query with no filter/search matches | "No applications match these filters" with clear/reset filters. Do not imply that all applications are absent. |
| Dependency/query failure | Safe error and retry, not an empty-success message. Do not keep showing stale approval as current evidence. |
| Authorization failure | Access-denied/login state as appropriate; no private queue or cached applicant data. |

## 4. Review detail and private evidence

GET /api/v1/admin/role-requests/{role_id} returns exactly application, applicant and documents under prerequisites section 4.2. Review an existing OWNER/DRIVER user_roles.id, never a Passenger/Admin membership. Show only allowlisted identity/contact/contact-verification fields, role status/request/decision evidence/version and relevant private document metadata. No password hashes, counters, tokens, role_profile dossier, private reviewer notes or other-user records. The applicant RoleResponse remains unchanged.

### 4.1 Accepted role evidence (AR-D01-AR-D05)

- Individual Owner: one verified NIC or PASSPORT plus applicant-owned VEHICLE_REGISTRATION evidence if the applicant is the registered owner; otherwise OWNER_AUTHORISATION evidence from the registered owner/company.
- A company-owned vehicle may be managed by an authorized individual; the company is not a Travelly account. Full company onboarding is deferred. Owner-only approval does not require a driving licence.
- Driver: one verified NIC or PASSPORT plus Sri Lanka-issued DRIVING_LICENCE (issuing_country LK). Foreign-driver licence approval is deferred; international Passenger registration remains unchanged.
- Initial Owner/Driver evidence belongs to documents.user_id = applicant ID with vehicle_id NULL. The accepted application linkage is derived ownership/type scope, not a new role/application FK or per-attempt snapshot. Do not create a fake vehicle to approve an Owner.
- All required evidence must match its applicant/ownership case, be APPROVED, current and unexpired where applicable, with trusted reviewer/time metadata. Recheck ownership/status/expiry/supersession during the locked role decision. Missing/unavailable evidence blocks approval; no evidence-free override.
- NEEDS_CORRECTION leaves the role PENDING. Rejecting a role is a separate Admin decision. Approving/correcting a document never automatically grants role approval, verifies a vehicle or reinstates a suspended role.

The exact mappings/catalogues/date/supersession rules are prerequisites sections 2.1-2.4. Do not add company/bank/age/licence-class fields or treat vehicle verification/publication as role approval.

Accepted Vehicle Document UI rule (AR-VUI):

- Required: all relevant vehicles must provide it before submission/verification.
- Required for your case: mandatory only when the applicant/registered-owner/company situation requires it.
- Optional: may be uploaded but never blocks submission or verification.
- Exact vehicle operating-document checklist remains for the future Vehicle Management Contract.

Optional never blocks eligibility. These labels add no database column/status and do not freeze the future vehicle operating checklist.

### 4.2 Private retrieval (AR-D06/AR-D07)

Use only authenticated GET /api/v1/documents/{document_id}/file, streaming private bytes from the backend after current authorization on every request. An eligible document owner may read their own personal/owned-vehicle evidence; every eligible APPROVED Admin may review other applicants' evidence. No self-verification, public/signed URL approach (including internal signed retrieval), storage redirects, query tokens or reusable download grants.

The existing secure_file_url response name refers only to the authenticated backend route, never a storage-provider URL. Fetch with Auth Bearer credentials; an authorized UI may use a transient local blob URL and release it when no longer needed. Private responses are no-store/nosniff with sanitized filename. Guessed IDs, copied routes or cached UI do not bypass current owner/session/Admin checks.

If evidence services are absent, show an honest unavailable state and disable approval. Document review uses only its planned endpoint and states under prerequisites section 5.2; no automatic role decisions or new document state is introduced.

## 5. Decision actions and reason/notes rules

Show actions only when the current role state permits them. The backend enforces the same rules even if the client displays a stale or manipulated button.

| Current role status | Available review action | Permitted result |
|---|---|---|
| PENDING | Approve | APPROVED, after authorized review and required evidence checks. |
| PENDING | Reject | REJECTED, with a valid rejection reason and authorized review. |
| APPROVED | Suspend | SUSPENDED, with a valid suspension reason and authorized review. |
| REJECTED | View existing decision | No direct Admin reapproval/reset here. The applicant may resubmit the same record to PENDING through the existing application operation. |
| SUSPENDED | View existing decision | No reinstatement, reset to PENDING or direct approval is authorized. |

No DRAFT, REQUESTED, UNDER_REVIEW, WITHDRAWN or other role approval status is added. There is no arbitrary status editor, bulk decision action, direct mutation of Passenger/Admin membership or undocumented transition.

Before committing a decision, show its target applicant, role, action and any applicant-visible reason for confirmation. Prevent duplicate clicks while submitting. A confirmation dialog is UI only and does not supply authorization or make the decision successful. On failure preserve editable reason text in the current form for correction, without storing it in browser persistence/history or sending it to analytics.

Reason and notes constraints:

- Reject requires a trimmed, non-empty `rejection_reason` of 1-2000 characters in the existing current-state field, with its full historical copy retained in the restricted durable audit channel. Suspend requires the corresponding `suspension_reason` with the same limits and history protection. The request key is `reason`, mapped server-side to the appropriate field.
- These reasons are applicant-visible through existing own-role responses. Label that visibility before submission. Use plain text, not executable markup, and do not place private document URLs, credentials, unrelated personal information or internal-only reviewer commentary in them.
- Approval has existing actor/time evidence but **no documented approval-reason field**. Do not add a required approval reason or free-text approval note that cannot be persisted. Do not misuse `rejection_reason`, `suspension_reason`, `role_profile` or `users` preferences to store it.
- No generic `notes`, `review_reason`, `approved_reason`, `reviewed_at` or `rejected_by` persistence field is introduced. Separate private reviewer notes and a requirement to retain approval reasons remain outside the frozen schema; an explicit accepted persistence decision would be required before offering them.
- A role decision does not edit identity/contact data, mark contacts verified or approve/reject underlying documents automatically.

All decisions require JSON body version as the expected current role version under prerequisites section 5. Re-read/lock authoritative target state, Admin authorization and applicable evidence as part of the decision workflow. Commit the permitted role update atomically, increment `version`, and use server timestamps and authenticated actor IDs. A stale/concurrent review must not overwrite a newer decision; return a safe conflict, reload the authoritative state and require a fresh review. Prerequisites sections 5-6 freeze the exact transport/error contract; audit confirmation under section 7 is required before commit.

An Admin must never review their own Owner/Driver application or verify their own documents, including rejection/suspension as well as approval. A normal Passenger, Owner or Driver can never approve/reject/suspend their own or another user's role. Client-supplied actor, timestamp, approval field or workspace flag is not trusted.

## 6. Decision effects on the applicant

| Result | Applicant access and dashboard effect |
|---|---|
| APPROVED Owner | Matching Owner role is eligible for the switcher and Owner-ready card after an authoritative profile/role refresh. Driver remains independently governed. |
| APPROVED Driver | Matching Driver role is eligible for the switcher and Driver-ready card after an authoritative profile/role refresh. Owner remains independently governed. |
| PENDING | No workspace or ready card for that role. Applicant remains in Passenger context for that application. |
| REJECTED | No workspace or ready card for that role. Show the own rejection reason and permitted rejected-resubmission entry; retain Passenger access. |
| SUSPENDED | Deny subsequent protected actions for that role immediately. On authoritative refresh remove its switcher option/ready card and return an otherwise eligible user from that role's workspace to Passenger. Show its own suspension reason; no self-reinstatement. |

APPROVED grants matching workspace eligibility only while account/session checks pass; it does not promise that a future operational dashboard has been implemented or that all document, assignment, vehicle and availability checks pass. Required operational eligibility remains independent. An approved Owner cannot self-drive without independently approved Driver membership and current required documents.

No decision removes or replaces permanent Passenger membership. Passenger remains the default, every successful login goes to `/dashboard`, and an approval never automatically changes the applicant's working context. Switching is explicit. A PENDING/REJECTED/SUSPENDED application does not revoke a separately APPROVED other role.

Account restrictions remain separate: account SUSPENDED/BLOCKED/CLOSED denies protected access regardless of role approvals. A role decision never reactivates a restricted account, sets contact-verification timestamps or grants booking eligibility before contact verification.

## 7. Existing persistence and restricted durable audit

Use only existing users/user_roles/documents/vehicles mappings. Current role decision fields are:

| Decision / evidence | Existing columns |
|---|---|
| Target/current submission/status | user_roles.id, user_id, role_code, requested_at, approval_status. |
| Approval | approved_by, approved_at, updated_by, updated_at, version + 1. |
| Rejection | rejection_reason, updated_by, updated_at, version + 1; no new rejected_by/rejected_at. |
| Suspension | suspended_at, suspension_reason, updated_by, updated_at, version + 1; preserve prior approved_by/approved_at. |
| Creation | Preserve created_at/created_by. |
| Document verification | documents.status, verified_by, verified_at, rejection_reason and planned common mutation/version fields; retained replacements use superseded_document_id. |

AR-D08 approves restricted durable audit infrastructure outside application tables. It must preserve every event's actor, timestamp, previous status, new status and complete applicant-visible reason, with target/version/trace correlation. Approval has NULL reason where none is accepted; current mutation columns alone are not historical audit. No application history/audit table, role_profile JSON store, notification, fake document or session-storage substitute is allowed.

Confirm durable audit preservation before committing any Admin status decision or destructive REJECTED resubmission. If confirmation fails or is uncertain, fail safely with no status commit/cleared reason. Return review 503 REVIEW_DEPENDENCY_UNAVAILABLE; never best-effort-log after committing and report success. The adapter must reconcile prepared/committed/aborted events, crashes and retries without orphan events masquerading as successful decisions or lost committed history; technical guarantees are prerequisites section 7/T02.

Restricted full-reason audit is distinct from ordinary metadata-only Auth/application/security logs. No credentials, request bodies, file bytes, URLs or full reasons in ordinary logs. Only authorized audit/review personnel and scoped services access restricted history; applicants retain complete own current reasons/status via existing own-role APIs. No new general audit/history viewer or applicant-history API is in scope.

REJECTED resubmission reuses the same membership and clears current decision fields only after complete prior history is confirmed durable; renew request time, set applicant mutation actor/time and increment version. PENDING/APPROVED/SUSPENDED duplicates remain 409; SUSPENDED cannot self-reset/reinstate. Passenger and independent other-role access are never removed.

## 8. API and frontend/backend responsibilities

The existing planned mutation remains PATCH /api/v1/admin/role-requests/{role_id}/review, with strict body decision, reason and version. AR-D09 adds GET /api/v1/admin/role-requests and GET /api/v1/admin/role-requests/{role_id}; AR-D07/D09 adds GET /api/v1/documents/{document_id}/file. Prerequisites sections 3-6 provide the exact request/response/error specification, including existing protected document list/detail/review, bounded search/pagination and optimistic concurrency. It is normative here; no replacement endpoint, schema field or silent workbook edit is implied.

Use the established Auth security boundary: missing/invalid credentials are unauthenticated; valid non-Admin credentials lack review permission; restricted accounts and revoked sessions fail under existing rules. Responses must be safe and must not reveal resource existence or evidence to an unauthorized caller. Validate resource IDs and allowed filters, handle missing records and stale versions without mutation, rate-limit bounded reads/actions, and fail closed when authorization, persistence or evidence dependencies are unavailable. Use the exact Auth-shaped error envelope and module-specific status/codes in prerequisites section 6. Non-Admin queue/detail/review is 403 ADMIN_REQUIRED; self-review is 403 REVIEW_FORBIDDEN; stale version is 409 VERSION_CONFLICT; unauthorized document IDs use safe 404 DOCUMENT_NOT_FOUND.

| Frontend responsibilities | Backend responsibilities |
|---|---|
| Guard routes and avoid private-data flashes; render queue/detail only after current authorization. | Enforce Admin/session/account authorization on every queue, detail, decision and related evidence request. Hiding navigation is not security. |
| Show current role/profile fields, filtered queue and honest loading/empty/error states. | Query only OWNER/DRIVER application records and return explicit field allowlists with bounded, validated filtering/pagination. |
| Expose only permitted actions, applicant-visible reason fields and confirmation. | Enforce permitted transitions, reason checks, document ownership/eligibility and expected-version concurrency in transactions. |
| Refresh current detail/queue after success or conflict; do not optimistically grant approval. | Return authoritative committed state and preserve current decision/audit evidence under existing persistence rules. |
| Clear private applicant/document state on logout, lost permission or account change. | Recheck current roles/accounts, preserve Auth session revocation, and deny further access immediately when authorization is lost. |
| Keep tokens in memory; private evidence and reasons out of browser storage, URLs and analytics. | Keep private files protected and logging safe; never publish evidence or grant approval from client claims. |

Retain the Travelly cream/burgundy visual style, sticky navbar and natural full-page scrolling in eventual desktop/tablet/mobile UI. All controls, reason labels, confirmation and errors must be keyboard/touch accessible, with status conveyed by text rather than colour alone. No new animation or polling infrastructure is required.

## 9. Acceptance scenarios

These are required future tests, not claims that implementation or tests have run during this documentation task.

| ID | Scenario | Required outcome |
|---|---|---|
| AR-01 | Authorized Admin opens the queue and filters Owner/Driver by each of PENDING, APPROVED, REJECTED, SUSPENDED. | Only matching real application records appear with correct identity, type, current submitted date and status; Passenger/Admin memberships are excluded. |
| AR-02 | Queue is genuinely empty, filters match nothing, a request fails or data is loading. | Distinct accurate states; no fabricated records/counts or failure disguised as empty success. |
| AR-03 | Normal Passenger or anonymous caller opens queue/detail URLs, changes role IDs or directly calls review/evidence APIs. | No review data, other-applicant evidence or decision authority; safe denial/login behaviour. Applicant's separate own-document/status access remains intact. |
| AR-04 | Authorized non-self Admin approves a PENDING Owner with required eligible evidence and current version. | Only OWNER becomes APPROVED; correct approval/mutation actor, time and version are stored. Passenger, Driver and contact verification are unchanged. |
| AR-05 | Authorized Admin rejects a PENDING Driver with a valid applicant-visible reason. | Only DRIVER becomes REJECTED; rejection reason and existing mutation actor/time/version evidence are recorded; no Driver workspace; Passenger retained. |
| AR-06 | Authorized Admin suspends an APPROVED role with a valid reason and current version. | Only that role becomes SUSPENDED with suspension/mutation evidence, retaining prior approval evidence. Subsequent protected role actions fail; Passenger remains available for an eligible account. |
| AR-07 | Applicant refreshes profile/roles after approval or suspension. | Approval adds only the matching ready card/switcher option without navigation. Suspension removes that option/card and returns an eligible active workspace to Passenger. Login/default context remains Passenger. |
| AR-08 | Owner is APPROVED while Driver is PENDING/REJECTED/SUSPENDED, or vice versa. | Only the independently approved role is selectable; rejection/suspension never removes Passenger or the other approval. |
| AR-09 | Applicant or Admin attempts self-review/self-approval, client-supplied actor/time, PASSENGER/ADMIN review, or undocumented transition. | Denied without privilege change, private-data disclosure or partial mutation. |
| AR-10 | Two Admins act on the same version, the user resubmits before a stale review commits, or a decision is retried. | No stale overwrite or duplicate transition; current state/version is authoritative and requires a fresh permitted review. |
| AR-11 | Reject/suspend reason is empty, whitespace-only or exceeds 2000 characters. | Validation failure; role and evidence unchanged; UI explains applicant visibility and permits correction. No unsupported approval/private-notes field is accepted. |
| AR-12 | Evidence is unavailable, belongs to another target, is unapproved/expired, or a protected document route is guessed or another session uses it. | No approval bypass or unauthorized retrieval. No private evidence appears in queue/public profiles/logs; file access remains authorized. |
| AR-13 | REJECTED applicant resubmits, or SUSPENDED applicant tries resubmission/reinstatement. | Rejected application follows existing same-row PENDING/version/evidence rules; suspended role cannot reset or reinstate. Required historical evidence must not be silently lost. |
| AR-14 | Admin or applicant account is restricted, or Admin role/session is revoked while detail is open. | Server checks override cached UI/role approval; private state is cleared appropriately. Role approval does not reactivate the account or verify contacts. |
| AR-15 | Decision fails during a transaction or required dependency is unavailable. | No partial status/evidence change, false success or fail-open authorization; safe failure and retry/refresh guidance. |
| AR-16 | Inspect successful decisions, logs, applicant responses and database inventory. | Existing current-state actor/time/reason fields plus complete historical actor/time/transition/full reason in restricted durable infrastructure; ordinary logs contain safe metadata only; applicant allowlists preserved; no new table/column, private note store or public document URL. |
| AR-17 | Navigate queue/detail/confirmation on desktop, tablet and mobile with keyboard/touch/reduced motion. | All supported controls, reasons and footer remain reachable; no clipped page, private-data flash or unsupported route/decision. |
| AR-18 | Owner evidence follows either own-registration or registered-owner/company-authorization branch; Driver supplies Sri Lanka-issued licence plus identity. | Exact accepted checklist enforced independently; no company account, unnecessary Owner licence or implicit vehicle approval. Foreign-driver licence approval deferred. |
| AR-19 | Reviewer marks required evidence NEEDS_CORRECTION. | Document result/reason retained; related role stays PENDING until a separate role decision; no automatic rejection. |
| AR-20 | Audit storage cannot confirm event or DB commit/retry/crash needs recovery. | No unconfirmed decision commits; complete prior reasons survive resubmission, and prepared/aborted events are not presented as committed decisions. |
| AR-21 | Same Admin has own Owner/Driver application and private documents. | Own queue/count exclusion and detail/review denial; separate own-file streaming read allowed without self-verification. |

## 10. Explicit non-goals

- Application code, tests, database data/schema changes, migrations, API-matrix edits or original PDF changes in this task; documentation changes are limited to the four authorized Markdown files.
- A general full Admin dashboard, analytics/export suite, unrestricted user management, Admin assignment UI, account suspension/reactivation UI or a generic permissions/configuration engine.
- New tables, undocumented persistence fields, a review-history entity, private-note storage, approval-reason field, new application statuses or arbitrary role editing.
- Document-module implementation, automatic document approval, evidence-free role approval, vehicle verification/publication or operational Owner/Driver dashboards.
- Automatic workspace switching, changed default login routing, removal of Passenger membership, contact verification or a separate Admin/Owner/Driver login.
- SUSPENDED reinstatement, appeals, withdrawal, bulk approvals and undocumented role transitions.
- Booking, vehicle, Ticket, rental, assignment, tracking, payment or settlement workflows and their state changes.
- Telephony/IVR, general promotions/coupon engines, subscriptions and secondary-owner delegation. Existing IN_APP/EMAIL scope is not expanded; SMS/OTP provider integration remains with Contact Verification.

## 11. Finalization and remaining technical build prerequisites

All nine accepted Admin Review decisions and AR-VUI are final. Individual-only Owners; exact Owner/Driver evidence alternatives and Sri Lanka licence issuer; document NEEDS_CORRECTION versus role rejection; all eligible APPROVED Admins except self-review; authenticated backend streaming only; restricted durable full-reason history with no-commit-on-audit-failure; and narrow queue/detail/file GET contracts are settled. No unresolved business decision remains.

This module's business/API contract is corrected and approved against Final Decisions and prerequisites sections 2-7. Technical prerequisites in prerequisites section 9 remain: complete 20-table PostgreSQL dictionary/API freeze, private document upload/storage/review capability, matrix/OpenAPI alignment, controlled Admin provisioning, and a configured durable audit adapter with tested acknowledgement, concurrency, crash/retry and rollback guarantees.

Readiness section 11 Stage B remains binding. Finalizing these four documents does not complete the remaining physical/API artifacts, select/deploy an audit sink, implement private documents, execute tests or open the full implementation gate. **Full Admin Application Review is not yet unconditionally APPROVED FOR BUILD while those technical prerequisites remain unsatisfied.** No new business-policy approval is required to carry out the accepted scope once the technical gate is met.

Approval/private reviewer notes, SUSPENDED reinstatement, general Admin dashboards, company onboarding, foreign-driver licence approval, the future vehicle operating-document checklist, IVR, subscriptions, secondary-owner delegation and general promotions/coupons remain excluded/deferred.
