# Travelly Admin Review Technical Acceptance Checklist

Version: 1.0 | Frozen: 25 October 2026

Use Final Decisions, 02C physical dictionary, 03C OpenAPI, 03D API contract and 04 prerequisites. These are required future implementation/enablement checks, not tests executed by this documentation task. A checked documentation freeze does not mean a deployed module passed runtime acceptance.

## 1. Documentation/build-start checks

| ID | Required evidence | Documentation result |
|---|---|---|
| DOC-01 | Exactly the 20 existing architecture tables have explicit per-column physical definitions, constraints/FK actions/indexes/version/lifecycle; no extra application entity. | Defined in 02C. |
| DOC-02 | Existing Auth baseline preserved; optional source-planned users fields are separate and not new Auth input or Admin migration prerequisites. | Defined in 02C/Final Decisions. |
| DOC-03 | vehicles precedes documents; existing hold/booked-booking FKs resolve by creating bookings before scheduled_trip_seats. | Defined in 02C. |
| DOC-04 | Matrix IDs 1-96 retained; 97/98/99 match queue/detail/stream; upload/reviews/DTO/errors/Bearer/version match OpenAPI and 03D. | Synchronized documentation; verify saved artifacts. |
| DOC-05 | Private multipart/storage and append-only journal/normal-commit/recovery/provisioning rules have no unresolved required specification. | Frozen in 04/03D. |

## 2. Schema and migration order (runtime; not executed)

- [ ] DB-01: Connect to PostgreSQL travelly_dev as travelly_app, never SQLite. Preserve existing data, Auth types/constraints and revisions. No superuser privilege grant to runtime.
- [ ] DB-02: Only affected planned migrations are introduced for Admin dependencies: existing users/user_roles -> vehicles -> documents. Do not implement all later modules or add an audit/outbox/session/history table.
- [ ] DB-03: Verify every affected column/type/precision/length/null/default, PK/unique/CHECK/FK/delete-update action and index against 02C. SQL CHECK null semantics must not bypass required evidence.
- [ ] DB-04: Verify exclusive document ownership, safe supersession/self-FK, storage-key uniqueness, file sizes/MIME/checksum and reviewer/result constraints. Preserve old files/rows/history.
- [ ] DB-05: Verify immutable Passenger membership, independent roles, exactly four role states and version >=1. No company account, requested self-approval or client actor/time.
- [ ] DB-06: Keep max_prepared_transactions unchanged/0; no PREPARE TRANSACTION or two-phase commit. Verify fsync and review-transaction synchronous_commit on, xid8 outcome-read capability and stable database/restore identity.

## 3. Upload validation and private storage

- [ ] FILE-01: USER/VEHICLE ownership checks precede accepting private uploads. Pending/rejected/suspended applicants with eligible accounts may upload/read their own evidence; no Admin impersonation upload.
- [ ] FILE-02: Exactly one file; accept genuine PDF/JPEG/PNG and reject HTML/SVG/executable/archive/renamed or MIME-mismatched content, malformed/encrypted PDF, missing/empty file, duplicate parts and unknown fields. Required validator unavailable fails closed.
- [ ] FILE-03: Test file boundary 10485760 bytes versus 10485761, text-field boundary 8192, full multipart boundary 10551296, chunked input and false Content-Length. Confirm 413/415/422 and no residual usable document on failure.
- [ ] FILE-04: Test traversal, absolute paths, backslashes, colon/NTFS alternate streams, Windows reserved names, CR/LF, control characters, junction/symlink escape and collision attempts. Storage key is server-generated opaque identity; filename is display only.
- [ ] FILE-05: Private root and journal are outside repository/webroot with restricted OS identities, no static mount/public/signed URLs, encrypted protected backup and restoration procedure. Browser/API never receives filesystem key/credentials.
- [ ] FILE-06: Success only after content validation, actual MIME/size/server SHA-256, durable final bytes and SUBMITTED metadata. No role/contact/vehicle approval is implied.
- [ ] FILE-07: Simulate failed validation, failed rename/flush, DB rollback, process kill before/after file placement and uncertain DB result. Clean only proven unreferenced own orphans; retain referenced/superseded/in-progress bytes. Missing referenced file returns safe dependency error and blocks approval.

## 4. Owner/Admin authorization and evidence

- [ ] AUTHZ-01: Anonymous/session-revoked/restricted accounts denied under existing Auth semantics; normal Passenger/Owner/Driver cannot access Admin queue/detail/review or another user's files. Do not disclose target/count existence first.
- [ ] AUTHZ-02: Eligible owners read own personal/owned-vehicle documents in all role states. Every eligible APPROVED Admin can review others. Own Admin files remain readable as owner; own Admin application detail/any self review/document verification is denied. Self applications excluded before queue counts/search/page.
- [ ] AUTHZ-03: Owner identity is NIC/PASSPORT plus own registration evidence or registered-owner/company authorization. Driver additionally requires Sri Lanka-issued licence. Verify ownership/type/status/expiry/reviewer under locks. No unnecessary Owner licence, fake vehicle/company account, foreign-driver licence approval or optional-file blocker.
- [ ] AUTHZ-04: NEEDS_CORRECTION leaves role PENDING. Missing/unapproved/expired/superseded/unavailable required evidence blocks role approval. Document approval never approves a role, verifies contacts or reinstates a suspension.
- [ ] AUTHZ-05: Revoking Admin membership/session/account during detail blocks later decisions/file access; cached JWT/UI flags never authorize operations.

