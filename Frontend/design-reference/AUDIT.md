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

## Owner "Your departures" polish

- One date format: new shared helper `src/i18n/dateTime.js` (`formatDateTime`, e.g. "20 Nov 2026, 8:00 AM", month always a word, app language via Intl; optional timeZone). Used in Your departures rows, the assign and edit-time panels and the "Stop bookings at" help, the passenger ticket search rows and seat step, Admin Refunds, and the booking page's `showTime`.
- Drafts whose departure (or booking cut-off) has passed: red "Departure time has passed" / "Booking cut-off has passed" chip with a tip, Publish disabled (tooltip on its wrapper), and an "Edit time" action. The backend does allow it: `PATCH /scheduled-trips/{id}` accepts `departure_at`, `estimated_arrival_at`, `booking_cutoff_at` on a draft (it must be in the future). Edit time sends `{expected_version, departure_at, estimated_arrival_at, booking_cutoff_at}` with arrival and cut-off shifted by the same amount. Publish errors "cut-off has already passed" and "departure must be in the future" now show friendly, translated messages.
- Seats on drafts: the list (`GET /scheduled-trips?mine=true`) fills `available_seats` by counting seat rows, which are only created on publish, so every draft showed "0 seats open". Drafts now show "{n} seats when published" from the vehicle's saved layout (`GET /vehicles/{id}/seat-layout`, bookable seats) or "Seats are created when you publish" when none is saved. Published departures keep the real "{n} seats open".
- Mocked: future draft, published, past draft, cut-off-only passed, no seat layout, 14 drafts with paging, edit time save, publish cut-off error. 1280x585 (card 449/449) and 1920x1080 (888/888): page scroll 0, no inner scroll, no overflow, no control overlap, rows 52px. Language test 64/64.

## Ticket departures: "Find a Driver by reference" (contract 03T)

- "Who will drive?" (create form step 3) and the "Assign driver" panel for drafts: a "Find a Driver by reference" input with a Find button (Enter also finds), under the Driver select. Calls `POST /owners/me/drivers/lookup` with `{driver_reference}` exactly as typed (the server accepts spaces and lower case). Result line: Approved / Not approved chip, display name and the server message. Eligible: "Use this Driver" adds the person to the Driver list as "Found by reference", selects them, and the Driver card shows them like a listed Driver; the id is sent as `operator_driver_user_id` (POST /scheduled-trips, or PATCH with `expected_version`). Not eligible: message only, no way to choose. No user ID is shown or typed.
- Errors: 404 DRIVER_NOT_FOUND (check the reference with the Driver), 422 (format hint with an example), 403, 429 RATE_LIMITED (try again in a few minutes), network, other (server message).
- Fixed on the way (pre-existing): in step 3 the "Accepted time window (minutes)" label made its field 304px wide inside a 217px cell, so the input overlapped the Driver select by 71px at 1280x585. The label is now "Time window (min)" and `.rate-field` grids use `minmax(0,1fr)` so no input can exceed its cell.
- Mocked: found + eligible, found + not eligible, not found, bad format, rate limited, 403, server error, network error, Enter key, empty list, assign panel found/not eligible/bad format and the assign PATCH body. 1280x585 and 1920x1080: page scroll 0, no inner scroll, no overflow, no control overlap. Language test 64/64.

## Vehicle Maintenance tab (contract 03M)

