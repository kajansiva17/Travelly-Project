# Landing PNG correction and shared dashboard branding — 7 November 2026

## Completed scope

Corrected the existing three public landing pages using the supplied standalone PNG archive and transparent branding. This supersedes the rejected crop-assembled implementation described in `landing-reference-replacement-2026-11-07.md`.

The latest six-image mapping is: Images 1–3 are defect examples; **Image 4 is Owner, Image 5 is Home, Image 6 is Driver**. Existing routes remain:

| Page | Route |
| --- | --- |
| Home / Passenger | `/` |
| For Owners | `/for-owners` |
| For Drivers | `/drive-with-us` |

The user subsequently authorized applying the supplied logo parts to **all four dashboard headers** and replacing the public navbar's Driver/Owner icons. Dashboard layouts, sidebar destinations, account controls and application logic were preserved. The shared brand component also supplies other existing headers; no authentication form, backend, `.env`, database, approval rule or booking workflow was changed.

## Corrections

- Removed the hero-fragment array and all corresponding fragment positioning styles. Each hero now contains **one continuous scene image**, filling its section from viewport edge to viewport edge with proportional `object-fit: cover` framing.
- Replaced all 21 small screenshot card crops with the supplied native card artwork. Added the supplied 768px alternatives via `srcset`, real image dimensions and appropriate lazy loading. Reviewed the family/driver/vehicle framing and adjusted focal positions.
- Removed the 1100px inset-image constraint. Header, hero text, search panel and main grids adapt using common gutters and a bounded 1320px content width. At 1260 CSS pixels the main grid grows from 876px to approximately 1164px, and hero text moves from x=200px to approximately x=63px.
- Hero heights respond to both viewport width and available height. The shorter desktop context keeps Home's search controls visible without changing zoom. Larger desktop scenes retain the important subjects with deliberate cover cropping.
- Hero copy has no background fill, backdrop blur, border or shadow panel. Only continuous light fades on the Owner/Driver scenes and a bottom transition remain; the photographs themselves have no blur or color filter.
- Refined English heading proportions and Driver introduction wrapping against the references. Home's numbered steps now give headings and descriptions separate grid rows, preventing text from entering the icon area at desktop widths and in longer translations.
- Replaced flattened landing logo crops with the supplied transparent standard and PUBLIC DRIVER PNGs. `object-fit: cover` frames their transparent canvas margins; no baked background, recoloring filter or screenshot patch remains on these logos.
- The Passenger, Owner, Driver and Admin shared dashboard headers now use the supplied navy/red dial and clean navy/red wordmark with the matching original glossy red needle. Updated the gauge pivot geometry while retaining the existing spring motion, link destinations and reduced-motion behavior. A small light shadow separates the navy artwork from the existing dark glass without changing its pixel colors or placing a rectangle behind it.
- Public For Drivers/For Owners links now use the supplied PNG icons. Transparent margins are framed to consistent visible sizes; selected icons become white on the existing red active pill. No removed operational public links were reintroduced into dashboard navigation.
- Footer links, copy, FAQs, search values, role-specific authentication intent and language persistence remain real HTML and retain their existing behavior. Footer scenery edge details stay at the viewport edges with soft inward transitions, rather than floating inside the centered content.

## Asset provenance and qualifications

Imported **48 scene/card PNGs**: 24 native assets plus 24 supplied 768px alternatives. Heroes are **1672×941**; native cards are **1536×1024**. All imported bytes, dimensions and SHA-256 hashes were verified. Production files are separate from the approved full-page reference images:

- `Frontend/public/images/travelly/landing-scenes-2026-11-07/`
- `Frontend/public/images/travelly/branding/approved-2026-11-07/`
- `Frontend/public/references/landing-2026-11-07/`

The PNG archive explicitly describes its artwork as **reconstructed from the reference designs**, with differences in poses, scenery, vehicle details, image edges and framing. The user supplied these files in response to the missing-artwork request. They are used as supplied; this task did not regenerate, redraw, upscale or sharpen the source asset files. They are not represented as the exact original reference photography.

Seven branding/icon PNGs were copied without altering their pixel bodies and verified against the import manifest. All have transparent alpha. The glossy red needle is the matching existing original shown in the user's upload, rather than the separate small flat-blue needle variant found in the upload folder.

The uploaded footer strips contain flattened logos/links/separators and are **reference material only**. They are not displayed as the webpage footer. The approved lower scenery's small native edge crops are retained; a separate complete panorama was not supplied.

## Chrome validation and screenshots

Fresh Chrome contexts used default **100% browser zoom**. Captures record CSS `zoom: 1` and `visualViewport.scale: 1`. Device scale factor emulates display density; it does not change browser/CSS zoom. No page-level scaling transform is used.

The supplied wider defect screenshots appear consistent with approximately 1.5 device-pixel density. This is an inference from their pixel dimensions and header/text sizes, so both a comparable density context and a genuinely wider CSS viewport were checked:

| Context | CSS viewport | Device scale factor | Screenshot pixel width |
| --- | --- | --- | --- |
| Approved reference width | 948×1659 | 1 | 948 |
| Comparable desktop/display density | 1260×588 | 1.5 | 1890 |
| Wide desktop | 1880×900 | 1 | 1880 |
| Mobile | 390×844 | 1 | 390 |

All three pages were captured full-page in every context and inspected from header to footer. Actual full-page image heights follow content; the table specifies viewport dimensions. All twelve captures have full-width scene boxes and no horizontal document overflow. Metrics are saved in [delivery/metrics.json](landing-correction-2026-11-07/delivery/metrics.json).

