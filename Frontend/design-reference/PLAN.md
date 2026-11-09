# Travelly UI revamp — phased plan

Design references: Frontend/design-reference/ (see REFERENCE_MAP.md). Landing page is NOT changed.
Constraints: no API/request/response/api() changes. Ticket JSX files untouched (restyle via CSS/shared components only).

## Current state (audit)
- All roles share `components/WorkspaceShell.jsx` (sidebar inline, `Header` from `components/components.jsx`); menus from `workspaceMenu(role)` in `routes/workspaceRoutes.js`.
- Look differs per role via CSS scoped by `data-workspace`: `adminReferenceGlass.css` (admin), `roleReferenceGlass.css` (owner/driver), dark-blue base in `workspaces.css` + `travellyTheme.css`.
- Passenger: `PassengerEntry`/`PassengerDashboard` use own full-width header, no sidebar (`passengerDashboard.css`); `/travel/book/*` uses the shell.
- Role differences hardcoded in shell: owner has no sidebar Logout, admin has avatar link, passenger/owner/driver have top-bar "Sign out", notification route per role.
- ~20 override CSS files loaded in sequence from `App.jsx` (fragile).

## Old blue theme still used in
- Base: workspaces.css, travellyTheme.css, dashboardReferences.css, referenceDesign.css, passengerDashboard.css, workspaceNavigation.css
- Owner: OwnerVehicleSetup, OwnerRates, OwnerServiceReadiness, OwnerEventPackages, OwnerEventOperations, OwnerFinanceOverview, OwnerTicketDepartures, VehicleWorkspace, VehicleCalendar, VehicleMaintenancePage
- Driver: DriverTicketBoarding
- Shared trip/rental: booking/TripPricing.jsx (HireSearchPage + BookingPage at /owner/personal/hire and /driver/personal/hire — source of old blue Travel & Booking form), TripOperationPage, TripFinancePage, rental/RentalUi.jsx
- Admin: AdminApplications, AdminServiceCatalogue, AdminOversight, AdminTicketAudit, AdminWorkflowPage, RoleDashboards.jsx
- Auth/onboarding: RoleOnboarding, RoleApplicationForm, AuthFlows, onboarding.css

## Phases
1. **Tokens & foundation** — one `ui-theme.css` (glass, red, radius, shadow vars). Scenic background once on the shell. Nothing removed yet.
2. **Shared form kit** — `components/ui/`: GlassCard, FormField, Chip, Checkbox, Button (primary/secondary), FormGrid. Extracted from passenger booking pages.
3. **Navbar** — `AppNavbar` from WorkspaceShell: logo, language, Travel Reels, notifications, avatar+name. Remove per-role differences.
4. **Sidebar** — `AppSidebar`: red active pill, shared bottom block (Settings, Profile, Travel & Booking, Logout) for every role; menu items role-driven.
5. **Shell consolidation** — passenger home onto shared shell WITH sidebar. Landing stays without sidebar.
6. **Migrate forms, one role per phase** — driver & owner Travel & Booking first (TripPricing), then other owner pages, then admin. Each phase deletes the old CSS it replaces.
7. **Login/register + cleanup** — align to tokens (keep/verify authFormCompact.css register fix), delete dead CSS layers, list and remove unused old images in public/references/.

## Reference files per phase
(To be filled in by Claude from REFERENCE_MAP.md.)
