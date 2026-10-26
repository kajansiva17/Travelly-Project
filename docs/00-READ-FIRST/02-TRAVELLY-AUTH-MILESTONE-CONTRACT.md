# Travelly Register/Login Milestone Contract

Version: 1.0 | Frozen: 23 October 2026 | Database: PostgreSQL 16

## International-passenger registration amendment - 25 October 2026

Accepted decision: "Travelly operates in Sri Lanka but accepts foreign passengers. Registration must support international mobile numbers. The UI uses a searchable country-code selector, defaulting to Sri Lanka (+94). The backend normalizes and stores all phone numbers in E.164 format. Contact verification remains separate from role approval. Actual SMS delivery/verification provider integration is deferred to the Contact Verification module."

This is a documentation-only amendment. Section 4.1 defines the selector, national-number entry, E.164 request boundary and validation; AUTH-19 through AUTH-28 specify acceptance scenarios. It replaces the earlier assumption that a user must type the country code into the registration phone input. The API still receives the existing `phone_e164` field, not new country/national-number fields. No table, column, endpoint, role state or live schema change is introduced by this documentation task.

The previous global eight-digit minimum conflicts with valid shorter foreign mobile numbers. The target `ck_users_phone` syntax check below is revised to remove that minimum; country-specific numbering validation remains mandatory in the API. Aligning the existing check and validators is future implementation work, not a migration performed here. The 20-table plan, automatic APPROVED Passenger membership, Passenger default workspace, independent Owner/Driver approvals and separate contact verification remain unchanged. The accepted 12-character password minimum also remains unchanged.

## Password-policy amendment - 25 October 2026

The accepted password minimum is now 12 Unicode code points for registration, with the existing 128-code-point maximum. This replaces the former 15-character minimum only, including any older reference wording. Sections 4 and 8 below reflect this decision. Registration length errors remain 422 VALIDATION_ERROR: password field message "Use at least 12 characters." for a short password, and "Use at most 128 characters." for an overlong password; never echo the supplied password. The frontend minimum and hint must match. Argon2id parameters, salt requirements, control-character rejection, spaces, no trimming/normalization/truncation, throttling and session rules are unchanged. Login retains its existing 1-128 compatibility input validation and generic credential failures; it does not enforce registration strength on credential attempts. Original PDF reference documents remain unchanged.

## Implementation amendment - 24 October 2026

The user's implementation instruction now explicitly includes JWT access **and refresh** tokens and authenticated Owner/Driver role applications. For this implementation, it overrides the opaque-refresh-token representation and deferred application-submission boundary below, without changing the two-table schema or any other module gate. Refresh tokens are signed HS256 JWTs with a separate environment secret (`JWT_REFRESH_SECRET`), issuer travelly-api, audience travelly-refresh, token_type refresh, sub/sid/jti/iat/exp and a random UUID jti. They retain the original seven-day absolute session expiry. Only SHA256 digests are stored in the Redis session mechanism; atomic rotation/reuse detection/revocation remain mandatory. Every token placeholder labelled opaque below should be read as a signed refresh JWT; the HTTP JSON field names are unchanged. The 43-character opaque-token length no longer applies; the API accepts at most 2048 characters.

POST /api/v1/users/me/role-requests is included for authenticated OWNER/DRIVER submission (request `{ "role_code": "OWNER" }`, or DRIVER; optional supporting_document_ids must be empty until the document module exists). Success is 201 RoleResponse, with PENDING approval. Duplicate PENDING/APPROVED/SUSPENDED membership is 409 ROLE_ALREADY_REQUESTED; a REJECTED membership may resubmit as PENDING, preserving prior evidence in safe logs. Authentication/account/input/rate errors follow this contract. Document-dependent Admin review and Owner/Driver operational permissions remain gated later work; no public approval or document-verification bypass is introduced. Tests may provision approved/rejected/suspended memberships in their isolated schema to verify authorization.

The database URL is required to use postgresql+psycopg, database travelly_dev, application user travelly_app. Tests use a random schema within this same database and user; never SQLite or a substitute database. Only users/user_roles are application migration targets; alembic_version is migration metadata.

This is the physical schema, API and acceptance-test specification for the first implementation stage. It refines the existing `users` and `user_roles` tables only. Together with `01-TRAVELLY-NBP-FINAL-DECISIONS.md` and the updated Readiness Contract, it satisfies the documentation gate for Register/Login. Implementation and execution of the tests are subsequent work, not claimed here.

## 1. Scope and precedence

Implement exactly these six existing API operations: register, login, refresh, logout, current profile and current role states. Role-application/approval behaviour is frozen below so authentication can enforce it; implementing those management endpoints and document verification belongs to the later gated modules. No additional application table is permitted. Sessions, revocation, throttling and refresh rotation use the infrastructure mechanism in section 7, consistent with 02B page 12.

This contract controls these two physical tables and these six Auth APIs over generic descriptions in 02A/02B/03A/03B. It does not authorize implementation of other modules. Telephony/IVR, subscriptions, secondary-owner delegation and general promotions/coupons are outside the current NBP.

## 2. Physical schema conventions

Use schema `public`, the `citext` extension, UUID identifiers and `TIMESTAMPTZ` in UTC. Use `VARCHAR` plus named CHECK constraints, not database ENUM types. `gen_random_uuid()` is PostgreSQL 16's UUID default. No role catalogue table is added. All unspecified nullable-column defaults below are SQL NULL; all listed NOT NULL constraints are mandatory. Identifiers and timestamps are server-controlled. Application transactions set `updated_at = now()` on each update and increment `version` by one. No trigger, sequence or extra application table is needed for this milestone.

### 2.1 users

These are the exact columns created for this milestone. Optional broader profile/provider fields described in the reference PDFs are deferred until their corresponding contract is frozen; they are not authentication prerequisites and must not be accepted through Auth requests.

