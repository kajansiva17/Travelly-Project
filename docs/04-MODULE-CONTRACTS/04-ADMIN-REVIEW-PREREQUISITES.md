# Travelly NBP Admin Review Prerequisites

Version: 1.2 | Business and technical documentation freeze: 25 October 2026

Status: FINAL. Accepted AR-D01-AR-D09 business rules and TR-D01-TR-D08 technical decisions are frozen. The 20-table physical dictionary, scoped OpenAPI/API matrix and technical acceptance checklist complete the Admin Review documentation gate. APPROVED FOR BUILD for the bounded module and its document/audit dependencies; no code, migration, live configuration or runtime acceptance is claimed complete.

## 1. Authority, source findings and change boundary

This contract addresses private evidence, Admin APIs and decision-history prerequisites. Final Decisions and Readiness retain their existing precedence. This document does not replace the full sources or silently change their status, privacy or scope rules.

Read with:

- [Final Decisions](../00-READ-FIRST/01-TRAVELLY-NBP-FINAL-DECISIONS.md), all accepted decisions and supersession entries, particularly project D01/D02/D07/D10/D11/D12/D13 and accepted Admin Review AR-D01-AR-D09/AR-VUI.
- [Readiness Contract](../00-READ-FIRST/00-TRAVELLY-BACKEND-BUILD-READINESS.md), sections 5-8 and 11.
- [Auth Contract](../00-READ-FIRST/02-TRAVELLY-AUTH-MILESTONE-CONTRACT.md), its amendments and sections 2.2, 3, 5-7.
- [Passenger Dashboard](01-PASSENGER-DASHBOARD.md), sections 6-7; [Owner/Driver Applications](02-OWNER-DRIVER-APPLICATIONS.md), sections 4-9 and 12; [Admin Application Review](03-ADMIN-APPLICATION-REVIEW.md), sections 4-8 and 11.

Original PDF source files remain unchanged. The editable matrix is synchronized in this technical stage:

| Alias | Exact reference and relevant locations |
|---|---|
| 02A | [20-table architecture](../02-DATABASE/02A-TRAVELLY-DATABASE-ARCHITECTURE-FINAL-20-TABLES.pdf.pdf), printed pp3-5 sections 2.1, 4.1-4.3; p15 section 6.1; p18 document transitions; pp19-20 constraints/indexes/privacy; p22 implementation boundary. |
| 02B | [Lecturer database design](../02-DATABASE/02B-TRAVELLY-NBP-DATABASE-DESIGN-LECTURER-TEMPLATE.pdf.pdf), pp3-4 attributes, p10 relational schema, p12 infrastructure logs, p13 Phase 2 advanced audit-event versioning. Supporting, not an override of 02A/Auth. |
| 03A | [API plan](../03-API/03A-TRAVELLY-NBP-API-PLAN.pdf.pdf), pp4-5 HTTP/errors, p7 RoleReview/Document DTOs, p8 pagination/ErrorResponse, p9 signed storage and safe logging. |
| 03B | [Endpoint matrix](../03-API/03B-TRAVELLY-API-ENDPOINT-MATRIX-96-ENDPOINTS.xlsx.xlsx), Sheet1 operations #7-13, Excel rows 8-14. |
| 01 | [Original proposal](../01-PROPOSAL/01-TRAVELLY-PROJECT-PROPOSAL-NBP-V1.0.pdf.pdf), pp2/5 Driver eligibility and Admin document review, pp9/12 safeguards, p14 correction trails. It supplies no exact alternative Owner evidence checklist or role-decision history table. |

02A lists 20 application tables and no role-review history table. AR-D08 now approves restricted durable audit infrastructure outside those tables for full decision history. Ordinary Auth logs remain metadata-only; this separate restricted channel may retain full reasons and status transitions. Final Decisions explicitly supersedes the prior claim that this policy choice is unresolved. The implementation approach is frozen in section 7: a restricted append-only durable intent/outcome journal with ordinary PostgreSQL commit and xid8 outcome reconciliation. No prepared transactions or two-phase commit. The approved design is not a claim that the implementation/configuration already exists.

This technical finalization creates the physical dictionary, scoped OpenAPI/API companion and acceptance checklist, updates this prerequisite contract, Final Decisions and the editable API matrix. Application source, tests, frontend UI, live schema/configuration, migrations and original PDFs remain unchanged. Documentation approval permits the next implementation stage; runtime capabilities are implementation deliverables, not prerequisites that must somehow be coded before coding can begin.

Read the new normative technical artifacts: [02C physical dictionary](../02-DATABASE/02C-TRAVELLY-PHYSICAL-DATA-DICTIONARY.md), [03C OpenAPI](../03-API/03C-TRAVELLY-ADMIN-REVIEW-OPENAPI.json), [03D API contract](../03-API/03D-TRAVELLY-ADMIN-REVIEW-API-CONTRACT.md), and [05 technical acceptance](05-ADMIN-REVIEW-TECHNICAL-ACCEPTANCE.md).

## 2. A - Existing document and application mappings

### 2.1 Identity, ownership and application scope

| Requirement | Exact existing table/column mapping | Frozen interpretation |
|---|---|---|
| Applicant identity | `users.id`, `public_user_reference`, `full_name`, `email`, `phone_e164` | One existing person/account; only authorized allowlisted profile fields are returned. |
| Contact verification | `users.account_status`, `email_verified_at`, `phone_verified_at` | Separate from document and role approval. Neither normalization nor an Admin role decision verifies a contact. |
| Application identity | `user_roles.id`, `user_id`, `role_code`, `requested_at`, `approval_status`, `version` | One existing membership per user/role. Only OWNER/DRIVER are review targets. Passenger remains permanent/default. |
| Personal document owner | `documents.user_id` -> `users.id`; `vehicle_id` NULL | Includes a pending applicant's own evidence. No approved Owner/Driver role is needed to read one's own documents. |
| Vehicle document owner | `documents.vehicle_id` -> `vehicles.id`; `user_id` NULL; `vehicles.owner_user_id` -> `users.id` | Existing vehicle ownership determines private access. A role alone never grants access to another person's vehicle evidence. |
| Application-to-personal-document scope | `user_roles.user_id = documents.user_id`, plus the role's accepted document-type checklist | A derived current-evidence view, not a new stored relationship. Shared eligible evidence can be evaluated for both roles independently. |
| Application-to-vehicle-document scope | `user_roles.user_id = vehicles.owner_user_id` and `vehicles.id = documents.vehicle_id` | For private vehicle-document access after a genuine vehicle exists; initial Owner approval uses applicant-owned registration/authorization evidence and does not require creating a vehicle. |

