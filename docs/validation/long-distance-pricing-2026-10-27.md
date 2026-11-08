# long-distance-pricing-2026-10-27

> Recovered source text, 7 November 2026. Source: documentation collection, pages 315-317, original path `docs/validation/long-distance-pricing-2026-10-27.md`. This is the saved page-text extraction, not the original Markdown. Line wrapping and table layout reflect the compilation; no policy wording has been rewritten. Later approved amendments recorded in `docs/00-READ-FIRST/Travelly_NBP_Codex_Context.md` take precedence.

~~~~text
Long-distance reusable pricing implementation validation
Date: 27 October 2026. Authority: Final Decisions (../00-READ-FIRST/01-TRAVELLY-NBP-FINAL-DECISIONS.md), approved
pricing flow and decisions (../04-MODULE-CONTRACTS/07-LONG-DISTANCE-PRICING-AND-REUSABLE-RATES.md), exact
API supplement (../03-API/03F-TRAVELLY-REUSABLE-RATE-CONTRACT.md), and physical dictionary
(../02-DATABASE/02C-TRAVELLY-PHYSICAL-DATA-DICTIONARY.md).
Subsequent owner addendum: recorded/implemented/future-scope audit (pricing-addendum-audit-2026-10-27.md). That audit
governs fixed-first one-way selection, departure applicability/consent and explicit service scope. The initial implementation/test
results below are retained as dated evidence; they do not claim Local/Airport/Event pricing or override the addendum.
Delivered behavior
One responsive cream/burgundy Owner rate form serves ordinary saved rates and itinerary-prefilled quotes. Conditional
distance/day/fixed-route inputs carry explicit units and helpers. New monetary fields and free allowances are blank until the
Owner enters values, including explicit zero. The form covers operating/pickup area, exact ordered route or bounded area,
direction, effective dates, included/excess km, package hours, night km, waiting, overnight costs, return to base, separately
payable actual costs and four operational change limits. Backend calculation supplies the clearly marked example preview.
Passenger trip entry records ordered pickup/stops/destination, Sri Lanka pickup time, pickup-anchored service windows and
planned waiting/rest. Search calculates fresh prices only from complete matching rules and checked availability. Browse/Owner
inventory remains reachable for quote requests. A quote saves reusable rules for its exact route; there is no
private-versus-publish switch and no reuse of a Passenger's total. Accepted initial/current price, breakdown, exclusions, itinerary
and rules are copied into booking snapshots; later rate edits affect future matching requests only.
Passenger price acceptance precedes Owner commitment. Self-drive and external Driver assignment/start recheck current
categories, evidence, approved roles and conflicts. Declining an assignment retains vehicle occupancy while the Owner seeks
another eligible operator. Added stops, destination changes and waiting display old/add/new amounts and require Passenger
acceptance. Owner limits and fresh eligibility/non-overlap checks govern automatic confirmation; manual review cannot override
an impossible change. Passenger, Owner and assigned Driver receive transactional in-app notifications.
Fixed-route changes outside the agreed route have no invented extra-km price: the Owner must quote the new route through the
same form, then obtain Passenger acceptance and feasible manual confirmation. Traffic alone cannot increase an accepted
price. Unknown actual costs are excluded from the covered total. Funded/protected/confirmed cancellation and reduced-price
refunds remain with the separate financial workflow.
Database and API changes
- 0005_reusable_rates: creates the existing planned service_types and vehicle_services.
- 0006_private_hire_pricing: creates existing planned routes, route_stops, scheduled_trips, bookings, trips, vehicle_records
and notifications in FK order, retaining original checks/indexes/catalogues. PostGIS supplies the planned route geometry type.
- Existing-table refinements: vehicles.verified_eligibility, documents.verified_categories; bookings.itinerary_snapshot,
price_snapshot, pending_change, accepted_quote_digest and vehicle_committed, with JSON/digest guards.
- Thirteen of the twenty planned application tables are now migrated. No twenty-first table, dummy FK target, live sample fleet or
invented live rate was added. Both new revisions were applied to the configured local database; Alembic reports head
0006_private_hire_pricing and no new upgrade operations.
- 03F lists all scoped endpoints, strict DTOs, errors and permissions. Additions include signed location lookup, full-itinerary POST
search, preview, reusable quote, price acceptance, change proposal/acceptance/review, in-app notifications, reviewed
compatibility/category/evidence configuration and explicit publication. Original PDF/XLSX matrix IDs are retained; the historical
workbook is not rewritten, and 03F is its explicit scoped transport supplement.
- Existing Auth business rules and interrupted Google UI changes are preserved. Passenger requests use the existing Auth
policy, including legacy accounts. Verified Owner email is required for publication. SMS/OTP is not introduced.

Pricing and operational cases
 Case