| Column | PostgreSQL type | Null? | Default | Meaning |
|---|---|---|---|---|
| id | UUID | No | gen_random_uuid() | Immutable PK |
| public_user_reference | VARCHAR(20) | No | none | `USR-` plus 16 uppercase hexadecimal characters; server-generated, collision retried |
| email | CITEXT | Yes | NULL | Trimmed, lowercase, validated email |
| phone_e164 | VARCHAR(20) | Yes | NULL | Canonical E.164 phone, including foreign passengers; no separate country-code column |
| password_hash | TEXT | No | none | Encoded Argon2id hash including salt and parameters |
| full_name | VARCHAR(150) | No | none | Trimmed Unicode name |
| display_name | VARCHAR(100) | Yes | NULL | Optional presentation name |
| profile_image_url | TEXT | Yes | NULL | Public-safe image URL, no private document URL |
| preferred_language | VARCHAR(2) | No | 'en' | en, ta or si |
| timezone | VARCHAR(64) | No | 'Asia/Colombo' | Fixed milestone display timezone |
| account_status | VARCHAR(24) | No | 'PENDING_VERIFICATION' | Account lifecycle, separate from roles |
| email_verified_at | TIMESTAMPTZ | Yes | NULL | Set only by trusted contact verification |
| phone_verified_at | TIMESTAMPTZ | Yes | NULL | Set only by trusted contact verification |
| last_login_at | TIMESTAMPTZ | Yes | NULL | Last successful password login |
| failed_login_count | INTEGER | No | 0 | Consecutive failures in current 15-minute failure window |
| locked_until | TIMESTAMPTZ | Yes | NULL | Temporary password-login lock expiry |
| created_at | TIMESTAMPTZ | No | now() | Creation time |
| updated_at | TIMESTAMPTZ | No | now() | Last mutation time |
| created_by | UUID | Yes | NULL | Self-reference; NULL for self-registration |
| updated_by | UUID | Yes | NULL | Last authenticated editor, or NULL for system action |
| version | INTEGER | No | 1 | Optimistic version |

Constraints (names are normative):

- `pk_users`: PRIMARY KEY (id).
- `uq_users_public_reference`: UNIQUE (public_user_reference).
- `uq_users_email`: UNIQUE (email), using CITEXT equality; multiple NULLs are permitted.
- `uq_users_phone`: UNIQUE (phone_e164), multiple NULLs permitted.
- `fk_users_created_by`, `fk_users_updated_by`: REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT. Add these after users exists; no extra table.
- `ck_users_reference`: public_user_reference matches `^USR-[0-9A-F]{16}$`.
- `ck_users_contact`: email IS NOT NULL OR phone_e164 IS NOT NULL.
- `ck_users_email`: email IS NULL OR (email::text = lower(btrim(email::text)) AND char_length(email::text) BETWEEN 3 AND 254 AND email::text !~ '[[:space:]]'). Full email syntax validation is performed by the API, not a misleading SQL email regex.
- `ck_users_phone`: phone_e164 IS NULL OR phone_e164 matches `^[+][1-9][0-9]{1,14}$`. This is a syntax/maximum-length check only; the API must also validate the country calling code and country-specific number using maintained numbering metadata. This supersedes the former global eight-digit minimum; no Sri Lanka-only length restriction may be applied to foreign numbers.
- `ck_users_password_hash`: char_length(password_hash) > 0.
- `ck_users_full_name`: full_name = btrim(full_name) AND char_length(full_name) BETWEEN 1 AND 150.
- `ck_users_display_name`: display_name IS NULL OR (display_name = btrim(display_name) AND char_length(display_name) BETWEEN 1 AND 100).
- `ck_users_language`: preferred_language IN ('en','ta','si').
- `ck_users_timezone`: timezone = 'Asia/Colombo' for this milestone.
- `ck_users_account_status`: account_status IN ('PENDING_VERIFICATION','ACTIVE','SUSPENDED','BLOCKED','CLOSED').
- `ck_users_verified_email`: email_verified_at IS NULL OR email IS NOT NULL.
- `ck_users_verified_phone`: phone_verified_at IS NULL OR phone_e164 IS NOT NULL.
- `ck_users_activation`: account_status <> 'ACTIVE' OR email_verified_at IS NOT NULL OR phone_verified_at IS NOT NULL.
- `ck_users_failures`: failed_login_count >= 0.
- `ck_users_version`: version >= 1.
- `ck_users_timestamps`: updated_at >= created_at.

Additional B-tree indexes: `ix_users_account_status` (account_status), `ix_users_created_at` (created_at), `ix_users_created_by` (created_by) WHERE created_by IS NOT NULL, `ix_users_updated_by` (updated_by) WHERE updated_by IS NOT NULL. PK/UNIQUE constraints already provide their indexes; do not create duplicate email/phone/reference indexes. The failure-window start is infrastructure state, not an additional users column.

### 2.2 user_roles

| Column | PostgreSQL type | Null? | Default | Meaning |
|---|---|---|---|---|
| id | UUID | No | gen_random_uuid() | PK |
| user_id | UUID | No | none | Account membership |
| role_code | VARCHAR(9) | No | none | PASSENGER, OWNER, DRIVER, ADMIN |
| approval_status | VARCHAR(9) | No | 'PENDING' | PENDING, APPROVED, REJECTED, SUSPENDED |
| requested_at | TIMESTAMPTZ | No | now() | Membership/application time |
| approved_at | TIMESTAMPTZ | Yes | NULL | Approval evidence |
| approved_by | UUID | Yes | NULL | Reviewer; NULL only for automatic Passenger approval or controlled Admin bootstrap |
| rejection_reason | TEXT | Yes | NULL | Required for REJECTED |
| suspended_at | TIMESTAMPTZ | Yes | NULL | Required for SUSPENDED |
| suspension_reason | TEXT | Yes | NULL | Required for SUSPENDED |
| role_profile | JSONB | No | '{}'::jsonb | Bounded non-authoritative preferences only |
| created_at | TIMESTAMPTZ | No | now() | Creation time |
| updated_at | TIMESTAMPTZ | No | now() | Mutation time |
| created_by | UUID | Yes | NULL | Creator or NULL for automatic membership |
| updated_by | UUID | Yes | NULL | Editor or NULL for system action |
| version | INTEGER | No | 1 | Optimistic version |

