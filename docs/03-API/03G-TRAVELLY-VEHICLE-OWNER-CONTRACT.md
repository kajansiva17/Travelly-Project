# 03G-TRAVELLY-VEHICLE-OWNER-CONTRACT

> Recovered source text, 7 November 2026. Source: documentation collection, pages 232-233, original path `docs/03-API/03G-TRAVELLY-VEHICLE-OWNER-CONTRACT.md`. This is the saved page-text extraction, not the original Markdown. Line wrapping and table layout reflect the compilation; no policy wording has been rewritten. Later approved amendments recorded in `docs/00-READ-FIRST/Travelly_NBP_Codex_Context.md` take precedence.

~~~~text
Vehicle/Owner first-delivery API supplement
Date: 27 October 2026. Authority: contracts 06/08 and Final Decisions. Supplements historical matrix #14-26/#94 without
renumbering or implementing the later calendar. All paths below begin /api/v1. Existing Auth, private-document operations and
03F pricing remain intact. JSON mutations reject unknown fields, duplicate keys, coercion of boolean/integer facts and
unsupported state transitions. Common expected_version is a strict positive integer; create has no client
actors/owner/version/states/media authority fields.
Method / path
Permission and DTO
POST /vehicles
Approved Owner; registration_number only; creates owned incomplete DRAFT, 201.
GET /owners/me/vehicles
Approved Owner, bounded page/page_size; own safe management summaries, existing
pricing-picker fields retained; default page_size 100 for compatibility, maximum 100, fleet
UI requests 20.
GET /owners/me/vehicles/{id}
Own approved Owner; factual details, declaration, registration lock/latest decision, current
non-superseded documents, checklist, safe media metadata.
PATCH /vehicles/{id}
Own approved Owner; expected_version and partial factual
fields/registration/registered_owner_case. Registration locked after first submission. No
direct state/media/review authority.
POST /vehicles/{id}/submit
Own approved Owner; expected_version, complete factual/core/case evidence; DRAFT
-> SUBMITTED.
PATCH /vehicles/{id}/availability
Own approved Owner; expected_version, availability_status ACTIVE/INACTIVE;
retirement commitment guard. No calendar/maintenance block write.
PATCH /vehicles/{id}/publish
Existing 03F Owner version/publication body; now also requires approved exterior photo.
Unpublish retains commitments.
POST /drivers/eligible-lookup
Approved owning Owner; vehicle_id, service_type_id, exact driver_reference; minimal
eligible profile only.
PATCH /vehicles/{id}/preferred-driver
Own approved Owner; expected_version, nullable driver_reference and service_type_id
required when selecting. Preference only.
GET /admin/vehicles
Current Admin; bounded page/page_size and optional verification_status; self vehicles
excluded before count.
GET /admin/vehicles/{id}
Non-self Admin; bounded details/checklist/evidence metadata and latest feedback; no full
audit history.
PATCH /admin/vehicles/{id}/review
Non-self Admin; expected_version, decision APPROVED/REJECTED/SUSPENDED;
reason required for negative decisions. Approval additionally requires reviewed category,
all three conditional_documents booleans and authorisation_required. Existing
implicit-APPROVED transport remains compatible.
PATCH /admin/vehicles/{id}/registration
Non-self Admin; expected_version, registration_number, required reason; unique
correction, commitment guard, unpublish/re-review.
PATCH /admin/vehicles/{id}/description/review
Non-self Admin; expected_version, decision APPROVED/REJECTED/REMOVED,
required negative reason (<=500); approval requires privacy_confirmed=true. Approval
binds current proposed text; removal withdraws approved public text; no stale-body
override. Vehicle verification unchanged.
POST /vehicles/{id}/photos
Own approved Owner; bounded multipart file, category EXTERIOR/INTERIOR,
expected_version; normalized PENDING photo, no client path/URL.
GET /vehicles/{id}/photos/{photo_id}/{width}
Width 480/960/1600; own approved Owner/non-self Admin may preview; anonymous only
approved photo on currently eligible published vehicle. JPEG with nosniff/no-store, no
original metadata.

