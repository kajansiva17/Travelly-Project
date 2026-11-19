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

## Follow-up: show vehicles first, verify, then book

- Future discovery now uses the saved base only as a provisional pickup-radius anchor. A preceding trip endpoint is used for repositioning feasibility, not as the permanent radius centre.
- Immediate discovery uses a fresh current position when available; stale current/base anchors can produce only `CONFIRMATION_REQUIRED`. A known fresh position outside the saved vehicle radius remains ineligible.
- Search returns explicit `AVAILABLE` and `CONFIRMATION_REQUIRED` states without fares. Enabled services with missing or temporarily uncomputable prices remain eligible for the protected Owner-quote path.
- Selecting a vehicle calculates any applicable saved Owner price even when location confirmation remains pending. Exact fixed-route pricing keeps precedence and no longer depends on road-distance routing.
- Future requests require a planned-position confirmation for the requested time. Price acceptance preserves that confirmation, and final Owner/Driver commitment still reruns eligibility, conflicts, radius and adjacent-travel feasibility.
- The implementation is coordinate/settings based across Sri Lanka. The Achchuveli/Colombo dates and coordinates are present only in regression tests; no example registration, vehicle ID, town, date or fare is hardcoded in production matching.

### Follow-up validation

- Location matching: 9 passed.
- Focused hire discovery/pricing/idempotency/confirmation tests: passed individually, including fixed-route precedence and routing-failure discovery.
- Ticket hold regression: 1 passed. Rental search regression: 1 passed.
- Frontend extra-policy/search grouping and Rental model tests: 14 passed. Fixed-rate validation tests: 8 passed.
- Frontend production build: passed.
- Browser state test could not launch Chrome in this environment (`os_crypt_win` failure); no authenticated browser persistence claim is made.
- The required `docs/00-READ-FIRST/Travelly_NBP_Codex_Context.md` remains absent from this checkout, so it could not be updated.

## Follow-up: unread notification bell badge

- The navbar bell now shows the recipient's visible unread notification count, capped visually at `99+` while retaining the full count in its accessible label.
- A lightweight count endpoint reuses the same recipient and notification-preference filters as the existing notification list. No new table or notification-generation rule was added.
- Workspace shells refresh the count on load, every 15 seconds, when the window regains focus, and when the page becomes visible. Opening the bell marks the recipient's visible notifications as read and clears the badge without changing the existing notification destination or list.
- Focused backend unread-count/read-all and existing notification-preference/list tests passed. Focused frontend notification/i18n tests passed (16 tests), and the production build passed with the existing large-chunk advisory.
- The existing road-alert notification integration selection was blocked before its assertion by its older future-hire fixture expecting an immediately quotable booking instead of the now-required planned-position confirmation. Notification-specific tests were unaffected and passed.

## Follow-up: Owner hire Trip / Price UI and pagination

- Owner booking pricing now distinguishes an applicable pending quote, an agreed price, location confirmation, a genuinely unpriced request and an explicit unpriced revision. An applicable saved fixed-route/package/per-km/Event price no longer opens duplicate Owner price inputs.
- Pending quotes show Passenger-acceptance status without auto-accepting. Genuine initial quotes and `CHANGE_REQUEST_UNPRICED` revisions keep the existing quote workflows and eligibility checks.
- Owner Trip location confirmation and Price breakdown/terms use retained-state substeps. Long terms are split into Price terms and Other terms; footer actions remain separate.
- The Price substeps now use the full card width without creating a second off-screen flex column. The breakdown uses a readable charges/extras layout, terms use separate cards, and short desktop viewports retain useful spacing and readable type without horizontal or card scrollbars.
- The remaining live agreed-price gap was traced to the shared `.booking-pane .rate-preview > h2` rule: its `flex: 1 1 100%` row-width behavior became vertical growth inside the column-oriented `.booking-price-snapshot`. A higher-specificity Price-snapshot rule now resets only that heading to `flex: none`; no offsets, clipping or pricing logic changed. The pre-fix live gap was about 280 px; the exact 1280 × 585 fixture measures 12 px after the fix.
- Focused state/i18n tests passed (9). Focused mocked Playwright checks passed for saved price, location confirmation, genuine initial quote, revised quote and change acceptance; English/Tamil/Sinhala were checked at 1280 × 585 with no document, card or sidebar scrollbar, no horizontal overflow or off-screen content, and no footer overlap. The frontend production build passed with the existing large-chunk advisory.
- Final live authenticated Chrome verification observed booking `BKG-B959E3AB626A3B90F036` in its Requested + accepted fixed-route state after Vite hot reload. The breakdown and long-terms panels flowed from the top and their Next/Back footer no longer overlapped content. Exact 1280 × 585 assertions remain mocked Playwright because the authenticated window was not resized to that viewport.
- `docs/00-READ-FIRST/Travelly_NBP_Codex_Context.md` remains absent, so it could not be updated without inventing the missing authoritative context.
