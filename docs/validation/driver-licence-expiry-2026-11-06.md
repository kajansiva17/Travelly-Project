# Driver licence expiry correction - 6 November 2026

## Root cause and completed scope

Read-only inspection of the configured PostgreSQL database found one current licence belonging to a PENDING Driver application whose document status is APPROVED but expiry_date is NULL. The API is correctly representing a missing database value; this is not a date parsing/serialization mismatch.

The generic private upload contract deliberately accepts omitted metadata. The main role application form already requires valid Driver expiry, but the private correction uploader described metadata as optional and used only generic format validation. The Admin document review endpoint also allowed UNDER_REVIEW -> APPROVED without validating licence expiry/country/issue metadata, while the final role gate correctly enforced it. This allowed an approved document that could not satisfy role approval. Finally, the waiting page only offered focused correction for REJECTED/NEEDS_CORRECTION documents, leaving the legacy APPROVED/null-expiry case without an obvious repair action.

Fixed these gaps for Driver licences. New invalid licence verification is denied. The existing pending Driver journey exposes Correct driving licence for a current invalid licence regardless of an old APPROVED label. Its replacement form requires the actual printed expiry and Sri Lanka issuer, validates current/future dates and submits a new evidence record on the same application. The old record and prior review remain intact. The new file starts SUBMITTED and must be independently reviewed/approved before final Driver approval.

No live expiry, document, role or audit record was altered, and no date was guessed. Existing NIC approval and Owner access remain intact. No Owner approval behavior/UI was changed by this task; earlier interrupted Admin UI edits were preserved. Authentication, Passenger access, Google/password/OTP behavior, optimistic versions, private authorization and durable audit remain unchanged. No .env, table, column or migration change.

## Changed files

- Backend/app/api/routers/review_api.py: before approving a Driving Licence, reject missing/expired expiry, future issue date or non-LK issuer with 422 INVALID_DRIVING_LICENCE_EVIDENCE and field errors. No state/version/verification mutation occurs on denial.
- Frontend/src/components/DocumentUploadForm.jsx: Driver/licence-only role metadata validation, required expiry/country controls and accurate guidance. Owner/shared/general upload validation stays as before.
- Frontend/src/features/auth/RoleOnboarding.jsx: detect invalid current Driver licence metadata including legacy APPROVED files, display focused replacement, preserve NIC/Owner access, pause background refresh during editing, resume current status after upload and clear correction state across journey/account changes.
- Backend/tests/test_driver_expiry.py: missing/expired/foreign/future metadata verification denial and legacy APPROVED/null fixture replacement through final Driver approval, same-role/current session/token refresh and Owner/Passenger preservation.
- Backend/tests/test_admin_review.py: invalid-licence tests now expect denial at document approval; final role gate still denies invalid evidence and valid alternative identity succeeds.
- Backend/tests/test_approval_readiness.py: invalid issuer/expired fixtures remain unverified, matching the tightened document decision boundary.
- Frontend/tests/browser/onboarding-single-submit.spec.js: fixtures preserve uploaded metadata/replacement links; approved missing/expired licence repair, required fields, no invalid uploads/no new application, retained NIC and Driver navigation tests.
- Frontend/tests/owner-approval-live/owner-approval.spec.js: additional Driver-only real correction, metadata storage, verification gate, Admin UI approval and dashboard/login integration test.
- Scoped contract 10, NBP context and this report.

## Verification

- Backend: 16 passed (134.53 seconds): new Driver expiry suite, existing complete readiness suite and licence issuer/expiry/identity test. A historical approved/null record is simulated only in an isolated schema, replaced and verified. The old record remains null, the corrected expiry is stored/serialized exactly, the replacement has fresh verification and the same Driver role is approved. Existing Owner and Passenger approval remain; login/token rotation see Driver access.
- Desktop controlled browser: 10 passed (1.4 minutes), including missing/expired APPROVED licence replacement with required expiry, invalid upload denial, one replacement/no new role submission, preserved NIC and matching dashboard. Existing Owner onboarding, approval/no-reapply and resubmission regressions pass.
- Mobile controlled browser: 2 passed (15.2 seconds), missing/expired approved licence correction.
- Unit regression: 16 passed, application evidence/date boundaries, generic upload and workspace routing/Owner precedence.
- Real API/browser: final desktop/mobile run: 2 passed (2.2 minutes). Real test creates isolated applicant/application/evidence, confirms missing expiry cannot be document-approved, uploads correction through Driver UI, checks exact persisted expiry and fresh unverified replacement, verifies final role is still blocked, previews/reviews/verifies through Super Admin UI and approves Driver. Existing waiting session automatically opens Driver Dashboard; same role ID and fresh general login are checked.
- Production build passed after final journey-reset change: 202 modules; existing chunk-size advisory only. Working-tree whitespace check passed.

The first real desktop attempt timed out because Chrome failed to load local app modules with ERR_NETWORK_CHANGED; mobile passed. An escalated retry could not read the sandbox-owned temporary fixture mail directory (EPERM) and made no approval assertions. Reran in the original fixture environment; this does not weaken test assertions or production permissions. Final original-environment rerun passed both desktop and mobile (2.2 minutes).

Artifacts: `.tools/driver-expiry-browser-2026-11-06/`, `.tools/driver-expiry-mobile-2026-11-06/`, `.tools/driver-expiry-live-2026-11-06/`, `.tools/driver-expiry-live-final-2026-11-06/` and final `.tools/driver-expiry-live-verified-2026-11-06/`. Real mutations use random isolated PostgreSQL/Redis/private temporary fixtures; no live application approvals. Cleanup uses the fixture's verified temporary stop file.

## Remaining action and deferred scope

The live applicant must open the existing /driver/onboarding journey, choose Correct driving licence, enter its actual printed current expiry, upload readable replacement evidence and submit. Super Admin reviews and approves that replacement, then Approve Driver. The current old APPROVED/null-expiry licence deliberately remains ineligible until corrected. No new role application or manual logout is required.

No implementation business decision is missing. Historical OpenAPI restoration/availability and live external Google/OTP delivery remain outside this task. Keep PostgreSQL/Redis and the existing private review writer available. General dual Owner/Driver login remains Owner by the user's earlier explicit preference; the active Driver approval journey redirects to Driver Dashboard.

The identified local API was restarted with the existing startup command. Unauthenticated Driver status returns 401 and the Google challenge returns 200. No live records changed.
The existing private review writer authenticated connection check reports ready after restart.
