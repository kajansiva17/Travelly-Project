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

