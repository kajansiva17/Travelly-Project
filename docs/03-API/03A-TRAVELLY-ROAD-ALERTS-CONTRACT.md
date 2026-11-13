# Travelly — Road alerts (PRD matrix 86–89)

Status: built on `claude-work` (12 Nov 2026). Migration **`0011_road_alerts`** creates the PRD `road_alerts` table
(data dictionary table 20), exactly as specified; migrated tables are now 18 of 20. Base `/api/v1`, Bearer token, JSON.
Errors: `{ "code", "message", "field_errors", "trace_id" }`.

## Rules (PRD + owner decisions 12 Nov 2026)

- **Who reports:** only the **assigned Driver of a running trip** (IN_PROGRESS / BREAKDOWN / ASSISTANCE_REQUIRED).
  - A self-driving Owner is that Driver, because driving needs the approved DRIVER role.
  - Passengers and Owner-only people cannot report.
- **Where:** the point must be within 3 km of the trip's live position, when that position is under 30 minutes old.
- **Types and how long they stay up:**

  | Type | Minutes |
  |---|---|
  | `POLICE_PRESENCE` | 60 |
  | `SPEED_CHECK` | 60 |
  | `ACCIDENT` | 120 |
  | `ROAD_HAZARD` | 120 |
  | `ROADBLOCK` | 180 |

  Change them with `.env` `ROAD_ALERT_MINUTES_<TYPE>`. There is no Admin screen for these: the PRD has no settings
  table.
- **Who sees it:** people on a running trip whose live position is within **15 km** (`ROAD_ALERT_RADIUS_KM`): that
  trip's Driver, operating Owner and Passengers.
- **Status:**
  - New alerts are `UNCONFIRMED`.
  - Nearby Drivers answer "still there" or "not there":
    - 1 confirmation → `ACTIVE`; 3 → `VERIFIED`. Each confirmation also extends the expiry.
    - 2 denials → `REJECTED`.
  - Each Driver answers once.
  - The Admin can `VERIFY`, `REJECT` or `REMOVE`.
  - Expired alerts become `EXPIRED`.
- **No duplicates:** the same type within 300 m of a live alert is not a new alert. From another Driver it counts
  as their confirmation.
- **Voice (PRD: voice never creates an alert by itself):**
  1. What the Driver says (Tamil, Sinhala or English) is classified by `voice-classify`. Nothing is stored.
  2. The app asks "Send a Police alert?".
  3. Only after the Driver confirms (a tap, or saying yes / ஆம் / ඔව්) does the app post the alert with
     `source_input: "VOICE"` and `driver_confirmed: true`.
  4. **The app listens 10 seconds for the answer (owner decision 12 Nov 2026). No answer = not sent.** Change it with
     `.env` `ROAD_ALERT_CONFIRM_SECONDS` (3–30).
- **Language:** listeners never hear the reporter's words. Each person gets a fixed sentence for the alert type in
  **their own `preferred_language`** (en/ta/si), so a Tamil report reaches a Sinhala driver in Sinhala.

## 1. Report — `POST /road-alerts`

```json
{ "trip_id": "…", "alert_type": "POLICE_PRESENCE", "latitude": "6.927079", "longitude": "79.861244",
  "travel_direction_degrees": "135.5", "source_input": "BUTTON" }
{ "trip_id": "…", "alert_type": "POLICE_PRESENCE", "latitude": "…", "longitude": "…",
  "source_input": "VOICE", "confidence_score": "0.92", "driver_confirmed": true, "description": "what was heard (optional)" }
```

**201** = the alert (section 3 item) plus `merged: false` and `notified` (how many people were told).
**200** with `merged: true`, `counted_as_confirmation` = the same alert was already up at that place.

