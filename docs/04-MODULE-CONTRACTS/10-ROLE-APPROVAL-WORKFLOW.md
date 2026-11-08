# Role review and approved dashboard entry - 6 November 2026

This is a scoped amendment authorized by the user's 6 November role-approval request and explicit answer **Owner Dashboard** for accounts with both Owner and Driver approval. It does not replace the missing original contract collection. The saved Final Decisions and Owner/Driver/Admin review contracts continue to govern all unchanged evidence, state, security and audit behavior.

## Application and decision

- Registration creates the existing single Passenger account. Owner and Driver applications use the existing independent user_roles rows. Passenger membership remains; approval never replaces it or creates another account.
- The applicant submits the required information/evidence through matching Owner/Driver onboarding. Existing pending applications lacking evidence use **Provide missing evidence**, without another role request. Approved applicants enter the workspace without submitting again. Rejected resubmission retains the existing audited same-record behavior.
- Only a currently authorized approved ADMIN (displayed as Super Admin) may review another applicant. Current account/session/role authority, self-review denial, expected versions, allowed transitions and durable audit remain enforced on the server.
- Preserve the frozen required-evidence rule: NIC or current Passport, plus Owner registration/authorization or a current Sri Lanka-issued Driver licence. A role decision does not automatically approve documents. Super Admin reviews those documents in the same application detail before role approval. No contact-verification or Google-linking step is added to role approval.
- The Admin detail response now includes metadata-based `approval_readiness: {ready, requirements: [{label, ready, message, action, documents: [{document_id, status, message}]}]}`. It explains missing evidence, each current document status, review/correction steps, expired/future/missing expiry metadata and trusted-verification failures; no private storage data is returned. The Approve role control is disabled while readiness is explicitly false. Reject remains available with its required applicant-visible reason.
- Readiness is guidance, not an authorization capability. Final role approval still locks and checks current records and validated private bytes. The unchanged 409 REQUIRED_EVIDENCE_NOT_VERIFIED code now explains that the Admin must review the application documents and the applicant need not reapply.

## Login and current sessions

- After successful existing password/Google authentication, fetch `/users/me` and `/users/me/roles`. Eligibility requires both current approved-role representations and an allowed account state.
- Explicit Owner/Driver entry opens the matching dashboard when approved; otherwise its matching onboarding/waiting/correction/status journey. Explicit Admin entry retains its existing guarded destination.
- General sign-in priority is existing Admin, then Owner, then Driver, then Passenger. The Owner-over-Driver choice is the user's explicit answer for dual-role accounts. No browser default-workspace preference, role selector, JWT role authority or new database field is introduced.
- Matching mounted pending onboarding continues its existing polling/focus/manual status checks and navigates after authoritative approval. General workspace focus/foreground refresh updates identity/memberships without a global redirect or interrupting an active booking. Existing token refresh and reauthentication remain unchanged.
- Applicant-visible rejection reasons appear in matching onboarding and in dashboard status notices. An approved Owner/Driver can see rejection of their independent other application. These are in-app notices derived from authorized own-role records; no outbound email/SMS notification integration is claimed.

No application table, migration, role code, approval state, document catalogue, audit-history store, authentication provider or contact-verification privilege is added.


## Own application status follow-up - 6 November 2026

- Authenticated GET `/api/v1/users/me/role-requests/{role_code}/status`, with OWNER or DRIVER only, returns `{application, approval_readiness, checked_at}` for the current account. `application` is the existing own RoleResponse or null. Readiness is returned only for PENDING and contains `{ready, requirements: [{label, ready, message}]}`. It omits document IDs, reviewer/audit actors, storage metadata and contacts. Missing applications are not created by a status read. Existing account/session restrictions apply; responses are no-store.
- Applicant guidance separates missing/current document verification, correction/invalid date requirements, and fully verified documents awaiting the final Super Admin role decision. Verified documents never imply role approval. New requirements are not introduced.
- Matching onboarding status refresh fetches the own status plus fresh `/users/me` and `/users/me/roles` with browser `cache: no-store`. It shows progress/last-check time and redirects only when both existing approved-role representations allow that workspace. Fetch failure clears displayed access and provides a retry. Duplicate concurrent status requests are prevented.
- Existing sessions remain valid through approval; permissions are read from PostgreSQL rather than embedded role claims. No client-side role grant, forced logout, new application or token bypass is introduced. Fresh sign-in also explicitly bypasses cached profile/membership reads. General login priority remains Admin, Owner, Driver, Passenger.


## Rejection/resubmission follow-up - 6 November 2026

- A rejected Owner/Driver resubmission continues to use the existing user_roles row: REJECTED -> PENDING, a later requested_at and incremented version. Existing audit commits retain the prior full rejection and decision evidence before clearing current decision fields. No extra application table or duplicate membership is introduced.
- Replacement uploads retain prior document rows/bytes/reasons and link them through superseded_document_id. The new document starts SUBMITTED with no inherited verification. Admin detail/readiness and final evidence checks consider current unreplaced documents. The latest role version is mandatory for a decision; stale pre-rejection/resubmission versions remain denied.
- The role application form reuses retained evidence only when its review status and metadata can satisfy the existing role-evidence rules. Rejected/correction, expired, future-issued and required-expiry/Driver-issuer-invalid evidence requires replacement. New role-form uploads are checked against these same existing metadata requirements before submission, using the Sri Lanka date boundary. This does not change the generic private document upload contract or grant document verification.
- Valid retained approved evidence may still be reused; role rejection does not invalidate otherwise valid shared identity evidence or the independently approved other role. Every replacement requires independent document review before it can support final role approval.
- Admin displays PENDING as Pending Review, supports explicit uncached latest-application refresh and safe focus refresh outside an active action/private preview, and clears stale decision notices on a new refresh. Backend approval failures include the exact current locked-evidence blockers. Existing security, audit and role transitions remain authoritative.


## Driver licence expiry correction - 6 November 2026

- The Driving Licence expiry is the existing documents.expiry_date field, serialized as an ISO date or null. No inferred date or new field/table is introduced. Generic archival uploads can still omit metadata under their existing contract; this never makes them eligible for Driver approval.
- Super Admin APPROVED document decisions for DRIVING_LICENCE now require current expiry, no future issue date and issuing_country LK. Invalid metadata returns 422 INVALID_DRIVING_LICENCE_EVIDENCE with safe field errors before any document verification/audit mutation. Final Driver role approval retains all existing evidence, private bytes, authority and version checks.
- A pending Driver applicant can replace a current licence with invalid metadata even when its legacy review status is APPROVED. The focused correction upload requires the printed current expiry and Sri Lanka issuer and validates the existing role metadata rules. It creates a new SUBMITTED replacement linked to retained old evidence, with no inherited verification; the same Driver application remains PENDING until independent document verification and final role approval.
- Owner evidence/UI behavior, valid NIC/shared identity, other approved roles and general login priority are unchanged. In particular, general dual Owner/Driver login still defaults to Owner; a mounted Driver journey opens Driver Dashboard after authoritative approval.