Method / path
Permission and DTO
PATCH /vehicles/{id}/photos/{photo_id}
Own approved Owner; expected_version; soft removal only, no bytes/history deletion.
PATCH /admin/vehicles/{id}/photos/{photo_id}/review
Non-self Admin; expected_version, decision APPROVED/REJECTED/REMOVED;
negative reason required, approval explicitly confirms privacy and genuine vehicle.
GET /vehicles/{id}
Public allowlisted eligible detail, same gates as Browse/search, never plate/private
evidence/contact/location.
Factual fields: vehicle_type_code initial enum; make/model <=80; manufacture_year positive and not future; colour <=40;
power_type ICE/MHEV/HEV/PHEV/BEV; engine_fuel_type PETROL/DIESEL (null for BEV);
seat_capacity/large_luggage_capacity/small_luggage_capacity strict nonnegative integers within existing SMALLINT storage,
positive usable seats for submission; current_odometer_km nonnegative decimal string within NUMERIC(12,1);
transmission_type <=40; nullable air_conditioned boolean; description <=4000; registered_owner_case
SELF/OTHER_PERSON/COMPANY. Nullable draft facts may be cleared subject to existing power/fuel checks. Trim strings,
reject empty non-null values. Complete submission never fabricates values.
Private vehicle evidence uses existing POST /documents owner_type VEHICLE/owner_id and GET /documents?vehicle_id=...
plus existing Admin document review/correction. Upload metadata remains optional when not printed. Individual corrections keep
vehicle SUBMITTED. Owners cannot verify files or own review; Admin requires current bytes/evidence and retains full reasons in
the restricted channel.
Public DTO: vehicle reference/id, type/make/model/year/colour, usable capacities, A/C/description, approved public photo
variant URLs/dimensions and safe Owner public reference/display name; pricing only via approved 03F scope/calculation.
Owner DTO may include own registration and latest feedback {decision,reason,decided_at}; never raw journal frames/previous
decisions/storage keys. Photo metadata is server-generated, versioned as part of the vehicle; no separate table.
Errors: 401 missing/expired session, 403 disallowed current role/self-review, 404 absent/alien private/ineligible public resource,
409 version/state/registration/commitment conflict, 413 body/file bound, 415 unsupported content type, 422
factual/file/submission validation, 503 storage/audit/decoder dependency. Durable audit intent must precede ordinary
PostgreSQL commit; uncertain outcome retains existing refresh/recovery behavior. Bytes are durably placed before references
and retained on uncertain commit; orphan bytes are inaccessible through public lookup and retained for restricted maintenance,
never deleted by row-invisibility guess.
Scoped writer RPC returns only registration lock and latest vehicle-review projection after database Owner/Admin checks and
committed-event filtering. It never enables a general history RPC. Exact projection code has tests against embedded and
separate-writer transports. No new application table or schema migration is needed for this delivery.
Approved content refinement: verified_eligibility.description_review is server-generated bounded content state,
distinct from operational/verification authority. Description edits mark PENDING while retaining the last approved text until a new
decision; empty text withdraws public text immediately. Non-self Admin privacy review records the current proposed text as
approved or retains the prior approved text on rejection, with latest reason/time visible to the owning Owner. Material re-review
clears the old projection. Public responses never use unreviewed vehicles.description directly. Pending descriptions do not block
publication. Expected-version content decisions are independently audited without changing verification status. Vehicle audit
stores complete changed-field before/after evidence (including keyed media changes), bounded before intent append, instead of
duplicating entire growing galleries.
Calendar transport supplement ? 28 October 2026
The later authorized contract 09 (../04-MODULE-CONTRACTS/09-VEHICLE-AVAILABILITY-CALENDAR.md) freezes Owner
GET /vehicles/{id}/calendar, Admin GET /admin/vehicles/{id}/calendar, POST /vehicles/{id}/availability-blocks, PATCH
/vehicles/{id}/availability-blocks/{block_id} and POST .../{block_id}/withdraw. Read its exact payloads, range limits, permissions,
errors and persistence mapping. It supersedes earlier calendar deferral and refines historical matrix #74 without renumbering it.
No general /records API is implemented.
GET /notifications retains its existing recipient scope and adds nullable support_vehicle_id only for ADMIN_ACTION
notifications. This links Admin recipients to the read-only support calendar; it grants no calendar access by itself. Search returns
AVAILABILITY_INCOMPLETE (503) when an occupancy source fails, even if some other inventory was checked. Unpriced
request fallback, Owner commitment, Driver acceptance, trip start and accepted trip changes reuse the complete occupancy
check; mutation callers retain the vehicle lock through commit.
~~~~
