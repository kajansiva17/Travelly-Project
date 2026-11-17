# Vehicle Location-Based Hire Matching — Delivery Report

Date: 18 November 2026
Branch: `feature/pending-screens`

## Completed scope

- Added vehicle hire opt-in, usual operating base and pickup-distance settings. Existing vehicles default to bookings OFF.
- Added separately timestamped GPS/manual current vehicle location. Editing another vehicle setting does not refresh the location observation time.
- Added the approved matching policy: pickup within two hours is immediate, location freshness is 15 minutes, and reachability includes 15 minutes of preparation time.
- Added immediate matching from a fresh current location and future matching from the nearest preceding commitment or the configured base.
- Added pickup-distance, route-time, preceding/following booking and scheduled-trip checks.
- Added the Owner-confirmation-required path for missing/stale position or unknown routing. Confirmation supplies a current or planned position and runs the feasibility checks again. It does not override bookings OFF, conflicts, Driver eligibility, pickup distance, or known late arrival.
- Applied matching to Local, Airport, Long Distance and Event private hire. Scheduled-ticket and rental behavior remains separate.
- Separated general reusable pricing from operating-area matching. Search results do not expose a price before a vehicle/package is selected.
- Added Owner vehicle controls and Passenger/Owner confirmation screens in English, Tamil and Sinhala.
- Kept precise vehicle coordinates out of public vehicle responses. Private coordinates remain in controlled persistence/audit data only.
- Added version/location signatures and lock-time rechecks around request, Owner commitment, Driver acceptance and relevant itinerary-change workflows.

## Database and API

- Migration `0023_vehicle_hire_location` adds the vehicle opt-in, base, pickup-distance and observed-current-location columns with non-destructive defaults and constraints.
- Owner vehicle APIs support hire-location settings and manual position confirmation.
- An accepted operating Driver may manually update an assigned vehicle; automatic GPS persistence remains restricted to an active trip.
- Booking APIs return distinct available, price-required and Owner-confirmation-required outcomes and provide an Owner positioning-confirmation endpoint.

## Validation completed

- Backend module compilation and import smoke checks: passed.
- Location matching unit tests: 8 passed.
- Combined focused backend run: 22 passed; 3 integration setup errors occurred before tested endpoints because the existing email-verification fixture returned `INVALID_OR_EXPIRED_LINK`.
- The migration upgraded a fresh integration database through revision `0023` successfully during the backend run.
- Frontend tests: 184 passed.
- Frontend production build: passed (existing large-chunk warning only).
- `git diff --check`: passed (line-ending notices only).

## Deferred / environment limits

- Authenticated 1280 × 585 visual verification was not completed because the required signed-in seeded workflow was not available in this validation environment.
- Broader backend integration assertions remain blocked by the existing email-verification test-fixture failure described above; production auth code was not changed to conceal that unrelated failure.
- `docs/00-READ-FIRST/Travelly_NBP_Codex_Context.md` and a tracked relevant delivery report were not present in this checkout. This report was added without reconstructing or inventing the missing authoritative context.
- Pre-existing untracked Task 9 files and `CODEX-HANDOFF-17NOV.md` were preserved and excluded from this delivery.

## Changed areas

- Backend vehicle model, migration, schemas and vehicle APIs.
- Backend hire matching, routing, pricing applicability and booking lifecycle checks.
- Owner vehicle/hire interfaces and Passenger matching/request interfaces.
- English/Tamil/Sinhala messages and focused backend/frontend tests.