Exactly one of `documents.user_id` and `vehicle_id` must be non-NULL, as specified by 02A. All FKs refer to the already planned tables. No `application_id`, `role_id`, applicant-document join table or membership ID hidden in JSON is added.

The accepted scope uses current applicant-owned evidence filtered by the checklist, not a per-attempt submitted-document list or decision-time evidence snapshot. No such snapshot is required or claimed by this module. Historical decisions/reasons are retained separately under AR-D08, not by inventing a document-to-role FK or JSON history. Existing submission continues to require empty supporting IDs until the document module is implemented; these read contracts do not expand that request payload.

### 2.2 Planned documents columns

The names below all occur in 02A section 4.3, or its section 2.1 common columns. 02C now freezes column-specific SQL types/lengths, nullability/defaults, FK actions, CHECKs/indexes and common audit/version fields for all 20 planned tables. It defines vehicles before documents and preserves the existing Auth baseline; this resolves documentation prerequisite T01 without applying a migration.

| Existing planned columns | Meaning and validation |
|---|---|
| `id` | Immutable UUID document PK. |
| `user_id`, `vehicle_id` | Nullable UUID FKs with the exclusive owner rule above. |
| `document_type` | Existing VARCHAR(60) catalogue: NIC, PASSPORT, DRIVING_LICENCE, BUSINESS_REGISTRATION, OWNER_AUTHORISATION, BANK_PROOF, VEHICLE_REGISTRATION, REVENUE_LICENCE, INSURANCE, EMISSION, FITNESS, ROUTE_PERMIT. No arbitrary client-created type. |
| `document_number`, `issuing_country`, `issue_date`, `expiry_date` | Existing evidence identifiers/issuer/date columns. Dates are DATE under 02B; country is an uppercase ISO alpha-2 value in the API, not inferred from the registration phone code. Issue cannot follow expiry. Mandatory/expiry applicability is defined by the accepted document-type policy. |
| `storage_key`, `secure_file_url` | Controlled private storage reference and secure access reference. `storage_key` is server-controlled. Never accept an arbitrary client URL as verified evidence or store a public file URL. No signed-URL approach is permitted, internally or externally. The secure_file_url compatibility field can represent only the protected backend path, never an object-store URL or credential. |
| `original_file_name`, `mime_type`, `file_size_bytes`, `file_checksum` | Existing file metadata. Server verifies object existence, real MIME/size and SHA-256 checksum; sanitize display filename. 02B identifies BIGINT for file size. |
| `status` | Existing document state: DRAFT, SUBMITTED, UNDER_REVIEW, APPROVED, REJECTED, NEEDS_CORRECTION, EXPIRED, SUPERSEDED. These are not role states. |
| `submitted_at`, `verified_by`, `verified_at`, `rejection_reason` | Existing submission/reviewer/result/reason evidence. Reviewer is an authorized Admin; timestamps are server UTC. |
| `superseded_document_id` | Existing UUID self-FK for retained replacement evidence. For this module, the replacement row points to the prior document; do not overwrite the prior file/identity. Reject cycles or cross-owner replacements. |
| `created_at`, `updated_at`, `created_by`, `updated_by`, `version` | Common audit/concurrency columns from 02A section 2.1; their document-specific physical constraints are frozen in 02C. No new decision-history column is inferred from these fields. |

Use the existing suggested indexes on `(user_id, document_type, status)`, `(vehicle_id, document_type, status)` and `(expiry_date, status)`. Retain superseded rows/files under the accepted retention policy; an applicant cannot delete reviewed evidence to erase a prior decision.

### 2.3 Frozen required evidence and Vehicle Document UI rules

AR-D01-AR-D04 resolve the previous checklist/company/issuer business gaps:

| Role / case | Exact required existing document types | Storage/approval rule |
|---|---|---|
| Individual Owner identity, every case | NIC or PASSPORT, one valid alternative. | documents.user_id = applicant users.id, vehicle_id NULL; verify identity matches the applicant. |
| Owner applicant is registered vehicle owner | VEHICLE_REGISTRATION proving the applicant owns the vehicle. | Applicant-owned evidence under documents.user_id before vehicle onboarding. A vehicles row is not required or fabricated for role approval. |
| Registered owner is another individual/company | OWNER_AUTHORISATION from that registered owner/company. | Applicant-owned evidence proving management authority for the relevant vehicle/registered owner. A company is not a Travelly account. |
| Driver | NIC or PASSPORT plus DRIVING_LICENCE issued in Sri Lanka (issuing_country LK). | Same applicant-owned mapping; verified identity/licence must match. Foreign-driver licence approval is deferred. |
| Owner who self-drives | Both independent role checklists and approvals. | Driving licence is not required for Owner-only approval. Operational eligibility remains separate. |

Each required item must be APPROVED, owned by the applicant, relevant to the role/ownership case, not SUPERSEDED, with trusted verified_by/verified_at and unexpired where applicable. Missing, DRAFT, SUBMITTED, UNDER_REVIEW, REJECTED, NEEDS_CORRECTION, EXPIRED or SUPERSEDED items cannot satisfy approval. Identity alternatives share evidence across roles without merging their approvals.

Owner accounts are individual-only. Company-account onboarding is deferred; no applicant-type/company/bank fields, synthetic company users or new relationships. BUSINESS_REGISTRATION/BANK_PROOF remain existing planned types, not added mandatory role evidence. Do not add citizenship, age, licence-class or other application fields under this freeze. Sri Lanka-issued Driver licence policy does not restrict international Passenger registration.

AR-D05: NEEDS_CORRECTION keeps the related role PENDING. A document correction, rejection, replacement or approval never automatically rejects, approves or reinstates a role. Admin must separately choose an authorized role decision. Passenger membership/contact verification are never document-review outcomes.

Accepted Vehicle Document UI rule (AR-VUI):

- Required: all relevant vehicles must provide it before submission/verification.
- Required for your case: mandatory only when the applicant/registered-owner/company situation requires it.
- Optional: may be uploaded but never blocks submission or verification.
- Exact vehicle operating-document checklist remains for the future Vehicle Management Contract.

These are derived UI/eligibility labels, not new columns or stored statuses. The role ownership/authorization checklist above does not freeze vehicle operating documents or verify/publish a vehicle.

Expiry is evaluated against server time in Asia/Colombo: a date-only expiry is valid through that local date and fails from the next local day. NULL expiry is acceptable only for a genuinely non-expiring evidence type; it is never an escape from a required licence expiry. Recheck expiry, identity, ownership and status during role approval.

### 2.4 Private retrieval and verification

