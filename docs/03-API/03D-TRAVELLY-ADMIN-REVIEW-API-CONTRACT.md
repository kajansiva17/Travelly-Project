# Travelly Admin Review and Private Document API Contract

Version: 1.0 | Technical documentation freeze: 25 October 2026

Read with Final Decisions, the Auth contract, the physical dictionary 02C, and Admin Review Prerequisites sections 2-7. The machine-readable companion is [03C OpenAPI](03C-TRAVELLY-ADMIN-REVIEW-OPENAPI.json). This is a frozen contract, not a statement that these endpoints exist in the live backend. It does not replace the six existing Auth APIs or authorize later business modules.

## 1. Endpoint identity and source reconciliation

| Matrix ID | Method | Path | Result |
|---|---|---|---|
| 9 | PATCH | /api/v1/admin/role-requests/{role_id}/review | 200 existing RoleResponse |
| 10 | POST | /api/v1/documents | 201 DocumentDetail after durable validated upload |
| 11 | GET | /api/v1/documents | 200 five-key DocumentPage |
| 12 | GET | /api/v1/documents/{document_id} | 200 DocumentDetail, no signed storage URL |
| 13 | PATCH | /api/v1/admin/documents/{document_id}/review | 200 DocumentSummary plus verified_by |
| 97 | GET | /api/v1/admin/role-requests | 200 five-key ApplicationPage |
| 98 | GET | /api/v1/admin/role-requests/{role_id} | 200 ApplicationDetail |
| 99 | GET | /api/v1/documents/{document_id}/file | 200 private binary stream |

Existing IDs 1-96 are not renumbered. Three accepted GET operations are appended as 97-99. Inactive IVR #78 stays inactive. Matrix #7 retains its existing own-role request shape but references the durable rejected-resubmission guard. No public Admin-creation or history-browsing endpoint is introduced.

## 2. Shared boundary and authorization

Use the existing Authorization: Bearer access JWT, infrastructure session, account check and current database role/ownership checks. Missing/revoked credentials are 401; account restrictions remain 403. Every eligible APPROVED Admin may review other applicants; own Admin detail and self role/document review are forbidden. Exclude self applications before queue search/count/pagination. Separate own document reads remain allowed, including pending/rejected/suspended role holders with an eligible account/session.

No token, reason or private storage credential goes in URLs, analytics or ordinary logs. All private responses/errors use Cache-Control: no-store and X-Request-ID; file responses also use nosniff. Production uses HTTPS. No public/signed URL approach, storage redirects or static private-file mount.

GET has no body. Review PATCH uses a UTF-8 JSON object, at most 8192 bytes, strict types, no unknown/duplicate fields. Malformed JSON is 400; semantic/field/query validation is 422. POST /documents alone uses the explicit multipart exception in section 4; Auth/role requests keep their existing JSON boundary. CORS must permit PATCH and Bearer/Content-Type for configured origins without weakening existing Auth routes.

## 3. Queue, detail, decisions and concurrency

Queue query: page integer >=1 default 1; page_size integer 1-100 default 20; status PENDING/APPROVED/REJECTED/SUSPENDED/ALL default PENDING; optional role_code OWNER/DRIVER; optional q trimmed, no control characters, maximum 100 characters. Search is literal case-insensitive name/public-reference substring only. Reject duplicate/unknown query keys. Sort requested_at ASC, id ASC. Response keys are exactly items, page, page_size, total, has_next. Empty/out-of-range page is honest 200; ALL is not a stored state.

ApplicationSummary contains id, role_code, approval_status, requested_at, version and applicant {id, public_user_reference, full_name}. Detail contains application (existing RoleResponse plus approved_by, updated_by, updated_at), applicant (allowlisted identity/contact/verification fields) and current in-scope DocumentSummary[]. Never add password/counter/session/role_profile data. Unavailable evidence is a dependency failure, not a fake empty list. Own detail is 403; missing/non-application target is 404.

Both review bodies use exactly decision, reason, version. Version is the expected current strict JSON integer >=1, never a new persistent field or expected_version alias. Role actions: PENDING -> APPROVED/REJECTED; APPROVED -> SUSPENDED. Document actions: SUBMITTED -> UNDER_REVIEW; UNDER_REVIEW -> APPROVED/REJECTED/NEEDS_CORRECTION. Require trimmed 1-2000-character applicant-visible reason for reject/suspend/correction; approval/start-review requires omitted/null reason. No approval/private notes field. NEEDS_CORRECTION keeps the related role PENDING; role rejection is separate.

