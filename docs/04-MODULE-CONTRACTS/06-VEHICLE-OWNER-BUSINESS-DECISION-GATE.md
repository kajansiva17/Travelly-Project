# Vehicle Management + Owner Workspace — Business Decision Gate

Date: 26 October 2026. **Status: PROPOSED — awaiting project-owner approval.**

This is one decision list for the 20-day final project. Every recommendation below is an option for approval, not an accepted rule or implementation authorization. Existing frozen rules remain binding. No code, schema, migrations, API contracts/matrix, tests or UI are changed by this document. No new application table is proposed.

## 1. Authorities and reusable rules

Read: [Final Decisions](../00-READ-FIRST/01-TRAVELLY-NBP-FINAL-DECISIONS.md), [Readiness](../00-READ-FIRST/00-TRAVELLY-BACKEND-BUILD-READINESS.md), the complete [02C dictionary](../02-DATABASE/02C-TRAVELLY-PHYSICAL-DATA-DICTIONARY.md), [03B API matrix](../03-API/03B-TRAVELLY-API-ENDPOINT-MATRIX-96-ENDPOINTS.xlsx.xlsx), [Owner/Driver contract](02-OWNER-DRIVER-APPLICATIONS.md), [Passenger Dashboard contract](01-PASSENGER-DASHBOARD.md), and the completed [Admin Review implementation report](../../Backend/ADMIN_REVIEW.md). Final Decisions/Readiness take precedence; implemented Admin Review does not authorize vehicle operations by implication.

Already frozen; approval is **not** being requested again:

- Passenger membership is permanent/default; login still lands at `/dashboard`. Only a currently APPROVED Owner may enter Owner workspace/manage owned vehicles. Contact verification and role approval are separate; Owner approval never grants Driver approval.
- Individual Owner accounts only. An authorized individual may manage a company-owned vehicle; no company account or secondary-owner delegation.
- Owner-role evidence and individual vehicle verification are separate. Approved Owner membership does not approve/publish any vehicle. No fake vehicle was required for role approval.
- Vehicle verification: `DRAFT, SUBMITTED, APPROVED, REJECTED, SUSPENDED`. Availability: `DRAFT, PENDING_VERIFICATION, ACTIVE, BOOKED, ON_TRIP, MAINTENANCE, SUSPENDED, INACTIVE`. These are separate fields, not interchangeable states. `NEEDS_CORRECTION` belongs to documents, not vehicles.
- Publication requires approved Owner/vehicle, required verified/current documents and operational eligibility. Unverified/unpublished vehicles must not appear as public Passenger inventory. A guessed private vehicle ID grants no access.
- Private documents use the existing owner/Admin-authorized upload and streaming pipeline. Owners cannot see another Driver's private licence merely by selecting that Driver. Public profiles never expose private evidence.
- Admin-only verification, no self-review, expected-version protection and durable pre-commit audit are reusable. Public Admin provisioning remains prohibited.
- Document labels retain their accepted meanings: **Required**, **Required for your case**, **Optional**. Optional evidence never blocks verification. The vehicle operating checklist itself is not yet frozen.
- Driver assignments are trip-specific; a permanent Owner–Driver network is deferred. One vehicle may have different Drivers on different trips. Each trip has its own assigned Driver; `default_driver_user_id` is not assignment history. External Drivers accept/reject; eligible Owner+Driver self-drive needs no second acceptance.
- No overlapping confirmed vehicle bookings or overlapping accepted Driver trips. Availability is rechecked at acceptance/start. Existing interval overlap is `existing.start_at < requested.end_at AND existing.end_at > requested.start_at`; display timezone is Asia/Colombo.
- Existing accepted journey/financial history is preserved. Maintenance, edits, missing responses or deadlines never silently cancel protected journeys; use the existing Admin escalation/verified replacement/fulfilment rule.
- No invented vehicles, bookings, earnings or availability guarantees. IVR, subscriptions, secondary-owner delegation and general promotions/coupons remain excluded.

## 2. Decisions for approval, in dependency order

Impact shorthand: **P** Passenger, **O** Owner, **D** Driver, **A** Admin. Options remain within the frozen rules; none permits public unverified inventory, self-approval or a new table.

### VM-D01 — First delivery boundary

