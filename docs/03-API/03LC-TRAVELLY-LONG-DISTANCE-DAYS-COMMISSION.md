# 03LC. Long-distance commission by service days

Owner decision, 14 November 2026. Not in the original PRD; add to the PRD when it is next revised.

## Rule
- A Long-distance service may have **two** commission percentages: the normal `commission_percent` (a one-service-day booking) and an optional `multi_day_commission_percent` (two or more service days).
- If `multi_day_commission_percent` is not set, every booking uses `commission_percent` (the old behaviour).
- Only Long-distance services (`pricing_scope = LONG_DISTANCE`) may have the second percentage. Airport, Local, Event, Ticket and Rental keep one percentage.
- The gateway fee is unchanged: one percentage per service, paid by the Owner (Travelly rule).

## What a "service day" is
The same days the price uses: 24-hour blocks counted **from the pickup time**, not calendar dates (`itinerary.service_hours` has one entry per block).
- 8:00 to 18:00 the same day: 1 service day.
- Pickup 18:00, drive through the night, finish at 16:00 the next day (22 hours): 1 service day.
- Pickup 18:00, finish at 20:00 the next day (26 hours): 2 service days.
- The Driver sleeping over is a separate matter: it only adds the overnight charge when the stop is marked `overnight_rest`.

## When the percentage is taken
At payment time (online capture or cash confirmation), from the booking's final itinerary, exactly like the existing commission. A change by Admin applies to new payments only.

## API
`GET /admin/payment-settings` items gain:
- `multi_day_commission_percent`: string like `"5.00"`, or `null` when not set.
- `supports_multi_day_commission`: true only for a Long-distance service. The UI shows the extra box only when true.

`PATCH /admin/service-types/{id}/payment-settings` body gains optional `multi_day_commission_percent` (string, 0 to 100, at most 2 decimals). Sending the field without a value (or leaving it out) clears it.
Errors: 422 `PAYMENT_SETTINGS_INVALID` (it plus the gateway fee is over 100%), 422 `MULTI_DAY_COMMISSION_NOT_ALLOWED` (the service is not Long-distance), 422 validation (bad format).

## For the UI
In Admin, Payments, for a Long-distance service, show two boxes: "Commission (%), 1 service day" (`commission_percent`) and "Commission (%), 2 or more service days" (`multi_day_commission_percent`, optional, empty means the same as the first). Show the 50,000 example for both.
