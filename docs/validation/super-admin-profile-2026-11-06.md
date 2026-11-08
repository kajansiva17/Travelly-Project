# Super Admin Profile and navigation - 6 November 2026

## Completed scope and authority

Implemented the user's explicit Super Admin request in the existing Admin shell and existing `/account?workspace=admin` route. This instruction supersedes the earlier general-account UI only for Admin Profile. Consulted current NBP context, saved relevant account/profile report (compilation pages 290-291), Final Decisions (page 8), Auth profile/user/API source and users dictionary (including page 28). Exact scoped API/storage behavior is recorded in [03H](../03-API/03H-TRAVELLY-SELF-PROFILE.md).

- Admin top-right identity retains avatar, full name and Super Admin label, links directly to Profile, and contains no dropdown or chevron. Owner/Driver account menus are retained.
- Sidebar Profile opens the same route; Dashboard, Settings and Logout retain their existing destinations/actions. Settings is titled Account settings for Admin.
- Centered navy profile card offers upload/change/remove avatar, full-name/mobile editing, read-only email and role, Save Changes and Cancel. Edit mode uses accessible labels, keyboard focus, validation/error feedback and save status. Cancel discards unsaved changes. Successful saves update the navbar without another account or role mutation.
- Admin Profile does not mount verification/Google linking, password/confirmation controls, private-document sections, retained-file buttons, dashboard returns or its own Sign Out. Existing security forms remain available in Settings. General/Owner/Driver profile/document functionality remains mounted in its existing contexts.
- New self-profile update endpoint uses the existing user row, authenticated approved ADMIN checks, locked version checking, existing name/phone validation and atomic unique-phone conflict handling. The server rejects client email/role/security fields. Changed phones do not inherit old verification. Existing ACTIVE-account verification constraints remain enforced.
- Photo uploads are validated/normalized on the server to metadata-free JPEG thumbnails, stored as bounded data URLs in the existing profile_image_url TEXT column. No table, column, migration, public user-photo endpoint, filesystem/storage key or external provider was added. No actual `.env` or customer account was edited.
- Restarted only the identified local Travelly API with its existing startup command so the new endpoint is available through the API and frontend proxy. An intermediate restart guard refused a command match because of trailing whitespace and stopped nothing; the subsequent verified-process restart succeeded.

## Changed files

Frontend:

- `Frontend/src/components/WorkspaceShell.jsx` - Admin direct identity link and in-memory saved-profile update.
- `Frontend/src/pages/AccountPage.jsx` - select the Admin presentation within the existing page.
- `Frontend/src/features/admin/AdminProfile.jsx` - compact editor/photo controls.
- `Frontend/src/components/RoleDashboards.jsx` - Admin Account settings title.
- `Frontend/src/styles/adminProfile.css` and `Frontend/src/App.jsx` - scoped responsive styling/import.
- `Frontend/tests/browser/admin-profile.spec.js` - interaction, navigation, errors and viewport coverage.
- `Frontend/tests/browser/profile-context.spec.js` - keep Owner/Driver document assertions, move Admin-specific coverage to the new tests, update expired Admin profile heading.
- `Frontend/tests/browser/redesign.spec.js` - expect the direct Admin link while retaining Owner/Driver menus.
- `Frontend/tests/browser/helpers/redesign.js` - explicitly navigate shared Passenger tests there after existing Admin-first general login; no application login logic changed.

Backend:

- `Backend/app/api/routers/api.py` - self-profile PATCH.
- `Backend/app/schemas/profile.py` - strict allowlisted profile update.
- `Backend/app/services/profile_image.py` - bounded raster validation and metadata stripping.
- `Backend/app/main.py` - bounded JSON size allowance only for profile PATCH uploads.
- `Backend/tests/test_profile_update.py` - persistence/security/version/contact/image coverage.

Documentation: `docs/03-API/03H-TRAVELLY-SELF-PROFILE.md`, NBP context and this report. Earlier worktree changes were preserved.

## Verification

- Backend `test_profile_update.py` plus existing successful account/login/logout, refresh replay and fail-closed session tests: **6 passed** (31.27 seconds), actual PostgreSQL/Redis with isolated fixture schemas/namespaces. Includes role/security invariance, same user identity, avatar normalization/removal, persistence, unauthorized/non-Admin rejection, invalid/extra fields, stale versions, duplicate contacts and phone verification boundaries.
- New `admin-profile.spec.js`: **4 desktop + 4 mobile passed**. Includes direct navbar/sidebar navigation, security UI removal, Settings retention, logout, save/cancel, upload/remove, navbar refresh, save errors and responsive layout.
- Screenshots at 1920x1080, 1366x768, 768x1024, 390x844 and 320x640. Desktop/mobile screenshots visually inspected; no horizontal page overflow. Standard Chrome zoom was used. Verification artifacts under `.tools/admin-profile-2026-11-06/` and `.tools/admin-profile-mobile-2026-11-06/` contain synthetic fixture identities only.
- Seven-screen production-artwork/navigation regression: **1 passed** (22.5 seconds).
- Workspace route unit tests: **3 passed**.
- Production build: **passed** (200 modules). Existing >500 kB bundle advisory remains.
- Broader `profile-context.spec.js` desktop suite: **10 passed, 2 failed**. Passing coverage includes Owner/Driver profile/evidence/settings/retained-file navigation, general profile, Admin guarded entry/no privilege grant, Google existing-account entry and expired profile sessions. Remaining failures are the legacy Owner onboarding waiting-heading expectation and Admin verification-return login query preservation. Their onboarding/auth-flow implementations were not changed in this task; this broader suite is not reported as passing. Artifacts: `.tools/admin-profile-regression-2026-11-06/`.
- Initial browser runs failed because the old shared helper expected Passenger content immediately after general Admin login. Corrected that fixture navigation, reran all new Profile tests and the broader suite; final results are listed above.
- Existing TestClient deprecation/Node colour notices remain non-failing. Checked tracked changed-file whitespace; no whitespace error.

## Deferred scope, blockers and next dependency

Requested Admin Profile scope is complete. The two broader onboarding/verification regression failures remain separately scoped; they do not block profile editing/navigation. No real customer profile, uploaded photo or live Google sign-in was exercised. No automatic Redis startup service or unrelated dashboard operational module was added. Reload the frontend and sign in again if needed under the existing memory-only session policy; local API has been refreshed to activate saves.
