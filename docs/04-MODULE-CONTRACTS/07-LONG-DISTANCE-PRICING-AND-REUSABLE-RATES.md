# 07-LONG-DISTANCE-PRICING-AND-REUSABLE-RATES

> Recovered source text, 7 November 2026. Source: documentation collection, pages 281-285, original path `docs/04-MODULE-CONTRACTS/07-LONG-DISTANCE-PRICING-AND-REUSABLE-RATES.md`. This is the saved page-text extraction, not the original Markdown. Line wrapping and table layout reflect the compilation; no policy wording has been rewritten. Later approved amendments recorded in `docs/00-READ-FIRST/Travelly_NBP_Codex_Context.md` take precedence.

~~~~text
Long-distance pricing and reusable vehicle rates
Master Rules V2 reconciliation boundary - 4 November 2026
This contract remains authoritative for approved Long-distance pricing, snapshots, consent and feasibility. The Master Rules V2
workflow amendment changes Owner/Driver personal-booking shell presentation, not price calculation, payment, refunds,
settlement or service eligibility.
For cross-service reconciliation, LD-Q01/LD-F01's pooled included km with separately per-day service hours remains the
approved Long-distance rule. It does not resolve the conflicting reported driver-inclusive multi-day “No KM Pooling” claim
(CF04); self-drive rental pooling is a separate RENT-04 scope. Do not apply either version to a driver-inclusive multi-day
implementation until explicit MULTI source approval/scope is recovered.
The directly evidenced 25% deposit / 30-minute deadline source, reported No Advance Payment, gateway-fee alternatives and
direct Owner settlement are recorded in Final Decisions CF01-CF03. None is selected by this contract; do not make payment,
custody, gateway or settlement behavior from those records. Local/Airport/Event numeric rules remain unfrozen except for the
already recorded future-scope principles in LD-A05-A07.
Date: 27 October 2026.
Status: LD-P01 through LD-P10, LD-Q01 through LD-Q05 and follow-ups LD-F01/LD-F02 are approved subject to the detailed
owner's amendments below. Bounded existing-table snapshot refinements are approved and implemented. See the
implementation validation (../validation/long-distance-pricing-2026-10-27.md) for tests and external setup dependencies.
Subsequent remaining VM approvals and the first fleet delivery are recorded in contract 08
(08-VEHICLE-OWNER-FIRST-DELIVERY.md); historical pending references below describe the earlier pricing-only gate.
1. Authority and inspected baseline
This request replaces the previous pricing-documentation task. It is one implementation task with a decision gate before
dependent code, not approval to run both prompts.
Inspected the current working tree, Final Decisions, Readiness, VM-D01 through VM-D20
(06-VEHICLE-OWNER-BUSINESS-DECISION-GATE.md), Owner/Driver and Passenger contracts, physical dictionary
(../02-DATABASE/02C-TRAVELLY-PHYSICAL-DATA-DICTIONARY.md), original database architecture
(../02-DATABASE/02A-TRAVELLY-DATABASE-ARCHITECTURE-FINAL-20-TABLES.pdf.pdf), lecturer database reference, API
plan (../03-API/03A-TRAVELLY-NBP-API-PLAN.pdf.pdf), current API matrix
(../03-API/03B-TRAVELLY-API-ENDPOINT-MATRIX-96-ENDPOINTS.xlsx.xlsx), and current backend/frontend implementations.
Readiness section 2 and dictionary section 11 contain the binding private-hire/Booking baseline; there is no separate frozen
Vehicle or Booking implementation contract in the tree beyond that baseline and the proposed vehicle gate.
At initial inspection the implementation had Auth, independent role applications, private documents and Admin application
review, with four migrated application tables: users, user_roles, vehicles and documents. This pricing slice adds nine of the
existing planned tables and implements the scoped publication, rates, search, quote, booking, assignment/start and
itinerary-change dependencies. Thirteen planned application tables are now migrated. General vehicle onboarding and unrelated
modules remain separate; existing Auth UI changes are preserved.
The NBP retains exactly twenty planned application tables. No new rate, quote, change-request or history table is authorized by
this document. Existing booking, assignment, vehicle and trip status catalogues and eligibility/authorization rules remain binding.
2. Approved requirements
- LD-P01: Passenger supplies pickup, destination, ordered stops, trip dates/times and point-to-point versus dedicated
day/multi-day hire.
- LD-P02: Search calculates a fresh itinerary-specific price only when saved rates fully cover that request and availability can be
checked. Missing rates do not fabricate a price or make the vehicle unreachable: eligible vehicles remain discoverable through
Browse vehicles/Owner profile for Request a quote. Existing publication/verification requirements still govern browse visibility.

