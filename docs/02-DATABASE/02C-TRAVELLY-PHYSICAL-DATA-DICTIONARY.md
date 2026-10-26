# Travelly NBP Physical Data Dictionary

Version: 1.0 | Physical target frozen: 25 October 2026 | PostgreSQL 16

This documentation defines all 20 already planned application tables. It applies Final Decisions, Readiness, the exact Auth dictionary and the finalized module contracts. It is not a migration and changes no live schema. Vehicles is defined before documents; bookings is defined before scheduled_trip_seats to resolve existing FKs. Original architecture catalogue numbers are unchanged.

## A. Authority, completeness and interpretation

1. Final Decisions remains the authority for listed conflicts. Readiness governs scope/business rules. Auth section 2 remains the exact implemented users/user_roles baseline; its existing columns, constraints and six APIs are preserved.
2. This physical dictionary refines the 02A logical columns and 02B type families. Source-defined optional users provider/profile columns are included as a future target, not accepted Auth input or prerequisites for Admin review. No new application entity, application-history table or session table is added.
3. Every column is enumerated below. NONE means no SQL default; the caller must supply a value for NOT NULL. NULL means nullable with no non-NULL default. Null means unknown/not applicable, never an invented factual zero. SQL CHECK permits UNKNOWN for nullable columns; mandatory conditional fields use explicit IS NOT NULL.
4. UUID identifiers/actors/FKs use UUID, times use TIMESTAMPTZ in UTC, calendar dates use DATE. Application display and date-only expiry use Asia/Colombo. Decimal values are exact NUMERIC, never floating-point money. String lengths are maximum Unicode characters, not new business eligibility rules.
5. Each table explicitly lists id, created_at, updated_at, created_by, updated_by and version, or reproduces the exact Auth dictionary. No universal metadata/deleted_at field is silently added. Existing named JSON columns keep bounded non-authoritative/configuration/snapshot purposes; none is an audit-history store. JSON request/configuration budgets are enforced by their API contracts, not a new application table.
6. FKs default to ON DELETE RESTRICT / ON UPDATE RESTRICT and NOT DEFERRABLE. Only architecture-explicit route_stops.route_id and scheduled_trip_seats.scheduled_trip_id use ON DELETE CASCADE; downstream retained references still prevent destructive deletion. Lifecycle guards remain server-side where a row CHECK cannot inspect another table or current authorization.
7. All status catalogues come from accepted Final Decisions/Readiness or unchanged 02A catalogues. Fields for which the source specifies no closed business catalogue use bounded nonblank text; no catalogue or transition is invented merely to complete DDL. Later non-Admin APIs must freeze those business meanings before writes are enabled. Physical completeness is not approval to implement all later modules.
8. No private document bytes/keys/URLs appear in public data. Documents and durable audit have separate private infrastructure, with no extra application table. IVR, subscriptions, secondary-owner delegation, company-account onboarding and general promotions/coupons remain excluded.

## B. Migration dependency order

Extensions (existing UUID support, CITEXT; PostGIS for the selected optional routes geometry), then: users, user_roles, vehicles, documents, service_types, vehicle_services, routes, route_stops, scheduled_trips, vehicle_seats, bookings, scheduled_trip_seats, booking_travellers, trips, payments, vehicle_records, notifications, social_posts, social_interactions, road_alerts. Existing migration revisions are not rewritten. Admin implementation needs only affected planned tables; do not generate or apply all 20 migrations in this documentation task. No route/profile/provider/finance module is opened by the Admin gate.

## 1. `users`

The existing Auth baseline is reproduced below without changing its column types/defaults/constraints/indexes. The four source-planned optional additions after it are future-target definitions, not new Auth inputs.


Existing Auth baseline; unchanged registration/login input and contact/Passenger separation.

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


### Source-planned optional users target (02A section 4.1)

| Column | PostgreSQL type | NULL | Default | Constraint / lifecycle |
|---|---|---|---|---|
| external_auth_provider | VARCHAR(40) | YES | NULL | Nullable pair with external_auth_subject; not an implemented identity provider. |
| external_auth_subject | VARCHAR(255) | YES | NULL | Opaque provider subject, not a password/token. |
| date_of_birth | DATE | YES | NULL | No age eligibility restriction invented. |
| common_profile | JSONB | NO | '{}'::jsonb | CHECK jsonb_typeof(common_profile)='object'; non-authoritative presentation only. |

Future target constraints: `ck_users_provider_pair`: both external provider/subject NULL or both non-NULL; `uq_users_external_identity`: UNIQUE(external_auth_provider, external_auth_subject); `ck_users_common_profile`: jsonb_typeof(common_profile)='object'. No new indexes beyond that unique index. These planned additions are not needed for Admin Review migrations and must not alter Auth requests/response allowlists. Existing full_name/contact/account/version lifecycle remains Auth section 3. Passenger membership is permanent/default; contacts are independent.

## 2. `user_roles`


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

Application constraints not expressible as row CHECKs: at least one Passenger membership per registered account; automatic Passenger approval; reviewer is an authorized active Admin; reviewer cannot review their own Owner/Driver application (approve/reject/suspend) or verify own evidence; matching document ownership/eligibility on review; account/role state changes audited without deleting referenced history. Users and role IDs are immutable; no hard-delete endpoint exists in this milestone.


Lifecycle: PENDING -> APPROVED/REJECTED, APPROVED -> SUSPENDED; REJECTED -> PENDING only by same-row applicant resubmission after durable history preservation. Passenger is never removed. Exact expected-version PATCH and no-self-review rules are prerequisites sections 3-7. No new role/audit column or schema change is required.

## 3. `vehicles`
Source: 02A section 4.4, pp5-6; Final D06/canonical availability.

| Column | PostgreSQL type | NULL | SQL default | FK / rule |
|---|---|---|---|---|
| id | UUID | NO | gen_random_uuid() | PK |
| created_at | TIMESTAMPTZ | NO | now() | No additional column rule; table checks below. |
| updated_at | TIMESTAMPTZ | NO | now() | No additional column rule; table checks below. |
| created_by | UUID | YES | NULL | REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| updated_by | UUID | YES | NULL | REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| version | INTEGER | NO | 1 | POSITIVE |
| public_vehicle_reference | VARCHAR(20) | NO | NONE | No additional column rule; table checks below. |
| owner_user_id | UUID | NO | NONE | REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| default_driver_user_id | UUID | YES | NULL | REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| registration_number | CITEXT | NO | NONE | No additional column rule; table checks below. |
| vehicle_type_code | VARCHAR(60) | YES | NULL | No additional column rule; table checks below. |
| make | VARCHAR(80) | YES | NULL | No additional column rule; table checks below. |
| model | VARCHAR(80) | YES | NULL | No additional column rule; table checks below. |
| manufacture_year | SMALLINT | YES | NULL | POSITIVE |
| colour | VARCHAR(40) | YES | NULL | No additional column rule; table checks below. |
| power_type | VARCHAR(4) | YES | NULL | CATALOGUE: ICE,MHEV,HEV,PHEV,BEV |
| engine_fuel_type | VARCHAR(6) | YES | NULL | CATALOGUE: PETROL,DIESEL |
| seat_capacity | SMALLINT | YES | NULL | NONNEGATIVE |
| large_luggage_capacity | SMALLINT | YES | NULL | NONNEGATIVE |
| small_luggage_capacity | SMALLINT | YES | NULL | NONNEGATIVE |
| current_odometer_km | NUMERIC(12,1) | YES | NULL | NONNEGATIVE |
| odometer_updated_at | TIMESTAMPTZ | YES | NULL | No additional column rule; table checks below. |
| transmission_type | VARCHAR(40) | YES | NULL | No additional column rule; table checks below. |
| air_conditioned | BOOLEAN | YES | NULL | No additional column rule; table checks below. |
| description | TEXT | YES | NULL | No additional column rule; table checks below. |
| media | JSONB | NO | '[]'::jsonb | JSON_ARRAY |
| verification_status | VARCHAR(9) | NO | 'DRAFT' | CATALOGUE: DRAFT,SUBMITTED,APPROVED,REJECTED,SUSPENDED |
| availability_status | VARCHAR(20) | NO | 'DRAFT' | CATALOGUE: DRAFT,PENDING_VERIFICATION,ACTIVE,BOOKED,ON_TRIP,MAINTENANCE,SUSPENDED,INACTIVE |
| is_published | BOOLEAN | NO | false | No additional column rule; table checks below. |
| approved_by | UUID | YES | NULL | REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| approved_at | TIMESTAMPTZ | YES | NULL | No additional column rule; table checks below. |

Primary key: `pk_vehicles (id)`. IDs and creation provenance are immutable. All FKs are NOT DEFERRABLE, with names `fk_vehicles_<column>`; actions are stated in the column rows.

Named CHECK constraints (SQL expressions; names are exact):

- `ck_vehicles_01`: `char_length(btrim(registration_number::text)) BETWEEN 1 AND 40`.
- `ck_vehicles_02`: `power_type IS DISTINCT FROM 'BEV' OR engine_fuel_type IS NULL`.
- `ck_vehicles_03`: `power_type IS NULL OR power_type='BEV' OR engine_fuel_type IS NOT NULL`.
- `ck_vehicles_04`: `NOT is_published OR verification_status='APPROVED'`.
- `ck_vehicles_05`: `verification_status<>'APPROVED' OR (approved_by IS NOT NULL AND approved_at IS NOT NULL)`.
- `ck_vehicles_06`: `version>=1`.
- `ck_vehicles_07`: `updated_at>=created_at`.
- `ck_vehicles_08`: `public_vehicle_reference=btrim(public_vehicle_reference) AND char_length(public_vehicle_reference)>0`.
- `ck_vehicles_09`: `vehicle_type_code=btrim(vehicle_type_code) AND char_length(vehicle_type_code)>0`.
- `ck_vehicles_10`: `make=btrim(make) AND char_length(make)>0`.
- `ck_vehicles_11`: `model=btrim(model) AND char_length(model)>0`.
- `ck_vehicles_12`: `manufacture_year>0`.
- `ck_vehicles_13`: `colour=btrim(colour) AND char_length(colour)>0`.
- `ck_vehicles_14`: `power_type IN ('ICE','MHEV','HEV','PHEV','BEV')`.
- `ck_vehicles_15`: `engine_fuel_type IN ('PETROL','DIESEL')`.
- `ck_vehicles_16`: `seat_capacity>=0`.
- `ck_vehicles_17`: `large_luggage_capacity>=0`.
- `ck_vehicles_18`: `small_luggage_capacity>=0`.
- `ck_vehicles_19`: `current_odometer_km>=0`.
- `ck_vehicles_20`: `transmission_type=btrim(transmission_type) AND char_length(transmission_type)>0`.
- `ck_vehicles_21`: `jsonb_typeof(media)='array'`.
- `ck_vehicles_22`: `verification_status IN ('DRAFT','SUBMITTED','APPROVED','REJECTED','SUSPENDED')`.
- `ck_vehicles_23`: `availability_status IN ('DRAFT','PENDING_VERIFICATION','ACTIVE','BOOKED','ON_TRIP','MAINTENANCE','SUSPENDED','INACTIVE')`.

UNIQUE constraints:
- `uq_vehicles_01`: UNIQUE (public_vehicle_reference); NULLs retain PostgreSQL distinct semantics.
- `uq_vehicles_02`: UNIQUE (registration_number); NULLs retain PostgreSQL distinct semantics.

Additional indexes (B-tree unless stated; PK/UNIQUE indexes are not duplicated):
- `ix_vehicles_01`: B-tree (owner_user_id) .
- `ix_vehicles_02`: B-tree (verification_status, is_published, availability_status) .
- `ix_vehicles_03`: B-tree (vehicle_type_code) .
- `ix_vehicles_04`: B-tree (availability_status) .
- `ix_vehicles_created_by`: (created_by) WHERE created_by IS NOT NULL.
- `ix_vehicles_updated_by`: (updated_by) WHERE updated_by IS NOT NULL.

Audit/version: increment version exactly once with every committed mutation, set server UTC updated_at/authenticated updated_by, retain created_at/created_by. Common actors do not replace durable decision history. Lifecycle immutability/append-only requirements below restrict otherwise valid SQL updates.

Lifecycle and cross-row guards: DRAFT -> SUBMITTED -> APPROVED/REJECTED; APPROVED -> SUSPENDED. Nullable factual fields represent unknown draft data, never fabricated zero/false. Submission/publication additionally enforces the future Vehicle Management contract. Role approval is separate and does not require a fake vehicle row. Publication requires an independently APPROVED Owner, verified required evidence and operational availability; a SQL CHECK alone cannot prove cross-table eligibility. Public reference is server-generated, unique, immutable and at most 20 characters; no new business reference format is imposed.

## 4. `documents`
Source: 02A section 4.3, p5; AR-D01-D09 and accepted upload policy.

