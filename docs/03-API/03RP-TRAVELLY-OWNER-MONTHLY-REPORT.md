# Travelly — Monthly Owner report (PDF)

Status: built on `claude-work` (13 Nov 2026). This is an owner decision; the PRD has no report. It is read-only and
nothing is stored.
- **Install once:** `reportlab` (added to `requirements.txt`). Run
  `.venv\Scripts\pip.exe install -r Backend\requirements.txt`.
- Base `/api/v1`, Bearer token, **approved OWNER** only. Each Owner sees only their own vehicles, trips and money.

## Owner decisions (13 Nov 2026)
- **For:** Owners.
- **Language:** English.
- **Delivery:** a "Download PDF" button for any month. There is no email.
- **Contents:** one calendar month (Sri Lanka time):
  1. **Trips and km:** trips the Owner operated that **finished** in the month. Per vehicle (trips, km), then each
     trip: date, reference, private hire or ticket, route, vehicle, driver, start km, end km, km. The readings are
     the ones entered with the odometer photo proof (03O).
  2. **Earnings:**
     - The Owner's share rows captured in the month: amount, commission, refunded, Owner net, settlement status.
       A partial refund pays pro rata (03P F).
     - Payouts Travelly paid in the month.
     - **Today's** open balance: payable to the Owner, commission due from the Owner (cash trips), and payments
       waiting for a refund.
  3. **Maintenance:**
     - Service, repair, fuel and charging records of the month, with the spend.
     - The next due items **as of today** (the PRD 4.16 summary: overdue, due, upcoming).
  4. **Documents (as of today):** the Owner's and the vehicles' documents, with expiry state: Expired, "Expires in N
     days" (30-day window), Valid, Needs correction or Rejected. Document numbers are masked (••••1234).
  5. **Month result** (owner request 13 Nov 2026): **income − expenses = profit (or loss)**.
     - Income = the Owner's share of the month's trips, after commission and refunds.
     - Expenses = the month's service/repair plus fuel/charging records entered in Travelly.
     - Costs not recorded in Travelly (driver pay, loans, insurance premiums) are not included, and the PDF says so.
- **Look:** Travelly branding: the website logo (`Backend/app/assets/travelly-logo.png`), navy `#002155` and red
  section bars, navy table headers, and summary tiles with the profit tile in green (red for a loss).
- The report says plainly that the **price** follows the accepted booking and approved extras. Odometer km is a
  record, not a charge.

## 1. Preview — `GET /owners/me/reports/monthly/{YYYY-MM}`

```json
{ "owner": { "name": "Maya Fernando", "reference": "TRV-…" }, "period": "2026-11", "period_label": "November 2026",
  "generated_at": "2026-11-13T10:15+05:30", "currency": "LKR",
  "summary": { "vehicles": 2, "completed_trips": 11, "total_km": "1276.0", "gross_collected": "185400.00", "commission": "18540.00",
               "refunded": "4500.00", "owner_net": "162360.00", "payouts_received": "120000.00",
               "maintenance_spend": "23500.00", "fuel_and_charging_spend": "41200.00", "documents_needing_attention": 2,
               "expenses_total": "64700.00", "profit": "97660.00" },
  "trips": { "per_vehicle": [ { "vehicle": "WP CAB-1234 (Toyota HiAce)", "trips": 6, "km": "696.0" } ],
             "items": [ { "date": "2026-11-01", "reference": "HIR-…", "kind": "Private hire", "route": "Kandy → Colombo Fort",
                          "vehicle": "WP CAB-1234", "driver": "Anushka Perera", "start_km": "45120.0", "end_km": "45236.0", "distance_km": "116.0" } ] },
  "earnings": { "items": [ { "date": "…", "booking": "…", "method": "Card", "type": "Payment", "amount": "16850.00",
                             "commission": "1685.00", "refunded": "0.00", "owner_net": "15165.00", "status": "Owner Paid" } ],
                "payouts": [ { "date": "…", "reference": "…", "method": "Bank Transfer", "amount": "120000.00" } ],
                "open_balance_today": { "payable_to_you": "42360.00", "commission_due_from_you": "3370.00", "waiting_for_refunds": 1 } },
  "maintenance": { "items": [ { "date": "…", "vehicle": "…", "type": "Oil Change", "odometer_km": "45210.0", "amount": "12500.00",
                                "provider": "…", "notes": "…" } ],
                   "coming_up_today": [ { "vehicle": "…", "task": "Wheel Alignment", "status": "Due", "due": "2026-11-15", "remaining_km": "-20.0" } ] },
  "documents": { "items": [ { "document": "Insurance", "for": "WP CAB-1234", "number": "••••4821", "expiry_date": "2026-11-30",
                              "status": "Approved", "state": "Expires in 17 days" } ] },
  "result": { "income": "162360.00", "expenses_service_and_repair": "23500.00", "expenses_fuel_and_charging": "41200.00",
              "expenses_total": "64700.00", "profit": "97660.00", "is_loss": false, "note": "Income is your share of trips…" } }
```

