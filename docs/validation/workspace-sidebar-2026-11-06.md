# Shared Admin-style operational sidebars - 6 November 2026

## Completed scope

Applied the existing Super Admin sidebar composition to the Owner and Driver dashboards: navy background/border, red active item, larger readable links/icons, full-height left column and topbar/main content in the right column. The sidebar stays at the viewport top while dashboard content scrolls. Profile/Settings/Travel & booking/Logout remain at the bottom. All existing per-role destinations and permissions are preserved.

Menu height adapts to the actual count of each role's menu items and measured topbar height, so the longer Owner menu fits without an internal desktop scrollbar or clipped links. Desktop mode is consistently >=1100px wide and >=760px high for all three operational workspaces. Short desktop, tablet and mobile use the existing accessible drawer; that drawer retains scrolling when needed to keep every item reachable. Passenger keeps its existing top-navigation layout.

The previous Admin-only desktop media rule applied even to short windows, conflicting with the shared compact-drawer breakpoint. The shared final stylesheet resolves this so Admin also uses the drawer below the supported height.

No dashboard content, application workflow, authentication, role eligibility, data/API request, backend, environment, record or business rule changed. Existing earlier worktree changes are preserved.

## Changed files

- Frontend/src/styles/workspaceNavigation.css: new shared operational sidebar/layout rules and consistent compact breakpoint; imported after existing Admin/theme styles.
- Frontend/src/App.jsx: import the scoped navigation stylesheet.
- Frontend/src/components/WorkspaceShell.jsx: expose the actual menu item count as a CSS custom property. Menu structure, destinations, permissions and authentication are unchanged.
- Frontend/tests/browser/sidebar-sticky.spec.js: verify each role's complete sidebar fits and stays at the top during real document scrolling, with Profile/Logout visible and no sidebar scrolling.
- This report and docs/00-READ-FIRST/Travelly_NBP_Codex_Context.md.

## Verification

- Existing operational navigation browser tests: eight passed (2.0 minutes), all Owner/Driver/Admin menus at 1920x1080, 1440x900, 1100x760, 1024x900, 768x900, 390x844, 320x640 and short desktop 1440x650. Checks include destinations, active link, desktop fit, no horizontal overflow, drawer behavior and keyboard focus restoration.
- New sticky browser tests: three passed in the final run, Owner/Driver/Admin at 1366x768. Every menu item and Logout fits the desktop viewport; sidebar scrollHeight does not exceed clientHeight, scrollTop stays zero, and its position is unchanged within one device pixel while dashboard content scrolls. Screenshots of Owner and Driver visually inspected.
- Unit: four workspace routing/menu/eligibility tests passed.
- Production build: passed, 203 modules; existing bundle-size advisory remains. Working-tree whitespace check passed.
- Initial sticky test passed Owner/Admin and failed Driver on exactly 0.5px of browser layout rounding at the scroll boundary. Set a one-pixel geometric tolerance, keeping actual scrolling, complete link visibility and overflow assertions; reran all three successfully.

Artifacts: .tools/sidebar-fit-2026-11-06/, .tools/sidebar-sticky-2026-11-06/ and final .tools/sidebar-sticky-final-2026-11-06/. Browser checks use synthetic authorized fixtures; no live records changed. Backend tests were not needed for this presentation-only change.

## Deferred scope, blockers and next dependency

Requested desktop sidebar scope is complete, with no blocker. Responsive drawer scrolling is intentionally retained where a full desktop menu cannot fit; no controls are hidden to imitate a non-scrollable mobile menu. Dashboard content/artwork and topbar account functionality remain as before. Reload the frontend to see the shared navigation styling; no backend restart or reapplication is required.
