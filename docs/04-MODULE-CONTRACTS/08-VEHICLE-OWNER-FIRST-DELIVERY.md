# 08-VEHICLE-OWNER-FIRST-DELIVERY

> Recovered source text, 7 November 2026. Source: documentation collection, pages 286-287, original path `docs/04-MODULE-CONTRACTS/08-VEHICLE-OWNER-FIRST-DELIVERY.md`. This is the saved page-text extraction, not the original Markdown. Line wrapping and table layout reflect the compilation; no policy wording has been rewritten. Later approved amendments recorded in `docs/00-READ-FIRST/Travelly_NBP_Codex_Context.md` take precedence.

~~~~text
Vehicle Management / Owner Workspace: first delivery
Authority: project-owner approvals dated 27 October 2026, Final Decisions and VM gate 06. Preserve Auth, Admin
application/private-document review and Long-distance pricing. D01 A defines this delivery. D14/D15 calendar decisions are
approved but implementation is deferred. Historical D10/D11 do not override the approved pricing contracts.
Persistence and security mapping before implementation
Use the thirteen already migrated tables from the frozen twenty-table target. No new table/column/migration is required. Vehicle
facts, globally case-insensitive unique registration, owner/default Driver, states, media, actors and version already exist. Private
evidence stays in retained documents.vehicle_id rows with user_id NULL, using the existing upload/private streaming and
correction pipeline. Never copy personal role evidence or invent a live vehicle to obtain role approval.
Existing vehicles.verified_eligibility retains Admin-only authority keys (reviewed category, conditional_documents,
authorisation_required and publication_fingerprint). A bounded owner_declaration member adds non-authoritative
registered-owner case SELF/OTHER_PERSON/COMPANY, exclusively editable as a declaration. It cannot set review authority.
Admin must review the evidence and explicitly confirm applicability; unknown applicability blocks approval. No company-account
fields or inferred licence categories.
The restricted journal already stores durable transitions. Add a narrow, owner-checked writer projection: registration_locked (any
committed first submission/review, plus current non-DRAFT state) and latest vehicle review decision's reason/time/status only.
No full history, prior reasons, actors, raw events, private keys or arbitrary resource/history query is returned. Scope is checked
against the actual vehicle and current approved Owner/Admin in the writer as well as the HTTP boundary. Reads are audited.
Registration lock survives REJECTED-to-DRAFT and material re-review. Unavailable/corrupt/incomplete journal fails closed
rather than allowing identity edits or inventing feedback. Full history remains offline restricted tooling.
Public photo metadata/moderation fits bounded vehicles.media (maximum twelve retained entries per vehicle in this first delivery;
technical resource bound, no invented vehicle fact). Each server-created item contains UUID, EXTERIOR/INTERIOR,
moderation state, normalized variant dimensions/checksums/opaque storage keys, upload/review actors/times and latest
moderation reason. HTTP DTOs never expose keys. Clients cannot write media JSON. Rejected/removed entries and bytes
remain retained; no public hard-delete shortcut.
Photo bytes use a separately provisioned VEHICLE_PHOTO_ROOT outside the repository/webroot and disjoint from private
document/journal roots. Upload JPEG/PNG only, at most 10 MiB; isolated bounded decoder verifies content and pixel limits,
applies orientation and re-encodes metadata-free JPEG derivatives at bounded responsive widths 480/960/1600 without
enlargement. No original/EXIF/GPS/SVG is public. PENDING photos are own Owner/non-self Admin only. Admin approval
separately confirms that the image represents this vehicle and contains no visible plates, contacts, private evidence or precise
private-location information. Public reads require APPROVED photo plus current published vehicle/evidence/Owner eligibility at
every fetch; no static mount or long-lived public/signed private-document URL. Admin may reject pending photos or remove
approved misleading photos. Owner can soft-remove own photos; removing the last approved exterior unpublishes. Photo
edits/moderation do not reset vehicle verification. At least one approved genuine EXTERIOR is mandatory for publication;
INTERIOR is optional.
States and editable facts
An approved Owner creates an incomplete DRAFT with only trimmed registration (case-insensitive uniqueness, no guessed
punctuation equivalence). Initial types CAR/VAN/BUS/THREE_WHEELER. Before submission require type, make/model/year,
colour, power/applicable fuel, positive usable Passenger seats excluding Driver/crew, explicit nonnegative large/small luggage
and declared registered-owner case. Existing dictionary power/fuel constraints and storage ranges apply; no per-type seat
maxima or invented facts. Description, transmission, A/C and odometer are factual/optional. Odometer changes carry their
update time.
Submission requires current retained uploads of registration, insurance and revenue licence plus authorization for
OTHER_PERSON/COMPANY. Conditional emission/fitness/route-permit requirements remain Admin-reviewed; missing
applicable evidence can be corrected while SUBMITTED. Metadata dates/numbers are copied only when printed, never

