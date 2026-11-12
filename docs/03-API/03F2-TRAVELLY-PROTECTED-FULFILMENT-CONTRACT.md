# Travelly — Protected fulfilment of Ticket departures (matrix 54–58), slices 1 and 2

Status: built on `claude-work` (12 Nov 2026). Binding sources: PRD Final Decisions **D08**, data dictionary
`scheduled_trips` lifecycle, and owner decisions of 12 Nov 2026. Base `/api/v1`, Bearer token, JSON.
Errors: `{ "code", "message", "field_errors", "trace_id" }`. No new table.

## Rules (D08 + owner decisions)

- A missed decision deadline **never** cancels, refunds or commits by itself. It moves the departure to
  `DECISION_REQUIRED` and alerts the Admin and the Owner. Bookings stay `CONFIRMED`.
- An Owner who cannot run a sold departure reports a problem. The departure becomes `DISRUPTED`, sales stop, and
  open seat holds end. Paid bookings stay `CONFIRMED` while Travelly arranges the journey.
- Refund for non-fulfilment happens **only** when Travelly cannot fulfil: 100% of every paid seat.
- Replacement vehicle (owner decisions 12 Nov 2026, built in slice 2, sections 5–6):
  - Any vehicle type, but enough bookable seats for every booked passenger.
  - Seats are assigned automatically.
  - Passengers see the change. If one rejects it, that passenger gets a 100% refund; otherwise they travel in the
    replacement vehicle.
- A replacement from **another Owner** is not built: NBP excludes automatic cross-owner settlement. Until then the
  Admin's choices are the Owner's own replacement or "cannot fulfil".
- `COMMITTED` departures keep selling until the booking cut-off; commitment does not close sales.
  A committed departure can start like a published one.

## Departure fields (Owner view of `GET /scheduled-trips?mine=true` and `GET /scheduled-trips/{id}`)

New fields: `committed_at`, `replacement_status`, `cancellation_reason`. `status` can now also be `COMMITTED`,
`DECISION_REQUIRED`, `DISRUPTED` or `CANCELLED`.

Opening the Owner list also runs the deadline check, so a passed deadline shows as `DECISION_REQUIRED` straight away.

## 1. Owner commits — `POST /scheduled-trips/{id}/commit`

```json
{ "expected_version": 4 }
```

- **Who:** the departure's Owner.
- **Allowed from:** `PUBLISHED`, `BOOKING_OPEN`, `DECISION_REQUIRED` or `DISRUPTED`, before departure time.
- **Result:** `COMMITTED` and `committed_at` set. Paid passengers get "Your departure will run". If the departure
  was waiting for Travelly, the Admin is told it is resolved.
- **Errors:**
  - 409 `DEPARTURE_ALREADY_GUARANTEED`: a fixed departure that is still selling; it is already promised.
  - 409 `DEPARTURE_NOT_COMMITTABLE`
  - 409 `DEPARTURE_STARTED`
  - 409 `VERSION_CONFLICT`
  - 404 `DEPARTURE_NOT_FOUND`

## 2. Owner cannot run it — `POST /scheduled-trips/{id}/problem`

```json
{ "expected_version": 4, "reason": "The bus engine failed its inspection." }
```

- **Reason:** 5–1000 characters.
- **Allowed:** before the journey starts, from `PUBLISHED`, `BOOKING_OPEN`, `COMMITTED`, `DECISION_REQUIRED` or
  `READY`.
- **Open seat holds** end. Their payments still waiting fail; money that arrives later is refunded automatically.
  Their passengers are told.
- **No paid seat:** the departure is simply withdrawn. Status `CANCELLED`, seats `BLOCKED`, journey `CANCELLED`.
- **Paid seats:** status `DISRUPTED`. The Admin gets an `ADMIN_ACTION` notice (action required). Every paid
  passenger gets a `REPLACEMENT` notice: "Your booking stays confirmed while Travelly arranges your journey."
- **Errors:** 409 `DEPARTURE_NOT_REPORTABLE`, 409 `VERSION_CONFLICT`, 404.

## 3. Admin attention list — `GET /admin/departures/attention`

Departures in `DECISION_REQUIRED` or `DISRUPTED`, soonest first. Runs the deadline check first.

```json
{ "items": [ { "id": "…", "departure_reference": "DEP-…", "status": "DISRUPTED", "version": 6,
  "replacement_status": "NOT_REQUIRED", "fulfilment_policy": "MINIMUM_SEATS_WITH_PROTECTED_FULFILMENT",
  "minimum_confirmed_seats": 3, "decision_deadline": "…", "committed_at": null,
  "departure_at": "…", "estimated_arrival_at": "…",
  "route": { "route_name": "Colombo to Kandy", "origin_name": "Colombo", "destination_name": "Kandy" },
  "vehicle": { "public_vehicle_reference": "…", "vehicle_type_code": "VAN", "seat_capacity": 14 },
  "owner": { "public_user_reference": "USR-…", "display_name": "…" },
  "booked_seats": 2, "held_seats": 0, "paid_amount": "3000.00", "currency": "LKR", "cancellation_reason": null } ] }
```

Admin only; anyone else gets 403 `ADMIN_REQUIRED`.

## 4. Admin: Travelly cannot fulfil — `POST /admin/scheduled-trips/{id}/cannot-fulfil`

```json
{ "expected_version": 6, "reason": "No equivalent vehicle is available for this date." }
```

