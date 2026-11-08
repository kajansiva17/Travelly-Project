# vehicle-availability-calendar-2026-10-28

> Recovered source text, 7 November 2026. Source: documentation collection, pages 345-347, original path `docs/validation/vehicle-availability-calendar-2026-10-28.md`. This is the saved page-text extraction, not the original Markdown. Line wrapping and table layout reflect the compilation; no policy wording has been rewritten. Later approved amendments recorded in `docs/00-READ-FIRST/Travelly_NBP_Codex_Context.md` take precedence.

~~~~text
Vehicle Availability Calendar delivery - 28 October 2026
Completed and retained boundaries
VM-D14/D15 is implemented with the existing VM-D13 occupancy policy. The dependency/business audit read the latest
Vehicle/Owner and Account/Profile reports, Final Decisions, gate 06, contracts 07/08, physical dictionary 02C, API supplement
03G and original endpoint matrix. Migration 0006 already provides all real booking/trip/departure/record foreign-key
dependencies. No unresolved business choice was found. The narrow persistence/API mapping was frozen in contract 09 before
implementation; Final Decisions, dictionary and API supplement now link that later authorization.
Owners have a seven-day calendar with a responsive overview and dated entry list, Sri Lanka times, commitment states,
independent block history, operational/verification restrictions and explicit source-check time. Own
personal/planned-maintenance/emergency blocks support create, versioned edit and reasoned withdrawal. Ordinary overlaps
surface protected references and require resolution. Historical block corrections remain allowed; no new past-date editing
prohibition was added. Emergency maintenance restricts its interval immediately, exposes affected commitments to
Owner/Admin and queues existing ADMIN_ACTION notifications to current approved Admin recipients. Notifications link to the
read-only Admin support calendar and include the interval.
Future blocks never change today's global availability or publication. Withdrawal retains the row and removes only that block
from restrictions. Other blocks, committed bookings, protected departures and accepted trips remain effective.
AWAITING_DRIVER and OWNER_ACTION_REQUIRED reservations survive Driver decline/reassignment. No booking
cancellation, reservation release, refund or price/itinerary rewrite is performed by calendar actions. No turnaround buffer was
introduced. Existing day-hire reserved hours remain authoritative.
Search, calculated offers, unpriced enquiry fallback, Passenger price acceptance, Owner commitment/reassignment, Driver
acceptance, trip start and accepted trip changes reuse the complete occupancy check. Mutation callers retain the existing
vehicle lock through commit. An ended reserved interval cannot authorize a present trip start; it needs existing itinerary resolution
without a guessed extension. Concurrency tests prove that overlapping Owner commitments and a block/commitment race
cannot both succeed.
All four occupancy sources are read in one PostgreSQL UNION snapshot, including when individual sources have no rows. A
query failure or bounded-result overflow yields AVAILABILITY_INCOMPLETE (503). Calendar read failure clears the view; a
failed availability-dependent write also disables decisions until refresh. Search never returns a partial checked set as complete.
Owner/Admin read views remain observations; commitment/start always rechecks under lock. General Browse remains vehicle
discovery rather than a dated availability promise.
Completed Auth, vehicle verification/media/content moderation, pricing snapshots and recent Account/Profile/navigation work
are preserved. Actual environment files and secrets were not changed. Local/Airport/Event numeric pricing, general
maintenance/expense records, new departure writers, protected fulfilment/replacement and financial resolution remain separate
slices.
Persistence and API changes
No migration, table, column or dependency addition. Head remains 0006_private_hire_pricing; thirteen of the planned twenty
application tables remain migrated.
Existing vehicle_records uses AVAILABILITY_BLOCK, UTC start_at/end_at, plain notes, recorded actor/time and common
version/actors. Its scoped approval_status mapping is PERSONAL/MAINTENANCE/EMERGENCY and
WITHDRAWN_PERSONAL/WITHDRAWN_MAINTENANCE/WITHDRAWN_EMERGENCY. NULL/unknown legacy blocks
remain restrictive and visibly unclassified until restricted operator review; they are never guessed or silently released. Other
record vocabularies stay unfrozen. No hard deletion or JSON calendar/audit history store.
Every block mutation uses current role/ownership authorization, vehicle/record row locks, strict expected_version on
edit/withdraw, interval validation and acknowledged pre-commit audit. The restricted writer retains full bounded before/after
snapshots and reasons. Owner access never grants raw history. Separate-process writer verification covers
create/edit/withdraw, before/after evidence, no runtime history access and fail-closed writer outage.

