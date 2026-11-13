# Travelly — Odometer photo proof and the live trip map

Status: built on `claude-work` (13 Nov 2026, owner decisions). Base `/api/v1`, Bearer token.
Errors: `{ "code", "message", "field_errors", "trace_id" }`.

## Rules (owner decisions 13 Nov 2026)

- **At trip start and at trip finish** the operator (the Driver, or the Owner driving their own vehicle):
  1. types the odometer reading, **and**
  2. takes a **live photo** of the odometer with the in-app camera.
  - There is **no gallery upload**, so an old photo cannot be reused. Each photo needs a one-time capture code (10
    minutes, one photo), and is sent with the time and the GPS position.
- **Gemini reads the photo** and the system compares it with the typed number:

  | `result` | When | `can_continue` |
  |---|---|---|
  | `MATCH` | The photo reading is within 1 km of the typed number | yes |
  | `MISMATCH` | The photo clearly shows another number | **no**: fix the number or retake |
  | `UNREADABLE` | Dark or blurred photo | no; **after 3 unreadable tries, yes**, with the typed number, shown as "photo not readable" |
  | `NOT_CHECKED` | Gemini not available (no key, daily limit, network) | yes: the photo is still kept as proof |

- **Always checked:**
  - The start reading cannot be lower than the vehicle's last recorded odometer (`ODOMETER_BELOW_LAST`).
  - The finish reading cannot be lower than the start reading.
  - A private-hire start photo must be taken within 2 km of the pickup point (`NOT_AT_PICKUP`).
- **Start / Finish** accept only the photographed number, while the photo is under 30 minutes old
  (`409 ODOMETER_PROOF_REQUIRED`).
- **Proof:**
  - At the end, the Passenger (private hire), the Owner, the operator and the Admin see start km, end km and the
    distance, plus the two photos.
  - Ticket departures: the Owner, operator and Admin only.
- **Price is not changed by the photos.** The price stays the accepted price plus approved extras (PRD). The km and
  photos are proof.
- **Storage:**
  - Photos are private files, outside the 20 PRD tables. They are deleted **7 days after the trip ends**, or 7 days
    after a photo of a cancelled trip.
  - The readings stay forever in `trips` (start, end, distance), for maintenance, documents and reports.
- `.env`:
  - `ODOMETER_PHOTO_REQUIRED=true`
  - `ODOMETER_PHOTO_KEEP_DAYS=7`
  - `ODOMETER_PHOTO_ROOT` (default `<PRIVATE_DOCUMENT_ROOT>/../odometer-photos`)
- Daily clean-up job: `scripts/delete_old_odometer_photos.py`. Photos are also removed when someone opens them after
  the 7 days.

## 1. Open the camera — `POST /trips/{trip_id}/odometer-session`

```json
{ "stage": "START" }      // or "END"
```

```json
{ "capture_code": "…", "expires_at": "…", "stage": "START", "minimum_km": "45210.0",
  "tries_unreadable": 0, "unreadable_tries_allowed": 3, "photo_required": true }
```

- `minimum_km`: the vehicle's last odometer (START) or the start reading (END). Use it for a hint and an early check.
- Only the trip's operator can call it. START needs a READY accepted trip; END needs a running trip.
- Errors: 404 `TRIP_NOT_FOUND`, 409 `TRIP_NOT_READY`, 429.

## 2. Send the photo — `POST /trips/{trip_id}/odometer-photo` (multipart/form-data)

Fields:

| Field | Required | Notes |
|---|---|---|
| `capture_code` | yes | From section 1 |
| `stage` | yes | `START` / `END` |
| `typed_km` | yes | At most one decimal |
| `latitude`, `longitude` | yes | `navigator.geolocation` |
| `accuracy_m` | no | |
| `file` | yes | One JPEG/PNG up to 8 MiB |

**200:**

```json
{ "stage": "START", "result": "MISMATCH", "typed_km": "45230.0", "read_km": "45320.0", "can_continue": false,
  "tries_unreadable": 0, "unreadable_tries_allowed": 3,
  "message": "The photo shows a different reading. Check the number you typed, or take the photo again." }
```

- Each code takes one photo. For another try, call section 1 again.
- Errors:
  - 409 `CAPTURE_CODE_INVALID` (expired or used)
  - 422 `ODOMETER_BELOW_LAST`, `ODOMETER_BELOW_START`, `NOT_AT_PICKUP`, `INVALID_PHOTO`
  - 413 `PHOTO_TOO_LARGE`
  - 429

## 3. Start and finish (existing)

- `POST /trips/{trip_id}/start` with `start_odometer_km` = the same `typed_km`.
- `POST /trips/{trip_id}/complete` with `end_odometer_km` = the same `typed_km`.
- New errors: 409 `ODOMETER_PROOF_REQUIRED`; 422 `ODOMETER_BELOW_LAST` (start).

## 4. Proof — `GET /trips/{trip_id}/odometer-proof`

```json
{ "trip_id": "…", "status": "COMPLETED",
  "start": { "reading_km": "45230.0", "typed_km": "45230.0", "read_km": "45230.0", "result": "MATCH", "taken_at": "…",
             "photo_available": true, "photo_deleted_at": null, "photo_url": "/api/v1/trips/…/odometer-photos/START" },
  "end":   { "reading_km": "45496.0", "…": "…" },
  "distance_km": "266.0", "photos_kept_until": "…", "photos_kept_days": 7 }
```

- **The photo:** `GET` `photo_url` with the Bearer token returns `image/jpeg` (fetch as a blob, show with
  `URL.createObjectURL`).
