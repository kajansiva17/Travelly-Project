# 03F-TRAVELLY-REUSABLE-RATE-CONTRACT

> Recovered source text, 7 November 2026. Source: documentation collection, pages 227-231, original path `docs/03-API/03F-TRAVELLY-REUSABLE-RATE-CONTRACT.md`. This is the saved page-text extraction, not the original Markdown. Line wrapping and table layout reflect the compilation; no policy wording has been rewritten. Later approved amendments recorded in `docs/00-READ-FIRST/Travelly_NBP_Codex_Context.md` take precedence.

~~~~text
Reusable rate configuration and calculation contract
Date: 27 October 2026. Authority: LD-P01-P10 and the owner's accepted LD-Q/LD-F replies in the pricing contract
(../04-MODULE-CONTRACTS/07-LONG-DISTANCE-PRICING-AND-REUSABLE-RATES.md). This freezes the scoped
reusable-rate, private-hire and operational eligibility implementation. LD-F01/LD-F02 are resolved. External routing configuration
and deployment verification remain dependencies.
Rate representation
Use planned service_types and vehicle_services. A PRIVATE_HIRE service uses existing pricing_basis DISTANCE, TIME (day
hire) or FIXED (explicit route fare); do not introduce another pricing enum. A versioned owner_terms.rate_rules collection is
authoritative for structured rates. A collection containing multiple methods uses existing OWNER_QUOTE as its scalar catalogue
marker; this never suppresses a valid structured matching calculation or stores a previous Passenger's total. Scalar legacy price
fields are null for structured rate configuration, avoiding two independent prices. No private/publish toggle.
Each rule has a UUID; label; vehicle from the containing service; operating/pickup coverage; directed route/area coverage;
one-way/return applicability; effective start/end dates; method; explicit Owner-entered components; toll/parking inclusion policy;
return-to-base terms; and automatic-change limits. Under LD-A01, ONE_WAY point-to-point fixed and distance rules may
coexist: select an applicable fixed rule first, then distance, then quote. Never add both bases. Same-priority overlapping rules
remain invalid; fixed departure windows may abut but not overlap for identical coverage. No return-journey precedence is
inferred. The full reserved interval must be covered by the effective dates. Route coverage identifies an exact ordered sequence
of server-validated locations; area coverage uses explicit bounded geometry, never a nationwide interpretation of a route name.
Owner notes are bounded text, not another pricing engine.
Required numeric fields have no fabricated defaults. Explicit zero is distinct from absent/unknown. Numeric values are finite,
nonnegative decimal strings; booleans and exponent notation are not monetary input. Currency is LKR. Rates are not totals from
a previous Passenger. One selected method supplies the base: distance base plus excess km; one day package and eligible
excesses; or fixed fare for its exact covered route. Day and distance bases are never combined.
Distance requires base charge, included km, excess-km rate and night-km surcharge. Day hire requires day charge, included
km/day, service hours/day (>0, <=24), extra-km/hour and night-km rates, plus explicitly disclosed overnight cost applicability.
Fixed route requires a fixed fare and receives no automatic night surcharge. Every method discloses free waiting minutes, hourly
waiting rate (proportional minutes, not started blocks), return-to-base applicability/amount calculation, other
included/separately-payable costs and nonnegative change limits. No automatic tax/commission, invented Driver wage or free
allowance.
Existing matrix operations and independent preview
All paths use /api/v1. Matrix #24 GET /vehicles/{vehicle_id}/services is scoped here to the authenticated current
approved Owner's own configuration, including unpublished vehicles. Public calculated prices use search, not raw rule
collections. Matrix #25 PUT at the same path requires current approved Owner ownership, expected version and one
PRIVATE_HIRE service configuration. It saves reusable rules; it does not approve a vehicle or confirm a booking. Version
mismatch is 409; alien/nonexistent private target is 404; unauthenticated is 401; disallowed role/account is 403;
malformed/negative/conflicting/incomplete configuration is 422.
Narrow preview addition: POST /vehicles/{vehicle_id}/services/preview requires the same Owner authority. It accepts
one proposed rule and explicitly Owner-entered example measurements only. Example mode NEVER creates a search offer,
quote, trusted route measurement or booking. Live quotes/searches obtain authoritative measurements from the backend routing
adapter; the browser cannot supply trusted distance, night km or eligibility. Return selected method, exact component
quantities/subtotals, final two-decimal LKR total, exclusions and example_only: true. Empty mandatory values do not become
zero.
Formula and snapshots

