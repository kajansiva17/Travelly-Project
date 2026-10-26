# Travelly NBP Owner and Driver Applications Contract

Version: 1.1 | Final business/API freeze: 25 October 2026

Status: FINAL business/application contract incorporating approved Admin Review gate D01-D09 (AR-D01-AR-D09). No unresolved business decisions in this scope. Technical implementation prerequisites and Readiness Stage B remain in section 12; no code/schema changes are made.

## 1. Purpose, authority and boundaries

Define how an existing Passenger applies for Owner and Driver roles, how application status affects the dashboard, and how authorized Admin review and private evidence must behave.

Read this contract with these authorities, in their existing precedence:

1. [Final Decisions](../00-READ-FIRST/01-TRAVELLY-NBP-FINAL-DECISIONS.md), especially project D01/D02/D07/D10/D11/D12/D13 and Admin Review gate AR-D01-AR-D09.
2. [Readiness Contract](../00-READ-FIRST/00-TRAVELLY-BACKEND-BUILD-READINESS.md), sections 1, 3, 4, 5, 6, 8 and 11.
3. [Auth Milestone Contract](../00-READ-FIRST/02-TRAVELLY-AUTH-MILESTONE-CONTRACT.md), including its 24 October implementation amendment and sections 2, 3, 5, 6 and 7. The amendment authorizes the existing application-submission API despite older deferred-submission wording below it.
4. [Approved Passenger Dashboard Contract](01-PASSENGER-DASHBOARD.md), especially sections 2, 3, 6 and 7.

This contract refines application behaviour; it does not override those authorities, replace the full source documents, revise the API matrix or introduce a physical schema. The authoritative 20-table architecture and corresponding API sources retain their existing precedence. The finalized [Admin Review](03-ADMIN-APPLICATION-REVIEW.md) and [Admin Review Prerequisites](04-ADMIN-REVIEW-PREREQUISITES.md) define the narrow accepted evidence, HTTP and audit refinements. Final Decisions expressly supersedes older conflicting source text. An unlisted disagreement must be resolved before implementing the affected operation.

The planned application-table count remains exactly 20. Application membership uses existing `users` and `user_roles`; private evidence uses the already planned `documents` module when its contract is frozen. No application, application-history, workspace, audit, session or role-catalogue table is added.

## 2. Permanent Passenger membership and independent roles

- Every registration creates one account and automatically APPROVED `PASSENGER` membership. Passenger membership remains permanent; applying, resubmitting, approval, rejection, suspension or workspace switching must never remove or replace it.
- Passenger is always the default workspace. Every successful login returns to `/dashboard`, after authenticated profile/role hydration. Approval never navigates the user automatically.
- An eligible registered Passenger may apply independently for `OWNER`, `DRIVER`, or both under the same account. Neither application requires the other role's approval. There is at most one `user_roles` row per user and role.
- The only application approval statuses are `PENDING`, `APPROVED`, `REJECTED`, `SUSPENDED`. Absence of a role row means "not applied" in the UI; it is not a fifth status. Do not add DRAFT, REQUESTED or UNDER_REVIEW role states.
- Contact verification is separate. `PENDING_VERIFICATION` is an account status, not a role-approval status. These accounts may access their own profile, role states and existing application submission. A normalized phone, application submission or Admin role decision never verifies a contact.
- Account `SUSPENDED`, `BLOCKED` or `CLOSED` still denies protected access under Auth. Permanent Passenger membership does not bypass account restrictions. A role suspension alone does not suspend the whole account or another independently approved role.
- Owner approval never implies Driver approval. Owner self-drive requires independently APPROVED Driver membership, current approved/unexpired required documents and all operation-specific eligibility checks.

## 3. Routes and access

