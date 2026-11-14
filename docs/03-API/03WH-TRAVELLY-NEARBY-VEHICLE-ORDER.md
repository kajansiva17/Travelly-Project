# Travelly — search orders vehicles by where they are (14 Nov 2026)

Status: built on `claude-work` (v86). **Owner decision** (not in the PRD). No GPS and nothing for the Owner or Driver to fill in.
Applies to `POST /search/vehicles` for Airport, Local, Long-distance (and Event) search results.

## Where a vehicle is taken to be
1. `LAST_TRIP`: the last stop of the vehicle's most recent **completed** private-hire / event trip, if it ended in the last 7 days.
   A vehicle that finished Jaffna -> Colombo is in Colombo.
2. `SERVICE_AREA`: otherwise the centre of the pickup area of the Owner's saved rate (for that service) nearest to the pickup.
3. unknown: `distance_km` and `location_source` are `null` (a new vehicle with no trip and no saved rate, or an Event search before any trip).

## What search returns
Both `items` and `quote_on_request` entries now have:
- `distance_km`: straight-line distance from that place to the pickup, 1 decimal (approximate, not a road distance), or `null`.
- `location_source`: `LAST_TRIP`, `SERVICE_AREA` or `null`.
- `near`: `true` when `distance_km` is 50 km or less.

Each list is ordered **nearest first, unknown last**. Nothing is hidden for being far: show far vehicles lower, for example under a
"Farther away" heading when `near` is `false`, and `distance_km` as "about N km away".

## Not yet
A vehicle's planned next trip, an Owner/Driver "I am here, going there" note, and a pickup-travel charge are not built.
