# Travelly UI Reference Map

## Reference usage rules

- `boards/` contains the original multi-panel workflow boards.
- `screens/` contains one cropped image per real application screen.
- Each cropped image represents one route or one workflow state; it is not a complete application page collection.
- Recreate references with functional React components and CSS. Never use a reference image as a page background.
- Preserve role sidebars:
  - Passenger sidebar: Passenger-only menu.
  - Driver sidebar: Driver-only menu.
  - Owner sidebar: compact Owner sidebar from `owner-operations.png`.
  - Admin sidebar: Admin-only menu.
- `Operations` is Owner-only.
- Vehicle/departure price must not be shown before the Passenger selects a matching vehicle/departure.
- Buttons must validate and save the current form state before opening the next screen.
- Back actions must preserve entered booking information.

---

## Passenger: private-hire booking flow

| Reference image | Route / state | Previous → Next | Purpose and main action |
|---|---|---|---|
| `passenger-choose-service.png` | `/travel/book/service` | Travel & Booking → trip details | Passenger selects Airport, Local, Event, Long Distance, Ticket, or Vehicle Rent. |
| `passenger-airport-details.png` | `/travel/book/details/airport` | Service → requirements | Pickup/drop-off, one-way/return, flight number, date and time. |
| `passenger-local-hire-details.png` | `/travel/book/details/local` | Service → requirements | Local one-way/return route, dates, times, and optional stops. |
| `passenger-event-hire-details.png` | `/travel/book/details/event` | Service → requirements | Event type, venue, pickup points, dates, times, vehicles, and travellers. |
| `passenger-long-distance-one-day.png` | `/travel/book/details/long-distance/one-day` | Service → requirements | One-day route, date, pickup, finish time, planned stops, and travellers. |
| `passenger-long-distance-multi-day.png` | `/travel/book/details/long-distance/multi-day` | Service → requirements | Multi-day dates, itinerary, planned stops, travellers, and overnight details. |
| `passenger-vehicle-needs.png` | `/travel/book/requirements` | Details → matching vehicles | Passenger/luggage count, AC, vehicle types, accessibility, and optional facilities. |
| `passenger-matching-vehicles.png` | `/travel/book/vehicles` | Requirements → selected vehicle | Show approved, available matching vehicles only. No price on this screen. |
| `passenger-selected-vehicle-price.png` | `/travel/book/vehicles/:vehicleId/review` | Matching vehicles → review request | Show selected vehicle, owner rate, inclusions, waiting, extra-km and stop rules. |
| `passenger-review-send-request.png` | `/travel/book/review` | Vehicle review → request status | Passenger reviews route, vehicle, frozen estimate/rules and sends request. |
| `passenger-request-status.png` | `/trips/:tripId/request-status` | Request sent → confirmed trip | Show Owner review, timeline, cancellation action, and booking status. |
| `passenger-ride-confirmed-qr-pin.png` | `/trips/:tripId/confirmed` | Owner accepts → live trip | Show assigned Driver, vehicle, pickup details, QR code, PIN, and track-trip action. |

### Passenger: ticket and rental

| Reference image | Route / state | Previous → Next | Purpose and main action |
|---|---|---|---|
| `passenger-ticket-search.png` | `/tickets/search` | Travel & Booking → seat selection | Search route/date/travellers and choose a Bus or Van departure. Do not show seat price before departure selection. |
| `passenger-ticket-seat-selection.png` | `/tickets/departures/:departureId/seats` | Ticket search → ticket payment | Select seats, hold seats temporarily, then show fare summary and continue to payment. |
| `passenger-rental-search.png` | `/rentals/search` | Travel & Booking → rental review | Select dates, locations, driver arrangement, vehicle type, capacity, luggage, and AC needs. No price before vehicle selection. |
| `passenger-rental-selected-vehicle.png` | `/rentals/vehicles/:vehicleId/review` | Rental search → rental request | Show selected rental vehicle, package, mileage, late/extra-day rules, deposit, documents, and request action. |

### Passenger: completed trip, payment, and rating