- Errors: 403 `ROLE_NOT_APPROVED`; 422 for a bad month (`YYYY-MM`, from 2020 up to this month); 429 (30 per 10
  minutes).
- An empty month still works, with zeros and "Nothing in this month".

## 2. Download — `GET /owners/me/reports/monthly/{YYYY-MM}/pdf`

- Returns `application/pdf` with `Content-Disposition: attachment; filename="travelly-report-2026-11.pdf"`.
- A4 pages, in English, in the Travelly red. Layout:
  1. A summary tile row.
  2. Four sections with tables.
  3. Page numbers and the Owner's name in the footer.

## Screen (UI Claude)

**Owner workspace → "Reports"** (or a card in Settlements/Overview):

- **Month picker:** defaults to the previous month (a finished month). It cannot go past this month.
- **Preview:** shows section 1 as summary tiles and short tables (trips, earnings, maintenance, documents).
  End with a clear **Month result card**: income, expenses, then profit (green) or loss (red), from `result`.
- **"Download PDF":**
  - Fetch section 2 with the Bearer token as a blob, then save it with
    `URL.createObjectURL` + `<a download="travelly-report-YYYY-MM.pdf">`.
  - A plain link will not work, because the token is not sent.
- Strings go in `messages.trips.js`.

---

# Monthly Admin report (same look)

Built 13 Nov 2026 (owner decision). This is an approved **ADMIN** only report covering the whole platform. It is
read-only, nothing is stored, and the PDF says "Confidential".

## Contents (one calendar month, Sri Lanka time)
1. **Summary:** private hire and ticket bookings made, bookings cancelled, trips completed, km, new users, vehicles
   published (today).
2. **Money:**
   - Per service: payments, collected, Travelly commission, Owners' share, refunded.
   - Online vs cash collected, refunds paid, payouts to Owners.
   - **Today's** open balance: owed to Owners, commission due from Owners, refunds waiting.
3. **People:** Owner and Driver applications approved and rejected this month, waiting now, suspended now; the list of
   approvals.
4. **Needs attention (as of today):**
   - departures in DECISION_REQUIRED / DISRUPTED;
   - refunds waiting or failed, with a plain reason (PayHere refused / not a card, refund by bank / no answer from
     PayHere);
   - documents expired or expiring within 30 days;
   - the oldest applications waiting.
5. **Month result:**
   - Travelly income = commission on online payments + commission on cash trips.
   - "Of which still to collect from Owners" is shown separately.
   - Gateway fees and running costs are not recorded, and the report says so.

## Endpoints
- `GET /admin/reports/monthly/{YYYY-MM}` returns JSON with `summary`, `money`, `people`, `attention` and `result`.
- `GET /admin/reports/monthly/{YYYY-MM}/pdf` returns `travelly-admin-report-YYYY-MM.pdf`.
- Errors: 403 for non-Admins; 422 for a bad month; 429 (30 per 10 minutes).

## Screen (UI Claude)
**Admin → "Reports":**
- A month picker (default: the previous month).
- Summary tiles: bookings, trips, km, new users, collected, **Travelly income** (green), paid to Owners, needs
  attention (red when above 0).
- **Needs attention:** short lists with links to the matching Admin screens (Attention, Refunds, Documents,
  Applications).
- **Download PDF:** fetch with the Bearer token as a blob, the same way as the Owner report.
- Mobile: tiles in 2 columns, tables as cards.


## Admin report: JSON field names (stable; UI may rely on them)
`GET /admin/reports/monthly/{YYYY-MM}` -> `period`, `period_label`, `generated_at`, `currency`, then:
- `summary`: `private_hire_bookings` (Event hire is counted here), `ticket_bookings`, `rental_bookings`, `cancelled_bookings`, `completed_trips`, `total_km`, `new_users`,
  `published_vehicles_today`, `collected_online`, `collected_cash`, `collected_total`, `travelly_commission`, `refunds_paid`, `payouts_paid`, `payouts_count`, `needs_attention`.
- `money.per_service[]`: `service`, `payments`, `collected`, `commission`, `owner_share`, `refunded`.
  `money.open_balance_today`: `owed_to_owners`, `commission_due_from_owners`, `refunds_waiting`, `refunds_waiting_amount`.
- `people.roles[]`: `role`, `approved`, `rejected`, `waiting_now`, `suspended_now`. `people.approved[]`: `date`, `name`, `reference`, `role`.
- `attention.departures[]`: `reference`, `route`, `departs`, `status`. `attention.refunds[]`: `booking`, `amount`, `method`, `status`, `problem`, `since`.
  `attention.documents[]`: `document`, `holder`, `vehicle`, `number` (masked), `expiry_date`, `state`. `attention.applications[]`: `name`, `reference`, `role`, `waiting_days`.
- `result`: `commission_online`, `commission_cash`, `income`, `cash_commission_still_due`, `note`.
Money values are strings with 2 decimals (LKR). Text values such as `status`, `method`, `state`, `problem`, `note` are **English display text**, not codes;
show them as they are (Admin report, same as the English PDF). Months and "today" use Sri Lanka time (Asia/Colombo); a month after the current Sri Lanka month is refused.