Verification
Direct trip, included distance and fractional quantities
Backend calculation and actual API browser journey; only final LKR total rounded to
two decimals.
Ordered multi-stop trip
Fresh route measurement and added-stop old/add/new totals; original order/pickup
protected.
Day / multi-day
Full first package and reservation, partial later window, full-package cap, full-package
overtime, pooled km and separate daily hours.
Night
Sri Lanka 22:00/05:00 boundaries; included km still receive the surcharge; fixed fare
receives no automatic night surcharge.
Waiting
Free allowance first, proportional hourly billing; overlapping excess service time
charged once at the higher rate.
Quote reuse
New route rule saved atomically; another request with different waiting obtains a fresh
total. Provider failure rolls the quote/rate write back. Disabled reusable quote rules
rejected.
Future rate edit
New search/request changes; accepted initial/current agreed snapshots stay
unchanged, including after a changed trip.
Changed trip
Passenger acceptance, repeated/stale acceptance, automatic limits, conflict-to-manual
path and refusal to override a conflict. In-progress external-Driver journey notifies all
three parties.
Eligibility / publication
Missing matrix entries, mismatches, unverified/expired/suspended Driver eligibility deny
operation. Renewed evidence stays hidden until explicit republication. Admin-only
configuration, no self-review.
Pending Driver decline
Reservation retained through OWNER_ACTION_REQUIRED, then explicitly released
by permitted pending cancellation.
Incomplete configuration
No fabricated fare/reservation; unpriced enquiry preserved when trusted route
measurement is unavailable; full reserved interval must fit rate effective dates.
Responsive/accessibility
Owner form, shared quote form, Passenger search/Browse and change review at
360px mobile, 768px tablet and 1366px desktop; labelled controls, visible focus, touch
targets, inline errors and no horizontal overflow.
Test results
Tests use actual PostgreSQL/Redis with random isolated schemas/namespaces; they do not truncate public data. Real browser
API journeys use deterministic routing fixtures, clearly separated from the production provider adapter.
- Frontend unit tests: 44 passed.
- Mocked browser regression: 24 passed, including 8 pricing cases and 16 preserved Google Auth cases across desktop/mobile.
Pricing tests also resize through tablet widths.
- Actual API browser journeys: 2 passed, desktop and mobile, with Owner save, Passenger fresh price/request/acceptance,
Owner commitment, added-stop acceptance and rate-edit snapshot preservation. Screenshot inspection confirmed the premium
form and readable mobile breakdown; the long booking-reference overflow found during testing was fixed.
- Frontend production build: passed, 164 modules. Vite reports a non-failing minified main-chunk warning (approximately 602
kB).
- Backend full regression: 214 passed in 660.23 seconds. This run preceded the final three added cases and
request-idempotency refinement; it is not claimed as one 217-test run.
- Backend final targeted pricing/operational suite: 44 passed in 132.36 seconds, including the added legacy-contact, fixed-route
quote/change and request-idempotency cases. The final retry/change check after the last idempotency refinement also passed:
2 tests in 13.58 seconds. All runs retain one non-failing upstream Starlette TestClient/httpx deprecation warning.
- Alembic current/check: passed, revision 0006 head, no schema drift.

Setup dependencies and boundaries
ROUTING_API_KEY is not configured in the current environment. No existing .env was changed. Configure a server-only
openrouteservice key, verify geocoding/directions and reviewed routing profiles with actual Sri Lankan routes, check quotas and
provider behavior before deployment. The production adapter never uses the browser test fixtures or straight-line distances.
Location proofs bind server-geocoded coordinates; missing trusted measurements produce unavailable/quote states. Provider
integration follows the official directions API (https://giscience.github.io/openrouteservice/api-reference/endpoints/directions/).
An approved Admin must configure the actual PRIVATE_HIRE catalogue, reviewed vehicle/service compatibility and routing
profiles, reviewed licence categories and vehicle evidence/applicability. No compatibility categories or exemption policies are
inferred. Existing vehicles can use the rate form; first-time fleet onboarding/media/block editing still depends on the remaining
unapproved VM decisions and its separate implementation. These unrelated choices were not selected implicitly by the pricing
slice.
No pricing business decision remains unresolved after LD-F01/LD-F02. Production rollout still requires the existing private
storage/audit OS identity, ACL, backup/restore and durability checks in Backend/ADMIN_REVIEW.md, provider verification and
actual approved fleet data. Ticket sales, payments/refunds, general fleet creation, trip completion and live tracking are not
claimed by this slice.
Changed files
Pricing code and checks:
- Backend/.env.example; Backend/alembic/env.py; Backend/alembic/versions/0005_reusable_rates.py;
Backend/alembic/versions/0006_private_hire_pricing.py.
- Backend/app/config.py; main.py; review_models.py; rate_models.py; rate_schemas.py; rate_calculation.py; rate_locations.py;
rate_api.py; hire_models.py; hire_schemas.py; hire_routing.py; hire_services.py; hire_api.py.
- Backend/tests/test_rates.py; test_hire_pricing.py; test_auth.py and test_auth_extension.py (only expected application-table
inventory); Backend/scripts/serve_pricing_test.py.
- Frontend/src/OwnerRates.jsx; TripPricing.jsx; rates.css; rateValidation.js; App.jsx; PassengerDashboard.jsx; PublicPages.jsx;
api.js.
- Frontend/tests/rateValidation.test.js; tests/browser/pricing.spec.js; tests/pricing-live/pricing.spec.js;
playwright.pricing-live.config.js.
Documents: README.md; Frontend/README.md; Final Decisions; 02C physical dictionary; 03F rate/API supplement; module
contracts 03/04 (scoped Admin category amendment), 06 vehicle decision gate and 07 pricing contract; this validation report.
Existing GoogleSignIn/auth CSS/Auth browser changes in the working tree were preserved, not replaced by this task.
~~~~
