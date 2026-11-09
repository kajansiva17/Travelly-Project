# Travelly DESIGN-SPEC

Source of truth: the images in `Frontend/design-reference/` (`auth/`, `screens/<role>/`, `boards/`, mapped by `REFERENCE_MAP.md`). `public/references/` is ignored.

Measurement note: references are small raster mock-ups (about 780 px wide for screens, 1600 px for auth). Hex values were sampled from the images with a canvas probe and rounded; sizes are scaled to a 1440 px wide desktop. Treat them as targets and check each against the reference during its phase. Re-measure from the original board when a value looks off.

## 0. Global rules (user decisions)

- **Single navbar.** Every page uses the OWNER navbar design (`screens/owner/*`, boards `O01`-`O04`): login, register, landing/home, and the passenger, driver, owner and admin dashboards. Same layout, colours, logo and buttons everywhere. Ignore the different navbar colours in the passenger, driver and admin references. Only role-specific items may differ: sidebar/menu links, user name and avatar, notification target.
- **Landing page:** replace ONLY its navbar; nothing else on it changes.
- Passenger home uses the shared shell WITH the sidebar.
- No API, request/response or `api()` changes. Ticket JSX files untouched; restyle via CSS and shared components.
- Images are never used as page backgrounds in the reference sense of a screenshot. Recreate with React and CSS. Photos come from `public/images/travelly/`.
- Honest unavailable states; no fake data.

## 1. Fonts

- Reference face: rounded geometric sans (Poppins / Nunito Sans feel); headings bold, body medium. The project font `Travelly Sans` stays the base unless it clearly differs when checked in Phase 1.
- Logo wordmark: italic bold "Travelly" (Travel in blue `#1b3fb8`, "ly" in red `#e8231a`), speedometer dial icon to the left, tagline "RENTAL · CARS · TRAVEL" (about 6 px, caps, navy) under the wordmark. Reuse `branding/approved-2026-11-07/standard-logo.png`, `meter-dial.png`, `meter-needle.png`, `wordmark.png` and the existing `Brand` component.
- Sizes (1440 wide): page title 36-40 px bold navy; greeting subtitle 15 px; card title 20-22 px bold; label 14-15 px semi-bold; helper text 12-13 px muted; button 16-18 px semi-bold; sidebar item 15 px medium.
- Login: title "Welcome" navy plus "Back" red, about 44 px bold; subtitle 18 px.

## 2. Colours

| Role | Value |
|---|---|
| Ink / headings | `#121552` (navy) |
| Body text | `#233e65` |
| Muted text | `#5b6f8f` |
| Primary red (top / mid / bottom of button gradient) | `#ff4a3c` / `#ed2b18` / `#d90f0a` |
| Red text / links (login) | `#e8231a` |
| Brand blue (icons, step 1, links) | `#2f6fe4`; deep icon blue `#1f3fa8` |
| Success green (status, "Online", donut) | `#3fb950` / chip bg `#dff3e2` |
| Warning / alert badge | red `#f11e00` |
| Glass card fill | white at 78-88% (`rgb(255 255 255 / .82)`), sampled `#e1eef9`-`#f6f9fc` over scenery |
| Glass card border | `rgb(255 255 255 / .9)` 1 px |
| Sidebar fill | WHITE frosted glass (`rgb(255 255 255 / .78)` with 18px blur, white border); text navy `#121552` (user decision; supersedes the green-grey seen in the references) |
| Active nav / selected card tint | red pill; selected cards get red outline `#ee3a2a` and `#fff0ee` fill |
| Disabled button | `#848c9e` at 60% on glass |
| Input fill | `#edf3f9` (owner forms), `#e8eaf2` pill (auth) |
| Scenic background | Sigiriya, lake, tropical foliage: `heroes/travelly-dashboard-sigiriya-background.png`; auth uses the sunset coast scene (see `heroes/*`, `landing-scenes-2026-11-07/*`; pick the closest match in Phase 1) |

## 3. Radius, shadow, glass

- Card radius 24-28 px; sidebar radius 28 px (all corners, floating with about 12 px inset from the screen edge); navbar radius 30 px (pill); input radius 12 px (owner/driver/passenger forms) and fully round 999 px (auth); chips 999 px; buttons 999 px (pill) for primary CTAs, 14 px for in-card secondary.
- Card shadow: `inset 0 1px 8px rgb(255 255 255 / .9), 0 8px 24px rgb(40 80 120 / .18)`.
- Glass: `backdrop-filter: blur(18px) saturate(1.2)`; navbar and cards at white 78-88%; sidebar white at about 78% with the same blur. Auth cards are slightly more transparent (white about 60-70%) with a visible blurred background.
- Hover: lift 1-2 px, shadow slightly stronger. Focus: 2 px blue ring `#2f6fe4`.

## 4. Navbar (single, owner design)