- LD-P03: Ordinary rates and quote responses use ONE reusable Owner rate form. A quote prefills the Passenger itinerary.
Submitting the quote saves structured rules for that vehicle and their explicit applicable route/coverage. It never publishes the
first Passenger's total as a reusable fare. Do not add a private-versus-publish switch.
- LD-P04: Explain on the form that saved rules affect future matching searches and each future itinerary gets its own calculation.
A route-specific quote must not become a nationwide rate.
- LD-P05: Owner edits affect future offers/searches. An accepted booking retains its agreed itinerary, price, breakdown and
extra-charge rules independently of later rate edits.
- LD-P06: In-trip stop/destination changes are calculated against the agreed itinerary. Show old total, added charge and
proposed new total. Passenger acceptance precedes any booking update. Notify Passenger, assigned Driver and Owner.
- LD-P07: Passenger acceptance alone cannot override operational feasibility. App confirmation also requires the Owner's
pre-authorized limits and current vehicle/Driver non-overlap/eligibility checks. Otherwise request manual review; do not mutate
the booking to an impossible itinerary or silently confirm it.
- LD-P08: Conditional form sections cover vehicle; operating/pickup area; route/area; one-way/return applicability; effective date;
trip type; distance base/minimum and included/excess km; night window/night-km surcharge; disclosed return-to-base charge;
day charge/included km/hours/excess rates/overnight Driver cost; waiting allowance/rate/unit; trip-change calculations and
operational limits; tolls/parking/other inclusions or separate payments.
- LD-P09: Owner preview states the selected method, covered amount, each extra and total. Distance and day hire must not
both charge the same base service. Unknown variable costs remain separately disclosed, never included in a claimed exact final
total.
- LD-P10: All monetary amounts and free allowances come from explicit Owner input. Do not supply invented rates or default free
allowances. Frontend/backend validate required fields, nonnegative values, units and conflicting rules. Preserve responsive
Travelly styling and accessible conditional labels.
3. Relationship to VM gate and Booking workflow
LD-P01 through LD-P10 supersede VM-D10's proposed quote-only first-slice limitation for this pricing task. VM-D10 was a
recommendation, not an approved binding rule. Record this as an accepted replacement requirement, not approval of every VM
recommendation.
VM-D11's proposed restriction to no calculated extras is superseded where it conflicts with the explicitly approved
distance/day/night/waiting/change extras. The owner's subsequent LD-Q03 response explicitly approves LKR only for this slice.
Price preservation is explicitly approved by LD-P05 and the existing history rules.
The owner explicitly approves VM-D02 B amended to verified EMAIL before publication (draft/review allowed; no SMS or
legacy-login change); VM-D05 vehicle-specific registration/conditional authorization; VM-D06 core
registration/insurance/revenue licence and Admin-confirmed conditional evidence; VM-D12 explicit publication; VM-D13
occupancy from Owner commitment after Passenger price acceptance, retained through Driver rejection/reassignment until
properly resolved; and VM-D20 hide on required-evidence expiry, verified renewal and explicit republication without erasing
commitments. No automatic turnaround buffer is added.
VM-D17 is amended: Admin reviews licence evidence, recorded categories/expiry and vehicle category; the backend
automatically checks verified Driver-to-vehicle/service eligibility on every actual assignment and start. Mismatched, unverified,
expired or suspended eligibility is denied. There is no separate Admin approval for each assignment. Driver acceptance and
private-document access restrictions stay in force. All other unapproved VM choices remain pending; this does not authorize
arbitrary fleet onboarding choices.
Booking's REQUESTED, AWAITING_DRIVER, OWNER_ACTION_REQUIRED, CONFIRMED, IN_PROGRESS, COMPLETED,
REJECTED and CANCELLED catalogue is retained. Matrix #47 remains deprecated. LD-Q04 explicitly requires Passenger price
acceptance before Owner commitment through self-drive or external Driver assignment. Their existing acceptance/eligibility rules
still apply. A quote response is not implicit Passenger price acceptance, booking confirmation or Driver acceptance.
4. Decision record and remaining specifications
The following selections are the owner's explicit replies on 27 October 2026, not defaults inferred from recommendations:
ID
Accepted selection
Remaining dependency
LD-Q01
Fixed Travelly billing policy supplied below; Owners enter
rates/allowances only.
Resolved by the policy and LD-F01 below; no per-Owner formula
switches.

