# Landing card alignment — 7 November 2026

## Completed scope

The user identified unevenly aligned cards and requested more consistent gaps on Home, then extended the same correction to For Drivers and For Owners. Updated the existing public routes `/`, `/drive-with-us` and `/for-owners`.

- Every service-card group uses equal-width, equal-height grid tracks, including across multiple rows. Cards in different groups retain their role-specific column counts and proportions.
- Card gaps are consistently 24–36px; card body padding, title alignment and description line-height are consistent. Text can grow without clipping rather than being forced into a fixed-height card.
- Driver's horizontal cards keep their image on the left and stretch that image to the card's height. Their small-phone layout remains stacked.
- At tablet widths, the four-card Home planning and Owner fleet grids use two columns for adequate space. On phones up to 480px, the Owner fleet cards use one column so long headings remain readable.
- The Home hero and search panel, supplied imagery, card content, glass styling, routes, role-specific links, FAQ interactions and booking/search logic remain in place. Dashboard pages, backend, `.env`, data and business rules were not changed.

## Validation

- Desktop Chrome: **12 passed** — nine card geometry cases (three pages × English/Tamil/Sinhala) covering 320, 390, 768 and 1280px widths, plus three existing page-spacing/hero checks. Geometry checks verify equal card dimensions within each group, at least 24px grid gaps, no card overlap, text containment and no horizontal document overflow.
- After the final Owner phone readability adjustment: **3 Owner language cases passed again**. These are repetitions of cases in the first run.
- Existing content, role-specific login/signup links, keyboard FAQ behavior, Home search/date handoff and unavailable-action notices: **11 passed**.
- Production build passed; Vite continues to show its existing large-chunk advisory. No backend tests were needed for this styling-only application change.
- Twelve full-page Chrome captures at default 100% browser zoom cover 948 × 1659, 1260 × 588 at device pixel ratio 1.5, 1880 × 900 and 390 × 844; none has horizontal document overflow. Captures were inspected through the footer, including the final Owner phone layout.

| Page | Reference width | Short desktop | Wide desktop | Phone |
| --- | --- | --- | --- | --- |
| Home | [PNG](landing-correction-2026-11-07/cards-delivery/home-reference.png) | [PNG](landing-correction-2026-11-07/cards-delivery/home-desktop-display150.png) | [PNG](landing-correction-2026-11-07/cards-delivery/home-wide-desktop.png) | [PNG](landing-correction-2026-11-07/cards-delivery/home-mobile.png) |
| Drivers | [PNG](landing-correction-2026-11-07/cards-delivery/driver-reference.png) | [PNG](landing-correction-2026-11-07/cards-delivery/driver-desktop-display150.png) | [PNG](landing-correction-2026-11-07/cards-delivery/driver-wide-desktop.png) | [PNG](landing-correction-2026-11-07/cards-delivery/driver-mobile.png) |
| Owners | [PNG](landing-correction-2026-11-07/cards-delivery/owner-reference.png) | [PNG](landing-correction-2026-11-07/cards-delivery/owner-desktop-display150.png) | [PNG](landing-correction-2026-11-07/cards-delivery/owner-wide-desktop.png) | [PNG](landing-correction-2026-11-07/cards-delivery/owner-mobile.png) |

[Capture metrics](landing-correction-2026-11-07/cards-delivery/metrics.json). Device pixel ratio represents display density, not browser zoom.

## Changed files and remaining dependency

- `Frontend/src/features/landing/referenceLanding.css` — card grid sizing, spacing, content alignment and responsive Owner/Driver adaptations.
- `Frontend/tests/browser/landing-card-alignment.spec.js` — cross-language and responsive card geometry/containment checks.
- This report, twelve screenshots and metrics, and `docs/00-READ-FIRST/Travelly_NBP_Codex_Context.md`.

No blocker remains for this scoped layout correction. Exact matching to the original artwork still depends on the clean source assets described in [the earlier PNG/branding report](landing-png-brand-correction-2026-11-07.md); no new imagery was generated or substituted.
