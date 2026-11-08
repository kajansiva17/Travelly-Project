# Dashboard navbar link removal - 6 November 2026

Removed the Home and Vehicles links from the shared Admin, Owner and Driver navbar as requested. Removed the positional compact-navbar rule that depended on their old ordering, allowing remaining links to fit naturally. Sidebar entries and their fixed single-column behavior, logo navigation, account controls, public/Passenger navigation, backend integrations and approval workflows are unchanged.

Changed files: Frontend/src/components/WorkspaceShell.jsx, Frontend/src/styles/dashboardReferences.css, this report and docs/00-READ-FIRST/Travelly_NBP_Codex_Context.md. No environment or backend files changed.

Validation: production build passed (203 modules; existing bundle-size advisory); existing 1366x768 browser scenario passed for all three roles, including overflow, complete sidebar visibility and non-scrolling checks. Whitespace check passed; source check confirms both navbar links are removed. Artifacts: `.tools/navbar-link-removal-2026-11-06/`. No new tests were needed for this reversible link removal.

Completed scope is limited to the operational navbar. No deferred work, blocker or next dependency.
