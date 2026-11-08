# Landing alignment and responsive spacing — 7 November 2026

## Completed scope

Applied the user's latest spacing correction to the three existing public pages: Home `/`, For Drivers `/drive-with-us`, and For Owners `/for-owners`. This follow-up intentionally gives the pages more vertical room than the older 948 × 1659 flattened references. Page height follows the real content rather than compressing the footer into that reference canvas.

- One centered navbar, maximum 1320px wide, with responsive side gutters and a 24px desktop / 16px phone top margin. All three pages share the same geometry. The mobile menu expands inside the header; the existing measured header height moves hero content below it.
- Hero text starts 36px below the desktop header and 32px below the phone header. Width- and height-aware hero minimums preserve room for content. No fixed maximum height crops the copy, controls or following section. Background images retain proportional cover framing.
- Home search is now a compact, rounded white/light glass card, maximum 1120px wide, with a soft shadow. Tabs sit above four aligned desktop form columns. On phones the fields form two columns. The card participates in normal document flow, stays inside its hero, and precedes the next section. It is fully above the fold at the checked 1260 × 588 and 1880 × 900 desktop viewports. Phones scroll naturally through the hero image and complete search card.
- All main sections use the same centered maximum content width, responsive 28–48px top/bottom padding, 20px desktop / 18px phone card gaps, and clear heading separation. Feature strips and CTA have larger internal padding and separate section space.
- FAQ cards now have a 108px minimum desktop height (116px on phones), generous padding, 16px between cards, 10px question/answer separation and improved line heights. Icons and arrows are vertically centered. Initially open state, accordion toggles and keyboard behavior remain unchanged.
- Long translated labels wrap instead of extending the page horizontally. Small-phone Driver cards stack artwork above copy for readable labels. Owner onboarding arrows have a dedicated gap between steps, verified after visual review.

Preserved all wording, supplied artwork and transparent logos, red active states, existing routes, role-intent authentication links, language persistence, FAQ interactions and real search state/date handoff. Dashboard pages, shared dashboard branding/search, backend, `.env`, records and business rules were not changed in this task.

## Validation

Chrome was run locally at default 100% browser zoom. Captures use CSS zoom 1 and visual viewport scale 1, with no whole-page transform. All twelve captures have full-width hero scenery and no document horizontal overflow.

| Context | CSS viewport | Device pixel ratio |
| --- | --- | --- |
| Reference width | 948 × 1659 | 1 |
| Short desktop / high-density display | 1260 × 588 | 1.5 |
| Wide desktop | 1880 × 900 | 1 |
| Phone | 390 × 844 | 1 |

The 1.5 device pixel ratio is display density, not browser zoom. Additional automated layouts cover 320px, 768px and 1366px widths; English, Tamil and Sinhala are checked at five widths.

- Full desktop landing and spacing suite: **24 passed**. Covers content, navigation, role-intent links, all three languages, responsive bounds, hero/menu clearance, section padding, FAQ alignment, Home search containment/date validation/state handoff, keyboard tabs and FAQs, unavailable-action notices and dashboard isolation.
- Mobile interaction suite: **9 passed** with the mobile browser project.
- After the final Owner arrow adjustment, targeted spacing/Owner reference/three-language checks: **7 passed**. These repeat relevant cases from the 24-test suite, rather than representing seven additional unique tests.
- Production build: passed. Vite retains its existing advisory about bundles larger than 500kB.
- No backend tests or live authentication/booking actions were required for this CSS-only application change.

Full-page renders were reviewed through the footer for hero clearance, search containment, section rhythm, grids, FAQs and CTA. Final screenshots and measurements:

| Page | Reference | Short desktop | Wide desktop | Phone |
| --- | --- | --- | --- | --- |
| Home | [PNG](landing-correction-2026-11-07/spacing-delivery/home-reference.png) | [PNG](landing-correction-2026-11-07/spacing-delivery/home-desktop-display150.png) | [PNG](landing-correction-2026-11-07/spacing-delivery/home-wide-desktop.png) | [PNG](landing-correction-2026-11-07/spacing-delivery/home-mobile.png) |
| Drivers | [PNG](landing-correction-2026-11-07/spacing-delivery/driver-reference.png) | [PNG](landing-correction-2026-11-07/spacing-delivery/driver-desktop-display150.png) | [PNG](landing-correction-2026-11-07/spacing-delivery/driver-wide-desktop.png) | [PNG](landing-correction-2026-11-07/spacing-delivery/driver-mobile.png) |
| Owners | [PNG](landing-correction-2026-11-07/spacing-delivery/owner-reference.png) | [PNG](landing-correction-2026-11-07/spacing-delivery/owner-desktop-display150.png) | [PNG](landing-correction-2026-11-07/spacing-delivery/owner-wide-desktop.png) | [PNG](landing-correction-2026-11-07/spacing-delivery/owner-mobile.png) |

[Capture dimensions and page metrics](landing-correction-2026-11-07/spacing-delivery/metrics.json). Earlier screenshot directories are historical; use `spacing-delivery` for this follow-up.

## Changed files

- `Frontend/src/features/landing/referenceLanding.css`: shared navbar, flowing hero/search, containers, spacing, card wrapping, FAQ/CTA and responsive rules.
- `Frontend/tests/browser/landing-spacing.spec.js`: regression checks for real geometry, safe menu/header clearance, search containment, FAQ alignment, Owner arrow spacing and natural scrolling.
- `Frontend/tests/browser/reference-landings.spec.js`: replace the obsolete exact footer-y expectation with a content-following footer clearance check.
- This report and `docs/00-READ-FIRST/Travelly_NBP_Codex_Context.md`.
- Twelve full-page screenshots and `metrics.json` under `docs/validation/landing-correction-2026-11-07/spacing-delivery/`, captured with the existing `.tools/landing-reference-2026-11-07/audit-correction.mjs` helper.

## Deferred scope, blockers and next dependency

No blocker remains for this layout correction. Artwork differences and original-asset qualifications from [the PNG/branding delivery](landing-png-brand-correction-2026-11-07.md) remain: the supplied scenes are reconstructions, original full lower-page panoramas and verified original font/non-navbar icon sources are unavailable. No imagery was regenerated or replaced here. Exact artwork parity would require those sources; further application modules and live Google provider verification remain outside this task.
