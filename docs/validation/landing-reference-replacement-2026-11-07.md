# Approved landing-reference replacement — 7 November 2026

**Superseded:** the user rejected the rendered crop-based result. Do not restore its hero-fragment assembly or flattened logo crops. The current correction uses user-supplied standalone PNGs and transparent branding; see [the PNG and dashboard-brand correction report](landing-png-brand-correction-2026-11-07.md).

## Completed scope and approved mapping

Replaced the three public landing entry components within the existing React/Vite application. The user resolved the contradictory initial written mapping by explicitly choosing the roles shown in the images:

| Reference | Page | Existing route |
| --- | --- | --- |
| `Refined Coastal Travel Vehicle Lineup.png` | Home / Passenger | `/` |
| `Travelly driver landing page in Sri Lanka.png` | For Drivers | `/drive-with-us` |
| `Travelly scheduled tickets landing page.png` | For Owners | `/for-owners` |

This new light-glass approval supersedes the old dark public landing appearance only. Dashboard, workspace, auth-page components, auth/role permissions, backend, `.env`, booking calculations and database structures were not changed.

Read the NBP context, relevant prior public/auth delivery, current account/role entry decisions and approved Long-distance/search contract boundaries. The approved marketing references do not authorize implementing future ticket, rental, financial, maintenance or trip-completion workflows.

## Implementation

- New landing-only module and scoped stylesheet; `App.jsx` changes only its three public page imports. The original shared `PublicPages.SearchPanel` used by PassengerDashboard is preserved.
- Exact English visible headings, descriptions, card labels, steps, helper sentences, FAQ answers, CTA labels and footer labels are selectable HTML. Navbar active states follow the existing routes. All nine FAQs start open, with real expanded-state buttons, labelled regions, Enter/Space and arrow/Home/End navigation.
- Header links and CTA actions retain general Passenger registration and explicit `?journey=owner` / `?journey=driver` auth intent. Existing signed-in public-role redirects remain authoritative.
- Home Hire/Tickets/Rentals tabs preserve the existing handoff and unavailability behavior. Pickup/destination are actual inputs and can be swapped. The displayed reference date `20 Jul 2024` is an example, not a selected past itinerary. An actual valid future local departure date/time is required before the existing `/hire` seed handoff. User-entered locations and departure survive a language change.
- Ticket and rental checkout, unsupported hire types, reels, expense entry and maintenance entry show honest unavailable notices. Existing operational card links use existing protected workspace routes, including existing placeholders where applicable. Help opens the FAQ; unpublished Terms/Privacy/Contact information is reported honestly instead of inventing policies, contacts or successful submissions.
- Reused language persistence/subscription and added the new copy to the centralized English-keyed Tamil/Sinhala catalogue. The desktop/mobile breakpoint is viewport-based at 761px, with wrapping for translated labels. No language-dependent switch to mobile navigation.
- The header reports its measured height to its own landing root, keeping tall translated navigation clear of the hero. Translated Home copy and its search panel use normal document flow. Final responsive tests check header/hero, hero/search and hero/content separation as well as horizontal bounds.
- Search-tab captions and footer labels explicitly wrap within their controls, including long Tamil words. Responsive checks inspect each control's internal scroll width as well as its viewport bounds, so root overflow clipping cannot conceal a failing label.
- Reused `/fonts/jakarta-latin.woff2` through a landing-only alias, requesting its fuller weight range and allowing weight synthesis. The script fallback is Nirmala UI: two UI font families within these pages. The screenshot font has not been identified or verified as this font.
- Copied all three complete references byte-for-byte into `Frontend/public/references/landing-2026-11-07/`, with SHA-256 and dimensions in the manifest. Production imagery is separate under `Frontend/public/images/travelly/landing-2026-11-07/`, with a crop provenance manifest and README.
- Existing assets were inspected first; they depict the old night scenes and different people/vehicles, so they were not substituted. Used clean approved photo/logo crops, real SVG icons and CSS glass/gradient surfaces. No whole-page screenshot, image containing card captions used as an interactive card, invisible screenshot hotspots, regenerated imagery or unrelated photo substitutions.

## Visual comparison and iteration

All references are **948 × 1659**. Local Chrome full-page captures were inspected against each supplied reference. Iterated heading weight, Owner hero wrapping, section/CTA heights, glass borders, image positioning, mobile photo framing, translated navbar bounds and date-popover stacking.

Final English layout has the footer at y=1603 for Home/Driver and approximately y=1605 for Owner; its height is 56px. Reference footer starts at y=1603. Similar total heights are layout evidence, not a claim of pixel accuracy. Main section positions and content order track the references; exact glyph widths and some card wrapping remain different.

Saved browser screenshots:

