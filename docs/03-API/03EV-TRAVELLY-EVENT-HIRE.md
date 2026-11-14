# Travelly — Event hire (14 Nov 2026)

Status: built on `claude-work`. **Owner decision** (the PRD names Event hire but gives no price rule). Event hire is a
private-hire service with `pricing_scope = EVENT`. It uses the same booking flow as Airport / Local / Long-distance
(request -> price acceptance -> Owner commits -> trip -> pay after the trip). Base `/api/v1`.

## What it is
The Owner saves **event packages** for a vehicle: a name, the **hours**, and a **fixed price** (vehicle + Driver).
One booking = one vehicle = one package. No distance, no route rates, no return leg. Hours or services beyond the
package are agreed directly with the Owner (shown as an exclusion on the price).

## Owner
`PUT /vehicles/{vehicle_id}/event-packages`
```json
{"service_type_id": "<EVENT service id>", "expected_version": 0, "enabled": true,
 "packages": [{"id": "<uuid you make>", "name": "Wedding car 6 hours", "hours": "6", "price": "25000", "notes": "Decorated car"}]}
```
- `expected_version` is the saved version (0 for the first save). `hours` > 0 and <= 24. `price` > 0, 2 decimals, strings.
- The package list is replaced as a whole (1 - 20 packages). Package `id`s are UUIDs made by the app and kept when a package is edited.
- `GET /vehicles/{id}/services` returns the packages as `event_packages` on the Event service row.
- `PUT /vehicles/{id}/services` (route rates) is refused for an Event service: `422 EVENT_PACKAGES_REQUIRED`.
- `GET /owners/me/service-readiness` lists the Event service with `missing: ["At least one complete Event package"]` until saved.
- Admin creates the Event service as before (`pricing_scope = EVENT`, then Active). `GET /service-types` now includes it.

## Passenger
1. `POST /search/vehicles` with the Event `service_type_id` and an `itinerary` (see below). Each vehicle comes back with
   `price` (its cheapest package) and `packages[]` = `{package_id, name, hours, notes, price{total,...}, reserved_end_at}`.
   Only packages that are free at that time are listed.
2. `POST /search/vehicles/{vehicle_id}/quote` and `POST /bookings/private-hires` — the same body, with
   **`itinerary.event_package_id`** set to the chosen package and **`itinerary.service_hours` = `[package hours]`**,
   `direction: "ONE_WAY"`, `method: "DAY_HIRE"` (ignored, but required by the shared schema), `stops`: pickup first and the
   event place last (both with place tokens as usual).
3. The price is the package price: `calculation.method = "EVENT_PACKAGE"`, one breakdown line, `calculation.package = {id, name, hours}`.
4. Then the normal steps: `POST /bookings/{id}/price-acceptance`, the Owner `self-drive` / `driver-assignments`, trip start/complete, payment after completion.

Errors: `422 EVENT_PACKAGE_REQUIRED` (missing / unknown package), `422 EVENT_PACKAGE_MISMATCH` (hours differ from the
package, or a return leg), `422 EVENT_PACKAGE_UNAVAILABLE` (a package id on a non-Event service).

## Fixed package
An Event booking cannot be re-quoted or changed: `POST /bookings/{id}/quote` and `POST /bookings/{id}/changes` return
`409 EVENT_FIXED_PACKAGE`. Cancel and book again.

## Where the package name and hours appear
- Booking (`GET /bookings`, `GET /bookings/{id}`, and the request / acceptance responses): **before** price acceptance `proposal.quote.calculation.package`;
  **after** acceptance `price.current.calculation.package` (`{id, name, hours}`). The hours are also `itinerary.itinerary.service_hours[0]`
  and the package id is `itinerary.itinerary.event_package_id`.
- Admin booking oversight (`GET /admin/workflow/bookings`): a new field **`event_package`** = `{id, name, hours}` (null for other bookings).
  Event bookings have `booking_type` `PRIVATE_HIRE`.

## Search before a package is chosen
`POST /search/vehicles`: `service_hours`, `direction`, `method` and `return_start_at` are **ignored for Event** (each package uses its own hours,
one way). Send any valid value, for example `["1"]`, `ONE_WAY`, `DAY_HIRE`. Only `start_at` and the stops matter (the vehicle must be free from
`start_at` for each package's hours).

## Owner "Prices" wizard
Hide the Event service in the route-rate (Prices) wizard: `PUT /vehicles/{id}/services` returns `422 EVENT_PACKAGES_REQUIRED` for it.
`GET /owners/me/service-readiness` still lists Event (`pricing_scope: "EVENT"`, `rate_rule_count` = number of packages), so use it for the
status chip and send the Owner to the Event packages tab.