| Reference image | Route / state | Previous → Next | Purpose and main action |
|---|---|---|---|
| `passenger-final-fare.png` | `/trips/:tripId/payment` | Trip completed → payment selection | Show itemised final fare and choose Online or Cash payment. |
| `passenger-cash-confirmation.png` | `/trips/:tripId/payment/cash` | Payment selection → driver receipt | Passenger confirms exact cash amount paid. |
| `passenger-payment-success.png` | `/trips/:tripId/payment/success` | Payment confirmed → rating | Show receipt, payment breakdown, and rate-trip action. |
| `passenger-rate-trip.png` | `/trips/:tripId/rate` | Payment success → My Trips | Passenger submits vehicle/driver rating and optional feedback. |

---

## Owner: vehicle setup and service rates

| Reference image | Route / state | Previous → Next | Purpose and main action |
|---|---|---|---|
| `owner-vehicle-basics.png` | `/owner/vehicles/new/basics` | Vehicles → features | Vehicle type, plate, make/model, passenger capacity, luggage capacity. |
| `owner-vehicle-features.png` | `/owner/vehicles/new/features` | Basics → documents | AC, luggage, seatbelts, USB, accessibility, and vehicle photos. |
| `owner-vehicle-documents.png` | `/owner/vehicles/new/documents` | Features → services | Registration, insurance, roadworthiness, and service-area availability. |
| `owner-vehicle-services.png` | `/owner/vehicles/:vehicleId/services` | Documents → rate setup | Enable Airport, Local, Event, Long Distance, Ticket, and Rental services. |
| `owner-event-pricing.png` | `/owner/vehicles/:vehicleId/rates/event` | Services → review | Event package, included hours/km, overtime, extra km, stop, waiting, optional venue charge. |
| `owner-airport-local-pricing.png` | `/owner/vehicles/:vehicleId/rates/airport-local` | Services → review | One-way/return rate, included km, waiting, extra km, extra-stop charges. |
| `owner-long-distance-pricing.png` | `/owner/vehicles/:vehicleId/rates/long-distance` | Services → review | One-day/multi-day price, hours/km, overtime, extra day, extra km, overnight charge. |
| `owner-rental-pricing-review.png` | `/owner/vehicles/:vehicleId/rates/rental` | Services → submit | Daily rental rate, included mileage, extra km, late return, extra day, deposit, payment methods, review/submit. |

---

## Owner: booking, operations, fleet, and maintenance

| Reference image | Route / state | Previous → Next | Purpose and main action |
|---|---|---|---|
| `owner-booking-requests.png` | `/owner/bookings/requests` | Bookings → assignment | Review Passenger request, vehicle match, requirements, and estimate. |
| `owner-assign-driver.png` | `/owner/bookings/:bookingId/assign` | Request → confirmed booking | Assign verified Driver or choose “I’ll drive myself”; accept or decline request. |
| `owner-overview.png` | `/owner/overview` | Owner login → dashboard areas | Fleet totals, current bookings, active trip controls, fleet status, alerts. |
| `owner-operations.png` | `/owner/operations` | Owner sidebar Operations → operation area | My Driving, Driver Assignments, Live Fleet Trips, Vehicle Expenses. |
| `owner-driving-task.png` | `/owner/operations/my-driving/:tripId` | My Driving → trip operation | Owner-driver verifies Passenger, captures odometer, starts Passenger trip. Owner sidebar stays visible. |
| `owner-travel-booking.png` | `/owner/travel-booking` | Travel & Booking → service selection | Owner uses Passenger booking functions while retaining the Owner sidebar. |
| `owner-fuel-expense-review.png` | `/owner/operations/expenses/:expenseId` | Vehicle Expenses → approval | Review Driver fuel/expense record; approve, reject, or query. |
| `owner-trip-profitability.png` | `/owner/finance/trips/:tripId` | Finance → settlement review | Show fare, platform fee, approved expenses, contribution, and settlement status. |
| `owner-return-garage-duty-log.png` | `/owner/vehicles/:vehicleId/duty-log/:tripId` | Operations → mileage log | Show departure, pickup, drop-off, return readings. Garage mileage never changes Passenger fare. |
| `owner-vehicle-mileage-log.png` | `/owner/vehicles/:vehicleId/mileage` | Vehicles → maintenance | View verified odometer timeline and manual/GPS evidence status. |
| `owner-maintenance-dashboard.png` | `/owner/vehicles/:vehicleId/maintenance` | Mileage → add service | Show oil/tyre maintenance targets and due kilometres/dates. |
| `owner-add-maintenance-record.png` | `/owner/vehicles/:vehicleId/maintenance/new` | Maintenance → saved record | Add service type, odometer, due km/date, cost, workshop receipt. |
| `owner-completed-settlement.png` | `/owner/bookings/:bookingId/settlement` | Completed booking → finance | Show completed booking, fare, cash status, settlement and Owner review action. |