Errors:
- 403 `ROLE_NOT_APPROVED`: not a Driver.
- 404 `TRIP_NOT_FOUND`: not your trip.
- 409 `TRIP_NOT_ACTIVE`.
- 422 `ALERT_TOO_FAR`.
- 422 `DRIVER_CONFIRMATION_REQUIRED`: voice without confirmation.
- 429: at most 10 reports in 10 minutes.

## 2. Voice — `POST /road-alerts/voice-classify`

```json
{ "transcript": "முன்னால போலீஸ் நிக்குது", "language": "ta" }
```
```json
{ "alert_type": "POLICE_PRESENCE", "confidence": 1.0, "candidates": [ { "alert_type": "POLICE_PRESENCE", "name": "போலீஸ்" } ],
  "confirm_prompt": "போலீஸ் எச்சரிக்கை அனுப்பவா?", "message": null }
```
- Understood replies also carry what the app needs for the spoken confirmation:

```json
{ "confirm_seconds": 10, "yes_words": ["ஆம்", "ஆமா", "சரி", "aam", "sari", "yes", "…"],
  "no_words": ["இல்லை", "வேண்டாம்", "illa", "venaam", "no", "…"],
  "sent_text": "எச்சரிக்கை அனுப்பப்பட்டது.", "not_sent_text": "எச்சரிக்கை அனுப்பப்படவில்லை." }
```
- Not understood: `alert_type: null`, `message: "Not understood. Choose the alert with a button."`.
- "police speed check" → `SPEED_CHECK` first, `POLICE_PRESENCE` second.
- Drivers only, 30 per 10 minutes.

## 3. Nearby alerts — `GET /road-alerts?trip_id=…`

For that trip's Driver, operating Owner or Passengers. The centre is the trip's live position. Poll every 30–60 s
while the trip runs.

```json
{ "trip_id": "…", "radius_km": 15, "note": null, "items": [
  { "id": "…", "alert_type": "POLICE_PRESENCE", "status": "ACTIVE", "version": 2, "latitude": "6.927079", "longitude": "79.861244",
    "travel_direction_degrees": null, "source_input": "BUTTON", "confirmation_count": 1, "denial_count": 0,
    "reported_at": "…", "expires_at": "…", "verified_at": null, "distance_km": 0.5,
    "language": "si", "name": "පොලිසිය", "message": "ඉදිරියෙන් පොලිසිය සිටී. ප්‍රවේශමෙන් රිය පදවන්න.",
    "my_vote": null, "can_vote": true } ] }
```

The list is sorted nearest first. With no live position, `items` is empty and `note` explains why. `can_vote` is
true only for a Driver who did not report it and has not answered.

## 4. Answer — `POST /road-alerts/{id}/votes`

```json
{ "vote": "CONFIRM" }      // or "DENY"
```

**200** = the item. Only Drivers on a running trip within 15 km can answer.

Errors:
- 409 `ALREADY_ANSWERED`
- 409 `OWN_ROAD_ALERT`
- 409 `NOT_NEAR_ROAD_ALERT`
- 409 `ROAD_ALERT_CLOSED`

## 5. Notifications

Nearby people get a `ROAD_ALERT` notification:
- `title`: "Road alert" / "சாலை எச்சரிக்கை" / "මාර්ග අනතුරු ඇඟවීම".
- `body`: the sentence plus the distance.
- `expires_at` = the alert's expiry.

```json
"action_payload": { "road_alert_id": "…", "alert_type": "ACCIDENT", "latitude": "…", "longitude": "…",
                    "distance_km": 3.2, "language": "ta", "speak": "முன்னால் விபத்து. வேகத்தைக் குறையுங்கள்." }
```

## 6. Admin — `GET /admin/road-alerts[?status=]`, `POST /admin/road-alerts/{id}/moderation`

- **List:** latest 200, with `description`, `confidence_score`, `reporter`, `trip_id`, `moderation_reason`.
- **Moderation:**

```json
{ "expected_version": 2, "action": "REMOVE", "reason": "Prank report." }
```

