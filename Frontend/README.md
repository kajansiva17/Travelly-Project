# Travelly frontend

React + Vite with JavaScript/JSX. Run from D:\Travelly:

```powershell
npm.cmd --prefix Frontend ci
npm.cmd --prefix Frontend run dev
npm.cmd --prefix Frontend run build
```

Review at http://127.0.0.1:5173. The Vite proxy sends /api requests to http://127.0.0.1:8000. Auth changes and provider setup are recorded in [the auth validation report](../docs/validation/auth-update-2026-10-26.md). The [30 October redesign report](../docs/validation/visual-redesign-2026-10-30.md) records the current scenic blue theme and visual checks; the explicitly dated baseline below is historical.

Current pricing behavior, migrations, provider setup and checks are recorded in [27 October pricing validation](../docs/validation/long-distance-pricing-2026-10-27.md). One `RateForm` component serves saved Owner rates and itinerary-prefilled quotes; the backend calculates authoritative prices. No monetary amount or free allowance is prefilled for a new rule.

The [owner addendum audit](../docs/validation/pricing-addendum-audit-2026-10-27.md) governs current fixed-first one-way selection, explicit fixed departure windows, included waiting and Owner departure-change consent. Only explicitly classified Long-distance services use this form's formulas. Local/Airport/Event pricing and Local-versus-Day comparison await their own approved numeric rules; trip duration never switches the Passenger's chosen service.

| Route | Page |
|---|---|
| / | Passenger landing |
| /for-owners | Owner public page |
| /drive-with-us | Driver public page |
| /register | Register |
| /login | Login |
| /check-email | Verification status and rate-limited resend |
| /verify-email | Explicitly consume an email verification link |
| /forgot-password | Request verified-email recovery |
| /reset-password | Consume a reset link and choose a new password |
| /google-complete | Confirm required details/terms before Google account creation |
| /account | Existing authenticated profile and role applications |
| /dashboard | Authenticated Passenger home and Owner/Driver application panels |
| /owner/dashboard | Approved Owner workspace and fleet/booking overview |
| /driver/dashboard | Approved Driver workspace and assignment overview |
| /admin/dashboard | Approved Admin workspace and review overview |
| /owner/rates | Approved Owner's reusable vehicle rate form and example preview |
| /owner/vehicles | Approved Owner fleet list and incomplete draft creation |
| /owner/vehicles/:vehicleId | Own facts/private evidence/photos, review feedback, submit/publish/retire/preference |
| /owner/vehicles/:vehicleId/calendar | Own vehicle availability and versioned calendar blocks |
| /owner/bookings | Owner customer bookings |
| /owner/assignments | Owner Driver assignments |
| /owner/personal/hire and /owner/personal/bookings | Owner's personal Passenger search and trips |
| /driver/assignments, /driver/operate-trip and /driver/trip-history | Assigned journeys and operational/history views |
| /driver/personal/hire and /driver/personal/bookings | Driver's personal Passenger search and trips |
| /admin/applications and /admin/applications/:roleId | Authorized role application queue and review |
| /admin/documents | Authorized document review entry points |
| /admin/manual-fulfilment | Protected fulfilment notices and support boundary |
| /admin/vehicles | Bounded non-self Admin vehicle queue |
| /admin/vehicles/:vehicleId | Vehicle/document correction, review and public-photo moderation |
| /admin/vehicles/:vehicleId/calendar | Read-only support calendar |
| /vehicles/:vehicleId | Eligible public vehicle detail with approved responsive photos |
| /hire | Priced private-hire search and Browse vehicles / quote requests |
| /owners/:ownerReference | Eligible public vehicles filtered to that Owner |
| /bookings | Own requests, owned bookings and assigned journeys |
| /bookings/:id | Price/rule acceptance, shared quote form, operational decisions and trip changes |

Owner/Driver application entries open `/dashboard#owner-application` and
`/dashboard#driver-application`. These are section anchors within the approved
dashboard route, not separate application/workspace routes. Review your existing
profile and explicitly submit the requested role. Each request independently
starts as PENDING; the form collects no new profile fields or documents. Existing
profile-page application links lead to the same panels.

The panels show current PENDING/APPROVED/REJECTED/SUSPENDED state and allowlisted
reasons. Only REJECTED applications offer resubmission; SUSPENDED roles cannot
self-reinstate. Passenger remains the default. Only current APPROVED roles appear
as direct workspace links in the sidebar and Passenger application cards. Approval does not redirect the user. The navbar account menu contains account actions. Deferred modules show explicit unavailable pages until their approved APIs exist. See [direct workspace navigation](../docs/validation/direct-workspace-navigation-2026-10-29.md).

