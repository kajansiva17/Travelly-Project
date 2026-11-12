# Travelly — Payments API contract (Ticket seats, private hire, refunds, Owner settlement; Sandbox and PayHere)

Status: **built and tested** on `claude-work` (11 Nov 2026). Backend suite 416 passed. This is the contract the UI
branch builds the **Pay button** and the **Admin payment settings** screen against. Do not change paths or field names.

Owner decisions (11 Nov 2026): no advance for private hire (paid after the trip, later slice); the gateway fee comes out
of the Owner's share, never Travelly's; commission is an Admin percentage per service type; built-in Sandbox and PayHere (Sandbox credentials now, live later)
are both available, chosen by Admin per service type. PayHere's address and city are asked on the Pay screen and never stored.
PRD 6.6: an online Ticket seat is BOOKED only after the **full** amount is paid. Ticket cash sale is Phase 2.

## Common rules

- Base URL `/api/v1`. Every call needs `Authorization: Bearer <access token>`, except the provider webhook.
- POST/PATCH bodies must be `Content-Type: application/json` (else **415** `UNSUPPORTED_MEDIA_TYPE`). Unknown body
  fields are rejected (**422** `VALIDATION_ERROR`). No query parameters on these endpoints.
- Money is always a **string** with two decimals: `"3000.00"`. Currency `"LKR"`.
- Every error has this shape:

```json
{ "code": "PAYMENT_IN_PROGRESS", "message": "A payment for this booking is already in progress.",
  "field_errors": [ { "field": "payment_id", "message": "247c7b8a-..." } ], "trace_id": "f2a3..." }
```

Show `message` to the user unless the screen has a better translated text for that `code`.

---

## A. Pay button (Passenger, ticket hold page)

### A1. Read the booking — `GET /bookings/{booking_id}/ticket` (existing, new payment fields)

New fields:

| Field | Meaning |
|---|---|
| `payment_status` | `null` (never tried), `"PENDING"`, `"FAILED"`, `"PAID"` |
| `latest_payment` | `null` or the most recent seat payment (below) |
| `payment_provider` | `"SANDBOX"` or `"PAYHERE"` — the provider Admin chose for this service; `null` if none can take payments right now (then hide Pay and show "Online payment is not available right now") |
| `payment_method` | the value to send as `method` in A2: `"SANDBOX"` for the Sandbox, `"CARD"` for PayHere; `null` when `payment_provider` is null |
| `payer_details_required` | list of fields to ask **before** Pay and send in A2's `payer`: `[]` for the Sandbox; for PayHere `["address", "city"]`, plus `"phone"` / `"email"` only if the account has none |

```json
{
  "id": "78110bda-...", "booking_reference": "TKT-08AE4837304A4896", "booking_type": "TICKET_HIRE",
  "status": "REQUESTED", "version": 3, "scheduled_trip_id": "d59bfcd3-...",
  "hold_active": true, "hold_expires_at": "2026-11-11T14:29:15.079846+00:00",
  "currency": "LKR", "total_amount": "3000.00",
  "payment_status": "FAILED",
  "payment_provider": "PAYHERE", "payment_method": "CARD", "payer_details_required": ["address", "city"],
  "latest_payment": {
    "id": "247c7b8a-...", "payment_reference": "PAY-C21DF5A47987440F879E", "status": "FAILED",
    "amount": "3000.00", "currency": "LKR", "provider_name": "SANDBOX",
    "failure_code": "SANDBOX_DECLINED", "failure_message": "The payment did not go through. No money was taken."
  },
  "assurance_type": "FIXED_DEPARTURE", "itinerary": { "...": "unchanged" }, "cancellation_reason": null,
  "travellers": [ { "full_name": "Traveller A1", "seat_code": "A1", "fare": "1500.00", "...": "unchanged" } ]
}
```

### A2. Start a payment — `POST /bookings/{booking_id}/payment-intents`

Request (all required):

```json
{ "amount": "3000.00", "currency": "LKR", "method": "SANDBOX", "idempotency_key": "9f1c2e0d4b7a4e21" }
```

- `amount` / `currency`: send the booking's `total_amount` and `currency` exactly.
- `method`: send A1's `payment_method` — `"SANDBOX"` when the service uses the built-in Sandbox; `"CARD"` when it uses PayHere (the Passenger picks
  card, HelaPay or a wallet on PayHere's page; the server records what they actually used).