UI confirmation precedes each decision. Backend authorization, target/version, evidence ownership/status/expiry and any relevant ownership links are rechecked under transaction locks in deterministic order. Compare version before changing fields; increment once on success. A stale/repeated old-version command returns 409 VERSION_CONFLICT with no new mutation. Missing required verified evidence is 409 REQUIRED_EVIDENCE_NOT_VERIFIED. A known but forbidden current-state transition is 409 INVALID_REVIEW_TRANSITION; unknown decision strings are 422.

Approve returns the existing RoleResponse allowlist. Refresh own /me and /me/roles to expose only independently APPROVED Owner/Driver workspaces; never auto-navigate or remove Passenger. Account/contact verification remain separate.

## 4. Exact private upload contract

POST /api/v1/documents accepts multipart/form-data with exactly one file part named file. Text fields:

| Field | Required | Validation / existing mapping |
|---|---|---|
| owner_type | Yes | USER or VEHICLE; selects existing ownership FK, not a new column. |
| owner_id | Yes | UUID; USER must be the caller; VEHICLE must be an authorized owned vehicle. No Admin impersonation upload. |
| document_type | Yes | One existing accepted catalogue value from prerequisites section 2.2. |
| number | No | 1-100 trimmed characters if supplied; maps document_number. |
| issuing_country | No | Valid uppercase ISO alpha-2 country if supplied; maps existing column. Sri Lanka Driver approval requires LK. |
| issue_date | No | ISO YYYY-MM-DD if supplied. |
| expiry_date | No | ISO YYYY-MM-DD; cannot precede issue date. Applicability follows document type. |

Omit absent optional fields; do not submit literal null strings. Repeated fields, additional file parts, unsupported fields and client actor/status/storage/checksum values are 422. Reject public URLs and upload-token/provider-upload variants. The issuing_country input refines the existing planned column mapping; it creates no schema field.

Allowed extensions are .pdf, .jpg, .jpeg and .png with actual MIME application/pdf, image/jpeg and image/png. Minimum one byte; maximum file size exactly 10485760 bytes (10 MiB). Maximum combined text-field payload 8192 bytes; maximum complete multipart request 10551296 bytes (10 MiB + 64 KiB). Enforce byte limits while reading, not only through Content-Length. Request media type other than multipart/form-data is 415; size excess is 413; bad format/content is 422 VALIDATION_ERROR with safe field=file detail.

Validate genuine format/signature and parser/decode success, date/owner metadata and actual MIME/extension consistency. Reject malformed/encrypted PDF and executable/HTML/SVG/archive formats. Bound parser resources; preserve submitted bytes and calculate server SHA-256. Infrastructure implementation must provide bounded local content validation; no external public file-scanning upload is authorized. Unavailable required validation/storage is 503 REVIEW_DEPENDENCY_UNAVAILABLE, never a successful submission or approval bypass.

Use a random opaque server-generated key under the configured private root. Never derive a path from original_file_name, owner input or a supplied URL. Keep sanitized basename for display only: maximum 255 characters, no path separators, colon, control characters, CR/LF or unsafe Windows reserved basename/trailing dots/spaces. Storage containment/reparse-point protection is mandatory. Cross-owner file sharing/checksum deduplication is not authorized; duplicate byte content is not a global uniqueness conflict.

Write a uniquely named private temporary file, validate and flush it, move atomically within the private volume to its final opaque key, then commit metadata as SUBMITTED with current actor/time/version. Return 201 DocumentDetail only when bytes and metadata are usable. Failed pre-commit requests remove their own temporary/final unreferenced files; cleanup must not delete a referenced or superseded file. Crash cleanup runs in maintenance mode before uploads, considers only upload staging files not protected by an active writer lock, and checks database references before removing final orphans. If DB outcome is uncertain, retain bytes until reconciliation proves unreferenced. Missing referenced bytes is a safe dependency error requiring repair, not evidence-free approval.

## 5. Protected list, metadata and byte streaming

GET /documents accepts the page bounds above, optional mutually exclusive user_id/vehicle_id, optional document_type and document status. Scope before counting; sort submitted_at DESC NULLS LAST,id ASC. DocumentSummary contains exactly id, user_id, vehicle_id, document_type, issuing_country, issue_date, expiry_date, status, submitted_at, verified_at, rejection_reason, superseded_document_id, version. The owner FKs are XOR.

