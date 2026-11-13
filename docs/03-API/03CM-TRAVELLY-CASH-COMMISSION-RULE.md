# Travelly — cash commission overdue rule (13 Nov 2026)

Status: built on `claude-work`. **Owner decision** (not in the PRD; the PRD only says the Owner owes the commission on cash
trips, `COMMISSION_DUE`). Base `/api/v1`. No new table and no migration: the standing is **computed** from the Owner's
unpaid cash payments.

## The rule
Age = days since the Owner's **oldest unpaid** cash commission (`payments.captured_at`, `owner_settlement_status = COMMISSION_DUE`).

| Day | Stage | What happens |
|---|---|---|
| 0 – 14 | `FREE` | Trips carry on. The Owner can pay each commission, or all of it together. |
| 14 – 18 | `GRACE` | Reminders. Paying keeps everything as it is. |
| 18 + | `BLOCKED` | **New bookings stop, automatically.** |

- Days are settings: `COMMISSION_FREE_DAYS` (14) and `COMMISSION_BLOCK_DAYS` (18) in `.env`.
- **Blocked = new bookings only.** The Owner's vehicles are hidden from the vehicle list and the ticket departure list, and
  a new quote / booking request / ticket hold is refused. **Bookings already made, trips under way, accepted Drivers and
  changes to an existing booking are never cancelled or blocked.** Owner screens, payouts and Admin screens keep working.
- **It ends by itself** when the commission is recorded as received (or taken out of a payout, below). Nothing is stored,
  so nothing needs switching back on.
- An Owner who is only a Driver for another Owner is not affected.

## Reminders (`scripts/send_reminders.py`, same daily job)
Notification (`PAYMENT`) + email copy when email is on. The latest stage reached is sent once per debt:
day 10 "Commission due soon", day 14 "Your commission is due", day 16 "Pay your commission" (2 days left),
day 17 "Last day to pay", day 18 "New bookings are stopped". When the commission is paid the Owner gets
"Bookings are open again".

## API
### Owner — `GET /owners/me/settlements` (and Admin `GET /admin/owner-settlements`) now include
```json
"commission_standing": { "stage": "GRACE", "days_open": 15, "amount_due": "3370.00", "oldest_due_at": "…",
  "free_until": "…", "blocked_from": "…", "extended_until": null, "free_days": 14, "block_days": 18, "blocked": false }
```
`stage`: `NONE` (nothing owed), `FREE`, `GRACE`, `BLOCKED`. `blocked` is the one that decides (an Admin extension can make a
`BLOCKED` stage show `blocked: false`).

### Admin — overdue list: `GET /admin/owner-settlements?overdue=true`
Only Owners in `GRACE` or `BLOCKED`, longest first.

### Admin — extra days: `POST /admin/owner-settlements/{owner_id}/commission-extension`
```json
{ "days": 3, "reason": "Bank holiday" }
```
`days` 1–30, `reason` 3–500 characters (kept in the audit record). Returns the new `commission_standing`. The Owner is
notified. When the extra days pass, the block applies again.

### Admin — take the commission out of a payout: `POST /admin/owner-settlements/{owner_id}/payouts`
New optional field `"settle_commission": true`. The commission the Owner owes (oldest first, whole payments only, never more
than the payout) is marked `COMMISSION_PAID`. The reply adds:
`commission_set_off`, `commission_payments` (ids), `bank_transfer_total` (= `total` − `commission_set_off`, the amount to
send to the bank). The Owner's notification says how much was taken out.

### Errors for Passengers
Blocked Owners are simply unavailable: `409 VEHICLE_NOT_AVAILABLE` (private hire) or `409 DEPARTURE_NOT_AVAILABLE` (ticket
hold). No reason about the Owner's money is shown to the Passenger.

## Screens (UI Claude)
- **Owner → Settlements / Overview:** a banner from `commission_standing`:
  - `FREE`: "You owe LKR {amount_due} commission. Please pay by {free_until}." (shown only when `amount_due` > 0)
  - `GRACE`: warning colour. "Pay LKR {amount_due} by {blocked_from} or new bookings stop."
  - `blocked`: red. "New bookings are stopped until you pay LKR {amount_due}. Bookings you already have are not affected."
- **Admin → Settlements:** a filter "Commission overdue" (`?overdue=true`), a stage chip and `days_open` per Owner, an
  "Extend days" action (days + reason), and a "Take commission out of this payout" tick on the payout form that shows
  `bank_transfer_total` after it is sent.
- Strings in `messages.js`.

## Not built (ask the owner)
- Waiving or forgiving a commission amount (the Admin can only extend days, or record it as received).
- Interest or a late fee.