| Column | PostgreSQL type | NULL | SQL default | FK / rule |
|---|---|---|---|---|
| id | UUID | NO | gen_random_uuid() | PK |
| created_at | TIMESTAMPTZ | NO | now() | No additional column rule; table checks below. |
| updated_at | TIMESTAMPTZ | NO | now() | No additional column rule; table checks below. |
| created_by | UUID | YES | NULL | REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| updated_by | UUID | YES | NULL | REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| version | INTEGER | NO | 1 | POSITIVE |
| user_id | UUID | YES | NULL | REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| vehicle_id | UUID | YES | NULL | REFERENCES vehicles(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| document_type | VARCHAR(60) | NO | NONE | CATALOGUE: NIC,PASSPORT,DRIVING_LICENCE,BUSINESS_REGISTRATION,OWNER_AUTHORISATION,BANK_PROOF,VEHICLE_REGISTRATION,REVENUE_LICENCE,INSURANCE,EMISSION,FITNESS,ROUTE_PERMIT |
| document_number | VARCHAR(100) | YES | NULL | No additional column rule; table checks below. |
| issuing_country | CHAR(2) | YES | NULL | No additional column rule; table checks below. |
| issue_date | DATE | YES | NULL | No additional column rule; table checks below. |
| expiry_date | DATE | YES | NULL | No additional column rule; table checks below. |
| storage_key | TEXT | NO | NONE | No additional column rule; table checks below. |
| secure_file_url | TEXT | YES | NULL | No additional column rule; table checks below. |
| original_file_name | VARCHAR(255) | NO | NONE | No additional column rule; table checks below. |
| mime_type | VARCHAR(100) | NO | NONE | No additional column rule; table checks below. |
| file_size_bytes | BIGINT | NO | NONE | No additional column rule; table checks below. |
| file_checksum | CHAR(64) | NO | NONE | No additional column rule; table checks below. |
| status | VARCHAR(20) | NO | 'DRAFT' | CATALOGUE: DRAFT,SUBMITTED,UNDER_REVIEW,APPROVED,REJECTED,NEEDS_CORRECTION,EXPIRED,SUPERSEDED |
| submitted_at | TIMESTAMPTZ | YES | NULL | No additional column rule; table checks below. |
| verified_by | UUID | YES | NULL | REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| verified_at | TIMESTAMPTZ | YES | NULL | No additional column rule; table checks below. |
| rejection_reason | TEXT | YES | NULL | No additional column rule; table checks below. |
| superseded_document_id | UUID | YES | NULL | REFERENCES documents(id) ON DELETE RESTRICT ON UPDATE RESTRICT |

Primary key: `pk_documents (id)`. IDs and creation provenance are immutable. All FKs are NOT DEFERRABLE, with names `fk_documents_<column>`; actions are stated in the column rows.

Named CHECK constraints (SQL expressions; names are exact):

- `ck_documents_01`: `(user_id IS NOT NULL)::int + (vehicle_id IS NOT NULL)::int = 1`.
- `ck_documents_02`: `issuing_country IS NULL OR issuing_country ~ '^[A-Z]{2}$'`.
- `ck_documents_03`: `issue_date IS NULL OR expiry_date IS NULL OR expiry_date>=issue_date`.
- `ck_documents_04`: `secure_file_url IS NULL OR secure_file_url='/api/v1/documents/'||id::text||'/file'`.
- `ck_documents_05`: `char_length(storage_key) BETWEEN 1 AND 200`.
- `ck_documents_06`: `mime_type IN ('application/pdf','image/jpeg','image/png')`.
- `ck_documents_07`: `file_size_bytes BETWEEN 1 AND 10485760`.
- `ck_documents_08`: `file_checksum ~ '^[0-9a-f]{64}$'`.
- `ck_documents_09`: `superseded_document_id IS NULL OR superseded_document_id<>id`.
- `ck_documents_10`: `status NOT IN ('APPROVED','REJECTED','NEEDS_CORRECTION') OR (verified_by IS NOT NULL AND verified_at IS NOT NULL)`.
- `ck_documents_11`: `status NOT IN ('REJECTED','NEEDS_CORRECTION') OR (rejection_reason IS NOT NULL AND char_length(btrim(rejection_reason)) BETWEEN 1 AND 2000)`.
- `ck_documents_12`: `status='DRAFT' OR submitted_at IS NOT NULL`.
- `ck_documents_13`: `version>=1`.
- `ck_documents_14`: `updated_at>=created_at`.
- `ck_documents_15`: `document_type IN ('NIC','PASSPORT','DRIVING_LICENCE','BUSINESS_REGISTRATION','OWNER_AUTHORISATION','BANK_PROOF','VEHICLE_REGISTRATION','REVENUE_LICENCE','INSURANCE','EMISSION','FITNESS','ROUTE_PERMIT')`.
- `ck_documents_16`: `document_number=btrim(document_number) AND char_length(document_number)>0`.
- `ck_documents_17`: `original_file_name=btrim(original_file_name) AND char_length(original_file_name)>0`.
- `ck_documents_18`: `mime_type=btrim(mime_type) AND char_length(mime_type)>0`.
- `ck_documents_19`: `status IN ('DRAFT','SUBMITTED','UNDER_REVIEW','APPROVED','REJECTED','NEEDS_CORRECTION','EXPIRED','SUPERSEDED')`.

UNIQUE constraints:
- `uq_documents_01`: UNIQUE (storage_key); NULLs retain PostgreSQL distinct semantics.

Additional indexes (B-tree unless stated; PK/UNIQUE indexes are not duplicated):
- `ix_documents_01`: B-tree (user_id, document_type, status) .
- `ix_documents_02`: B-tree (vehicle_id, document_type, status) .
- `ix_documents_03`: B-tree (expiry_date, status) .
- `ix_documents_04`: B-tree (superseded_document_id) .
- `ix_documents_created_by`: (created_by) WHERE created_by IS NOT NULL.
- `ix_documents_updated_by`: (updated_by) WHERE updated_by IS NOT NULL.

Audit/version: increment version exactly once with every committed mutation, set server UTC updated_at/authenticated updated_by, retain created_at/created_by. Common actors do not replace durable decision history. Lifecycle immutability/append-only requirements below restrict otherwise valid SQL updates.

Lifecycle and cross-row guards: DRAFT -> SUBMITTED -> UNDER_REVIEW -> APPROVED/REJECTED/NEEDS_CORRECTION; APPROVED -> EXPIRED/SUPERSEDED. A validated upload is explicitly inserted as SUBMITTED after durable private file placement; DRAFT is not an evidence-free approval path. Retain prior rows and bytes; a replacement points to the superseded document, with same-owner/no-cycle checks under lock. Required role evidence must be APPROVED/current/unexpired with trusted reviewer metadata. NEEDS_CORRECTION leaves the application PENDING. Self verification is forbidden. Initial role evidence uses user_id and vehicle_id NULL. secure_file_url is stored NULL by this module; the API derives its authenticated relative path. No public/signed file URL. Do not add a role/application FK, attachment-history table or authoritative JSON dossier.

## 5. `service_types`
Source: 02A section 4.5, p6.

| Column | PostgreSQL type | NULL | SQL default | FK / rule |
|---|---|---|---|---|
| id | UUID | NO | gen_random_uuid() | PK |
| created_at | TIMESTAMPTZ | NO | now() | No additional column rule; table checks below. |
| updated_at | TIMESTAMPTZ | NO | now() | No additional column rule; table checks below. |
| created_by | UUID | YES | NULL | REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| updated_by | UUID | YES | NULL | REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| version | INTEGER | NO | 1 | POSITIVE |
| code | CITEXT | NO | NONE | No additional column rule; table checks below. |
| name | VARCHAR(100) | NO | NONE | No additional column rule; table checks below. |
| description | TEXT | YES | NULL | No additional column rule; table checks below. |
| category | VARCHAR(16) | NO | NONE | CATALOGUE: PRIVATE_HIRE,TICKET_HIRE,RENTAL |
| is_active | BOOLEAN | NO | false | No additional column rule; table checks below. |
| display_order | INTEGER | NO | 0 | NONNEGATIVE |
| default_pricing_basis | VARCHAR(16) | NO | NONE | CATALOGUE: FIXED,DISTANCE,TIME,PER_SEAT,OWNER_QUOTE |
| settings | JSONB | NO | '{}'::jsonb | JSON_OBJECT |

Primary key: `pk_service_types (id)`. IDs and creation provenance are immutable. All FKs are NOT DEFERRABLE, with names `fk_service_types_<column>`; actions are stated in the column rows.

Named CHECK constraints (SQL expressions; names are exact):

- `ck_service_types_01`: `version>=1`.
- `ck_service_types_02`: `updated_at>=created_at`.
- `ck_service_types_03`: `name=btrim(name) AND char_length(name)>0`.
- `ck_service_types_04`: `category IN ('PRIVATE_HIRE','TICKET_HIRE','RENTAL')`.
- `ck_service_types_05`: `display_order>=0`.
- `ck_service_types_06`: `default_pricing_basis IN ('FIXED','DISTANCE','TIME','PER_SEAT','OWNER_QUOTE')`.
- `ck_service_types_07`: `jsonb_typeof(settings)='object'`.

UNIQUE constraints:
- `uq_service_types_01`: UNIQUE (code); NULLs retain PostgreSQL distinct semantics.

Additional indexes (B-tree unless stated; PK/UNIQUE indexes are not duplicated):
- `ix_service_types_01`: B-tree (category, is_active) .
- `ix_service_types_02`: B-tree (display_order) .
- `ix_service_types_created_by`: (created_by) WHERE created_by IS NOT NULL.
- `ix_service_types_updated_by`: (updated_by) WHERE updated_by IS NOT NULL.

Audit/version: increment version exactly once with every committed mutation, set server UTC updated_at/authenticated updated_by, retain created_at/created_by. Common actors do not replace durable decision history. Lifecycle immutability/append-only requirements below restrict otherwise valid SQL updates.

Lifecycle and cross-row guards: Admin-controlled activate/deactivate, not a new status enum. Only bounded existing operational configuration; no general promotions/coupons or configuration engine. Settings changes affect new offers; accepted booking/departure terms remain immutable snapshots. No new service category or required document checklist is inferred.

## 6. `vehicle_services`
Source: 02A section 4.6, pp6-7.

| Column | PostgreSQL type | NULL | SQL default | FK / rule |
|---|---|---|---|---|
| id | UUID | NO | gen_random_uuid() | PK |
| created_at | TIMESTAMPTZ | NO | now() | No additional column rule; table checks below. |
| updated_at | TIMESTAMPTZ | NO | now() | No additional column rule; table checks below. |
| created_by | UUID | YES | NULL | REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| updated_by | UUID | YES | NULL | REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| version | INTEGER | NO | 1 | POSITIVE |
| vehicle_id | UUID | NO | NONE | REFERENCES vehicles(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| service_type_id | UUID | NO | NONE | REFERENCES service_types(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| is_enabled | BOOLEAN | NO | false | No additional column rule; table checks below. |
| pricing_basis | VARCHAR(16) | NO | NONE | CATALOGUE: FIXED,DISTANCE,TIME,PER_SEAT,OWNER_QUOTE |
| base_price | NUMERIC(12,2) | YES | NULL | NONNEGATIVE |
| price_per_km | NUMERIC(12,2) | YES | NULL | NONNEGATIVE |
| price_per_hour | NUMERIC(12,2) | YES | NULL | NONNEGATIVE |
| currency | CHAR(3) | NO | NONE | No additional column rule; table checks below. |
| minimum_hire_hours | NUMERIC(8,2) | YES | NULL | NONNEGATIVE |
| minimum_hire_km | NUMERIC(10,2) | YES | NULL | NONNEGATIVE |
| available_from | DATE | YES | NULL | No additional column rule; table checks below. |
| available_until | DATE | YES | NULL | No additional column rule; table checks below. |
| owner_terms | JSONB | NO | '{}'::jsonb | JSON_OBJECT |

Primary key: `pk_vehicle_services (id)`. IDs and creation provenance are immutable. All FKs are NOT DEFERRABLE, with names `fk_vehicle_services_<column>`; actions are stated in the column rows.

Named CHECK constraints (SQL expressions; names are exact):

- `ck_vehicle_services_01`: `available_from IS NULL OR available_until IS NULL OR available_until>=available_from`.
- `ck_vehicle_services_02`: `version>=1`.
- `ck_vehicle_services_03`: `updated_at>=created_at`.
- `ck_vehicle_services_04`: `pricing_basis IN ('FIXED','DISTANCE','TIME','PER_SEAT','OWNER_QUOTE')`.
- `ck_vehicle_services_05`: `base_price>=0`.
- `ck_vehicle_services_06`: `price_per_km>=0`.
- `ck_vehicle_services_07`: `price_per_hour>=0`.
- `ck_vehicle_services_08`: `currency ~ '^[A-Z]{3}$'`.
- `ck_vehicle_services_09`: `minimum_hire_hours>=0`.
- `ck_vehicle_services_10`: `minimum_hire_km>=0`.
- `ck_vehicle_services_11`: `jsonb_typeof(owner_terms)='object'`.

UNIQUE constraints:
- `uq_vehicle_services_01`: UNIQUE (vehicle_id, service_type_id); NULLs retain PostgreSQL distinct semantics.

Additional indexes (B-tree unless stated; PK/UNIQUE indexes are not duplicated):
- `ix_vehicle_services_01`: B-tree (service_type_id, is_enabled) .
- `ix_vehicle_services_02`: B-tree (vehicle_id) .
- `ix_vehicle_services_created_by`: (created_by) WHERE created_by IS NOT NULL.
- `ix_vehicle_services_updated_by`: (updated_by) WHERE updated_by IS NOT NULL.

Audit/version: increment version exactly once with every committed mutation, set server UTC updated_at/authenticated updated_by, retain created_at/created_by. Common actors do not replace durable decision history. Lifecycle immutability/append-only requirements below restrict otherwise valid SQL updates.

Lifecycle and cross-row guards: Enabled/disabled only; positive/zero prices remain actual supplied terms, not fabricated defaults. Discovery also checks active service, vehicle verification/availability, documents and schedule. Optional price components remain NULL when not applicable. No promotion engine.

## 7. `routes`
Source: 02A section 4.7, p7.

| Column | PostgreSQL type | NULL | SQL default | FK / rule |
|---|---|---|---|---|
| id | UUID | NO | gen_random_uuid() | PK |
| created_at | TIMESTAMPTZ | NO | now() | No additional column rule; table checks below. |
| updated_at | TIMESTAMPTZ | NO | now() | No additional column rule; table checks below. |
| created_by | UUID | YES | NULL | REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| updated_by | UUID | YES | NULL | REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| version | INTEGER | NO | 1 | POSITIVE |
| route_code | CITEXT | NO | NONE | No additional column rule; table checks below. |
| route_name | VARCHAR(150) | NO | NONE | No additional column rule; table checks below. |
| origin_name | VARCHAR(150) | NO | NONE | No additional column rule; table checks below. |
| destination_name | VARCHAR(150) | NO | NONE | No additional column rule; table checks below. |
| origin_latitude | NUMERIC(9,6) | YES | NULL | No additional column rule; table checks below. |
| origin_longitude | NUMERIC(9,6) | YES | NULL | No additional column rule; table checks below. |
| destination_latitude | NUMERIC(9,6) | YES | NULL | No additional column rule; table checks below. |
| destination_longitude | NUMERIC(9,6) | YES | NULL | No additional column rule; table checks below. |
| estimated_distance_km | NUMERIC(12,3) | YES | NULL | NONNEGATIVE |
| estimated_duration_minutes | INTEGER | YES | NULL | NONNEGATIVE |
| status | VARCHAR(8) | NO | 'DRAFT' | CATALOGUE: DRAFT,ACTIVE,INACTIVE |
| created_by_owner_id | UUID | YES | NULL | REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| approved_by | UUID | YES | NULL | REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| approved_at | TIMESTAMPTZ | YES | NULL | No additional column rule; table checks below. |
| route_geometry | geometry(LineString,4326) | YES | NULL | No additional column rule; table checks below. |
| route_settings | JSONB | NO | '{}'::jsonb | JSON_OBJECT |

Primary key: `pk_routes (id)`. IDs and creation provenance are immutable. All FKs are NOT DEFERRABLE, with names `fk_routes_<column>`; actions are stated in the column rows.

Named CHECK constraints (SQL expressions; names are exact):

- `ck_routes_01`: `status<>'ACTIVE' OR (approved_by IS NOT NULL AND approved_at IS NOT NULL)`.
- `ck_routes_02`: `version>=1`.
- `ck_routes_03`: `updated_at>=created_at`.
- `ck_routes_04`: `route_name=btrim(route_name) AND char_length(route_name)>0`.
- `ck_routes_05`: `origin_name=btrim(origin_name) AND char_length(origin_name)>0`.
- `ck_routes_06`: `destination_name=btrim(destination_name) AND char_length(destination_name)>0`.
- `ck_routes_07`: `origin_latitude BETWEEN -90 AND 90`.
- `ck_routes_08`: `origin_longitude BETWEEN -180 AND 180`.
- `ck_routes_09`: `destination_latitude BETWEEN -90 AND 90`.
- `ck_routes_10`: `destination_longitude BETWEEN -180 AND 180`.
- `ck_routes_11`: `estimated_distance_km>=0`.
- `ck_routes_12`: `estimated_duration_minutes>=0`.
- `ck_routes_13`: `status IN ('DRAFT','ACTIVE','INACTIVE')`.
- `ck_routes_14`: `jsonb_typeof(route_settings)='object'`.

UNIQUE constraints:
- `uq_routes_01`: UNIQUE (route_code); NULLs retain PostgreSQL distinct semantics.

Additional indexes (B-tree unless stated; PK/UNIQUE indexes are not duplicated):
- `ix_routes_01`: B-tree (origin_name, destination_name, status) .
- `ix_routes_02`: B-tree (created_by_owner_id) .
- `ix_routes_03`: GiST (route_geometry) .
- `ix_routes_created_by`: (created_by) WHERE created_by IS NOT NULL.
- `ix_routes_updated_by`: (updated_by) WHERE updated_by IS NOT NULL.

Audit/version: increment version exactly once with every committed mutation, set server UTC updated_at/authenticated updated_by, retain created_at/created_by. Common actors do not replace durable decision history. Lifecycle immutability/append-only requirements below restrict otherwise valid SQL updates.

Lifecycle and cross-row guards: DRAFT -> ACTIVE/INACTIVE by authorized management; no new transition catalogue. NULL creator Owner means Admin-owned route. This physical target selects the existing optional PostGIS geometry alternative; it is not a new application table. No route geometry is mandatory for Admin review.

## 8. `route_stops`
Source: 02A section 4.8, p7.

| Column | PostgreSQL type | NULL | SQL default | FK / rule |
|---|---|---|---|---|
| id | UUID | NO | gen_random_uuid() | PK |
| created_at | TIMESTAMPTZ | NO | now() | No additional column rule; table checks below. |
| updated_at | TIMESTAMPTZ | NO | now() | No additional column rule; table checks below. |
| created_by | UUID | YES | NULL | REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| updated_by | UUID | YES | NULL | REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| version | INTEGER | NO | 1 | POSITIVE |
| route_id | UUID | NO | NONE | REFERENCES routes(id) ON DELETE CASCADE ON UPDATE RESTRICT |
| stop_order | SMALLINT | NO | NONE | NONNEGATIVE |
| stop_code | VARCHAR(30) | YES | NULL | No additional column rule; table checks below. |
| stop_name | VARCHAR(150) | NO | NONE | No additional column rule; table checks below. |
| latitude | NUMERIC(9,6) | NO | NONE | No additional column rule; table checks below. |
| longitude | NUMERIC(9,6) | NO | NONE | No additional column rule; table checks below. |
| pickup_allowed | BOOLEAN | NO | true | No additional column rule; table checks below. |
| dropoff_allowed | BOOLEAN | NO | true | No additional column rule; table checks below. |
| scheduled_offset_minutes | INTEGER | NO | 0 | NONNEGATIVE |
| is_active | BOOLEAN | NO | true | No additional column rule; table checks below. |

Primary key: `pk_route_stops (id)`. IDs and creation provenance are immutable. All FKs are NOT DEFERRABLE, with names `fk_route_stops_<column>`; actions are stated in the column rows.

Named CHECK constraints (SQL expressions; names are exact):

- `ck_route_stops_01`: `version>=1`.
- `ck_route_stops_02`: `updated_at>=created_at`.
- `ck_route_stops_03`: `stop_order>=0`.
- `ck_route_stops_04`: `stop_code=btrim(stop_code) AND char_length(stop_code)>0`.
- `ck_route_stops_05`: `stop_name=btrim(stop_name) AND char_length(stop_name)>0`.
- `ck_route_stops_06`: `latitude BETWEEN -90 AND 90`.
- `ck_route_stops_07`: `longitude BETWEEN -180 AND 180`.
- `ck_route_stops_08`: `scheduled_offset_minutes>=0`.

UNIQUE constraints:
- `uq_route_stops_01`: UNIQUE (route_id, stop_order); NULLs retain PostgreSQL distinct semantics.
- `uq_route_stops_02`: UNIQUE (route_id, stop_code); NULLs retain PostgreSQL distinct semantics.

Additional indexes (B-tree unless stated; PK/UNIQUE indexes are not duplicated):
- `ix_route_stops_01`: B-tree (route_id, is_active) .
- `ix_route_stops_created_by`: (created_by) WHERE created_by IS NOT NULL.
- `ix_route_stops_updated_by`: (updated_by) WHERE updated_by IS NOT NULL.

Audit/version: increment version exactly once with every committed mutation, set server UTC updated_at/authenticated updated_by, retain created_at/created_by. Common actors do not replace durable decision history. Lifecycle immutability/append-only requirements below restrict otherwise valid SQL updates.

Lifecycle and cross-row guards: Route-owned ordered rows; first/last represent origin/destination under route transaction validation. Preserve stops referenced by bookings/travellers despite route CASCADE: those foreign keys RESTRICT deletion. No segment seat reuse.

## 9. `scheduled_trips`
Source: 02A section 4.9, pp7-8; project D08.

| Column | PostgreSQL type | NULL | SQL default | FK / rule |
|---|---|---|---|---|
| id | UUID | NO | gen_random_uuid() | PK |
| created_at | TIMESTAMPTZ | NO | now() | No additional column rule; table checks below. |
| updated_at | TIMESTAMPTZ | NO | now() | No additional column rule; table checks below. |
| created_by | UUID | YES | NULL | REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| updated_by | UUID | YES | NULL | REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| version | INTEGER | NO | 1 | POSITIVE |
| departure_reference | VARCHAR(24) | NO | NONE | No additional column rule; table checks below. |
| owner_user_id | UUID | NO | NONE | REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| service_type_id | UUID | NO | NONE | REFERENCES service_types(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| route_id | UUID | NO | NONE | REFERENCES routes(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| original_vehicle_id | UUID | NO | NONE | REFERENCES vehicles(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| current_vehicle_id | UUID | NO | NONE | REFERENCES vehicles(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| operator_driver_user_id | UUID | YES | NULL | REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| departure_at | TIMESTAMPTZ | NO | NONE | No additional column rule; table checks below. |
| estimated_arrival_at | TIMESTAMPTZ | NO | NONE | No additional column rule; table checks below. |
| booking_cutoff_at | TIMESTAMPTZ | NO | NONE | No additional column rule; table checks below. |
| fare_per_seat | NUMERIC(12,2) | NO | NONE | NONNEGATIVE |
| currency | CHAR(3) | NO | NONE | No additional column rule; table checks below. |
| fulfilment_policy | VARCHAR(48) | NO | NONE | CATALOGUE: FIXED_GUARANTEED,MINIMUM_SEATS_WITH_PROTECTED_FULFILMENT |
| minimum_confirmed_seats | SMALLINT | YES | NULL | NONNEGATIVE |
| decision_deadline | TIMESTAMPTZ | YES | NULL | No additional column rule; table checks below. |
| accepted_time_window_minutes | INTEGER | NO | 0 | NONNEGATIVE |
| accepted_replacement_terms | JSONB | NO | '{}'::jsonb | JSON_OBJECT |
| status | VARCHAR(20) | NO | 'DRAFT' | CATALOGUE: DRAFT,PUBLISHED,BOOKING_OPEN,DECISION_REQUIRED,COMMITTED,READY,IN_PROGRESS,COMPLETED,CANCELLED,DISRUPTED |
| replacement_status | VARCHAR(24) | NO | 'NOT_REQUIRED' | CATALOGUE: NOT_REQUIRED,OWNER_ALTERNATIVE,PLATFORM_SHORTLISTED,AWAITING_OTHER_OWNER,APPROVED,REJECTED,FAILED |
| replacement_scheduled_trip_id | UUID | YES | NULL | REFERENCES scheduled_trips(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| final_operating_owner_user_id | UUID | YES | NULL | REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| committed_at | TIMESTAMPTZ | YES | NULL | No additional column rule; table checks below. |
| cancellation_reason | TEXT | YES | NULL | No additional column rule; table checks below. |

Primary key: `pk_scheduled_trips (id)`. IDs and creation provenance are immutable. All FKs are NOT DEFERRABLE, with names `fk_scheduled_trips_<column>`; actions are stated in the column rows.

Named CHECK constraints (SQL expressions; names are exact):

- `ck_scheduled_trips_01`: `estimated_arrival_at>departure_at`.
- `ck_scheduled_trips_02`: `booking_cutoff_at<=departure_at`.
- `ck_scheduled_trips_03`: `decision_deadline IS NULL OR decision_deadline<=departure_at`.
- `ck_scheduled_trips_04`: `fulfilment_policy<>'FIXED_GUARANTEED' OR minimum_confirmed_seats IS NULL`.
- `ck_scheduled_trips_05`: `fulfilment_policy<>'MINIMUM_SEATS_WITH_PROTECTED_FULFILMENT' OR (minimum_confirmed_seats IS NOT NULL AND minimum_confirmed_seats>0 AND decision_deadline IS NOT NULL)`.
- `ck_scheduled_trips_06`: `replacement_scheduled_trip_id IS NULL OR replacement_scheduled_trip_id<>id`.
- `ck_scheduled_trips_07`: `version>=1`.
- `ck_scheduled_trips_08`: `updated_at>=created_at`.
- `ck_scheduled_trips_09`: `departure_reference=btrim(departure_reference) AND char_length(departure_reference)>0`.
- `ck_scheduled_trips_10`: `fare_per_seat>=0`.
- `ck_scheduled_trips_11`: `currency ~ '^[A-Z]{3}$'`.
- `ck_scheduled_trips_12`: `fulfilment_policy IN ('FIXED_GUARANTEED','MINIMUM_SEATS_WITH_PROTECTED_FULFILMENT')`.
- `ck_scheduled_trips_13`: `minimum_confirmed_seats>=0`.
- `ck_scheduled_trips_14`: `accepted_time_window_minutes>=0`.
- `ck_scheduled_trips_15`: `jsonb_typeof(accepted_replacement_terms)='object'`.
- `ck_scheduled_trips_16`: `status IN ('DRAFT','PUBLISHED','BOOKING_OPEN','DECISION_REQUIRED','COMMITTED','READY','IN_PROGRESS','COMPLETED','CANCELLED','DISRUPTED')`.
- `ck_scheduled_trips_17`: `replacement_status IN ('NOT_REQUIRED','OWNER_ALTERNATIVE','PLATFORM_SHORTLISTED','AWAITING_OTHER_OWNER','APPROVED','REJECTED','FAILED')`.

UNIQUE constraints:
- `uq_scheduled_trips_01`: UNIQUE (departure_reference); NULLs retain PostgreSQL distinct semantics.

Additional indexes (B-tree unless stated; PK/UNIQUE indexes are not duplicated):
- `ix_scheduled_trips_01`: B-tree (route_id, departure_at, status) .
- `ix_scheduled_trips_02`: B-tree (current_vehicle_id, departure_at) .
- `ix_scheduled_trips_03`: B-tree (owner_user_id, status) .
- `ix_scheduled_trips_04`: B-tree (decision_deadline, status) .
- `ix_scheduled_trips_created_by`: (created_by) WHERE created_by IS NOT NULL.
- `ix_scheduled_trips_updated_by`: (updated_by) WHERE updated_by IS NOT NULL.

Audit/version: increment version exactly once with every committed mutation, set server UTC updated_at/authenticated updated_by, retain created_at/created_by. Common actors do not replace durable decision history. Lifecycle immutability/append-only requirements below restrict otherwise valid SQL updates.

Lifecycle and cross-row guards: DRAFT -> PUBLISHED -> BOOKING_OPEN -> DECISION_REQUIRED/COMMITTED -> READY -> IN_PROGRESS -> COMPLETED; authorized disruption/cancellation only under protected fulfilment policy. Missed deadline escalates to Admin; it does not automatically commit/cancel/refund. Original/current/final links and accepted protection snapshots preserve the promise. Equivalent verified replacement and material-change Passenger acceptance remain mandatory; refund for non-fulfilment only if Travelly cannot fulfil.

## 10. `vehicle_seats`
Source: 02A section 4.10, p8.

| Column | PostgreSQL type | NULL | SQL default | FK / rule |
|---|---|---|---|---|
| id | UUID | NO | gen_random_uuid() | PK |
| created_at | TIMESTAMPTZ | NO | now() | No additional column rule; table checks below. |
| updated_at | TIMESTAMPTZ | NO | now() | No additional column rule; table checks below. |
| created_by | UUID | YES | NULL | REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| updated_by | UUID | YES | NULL | REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| version | INTEGER | NO | 1 | POSITIVE |
| vehicle_id | UUID | NO | NONE | REFERENCES vehicles(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| layout_version | INTEGER | NO | 1 | POSITIVE |
| seat_code | VARCHAR(12) | NO | NONE | No additional column rule; table checks below. |
| row_number | SMALLINT | NO | NONE | NONNEGATIVE |
| column_number | SMALLINT | NO | NONE | NONNEGATIVE |
| deck_number | SMALLINT | NO | 1 | POSITIVE |
| seat_type | VARCHAR(12) | NO | 'STANDARD' | CATALOGUE: STANDARD,WINDOW,AISLE,PREMIUM,ACCESSIBLE,CREW |
| is_active | BOOLEAN | NO | true | No additional column rule; table checks below. |
| is_bookable | BOOLEAN | NO | true | No additional column rule; table checks below. |
| display_metadata | JSONB | NO | '{}'::jsonb | JSON_OBJECT |

Primary key: `pk_vehicle_seats (id)`. IDs and creation provenance are immutable. All FKs are NOT DEFERRABLE, with names `fk_vehicle_seats_<column>`; actions are stated in the column rows.

Named CHECK constraints (SQL expressions; names are exact):

- `ck_vehicle_seats_01`: `version>=1`.
- `ck_vehicle_seats_02`: `updated_at>=created_at`.
- `ck_vehicle_seats_03`: `layout_version>0`.
- `ck_vehicle_seats_04`: `seat_code=btrim(seat_code) AND char_length(seat_code)>0`.
- `ck_vehicle_seats_05`: `row_number>=0`.
- `ck_vehicle_seats_06`: `column_number>=0`.
- `ck_vehicle_seats_07`: `deck_number>0`.
- `ck_vehicle_seats_08`: `seat_type IN ('STANDARD','WINDOW','AISLE','PREMIUM','ACCESSIBLE','CREW')`.
- `ck_vehicle_seats_09`: `jsonb_typeof(display_metadata)='object'`.

UNIQUE constraints:
- `uq_vehicle_seats_01`: UNIQUE (vehicle_id, layout_version, seat_code); NULLs retain PostgreSQL distinct semantics.
- `uq_vehicle_seats_02`: UNIQUE (vehicle_id, layout_version, deck_number, row_number, column_number); NULLs retain PostgreSQL distinct semantics.

Additional indexes (B-tree unless stated; PK/UNIQUE indexes are not duplicated):
- `ix_vehicle_seats_01`: B-tree (vehicle_id, layout_version, is_active) .
- `ix_vehicle_seats_created_by`: (created_by) WHERE created_by IS NOT NULL.
- `ix_vehicle_seats_updated_by`: (updated_by) WHERE updated_by IS NOT NULL.

Audit/version: increment version exactly once with every committed mutation, set server UTC updated_at/authenticated updated_by, retain created_at/created_by. Common actors do not replace durable decision history. Lifecycle immutability/append-only requirements below restrict otherwise valid SQL updates.

Lifecycle and cross-row guards: Version layouts instead of rewriting published departure inventory. Deactivate future selectable layout rows without deleting referenced seats. No new seat state or segment reuse.

## 11. `bookings`
Source: 02A section 4.12, pp9-10; Readiness section 5 requested_owner_user_id; canonical booking/payment.

| Column | PostgreSQL type | NULL | SQL default | FK / rule |
|---|---|---|---|---|
| id | UUID | NO | gen_random_uuid() | PK |
| created_at | TIMESTAMPTZ | NO | now() | No additional column rule; table checks below. |
| updated_at | TIMESTAMPTZ | NO | now() | No additional column rule; table checks below. |
| created_by | UUID | YES | NULL | REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| updated_by | UUID | YES | NULL | REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| version | INTEGER | NO | 1 | POSITIVE |
| booking_reference | VARCHAR(24) | NO | NONE | No additional column rule; table checks below. |
| passenger_user_id | UUID | NO | NONE | REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| booking_type | VARCHAR(16) | NO | NONE | CATALOGUE: PRIVATE_HIRE,TICKET_HIRE,RENTAL |
| service_type_id | UUID | NO | NONE | REFERENCES service_types(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| requested_owner_user_id | UUID | YES | NULL | REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| owner_user_id | UUID | YES | NULL | REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| vehicle_id | UUID | YES | NULL | REFERENCES vehicles(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| original_scheduled_trip_id | UUID | YES | NULL | REFERENCES scheduled_trips(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| current_scheduled_trip_id | UUID | YES | NULL | REFERENCES scheduled_trips(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| origin_text | TEXT | YES | NULL | No additional column rule; table checks below. |
| destination_text | TEXT | YES | NULL | No additional column rule; table checks below. |
| origin_stop_id | UUID | YES | NULL | REFERENCES route_stops(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| destination_stop_id | UUID | YES | NULL | REFERENCES route_stops(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| start_at | TIMESTAMPTZ | NO | NONE | No additional column rule; table checks below. |
| end_at | TIMESTAMPTZ | NO | NONE | No additional column rule; table checks below. |
| passenger_count | SMALLINT | NO | NONE | POSITIVE |
| large_luggage_count | SMALLINT | NO | 0 | NONNEGATIVE |
| small_luggage_count | SMALLINT | NO | 0 | NONNEGATIVE |
| special_requirements | TEXT | YES | NULL | No additional column rule; table checks below. |
| status | VARCHAR(24) | NO | 'REQUESTED' | CATALOGUE: REQUESTED,AWAITING_DRIVER,OWNER_ACTION_REQUIRED,CONFIRMED,IN_PROGRESS,COMPLETED,REJECTED,CANCELLED |
| assurance_type | VARCHAR(24) | NO | NONE | CATALOGUE: STANDARD_HIRE,FIXED_DEPARTURE,TRAVELLY_PROTECTED |
| protected_terms_snapshot | JSONB | NO | '{}'::jsonb | JSON_OBJECT |
| quoted_amount | NUMERIC(12,2) | YES | NULL | NONNEGATIVE |
| discount_amount | NUMERIC(12,2) | NO | 0 | NONNEGATIVE |
| total_amount | NUMERIC(12,2) | YES | NULL | NONNEGATIVE |
| currency | CHAR(3) | NO | NONE | No additional column rule; table checks below. |
| payment_status_snapshot | VARCHAR(32) | YES | NULL | CATALOGUE: PENDING,PROCESSING,PAID,CASH_AWAITING_CONFIRMATION,FAILED,REFUNDED,PARTIALLY_REFUNDED |
| cancelled_by_user_id | UUID | YES | NULL | REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| cancelled_at | TIMESTAMPTZ | YES | NULL | No additional column rule; table checks below. |
| cancellation_reason | TEXT | YES | NULL | No additional column rule; table checks below. |
| cancellation_policy_snapshot | JSONB | NO | '{}'::jsonb | JSON_OBJECT |
| idempotency_key | VARCHAR(80) | YES | NULL | No additional column rule; table checks below. |
| accepted_at | TIMESTAMPTZ | YES | NULL | No additional column rule; table checks below. |
| confirmed_at | TIMESTAMPTZ | YES | NULL | No additional column rule; table checks below. |

Primary key: `pk_bookings (id)`. IDs and creation provenance are immutable. All FKs are NOT DEFERRABLE, with names `fk_bookings_<column>`; actions are stated in the column rows.

Named CHECK constraints (SQL expressions; names are exact):

- `ck_bookings_01`: `end_at>start_at`.
- `ck_bookings_02`: `discount_amount=0 OR quoted_amount IS NOT NULL`.
- `ck_bookings_03`: `quoted_amount IS NULL OR discount_amount<=quoted_amount`.
- `ck_bookings_04`: `booking_type<>'TICKET_HIRE' OR (original_scheduled_trip_id IS NOT NULL AND current_scheduled_trip_id IS NOT NULL)`.
- `ck_bookings_05`: `version>=1`.
- `ck_bookings_06`: `updated_at>=created_at`.
- `ck_bookings_07`: `booking_reference=btrim(booking_reference) AND char_length(booking_reference)>0`.
- `ck_bookings_08`: `booking_type IN ('PRIVATE_HIRE','TICKET_HIRE','RENTAL')`.
- `ck_bookings_09`: `passenger_count>0`.
- `ck_bookings_10`: `large_luggage_count>=0`.
- `ck_bookings_11`: `small_luggage_count>=0`.
- `ck_bookings_12`: `status IN ('REQUESTED','AWAITING_DRIVER','OWNER_ACTION_REQUIRED','CONFIRMED','IN_PROGRESS','COMPLETED','REJECTED','CANCELLED')`.
- `ck_bookings_13`: `assurance_type IN ('STANDARD_HIRE','FIXED_DEPARTURE','TRAVELLY_PROTECTED')`.
- `ck_bookings_14`: `jsonb_typeof(protected_terms_snapshot)='object'`.
- `ck_bookings_15`: `quoted_amount>=0`.
- `ck_bookings_16`: `discount_amount>=0`.
- `ck_bookings_17`: `total_amount>=0`.
- `ck_bookings_18`: `currency ~ '^[A-Z]{3}$'`.
- `ck_bookings_19`: `payment_status_snapshot IN ('PENDING','PROCESSING','PAID','CASH_AWAITING_CONFIRMATION','FAILED','REFUNDED','PARTIALLY_REFUNDED')`.
- `ck_bookings_20`: `jsonb_typeof(cancellation_policy_snapshot)='object'`.
- `ck_bookings_21`: `idempotency_key=btrim(idempotency_key) AND char_length(idempotency_key)>0`.

UNIQUE constraints:
- `uq_bookings_01`: UNIQUE (booking_reference); NULLs retain PostgreSQL distinct semantics.
- `uq_bookings_02`: UNIQUE (idempotency_key); NULLs retain PostgreSQL distinct semantics.

Additional indexes (B-tree unless stated; PK/UNIQUE indexes are not duplicated):
- `ix_bookings_01`: B-tree (passenger_user_id, status, created_at DESC) .
- `ix_bookings_02`: B-tree (owner_user_id, status, start_at) .
- `ix_bookings_03`: B-tree (vehicle_id, start_at, end_at) .
- `ix_bookings_04`: B-tree (current_scheduled_trip_id, status) .
- `ix_bookings_05`: B-tree (service_type_id, start_at) .
- `ix_bookings_created_by`: (created_by) WHERE created_by IS NOT NULL.
- `ix_bookings_updated_by`: (updated_by) WHERE updated_by IS NOT NULL.

Audit/version: increment version exactly once with every committed mutation, set server UTC updated_at/authenticated updated_by, retain created_at/created_by. Common actors do not replace durable decision history. Lifecycle immutability/append-only requirements below restrict otherwise valid SQL updates.

Lifecycle and cross-row guards: REQUESTED -> CONFIRMED for eligible self-drive or AWAITING_DRIVER for external assignment; accepted assignment confirms; rejection -> OWNER_ACTION_REQUIRED; reassignment -> AWAITING_DRIVER; Owner rejection -> REJECTED; CONFIRMED -> IN_PROGRESS -> COMPLETED; cancellation by accepted policy. No DRAFT/HOLDING/refund booking values. Ticket temporary holds use seats only, then confirmed paid booking under Ticket contract. requested_owner_user_id is the immutable selected Owner from Readiness; owner_user_id is current authorized fulfilment Owner, not a replacement of Passenger identity. Original/current departure links and protected terms are retained. This maps already planned fields, not another ownership table. Do not expose these later-module operations under Admin Review approval.

## 12. `scheduled_trip_seats`
Source: 02A section 4.11, p9; project D03.

| Column | PostgreSQL type | NULL | SQL default | FK / rule |
|---|---|---|---|---|
| id | UUID | NO | gen_random_uuid() | PK |
| created_at | TIMESTAMPTZ | NO | now() | No additional column rule; table checks below. |
| updated_at | TIMESTAMPTZ | NO | now() | No additional column rule; table checks below. |
| created_by | UUID | YES | NULL | REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| updated_by | UUID | YES | NULL | REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| version | INTEGER | NO | 1 | POSITIVE |
| scheduled_trip_id | UUID | NO | NONE | REFERENCES scheduled_trips(id) ON DELETE CASCADE ON UPDATE RESTRICT |
| vehicle_seat_id | UUID | NO | NONE | REFERENCES vehicle_seats(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| seat_status | VARCHAR(9) | NO | 'AVAILABLE' | CATALOGUE: AVAILABLE,HELD,BOOKED,BLOCKED |
| held_by_booking_id | UUID | YES | NULL | REFERENCES bookings(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| hold_expires_at | TIMESTAMPTZ | YES | NULL | No additional column rule; table checks below. |
| booked_booking_id | UUID | YES | NULL | REFERENCES bookings(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| fare_override | NUMERIC(12,2) | YES | NULL | NONNEGATIVE |

Primary key: `pk_scheduled_trip_seats (id)`. IDs and creation provenance are immutable. All FKs are NOT DEFERRABLE, with names `fk_scheduled_trip_seats_<column>`; actions are stated in the column rows.

Named CHECK constraints (SQL expressions; names are exact):

- `ck_scheduled_trip_seats_01`: `seat_status<>'HELD' OR (held_by_booking_id IS NOT NULL AND hold_expires_at IS NOT NULL)`.
- `ck_scheduled_trip_seats_02`: `seat_status<>'BOOKED' OR booked_booking_id IS NOT NULL`.
- `ck_scheduled_trip_seats_03`: `seat_status<>'AVAILABLE' OR (held_by_booking_id IS NULL AND hold_expires_at IS NULL AND booked_booking_id IS NULL)`.
- `ck_scheduled_trip_seats_04`: `seat_status<>'HELD' OR booked_booking_id IS NULL`.
- `ck_scheduled_trip_seats_05`: `version>=1`.
- `ck_scheduled_trip_seats_06`: `updated_at>=created_at`.
- `ck_scheduled_trip_seats_07`: `seat_status IN ('AVAILABLE','HELD','BOOKED','BLOCKED')`.
- `ck_scheduled_trip_seats_08`: `fare_override>=0`.

UNIQUE constraints:
- `uq_scheduled_trip_seats_01`: UNIQUE (scheduled_trip_id, vehicle_seat_id); NULLs retain PostgreSQL distinct semantics.

Additional indexes (B-tree unless stated; PK/UNIQUE indexes are not duplicated):
- `ix_scheduled_trip_seats_01`: B-tree (scheduled_trip_id, seat_status) .
- `ix_scheduled_trip_seats_02`: B-tree (hold_expires_at) WHERE seat_status='HELD'.
- `ix_scheduled_trip_seats_created_by`: (created_by) WHERE created_by IS NOT NULL.
- `ix_scheduled_trip_seats_updated_by`: (updated_by) WHERE updated_by IS NOT NULL.

Audit/version: increment version exactly once with every committed mutation, set server UTC updated_at/authenticated updated_by, retain created_at/created_by. Common actors do not replace durable decision history. Lifecycle immutability/append-only requirements below restrict otherwise valid SQL updates.

Lifecycle and cross-row guards: AVAILABLE -> HELD -> BOOKED; affected unconfirmed HELD -> AVAILABLE on expiry/payment failure; authorized BLOCKED. Lock inventory atomically; never release BOOKED seats due to hold expiry. Clearing expired hold linkage and expiry happens in the same transaction. One seat covers the full departure. Creation follows bookings in migration order so existing hold/booked FKs resolve; table catalogue identity is unchanged.

## 13. `booking_travellers`
Source: 02A section 4.13, p10.

| Column | PostgreSQL type | NULL | SQL default | FK / rule |
|---|---|---|---|---|
| id | UUID | NO | gen_random_uuid() | PK |
| created_at | TIMESTAMPTZ | NO | now() | No additional column rule; table checks below. |
| updated_at | TIMESTAMPTZ | NO | now() | No additional column rule; table checks below. |
| created_by | UUID | YES | NULL | REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| updated_by | UUID | YES | NULL | REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| version | INTEGER | NO | 1 | POSITIVE |
| booking_id | UUID | NO | NONE | REFERENCES bookings(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| linked_user_id | UUID | YES | NULL | REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| full_name | VARCHAR(150) | NO | NONE | No additional column rule; table checks below. |
| contact_phone | VARCHAR(20) | YES | NULL | No additional column rule; table checks below. |
| contact_email | CITEXT | YES | NULL | No additional column rule; table checks below. |
| age_category | VARCHAR(30) | YES | NULL | No additional column rule; table checks below. |
| is_primary | BOOLEAN | NO | false | No additional column rule; table checks below. |
| identity_reference | VARCHAR(100) | YES | NULL | No additional column rule; table checks below. |
| scheduled_trip_seat_id | UUID | YES | NULL | REFERENCES scheduled_trip_seats(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| boarding_stop_id | UUID | YES | NULL | REFERENCES route_stops(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| dropoff_stop_id | UUID | YES | NULL | REFERENCES route_stops(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| special_assistance | TEXT | YES | NULL | No additional column rule; table checks below. |
| traveller_status | VARCHAR(12) | NO | 'ACTIVE' | CATALOGUE: ACTIVE,MOVED,CANCELLED,BOARDED,COMPLETED |

Primary key: `pk_booking_travellers (id)`. IDs and creation provenance are immutable. All FKs are NOT DEFERRABLE, with names `fk_booking_travellers_<column>`; actions are stated in the column rows.

Named CHECK constraints (SQL expressions; names are exact):

- `ck_booking_travellers_01`: `version>=1`.
- `ck_booking_travellers_02`: `updated_at>=created_at`.
- `ck_booking_travellers_03`: `full_name=btrim(full_name) AND char_length(full_name)>0`.
- `ck_booking_travellers_04`: `contact_phone=btrim(contact_phone) AND char_length(contact_phone)>0`.
- `ck_booking_travellers_05`: `age_category=btrim(age_category) AND char_length(age_category)>0`.
- `ck_booking_travellers_06`: `identity_reference=btrim(identity_reference) AND char_length(identity_reference)>0`.
- `ck_booking_travellers_07`: `traveller_status IN ('ACTIVE','MOVED','CANCELLED','BOARDED','COMPLETED')`.

UNIQUE constraints:
- None beyond the PK; do not infer global uniqueness from document numbers, filenames or display text.

Additional indexes (B-tree unless stated; PK/UNIQUE indexes are not duplicated):
- `ix_booking_travellers_01`: B-tree (booking_id) .
- `ix_booking_travellers_02`: UNIQUE B-tree (booking_id) WHERE is_primary.
- `ix_booking_travellers_03`: UNIQUE B-tree (scheduled_trip_seat_id) WHERE scheduled_trip_seat_id IS NOT NULL AND traveller_status IN ('ACTIVE','BOARDED').
- `ix_booking_travellers_created_by`: (created_by) WHERE created_by IS NOT NULL.
- `ix_booking_travellers_updated_by`: (updated_by) WHERE updated_by IS NOT NULL.

Audit/version: increment version exactly once with every committed mutation, set server UTC updated_at/authenticated updated_by, retain created_at/created_by. Common actors do not replace durable decision history. Lifecycle immutability/append-only requirements below restrict otherwise valid SQL updates.

Lifecycle and cross-row guards: ACTIVE -> BOARDED -> COMPLETED; authorized MOVED/CANCELLED retain old row. Enforce at most one primary row with a partial unique index and required primary completeness in booking transaction. Route transaction checks boarding precedes drop-off and correct departure/seat. No new age-category catalogue is invented: nullable nonblank bounded text until the service contract defines its accepted values.

## 14. `trips`
Source: 02A section 4.14, pp10-11; canonical assignment/trip states.

| Column | PostgreSQL type | NULL | SQL default | FK / rule |
|---|---|---|---|---|
| id | UUID | NO | gen_random_uuid() | PK |
| created_at | TIMESTAMPTZ | NO | now() | No additional column rule; table checks below. |
| updated_at | TIMESTAMPTZ | NO | now() | No additional column rule; table checks below. |
| created_by | UUID | YES | NULL | REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| updated_by | UUID | YES | NULL | REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| version | INTEGER | NO | 1 | POSITIVE |
| trip_reference | VARCHAR(24) | NO | NONE | No additional column rule; table checks below. |
| booking_id | UUID | YES | NULL | REFERENCES bookings(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| scheduled_trip_id | UUID | YES | NULL | REFERENCES scheduled_trips(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| vehicle_id | UUID | NO | NONE | REFERENCES vehicles(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| operating_owner_user_id | UUID | NO | NONE | REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| driver_user_id | UUID | YES | NULL | REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| assignment_type | VARCHAR(20) | YES | NULL | CATALOGUE: OWNER_SELF_DRIVE,EXTERNAL_DRIVER |
| assignment_status | VARCHAR(12) | NO | 'PENDING' | CATALOGUE: NOT_REQUIRED,PENDING,ACCEPTED,REJECTED,CANCELLED |
| status | VARCHAR(24) | NO | 'READY' | CATALOGUE: READY,IN_PROGRESS,BREAKDOWN,ASSISTANCE_REQUIRED,COMPLETED,CANCELLED |
| scheduled_start_at | TIMESTAMPTZ | NO | NONE | No additional column rule; table checks below. |
| scheduled_end_at | TIMESTAMPTZ | NO | NONE | No additional column rule; table checks below. |
| actual_start_at | TIMESTAMPTZ | YES | NULL | No additional column rule; table checks below. |
| actual_end_at | TIMESTAMPTZ | YES | NULL | No additional column rule; table checks below. |
| start_odometer_km | NUMERIC(12,1) | YES | NULL | NONNEGATIVE |
| end_odometer_km | NUMERIC(12,1) | YES | NULL | NONNEGATIVE |
| calculated_distance_km | NUMERIC(12,1) | YES | NULL | NONNEGATIVE |
| tracking_status | VARCHAR(8) | NO | 'OFF' | CATALOGUE: OFF,ACTIVE,STALE,ENDED |
| current_latitude | NUMERIC(9,6) | YES | NULL | No additional column rule; table checks below. |
| current_longitude | NUMERIC(9,6) | YES | NULL | No additional column rule; table checks below. |
| location_accuracy_m | NUMERIC(10,2) | YES | NULL | NONNEGATIVE |
| current_speed_kph | NUMERIC(8,2) | YES | NULL | NONNEGATIVE |
| location_updated_at | TIMESTAMPTZ | YES | NULL | No additional column rule; table checks below. |
| breakdown_details | TEXT | YES | NULL | No additional column rule; table checks below. |
| completion_notes | TEXT | YES | NULL | No additional column rule; table checks below. |

Primary key: `pk_trips (id)`. IDs and creation provenance are immutable. All FKs are NOT DEFERRABLE, with names `fk_trips_<column>`; actions are stated in the column rows.

Named CHECK constraints (SQL expressions; names are exact):

- `ck_trips_01`: `booking_id IS NOT NULL OR scheduled_trip_id IS NOT NULL`.
- `ck_trips_02`: `scheduled_end_at>scheduled_start_at`.
- `ck_trips_03`: `actual_start_at IS NULL OR actual_end_at IS NULL OR actual_end_at>=actual_start_at`.
- `ck_trips_04`: `start_odometer_km IS NULL OR end_odometer_km IS NULL OR end_odometer_km>=start_odometer_km`.
- `ck_trips_05`: `tracking_status NOT IN ('ACTIVE','STALE') OR status IN ('IN_PROGRESS','BREAKDOWN','ASSISTANCE_REQUIRED')`.
- `ck_trips_06`: `version>=1`.
- `ck_trips_07`: `updated_at>=created_at`.
- `ck_trips_08`: `trip_reference=btrim(trip_reference) AND char_length(trip_reference)>0`.
- `ck_trips_09`: `assignment_type IN ('OWNER_SELF_DRIVE','EXTERNAL_DRIVER')`.
- `ck_trips_10`: `assignment_status IN ('NOT_REQUIRED','PENDING','ACCEPTED','REJECTED','CANCELLED')`.
- `ck_trips_11`: `status IN ('READY','IN_PROGRESS','BREAKDOWN','ASSISTANCE_REQUIRED','COMPLETED','CANCELLED')`.
- `ck_trips_12`: `start_odometer_km>=0`.
- `ck_trips_13`: `end_odometer_km>=0`.
- `ck_trips_14`: `calculated_distance_km>=0`.
- `ck_trips_15`: `tracking_status IN ('OFF','ACTIVE','STALE','ENDED')`.
- `ck_trips_16`: `current_latitude BETWEEN -90 AND 90`.
- `ck_trips_17`: `current_longitude BETWEEN -180 AND 180`.
- `ck_trips_18`: `location_accuracy_m>=0`.
- `ck_trips_19`: `current_speed_kph>=0`.

UNIQUE constraints:
- `uq_trips_01`: UNIQUE (trip_reference); NULLs retain PostgreSQL distinct semantics.

Additional indexes (B-tree unless stated; PK/UNIQUE indexes are not duplicated):
- `ix_trips_01`: B-tree (driver_user_id, status, scheduled_start_at) .
- `ix_trips_02`: B-tree (operating_owner_user_id, status, scheduled_start_at) .
- `ix_trips_03`: B-tree (vehicle_id, scheduled_start_at) .
- `ix_trips_04`: B-tree (status) WHERE tracking_status IN ('ACTIVE','STALE').
- `ix_trips_created_by`: (created_by) WHERE created_by IS NOT NULL.
- `ix_trips_updated_by`: (updated_by) WHERE updated_by IS NOT NULL.

Audit/version: increment version exactly once with every committed mutation, set server UTC updated_at/authenticated updated_by, retain created_at/created_by. Common actors do not replace durable decision history. Lifecycle immutability/append-only requirements below restrict otherwise valid SQL updates.

Lifecycle and cross-row guards: READY -> IN_PROGRESS through POST /api/v1/trips/{trip_id}/start; active disruption -> BREAKDOWN/ASSISTANCE_REQUIRED; authorized completion/cancellation. Assignment PENDING -> ACCEPTED/REJECTED, or applicable NOT_REQUIRED/CANCELLED, separate from trip state. Only assigned eligible Driver/self-driving Owner operates; approval/documents/availability and non-overlap rechecked. Tracking ends at completion/cancellation. operating_owner_user_id is the architecture physical field; Readiness trip owner_user_id denotes that existing operating-owner relationship, not an additional column.

## 15. `payments`
Source: 02A section 4.15, p11; accepted separate Passenger payment/Owner settlement.

| Column | PostgreSQL type | NULL | SQL default | FK / rule |
|---|---|---|---|---|
| id | UUID | NO | gen_random_uuid() | PK |
| created_at | TIMESTAMPTZ | NO | now() | No additional column rule; table checks below. |
| updated_at | TIMESTAMPTZ | NO | now() | No additional column rule; table checks below. |
| created_by | UUID | YES | NULL | REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| updated_by | UUID | YES | NULL | REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| version | INTEGER | NO | 1 | POSITIVE |
| payment_reference | VARCHAR(30) | NO | NONE | No additional column rule; table checks below. |
| booking_id | UUID | NO | NONE | REFERENCES bookings(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| original_payment_id | UUID | YES | NULL | REFERENCES payments(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| payee_owner_user_id | UUID | YES | NULL | REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| transaction_type | VARCHAR(20) | NO | NONE | CATALOGUE: PAYMENT,REALLOCATION,ADDITIONAL_CHARGE,PARTIAL_REFUND,FULL_REFUND,OWNER_PAYOUT |
| payment_method | VARCHAR(12) | NO | NONE | CATALOGUE: CARD,BANK,MOBILE,CASH,SANDBOX |
| provider_name | VARCHAR(100) | YES | NULL | No additional column rule; table checks below. |
| provider_reference | VARCHAR(200) | YES | NULL | No additional column rule; table checks below. |
| idempotency_key | VARCHAR(100) | NO | NONE | No additional column rule; table checks below. |
| amount | NUMERIC(12,2) | NO | NONE | NONNEGATIVE |
| commission_amount | NUMERIC(12,2) | YES | NULL | NONNEGATIVE |
| owner_net_amount | NUMERIC(12,2) | YES | NULL | NONNEGATIVE |
| currency | CHAR(3) | NO | NONE | No additional column rule; table checks below. |
| status | VARCHAR(32) | NO | 'PENDING' | CATALOGUE: PENDING,PROCESSING,PAID,CASH_AWAITING_CONFIRMATION,FAILED,REFUNDED,PARTIALLY_REFUNDED |
| owner_settlement_status | VARCHAR(32) | YES | NULL | No additional column rule; table checks below. |
| authorized_at | TIMESTAMPTZ | YES | NULL | No additional column rule; table checks below. |
| captured_at | TIMESTAMPTZ | YES | NULL | No additional column rule; table checks below. |
| refunded_at | TIMESTAMPTZ | YES | NULL | No additional column rule; table checks below. |
| owner_payable_at | TIMESTAMPTZ | YES | NULL | No additional column rule; table checks below. |
| owner_paid_at | TIMESTAMPTZ | YES | NULL | No additional column rule; table checks below. |
| failure_code | VARCHAR(100) | YES | NULL | No additional column rule; table checks below. |
| failure_message | TEXT | YES | NULL | No additional column rule; table checks below. |

Primary key: `pk_payments (id)`. IDs and creation provenance are immutable. All FKs are NOT DEFERRABLE, with names `fk_payments_<column>`; actions are stated in the column rows.

Named CHECK constraints (SQL expressions; names are exact):

- `ck_payments_01`: `original_payment_id IS NULL OR original_payment_id<>id`.
- `ck_payments_02`: `commission_amount IS NULL OR commission_amount<=amount`.
- `ck_payments_03`: `owner_net_amount IS NULL OR owner_net_amount<=amount`.
- `ck_payments_04`: `version>=1`.
- `ck_payments_05`: `updated_at>=created_at`.
- `ck_payments_06`: `payment_reference=btrim(payment_reference) AND char_length(payment_reference)>0`.
- `ck_payments_07`: `transaction_type IN ('PAYMENT','REALLOCATION','ADDITIONAL_CHARGE','PARTIAL_REFUND','FULL_REFUND','OWNER_PAYOUT')`.
- `ck_payments_08`: `payment_method IN ('CARD','BANK','MOBILE','CASH','SANDBOX')`.
- `ck_payments_09`: `provider_name=btrim(provider_name) AND char_length(provider_name)>0`.
- `ck_payments_10`: `provider_reference=btrim(provider_reference) AND char_length(provider_reference)>0`.
- `ck_payments_11`: `idempotency_key=btrim(idempotency_key) AND char_length(idempotency_key)>0`.
- `ck_payments_12`: `amount>=0`.
- `ck_payments_13`: `commission_amount>=0`.
- `ck_payments_14`: `owner_net_amount>=0`.
- `ck_payments_15`: `currency ~ '^[A-Z]{3}$'`.
- `ck_payments_16`: `status IN ('PENDING','PROCESSING','PAID','CASH_AWAITING_CONFIRMATION','FAILED','REFUNDED','PARTIALLY_REFUNDED')`.
- `ck_payments_17`: `owner_settlement_status=btrim(owner_settlement_status) AND char_length(owner_settlement_status)>0`.
- `ck_payments_18`: `failure_code=btrim(failure_code) AND char_length(failure_code)>0`.

UNIQUE constraints:
- `uq_payments_01`: UNIQUE (payment_reference); NULLs retain PostgreSQL distinct semantics.
- `uq_payments_02`: UNIQUE (idempotency_key); NULLs retain PostgreSQL distinct semantics.

Additional indexes (B-tree unless stated; PK/UNIQUE indexes are not duplicated):
- `ix_payments_01`: B-tree (booking_id, created_at) .
- `ix_payments_02`: B-tree (provider_reference) .
- `ix_payments_03`: B-tree (payee_owner_user_id, owner_settlement_status) .
- `ix_payments_created_by`: (created_by) WHERE created_by IS NOT NULL.
- `ix_payments_updated_by`: (updated_by) WHERE updated_by IS NOT NULL.

Audit/version: increment version exactly once with every committed mutation, set server UTC updated_at/authenticated updated_by, retain created_at/created_by. Common actors do not replace durable decision history. Lifecycle immutability/append-only requirements below restrict otherwise valid SQL updates.

Lifecycle and cross-row guards: status is canonical Passenger payment state; owner_settlement_status is a distinct accepted settlement field, NULL until applicable. Existing named settlement meanings OWNER_PAYABLE/OWNER_PAID remain valid; this physical VARCHAR definition deliberately does not invent a complete settlement enum or grant unapproved transitions. Later settlement API must freeze its full business catalogue before write enablement. Provider stages are evidenced by existing provider references/timestamps and linked immutable transactions, not mixed into Passenger status. Append linked refund/reallocation/payout events; never rewrite captured amounts/history. Payable only after completion/reconciliation; sandbox/Admin-assisted current scope, no wallet/cross-owner automation. Physical definition is complete; later financial workflows remain outside Admin Review build approval.

## 16. `vehicle_records`
Source: 02A section 4.16, pp11-12.

| Column | PostgreSQL type | NULL | SQL default | FK / rule |
|---|---|---|---|---|
| id | UUID | NO | gen_random_uuid() | PK |
| created_at | TIMESTAMPTZ | NO | now() | No additional column rule; table checks below. |
| updated_at | TIMESTAMPTZ | NO | now() | No additional column rule; table checks below. |
| created_by | UUID | YES | NULL | REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| updated_by | UUID | YES | NULL | REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| version | INTEGER | NO | 1 | POSITIVE |
| vehicle_id | UUID | NO | NONE | REFERENCES vehicles(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| trip_id | UUID | YES | NULL | REFERENCES trips(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| recorded_by_user_id | UUID | NO | NONE | REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| record_type | VARCHAR(32) | NO | NONE | CATALOGUE: OIL_CHANGE,OIL_FILTER_CHANGE,TYRE_CHANGE,TYRE_ROTATION,WHEEL_ALIGNMENT,WHEEL_BALANCING,GENERAL_SERVICE,BRAKE_SERVICE,BATTERY_SERVICE,REPAIR,FUEL_PURCHASE,EV_CHARGING,PERSONAL_EXTRA_USE,ODOMETER_UPDATE,AVAILABILITY_BLOCK |
| recorded_at | TIMESTAMPTZ | NO | NONE | No additional column rule; table checks below. |
| odometer_km | NUMERIC(12,1) | YES | NULL | NONNEGATIVE |
| start_at | TIMESTAMPTZ | YES | NULL | No additional column rule; table checks below. |
| end_at | TIMESTAMPTZ | YES | NULL | No additional column rule; table checks below. |
| start_odometer_km | NUMERIC(12,1) | YES | NULL | NONNEGATIVE |
| end_odometer_km | NUMERIC(12,1) | YES | NULL | NONNEGATIVE |
| amount | NUMERIC(12,2) | YES | NULL | NONNEGATIVE |
| currency | CHAR(3) | YES | NULL | No additional column rule; table checks below. |
| quantity | NUMERIC(12,3) | YES | NULL | NONNEGATIVE |
| unit | VARCHAR(20) | YES | NULL | No additional column rule; table checks below. |
| fuel_type | VARCHAR(30) | YES | NULL | No additional column rule; table checks below. |
| fuel_grade_product | VARCHAR(100) | YES | NULL | No additional column rule; table checks below. |
| charging_kwh | NUMERIC(12,3) | YES | NULL | NONNEGATIVE |
| next_due_odometer_km | NUMERIC(12,1) | YES | NULL | NONNEGATIVE |
| genuine_calendar_due_date | DATE | YES | NULL | No additional column rule; table checks below. |
| service_provider | VARCHAR(150) | YES | NULL | No additional column rule; table checks below. |
| receipt_url | TEXT | YES | NULL | No additional column rule; table checks below. |
| notes | TEXT | YES | NULL | No additional column rule; table checks below. |
| approval_status | VARCHAR(24) | YES | NULL | No additional column rule; table checks below. |

Primary key: `pk_vehicle_records (id)`. IDs and creation provenance are immutable. All FKs are NOT DEFERRABLE, with names `fk_vehicle_records_<column>`; actions are stated in the column rows.

Named CHECK constraints (SQL expressions; names are exact):

- `ck_vehicle_records_01`: `start_at IS NULL OR end_at IS NULL OR end_at>start_at`.
- `ck_vehicle_records_02`: `start_odometer_km IS NULL OR end_odometer_km IS NULL OR end_odometer_km>=start_odometer_km`.
- `ck_vehicle_records_03`: `record_type<>'AVAILABILITY_BLOCK' OR (start_at IS NOT NULL AND end_at IS NOT NULL)`.
- `ck_vehicle_records_04`: `record_type<>'FUEL_PURCHASE' OR (fuel_grade_product IS NOT NULL AND quantity IS NOT NULL AND amount IS NOT NULL)`.
- `ck_vehicle_records_05`: `record_type<>'EV_CHARGING' OR amount IS NOT NULL`.
- `ck_vehicle_records_06`: `version>=1`.
- `ck_vehicle_records_07`: `updated_at>=created_at`.
- `ck_vehicle_records_08`: `record_type IN ('OIL_CHANGE','OIL_FILTER_CHANGE','TYRE_CHANGE','TYRE_ROTATION','WHEEL_ALIGNMENT','WHEEL_BALANCING','GENERAL_SERVICE','BRAKE_SERVICE','BATTERY_SERVICE','REPAIR','FUEL_PURCHASE','EV_CHARGING','PERSONAL_EXTRA_USE','ODOMETER_UPDATE','AVAILABILITY_BLOCK')`.
- `ck_vehicle_records_09`: `odometer_km>=0`.
- `ck_vehicle_records_10`: `start_odometer_km>=0`.
- `ck_vehicle_records_11`: `end_odometer_km>=0`.
- `ck_vehicle_records_12`: `amount>=0`.
- `ck_vehicle_records_13`: `currency ~ '^[A-Z]{3}$'`.
- `ck_vehicle_records_14`: `quantity>=0`.
- `ck_vehicle_records_15`: `unit=btrim(unit) AND char_length(unit)>0`.
- `ck_vehicle_records_16`: `fuel_type=btrim(fuel_type) AND char_length(fuel_type)>0`.
- `ck_vehicle_records_17`: `fuel_grade_product=btrim(fuel_grade_product) AND char_length(fuel_grade_product)>0`.
- `ck_vehicle_records_18`: `charging_kwh>=0`.
- `ck_vehicle_records_19`: `next_due_odometer_km>=0`.
- `ck_vehicle_records_20`: `service_provider=btrim(service_provider) AND char_length(service_provider)>0`.
- `ck_vehicle_records_21`: `approval_status=btrim(approval_status) AND char_length(approval_status)>0`.

UNIQUE constraints:
- None beyond the PK; do not infer global uniqueness from document numbers, filenames or display text.

Additional indexes (B-tree unless stated; PK/UNIQUE indexes are not duplicated):
- `ix_vehicle_records_01`: B-tree (vehicle_id, record_type, recorded_at DESC) .
- `ix_vehicle_records_02`: B-tree (vehicle_id, start_at, end_at) .
- `ix_vehicle_records_03`: B-tree (trip_id) .
- `ix_vehicle_records_created_by`: (created_by) WHERE created_by IS NOT NULL.
- `ix_vehicle_records_updated_by`: (updated_by) WHERE updated_by IS NOT NULL.

Audit/version: increment version exactly once with every committed mutation, set server UTC updated_at/authenticated updated_by, retain created_at/created_by. Common actors do not replace durable decision history. Lifecycle immutability/append-only requirements below restrict otherwise valid SQL updates.

Lifecycle and cross-row guards: The architecture names approval_status but supplies no closed record-approval catalogue. Freeze nullable bounded nonblank text without inventing a default/status vocabulary; the later Vehicle Records contract must authorize its exact values/transitions before writes. This is not an Owner/Driver role application. Accepted records alone update odometer/estimates; historical expenses not recalculated at current prices. Preserve litres versus kWh, BEV/PHEV compatibility and no invented consumption/usage. Availability uses existing.start_at < requested.end_at AND existing.end_at > requested.start_at; no fixed calendar exclusivity constraint that would block historical maintenance entries.

## 17. `notifications`
Source: 02A section 4.17, pp12-13; IVR/SMS deferred correction.

| Column | PostgreSQL type | NULL | SQL default | FK / rule |
|---|---|---|---|---|
| id | UUID | NO | gen_random_uuid() | PK |
| created_at | TIMESTAMPTZ | NO | now() | No additional column rule; table checks below. |
| updated_at | TIMESTAMPTZ | NO | now() | No additional column rule; table checks below. |
| created_by | UUID | YES | NULL | REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| updated_by | UUID | YES | NULL | REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| version | INTEGER | NO | 1 | POSITIVE |
| recipient_user_id | UUID | NO | NONE | REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| booking_id | UUID | YES | NULL | REFERENCES bookings(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| scheduled_trip_id | UUID | YES | NULL | REFERENCES scheduled_trips(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| trip_id | UUID | YES | NULL | REFERENCES trips(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| notification_type | VARCHAR(24) | NO | NONE | CATALOGUE: BOOKING_REQUEST,BOOKING_CONFIRMED,DRIVER_ASSIGNMENT,RECONFIRMATION,PAYMENT,REFUND,REPLACEMENT,MAINTENANCE_DUE,DOCUMENT_EXPIRY,ROAD_ALERT,ADMIN_ACTION |
| channel | VARCHAR(8) | NO | NONE | CATALOGUE: IN_APP,EMAIL |
| title | VARCHAR(200) | NO | NONE | No additional column rule; table checks below. |
| body | TEXT | NO | NONE | No additional column rule; table checks below. |
| action_required | BOOLEAN | NO | false | No additional column rule; table checks below. |
| action_payload | JSONB | NO | '{}'::jsonb | JSON_OBJECT |
| status | VARCHAR(12) | NO | 'QUEUED' | CATALOGUE: QUEUED,SENT,DELIVERED,READ,RESPONDED,FAILED,EXPIRED |
| sent_at | TIMESTAMPTZ | YES | NULL | No additional column rule; table checks below. |
| delivered_at | TIMESTAMPTZ | YES | NULL | No additional column rule; table checks below. |
| read_at | TIMESTAMPTZ | YES | NULL | No additional column rule; table checks below. |
| response_code | VARCHAR(40) | YES | NULL | No additional column rule; table checks below. |
| response_value | TEXT | YES | NULL | No additional column rule; table checks below. |
| responded_at | TIMESTAMPTZ | YES | NULL | No additional column rule; table checks below. |
| expires_at | TIMESTAMPTZ | YES | NULL | No additional column rule; table checks below. |
| retry_count | INTEGER | NO | 0 | NONNEGATIVE |

Primary key: `pk_notifications (id)`. IDs and creation provenance are immutable. All FKs are NOT DEFERRABLE, with names `fk_notifications_<column>`; actions are stated in the column rows.

Named CHECK constraints (SQL expressions; names are exact):

- `ck_notifications_01`: `version>=1`.
- `ck_notifications_02`: `updated_at>=created_at`.
- `ck_notifications_03`: `notification_type IN ('BOOKING_REQUEST','BOOKING_CONFIRMED','DRIVER_ASSIGNMENT','RECONFIRMATION','PAYMENT','REFUND','REPLACEMENT','MAINTENANCE_DUE','DOCUMENT_EXPIRY','ROAD_ALERT','ADMIN_ACTION')`.
- `ck_notifications_04`: `channel IN ('IN_APP','EMAIL')`.
- `ck_notifications_05`: `title=btrim(title) AND char_length(title)>0`.
- `ck_notifications_06`: `jsonb_typeof(action_payload)='object'`.
- `ck_notifications_07`: `status IN ('QUEUED','SENT','DELIVERED','READ','RESPONDED','FAILED','EXPIRED')`.
- `ck_notifications_08`: `response_code=btrim(response_code) AND char_length(response_code)>0`.
- `ck_notifications_09`: `retry_count>=0`.

UNIQUE constraints:
- None beyond the PK; do not infer global uniqueness from document numbers, filenames or display text.

Additional indexes (B-tree unless stated; PK/UNIQUE indexes are not duplicated):
- `ix_notifications_01`: B-tree (recipient_user_id, status, created_at) .
- `ix_notifications_02`: B-tree (expires_at, status) .
- `ix_notifications_created_by`: (created_by) WHERE created_by IS NOT NULL.
- `ix_notifications_updated_by`: (updated_by) WHERE updated_by IS NOT NULL.

Audit/version: increment version exactly once with every committed mutation, set server UTC updated_at/authenticated updated_by, retain created_at/created_by. Common actors do not replace durable decision history. Lifecycle immutability/append-only requirements below restrict otherwise valid SQL updates.

Lifecycle and cross-row guards: QUEUED -> SENT -> DELIVERED -> READ/RESPONDED; bounded retry FAILED/EXPIRED under the delivery contract. Only authenticated in-app/email actions; response fields do not implement IVR. No response alone never cancels or releases inventory. No SMS/IVR runtime channel, subscriptions or promotions. Private document bytes/reasons are not a history substitute in action_payload/body.

## 18. `social_posts`
Source: 02A section 4.18, p13.

| Column | PostgreSQL type | NULL | SQL default | FK / rule |
|---|---|---|---|---|
| id | UUID | NO | gen_random_uuid() | PK |
| created_at | TIMESTAMPTZ | NO | now() | No additional column rule; table checks below. |
| updated_at | TIMESTAMPTZ | NO | now() | No additional column rule; table checks below. |
| created_by | UUID | YES | NULL | REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| updated_by | UUID | YES | NULL | REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| version | INTEGER | NO | 1 | POSITIVE |
| author_user_id | UUID | NO | NONE | REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| post_type | VARCHAR(8) | NO | NONE | CATALOGUE: REEL,PHOTO,REVIEW |
| media_url | TEXT | YES | NULL | No additional column rule; table checks below. |
| thumbnail_url | TEXT | YES | NULL | No additional column rule; table checks below. |
| caption | TEXT | YES | NULL | No additional column rule; table checks below. |
| hashtags | JSONB | NO | '[]'::jsonb | JSON_ARRAY |
| location_name | VARCHAR(150) | YES | NULL | No additional column rule; table checks below. |
| latitude | NUMERIC(9,6) | YES | NULL | No additional column rule; table checks below. |
| longitude | NUMERIC(9,6) | YES | NULL | No additional column rule; table checks below. |
| linked_vehicle_id | UUID | YES | NULL | REFERENCES vehicles(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| linked_route_id | UUID | YES | NULL | REFERENCES routes(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| linked_scheduled_trip_id | UUID | YES | NULL | REFERENCES scheduled_trips(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| visibility | VARCHAR(12) | NO | 'PRIVATE' | CATALOGUE: PUBLIC,FOLLOWERS,PRIVATE |
| moderation_status | VARCHAR(9) | NO | 'PENDING' | CATALOGUE: PENDING,APPROVED,REJECTED,HIDDEN |
| published_at | TIMESTAMPTZ | YES | NULL | No additional column rule; table checks below. |
| duration_seconds | INTEGER | YES | NULL | NONNEGATIVE |
| denormalized_like_count | INTEGER | NO | 0 | NONNEGATIVE |
| comment_count | INTEGER | NO | 0 | NONNEGATIVE |
| share_count | INTEGER | NO | 0 | NONNEGATIVE |

Primary key: `pk_social_posts (id)`. IDs and creation provenance are immutable. All FKs are NOT DEFERRABLE, with names `fk_social_posts_<column>`; actions are stated in the column rows.

Named CHECK constraints (SQL expressions; names are exact):

- `ck_social_posts_01`: `version>=1`.
- `ck_social_posts_02`: `updated_at>=created_at`.
- `ck_social_posts_03`: `post_type IN ('REEL','PHOTO','REVIEW')`.
- `ck_social_posts_04`: `jsonb_typeof(hashtags)='array'`.
- `ck_social_posts_05`: `location_name=btrim(location_name) AND char_length(location_name)>0`.
- `ck_social_posts_06`: `latitude BETWEEN -90 AND 90`.
- `ck_social_posts_07`: `longitude BETWEEN -180 AND 180`.
- `ck_social_posts_08`: `visibility IN ('PUBLIC','FOLLOWERS','PRIVATE')`.
- `ck_social_posts_09`: `moderation_status IN ('PENDING','APPROVED','REJECTED','HIDDEN')`.
- `ck_social_posts_10`: `duration_seconds>=0`.
- `ck_social_posts_11`: `denormalized_like_count>=0`.
- `ck_social_posts_12`: `comment_count>=0`.
- `ck_social_posts_13`: `share_count>=0`.

UNIQUE constraints:
- None beyond the PK; do not infer global uniqueness from document numbers, filenames or display text.

Additional indexes (B-tree unless stated; PK/UNIQUE indexes are not duplicated):
- `ix_social_posts_01`: B-tree (moderation_status, published_at) .
- `ix_social_posts_02`: B-tree (author_user_id, published_at) .
- `ix_social_posts_created_by`: (created_by) WHERE created_by IS NOT NULL.
- `ix_social_posts_updated_by`: (updated_by) WHERE updated_by IS NOT NULL.

Audit/version: increment version exactly once with every committed mutation, set server UTC updated_at/authenticated updated_by, retain created_at/created_by. Common actors do not replace durable decision history. Lifecycle immutability/append-only requirements below restrict otherwise valid SQL updates.

Lifecycle and cross-row guards: PENDING -> APPROVED/REJECTED; authorized HIDDEN. Public reads require visibility/moderation/publication guards; default PRIVATE is fail-closed storage, not a new posting workflow. Media outside DB, no private document links. Counter caches reconcile from interactions; discovery links never guarantee live availability. General promotions/coupons excluded; ordinary promotional Reel content retains existing scope.

## 19. `social_interactions`
Source: 02A section 4.19, p13.

| Column | PostgreSQL type | NULL | SQL default | FK / rule |
|---|---|---|---|---|
| id | UUID | NO | gen_random_uuid() | PK |
| created_at | TIMESTAMPTZ | NO | now() | No additional column rule; table checks below. |
| updated_at | TIMESTAMPTZ | NO | now() | No additional column rule; table checks below. |
| created_by | UUID | YES | NULL | REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| updated_by | UUID | YES | NULL | REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| version | INTEGER | NO | 1 | POSITIVE |
| actor_user_id | UUID | NO | NONE | REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| post_id | UUID | YES | NULL | REFERENCES social_posts(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| target_user_id | UUID | YES | NULL | REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| interaction_type | VARCHAR(12) | NO | NONE | CATALOGUE: LIKE,COMMENT,SAVE,SHARE,FOLLOW,REPORT,RATING |
| comment_text | TEXT | YES | NULL | No additional column rule; table checks below. |
| rating | SMALLINT | YES | NULL | No additional column rule; table checks below. |
| report_reason | TEXT | YES | NULL | No additional column rule; table checks below. |
| interaction_status | VARCHAR(12) | NO | 'ACTIVE' | CATALOGUE: ACTIVE,REMOVED,UNDER_REVIEW,RESOLVED |
| parent_interaction_id | UUID | YES | NULL | REFERENCES social_interactions(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| interaction_metadata | JSONB | NO | '{}'::jsonb | JSON_OBJECT |

Primary key: `pk_social_interactions (id)`. IDs and creation provenance are immutable. All FKs are NOT DEFERRABLE, with names `fk_social_interactions_<column>`; actions are stated in the column rows.

Named CHECK constraints (SQL expressions; names are exact):

- `ck_social_interactions_01`: `(interaction_type='FOLLOW' AND target_user_id IS NOT NULL AND post_id IS NULL) OR (interaction_type<>'FOLLOW' AND post_id IS NOT NULL AND target_user_id IS NULL)`.
- `ck_social_interactions_02`: `rating IS NULL OR rating BETWEEN 1 AND 5`.
- `ck_social_interactions_03`: `interaction_type<>'RATING' OR rating IS NOT NULL`.
- `ck_social_interactions_04`: `parent_interaction_id IS NULL OR (parent_interaction_id<>id AND interaction_type='COMMENT')`.
- `ck_social_interactions_05`: `version>=1`.
- `ck_social_interactions_06`: `updated_at>=created_at`.
- `ck_social_interactions_07`: `interaction_type IN ('LIKE','COMMENT','SAVE','SHARE','FOLLOW','REPORT','RATING')`.
- `ck_social_interactions_08`: `interaction_status IN ('ACTIVE','REMOVED','UNDER_REVIEW','RESOLVED')`.
- `ck_social_interactions_09`: `jsonb_typeof(interaction_metadata)='object'`.

UNIQUE constraints:
- None beyond the PK; do not infer global uniqueness from document numbers, filenames or display text.

Additional indexes (B-tree unless stated; PK/UNIQUE indexes are not duplicated):
- `ix_social_interactions_01`: B-tree (post_id, interaction_type, interaction_status) .
- `ix_social_interactions_02`: UNIQUE B-tree (actor_user_id, post_id, interaction_type) WHERE interaction_status='ACTIVE' AND interaction_type IN ('LIKE','SAVE').
- `ix_social_interactions_03`: UNIQUE B-tree (actor_user_id, target_user_id) WHERE interaction_status='ACTIVE' AND interaction_type='FOLLOW'.
- `ix_social_interactions_04`: B-tree (parent_interaction_id) .
- `ix_social_interactions_created_by`: (created_by) WHERE created_by IS NOT NULL.
- `ix_social_interactions_updated_by`: (updated_by) WHERE updated_by IS NOT NULL.

Audit/version: increment version exactly once with every committed mutation, set server UTC updated_at/authenticated updated_by, retain created_at/created_by. Common actors do not replace durable decision history. Lifecycle immutability/append-only requirements below restrict otherwise valid SQL updates.

Lifecycle and cross-row guards: ACTIVE -> REMOVED/UNDER_REVIEW; moderation may resolve under its future contract. Preserve typed target shapes and same-post reply ownership; rating 1-5. At most one active LIKE/SAVE per actor/post/type and FOLLOW per actor/target; no extra social join/history table.

## 20. `road_alerts`
Source: 02A section 4.20, p14.

| Column | PostgreSQL type | NULL | SQL default | FK / rule |
|---|---|---|---|---|
| id | UUID | NO | gen_random_uuid() | PK |
| created_at | TIMESTAMPTZ | NO | now() | No additional column rule; table checks below. |
| updated_at | TIMESTAMPTZ | NO | now() | No additional column rule; table checks below. |
| created_by | UUID | YES | NULL | REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| updated_by | UUID | YES | NULL | REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| version | INTEGER | NO | 1 | POSITIVE |
| reporter_user_id | UUID | NO | NONE | REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| trip_id | UUID | YES | NULL | REFERENCES trips(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| alert_type | VARCHAR(20) | NO | NONE | CATALOGUE: POLICE_PRESENCE,SPEED_CHECK,ACCIDENT,ROADBLOCK,ROAD_HAZARD |
| latitude | NUMERIC(9,6) | NO | NONE | No additional column rule; table checks below. |
| longitude | NUMERIC(9,6) | NO | NONE | No additional column rule; table checks below. |
| travel_direction_degrees | NUMERIC(6,3) | YES | NULL | No additional column rule; table checks below. |
| description | TEXT | YES | NULL | No additional column rule; table checks below. |
| source_input | VARCHAR(8) | NO | NONE | CATALOGUE: BUTTON,VOICE |
| status | VARCHAR(12) | NO | 'UNCONFIRMED' | CATALOGUE: ACTIVE,UNCONFIRMED,VERIFIED,EXPIRED,REJECTED,REMOVED |
| confidence_score | NUMERIC(5,4) | YES | NULL | No additional column rule; table checks below. |
| confirmation_count | INTEGER | NO | 0 | NONNEGATIVE |
| denial_count | INTEGER | NO | 0 | NONNEGATIVE |
| reported_at | TIMESTAMPTZ | NO | NONE | No additional column rule; table checks below. |
| verified_at | TIMESTAMPTZ | YES | NULL | No additional column rule; table checks below. |
| expires_at | TIMESTAMPTZ | NO | NONE | No additional column rule; table checks below. |
| moderated_by_user_id | UUID | YES | NULL | REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT |
| moderation_reason | TEXT | YES | NULL | No additional column rule; table checks below. |

Primary key: `pk_road_alerts (id)`. IDs and creation provenance are immutable. All FKs are NOT DEFERRABLE, with names `fk_road_alerts_<column>`; actions are stated in the column rows.

Named CHECK constraints (SQL expressions; names are exact):

- `ck_road_alerts_01`: `travel_direction_degrees IS NULL OR (travel_direction_degrees>=0 AND travel_direction_degrees<360)`.
- `ck_road_alerts_02`: `confidence_score IS NULL OR confidence_score BETWEEN 0 AND 1`.
- `ck_road_alerts_03`: `expires_at>reported_at`.
- `ck_road_alerts_04`: `version>=1`.
- `ck_road_alerts_05`: `updated_at>=created_at`.
- `ck_road_alerts_06`: `alert_type IN ('POLICE_PRESENCE','SPEED_CHECK','ACCIDENT','ROADBLOCK','ROAD_HAZARD')`.
- `ck_road_alerts_07`: `latitude BETWEEN -90 AND 90`.
- `ck_road_alerts_08`: `longitude BETWEEN -180 AND 180`.
- `ck_road_alerts_09`: `source_input IN ('BUTTON','VOICE')`.
- `ck_road_alerts_10`: `status IN ('ACTIVE','UNCONFIRMED','VERIFIED','EXPIRED','REJECTED','REMOVED')`.
- `ck_road_alerts_11`: `confirmation_count>=0`.
- `ck_road_alerts_12`: `denial_count>=0`.

UNIQUE constraints:
- None beyond the PK; do not infer global uniqueness from document numbers, filenames or display text.

Additional indexes (B-tree unless stated; PK/UNIQUE indexes are not duplicated):
- `ix_road_alerts_01`: B-tree (status, expires_at) .
- `ix_road_alerts_02`: B-tree (trip_id) .
- `ix_road_alerts_03`: B-tree (reporter_user_id) .
- `ix_road_alerts_04`: B-tree (latitude, longitude) .
- `ix_road_alerts_created_by`: (created_by) WHERE created_by IS NOT NULL.
- `ix_road_alerts_updated_by`: (updated_by) WHERE updated_by IS NOT NULL.

Audit/version: increment version exactly once with every committed mutation, set server UTC updated_at/authenticated updated_by, retain created_at/created_by. Common actors do not replace durable decision history. Lifecycle immutability/append-only requirements below restrict otherwise valid SQL updates.

Lifecycle and cross-row guards: Existing ACTIVE/UNCONFIRMED/VERIFIED and authorized EXPIRED/REJECTED/REMOVED states only. Reporting requires assigned active eligible Driver/self-driving Owner, valid current trip/direction/expiry; nullable trip FK accommodates existing architecture but does not waive reporting eligibility. Use bounded coordinate indexes and distance calculation; no new stored geospatial point column. Voice classification never directly invents an alert or bypasses confirmation. Road safety only; no full GPS-history/AI-query table.

## C. Cross-table transaction, privacy and lifecycle requirements

- SQL CHECKs are structural, not authorization. Every protected endpoint rechecks live account/session/role/ownership. Only APPROVED Owner/Driver workspaces are selectable, independently; Passenger remains permanent/default.
- Versioned updates lock/re-read the current target and relevant ownership/evidence rows; compare expected version before mutation and atomically increment once. A stale reviewer cannot overwrite a newer status. No self-review, client-supplied reviewer/time or approval bypass.
- Required document identity/ownership/licence evidence follows AR-D01-D05. Approval cannot happen until the exact checklist is verified/current. User-owned evidence has vehicle_id NULL; no fake vehicle or company account. Document owners retain private access subject to eligible account/session even when roles are pending/rejected/suspended.
- Ordinary transaction plus confirmed durable audit intent precedes any Admin decision commit. The restricted append-only journal records full reasons outside application tables; crash recovery uses PostgreSQL transaction outcome, never prepared transactions. Detailed protocol is prerequisites section 7.
- Booking/assignment/trip/payment/settlement and vehicle verification/availability remain separate states. Lock seats and accepted availability checks at their module gates; no automatic protected cancellation/refund/commit on missed deadline or missing attendance response. Required refunds/financial history are linked immutable events.
- Departure/booking accepted terms and original/current relationships remain retained. Privacy-scoped tracking only during active permitted trip states; completion/cancellation stops sharing. No GPS-history table.
- Nullable text fields with an unfrozen later business vocabulary (e.g. age_category, settlement detail) have a complete physical type/default/CHECK definition, but this document does not authorize new values, states or future workflows. Financial, vehicle, booking and Social module API/business freezes remain separate from Admin Review.

## D. Completeness and build boundary

Exactly 20 application table definitions are present. SQL common fields, PKs, FKs/actions, nullability/defaults, uniqueness, checks, indexes and lifecycle guards are normative. Physical inventory and FK integrity checks are documentation checks, not executed migrations or database tests. Original PDFs remain unchanged. The exact Admin/document API artifact and technical acceptance checklist must agree with this dictionary before Admin code is built; runtime acceptance is still required before enabling review.


## 26 October 2026 Auth extension amendment

Under Final Decisions AU-01 through AU-07 and 03E, activate the already planned users.external_auth_provider/external_auth_subject nullable unique pair for GOOGLE. No new table. users.password_hash becomes nullable only when external_auth_provider is present; non-null hashes keep the existing nonempty constraint and unchanged Argon2id parameters. Add users.email_login_required BOOLEAN NOT NULL (existing rows backfilled false; new rows default true), users.auth_version INTEGER NOT NULL DEFAULT 0 CHECK >=0, and users.terms_accepted_at TIMESTAMPTZ NULL for legacy rows. Add a CHECK requiring a password hash or an external provider; provider/subject must be jointly NULL or valid GOOGLE/nonempty-subject. These auth fields are not arbitrary request input or public profile details. Migration preserves every current user ID, role and contact timestamp. The planned count remains twenty application tables, with the current four implemented application tables unchanged. Earlier provider deferral/password NOT NULL statements are superseded only by this amendment.