Constraints:

- `pk_user_roles`: PRIMARY KEY (id).
- `uq_user_roles_user_role`: UNIQUE (user_id, role_code).
- `fk_user_roles_user`, `fk_user_roles_approved_by`, `fk_user_roles_created_by`, `fk_user_roles_updated_by`: respective UUID columns REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT.
- `ck_user_roles_code`: role_code IN ('PASSENGER','OWNER','DRIVER','ADMIN').
- `ck_user_roles_approval`: approval_status IN ('PENDING','APPROVED','REJECTED','SUSPENDED').
- `ck_user_roles_approved`: approval_status <> 'APPROVED' OR approved_at IS NOT NULL.
- `ck_user_roles_reviewer`: approval_status <> 'APPROVED' OR role_code IN ('PASSENGER','ADMIN') OR approved_by IS NOT NULL. The ADMIN exception is solely for controlled bootstrap, never public self-assignment.
- `ck_user_roles_rejected`: approval_status <> 'REJECTED' OR (rejection_reason IS NOT NULL AND char_length(btrim(rejection_reason)) BETWEEN 1 AND 2000).
- `ck_user_roles_suspended`: approval_status <> 'SUSPENDED' OR (suspended_at IS NOT NULL AND suspension_reason IS NOT NULL AND char_length(btrim(suspension_reason)) BETWEEN 1 AND 2000).
- `ck_user_roles_profile`: jsonb_typeof(role_profile) = 'object'.
- `ck_user_roles_version`: version >= 1.
- `ck_user_roles_timestamps`: updated_at >= created_at AND requested_at >= created_at AND (approved_at IS NULL OR approved_at >= requested_at) AND (suspended_at IS NULL OR suspended_at >= requested_at).

Additional B-tree indexes: `ix_user_roles_role_approval` (role_code, approval_status), `ix_user_roles_approved_by` (approved_by) WHERE approved_by IS NOT NULL, `ix_user_roles_created_by` (created_by) WHERE created_by IS NOT NULL, `ix_user_roles_updated_by` (updated_by) WHERE updated_by IS NOT NULL. The user/role unique index also supports membership lookup by user_id.

Application constraints not expressible as row CHECKs: at least one Passenger membership per registered account; automatic Passenger approval; reviewer is an authorized active Admin; reviewer cannot approve their own Owner/Driver application; matching document ownership/eligibility on review; account/role state changes audited without deleting referenced history. Users and role IDs are immutable; no hard-delete endpoint exists in this milestone.

## 3. Registration, contact verification and role behaviour

Registration inserts users plus exactly one PASSENGER membership in one database transaction. PASSENGER is automatically APPROVED with requested_at = created_at, approved_at equal to the transaction time and approved_by NULL. A failed membership insert rolls back the user insert. Account status remains PENDING_VERIFICATION and both verification timestamps remain NULL. This is deliberate: Passenger membership and contact verification are independent.

PENDING_VERIFICATION accounts may log in, refresh, read their profile/roles and log out. They may not book until a contact is verified. The six Auth operations never mark contacts verified. A trusted later verification workflow sets the corresponding timestamp and changes PENDING_VERIFICATION to ACTIVE in the same transaction; it must not reactivate a SUSPENDED/BLOCKED/CLOSED account. ACTIVE requires at least one verified contact. Contact-verification delivery, password recovery/change and MFA APIs are later work; they are not prerequisites for this limited milestone and remain prerequisites for their applicable production workflows. Phone-only signup never implies verified phone ownership.

Owner and Driver requests use the existing POST /api/v1/users/me/role-requests endpoint after its module gate. Only OWNER or DRIVER may be requested; no second users row is created. First request creates PENDING. A duplicate PENDING/APPROVED/SUSPENDED membership returns 409. A REJECTED membership may be resubmitted as PENDING with a new requested_at, cleared decision fields and incremented version; prior decision evidence remains in authorized application logs. Admin review uses existing PATCH /api/v1/admin/role-requests/{role_id}/review: PENDING -> APPROVED or REJECTED, APPROVED -> SUSPENDED. No reinstatement transition is authorized by this milestone. Reviews require expected version, relevant approved/unexpired documents and authorized Admin identity; decisions affect only the reviewed role. Server timestamps prevail over client timestamps. Admin role assignment is controlled administration/bootstrap, never public registration or role application. Driver suspension blocks Driver actions but leaves valid Passenger membership intact. Self-driving Owners still need independently APPROVED DRIVER status and current documents.

## 4. Shared API conventions and validation

HTTPS JSON under /api/v1. Bodies must be JSON objects, Content-Type application/json, maximum 8 KiB; larger requests use 413 and unsupported content type uses 415. Duplicate JSON keys or malformed JSON use 400. Unknown keys, wrong types and semantic field validation use 422. Do not coerce numbers/booleans into strings. Missing bodies on POST operations use 422. Reject unknown query parameters with 422. GET operations have no request body/query parameters. Valid UUIDs and timestamps are serialized as strings; timestamps use UTC RFC3339 with Z. Null fields below are returned explicitly. No success envelope. POST responses never echo passwords or refresh tokens except in the specified token response. All Auth success/error responses use Cache-Control: no-store; token-bearing responses also use Pragma: no-cache. Never log bodies, Authorization headers or token values.