Authenticate every metadata/file request. Permit the personal document owner, the owning vehicle's authorized Owner, or an eligible authorized Admin reviewer. Deny unrelated Passengers/Owners/Drivers even with a valid document ID. Check current account/session state; role suspension does not remove otherwise eligible own-document access. Non-Admins cannot enter the Admin queue/detail API, but applicants keep their own-document/status rights under D11.

The browser never receives a storage key or a public object URL. Document detail returns an authenticated same-origin retrieval path in the existing response field `secure_file_url`. The frontend fetches it with Bearer credentials and displays a temporary local blob URL; no tokens in query strings/history. The protected file endpoint reauthorizes each fetch, streams private storage content, sets `Cache-Control: no-store`, `X-Content-Type-Options: nosniff` and a sanitized Content-Disposition, and never redirects to public storage. No public/signed URL approach is allowed, including internal provider-signed retrieval. Fetch storage through private backend credentials/SDK and stream bytes without a storage redirect; tokens never appear in URLs.

Document verification uses the already planned Admin document-review operation. SUBMITTED -> UNDER_REVIEW records the review-start mutation actor/time; UNDER_REVIEW -> APPROVED, REJECTED or NEEDS_CORRECTION records `verified_by`, `verified_at`, `updated_by`, `updated_at` and increments `version`. REJECTED/NEEDS_CORRECTION require a trimmed 1-2000-character applicant-visible reason in existing `rejection_reason`; APPROVED has no free-text note and clears the current correction/rejection reason only after required history preservation is available. Only a new retained replacement row corrects a reviewed file; opening/downloading does not verify it.

The document's existing status/reviewer/reason fields retain a current result, not all past review events. History requirements in section 7 also apply before overwriting required document review evidence. Role approval additionally rechecks every required document's ownership, relevance, status, supersession and expiry atomically with the role decision. Unavailable evidence services or an unsatisfied accepted checklist block approval; there is no evidence-free override.

## 3. B - HTTP boundary and endpoint inventory

This section freezes exact HTTP refinements as documentation only and synchronizes the editable API matrix. It adds no application table/column. Existing operations retain their methods/paths. The three additional read paths below are explicitly new **API documentation additions** needed for the requested queue/detail/protected retrieval, not endpoints found in the original 96-entry matrix. AR-D09 approves these additions. Matrix IDs 97/98/99 and the scoped 03C/03D contract now synchronize them; existing IDs 1-96 are unchanged. Upload #10 is multipart, document detail #12 no longer delivers signed storage URLs. This resolves the documentation part of T03, not the runtime implementation.

| Method and path | Origin | Authorization |
|---|---|---|
| GET `/api/v1/admin/role-requests` | New queue read defined here; no matching original 03B operation. | Eligible authorized APPROVED Admin only. |
| GET `/api/v1/admin/role-requests/{role_id}` | New detail read defined here; no matching original 03B operation. | Same Admin authorization, OWNER/DRIVER target only. |
| GET `/api/v1/documents` | Existing 03B #11, Excel row 12. | Personal owner, owned-vehicle Owner or authorized Admin; results scoped before counting/pagination. |
| GET `/api/v1/documents/{document_id}` | Existing 03B #12, Excel row 13. | Same resource-specific document authorization. |
| GET `/api/v1/documents/{document_id}/file` | New protected streaming read defined here; no matching original 03B operation. | Same ownership/reviewer checks on every fetch. |
| PATCH `/api/v1/admin/documents/{document_id}/review` | Existing 03B #13, Excel row 14. | Authorized Admin verification access only. |
| PATCH `/api/v1/admin/role-requests/{role_id}/review` | Existing 03B #9, Excel row 10. | Authorized Admin only; all self-review prohibited. |

Reuse the Auth Bearer access-token/session mechanism and controlled Admin provisioning. AR-D06 makes every eligible APPROVED Admin a reviewer: valid current session, account permitted by Auth and current APPROVED ADMIN membership; no additional permission bit or reviewer subset. Account SUSPENDED/BLOCKED/CLOSED is denied. An Admin cannot review their own role application or verify their own personal/owned-vehicle documents, including reject/suspend actions; separate personal document reads remain allowed by ownership. Exclude their own applications from queue/counts; own Admin detail and self-review PATCH return 403 REVIEW_FORBIDDEN. No client permission flag, public Admin signup, new login or permission table.

Shared JSON rules: UTF-8 objects, Content-Type application/json for PATCH, at most 8 KiB for review JSON (upload has the explicit multipart exception below), strict types, unknown/duplicate keys rejected, no GET body. UUID strings must be valid UUIDs. JSON body integers are strict, not booleans or quoted numbers. URL integer parameters use decimal digits parsed as integers, with the bounds below; reject fractional/exponential values and duplicate query keys. Dates use YYYY-MM-DD; timestamps UTC RFC3339 ending Z. Return explicit NULL values. All private responses/errors are no-store; do not log bodies or token/header material. Ordinary Auth registration/login/profile JSON and international-phone/password rules are unchanged.

## 4. B - Exact read requests and responses

### 4.1 Queue

GET `/api/v1/admin/role-requests` accepts only:

| Query | Type/default | Validation |
|---|---|---|
| `page` | Integer, 1 | At least 1. |
| `page_size` | Integer, 20 | 1-100. |
| `status` | String, PENDING | PENDING, APPROVED, REJECTED, SUSPENDED or ALL. ALL is a filter sentinel, never stored. |
| `role_code` | Optional string, omitted | OWNER or DRIVER; omission means both. |
| `q` | Optional string, omitted | Trim; at most 100 Unicode characters; no control characters. Empty means no search. Literal case-insensitive substring on full_name/public_user_reference only; escape SQL wildcard characters and parameterize. |

Only OWNER/DRIVER rows are eligible; exclude rows with user_id equal to the current reviewer before search, count and pagination. Sort `requested_at ASC, id ASC`. `total` counts authorized matching rows; `has_next = page * page_size < total`. A page past the last returns empty items with the actual total; no fabricated records. Concurrent later requests may see a changed live queue; pagination is not a historical snapshot.

200 uses exactly the five keys in 03A's existing pagination shape. Empty-result example: `{"items":[],"page":1,"page_size":20,"total":0,"has_next":false}`. Non-empty items have the ApplicationSummary shape below.

`ApplicationSummary` exact fields: `id` UUID, `role_code` OWNER|DRIVER, `approval_status` PENDING|APPROVED|REJECTED|SUSPENDED, `requested_at` timestamp, `version` integer >=1, and `applicant` object containing only `id` UUID, `public_user_reference` string and `full_name` string. It contains no documents, file links, contacts or reason text. Response objects are DTO views, not new persistence fields.

