# Travelly — Payments API contract (Ticket seats + private hire, Sandbox and PayHere)

Status: **built and tested** on `claude-work` (11 Nov 2026). Backend suite 401 passed. This is the contract the UI
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

Refunds (waiting for the
cancellation-band decision CF08–09; PayHere Refund API needs an API key), Admin payments list, Owner payout marking
(OWNER_PAID), PayHere live mode (needs business registration, bank account and live credentials — configuration only).

## Server setup for PayHere (project owner, once)

`Backend/.env` (see `.env.example`): `PAYHERE_MERCHANT_ID`, `PAYHERE_MERCHANT_SECRET`, `PAYHERE_MODE=sandbox`,
`PUBLIC_API_URL=https://<your ngrok domain>`. PayHere cannot reach localhost, so run ngrok to port 8000 and register that
domain in PayHere > Integrations > Add Domain/App. Restart the backend; PayHere then appears in the Admin dropdown.

## Translations

The backend adds no new UI strings for this slice. The UI branch owns the labels for these screens in `messages.js`.