- full_name: Unicode, btrim outer whitespace, 1-150 characters, reject control characters.
- email: optional or null; if supplied, trim and lowercase; 3-254 characters; syntax-valid address; no whitespace/control characters. No provider-specific dot/plus rewriting. Database CITEXT enforces case-insensitive uniqueness.
- phone_e164: optional or null; the registration UI collects an explicit country selection and national number as defined in section 4.1, then submits the existing field in international form beginning with `+`. The backend independently validates and normalizes it to canonical E.164 with at most 15 digits, excluding `+`. Country-specific metadata determines valid lengths; there is no global eight-digit minimum. A direct API request containing only a local number is still rejected rather than assigned +94 implicitly.
- At least one non-null contact is required. Empty contacts are invalid, not converted to NULL.
- password: 12-128 Unicode code points; no trimming, normalization, composition rules or silent truncation; spaces are allowed. Password confirmation is UI-only and is not an API key. Reject control characters. Login accepts 1-128 characters for compatibility; failed credential verification is 401, not a registration-strength message.
- preferred_language: omitted -> en; otherwise exactly en, ta or si. null is invalid.
- identifier: email or explicit international phone, normalized by the same rules. Shape/length failure -> 422; syntactically valid but unknown identifier -> 401.
- Tokens are server-generated opaque strings/JWTs. Refresh/logout bodies require a nonempty string <= 2048 characters; nonempty but invalid/unknown/revoked refresh credentials -> 401 (logout exception in section 6). Never accept user_id, role_code, verification timestamps, status or hash in these bodies.
- Public registration never links/merges an existing account by matching a contact; duplicate email or phone -> 409 CONTACT_ALREADY_REGISTERED with a generic message, no matched account ID or contact detail.

### 4.1 International mobile-number entry and normalization

**Country selector and national number**

- Registration uses a searchable country/region and calling-code selector, initially Sri Lanka (LK, +94). Search supports country name, ISO region and dial code. Display both country/region name and calling code; shared calling codes such as +1 must retain the selected region for national-format validation. Use maintained numbering metadata/static UI data, not a new database country table.
- The user selects the country code and enters the national number **without duplicating the country code**. Keep the calling code in the selector, not prefilled into the national-number input. The default is visible and editable; do not infer nationality, residency, preferred language or authorization from it. Changing the country revalidates the entered number.
- A national-number field may accept ordinary display separators such as spaces, hyphens and parentheses. Reject letters, extensions, control characters, an embedded `+` or an international exit prefix instead of silently turning another format into a different number. Explain: "Select your country code and enter the national number without the country code." Do not blindly strip a leading sequence merely because it matches the calling code; those digits may legitimately belong to a national number.
- For selected Sri Lanka (+94), `771234567` and local-format `0771234567` both normalize to `+94771234567`. Remove the single Sri Lankan national trunk zero when it is present in an otherwise valid local mobile number. Do not submit `+940771234567`. Do not strip leading zeroes globally: another country's numbering rules may require them.
- An explicit full international number pasted into the national field, or an accidentally repeated calling code that does not constitute a valid national number, must prompt correction instead of prepending the selected code again. The frontend must not rely on a permissive parser silently removing a duplicated calling code. Genuine national digits coincidentally beginning with the same digits as the calling code remain subject to normal country-specific validation, not a blanket prefix rejection.
- A selected country code alone is not a contact. With an empty national number and a valid email, submit `phone_e164: null` (or omit it) and allow email-only registration. Without an email or complete phone, retain the existing contact-required validation. If any phone digits are supplied but incomplete/invalid, show the phone error; do not silently discard them merely because an email is also present.

**API and persistence boundary**

- The frontend combines the selected calling code with the validated national number exactly once, removing only the selected region's applicable national trunk prefix, to construct the existing `phone_e164` request value. The selected UI region is not a new API or database field.
- `POST /api/v1/auth/register` keeps its existing request/response shapes. Backend validation is authoritative: parse explicit international input, reject invalid/unassigned calling codes and invalid national numbers, and serialize `+` followed by canonical digits only. Formatting separators may be normalized; extensions, letters and control characters must not be accepted as another number. A valid shape alone is insufficient.
- A direct API request with `phone_e164: "0771234567"` remains 422 because it supplies no international context. This does not conflict with local-format UI entry: the selector provides context before the UI sends `+94771234567`. The API does not default an absent country code to +94.
- Store only the canonical value in the existing `users.phone_e164`; retain its existing nullable `VARCHAR(20)` type, unique constraint and no-additional-table design. Canonical equivalents must compare equal under `uq_users_phone`, including concurrent registrations. The revised syntax check does not replace application-level validation.
- A number valid under numbering metadata is not proof of ownership, SMS reachability or provider coverage. No SMS, OTP generation/delivery/provider integration, verification callback or new verification API is implemented under this registration amendment. The later Contact Verification module owns those workflows, including foreign-number delivery support.
- Successful Sri Lankan and foreign registrations have the same identity/role behaviour: automatically APPROVED PASSENGER membership, `PENDING_VERIFICATION` account, NULL contact-verification timestamps and no registration tokens. Phone normalization never marks a contact verified or grants Owner/Driver approval. Existing language options and milestone timezone remain unchanged for foreign passengers.

**Validation and error behaviour**

