# Travelly — My notifications (`GET /api/v1/notifications`)

Status: built on `claude-work` (12 Nov 2026), from the UI note "notifications have no type or payload".
Base `/api/v1`, Bearer token. It returns the caller's latest 100 notifications, newest first.

```json
{ "items": [ {
  "id": "…", "notification_type": "REPLACEMENT", "channel": "IN_APP",
  "title": "Your journey has a replacement vehicle", "body": "…",
  "status": "QUEUED", "action_required": true,
  "action_payload": { "scheduled_trip_id": "…", "booking_id": "…" },
  "booking_id": "…", "scheduled_trip_id": "…", "trip_id": null,
  "response_code": null, "created_at": "…", "read_at": null, "expires_at": null,
  "support_vehicle_id": null } ] }
```

- `notification_type` is one of the PRD values: `BOOKING_REQUEST`, `BOOKING_CONFIRMED`, `DRIVER_ASSIGNMENT`,
  `RECONFIRMATION`, `PAYMENT`, `REFUND`, `REPLACEMENT`, `MAINTENANCE_DUE`, `DOCUMENT_EXPIRY`, `ROAD_ALERT`,
  `ADMIN_ACTION`.
- `action_payload` is returned as stored. Unknown keys can be ignored.
- `support_vehicle_id` is kept only for screens built before this change. New screens use
  `action_payload.vehicle_id`.

## What the UI matches on (use the type, not the title wording)

| Notice | `notification_type` | `action_payload` keys |
|---|---|---|
| Replacement vehicle (Passenger, can reject) | `REPLACEMENT`, `action_required: true` | `scheduled_trip_id`, `booking_id` → open the booking's change card |
| "We are arranging your journey" | `REPLACEMENT` | `scheduled_trip_id`, `booking_id` |
| Replacement request to another Owner / declined / accepted | `REPLACEMENT` | `scheduled_trip_id` (the draft or the original departure) |
| "Booking cancelled - full refund", "Departure cancelled - full refund" | `REFUND` | `scheduled_trip_id`, `booking_id` |
| Document expiry reminder | `DOCUMENT_EXPIRY`, `action_required: true` | `document_id`, `document_type`, `expiry_date`, `stage`, `vehicle_id` (vehicle documents only), `reminder_key` |
| Maintenance due reminder | `MAINTENANCE_DUE`, `action_required: true` | `vehicle_id`, `task`, `stage`, `record_id`, `reminder_key` (03R) |
| Road alert | `ROAD_ALERT` | `road_alert_id`, `alert_type`, `latitude`, `longitude`, `distance_km`, `language`, `speak` (03A §5) |
| Admin support message | `ADMIN_ACTION` | `vehicle_id` |

Links:
- With `booking_id` → open that booking.
- With `document_id` → that document's upload/renew screen. Vehicle documents are under the vehicle in `vehicle_id`.
- With `vehicle_id` only → open that vehicle.
- With `road_alert_id` → the trip map.

## Role application status — "Needs correction"

`GET /users/me/role-requests/{OWNER|DRIVER}/status` has no separate "needs correction" state. The PRD role states are
only `PENDING`, `APPROVED`, `REJECTED` and `SUSPENDED`.

- **Showing "Needs correction" for `REJECTED`, with `application.rejection_reason`, is correct.** The database requires
  a reason (1–2000 characters) for every rejection.
- After correcting, the person sends the same application form again; it goes back to `PENDING`.
- `SUSPENDED` is different: show "Suspended" with `suspension_reason`, and no resubmit button.
- `NEEDS_CORRECTION` exists only for single **documents** (`documents.status`), and the UI shows it on that document.