| Route or entry | Access and behaviour |
|---|---|
| `/for-owners`, `/drive-with-us` | Public information only. Sign in goes to `/login`; account creation goes to `/register`. Public CTAs cannot submit or approve a role. |
| `/register`, `/login` | Retain existing Auth contracts. Registration creates Passenger only and goes to Login; login hydrates the current profile/roles and goes to `/dashboard`. |
| `/dashboard` | Authenticated Passenger home. Require eligible account, valid session and APPROVED Passenger membership. Show independent Owner/Driver application entries or real statuses. Anonymous access returns to `/login` without flashing private content. |
| Application entry or status detail | Start from the authenticated dashboard using the current account. Application UI may remain within `/dashboard`; this contract creates no additional frontend pathname. Show only the current user's application and permitted evidence. |
| Owner/Driver workspace entry | Only the corresponding current APPROVED role can enter by explicit selection. Operational workspace route definitions belong to their separate contracts; no new path or dashboard is invented here. |
| Admin application review | Server-authorized verification management, never a public or applicant-accessible action. The separate Admin Review contract defines /admin/applications and /admin/applications/{role_id}; prerequisites defines exact APIs. No review code is implemented by this document. |
| Private document action | Valid session plus document ownership or authorized Admin verification permission. Authentication alone never grants access to another applicant's evidence. |

All protected actions recheck current server account/role state. Workspace flags, URLs, hidden buttons and JWT role claims are not authorization. Missing/expired/revoked credentials follow Auth refresh/login rules; restricted accounts follow Auth denial rules. Own-session logout remains available as defined there. Retain memory-only token storage and clear private application state on logout/account change.

## 4. Required profile, application information and evidence

Use existing users identity/contact fields and user_roles membership only. Applicants submit role_code OWNER or DRIVER independently through the existing POST /api/v1/users/me/role-requests; PASSENGER/ADMIN cannot be requested. Request/decision times, status, actors and version remain server-controlled. No new applicant-type, company, age, bank, address or licence-class fields are introduced. user_roles.role_profile remains bounded non-authoritative preferences, never an application dossier, document store or approval source.

### 4.1 Accepted checklist (AR-D01-D05)

| Role / case | Required evidence using existing document types | Mapping and gate |
|---|---|---|
| Individual Owner, all cases | One NIC or PASSPORT. | Applicant-owned documents.user_id = users.id, vehicle_id NULL. Identity must be verified and match applicant. |
| Applicant is the vehicle's registered owner | VEHICLE_REGISTRATION demonstrating applicant ownership. | Store as applicant-owned evidence before vehicle onboarding; no fabricated vehicle record or mandatory existing vehicle FK. |
| Registered owner is another individual or a company | OWNER_AUTHORISATION from that registered owner/company authorizing the applicant. | Applicant-owned authorization evidence must establish the relevant registered-owner/company authority. Company is not a separate Travelly account. |
| Driver | One NIC or PASSPORT, plus Sri Lanka-issued DRIVING_LICENCE (issuing_country LK). | Applicant-owned verified evidence; foreign-driver licence approval deferred. An international phone number does not determine licence eligibility. |
| Owner also wants to drive | Independent Owner and Driver checklists/approvals. | No Owner-only licence requirement; Owner approval never grants Driver eligibility. |

Every required document must be current, APPROVED, correctly owned/relevant and unexpired where expiry applies, with trusted reviewer/time evidence, before role approval. Refer to prerequisites sections 2.2-2.4 for exact columns, status catalogue, date validation and supersession. NEEDS_CORRECTION keeps the related role PENDING; role REJECTED requires a separate Admin decision. NIC/PASSPORT alternatives do not impose Sri Lankan citizenship on Passengers or Owners.

Full company-account onboarding is deferred. BUSINESS_REGISTRATION and BANK_PROOF remain existing planned document types but are not additional mandatory requirements for these individual roles. Vehicle verification and its operating documents remain a separate future module.

Current submission compatibility is unchanged: optional supporting_document_ids must be empty until the document module is implemented. The accepted review scope derives current evidence from user_roles.user_id = documents.user_id and the checklist; it does not persist a per-attempt attachment list or decision-time document snapshot. No role_id/application_id FK or join table is invented. Shared valid personal identity evidence may satisfy both roles independently.

### 4.2 Accepted Vehicle Document UI rule (AR-VUI)

- Required: all relevant vehicles must provide it before submission/verification.
- Required for your case: mandatory only when the applicant/registered-owner/company situation requires it.
- Optional: may be uploaded but never blocks submission or verification.
- Exact vehicle operating-document checklist remains for the future Vehicle Management Contract.

Apply these labels without new columns or statuses. Role-application ownership/authorization evidence above is distinct from the future vehicle operating-document checklist. An optional file must not become a submission/verification blocker.

## 5. Submission, duplicates and resubmission

