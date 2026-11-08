# Operational dashboard reference restoration — 6 November 2026

## Completed scope

Supersedes the visual direction in workspace-sidebar-2026-11-06.md at the user's explicit request. Removed the recently added Admin dashboard stylesheet from the application cascade. Restored the existing reference composition with a full-width blue glass navbar, scenic canvas, translucent navy cards, circular metric icons, blue borders/glows and coral selection/actions. Admin uses the reference map/trend/alerts, pending-review and quick-action column positions; recent bookings sits under the map and pending queue. Existing vehicle review and Operations watch destinations remain available below.

All three desktop sidebars are fixed below the measured navbar and do not move with page scrolling. All existing destinations, Profile, Settings, personal travel and Logout are retained. Row heights use the real menu count. Compact navigation also fits without internal scrolling; short viewports use two columns. No clipping or overflow-hiding workaround is used to remove links. The help control occupies its own space rather than covering dashboard actions.

The navbar retains the direct Admin profile destination and Owner/Driver account menus, adds existing public navigation destinations to Admin, and links Travel Reels to each role's existing destination. The notification icon opens the existing support/booking/assignment destinations, without an invented unread count.

Existing API resources, real booking/fleet counts, error/retry states, calendar restrictions, application notices, approval detail links, access checks and trip action destinations are preserved. No backend, environment, database, role or approval transition changed. No sample earnings, contact details, map markers, vehicle records, online status or trend values were introduced.

## Visual limitations / deferred scope

This is a reference-guided restoration, not a pixel-identical reproduction. The repository's scenic and vehicle assets differ from the embedded reference artwork. Existing SVG icons/font differ from the screenshots. Exact artwork reconstruction is not claimed. More existing navigation destinations must fit than are pictured in the references, so their spacing adapts.

The current API does not provide global Admin booking/revenue summaries, live tracking, safety feeds, an Owner driver-team summary, Driver online controls, passenger contacts or earnings ledgers. Those remain honest unavailable states or existing functional calendar/status previews. Do not populate these with the reference's sample data. Admin approval/rejection remains in the existing authorized review detail and confirmation flow.

## Changed files

- Frontend/src/App.jsx — remove Admin redesign cascade; load scoped reference restoration last.
- Frontend/src/styles/dashboardReferences.css — operational visual restoration and responsive non-scrolling navigation.
- Frontend/src/components/WorkspaceShell.jsx — shared reference navbar links, existing role-specific destinations and accessible labels.
- Frontend/src/components/RoleDashboards.jsx — restored Admin composition; preserve API content and links; readable unavailable earnings.
- Frontend/tests/browser/dashboard-references.spec.js — all roles, six viewport sizes, role-specific heading, document overflow, complete menu visibility, actual scroll prevention and screenshots.
- Frontend/tests/browser/sidebar-sticky.spec.js — compare sidebar position with its initial position below the full-width navbar.
- This delivery report and docs/00-READ-FIRST/Travelly_NBP_Codex_Context.md.

## Verification

- Production build passed (203 modules); existing bundle-size advisory remains.
- Four workspace route/eligibility/menu unit checks passed.
- Initial responsive runs exposed a collapsed navbar flex basis at compact widths. Fixed with an intrinsic flex basis, retaining the visible account control. Initial bounded sticky positioning also allowed the Admin sidebar to move near its container end; explicit fixed positioning resolves that.
- Final combined browser run: 21 passed, two failed. All six new reference/overflow/non-scrolling-navigation scenarios passed (1672x941, 1366x768, 1024x900, 390x844, 320x640 and 844x390), each testing all three roles. All three fixed-sidebar scrolling checks passed. Existing navigation checks at eight sizes, current-access denial, role-scoped records, source retry/incomplete availability and logout recovery passed.
- Two broader onboarding fixture tests failed: legacy application links expected an absent `Owner application` article; rejected-membership resubmission expected an immediate pending notice but retained the correction notice. These paths use the unchanged Passenger/onboarding components. They were not modified or marked passing. Artifacts: `.tools/dashboard-restoration-final/`.
- Separate Admin document-checklist regression passed, including its existing approval readiness checks. Artifacts: `.tools/dashboard-approval-regression/`.
- After the last help-position adjustment, repeated the 1672x941 visual/navigation scenario successfully for all three roles; screenshots inspected for Admin/Owner/Driver and mobile Driver. Artifacts: `.tools/dashboard-final-visual/`. Browser coverage uses authorized synthetic fixtures, not live account modifications.

## Blockers and next dependency

No blocker for the scoped styling and non-scrolling navigation work. Pixel-level artwork parity requires the exact standalone reference assets; unavailable operational widgets require separately authorized APIs/features. Neither is fabricated in this change. Existing worktree changes and Backend/.env are preserved.