- Floating white-glass pill, full width with about 12 px margin, height about 64-72 px.
- Left: logo (dial + italic wordmark + tagline).
- Right (dashboard): language `EN` with globe and chevron; Travel Reels (red play icon in a rounded square, label navy); bell with red count badge; circular avatar with user name.
- Right (login/register): Back to Home (house icon), Help (question circle), EN with chevron, separated by thin vertical dividers. Landing keeps its own links inside this same pill style.
- Colours: text navy `#121552`, icons navy/blue; no role colours.
- Mobile: collapses to logo + menu toggle (existing behaviour kept).

## 5. Sidebar (role menus, one design)

- Floating rounded WHITE glass panel on the left (not green-grey), width about 190 px at 1440 (clamp 180-220).
- Item: line icon + label, navy text 15 px (white on the red active pill), row height about 40 px, radius 14 px.
- Active item (current page): red gradient pill with white text and icon. Hover: white glass pill (confirmed).
- Bottom block (divider above): Settings, Profile, Travel & Booking, Logout. Travel & Booking turns into the red pill when active (see `O04-04`).
- Menus by role (from the references):
  - Passenger: Overview, My Trips, Bookings, Saved Places, Payments, Support.
  - Owner: Overview, My Fleet, Vehicles, Services, Departures, Seat Inventory, Drivers, Bookings, Operations (Owner only), Earnings, Reviews, Documents, Support.
  - Driver: Overview, My Trips, Operate Trip, Availability, Earnings, Trip History, Road Alerts, Support.
  - Admin: Overview, Users & Roles, Documents, Vehicles, Services & Routes, Bookings, Payments, Social & Reviews, Road Alerts, Manual Fulfilment, Reports.
- Confirmed: red = current page, white = hover.

## 6. Buttons

- **Primary:** red vertical gradient `#ff4a3c` to `#d90f0a`, white text 16-18 px semi-bold, trailing arrow icon, pill radius, inner top highlight `inset 0 1px 1px rgb(255 255 255 / .5)`, shadow `0 6px 14px rgb(217 15 10 / .3)`, min-height 46-52 px.
- **Secondary:** white glass fill, 1 px white/blue-grey border, navy text, leading arrow icon for Back; radius 999 px.
- **Disabled:** grey `#848c9e` glass, text white 70%.
- **Active-trip banner button:** red pill with car icon and chevron (header area of owner/driver screens).
- **Tab bar buttons** (Travel & Booking): white glass segmented bar, selected tab red outline and tinted fill with red icon.
- Google button: white pill, Google "G", navy text "Continue with Google".

## 7. Inputs, chips, steppers

- Labels above fields, 14 px semi-bold navy, red `*` for required.
- Input: height 44-48 px, radius 12 px, fill `#edf3f9`, 1 px `#cfe0f0` border, navy text, placeholder `#7d8fa8`; optional leading icon in muted blue (capacity fields show seat/luggage icons).
- Select: same style with chevron.
- Auth inputs: pill (radius 999), leading line icon, placeholder navy; password has an eye-off icon at the right.
- Checkbox: white rounded square 18 px, red check; link text blue underlined (`Forgot password?`) and red underlined (`Sign up`, `Log in`).
- Chips: pill, white glass, small icon + text; positive chips use green tick on `#dff3e2`; info chip uses blue snowflake on `#e3efff`.
- Stepper: numbered circles (active blue `#2f6fe4` filled, upcoming white with blue border) joined by thin blue lines, labels below.
- Info callout: pale blue glass box with shield/info icon and 12 px text.

## 8. Icons and images

- Icon set: outline line icons, 1.8-2 px stroke, rounded caps, 22-24 px; navy in cards, white in sidebar, blue for feature icons. Reuse the existing inline `Icon` set in `components/components.jsx`; add missing icons in the same style (plane, car, ticket, key, route, bag, snowflake, phone, shield).
- Service tiles (Travel & Booking, `P01-01`, `O04-04`): icon plus small illustration (airport, city, tent, mountain road, ticket, SUV) on the right of each card; reuse `public/images/travelly/illustrations`, `icons`, `vehicles`, `destinations`.
- Vehicle photos from `public/images/travelly/vehicles/`; avatars circular 36-44 px.
- Status donut / metric cards: blue `#3696ff`, green `#3fb950`, grey `#d2dfec`.

## 9. Layout patterns

- Page = scenic background, navbar pill on top, sidebar left, content in the right column.
- Greeting header over the scenery: bold title with subtitle (e.g. "Grow every journey, Nimal."), location chip right ("Sigiriya, Sri Lanka" white glass pill with pin icon).
- Content cards: large glass cards, 2-4 column grids, 20-24 px gap.
- Form pages (O01-O03, P01-P04): left photo/summary card plus right form card, stepper across the top of the card, primary CTA bottom-right.
- Auth: two glass cards on a sunset coast background; left "Your Journey, Your Way" ticket card (existing `journey-pass` image), right form card (login: Welcome Back; register: Create Your Account, compact fields in single column).