Example of the accepted queue contract: `GET /api/v1/admin/role-requests?page=1&page_size=20&status=PENDING&role_code=OWNER` with `Authorization: Bearer <access_token>` and `Accept: application/json`. No request JSON is sent. All requests recheck the current session/account/Admin membership; the access JWT alone is insufficient.

### 4.2 Detail

GET `/api/v1/admin/role-requests/{role_id}` has no query/body. 200 has exactly `application`, `applicant`, `documents`:

- `application`: existing RoleResponse fields `id`, `role_code`, `approval_status`, `requested_at`, `approved_at`, `rejection_reason`, `suspended_at`, `suspension_reason`, `version`, plus Admin-only existing fields `approved_by`, `updated_by`, `updated_at`. Actor IDs are UUID or NULL. This does not alter the applicant's RoleResponse.
- `applicant`: `id`, `public_user_reference`, `full_name`, `display_name`, `email`, `phone_e164`, `account_status`, `email_verified_at`, `phone_verified_at`, using existing Auth types/nullability. No password/counter/session/role_profile data.
- `documents`: array of DocumentSummary for current in-scope evidence under section 2; superseded rows are available through the protected document reads, not used to satisfy current requirements. If the evidence dependency cannot be evaluated, fail safely rather than return an empty array implying no documents.

Own application detail is 403 REVIEW_FORBIDDEN for an Admin even if it is OWNER/DRIVER. Opening detail never changes role status or request date. A PASSENGER/ADMIN target is not a reviewable application and returns 404 to an authorized reviewer.

### 4.3 Document list, detail and file

GET `/api/v1/documents` accepts only `page`/`page_size` with the bounds above; optional `user_id` UUID or `vehicle_id` UUID (mutually exclusive); optional `document_type` from section 2.2; optional `status` from the document catalogue. An applicant may restrict to their own user/owned vehicle, never widen access. Without an owner filter, authorized owners see their own personal/owned vehicle documents; eligible APPROVED Admins see verification records; their own files remain readable as owners but cannot be self-verified. Sort `submitted_at DESC NULLS LAST, id ASC`. Return the exact five-key pagination shape with DocumentSummary items.

`DocumentSummary` exact fields: `id` UUID, `user_id` UUID|NULL, `vehicle_id` UUID|NULL, `document_type` string, `issuing_country` string|NULL, `issue_date` date|NULL, `expiry_date` date|NULL, `status` string, `submitted_at` timestamp|NULL, `verified_at` timestamp|NULL, `rejection_reason` string|NULL, `superseded_document_id` UUID|NULL, `version` integer >=1. These are existing columns; no file key/number/link in list responses.

GET `/api/v1/documents/{document_id}` has no query/body. 200 is DocumentSummary plus exactly `document_number` string|NULL, `original_file_name` string, `mime_type` string, `file_size_bytes` integer, `verified_by` UUID|NULL, and `secure_file_url` string. The URL is the protected file path above, generated from the ID; no storage key/checksum/provider credential is exposed. Private owners and authorized Admin reviewers may see these fields; nobody receives them publicly.

