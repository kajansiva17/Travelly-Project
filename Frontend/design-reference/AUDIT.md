# Route audit (FORM & PAGE RULE, 1280x585)

Method: Playwright with mocked `/api/v1/**`, busy + empty states, tabs clicked. 'Not matching reference' is a structural proxy (shared FlowShell/dash layout vs legacy layout class, dark panels). CRASH rows are likely mock gaps. Source data: audit_<ROLE>.tsv in D:	mp-shots.

Admin: every route also fails on sidebar menu scroll (372/304px).

| Role | Route | Result | Reasons |
|---|---|---|---|
| Passenger | `/dashboard` | PASS |  |
| Passenger | `/account` | PASS |  |
| Passenger | `/bookings` | PASS |  |
| Passenger | `/bookings/b1` | PASS |  |
| Passenger | `/trips/t1/finance` | PASS |  |
| Passenger | `/passenger/bookings` | PASS |  |
| Passenger | `/passenger/saved-places` | PASS |  |
| Passenger | `/passenger/payments` | PASS |  |
| Passenger | `/passenger/support` | PASS |  |
| Passenger | `/passenger/settings` | PASS |  |
| Passenger | `/passenger/trips/t1/finance` | FAIL | legacy layout (role-dashboard) [busy] ; legacy layout (role-dashboard) [empty] ; page scroll 212px [busy] |
| Passenger | `/travel/book/service` | PASS |  |
| Passenger | `/travel/book/event` | FAIL | card scroll/clip: flow-card.ui-card 582/465 [busy] ; card scroll/clip: flow-card.ui-card 582/465 [empty] ; overlap INPUT�Back [busy] ; overlap INPUT�Back [empty] |
| Passenger | `/travel/book/tickets` | FAIL | legacy layout (passenger-booking-flow) [busy] ; legacy layout (passenger-booking-flow) [empty] |
| Passenger | `/travel/book/rental` | FAIL | legacy layout (passenger-booking-flow) [busy] ; legacy layout (passenger-booking-flow) [empty] |
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
| Owner | `/owner/event-packages` | PASS |  |
| Owner | `/owner/event-operations` | PASS |  |
| Owner | `/owner/ticket-departures` | FAIL | card scroll/clip: travelly-glass-panel 1640/430 [busy] ; legacy layout (role-dashboard) [busy] ; legacy layout (role-dashboard) [empty] ; page scroll 20px [busy] ; page scroll 20px [empty] |
| Owner | `/owner/vehicles` | PASS |  |
| Owner | `/owner/vehicle-setup` | PASS |  |
| Owner | `/owner/vehicles/v1` | PASS |  |
| Owner | `/owner/vehicles/v1/calendar` | PASS |  |
| Owner | `/owner/vehicles/v1/maintenance` | PASS |  |
| Owner | `/owner/bookings` | PASS |  |
| Owner | `/owner/assignments` | PASS |  |
| Owner | `/owner/operations` | FAIL | legacy layout (role-dashboard) [busy] ; legacy layout (role-dashboard) [empty] ; page scroll 3585px [busy] ; page scroll 494px [empty] |
| Owner | `/owner/earnings` | PASS |  |
| Owner | `/owner/rentals` | PASS |  |
| Owner | `/owner/settings` | PASS |  |
| Owner | `/owner/support` | PASS |  |
| Owner | `/account?workspace=owner` | PASS |  |
| Owner | `/bookings/b1?workspace=owner` | PASS |  |
| Owner | `/trips/t1/finance?workspace=owner` | PASS |  |
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
| Driver | `/driver/ticket-boarding` | FAIL | legacy layout (role-dashboard) [busy] ; legacy layout (role-dashboard) [empty] ; page scroll 20px [busy] ; page scroll 20px [empty] |
| Driver | `/driver/rentals` | PASS |  |
| Driver | `/driver/trip-history` | PASS |  |
| Driver | `/driver/settings` | PASS |  |
| Driver | `/driver/availability` | PASS |  |
| Driver | `/driver/earnings` | PASS |  |
| Driver | `/driver/road-alerts` | PASS |  |
| Driver | `/driver/support` | PASS |  |
| Driver | `/account?workspace=driver` | PASS |  |
| Driver | `/bookings/b1?workspace=driver` | PASS |  |
| Driver | `/trips/t1/finance?workspace=driver` | PASS |  |
| Driver | `/trips/t1/operation?workspace=driver` | PASS |  |
| Admin | `/admin/dashboard` | PASS |  |
| Admin | `/admin/personal/hire` | PASS |  |
| Admin | `/admin/personal/owners/OWN1` | FAIL | card scroll/clip: app-sidebar-menu 372/304 [busy/tab2] ; card scroll/clip: app-sidebar-menu 372/304 [busy] ; card scroll/clip: app-sidebar-menu 372/304 [empty/tab2] ; card scroll/clip: app-sidebar-menu 372/304 [empty] |
| Admin | `/admin/personal/bookings` | FAIL | card scroll/clip: app-sidebar-menu 372/304 [busy/tab2] ; card scroll/clip: app-sidebar-menu 372/304 [busy] ; card scroll/clip: app-sidebar-menu 372/304 [empty/tab2] ; card scroll/clip: app-sidebar-menu 372/304 [empty] |
| Admin | `/admin/personal/bookings/b1` | FAIL | card scroll/clip: app-sidebar-menu 372/304 [busy] ; card scroll/clip: app-sidebar-menu 372/304 [empty] |
| Admin | `/admin/personal/vehicles/v1` | PASS |  |
| Admin | `/admin/applications` | PASS |  |
| Admin | `/admin/applications/r1` | PASS |  |
| Admin | `/admin/vehicles` | FAIL | card scroll/clip: app-sidebar-menu 372/304 [busy] ; card scroll/clip: app-sidebar-menu 372/304 [empty] |
| Admin | `/admin/vehicles/v1` | FAIL | card scroll/clip: app-sidebar-menu 372/304 [busy/tab2] ; card scroll/clip: app-sidebar-menu 372/304 [busy/tab3] ; card scroll/clip: app-sidebar-menu 372/304 [busy/tab4] ; card scroll/clip: app-sidebar-menu 372/304 [busy] ; card scroll/clip: app-sidebar-menu 37 |
| Admin | `/admin/vehicles/v1/calendar` | FAIL | card scroll/clip: app-sidebar-menu 372/304 [busy] ; card scroll/clip: app-sidebar-menu 372/304 [empty] |
| Admin | `/admin/documents` | PASS |  |
| Admin | `/admin/services-routes` | PASS |  |
| Admin | `/admin/services-routes/tickets` | PASS |  |
| Admin | `/admin/bookings` | PASS |  |
| Admin | `/admin/oversight` | PASS |  |
| Admin | `/admin/rentals` | FAIL | card scroll/clip: app-sidebar-menu 372/304 [busy/tab2] ; card scroll/clip: app-sidebar-menu 372/304 [busy/tab3] ; card scroll/clip: app-sidebar-menu 372/304 [busy] ; card scroll/clip: app-sidebar-menu 372/304 [empty/tab2] ; card scroll/clip: app-sidebar-menu 3 |
| Admin | `/admin/payments` | PASS |  |
| Admin | `/admin/social-reviews` | PASS |  |
| Admin | `/admin/road-alerts` | PASS |  |
| Admin | `/admin/reports` | PASS |  |
| Admin | `/admin/manual-fulfilment` | PASS |  |
| Admin | `/admin/settings` | PASS |  |
| Admin | `/account?workspace=admin` | PASS |  |
| Admin | `/bookings/b1?workspace=admin` | FAIL | card scroll/clip: app-sidebar-menu 372/304 [busy/tab2] ; card scroll/clip: app-sidebar-menu 372/304 [busy/tab3] ; card scroll/clip: app-sidebar-menu 372/304 [busy/tab4] ; card scroll/clip: app-sidebar-menu 372/304 [busy/tab5] ; card scroll/clip: app-sidebar-me |


