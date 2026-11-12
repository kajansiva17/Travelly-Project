# Route audit (FORM & PAGE RULE, 1280x585)

Method: Playwright with mocked `/api/v1/**`, busy + empty states, tabs clicked. 'Not matching reference' is a structural proxy (shared FlowShell/dash layout vs legacy layout class, dark panels). CRASH rows are likely mock gaps. Source data: audit_<ROLE>.tsv in D:	mp-shots.

Admin: every route also fails on sidebar menu scroll (372/304px).

| Role | Route | Result | Reasons |
|---|---|---|---|
| Passenger | `/dashboard` | PASS |  |
| Passenger | `/account` | PASS |  |
| Passenger | `/bookings` | PASS |  |
| Passenger | `/bookings/b1` | PASS |  |
| Passenger | `/trips/t1/finance` | legacy, being removed |  |
| Passenger | `/passenger/bookings` | PASS |  |
| Passenger | `/passenger/saved-places` | PASS |  |
| Passenger | `/passenger/payments` | PASS |  |
| Passenger | `/passenger/support` | PASS |  |
| Passenger | `/passenger/settings` | PASS |  |
| Passenger | `/passenger/trips/t1/finance` | legacy, being removed (PassengerFinalFare) |  |
| Passenger | `/travel/book/service` | PASS |  |
| Passenger | `/travel/book/event` | PASS |  |
| Passenger | `/travel/book/tickets` | PASS |  |
| Passenger | `/travel/book/rental` | PASS |  |
| Passenger | `/travel/book/details/airport` | PASS |  |
| Passenger | `/travel/book/details/local` | PASS |  |
| Passenger | `/travel/book/details/event` | PASS |  |
| Passenger | `/travel/book/details/long-distance/one-day` | PASS |  |
| Passenger | `/travel/book/details/long-distance/multi-day` | PASS |  |
| Passenger | `/travel/book/requirements` | PASS |  |
| Passenger | `/travel/book/vehicles` | PASS |  |
| Passenger | `/travel/book/vehicles/v1/review` | PASS |  |
| Passenger | `/travel/book/review` | PASS |  |
| Passenger | `/trips/t1/request-status` | PASS |  |
| Passenger | `/trips/t1/confirmed` | PASS |  |
| Passenger | `/vehicles/v1` | PASS |  |
| Passenger | `/hire` | PASS |  |
| Passenger | `/owners/OWN1` | PASS |  |
| Owner | `/owner/dashboard` | PASS |  |
| Owner | `/owner/personal/hire` | PASS |  |
| Owner | `/owner/personal/owners/OWN1` | PASS |  |
| Owner | `/owner/personal/bookings` | PASS |  |
| Owner | `/owner/personal/bookings/b1` | PASS |  |
| Owner | `/owner/personal/vehicles/v1` | PASS |  |
| Owner | `/owner/rates` | PASS |  |
| Owner | `/owner/service-readiness` | PASS |  |
| Owner | `/owner/event-packages` | legacy, being removed |  |
| Owner | `/owner/event-operations` | legacy, being removed |  |
| Owner | `/owner/ticket-departures` | PASS |  |
| Owner | `/owner/vehicles` | PASS |  |
| Owner | `/owner/vehicle-setup` | PASS |  |
| Owner | `/owner/vehicles/v1` | PASS |  |
| Owner | `/owner/vehicles/v1/calendar` | PASS |  |
| Owner | `/owner/vehicles/v1/maintenance` | legacy, being removed |  |
| Owner | `/owner/bookings` | PASS |  |
| Owner | `/owner/assignments` | PASS |  |
| Owner | `/owner/operations` | PASS |  |
| Owner | `/owner/earnings` | PASS |  |
| Owner | `/owner/rentals` | PASS |  |
| Owner | `/owner/settings` | PASS |  |
| Owner | `/owner/support` | PASS |  |
| Owner | `/account?workspace=owner` | PASS |  |
| Owner | `/bookings/b1?workspace=owner` | PASS |  |
| Owner | `/trips/t1/finance?workspace=owner` | legacy, being removed |  |
| Driver | `/driver/dashboard` | PASS |  |
| Driver | `/driver/personal/hire` | PASS |  |
| Driver | `/driver/personal/owners/OWN1` | PASS |  |
| Driver | `/driver/personal/bookings` | PASS |  |
| Driver | `/driver/personal/bookings/b1` | PASS |  |
| Driver | `/driver/personal/vehicles/v1` | PASS |  |
| Driver | `/driver/assignments` | PASS |  |
| Driver | `/driver/operate-trip` | PASS |  |
| Driver | `/driver/trips/t1/assigned` | PASS |  |
| Driver | `/driver/trips/t1/verify-passenger` | PASS |  |
| Driver | `/driver/trips/t1/live` | PASS |  |
| Driver | `/driver/trips/t1/cash` | PASS |  |
| Driver | `/driver/ticket-boarding` | PASS |  |
| Driver | `/driver/rentals` | PASS |  |
| Driver | `/driver/trip-history` | PASS |  |
| Driver | `/driver/settings` | PASS |  |
| Driver | `/driver/availability` | PASS |  |
| Driver | `/driver/earnings` | PASS |  |
| Driver | `/driver/road-alerts` | PASS |  |
| Driver | `/driver/support` | PASS |  |
| Driver | `/account?workspace=driver` | PASS |  |
| Driver | `/bookings/b1?workspace=driver` | PASS |  |
| Driver | `/trips/t1/finance?workspace=driver` | legacy, being removed |  |
| Driver | `/trips/t1/operation?workspace=driver` | PASS |  |
| Admin | `/admin/dashboard` | PASS |  |
| Admin | `/admin/personal/hire` | PASS |  |
| Admin | `/admin/personal/owners/OWN1` | PASS |  |
| Admin | `/admin/personal/bookings` | PASS |  |
| Admin | `/admin/personal/bookings/b1` | PASS |  |
| Admin | `/admin/personal/vehicles/v1` | PASS |  |
| Admin | `/admin/applications` | PASS |  |
| Admin | `/admin/applications/r1` | PASS |  |
| Admin | `/admin/vehicles` | PASS |  |
| Admin | `/admin/vehicles/v1` | PASS |  |
| Admin | `/admin/vehicles/v1/calendar` | PASS |  |
| Admin | `/admin/documents` | PASS |  |
| Admin | `/admin/services-routes` | PASS |  |
| Admin | `/admin/services-routes/tickets` | PASS |  |
| Admin | `/admin/bookings` | PASS |  |
| Admin | `/admin/oversight` | PASS |  |
| Admin | `/admin/rentals` | PASS |  |
| Admin | `/admin/payments` | PASS |  |
| Admin | `/admin/social-reviews` | PASS |  |
| Admin | `/admin/road-alerts` | PASS |  |
| Admin | `/admin/reports` | PASS |  |
| Admin | `/admin/manual-fulfilment` | PASS |  |
| Admin | `/admin/settings` | PASS |  |
| Admin | `/account?workspace=admin` | PASS |  |
| Admin | `/bookings/b1?workspace=admin` | PASS |  |