## 5. Decisions, versions, workspaces and reason preservation

- [ ] REVIEW-01: Real queue status/type/search/page filters match the exact DTO, sort/count and empty/error/loading semantics; no fixtures/fake applicants in normal accounts.
- [ ] REVIEW-02: Confirm PENDING Owner approval, PENDING Driver rejection and APPROVED role suspension with required applicant-visible reason/confirmation. Unknown or disallowed statuses/transitions fail without mutation.
- [ ] REVIEW-03: Concurrent reviewers with one expected version yield one committed decision and a 409 conflict; no lost update. Old-version retry never produces another transition/audit success. Lock ownership/evidence and recheck expiry/authorization.
- [ ] REVIEW-04: Reject whitespace-only/overlong reasons, approval notes, client reviewer/time, expected_version alias and extra fields. Correct allowlists/explicit nulls, one increment and server timestamps.
- [ ] REVIEW-05: After authoritative profile/role reload or sign-in, only matching APPROVED Owner/Driver appears. Passenger remains permanent/default; PENDING/REJECTED/SUSPENDED role does not grant its workspace or revoke another independently approved role.
- [ ] REVIEW-06: REJECTED resubmission durably preserves the complete old reason/actor/time/status evidence before same-row reset. Failed acknowledgement leaves old reason/status/version intact. PENDING/APPROVED/SUSPENDED duplicates remain 409; no self reinstatement.

## 6. Audit failure and crash reconciliation

- [ ] AUDIT-01: Acknowledgement requires full framed/integrity-checked append and durable flush, not logger output, cached/queued write or a mock Redis/session key. Full reasons retained separately from ordinary metadata logs.
- [ ] AUDIT-02: Inject denied permission, full disk, flush/append failure and uncertain acknowledgement before COMMIT: safe 503, no COMMIT issued, no role/document status/version/reason change.
- [ ] AUDIT-03: Kill process before intent, during torn write, after acknowledged intent/before COMMIT, during COMMIT and after commit/before terminal append. Recover using recorded full xid8 and correct database identity; never reapply the SQL decision.
- [ ] AUDIT-04: committed/aborted/in progress/NULL/unavailable outcome cases follow the exact protocol. Never classify timeout or similar current row as proof of abort/commit. Unknown or stale outcome blocks new status mutations and invokes restricted recovery.
- [ ] AUDIT-05: Test multiple workers, single coordination lock, deterministic DB lock order, idempotent terminal events, retry/response-loss and restore continuity. No contradictory terminal records, unlogged committed decision or prepared transaction.
- [ ] AUDIT-06: Reject corrupt/torn/reordered/tampered journal frames without silently overwriting/truncating history. Preserve suspect bytes, restrict repair, verify backup restore and integrity key access. Reader projection distinguishes intent from committed decision.
- [ ] AUDIT-07: Secure operator history retrieval is scoped/read-audited; public/unrelated users cannot read history. Full reason remains available after subsequent decisions/resubmission; no new history endpoint or application table.
- [ ] AUDIT-08: If COMMIT outcome is uncertain, UI receives no false success/no-change failure: unresolved outcome uses the safe 500 INTERNAL_ERROR message and reloads current detail. A committed old-version retry conflicts; a rollback is only claimed when established. Continued audit outage after commit blocks further mutations until finalization.

## 7. Controlled Admin provisioning and API consistency

- [ ] ADMIN-01: Explicit offline development command targets a named existing eligible account, preserves Passenger and uses existing ADMIN membership columns. Repeated command reports existing membership; no destructive upsert/reinstatement or default password.
- [ ] ADMIN-02: Public register/role-request payloads cannot grant ADMIN; no browser Admin-creation UI, public endpoint, second login or startup grant. Production process requires restricted operator identity, credentials, target/environment confirmation and recorded audit evidence.
- [ ] API-01: Validate 03C OpenAPI syntax/local references and 8 operation-to-matrix IDs; strict schemas/Bearer security, correct 201/200 and binary MIME/header response. No duplicate/renumbered endpoints.
- [ ] API-02: Test 401, appropriate 403, opaque 404, exact 409 codes, JSON/multipart 413/415/422, 429 Retry-After and safe 503. Error envelope is code/message/field_errors/trace_id; no supplied secret/private file/reason/provider stack leak.
- [ ] API-03: Route-aware query validation permits frozen queue/document queries but retains six Auth query rejection. PATCH CORS/JSON duplicate/size handling and multipart-only exception do not weaken registration/login/refresh/logout.
- [ ] API-04: Protected file response never redirects; no public/signed variant or token URL. Failure after headers aborts incomplete stream without appended JSON; repeated fetch reauthorizes.
- [ ] REGRESSION-01: Existing Auth/international phone, public pages, Login/Register, Passenger dashboard, sticky/navbar/animations and mobile scrolling remain intact. Run relevant PostgreSQL/Redis backend tests, frontend checks and production build after actual implementation.

## 8. Gate distinction

The technical documentation gate is APPROVED FOR BUILD once DOC checks verify the saved artifacts. All unchecked runtime items above remain mandatory implementation/enablement work. No execution result is claimed here. Unrelated future vehicle operating checklist, full financial settlement policy, general Admin dashboard, IVR, subscriptions, secondary-owner delegation, company onboarding, foreign-driver licence approval and general promotions/coupons remain outside this build scope.
