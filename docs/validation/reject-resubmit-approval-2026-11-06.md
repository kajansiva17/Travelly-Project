# Owner/Driver reject, replace, resubmit and approve - 6 November 2026

## Completed scope and root cause

Read-only PostgreSQL inspection found one PENDING Owner role with multiple recorded changes, currently version 5. Its current NIC and vehicle registration were both SUBMITTED and future-issued. The role had successfully returned to PENDING; it was not stuck in REJECTED, using an obsolete application ID, or blocked by an older replaced document. Mandatory current-evidence eligibility correctly prevented approval.

The actual form defect was that a retained SUBMITTED/UNDER_REVIEW/APPROVED document with a future issue date could be considered reusable. Newly uploaded future-issued documents, expired/missing required expiry or unsuitable Driver-country evidence also passed the general upload-format validation and allowed resubmission, even though they could not satisfy final role approval. This made repeatedly submitting the same invalid evidence look like a repair.

Fixed the role form to identify invalid retained evidence explicitly, require a replacement, and validate new role-form metadata against the already-required approval rules before upload. Generic private upload behavior remains unchanged. Resubmission has an explicit label and explains retention of previous rejection history. Valid existing evidence can still be reused; evidence is never automatically approved.

Existing backend resubmission and replacement mechanics were correct and are preserved: the same membership moves REJECTED -> PENDING with a later request/version; prior rejection decisions are durably audited. Replacements are new SUBMITTED documents linked to retained prior evidence; old verification is not inherited. Only current replacements appear in Admin review/readiness. Final approval still requires trusted independent verification, validated bytes, current authority and matching expected version.

Admin now displays Pending Review for PENDING, reloads uncached latest detail explicitly or on focus when no review/preview is active, and clears obsolete success messages when refreshing a changed submission. Final server approval errors now contain the exact blockers from locked current evidence. Automatic matching Owner/Driver polling/refresh and approved login routing are preserved and verified end to end.

## Changed files

- Backend/app/api/routers/review_api.py: actionable exact final-approval blockers from the existing locked current-document checks.
- Backend/tests/test_approval_readiness.py: parameterized real Owner/Driver reject, replace, resubmit, re-review, same-role approve and audit/old-version/history tests.
- Frontend/src/services/applicationEvidence.js: scoped role metadata checks, retained-evidence eligibility and Sri Lanka date boundary.
- Frontend/src/features/auth/RoleApplicationForm.jsx: required replacement guidance, metadata validation, expiry labels and explicit resubmission.
- Frontend/src/features/auth/RoleOnboarding.jsx: passes the existing rejected state to the form; existing current-session redirects unchanged.
- Frontend/src/features/admin/AdminApplications.jsx: latest review refresh, Pending Review label, notice lifecycle; existing confirmation/version/security preserved.
- Frontend/src/styles/review.css: matching navy hover treatment for the new refresh control only.
- Frontend/tests/applicationEvidence.test.js: role-specific metadata and local date eligibility.
- Frontend/tests/browser/onboarding-single-submit.spec.js: invalid retained evidence/replacement/resubmission cases for both roles; existing Driver upload fixture now supplies its required expiry.
- Frontend/tests/browser/admin-review.spec.js: changed submission refresh clears stale rejection notice and retains approval gating/theme.
- Frontend/tests/owner-approval-live/owner-approval.spec.js: real Owner and Driver rejection/corrected form uploads/resubmission/Admin review/automatic existing-session dashboard/fresh-login cases.
- Scoped contract 10, NBP context and this report.

No live applicant, role, document, audit record or environment setting was changed. No new table, column, migration or application identity. Passenger access, independent roles, Google/password/OTP/contact verification, Super Admin privileges and existing dashboard operations remain governed by their unchanged controls.

## Verification

- Backend: 11 passed (100.67 seconds): complete readiness suite plus the existing audit-failure atomicity test. New resubmission cases exercise both roles, replace a previously approved identity and a rejected role-specific document, assert fresh SUBMITTED verification state, preserve old file/rejection, deny stale role versions, verify both replacements, approve the same role and inspect committed audit events retaining the previous rejection.
- Unit: 16 passed: application evidence metadata/date boundary plus generic document-upload and workspace routing regression. Generic omitted metadata remains accepted by its own upload contract; role-form checks are deliberately scoped.
- Form browser: eight unique desktop cases passed (six in the initial run plus two new resubmission cases rerun successfully). Tests prove invalid future dates cause no uploads/role submission, corrected documents upload once, resubmission happens once, and existing onboarding/error recovery/approved-no-reapply/correction/ownership behavior remains.
- Real API/browser: four passed on desktop/mobile (4.1 minutes), one Owner and one Driver per viewport. Admin rejects identity evidence and the role; applicant corrects/replaces rejected/future-dated evidence through the actual form and resubmits; Admin refreshes the same ID/version, sees Pending Review and only current valid-date submissions, previews/reviews/approves both replacements and approves the role; existing waiting session automatically opens its dashboard through authenticated polling without logout/new application; fresh general login routes correctly. Old rejected evidence remains readable with its original reason.
- Admin browser regression: 11 passed (2.6 minutes), followed by the new stale-notice test and three repeated decision regressions in the final focused run. The final focused run passed all four tests (55.0 seconds): the new notice/refresh case plus three repeated decision regressions. This gives 12 unique Admin scenarios, 24 unique browser scenarios overall.
- Production build passed: 202 modules, existing large-chunk advisory only. Working-tree whitespace check passed. Mobile pending/latest-evidence screenshot inspected.

Two initial new form assertions failed because Windows pipeline encoding changed the em dash in test expectations; corrected the test text and reran both successfully. An initial live run with the same encoding issue was interrupted and replaced by the clean four-pass run. The final focused Admin test also verifies the new refresh button keeps the navy theme on hover. These were test harness/visual verification corrections, not a relaxed approval condition.

Artifacts: `.tools/reject-resubmit-live-2026-11-06/`, `.tools/resubmission-form-2026-11-06/`, `.tools/resubmission-form-final-2026-11-06/`, `.tools/resubmission-admin-regression-2026-11-06/`, `.tools/resubmission-admin-final-2026-11-06/`. All real mutations use the existing disposable fixture server with a random isolated PostgreSQL schema/Redis namespace/private temporary roots. Cleanup is requested through its verified temporary stop file.

## Deferred scope, blockers and next dependency

No missing business decision blocks this feature. The existing live resubmission still requires corrected current documents and authorized document/final role approval; it was not repaired by fabricating dates or granting a role. The next action is to replace the future-dated evidence on that application, have Super Admin review/verify the replacements and complete final role approval. Resubmission alone never satisfies mandatory verification.

Previously reported missing historical OpenAPI contract/runtime OpenAPI issue remains outside this scope. No live Google provider interaction or external OTP delivery test was performed. The existing local API is restarted after verification to load the final-approval error change; the configured private writer remains required. The identified API was restarted; unauthenticated own-status correctly returns 401 and the Google challenge returns 200.
