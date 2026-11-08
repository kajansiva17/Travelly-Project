# Owner approval readiness - 6 November 2026

## Completed scope and exact cause

The supplied application has NIC and VEHICLE_REGISTRATION in SUBMITTED status. These do not satisfy the frozen requirement for independently verified, APPROVED, current evidence. Approve Owner is intentionally disabled; Reject Owner remains available because rejection does not require approved evidence. The existing API and reload path correctly enforce this distinction. The defect addressed here was vague guidance and a confirmation panel below the evidence that could be missed after choosing Start review.

The required sequence is: View private document, Start review, Review confirmation, Confirm decision; then Approve the reviewed document with explicit confirmation. Repeat for identity and ownership evidence. The same application's Approve Owner becomes active after both requirements are met. Final role approval still locks/rechecks authority, version, metadata and verified private bytes, and commits the existing audited role transition.

Implemented status-specific diagnostics for each submitted document, UNDER_REVIEW, rejected/correction evidence, expired documents, future issue dates, missing required expiry, unsupported Driver licence issuer and missing independent verification. Missing evidence explicitly directs upload to the existing application. Added direct evidence links, an accessible explanation beside disabled approval and automatic focus/scroll to the decision confirmation. No document or role is automatically approved.

Preserved authentication, Google independence, Passenger membership, same-account Owner role, existing owner workspace access, review authorization/no self-review, optimistic versions, audit/security requirements and unrelated worktree changes. No live applicant or document was changed; no migration/table or environment change.

## Changed files

- Backend/app/api/routers/review_api.py: additive safe readiness diagnostics; final approval/security gates unchanged.
- Backend/tests/test_approval_readiness.py: full real Owner transitions/access/refresh/rejection plus diagnostic edge cases.
- Frontend/src/features/admin/AdminApplications.jsx: actionable checklist, evidence anchors, disabled explanation, confirmation focus.
- Frontend/src/styles/review.css: scoped link/anchor/focus positioning.
- Frontend/tests/owner-approval-live/owner-approval.spec.js and Frontend/playwright.owner-approval-live.config.js: real HTTP/browser Owner approval and rejection on desktop/mobile.
- docs/04-MODULE-CONTRACTS/10-ROLE-APPROVAL-WORKFLOW.md, this report and NBP context.

## Verification

- Readiness/Owner backend tests: 5 passed, 32.51 seconds. Actual isolated PostgreSQL/Redis/private-document fixture. SUBMITTED cannot be directly approved or used to approve a role. Tests cover both document reviews, persisted same role and approving Admin, current session access, fresh login/token rotation, denied unapproved access, no duplicate role request, rejection reason, invalid metadata.
- Existing Admin backend suite: 26 passed, 1 failed (146.76 seconds). Failure is FileNotFoundError for the already absent docs/03-API/03C-TRAVELLY-ADMIN-REVIEW-OPENAPI.json in test_controlled_admin_revocation_and_live_openapi_contract; preceding revocation assertions passed. No historical contract was recreated or weakened.
- Real browser + real API: 2 desktop and 2 mobile tests passed (45.2/29.9 seconds). Tests create new isolated applicants, submit real PNG evidence through the API, preview both files in Admin UI, confirm every review transition, verify approval disabled until both documents approved, approve Owner through UI, verify existing applicant session refresh and fresh general login reach Owner Dashboard without reapplying. Real rejection through UI verifies required reason and applicant-visible dashboard notification; unapproved Owner API remains denied.
- Login/current-session/Driver/Admin regression browser fixtures: 11 passed, 38.7 seconds.
- Review rules/workspace routing unit tests: 7 passed.
- Production build passed (201 modules), existing chunk-size advisory only. Working-tree whitespace check passed. Desktop/mobile screenshots inspected.
- Initial live browser attempt used the Frontend .env API URL instead of the isolated API; browser fetches failed. Restarted only test Vite with VITE_API_URL=/ and TRAVELLY_API_TARGET=http://127.0.0.1:8002, then reran successfully. Production .env untouched.
- Identified local API restarted with its existing command to load the code. Authentication challenge returns 200; existing private audit writer authenticated handshake reports ready.
- Separate /openapi.json availability probe returned an internal error, outside the tested Owner review endpoints. Its cause was not investigated or claimed fixed in this bounded task.

## Reproduction and artifacts

Use Backend/scripts/serve_pricing_test.py with TRAVELLY_PRICING_FIXTURE_PATH pointing to .tools/owner-approval-browser-fixture.json; this existing disposable server creates a random test schema, Redis prefix and temporary private roots. Start test Vite on 5182 with TRAVELLY_API_TARGET=http://127.0.0.1:8002 and VITE_API_URL=/, then run npx.cmd playwright test --config playwright.owner-approval-live.config.js. The fixture is required and must belong to this disposable process. Stop via its fixture stop_file so the random schema/Redis namespace are cleaned up.

Desktop screenshots: Frontend/test-results/owner-approval-live/. Mobile screenshots: .tools/owner-approval-mobile-2026-11-06/. Routing regression: .tools/owner-approval-routing-2026-11-06/.

## Deferred scope, blockers and next dependency

Owner approval implementation is complete with no blocking business decision. The real application still needs the Super Admin to inspect and approve both submitted documents before approving Owner. Tests never approve live private evidence. Keep PostgreSQL, Redis and the existing private review writer running. Historical OpenAPI-file restoration and the separate OpenAPI availability error remain outside this feature.