**Options:** A. Fleet drafts/editing, evidence, limited vehicle review/publication, service/pricing configuration and default-Driver preference first; dated calendar follows its dependency gate. B. Include the full dated calendar in the first delivery as well.

**Recommend A:** protect the 20-day schedule; do not pull booking/trip workflows into vehicle CRUD. Calendar decisions below can be approved now for the next slice.

**Effects:** P gets verified listings only; O gets a usable fleet workspace sooner; D assignment operations stay deferred; A gets only the vehicle-verification dependency, not a general dashboard.

### VM-D02 — Contact-unverified Owner actions

**Options:** A. Eligible APPROVED Owners can draft, submit and publish without a new contact-verification gate. B. Permit drafts/review but require a verified contact before publication.

**Recommend A:** Contact Verification delivery is deferred; B would block publication behind another unbuilt module. Keep reminders and existing booking-contact rules.

**Effects:** P's own booking rules stay unchanged; O can complete onboarding; D gains no permissions; A still verifies vehicle evidence independently.

### VM-D03 — Draft completeness and registration editing

**Options:** A. Start with registration number; require complete factual fields/evidence at submission. B. Require the entire submission checklist when creating a draft.

**Recommend A:** honest incomplete drafts are useful. Submission requires type, make/model/year, colour, power/applicable fuel, capacities and required evidence; description, transmission, A/C and odometer stay factual/optional unless needed by a selected service. Recommend trim/case-insensitive registration comparison without guessing punctuation equivalence; registration becomes Owner-immutable after first submission, with Admin-controlled correction.

**Effects:** P never sees incomplete drafts; O saves progress; D sees no assumed specifications; A reviews complete submissions and controls identity corrections. Global registration uniqueness is already frozen.

### VM-D04 — Vehicle types and capacity meaning

**Options:** A. Initial types CAR, VAN, BUS, THREE_WHEELER. B. A larger configurable taxonomy including additional body types.

**Recommend A:** match the existing project presentation. `seat_capacity` means usable Passenger seats, excluding Driver/crew; require positive, evidence-consistent seats before submission and explicit nonnegative large/small luggage counts before publication. Do not invent per-type seat maxima or standing/child-seat allowances.

**Effects:** P sees comparable usable capacity; O supplies real counts; D is not counted as a Passenger seat; A checks registration/specification consistency. Detailed seat maps stay with Ticket services.

### VM-D05 — Evidence for each actual vehicle

**Options:** A. Vehicle-scoped registration for every vehicle, plus authorization when registered to another person/company. B. Accept the earlier personal Owner-role evidence alone wherever it appears relevant.

**Recommend A:** role evidence does not prove every fleet vehicle. Use new retained `documents.vehicle_id` rows; keep personal evidence unchanged. Do not give a document both ownership FKs or create another linkage table. No extra vehicle NIC/licence requirement for an Owner-only account.

**Effects:** P gets vehicle-specific assurance; O submits each vehicle's proof; D approval stays separate; A checks plate, registered owner and authorization scope/expiry.

### VM-D06 — Operating-document checklist and applicability

**Options:** A. Small fixed core plus Admin-confirmed conditional requirements. B. Freeze an exhaustive automatic rule matrix for every vehicle/service before launch.

**Recommend A:** proposed core is VEHICLE_REGISTRATION, INSURANCE and REVENUE_LICENCE. OWNER_AUTHORISATION is required for the case in VM-D05. EMISSION, FITNESS and ROUTE_PERMIT are required where applicable to that vehicle/service; Admin must confirm applicability and retain its basis, not assume exemption. Unknown applicability blocks approval. BUSINESS_REGISTRATION/BANK_PROOF are not universal vehicle requirements.

This is a proposed product checklist, not a statement of statutory applicability. Exact case/expiry evidence and its approved persistence mapping must be frozen before build; no guessed exemptions or invented exemption fields.

**Effects:** P avoids unsupported eligibility claims; O sees the three accepted document labels; D cannot operate on missing required evidence; A owns applicability/expiry assessment.

### VM-D07 — Correction, rejection and resubmission

**Options:** A. Correct individual documents while vehicle remains SUBMITTED; reserve vehicle REJECTED for an explicit decision. B. Reject the whole vehicle for every document correction.