## BATCH A re-measure (1280x585 and 1920x1080, busy + empty + all tabs)
PASS (no page scroll, no card scroll/clip, no overlap, no legacy layout, admin sidebar fits): hire x4, /account x4 roles (3 tabs), vehicle detail x4, owner/personal/bookings, driver/personal/bookings/b1, admin/settings, owner/rates, owner/service-readiness, passenger/bookings. Admin sidebar scroll: gone on all admin routes at 1280x585.

## ADMIN batch re-measure (1280x585 and 1920x1080, busy + empty, tabs/details/confirmation opened)
PASS (no page scroll, no card scroll/clip, no overlap, no legacy layout, no dark panel, actions in view, sidebar fits): /admin/dashboard (reference grid: 4 stats, 6 tiles + Travelly AI card, no tabs), /admin/applications (+ /:id with Application / Evidence tabs and the confirmation step), /admin/documents, /admin/bookings, /admin/payments, /admin/social-reviews, /admin/road-alerts, /admin/reports, /admin/oversight (3 tabs), /admin/manual-fulfilment (Events / Record an event), /admin/services-routes (list + details), /admin/services-routes/tickets, /admin/settings, /account?workspace=admin.
Shared layout: features/admin/AdminList.jsx (filter row, compact rows, paging, Details view). Crash fixes: /admin/applications/:id and /admin/services-routes now guard missing application / pricing_scope / status / ready_vehicles.
Not in this batch (still listed above as FAIL by the old sidebar finding only, which is fixed): /admin/personal/*, /admin/vehicles*, /admin/rentals, /bookings/:id?workspace=admin.

## Passenger dashboard batch (1280x585 and 1920x1080, busy + empty)
PASS: /dashboard (shared dash grid: 4 stat cards, 6 tiles + Travelly AI card, no page or tile scroll; legacy passenger-dashboard layout, DashboardSearchPanel and passengerDashboard.css deleted), /trips/:id/request-status and /trips/:id/confirmed (BookingState guards missing status/itinerary/proposal; pickup QR + PIN beside each other so quote + code still fit 1280x585).