| Page | Reference-width capture | Comparable desktop | Wide desktop | Mobile |
| --- | --- | --- | --- | --- |
| Home | [948px](landing-correction-2026-11-07/delivery/home-reference.png) | [1260px, DPR 1.5](landing-correction-2026-11-07/delivery/home-desktop-display150.png) | [1880px](landing-correction-2026-11-07/delivery/home-wide-desktop.png) | [390px](landing-correction-2026-11-07/delivery/home-mobile.png) |
| Owner | [948px](landing-correction-2026-11-07/delivery/owner-reference.png) | [1260px, DPR 1.5](landing-correction-2026-11-07/delivery/owner-desktop-display150.png) | [1880px](landing-correction-2026-11-07/delivery/owner-wide-desktop.png) | [390px](landing-correction-2026-11-07/delivery/owner-mobile.png) |
| Driver | [948px](landing-correction-2026-11-07/delivery/driver-reference.png) | [1260px, DPR 1.5](landing-correction-2026-11-07/delivery/driver-desktop-display150.png) | [1880px](landing-correction-2026-11-07/delivery/driver-wide-desktop.png) | [390px](landing-correction-2026-11-07/delivery/driver-mobile.png) |

Dashboard header captures use the existing mocked workspace fixtures, not live private account data:

| Dashboard | Desktop 1366px | Mobile 390px |
| --- | --- | --- |
| Passenger | [Header](landing-correction-2026-11-07/dashboard-brand/passenger-brand-1366.png) | [Header](landing-correction-2026-11-07/dashboard-brand/passenger-brand-390.png) |
| Owner | [Header](landing-correction-2026-11-07/dashboard-brand/owner-brand-1366.png) | [Header](landing-correction-2026-11-07/dashboard-brand/owner-brand-390.png) |
| Driver | [Header](landing-correction-2026-11-07/dashboard-brand/driver-brand-1366.png) | [Header](landing-correction-2026-11-07/dashboard-brand/driver-brand-390.png) |
| Admin | [Header](landing-correction-2026-11-07/dashboard-brand/admin-brand-1366.png) | [Header](landing-correction-2026-11-07/dashboard-brand/admin-brand-390.png) |

## Tests

- **31 desktop browser tests passed in the final complete run**: `reference-landings.spec.js` and `approved-brand-assets.spec.js`, output `test-results/landing-brand-verified`.
- Coverage includes all four dashboard brands at two widths, native asset loading, gauge pivot alignment, hover/reduced-motion behavior, transparent landing logos, supplied role icons, one full-width scene per page, unmasked hero copy, exact interface copy, active nav, auth intent, search handoff and validation, language-state retention, keyboard tabs/FAQs and honest unavailable actions.
- English, Tamil and Sinhala responsive cases each visit 320, 390, 768, 948 and 1366px. They check navigation/control bounds, text clipping, hero clearance and Home step-description/icon intersections. The five-visit PNG-heavy cases have a 60-second budget; assertions remain enabled.
- **9 mobile interaction tests passed**, output `test-results/landing-brand-mobile-delivery`: role-specific login links, FAQ keyboard controls, valid/invalid departure selection, real Hire seed handoff, unsupported-service notices and dashboard isolation.
- **63 frontend unit tests passed** and the final production build passed. Vite retains its pre-existing large-chunk advisory.
- Verified 48 supplied scene/card file hashes and dimensions, seven branding/icon hashes and alpha channels, and all twelve final viewport metrics. No backend tests were run because backend behavior was untouched.

## Remaining differences and next dependency

This is substantially closer and removes the crop-assembled hero defect; it is **not an exact pixel reproduction**. Remaining qualifications:

1. The supplied reconstructed photos differ from the approved reference's people, vehicle positioning, scenery and photographic signage. Exact original clean scene/card assets are required to eliminate those differences. No further imagery was regenerated here.
2. The largest supplied hero is 1672px wide. It is sampled about 12–13% above native width in the 1880px / 1890px physical desktop captures. No artificially upscaled source is labelled as a sharp original; larger native originals are needed for greater detail at those densities.
3. Complete separate Home coastal, Driver tea-estate and Owner depot/garden lower panoramas are still unavailable. Edge foliage and CSS color transitions approximate those lower backgrounds; the center scenery cannot be recovered from flattened footer strips.
4. The actual reference UI font and original non-navbar icon set remain unverified. The pages reuse the existing bundled Latin font plus Nirmala UI fallback, within two UI font families. Some glyph metrics, card wrapping, icon shapes and glass/shadow details therefore differ.

These source assets are the next dependency for tighter visual matching. Building unavailable booking/finance/maintenance modules, changing dashboard layouts and resolving the separate external Google-origin configuration remain deferred from this visual/branding scope.

## Changed files

- `Frontend/src/features/landing/ReferenceLandingPages.jsx` — continuous hero image, native/responsive card artwork, transparent logos and supplied navigation icons.
- `Frontend/src/features/landing/landingAssets.js` — explicit image mapping and native/responsive source metadata.
- `Frontend/src/features/landing/referenceLanding.css` — responsive composition, scene framing/transitions, typography, step layout and transparent branding styles.
- `Frontend/src/components/NavbarBrand.jsx` and `Frontend/src/styles/navbarSpeedometer.css` — shared dashboard identity artwork, pivot calibration and contrast shadow.
- `Frontend/public/images/travelly/landing-scenes-2026-11-07/` and `branding/approved-2026-11-07/` — supplied assets and import manifests.
- `Frontend/tests/browser/reference-landings.spec.js` and `approved-brand-assets.spec.js` — focused layout, asset, interaction and shared-brand checks.
- `.tools/landing-reference-2026-11-07/audit-correction.mjs` and related asset-audit artifacts — reproducible Chrome captures and measurements.
- This report, its screenshot directory, the prior delivery's supersession note, asset READMEs and the NBP continuity context.
