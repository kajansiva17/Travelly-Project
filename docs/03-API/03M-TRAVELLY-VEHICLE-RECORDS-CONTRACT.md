# Travelly — Vehicle records and maintenance API (PRD matrix 71–73)

Status: built and tested on `claude-work` (12 Nov 2026), backend suite 428 passed. For the Owner's vehicle
**Maintenance** tab (owner decision 11 Nov: the odometer on the vehicle form goes stale, so maintenance and odometer
live in their own tab). Stored only in the PRD table `vehicle_records`; no new table. Base `/api/v1`, Bearer token,
JSON. Errors: `{ "code", "message", "field_errors": [ { "field", "message" } ], "trace_id" }`.

Who: the vehicle's **Owner** reads and adds. The vehicle's preferred Driver can read (Driver entries wait for the
PRD's Driver-entry review rules). Anyone else gets 404 `VEHICLE_NOT_FOUND`. Records are **never edited or deleted**; a
correction is a new record (PRD 9.1 audit trail). Receipts are not accepted yet (private media storage pending).
Availability blocks are **not** made here — they stay on the calendar endpoints.

## Record types

| `record_type` | Shown as | Extra fields allowed | Required |
|---|---|---|---|
| `OIL_CHANGE`, `OIL_FILTER_CHANGE` | Oil / oil filter (not for BEV) | odometer_km, amount, next_due_odometer_km, genuine_calendar_due_date, service_provider, notes | — |
| `TYRE_CHANGE`, `TYRE_ROTATION`, `WHEEL_ALIGNMENT`, `WHEEL_BALANCING`, `GENERAL_SERVICE`, `BRAKE_SERVICE`, `BATTERY_SERVICE` | Tyres / alignment / balancing / service / brakes / battery | same as above | — |
| `REPAIR` | Repair | odometer_km, amount, service_provider, notes | — |
| `FUEL_PURCHASE` | Fuel (not for BEV) | odometer_km, amount, quantity (litres), unit `"L"`, fuel_type `PETROL`/`DIESEL`, fuel_grade_product, service_provider, notes | fuel_grade_product, quantity, amount |
| `EV_CHARGING` | Charging (BEV, PHEV only) | odometer_km, amount, charging_kwh, service_provider, notes | amount |
| `ODOMETER_UPDATE` | Odometer reading | odometer_km, notes | odometer_km |
| `PERSONAL_EXTRA_USE` | Personal / off-platform use | start_odometer_km, end_odometer_km, notes | both, end ≥ start |

Fields not in the row's list are refused (422 `FIELD_NOT_APPLICABLE`), so show only the fields of the chosen type.
`GET …/records` returns `allowed_record_types` for that vehicle's power type — build the type picker from it.

## 1. List — `GET /vehicles/{vehicle_id}/records`

```json
{ "vehicle_id": "…", "power_type": "ICE", "engine_fuel_type": "PETROL",
  "current_odometer_km": "50000.0", "odometer_updated_at": "2026-11-11T04:00:00+00:00",
  "allowed_record_types": ["OIL_CHANGE", "OIL_FILTER_CHANGE", "TYRE_CHANGE", "…", "REPAIR", "FUEL_PURCHASE", "ODOMETER_UPDATE", "PERSONAL_EXTRA_USE"],
  "can_add": true,
  "totals": { "currency": "LKR", "fuel": "6000.00", "charging": "0.00", "maintenance": "8500.00" },
  "items": [ { "id": "…", "vehicle_id": "…", "trip_id": null, "record_type": "OIL_CHANGE",
               "recorded_at": "2026-11-11T04:00:00+00:00", "odometer_km": "50000.0", "start_odometer_km": null,
               "end_odometer_km": null, "amount": "8500.00", "currency": "LKR", "quantity": null, "unit": null,
               "fuel_type": null, "fuel_grade_product": null, "charging_kwh": null, "next_due_odometer_km": "55000.0",
               "genuine_calendar_due_date": "2027-05-10", "service_provider": "Lanka Auto Care", "notes": null,
               "review_status": null, "recorded_by_user_id": "…", "created_at": "…" } ] }
```
Newest first, latest 200. `review_status: "NEEDS_REVIEW"` marks a reading that was lower than the vehicle's newer reading
(show a small warning). `can_add` is true only for the Owner.

## 2. Add — `POST /vehicles/{vehicle_id}/records`

```json
{ "record_type": "OIL_CHANGE", "recorded_at": "2026-11-12T09:30:00+05:30", "odometer_km": "50000.0",
  "amount": "8500.00", "next_due_odometer_km": "55000.0", "genuine_calendar_due_date": "2027-05-10",
  "service_provider": "Lanka Auto Care", "notes": "Synthetic 5W-30" }
```
```json
{ "record_type": "FUEL_PURCHASE", "recorded_at": "2026-11-12T08:10:00+05:30", "odometer_km": "50120.0",
  "amount": "6000.00", "quantity": "15.500", "fuel_grade_product": "Octane 92" }
```
- `recorded_at` needs a time zone and cannot be in the future. Numbers may be strings or numbers: km 1 decimal,
  money 2, litres/kWh 3. Amounts are LKR (`currency` may be omitted).
- Fuel: `fuel_type` defaults to the vehicle's engine fuel; a different one is refused. `unit` is always litres.
- `next_due_odometer_km` must be above `odometer_km`; `genuine_calendar_due_date` must be after the record date.
- `confirm_duplicate: true` saves a record that looks like one already saved that day (same type, amount, reading).

**201** = the item (as in the list) plus `odometer_status`:

| `odometer_status` | Meaning |
|---|---|
| `APPLIED` | the vehicle's current odometer moved up to this reading |
| `UNCHANGED` | same as the current reading |
| `HISTORICAL` | an older entry being filled in; the vehicle keeps its newer reading |
| `NEEDS_REVIEW` | newer but **lower** than the vehicle's reading — saved, flagged, the odometer did not change (meter change or typing mistake) |
| `NO_READING` | the record has no reading |

Errors: 422 `RECORD_NOT_COMPATIBLE` (type or fuel does not fit the vehicle's power/fuel), 422 `FIELD_NOT_APPLICABLE`,
422 `VALIDATION_ERROR` (missing required field, future time, next-due not ahead…; `field_errors[0].field` names it),
409 `POSSIBLE_DUPLICATE`, 404 `VEHICLE_NOT_FOUND` (not your vehicle).

## 3. Maintenance summary — `GET /vehicles/{vehicle_id}/maintenance-summary`

```json
{ "vehicle_id": "…", "power_type": "ICE", "current_odometer_km": "50000.0", "odometer_updated_at": "…",
  "average_daily_km": "100.0",
  "data_period": { "from": "…", "to": "…", "days": 30, "readings": 3 },
  "estimate_note": null,
  "items": [ { "task": "OIL_CHANGE", "last_done_at": "…", "last_odometer_km": "49000.0", "next_due_odometer_km": "50500.0",
               "remaining_km": "500.0", "estimated_due_date": "2026-11-17", "estimate_note": null,
               "genuine_calendar_due_date": null, "days_to_calendar_due": null, "due_by": "DISTANCE", "status": "UPCOMING" },
             { "task": "WHEEL_ALIGNMENT", "status": "NOT_RECORDED", "…": null } ] }
```
PRD 4.16 formula: `remaining_km = next_due_odometer_km − current odometer`; `average_daily_km` = distance covered by
accepted readings (records and trip start/finish readings) in the last 30 days ÷ days covered;
`estimated_due_date = today + ceil(remaining_km ÷ average_daily_km)`. With fewer than two readings or no movement:
`average_daily_km: null`, `estimate_note: "Estimated date unavailable: …"` (per item `estimate_note: "Estimated date unavailable"`).

`status`: `OVERDUE` (km or calendar limit passed), `DUE` (reached today), `UPCOMING`, `NO_LIMIT_SET` (done but no next
km/date given), `NOT_RECORDED`. `due_by`: which limit comes first, `DISTANCE` or `DATE` — the earlier one decides.
Items are sorted overdue → due → upcoming → no limit → not recorded. BEV vehicles have no oil tasks.

Screen idea: top line "Current odometer 50,000 km · updated 11 Nov"; a list of tasks with remaining km / due date /
status chip; "Add record" opens a two-step form (step 1: type, date, odometer; step 2: amount, provider, next due),
no scrolling (owner rule). Show "Estimated date unavailable" when the API says so.

## Also changed

Finishing a trip (`POST /trips/{id}/complete`, private hire and departures) now moves the vehicle's odometer forward
to the closing reading (PRD: trip finish updates the odometer). The vehicle form's `current_odometer_km` stays as an
optional starting value.

Not built yet: `MAINTENANCE_DUE` reminder notifications (need a scheduled job), receipts, Driver entries, Owner
reports/exports.
