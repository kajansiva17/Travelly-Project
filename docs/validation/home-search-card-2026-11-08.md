# Home search card — 8 November 2026

## Completed scope

Updated the existing Home `/` search card to follow the supplied reference: rounded light-blue glass panel, white border, soft inner and outer shadows, pill-shaped Hire/Tickets/Rentals tabs, layered input fields and the existing red Search button. The card retains responsive four-column desktop and two-column phone layouts. No screenshot is used as an interactive component.

Pickup and destination remain editable; swapping them, choosing a real date and time, and submitting Hire carry those values to the existing journey form. The downstream location controls receive the typed text as search queries; users still select matching real locations there, as required by the existing booking flow. The selected local departure value is carried through unchanged. The field now shows a localized “Select date & time” prompt instead of the reference image's past example date; once selected it shows both the date and time. No default or synthetic location, reservation or booking is created.

Tickets and Rentals keep their existing honest unavailable notices; implementing those separate services was outside this task. Other landing pages, dashboards, booking rules, backend, `.env` and stored data were not changed.

## Validation

- **6 desktop Chrome cases passed:** Home hero/card geometry, English/Tamil/Sinhala responsiveness, actual Hire search with swap, required future date/time, language persistence and destination-form values, plus keyboard tabs and unavailable notices.
- **2 mobile Chrome cases passed:** the same Hire handoff and unavailable/keyboard-tab interactions.
- **63 frontend unit tests passed** and the production build passed. Vite retained its existing large-chunk advisory.
- Inspected empty and filled card captures at 1280×900, 1260×588, 390×844 and 320×640. The four captures had no horizontal page overflow, and the selected date/time fit the field. Captures use default browser zoom.

Screenshots: [desktop empty](home-search-card-2026-11-08/desktop-empty.png), [desktop filled](home-search-card-2026-11-08/desktop-filled.png), [phone empty](home-search-card-2026-11-08/phone-empty.png), [phone filled](home-search-card-2026-11-08/phone-filled.png), [small phone filled](home-search-card-2026-11-08/small-phone-filled.png). [Measurements](home-search-card-2026-11-08/metrics.json).

## Changed files and remaining dependency

- `Frontend/src/features/landing/referenceLanding.css` — scoped Home search card styling and responsive date text.
- `Frontend/src/features/landing/ReferenceLandingPages.jsx` — explicit empty-date prompt and display of selected date and time.
- `Frontend/src/i18n/messages.landing.js` — Tamil and Sinhala prompt translations.
- `Frontend/tests/browser/reference-landings.spec.js` — verify the prompt, selected time and values in the actual Hire journey form.
- `.tools/landing-reference-2026-11-07/audit-search-card.mjs` — repeatable empty/filled captures.
- This report, screenshots/metrics and `docs/00-READ-FIRST/Travelly_NBP_Codex_Context.md`.

There is no blocker for the requested Hire form. Tickets and Rentals remain deferred existing services; the next step for a Hire user is to select the actual pickup and destination from the location results in the journey form.
