# Travelly — extra charge choices on rate rules (14 Nov 2026)

Status: built on `claude-work`. **Owner decision** (not in the PRD). Applies to the Owner route rates (`PUT /vehicles/{id}/services`):
Airport, Local and Long-distance (fixed route, km-wise and day hire).

## The choice
For each extra charge the Owner picks one of three, in a new optional rule field **`extra_policy`**:
```json
"extra_policy": {"WAITING": "NOT_OFFERED", "EXTRA_KM": "CHARGED", "EXTRA_HOURS": "FREE", "OVERNIGHT": "CHARGED"}
```
| Mode | Meaning | Rate fields |
|---|---|---|
| `NOT_OFFERED` | The Owner does not do this on this rate. A journey that needs it is not priced: the Passenger gets "ask the Owner for a price" (03SQ). | must be `"0"` |
| `FREE` | No extra charge, ever, for this extra. | must be `"0"` |
| `CHARGED` (default; also when the key is missing) | The usual rates apply. Show the rate form. | filled in as today |

| Key | Used by methods | Rate fields it controls |
|---|---|---|
| `WAITING` | DISTANCE, DAY_HIRE, FIXED_ROUTE | `free_wait_minutes`, `waiting_hour_rate` |
| `EXTRA_KM` | DISTANCE, DAY_HIRE | `extra_km_rate` |
| `EXTRA_HOURS` | DAY_HIRE | `extra_hour_rate` (hours beyond the daily package) |
| `OVERNIGHT` | DAY_HIRE | `overnight_driver_cost` |

Rules: a key the method does not use is refused (`422`); with `NOT_OFFERED` / `FREE` the rate fields above must be `"0"`
(the existing required fields stay required, send `"0"`). Older saved rules have no `extra_policy` and behave as `CHARGED`.

## What the Passenger sees before booking
Every price (`calculation`, in search, quote and booking) now has **`extra_policies`**: one entry per extra the rate method uses:
`{code, mode}` plus, only when `mode` is `CHARGED`: `WAITING` -> `free_minutes`, `hour_rate`; `EXTRA_KM` -> `km_rate`;
`EXTRA_HOURS` -> `hour_rate`; `OVERNIGHT` -> `cost`. Show "Not available", "No extra charge" or the rate. The Owner cannot add
a charge later for an extra marked `FREE` or `NOT_OFFERED`.

## NOT_OFFERED in a search
If the Passenger's journey uses a `NOT_OFFERED` extra (for example waiting minutes > 0 when waiting is not offered, more km than the
included km, hours beyond the daily package, overnight stays), that rate does not price it: the vehicle appears in `quote_on_request`.
The Owner's quote for that journey is a route rate of its own, where the extra can be `CHARGED`.

## Not covered (stay as they are)
- **Event packages:** the price is fixed; extra hours are agreed directly and shown as an exclusion.
- **Rental:** `late_hour_rate` and `extra_km_rate` are required numbers; `0` means no charge. The extras list is the Owner's optional paid add-ons.