| Case | UI behaviour | Direct API/server behaviour |
|---|---|---|
| Invalid or missing country selection with a supplied national number | Require a supported country/region selection; do not submit an arbitrary/unknown calling code. | Invalid/unassigned international calling code -> 422 `VALIDATION_ERROR`, field `phone_e164`. |
| Incomplete or country-invalid national number, country code only, invalid characters, extension, or international number entered in the national field | Show an actionable phone error and preserve the user's input for correction; no fabricated successful registration. | Invalid international number -> 422 `VALIDATION_ERROR`, field `phone_e164`; no account or membership is created. |
| Sri Lankan `0771234567` with Sri Lanka +94 selected | Normalize the valid national trunk-prefix form once; send `+94771234567`. | Independently validate the explicit international number and store canonical E.164. Local-only API input is 422. |
| Valid foreign national number with its matching selected country | Use that region's numbering rules; never force +94 or Sri Lankan number length. | Validate and store the foreign E.164 value; retain the 15-digit maximum and no arbitrary eight-digit floor. |
| Duplicate canonical phone, including alternate formatting or a race | Display the existing generic contact-conflict message; do not log in, merge accounts or imply ownership. | 409 `CONTACT_ALREADY_REGISTERED`, exact message "A supplied contact is already registered." No matched user/phone details; atomic user/Passenger insert rules remain. |
| Empty national number and valid email | Allow email-only registration; do not submit a bare +94 prefix or an empty phone string. | Existing omitted/NULL phone behaviour applies. An explicitly supplied empty string remains 422. |

These are additions to the existing error envelope, not new HTTP/error catalogues. The UI maps any `phone_e164` field error to the phone-entry group; no new server field named `country_code` or `national_number` is accepted. Invalid registration input uses 422, while malformed JSON, duplicates, throttling and dependency errors retain their existing 400/409/429/503 behaviour.