Follow the accepted fixed policy verbatim. Distance = base + max(0,total route km-included km)*extra km rate + all planned night
km*night rate + applicable disclosed extras. Fixed route = covered fixed fare plus explicitly disclosed permitted extras, without
automatic night surcharge. Night is 22:00-05:00 Asia/Colombo; routing uses ordered timed segments and stop durations, not a
total-distance guess. Waiting applies its free minutes first. For overlapping waiting/day overtime intervals choose the higher
amount once; disjoint intervals remain separately chargeable. Only the final total is rounded to cents (decimal half-up); do not
round per stop/component. Traffic-only delay is not a price-change trigger.
Rates/allowances have no default monetary values. Accepted bookings copy exact rate version, rule, calculation policy, trusted
itinerary and measured inputs, component breakdown and exclusions into dedicated booking snapshots; later edits cannot
rewrite those snapshots. Price acceptance and operational commitment are separate. Bookings pending another Driver after
rejection retain their committed occupancy. Any live itinerary mutation requires fresh conflict/eligibility checks and Passenger
approval of old/add/new amounts; failing limits/data/operational checks yields manual review without mutation.
The owner has approved later full-package-plus-overtime calculation and an Admin-reviewed explicit compatibility matrix;
missing entries deny operation. Provider configuration and real route-data testing are external dependencies, never replaced by
fabricated data.
Booking, quote and operation refinement
Existing private-hire creation (#42) creates REQUESTED only. New POST /bookings/{id}/quote uses the same
RateConfiguration request plus expected booking version; save reusable rates and the new quote snapshot atomically, with
trusted route recalculation. GET own booking/list responses include the allowlisted itinerary/quote. New POST
/bookings/{id}/price-acceptance requires the Passenger, expected version and current quote digest. It freezes agreed
itinerary/price/rules before Owner commitment. Existing self-drive/driver-assignment/assignment-accept/decline/start operations
retain canonical statuses and now require current accepted price, verified category compatibility and locked non-overlap checks.
New POST /bookings/{id}/changes proposes a changed ordered itinerary using the AGREED rule snapshot, not current
rates. It stores a bounded proposal with old/add/new totals and a digest. New POST /bookings/{id}/changes/accept
requires Passenger ownership, expected booking version and proposal digest. Recalculate and recheck before update; when
limits, evidence, vehicle/Driver conflicts or trustworthy measurements fail, retain the proposal as manual-review-required with no
agreed itinerary/price mutation. New POST /bookings/{id}/changes/review requires booking Owner and current Passenger
acceptance; it may confirm an over-limit feasible proposal but cannot override conflicts/eligibility. Notifications for all existing
Passenger/Owner/assigned-Driver recipients are committed in the same transaction, using planned notifications with IN_APP
channel and RECONFIRMATION type. No notification response grants operational authority.
Initial committed price and later Passenger-accepted revisions are separately preserved in booking JSON snapshots and
durable decision evidence; completed records are immutable. A declined Driver sets OWNER_ACTION_REQUIRED without
releasing committed occupancy. Proper cancellation/rejection explicitly resolves occupancy; there is no generic timeout release.
Lock user/role, vehicle and booking rows in consistent order before overlapping commitments; repeat checks at assignment
acceptance/start/change acceptance. Expected-version conflicts are 409, absence of a pending price/proposal is 409, missing
trusted routing is 503, and invalid/unsupported inputs are 422.
Physical refinements on existing tables: bookings.itinerary_snapshot, price_snapshot, pending_change JSONB objects (default
empty), accepted_quote_digest CHAR(64) nullable, vehicle_committed BOOLEAN default false; documents.verified_categories
JSONB array default empty, written only by eligible Admin review; vehicles.verified_eligibility JSONB object default empty for
Admin-confirmed evidence applicability and reviewed vehicle/routing categories. service_types.settings.licence_compatibility is a
bounded reviewed map from vehicle category to accepted licence category codes and routing profile, controlled by Admin with
durable review evidence/version. Applicant role_profile remains non-authoritative. No new table, new role, new booking state or
per-assignment Admin approval.
Vehicle publication requires approved Owner with verified email, approved vehicle and all applicable verified/current vehicle
evidence, with unknown applicability failing closed. Admin vehicle review records the conditional evidence requirements and
verified vehicle category; expiry immediately excludes public reads/search and assignment/start. Renewed evidence does not
silently republish; explicit Owner republication must set a new publication epoch bound to the current approved evidence
versions. The existing approved-vehicle database guard stays in force.
Exact transport supplement to 03B
LD-A01-A07 addendum (27 October 2026)
The addendum in pricing contract 07 section 6 supplements all accepted LD-P/LD-Q/LD-F decisions. This engine is restricted to
explicit service_types.settings.pricing_scope: LONG_DISTANCE. LOCAL, AIRPORT, EVENT, UNSPECIFIED and

missing scope cannot save or calculate new long-distance rates/offers/quotes. GET /service-types returns active
Long-distance entries only for this implemented form. Admin creation requires pricing_scope (one of those five explicit values);
PATCH /admin/service-types/{id}/pricing-scope accepts {expected_version, pricing_scope}, preserves other
settings, uses current Admin authority, optimistic concurrency and durable review evidence. There is no name/code-based
inference or default classification. Existing accepted bookings retain their snapshots and operational eligibility checks; new price
acceptance/calculation requires approved scope. Old unaccepted fixed quotes missing departure applicability must be requoted;
accepted legacy snapshots are not rewritten.
Newly saved fixed rules require departure: {kind: "ANY_TIME"} or {kind: "WEEKLY_WINDOW", weekdays: [...],
from_time: "HH:MM", until_time: "HH:MM"}. Weekdays are unique integers 0=Monday through 6=Sunday (1-7 entries).
Times are 00:00-23:59 in Asia/Colombo, with start included and end excluded. Equal times are invalid; crossing-midnight
windows run from the selected start weekday into the next morning. ANY_TIME contains no hidden weekday/time fields.
Departure applicability is not a billing convention or a night surcharge. Other pricing methods must not carry it. Reverse one-way
coverage requires a separate explicitly entered reversed ordered route, with equal or different Owner-entered fare. Do not infer
reverse coverage from the ONE_WAY/RETURN flag. Duration does not switch to Day hire.
Normal stops use the exact ordered route; free_wait_minutes is disclosed as Included waiting for fixed fares, with
waiting_hour_rate for explicitly priced excess waiting. Fixed calculation never adds the distance fare or automatic night
surcharge. The Passenger sees itinerary/stops/planned waiting, included waiting, price breakdown and separately payable costs
before acceptance. Charges beyond the fare inclusions require this acceptance or a later accepted change; no silent actual-wait
charge is introduced.
DEPARTURE_TIME_CHANGE extends the change-reason DTO for the current owning approved Owner of an unstarted
CONFIRMED fixed-fare booking. The proposed pickup must be in the future and only departure changes: method, direction,
ordered places/waiting/rest and service durations stay agreed. Create CHANGE_REQUEST_UNPRICED with
old_departure/new_departure and old total; no schedule/price mutation. The same reusable quote form supplies a new
applicable route quote. Priced CHANGE includes those times, old/add/new amounts and manual review. Passenger
sees/accepts the exact new time and quote digest; Owner confirmation then rechecks both new start/end, evidence, accepted
Driver and vehicle/Driver conflicts before atomically updating booking/trip intervals. No approval overrides a conflict; original
snapshot remains immutable. Notifications include the material change. A started booking cannot be rescheduled this way.
Existing reduced-price financial-adjustment restrictions remain: show the proposed decrease but do not invent a
refund/settlement workflow.
Local maximum-reservation, verified-actual-waiting, accepted extension and Local-versus-Day comparison behavior is recorded
for its future numeric contract. No Local/Airport/Event formula or comparison is implemented here. Existing full first-package Day
reservation and explicit Passenger service choice are preserved.
The historical XLSX is retained without renumbering its operations. This scoped supplement governs the affected operations and
additions; it does not claim to implement unrelated matrix rows. Runtime /openapi.json describes the strict DTOs. Unknown
JSON fields, unsupported query parameters and duplicate keys are rejected. Pricing bodies are bounded to 64 KiB; other JSON
bodies to 8 KiB. All mutations use JSON. Decimal quantities/rates are explicit strings of 1-10 integer digits and up to 10 fractional
digits; no negatives, separators, exponent notation or boolean coercion. Version fields are strict integers.
Operation
Authority and exact body/query
GET /locations?q=...
Public; 3-150-character query; server geocoding returns label, latitude, longitude and
signed coordinate proof, with attribution. Rate limited.
GET /service-types
Public; active explicitly classified LONG_DISTANCE PRIVATE_HIRE entries, safe
IDs/names/codes/pricing_scope only.
GET /owners/me/vehicles
Current approved Owner; own IDs, labels, verification/publication state; bounded list.
GET /vehicles
Public eligible inventory; optional owner_reference; public vehicle/Owner references
and safe display name, no private registration/contact/documents.
POST /search/vehicles
Public ordered-itinerary search addition alongside historical #26 GET. Body:
service_type_id, itinerary, passenger_count, large_luggage_count,
small_luggage_count. Returns freshly calculated eligible available matches only.
Historical GET transport is not implemented in this slice.
PUT /vehicles/{id}/services
Current owning approved Owner; RateConfiguration below. Expected version 0
creates; otherwise compare-and-swap.

Operation
Authority and exact body/query
POST /vehicles/{id}/services/preview
Same Owner; {rule, example}. Example quantities include distance_km, night_km,
waiting_minutes, service_hours, overnight_stays and optional waiting_periods.
POST /bookings/private-hires
Current Passenger under existing Auth contact policy; search body plus vehicle_id
and 16-80-character idempotency_key. 201 REQUESTED, possibly an unpriced
enquiry; never reserves. Existing legacy Auth access is preserved; no new Passenger
email gate.
GET /bookings, /bookings/{id}
Owning Passenger/Owner or assigned Driver only; allowlisted snapshots/current trip.
POST /bookings/{id}/quote
Current owning approved Owner; {expected_version, rates:
RateConfiguration}. Requires enabled reusable rules and one exact matching
ROUTE rule. Saves rules and quote atomically.
POST /bookings/{id}/price-acceptance
Owning Passenger; {expected_version, digest} for exact current quote. Does not
reserve or promise confirmation.
POST /bookings/{id}/self-drive
Owning approved Owner who is also an eligible Driver; {expected_version}.
POST /bookings/{id}/driver-assignments
Owning approved Owner; {expected_version, driver_reference}; exact public
Driver reference, never private phone lookup.
POST /trips/{id}/assignment-accept,
/assignment-decline
Assigned Driver; {expected_version} uses TRIP version. Decline retains vehicle
commitment.
POST /trips/{id}/start
Accepted assigned eligible Driver, after scheduled pickup; {expected_version,
start_odometer_km, checklist_confirmed: true}. Odometer decimal string, at
most one decimal place. This scoped transport does not implement historical
GPS/tracking fields or imply tracking exists.
POST /bookings/{id}/changes
Owning Passenger/current owning approved Owner/assigned approved Driver;
{expected_version, reason, itinerary}. Reasons ADDED_STOP,
DESTINATION_CHANGE, EXTRA_WAIT; additionally Owner-only
DEPARTURE_TIME_CHANGE under the addendum guards. Traffic is not a trigger.
POST /bookings/{id}/changes/accept
Passenger; {expected_version, digest}; old/new agreement remains unchanged
if review needed.
POST /bookings/{id}/changes/review
Current owning approved Owner; {expected_version, digest}; current Passenger
acceptance mandatory, no operational override.
POST /bookings/{id}/cancel
Passenger/owning approved Owner; {expected_version, reason}; only unfunded
standard pending/Owner-action/awaiting-Driver requests. Confirmed/in-progress,
funded and protected cases require the separate cancellation/financial workflow.
GET /notifications
Current recipient only; allowlisted IN_APP notifications. No external mail/SMS side
effect.
GET, POST /admin/service-types
Current approved Admin. POST {code, name, default_pricing_basis,
is_active, pricing_scope}, creates PRIVATE_HIRE only; unique uppercase
code, explicit approved scope, no invented rates/seed catalogue.
PATCH /admin/service-types/{id}/pricing-scope
Current approved Admin; {expected_version, pricing_scope}; explicit
classification, preserves other settings and uses durable audit; missing/unsupported
scope never inherits Long-distance pricing.
PUT /admin/service-types/{id}/licence-compatibility
Admin; {expected_version, matrix, routing_profiles}. Explicit reviewed
vehicle categories to licence codes, and same-key routing profiles
driving-car/driving-hgv; missing entries deny operation.
PATCH /admin/documents/{id}/licence-categories
Non-self Admin review; {expected_version, categories}; only reviewed LK
licence evidence with expiry. Applicant cannot set these fields.
PATCH /admin/vehicles/{id}/review
Non-self Admin; {expected_version, category, conditional_documents,
authorisation_required}; explicitly supply all three conditional evidence booleans;
required verified/current evidence mandatory. Reviewed vehicle becomes
APPROVED and unpublished.
PATCH /vehicles/{id}/publish
Owning approved Owner; {expected_version, published}; true checks verified
email/current evidence/eligibility, false unpublishes.

RateConfiguration: {service_type_id, expected_version, enabled, currency: "LKR", rules}. Collection is 1-30 rules
with unique UUIDs. Each rule requires id, 1-120-character label, method, direction, effective_from, optional effective_until,
pickup_area, coverage, free_wait_minutes, waiting_hour_rate, return_to_base, return_to_base_notes, tolls, parking,
other_charges (0-10), and change_limits (added_km, added_hours, added_wait_minutes, added_amount). Conditional monetary
fields are exactly those listed above; irrelevant non-null fields fail validation. Included service hours must be >0 and <=24.
Return-to-base charge is present only for SEPARATE_FIXED, otherwise INCLUDED. Tolls/parking/other-cost treatment is
INCLUDED or SEPARATE_AT_COST. Notes are 1-500 characters. Unknown actual costs cannot enter the covered total.
Place: {label, latitude, longitude, token}; proof binds the server geocoder's coordinates and label. Area: {label,
south, north, west, east} with ordered finite latitude/longitude bounds. ROUTE coverage has 2-12 ordered places and no
area. AREA coverage has one explicit area and no places; every stop and route geometry point must fit it. Pickup must also fit
pickup_area. Direction is ONE_WAY or RETURN; no inferred return leg. A route rule is exact directed ordered coordinates, not a
route name or nationwide rate. The Owner UI defines rectangles from a selected centre and explicit extent and describes the
rectangle.
Itinerary: {start_at, method, direction, stops, service_hours}. start_at is timezone-aware; method is DISTANCE
(point-to-point, may match a fixed-route rule) or DAY_HIRE. Stops have {place, wait_minutes, overnight_rest}; 2-12
stops, rest only intermediate and within a multi-day request. service_hours contains 1-30 explicit positive durations <=24, each
starting at pickup time in the corresponding 24-hour window. Route travel/wait must fit the windows; explicit non-billable
overnight rest bridges them. Counts are strict integers, passengers 1-200, luggage 0-200, checked against verified vehicle
capacities. Example day waiting requires non-overlapping {day, start_hour, minutes} periods summing to waiting_minutes;
day is zero-based. No client-provided live distance or fare is accepted.
Search and creation require future pickup. Missing provider measurements cannot produce an offer; an already validated
itinerary may remain an unpriced REQUESTED enquiry without reservation. Quote submission still requires trusted routing and
atomic save; routing failure rolls back its reusable-rate write. On fixed-route destination/stop changes, preserve old total and
mark CHANGE_REQUEST_UNPRICED; do not invent a per-km rate. Owner reuses the same form to quote the new exact
route, followed by Passenger acceptance and feasible Owner review. Distance/day changes use agreed rules, retaining the
initial snapshot and accepted revisions. No reduced-price automatic refund is implemented.
Success responses are safe resource objects (booking mutations return current booking/version/snapshots; service/rate
operations return their current version). Auth failures use existing 401/403 rules. State/version/digest/availability/eligibility
conflicts use 409; invalid DTO/coverage/capacity format uses 422; provider unavailable is 503. Dependency errors never
become a zero price or automatic confirmation. Mutations serialize authoritative user/role, vehicle, booking and assigned-Driver
checks, use the existing restricted durable review journal and commit notifications with the booking. A repeated stale acceptance
returns 409 rather than charging/applying twice.
~~~~
