# Travelly — search shows "ask the Owner" vehicles (14 Nov 2026)

Status: built on `claude-work`. **Owner decision** (not in the PRD). Applies to Airport, Local and Long-distance private hire
(not Event, which sells fixed packages). Base `/api/v1`.

## How a price is found (unchanged)
1. A **fixed-route rate** that covers the journey (wins).
2. Otherwise a **km-wise / day-hire rate** whose area covers the journey.
3. Otherwise there is no saved price: the Passenger asks the Owner for one.

## What changed in `POST /search/vehicles`
The response now has two lists:
- `items`: vehicles with a price, exactly as before.
- **`quote_on_request`**: vehicles that offer this service around the pickup (one of the Owner's saved rates for this service covers the
  pickup area), are approved, published and free for the dates, but have **no saved price for this exact journey**. Each entry is the usual
  vehicle card plus `price: null` and `quote_required: true`. The Owner's other rates are never shown.
- Vehicles that do not offer this service, do not cover the pickup area, are busy, blocked (cash commission rule) or not approved appear in neither list.
- When the road-distance service is down, vehicles are listed in `quote_on_request` instead of failing.
- Limitation: a vehicle with no saved rate at all for the service has no known area, so it is not listed until its Owner saves one rate.

## Asking the Owner
Use the existing `POST /bookings/private-hires` for the chosen vehicle. With no saved price it creates an unpriced request
(`status: REQUESTED`, `proposal: {}`). The Owner answers with `POST /bookings/{id}/quote` (the quote also saves the reusable rate), the
Passenger sees `proposal.quote`, and accepts with `POST /bookings/{id}/price-acceptance`.
- A Passenger can wait for at most **3** Owner prices at once: `409 TOO_MANY_OPEN_REQUESTS`. Cancel one with `POST /bookings/{id}/cancel`.
- An unanswered request closes after **24 hours** (daily `send_reminders.py`): status `CANCELLED`, reason "The Owner did not send a price in time.",
  and the Passenger gets a notification.