Numbering references: [ITU-T E.164](https://www.itu.int/rec/T-REC-E.164/) defines the international numbering plan and 15-digit maximum. The [libphonenumber FAQ](https://github.com/google/libphonenumber/blob/master/FAQ.md) explains country-code ambiguity, region-specific leading zeroes and why number validity does not establish ownership/reachability. Use maintained metadata when implementing validation; do not infer delivery verification from a successful parse.

## 5. Exact JSON success contracts

Example UUIDs/times below are illustrative. Field names, types, nullability and status codes are normative. Token placeholders stand for issued credentials and are never literal values. Role arrays are sorted by role_code, then id where needed. Each response is built from an explicit allowlist.

### POST /api/v1/auth/register (public)

Request (email-only, phone-only or both supported; omitted optional contacts become NULL):

```json
{"full_name":"Sample Passenger","email":"passenger@example.com","phone_e164":null,"password":"correct horse travel phrase","preferred_language":"en"}
```

201 response:

```json
{"id":"11111111-1111-4111-8111-111111111111","public_user_reference":"USR-0123456789ABCDEF","full_name":"Sample Passenger","display_name":null,"profile_image_url":null,"email":"passenger@example.com","phone_e164":null,"preferred_language":"en","timezone":"Asia/Colombo","account_status":"PENDING_VERIFICATION","email_verified_at":null,"phone_verified_at":null,"approved_roles":["PASSENGER"],"created_at":"2026-10-23T12:00:00Z","updated_at":"2026-10-23T12:00:00Z","version":1}
```

This exact object is UserResponse. Registration does not issue tokens. Database contact conflicts are caught even under concurrent inserts; reference collisions are retried internally and are not reported as contact conflicts.

### POST /api/v1/auth/login (public)

Request:

```json
{"identifier":"passenger@example.com","password":"correct horse travel phrase"}
```

200 TokenResponse:

```json
{"access_token":"<signed-access-token>","refresh_token":"<opaque-refresh-token>","token_type":"bearer","expires_in":900,"refresh_expires_in":604800}
```

After validating the password, PENDING_VERIFICATION and ACTIVE may receive sessions. Unknown user/wrong password/inactive account all return generic 401 INVALID_CREDENTIALS. Use a dummy hash verification for unknown identifiers. Successful login resets failed_login_count, clears locked_until and its failure-window state, updates last_login_at/updated_at/version and creates a fresh session. Do not return a token before the database transaction and session-store creation succeed. On a session-store failure return 503; any failed issuance's DB login audit is allowed to remain but no usable session/token is returned.

### POST /api/v1/auth/refresh (refresh credential)

Request:

```json
{"refresh_token":"<current-opaque-refresh-token>"}
```

200: same TokenResponse fields. Both access and refresh credentials are replaced. expires_in is at most 900; refresh_expires_in is the remaining session lifetime, at most 604800. Refresh does not extend absolute session expiry. No access Authorization header is required; the refresh credential authenticates this operation. Unknown, expired, reused or revoked refresh -> 401 INVALID_REFRESH_TOKEN. Valid refresh for an account now SUSPENDED/BLOCKED/CLOSED -> 403 ACCOUNT_RESTRICTED and revoke the session. Role approval is not a prerequisite for refresh.

### POST /api/v1/auth/logout (current session credentials)

Request:

```json
{"refresh_token":"<current-opaque-refresh-token>"}
```

Require Authorization: Bearer <access_token> for the same session/user. A valid, still-active session requires its current refresh token. Session/refresh mismatch or invalid refresh -> 401 INVALID_SESSION. Successful revocation returns 204 with an empty body, revokes the whole current session family and invalidates every access token carrying its sid. A retry with the same signature-valid, unexpired access token for that already-revoked sid plus its previously matched refresh token returns 204 while its hash tombstone remains; normal protected-route authorization still rejects that revoked access token. Missing/invalid/expired access JWT -> 401; this endpoint is not a global logout. Restricted accounts may revoke their own session. Other device sessions remain independent.

### GET /api/v1/users/me (access credential)

Request: no body; Authorization: Bearer <access_token>.

200 response is exactly UserResponse shown for registration, populated with current database values. No password_hash, counters, lock expiry, reviewer evidence, session secrets or private documents are included. approved_roles includes only currently APPROVED memberships; it does not promise document/booking eligibility.

### GET /api/v1/users/me/roles (access credential)

Request: no body; Authorization: Bearer <access_token>.

200 response:

```json
{"items":[{"id":"22222222-2222-4222-8222-222222222222","role_code":"PASSENGER","approval_status":"APPROVED","requested_at":"2026-10-23T12:00:00Z","approved_at":"2026-10-23T12:00:00Z","rejection_reason":null,"suspended_at":null,"suspension_reason":null,"version":1}]}
```

Return every membership belonging to the authenticated user, including pending/rejected/suspended memberships. Exclude reviewer IDs, role_profile and audit actor fields. No pagination parameters; at most four role memberships exist per user.

## 6. Exact error behaviour

Every error response is ErrorResponse:

```json
{"code":"VALIDATION_ERROR","message":"Request validation failed.","field_errors":[{"field":"email","code":"invalid_format","message":"Enter a valid email address."}],"trace_id":"33333333-3333-4333-8333-333333333333"}
```

field_errors is always an array, empty for non-field errors; field is a dot-separated body/query field path. trace_id is a server UUID and is also returned as X-Request-ID. Do not include supplied passwords/tokens, account existence detail in login errors, internal SQL/provider messages or stack traces. Validate rate limit first, JSON/body shape next, then credentials/permissions; do not use validation errors to disclose account existence.

| HTTP / code | When | Applicable routes |
|---|---|---|
| 400 MALFORMED_REQUEST | Malformed JSON, duplicate JSON keys | Four POST Auth routes |
| 401 INVALID_CREDENTIALS | Unknown identifier, wrong password, or restricted account on password login | login |
| 401 INVALID_REFRESH_TOKEN | Unknown, expired, revoked or reused refresh token | refresh |
| 401 UNAUTHENTICATED | Missing, invalid-signature, expired, wrong-issuer/audience/type access JWT | logout, users/me, users/me/roles |
| 401 SESSION_REVOKED | Access JWT's session missing/revoked/expired | users/me, users/me/roles |
| 401 INVALID_SESSION | Active-session logout credentials do not match | logout |
| 403 ACCOUNT_RESTRICTED | Valid session but current account SUSPENDED/BLOCKED/CLOSED | refresh, users/me, users/me/roles; logout remains allowed |
| 409 CONTACT_ALREADY_REGISTERED | Normalized email or phone already exists, including race at UNIQUE constraint | register only |
| 422 VALIDATION_ERROR | Missing/invalid/unknown fields, no contact, invalid identifier shape, unsupported query | All six, as applicable |
| 429 RATE_LIMITED | Defined route/IP/identifier limit or temporary login lock | All six |
| 503 AUTH_DEPENDENCY_UNAVAILABLE | Database/session store unavailable; authorization fails closed | All six |
| 500 INTERNAL_ERROR | Unexpected failure, safe message and trace ID only | All six |

No routine 403 for registration/login, no routine 409 for login/refresh/logout/profile, and no user-role requirement for basic current-profile reads. Missing authentication is 401, not 403. Token-related 401 responses include WWW-Authenticate: Bearer. A PENDING_VERIFICATION account is not ACCOUNT_RESTRICTED for these six operations. Register's duplicate message is exactly "A supplied contact is already registered." Login's generic message is "Invalid credentials or account unavailable." Other messages may describe the stable code without identifying secrets.

Throttles use atomic infrastructure counters: register 10 requests/IP/15 minutes; login 30 requests/IP/15 minutes plus five password failures/normalized identifier/15 minutes; refresh 60/IP/minute and 20/session/minute; logout 60/IP/minute; profile and role reads share 120/session/minute plus 300/IP/minute. First identifier failure starts a fixed 15-minute window. On the fifth failure return 429, set known account locked_until = server time + 15 minutes and block further login until expiry. Unknown identifiers use the same identifier limit/429 without a users row. Once the lock/window expires, reset the counter before the next attempt. Account lock checks and counters must be concurrency-safe; successful login does not remove the IP limit. Every 429 includes Retry-After as integer seconds until the applicable limit/lock expires. Trust forwarded IP only from configured trusted proxies. Fail closed if counters cannot be checked.

## 7. Passwords, tokens, sessions and browser behaviour

Use maintained Argon2id with a unique cryptographic salt (at least 16 bytes), memory 65536 KiB, iterations 3, parallelism 1 and hash length 32 bytes. Store only the library's encoded hash string; never encrypt/reversibly store passwords or implement hashing manually. Verify using the library; rehash on successful login when approved parameters increase. Benchmark at implementation without silently reducing these frozen minimums. No password/hash/token in logs, analytics, profile DTOs or errors.

Access JWT: HS256 with a random environment-held key of at least 32 bytes, one configured issuer `travelly-api` and audience `travelly-web`. Allow only HS256, validate typ/issuer/audience/signature/exp, use at most 30 seconds clock skew. Claims: sub=user UUID, sid=session UUID, jti=new UUID, iat, exp and token_type=access. Header typ=JWT. No private contact/document data or authoritative roles in JWT. Effective access expiry is min(now+900 seconds, session absolute expiry). Refresh tokens cannot be used as Bearer access credentials.

Refresh tokens: 32 cryptographically random bytes, base64url without padding (43 characters), seven-day absolute session lifetime beginning at login. Store SHA-256 token digests only; plaintext is returned once. Refresh never resets the absolute deadline. A session-store record contains sid, user_id, current digest, created_at, absolute_expires_at and revoked_at; keep consumed/revoked token-digest -> sid tombstones until original session expiry for reuse detection and idempotent logout. These are infrastructure keys, not application tables, and not stored in profile JSON.

Select Redis infrastructure with authentication/TLS, AOF persistence (appendfsync always), no eviction for live security keys, expiries and atomic scripts/transactions for token rotation/revocation/counters. Never permit an in-process-only production fallback. In one atomic refresh operation, consume the old digest, retain its tombstone and publish exactly one new digest. Reuse of a consumed digest revokes that session family; concurrent refresh calls yield at most one initial success and any detected reuse invalidates that family's credentials. Browser clients must serialize refresh requests. Session/key loss or restart without restored security state invalidates sessions; it must never revalidate previously issued credentials. Current user account and role states are read from PostgreSQL on each protected request, not cached JWT claims. Logout/restriction and missing/revoked session state deny all subsequent authorization checks; already-authorized in-flight requests are outside this revocation boundary.

Authentication session changes and important account/role decisions use safe infrastructure/application logs containing actor/resource IDs, action, time and trace ID only. No new audit/session table. Active sessions are checked for /me and /roles and future protected endpoints. A role switcher is presentation context, never authority. Required role must be APPROVED, account must be eligible, and ownership/assignment and current documents must separately pass. Account SUSPENDED/BLOCKED/CLOSED denies access regardless of approved roles. Public reads expose only public-safe fields; tracking/documents/management are protected.

Browser contract preserves the source JSON transport: store tokens in memory, attach access token as Authorization Bearer, and refresh using the JSON body above. Do not persist tokens in localStorage/sessionStorage or readable cookies. Reload/closing the page loses the local session credentials and requires login; the infrastructure session expires or is revoked separately. Persistent browser sign-in/cookie transport is outside this milestone and requires a contract revision. Use explicit CORS origins; no wildcard credentialed CORS. Registration success routes to Login. Login then reads /users/me and /users/me/roles. UI defaults to Passenger context, shows pending/suspended role state without protected dashboard access, and displays contact-verification state without claiming booking eligibility.

## 8. Frozen acceptance tests

Use real PostgreSQL 16 with CITEXT and a real isolated Redis instance for integration/concurrency tests. UI end-to-end tests exercise the real API. UUID/time/token values in examples are not seed credentials. Fixtures are isolated: fresh user, existing email/phone, ACTIVE user with verified contact, PENDING_VERIFICATION user, blocked account, approved Passenger with suspended Driver, and approved multi-role user. Privileged fixtures are not public signup paths or production default passwords.

| ID | Given / action | Required result |
|---|---|---|
| AUTH-01 | Register valid email, phone-only, or both in independent cases | 201; normalized contacts; one users row and one APPROVED PASSENGER row; PENDING_VERIFICATION; verification timestamps NULL; no tokens |
| AUTH-02 | Read stored password after registration | Argon2id parameters meet section 7; plaintext absent; equal passwords have distinct salts/hashes |
| AUTH-03 | Same contact with email case/outer whitespace or canonical phone formatting; two simultaneous matching registrations | Exactly one 201 and one 409; no duplicate/orphan user/role; simulated membership insert failure rolls back user |
| AUTH-04 | Missing contact, empty/invalid contact, password boundary 11/12/128/129 (including Unicode code points), unsupported language, extra role/status/verification key | 422 at invalid boundary with the amended password-length field message; valid values succeed; cannot grant OWNER/DRIVER/ADMIN or self-verify |
| AUTH-05 | Malformed JSON, duplicate keys, wrong content type, oversized request | 400, 400, 415, 413 respectively; safe error JSON |
| AUTH-06 | Login after AUTH-01 using matching email or phone | 200 TokenResponse; verify claims/lifetimes; last_login_at set; counter reset; no contact auto-verification |
| AUTH-07 | Valid-shape unknown identifier, incorrect password or blocked-account password login | Same generic 401 code/message; dummy-hash path for unknown; no identifier existence detail |
| AUTH-08 | Five failed logins, including concurrent attempts, for known and unknown identifier | Fifth reaches 429; Retry-After correct; known lock persists 15 minutes; lock expiry restores attempts; IP limits independent |
| AUTH-09 | GET /me and /roles with valid login | Exact allowlisted JSON; own user only; approved_roles versus all role states distinguished; no secret/counter/reviewer leakage |
| AUTH-10 | Missing/expired/wrong-signature/wrong-audience/wrong-issuer JWT, refresh-as-access or revoked sid | 401; no protected data |
| AUTH-11 | PENDING_VERIFICATION versus SUSPENDED/BLOCKED/CLOSED after login; isolate each operation before revocation | Pending can access six-route milestone; first restricted /me,/roles/refresh check with a valid active session -> 403; refresh revokes that session, so later checks use 401; own logout permitted; later booking requires verification |
| AUTH-12 | Approved Passenger, PENDING Owner or SUSPENDED Driver fixture | Only approved roles in /me; all memberships in /roles; Passenger remains; restricted role cannot authorize its protected actions; UI context cannot override |
| AUTH-13 | Refresh once then reuse old token; concurrent same-token refresh | First rotation replaces both tokens; no sliding seven-day lifetime; reuse -> 401 and session-family revocation; no two valid successor refresh credentials |
| AUTH-14 | Logout with matching session credentials then /me and refresh | Empty 204; all that sid's access/refresh credentials rejected; second session unaffected; matching idempotent retry 204; mismatch -> 401 |
| AUTH-15 | Database/Redis unavailable or Redis security state lost | 503 or rejected missing session as specified; never permit authorization through a fallback |
| AUTH-16 | Browser Register -> Login -> Profile -> Logout | Register creates Passenger; Login issues credentials; Profile/roles render own data and unverified state; Logout clears memory and revokes session; protected navigation returns to Login |
| AUTH-17 | Browser reload and concurrent API 401 responses | Memory credentials lost on reload, Login required; client serializes a single refresh; no token persistence or secret logs |
| AUTH-18 | SQL constraints: duplicate memberships, invalid catalogues, ACTIVE without verified contact, invalid FK, rejected/suspended without evidence | Database rejects invalid rows; RESTRICT prevents deleting referenced identity; no extra application table |
| AUTH-19 | Open registration and search/select countries by name, ISO region and calling code, including countries sharing +1. | Sri Lanka (+94) is the visible initial selection; a searchable, keyboard-accessible selector can choose foreign regions without changing account/role defaults or adding a table. |
| AUTH-20 | In independent registrations with fresh contacts, select Sri Lanka +94 and enter `771234567` or `0771234567`. | Both UI forms send/store `+94771234567`; no duplicate +94 or retained Sri Lankan trunk zero. Each isolated success is 201 with APPROVED PASSENGER, PENDING_VERIFICATION and NULL verification timestamps. |
| AUTH-21 | Select United Kingdom +44 and enter valid national mobile `7400123456`, using isolated example data; repeat with maintained valid example fixtures from other countries. | UI sends `+447400123456`; backend validates/stores foreign canonical E.164. No Sri Lanka-only prefix/length gate; identity, language options and Passenger default rules remain unchanged. Fixtures prove normalization only, not live subscriber ownership. |
| AUTH-22 | Supply an unknown country code, select no region with phone digits, or enter an incomplete/country-invalid number. | UI blocks submission with an actionable phone error. Equivalent malformed direct `phone_e164` input is 422 on `phone_e164`; no account/membership is created. |
| AUTH-23 | With +94 selected, paste `+94771234567` or enter an invalid duplicated-code national value; also test a valid country's national number whose digits happen to begin like its calling code. | Full international/duplicated-code input prompts correction, not double-prefix concatenation or silent stripping. Genuine valid national digits are not rejected solely by a prefix coincidence. |
| AUTH-24 | Register canonical equivalents through national/trunk-prefix UI entry, formatted international API entry and two simultaneous matching requests. | All normalize to the same value; only one registration succeeds, duplicates are generic 409; no merged account, extra Passenger membership or leaked contact owner. |
| AUTH-25 | Send direct API local-only `0771234567`; separately use UI Sri Lanka selection with that national number. | Direct API is 422 for missing international context; UI sends `+94771234567` and may succeed. No backend country-code guessing. |
| AUTH-26 | Leave national number blank with a valid email, then test both contacts absent, an explicit empty phone string and partially entered phone digits alongside a valid email. | Email-only registration preserves NULL phone. Both contacts absent, empty API string and supplied invalid/partial phone are validation failures; the selector alone is never a contact. |
| AUTH-27 | Register a valid foreign example whose canonical number has fewer than eight digits; test the 15-digit cap and country-specific validity independently. | Maintained valid short foreign number is accepted by the API and revised existing phone check; invalid numbers and more than 15 digits are rejected. No new table or Sri Lanka-wide fixed length is introduced. |
| AUTH-28 | Complete Sri Lankan and foreign phone registration, inspect profile/roles and attempt to set verification/approval fields from the client. | Phone is E.164, Passenger remains default/APPROVED, account remains PENDING_VERIFICATION, phone_verified_at remains NULL. No SMS/OTP/provider call occurs. Client self-verification/role approval is rejected under existing validation rules. |

## 9. Documentation gate result and remaining module work

Register/Login documentation gate: PASS, version 1.0 frozen 23 October 2026, provided the decisions file, Readiness staged gate and six matrix entries agree with this contract. This is permission readiness, not an implementation/test-pass claim. No migrations/application code are delivered in this stage.

Later module gate remains closed until the complete 20-table physical dictionary and corresponding APIs/acceptance tests are frozen. Outstanding later work includes contact verification/delivery (especially phone-only accounts), recovery/change, privileged MFA, complete Owner/Driver/document management APIs, the Owner settlement catalogue, and Ticket hold/checkout persistence/state transitions. None requires or authorizes a twenty-first application table here.

Actual SMS delivery/verification provider selection, integration and coverage for Sri Lankan and foreign phone numbers are explicitly deferred to the Contact Verification module. The country selector and normalization rules are registration requirements, not permission to implement that provider workflow. International input/UI and existing phone-check alignment remain implementation work after this documentation-only amendment.


## 26 October 2026 auth extension precedence

Final Decisions AU-01 through AU-07 and [03E](../03-API/03E-TRAVELLY-AUTH-EXTENSION.md) supersede the earlier password-composition/no-verification/no-Google restrictions for this accepted extension. New passwords require uppercase/lowercase/digit/symbol and no whitespace, still 12-128 code points; existing-password login is unchanged. New email accounts must verify before session issuance. Old accounts are grandfathered by an explicit persisted migration marker, never by guessing from dates or contact state. Existing registration/login response extensions, delivery status, Google completion/linking and token-purpose rules are governed by 03E. Existing roles and account enum are retained. AU-08/AU-09 below resolve the contact-required and recovery scope.


### Owner clarification accepted 26 October 2026 - AU-08 / AU-09

The owner explicitly selected: **Require email and phone for all new accounts** and **Add verified-email password recovery**. These choices resolve the pending conflicts above and supersede older email-only/phone-only NEW registration and recovery-deferral wording. Existing accounts remain usable regardless of missing contacts; neither login nor migration invents or verifies contacts. Both new registration methods require normalized email, valid international phone, full name and explicit terms acceptance.

Recovery: POST /api/v1/auth/password/forgot accepts email and always returns the same non-enumerating 202 response regardless of existence, verification, throttled recipient or provider outcome. It never claims delivery. Only an eligible account's already verified email receives a single-use 30-minute link. POST /api/v1/auth/password/reset accepts token and new password under AU-02, atomically consumes the token and locks the bound user; it updates the hash, clears password failure state, increments auth_version to revoke all old access/refresh sessions and requires a fresh login. Verified-email ownership can establish a password on the same Google account as well; it never unlinks Google, changes roles or creates a replacement account. Unverified-email/phone-only accounts cannot recover through this channel; the UI states this limitation without revealing account existence. Invalid/used/expired links share a safe response. Provider outages/quota handling never reveals whether an email exists.
