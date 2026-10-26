# Travelly frontend

React + Vite with JavaScript/JSX. Run from D:\Travelly:

```powershell
npm.cmd --prefix Frontend ci
npm.cmd --prefix Frontend run dev
npm.cmd --prefix Frontend run build
```

Review at http://127.0.0.1:5173. The Vite proxy sends /api requests to http://127.0.0.1:8000. Current auth changes, provider setup and tests are recorded in [the auth validation report](../docs/validation/auth-update-2026-10-26.md); the visual-baseline notes below are historical.

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

Owner/Driver application entries open `/dashboard#owner-application` and
`/dashboard#driver-application`. These are section anchors within the approved
dashboard route, not separate application/workspace routes. Review your existing
profile and explicitly submit the requested role. Each request independently
starts as PENDING; the form collects no new profile fields or documents. Existing
profile-page application links lead to the same panels.

The panels show current PENDING/APPROVED/REJECTED/SUSPENDED state and allowlisted
reasons. Only REJECTED applications offer resubmission; SUSPENDED roles cannot
self-reinstate. Passenger remains the default. Only current APPROVED roles appear
as additional workspace options; operational workspaces remain unavailable.

Document upload and Admin Review follow the approved application/review contracts.
See [document form validation](../docs/validation/document-upload-form-2026-10-26.md)
and [Admin Review setup](../Backend/ADMIN_REVIEW.md). Their role checklist is
preserved by the auth update.

The supplied blueprint folder is named **design-reference** (singular), including its auth subfolder. Blueprint images are inspection references only and are never rendered in the app. All rendered raster artwork comes from public/images. The standalone ticket artwork in public/images/auth is retained intact, including its ticket shape, vehicles, icons and lettering. No supplied image file was edited, cropped, regenerated or replaced. Images retain their intrinsic proportions; contain sizing provides room where card dimensions differ. At widths up to 767px, the Passenger hero stacks its cream headline area above the dedicated passenger-mobile-hero.png image, selected with a picture source. The image spans the full viewport width without side gutters. At 768px and above, the original desktop image remains selected. The mobile image uses height: clamp(280px, 55vw, 340px), object-fit: cover and object-position: center 75%. This compact framing removes excess sky and foreground while keeping the vehicle row visible without distortion. The booking card sits 18px below the image. Desktop hero geometry is unchanged. Below-the-fold images use native lazy loading. Both Register and Login show their complete ticket branding panel directly beneath the header at widths up to 767px, followed by the form in a vertically scrolling layout. The ticket artwork loads immediately and scales proportionally without cropping; form controls retain touch-friendly sizes. Desktop two-column layouts are unchanged. Only the active page's hero receives high fetch priority. The palette uses cream, deep burgundy and warm neutrals; there are no external image/font services or new dependencies.

At widths up to 767px, the Driver hero places all copy and CTA buttons above a photo-only frame with overflow: hidden and height: clamp(240px, 55vw, 310px). The original image is framed with cover sizing and a slight left-edge crop to exclude lettering baked into the source, while keeping the driver's face, upper body and steering wheel visible. The source file and desktop hero are unchanged. Verified at 360px, 390px and 430px, with desktop geometry checked at 768px and above.

Register requires name, email, international mobile, a password meeting the displayed 12-128 character composition rule, and Terms acceptance. Google completion requires the same contacts/name/terms without a password. New unverified accounts go to Check your email; existing accounts keep login access. Login accepts email or international phone and does not impose new password rules on old hashes. Tokens and Google completion state remain in memory. Remember me saves only the login identifier, never a password or token.

Terms and Privacy Policy destinations have not been supplied; those links open explicit preview notices. Help provides account guidance. Password recovery is available through an already verified email; unavailable/unknown accounts receive the same safe response. Profile shows email verification and Google connection status, and supports explicit linking to the current account. Public pages describe planned services. The search panel supports service selection and input validation, then offers sign-in; it does not fabricate inventory, bookings, tickets or payments. FAQs are accessible native disclosure controls.

Verified on 25 October 2026: production build; all five desktop/mobile pages without horizontal overflow, broken images or image distortion; navigation, menu, FAQs, policy dialogs and password visibility; actual PostgreSQL Register → Login → Profile → Owner/Driver PENDING applications → Logout. The temporary browser-test account was removed. All 34 supplied assets/reference files were checked for byte-for-byte integrity.
