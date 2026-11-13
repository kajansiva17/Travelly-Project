# Travelly — Self-drive rental (14 Nov 2026)

Status: built on `claude-work`. **Owner decisions** (the PRD names Rental but gives no price rule). The renter drives the
vehicle; no Driver is assigned. Base `/api/v1`. Booking type `RENTAL`. Service type `SELF_DRIVE_RENTAL` (category
RENTAL) is created automatically the first time an Owner saves rental rates; Admin sets its commission with the existing
`PATCH /admin/service-types/{id}/payment-settings` and can see it in `GET /admin/payment-settings`.

## Price (worked out when the vehicle comes back)
```
total = day_rate x booked days
      + max(0, km driven - free_km_per_day x booked days) x extra_km_rate      (free km are pooled over all days)
      + the renter's chosen extras (price x days when per = DAY, price once when per = ONCE)
      + late hours x late_hour_rate    (late = time after booked days x 24 h + 1 hour grace, each started hour counts)
```
- km driven = end odometer - start odometer. Both are photographed by the **Owner** (03O) and typed.
- Returning early is **not** refunded (the booked days are charged). The Owner can choose to be kind outside the app.
- Deposit, fuel and damage are settled between Owner and renter. Travelly does not hold the deposit. The Owner writes the
  rules in `notes`, which the renter sees before asking.
- The renter's driving licence number is given when asking; the Owner checks the licence at handover (`licence_checked`).

## Owner
`PUT /vehicles/{vehicle_id}/rental`
```json
{"expected_version": 0, "enabled": true, "day_rate": "8000", "free_km_per_day": "100", "extra_km_rate": "40",
 "late_hour_rate": "500", "max_days": 7, "notes": "Rs 20000 deposit in cash. Same fuel level.", "cash_accepted": true,
 "extras": [{"id": "<uuid you make>", "name": "Child seat", "price": "300", "per": "DAY"}]}
```
`extras` (0 - 10) are optional paid add-ons: `per` is `DAY` or `ONCE`. `GET /vehicles/{vehicle_id}/rental` returns the same fields plus `version`. Money fields are strings with up to 2
decimals. `max_days` 1 - 30. `cash_accepted` is optional (also available on the existing payment-options endpoint).

## Passenger
- `POST /rentals/search` `{"start_at": "...Z", "days": 2}` (no sign-in). Each item is the usual vehicle card plus
  `rental` = rates + `base_price`, `free_km_total`, `late_grace_hours`, `notes`. Only vehicles free for those dates.
- `POST /rentals` `{"vehicle_id", "start_at", "days", "licence_number", "extras": [extra ids]?, "idempotency_key"}` -> booking `REQUESTED`
  (`booking_type` is not in the summary; use `price.estimate` / `itinerary.rental`). `409 VEHICLE_SCHEDULE_CONFLICT` if taken.
- `POST /rentals/{id}/cancel` `{"expected_version", "reason"}` — Passenger or Owner, while `REQUESTED` or `CONFIRMED`.
- `POST /rentals/{id}/confirm` `{"stage": "HANDOVER" | "RETURN"}` — the renter confirms what the Owner recorded. It is a record
  (`itinerary.rental.handover.passenger_confirmed_at`), not a gate.

## Owner steps
| Call | Body | Result |
|---|---|---|
| `POST /rentals/{id}/accept` | `{expected_version}` | `CONFIRMED`; vehicle reserved; a driverless trip is made with the Owner as operator |
| `POST /rentals/{id}/decline` | `{expected_version, reason}` | `REJECTED` |
| `POST /rentals/{id}/handover` | `{expected_version, start_odometer_km, licence_checked: true, note?}` | `IN_PROGRESS`; allowed from 3 hours before the start |
| `POST /rentals/{id}/return` | `{expected_version, end_odometer_km, note?}` | `COMPLETED`; `total_amount` set; `price.final` = the bill |

**Odometer photos use the existing 03O endpoints on the rental trip** (`itinerary` has no trip id; read it from
`GET /bookings/{id}` -> `trip.id`): `POST /trips/{trip_id}/odometer-session`, `POST /trips/{trip_id}/odometer-photo`
(stage `START` before the handover, `END` before the return), `GET /trips/{trip_id}/odometer-proof`. The Owner is the trip
operator, so only the Owner takes the photos. The renter and Owner can both see them for 7 days. When
`ODOMETER_PHOTO_REQUIRED=true`, handover and return need a fresh matching photo (`409 ODOMETER_PROOF_REQUIRED`).

`price.final` = `{currency, breakdown[{code: DAYS|EXTRA_KM|LATE|EXTRA_1.., label, quantity, rate, amount}], total, distance_km, free_km, late_hours}`.

## Payment
After `COMPLETED`, exactly like private hire: `GET /bookings/{id}/payment-summary`, `POST /bookings/{id}/payment-intents`
(online) or cash receipts (the Owner collects; confirmed by both). Commission and the 14 / 18 day cash rule (03CM) apply.
A blocked Owner's vehicles are not shown and cannot be rented (`VEHICLE_NOT_AVAILABLE`).

## Booking summary fields for the screens
`price.estimate` (before; `extras_price` is included in `base_price`), `price.chosen_extras`, and `price.final` (after), `price.terms` (the rates the Owner had when it was requested),
`itinerary.rental = {days, start_at, licence_number, handover?{at,start_odometer_km,note,passenger_confirmed_at}, return?{at,end_odometer_km,note,passenger_confirmed_at}}`.
Rates saved later never change an accepted rental.

## Errors
`422 EXTRA_UNAVAILABLE` (an extra the Owner does not offer, or chosen twice), `409 RENTAL_NOT_OPEN`, `409 RENTAL_NOT_READY`, `409 CANCELLATION_REVIEW_REQUIRED` (started or finished), `409 OWN_VEHICLE`,
`409 SERVICE_UNAVAILABLE`, `422 ODOMETER_BELOW_LAST`, `422 VALIDATION_ERROR` (end below start).