**Recommend A:** fewer unnecessary application resets. Propose REJECTED → DRAFT → SUBMITTED for corrected resubmission of the same vehicle, retaining reasons/history. A SUSPENDED vehicle cannot self-reset; reinstatement remains outside this slice.

**Effects:** P sees neither pending nor rejected inventory; O gets a correction route; D gets no premature eligibility; A separately decides documents and vehicle. These resubmission transitions need an explicit contract refinement after approval; no new vehicle status is proposed.

### VM-D08 — Edits after approval

**Options:** A. Re-review material identity/specification changes only. B. Re-review every edit, including description and pricing.

**Recommend A:** type, make/model/year, power/fuel and capacity changes unpublish and return to DRAFT for resubmission; registration correction stays Admin-controlled. Description, ordinary photo updates, service prices and calendar changes do not themselves reset verification, but retain their own validation/moderation rules. Do not rewrite accepted journey snapshots.

**Effects:** P sees verified specifications; O can maintain ordinary listing details; D's existing accepted trip is not silently changed; A reviews material changes. Conflicting future commitments require resolution before a material edit takes effect; emergencies follow VM-D14.

### VM-D09 — Applicant-visible vehicle decision feedback

**Options:** A. Show the latest own-vehicle rejection/suspension reason and decision time. B. Show only status and individual document reasons.

**Recommend A:** Owners need an actionable explanation even when the defect is not a document. Preserve full history in the approved journal; do not add a vehicle reason column.

**Effects:** P sees no review text; O sees only their latest vehicle feedback; D gets no evidence/history access; A supplies an applicant-visible reason. Owner-scoped latest-feedback retrieval is a proposed refinement: the existing full-history interface remains restricted offline. Its safe journal projection/API contract must be approved before implementation.

### VM-D10 — Initial pricing basis

**Options:** A. OWNER_QUOTE for initial private hire. B. DISTANCE with a frozen base/km formula. C. FIXED for explicitly defined packages.

**Recommend A:** no route-distance engine or new package catalogue is needed for the first fleet slice. Public pricing says “Quote required”; unknown amounts stay NULL, never a fabricated zero. Other existing pricing bases are retained for later service contracts.

**Effects:** P does not mistake an estimate for a final fare; O configures quote-based service terms; D receives no implied compensation; A manages the bounded service catalogue. Quote acceptance/final fare must be frozen in the later Booking contract before booking confirmation is enabled.

### VM-D11 — Currency, extras and price-setting authority

**Options:** A. LKR only, Owner-controlled own service terms, no free offers or automatic add-ons in this slice. B. Multiple currencies and separately calculated fuel/toll/overtime/platform extras now.

**Recommend A:** reduce pricing ambiguity. Disclose any proposed inclusions/exclusions before a later accepted quote; no hidden surcharge, automatic commission calculation or coupon logic. Price changes apply to future offers, never accepted terms.

**Effects:** P gets one disclosed currency; O controls their own offer, not global settings; D pay remains a separate future decision; A controls service activation/operational defaults, not arbitrary retrospective fare changes.

### VM-D12 — Availability authority, publication and public detail

**Options:** A. Explicit Owner publish/unpublish; Owner requests eligible ACTIVE/INACTIVE/MAINTENANCE, with BOOKED/ON_TRIP and verification-related states controlled by their workflows. B. Automatically publish whenever Admin approves.

**Recommend A:** verification is not consent to advertise or proof of availability. Public views require current eligibility; unverified/unpublished/ineligible inventory is hidden, including guessed detail URLs. Proposed public allowlist: vehicle reference, type/make/model/year/colour, usable capacities, A/C, description, approved public photos and enabled public service terms. Exclude registration plate, private documents, contact/account details and precise location.

**Effects:** P sees only safe eligible inventory; O controls advertising without self-approval; D cannot change fleet/pricing/publication; A controls verification/suspension. Automatic publication would still need all frozen eligibility checks; it cannot bypass them.

### VM-D13 — Calendar occupancy and turnaround

**Options:** A. Reserve a vehicle once the Owner commits, including AWAITING_DRIVER; ordinary REQUESTED enquiries do not reserve it. B. Reserve only after booking confirmation/Driver acceptance.

