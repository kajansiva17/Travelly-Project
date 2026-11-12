# Travelly — Reminders (document expiry and maintenance due)

Status: built on `claude-work` (12 Nov 2026). No new endpoint and no new table. Reminders are rows in the PRD
`notifications` table, read through the existing notifications API (`GET /api/v1/notifications`).

## When a reminder is created

| Type | Recipient | Stages (each sent once) | Rule |
|---|---|---|---|
| `DOCUMENT_EXPIRY` | the document's user, or the vehicle's Owner for a vehicle document | `EXPIRING`, then `EXPIRED` | Current `APPROVED` documents with an expiry date. `EXPIRING` when the expiry is within **5 working days** (PRD default, `REMINDER_WORKING_DAYS`). `EXPIRED` the day after it has passed. |
| `MAINTENANCE_DUE` | the vehicle's Owner | `DUE_SOON`, `DUE`, `OVERDUE` | From the maintenance summary (03M) of every approved vehicle that is not inactive or suspended. `DUE_SOON` when the earliest limit (estimated distance date or calendar date) is within the same working-day window. `DUE` and `OVERDUE` as the summary reports them. A new service record starts a new cycle. |

- Working days are Monday to Friday; public holidays are not known.
- Each reminder has `action_required: true` and an `action_payload`:

```json
{ "reminder_key": "DOCUMENT_EXPIRY:<document id>:2026-11-20:EXPIRING", "document_id": "…", "document_type": "INSURANCE",
  "expiry_date": "2026-11-20", "stage": "EXPIRING", "vehicle_id": "…" }
{ "reminder_key": "MAINTENANCE_DUE:<vehicle id>:OIL_CHANGE:<record id>:OVERDUE", "vehicle_id": "…", "task": "OIL_CHANGE",
  "stage": "OVERDUE", "record_id": "…", "remaining_km": "-1000.0", "due_date": "2026-11-12" }
```

- **Titles and bodies** are plain English, for example:
  - "Insurance expires soon / Your insurance for vehicle CAB-1234 expires on 20 Nov 2026. Upload a renewed copy before then."
  - "Oil change overdue / Oil change overdue for CAB-1234 (1000.0 km past the limit). Add a record in the Maintenance tab when it is done."
- **No duplicates:** `reminder_key` is unique per document, expiry date and stage, and per vehicle, task, service
  record and stage. Running the job again never sends a duplicate. Two runs at the same time take turns (advisory
  lock).
- **Email copies:** an extra row with `channel: "EMAIL"` (status `SENT` or `FAILED`) is created only when
  `REMINDER_EMAIL_ENABLED=true` and the recipient's email is verified. It is sent through the configured mail
  backend and counts toward the shared daily limit.

## Running it

`Backend/scripts/send_reminders.py`, for example once a day:
- **Demo:** Windows Task Scheduler runs `D:\Travelly\.venv\Scripts\python.exe D:\Travelly\Backend\scripts\send_reminders.py`
  with "Start in" set to `D:\Travelly`.
- **Server:** cron, e.g. `5 8 * * * cd /srv/travelly && .venv/bin/python Backend/scripts/send_reminders.py`.

It prints `Reminders sent: N document, M maintenance.`

`.env`:
- `REMINDER_WORKING_DAYS=5` (1–30)
- `REMINDER_EMAIL_ENABLED=false` (turn on with real email, `MAIL_BACKEND=brevo`)

## Screens (UI Claude)

Show the notifications with these types:
- `DOCUMENT_EXPIRY`: link to the document upload, for the person or for the vehicle (`vehicle_id`).
- `MAINTENANCE_DUE`: link to the vehicle's Maintenance tab (`vehicle_id`).
