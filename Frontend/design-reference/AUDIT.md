# Route audit (FORM & PAGE RULE, 1280x585)

Method: Playwright with mocked `/api/v1/**`, busy + empty states, tabs clicked. 'Not matching reference' is a structural proxy (shared FlowShell/dash layout vs legacy layout class, dark panels). CRASH rows are likely mock gaps. Source data: audit_<ROLE>.tsv in D:	mp-shots.

Admin: every route also fails on sidebar menu scroll (372/304px).

| Role | Route | Result | Reasons |
|---|---|---|---|
| Passenger | `/dashboard` | FAIL | legacy layout (passenger-dashboard) [busy] ; legacy layout (passenger-dashboard) [empty] ; page scroll 697px [busy] ; page scroll 697px [empty] |
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
| Passenger | `/trips/t1/request-status` | FAIL | CRASH Cannot read properties of undefined (reading 'replaceAll') @     at BookingState ; Cannot read properties of undefined (reading 'replaceAll') @     at BookingState (http://127.0.0.1:5199/src/features/pas [empty] ; no app shell/redirect -> /trips/t1/reque |
| Passenger | `/trips/t1/confirmed` | FAIL | CRASH Cannot read properties of undefined (reading 'replaceAll') @     at BookingState ; Cannot read properties of undefined (reading 'replaceAll') @     at BookingState (http://127.0.0.1:5199/src/features/pas [busy] ; Cannot read properties of undefined (read |
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
| Admin | `/admin/dashboard` | FAIL | card scroll/clip: app-sidebar-menu 372/304 [busy] ; card scroll/clip: app-sidebar-menu 372/304 [empty] ; legacy layout (role-dashboard) [busy] ; legacy layout (role-dashboard) [empty] ; page scroll 597px [busy] ; page scroll 597px [empty] |
| Admin | `/admin/personal/hire` | PASS |  |
| Admin | `/admin/personal/owners/OWN1` | FAIL | card scroll/clip: app-sidebar-menu 372/304 [busy/tab2] ; card scroll/clip: app-sidebar-menu 372/304 [busy] ; card scroll/clip: app-sidebar-menu 372/304 [empty/tab2] ; card scroll/clip: app-sidebar-menu 372/304 [empty] |
| Admin | `/admin/personal/bookings` | FAIL | card scroll/clip: app-sidebar-menu 372/304 [busy/tab2] ; card scroll/clip: app-sidebar-menu 372/304 [busy] ; card scroll/clip: app-sidebar-menu 372/304 [empty/tab2] ; card scroll/clip: app-sidebar-menu 372/304 [empty] |
| Admin | `/admin/personal/bookings/b1` | FAIL | card scroll/clip: app-sidebar-menu 372/304 [busy] ; card scroll/clip: app-sidebar-menu 372/304 [empty] |
| Admin | `/admin/personal/vehicles/v1` | PASS |  |
| Admin | `/admin/applications` | FAIL | card scroll/clip: app-sidebar-menu 372/304 [busy] ; card scroll/clip: app-sidebar-menu 372/304 [empty] ; legacy layout (dashboard-main) [empty] ; legacy layout (role-dashboard) [busy] ; old theme dark: site-footer [empty] ; page scroll 137px [empty] ; page scr |
| Admin | `/admin/applications/r1` | FAIL | CRASH Cannot read properties of undefined (reading 'role_code') @     at AdminApplicat ; Cannot read properties of undefined (reading 'role_code') @     at AdminApplications (http://127.0.0.1:5199/src/features [busy] ; card scroll/clip: app-sidebar-menu 372/30 |
| Admin | `/admin/vehicles` | FAIL | card scroll/clip: app-sidebar-menu 372/304 [busy] ; card scroll/clip: app-sidebar-menu 372/304 [empty] |
| Admin | `/admin/vehicles/v1` | FAIL | card scroll/clip: app-sidebar-menu 372/304 [busy/tab2] ; card scroll/clip: app-sidebar-menu 372/304 [busy/tab3] ; card scroll/clip: app-sidebar-menu 372/304 [busy/tab4] ; card scroll/clip: app-sidebar-menu 372/304 [busy] ; card scroll/clip: app-sidebar-menu 37 |
| Admin | `/admin/vehicles/v1/calendar` | FAIL | card scroll/clip: app-sidebar-menu 372/304 [busy] ; card scroll/clip: app-sidebar-menu 372/304 [empty] |
| Admin | `/admin/documents` | FAIL | card scroll/clip: app-sidebar-menu 372/304 [busy] ; card scroll/clip: app-sidebar-menu 372/304 [empty] ; legacy layout (role-dashboard) [busy] ; legacy layout (role-dashboard) [empty] ; page scroll 495px [busy] |
| Admin | `/admin/services-routes` | FAIL | CRASH Cannot read properties of undefined (reading 'replaceAll') @     at http://127.0 ; Cannot read properties of undefined (reading 'replaceAll') @     at http://127.0.0.1:5199/src/features/admin/AdminServic [busy] ; card scroll/clip: app-sidebar-menu 372/30 |
| Admin | `/admin/services-routes/tickets` | FAIL |     at http://127.0.0.1:5199/src/feat [busy] ; CRASH Cannot convert undefined or null to object @     at Object.entries (<anonymous>) ; Cannot convert undefined or null to object @     at Object.entries (<anonymous>) [busy] ; card scroll/clip: app-sidebar-menu |
| Admin | `/admin/bookings` | FAIL | card scroll/clip: app-sidebar-menu 372/304 [busy] ; card scroll/clip: app-sidebar-menu 372/304 [empty] ; legacy layout (role-dashboard) [busy] ; legacy layout (role-dashboard) [empty] ; page scroll 445px [busy] |
| Admin | `/admin/oversight` | FAIL | card scroll/clip: app-sidebar-menu 372/304 [busy] ; card scroll/clip: app-sidebar-menu 372/304 [empty] ; legacy layout (role-dashboard) [busy] ; legacy layout (role-dashboard) [empty] ; page scroll 2323px [busy] ; page scroll 402px [empty] |
| Admin | `/admin/rentals` | FAIL | card scroll/clip: app-sidebar-menu 372/304 [busy/tab2] ; card scroll/clip: app-sidebar-menu 372/304 [busy/tab3] ; card scroll/clip: app-sidebar-menu 372/304 [busy] ; card scroll/clip: app-sidebar-menu 372/304 [empty/tab2] ; card scroll/clip: app-sidebar-menu 3 |
| Admin | `/admin/payments` | FAIL | card scroll/clip: app-sidebar-menu 372/304 [busy] ; card scroll/clip: app-sidebar-menu 372/304 [empty] ; legacy layout (role-dashboard) [busy] ; legacy layout (role-dashboard) [empty] ; page scroll 443px [busy] |
| Admin | `/admin/social-reviews` | FAIL | card scroll/clip: app-sidebar-menu 372/304 [busy] ; card scroll/clip: app-sidebar-menu 372/304 [empty] ; legacy layout (role-dashboard) [busy] ; legacy layout (role-dashboard) [empty] ; page scroll 443px [busy] |
| Admin | `/admin/road-alerts` | FAIL | card scroll/clip: app-sidebar-menu 372/304 [busy] ; card scroll/clip: app-sidebar-menu 372/304 [empty] ; legacy layout (role-dashboard) [busy] ; legacy layout (role-dashboard) [empty] ; page scroll 445px [busy] |
| Admin | `/admin/reports` | FAIL | card scroll/clip: app-sidebar-menu 372/304 [busy] ; card scroll/clip: app-sidebar-menu 372/304 [empty] ; legacy layout (role-dashboard) [busy] ; legacy layout (role-dashboard) [empty] ; page scroll 172px [busy] |
| Admin | `/admin/manual-fulfilment` | FAIL | card scroll/clip: app-sidebar-menu 372/304 [busy] ; legacy layout (role-dashboard) [busy] ; legacy layout (workspace-state) [empty] ; page scroll 770px [busy] |
| Admin | `/admin/settings` | PASS |  |
| Admin | `/account?workspace=admin` | PASS |  |
| Admin | `/bookings/b1?workspace=admin` | FAIL | card scroll/clip: app-sidebar-menu 372/304 [busy/tab2] ; card scroll/clip: app-sidebar-menu 372/304 [busy/tab3] ; card scroll/clip: app-sidebar-menu 372/304 [busy/tab4] ; card scroll/clip: app-sidebar-menu 372/304 [busy/tab5] ; card scroll/clip: app-sidebar-me |


## BATCH A re-measure (1280x585 and 1920x1080, busy + empty + all tabs)
PASS (no page scroll, no card scroll/clip, no overlap, no legacy layout, admin sidebar fits): hire x4, /account x4 roles (3 tabs), vehicle detail x4, owner/personal/bookings, driver/personal/bookings/b1, admin/settings, owner/rates, owner/service-readiness, passenger/bookings. Admin sidebar scroll: gone on all admin routes at 1280x585.
