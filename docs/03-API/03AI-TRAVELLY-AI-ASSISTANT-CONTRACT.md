# Travelly AI — chat/voice search and help (PRD matrix 90–91, D10)

Status: built on `claude-work` (12 Nov 2026). Base `/api/v1`, JSON. **Signed-in customers only** (owner decision 13 Nov
2026, see the end). Nothing is stored, held or booked.

## Rules (PRD + owner decisions 12 Nov 2026)

- **PRD:** "AI text/voice search produces editable filters and returns only real eligible inventory." AI discovery
  never books or pays.
- **Owner decision:** the AI asks the questions the search form asks, one at a time, fills the form, and shows it for
  checking. **The person presses Search.** Choosing a vehicle, confirming, booking and paying stay manual, exactly as
  today.
- The AI asks only for fields the form has. The questions are fixed sentences in en/ta/si, so the AI never makes up
  rules, prices or vehicles.
- **Engines:**
  - **AI services** (Groq, then OpenRouter, then Gemini; see clarification 5). Daily caps `AI_DAILY_LIMIT` (1000) and `AI_USER_DAILY_LIMIT` (40).
    Only the typed or spoken text is sent, with emails and phone numbers masked.
  - **Built-in rules**, used when there is no key, the cap is reached, or every AI service fails. They understand English,
    Tanglish ("Kandy-la irunthu Colombo-kku", "naalai kaalai 8 mani", "5 per", "2 periya bag"), Tamil and Sinhala
    sentences.
  - `engine` in each reply says which one answered.
- **Help** answers only from `Backend/app/services/help_guide.py`. Anything else: "I don't know, contact Support".
- Signed-in customers only. Rate limits per person: search-assist 60 / 10 min, help 30 / 10 min (429 `RATE_LIMITED`); 401 without a token.

## 1. One chat/voice turn — `POST /ai/search-assist`

```json
{ "message": "naan Kandy-la irunthu Colombo pooka van venum", "language": "ta",
  "filters": { }, "asking": null }
```

- `language`: `en` | `ta` | `si`, from the app language. It sets the language of the questions.
- `filters`: what is known so far. **Send back the `filters` from the previous reply**, including any edits the person
  made in the card.
- `asking`: send back the previous reply's `asking`, so a bare answer ("5", "Colombo Fort", "8") fills that field.

**200:**

```json
{ "filters": { "pickup": "Kandy", "destination": "Colombo" },
  "asking": "service",
  "question": "எந்த சேவை வேண்டும்: உள்ளூர் வாடகை, விமான நிலையம், நீண்ட தூரம், அல்லது பஸ்/வேன் டிக்கெட்?",
  "options": [ { "value": "local", "label": "உள்ளூர் வாடகை" }, { "value": "airport", "label": "விமான நிலையம்" },
               { "value": "long-distance", "label": "நீண்ட தூரம்" }, { "value": "ticket", "label": "பஸ்/வேன் டிக்கெட்" } ],
  "notes": [], "ready": false, "form_path": "/travel/book/service",
  "summary": [ { "field": "pickup", "label": "புறப்படும் இடம்", "value": "Kandy" } ],
  "language": "ta", "engine": "rules" }
```

- **`question`**: show it as the assistant's message, and speak it when voice is on.
- **`options`**: quick-reply chips. Send the chip's `value` as the next `message`.
- **`notes`**: short lines to show before the question, e.g. "That time has already passed.", "Sorry, I did not
  catch that.", or "Self-drive rent is not available yet…".
- **The order of questions:**
  1. service, pickup, destination, date
  2. time (not asked for tickets)
  3. return date and time (return journeys)
  4. hours per day; return date for multi-day (long distance)
  5. passengers
  6. luggage (hire only)
- `journey` defaults to `ONE_WAY` and `duration` to `ONE_DAY`. Both are shown in the card and can be edited.
- **`ready: true`**: everything the form needs is known. `question` = "Here is your search. Check it…".

### Filter fields → the existing booking draft (`travelly.passenger.booking-draft.v2`)

| `filters` | draft | Notes |
|---|---|---|
| `service` `local` / `airport` / `long-distance` | `service` + `serviceTypeId` | Match the service from `GET /service-types` by `pricing_scope` (LOCAL / AIRPORT / LONG_DISTANCE), the same way `PassengerServiceSelection` does. |
| `service` `ticket` | — | Ticket search: `origin` = `pickup`, `destination`, `date`, `travellers` = `passengers`. |
| `pickup`, `destination` | `detail.pickup`, `detail.destination` | Text only. These seed `PlaceSearch` (`querySeed`). **The person picks the verified place from the list** before Search, because a hire search needs the place token. |
| `date`, `time` | `detail.date`, `detail.time` | `YYYY-MM-DD`, `HH:MM`, Sri Lanka time. |
| `journey` | `detail.journey` | `ONE_WAY` / `RETURN` |
| `return_date`, `return_time` | `detail.returnDate`, `detail.returnTime` | |
| `duration` | `detail.duration` | `ONE_DAY` / `MULTI_DAY` |
| `hours` | `detail.hours` | Long distance |
| `passengers` | `requirements.passengers` | |
| `large_luggage`, `small_luggage` | `requirements.largeLuggage`, `requirements.smallLuggage` | |
| `flight` | `detail.flight` | Airport only, optional |

Event hire: `notes` says to open Event hire, with `form_path: /travel/book/event`.

## 2. Help — `POST /ai/help`

```json
{ "question": "ticket eppadi cancel pannurathu", "language": "ta" }
```

