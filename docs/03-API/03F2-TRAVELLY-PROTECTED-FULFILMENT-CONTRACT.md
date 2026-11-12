# Travelly — Protected fulfilment of Ticket departures (matrix 54–58), slice 1

Status: built on `claude-work` (12 Nov 2026). Binding sources: PRD Final Decisions **D08**, data dictionary
`scheduled_trips` lifecycle, and owner decisions of 12 Nov 2026. Base `/api/v1`, Bearer token, JSON.
Errors: `{ "code", "message", "field_errors", "trace_id" }`. No new table.

## Rules (D08 + owner decisions)

- A missed decision deadline **never** cancels, refunds or commits by itself. It moves the departure to
  `DECISION_REQUIRED` and alerts the Admin and the Owner. Bookings stay `CONFIRMED`.
- An Owner who cannot run a sold departure reports a problem. The departure becomes `DISRUPTED`, sales stop, and
  open seat holds end. Paid bookings stay `CONFIRMED` while Travelly arranges the journey.
- Refund for non-fulfilment happens **only** when Travelly cannot fulfil: 100% of every paid seat.
- Next slice (not built yet), from the owner decisions:
  - Replacement vehicle: any type, but with enough seats for every booked passenger.
  - Seats are assigned automatically.
  - Passengers see the change. If one rejects it, that passenger gets a 100% refund; otherwise they travel in the
    replacement vehicle.
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

## Scheduled job

`scripts/escalate_departure_deadlines.py` runs the same deadline check, for example every 15 minutes. It is safe to
run repeatedly.

## Screens (UI Claude)

- **Owner, Ticket departures:**
  - Status chip.
  - "Commit to run" button for minimum-seats departures until committed, and when the departure is waiting for
    Travelly.
  - "I can't run this departure" button with a reason box.
- **Admin:** a "Departures needing attention" list with a "Cannot fulfil, refund everyone" action (reason required,
  confirmation step).
- **Passenger booking page:** show the `REPLACEMENT` / `REFUND` notices.
