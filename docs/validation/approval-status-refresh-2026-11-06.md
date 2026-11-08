# Owner and Driver approval status refresh - 6 November 2026

## Completed scope and diagnosis

Read-only inspection of the configured local PostgreSQL database found 11 Owner and eight Driver applications, all PENDING; no saved APPROVED Owner/Driver membership or completed role approval existed. Therefore the waiting page was accurately reflecting the saved role, rather than failing to recognize an existing approved membership. The screenshot-name search matched several accounts; the evidence-bearing pending Owner records had submitted/under-review evidence with future issue dates. No private applicant identity, contact, document ID or date is reproduced here. The database aggregate rules out a saved Owner/Driver approval in this configured environment independently of name matching.

Document Start review/Approve and final Approve Owner/Driver are distinct audited decisions. One evidence-bearing Owner record had NIC UNDER_REVIEW and registration SUBMITTED, neither independently verified. Future issue dates also fail the existing final evidence eligibility check. Clicking Refresh cannot grant access to these records. No live approval, date correction, applicant record or role was fabricated or changed during diagnosis.

The user-facing defect was generic waiting text that did not explain the actual remaining requirements or distinguish completed document reviews from final role approval. Existing own-role reads already queried PostgreSQL, response middleware used no-store, and server permissions read current saved roles rather than token role claims. Preserved that authority while making browser refresh explicitly bypass cache, visible and testable.

## Exact changes and files

- Backend/app/api/routers/review_api.py: new authenticated own-account OWNER/DRIVER status GET using the existing role row and evidence eligibility helpers. Returns own RoleResponse, pending readiness and checked_at. Safe applicant-specific requirements explain missing evidence, waiting document verification/correction, expired/future/missing expiry/Driver issuer conditions, or verified documents awaiting final role approval. No Admin audit actors, contacts, storage metadata or document IDs are added to this response.
- Frontend/src/features/auth/RoleOnboarding.jsx: manual/poll/focus refresh fetches latest own status, current profile and memberships with cache:no-store. Shows actual pending requirements, explicit document-vs-role distinction and Sri Lanka last-check time. Reactive refreshing state disables the button visibly; concurrent checks are prevented. Failures clear old access and allow retry. Existing matching dashboard redirect remains guarded by both current approved-role representations. Pending applicants never submit another application as part of a refresh.
- Frontend/src/features/auth/AuthPage.jsx: fresh login destination reads profile/membership with cache:no-store, preserving Admin/Owner/Driver/Passenger priority, explicit journey intent and all authentication mechanisms.
- Backend/tests/test_approval_readiness.py: added parameterized Owner/Driver fresh own-status, no cross-account disclosure, no-cache response, verified-documents-still-PENDING, same-role APPROVED visibility and metadata-blocker tests.
- Frontend/tests/owner-approval-live/owner-approval.spec.js: expanded real integration flow to Driver as well as Owner. Explicit waiting-session manual refresh is tested with polling disabled, including document-ready-before-role-approved state and actual fetch cache options. Fresh general login and same-row role persistence are checked for both.
- Frontend/tests/browser/role-approval-workflow.spec.js: controlled pending requirements/role distinction, successful refresh and failed-refresh retry tests, preserving existing route/session checks.
- Module contract 10, NBP context and this report.

No new table, migration, role, persisted credential/workspace preference, environment edit or security bypass. Passenger membership, Google/password/email/OTP authentication, independent roles, Super Admin authority and durable private evidence/audit requirements remain.

## Tests and deployment

- Backend readiness/status suite: 8 passed, 53.84 seconds. Real isolated PostgreSQL schema, Redis prefix, private document storage and audit fixture.
- Real browser/API: 6 passed, 3.7 minutes, desktop and mobile. Both Owner and Driver cover real evidence upload, Admin file preview, document review, readiness still pending until final role decision, Admin role approval saved, explicit applicant refresh with cache:no-store, existing session matching-dashboard access, fresh general login and same role ID. Owner rejection/reason/denied unapproved access also passes in each viewport.
- Controlled browser regression: 12 passed (2.0 minutes), then one new failed-status-refresh test passed (6.4 seconds including setup). Total 13, covering saved pending blockers, final-role distinction, login priorities, focus refresh, rejection reasons and fail-closed retry.
- Review/workspace unit tests: 7 passed.
- Production build passed after final frontend change (201 modules; existing chunk-size advisory only). Working-tree whitespace check passed.
- Local API restarted with its existing identified command to load the endpoint. Live status route correctly returns 401 without authentication; Google challenge returns 200; the existing private review writer authenticated handshake reports ready. No live records changed.

Artifacts: `.tools/approval-status-live-2026-11-06/`, `.tools/approval-status-regression-2026-11-06/`, `.tools/approval-status-failure-2026-11-06/`. The disposable API used existing Backend/scripts/serve_pricing_test.py with its isolated fixture path; Vite on 5182 used VITE_API_URL=/ and TRAVELLY_API_TARGET=http://127.0.0.1:8002. No production .env change. Test API cleanup uses its verified temporary stop file, dropping only its random test schema/Redis namespace.

## Deferred scope, blockers and next dependency

Implementation is complete with no missing business decision. Current real applicants remain PENDING until their future-dated/unverified/missing evidence is corrected and verified, then Super Admin completes final role approval. For future issue dates, Super Admin should request document correction through the existing review workflow; the applicant supplies corrected evidence on that application. Never submit a new application merely to refresh permissions.

Historical OpenAPI-file restoration and the separate previously reported OpenAPI availability issue remain outside this task; that historical test was not rerun or claimed fixed. No external Google provider or OTP delivery integration was exercised by this bounded status change. The next dependency for the supplied live account is valid evidence and the authorized final role decision, not another login or application.