Document upload and Admin Review follow the approved application/review contracts.
See [document form validation](../docs/validation/document-upload-form-2026-10-26.md)
and [Admin Review setup](../Backend/ADMIN_REVIEW.md). Their role checklist is
preserved by the auth update.

### Historical visual baseline (25 October 2026)

The following Driver layout notes describe the earlier cream/burgundy implementation. The 30 October scenic blue redesign below supersedes its palette, artwork selection, ticket composition and layout measurements. The supplied blueprint folder is named **design-reference** (singular), including its auth subfolder; blueprint screenshots remain inspection references and are never rendered as production UI.

At widths up to 767px, the Driver hero places all copy and CTA buttons above a photo-only frame with overflow: hidden and height: clamp(240px, 55vw, 310px). The original image is framed with cover sizing and a slight left-edge crop to exclude lettering baked into the source, while keeping the driver's face, upper body and steering wheel visible. The source file and desktop hero are unchanged. Verified at 360px, 390px and 430px, with desktop geometry checked at 768px and above.

### Current account behavior

Register requires name, email, international mobile, a password meeting the displayed 12-128 character composition rule, matching password confirmation, and Terms acceptance. Confirmation is checked locally and omitted from the API payload. Google completion requires the same contacts/name/terms without a password. New unverified accounts go to Check your email; existing accounts keep login access. Login accepts email or international phone and does not impose new password rules on old hashes. Tokens and Google completion state remain in memory. Remember me saves only the login identifier, never a password or token.

Terms and Privacy Policy destinations have not been supplied; those links open explicit preview notices. Help provides account guidance. Password recovery is available through an already verified email; unavailable/unknown accounts receive the same safe response. Profile shows email verification and Google connection status, and supports explicit linking to the current account. The Passenger private-hire entry leads to the ordered-itinerary form. Matching saved rules yield fresh prices; Browse vehicles keeps quote-only cases reachable. Real catalogue/vehicle evidence and server routing configuration are required. Ticketing/payments remain separate. FAQs are accessible native disclosure controls.

Historical verification on 25 October 2026 covered the earlier production build, desktop/mobile pages and PostgreSQL registration/application journey. Current visual verification is recorded in the 30 October redesign report below.


Account/Profile navigation observes the current in-memory session. Signed-in Login/Register visits return to the Passenger dashboard; ordinary Home navigation preserves the session. Full reload still requires sign-in; tokens are never persisted. `/account` offers shared identity uploads and retained private files. Owner and Driver application links open `/account?documents=owner` and `/account?documents=driver`, with only the corresponding requirements/upload types plus shared identity. These are frontend contexts over unchanged private-document APIs. See [Account/Profile UX verification](../docs/validation/account-profile-ux-2026-10-27.md).

### Vehicle availability calendar

Owner vehicle detail links to `/owner/vehicles/:vehicleId/calendar`; Admin detail/support notifications link to the read-only `/admin/vehicles/:vehicleId/calendar`. Seven-day overview and responsive entries use Asia/Colombo times. Personal, planned-maintenance and emergency blocks support versioned edit/withdrawal, retained history and actionable conflicts. Incomplete loads disable writes and never show an authoritative empty calendar. Real API journeys: `npx playwright test --config playwright.calendar-live.config.js` against the existing isolated pricing fixture server (8002) and Vite proxy (5182). See contract 09 and the 28 October validation report.


## Scenic blue redesign (30 October 2026)

The existing routes and API workflows now share a navy/royal-blue, glass-panel and coral design system in `src/styles/travellyTheme.css`. `TravellyVisuals.jsx` supplies responsive artwork, the HTML authentication journey ticket and status charts derived from real booking records. Supplied production artwork is served as WebP derivatives under `public/images/travelly`; reference mockups are excluded. Provenance and responsive dimensions are retained in `src/assets/travelly`.

Regenerate derivatives with the root Python environment and `Frontend/scripts/prepare_travelly_assets.py <original ZIP path>` from the repository root. An optional second argument selects one asset, for example `branding/shared-logo.png`. Originals are retained under `.tools/travelly-redesign/source`.

Registration includes local password confirmation; its API payload and session behavior are unchanged. Direct approved-role navigation, Passenger personal booking storage, contextual Owner self-drive and separate external Driver acceptance remain mandatory. Unavailable mockup metrics and operations are labelled instead of populated with sample data. See [the redesign report](../docs/validation/visual-redesign-2026-10-30.md) for changed files, checks and reference comparisons.

Continuation check on 30 October 2026: `npm.cmd --prefix Frontend test` passed all 53 unit tests and `npm.cmd --prefix Frontend run build` passed. The existing 694 kB JavaScript chunk warning remains. Setup documentation was reconciled with current routes and UI; production dependencies remain tracked in the [outstanding deployment checklist](../docs/validation/outstanding-deployment-checklist.md).