- `VERIFY` needs no reason. `REJECT` and `REMOVE` need one (422 `REASON_REQUIRED`).
- Audited. Errors: 409 `VERSION_CONFLICT`, 409 `ROAD_ALERT_CLOSED`.

## Screens (UI Claude)

**Driver's live trip map (Driver workspace and "My driving"). It opens by itself when the trip starts. The alert
buttons appear only here, never on the dashboards (owner decision 13 Nov 2026). Map layout: 03O section C.**
- **Alert button:** one round button on the side of the map.
  - It opens five big buttons: Police, Speed check, Accident, Roadblock, Road hazard, with icons.
  - Tapping one sends it with the current position and heading (section 1, `BUTTON`).
- **Microphone button (voice) — one tap, then hands free (owner decision 12 Nov 2026):**
  1. The Driver taps the mic **once** and speaks. Use browser speech recognition (`webkitSpeechRecognition`), with
     `lang` = `ta-LK`, `si-LK` or `en-US` from the Driver's language.
  2. Send the text to section 2.
  3. Not understood (`alert_type: null`): speak and show `message`, and open the five buttons.
  4. Understood: show `confirm_prompt` with two big buttons, **Send** and **Cancel**, and a 10-second countdown ring
     (`confirm_seconds`). Speak `confirm_prompt` with `speechSynthesis`.
  5. When the speech ends, **start listening again by itself**, so the Driver does not tap a second time. Keep
     listening until `confirm_seconds` have passed.
     - Any of `yes_words` heard, or Send tapped → post the alert (`source_input: "VOICE"`, `driver_confirmed: true`,
       `confidence_score` = `confidence`). Speak `sent_text`.
     - Any of `no_words` heard, or Cancel tapped → nothing is sent. Speak `not_sent_text`.
     - **Silence or anything else until the time ends → nothing is sent.** Show and speak `not_sent_text`.
     - Match whole words in lower case ("ok" must not match inside another word). If both a yes and a no word are
       heard, treat it as no.
  6. Turn the microphone off after the answer or the timeout. Never keep it on between alerts.
  7. While the app is speaking, do not listen, so it does not hear itself.
  8. If the browser has no speech recognition (not Chrome/Edge) or the mic is blocked, hide the mic button and keep
     the five buttons.
- **Keep the screen on during a trip (Screen Wake Lock, owner decision 12 Nov 2026):**
  - Travelly runs in the browser, and a phone with its screen off pauses the page. Live position updates, new alerts
    and the speaker all stop.
  - So while the trip is running (`IN_PROGRESS` / `BREAKDOWN` / `ASSISTANCE_REQUIRED`), the Driver's live trip page,
    and a Passenger's trip page when the speaker is on, ask for `navigator.wakeLock.request('screen')`.
  - Ask again on `visibilitychange` when the page becomes visible: the browser drops the lock when the person
    switches app.
  - Release it when the trip finishes or the page closes.
  - If the browser does not support it, show once: "Keep the screen on during the trip so alerts and location keep
    working." Add one line in the trip page: "Tip: keep the phone on the charger."
- **Alerts on the map:** markers from section 3. For a Driver with `can_vote`, show "Still there" / "Not there"
  (section 4).

**Speaker:**
- **Setting:** "Speak road alerts" (on/off, kept per device). The voice language is the user's `preferred_language`
  (Profile → language).
- **When a new alert arrives** (a new item in section 3, or a new `ROAD_ALERT` notification), speak
  `message` / `action_payload.speak` with `speechSynthesis`, `utterance.lang` = `ta-LK` / `si-LK` / `en-US`.
- **If the device has no voice for that language,** show the text banner only. Sinhala and Tamil voices are not
  installed on every device.
- **Passengers** see the alerts on their trip map, and hear them if they switched the speaker on.

**Admin:** "Road alerts" list with status filter and Verify / Reject / Remove (reason).