**Recommend A:** avoid offering the same committed vehicle to multiple journeys. Include confirmed/in-progress commitments, applicable published departures and effective manual blocks; retain protected reservations until explicitly resolved. Driver schedule blocking remains tied to accepted assignments. Use the frozen half-open interval rule, with no extra turnaround buffer in this NBP.

**Effects:** P sees time-specific availability subject to confirmation; O sees pending commitments distinctly; D can receive a pending offer without a permanent vehicle link; A resolves conflicts. Never advertise a fully authoritative calendar while booking/departure/trip sources are unavailable.

### VM-D14 — Maintenance and temporary unavailability

**Options:** A. Owner-controlled personal/maintenance blocks take effect directly. B. Admin must approve every block.

**Recommend A:** Owners can stop new demand promptly. A future block affects its interval only, not today's global status. Normal new blocks conflicting with commitments require prior resolution. Emergency maintenance may immediately stop new use but must surface existing commitments for Admin fulfilment/support; it never silently cancels/refunds them.

**Effects:** P is not promised an unavailable vehicle; O can report real downtime; D cannot be assigned into known downtime; A handles genuine exceptions, not every personal calendar entry.

### VM-D15 — Editing or withdrawing blocks

**Options:** A. Owners may edit/withdraw their own blocks with retained before/after audit. B. Blocks remain immutable/effective until their original end.

**Recommend A:** plans change; keep the record/history rather than hard-delete it. Withdrawal affects only that block, never a booking, departure or another restriction. Recheck conflicts and expected version.

**Effects:** P sees corrected availability; O can correct mistakes; D's accepted assignments remain protected; A can inspect retained reasons. “Effective” versus “withdrawn” are business meanings here, not new status literals: the existing vehicle_records mapping/vocabulary must be frozen at the technical gate.

### VM-D16 — Default Driver selection and discovery

**Options:** A. Optional default-Driver preference, selected by exact public reference with minimal eligible-profile lookup. B. Defer defaults and select only on each trip.

**Recommend A:** reuse `default_driver_user_id` as a convenience only. Recheck approved Driver/account/current licence eligibility. No global user directory, private phone/licence exposure, standing employment relationship, automatic assignment, calendar reservation or fleet-management permission. Actual external assignment still requires Driver acceptance.

**Effects:** P gets no misleading assigned-Driver claim; O avoids repeated selection; D gets no unsolicited permanent obligation; A retains role/document control. The matrix does not yet freeze this lookup or default-edit DTO; no endpoint is invented here.

### VM-D17 — Vehicle-specific licence suitability

**Options:** A. Admin manually verifies licence suitability for the vehicle/service before actual operation. B. Build a structured licence-class/vehicle qualification system now.

**Recommend A:** do not infer that every approved Driver can drive every vehicle type. Default preference alone is not suitability approval. Keep actual assignment/start unavailable until the Trip contract defines how the check is recorded/rechecked using approved persistence; no new qualification table/field.

**Effects:** P gets no unsupported safety claim; O cannot bypass licence suitability; D is assessed for the actual vehicle; A performs the check. One vehicle's different trips may still use different eligible Drivers; that existing rule is not being reopened.

### VM-D18 — Retirement, deletion and management transfer

**Options:** A. Unpublish/INACTIVE for retirement; no Owner self-transfer or hard deletion in this slice. B. Add draft deletion and controlled vehicle-management transfer now.

**Recommend A:** retain unique registration, evidence and journey history. Ownership disputes go to Admin support, not duplicate registration under another account. Retiring a listing cannot abandon existing commitments.

**Effects:** P loses future discovery, not historical records; O keeps their records without delegating ownership; D's accepted obligations stay visible; A handles disputes without a new transfer subsystem.

### VM-D19 — Vehicle photographs

**Options:** A. At least one genuine EXTERIOR photo before publication; INTERIOR optional, simple photo gallery only. B. Require a multi-angle/interior inspection gallery for every type.

**Recommend A:** achievable onboarding without inventing a larger inspection process. Owner uploads must depict the actual vehicle; private identity/operating scans never enter public `media`. Admin can reject/remove misleading photos; material specimen mismatch follows VM-D08.

**Effects:** P sees the real vehicle; O has a small upload checklist; D gains no photo-management right; A checks consistency. Public-photo upload/storage rules need their own technical freeze; the private-document streaming rule is not a public-photo delivery contract.