- `payer` (optional object, **required for PayHere**; ask exactly the fields in A1's `payer_details_required`): `{"address": "12 Galle Road", "city": "Colombo"}`, plus `"phone"`
  (E.164, e.g. `"+94771234567"`) only if the account has no phone and `"email"` only if it has no email. Name, email and
  phone otherwise come from the Travelly account. Sent to PayHere, not stored by Travelly. Ignored by the Sandbox.
- `idempotency_key`: 8–40 chars `[A-Za-z0-9_-]`. Make **one key per button press** and reuse it if you retry the same
  request after a network error; the server then returns the same payment instead of a second one.

**201 Created** (a repeat with the same key returns **200** and the same body):

```json
{
  "id": "247c7b8a-b1ab-43f5-8b72-4cc35342181a", "payment_reference": "PAY-C21DF5A47987440F879E",
  "booking_id": "78110bda-...", "transaction_type": "PAYMENT", "payment_method": "SANDBOX",
  "provider_name": "SANDBOX", "amount": "3000.00", "currency": "LKR", "status": "PENDING", "version": 1,
  "created_at": "2026-11-11T14:19:15.139685+00:00", "captured_at": null,
  "failure_code": null, "failure_message": null,
  "checkout": { "provider": "SANDBOX", "mode": "SANDBOX",
                "message": "Sandbox payment: no real money moves. Choose success or failure to finish." }
}
```

| Status | `code` | When | What the UI does |
|---|---|---|---|
| 404 | `BOOKING_NOT_FOUND` | not this Passenger's booking | show not found |
| 409 | `PAYMENT_NOT_AVAILABLE` | booking is not a ticket booking | hide the Pay button |
| 410 | `HOLD_EXPIRED` | the hold ended, seats released | "Hold ended — choose seats again", link back to the seat map |
| 409 | `HOLD_NOT_ACTIVE` | booking has no active hold | refresh A1 |
| 409 | `BOOKING_ALREADY_PAID` | already paid | refresh A1 (shows confirmed) |
| 409 | `PAYMENT_IN_PROGRESS` | a payment is already waiting | use `field_errors[0].message` (= payment id) and go to the Sandbox choice for that payment |
| 422 | `PAYMENT_AMOUNT_MISMATCH` | amount/currency differ | `field_errors[0].message` is the correct amount, e.g. `"3000.00 LKR"`; refresh A1 |
| 422 | `PAYMENT_METHOD_UNAVAILABLE` | method not offered by the provider | send `SANDBOX` |
| 409 | `PAYMENT_PROVIDER_UNAVAILABLE` | no provider configured | "Online payment is not available right now" |
| 409 | `IDEMPOTENCY_KEY_REUSED` | key used for another booking | make a new key |
| 422 | `PAYER_DETAILS_REQUIRED` | PayHere needs details the request did not give | `field_errors[].field` lists them: `payer.address`, `payer.city`, maybe `payer.phone`, `payer.email` |
| 422 | `VALIDATION_ERROR` | bad body | show field errors |

#### A2b. When the service uses PayHere, `checkout` looks like this

```json
"checkout": {
  "provider": "PAYHERE", "mode": "SANDBOX", "method": "POST",
  "action": "https://sandbox.payhere.lk/pay/checkout",
  "fields": { "merchant_id": "1211149", "return_url": "http://127.0.0.1:5173/travel/book/tickets?booking=<booking_id>&payment=returned",
              "cancel_url": "http://127.0.0.1:5173/travel/book/tickets?booking=<booking_id>&payment=cancelled",
              "notify_url": "https://<public api>/api/v1/payments/webhooks/payhere", "order_id": "PAY-C21DF5A47987440F879E",
              "items": "Travelly booking TKT-08AE4837304A4896", "currency": "LKR", "amount": "3000.00",
              "first_name": "Test", "last_name": "Person", "email": "...", "phone": "+9477...", "address": "12 Galle Road",
              "city": "Colombo", "country": "Sri Lanka", "custom_1": "<booking_id>", "hash": "3C7A...UPPERCASE MD5" },
  "message": "You will be taken to PayHere to pay. Your seats are confirmed only after PayHere reports success."
}
```

The Pay button **builds an HTML form** with `action`, `method="POST"` and one hidden input per entry in `fields`
(names and values exactly as given), then submits it. Do not change or recompute any field — `hash` is
made on the server so the merchant secret never reaches the browser. In live mode `action` is
`https://www.payhere.lk/pay/checkout` and `mode` is `"LIVE"`.

PayHere sends the browser back to `return_url` (`&payment=returned`) or `cancel_url` (`&payment=cancelled`). **Neither
proves payment.** On that page read A1 again: the seats are confirmed only when PayHere's signed server notice has
arrived (`status: "CONFIRMED"`, `payment_status: "PAID"`). If it still says `latest_payment.status: "PENDING"`, show
"Waiting for PayHere to confirm…" and re-read A1 every few seconds for about a minute.

#### A2c. Reopen a waiting payment — `POST /payments/{payment_id}/checkout`

For a payment still `PENDING` (e.g. the Passenger closed PayHere and came back while the hold is active). Body:
`{"payer": {"address": "...", "city": "..."}}` for PayHere, `{}` for the Sandbox. **200** returns the payment plus a fresh
`checkout` (same order id, same amount). Errors: 404 `PAYMENT_NOT_FOUND`, 409 `PAYMENT_NOT_PENDING`, 422
`PAYER_DETAILS_REQUIRED`. Use this instead of A2 when A2 answers `PAYMENT_IN_PROGRESS`.

### A3. Finish a Sandbox payment — `POST /payments/{payment_id}/sandbox-outcome`

Sandbox only (refused in production). `outcome` is `"SUCCEEDED"` or `"FAILED"`. The Passenger chooses the result; this runs the same code a real provider
notification runs.

```json
{ "outcome": "SUCCEEDED" }
```

**200** — the payment (same fields as A2, without `checkout`) plus `booking_status`:

```json
{ "id": "0d3b3333-...", "payment_reference": "PAY-F176925AF3E3464B9CC3", "status": "PAID", "version": 2,
  "amount": "3000.00", "currency": "LKR", "captured_at": "2026-11-11T14:19:15.228772+00:00",
  "failure_code": null, "failure_message": null, "booking_status": "CONFIRMED", "...": "other A2 fields" }
```

- `SUCCEEDED` → `status: "PAID"`, `booking_status: "CONFIRMED"`; every held seat is now BOOKED.
- `FAILED` → `status: "FAILED"`, `failure_code: "SANDBOX_DECLINED"`, `booking_status: "REQUESTED"`; **the hold stays**,
  so the Passenger can press Pay again (new A2 call, new key) until `hold_expires_at`.
- Sending `SUCCEEDED` again on a PAID payment returns 200 PAID (no second charge).

| Status | `code` | When | What the UI does |
|---|---|---|---|
| 404 | `PAYMENT_NOT_FOUND` | not this Passenger's Sandbox payment | show not found |
| 410 | `HOLD_EXPIRED` | the hold ended before success; payment marked FAILED, seats released | "Hold ended — choose seats again" |
| 409 | `PAYMENT_NOT_PENDING` | payment already FAILED | start a new payment (A2) |

A3 works only for payments whose `provider_name` is `"SANDBOX"`; a PayHere payment answers 404 here.

### A4. Payment history — `GET /bookings/{booking_id}/payments`

Passenger, the booking's Owner, or an Admin. **200**:

```json
{ "booking_id": "78110bda-...", "payment_status": "PAID",
  "items": [ { "id": "...", "payment_reference": "PAY-...", "booking_id": "...", "transaction_type": "PAYMENT",
               "payment_method": "SANDBOX", "provider_name": "SANDBOX", "amount": "3000.00", "currency": "LKR",
               "status": "PAID", "version": 2, "created_at": "...", "captured_at": "...",
               "failure_code": null, "failure_message": null } ] }
```

Owner and Admin also get, per item: `commission_amount`, `gateway_fee_amount`, `owner_net_amount`,
`owner_settlement_status` (`null` until the trip completes, then `"OWNER_PAYABLE"`), `owner_payable_at`,
`owner_paid_at`. All amounts are strings or `null` (null while not PAID). **404** `BOOKING_NOT_FOUND` for anyone else.

### Pay button — states the screen needs

| A1 says | Show |
|---|---|
| `status: "REQUESTED"`, `hold_active: true`, `payment_status` null or `"FAILED"` | **Pay LKR {total_amount}** button + countdown to `hold_expires_at`. If FAILED, show `latest_payment.failure_message` above it. |
| `hold_active: true`, `latest_payment.status: "PENDING"`, `provider_name: "SANDBOX"` | the Sandbox choice for `latest_payment.id` (do not call A2 again) |
| `hold_active: true`, `latest_payment.status: "PENDING"`, `provider_name: "PAYHERE"` | "Waiting for PayHere…" + a **Continue to PayHere** button → A2c, then submit the form |
| Before Pay, `payer_details_required` not empty | ask exactly those fields (address, city, maybe phone/email); one short line: "Needed by PayHere for this payment. Travelly does not keep it." |
| `payment_provider: null` | no Pay button; "Online payment is not available right now" |

Choose the flow from A1's `payment_provider`, never by trying one method and falling back to another.
| Sandbox choice (after A2 or the row above) | two buttons: **Pay successfully** → A3 `SUCCEEDED`; **Simulate failure** → A3 `FAILED`; plus `checkout.message` |
| `status: "CONFIRMED"`, `payment_status: "PAID"` | "Seats confirmed" + `latest_payment.payment_reference`; no Pay button |
| `status: "CANCELLED"` | "Hold ended — choose seats again" |

After every A2/A3 response, re-read A1 rather than guessing the state. Disable the buttons while a request is running.
The countdown ends at `hold_expires_at`; when it reaches zero, re-read A1 (the server releases the seats).

---

## B. Admin payment settings screen

Admin only (approved ADMIN). Non-admins get **403**.

### B1. List — `GET /admin/payment-settings`

```json
{ "items": [ { "id": "a3ab10ce-...", "code": "TICKET_HIRE", "name": "Scheduled ticket", "category": "TICKET_HIRE",
               "is_active": true, "version": 3, "payment_provider": "SANDBOX",
               "commission_percent": "0.00", "gateway_fee_percent": "0.00",
               "available_providers": ["SANDBOX"] } ] }
```

One row per service type (ordered by display order). Unset settings read as Sandbox / 0.00 / 0.00.
Fill the provider dropdown from `available_providers`: `["SANDBOX"]`, or `["PAYHERE", "SANDBOX"]` once the server has
PayHere credentials and a public HTTPS address. When the provider is PayHere, set the gateway fee % to PayHere's plan
rate (Lite 3.30) so the Owner's share is right; PayHere's notice does not report the fee.

### B2. Save one row — `PATCH /admin/service-types/{service_id}/payment-settings`

```json
{ "expected_version": 3, "payment_provider": "SANDBOX", "commission_percent": "10", "gateway_fee_percent": "2.5" }
```

- Percentages are strings, 0–100, at most two decimals. Returned normalised (`"10.00"`, `"2.50"`).
- `expected_version` = the row's `version` from B1. **200** returns the updated row (new `version`); keep it for the
  next save.
- The change applies to **new** payments only; paid payments keep their amounts. Each save is audited.

| Status | `code` | When | What the UI does |
|---|---|---|---|
| 409 | `VERSION_CONFLICT` | someone else saved first | "Changed by someone else — reload", re-read B1 |
| 422 | `PAYMENT_SETTINGS_INVALID` | commission + fee > 100 | show on the fee field (`field_errors[0].field = "gateway_fee_percent"`) |
| 422 | `PAYMENT_PROVIDER_UNAVAILABLE` | `PAYHERE` chosen but the server has no PayHere credentials | show on the provider field |
| 422 | `VALIDATION_ERROR` | bad percentage format or > 100 | show on that field (`field_errors[].field`) |
| 404 | `SERVICE_NOT_FOUND` | unknown service | re-read B1 |
| 403 | — | not an approved Admin | — |

Screen content: one row per service: name, provider dropdown, commission %, gateway fee %, a live example
"On LKR 1,000: Travelly {commission}, gateway {fee}, Owner {1000 − both}", Save. Explain in one line that the gateway fee
is taken from the Owner's share and is never Travelly income; Travelly earns only the commission.

---

## D. Private hire payment (slice 2) — booking page, Passenger + Driver/Owner

Owner decisions (11 Nov 2026): **no advance** — a private hire is paid in full **after the trip is COMPLETED**, online or
in cash. Cash only if the Owner accepts cash for that vehicle service, collected at the **END** only, and settled only
when **both** the Passenger and the collector (the trip's Driver, or the Owner when self-driving) confirm. Commission
applies to cash too; the Owner owes it to Travelly (`owner_settlement_status: "COMMISSION_DUE"`).

### D1. Payment panel — `GET /bookings/{booking_id}/payment-summary`

Passenger, the booking's Owner, the trip's Driver, or Admin (others 404; ticket bookings 404 — they use A1).

```json
{ "booking_id": "…", "booking_status": "COMPLETED",
  "payment_status": null, "payment_due": true, "amount_due": "6900.00", "currency": "LKR",
  "payment_provider": "SANDBOX", "payment_method": "SANDBOX", "payer_details_required": [],
  "cash_accepted": true, "cash_collection_stage": "END", "collector_user_id": "…",
  "cash": null, "latest_payment": null }
```

| Field | Meaning |
|---|---|
| `payment_due` | `true` only when the booking is COMPLETED and not yet paid — show the pay options then, never before |
| `amount_due` | the full amount to pay (string), `null` when nothing is due |
| `payment_status` | `null`, `"PENDING"`, `"FAILED"`, `"CASH_AWAITING_CONFIRMATION"`, `"PAID"` |
| `payment_provider` / `payment_method` / `payer_details_required` | same meaning as in A1 (online payment) |
| `cash_accepted` | show the "Pay in cash" option only when `true` |
| `collector_user_id` | who collects cash (the trip's Driver / self-driving Owner); send it in D3 |
| `cash` | `null`, or `{ "payment_id", "status", "passenger_confirmed": bool, "collector_confirmed": bool }` |
| `latest_payment` | `null` or `{ "id", "payment_reference", "status", "payment_method", "provider_name", "amount", "currency", "failure_code", "failure_message" }` |

### D2. Pay online after the trip

Same as A2/A2b/A2c/A3 with the private-hire booking id: `POST /bookings/{booking_id}/payment-intents` with
`amount` = `amount_due`. Before completion → **409 `PAYMENT_NOT_DUE`**. A cash payment waiting for confirmation →
409 `PAYMENT_IN_PROGRESS`. Sandbox success answers `booking_status: "COMPLETED"` (the booking stays completed;
`payment_status` becomes `"PAID"`). PayHere returns the browser to `/bookings/{id}?booking={id}&payment=returned|cancelled`
— re-read D1, which proves nothing until `payment_status` is `"PAID"`. Online private-hire payments are immediately
`OWNER_PAYABLE` for the Owner.

### D3. Cash — `POST /bookings/{booking_id}/cash-receipts`

Each side calls it once with **only its own** confirmation.

Passenger ("I paid"):
```json
{ "amount": "6900.00", "currency": "LKR", "collection_stage": "END", "collector_user_id": "<D1 collector_user_id>",
  "passenger_confirmation": true, "collector_confirmation": false, "idempotency_key": "c4f1a2b3d4e5" }
```
Driver / self-driving Owner ("I received it"): same body with `"passenger_confirmation": false, "collector_confirmation": true`.

- First confirmation → **201**, payment `status: "CASH_AWAITING_CONFIRMATION"`; the other side gets a notification.
- The same side again → **200**, unchanged.
- The other side → **200**, `status: "PAID"`; both get a notification.

Response: the payment (A2 fields) plus `booking_payment_status`, `passenger_confirmed`, `collector_confirmed`.

| Status | `code` | When |
|---|---|---|
| 404 | `BOOKING_NOT_FOUND` | caller is neither the Passenger nor the collector |
| 409 | `CASH_NOT_AVAILABLE` | not a private hire |
| 422 | `CASH_COLLECTION_STAGE_INVALID` | `collection_stage` is not `END` |
| 409 | `PAYMENT_NOT_DUE` | trip not completed yet |
| 409 | `CASH_NOT_ACCEPTED` | the Owner does not accept cash for this vehicle — offer online |
| 422 | `COLLECTOR_NOT_ASSIGNED` | wrong `collector_user_id` (`field_errors[0].message` is the right one) |
| 422 | `CONFIRMATION_NOT_YOURS` | a caller set the other side's flag, or not its own |
| 422 | `PAYMENT_AMOUNT_MISMATCH` | amount ≠ `amount_due` |
| 409 | `PAYMENT_IN_PROGRESS` | an online payment is waiting |
| 409 | `BOOKING_ALREADY_PAID` | already paid online |

Booking page states: before completion → "Payment opens when the trip is completed"; `payment_due` → **Pay online**
(+ **Pay in cash** if `cash_accepted`); Passenger after confirming cash → "Waiting for the Driver to confirm"; collector
sees **Confirm cash received LKR {amount_due}** when `cash.passenger_confirmed` (or first); `PAID` → "Paid" + reference.

### D4. Owner — accept cash per vehicle service — `PATCH /vehicles/{vehicle_id}/services/{service_type_id}/payment-options`

```json
{ "expected_version": 4, "cash_accepted": true }
```
`expected_version` is that service's `version` from `GET /vehicles/{vehicle_id}/services` (each item now also has
`cash_accepted`). **200** `{ "vehicle_id", "service_type_id", "version", "cash_accepted", "cash_collection_stage": "END" }`.
Errors: 404 `VEHICLE_NOT_FOUND` / `VEHICLE_SERVICE_NOT_FOUND` (save the service and prices first), 409 `VERSION_CONFLICT`,
422 `CASH_NOT_ALLOWED` (ticket services are online only). Put it on the vehicle's Prices / service step as a single
switch: "Accept cash at the end of the trip".

## E. Ticket cancellation and refunds

Owner decisions (11 Nov 2026): a Passenger who cancels a **paid** ticket gets **100%** if more than 72 h before departure,
**50%** from 24 to 72 h, **0%** under 24 h. The system works out the amount and queues the refund; an **Admin approves**
(or rejects with a reason). Money that arrived after a seat hold ended is queued for a full refund automatically.
Refunds are rows in the same payment history (`transaction_type` `FULL_REFUND` / `PARTIAL_REFUND`).

### E1. Passenger cancels a paid ticket — `POST /bookings/{booking_id}/ticket-cancellation`

```json
{ "reason": "Plans changed", "expected_version": 6 }
```
`expected_version` optional (A1 `version`). **200** = A1 body (now `status: "CANCELLED"`) plus:
```json
{ "refund_percent": 50, "hours_before_departure": 48.0,
  "refund": { "id": "…", "payment_reference": "RFD-…", "amount": "1500.00", "currency": "LKR",
              "transaction_type": "PARTIAL_REFUND", "status": "PENDING", "cause": "PASSENGER_CANCELLATION", "…": "see E2" } }
```
`refund` is `null` when 0% applies. Seats become available at once.

Errors: 404 `BOOKING_NOT_FOUND`; 409 `TICKET_NOT_CANCELLABLE` (not a paid confirmed ticket — an unpaid hold is
released with `DELETE /bookings/{id}/seat-hold`); 409 `DEPARTURE_STARTED`; 409 `VERSION_CONFLICT`.

UI before confirming: show the band that applies now, e.g. "Cancelling now refunds 50% (LKR 1,500.00) after Admin
approval", computed from `itinerary.departure_at`: > 72 h → 100%, 24–72 h → 50%, < 24 h → 0%. The server decides at the
moment of the request.

### E2. Admin refunds screen — `GET /admin/refunds`

```json
{ "waiting": 1,
  "items": [ { "id": "…", "payment_reference": "RFD-…", "booking_id": "…", "booking_reference": "TKT-…",
               "original_payment_id": "…", "original_payment_reference": "PAY-…", "original_amount": "3000.00",
               "transaction_type": "PARTIAL_REFUND", "cause": "PASSENGER_CANCELLATION", "amount": "1500.00", "currency": "LKR",
               "provider_name": "SANDBOX", "payment_method": "SANDBOX", "status": "PENDING", "version": 1,
               "created_at": "…", "refunded_at": null, "provider_reference": null, "failure_code": null,
               "cancellation": { "policy": "TICKET_PASSENGER_CANCELLATION_2026_11", "refund_percent": 50,
                                 "hours_before_departure": 48.0, "cancelled_at": "…", "bands": ["…"] } } ] }
```
Waiting first (`PENDING`, then `PROCESSING`), then the latest 200. `cause`: `PASSENGER_CANCELLATION`,
`PAYMENT_AFTER_HOLD`, `ADMIN`. Status: `PENDING` (needs a decision) → `PAID` (money back) or `FAILED` (rejected);
PayHere refunds go `PENDING` → `PROCESSING` → `PAID`.

### E3. Decide — `POST /admin/refunds/{refund_id}/decision`

```json
{ "expected_version": 1, "decision": "APPROVE" }
{ "expected_version": 1, "decision": "REJECT", "reason": "Duplicate request" }
```
**200** = the E2 item. Sandbox approve → `PAID` at once. PayHere approve → `PROCESSING`, then (12 Nov 2026, when the
Refund API is set up) the refund is sent to PayHere straight away, see E6; otherwise the Admin refunds it in the
PayHere portal and records it with E4. Reject → `FAILED`, `failure_code: "REFUND_REJECTED"`; the payment stays paid.
Errors: 422 `REASON_REQUIRED` (reject without reason), 409 `REFUND_ALREADY_DECIDED`, 409 `VERSION_CONFLICT`, 404 `REFUND_NOT_FOUND`.

### E4. Record a PayHere refund — `POST /admin/refunds/{refund_id}/complete`

```json
{ "expected_version": 2, "provider_reference": "PayHere refund no. from the portal" }
```
Only for `PROCESSING`. **200** → `PAID`. Error 409 `REFUND_NOT_PROCESSING`. Use it for a refund done in the PayHere
portal, a wallet or bank payment refunded by bank transfer (`PAYHERE_MANUAL_REQUIRED`), or a refund whose PayHere
answer never arrived (`PAYHERE_REQUESTED`).

### E5. Admin refunds a payment directly — `POST /payments/{payment_id}/refunds` (PRD 68)

```json
{ "full": true, "reason": "Trip cancelled by operator", "idempotency_key": "a1b2c3d4e5f6" }
{ "full": false, "amount": "500.00", "reason": "Goodwill for a late departure", "idempotency_key": "…" }
```
**201** = E2 item, approved at once (Sandbox `PAID`, PayHere `PROCESSING`). The same key again returns the same refund.
Errors: 422 `VALIDATION_ERROR` (both `full` and `amount`), 422 `REFUND_AMOUNT_INVALID` (more than is left;
`field_errors[0].message` = what can still be refunded), 409 `PAYMENT_NOT_REFUNDABLE`.

### E6. PayHere Refund API (automatic, 12 Nov 2026)

Set up with `PAYHERE_APP_ID` and `PAYHERE_APP_SECRET` in `Backend/.env`: PayHere > Settings > API Keys, permission
"Automatic Charging API" (plus "Payment Retrieval API"), allowed domain as registered. Check with
`.venv\Scripts\python.exe Backend\scripts\check_payhere_refund_api.py`. It prints only yes/no and makes no refund.

After an approval is committed (E3, E5, and the protected-fulfilment "cannot fulfil"), each PayHere refund in
`PROCESSING` is sent to PayHere: the full amount, or `amount` for a partial refund (for example the 50% ticket rule).
The E2 item then shows:

| `status` / `failure_code` | Meaning | Admin action |
|---|---|---|
| `PAID`, `provider_reference: "PHR-<PayHere refund no.>"` | PayHere accepted it | none |
| `PROCESSING` / `PAYHERE_REFUND_FAILED` (+ `failure_message` from PayHere) | PayHere refused it or could not be reached | **Send again** (E7), or refund in the portal and record with E4 |
| `PROCESSING` / `PAYHERE_MANUAL_REQUIRED` | not a card payment; PayHere refunds cards only | refund by bank transfer, record with E4 |
| `PROCESSING` / `PAYHERE_REQUESTED` | sent, answer not recorded (timeout or crash). Never sent again automatically | check the PayHere portal, record with E4 |
| `PROCESSING` / `null` | Refund API not set up | portal + E4, as before |

E2 items now also carry `failure_message`.

### E7. Send again — `POST /admin/refunds/{refund_id}/payhere`

Body `{}`. Only for a PayHere card refund in `PROCESSING` with `failure_code` `PAYHERE_REFUND_FAILED` (or none).
**200** = the E2 item after the new attempt.
Errors:
- 409 `REFUND_NOT_RETRYABLE` (already paid, waiting for PayHere, or not a card payment)
- 409 `PAYHERE_REFUND_API_OFF`
- 404 `REFUND_NOT_FOUND`

When the refunds add up to the whole payment its status becomes `REFUNDED`, otherwise `PARTIALLY_REFUNDED`; the
booking's `payment_status` follows. The Passenger gets a `REFUND` notification when money goes back. Every Admin decision
is audited with its reason.

## F. Admin payments and Owner settlement

Money Travelly holds for an Owner is paid out only after the trip (PRD 6.6). Settlement status on each `PAYMENT` row
(`owner_settlement_status`): `OWNER_PAYABLE` (online money held for the Owner — ticket: once the departure completes;
private hire: when paid) → `OWNER_PAID`; cash: `COMMISSION_DUE` (the Owner collected the cash and owes the commission)
→ `COMMISSION_PAID`. A payout is a new `OWNER_PAYOUT` row linked to the payment. Payments with a **partial refund** are
never made payable automatically (who bears a refund is not decided yet); they are listed under `needs_review`.

Row shape used below (`row`): `{ "id", "payment_reference", "booking_id", "booking_reference", "booking_type",
"original_payment_id", "payee_owner_user_id", "transaction_type", "payment_method", "provider_name", "amount", "currency",
"status", "commission_amount", "owner_net_amount", "owner_settlement_status", "created_at", "captured_at",
"owner_payable_at", "owner_paid_at", "provider_reference", "version" }` (amounts strings or null).

### F1. Admin payments screen — `GET /admin/payments`

```json
{ "items": [ "row", "…latest 200, every transaction type…" ],
  "totals": { "currency": "LKR", "collected_online": "…", "collected_cash": "…", "refunded": "…", "refunds_waiting": "…",
              "commission_earned": "…", "owner_payable": "…", "owner_paid": "…", "commission_due_from_owners": "…" } }
```

### F2. Owner settlement list — `GET /admin/owner-settlements`

```json
{ "items": [ { "owner_user_id": "…", "owner_reference": "USR-…", "owner_name": "…", "currency": "LKR",
               "payable_amount": "2625.00", "payable": [ "row" ],
               "commission_due_amount": "690.00", "commission_due": [ "row" ],
               "needs_review": [ "row" ], "settled": [ "row (latest 50)" ] } ] }
```
Owners with something payable, owed or to review; biggest payable first.

### F3. Record a payout — `POST /admin/owner-settlements/{owner_id}/payouts`

After the Admin has made the bank transfer:
```json
{ "payment_ids": ["<row id>", "…"], "bank_reference": "BOC-TRF-001", "idempotency_key": "p4y0ut123456" }
```
**201** `{ "payouts": [ "OWNER_PAYOUT row per payment (amount = owner_net_amount, provider_reference = bank_reference)" ], "total": "2625.00" }`.
The payments become `OWNER_PAID`; the Owner gets a "Payout sent" notification; audited. The same key again → **200**
with the same payouts. Error **409 `SETTLEMENT_NOT_ALLOWED`** (`field_errors` list the ids) when a payment is not
`OWNER_PAYABLE` for this Owner — already paid, cash, refunded or another Owner's.

### F4. Record commission received from an Owner — `POST /admin/owner-settlements/{owner_id}/commission-receipts`

```json
{ "payment_ids": ["<COMMISSION_DUE row id>"], "reference": "Cash deposit 12 Nov", "idempotency_key": "c0mm1ss10n12" }
```
**200** `{ "payments": [ "row now COMMISSION_PAID" ], "total": "<commission>" }`. Repeating it → 200 unchanged.
409 `SETTLEMENT_NOT_ALLOWED` for rows that are not `COMMISSION_DUE` for this Owner.

### F5. Owner's own view — `GET /owners/me/settlements`

Owner only. Same object as one F2 item, for the caller: what Travelly owes them (`payable_amount`, `payable`), what they
owe Travelly (`commission_due_amount`, `commission_due`), items waiting for Admin review, and recent settled rows.
Suits the Owner's Finance page.

All F endpoints except F5 are Admin only (403 otherwise).

## C. Server-only (no UI)

`POST /payments/webhooks/sandbox` — JSON, signed with `x-travelly-signature` (HMAC-SHA256 of the raw body).

`POST /payments/webhooks/payhere` — PayHere's `application/x-www-form-urlencoded` notice. Accepted only when
`merchant_id` is ours and `md5sig` = UPPER(MD5(merchant_id + order_id + payhere_amount + payhere_currency + status_code +
UPPER(MD5(merchant_secret)))). `status_code` 2 → PAID; −1 → FAILED `PAYHERE_CANCELLED`; −2 → FAILED `PAYHERE_FAILED`;
0 (pending) and −3 (chargeback) change nothing yet. The method PayHere reports becomes `payment_method`
(cards → `CARD`, HelaPay/Vishwa → `BANK`, wallets → `MOBILE`).

Both: 401 `INVALID_SIGNATURE`; retries are idempotent. If real money arrives after a hold ended, the payment is recorded PAID
with `failure_code: "SEATS_RELEASED_REFUND_DUE"` and no seat is given (refunds are a later slice).

## Not in this slice

Payout of partly refunded
payments (needs the decision who bears a refund)
(OWNER_PAID), PayHere live mode (needs business registration, bank account and live credentials — configuration only).

## Server setup for PayHere (project owner, once)

`Backend/.env` (see `.env.example`): `PAYHERE_MERCHANT_ID`, `PAYHERE_MERCHANT_SECRET`, `PAYHERE_MODE=sandbox`,
`PUBLIC_API_URL=https://<your ngrok domain>`. PayHere cannot reach localhost, so run ngrok to port 8000 and register that
domain in PayHere > Integrations > Add Domain/App. Restart the backend; PayHere then appears in the Admin dropdown.
For automatic refunds also add `PAYHERE_APP_ID` and `PAYHERE_APP_SECRET` (E6). For **live** mode PayHere must first
whitelist the server's IP address: email support@payhere.lk.

## Translations

The backend adds no new UI strings for this slice. The UI branch owns the labels for these screens in `messages.js`.