All paths below begin /api/v1:
Method/path
Change
GET /vehicles/{vehicle_id}/calendar
Own current approved Owner; complete bounded dated sources and safe
commitment/block DTO.
GET /admin/vehicles/{vehicle_id}/calendar
Current Admin read-only support view, including affected commitments.
POST /vehicles/{vehicle_id}/availability-blocks
Create direct effective dated block; returns affected commitments for emergency
support.
PATCH /vehicles/{vehicle_id}/availability-blocks/{block_id}
Own classified effective block; expected version and rechecked interval.
POST /vehicles/{vehicle_id}/availability-blocks/{block_id}/withdraw
Retain versioned withdrawn row and durable withdrawal reason.
GET /notifications
Adds nullable support_vehicle_id for recipient-scoped ADMIN_ACTION navigation.
Existing API error vocabulary is reused plus AVAILABILITY_INCOMPLETE, BLOCK_WITHDRAWN and
BLOCK_CLASSIFICATION_REQUIRED. Contract 09 explicitly supplements historical matrix #74's generic block payload and
adds calendar/edit/withdraw transport without renumbering the original matrix. No general /records API is claimed.
Files changed in this batch
- Backend: new app/availability.py, app/calendar_api.py; integration in app/main.py, hire_services.py,
hire_api.py.
- Frontend: new src/VehicleCalendar.jsx, calendar.css; routes/links/support notification navigation in App.jsx,
VehicleWorkspace.jsx, TripPricing.jsx.
- Verification: new Backend/tests/test_calendar.py, Frontend/tests/browser/calendar.spec.js,
Frontend/tests/calendar-live/calendar.spec.js, playwright.calendar-live.config.js; extended existing
Backend/tests/test_vehicle_writer.py. Reused existing hire/rate fixtures and isolated API server. Writer test now retains
diagnostics and allows bounded process startup on a busy Windows host.
- Documents: new contract 09, this report and outstanding deployment checklist; updated Final Decisions, dictionary 02C, API
03G, gate 06, prior vehicle report and root/frontend READMEs. Earlier unrelated uncommitted work remains retained.
Verification
The final results below distinguish combined coverage and targeted reruns from a single uninterrupted run.
Check
Result/evidence
Existing hire-pricing suite
29 passed; .tools/calendar-hire.log.
Remaining backend project gate
248 passed with one writer-startup timeout; .tools/calendar-project-gate.log. The
isolated writer rerun passed after bounded readiness/diagnostics adjustment:
.tools/calendar-writer-final.log.
Final start checks
2 passed for emergency/ended-interval enforcement;
.tools/calendar-start-final.log. Existing successful start, eligibility and
started-trip-change regression: 5 passed; .tools/calendar-start-regression.log.
These include overlapping coverage, not additional disjoint counts.
Final historical-block/validation checks
7 passed, including historical create/edit/withdraw and payload validation;
.tools/calendar-validation-final.log.
Frontend unit suite
50 passed; .tools/calendar-frontend-unit.log.
Calendar/Account/Profile/pricing browser checks
28 passed with exit 0 in the final harness run;
.tools/calendar-browser-confirmed.log. An earlier run passed the same cases but
stalled in Windows managed-webserver teardown; the justified harness rerun reused a
separately started server.
Real API calendar journeys
2 passed, desktop 1366×900 and mobile 360×740; .tools/calendar-live.log.
Production build
Passed with exit 0; .tools/calendar-build-confirmed.log. Main JS 653.75 kB, gzip
188.57 kB. Existing non-failing large-chunk warning remains.

Check
Result/evidence
Migration/schema
alembic current: 0006 head; alembic check: no new upgrade operations.
Whitespace
git diff --check passed, including final documentation.
Combined backend coverage is 280 distinct cases verified: 248 passes from the remaining-project gate plus its one
successfully rerun writer case, 29 hire cases, and the two new ended-reservation/historical-correction cases. Targeted
start/validation reruns overlap those cases and are not added again. This is combined verification, not a claim of one
uninterrupted 280-pass run.
Calendar cases cover exact touching/enclosing/partial boundaries, timezone equivalence, own/alien/current role access,
unknown legacy restrictions, validation, stale versions, independent overlapping blocks, withdrawal, emergency support,
AWAITING_DRIVER/decline reservation preservation, unchanged accepted prices, protected departures and independent
accepted trips, current emergency trip-start denial, missing-source failure, writer outage and concurrent requests.
Real browser journeys create accepted/committed bookings through normal APIs, then use the calendar UI to reject an ordinary
overlap, create emergency maintenance, inspect retained references, withdraw without releasing the booking or altering its price,
create/edit a personal block, reproduce a competing-session version conflict, refresh, withdraw and inspect Admin support
navigation. Desktop/mobile screenshots were visually inspected; no horizontal overflow. The separate controlled browser check
verifies that missing sources and failed availability writes disable actions until a complete refresh. Account/profile navigation,
contextual document views, pagination and pricing consent/snapshot regressions remain covered.
Tests use disposable PostgreSQL schemas, isolated Redis namespaces, temporary document/audit/photo roots and explicit
fixture accounts/vehicles. Routing is deterministic in browser fixtures, not a real routing-provider test. No live fleet, booking or
external account was altered. Non-failing warnings remain Starlette/httpx deprecation, Node colour-environment notice and Vite
chunk size.
Blockers, deployment and next dependency
No unresolved calendar business decision or code blocker remains after final checks. Production enablement remains subject to
the outstanding deployment checklist (outstanding-deployment-checklist.md): photo storage/ACL/durability/retention, matching
restricted audit-writer deployment and recovery, live routing provider verification, real Google/Brevo setup and official
Terms/Privacy destinations. Calendar does not complete these external tasks.
The next product dependency is the separately contracted protected departure/booking fulfilment and Admin support resolution
slice. New departure writers must take the same vehicle lock and reuse the shared occupancy guard. No automatic
cancellation/refund or unrelated pricing expansion is authorized by this calendar delivery.
~~~~
