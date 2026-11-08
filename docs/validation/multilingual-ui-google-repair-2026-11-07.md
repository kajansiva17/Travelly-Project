# Multilingual UI and Google sign-in repair - 7 November 2026

**Saved-origin follow-up:** the user subsequently confirmed saving both local origins. A fresh live recheck still gets Google's origin rejection. Corrected a further scoped referrer-policy/measurable-host issue; final live results are API/script 200 and Google button 403 on both origins and both auth pages. Google acceptance and real sign-in remain unverified. See [the recheck report](google-origin-recheck-2026-11-07.md) for current evidence, 24 passing Google browser cases and the external next dependency. Earlier results below remain historical.

## Completed scope

Repaired the multilingual presentation regression using the existing English Travelly theme and the user's screenshots as the visual baseline. Preserved the scenic backgrounds, Journey Pass artwork, logo artwork, glass panels, borders, shadows, colors and form structure. Existing compact registration steps remain in place. Booking, pricing, payment, application/role permissions and database structures were not changed.

Read the current NBP context, Google delivery and viewport follow-up reports, current role/login amendments and the relevant saved Auth extension source (collection pages 224-226). The existing Google account-completion, explicit linking, nonce verification, independent roles and memory-only credential rules remain binding.

### Causes and corrections

- `languages.css` forced Tamil/Sinhala public and authentication navigation into mobile mode below 1500px and overrode the blue menu with a cream background. Removed that language-dependent breakpoint and background. Auth desktop navigation starts at 1024px; public/customer navigation uses a consistent 1280px breakpoint for every language. Narrower menus retain the blue glass theme, bounded height, contrast and accessible controls. Escape closes the main menu and restores focus.
- Long labels were competing with a fixed-size logo and non-shrinking navigation content. Added flexible container sizing, responsive logo allocation/padding/gaps, and wrapping at word boundaries. Public navigation uses more of the available desktop width. Passenger's larger signed-in navigation may use a second row; all destinations remain available. Narrow Owner/Driver/Admin headers reserve space for the language selector and account controls.
- Cards and auth helpers had inherited nowrap/min-content behavior that pushed text outside their boxes. Corrected flex minimum widths, wrapping, script line heights, heading/link flow and login-options wrapping. Operational card headings can place their action on a separate line. Interface typography uses the existing Travelly Sans with Nirmala UI and a platform sans fallback for script coverage; no font or artwork download was introduced.
- Corrected identified Tamil/Sinhala copy, a Sinhala character in the Tamil Rentals label, untranslated fragments, generic-word translations of the Travelly brand, and an overlong Tamil Manual Fulfilment label. The central merged catalogue has 2481 entries. Whole-catalogue checks cover key coverage, placeholders, well-formed Unicode, script contamination and brand retention. Long operational translations retain their existing source catalogue except identified corrections; this is not a claim of independent native-language editorial certification of every sentence.
- Password visibility labels now translate. Password validation stores its individual source messages and translates each on render, so switching language also updates an already displayed combination of errors. Dashboard greetings and textual metric values now translate while names, vehicle labels, numeric values and route destinations remain intact. Application status labels translate without changing their underlying codes. Driver hero copy uses one translatable sentence, retaining the existing English line breaks and allowing natural Tamil/Sinhala sentence order.
- Localized remaining brand/footer accessibility labels, static artwork descriptions, operational notification/profile labels and the Passenger browser title. The accessible profile label preserves the person's supplied name.
- Google script loading now has a bounded failure/retry path. A visible disabled Google control retains its inline icon while loading or unavailable; translated status and retry controls remain readable. The official GIS button is used when ready. Network failures use the existing safe Travelly connection message. Credential callbacks are awaited and guarded against duplicate submission; consumed challenges are renewed when a completed callback leaves the page open. A failure requires a fresh retry instead of reusing a consumed challenge. Credentials remain in memory and are sent through the existing verified backend flow.

## Google live configuration finding and next dependency

The existing local Redis startup helper failed in the sandbox and succeeded with approved escalation, retaining its persistent data. The real API returned 200 for Google challenge, with a configured Web Client ID and nonce. No token, challenge, client secret or environment file contents were printed or changed.

The real browser provider check on `http://127.0.0.1:5173/login`, outside the sandbox, loaded Google's official script (200). Google's button endpoint returned 400 and logged exactly: **The given origin is not allowed for the given client ID.** This is an external OAuth origin configuration blocker. A rendered iframe is not proof of a successful provider sign-in.

The connected browser inventory was also checked read-only using the computer-use workflow. It reported **The browser access host is unavailable**, so the Google Cloud project could not be opened through connected browser access. No Cloud credential, origin, consent or access setting was edited.

Required external correction:

