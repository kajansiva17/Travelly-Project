# Travelly UI revamp — phased plan

Source of truth: `Frontend/design-reference/` only (`REFERENCE_MAP.md` first, then `DESIGN-SPEC.md`). `public/references/` is ignored; delete nothing there.

## Rules
- **NAVBAR RULE:** the OWNER navbar design (`screens/owner/*`, boards `O01`-`O04`) is the single navbar for EVERY page: login, register, landing/home, passenger, driver, owner and admin dashboards. Same layout, colours, logo style and buttons. Ignore the differing navbar colours in passenger, driver and admin references. Only role-specific items may differ: menu links, user name/avatar, notification target.
- **Landing page:** replace ONLY its navbar with the shared navbar. Change nothing else on it.
- Passenger home uses the shared shell WITH the sidebar. Sidebar items vary by role; design is identical.
- No API paths, request/response field names or `api()` logic changes.
- Ticket JSX files untouched (`PassengerTicketBooking`, `OwnerTicketDepartures`, `DriverTicketBoarding`, `AdminTicketAudit`): restyle via CSS and shared components only.
- Keep the register fix at the end of `src/styles/authFormCompact.css`; verify in Phase 7.
- Match references closely: layout, fonts, colours, glass cards, buttons, fields, chips, icons, images. Photos from `public/images/travelly/`.
- Business rules in `REFERENCE_MAP.md` stay (price only after vehicle/departure selected; `Operations` Owner-only; Back keeps entered data; honest unavailable states).
- No screenshots unless the user asks.

## Current state (audit)
- All roles share `components/WorkspaceShell.jsx` (sidebar inline, `Header` from `components/components.jsx`); menus from `workspaceMenu(role)` in `routes/workspaceRoutes.js`.
- Looks differ per role via CSS scoped by `data-workspace`: `adminReferenceGlass.css`, `roleReferenceGlass.css`, base `workspaces.css` + `travellyTheme.css` (plus `dashboardLightGlass.css`, `dashboardReferences.css`, `dashboardScenicBackground.css`, `workspaceNavigation.css`).
- Passenger home (`PassengerEntry`/`PassengerDashboard`) uses its own header and no sidebar (`passengerDashboard.css`); `/travel/book/*` uses the shell.
- Role differences hardcoded in the shell: owner has no sidebar Logout, admin has avatar link, passenger/owner/driver have top-bar "Sign out", notification route per role.
- Header variants live in `Header` (`auth`, `dashboard`, `workspaceHeader`, `customerHeader`) plus `NavbarBrand.jsx`, `navbarSpeedometer.css`, `TravellyBrand.css`.
- About 20 override CSS files loaded in sequence from `App.jsx`.

## Old blue theme still used in
- Base: workspaces.css, travellyTheme.css, dashboardReferences.css, referenceDesign.css, passengerDashboard.css, workspaceNavigation.css
- Owner: OwnerVehicleSetup, OwnerRates, OwnerServiceReadiness, OwnerEventPackages, OwnerEventOperations, OwnerFinanceOverview, OwnerTicketDepartures, VehicleWorkspace, VehicleCalendar, VehicleMaintenancePage
- Driver: DriverTicketBoarding
- Shared trip/rental: booking/TripPricing.jsx (HireSearchPage + BookingPage at /owner/personal/hire and /driver/personal/hire — old blue Travel & Booking), TripOperationPage, TripFinancePage, rental/RentalUi.jsx
- Admin: AdminApplications, AdminServiceCatalogue, AdminOversight, AdminTicketAudit, AdminWorkflowPage, RoleDashboards.jsx
- Auth/onboarding: RoleOnboarding, RoleApplicationForm, AuthFlows, onboarding.css

## Phases and the exact references each must match
Paths are relative to `Frontend/design-reference/`.

1. **Tokens and foundation.** One `ui-theme.css` with the values in `DESIGN-SPEC.md` (glass, red gradient, radius, shadow, blur, navy ink, input and chip styles). Scenic background set once on the shell. Nothing removed yet.
   - Match: `DESIGN-SPEC.md`; `screens/owner/O04-01-owner-overview.png`, `screens/owner/O01-01-vehicle-basics.png`, `auth/authlogin-reference.jpg.jpg.jpeg`.