| Existing membership | Permitted applicant action | Required result |
|---|---|---|
| No OWNER/DRIVER row | Submit that role application. | Create one PENDING membership; 201 existing RoleResponse. Passenger is unchanged. |
| PENDING | Read status and authorized own evidence; follow accurate next-step guidance. | Duplicate submission is 409 `ROLE_ALREADY_REQUESTED`; no second row or new request timestamp. |
| APPROVED | Explicitly select the approved workspace when desired. | Duplicate submission is 409; no new application or automatic workspace switch. |
| REJECTED | Correct the stated issue using supported capabilities and resubmit that role. | Reuse the same membership ID, change to PENDING, renew `requested_at`, clear decision fields, update audit timestamps/actor and increment version. Return 201 RoleResponse. Preserve prior full actor/time/status/reason history through the approved restricted durable audit infrastructure before commit. |
| SUSPENDED | Read the reason and seek authorized support/review. | Submission remains 409. No new row, self-reinstatement or automatic reset to PENDING/APPROVED. |

The rejected resubmission clears `approved_at`, `approved_by`, `rejection_reason`, `suspended_at` and `suspension_reason` for the new pending request, while retaining immutable identity and creation history. The backend must preserve prior full decision evidence under AR-D08 and prerequisites section 7 before replacing it; it must not add a history table. If durable audit storage cannot confirm preservation, fail safely without clearing fields or committing the resubmission.

Process each request transactionally and enforce existing `(user_id, role_code)` uniqueness, including concurrent requests. A failed request must not partially mutate a membership or affect Passenger/other-role access. Reload authoritative role/profile state after success or conflict; do not optimistically show approval.

There is no approved SUSPENDED reinstatement transition in the current authorities. Administrative correction, appeal handling and any future reinstatement route/payload must be explicitly resolved before implementation. Contact verification, document replacement or filing another role request must never bypass a suspension. Independently applying for the other role remains allowed for an otherwise eligible account.

## 6. Admin review and audit expectations

| Current status | Authorized decision | Required evidence/effect |
|---|---|---|
| PENDING | APPROVED | Authorized active Admin reviewer, expected current version and applicable required approved/unexpired evidence. Set server `approved_at` and `approved_by`; record mutation actor/time/version. Affect only the reviewed role. |
| PENDING | REJECTED | Authorized Admin decision with non-empty trimmed `rejection_reason` of 1-2000 characters, expected current version and recorded decision evidence. No workspace granted. |
| APPROVED | SUSPENDED | Authorized Admin decision with server `suspended_at`, non-empty trimmed `suspension_reason` of 1-2000 characters, expected current version and recorded mutation actor/time/version. Deny subsequent protected actions for that role. |
| Any other transition | Not authorized by the current contract. | Reject without mutation; no direct REJECTED/SUSPENDED to APPROVED or arbitrary status rewrite. REJECTED to PENDING is applicant resubmission under section 5. |

Every eligible APPROVED Admin may review other applicants; eligibility is the existing valid session/account checks plus current APPROVED ADMIN membership, with no additional reviewer flag. An Admin cannot review their own application or verify their own documents, including approval, rejection or suspension. Exclude self applications from queue/counts and deny own Admin detail; retain separate own-document read rights. No public Admin signup, applicant self-review/self-approval or client-supplied timestamps are allowed. Review must evaluate document ownership, relevance, approval and expiry; role approval must never substitute for document review or vehicle verification.

Use the existing review operation `PATCH /api/v1/admin/role-requests/{role_id}/review`. Concurrent/stale reviews must not overwrite one another; enforce the expected version and update the role atomically. Prerequisites sections 3-6 freeze the exact DTOs/errors and required JSON version transport; stale version is 409 VERSION_CONFLICT with no mutation.

Keep current decision evidence in existing role fields. AR-D08 separately requires restricted durable audit infrastructure outside application tables to retain actor, timestamp, previous status, new status and full applicant-visible reason for every decision and resubmission. Approval has NULL reason; rejection/suspension retain complete text. Confirm durable preservation before status commit or clearing prior fields; audit failure fails safely with no commit. Ordinary application/security logs remain metadata-only. Do not write full reasons, credentials, request bodies or private files into ordinary logs, role_profile, session storage or any improvised table/JSON store. Prerequisites section 7 specifies correlation, commit/recovery and access requirements; selecting/configuring that infrastructure is a technical prerequisite, not an unresolved business-policy choice.