guessed. Existing approval/current-evidence date policy remains unchanged. Approval requires all applicable verified current
evidence; unknown conditional applicability blocks it. Uploaded private evidence is not itself approval.
DRAFT -> SUBMITTED (availability PENDING_VERIFICATION); SUBMITTED -> APPROVED or explicit REJECTED.
Document NEEDS_CORRECTION leaves the vehicle SUBMITTED. Owner corrects a REJECTED vehicle through DRAFT ->
SUBMITTED, retaining feedback/history and registration lock. APPROVED -> SUSPENDED is Admin-only with reason;
suspended vehicles cannot self-reset/reinstate. No new vehicle state. Initial approved review makes operational ACTIVE unless
already retired INACTIVE, and leaves it unpublished; Owner must explicitly publish after email/evidence/photo/eligibility checks.
Type, make/model/year, power/fuel and capacities are material: unpublish, clear reviewed authority and return to DRAFT for
resubmission. Unresolved vehicle/departure/accepted-trip commitments must be resolved before material changes take effect.
Registration is Owner-immutable after first submission; Admin correction requires version/reason, the same uniqueness and
commitment guards and re-review. Valid ordinary description/colour/transmission/A/C/odometer, photos and rates do not reset
verification. No accepted booking price/itinerary/assignment is rewritten. Admin suspension immediately hides inventory and
surfaces commitments for support without cancelling them.
Owner may unpublish without releasing commitments. INACTIVE retirement unpublishes but is blocked by unresolved
commitments, including overdue committed/in-progress records; planned end alone is not resolution. No hard
delete/self-transfer. Eligible explicit ACTIVE request does not publish and cannot overwrite
BOOKED/ON_TRIP/MAINTENANCE/SUSPENDED workflow states. Initial approval respects a prior inactive retirement;
renewed approval preserves operational availability. Dated personal/maintenance blocks, emergency calendar controls and
audited withdrawal/edit are deferred, not disguised as completed calendar features.
Preferred Driver is optional existing default_driver_user_id. Exact public-reference lookup returns only eligible reference/display
name and checked suitability for an explicitly selected approved service/current vehicle category. No directory search,
phone/contact/private licence or employment/network relationship. Setting/clearing the preference is audited/versioned and
never assigns a trip or reserves a Driver. Actual assignment/start retains current reviewed matrix, Driver acceptance,
expiry/suspension and conflict rechecks.
Bounded Admin queue/detail excludes self vehicles before counts. Decisions/corrections/moderation require current Admin, no
self-review, expected version and durable audit. Owner sees only own latest actionable review reason/time, plus own current
documents and photo feedback. Public detail/browse/search allowlists exclude plate, contacts, private files, raw storage keys
and precise location. Existing Long-distance service/rate workflow is linked, preserving explicit pricing_scope;
Local/Airport/Event gain no formula.
Delivery acceptance
Resolved public-text decision: the project owner explicitly approved separate Admin content approval. Ordinary description edits
do not reset vehicle verification. Current proposed text remains in vehicles.description; existing
verified_eligibility.description_review stores PENDING/APPROVED/REJECTED/REMOVED/WITHDRAWN state, last approved
text, reviewer/time and latest correction reason. Only last approved text is public; a newer proposal does not overwrite it before
approval. Clearing a description withdraws public text immediately. Admin REMOVED withdraws the currently public text even
while a newer proposal is pending; rejecting a newer proposal retains the previously approved text. A material change invalidates
the prior text projection with other eligibility authority. Description is optional and pending text never blocks otherwise eligible
publication. Non-self Admin explicitly confirms no plates/contacts/precise private location, with expected version and durable
audit. This bounded existing-JSONB refinement adds no table or migration. No other public free-text approval policy is inferred.
Verify own/alien/suspended-role access, stale versions, duplicate registration races, incomplete drafts/submission,
registered-owner cases, correction/resubmission, registration locking, material-change commitment guards, ordinary edits, photo
validation/privacy/moderation/public gating, feedback projection and separate-writer denial of full history,
publication/retirement/preference and pricing preservation. Exercise actual API desktop/mobile Owner/Admin journeys with
isolated PostgreSQL/Redis/files. Check migrations/schema and frontend build. No live sample fleet is inserted. Storage/OS
identity/backup durability remain deployment checks, not new business policy.
~~~~