ID
Accepted selection
Remaining dependency
LD-Q02
Backend-validated routing and explicit coverage.
Define provider integration, validated ordered-leg/time/stop data and
exact coverage transport in the technical contract. Missing trusted
measurements cannot yield a fabricated price.
LD-Q03
LKR only.
Reflect this in eventual validation and DTOs; no multi-currency
conversion/comparison workflow.
LD-Q04
Require Passenger price acceptance before Owner commitment.
Freeze transport/version/concurrency guards without adding
booking statuses or bypassing Driver acceptance.
LD-Q05
Named vehicle prerequisites approved/amended as recorded in
section 3; bounded snapshots on existing bookings and structured
rates in vehicle_services.owner_terms approved.
LD-F02 resolves the matrix source; 02C and 03F freeze
persistence/API details. Other unapproved VM decisions remain
pending.
Original choices and rationale are retained below as history. Recommendations are not the accepted selection where the owner
chose another option; this table is not a second pending request to decide LD-Q02 through LD-Q04.
ID
Exact unresolved decision
Options and recommendation
LD-Q01
Who defines the calculation conventions omitted from the request:
whether base is additive or a minimum fare floor, started-day versus
calendar/pro-rata day billing, pooling of daily km/hours, partial-unit
rounding, night surcharge inside included km, and the interaction of
waiting with day-hire excess hours?
A: Owner explicitly selects supported conventions in the same rate
form, with the choices disclosed and snapshotted; B: Travelly fixes
one platform policy, whose exact conventions must first be
supplied/approved. Recommend A to keep rates explicit without
invented monetary values. Mutual exclusion must prevent charging
the same base service twice under either option.
LD-Q02
What establishes trusted route distance, time, night km and
matching coverage for saved rules? Free text and a single route
distance cannot establish this for arbitrary ordered stops.
A: Backend-validated directions/geocoding with explicit route/area
boundaries, ordered-leg timing and planned stop durations;
incomplete measurements go to quote, never fabricated price. B:
Restrict first delivery to Owner-confirmed itinerary measurements
and explicitly matched itineraries, without claiming arbitrary
automatic route pricing. Recommend A for the requested search
workflow; provider configuration is then a dependency. Coverage
geometry/matching semantics must be frozen with it.
LD-Q03
Is currency limited to LKR for this slice? The only LKR-only wording
is VM-D11's unapproved recommendation.
A: LKR only; B: multiple explicitly supported currencies, with
comparison/settlement behavior requiring a further contract.
Recommend A for the bounded Sri Lankan deployment. No
currency default is installed while open.
LD-Q04
Must the Passenger explicitly accept the Owner's calculated quote
before the Owner may perform self-drive/external assignment
acceptance? The old Booking workflow has no
quote-response/Passenger-price-acceptance phase.
A: Require Passenger price acceptance first while retaining
canonical booking states and all operational checks; B: keep
quote/rate saving in this slice and defer booking
acceptance/changes to a later Booking contract. Recommend A for
the complete requested workflow. No new booking state or revival of
deprecated owner-accept is implied.
LD-Q05
May this slice adopt the existing prerequisite recommendations
VM-D02, D05-D06, D12-D13, D17 and D20 (contact gate, vehicle
evidence, publication, occupancy, licence suitability and expiry), and
freeze the dedicated existing-bookings snapshot/proposal
refinement described below?
A: Approve those bounded prerequisites and the existing-table
refinement for the complete workflow; B: review/amend the named
prerequisites before dependent implementation. Recommend A,
with exact persistence/API details documented before migration. All
other unapproved VM choices stay pending; this is not approval of
all twenty recommendations.
4.1 Accepted fixed billing policy and narrow follow-up
The owner's policy is binding:
- Distance base covers its stated included km; add extra-km rate only beyond that allowance. It is not an independently chosen
minimum-fare-floor mode.
- The first day package is charged even when initially planned service hours are fewer than its included hours. Reserve the
vehicle for the full included hours. A hire day is a 24-hour window from pickup in Asia/Colombo, not a calendar day.
- Service hours beyond the package use the Owner's extra-hour rate. A partial further day uses extra-hour pricing capped at one
full package. Its included km are proportional to booked service hours, with full km allowance when the full package is charged.
Pool included km across the booking; apply service-hour allowances separately per day.

