# Claude Code — project context

<!-- cloude-code-toolbox:mcp-skills-awareness-begin -->

### MCP & Skills awareness (Claude Code ToolBox)

_Last synced: 2026-11-09T02:38:23.058Z._

- **Full report:** `.claude/cloude-code-toolbox-mcp-skills-awareness.md` in this workspace (auto-overwritten on each scan). Use it as ground truth for configured servers and skill folders.
- **MCP:** For **live tools** in Claude Code, enable the matching server via `/mcp`. Servers are configured in `~/.claude.json` (user) and `.mcp.json` (project).
- **When the user’s task matches a server** (e.g. Confluence work and a **Confluence** / **Atlassian** MCP is listed), **prefer that server id** and plan on tool use—not only file search.
- **Skills:** Folders below contain `SKILL.md`; attach or cite paths in chat when relevant.

#### Workspace MCP

- `d:\Travelly\.mcp.json` _(workspace: Travelly)_ — _file missing_

_No active workspace servers in mcp.json._

#### User MCP

- `C:\Users\Karuna\.claude.json` — _file missing_

_No active user-scoped servers in mcp.json._

#### Project skills

_None found (or no workspace open)._

#### User skills

_None found._

<!-- cloude-code-toolbox:mcp-skills-awareness-end -->

## Who works where (updated 15 Nov 2026)
- One Claude now does both the backend (Backend/) and the frontend (Frontend/). There is no separate UI Claude any more.
- The API contract docs (docs/03-API) were removed from the repo. The backend code is the source of truth for field names and errors. Do not look for docs/ unless the task asks for it.
- When a change touches an API path, a request/response field or an error code, change the backend and the frontend together and run both test suites (Backend: pytest; Frontend: npm test and a build).

## UI rules (apply to every UI change)
- Do NOT change api() call logic, auth/token handling or routing logic unless the task needs it.
- Presentation work: JSX markup/classes, CSS, layout components, styling.
- Target design reference: - Design references: Frontend/design-reference/ (see REFERENCE_MAP.md). Only source of truth.
- Remove the old blue form theme completely; do not leave old styles as fallback.
- Prefer shared components/styles over per-page duplicate CSS.

## FORM & PAGE RULE (applies to EVERY page, every role)
- Every form and page must follow the reference style in Frontend/design-reference/ (glass cards, compact kit controls, red primary buttons, chips, one-line labels with red *).
- NO long scrolling forms. Primary viewport is 1280x585: each page/step/tab must fit with no page scroll and no card scroll. Also check 1366x768, 1920x1080, 2560x1440.
- Long forms are split into steps (stepper + Back/Next) or tabs. Long lists use paging. Long help text goes into tooltips.
- Footer actions sit in one row and never overlap fields. 20px gutters, nothing touches the screen edge.
- No old dark-navy/teal theme panels anywhere.
- Before saying a page is done, test with realistic states (empty, many items, approved/rejected, errors showing) and report measurements.

## TRANSLATION RULE (every page you touch)
- tests/language.test.js must keep passing. Every t("...") string must exist in src/i18n/messages.js with Tamil and Sinhala.
- No raw English text in JSX: wrap it in t().
- While restyling a page, also fix that page's entries: wrap its raw JSX text and add the missing strings to messages.js with both translations.
- Run `npm.cmd test` after each batch and report the language-test count. It must go down, never up.
- Only the UI work (this branch) edits messages.js; backend work must not, to avoid conflicts.