Review, rejection or suspension must not delete identity/membership history, mutate contact-verification timestamps, remove Passenger membership or change the other role. Account restriction is a separate authorized account action. Role suspension takes effect on subsequent protected authorization checks, independently of UI refresh.

## 7. Private documents and verification access

- Authenticated users may access their own personal documents, including while an application is PENDING, REJECTED or SUSPENDED, subject to account/session eligibility. An approved Owner/Driver role is not a prerequisite for own-document access.
- Owners may access owned vehicle documents under the separate ownership checks. Another Owner, Driver or Passenger cannot read an applicant's private evidence merely by holding an operational role.
- Every eligible APPROVED Admin has verification access for other applicants under AR-D06; no self document verification or application review. Check authorization and resource ownership on metadata, file retrieval and every protected document action; a guessed document ID must not widen access.
- File bytes are delivered only by GET /api/v1/documents/{document_id}/file with authenticated backend streaming and authorization on every request. No public/signed URLs, provider redirects or reusable download grants, including internal signed retrieval. Private keys/files never appear in public profiles, discovery, public images or responses. `/users/me` and role responses remain allowlisted and do not embed private evidence.
- Uploads must validate type, size and ownership under the document module. No upload/review UI or success claim is available until that module exists. Pending applicants cannot bypass the empty-supporting-document restriction in the current submission API.
- A document marked NEEDS_CORRECTION keeps the role PENDING; a separate Admin role decision is required to reject it. Document review states are separate from role approval. A file upload, contact verification or document approval does not automatically approve either role. Expired or missing required evidence must not be treated as operational readiness.

## 8. Passenger dashboard, switcher and presentation states

Maintain separate Owner and Driver cards/statuses using the authenticated user's current role responses. A pending/rejected/suspended role stays in Passenger context for that application; a separately APPROVED other role remains available through explicit selection.

| State | Dashboard presentation | Switcher and readiness |
|---|---|---|
| Not applied | Offer "Become an Owner" or "Drive with Travelly" using the existing account. | No option or ready card for that role. |
| PENDING | Show application pending and only supported next steps. No invented review deadline or approval promise. | No option or ready card for that role. |
| APPROVED | Show real approval and the corresponding Owner-ready/Driver-ready entry. | Include that role; explicit selection only. Approval alone does not guarantee operational eligibility. |
| REJECTED | Show the allowlisted own rejection reason and reapply action. | No option or ready card for that role. |
| SUSPENDED | Show the allowlisted own suspension reason and honest support/review guidance. Do not invent a support destination or reinstatement button. | Remove that role's option/ready card; no self-reactivation. |
| Loading or failed role read | Show loading, retry or unavailable state, retaining safe access boundaries. | Never infer approval or absence of an application from a failed request. |

Passenger always remains the default and selectable for an eligible account. Switcher options come only from current APPROVED memberships; PENDING/REJECTED/SUSPENDED roles are not listed even as disabled options. A switch changes working context only, never stored membership or the default login destination. Return to `/dashboard` selects Passenger. No persisted workspace preference is introduced.

After an authoritative role refresh, approval adds the appropriate option/card without navigation. Suspension removes it and returns an otherwise eligible user from the affected workspace to Passenger; server checks deny restricted actions immediately without waiting for the refresh. No polling/realtime service is required here.

Keep the Passenger home, discovery actions and accurate contact reminder available within existing authorization. New users retain polished no-journey/no-booking states; applications must not fabricate journeys, earnings, vehicles, assignments, approvals or counts. A missing later service is unavailable, not proof of an empty successful result. Retain accessible Travelly styling, sticky navbar and natural full-page scrolling on desktop, tablet and mobile.

## 9. API and implementation responsibilities

| Existing API | Responsibility and boundary |
|---|---|
| `GET /api/v1/users/me` | Return the authenticated user's allowlisted profile and currently approved roles; no private document/reviewer leakage. |
| `GET /api/v1/users/me/roles` | Return all own memberships/states using the existing RoleResponse allowlist, not another user's applications. |
| `POST /api/v1/users/me/role-requests` | Existing authenticated submission: body `{ "role_code": "OWNER" }` or DRIVER; optional supporting_document_ids remains empty until documents exist. Return 201 RoleResponse/PENDING for first application or rejected resubmission; duplicates in other states return 409 `ROLE_ALREADY_REQUESTED`. |
| `PATCH /api/v1/admin/role-requests/{role_id}/review` | Existing planned Admin-only review; enforce section 6 and the exact accepted DTO/error/evidence/version contract in prerequisites sections 3-7. |
| Admin reads / protected documents | Prerequisites sections 3-6 freeze the accepted queue/detail GETs, protected streaming GET, existing document metadata reads and existing review PATCH. Upload/ingestion remains a separate technical contract prerequisite. |

