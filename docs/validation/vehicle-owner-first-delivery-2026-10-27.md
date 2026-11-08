# vehicle-owner-first-delivery-2026-10-27

> Recovered source text, 7 November 2026. Source: documentation collection, pages 348-350, original path `docs/validation/vehicle-owner-first-delivery-2026-10-27.md`. This is the saved page-text extraction, not the original Markdown. Line wrapping and table layout reflect the compilation; no policy wording has been rewritten. Later approved amendments recorded in `docs/00-READ-FIRST/Travelly_NBP_Codex_Context.md` take precedence.

~~~~text
Vehicle Management / Owner Workspace first delivery - 27
October 2026
Outcome and authority
The first delivery in VM-D01 A is implemented. Completed Auth, Admin application/private-document review and Long-distance
pricing remain in place. The remaining approvals D01 A, D03 A, D04 A, D07 A, D08 A, D09 A, D14 A, D15 A, D16 A, D18 A and
D19 A are recorded in contract 06 and Final Decisions. Previously accepted D02 B, D05 A, D06 A, D12 A, D13 A, amended D17
and D20 A remain binding. Accepted Long-distance decisions supersede historical D10/D11 proposals.
The subsequent explicit owner decision for separate Admin description content approval is recorded and implemented. Ordinary
description edits preserve vehicle verification. Only approved text becomes public; a newer proposal retains the previous
approved text until reviewed. Clearing the description or Admin removal withdraws public text. Pending optional content does not
block publication.
D14/D15 dated maintenance/personal blocks and audited calendar edits/withdrawal are deferred, despite their approved policy.
No calendar completion, hard deletion, Owner self-transfer, standing Driver network or automatic assignment is claimed.
Local/Airport/Event numeric pricing remains outside this delivery; these services do not inherit Long-distance formulas.
Contracts, persistence and API
Normative documents: Final Decisions, gate 06, delivery contract 08, physical dictionary 02C and API supplement 03G. Contract
07 now links the later fleet approvals while preserving its earlier decision history.
No new migration, application table or column was needed. Current migration head remains 0006_private_hire_pricing;
thirteen of the existing twenty planned application tables are migrated. Existing vehicle factual/state/actor/version/default-Driver
columns are used. Bounded vehicles.media holds server-generated photo metadata;
vehicles.verified_eligibility.owner_declaration holds the non-authoritative registered-owner case, and
description_review holds separate current moderated content. Admin eligibility authority stays distinct. Private evidence
remains in retained vehicle-scoped document rows. Durable history remains in the protected journal, not JSON history or a
twenty-first table.
API supplement 03G defines vehicle create/list/detail/partial edit/submission, explicit publication/availability, exact minimal
eligible-Driver lookup/preference, bounded non-self Admin queue/detail/review/registration correction, photo
upload/read/removal/moderation, independent description moderation and public allowlisted vehicle detail. Existing
private-document endpoints and structured service/rate endpoints are reused. Owner list retains its prior pricing-picker default of
100; the fleet UI explicitly pages 20.
Vehicle registration remains globally case-insensitive unique. First submission permanently locks Owner registration edits,
including after rejection/correction. Admin correction requires reason/version and re-review. Required actual submission facts
cover CAR/VAN/BUS/THREE_WHEELER, usable seats excluding Driver/crew and explicit nonnegative luggage; unknown draft
facts stay absent. Power/fuel, storage ranges, year and odometer precision are validated. No sample live fleet or invented facts
were added.
Material identity/capacity/declaration edits require re-review and cannot proceed with unresolved commitments, including
overdue in-progress records. Ordinary valid description, colour, transmission, A/C, odometer, photo and rate edits preserve
verification. Inactive retirement and explicit activation respect controlled operational states. Initial approval respects prior inactive
retirement; renewed approval preserves operational availability. Accepted booking snapshots and reservations are retained; no
vehicle action silently cancels a booking.
Media, audit and privacy
Public photos use a separately provisioned optional VEHICLE_PHOTO_ROOT, outside repository/webroot and disjoint from
document/journal storage. JPEG/PNG uploads are limited to 10 MiB and processed by a bounded isolated decoder. Orientation
is applied and embedded metadata discarded through fresh JPEG encoding. Responsive variants are bounded to 480/960/1600