1. Open the existing Web application client in [Google Cloud Clients](https://console.cloud.google.com/auth/clients), matching the application's existing backend `GOOGLE_CLIENT_ID`.
2. Preserve existing entries and add the actual local origins under **Authorized JavaScript origins**: `http://127.0.0.1:5173` and, if used, `http://localhost:5173`. Add the production origin only when the actual deployment is known. Do not guess a production hostname.
3. Save, allow the configuration change to propagate, reload and verify the provider button and real sign-in/signup. The current GIS integration uses a JavaScript popup callback, so inventing a redirect URI is not the fix for this observed origin rejection.

Google's official [setup guide](https://developers.google.com/identity/gsi/web/guides/get-google-api-clientid) documents exact authorized JavaScript origins and the distinction from redirect mode. The [JavaScript reference](https://developers.google.com/identity/gsi/web/reference/js-reference) documents the initialization, nonce, callback and rendered-button APIs.

Live Google account selection/sign-in and account creation were not performed. Existing-account linking and new Passenger completion have automated fixture coverage, not a claim of a successful live provider round trip. Redis must remain running; automatic startup is still separately deferred.

The user selected **I'll update Google Cloud now** after receiving the exact setup explanation in Tamil. This records an intended external action, not confirmation that the origin has been saved. Recheck the real provider after that confirmation; do not infer completion from elapsed time.

## Changed files

Application presentation:

- `Frontend/src/styles/languages.css`
- `Frontend/src/styles/publicHomeGlass.css`
- `Frontend/src/i18n/messages.js`
- `Frontend/src/features/auth/AuthPage.jsx`
- `Frontend/src/features/auth/GoogleSignIn.jsx`
- `Frontend/src/components/components.jsx`
- `Frontend/src/components/NavbarBrand.jsx`
- `Frontend/src/components/RoleDashboards.jsx`
- `Frontend/src/components/ApplicationStatusNotices.jsx`
- `Frontend/src/components/WorkspaceShell.jsx`
- `Frontend/src/pages/PublicPages.jsx`
- `Frontend/src/features/passenger/PassengerDashboard.jsx`

Verification:

- `Frontend/tests/language.test.js`
- `Frontend/tests/browser/auth-google.spec.js`
- `Frontend/tests/browser/languages.spec.js`
- `Frontend/tests/browser/multilingual-layout.spec.js`
- `Frontend/tests/browser/multilingual-zoom.spec.js`
- `.tools/audit-language.mjs`, `.tools/probe-multilingual.mjs`, `.tools/probe-workspace-language.mjs` (local diagnostics; no credentials).

Continuity: this report and `docs/00-READ-FIRST/Travelly_NBP_Codex_Context.md`.

## Verification

- Frontend unit tests: **63 passed**. Includes translation coverage/placeholders/Unicode/brand retention, registration validation, role routes, current permissions and booking-rate validations.
- Backend Google selection: **15 passed, 42 deselected** (`tests/test_auth_extension.py -k google`), using isolated PostgreSQL/Redis fixtures. Covers signed claims, required boolean email verification, signature/challenge replay, Passenger completion, same-email conflict, explicit linking and role preservation. One existing Starlette/httpx deprecation warning.
- Focused Google browser flows: **11 passed on desktop and 11 on mobile**, including missing configuration, temporary failure/retry, registration completion/terms, third-party-email verification, linking, invalid tokens, translated loader failures and duplicate callbacks. GIS and account data are mocked in these tests.
- Auth viewport regression: **5 passed**, covering desktop fit, natural mobile scroll, visible validation, compact registration payload and the hero/search-panel boundary.
- The multilingual matrix checks Home/Login/Register at 1920x1080, 1536x864, 1366x768, 1280x800, 1024x768, 768x1024, 375x812 and 390x844 in all three languages. It checks navigation overlap/overflow, desktop/mobile breakpoints, dark menus, card boundaries and no unnecessary desktop auth scrolling, plus retained login/registration state and translated validation.
- Actual Chrome zoom coverage uses 90%, 100%, 110% and 125% in every language across Home/Login/Register. It checks actual device-pixel ratio/CSS viewport, navigation reachability and auth controls, without CSS zoom/transform shortcuts.
- Desktop/mobile language tests cover public navigation/reload persistence, untouched registration API values, all four workspaces/sidebar destinations and Admin filter enum preservation. Header bounds are checked as well as document width.
- Visual review includes Tamil desktop Home/Login, Tamil mobile Login and Sinhala desktop Register screenshots. Embedded English text in the retained raster artwork is unchanged; its accessible description is translated.

Final focused results:

- Combined desktop delivery run: **50 passed (6.9 minutes)** across `auth-google`, `auth-viewport-fit`, `multilingual-layout`, `multilingual-zoom` and `languages`, with artifacts in `Frontend/test-results/multilingual-delivery-desktop/`.
- After the final accessibility-label changes, the desktop language selection passed all **7 scenarios**. The mobile language selection passed all **7 scenarios (59.2 seconds)** after explicitly waiting for the intended dashboard/Admin shell before interacting. Artifacts are in `Frontend/test-results/multilingual-delivery-language-final/` and `Frontend/test-results/multilingual-delivery-language-mobile-final/` respectively.
- All **11 mobile Google scenarios** passed in `Frontend/test-results/multilingual-delivery-mobile/`. That combined mobile run also contained a language-test navigation timeout, subsequently closed by the explicit route-readiness wait and the passing seven-test mobile language rerun above. It is not described as a clean combined 18-test run.
- Production build: **PASS**, 209 modules; the existing large-chunk advisory remains (approximately 1.34 MB minified JavaScript). Latest frontend unit run: **63 passed**.
- The visible steering-wheel, ticket and key service artwork decoded successfully after normal scrolling; inspected `.tools/multilingual-reviewed-cards-ta.png`. Full-page captures taken before scrolling may show unloaded below-fold lazy images; no image asset was removed or replaced.

Earlier runs exposed real overflow defects that were repaired; one interrupted parallel run also had a Playwright trace-directory collision. Intermediate source edits/live reloads and tests that interacted before the destination shell settled also caused timeouts. Final checks used separate artifact directories and explicit route readiness. Intermediate failures are not counted as passing checks.

## Deferred scope and blockers

The Google Cloud origin correction and live provider round trip remain blocked by external project access/configuration. Other pending project work (session restoration, search pagination, terminal trip/payment flows, CF01-CF12, service expansion and production provisioning) was not started. No backend application source, `.env`, live account, role, application table or migration was changed.
