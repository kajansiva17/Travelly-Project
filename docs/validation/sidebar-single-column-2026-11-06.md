# Single-column, always-visible operational sidebar - 6 November 2026

## Completed scope

User requested all Admin/Owner/Driver options in one vertical sidebar, each label on one line, visible while using the dashboard. Sidebar labels now remain complete without wrapping or truncation. Width reserves room for the longest existing labels; icons and row height adapt to the available viewport height and actual menu count.

The sidebar is fixed below the measured navbar for windows at least 768px wide, including short desktop/tablet landscape windows. Every option remains visible while dashboard content scrolls, with no sidebar scrolling. This replaces the earlier 1100x760 desktop threshold and two-column short-window drawer. Content reserves the sidebar width and stacks dashboard panels when needed.

Below 768px, phones retain the fixed navbar/menu button and modal navigation to leave usable content width. The opened menu also uses one column with complete labels, no internal scrolling and no two-column landscape exception. It remains visible until navigation/dismissal; it is not permanently open over phone content. Passenger retains its established top navigation without adding a new sidebar.

All menu entries, destinations, account controls, access checks, backend integrations and approval workflows remain unchanged. No Backend/.env, record, table or business rule was changed.

## Changed files

- Frontend/src/styles/workspaceNavigation.css: consolidated final sidebar sizing/position, one-column fit and responsive rules.
- Frontend/src/App.jsx: import navigation after dashboard reference styling so it consistently governs sidebar behavior.
- Frontend/src/components/WorkspaceShell.jsx: align modal close-on-resize with the 768px persistent-sidebar breakpoint.
- Frontend/tests/browser/dashboard-references.spec.js: assert complete single-line labels, equal left alignment, sequential non-overlapping rows and persistent navigation threshold; add tablet/short-phone sizes.
- Frontend/tests/browser/workspaces.spec.js: existing navigation fit expectations follow the new breakpoint.
- This report and docs/00-READ-FIRST/Travelly_NBP_Codex_Context.md.

## Verification

Production build passed (203 modules; existing bundle-size advisory). Four workspace menu/permission/routing unit checks passed. Nineteen browser scenarios passed: eight three-role viewport scenarios assert complete single-line labels, one aligned column, no overlapping rows, no horizontal page overflow, full menu visibility and no internal scroll; three sidebar checks verify fixed position during page scrolling; eight existing navigation scenarios verify every role destination, active link and the desktop/phone navigation behavior. Viewports include 1672x941, 1366x768, 1024x900, 768x900, 390x844, 320x640, 844x390 and 640x360. Owner desktop screenshot visually inspected. Whitespace check passed. All browser checks use synthetic authorized fixtures; no live applicant data changed.

Artifacts: `.tools/sidebar-single-column-final/` and `.tools/sidebar-single-column-navigation/`.

## Deferred scope, blockers and next dependency

No blocker for this sidebar correction. Phone navigation remains a one-column modal instead of permanently taking most of a narrow screen. Existing dashboard artwork/widget limitations documented in dashboard-reference-restoration-2026-11-06.md remain outside this bounded change. No backend restart is needed.
