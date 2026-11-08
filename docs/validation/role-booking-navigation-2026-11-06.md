# Role-based Travel & Booking navigation - 6 November 2026

## Completed scope

Admin navbar now contains only its support-notification and direct Super Admin profile controls; Passenger/public Tickets, Rentals, For Owners, For Drivers, language/reels controls are excluded from that role navbar. Remaining controls align to the right. Owner/Driver navbars and the independent Passenger shell remain unchanged.

The existing Travel & Booking sidebar entry now opens each operational role's own nested personal-hire route rather than `/`. Admin gains the same personal search, public vehicle detail, Owner-profile search, personal booking list and booking-detail route family already used by Owner/Driver. All three use the same HireSearchPage, PublicVehicle, WorkspaceBookings and BookingPage components. No PassengerDashboard is embedded in any operational shell.

All booking links retain role-specific URLs and therefore the matching shell on in-app navigation, back and forward. Passenger vehicle detail now shares the existing optional Passenger wrapper used by hire search: authenticated Passengers retain their own top navigation; guests still use the public header. Search data passed from search to vehicle details is returned to the shared search component on Browse vehicles, including Passenger.

Personal booking lists and notifications link to personal detail routes. Personal detail pages require the current account to be the Passenger on that booking and omit Owner/Driver operation controls. This is UI separation only: existing server authentication, role approval, ownership/assignment and price-acceptance checks remain authoritative and unchanged. Direct management URLs continue using existing management behavior. Personal requests send the existing Passenger payload with no workspace, Owner, Driver or role grant fields.

No backend, environment, database, approval workflow, pricing rule, payment scope or live record was changed.

## Changed files

- Frontend/src/App.jsx: Admin personal nested routes and optional Passenger vehicle-detail wrapper.
- Frontend/src/components/WorkspaceShell.jsx: role-specific Travel & Booking target/active state and Admin-only navbar.
- Frontend/src/components/RoleDashboards.jsx: personal list/notification links retain the personal route family.
- Frontend/src/features/booking/TripPricing.jsx: reuse personal search/booking routing for Admin, personal-trip list entry, scoped detail controls and personal refresh handling.
- Frontend/src/features/owner/VehicleWorkspace.jsx: Admin public vehicle details retain personal search context.
- Frontend/src/styles/dashboardReferences.css: Admin navbar right alignment.
- Frontend/tests/browser/pricing.spec.js: full four-role journeys and personal/management separation checks using the existing fixture.
- Frontend/tests/browser/workspaces.spec.js: deny all new Admin personal routes without current approved Admin access.
- This report, the session-persistence proposal and docs/00-READ-FIRST/Travelly_NBP_Codex_Context.md.

## Verification

- Eight full journeys passed: Admin/Owner/Driver/Passenger on desktop and mobile. Each exercises search, details, back/forward, booking creation, explicit price acceptance, personal list/detail links, shell/header independence, no horizontal overflow, reload-required sign-in and reopening the saved deep link.
- Six personal/management scope checks passed (three operational roles, desktop/mobile): an accessible management booking is not displayed as a personal journey and operation controls are absent.
- Two current-approval route-protection checks passed, including all new Admin personal routes on desktop/mobile.
- Four existing Owner/Driver confirmed-personal-booking scenarios passed on desktop/mobile.
- Four workspace route/menu/eligibility unit checks passed. Build passed (203 modules; existing bundle-size advisory). Whitespace checks passed.
- The first expanded full-journey run had a mobile Admin timeout during the second login after reload; the longer scenario exceeded the previous 30-second test budget. Set that full-journey test to 60 seconds; all eight passed in the final run. No production timeout or authentication rule was changed.

Artifacts: `.tools/travel-booking-navigation-final/`, `.tools/travel-booking-scope/`, `.tools/travel-booking-access/`, `.tools/travel-booking-existing-confirmed/`. Browser tests use synthetic authorized API fixtures; these are not live production bookings. Desktop Admin and mobile Driver screenshots inspected.

## Deferred scope, blockers and next dependency

Navigation and layout scope is complete. Full-reload sign-in continuity remains unimplemented: the existing authentication deliberately discards memory-only credentials on reload. Current tests explicitly verify sign-in again, then reopening the saved role-specific URL; they do not claim automatic session restoration.

The user expanded the scope to **discuss** session persistence and selected reload persistence for the current browser session only. The next bounded work is the proposed authentication contract revision in `../03-API/03I-BROWSER-SESSION-RESTORATION-PROPOSAL.md`; it is not an implemented authentication change. Until that is implemented, the original request's seamless authenticated full-refresh requirement remains deferred. No backend restart is needed for the delivered frontend navigation.