Submission retains the Auth error envelope and existing validation/authentication/account/rate/dependency behaviour: malformed JSON 400, missing/invalid session 401, restricted account 403, duplicate role 409, invalid/unknown fields or role code 422, throttling 429 with Retry-After, and unavailable required dependencies 503. Never accept user-controlled approval, verification or reviewer fields. Review/document operations use the exact module errors in prerequisites section 6, rather than borrowing Auth codes by assumption.

Frontend responsibilities: guard private rendering, invoke existing own-profile/role/submission APIs, show server-derived status/reasons, handle errors honestly, refresh authoritative state, keep workspace changes explicit and clear stale user data. Do not create approval, evidence or future operational API responses locally.

Backend responsibilities: derive the caller from the session; enforce account eligibility, ownership, independent role transitions and uniqueness; return only allowlisted data; use transactions/version checks; preserve decision evidence; deny unauthorized review/document/operational access regardless of UI. Do not treat a switched workspace or supplied user/role ID as permission.

## 10. Acceptance scenarios

These are required future acceptance scenarios, not a claim that implementation or tests run in this documentation task.

| ID | Scenario | Expected result |
|---|---|---|
| OD-01 | New registered Passenger logs in without other roles. | `/dashboard` in Passenger context; one APPROVED Passenger membership; two application entries; real empty states, no fake journeys. |
| OD-02 | Passenger applies for Owner, Driver, then both independently in isolated cases. | Each first request returns 201/PENDING for the selected role under the same user. Passenger/default context and the other role remain unchanged. |
| OD-03 | PENDING_VERIFICATION Passenger submits with valid session. | Existing submission is permitted; contact remains unverified and Passenger remains APPROVED. No contact/SMS verification is implied. |
| OD-04 | Duplicate or concurrent PENDING/APPROVED/SUSPENDED request. | Existing uniqueness holds; 409 for the duplicate; no additional account/membership or unauthorized status change. |
| OD-05 | Authorized Admin approves eligible PENDING Owner or Driver. | Correct reviewer/time/version evidence; only reviewed role becomes APPROVED. On role refresh its switcher option/ready card appears; Passenger remains current until explicit selection. |
| OD-06 | Admin rejects a PENDING application with a valid reason. | REJECTED plus own visible reason; no workspace/ready card; Passenger unaffected. Empty/overlong required reason is rejected. |
| OD-07 | REJECTED applicant resubmits. | Same role ID returns to PENDING with renewed request time, cleared decision fields, incremented version and prior evidence preserved; Passenger unchanged. |
| OD-08 | Admin suspends an APPROVED role while its workspace is active. | SUSPENDED with valid reason/server time; subsequent protected role actions denied; refresh removes its option/card and returns eligible user to Passenger. |
| OD-09 | SUSPENDED user replaces a document or requests that role again. | No reinstatement; duplicate submission is 409, status remains SUSPENDED and support/review guidance is honest. |
| OD-10 | Owner APPROVED with Driver PENDING/REJECTED/SUSPENDED, or reverse. | Only independently approved additional workspace is available. Passenger remains default; Owner alone cannot self-drive. |
| OD-11 | APPROVED multi-role user switches, logs out and logs in again. | Explicit context switch never changes memberships; new login and `/dashboard` return to Passenger. |
| OD-12 | Applicant or unauthorized reviewer attempts self-review/self-approval, Admin application, another user's ID or stale review version. | Denied without unauthorized mutation/data disclosure. Concurrent reviews cannot overwrite a committed decision. |
| OD-13 | Pending/rejected/suspended eligible applicant accesses own documents; another user guesses those IDs. | Applicant's own-document access is permitted under document authorization; other-user access denied. Authorized Admin verification access succeeds; public profile contains no private evidence/keys/URLs. |
| OD-14 | Required evidence is missing, unapproved or expired. | No fabricated readiness/approval bypass; document and operational eligibility checks remain enforced. |
| OD-15 | Account becomes SUSPENDED/BLOCKED/CLOSED despite approved roles. | Existing Auth account restrictions override workspaces; own logout remains allowed. Role state alone cannot reactivate the account. |
| OD-16 | Role request/read fails or document module is absent. | Honest error/unavailable state; no invented application, approval, upload success or false empty state; supporting document IDs remain empty. |
| OD-17 | Another user logs in, browser Back is used, or session expires. | Clear prior applicant data/context and enforce Auth navigation; no cross-user evidence/status leakage. |
| OD-18 | Review schema/scope and responsive application states. | No new tables/role statuses or undocumented endpoints, IVR or coupons; all supported controls and footer reachable on mobile/desktop, including reduced-motion use. |
| OD-19 | Individual Owner supplies NIC/PASSPORT with own vehicle registration, or another registered owner's/company authorization. | Correct evidence branch; no Owner-only driving licence, new company account or fabricated vehicle row. Required evidence verified before approval; vehicle verification remains separate. |
| OD-20 | Driver supplies foreign licence or Sri Lanka-issued licence plus NIC/PASSPORT. | Foreign-licence approval deferred; only the Sri Lanka-issued verified licence/identity combination satisfies this checklist. International Passenger phone registration unchanged. |
| OD-21 | Required document is NEEDS_CORRECTION; Optional vehicle evidence is absent. | Role remains PENDING until a separate role decision; Optional never blocks submission/verification. |
| OD-22 | Audit sink cannot confirm a decision/resubmission, or retries/crashes occur. | No unconfirmed status commit or cleared historical reason; restricted full actor/time/status/reason history remains durable and ordinary logs remain metadata-only. |
| OD-23 | Admin reads own documents versus opening own Admin application detail/review. | Own protected document read allowed as owner; own review/detail/verification denied and own role excluded from review queue/counts. |

