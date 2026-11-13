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