---

## Driver: trip operations and expenses

| Reference image | Route / state | Previous → Next | Purpose and main action |
|---|---|---|---|
| `driver-assigned-trip.png` | `/driver/operate-trip/:tripId` | My Assignments → pickup | Show assigned vehicle, Passenger, route, customer needs, and navigate-to-pickup action. |
| `driver-verify-passenger.png` | `/driver/operate-trip/:tripId/pickup` | Assigned trip → live trip | Scan Passenger QR or enter PIN, verify identity, record pickup odometer, start trip. |
| `driver-waiting-timer.png` | `/driver/operate-trip/:tripId/waiting` | Live trip → resume trip | Show waiting timer, free allowance, chargeable time, rate, estimate, and resume action. |
| `driver-extra-stop-request.png` | `/driver/operate-trip/:tripId/extra-stop` | Live trip → Passenger decision | Propose stop, show proposed calculation, wait for Passenger approval/rejection. |
| `driver-add-fuel-expense.png` | `/driver/operate-trip/:tripId/expenses/new` | Operate Trip → saved expense | Fuel type, litres, rate, amount, odometer, station, payer, receipt evidence. |
| `driver-fuel-expense-saved.png` | `/driver/operate-trip/:tripId/expenses/:expenseId` | Fuel entry → Owner review | Show submitted expense and reimbursement/Owner review status. |
| `driver-cash-received.png` | `/driver/trips/:tripId/cash-receipt` | Passenger cash confirmation → Owner settlement | Driver confirms exact cash received, then later records Owner handover. |

---

## Admin: verification, oversight, and audit

| Reference image | Route / state | Previous → Next | Purpose and main action |
|---|---|---|---|
| `admin-vehicle-verification-queue.png` | `/admin/vehicles/verifications` | Vehicles → vehicle review | Show pending vehicle submissions and open selected review. |
| `admin-verify-vehicle.png` | `/admin/vehicles/:vehicleId/review` | Verification queue → searchable vehicle | Review documents, images, capacity, features, rates, type mapping; approve or request changes. |
| `admin-booking-details.png` | `/admin/bookings/:bookingId` | Bookings → audit/detail view | Show timeline, Passenger, Owner, Driver, approved vehicle, frozen rate and booking details. |
| `admin-cash-mismatch-review.png` | `/admin/payments/:paymentId/review` | Payments → dispute/audit action | Review Passenger/Driver cash mismatch, evidence metadata, and request clarification. |

---

## Shared workflow business rules

1. Price appears only after a Passenger chooses a specific matching vehicle or departure.
2. Passenger distance is pickup odometer minus drop-off odometer only.
3. Garage/departure/return mileage belongs to fleet operations and maintenance, not Passenger fare.
4. Fuel and vehicle expenses are never added automatically to Passenger fare.
5. Extra stops require Passenger approval before a charge can be finalised.
6. Cash requires Passenger confirmation, Driver confirmation, Driver handover, and Owner settlement receipt.
7. Booking rate rules are frozen once the Passenger accepts the selected vehicle/departure.
8. `Operations` appears only on the Owner sidebar.
9. If a backend feature is unavailable, the UI must show an honest unavailable state; never show fake success data.