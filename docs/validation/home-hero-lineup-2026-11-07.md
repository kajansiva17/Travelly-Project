# Home hero and search card — 7 November 2026

## Completed scope

Adjusted Home `/` to follow the user's second image: the supplied coastal vehicle lineup is framed so the bus, van, car and tuk-tuk are visible above a shorter rounded glass search card. On normal landscape desktop screens the hero fills the first viewport, with the search card at its bottom and the remaining content beginning below it. The card remains part of the page and the tabs, fields, date selector and existing search handoff remain usable. No content is removed or hidden.

On unusually tall or nearly square windows, the hero adapts to the artwork's aspect ratio to avoid an oversized empty area or cropping the lineup; the next section can therefore appear in the initial viewport. On phones, artwork and search remain in normal vertical flow and can be reached by scrolling on shorter screens. Owner and Driver pages are unchanged.

The scenery is the same supplied reconstructed PNG used previously; the exact reference image is not available as a clean source. The layout preserves the existing navigation, text, translation, sign-in and booking behavior. No dashboard, backend, `.env`, record or business rule was changed.

## Validation

- Seven focused desktop browser cases passed: Home reference content, responsive layouts in English/Tamil/Sinhala, search/date/seed handoff and unavailable-action/tab behavior, plus shared geometry.
- After the final viewport-aspect adjustment, the Home geometry case passed again, including 1260 × 588, 1280 × 900, 1880 × 900, 948 × 1659 and phone widths.
- Chrome screenshots were inspected at 100% zoom. For 1260 × 588, 1280 × 900 and 1880 × 900, the search card ends 20px above the bottom of the hero and subsequent content starts below the initial viewport. On the 390 × 844 phone capture the complete search card is reachable in normal flow. Five captures had no horizontal overflow.
- Production build passed; Vite retains its existing large-chunk advisory.

First-screen screenshots: [short desktop](home-hero-2026-11-07/short-desktop-first-screen.png), [desktop](home-hero-2026-11-07/desktop-first-screen.png), [wide desktop](home-hero-2026-11-07/wide-desktop-first-screen.png), [tall window](home-hero-2026-11-07/tall-first-screen.png), [phone](home-hero-2026-11-07/phone-first-screen.png). Full-page captures and viewport measurements are in the same directory, including [metrics.json](home-hero-2026-11-07/metrics.json). The short desktop uses device pixel ratio 1.5; browser zoom remains 100%.

## Changed files and next dependency

- `Frontend/src/features/landing/referenceLanding.css` — scoped Home hero framing, viewport behavior and compact card shape.
- `Frontend/tests/browser/landing-spacing.spec.js` — updated Home geometry expectations and added a standard desktop viewport.
- `.tools/landing-reference-2026-11-07/audit-home-hero.mjs` — repeatable first-screen and full-page captures.
- This report, its screenshots/metrics, and `docs/00-READ-FIRST/Travelly_NBP_Codex_Context.md`.

There is no blocker for this change. Exact artwork parity remains dependent on the original clean source assets described in the earlier [PNG/branding report](landing-png-brand-correction-2026-11-07.md); no image was generated or replaced in this task.