GET `/api/v1/documents/{document_id}/file` requires `Authorization: Bearer <access_token>` and has no query/body. 200 is the authenticated byte stream (Content-Type from verified mime_type, Content-Length from verified file_size_bytes and safe Content-Disposition: inline with sanitized filename), not JSON; MIME/filename/size must match server-verified storage metadata. No public/signed URL, internal signed retrieval or storage redirect. Authorization is checked afresh for every request; use Cache-Control: no-store, X-Content-Type-Options: nosniff, server-verified Content-Type and a sanitized Content-Disposition. No token-bearing query or alternate signed-download mode. Failure before headers returns the shared error JSON; after headers, section 4.4 requires aborting an incomplete stream. Existing POST `/api/v1/documents` (#10) is now frozen as authenticated multipart ingestion in section 4.5 and 03D section 4. No upload-token issuer, public/signed upload URL or new ingestion endpoint is added.

### 4.4 Read endpoint error applicability

The exact error envelope/cases in section 6 apply to all three accepted new GETs. Queue/detail require Admin before private target lookup: 401 invalid session, 403 restricted/non-Admin, 403 self detail, 404 missing/non-application detail, 422 invalid path/query/body, 429 throttling, 503 dependencies and safe 500. Queue success with no matches is 200 with empty items, not 404. Protected file permits authorized owners as well as Admins: 401 invalid session, 403 restricted account, opaque 404 absent/out-of-scope document, 422 invalid path/query/body, 429, 503 and safe 500. Non-Admin owners never need ADMIN_REQUIRED for their own file.

Read operations never produce decision-only 409 version/transition/evidence errors or PATCH-only 400/413/415 errors. If a byte-stream failure occurs after response headers have been sent, abort the incomplete stream and report safe correlation metadata; do not append JSON to file bytes or claim a complete successful download. Authorize/open/validate storage before beginning the response where possible.

### 4.5 Frozen private multipart upload and local storage

POST /api/v1/documents is authenticated multipart/form-data. Exactly one file part named file; existing owner_type (USER/VEHICLE), owner_id UUID, document_type and optional number/issue_date/expiry_date inputs map to existing columns. Optional issuing_country maps the already planned field. Full request/response/errors are 03C/03D: success 201 DocumentDetail with status SUBMITTED, not role approval. USER owner must be the caller; VEHICLE must be owned/authorized. No reviewer/status/storage-key/URL/upload-token client authority, public Admin impersonation upload or new table.

PDF, JPEG and PNG only: application/pdf, image/jpeg, image/png; allowed .pdf/.jpg/.jpeg/.png. One to 10485760 bytes (10 MiB) per file; combined scalar text fields at most 8192 bytes; complete multipart request at most 10551296 bytes. Size is enforced while streaming. Missing/repeated/unknown/invalid fields or malformed/disallowed/extension-MIME-inconsistent file content are 422; size excess 413, wrong request media type 415. Validate genuine signature and bounded parser/decode success; reject encrypted/malformed PDFs and executable/HTML/SVG/archive uploads. Preserve bytes and calculate server SHA-256; no public external scanning service. A validator/storage dependency that cannot perform required checks fails safely with 503 REVIEW_DEPENDENCY_UNAVAILABLE. Metadata/file values supplied by the browser are never trusted evidence.

Development uses a configured absolute private root outside repository and webroot, for example D:/TravellyData/private-documents. This is an example deployment path, not a directory created by this task. Restricted OS service-account access, no static mount, no public/signed URLs. Production uses the same backend-only interface on durable private storage with encryption/backups/access controls; deployment paths/credentials are environment configuration, never application-table fields.

Generate an opaque random UUID-based storage key on the server, independent of filename/owner/client path. Store sanitized original basename only for display: maximum 255 characters; reject/remove separators, colon, controls, CR/LF, reserved Windows names and unsafe trailing dots/spaces. Resolve within the approved root; prevent traversal, symlink/junction escapes and overwrite of existing reviewed bytes. Existing secure_file_url is stored NULL by this module; responses derive only the protected authenticated backend path.

Private unique staging file -> content/owner/date validation -> flush/atomic same-volume final placement -> transactional SUBMITTED metadata -> success. No metadata success before durable validated bytes. Failed pre-commit upload cleans only its own unreferenced staging/final bytes. Startup/maintenance orphan recovery pauses uploads, excludes active writer-locked files and rechecks DB references. Retain bytes if commit outcome is uncertain; never delete referenced/superseded history. Missing referenced bytes blocks retrieval/approval with safe dependency failure, not an empty evidence result. Journal, uploads and ordinary logs use separate private locations/permissions.

Only the existing authenticated file GET delivers private bytes, with authorization on every request and no storage redirect; owners retain eligible own-file access, every eligible APPROVED Admin can review others, no self-verification. The document metadata/streaming responses remain section 4.3. The 10 MiB multipart boundary is a narrow exception, not an increase to Auth/review JSON limits. Upload rate: 10/session/15 minutes and 30/IP/15 minutes using existing infrastructure, no table.

## 5. B - Exact decision contracts

Both existing PATCH operations accept exactly the three documented 03A/03B body keys:

```json
{"decision":"REJECTED","reason":"The required evidence needs correction.","version":3}
```

`version` is the strict expected current version integer >=1, transported in the JSON body. There is no `expected_version` alias or new persistent version field. `decision` is a strict catalogue string. `reason` is omitted/NULL for approval or starting document review; otherwise it is trimmed plain text of 1-2000 characters. Reject unknown fields, applicant-controlled reviewer/time values and reason text supplied for an action with no approved reason location. There are no approval notes/private reviewer notes.

### 5.1 Role review

PATCH `/api/v1/admin/role-requests/{role_id}/review`:

| Body decision | Required current state | Required reason/evidence | Existing mutation |
|---|---|---|---|
| APPROVED | PENDING | reason NULL/omitted; all accepted mandatory evidence APPROVED/unexpired, correct owner/type, trusted reviewer metadata; reviewer cannot equal applicant; checklist is frozen in section 2.3. | `approval_status`, `approved_at`, `approved_by`, `updated_at`, `updated_by`, `version + 1`. |
| REJECTED | PENDING | Applicant-visible reason required. | `approval_status`, `rejection_reason`, `updated_at`, `updated_by`, `version + 1`. |
| SUSPENDED | APPROVED | Applicant-visible reason required; authorized Admin identity. | `approval_status`, `suspended_at`, `suspension_reason`, `updated_at`, `updated_by`, `version + 1`; retain approval actor/time. |

No other transition, no Passenger/Admin target, no self-review (approve/reject/suspend) or account/contact mutation. 200 is the existing applicant RoleResponse exact allowlist, as frozen by Auth; no applicant/reviewer/private-document expansion. The Admin UI reloads detail for its authorized evidence. Current-state actor/time/reason mapping is not immutable history; every decision requires confirmed durable history under the approved infrastructure mapping in section 7 before commit; unavailable/unconfirmed audit fails safely.

### 5.2 Document review

PATCH `/api/v1/admin/documents/{document_id}/review` accepts `decision` UNDER_REVIEW from SUBMITTED; or APPROVED, REJECTED, NEEDS_CORRECTION from UNDER_REVIEW. The UNDER_REVIEW command is an explicit documentation refinement implementing 02A's documented review-start transition, not a role status. REJECTED/NEEDS_CORRECTION require reason; other decisions require reason NULL/omitted. Record fields per section 2.4; preserve reviewed file identity and prior evidence. 200 is DocumentSummary plus `verified_by` UUID|NULL; no file URL or storage key. No EXPIRED/SUPERSEDED status editor is added to this endpoint. An Admin cannot review their own evidence. NEEDS_CORRECTION leaves related roles PENDING; a separate role rejection is required.

### 5.3 Concurrency and confirmation

The frontend confirms applicant/document, role/action, expected version and applicant-visible reason before PATCH; confirmation is not permission. The server rechecks session/Admin authorization and current account/target eligibility, locks the target and relevant evidence, compares `version`, verifies the permitted current-state transition and evidence, and updates atomically. A different version or invalid transition is 409, never last-write-wins. A repeated committed PATCH with the old version is 409 and must not produce a second decision.

Approval locks/rechecks the evidence rows and any relevant ownership link so a concurrent document expiry/supersession or ownership change cannot authorize a stale approval. Before COMMIT, lost authorization, unavailable evidence/required audit acknowledgement or confirmed transaction failure rolls back with no committed decision. Uncertain COMMIT outcomes follow section 7 recovery; never claim an already committed decision rolled back. Return the new version only after commit. Preserve Passenger and the other independent role; new approved workspace visibility occurs only after authoritative own-profile/role refresh, never automatic navigation.

## 6. B - Exact error behaviour and operational bounds

All JSON errors retain the Auth envelope with exactly `code`, `message`, `field_errors` (array) and UUID `trace_id`, also X-Request-ID. No stack traces, SQL/storage messages, password/token values, private URLs, cross-user identity or reason text in errors/logs. Each field_errors item has exactly field (dot-separated body/query path), code and message strings as in Auth; non-field errors use []. Token-related 401 includes WWW-Authenticate: Bearer. Authorize before querying private resource existence, evidence, counts or search results.

| HTTP / code | Exact case |
|---|---|
| 400 MALFORMED_REQUEST | PATCH malformed JSON/duplicate keys. |
| 401 UNAUTHENTICATED / SESSION_REVOKED | Invalid/missing/expired access credentials or revoked/missing session under Auth. |
| 403 ACCOUNT_RESTRICTED | Current account disallowed under Auth. |
| 403 ADMIN_REQUIRED | Valid eligible non-Admin calls queue/detail/decision APIs. No target existence is disclosed. |
| 403 REVIEW_FORBIDDEN | Admin requests own application detail or attempts any self role/document review. No extra reviewer-permission flag is required. |
| 404 APPLICATION_NOT_FOUND | Authorized Admin's role ID absent or not OWNER/DRIVER. |
| 404 DOCUMENT_NOT_FOUND | Document absent or outside caller's authorized ownership/verification scope; same safe response. |
| 409 VERSION_CONFLICT | Body version differs from current target version; no mutation. |
| 409 INVALID_REVIEW_TRANSITION | Valid decision value disallowed from current target state. |
| 409 REQUIRED_EVIDENCE_NOT_VERIFIED | Role approval's accepted checklist is unsatisfied or evidence expired/superseded/ineligible; no bypass. |
| 422 VALIDATION_ERROR | Invalid UUID, enum, query/body field/type/range, reason, unsupported query/extra key, GET body or invalid owner-filter combination. |
| 413 REQUEST_TOO_LARGE / 415 UNSUPPORTED_MEDIA_TYPE | PATCH exceeds 8 KiB or is not application/json. |
| 429 RATE_LIMITED | Route/session/IP limit reached; integer Retry-After required. |
| 503 REVIEW_DEPENDENCY_UNAVAILABLE | Required dependency unavailable before COMMIT: no decision commit. Uncertain COMMIT follows section 7 reconciliation/unknown-outcome rules; no false no-change response. |
| 500 INTERNAL_ERROR | Unexpected failure; safe message/trace only. |

The enum/error names and read DTOs above are explicit documentation refinements frozen here, not claims they already appear in 03B or application code. UI implementation remains required; API-matrix/OpenAPI documentation is now synchronized. Unknown decision strings are 422; known but disallowed transitions are 409. Resource-owner document reads do not require approved operational membership.

Use existing infrastructure counters, no table: queue/detail/document-metadata reads share 120/session/minute and 300/IP/minute; protected files 30/session/minute and 100/IP/minute; review PATCH commands 30/session/minute and 100/IP/minute. Apply the strictest applicable limit and fail closed if counters cannot be checked. File limits do not authorize file-size/upload policy; those remain the document-module contract. Do not cache private API results publicly.

## 7. C - Frozen append-only durable audit and normal-commit recovery

TR-D04-D06 freezes a restricted append-only journal outside application tables. It is separate from ordinary logs, private documents and Redis session/rate keys. No new application audit/outbox/history table or JSON history column. No PostgreSQL PREPARE TRANSACTION, COMMIT PREPARED, two-phase commit, prepared-transaction coordinator or max_prepared_transactions change is used by this NBP. PostgreSQL fsync and synchronous_commit must be on for review transactions; normal single-database transactions are used.

### 7.1 Exact journal record and access mapping

Canonical UTF-8 record frames contain the following infrastructure fields (not SQL columns):

| Field | Frozen type / content |
|---|---|
| correlation_id | Server UUID, stable across intent/terminal records for one transaction attempt. |
| sequence | Positive monotonically increasing journal integer under exclusive writer lock. |
| actor | Authenticated user UUID for review/resubmission; controlled operator principal for offline bootstrap, with existing user actor where available. Never client-supplied. |
| timestamp | Server UTC RFC3339 Z time of this journal record. |
| target | Existing resource type, UUID and applicant/role identity; no new application entity. |
| previous_status / new_status | Exact domain catalogue values; NULL prior status only for controlled creation. |
| full_reason | Complete applicant-visible reason, never truncated/hashed as replacement. NULL where approval/start-review accepts no reason. Resubmission additionally preserves the full existing prior reason and decision evidence before clearing. |
| previous_version / new_version | Existing row versions as integers; one successful mutation increments once. |
| previous_decision_evidence | Allowlisted existing actor/time/reason fields necessary to preserve the current decision before reset; no credential/file content. |
| postgres_xid8 | Full PostgreSQL transaction identifier, serialized decimal string from pg_current_xact_id(), including epoch; not a truncated 32-bit xid. |
| outcome | intent, committed or aborted. These are infrastructure outcomes, not new role/document statuses. |
| trace_id / database_identity | Server request UUID and configured database/cluster identity so recovery cannot query an unrelated restored/recreated database. No connection secrets. |
| framing/integrity | Frame length/checksum, prior-record digest and authentication tag using a restricted infrastructure key; detect torn records, reordering and modification. These are journal metadata only. |

Each terminal record refers to the immutable intent/correlation and its transaction evidence. Duplicate terminal finalization is idempotent; contradictory terminal outcomes fail closed. Retain full reasons and original record frames across resubmission. Do not put passwords, tokens, raw bytes, public/private file URLs or unrelated contact data in this channel. Ordinary application/security logs remain metadata-only.

Journal root is configured outside repository/webroot, e.g. D:/TravellyData/review-audit, separate from document storage. Pre-provision restricted durable storage/segments and OS ACLs; append using a dedicated writer identity with no application read/delete/overwrite authority over finalized history. Scoped recovery/audit services have controlled read access. A single infrastructure coordination lock serializes review/document-decision/rejected-resubmission attempts across workers; acquire it before DB row locks. Do not rely on process-local locks or best-effort logging. Production requires durable storage, protected backup/restore continuity and restricted integrity-key configuration; local development must exercise the same acknowledgement/recovery semantics, not an in-memory mock.

### 7.2 Exact pre-commit acknowledgement and mutation sequence

1. Obtain the cross-worker coordination lock; reconcile prior unresolved intents before accepting a new status mutation. Authenticate and recheck eligible account/APPROVED Admin or own resubmission authority. Lock caller/role, target and relevant evidence/ownership rows in deterministic order. Reject self-review, stale version, invalid transitions or missing evidence before status mutation.
2. Stage the existing SQL column changes and version increment inside the uncommitted transaction. Capture before/after state and full current/prior reason evidence. Read pg_current_xact_id() as xid8. Nothing is committed or visible as a successful decision yet.
3. Append the complete intent frame under the journal writer lock, flush to the OS and perform a durable filesystem flush (fsync/Windows FlushFileBuffers-equivalent) before acknowledging. Acknowledgement means the full validated frame is on the configured durable medium, not buffered, queued or merely logged. New segment/metadata durability and protected backups must be validated for the deployment.
4. If acknowledgement fails or is uncertain, never issue COMMIT. Roll back, retain old status/version/reason, and return safe 503 REVIEW_DEPENDENCY_UNAVAILABLE for review/history dependency failure. Do not clear history and log afterwards. A durable orphan intent, if any, is later classified using the SQL transaction outcome.
5. Only after confirmed intent acknowledgement issue ordinary PostgreSQL COMMIT with synchronous_commit on. Append/flush the matching committed terminal frame once commit is confirmed. Send the authoritative 200 and new version only after database commit and terminal audit durability are known. Confirmed rollback records aborted and does not change role/document state.
6. If the connection drops while COMMIT may have reached PostgreSQL, do not issue a second decision, assert rollback or return a 503 claiming no change. Resolve through section 7.3. If the outcome cannot be established within the request, return safe 500 INTERNAL_ERROR with message "The decision outcome could not be confirmed. Refresh before retrying." It makes no success/rollback/no-change assertion; UI reloads authorized current detail. A connection that is already lost naturally has no usable response. Existing-version retry after a committed change is 409 VERSION_CONFLICT, not another mutation.

Full audit confirmation before normal COMMIT satisfies AR-D08 without pretending two independent stores are atomically committed. Terminal-write failure after a database commit is a recovery condition: the already durable intent retains the full reason/status evidence, and further status mutations remain blocked until reconciliation finishes. It must never be reported as a rolled-back decision.

### 7.3 Crash recovery, uncertain outcome and integrity failure

On startup and before each new status mutation, acquire the coordinator lock and inspect unmatched valid intents. Query PostgreSQL pg_xact_status(postgres_xid8) against the recorded database/cluster identity:

| PostgreSQL result | Required recovery |
|---|---|
| committed | Append/flush committed outcome exactly once; never reapply SQL mutation. Current row may have later versions only if an already recorded ordered event explains them. |
| aborted | Append/flush aborted outcome; preserve all original frames. No successful status change is claimed. |
| in progress | Wait/retry boundedly and expose safe dependency unavailability for new decisions; do not assume abort or kill a legitimate transaction automatically. |
| NULL, database unavailable or identity/restore continuity mismatch | Outcome is unproven. Keep intent and full evidence; block new status mutations and require restricted operator recovery using database/WAL/backups. Never infer commit solely from similar current status/version or mark aborted from timeout. |

PostgreSQL only retains recent transaction outcome information; NULL is not proof of abort. Require prompt startup/continuous reconciliation, monitoring for unmatched intents, and no new decision while unresolved. The audit journal is retained history; pg_xact_status is a recovery aid, not historical event storage. Source: [PostgreSQL 16 system information functions](https://www.postgresql.org/docs/16/functions-info.html). track_commit_timestamp is not required and remains unchanged; max_prepared_transactions can remain 0.

A torn/corrupt frame, broken integrity chain, unwritable/full storage or missing acknowledgement fails closed. Preserve suspect bytes/segments; do not silently truncate/rewrite history. Restricted maintenance may archive the damaged segment and establish a verified new segment only after accounting for every intent and continuity record. Restore database and journal coherently; never reuse a stale xid against an unrelated restore. Recovery and reader projections must distinguish intent/committed/aborted; an intent is not a successful decision.

### 7.4 Existing current-state mapping and resubmission

Current role fields remain user_roles.approval_status, requested_at, approved_by/approved_at, rejection_reason, suspended_at/suspension_reason, updated_by/updated_at and version. Document fields remain documents.status, verified_by/verified_at, rejection_reason and common version/actors; replacements use superseded_document_id. There is no new rejected_by/reviewed_at/history column.

REJECTED -> PENDING reuses the same membership, retains creation identity, renews requested_at, clears current approval/rejection/suspension fields only after capturing complete prior decision evidence in the durable intent, sets applicant mutation actor/time and increments once. Run this through the same acknowledgement/normal-commit/recovery protocol before enabling Admin review. The existing implementation's ordinary log followed by clearing reason is insufficient and must be corrected in the next code stage. Authentication dependencies keep existing Auth errors; durable history failure uses safe 503 REVIEW_DEPENDENCY_UNAVAILABLE for this history guard. PENDING/APPROVED/SUSPENDED duplicate remains 409 ROLE_ALREADY_REQUESTED. No suspended self-reinstatement; Passenger and other-role eligibility remain independent.

### 7.5 Secure history retrieval and controlled Admin provisioning

History retrieval uses restricted offline/operator tooling over committed journal projections, filtered by target/correlation and scoped personnel authorization. Read access is itself safely audited. No public/general Admin history UI or new applicant-history API. Existing own-role APIs return complete current applicant-visible reasons; unrelated users never read the journal. Ordinary logs never receive full reasons.

Controlled development provisioning is an explicit offline command for a named existing registered account; no automatic startup grant, default password or public Admin signup. Preserve Passenger. Transactionally insert the existing APPROVED ADMIN membership only if absent; approved_at is server time. The initial controlled bootstrap may use approved_by NULL as already permitted by Auth. Later provisioning records existing authorized actor where available and restricted operator identity in the journal; do not fabricate a user actor. Repeated execution is non-destructive: report existing membership, never silently reinstate a rejected/suspended Admin or alter Owner/Driver state.

Production uses a restricted operator process/job, controlled credentials and explicit target/environment confirmation, with restricted audit evidence and revocation procedure. No browser Admin creation/registration endpoint, user-selected ADMIN role or second login. Provisioning tooling must respect journal durability/recovery and not bypass self-review protection for Owner/Driver applications. This documentation does not provision an account, configure infrastructure, change passwords or grant database superuser privileges.

## 8. Acceptance scenarios and non-goals

These are future acceptance requirements, not executed tests in this documentation task.

| ID | Scenario | Required result |
|---|---|---|
| PR-01 | Applicant reads own personal evidence while role PENDING/REJECTED/SUSPENDED; unrelated user guesses metadata/file ID. | Eligible owner succeeds; other caller gets safe 404; applicant needs no approved Owner/Driver role. Admin queue still requires Admin. |
| PR-02 | Authorized Admin reads in-scope evidence; revoked/non-Admin caller requests the protected file. | Reauthorize every fetch; private bytes only to permitted caller; no public redirect/key/token URL. |
| PR-03 | Driver lacks Sri Lanka-issued verified licence/identity, or Owner lacks the required identity/ownership/authorization evidence. | Approval blocked; no bypass, fabricated evidence or automatic document approval. |
| PR-04 | File is corrected/replaced or two document reviews race. | Retain old file/row and valid same-owner supersession linkage; version conflict cannot overwrite reviewed evidence. |
| PR-05 | Queue status/type/literal search, page bounds, empty query and no matches. | Exact filtering, stable sort, safe pagination; no Passenger/Admin rows or fake counts. Unsupported keys/ranges return 422. |
| PR-06 | Passenger calls queue/detail/PATCH; Admin tries own detail, any self role decision or own document verification. | 403 ADMIN_REQUIRED or REVIEW_FORBIDDEN before private data/decision access; no self-grant. |
| PR-07 | Valid Admin approves PENDING Owner, rejects PENDING Driver or suspends APPROVED role after all prerequisites are met. | Correct existing actor/time/reason/version fields; preserve Passenger/other role/contact state; only matching APPROVED workspace visible after own-profile refresh. |
| PR-08 | Repeat old-version decision, stale reviewer, concurrent evidence expiry/supersession or invalid transition. | 409 or safe dependency failure with no stale commit; new review required. |
| PR-09 | Missing/blank/overlong reject/suspend reason, unknown field or approval note. | 422; no undocumented field or hidden notes persistence. |
| PR-10 | Rejected applicant resubmits after a decision with a reason. | Same membership returns PENDING only after all prior actor/time/status/reason evidence is durably retained. If durable audit confirmation is unavailable/uncertain, no destructive mutation is committed. |
| PR-11 | Suspended applicant resubmits or replaces evidence. | 409 duplicate role; no reinstatement; valid Passenger membership remains. |
| PR-12 | Audit persistence fails around a DB decision/response or a retry occurs. | Never lose a committed decision's history or falsely claim an uncommitted decision succeeded. The deployed adapter must demonstrate the frozen acknowledgement, normal-commit, xid8 reconciliation, rollback/retry and crash-recovery guarantees before enabling decisions; no prepared transactions. |
| PR-13 | Inspect logs, schema, DTOs and original sources. | No extra table/column/JSON history store, private file URL leak or unapproved matrix/source edit; response-only DTO fields are not schema additions. |
| PR-14 | Contact-unverified multi-role applicant logs in after approval. | Passenger remains default; contact reminder accurate; role approval does not verify a contact or bypass booking-contact/account checks. |
| PR-15 | Individual Owner submits NIC/PASSPORT plus their registration evidence, or another registered owner's/company authorization. | Correct alternative accepted; no Owner driving-licence/company-account requirement, invented vehicle row or implicit vehicle verification. |
| PR-16 | Driver uses a foreign-issued licence, or a foreign Passenger registers with a valid international number. | Foreign-driver licence approval unavailable; Passenger international registration and membership remain supported independently. |
| PR-17 | Document becomes NEEDS_CORRECTION, or Optional vehicle file is absent. | Role remains PENDING unless separately rejected; Optional never blocks submission/verification; no future vehicle operating checklist invented. |
| PR-18 | Different eligible APPROVED Admins review applications; current Admin has an own Owner/Driver role. | All eligible reviewers can act on others; own application excluded from queue/counts and Admin detail denied; own-file reading remains allowed without self-verification. |

Explicit non-goals: application code, schema/migrations/live data edits; full Admin dashboard; public Admin provisioning; new role/document states; owner/driver operational dashboards; verification SMS/OTP; appeals/reinstatement; approval/private reviewer notes; booking/vehicle/payment/tracking modules; IVR, subscriptions, secondary-owner delegation and general promotions/coupons. The frozen private upload/storage implementation is next-stage work. Nothing here adds a twenty-first application table.

## 9. Final mapping, completed documentation gate and runtime checklist

### 9.1 Exact existing table/column mappings used

| Existing table | Columns used by this contract |
|---|---|
| `users` | `id`, `public_user_reference`, `full_name`, `display_name`, `email`, `phone_e164`, `account_status`, `email_verified_at`, `phone_verified_at`. |
| `user_roles` | `id`, `user_id`, `role_code`, `approval_status`, `requested_at`, `approved_at`, `approved_by`, `rejection_reason`, `suspended_at`, `suspension_reason`, `created_at`, `created_by`, `updated_at`, `updated_by`, `version`. No authoritative history in `role_profile`. |
| `documents` (planned) | `id`, `user_id`, `vehicle_id`, `document_type`, `document_number`, `issuing_country`, `issue_date`, `expiry_date`, `storage_key`, `secure_file_url`, `original_file_name`, `mime_type`, `file_size_bytes`, `file_checksum`, `status`, `submitted_at`, `verified_by`, `verified_at`, `rejection_reason`, `superseded_document_id`; common `created_at`, `created_by`, `updated_at`, `updated_by`, `version` under 02A section 2.1. |
| `vehicles` (planned) | `id`, `owner_user_id`, used only for owned-vehicle evidence authorization. No fleet module is implemented here. |
| Infrastructure | Existing Auth sessions/counters and metadata-only ordinary logs; AR-D08 separately approves restricted durable decision-history infrastructure outside application tables with full actor/time/previous/new status/reason. Its exact normal-commit/reconciliation contract is frozen in section 7; runtime implementation remains required. |



### 9.2 Completed technical documentation specifications

| Gate item | Frozen artifact / result |
|---|---|
| T01 Physical dictionary | 02C enumerates all 20 planned tables, including exact users/user_roles baseline and complete vehicles/documents definitions, FKs/checks/indexes/defaults/version/lifecycle. Vehicles precedes documents; no 21st table. |
| T02 Audit approach | Section 7 fixes restricted append-only journal, confirmed intent before normal COMMIT, xid8 outcome reconciliation and fail-closed uncertainty. No PostgreSQL prepared transactions. |
| T03 API consistency | 03C/03D and matrix IDs 9-13/97-99 fix exact reads/reviews/upload/streaming/DTO/errors/version; existing endpoint IDs retained. |
| T04 Private documents | Section 4.5/03D fixes multipart one-file PDF/JPEG/PNG <=10 MiB, private external root, safe opaque keys/content checks, streaming, cleanup and orphan reconciliation. |
| T05 Admin and validation | Section 7.5 fixes controlled existing-account offline/operator provisioning; 05 freezes schema/security/upload/audit/recovery/concurrency/API acceptance requirements. |

### 9.3 Technical Readiness Gate verdict

**Admin Application Review Technical Readiness Gate: APPROVED FOR BUILD.** This is a documentation/build-start verdict for the limited Admin module and necessary private-document/audit/provisioning dependencies. The complete physical dictionary and corresponding scoped API contract now satisfy the Admin documentation part of Readiness Stage B. It does not approve all later Travelly workflows or freeze their business/API policies by implication.

No unresolved specification blocks this bounded implementation. Runtime deployment configuration, private paths/ACLs/backups, adapter code, affected migrations, controlled account provisioning and future acceptance execution are implementation/enablement deliverables in 05, not reasons to keep the documentation gate circularly blocked. Actual review remains disabled until those runtime checks pass. No test result, migration execution, live audit capability or production readiness is claimed by this task.

The full future settlement business catalogue, vehicle operating-document checklist, record-specific approval vocabulary and other later-module APIs remain separately gated; their physical storage definitions do not invent those rules and do not block Admin review. Company onboarding, foreign-driver licence approval, IVR, subscriptions, secondary-owner delegation and general promotions/coupons remain excluded/deferred. Passenger permanence/default, independent four-state role applications, separate contact verification and approved-only switcher remain unchanged.