- Use trusted total route distance and verified billable time proportionally; do not round each stop or bill in 15-minute blocks.
Round only the final LKR total to two decimal places.
- Distance/day-hire night window is fixed at 22:00-05:00 Asia/Colombo. Night surcharge covers ALL planned night km, including
included km. Fixed-route fares receive no automatic night-km surcharge.
- Traffic delay alone does not increase an accepted price. Apply free waiting first. Where waiting and extra-hour charges cover
the same time, charge the higher applicable amount once, not their sum.
Accepted LD-F01: in a later window below included service hours, charge booked hours multiplied by extra-hour rate capped at
one package. At/above included hours charge the full package plus excess hours. Apply proportional km only to a partial window
not charged as a full package. Accepted LD-F02: Admin maintains an explicit reviewed licence-category-to-vehicle/service
compatibility matrix; missing entries deny assignment/start. No matching rule is inferred from a vehicle display type.
LD-Q02 cannot use guessed straight-line km, whole-leg uniform-speed night allocation or label-only nationwide coverage.
Missing trusted route/time/coverage or calendar data fails closed to quote/manual review, never a fabricated calculated fare or
availability promise.
5. Physical mapping conflict and proposed resolution
Dictionary section 6 permits one vehicle_services row per vehicle/service_type. It has base_price, price_per_km,
price_per_hour, minimum_hire fields, date bounds, currency and owner_terms JSONB. The approved refinement now freezes
structured coverage-specific rules, daily allowances, night windows, waiting units and automatic-change limits in
owner_terms.rate_rules, with bounded validation in 03F. Scalar price fields stay null for these rules and cannot become a
competing source of truth.
Dictionary section 11 has origin/destination and booking intervals/amounts but no ordered private-hire itinerary, general
agreed-price/rule breakdown snapshot or pending change proposal. protected_terms_snapshot is for the protected-departure
promise; cancellation_policy_snapshot is for cancellation. Do not repurpose either into an unrelated private-hire quote/change
store, or hide it in special_requirements text. There is no quote/change entity in the twenty-table target.
The owner approves the refinement for the full dependency slice: dedicated bounded JSONB snapshot/proposal columns on the
EXISTING bookings table for agreed itinerary, price/rules and current proposal/acceptance state, retaining completed change
evidence in the approved durable audit channel. Exact names, shape, write guards, retention and concurrency semantics must
be written into 02C and the API contract before migration. No twenty-first table is introduced; protected/cancellation snapshots
retain their purpose.
Planned service_types, vehicle_services, route/stop, booking, trip, notification and occupancy dependencies must be migrated in
the dictionary's valid FK order. Nullable FKs still require target tables. No dummy tables/records, removed FKs, Redis-only
permanent quote store or audit journal standing in for a booking database.
6. Project-owner addendum and reconciliation
The additional owner decisions below supplement, rather than replace, LD-P01-P10, the three submitted LD-Q reply batches
and LD-F01/LD-F02. All previously accepted billing conventions, routing/coverage, LKR, price acceptance, eligibility and
snapshot decisions remain authoritative.
ID
Recorded binding decision
Implementation boundary / conflict resolution
LD-A01
Matching one-way point-to-point requests select the applicable
fixed-route fare first, then a matching distance rule, otherwise
Request a quote. Never sum fixed and distance fares.
Supersedes the implementation's cross-method overlap rejection for
ONE_WAY only. Same-priority ambiguity remains invalid; day hire
remains explicitly selected. No return-fare precedence is inferred.
LD-A02
Owner explicitly sets equal or different fixed fares by travel direction.
Eight hours of travel does not make a drop-off into Day hire.
Directional one-way rules use the ordered route: A-to-B and B-to-A
are separate explicit entries, which may have equal or different
fares. The ONE_WAY/RETURN journey flag is separate from route
orientation. Never infer reverse coverage or switch service from
duration.
LD-A03
A fixed fare discloses departure applicability, normal itinerary/stops
and included waiting. Planned night adds no automatic night
surcharge. Extras beyond inclusions and Owner-proposed
departure changes need displayed price and Passenger
acceptance.
Add explicit Owner-selected any-time or weekly local departure
windows, retaining exact ordered route and waiting allowance.
Previously saved fixed rules missing applicability do not produce
new automatic offers. Accepted legacy snapshots remain intact.
Owner-only future departure changes on unstarted confirmed
fixed-fare bookings use a new reusable quote, Passenger
acceptance and feasible manual confirmation; no silent schedule
mutation.