### VM-D20 — Evidence expiry and reopening visibility

**Options:** A. Hide ineligible inventory immediately; require renewed verified evidence and explicit Owner republication. B. Restore prior public visibility automatically when eligibility returns.

**Recommend A:** no silent reopening. Expiry does not invent a vehicle REJECTED state or remove Passenger membership. Suspended Owner roles lose Owner workspace under the frozen rule, while eligible own-document access remains available through the account flow. Existing commitments are escalated, not erased.

**Effects:** P cannot request newly ineligible inventory; O sees the repair path/reminder without a new contact gate; D cannot operate with expired required evidence; A verifies renewal and handles commitments. Suspended roles/vehicles cannot use renewal as self-reinstatement.

## 3. Existing mappings and technical follow-up — not extra business approvals

| Existing planned location | Available use / boundary |
|---|---|
| users + user_roles | Shared identity, current role/account/contact checks. No separate Owner account. |
| vehicles | owner_user_id, registration_number, factual specifications/capacities, media, default_driver_user_id, verification_status, availability_status, is_published, approved_by/approved_at, common actors/version. Already migrated by Admin Review. No rejection/suspension-reason column. |
| documents | Vehicle evidence via vehicle_id with user_id NULL; type, expiry, result/reviewer/reason/version and retained supersession. Private pipeline already implemented; no dual FK ownership. |
| service_types + vehicle_services | Existing categories/pricing bases, enablement, base/km/hour amounts, currency, minimums, date bounds and owner_terms. Planned, not implemented by Admin Review. No hidden calendar, Driver roster or audit store in JSON. |
| vehicle_records | AVAILABILITY_BLOCK, start_at/end_at, recorded_by_user_id, notes, common actors/version. approval_status is physically defined but its record-specific vocabulary remains unfrozen. |
| bookings + trips + scheduled_trips | Existing time intervals, vehicle/Driver links, booking/assignment/trip/departure states. Future calendar inputs; no fake journeys or standalone trips to represent a default Driver. |
| Restricted durable journal | Preserve vehicle review/block-edit decisions after a scoped contract refinement. Full-history read stays restricted; VM-D09's own latest-feedback projection is not already implemented. |

Follow-up before any build authorization:

1. Translate approved decisions into a Vehicle/Owner module contract and exact DTOs/permissions/errors. Existing matrix references are #14–20, #21–26, #71–74 and the vehicle portion of #94; generic cells do not settle submission, default lookup, block withdrawal or review feedback. Do not renumber endpoints or silently add APIs.
2. Freeze missing transport for vehicle submission/resubmission, any scoped vehicle review queue, Driver lookup and block edit/withdrawal; define public media separately from private evidence. Resolve the existing #18 signed-upload-token wording explicitly in that stage, not by applying document rules to all images.
3. Prove vehicle feedback, applicability assessments and licence-suitability evidence fit existing planned persistence/authorized audit access; otherwise report the exact missing mapping. No invented reason/exemption/qualification field or application table.
4. Resolve calendar migration order honestly: vehicle_records references trips; trips references bookings/scheduled_trips, which have further planned dependencies. A nullable FK still requires its target table. No dummy tables/trips, dropped FKs or JSON workaround. Approve the affected existing-table migration/API slice before calendar implementation; otherwise show it as unavailable/deferred.
5. Carry forward the Admin report's production OS-identity/ACL, backup/restore and physical-durability limitations. They are deployment checks, not settled by this business gate.

## 4. Fast-track sequence and approval boundary

Recommended sequence within the 20-day project: approve these decisions → freeze the narrow module/API/persistence contract → build core fleet/workspace/evidence/review/publication → service terms/default preference → calendar only when its planned dependencies are ready → regression/security/mobile acceptance. Reserve time for later Booking/Driver/Payment milestones; do not expand this into a general Admin dashboard, financial settlement, maintenance-accounting suite or permanent Driver network.

**Approval record: VM-D01 through VM-D20 are all PENDING project-owner approval.** Approve or amend individual IDs. No recommendation becomes authoritative merely because this document exists. After approval, document corrections and the corresponding technical/API gate still precede coding. Work stops here awaiting approval.