DocumentDetail adds only document_number, original_file_name, mime_type, file_size_bytes, verified_by and secure_file_url. The latter is the generated authenticated relative route /api/v1/documents/{id}/file, not an object-store URL. Storage key/checksum are not returned.

The file GET requires Bearer authorization on each request; it has no query/body, signed alternative or Range response variant. A 200 response streams original verified bytes with actual Content-Type, verified Content-Length, Cache-Control: no-store, X-Content-Type-Options: nosniff and safe Content-Disposition: inline filename. Do not redirect. Missing/out-of-scope document is opaque 404 DOCUMENT_NOT_FOUND. If failure occurs after headers, terminate the incomplete stream rather than append JSON; before headers return the shared error response.

## 6. Exact errors, rate bounds and audit commit uncertainty

Every JSON error has exactly code, message, field_errors array and UUID trace_id; each field error has field/code/message. Non-field errors use []; no secrets, supplied values, file bytes or full reason in error messages. Token 401 includes WWW-Authenticate: Bearer; 429 includes positive integer Retry-After.

| HTTP | Cases |
|---|---|
| 400 | MALFORMED_REQUEST for malformed/duplicate-key review JSON. |
| 401 | UNAUTHENTICATED or SESSION_REVOKED. |
| 403 | ACCOUNT_RESTRICTED; ADMIN_REQUIRED for Admin APIs; REVIEW_FORBIDDEN for self review/detail. Own document reads do not require ADMIN_REQUIRED. |
| 404 | APPLICATION_NOT_FOUND for absent/non-reviewable role target; DOCUMENT_NOT_FOUND for absent/out-of-scope document or upload ownership target. |
| 409 | VERSION_CONFLICT, INVALID_REVIEW_TRANSITION; role approval also REQUIRED_EVIDENCE_NOT_VERIFIED. Reads/upload do not produce decision-conflict errors. |
| 413 / 415 | REQUEST_TOO_LARGE / UNSUPPORTED_MEDIA_TYPE for the applicable JSON/multipart boundary. |
| 422 | VALIDATION_ERROR for wrong fields/types/bounds/UUIDs/reasons/file content; unknown/duplicate query or multipart fields; GET body. |
| 429 | RATE_LIMITED. |
| 503 | REVIEW_DEPENDENCY_UNAVAILABLE for required review/document/audit dependencies. |
| 500 | INTERNAL_ERROR, safe message/trace only. |

Frozen limits use existing infrastructure, never a new table: metadata reads 120/session/minute and 300/IP/minute; files 30/session/minute and 100/IP/minute; review commands 30/session/minute and 100/IP/minute; uploads 10/session/15 minutes and 30/IP/15 minutes. Apply applicable limits without changing the six Auth limits. Unavailable counters fail closed.

Audit-intent acknowledgement failure before COMMIT must roll back and return safe 503 with no status change. PostgreSQL commit may itself have an uncertain network outcome: do not falsely assert rollback or issue a second decision. The journal xid8 protocol in prerequisites section 7 resolves it. If outcome cannot be established within the request, return safe 500 INTERNAL_ERROR: "The decision outcome could not be confirmed. Refresh before retrying." This does not assert rollback/no change; UI reloads authorized current detail. An already lost connection naturally has no usable response. A known committed command returns its committed success; a replay with old version is 409. A known aborted command can return safe failure. No new HTTP status, application state, retry mutation or prepared transaction is introduced.

## 7. Consistency and implementation boundary

OpenAPI is machine-readable companion authority for these eight operations; prerequisites supplies transaction/privacy details that JSON Schema cannot express. Matrix IDs remain stable. Original PDFs are explicitly superseded through Final Decisions, not rewritten. The accepted technical checklist is [05 Admin Technical Acceptance](../04-MODULE-CONTRACTS/05-ADMIN-REVIEW-TECHNICAL-ACCEPTANCE.md).

This freeze authorizes building the bounded Admin/private-document prerequisites, subject to the checklist. It does not assert that production configuration, migrations, upload/recovery/security tests or an Admin account already exist. All other Travelly modules retain their own API/business gates. No IVR, promotions/coupons, new application table or public Admin registration.