- Where: Owner vehicle workspace (`/owner/vehicles/:id`), new "Maintenance" tab after Submit (Owner view only; no new sidebar item). New `VehicleMaintenance.jsx`; the tab's primary action uses the shared footer slot.
- Sub-views as chips: Summary, Records, Add record, plus the current odometer and when it was updated. All data from the API: `GET /vehicles/{id}/records` (type picker from `allowed_record_types`, totals, `can_add`) and `GET /vehicles/{id}/maintenance-summary`.
- Summary: one row per task with km left (or km overdue), estimated due date or "Estimated date unavailable", the manufacturer date when given, and a status chip as the contract defines it (OVERDUE = Overdue, DUE = Due today, UPCOMING = OK, NO_LIMIT_SET, NOT_RECORDED). "Record" on a row opens Add record with that task's type. The API has no "due soon" status, so none is invented.
- Records: totals chips (fuel, charging only for EV types, maintenance), type filter, paged rows with date, reading, provider, litres or kWh; a red "Needs review" chip with a tip for `review_status: NEEDS_REVIEW`.
- Add record: step 1 type, date and time, odometer (or start and end for personal use); step 2 only that type's other fields (per the contract table); a check step, then Save. Client checks mirror the contract (required fields per type, no future time, decimals, next due above the reading, calendar date after the record date, end not below start); API `field_errors` appear on the matching field and open the right step. `odometer_status` messages: APPLIED, UNCHANGED, HISTORICAL, NEEDS_REVIEW (saved, flagged, odometer not changed, add a corrected record), NO_READING. Errors: POSSIBLE_DUPLICATE (Save it anyway sends `confirm_duplicate`), RECORD_NOT_COMPATIBLE, FIELD_NOT_APPLICABLE, VALIDATION_ERROR, VEHICLE_NOT_FOUND, 403, network.
- Mocked 44 states (busy 60 rows and empty lists, filter, BEV type list, every record type's fields, all odometer statuses, client and API validation errors, summary with overdue/due/OK/unknown date/no limit/not recorded, summary error, read-only). 1280x585 (card 449/449), 1920x1080 (888/888): page scroll 0, no inner scroll, no overflow, no overlap. Rows per page follow the window height (4 at 585, 10 at 1080); slack above the footer checked at 1280x585, 1366x768, 1920x1080, 2560x1440. Also added translations for the 4 permit strings in `VehicleWorkspace.jsx` that were missing. Language test 64/64.

## Protected fulfilment of ticket departures (contract 03F2)

- Owner, Your departures: the status chip uses the contract's values (PUBLISHED, BOOKING_OPEN, COMMITTED, DECISION_REQUIRED, DISRUPTED, READY, CANCELLED). Every non-draft row has "Manage", opening a panel (new `DepartureFulfilment.jsx`) with the dates, status and the allowed actions only: "Commit to run" (minimum-seats departures until committed, and DECISION_REQUIRED / DISRUPTED, before departure time) with a confirm step; "I can't run this departure" (PUBLISHED, BOOKING_OPEN, COMMITTED, DECISION_REQUIRED, READY, before departure) asks for a reason (5 to 1000 characters, required), then a confirm step that says selling stops, open holds end, paid passengers stay booked while Travelly arranges their journey and are told, and a departure nobody paid for is withdrawn. Fixed departures that are still selling show no Commit (the API would answer DEPARTURE_ALREADY_GUARANTEED). Errors handled: DEPARTURE_ALREADY_GUARANTEED, DEPARTURE_NOT_COMMITTABLE, DEPARTURE_STARTED, DEPARTURE_NOT_REPORTABLE, VERSION_CONFLICT, DEPARTURE_NOT_FOUND, validation (field message), 403, network; the list is re-read after every action and buttons are disabled while saving.
- Admin, Services & Routes, new "Needs attention" tab (`AdminAttention.jsx`, AdminList): `GET /admin/departures/attention`, filter (All, Decision needed, Disrupted), compact rows (reference, route, date, seats booked, paid amount), paging, Details with safe facts only. "Cannot fulfil, refund everyone": reason (5 to 1000), a confirm step stating the booked seats and paid amount (the API gives seat counts, not booking counts), then `POST /admin/scheduled-trips/{id}/cannot-fulfil`. The result shows the number of refunds created and the total, whether PayHere refunds are waiting in Processing, and "Open Refunds". Errors: DEPARTURE_NOT_ESCALATED, DEPARTURE_STARTED, VERSION_CONFLICT, DEPARTURE_NOT_FOUND, ADMIN_REQUIRED, validation.
- Passenger ticket page (step 3): a compact notice for REPLACEMENT and REFUND. `GET /notifications` does not return `notification_type`, so a notice is recognised by its booking and the exact server titles ("We are arranging your journey", "Departure cancelled - full refund", "Refund sent", "Booking cancelled"); only the server's title and text are shown, with a short pointer (nothing to do / refund status below, which is the cancelled-ticket refund panel). There is no ticket detail page under My Trips (that list is private hire only), so the notice lives on the ticket page.
- Mocked 43 states: every owner status, commit success and 5 errors, report success (disrupted and withdrawn) and 4 errors, admin empty and 30-row lists with filter, cannot-fulfil success (Sandbox and PayHere) and 6 errors, passenger REPLACEMENT, REFUND and no notice. 1280x585 and 1920x1080: page scroll 0, no inner scroll, no overflow, no control overlap. Language test 64/64.

## Protected fulfilment: replacement vehicle (contract 03F2, sections 5 and 6)

- Owner, departure panel (Manage), only for DECISION_REQUIRED or DISRUPTED before departure: "Use another of my vehicles". A picker lists the Owner's own approved vehicles (not the current one) with seats and availability as `GET /owners/me/vehicles` returns them; inactive ones are disabled. Continue, then a confirm step (seats move automatically: same seat code when it exists, otherwise the next free seat; open holds end; each passenger may accept or reject for a full refund), then `POST /scheduled-trips/{id}/replacement-vehicle` with `{expected_version, vehicle_id}`. Success notice shows `moved_seats`; the list is re-read. Errors REPLACEMENT_NOT_ALLOWED, REPLACEMENT_VEHICLE_UNAVAILABLE, VEHICLE_SCHEDULE_CONFLICT show the contract's server message (translated when it is one of the known texts); REPLACEMENT_TOO_SMALL shows "This vehicle has 12 bookable seats; 14 passengers are booked."; VERSION_CONFLICT and 404 refresh the list.
- Passenger ticket page: when `pending_change.kind` is REPLACEMENT_VEHICLE and `status` is PENDING (booking CONFIRMED) a decision card replaces the notices: Was and Now vehicle lines (type, make, model, colour, AC, seats), the seat moves (paged, 3 per page) and two answers. "Travel in the new vehicle" sends `{expected_version, decision: "ACCEPT"}`. "Reject and get a full refund" first asks to confirm (the card shrinks to the question so it fits), then sends `REJECT`; the booking is re-read and the cancelled-ticket panel shows the refund (from the answer's `refund`, then the payment history). ACCEPTED shows a one-line "Vehicle change accepted" with the new vehicle. Errors: NO_PENDING_CHANGE, DEPARTURE_STARTED, VERSION_CONFLICT, BOOKING_NOT_FOUND, network; the booking is re-read after each.
- Passenger dashboard: Notifications tile gets one "Action needed / Your vehicle has changed / Now: …" row linking to the ticket page when a notification titled "Your journey has a replacement vehicle" exists and its ticket is still PENDING (the ticket is read to confirm).
- Mocked 22 states: owner picker on DISRUPTED and DECISION_REQUIRED, no action on PUBLISHED/COMMITTED, only-one-vehicle, success and 6 errors; passenger card with 2 and 7 seat moves, accept, reject with confirm (nothing sent before it) and refund, 4 errors, accepted, dashboard row with and without a pending change. 1280x585 and 1920x1080: page scroll 0, no inner scroll, no overflow, no control overlap (error lines needed the "Changed" row removed to fit at 585). Language test 64/64.

## Protected fulfilment: replacement options, requests to another Owner (contract 03F2, sections 7 to 10)

- Owner, departure panel: the single "Find a replacement vehicle" action replaces "Use another of my vehicles" (only DECISION_REQUIRED or DISRUPTED, before departure, and not while waiting for another Owner). It loads `GET /scheduled-trips/{id}/replacement-options`, with a "Find a vehicle by reference" box (`?reference=`, Enter or Search, "Show all" resets). Each option shows reference, whose vehicle (My vehicle or the Owner's name), make, model, type, colour, AC, seats and bookable seats. An own vehicle goes through section 5 (`replacement-vehicle`); another Owner's vehicle goes through section 8 (`replacement-request`) after a confirm step that says nothing moves until they accept and that the Owner cannot commit or use their own vehicle meanwhile. After a request the panel and list show the "Waiting for the other Owner" state (`replacement_status` AWAITING_OTHER_OWNER) and Find and Commit are hidden. Errors are the contract's messages as returned (REPLACEMENT_PENDING, REPLACEMENT_NOT_ALLOWED, REPLACEMENT_VEHICLE_UNAVAILABLE, VEHICLE_SCHEDULE_CONFLICT, VERSION_CONFLICT, REPLACEMENT_TOO_SMALL with its seat counts); a REPLACEMENT_REQUEST_DRAFT answer when publishing such a draft is shown too.
- Owner, new "Replacement requests" tab in Ticket departures (`GET /owners/me/replacement-requests`): rows with the original departure reference, route, time, requested vehicle, booked seats, price and who asked; Accept and Decline while `answer_pending`. Accept asks for the Driver (I will drive, one of my Drivers, or one found by reference, same picker as the departure form), then a confirm step, then `POST /scheduled-trips/{draft id}/replacement-answer` with `{expected_version, decision: "ACCEPT", operator_driver_user_id}` (null for "I will drive"). Decline needs a reason (3 to 1000 characters, from the API schema) and a confirm step. The contract errors NO_REPLACEMENT_REQUEST, REPLACEMENT_NOT_ALLOWED, REPLACEMENT_TOO_SMALL, VEHICLE_SCHEDULE_CONFLICT, DRIVER_NOT_ELIGIBLE, VERSION_CONFLICT and 404 show the server message; the list is re-read after every action. Empty state uses EmptyState.
- Passenger replacement card: when `pending_change.operator_changed` is true it also shows "New operator" with `replacement_vehicle.operator_name`. To keep it inside 1280x585 the payment line under the card is hidden while an answer is pending.
- Mocked 38 states (picker with own and other vehicles, reference search and no match, no fit, options 404, request success and 5 errors, waiting state, draft publish error, requests empty, list, 25-row paging, accept as myself, with a listed Driver and with a Driver found by reference, decline, 7 answer errors, passenger with and without operator change). 1280x585 and 1920x1080: page scroll 0, no inner scroll, no overflow, no control overlap. Language test 64/64.

## Role workspaces: one dashboard per person (contract 03W, sections 1-3)

- **Sign-in destination** (`loginDestination`): plain sign-in goes to the highest approved role, Admin > Owner > Driver > Passenger. Owner / Driver landing pages go to that role's dashboard when approved, otherwise to `/owner/onboarding` / `/driver/onboarding`. A pending, rejected or suspended role never wins. The old rule "plain sign-in opens the Passenger workspace" is gone; `tests/workspaceRoutes.test.js` was rewritten to the new rules. Nothing is remembered after logout (unchanged).
- **Owner sidebar**: Overview, My vehicles, Prices, Routes, Ticket departures, Bookings for my vehicles, Replacement requests, Settlements, Travel & booking, My driving (approved Owner + approved Driver only), then Settings, Profile, Logout. The sidebar is identical on every Owner page. Replacement requests is its own page (`/owner/replacement-requests`), the same component as before (the tab in Ticket departures is removed). The earlier Operations page is no longer in the sidebar; it stays reachable from Bookings for my vehicles ("Assign Drivers and live trips").
- **Travel & booking** lives inside the Owner and Driver shells under `/owner/travel/...` and `/driver/travel/...`. The Passenger pages are the same components: `features/passenger/travelRouter.jsx` re-maps their Passenger paths (`/travel/...`, `/bookings`, `/trips/...`, `/hire`, `/vehicles/...`, `/owners/...`) to the current workspace, so nothing is copied and nothing leaves the shell. Old `<role>/personal/...` links redirect to the same page under `/travel`. Passenger-only and Admin screens are unchanged.
- **My driving** (`/owner/driving`, `/owner/driving/trips/:tripId`): tabs Trips I drive / Driving history. Data: `GET /bookings?as=driver` (private hire) and `GET /scheduled-trips?driving=true` (ticket departures). The trip page (passenger QR/PIN check, start, live position, road problem, finish) is the existing Driver trip page. Empty state: "Trips you drive yourself appear here." An Owner-only person is sent to the dashboard if they open the address.
- **Booking lists** use `?as=`: My trips `passenger`, Bookings for my vehicles and Settlements `owner`, driving `driver`.
- Measured at 1280x585 and 1920x1080: page scroll 0, no inner scroll, sidebar (13 entries with My driving) ends at y=566 of 585 with no clipped link, card never overflows.

## Role workspaces part 2: My roles, Settlements, PayHere refund states, reminders, cleanup (03W 4, 03P E6-E7 and F, 03R)

- **Profile > My roles** (`features/auth/MyRoles.jsx`, a fourth tab on the Profile page): Passenger always with a tick; Owner and Driver each show Approved, Waiting for approval, Needs correction (Admin's reason + "Fix and resubmit"), Suspended (reason, no button) or "Become an Owner" / "Become a Driver". Data: `GET /users/me/role-requests/{OWNER|DRIVER}/status`. Buttons are links to the existing `/owner/onboarding` and `/driver/onboarding` forms; there is no second copy of the form. A status error shows a row-level "Try again".
- **Owner Settlements** (`/owner/earnings`, `OwnerFinanceOverview`, replaced the bookings placeholder): `GET /owners/me/settlements` in four tabs: To be paid to you, Commission you owe, Waiting for review, Paid and settled. Every payable row shows `payable_amount` ("Payable LKR 1,450.50" for a partly refunded payment); totals `payable_amount` and `commission_due_amount` sit above the list. Paged, empty states with EmptyState.
- **Admin Refunds**: `failure_code` and `failure_message` are shown. PROCESSING + `PAYHERE_REFUND_FAILED`: "Send to PayHere again" (`POST /admin/refunds/{id}/payhere`, body `{}`, with a confirm step) or "Refund in the PayHere portal, then record it". `PAYHERE_MANUAL_REQUIRED`: "Do the bank transfer, then record it". `PAYHERE_REQUESTED`: "Check the PayHere portal, then record it" (never offers a resend). Recording reuses the existing complete step. Errors `REFUND_NOT_RETRYABLE` and `PAYHERE_REFUND_API_OFF` have their own messages. A PROCESSING refund with no code keeps the earlier portal flow.
- **Reminders (03R)**: `DOCUMENT_EXPIRY` and `MAINTENANCE_DUE` appear first in the Trip notifications tab of Bookings for my vehicles (Owner) and the Driver lists. A document reminder opens the document upload (the person's Documents tab, or the vehicle's Documents tab); a maintenance reminder opens that vehicle's Maintenance tab (`/owner/vehicles/{id}?tab=maintenance`). `GET /notifications` does not return `notification_type` or `action_payload`, so reminders are recognised by their fixed wording and the vehicle from its registration number against the Owner's vehicles; both are used directly when the API starts returning them.
- **Cleanup**: `PassengerEventHire.jsx` (removed `/event-hire/*` endpoints) and `PrivateEvidenceUpload.jsx` are deleted with 22 strings; `/travel/book/event` and the Event hire tile now go to the private hire flow (`/travel/book/details/event`).

## Road alerts (contract 03A)

- **Driver live trip** (Operate trip > Live position, used by the Driver workspace and My driving): a side rail beside the position and alert list, never drawn over them. Closed it holds a round Report-an-alert button, a round microphone and the "Speak road alerts" switch. Open it shows five big buttons (Police, Speed check, Accident, Roadblock, Road hazard, each with an icon; at least 52 px high, 72 px on tall screens). One tap sends `POST /road-alerts` with `trip_id`, `alert_type`, the device position (`latitude`, `longitude` as strings) and heading (`travel_direction_degrees`) and `source_input: "BUTTON"`; if the device cannot give a position it uses the position the trip last shared. A merged result says it counted as a confirmation. Server errors (`ALERT_TOO_FAR`, `TRIP_NOT_ACTIVE`, 429, ...) show the server's own message.
- **Voice**: the browser's speech recognition with `ta-LK`, `si-LK` or `en-US` from the selected language. The recognised words go to `POST /road-alerts/voice-classify`; the returned `confirm_prompt` is shown and spoken (when the device has a voice for the language) with big Send and Cancel buttons, and a spoken "yes", "ஆம்" or "ඔව්" also confirms. Only then `POST /road-alerts` with `source_input: "VOICE"`, `driver_confirmed: true`, `confidence_score` and the heard text as `description`. Not understood: the server's message shows and the five buttons open. Without speech recognition, or when the microphone is denied, the mic is disabled with a short message and the five buttons keep working.
- **Alerts and voting**: `GET /road-alerts?trip_id=` every 45 seconds while the trip runs; paused while the tab is hidden (and refreshed when it is visible again), stopped when the trip ends, one request at a time. Rows show the server's `name`, `message`, distance and status; when `can_vote` is true they show Still there / Not there (`POST /road-alerts/{id}/votes`).
- **Speaker**: "Speak road alerts" switch, off by default, remembered on the device. When on, a new alert is spoken once (`action_payload.speak` if present, else `message`) in the language the server sent it; with no voice for that language the text stays on screen with one line saying so. Alerts already up when the page opens are not read out. A new `ROAD_ALERT` notification (`GET /notifications`, `notification_type`) is spoken too, from `action_payload.speak` or the message, once per notification; an alert that arrives both in the nearby list and as a notification (same `road_alert_id`) is spoken once. Expired notifications and notifications that already existed when the page opened are not read out.
- **Admin**: `/admin/road-alerts` (the existing Road Alerts sidebar entry) is now an AdminList with a status filter, paging and EmptyState. Details show reporter, how it was reported, confidence, place, counts and any reason; Verify needs no reason, Reject and Remove need a reason and a confirm step; closed alerts show no actions.
- Measured at 1280x585 and 1920x1080: page scroll 0, card never overflows, the list scrolls only inside itself, the rail never overlaps the content area.

## Two animations: navbar needle and login card light

- **Navbar needle** (shared `TravellyBrand`, so `Header` and `LandingHeader` both get it; CSS in `styles/navbarSpeedometer.css`): the logo has two invisible hover halves. Hovering the left half swings the needle about 14 degrees to the left, the right half to the right, and it settles back when the pointer leaves (a short transition with a small overshoot). Keyboard focus-visible on the logo gives the same swing. Clicking the logo adds a class that plays one full 360-degree sweep (0.9 s) and removes itself when it ends; clicks during the sweep do nothing. The motion uses the separate CSS `rotate` property, so it adds to the angle the existing script sets with `transform` and the two never fight. The script's quick sweep still runs for every other navbar control but no longer for the logo.
- **Login vehicle card** (`AuthLayout` `JourneyCard`, `styles/authGlass.css`): a thin (1.5 px) ring inside the card's own box with a warm gold to soft white light travelling around it in a 7 s linear loop. A masked window clips a larger conic-gradient layer that turns with `transform` only, so nothing spills outside the card, the card size does not change and there is no layout shift. The earlier conic-angle animation and its blurred glow are switched off (their rules are kept, overridden).
- **Reduced motion**: both animations are off. The needle stays at rest and the hover halves are disabled; the card keeps a static gold to soft white border.
- Measured at 1280x585 and 1920x1080: login page scroll 0, card box identical with and without the ring, no overflow.

## Road alerts: hands-free voice confirmation and Screen Wake Lock (contract 03A update)

- **Voice, one tap then hands free**: the mic is tapped once. The app listens once, sends the words to `POST /road-alerts/voice-classify`, shows and speaks `confirm_prompt`, and only when the speech has ended listens again by itself for `confirm_seconds` (10) with a countdown ring beside the question and large Send / Cancel buttons. A yes word or Send posts the alert (`source_input: "VOICE"`, `driver_confirmed: true`); a no word, Cancel or silence until the ring ends sends nothing. `sent_text` or `not_sent_text` is then shown and spoken. The spoken-yes handling with built-in Tamil, Sinhala and English words is gone: matching uses the server's `yes_words` and `no_words`, whole words in lower case, and both heard counts as no.
- **Microphone discipline**: the app never listens while it speaks (listening starts from the end of the speech, or at once when the device has no voice for the language and the texts are only shown), and the microphone is stopped after the answer or the timeout. Nothing listens between alerts.
- **No recognition or blocked mic**: the mic button is hidden (a short line says why) and the five buttons keep working.
- **Screen Wake Lock** (`useScreenWakeLock`, `screenWakeLock.js`): while the trip is `IN_PROGRESS`, `BREAKDOWN` or `ASSISTANCE_REQUIRED` the Driver's live trip page asks for `navigator.wakeLock.request('screen')`, asks again on `visibilitychange` when the page becomes visible, and releases it when the trip ends, on `pagehide` and on leaving the page. If the browser has no wake lock or the request is refused, one line shows: "Keep the screen on during the trip so alerts and location keep working. Tip: keep the phone on the charger." No dialog. The Passenger part is a gap: there is no Passenger trip page with road alerts or a speaker yet.
- Measured at 1280x585 and 1920x1080: no page scroll, the confirmation block and ring fit with the alert list scrolling only inside itself.

## Notifications by type, role-status check, Admin settlement screens (contracts 03N and 03P F)

- **Notifications by type, not wording** (`features/notifications/notices.js`, `reminders.js`): `GET /notifications` now carries `notification_type` and `action_payload`, so every place that matched a title or body now matches on type and payload keys (03N table):
  - the replacement-vehicle row on the Passenger dashboard is a `REPLACEMENT` with `action_required` and a booking (`booking_id` or `action_payload.booking_id`); it opens that booking's change card and no longer reads the ticket to find it;
  - the ticket page notices (`FulfilmentNotice`) are `REPLACEMENT` without an answer to give and `REFUND` for that booking;
  - reminders are `DOCUMENT_EXPIRY` and `MAINTENANCE_DUE`, linked by `action_payload`: `vehicle_id` opens that vehicle's Documents or Maintenance tab, a document without `vehicle_id` opens the person's own documents, and a missing key falls back to the vehicle list. The wording match, the registration-number match and the extra read of the Owner's vehicles are gone;
  - `ROAD_ALERT` notifications are kept in the Trip notifications list and shown greyed with "Expired" once `expires_at` has passed (03O section D). The road-alert voice and speaker logic is unchanged.
  - There is no Admin screen that matched notifications by wording any more (the old support-notice page was removed in the cleanup).
- **Profile > My roles**: checked against 03N. REJECTED shows "Needs correction" with `application.rejection_reason` and "Fix and resubmit"; SUSPENDED shows "Suspended" with `suspension_reason` and no button. The reason shown now belongs to the state shown (an old rejection reason is never shown on a suspended role). The button opens the same application form, which posts the same request again and returns the role to PENDING.
- **Admin Payments** (`/admin/payments`, the existing Payments sidebar entry; `AdminPayments.jsx`): tabs Totals (F1 totals), Payments (F1 list with a type filter, paging and details) and Owner settlements (F2). An Owner's details have four sections (To be paid, Commission due, Waiting for review, Paid and settled) with `payable_amount` on every payable row. Payable rows are selected and recorded as a payout (F3) after entering the bank reference; commission-due rows as commission received (F4). Both go through a confirm step, nothing is sent before it, each press sends one `idempotency_key` (a retry after a lost answer reuses it), and `SETTLEMENT_NOT_ALLOWED` shows the server's message with the references of the payments it names. Waiting-for-review and settled rows are read only. The Owner's own screen (F5) is unchanged.
- Measured at 1280x585 and 1920x1080: no page scroll, no card overflow; lists scroll and page inside themselves.

## Travelly AI: chat panel, "Find a ride" and "Help" (contract 03AI)

- **The card**: the dashboard AI card (`TravellyAiPanel`, Passenger, Owner and Driver dashboards) was a "Coming soon" placeholder with two disabled buttons. Both are live now: "Chat with Travelly AI" (short label "Chat" on narrow cards) opens the panel, "Talk by voice" opens it and listens for one spoken answer. The greeting is "Hi {name}! I'm your Travelly AI assistant".
- **The panel** (`features/ai/AiAssistant.jsx`, a modal `<dialog>`): header, two tabs (**Find a ride** and **Help**), a message list that is the only thing that scrolls, and the composer pinned at the bottom. It is 560 px wide and up to 640 px high and always inside the window (12 px gutter at 1280x585); at phone width it fills the screen with an 8 px margin.
- **Find a ride** (`POST /ai/search-assist`, public, no sign-in header): each turn sends `message`, `language` (app language), the previous reply's `filters` (including edits made in the card) and `asking`. The reply's `notes` show above its `question`; `options` are quick-reply chips that send their `value`. When `ready` is true a "Check your search" card is built from `summary`: every row is editable, pickup and destination (hire) use `PlaceSearch` seeded with the text and the person must pick the verified place, and Search stays off until the places and required fields are filled ("Still needed: ..."). **Search** writes the booking draft (`travelly.passenger.booking-draft.v2`) from the 03AI mapping table and opens the vehicle list, or for a ticket opens the ticket page with `origin`, `destination`, `date` and `travellers` in the address, which runs the normal ticket search once. **Edit in form** writes the draft and opens `form_path`. The AI never chooses a vehicle, books or pays.
- **Help** (`POST /ai/help`, `GET /ai/help/topics/{lang}`): the answer shows `title`, `answer`, the numbered `steps` (with the API's `note` above them when `steps_language` is `en`), an **Open this page** button that goes through `travelPath` (so the Owner and Driver workspaces open their own copy) and `related` chips; `found: false` shows the answer with a **Support** button. A "What can I ask?" list of topics sits at the top of the Help tab.
- **Voice**: browser speech recognition (`ta-LK`, `si-LK`, `en-US`), one mic tap per answer, off again after it; the recognised text is sent as `message` (or the help question). The reply's question is spoken only when the device has a voice for the language, otherwise it is text only. With no recognition the mic is hidden and a short line says typing works; a denied microphone hides it with a message.
- **Errors**: a network failure, a rate limit (429 `RATE_LIMITED`) and any other error each show one friendly line in the chat; a raw error is never shown.
- Measured at 1280x585, 1920x1080 and 390x800: no page scroll, the panel inside the window, the composer always visible.

### Travelly AI: signed-in only (contract 03AI update, 13 Nov 2026)

- **Auth**: the AI endpoints are for signed-in customers. `POST /ai/search-assist`, `POST /ai/help` and `GET /ai/help/topics/{lang}` now go through the app's normal API client (`aiClient.js` / `aiRequests.js`), which sends the Bearer token and handles an expired session exactly like every other screen (renew once, otherwise end the session and return to sign-in). The earlier no-sign-in behaviour (the public request helpers) is removed, and a test guards against it coming back.
- **Errors, never raw**: a network failure, an ended session (401), a message of the wrong length (422), the rate limit (429 `RATE_LIMITED`) and anything else each show one friendly line in the chat. Past the daily caps the backend answers with its built-in rules (`engine: "rules"`), so there is no error to show.
- **Help paths** (clarification 1, `aiHelp.js`): the help path is a Passenger path and opens the person's own workspace copy. `/passenger/support` becomes `/owner/support` or `/driver/support` inside those workspaces, `/travel/...` and `/bookings` go through `travelPath`, `/dashboard` becomes the workspace dashboard, `/owner/...` and `/driver/...` topics show their button only to people with that approved role (the steps still show), and `/account`, `/forgot-password`, `/reels` and the two onboarding pages are used as given.
- **Intro**: one line from the UI with no API call until the person types or speaks: "Hi! Tell me where you want to go, or ask how to do something in Travelly." A message is cut to 500 characters.
- **Where the card is**: only the Passenger, Owner and Driver dashboards. It is no longer on the Admin dashboard (the Recent bookings tile there now uses the full row) and was never on the landing page.

### field_errors: one shared helper (`services/fieldErrors.js`)

- Backend confirmed `field_errors` is always a **list** of `{field, message}` (api.js puts it on `error.fields`). Every screen now reads it through `fieldErrors`, `fieldErrorMap` and `fieldErrorText` instead of its own `(error.fields || [])` and `Object.fromEntries(...)`: the sign-in, registration, reset and profile forms, the document and application evidence forms, owner rates, vehicle facts and calendar, maintenance, departures and replacement, refunds, payment settings, settlements, ticket cancel, ticket and private hire payment, and the Driver trip odometer and problem forms.
- **Inputs**: the message shows under the input named by `field`; a dotted name such as `payer.address` or `rules.2.price` also answers to its last part (`address`, `price`). With an empty list the response message shows.
- **Codes that use the list for data**: `PAYMENT_IN_PROGRESS` (`waitingPaymentId`: the waiting payment id), `PAYMENT_AMOUNT_MISMATCH` (`correctAmount`: "The amount changed. It is now 3000.00 LKR." and the booking is read again), `PAYER_DETAILS_REQUIRED` (`payerFieldNames`: the `payer.*` fields still needed), `SETTLEMENT_NOT_ALLOWED` (`settlementIds`: the payment ids, shown as booking references with the server's message), and the limit or rule messages of `REFUND_AMOUNT_INVALID` and `PAYMENT_SETTINGS_INVALID`.
- The Driver trip page now shows the server's message under the odometer (start and end), problem details and pickup code inputs.
- **payable_amount**: audited. Every "how much will be paid" amount in the Owner Settlements screen and the Admin payments and settlements screens uses `payable_amount` (rows, totals and the payout total); `owner_net_amount` only appears as the original "Owner share" in a payment's details.
- **Help paths** (clarification 1): `found: false` returns `/passenger/support`, which opens `/owner/support` in the Owner workspace, `/driver/support` in the Driver workspace and stays `/passenger/support` for Passengers; topic paths go through `travelPath`.

## Odometer photo proof: start, finish and the proof card (contract 03O, A, B and E)

- **Start trip** (`features/odometer/OdometerStep.jsx`, used by the Driver trip page in the Driver workspace and My driving): the odometer step comes first. It opens `POST /trips/{id}/odometer-session` and shows the "Odometer reading" box with "Last recorded: {minimum_km} km". **Take photo** opens the in-app camera only (`getUserMedia({video:{facingMode:'environment'}})`, a live preview and a Capture button; the frame is drawn on a canvas and sent as a JPEG). There is no file input and no gallery. The location is asked for at the same moment (`getCurrentPosition`, high accuracy). The photo goes to `POST /trips/{id}/odometer-photo` as multipart with exactly `capture_code`, `stage`, `typed_km`, `latitude`, `longitude`, `accuracy_m` and `file`; each photo uses its own capture code (Retake opens a new session).
- **Results**: `MATCH` "Photo matches ✓" (Start opens); `MISMATCH` "Photo: 45,320 • You typed: 45,230" with Retake and Edit number, Start stays off; `UNREADABLE` "Couldn't read the photo (try n of 3). Move closer, turn on the light." with Retake, and after the third try "Start with the typed number" in orange with Start on; `NOT_CHECKED` "Photo saved as proof" with Start on. Start and Finish open only when the server says `can_continue`, and only for the number in the box when the photo was checked: changing the number asks for a new photo.
- **Errors**: `NOT_AT_PICKUP` shows "Take the start photo at the pickup point."; `CAPTURE_CODE_INVALID` opens the camera again with a new capture code; `ODOMETER_BELOW_LAST`, `ODOMETER_BELOW_START`, `INVALID_PHOTO`, `PHOTO_TOO_LARGE`, 429 and `ODOMETER_PROOF_REQUIRED` show the server's message (the field_errors helper reads any list), and `ODOMETER_PROOF_REQUIRED` also starts a new odometer step. With no camera or no location the step says so and Start stays blocked.
- **Start** posts the existing start with `start_odometer_km` = the same number; the trip page then continues as before (the live map opens by itself in the next step).
- **Finish trip**: the same step with `stage: "END"` (the minimum is the start reading), then the existing complete call with `end_odometer_km` = the same number. Afterwards the summary shows start km → end km and the distance, with **See proof**.
- **Proof card** (`OdometerProofCard.jsx`, `GET /trips/{id}/odometer-proof`): "Trip distance" with start km, end km and distance, a result badge per photo (Match ✓ / Not readable / Not checked) and two thumbnails fetched with the sign-in token as blobs (`photo_url`) and shown from object URLs, which are revoked when the card closes; tap enlarges. After the keep days (`photo_available: false`) only the numbers show with "Photos are kept for 7 days after the trip". It appears as a "Trip distance" tab on the Passenger and Owner booking page once the trip has started, in the Driver summary, and in the Admin booking details.
- Measured at 1280x585 and 1920x1080: no page scroll, the card never overflows; the camera is a modal that fits the window.

## Live trip map, Trip in progress card (contract 03O C, D and GET /trips/active)
- **Map** (`features/trips/TripMap.jsx`): Leaflet 1.9.4 (normal dependency, circle markers, no marker images) with OpenStreetMap tiles, no key, "© OpenStreetMap contributors" attribution always visible. Draws START (green), STOP (grey), END (red), the road `line` ([lng,lat] pairs; straight dashed lines between the points when it is null), the vehicle and nearby road alerts (`GET /road-alerts?trip_id=`, same polling rules). If tiles fail, a text line with the route shows over the still-drawn route. "Follow me" ends when the map is dragged.
- **Driver:** after Start the Operate trip page opens on the map (no Live position tab any more; position text is a small strip with Stop sharing / Send my position now; sharing starts by itself on a running trip). Fixed side column: road alert (5 types), mic (10 s voice confirm, 03A), speaker, Problem on the road, Finish trip (opens the END odometer step; "Back to the map" on every form). Wake Lock stays on.
- **Passenger / Owner (not driving):** read-only `/trips/:id/map` (also under `/owner/travel` and `/driver/travel`): map, position strip, alert info, speaker switch only. A viewer whose `viewer_roles` has DRIVER is redirected to the Operate trip page.
- **Trip in progress card** (`GET /trips/active`, on open and every 30 s, paused when the tab is hidden, one request at a time): Passenger, Owner and Driver dashboards, two cards then "{n} more trips", none when empty; opens through `travelPath` in the current workspace. Back or Dashboard never stops the trip.
- **D:** road alert buttons removed from the Driver dashboard (quick link and tile link); Admin keeps its own alert tile.
- Measured (no page scroll, card never overflows): 1280x585 map 802x206 (694x302 with the five buttons open), 1920x1080 map 888x718, 390x800 map stays visible with the controls in a bar under it. Passenger map 774x342 / 872x757 / 322x405.

## Cash commission rule (contract 03CM)
- **Owner banner** (`features/settlements/CommissionBanner.jsx`, rules in `commissionStanding.js`): from `commission_standing` on Settlements and the Owner dashboard. FREE (only when `amount_due` > 0) info; GRACE warning colour; `blocked` red ("New bookings are stopped until you pay … Bookings you already have are not affected."). NONE shows nothing. `blocked` decides, so an extended BLOCKED stage with `blocked:false` shows the grace warning. Dates through `formatDate`, money through `money()`.
- **Admin Settlements:** "Commission overdue" chip filter (`?overdue=true`), stage chip + "{n} days open" on every Owner row and in the details, "Extend days" (days + reason, confirm step, no idempotency key because the contract names none; server `field_errors` under the inputs), and "Take commission out of this payout" on the payout form (`settle_commission: true`); after saving it shows `commission_set_off` and "Amount to send to the bank" (`bank_transfer_total`); `payable_amount` stays per row.
- **Passenger:** `VEHICLE_NOT_AVAILABLE` / `DEPARTURE_NOT_AVAILABLE` show the server message with a "Search again" action (`components/NotAvailableNotice.jsx`) on the vehicle quote, the request review and the ticket hold. No reason about the Owner's money is shown.
- **Owner's own screens:** unchanged (the Screens section does not ask for anything there).
- Measured at 1280x585, 1920x1080, 390x800: no page scroll; banner 58px high; Admin detail card never overflows.

## Travel Reels, profile and vehicle rating (contract 03SO, viewing part)
- **Dashboard card** (`features/social/ReelsCard.jsx`, `GET /social/feed?type=REEL&limit=8`): thumbnails with the place and "{n} views"; See all opens `/reels` in the current workspace (`travelRouter` Link, `/reels` and `/social/` added to the Passenger paths in `travelPath`). Passenger and Owner: bottom row is now Reels / existing tile / Travelly AI (three tiles). Driver: the Reels card replaces the "Quick actions" tile (its links are in the sidebar).
- **/reels** (`ReelsPage.jsx`, also `/reels/:postId`, and under `/owner/travel` and `/driver/travel`): vertical 9:16 player filling the page height (no page scroll), autoplay muted, tap for sound, only the visible reel is rendered/playing and only the next one is preloaded. Swipe, wheel and arrow keys move on (450 ms guard). `POST /social/posts/{id}/views` with `{}` once per reel per visit when playback starts. Side buttons: like, comments, save, share (`share_path`, `navigator.share`, else copy), follow, ⋯ (Report; Edit / Remove on my own post). Tabs Reels / Photos / Reviews / Following; hashtag chips filter (`hashtag=`); paging with `next_before`. `media_url` and `thumbnail_url` used as given (signed `?t=` included, no Bearer token). Navbar "Travel Reels" is now a link (not for Admin).
- **Panels** (`ReelPanels.jsx`): comments with one level of replies and remove, report (3–500), edit (`expected_version`; 409 `VERSION_CONFLICT` shows the server message and reloads the post), remove with confirm. Server errors through `services/fieldErrors.js`.
- **Profile** `/social/users/:reference`: posts grid (paged), counts, Follow, Saved tab on my own profile. **Vehicle page:** "★ average (count)" and the latest two reviews from `/social/vehicles/{id}/reviews`.
- Measured, no page scroll: 1280x585 stage 938x431 (video 233x415, comments panel 340 wide beside it); 1920x1080 video 497x884; 390x800 video 330x586 with buttons on the video and panels covering it. Dashboard card 306x113 at 1280x585, fits the bottom row.

### Cash commission follow-up (backend answers)
- Stage chip: No commission / Free period / Grace period / Blocked; stage BLOCKED with `blocked:false` shows "Extended". Days: "Opened today", "1 day open", "{n} days open" (separate strings, so Tamil and Sinhala need no plural rule).
- Banner for the extended state: "Bookings are open until {extended_until}. Pay {amount_due} before then or new bookings stop." (date from `extended_until`; GRACE keeps `blocked_from`). Admin shows "Extended until {extended_until}".
- Extend days: the confirm and the form button are disabled while the request runs, plus a ref guard against a double click.
- Payout tick only when `commission_standing.amount_due` > 0; after sending, a `commission_set_off` of 0 reads "No commission was taken out" (bank transfer total still shown).
- Mocked states: NONE, FREE, GRACE, BLOCKED, BLOCKED extended. Banner stays 58px high; no scroll at 1280x585 and 1920x1080.

## Creating posts and Admin moderation (contract 03SO)
- **+ Post** (`features/social/PostCreate.jsx`, `/social/post`, also under `/owner/travel` and `/driver/travel`; button on the /reels top bar): three steps (kind, media, words and sharing). Reel: the length is read from `video.duration` in the browser, over 60 s shows "Trim to 60 seconds", over 50 MB shows the limit, neither is uploaded; a canvas frame becomes `thumbnail`; `duration_seconds` is sent. Photo; Review (vehicle from `/social/me/reviewable-vehicles`, stars, caption, optional photo). Visibility Everyone / Followers / Only me; place and hashtags (30 at most). Multipart through `uploadForm()` (XHR in `services/api.js`: same address, Bearer token, 401 renew once, same error shape) with progress, Cancel upload (on the left, so a double click on Post cannot hit it) and a single submit; the Post button is disabled while uploading. Server errors (413, 422, 403 REVIEW_NOT_ALLOWED, 409 ALREADY_REVIEWED, 429) show the server message, field errors sit under the inputs.
- **Admin → Social reviews** (`features/admin/AdminSocialPosts.jsx`, `/admin/social-reviews`): AdminList of `GET /admin/social/posts` with chips Reported (`?reported=true`, default) / All posts / Hidden (`?status=HIDDEN`), paging, details with media, open reports, and Hide / Restore with a reason and a confirm step (`POST .../moderation { expected_version, action, reason }`; 409 and 422 messages shown).
- **Viewer report:** reason (3–500) then a confirm step, then `POST .../report { reason }`; 409 `OWN_POST` / `ALREADY_REPORTED` show the server message.
- Measured at 1280x585, 1920x1080, 390x800: no page scroll, cards never overflow.

## Monthly reports: Owner and Admin (contract 03RP)
- **Owner → Reports** (`features/reports/OwnerReport.jsx`, `/owner/reports`, sidebar entry after Settlements, the other entries keep their order): `GET /owners/me/reports/monthly/{YYYY-MM}`; month picker defaults to the previous month and stops at this month (2020-01 first). Tabs Overview / Trips and km / Earnings / Maintenance / Documents. Overview starts with the **Month result** card (income − expenses = profit ✓ green, or loss ▼ red, from `result`; the icon repeats the colour), then the summary tiles. Other tabs keep a compact result strip on top. **Download PDF** fetches `.../pdf` as a blob with the Bearer token and saves it as `travelly-report-YYYY-MM.pdf`.
- **Admin → Reports** (`AdminReport.jsx`, `/admin/reports`, replaces the old placeholder page): `GET /admin/reports/monthly/{YYYY-MM}`; tiles bookings, trips, km, new users, collected, Travelly income (green), paid to Owners, needs attention (red when above 0, opens the list); Money, People and Needs attention tabs with links to Services & Routes tickets, Payments, Documents and Applications. **Download PDF** opens the blob in a new tab (object URL, revoked after 60 s).
- **Mobile first** (`styles/reports.css`): tiles 2 columns (1 under 360px, 3 from 640, 4 from 1000, 6 from 1500); tables become stacked cards under 720px (date and amount on top, details below with their labels); result card stacks one value per row; Download PDF is full width at the bottom; the list area scrolls inside the card, the page never scrolls sideways.
- Shared header fix (needed for the Admin screens at 360px): at ≤480px the logo width comes from `--nav-logo-w` (96px) and at ≤400px it is 80px with a smaller bell and language box, so the bar no longer widens the page.
- Measured: 360x740, 390x844, 768x1024, 1280x585 and 1920x1080 have no page scroll and no sideways scroll; at 1280x585 the card never overflows (long tables scroll inside the list).

## Event hire (contract 03EV)
- **Owner → vehicle → "Event packages" tab** (`features/owner/EventPackages.jsx`, model in `eventPackageModel.js`): loads the Event service from `GET /service-types` and the saved packages from `GET /vehicles/{id}/services` (`event_packages` on the Event row, version 0 when none). Add, edit and remove on the list (remove asks "Remove {name}?" first), then **Save packages** sends `PUT /vehicles/{id}/event-packages` `{service_type_id, expected_version, enabled, packages:[{id (uuid made here, kept on edit), name, hours, price (2 decimals), notes?}]}`. Checks: name, hours above 0 and at most 24, price above 0 with two decimals, 1 to 20 packages. The server message is shown after saving; `VERSION_CONFLICT` shows the server message and reloads the packages. One save at a time.
- **Passenger:** the Event tile uses the EVENT service type; the details step labels the destination "Event place" (PlaceSearch); search sends DAY_HIRE / ONE_WAY and each returned vehicle lists its `packages[]` as selectable chips (name, hours, price; the first is chosen by default). The quote and the request add `itinerary.event_package_id`, `service_hours=[package hours]`, `direction ONE_WAY`, `method DAY_HIRE` through `withPackage()`. The review shows the package. Then the normal acceptance, trip and payment steps.
- **Fixed package:** booking pages show "Package: name · hours", hide the Owner re-quote editor, the change form and the agreed-rule text for Event bookings, and show that an event booking cannot be re-quoted or changed (`EVENT_FIXED_PACKAGE` messages from the server show as they are). Lists (My trips, Bookings for my vehicles, dashboards) add the package name and hours after the route when the booking carries its price calculation.
- Measured: 1280x585 and 1920x1080 wizard steps and the Owner tab fit without page scroll; 390x800 usable (long review pages scroll inside the card).

## Self-drive rental (contract 03RN)
- **Owner → vehicle → "Rental rates" tab** (`features/rental/RentalRates.jsx`, checks in `rentalModel.js`): `GET/PUT /vehicles/{id}/rental` (first time `{version:0, enabled:false}`; the form starts enabled). Day rate, free km per day, extra km rate, late hour rate (money with at most two decimals), longest rental 1–30 days, notes (500), Enabled, Cash accepted, and up to 10 extras (id made here, name, price, per DAY or ONCE) on an Extras sub-view with add, edit and remove-with-confirm. The server message shows after saving; `VERSION_CONFLICT` shows the server message and reloads.
- **Passenger `/travel/book/rental`** (`RentalUi.jsx`, replaces the unavailable placeholder; also under `/owner/travel` and `/driver/travel`): When and how long → Choose a vehicle (`POST /rentals/search {start_at (UTC), days}`; day rate, free km, extra km rate, Owner notes, optional extras as chips, estimate = day rate × days + extras) → Licence and request (`POST /rentals`, one idempotency key per request, reused on retry) → Request sent (reference, extras price, estimate).
- **Rental booking page** (`RentalBooking.jsx`, used by the booking page when `itinerary.rental` is present): tabs Rental / Price / Actions / Payment (after COMPLETED, `HirePayment`) / Trip distance (`OdometerProofCard`). Price shows `price.estimate` (with `extras_price` and chosen extras) before the return and the `price.final` bill (DAYS / EXTRA_KM / LATE / EXTRA_n lines, total, distance, free km, late hours) after it. Owner actions with a confirm step: accept, decline (reason), cancel (reason, Owner or renter), hand over (03O odometer step START on `booking.trip.id`, licence checked, note → `start_odometer_km`), take back (odometer step END, note → `end_odometer_km`). The renter confirms HANDOVER and RETURN (`POST /rentals/{id}/confirm`).
- Lists (My trips, Bookings for my vehicles, dashboards) label rentals "Self-drive rental · N days"; status chips follow the booking status.
- Measured at 1280x585, 1920x1080, 390x800: wizard steps and tabs fit without page scroll (long vehicle lists scroll inside the card on phones).

## Follow-up: Event package paths, Prices wizard, rental card and reminders (03EV, 03RN)
- **Package on bookings** (`features/booking/eventPackage.js`, one place): `event_package` (Admin oversight, null for other bookings), `price.current.calculation.package` (after acceptance), `proposal.quote.calculation.package` (before). The booking page, My trips, Bookings for my vehicles, the dashboards, Admin oversight (both lists) show "Package: name · N hours"; the earlier guesses are gone.
- **Owner Prices wizard:** the Event service is not offered there. The vehicle step shows the Event status chip from `GET /owners/me/service-readiness` (Ready / Not ready, `rate_rule_count` = packages) and a "Set up Event packages" link to the vehicle's tab (`?tab=event-packages`; `?tab=rental-rates` also works). The service readiness page counts packages for Event and links to the same tab.
- **Trip in progress card:** `kind RENTAL` shows a "Self-drive rental" card with the vehicle and "Open the rental"; it opens the rental booking (Owner managing: `/bookings/{id}?workspace=owner`; renter: through `travelPath`). TICKET and PRIVATE_HIRE still open the map.
- **Rental reminders:** RECONFIRMATION notices whose `action_payload.stage` is UNANSWERED, STARTS_SOON, NOT_HANDED_OVER, RETURN_SOON or OVERDUE (with `booking_id`) are listed in Trip notifications for every role with a link to the rental booking; matched by type and stage, never by title wording.
- **/owner/rentals** redirects to Bookings for my vehicles (there was no sidebar entry).

## Follow-up: report months in Sri Lanka time, rental fields (03RP, 03RN)
- **Months:** the default month and the picker limit use Asia/Colombo (`reportModel.js`, `Intl` time zone, not the device clock): default = the month before the current Sri Lanka month; the picker stops at the current Sri Lanka month (typed values past it, or before 2020-01, are ignored). Tests cover 1 Dec 00:30 Sri Lanka (= 30 Nov 19:00 UTC), 30 Nov 23:59 Sri Lanka and the new-year change.
- **Admin report:** the Bookings tile is `private_hire_bookings` + `ticket_bookings` + `rental_bookings`; a line under the tiles shows the breakdown (private hire, ticket, rental, cancelled).
- **Rental search:** the live estimate is `rental.base_price` (day rate for the searched days) + the `amount` of each chosen extra from `rental.extras[]`; the UI has no price formula of its own. After the request, `price.estimate.base_price` (includes the extras) and `extras_price` are shown as sent.
- **Rental label:** from `booking_type === "RENTAL"` (not `itinerary.rental`): "Self-drive rental · N days" on My trips, Owner bookings, dashboards and both Admin oversight lists (`rental_days` there); the rental booking page opens for `booking_type RENTAL`. A handover that is too early shows the server's `RENTAL_NOT_READY` message through the normal notice (button stays enabled).

## Final cleanup and audit pass (14 Nov 2026)

This section is the final audit record. Everything below was checked with the mocked-API scripts (Playwright, Chrome)
against the dev server; no screenshots.

### Removed
- Source files nothing imported: `features/auth/RoleApplicationCard.jsx`, `components/ApplicationStatusNotices.jsx`,
  `components/TravellyVisuals.jsx` and its `assets/travelly/manifest.json`.
- Unused components and helpers: `Footer`, `Asset` (with its image size table), `BookingPipeline`, `UnavailableFeature`,
  `ItineraryPreview`, `PlatformMapPlaceholder`, `TravellyHelp`, `hasRows`; the Driver/Admin rental placeholder page
  (`RentalRoleUi`) and its strings ("Rental package APIs are not implemented…", inspection placeholders).
- Images and fonts nothing loads (about 20 MB): `-320/-640/-800.webp` variants of icons, destinations, heroes,
  illustrations, fleet and vehicles (only `vehicle-*-400.webp` is used), landing `*-hero-region-*.png` and `logo-*.png`
  copies, `*-entry.png(.png)`, `exo2-travelly-semibold-italic.ttf`, `jakarta-wordmark.woff2`, `ticket-*-outline.svg`,
  `account/*-transparent.png`. `public/references/` and the brand PNGs loaded by name are kept.
- Unused imports in about 100 files and about 130 CSS selectors no component renders (old dashboard/theme layers).
  Frame and colour tokens were not touched.
- `/driver/rentals` redirects to My Assignments and `/admin/rentals` to Booking oversight.

### Fixed
- Raw codes on screen (CONFIRMED, AWAITING_DRIVER, `DRAFT · ACTIVE`, OWNER, VAN, document types, price methods,
  vehicle facts) now go through one label map, `src/i18n/codeLabels.js`. Unknown codes are shown in sentence case. The
  Driver trip title was "பயணம் in progress" and now reads the status label.
- Label tables passed through `t()` (wizard steps, tabs, route options) had 34 strings without Tamil and Sinhala; the
  Stepper did not translate its labels at all. Both fixed; the language test now also checks every code label.
- Console: Leaflet threw `_leaflet_pos` after the map was removed mid-zoom (first fit and "Follow me" no longer animate
  the zoom; `stop()` before `remove()`; the map fits again after React mounts it twice). Missing key on the Trip in
  progress card (rental items without `trip_id` now key on `booking_id`). The other warnings seen in the sweep came
  from the mock (every booking detail returned id `b1`; generic routes without `stops`), not from the app.
- Live trip map: `GET /trips/{id}/map` once, then `GET /trips/{id}` every 20 s for `status` and `location`; polling stops
  at COMPLETED or CANCELLED; "Last seen at …" from `location.updated_at`, "The vehicle position is not shared yet."
  until the first update. `tracking_status` is not used. The dashboard card is the only entry to the map.
- Admin Social reviews: the open details show Hidden/Visible right after Hide/Restore, also when the post leaves the
  Reported list (read again from the full list).
- Phones: the landing header showed every link inline (168–198 px horizontal scroll at 360/390); they sit behind the
  menu button again, with the dropdown under the header. Dashboards at 1000 px and narrower were squashed to tile
  headers by the one-screen height; they now stack at natural height and the page scrolls.
- Sidebar: "Bookings for my vehicles" was 2 px too long at 1366x768 (font 13.5px there).
- One-line field labels carry the full text as a tooltip for long Tamil and Sinhala labels.
- "Not available" notice (409 VEHICLE_NOT_AVAILABLE / DEPARTURE_NOT_AVAILABLE) exercised in the browser on the quote,
  the request review and the ticket hold: the server message and "Search again" show (quote/review go back to the vehicle
  list, the ticket hold to step 1), no page scroll at 1280x585, card scroll only inside at 390x800.

### Sizes checked
- One-screen fit, 55 routes across all roles at 1280x585, 1366x768, 1920x1080 and 2560x1440 (220 checks): no page scroll,
  no horizontal scroll, no clipped card, nothing past the edge.
- Phones, the same routes plus landing/login/register at 360x740, 390x844 and 768x1024 (165 checks): no horizontal scroll
  on any Passenger, Owner, Driver or Admin screen.
- Frame check (navbar, sidebar and content edges) at 1280x585, 1366x768 and 1920x1080: all OK.
- Tamil and Sinhala at 1280x585 and 390x844 on 28 key pages and their tabs: no button, tab or chip text cut or spilling.
  Long field labels end in an ellipsis (one-line label rule) with the full text in the tooltip.
- Odometer Mismatch: the reported ~22 px inner scroll was not reproduced. Start, Finish, Owner My driving and the proof
  card measure scrollHeight = clientHeight at 1280x585 and 1366x768, in English, Tamil and Sinhala, also with a two-line
  server message.

### Not fixed or not verified
- Needs a real device or backend: camera capture of the odometer photo, microphone and voice alerts, Screen Wake Lock,
  real GPS position updates, OpenStreetMap tiles over the network, video upload progress on a slow connection, PDF
  download of reports, Google sign-in (the mock has no `gis`), HTTPS-only browser features.
- The `GET /trips/{id}` location shape was read from the backend source (`trip_summary`), not from a contract.
- The landing cards for Tickets and Rentals still open the "not available yet" notice although both flows exist now;
  changing their target is a wording/route decision, left as is.
- The favicon link in `index.html` points to a file that does not exist; no approved square icon to point it at.
- Phone dashboards scroll the page (stacked tiles); desktop sizes keep the one-screen layout.

## Extra charge choices, nearby order, landing cards, favicon (contracts 03XP, 03WH)

- **Owner rate form (03XP):** each extra has three choices (Not offered, No extra charge, Charge) in `OwnerRates`. Rate fields show
  only for Charge. Extras by method: WAITING for all, EXTRA_KM for km-wise and day hire, EXTRA_HOURS and OVERNIGHT for day hire only.
  On save (and in the example preview) `withExtraPolicy` sends `extra_policy` with only the keys the method uses and "0" for the rates
  of an extra that is not charged; rules without `extra_policy` load as Charge. A 422 shows the server message through the shared
  field-error list. Rules live in `features/booking/extraPolicy.js` (unit tests in `tests/extraPolicy.test.js`).
- **Passenger (03XP):** `calculation.extra_policies` is shown as "Not available", "No extra charge" or the rate with its unit
  (`ExtraLines`): compact on the vehicle card, full under the quote total (`FlowEstimate`) and in the booking price table (`PriceTable`).
- **Ask the Owner (03SQ list, 03XP):** `quote_on_request` entries are listed after the priced ones under "Ask the Owner for a price".
  The card says "The Owner has not saved a price for this journey. Ask the Owner and they will send you a price." (the contract gives no
  reason, so none is shown). The button goes to the request review and sends `POST /bookings/private-hires` without a quote.
- **Nearby order (03WH):** server order kept; near entries first, then "Farther away" (near false); "about N km away" only when
  `distance_km` is not null; `location_source` is never shown. Pages never mix parts, so a heading sits at the top of a page. Same
  ordering in the Owner/Driver/Admin personal-hire list.
- **Admin report:** "Private hire (includes Event hire)".
- **Landing:** the Tickets and Rentals cards and the Tickets/Rentals search tabs open `/travel/book/tickets` and `/travel/book/rental`;
  a signed-out visitor goes to `/login` with `returnTo` and comes back to that page after signing in (only those two pages are accepted).
- **Favicon:** `public/favicon.svg`, `favicon-32.png`, `apple-touch-icon.png` are made from the navbar speedometer (dial and needle at
  rest, from the real brand images) on a white square; linked in `index.html`. The brand mark itself is unchanged.
- **Fit checked** (mocked API): Owner rate steps with 1, 3 and 4 extras at 1280x585, 1920x1080 and 390x844 (1280x585 day-hire rate
  step 1 px over, rounding); vehicle search with all near, mixed, all far and null distances at 1280x585, 1920x1080, 390x844. At
  1280x585 the vehicle list scrolls inside itself (8–38 px) when a heading and the extra lines are shown; the card never scrolls.
  On phones the card scrolls as before.
- **Left open:** the Owner landing "Rentals" card still shows the "not available yet" notice (not asked); the personal-hire list in
  Owner/Driver/Admin shows unpriced vehicles with its existing "Request a quote" text.

## Contract re-check, long-distance commission, account settings (03XP, 03WH, 03SQ, 03O, 03P, 03LC, 03ST)

- **Re-check against the backend source and contracts:**
  - 03XP: modes and keys match. The 422 for a key the method does not use comes back as field `rules.<index>` with the message
    `extra_policy.<KEY>: not used by the <METHOD> method.` (not `rules.0.extra_policy.<KEY>`); the form jumps to that rule and shows the message.
    The contract gives no unit wording, so the extra lines keep the wording from the earlier step.
  - 03WH: the server sets `near` false whenever `distance_km` is null, so those entries sit under "Farther away" with no distance (as built).
  - 03SQ: nothing beyond `POST /bookings/private-hires` (unchanged request body).
  - 03O: `GET /trips/{id}` `location` is null when tracking is off or the trip has ended. The map now drops the marker then (before it kept
    the last position). `status` COMPLETED/CANCELLED still stops polling; STALE shows "Last seen at …" from `updated_at`.
  - 03P: the latest `payment_api.py` / `payment_schemas.py` only add the multi-day commission; no existing payment field changed.
- **03LC (Admin, Payments, Long-distance):** a second box "Commission (%), 2 or more service days" (`multi_day_commission_percent`, optional)
  next to "Commission (%), 1 service day", shown only when `supports_multi_day_commission` is true. An empty box is not sent (clears it). The
  50,000 example is shown for both. 422 `PAYMENT_SETTINGS_INVALID` and `MULTI_DAY_COMMISSION_NOT_ALLOWED` show on the second box.
- **03ST (Settings, every role):** new tabs Password, Devices and Notifications beside Account security and Profile details
  (`features/auth/AccountSettings.jsx`): sessions list with sign out and "Sign out all other devices" (`{}`), change password (new tokens
  replace the stored ones; CURRENT_PASSWORD_WRONG on the current field, PASSWORD_UNCHANGED on the new one, 429 message, NO_PASSWORD_SET
  with a link to reset by email), notification switches only where `can_turn_off` (others "Always on"; maintenance hidden for Passengers).
  The database migration is backend-only.
- **Landing:** the Owner "Rentals" card opens `/owner/vehicles` (vehicle page, tab Rental rates); signed-out visitors return there after login.
- **Return after login:** email login returns to the clicked landing page. Google sign-in returns too when the account exists
  (checked with a simulated Google callback); a brand-new Google account goes to /google-complete and the return target is not kept.
- **Fit:** the Admin payment form and the three settings tabs measure 449/449 at 1280x585 and fit at 1920x1080; on 390x844 the form card scrolls inside.

## Two-step verification and closing the account (contract 03SV)

- **Login:** a login or Google answer with `status: two_factor_required` and a `challenge` opens an "Enter your code" screen in `AuthPage`
  (`TwoFactorStep`). `POST /auth/2fa {challenge, code}` answers like login; then the normal role destination (03W) or the landing-card
  return page. Wrong code (`TWO_FACTOR_CODE_WRONG`) and rate limit (429, with Retry-After) show friendly text and keep the screen; an expired
  step (`TWO_FACTOR_CHALLENGE_EXPIRED`) goes back to the sign-in form with the message. Email and Google follow the same branch (tested with a
  simulated Google callback). Rules and request bodies are in `features/auth/loginFlow.js` (`tests/loginFlow.test.js`).
- **Return page through /google-complete:** the return target is passed in the navigation state to /google-complete and used after the
  profile is completed (small change in `AuthPage.jsx` and `AuthFlows.jsx`). Tested: Rentals card, new Google account, ends on /travel/book/rental.
- **Settings, Two-step tab:** `GET /users/me/2fa`, `POST .../setup {}` (secret as text and QR made in the UI), `POST .../enable {code}`
  (10 backup codes shown once with Copy and Download; Done only after "I have saved my backup codes"; kept only in component state, never in
  storage or logs), `POST .../disable` and `POST .../backup-codes` with `password` (only when the account has one, from
  `GET /users/me/auth-methods`) and `code`.
- **Settings, Close account tab:** `GET /users/me/account-closure`; blockers listed with the UI's own text per code and the count; both buttons
  off while any exist; confirm step asks for the password (if the account has one) and the code (only when two-step is on); then
  `POST /users/me/deactivate` or `/delete-request` `{confirm:true, password?, code?}`. `409 ACCOUNT_HAS_OPEN_ITEMS` reloads the blockers.
  Success clears the session and loads the landing page fresh.
- **Fit:** checked with the mocked API at 1280x585, 1920x1080 and 390x844 in English, Tamil and Sinhala (code screen, two-step on/off, setup,
  backup codes, off form, blockers, confirm form): no page scroll, no cut labels; on 390x844 the setup card scrolls inside.
- **Unclear in the contract:** no page is given for any blocker, so none is linked (`BLOCKERS[code].path` is where one would go);
  the contract does not say how the client learns a delete request was cancelled by signing in (the "Welcome back" message is not shown);
  the login and disable code accepts an app code or a backup code (letters and a hyphen), so those inputs are text fields with
  `autocomplete="one-time-code"`; only the setup confirmation (app code only) is numeric.