| Page | Reference-size render | Mobile render |
| --- | --- | --- |
| Home | [948px](landing-reference-2026-11-07/home-948x1659.png) | [390px](landing-reference-2026-11-07/home-en-390.png) |
| Driver | [948px](landing-reference-2026-11-07/driver-948x1659.png) | [390px](landing-reference-2026-11-07/driver-en-390.png) |
| Owner | [948px](landing-reference-2026-11-07/owner-948x1659.png) | [390px](landing-reference-2026-11-07/owner-en-390.png) |

Additional mobile examples: [Tamil Home](landing-reference-2026-11-07/home-ta-390.png), [Sinhala Home](landing-reference-2026-11-07/home-si-390.png), [Sinhala Owner](landing-reference-2026-11-07/owner-si-390.png).

## Validation

- `npm test`: **63 passed**, including translation-key coverage, script/brand/placeholder integrity and existing auth, role and input checks.
- `reference-landings.spec.js`, desktop: **21 passed**. Includes exact English content/initial FAQ state, reference-size screenshots, image loading, JS errors, active nav, role-specific auth URLs, keyboard FAQ/tab controls, actual search seed, invalid-date rejection, language-state retention, honest unavailable actions and a four-dashboard isolation smoke check using the existing mocked session helper.
- Responsive cases visit all three pages in English, Tamil and Sinhala at **320, 390, 768, 948 and 1366px**. Checked document bounds, visible navbar controls and non-overlap; captured 390px full-page renders.
- Mobile Chrome/Pixel emulation: **9 passed**, covering role-specific auth links, FAQ keyboard operation, actual date/input/search handoff, unavailable tabs/cards and dashboard isolation. An initial mobile test incorrectly tried to use the hidden language selector; corrected it to open/close the actual menu.
- Final visual-only refinement removes internal crop-join fading while retaining exposed-edge blending; three reference-capture checks and the production build were rerun afterward (see final status below).
- Verified the three original-reference SHA-256 hashes and all **44** production PNG crop pixel bodies against their declared source rectangles.
- Production build passed; Vite retains its existing large-chunk advisory. No backend tests were run because backend code and contracts were untouched. Browser workspace checks use existing test fixtures; this task does not establish live Google sign-in or operational completion of placeholder modules.

## Remaining differences, deferred scope and next dependency

This is a real, functioning UI approximation of the approved references; it is **not pixel-exact**. Remaining material visual differences are the CSS-filled sky/fog areas, crop seams and partial lower scenery, flattened logo backgrounds, font metrics/line wrapping, some icon shapes and precise glass/shadow details. Source card photos match the approved crop areas, but the screenshots cannot supply imagery hidden behind their text.

The exact clean assets still required are:

1. Home: complete coastal/lighthouse/palm/fleet hero without overlaid text/search UI, plus the full lower coastal road/garden panorama behind FAQ/CTA.
2. Driver: complete tea-estate road/driver/white-van hero without overlaid text, plus the full lower tea-estate panorama.
3. Owner: complete depot/fleet/tablet-user hero without overlaid text, plus the full lower depot/garden panorama.
4. Transparent original standard Travelly logo with the vehicle/tickets/rentals tagline and the PUBLIC DRIVER variant, preferably SVG or high-resolution PNG.
5. The actual licensed screenshot UI font files/name and original vector icon set. Font identity cannot be established reliably from these flattened screenshots.

No approved imagery was regenerated. Replacing the bounded crops/gradients with these original clean assets is the next visual dependency. Building the unavailable business modules, publishing legal/contact information, changing dashboards and resolving Google's external OAuth-origin rejection remain outside this completed landing scope.

## Changed files

- `Frontend/src/App.jsx` — public landing import only.
- `Frontend/src/features/landing/ReferenceLandingPages.jsx`, `landingContent.js`, `referenceLanding.css` — components, approved copy/action mapping and scoped styles.
- `Frontend/src/i18n/messages.js`, `messages.landing.js` — central catalogue merge and new translations.
- `Frontend/public/references/landing-2026-11-07/` — original reference copies and manifest.
- `Frontend/public/images/travelly/landing-2026-11-07/` — clean crop production assets, provenance and limitations.
- `Frontend/tests/browser/reference-landings.spec.js` — focused browser coverage and captures.
- `.tools/landing-reference-2026-11-07/` — extraction/capture and asset-inspection tools/artifacts.
- This report, its screenshot directory and the NBP context continuity entry.

Final delivery verification: the complete **21-test desktop suite passed again** after measured-header/translated-flow and control-wrapping corrections. The **9 mobile interaction checks passed again** after control wrapping. Then **6 English reference/responsive checks passed** after refining the role-specific desktop hero CTA dimensions and footer alignment, and **2 Tamil/Sinhala responsive cases passed** after stacking mobile tab icons above their labels (five widths each). Refreshed all six English delivery captures and translated Home examples from these last runs. Frontend unit tests remain **63 passed**; the final production build passed. These supplementary runs repeat relevant cases after refinements rather than representing additional distinct business features.
