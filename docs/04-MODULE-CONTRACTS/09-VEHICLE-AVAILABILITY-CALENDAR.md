# 09-VEHICLE-AVAILABILITY-CALENDAR

> Recovered source text, 7 November 2026. Source: documentation collection, pages 288-289, original path `docs/04-MODULE-CONTRACTS/09-VEHICLE-AVAILABILITY-CALENDAR.md`. This is the saved page-text extraction, not the original Markdown. Line wrapping and table layout reflect the compilation; no policy wording has been rewritten. Later approved amendments recorded in `docs/00-READ-FIRST/Travelly_NBP_Codex_Context.md` take precedence.

~~~~text
Vehicle Availability Calendar - frozen narrow contract
28 October 2026. The project owner's current instruction authorizes VM-D14/D15 implementation, superseding only the earlier
delivery deferral. VM-D13, Final Decisions, 02C, 03F and 03G remain binding. No new business choice is needed.
Dependencies were checked before implementation: migration 0006 already supplies bookings, trips, scheduled_trips,
vehicle_records and notifications, including their real foreign keys. No migration, new column or twenty-first table is required.
Persistence and transitions
Use vehicle_records.record_type=AVAILABILITY_BLOCK, vehicle_id, server recorded_by_user_id/recorded_at, start_at/end_at,
plain-text notes and common actors/version. trip_id and unrelated expense/odometer fields stay NULL. Freeze the
record-specific approval_status mapping as PERSONAL, MAINTENANCE, EMERGENCY and WITHDRAWN_PERSONAL,
WITHDRAWN_MAINTENANCE, WITHDRAWN_EMERGENCY (all within VARCHAR(24)). These encode directly effective
Owner blocks and retained withdrawals, not Admin approval. Existing NULL/unknown legacy blocks remain restrictive and visibly
unclassified; no automatic reinterpretation or silent release. Only classified records created by the current vehicle Owner are
editable/withdrawable. A withdrawn record cannot be reactivated; create a new block.
Create/edit requires offset-aware timestamps, end > start, a nonblank reason of at most 2000 characters, and an interval with
end after start. Historical date corrections remain allowed under D15; no new past-date editing prohibition is introduced.
Emergency maintenance stops new use immediately when its stated interval includes the present; future intervals restrict only
those dates. No global availability or publication status is rewritten. Edit replaces the entire interval/kind/reason after version and
commitment checks; withdrawal retains the original interval/kind/reason and stores its reason in durable audit. Both increment
the record version once. No hard deletion. Overlapping blocks may coexist; withdrawal removes only the selected record's
restriction.
All source reads use the approved half-open overlap predicate start < requested.end AND end > requested.start; no turnaround
buffer. Preserve full day-hire reserved intervals already stored by pricing. Protected sources are vehicle_committed bookings
(including AWAITING_DRIVER and OWNER_ACTION_REQUIRED), protected departure states excluding
DRAFT/CANCELLED/COMPLETED, and accepted nonterminal trips. Booking/trip/departure states are not changed by calendar
writes. Completed/cancelled/rejected bookings do not restrict new use. Calendar includes historical commitments with explicit
state and restriction flags. Ordinary create/edit overlapping unresolved commitments is rejected with actionable references;
emergency writes retain them and enqueue ADMIN_ACTION notifications to current approved Admins in the same transaction.
The Owner response and Admin calendar always expose affected commitment references even when no Admin is currently
provisioned. Support resolution and refunds remain existing/later workflows, never implicit calendar actions.
Mutations lock authenticated authority then the vehicle row, then the block, inside existing durable audit coordination, matching
commitment/assignment locking. Conflict queries run after the vehicle lock. Driver locks/checks remain in existing assignment
workflows. Durable audit stores full bounded before/after block snapshots plus action/reason; history remains restricted.
Notification payloads identify the block/vehicle and affected records without private Passenger data.
Availability source queries use one PostgreSQL statement snapshot across all four sources. Any source failure yields
AVAILABILITY_INCOMPLETE (503) and blocks availability-dependent writes/search/assignment/start. Calendar must show
unavailable/incomplete, never an empty authoritative result. Responses with a bounded result overflow also fail closed; users
narrow the interval. Read views are observations, not reservations; authoritative acceptance always rechecks under lock.
General vehicle Browse remains discovery rather than an interval availability promise.
Frozen API supplement to matrix #19/#20 and #71-74
All paths begin /api/v1. No historical matrix renumbering; the following named additions explicitly settle the formerly generic block
transport.
* GET /vehicles/{vehicle_id}/calendar?start_at=...&end_at=...: current approved owning Owner; offset-aware range, maximum 93
days. Returns complete=true, checked_at, time_zone=Asia/Colombo, vehicle availability state, and bounded events
(source/id/reference/start/end/status/restricts/kind/reason/version/editable where applicable). No Passenger contact, private
document or price snapshot. Existing global restrictions remain separately visible.

* GET /admin/vehicles/{vehicle_id}/calendar with the same query: current Admin, read-only support view; no Owner mutation
authority. Includes affected commitments for emergency entries.
* POST /vehicles/{vehicle_id}/availability-blocks: own current approved Owner; {kind:
PERSONAL|MAINTENANCE|EMERGENCY, start_at, end_at, reason}; returns 201 block plus affected_commitments.
* PATCH /vehicles/{vehicle_id}/availability-blocks/{block_id}: same authority and full create payload plus strict positive
expected_version; returns current block plus affected_commitments.
* POST /vehicles/{vehicle_id}/availability-blocks/{block_id}/withdraw: same authority; {expected_version, reason}; returns
retained withdrawn block. Withdrawal requires a complete source read but never clears any other restriction.
Unknown/duplicate fields and naive timestamps are rejected. 401/403 current authentication/role rules; 404 hides alien
vehicle/block; 409 VERSION_CONFLICT, BLOCK_WITHDRAWN, BLOCK_CLASSIFICATION_REQUIRED or
VEHICLE_COMMITMENTS_REQUIRE_RESOLUTION; 422 invalid payload/range; 503 AVAILABILITY_INCOMPLETE or
existing durable-audit unavailable. No new public calendar/history endpoint.
Acceptance and boundaries
Verify touching endpoints, enclosing intervals, timezone equivalence, full reserved hours, own/alien/current roles, stale
edits/withdrawals, protected sources, overlapping independent blocks, emergency support notifications, missing sources,
durable before/after audit and concurrent commitment/block races. Reuse pricing fixtures and test actual desktop/mobile API
journeys, backend suite, affected frontend checks, migration drift, build and whitespace gates. Keep unrelated pricing,
Auth/profile/navigation, verification and deployment work unchanged.
The historical matrix #74 block_type becomes kind in this supplement. Create has no expected_version because it creates a new
independently versioned record; its conflict check is serialized on the vehicle. Edits/withdrawals require the record
expected_version. #19/#20 retain their vehicle publication/review behavior; this supplement adds no general records/expenses
API.
Trip-start enforcement also rejects a reserved interval that has already ended: an expired planned interval cannot authorize
present use outside its checked dates. The itinerary must be resolved through the existing workflow; no guessed extension or
reservation release is performed. Emergency Admin notifications include their exact maintenance interval and a link to the
read-only vehicle calendar.
~~~~
