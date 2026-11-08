# Owner and Driver role-only navigation - 6 November 2026

## Completed scope

Applied the Admin navbar separation to Owner and Driver at the user's request. The operational navbar no longer contains public Tickets, Rentals, For Owners, For Drivers, language or Travel Reels links. Each role keeps its own notification destination, profile/account menu and sidebar. Remaining navbar controls align to the right. Role-specific Reels and other management destinations remain in the sidebar.

Verified that the previously delivered Travel & Booking entry already uses `/owner/personal/hire` and `/driver/personal/hire`. Their search, vehicle details, quote/price-acceptance and personal booking list/detail routes continue rendering the existing shared booking components inside the matching workspace. No complete Passenger dashboard is embedded or substituted. No new booking system or role switch was introduced.

Passenger/public navigation and the Admin role-specific controls are preserved. No authentication code, backend, environment file, database record, permission, approval workflow or business rule was changed.

## Changed files

- Frontend/src/components/WorkspaceShell.jsx: remove the remaining public-navigation fragment from Owner/Driver operational navbars.
- Frontend/src/styles/dashboardReferences.css: apply right-aligned role controls to all operational navbars.
- Frontend/tests/browser/pricing.spec.js: require absence of Passenger/public navbar links for Owner/Driver as well as Admin during the existing full booking journeys.
- This report and docs/00-READ-FIRST/Travelly_NBP_Codex_Context.md.

## Verification

Production build passed (203 modules; existing bundle-size advisory). Eight full browser journeys passed: Admin, Owner, Driver and Passenger on desktop/mobile. They verify absence of public navbar links in all operational workspaces, role-specific sidebar entry, shared search and vehicle details, back/forward navigation, booking creation/explicit price acceptance, personal list/detail links, no embedded Passenger dashboard or horizontal overflow, and reopening the saved role-specific URL after reload-required sign-in. Owner desktop screenshot visually inspected. Whitespace check passed. Browser tests use synthetic authorized records and never create live bookings. Artifacts: `.tools/owner-driver-role-navigation-2026-11-06/`.

## Deferred scope, blockers and next dependency

No blocker for the role-navigation change. Session restoration remains the separate discussion draft in `../03-API/03I-BROWSER-SESSION-RESTORATION-PROPOSAL.md`; the current request does not change authentication. Full page reload still requires sign-in under the existing memory-only policy; saved role-specific booking URLs reopen in their matching shell after sign-in. No backend restart is needed.