- **Allowed:** only from `DECISION_REQUIRED` or `DISRUPTED`, and only before the journey starts.
- **Paid bookings:**
  - Booking `CANCELLED`, travellers `CANCELLED`.
  - `cancellation_policy_snapshot` is `{ "policy": "DEPARTURE_NOT_FULFILLED_2026_11", "refund_percent": 100, … }`.
  - Every paid payment gets a full refund (`FULL_REFUND`, cause `DEPARTURE_NOT_FULFILLED`). The Admin's decision is
    the approval: Sandbox money goes back at once (`PAID`); PayHere goes to `PROCESSING`, to be completed in the
    portal as for other refunds.
  - The passenger gets a `REFUND` notice.
- **Holds:** cancelled.
- **Seats:** `BLOCKED`.
- **Departure:** journey `CANCELLED`, departure `CANCELLED`, `replacement_status` `FAILED`, `cancellation_reason`
  set. The Owner is told. Audited.
- **Response:** the attention item plus `refunds: [{ id, booking_id, amount, status }]`.
- **Errors:** 409 `DEPARTURE_NOT_ESCALATED`, 409 `DEPARTURE_STARTED`, 409 `VERSION_CONFLICT`, 404.

Refunded payments drop out of Owner payouts automatically (they are no longer `PAID`).

## 5. Owner replacement vehicle — `POST /scheduled-trips/{id}/replacement-vehicle`

```json
{ "expected_version": 6, "vehicle_id": "…" }
```

- **Who:** the departure's Owner.
- **Allowed:** only while the departure waits for Travelly (`DECISION_REQUIRED` or `DISRUPTED`), before it starts.
- **Vehicle:** one of the Owner's own. It must be approved and active, not the current one, have enough bookable
  seats in its newest seat layout for every booked passenger, and be free at that time.
- **Seats move automatically:** the same seat code when the replacement has it, otherwise the next free seat
  (front to back). The replacement's other bookable seats are offered for sale. The original vehicle's seats stay
  as history (`BLOCKED`). Open holds end.
- **Departure:** status `COMMITTED`, `replacement_status` `APPROVED`. The journey's vehicle changes. The Admin is
  told it is resolved. Audited.
- **Each paid booking** gets `pending_change` (shown on `GET /bookings/{id}/ticket`) and an action-required
  `REPLACEMENT` notice:

```json
{ "kind": "REPLACEMENT_VEHICLE", "status": "PENDING", "proposed_at": "…", "scheduled_trip_id": "…",
  "previous_vehicle": { "public_vehicle_reference": "…", "vehicle_type_code": "VAN", "make": "Toyota", "model": "Hiace",
                        "colour": "White", "air_conditioned": true, "seat_capacity": 14 },
  "replacement_vehicle": { "…": "same fields" },
  "seats": [ { "full_name": "Traveller A2", "from_seat": "A2", "to_seat": "B1", "seat_id": "…" } ],
  "refund_if_rejected_percent": 100, "decided_at": null }
```

- **Response:** the attention item plus `moved_seats`.
- **Errors:**
  - 409 `REPLACEMENT_NOT_ALLOWED`
  - 409 `REPLACEMENT_VEHICLE_UNAVAILABLE`
  - 409 `REPLACEMENT_TOO_SMALL` (message names the seat counts)
  - 409 `VEHICLE_SCHEDULE_CONFLICT`
  - 409 `VERSION_CONFLICT`
  - 404

## 6. Passenger answers the change — `POST /bookings/{id}/replacement-decision`

```json
{ "expected_version": 9, "decision": "ACCEPT" }
```

- **Who:** the booking's Passenger.
- **When:** while `pending_change.status` is `PENDING` and before the departure starts. **No answer means the
  passenger travels.**
- **`ACCEPT`:** `pending_change.status` becomes `ACCEPTED`. Nothing else changes.
- **`REJECT`:**
  - The booking is `CANCELLED` and its seats go back on sale.
  - `cancellation_policy_snapshot` is `{ "policy": "REPLACEMENT_REJECTED_2026_11", "refund_percent": 100 }`.
  - A `FULL_REFUND` (cause `REPLACEMENT_REJECTED`) is queued `PENDING` for Admin approval in the refunds screen, as
    for any Passenger cancellation.
  - The Passenger gets a `REFUND` notice; the Owner is told.
- **Response:** `{ booking_id, status, version, pending_change, refund: { id, amount, status } | null }`.
- **Errors:** 409 `NO_PENDING_CHANGE`, 409 `DEPARTURE_STARTED`, 409 `VERSION_CONFLICT`, 404 `BOOKING_NOT_FOUND`.

The seat map (`GET /scheduled-trips/{id}/seats`) shows only the vehicle that runs.

## Scheduled job

`scripts/escalate_departure_deadlines.py` runs the same deadline check, for example every 15 minutes. It is safe to
run repeatedly.

## Screens (UI Claude)

- **Owner, Ticket departures:**
  - Status chip.
  - "Commit to run" button for minimum-seats departures until committed, and when the departure is waiting for
    Travelly.
  - "I can't run this departure" button with a reason box.
- **Owner, departure that waits for Travelly:** "Use another of my vehicles" picker. Show the error message as is
  (for example "This vehicle has 12 bookable seats; 14 passengers are booked").
- **Passenger ticket page:** when `pending_change.status` is `PENDING`, show a card with the old and new vehicle and
  each seat move, plus two buttons: "Travel in the new vehicle" and "Reject and get a full refund" (confirm first).
- **Admin:** a "Departures needing attention" list with a "Cannot fulfil, refund everyone" action (reason required,
  confirmation step).
- **Passenger booking page:** show the `REPLACEMENT` / `REFUND` notices.