```json
{ "found": true, "topic_id": "cancel", "title": "பதிவை ரத்து செய்ய / பணம் திரும்ப", "answer": null,
  "steps": ["Open Bookings and choose the booking.", "Press Cancel. …"], "steps_language": "en",
  "note": "படிகள் ஆங்கிலத்தில்:", "path": "/bookings",
  "related": [ { "topic_id": "pay", "title": "பணம் செலுத்த", "path": "/bookings" } ],
  "language": "ta", "engine": "rules" }
```

- **Show:** `title`, then `answer` if any, then the numbered `steps`, then a button **"Open this page"** → `path`
  (through `travelPath`, so the Owner and Driver workspaces open their own copy). Show `related` as chips.
- **Language:** with an AI service the steps come in the person's language (`steps_language` = `ta`/`si`). With the rules
  they are in English, with `note` saying so.
- **Not found:** `found: false`, `answer` = "I don't know that yet. Please contact Support…", `path` = Support.
- **`GET /ai/help/topics/{en|ta|si}`** lists every topic for a "What can I ask?" list.

## Screens (UI Claude)

The "Hi Maya! I'm your Travelly AI assistant" card (signed-in dashboards only; not on the landing page):

- **Chat with Travelly AI:** opens a chat panel. Each message goes to section 1, or to section 2 when it is a question
  about the app.
  - Simple routing: if the person picked "Help" or the text starts with how / eppadi / எப்படி / කොහොමද, use help.
  - Two tabs, **Find a ride** and **Help**, are also fine.
- **Talk by voice:**
  1. Browser speech recognition (`webkitSpeechRecognition`), `lang` = `ta-LK` / `si-LK` / `en-US`.
  2. The recognised text is sent as `message`.
  3. The reply's `question` is spoken with `speechSynthesis`. If the device has no voice for that language, show the
     text only.
  4. A mic button is used for each answer. No always-on listening.
- **When `ready: true`:** show a **"Check your search"** card built from `summary`. Each row can be edited inline, and
  the pickup and destination use `PlaceSearch` seeded with the text.
  - **Search:** write the values into the booking draft (table above) and open the vehicle list
    (`/travel/book/vehicles`) for hire, or run the ticket search. The normal search endpoint runs, so only real
    vehicles appear.
  - **Edit in form:** open `form_path` with the draft filled.
- After that, the normal flow continues by hand: pick a vehicle, review, request or book, pay.
- **Strings:** new UI wording goes in `messages.trips.js`. The question texts come from the API already translated.

## Clarifications for the UI (13 Nov 2026)

1. **Help paths are Passenger paths. The UI maps them to the person's workspace**, the same way `travelPath` does
   for booking pages:
   - `found: false` always returns `path: "/passenger/support"`. Inside the Owner workspace open `/owner/support`,
     inside the Driver workspace `/driver/support`.
   - `/travel/...`, `/bookings`, `/dashboard`: use `travelPath` / the current workspace.
   - `/owner/...` topics (vehicles, earnings) and `/driver/assignments` (road alerts): show the button only to people
     with that approved role. For anyone else, show the steps without the button, or `/owner/onboarding` /
     `/driver/onboarding`.
   - `/account`, `/forgot-password`, `/reels`, `/owner/onboarding`, `/driver/onboarding`: use as given.
2. **`GET /ai/help/topics/{en|ta|si}`** returns `{ "items": [ { "topic_id": "cancel", "title": "…", "path": "/bookings" } ] }`.
3. **The first message cannot be empty:** `message` is 1–500 characters (422 otherwise).
   - Show the intro line from the UI itself, with no API call. Suggested text: "Hi! Tell me where you want to go, or
     ask how to do something in Travelly." It goes in `messages.trips.js` (en/ta/si).
   - Call `search-assist` / `help` only when the person types or speaks.
   - Start with `filters: {}` and `asking: null`.
4. **No AI on the landing page. Signed-in customers only** (owner decision 13 Nov 2026).
   - PRD D10 allows public AI, but a public page would use up the free AI quota. So `POST /ai/search-assist`
     and `POST /ai/help` need the Bearer token (401 without it).
   - Each person gets `AI_USER_DAILY_LIMIT` (default 40) AI answers a day, and the whole site gets
     `AI_DAILY_LIMIT` (1000). Past either cap the built-in rules answer (`engine: "rules"`), so the chat still
     works.
   - Rate limits are per person: search 60 / 10 min, help 30 / 10 min.
   - `GET /ai/help/topics/{lang}` stays public; it is static and uses no AI service.
   - UI: show the AI card only in signed-in dashboards (Passenger, Owner, Driver workspaces). There is no AI card on
     the landing/home page.
5. **AI services: Groq, then OpenRouter, then Gemini** (owner decision 13 Nov 2026). The services are tried one
   after another:
   - **Chat, search and help:** `AI_PROVIDERS=groq,openrouter,gemini`.
   - **Odometer photo:** `AI_VISION_PROVIDERS=openrouter,gemini`. Groq's free models do not read images.
   - A service without a key is skipped. When a service fails or hits its limit, the next one answers. After all of
     them the built-in rules answer, so the app never stops.
   - **Only one service answers each message**, and its answer goes through the same backend checks. `engine` says
     which one answered: `groq`, `openrouter`, `gemini` or `rules`. The UI needs no change.
   - **Caps:** `AI_USER_DAILY_LIMIT` = 40 per person per day; `AI_DAILY_LIMIT` = 1000 for the site.
   - **Models:** `GROQ_MODEL` (`openai/gpt-oss-120b`), `OPENROUTER_MODEL` / `OPENROUTER_VISION_MODEL`
     (`google/gemma-4-31b-it:free`), `GEMINI_MODEL` (`gemini-3.5-flash-lite`).
   - **Check:** `scripts/check_ai.py` tests every service that has a key.
