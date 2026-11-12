# Travelly — choosing the Driver of a ticket departure

Status: built and tested on `claude-work` (11 Nov 2026). For the Owner's departure form ("Choose a driver"). Base URL
`/api/v1`, `Authorization: Bearer <token>`, JSON bodies. Errors use the usual shape
`{ "code", "message", "field_errors": [ { "field", "message" } ], "trace_id" }`.

A departure's Driver is `operator_driver_user_id` on `POST /scheduled-trips` and `PATCH /scheduled-trips/{id}` (DRAFT
only). The rule there, and in the lookup below, is the same: the person must hold an **APPROVED Driver role**
(otherwise 422 `DRIVER_NOT_ELIGIBLE`). If no Driver is given, an Owner who is an approved Driver drives it themselves.
There is no standing Owner–Driver network (PRD), so the list shows people already worked with, and anyone else is found
by their public reference.

## 1. Drivers I have worked with — `GET /owners/me/drivers`

Owner only (403 otherwise). No body.

```json
{ "items": [ { "id": "6f1c…", "reference": "USR-0123456789ABCDEF", "display_name": "Kamal",
               "eligible": true, "how_you_know_them": "Drove one of your departures" } ],
  "message": "Only Drivers you have already worked with. Add anyone else by public reference." }
```

- Sources: a vehicle's preferred Driver ("Preferred Driver for one of your vehicles"), a Driver of the Owner's trips
  ("Drove one of your trips") or departures ("Drove one of your departures"), and the Owner when they are an approved
  Driver ("You").
- Eligible first, then by name. Only ids with `eligible: true` can be saved as `operator_driver_user_id`.
- No history: `{ "items": [], "message": "No Driver has worked with you yet. Add one by public reference." }`
- Never returns phone, email or documents.

## 2. Find a Driver by public reference — `POST /owners/me/drivers/lookup`

Owner only. For anyone not in the list above, e.g. a new Owner. The Driver reads their reference (`USR-` + 16
characters) from their Travelly profile and gives it to the Owner.

Request:
```json
{ "driver_reference": "USR-0123456789ABCDEF" }
```
Leading/trailing spaces and lower case are accepted (`usr-0123…` works).

**200**, approved Driver:
```json
{ "id": "6f1c2a9e-…", "reference": "USR-0123456789ABCDEF", "display_name": "Kamal",
  "eligible": true, "message": "Approved Driver. You can assign them to this departure." }
```
**200**, a Travelly user who is not an approved Driver:
```json
{ "id": null, "reference": "USR-0123456789ABCDEF", "display_name": "USR-0123456789ABCDEF",
  "eligible": false, "message": "This person is not an approved Driver yet, so they cannot drive a departure." }
```
`display_name` falls back to the reference when the user has no display name. `id` is given only when eligible (it is
only useful for assigning them). Nothing else about the user is returned.

| Status | `code` | When |
|---|---|---|
| 404 | `DRIVER_NOT_FOUND` | no user has this reference |
| 422 | `VALIDATION_ERROR` | not `USR-` + 16 hex characters (`field_errors[0].field = "driver_reference"`) |
| 403 | — | caller is not an approved Owner |
| 429 | `RATE_LIMITED` | more than 30 lookups in 5 minutes by this Owner (`Retry-After` header) |

## 3. Using the result

Save `id` as `operator_driver_user_id`:
- new draft: `POST /scheduled-trips` with `"operator_driver_user_id": "<id>"`;
- existing draft: `PATCH /scheduled-trips/{id}` with `{ "expected_version": <version>, "operator_driver_user_id": "<id>" }`.

The departure response echoes `operator_driver_user_id`. Publishing needs a Driver (409 `DEPARTURE_NOT_READY` otherwise).
Publishing creates the departure's trip for that Driver.

Suggested form: the list from (1) as choices, plus "Add by reference" → text field → (2) → show `display_name` and
`message`, and enable "Use this Driver" only when `eligible` is true.