## BATCH A re-measure (1280x585 and 1920x1080, busy + empty + all tabs)
PASS (no page scroll, no card scroll/clip, no overlap, no legacy layout, admin sidebar fits): hire x4, /account x4 roles (3 tabs), vehicle detail x4, owner/personal/bookings, driver/personal/bookings/b1, admin/settings, owner/rates, owner/service-readiness, passenger/bookings. Admin sidebar scroll: gone on all admin routes at 1280x585.

## ADMIN batch re-measure (1280x585 and 1920x1080, busy + empty, tabs/details/confirmation opened)
PASS (no page scroll, no card scroll/clip, no overlap, no legacy layout, no dark panel, actions in view, sidebar fits): /admin/dashboard (reference grid: 4 stats, 6 tiles + Travelly AI card, no tabs), /admin/applications (+ /:id with Application / Evidence tabs and the confirmation step), /admin/documents, /admin/bookings, /admin/payments, /admin/social-reviews, /admin/road-alerts, /admin/reports, /admin/oversight (3 tabs), /admin/manual-fulfilment (Events / Record an event), /admin/services-routes (list + details), /admin/services-routes/tickets, /admin/settings, /account?workspace=admin.
Shared layout: features/admin/AdminList.jsx (filter row, compact rows, paging, Details view). Crash fixes: /admin/applications/:id and /admin/services-routes now guard missing application / pricing_scope / status / ready_vehicles.
Not in this batch (still listed above as FAIL by the old sidebar finding only, which is fixed): /admin/personal/*, /admin/vehicles*, /admin/rentals, /bookings/:id?workspace=admin.

## Passenger dashboard batch (1280x585 and 1920x1080, busy + empty)
PASS: /dashboard (shared dash grid: 4 stat cards, 6 tiles + Travelly AI card, no page or tile scroll; legacy passenger-dashboard layout, DashboardSearchPanel and passengerDashboard.css deleted), /trips/:id/request-status and /trips/:id/confirmed (BookingState guards missing status/itinerary/proposal; pickup QR + PIN beside each other so quote + code still fit 1280x585).

## Booking wizard batch (1280x585 and 1920x1080)
PASS (no page/card scroll, nothing outside the card): /hire signed-out and signed-in (steps: service cards, Journey, Pickup & stops incl. populated pickup list and 4 stops, vehicle needs, vehicles), /travel/book/service, /details/{airport,local,event,long-distance/one-day,multi-day}, /requirements, /vehicles, /vehicles/:id/review, /review, /travel/book/tickets, /travel/book/event (Event / Date & vehicles / Results tabs), /travel/book/rental, /vehicles/:id.
Root cause of the signed-out /hire breakage: the compact flow CSS was keyed to `.workspace-shell[data-workspace]`, which public pages do not have. FlowShell now marks the body `flow-standalone` and those 242 selectors accept either. The audit script flags Event hire's Venue/Pickup fields as overlapping their own search button; the button is drawn inside the input on purpose.

## Group 2 (owner pages, 1280x585 and 1920x1080, busy + empty)
All /owner/* routes PASS. /owner/operations rebuilt as FlowShell tabs (My Driving, Driver Assignments, Live Fleet Trips, Vehicle Expenses) with paging; the dashboard tiles tighten at heights <= 640px so Fleet at a glance and Booking activity no longer clip. Legacy components skipped and marked above: OwnerEventPackages, OwnerEventOperations, VehicleMaintenancePage, TripFinancePage, TripOperationPage, PassengerFinalFare.

## Group 3 (admin personal, vehicles, rentals, booking detail; 1280x585 and 1920x1080, busy + empty, all tabs)
All listed routes PASS. The old failures were the 13-item admin sidebar scroll (372/304), fixed earlier; nothing else was failing.

## Page frame (navbar + sidebar + content) - 1280x585, 1366x768, 1920x1080
Tokens in `src/styles/frame.css` (--frame-inset-x 48px, --frame-max 1320px, --frame-top 24px, --nav-h 64px, --frame-gap 16px, --frame-bottom 20px; at heights <= 640px: top 12px, nav 56px, gap 10px, bottom 12px). Verified by script for /, /login, /register, /hire, /dashboard, /owner/dashboard, /driver/dashboard, /admin/dashboard, /account:

| Viewport | Navbar left-right | Top | Height | Sidebar left | Content right |
|---|---|---|---|---|---|
| 1280x585 | 48 - 1232 | 12 | 56 | 48 | 1232 |
| 1366x768 | 48 - 1318 | 24 | 64 | 48 | 1318 |
| 1920x1080 | 300 - 1620 | 24 | 64 | 300 | 1620 |

Identical on every route; sidebar top = content top, bottoms aligned, navbar-sidebar gap = sidebar-content gap; no page scroll except the landing page; no sidebar label cut off (sidebar is 236-264px wide). Full audit at 1280x585 for all four roles and the listed routes at 1920x1080 pass except the legacy rows and the by-design search-button overlap on /travel/book/event.


## Payments UI (Sandbox + PayHere) — mocked-API audit

Routes: `/travel/book/tickets` (step 3 payment panel, also `?booking=<id>&payment=returned|cancelled`) and `/admin/services-routes` (Payments tab).
Measured at 1280x585 and 1920x1080 (card scrollHeight = clientHeight, page scroll 0/0, nothing outside the card, footer row in view):

| State | 1280x585 | 1920x1080 |
|---|---|---|
| Held, Pay shown | pass (453/453) | pass (861/861) |
| Sandbox: test label + Simulate success/failure | pass | pass |
| Sandbox success → Seats confirmed | pass | pass |
| Sandbox failure → retry offered | pass | pass |
| PayHere payer details required (address, city, phone, email) | pass | pass |
| 410 expired hold / 409 already paid / 422 amount changed / 409 in progress | pass | pass |
| Returned from PayHere, pending ("Waiting…") | pass | pass |
| Returned from PayHere, paid | pass | pass |
| Cancelled return, Try again | pass | pass |
| Admin payment settings: 12 rows, empty, Edit form, saved | pass (449/449) | pass (888/888) |
| Admin 409 VERSION_CONFLICT notice, 422 field message on fee | pass | pass |

Language test 64/64 green. Not covered by the mock: the real PayHere form POST and return, real error bodies.

## Owner Operations polish (/owner/operations)

Empty states (My Driving, Driver Assignments, Live Fleet Trips) are a shared centered `EmptyState` (icon, title, one sentence, optional action; "Open my vehicles" on Live Fleet Trips). Vehicle Expenses is one "coming soon" empty state, the six "Unavailable" tiles are gone. Developer wording ("API", "assumed", "ledger") reworded, Tamil + Sinhala added.
1280x585 and 1920x1080, all 4 tabs, with data and empty: card 449/449 (888/888), page scroll 0, nothing outside the card, empty block centered in the pane (within 8px of the pane middle, the gap is the footer row). Language test 64/64.

## Auth pages restyle: /check-email, /verify-email, /reset-password, /google-complete

All four now use the shared `AuthLayout` (sunset background, white-pill navbar, frosted card, red-accent title word, rounded `Field` inputs, red gradient pill button), the same as /forgot-password. Old `Shell` wrapper and every `.auth-flow-*` rule (authGlass.css plus the `.auth-flow-panel` entries in six other stylesheets) removed. Logic, validation, API calls and routes untouched.
Measured at 1280x585 and 1920x1080, states: check-email (with ticket, cooldown after resend, resend error, no flow), verify (no token, token, error, success), reset (no token, form, weak password, server error, success), google-complete (no flow, form, field errors, server error, Admin journey). Result: page scroll 0, card scroll 0, nothing outside the card, background and red button present, inputs rounded. Card sits vertically centred (bottom gap 117-126px at 1280x585, 265-308px at 1920x1080). Language test 64/64.

## Payments: provider chosen by the ticket (payment_provider / payment_method / payer_details_required)

The Pay flow now reads `payment_provider`, `payment_method` and `payer_details_required` from `GET /bookings/{id}/ticket` (the hold response is followed by a ticket read so the fields are present). The CARD-then-SANDBOX probe is removed; `PAYER_DETAILS_REQUIRED` is kept only as a safety net. Simulate success/failure appear only when `payment_provider` is SANDBOX. `payment_provider: null` hides Pay and shows "Online payment is not available right now".
Mocked and measured at 1280x585 and 1920x1080 (card 453/453 and 861/861, page scroll 0, nothing outside the card, footer in view) for: SANDBOX (no payer fields, method SANDBOX, no `payer` sent), PAYHERE address+city (Pay disabled until filled, body `method:CARD, payer:{address,city}`), PAYHERE with phone and email (4 fields, all four sent), provider null (0 Pay buttons, 0 Simulate buttons, message shown), plus the earlier failed/paid/410/409/422/returned/cancelled states and the admin settings tab. Language test 64/64.

## Owner Ticket departures: Choose a driver (/owner/ticket-departures)

Uses `GET /owners/me/drivers` (id, reference, display_name, eligible, how_you_know_them) and `PATCH /scheduled-trips/{id}` with `expected_version` + `operator_driver_user_id` (drafts only); `POST /scheduled-trips` takes the same field. No new endpoints, no sidebar change.
- New departure, step 3 "Who will drive?": Assign later / "I will drive (self-drive)" (only for an approved Driver) / "My drivers" group (ineligible ones disabled), plus an info line with an Approved / Not approved chip and how the Owner knows them. Empty state: "You have no other Drivers listed yet" with "Drive it myself" (Driver Owners) or an "apply to drive" link. No raw user ID is typed anywhere.
- Your departures: each draft shows "Driver: name / You (self-drive) / No Driver yet"; drafts with no driver get "Assign driver", an inline panel (no modal) with Back to list. Errors: DRIVER_NOT_ELIGIBLE (stays on the panel), VERSION_CONFLICT (refreshes, asks to choose again), 404 and DEPARTURE_NOT_DRAFT (refreshes the list).
Mocked (12 drivers incl. one ineligible, no drivers, owner Driver / not Driver, protected departure with 5 fields, 6 drafts with and without drivers) and measured at 1280x585 (card 449/449) and 1920x1080 (840/840 form, 888/888 list): page scroll 0, no inner scroll, nothing outside the card, footer clear. Bodies checked: listed driver sends that id, self-drive sends the owner's id, Assign later sends null, assign sends `{expected_version, operator_driver_user_id}`. Language test 64/64.

## Ticket departures "New departure": stepper and Driver step layout

- Stepper vs tabs: on short windows the stepper shares a row with the tabs; below about 1380px wide the labels ran past the stepper card and under the tabs (measured: last label right edge 719 vs stepper 717 at 1280, 668 vs 617 at 1180). Now, on windows no taller than 640px and no wider than 1380px, only the current step keeps a visible label (the others stay readable to screen readers), and labels/connectors can no longer overflow their step. Measured at 1280x585, 1366x600 and 1920x1080: stepper and tabs never overlap, the current label is inside the stepper.
- Step 3: type and window on the left, "Who will drive?" and one aligned Driver card on the right (icon + message left, action right, same row centre: 315/315/315 at 1280x585, 451/451/451 at 1920x1080). Card shows the chosen driver, self-drive, the empty state (Drive it myself / Apply to drive) or a "No Driver chosen yet" prompt.
- All three steps plus the departures list and the assign panel re-checked at 1280x585 (card 449/449) and 1920x1080: page scroll 0, no inner scroll, nothing outside the card, footer clear. Language test 64/64.

## Private hire payment (contract section D)

- Booking page (`/bookings/:id`, Passenger, Owner and assigned Driver): new "Payment" tab reading `GET /bookings/{id}/payment-summary`. Not due: "Payment opens when the trip is completed" and no Pay button. Due: status chip + amount; "Pay online" reuses the ticket Pay flow (`TicketPayment` with `hire`: amount = `amount_due`, new key per press, provider/method/payer from the summary, PayHere hidden-form POST and return handling; the page opens on the Payment tab for `?payment=returned|cancelled`); "Pay in cash" appears only when `cash_accepted`.
- Cash: `POST /bookings/{id}/cash-receipts`, each side sends only its own confirmation, behind a two-step "Yes, confirm" (nothing is sent on the first tap). Passenger confirm lives on the booking page; the collector's "Confirm cash received" is on the Owner's booking view and on the Driver trip page once the trip is completed. States from `cash.passenger_confirmed` / `cash.collector_confirmed`; paid only when both. Every contract error code has a short message (CASH_NOT_ACCEPTED, PAYMENT_NOT_DUE, COLLECTOR_NOT_ASSIGNED, CONFIRMATION_NOT_YOURS, PAYMENT_AMOUNT_MISMATCH, PAYMENT_IN_PROGRESS, BOOKING_ALREADY_PAID, BOOKING_NOT_FOUND, CASH_NOT_AVAILABLE, network). Buttons are disabled while a request runs.
- Owner rates (`/owner/rates`, Vehicle and service step): switch "Accept cash at the end of the trip" calling `PATCH /vehicles/{id}/services/{service}/payment-options` with `{expected_version, cash_accepted}`; disabled with a hint until the service has saved rates; saving / saved / error states (VERSION_CONFLICT reloads, VEHICLE_SERVICE_NOT_FOUND, VEHICLE_NOT_FOUND, CASH_NOT_ALLOWED).
Mocked (not due, online only incl. Sandbox success, cash accepted, cash waiting for driver, cash waiting for passenger, paid, cash and intent errors, PayHere address+city, returned pending, returned cancelled, collector views incl. Driver trip page, switch on/off/unsaved/409/422/404) and measured at 1280x585 (card 449/449, driver trip page 487/487, rates 453/453) and 1920x1080: page scroll 0, no inner scroll, nothing outside the card, footer clear, 33 of 33 states. Language test 64/64.

## Ticket cancellation and refunds (contract section E)

- Passenger ticket page (`/travel/book/tickets?booking=…`, step 3): on a paid ticket a "Cancel ticket" button sits in the footer. Step 1 shows the booking, "Estimated refund: 50% (LKR 1,500.00) after Admin approval" (or "none" under 24 h), a reason list (Other adds a text field) and Continue. Step 2 is a plain confirm ("Yes, cancel my ticket" / Back). Nothing is sent before the second step. Bands (over 72 h 100%, 24 to 72 h 50%, under 24 h 0%) come from `itinerary.departure_at`; the server decides on the request. After success the screen shows the cancelled state and the refund from the answer (`refund_percent`, `refund`), then from `GET /bookings/{id}/payments` (Waiting for Admin approval / Being refunded / Refunded / Refund declined). Errors: TICKET_NOT_CANCELLABLE, DEPARTURE_STARTED, VERSION_CONFLICT (booking re-read, confirm again), BOOKING_NOT_FOUND, VALIDATION_ERROR (field message), network.
- Admin "Refunds" tab in Services & Routes: AdminList over `GET /admin/refunds` (status filter done in the screen, the endpoint takes no query), compact rows, paging, Details. Details: Approve / Reject (reason required, confirm step), PayHere "Record as refunded" (`/complete` with `{expected_version, provider_reference}`, confirm step). "Refund a payment" (footer, or "Refund more of the original payment" in Details): finds a booking's payments (`GET /bookings/{id}/payments`), then `POST /payments/{id}/refunds` full or part, amount capped at the payment, confirm step, new idempotency key per press (reused after a network error). Errors: REASON_REQUIRED, REFUND_ALREADY_DECIDED, VERSION_CONFLICT, REFUND_NOT_FOUND, REFUND_NOT_PROCESSING, REFUND_AMOUNT_INVALID (shows what is left), PAYMENT_NOT_REFUNDABLE, VALIDATION_ERROR (per field). Lists show only references, amounts, status and dates.
- Mocked 50 states (tiers 100/50/0, Other reason, 5 cancel errors, reopened cancelled ticket, empty and 40-row lists with filters, approve, approve PayHere then complete, reject, 3 decision errors, complete error, paid/rejected details, direct refund full and partial, over-cap, 3 direct errors, lookup not found): at 1280x585 (card 453/453 ticket, 449/449 admin) and 1920x1080 (845/845 admin) page scroll 0, no inner scroll, no overflow, no control overlap, footer clear. An early run found the PayHere "Record as refunded" button overlapping "Refund more of the original payment" at 1280x585; fixed by trimming Details to six facts and putting the extra action in the same row. Language test 64/64.