widths without enlargement. No original, EXIF/GPS or private-document URL is public. At least one Admin-approved genuine
EXTERIOR image is required for publication; INTERIOR is optional.
Admin explicitly confirms genuine vehicle content and absence of visible plates, contacts/private evidence/precise private
location. Removing the last approved exterior unpublishes without resetting verification. Every public image fetch rechecks
current publication/eligibility. Photo references use opaque server keys, safe response DTOs and guarded endpoints rather than
a static directory mount. Rejected/removed metadata and bytes remain retained. The technical bound is twelve retained entries
per vehicle; retained/orphan media maintenance is an operator responsibility, with no new deletion API.
The separate audit writer exposes only an identity-checked committed projection for registration lock and latest vehicle decision
reason/time/status. It does not expose raw history or a general history RPC. Reads are audited; missing/corrupt/unavailable
dependencies fail closed. Changed-field before/after audit evidence, including keyed media changes, is bounded before append.
Oversized frames are rejected without corrupting the journal. Durable intent precedes database commit. Photo derivatives are
durably placed before references; uncertain outcomes retain inaccessible bytes for restricted reconciliation.
Public detail/Browse/search omit plates, contacts, private evidence, raw storage keys and precise private location. Owner
feedback is scoped to their own latest actionable vehicle decision. Full history stays restricted. Preferred-Driver lookup returns an
eligible public reference/display name only; saving a preference creates no assignment/trip/reservation. Actual assignment/start
retains reviewed compatibility, current licence/role/expiry checks and Driver acceptance.
Files changed for this delivery
- Backend implementation: app/vehicle_schemas.py, vehicle_rules.py, vehicle_api.py, vehicle_media.py,
normalize_vehicle_photo.py; integration in main.py, config.py, review_operator.py, review_audit.py,
review_writer.py, review_models.py, hire_api.py, hire_services.py, rate_api.py; configuration example and
operator documentation.
- Frontend: VehicleWorkspace.jsx, VehiclePhoto.jsx, vehicleValidation.js, vehicles.css;
route/navigation/API/rate/Browse integration in App.jsx, PassengerDashboard.jsx, api.js, OwnerRates.jsx,
TripPricing.jsx; frontend/root README updates.
- Tests/tooling: Backend/tests/test_vehicles.py, test_vehicle_writer.py, isolated conftest.py and existing pricing
fixtures; Backend/scripts/serve_pricing_test.py; frontend vehicle validation tests, live browser config and vehicle journey
test.
- Documents: Final Decisions, contracts 06/07/08, dictionary 02C, API supplement 03G and this report. Existing unrelated dirty
work is preserved. Actual environment configuration is unchanged.
Verification results
 Check
Result
Full backend suite
255 passed; log .tools/vehicle-final-full.log.
Final vehicle and separate-writer release checks after audit/commitment
refinements
21 passed; log .tools/vehicle-release-checks.log. This is a targeted
rerun, not an additional disjoint test count.
Frontend unit tests
50 passed, including missing/explicit-zero facts, invalid quantities and photo
type/size boundaries.
Existing Auth/Google and pricing browser regression
30 passed across desktop/mobile;
.tools/vehicle-frontend-regression.log.
Real API Owner/Admin vehicle journey including description moderation
2 passed, desktop 1366×900 and mobile 360×740;
.tools/vehicle-content-verified.log.
Real API existing Long-distance pricing journey
2 passed, desktop/mobile; .tools/vehicle-pricing-live.log.
Production build
Passed, 168 modules; main JS approximately 641.39 kB (185.23 kB gzip).
Non-failing existing large-chunk warning remains.
Migration/schema
alembic current: 0006 head; alembic check: no new upgrade
operations. No first-delivery migration.
Whitespace verification
git diff --check passed.

Backend cases include own/alien/current-role authorization, no self-review, duplicate registration, stale versions, missing
submission facts, all four initial types, SELF/OTHER_PERSON/COMPANY evidence, rejection/correction/resubmission and
permanent registration lock, suspension, Admin registration correction, current/expired evidence, unavailable durable audit,
image validation/normalization/moderation/revocation, public privacy gates, ordinary versus material edits, accepted-price
preservation, retirement/overdue commitments, minimal preferred-Driver lookup and no trip creation, pagination compatibility,
multibyte audit bounds, and independent description approval/rejection/removal/withdrawal. Separate-process writer tests deny
arbitrary history/other-owner projections and fail closed on outage.
Real browser journeys create incomplete drafts, enter factual COMPANY-case data, upload all four required/case-specific
documents, request and resolve an insurance correction, reject with Owner feedback, correct/resubmit while registration stays
locked, approve vehicle applicability, moderate an exterior photo, explicitly publish, propose/approve a description without
resetting verification, check anonymous privacy/image loading and retire. Mobile gallery/public screenshots were visually
inspected; layout has no horizontal overflow. The test uncovered and fixed a stale-refresh action race and duplicate sibling React
keys that retained old forms. The final journey asserts a single factual form after refresh/resubmission.
Existing pricing browser journeys verify reusable rates, fresh Passenger pricing and acceptance, Owner commitment, accepted
changed-stop pricing and preserved snapshots. This delivery does not claim real external routing-provider validation.
Tests use disposable PostgreSQL schemas, isolated Redis namespaces and temporary private storage/journal/photo roots.
Accounts, registrations and the solid-colour image are explicitly isolated test fixtures, not invented live vehicles or evidence of a
real vehicle photograph. The helper cleans its schema/Redis scope on graceful shutdown. Screenshots/logs/build output are
ignored verification artifacts.
Non-failing warnings: existing Starlette/httpx TestClient deprecation, Node colour-environment notice and Vite bundle-size
warning. No unresolved business decision or first-delivery code blocker remains.
Next dependency
Before deployment, provision the separate photo root with the documented OS identities/ACLs, durability/backup and
retained-media maintenance, deploy the matching restricted audit writer and web code together, and verify deployment storage
access. Existing environment files were not changed or secrets provisioned. The earlier Long-distance live routing provider still
needs its configured provider/key and a real integration check. The next approved product slice is D14/D15 calendar
implementation; it remains separate from this completed first delivery.
Follow-on delivery
The 28 October calendar slice is reported separately in Vehicle Availability Calendar
(vehicle-availability-calendar-2026-10-28.md). It supersedes the calendar deferral above only; this report's completed
fleet/verification/media behavior and deployment obligations remain retained.
~~~~