ID
Recorded binding decision
Implementation boundary / conflict resolution
LD-A04
Future rate edits affect future offers, never accepted bookings;
quote responses save structured reusable rules and future
itineraries get fresh calculations.
Retain LD-P03-P05 and the existing shared form, atomic quote save
and immutable initial/current snapshots.
LD-A05
Local hire can be one-way, multi-stop or return within its eventual
distance/time limits. Uncertain return waiting requires
Passenger-selected maximum reservation time, included waiting,
extra-wait rate and maximum possible charge before acceptance.
Charge verified actual waiting within that limit; extensions need a
new disclosed accepted price.
Recorded for the future Local contract. Numeric limits/formula,
actual-wait evidence and settlement transport are not frozen. Do not
substitute long-distance waiting or day formulas.
LD-A06
When both eligible Local and Day prices are calculable, show
comparison/suggestion without changing the selected service. Day
customers receive the full Owner-entered included service-hours
reservation.
Comparison is future scope until Local numeric rules are frozen.
Preserve the implemented full first-package Day reservation and
explicit Passenger service choice.
LD-A07
Local, Airport and Event numeric rules are unfrozen.
Explicit Admin service pricing-scope classification gates this
long-distance engine. Unknown/non-long-distance scopes cannot
save or calculate new long-distance offers/quotes by service-name
inference. Existing accepted records remain readable and are not
repriced. No additional table/migration is needed.
Technical representation: service_types.settings.pricing_scope is explicit Admin configuration (LONG_DISTANCE,
LOCAL, AIRPORT, EVENT or UNSPECIFIED). New long-distance calculations require LONG_DISTANCE. Fixed departure
applicability is Owner-entered in existing owner_terms.rate_rules: ANY_TIME, or WEEKLY_WINDOW with explicit weekdays
and start/end local times. Windows are half-open in Asia/Colombo; a crossing-midnight window is anchored to its selected start
weekday. Same-priority overlapping windows/coverage are rejected. This is applicability transport, not an Owner-selectable
billing convention or an invented numeric allowance.
Remaining future business decisions: Local distance/time limits and numeric formula; how verified actual waiting is
established/disputed/settled within the accepted maximum; Airport and Event numeric pricing. These do not authorize coding a
substitute formula. No unresolved business choice is needed for the bounded long-distance precedence/applicability and explicit
departure-consent changes described above.
7. API gap and implementation acceptance
Inspected current matrix #24-26 (service config/search), #42 (private-hire creation), #45 (booking detail), #48-53 (Owner/Driver
decisions), #58 (material alternative), #59-64 (trips), #71-74 (records/availability), and #94 (vehicle moderation dependency).
These generic DTOs do not freeze reusable quote response, Passenger price acceptance, preview calculation, general
itinerary-change proposal/acceptance or immutable rate snapshots. Protected-alternative #58 is not automatically a general
in-trip pricing endpoint. Preserve matrix IDs; define exact DTOs/errors/permissions/idempotency/version handling and any
required additional operations only after the decisions above.
Implementation acceptance: use one shared form and backend calculation authority; verify
direct/multi-stop/day/multi-day/night/waiting, nonmatching coverage, fresh quote reuse, future rate edits, accepted snapshots,
changed itinerary old/add/new presentation, stale/repeated acceptance, limits, vehicle/Driver conflicts, notifications, permissions
and responsive layouts. Exact delivered transport is frozen in 03F as a supplement to the original numbered matrix, whose
historical workbook is retained. Runtime results and remaining provider/deployment dependencies are recorded separately in the
validation report.
~~~~