- **After 7 days:** `photo_available: false` and `photo_url: null`. The numbers stay.
- **Who can see it:**
  - the trip's operator, operating Owner and Admin;
  - the Passenger of a private hire.
  - Anyone else gets 404.

## 5. Trip map data — `GET /trips/{trip_id}/map`

```json
{ "trip_id": "…", "status": "IN_PROGRESS",
  "points": [ { "label": "Kandy", "latitude": "7.2906", "longitude": "80.6337", "kind": "START" },
              { "label": "Colombo Fort", "latitude": "6.9344", "longitude": "79.8428", "kind": "END" } ],
  "line": [[80.6337, 7.2906], "… [lng, lat] …"],
  "position": { "latitude": "…", "longitude": "…", "updated_at": "…" } }
```

- `line` follows the roads (route service, cached 12 h). When it is `null`, draw straight lines between `points`.
- Ticket departures list their route stops as `STOP` points.
- Same people as `GET /trips/{id}`.

## Screens (UI Claude)

### A. Start trip (Driver / "My driving")

Pressing **Start trip** opens an **odometer step** before anything else:

1. **"Odometer reading" box:** numbers only, one decimal. It shows "Last recorded: `minimum_km` km" under it.
2. **"Take photo" button:**
   - Opens the **in-app camera**: `getUserMedia({ video: { facingMode: 'environment' } })` with a live preview and a
     capture button.
   - Draw the frame to a canvas and send it as JPEG.
   - **No file picker and no `<input type=file>`**, so gallery photos cannot be chosen.
   - Ask for location at the same time (`navigator.geolocation.getCurrentPosition`, high accuracy).
3. **Send:** call section 1, then section 2. Show the result:
   - `MATCH`: green "Photo matches ✓"; **Start trip** becomes active.
   - `MISMATCH`: red, showing both numbers ("Photo: 45,320 • You typed: 45,230"), with **Retake** and **Edit number**.
     Start stays disabled.
   - `UNREADABLE`: "Couldn't read the photo (try 1 of 3). Move closer, turn on the light." with **Retake**. After the
     3rd try, show "Start with the typed number" (orange) and enable Start.
   - `NOT_CHECKED`: "Photo saved as proof". Start is enabled.
4. **Start trip:** posts the existing start with the same number. Then **open the live trip map straight away**.
5. Error texts:
   - `NOT_AT_PICKUP`: "Take the start photo at the pickup point."
   - `ODOMETER_BELOW_LAST`: the message as given.
   - `CAPTURE_CODE_INVALID`: open the camera again.

### B. Finish trip

The same odometer step with `stage: "END"`, then the existing complete call. Afterwards show the **trip summary**:
start km → end km = distance, with **"See proof"**.

### C. Live trip map: opens by itself when the trip starts

- **Map:** full screen. Use Leaflet with OpenStreetMap tiles (free, no key).
  - Markers for `points` (START green, END red, STOP grey) and the road `line`.
  - The vehicle's position, from the existing location updates (send every 15–30 s while running).
  - Fit the map to the route; a "Follow me" toggle.
- **Side buttons** (this is the only place they appear):
  - the **road alert** button (5 types),
  - the **mic** (voice alert with the 10 s confirmation, 03A),
  - **speaker on/off**,
  - **problem on the road** (existing breakdown),
  - **Finish trip** (B).
- Alert markers from `GET /road-alerts?trip_id=` (poll 30–60 s), with "Still there / Not there" for Drivers (03A).
- **Screen Wake Lock** while the map is open and the trip runs (03A).
- **Passengers** open the same map (read-only, without report buttons) from their booking: route, vehicle position,
  alerts, and speaker on/off.

### D. No alert buttons on dashboards

- The Driver and Owner dashboards show **no** road alert buttons. They only appear on the live trip map (C).
- **Notifications stay in the app:** the bell list (`GET /notifications`, 03N) keeps road alerts and every other
  notice, so someone who opens the app later still sees them.
  - Show a `ROAD_ALERT` whose `expires_at` has passed as "Expired", greyed.

### E. Proof view (Passenger booking, Owner booking, Admin)

- **"Trip distance" card:** start km, end km, distance.
  - A result badge per photo: Match ✓ / Not readable / Not checked.
  - Two thumbnails from `photo_url` (blob fetch). Tap to enlarge.
- **After 7 days:** "Photos are kept for 7 days after the trip" with the numbers only.
- New UI strings go in `messages.trips.js`.

## Trips running now — `GET /trips/active` (13 Nov 2026)

For the dashboard **"Trip in progress"** card. Bearer token, any signed-in person (Passenger, Owner, Driver workspaces).
Returns the caller's trips with status `IN_PROGRESS` (newest first, at most 20):

```json
{ "items": [ { "trip_id": "…", "kind": "PRIVATE_HIRE", "viewer_roles": ["DRIVER", "OWNER"],
               "booking_id": "…", "scheduled_trip_id": null, "origin": "Kandy", "destination": "Colombo Fort",
               "vehicle": "WP CAB-1234", "actual_start_at": "2026-11-13T08:02:00+00:00",
               "start_odometer_km": "45120.0", "tracking_status": "ACTIVE" } ] }
```

- `kind`: `PRIVATE_HIRE` or `TICKET` (a published departure).
- `viewer_roles`: `DRIVER` = drives it, `OWNER` = operates it, `PASSENGER` = booked it / holds a seat.
- Empty `items` = no card. Tap the card → open the live map screen for `trip_id` and load `GET /trips/{id}/map`.
- The trip stays `IN_PROGRESS` on the server while the person goes back or to the dashboard. Poll this list when the
  dashboard opens (and about every 30 s while it is open).