2. **Shared form kit.** `components/ui/`: GlassCard, FormField, Select, Chip, Checkbox, Button (primary/secondary/disabled), Stepper, InfoCallout, FormGrid, ServiceTile.
   - Match: `screens/owner/O01-01-vehicle-basics.png`, `O01-02-vehicle-features.png`, `O01-03-vehicle-documents.png`, `O01-04-vehicle-services.png`; `screens/passenger/P01-01-choose-service.png`, `P01-03-vehicle-needs.png`, `P02-01-local-hire-form.png`; `boards/O01-owner-add-vehicle-board.png.png`, `boards/P02-passenger-service-forms-board.png.png`.
3. **Single navbar (owner design).** `AppNavbar`: logo, EN selector, Travel Reels, bell with badge, avatar + name; auth/landing variant (Back to Home, Help, EN). Used by `WorkspaceShell`, `AuthPage`/`AuthFlows`, `Header` consumers and the landing page. Remove per-role navbar differences; landing change is the navbar only.
   - Match: `screens/owner/O04-01-owner-overview.png`, `O04-02-owner-operations.png`, `O04-03-owner-driving-task.png`, `O04-04-owner-travel-booking.png`, `O01-01-vehicle-basics.png`; auth variant from `auth/authlogin-reference.jpg.jpg.jpeg`, `auth/authregister-reference.jpg.jpg.jpeg`.
4. **Sidebar.** `AppSidebar`: floating green glass, red active pill, bottom block Settings / Profile / Travel & Booking / Logout for every role; items role-driven; `Operations` Owner-only.
   - Match: `screens/owner/O04-01-owner-overview.png` and `O04-02-owner-operations.png` (owner), `screens/passenger/P01-01-choose-service.png` (passenger), `screens/driver/D01-01-assigned-trip.png` (driver), `screens/admin/A01-01-vehicle-verification-queue.png` (admin).
5. **Shell consolidation.** Passenger home onto the shared shell with sidebar; landing stays without sidebar (navbar swap only).
   - Match: `screens/passenger/P01-01-choose-service.png`, `P01-04-matching-vehicles.png`; `boards/P01-passenger-booking-steps-board.png.png`.
6. **Migrate pages (one role per sub-phase; delete the old CSS each one replaces).**
   - 6a Driver and Owner Travel & Booking (`TripPricing.jsx`): `screens/owner/O04-04-owner-travel-booking.png`, `screens/passenger/P01-01-choose-service.png`, `P01-02-airport-trip-details.png`, `P02-01-local-hire-form.png`, `P02-02-event-hire-form.png`, `P02-03-long-distance-one-day.png`, `P02-04-long-distance-multi-day.png`; `boards/P02-passenger-service-forms-board.png.png`.
   - 6b Passenger flow: `screens/passenger/P01-*`, `P03-01-selected-vehicle-price.png`, `P03-02-review-send-request.png`, `P03-03-awaiting-owner-confirmation.png`, `P03-04-ride-confirmed-qr-pin.png`, `P04-01-ticket-search-departures.png`, `P04-02-ticket-seat-selection.png`, `P04-03-rental-search.png`, `P04-04-selected-rental-review.png`; `boards/P01`, `P03`, `P04`. Ticket pages via CSS and shared components only.
   - 6c Owner: `screens/owner/O01-01..04`, `O02-01..04`, `O03-01..04`, `O04-01..04`; `boards/O01`-`O04`.
   - 6d Driver: `screens/driver/D01-01..04`; `screens/shared/M02-01-driver-add-fuel.png`, `M02-02-fuel-expense-saved.png`, `M01-03-driver-cash-received.png`; `boards/D01-driver-trip-operations-board.png.png`.
   - 6e Admin: `screens/admin/A01-01..04`; `boards/A01-admin-review-board.png.png`.
   - 6f Shared payment/finance: `screens/shared/M01-01..04`, `M02-03`, `M02-04`, `M03-01..04`; `boards/M01`, `M02`, `M03`.
7. **Login/register and cleanup.** Align to tokens and the shared navbar; verify the `authFormCompact.css` register fix; delete dead CSS layers. Do not touch or delete `public/references/`.
   - Match: `auth/authlogin-reference.jpg.jpg.jpeg`, `auth/authregister-reference.jpg.jpg.jpeg`.

## Status
- [x] Audit, `DESIGN-SPEC.md`, this plan
- [x] Phase 1 — `src/styles/ui-theme.css` (tokens + scenic background), imported last in `App.jsx`
- [x] Phase 2 — `src/components/ui/*` + `src/styles/ui-kit.css`; dev gallery at `/__ui-kit`
- [ ] Phases 3-7