## 11. Deferred items and explicit non-goals

- This task finalizes only the four authorized Markdown contracts: no application code, tests, migrations, schema, database data, API-matrix edits or original PDF changes.
- No Owner/Driver/Admin operational dashboard, vehicle listing/verification, booking, Ticket, rental transaction, assignment, tracking, payment, payout or settlement implementation is authorized here.
- Full document upload/review and Admin decision implementation remain behind their respective physical/API freezes. No private files are embedded in profile preferences or new application tables.
- Contact verification is a separate module. SMS/OTP delivery/provider integration, recovery, MFA and persistent browser sign-in are not implemented by an application flow or reminder.
- SUSPENDED reinstatement, appeals workflow and application withdrawal are not authorized transitions. No additional role statuses or fabricated deadlines are introduced.
- Telephony/IVR, subscriptions, secondary-owner delegation and general promotions/coupons are excluded from the current NBP. No calls, callbacks, coupon engine or promotion-driven application approvals are included. Current operational notification channels remain IN_APP/EMAIL under existing contracts; no new delivery mechanism is created here.

## 12. Finalized decisions and technical build gate

AR-D01-AR-D09 and AR-VUI are accepted in Final Decisions. The checklist, individual-only Owner model, Sri Lanka-issued Driver licence, NEEDS_CORRECTION effect, all-eligible-Admin/no-self-review rule, streaming-only retrieval, durable full-reason history and narrow Admin GET contracts are final. There is no remaining business decision in this module.

The exact HTTP contract is prerequisites sections 3-6; existing current-state columns and approved external audit mapping are sections 2/7/9. Rejected resubmission preserves history before clearing current fields; suspended resubmission/reinstatement remains excluded. These rules cannot be relaxed for a missing implementation dependency.

Technical prerequisites remain: freeze the complete planned 20-table physical dictionary and corresponding API artifacts under Readiness section 11 Stage B; align the API matrix/OpenAPI in a separately authorized stage; implement private document ingestion/storage/review from existing planned columns; configure and validate the restricted durable audit sink and database commit/recovery guarantees. No extra application table is permitted. Required future acceptance tests must demonstrate these guarantees.

The business/API documentation is finalized and can support the corrected Admin Review contract. This document does not itself satisfy Stage B or declare the full implementation gate passed. Company onboarding, foreign-driver licence approval, exact vehicle operating documents, SUSPENDED reinstatement, IVR, subscriptions, secondary-owner delegation and general promotions/coupons remain deferred/non-goals.
