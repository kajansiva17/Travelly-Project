# Role approval workflow recovery - 6 November 2026

## Findings and completed scope

The supplied screenshot shows the general Account/Profile document uploader and authentication settings, rather than the Super Admin application-detail review route. These authentication/Google components are not mounted in matching Owner/Driver onboarding or Admin application review.

The configured private audit writer was stopped/unavailable. Its absence prevents private uploads and privileged review decisions, returning REVIEW_DEPENDENCY_UNAVAILABLE. Restarted that existing writer with the original configuration and persistent audit infrastructure using an approved hidden process. A protected handshake could not complete in the sandbox; outside-sandbox authenticated checks succeeded after recovery and again after API restart. No audit-history content, keys, private paths or credentials were printed.

Read-only aggregate queries against the local database found **18 pending Owner/Driver applications and zero saved document records**. Failed upload attempts therefore had not created reviewable evidence. The existing evidence guard correctly blocks role approval in this state. No document, approval, account, role or private record was fabricated or changed in the live database.

Authority reviewed: NBP context, relevant account/profile delivery, saved V2 onboarding delivery (compilation pages 338-339), local Admin dependency report (292), Final Decisions (8), Owner/Driver module (241-242), Admin review module (249-252) and API contract (220-221). Existing users/user_roles/documents model/DTO fields remain unchanged. The frozen review contract explicitly says a role decision does not automatically approve underlying documents; that rule is preserved.

Implemented:

- Admin application detail now returns a safe required-evidence readiness checklist. The UI explains whether identity and role-specific evidence are submitted/reviewed/current, and disables Approve only when the server explicitly reports unmet requirements. Reject remains available with the full applicant-visible reason and explicit confirmation.
- Final approval still locks/rechecks the existing account, current ADMIN authorization, version, evidence metadata and validated private bytes, and durably audits the existing transition. The same REQUIRED_EVIDENCE_NOT_VERIFIED code now gives actionable guidance without asking the applicant to reapply.
- Application decisions and document decisions have distinct, clear confirmation messages. Relevant review actions stay within Admin application detail; no Google-linking/account-security form is introduced there.
- General password/Google sign-in uses fresh authenticated profile and own-role reads. Existing approved Admin precedence remains; otherwise approved Owner opens Owner Dashboard, then approved Driver opens Driver Dashboard, otherwise Passenger. **The user explicitly chose Owner Dashboard for dual Owner/Driver approval.** Explicit Owner/Driver entries retain their matching destination, or their matching onboarding/status when not approved.
- Verification continuation and Google completion use that same authoritative routing decision. Neither grants a role or links accounts based on email.
- Existing matching waiting-page polling/focus/manual approval progression remains. Workspace focus/foreground refresh securely updates current identity/memberships without a global redirect, so an unrelated active booking stays in place. Existing API access and token-refresh checks remain authoritative.
- Own application status/rejection reason is visible on Passenger Dashboard; Owner/Driver dashboard notices show rejected independent applications. Links resume the existing application rather than creating a new one. Notifications here are in-app views of existing own-role records, not a new email/SMS integration.
- Existing pending applications with no evidence use **Provide missing evidence**. Existing approved applications never submit again. Rejected resubmission still uses the same role row with retained audit history.
- Restarted only the identified local API using its existing startup command to load the review changes. Live API/frontend Google challenge returns 200, and the private writer handshake remains healthy.

No `.env` edit, new table, column, migration, role code, approval state, security bypass, saved workspace preference or persisted browser credential was introduced. Passenger membership, independent roles, private file authorization, existing dashboard features and earlier worktree changes are preserved.

## Changed files

- `Backend/app/api/routers/review_api.py` - share existing evidence-eligibility checks with read-only Admin readiness; clearer existing approval error.
- `Backend/tests/test_approval_readiness.py` - real database/document review, same-record approval, role access and invalid-evidence coverage.
- `Frontend/src/routes/workspaceRoutes.js` - authoritative login destination and approved priority.
- `Frontend/src/features/auth/AuthPage.jsx` and `AuthFlows.jsx` - apply that destination after authentication/verification/completion.
- `Frontend/src/components/WorkspaceShell.jsx` - quiet authenticated focus/foreground access refresh.
- `Frontend/src/features/admin/AdminApplications.jsx` - checklist, enabled/disabled decisions and specific feedback.
- `Frontend/src/features/auth/RoleApplicationForm.jsx` - explain one evidence submission with application review.
- `Frontend/src/components/ApplicationStatusNotices.jsx`, `RoleDashboards.jsx`, `Frontend/src/features/passenger/PassengerDashboard.jsx` - own in-app status/rejection notices.
- `Frontend/src/styles/review.css` - bounded checklist/status styling.
- `Frontend/tests/workspaceRoutes.test.js`, `Frontend/tests/browser/role-approval-workflow.spec.js`, `admin-review.spec.js`, `helpers/redesign.js` - routing, authorization, review/status/session coverage and fixtures updated for the existing approved-dashboard entry.
- NBP context, scoped module contract 10 and this report.

## Tests

- Backend: **6 passed** (49.29 seconds). New readiness tests plus existing Owner approval/Driver rejection/suspension, licence issuer/expiry/identity, queue authorization/self-exclusion and audit-failure atomicity checks. Actual isolated PostgreSQL schemas, Redis namespaces and temporary evidence/journals; no live application decisions.
- Unit: **7 passed**, workspace/login eligibility/priority/navigation and review action/payload rules.
- Desktop browser: **28 passed** (2.8 minutes), current single-submit onboarding, protected Admin review and new role-workflow tests.
- Mobile browser: **11 passed** (1.6 minutes), new role-workflow scenarios.
- Google/verification browser regression: **15 passed** (46.4 seconds), including unconfigured/retry/completion, third-party verification, email conflict/no automatic linking, explicit linking, approved/pending/correction continuations and no replacement of another signed-in identity.
- Total final browser checks: **54 passed**. Browser responses use controlled fixtures; real provider interaction was not performed.
- Production build: **passed**, 201 modules. Existing large-chunk advisory remains. Tracked touched-file whitespace check passed.
- Initial desktop run: 26 passed, one test still expected the previous generic success message. Updated that expectation to the new applicant-visible rejection confirmation and reran the complete selected desktop scope, producing the final 28-pass result above.

Artifacts are under `.tools/role-approval-final-2026-11-06/`, `.tools/role-approval-mobile-2026-11-06/` and `.tools/role-approval-auth-regression-2026-11-06/`. Existing dependency warnings remain non-failing.

## Deferred scope, blockers and next dependency

Implementation is complete. **The local pending applications still require real applicant documents.** Open the matching `/owner/onboarding` or `/driver/onboarding` journey, select Provide missing evidence, and upload the required evidence once. Super Admin then reviews those documents and approves/rejects the same application through `/admin/applications`. An approval cannot safely be granted to the currently empty evidence records.

Keep the private review writer running alongside Redis/PostgreSQL/API. Its existing startup command from Backend is `..\.venv\Scripts\python.exe -m app.services.review_writer`; no Windows boot service was installed. No live user role was approved as part of diagnosis. The wider historical profile-context regression file was not rerun or claimed fixed by this bounded task.
