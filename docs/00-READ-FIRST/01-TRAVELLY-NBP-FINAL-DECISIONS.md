# Travelly NBP Final Decisions and Supersession Register

Version: 1.3 | Technical readiness freeze: 25 October 2026 | Admin Review decisions finalized: 25 October 2026 | Original freeze: 23 October 2026 | International-phone amendment: 25 October 2026 | Authority: accepted project conflict-resolution decisions

## 1. Purpose and document precedence

This file records the accepted decisions, all 77 original entries in the agreed document-correction list, the two international-phone clarifications C78-C79 and the Admin Review clarifications C80-C90 and technical clarifications C91-C98. It overrides **only the conflicts and clarifications listed here**. It does not replace the full source documents or authorize unrelated scope/schema changes. The original PDFs remain unchanged reference artifacts; their identified text and diagrams must be read with the replacements below. No additional application table is introduced: the NBP retains exactly 20 planned application tables.

Apply precedence by subject:

1. Explicit accepted project decisions recorded here govern the listed conflicts, including statements in the Readiness Contract itself.
2. `00-TRAVELLY-BACKEND-BUILD-READINESS.md` governs current scope, business rules and staged build gates, subject to this register.
3. `02-TRAVELLY-AUTH-MILESTONE-CONTRACT.md` is the frozen detailed physical/schema/API/test contract for users, user_roles and the six Auth operations. It refines generic source descriptions without replacing other modules. 02C now freezes the complete 20-table physical target, preserving that Auth baseline and separately identifying the original source-planned optional users fields.
4. 02A is the authoritative 20-table database architecture, subject to the listed corrections and the Auth refinement. 02B is lecturer-format supporting material, not an independent conflicting architecture.
5. 03A and editable 03B together define the API contract, subject to this register, the exact Auth contract and the narrow accepted Admin Review API refinements in prerequisites sections 3-7 and scoped 03C OpenAPI/03D API contract. 03B now includes accepted GET additions 97-99 without renumbering existing IDs. Neither silently overrides the other; an unlisted disagreement must be resolved before implementing the affected operation.
6. 01 proposal, diagrams and planned UI descriptions are supporting references. Archived 149-table designs are not current implementation authority.

The source readiness filename was `00-TRAVELLY-BACKEND-BUILD-READINESS.md.md`; it is normalized to the requested single `.md` name during this documentation stage. Other source filenames retain their existing double extensions. PDF pages below are printed page numbers. Matrix #N is Sheet1 row N+1; columns E purpose, F input, G validation, I success, J errors, K auth.

## 2. Accepted decisions

| Decision | Binding rule |
|---|---|
| D01 | Role approval statuses are PENDING, APPROVED, REJECTED, SUSPENDED. UNDER_REVIEW remains valid for document/social review where separately defined, not for user_roles. |
| D02 | Every registered account receives Passenger membership. Contact verification is stored separately from role approval. The Auth contract specifies automatic APPROVED Passenger membership with PENDING_VERIFICATION account state; Owner/Driver approvals remain independent. |
| D03 | Booking uses the Readiness Contract lifecycle. Temporary Ticket holds belong to scheduled_trip_seats using HELD and hold_expires_at, not DRAFT/HOLDING booking statuses. |
| D04 | Assignment rejection is REJECTED. A started trip is IN_PROGRESS. Use the full separate assignment/trip catalogues below. |
| D05 | Passenger payment status and Owner settlement status are separate fields. Settlement changes never overwrite Passenger payment state. Existing linked financial transaction history is preserved. |
| D06 | vehicles.verification_status and availability_status are separate fields and eligibility checks evaluate both. |
| D07 | Telephony/IVR is deferred and must not be implemented or exposed in the current NBP. Current notification channels are IN_APP and EMAIL. |
| D08 | A missed protected-departure deadline does not automatically cancel a booking or trigger refund/automatic Owner commitment. Escalate to Admin and fulfil using the original or an equivalent verified replacement. Refund for failure to fulfil only if Travelly cannot fulfil the protected journey. Material changes still require Passenger acceptance. Passenger-initiated cancellation retains its separate accepted policy. |
| D09 | Trip start is POST /api/v1/trips/{trip_id}/start. |
| D10 | Public-safe search/profile/departure/social/AI discovery reads may be public. Booking, payment, tracking, document and management actions require authentication plus applicable authorization. AI discovery may use POST without becoming a booking/mutation permission. Provider callbacks use provider signatures/credentials, not a Passenger login. |
| D11 | Authenticated users may access their own documents; Owners may access owned vehicle documents; Admin access requires authorized verification permission. Private documents/keys/signed URLs never appear in public responses. |
| D12 | General promotions/coupons remain Phase 2. Only bounded NBP operational configuration is included. |
| D13 | Travelly operates in Sri Lanka but accepts foreign passengers. Registration must support international mobile numbers. The UI uses a searchable country-code selector, defaulting to Sri Lanka (+94). The backend normalizes and stores all phone numbers in E.164 format. Contact verification remains separate from role approval. Actual SMS delivery/verification provider integration is deferred to the Contact Verification module. |

Telephony/IVR, subscriptions, secondary-owner delegation and general promotions/coupons are **not part of the current NBP**. Conversational AI calling, production wallet and automatic cross-owner settlement remain excluded. Promotional Reel content is not a promotion/coupon billing engine and remains within the existing Social scope.

### International-passenger registration clarification (D13)

The user selects a country/region and calling code, then enters the national number without duplicating the calling code. The selector supplies explicit UI context; it does not imply Sri Lankan nationality or authorize backend guessing. With Sri Lanka (+94) selected, valid `771234567` and local `0771234567` entry both become `+94771234567`, removing only the Sri Lankan national trunk zero. Foreign numbers use their own region's rules; leading zeroes are not globally stripped. Invalid/unknown calling codes, incomplete numbers and invalid duplicated-code entry are validation failures, not silently repaired contacts.

The existing API still receives only `phone_e164` for the phone contact. A direct local-only API number remains 422 `VALIDATION_ERROR`; canonical equivalents collide under the existing phone uniqueness constraint and return generic 409 `CONTACT_ALREADY_REGISTERED`, without merging accounts. A selected code alone is not a contact; email-only registration remains allowed. Detailed UI/API validation and Sri Lankan/foreign acceptance scenarios are normative in Auth contract section 4.1 and AUTH-19 through AUTH-28.

The previous Auth eight-digit global minimum can exclude valid foreign numbers and is superseded by country-specific validity and the 15-digit E.164 maximum. The Auth dictionary revises only the existing phone syntax check; no new table or column is required. This decision does not apply a live migration or change application code. Future implementation must align the current check and validators before claiming full international-input support.

D01/D02 remain binding: every registration receives APPROVED Passenger membership, Passenger remains the default workspace, contact-verification timestamps remain separate, and Owner/Driver applications have independent PENDING/APPROVED/REJECTED/SUSPENDED states. A valid/normalized foreign number neither verifies ownership nor grants an operational role. SMS delivery, OTP/provider integration and verification callbacks remain deferred to Contact Verification. Registration country selection does not expand the current IN_APP/EMAIL operational notification channels or reintroduce IVR.

### Admin Application Review Business Decision Gate - accepted 25 October 2026

The project owner approves all nine recommendations below. **D01-D09 in this subsection are the Admin Review gate identifiers, referenced elsewhere as AR-D01 through AR-D09.** They do not renumber or replace the earlier project-wide D01-D13. The text of each accepted decision is recorded verbatim:

D01. Individual Owner accounts only in the current NBP. Full company-account onboarding is deferred. A company-owned vehicle may be managed by an authorized individual.

D02. Owner requires NIC or Passport plus ownership/authorization evidence. Driving licence is required only for Driver approval.

D03. Owner approval requires applicant-owned vehicle registration evidence, or registered-owner/company authorization evidence. Vehicle verification remains separate.

D04. Driver requires a Sri Lanka-issued driving licence plus NIC or Passport. Foreign-driver licence approval is deferred.

D05. A document marked NEEDS_CORRECTION keeps the related role application PENDING. Role rejection is a separate Admin decision.

D06. Every eligible APPROVED Admin may review applications, except self-review/self-approval.

D07. Private documents are delivered only through an authenticated backend streaming endpoint with authorization checked for every request. No public/signed URL approach in this NBP.

D08. Decision history uses approved restricted durable audit infrastructure outside application tables. It must retain actor, timestamp, previous status, new status and full applicant-visible reason. If durable audit storage cannot confirm the event, the Admin status decision must fail safely and must not commit.

D09. Add narrow dedicated Admin role-application queue and detail GET API contracts, plus the protected document-streaming endpoint.

Accepted Vehicle Document UI rule (AR-VUI):

- Required: all relevant vehicles must provide it before submission/verification.
- Required for your case: mandatory only when the applicant/registered-owner/company situation requires it.
- Optional: may be uploaded but never blocks submission or verification.
- Exact vehicle operating-document checklist remains for the future Vehicle Management Contract.

These labels are presentation/eligibility rules, not new table columns, document states or role states. Do not make an optional upload a hidden blocker. The role-application checklist below does not freeze the future vehicle operating-document checklist.

#### Binding application, evidence and review interpretation

- A company is never a separate Travelly account in this NBP. Use the existing individual applicant and existing evidence types. BUSINESS_REGISTRATION and BANK_PROOF remain planned document types, but this decision does not make them mandatory for individual Owner/Driver approval or start company onboarding.
- Owner identity is one verified NIC or PASSPORT. If the applicant is the registered owner, require their VEHICLE_REGISTRATION evidence; otherwise require OWNER_AUTHORISATION evidence from the registered owner/company. Before vehicle onboarding, store this applicant-owned evidence with documents.user_id and vehicle_id NULL. No vehicle row is fabricated to permit Owner approval. A later vehicle and its own verification remain separate.
- Driver identity is one verified NIC or PASSPORT plus verified DRIVING_LICENCE with issuing_country LK. Do not infer citizenship or licence issuer from an international registration phone number. No new age, licence-class, company or bank fields/conditions are added by this gate.
- Every required evidence item must belong to the applicant, match the required type/subject and be APPROVED, current and unexpired where expiry applies before role approval. NEEDS_CORRECTION is a document outcome only; the role stays PENDING unless an Admin separately rejects it.
- Eligible APPROVED Admin means a currently valid Auth session, an account permitted by Auth and a current APPROVED ADMIN membership. No additional reviewer-flag table, reviewer subset or contact-verification prerequisite is introduced. Exclude the reviewer's own applications from the queue/counts; deny own review detail and all self role/document review decisions. Separate personal document reads remain available through ownership authorization.
- REJECTED resubmission reuses the same role row, resets to PENDING and clears current decision fields only after complete prior history is durably preserved. PENDING/APPROVED/SUSPENDED duplicate submission remains 409 ROLE_ALREADY_REQUESTED. SUSPENDED cannot self-resubmit or reinstate; it retains Passenger access and independent other-role eligibility.
- The approved audit channel is restricted durable infrastructure outside the application tables. It may retain full applicant-visible rejection/suspension/correction reasons, previous/new status, actor and time. This is a narrow exception to Auth's ordinary metadata-only logging wording, not permission to log reasons, request bodies, credentials or files in ordinary logs. Approval/start-review events have a NULL reason where no reason is accepted. Current mutation columns are not historical audit.
- Private file bytes are streamed by the authenticated backend on every request. No public URLs, signed URLs (including internal provider-signed retrieval), redirects to storage, URL credentials or reusable download grants. Use private server storage credentials; the existing secure_file_url response name, when present, refers only to the authenticated backend route.
- AR-D09 freezes GET /api/v1/admin/role-requests, GET /api/v1/admin/role-requests/{role_id} and GET /api/v1/documents/{document_id}/file. The exact DTOs, query bounds, authorization, expected-version PATCH transport and errors are in [Admin Review Prerequisites](../04-MODULE-CONTRACTS/04-ADMIN-REVIEW-PREREQUISITES.md), sections 3-7. Those narrow module refinements supplement the original API sources; the later TR-D08 technical stage synchronizes the workbook without renumbering existing endpoints.

Passenger permanence/default workspace, the four role statuses, independent Owner/Driver approvals, contact-verification separation, approved-only workspace switching and international Passenger registration remain unchanged. Telephony/IVR, subscriptions, secondary-owner delegation and general promotions/coupons remain excluded.

### Accepted Technical Readiness Decisions - 25 October 2026

The owner approves the technical recommendations, with the explicit final choice below excluding PostgreSQL prepared transactions. TR-D01-TR-D08 are technical identifiers; project D01-D13 and AR-D01-AR-D09 business decisions are preserved verbatim.

| ID | Binding accepted technical approach |
|---|---|
| TR-D01 | Freeze every existing planned table/column in 02C, exactly 20 application tables. Vehicles is defined before documents. Preserve the exact implemented users/user_roles Auth baseline; optional source-planned user fields remain separate future target, not new Auth input. |
| TR-D02 | Existing POST /api/v1/documents uses authenticated multipart upload, one file, PDF/JPEG/PNG only, maximum 10485760 bytes (10 MiB); actual-content validation, safe display filename and opaque server-generated storage key. Full request/response/error boundaries are 03C/03D and prerequisites section 4.5. |
| TR-D03 | Local development private storage is outside repository/webroot. Backend authorization/streaming only; no public/signed URLs or static private-file mount. Durable file/metadata placement, failed-upload cleanup and reference-aware crash/orphan recovery are mandatory. |
| TR-D04 | Restricted append-only durable audit journal outside application tables retains correlation ID, actor, timestamp, target, previous/new status, full reason, existing versions, PostgreSQL xid8 and intent/committed/aborted outcome. These are infrastructure metadata, not new SQL columns or role states. |
| TR-D05 | Durable complete audit intent acknowledgement must succeed before an Admin decision commits. Failure/uncertainty before COMMIT returns safe 503 and rolls back with no status change. Rejected resubmission must preserve full prior reason/evidence through the same guard before clearing fields. |
| TR-D06 | Use ordinary PostgreSQL transactions, never two-phase commit/prepared transactions in this NBP. Crash/connection-loss recovery reconciles journal xid8 with PostgreSQL transaction outcome; unresolved/old/unknown outcome fails closed, never inferred from a matching row. Do not claim rollback after a commit or automatically apply the decision twice. |
| TR-D07 | Controlled Admin provisioning uses an explicit offline local-development command for an existing registered account; production uses a restricted operator process with target confirmation and audit. No public Admin signup/UI, startup grant, default password, second login or invented permission table. |
| TR-D08 | Synchronize matrix/OpenAPI/DTOs/Bearer/binary/error/version contracts and the technical acceptance checklist. Documentation gate approves building the limited Admin/private-document/audit dependencies; runtime migrations/configuration/security/recovery tests must pass before review enablement. No application code/live schema is changed by this freeze. |

The exact technical protocol is [prerequisites sections 4.5 and 7](../04-MODULE-CONTRACTS/04-ADMIN-REVIEW-PREREQUISITES.md). [02C](../02-DATABASE/02C-TRAVELLY-PHYSICAL-DATA-DICTIONARY.md), [03C](../03-API/03C-TRAVELLY-ADMIN-REVIEW-OPENAPI.json), [03D](../03-API/03D-TRAVELLY-ADMIN-REVIEW-API-CONTRACT.md) and [05 acceptance](../04-MODULE-CONTRACTS/05-ADMIN-REVIEW-TECHNICAL-ACCEPTANCE.md) are the frozen corresponding artifacts. Unknown future business catalogues are not invented to complete physical types; later-module writes remain gated by their own policies/API contracts.

### Canonical catalogues

- Role approval: PENDING, APPROVED, REJECTED, SUSPENDED.
- Booking: REQUESTED, AWAITING_DRIVER, OWNER_ACTION_REQUIRED, CONFIRMED, IN_PROGRESS, COMPLETED, REJECTED, CANCELLED.
- Driver assignment: NOT_REQUIRED, PENDING, ACCEPTED, REJECTED, CANCELLED.
- Trip: READY, IN_PROGRESS, BREAKDOWN, ASSISTANCE_REQUIRED, COMPLETED, CANCELLED.
- Passenger payment: PENDING, PROCESSING, PAID, CASH_AWAITING_CONFIRMATION, FAILED, REFUNDED, PARTIALLY_REFUNDED.
- Vehicle availability: DRAFT, PENDING_VERIFICATION, ACTIVE, BOOKED, ON_TRIP, MAINTENANCE, SUSPENDED, INACTIVE. Vehicle verification retains its separate DRAFT, SUBMITTED, APPROVED, REJECTED, SUSPENDED catalogue from 02A.
- Scheduled Ticket seat: AVAILABLE, HELD, BOOKED, BLOCKED.

Owner settlement retains separate settlement meaning, including OWNER_PAYABLE and OWNER_PAID; the complete settlement catalogue remains subject to the later module physical dictionary. Provider stages such as AUTHORIZED/CAPTURED and allocations must not be mistaken for booking or Passenger payment enums. No new settlement enum or table is invented here.

## 3. Complete supersession register

Document aliases resolve to these exact files relative to docs:

- 00: `00-READ-FIRST/00-TRAVELLY-BACKEND-BUILD-READINESS.md` (formerly `.md.md`).
- 01: `01-PROPOSAL/01-TRAVELLY-PROJECT-PROPOSAL-NBP-V1.0.pdf.pdf`.
- 02A: `02-DATABASE/02A-TRAVELLY-DATABASE-ARCHITECTURE-FINAL-20-TABLES.pdf.pdf`.
- 02B: `02-DATABASE/02B-TRAVELLY-NBP-DATABASE-DESIGN-LECTURER-TEMPLATE.pdf.pdf`.
- 03A: `03-API/03A-TRAVELLY-NBP-API-PLAN.pdf.pdf`.
- 03B: `03-API/03B-TRAVELLY-API-ENDPOINT-MATRIX-96-ENDPOINTS.xlsx.xlsx`.

Each row's replacement is normative. Short quotes identify the superseded source fragment; replacements apply to the identified field/rule, not unrelated surrounding content. Rows covering multiple locations apply at every named location. Entries described as additions resolve incomplete wording rather than falsely claiming an absent quote existed. This register remains the correction authority even where the narrower authorized workbook edit leaves an explanatory cell unchanged.

| ID | Document and location | Superseded statement / incomplete text | Required replacement / clarification |
|---|---|---|---|
| C01 | 00 header Excluded | Subscription billing / delegation / AI calling / wallet / settlement list | Explicitly exclude Telephony/IVR, subscriptions, secondary-owner delegation and general promotions/coupons; retain other exclusions. |
| C02 | 00 section 1 Passenger | Every account receives PASSENGER role | Every registered account receives Passenger membership; contact verification is separate; Owner/Driver approvals independent. |
| C03 | 00 section 3 Payment | Single Payment heading/catalogue | Label as Passenger payment; Owner settlement is a separate field and cannot overwrite it. |
| C04 | 00 section 3 Vehicle availability | Catalogue lacks separation note | Retain canonical availability values and require separate verification_status/availability_status and both eligibility checks. |
| C05 | 00 section 4 document Owner cell | Owned vehicle documents | Own personal documents and owned vehicle documents. |
| C06 | 00 section 7 reconfirmation rule | Missing protected-deadline guard | Retain no-response protection; append D08 Admin escalation/original-or-equivalent fulfilment/refund-only-if-unfulfillable rule. |
| C07 | 00 section 8 authorization | Protected-endpoint rule without public boundary | Apply D10 public-safe versus authenticated business-operation boundary and signed-provider exception. |
| C08 | 00 section 8 documents | Incomplete owner-access rule | Apply D11; own personal/owned vehicle documents, authorized Admin verification, never public. |
| C09 | 00 section 9 item 7 | IVR not implemented unless later separately approved | No current implementation/exposed IVR route; IN_APP and EMAIL only. |
| C10 | 01 p3 section 3 summary | Conditional departures resolved by commitment/replacement or refund | Apply D08; missed deadline alone neither cancels nor refunds protected journey. |
| C11 | 01 p6 section 5.1 Attendance Request | selected message/email actions or optional keypad calls | Authenticated in-app/email responses only; IVR deferred. |
| C12 | 01 p6 section 5.1 Telephony actor | If selected, deliver 1/2 prompts; optional NBP channel | Future reference only, no calls/callbacks; classification Deferred - outside current NBP. |
| C13 | 01 p8 External Provider Diagram communication box | SMS / Email / Optional IVR; simple 1/2 confirmation | In-app Notifications / Email; authorized notices, delivery status and authenticated responses; IVR deferred. |
| C14 | 01 p9 F11 | Conditional departure and published refund terms | Protected fulfilment/Admin escalation/published refund terms; missed deadline does not automatically cancel. |
| C15 | 01 p9 F18 | current channels, pending optional keypad IVR, cash | In-app/email attendance and authorized cash verification; IVR deferred. |
| C16 | 01 p10 Protected Ticket Fulfilment diagram | Owner decision before deadline; unfulfillable disruption refund/support | Minimum-seat/deadline issue escalates to Admin; booking remains confirmed; original/equivalent verified fulfilment, material-change acceptance, refund only if Travelly cannot fulfil. |
| C17 | 01 p11 FR05 | pricing/promotion versions | Published NBP pricing and accepted fare-policy versions; general promotions/coupons Phase 2. |
| C18 | 01 p12 FR12 | fare, commission and promotion policies | Bounded NBP fare/commission/operational settings with historical terms preserved; general promotion/rules engine Phase 2. |
| C19 | 01 p12 FR18 | Full refund when uncommitted trip misses deadline | Apply D08; full applicable refund after reconciliation only if protected journey cannot be fulfilled; separate Passenger cancellation policy retained. |
| C20 | 01 p16 architecture diagram provider box | Messaging/IVR | Email; in-app notices handled by application; IVR deferred. |
| C21 | 01 p18 section 14 Admin summary | POST /admin/policies; generic controlled settings | Use bounded service-setting/verification operations in 03B; promotion/coupon management and general policy engine Phase 2. This does not create a new endpoint. |
| C22 | 01 p23 risk Conditional departure fails | full refund for uncommitted missed deadline | Apply D08; deadline escalates while booking stays protected; refund only if Travelly cannot fulfil after reconciliation. |
| C23 | 02A p2 section 1.1 notices | in-app, email, message and automated IVR outcomes | IN_APP and EMAIL delivery/authenticated response outcomes only; IVR deferred. |
| C24 | 02A p2 section 1.2 exclusions | Missing scripted IVR and promotion exclusions | Explicitly exclude current IVR calls/callbacks and general promotions/coupons; bounded configuration only. |
| C25 | 02A p3 section 3 notifications catalogue | delivery/read state and IVR response outcome | In-app/email delivery/read/authenticated action-response outcome; IVR deferred. |
| C26 | 02A p4 section 4.2 approval_status | REQUESTED, UNDER_REVIEW, APPROVED, REJECTED, SUSPENDED | PENDING, APPROVED, REJECTED, SUSPENDED. |
| C27 | 02A p5 section 4.2 Passenger | may be automatically approved after verification | Every registration receives Passenger membership; verification separately stored, not role approval; independent Owner/Driver states. Auth contract fixes automatic Passenger approval. |
| C28 | 02A p6 section 4.4 availability | INACTIVE, AVAILABLE, HELD, BOOKED, ON_TRIP, MAINTENANCE, BLOCKED | Canonical vehicle availability catalogue above; verification separate; seat HELD belongs to scheduled_trip_seats, dated blocks to vehicle_records. |
| C29 | 02A p8 section 4.9 deadline | No action by deadline commits original trip | No action escalates to Admin, not automatic commitment/cancellation; original/equivalent verified fulfilment; refund only if unfulfillable. |
| C30 | 02A p9 section 4.12 bookings.status | DRAFT, HOLDING, OWNER_ACCEPTED, DRIVER_ASSIGNMENT_PENDING, READY, refund/failure states mixed with booking states | Replace entire booking catalogue with canonical booking values. Hold expiry is seat state; refund/payment separate. |
| C31 | 02A p9 section 4.12 payment_status_snapshot | No distinction from settlement | Snapshot reflects Passenger payment only; settlement does not overwrite it. |
| C32 | 02A p10 section 4.14 assignment | PENDING, ACCEPTED, DECLINED, REASSIGN_REQUIRED, CANCELLED | Canonical assignment catalogue; rejection REJECTED, booking OWNER_ACTION_REQUIRED. |
| C33 | 02A p10 section 4.14 trip status | PREPARING, READY, STARTED, PAUSED, BREAKDOWN, COMPLETED, CANCELLED | Canonical trip catalogue; start -> IN_PROGRESS. |
| C34 | 02A pp10-11 section 4.14 tracking | STARTED/PAUSED/BREAKDOWN with ACTIVE/STALE | Authorized participants only during IN_PROGRESS/BREAKDOWN/ASSISTANCE_REQUIRED with ACTIVE/STALE tracking; end sharing on completion/cancellation. |
| C35 | 02A p11 section 4.15 status | INITIATED/AUTHORIZED/CAPTURED/ALLOCATED/TRANSFERRED/.../OWNER_PAYABLE/OWNER_PAID mixed | Separate Passenger payment and Owner settlement fields; canonical Passenger values; preserve provider/allocation details and linked immutable financial transactions separately. |
| C36 | 02A p12 section 4.17 channels | IN_APP, EMAIL, SMS_MESSAGE, AUTOMATED_IVR | IN_APP, EMAIL for current NBP; IVR deferred and unexposed. |
| C37 | 02A p13 section 4.17 IVR rules | automated press 1/2 script | Authenticated in-app/email responses only; retain no-response protection; IVR deferred. |
| C38 | 02A p15 section 6.1 registration | users row and approved Passenger role without explicit contact distinction | users plus Passenger membership; separate verification; Owner/Driver PENDING applications. Automatic Passenger approval is defined in Auth contract. |
| C39 | 02A p15 section 6.3 checkout | HELD expiry plus booking/traveller/payment attempts | Hold is scheduled_trip_seats HELD/hold_expires_at with existing linkage; related booking only canonical states; full online payment before seat confirmation; release affected unconfirmed hold only. |
| C40 | 02A pp15-16 section 6.4 fulfilment | refund/support after permitted disruption | Apply D08, preserving material-change acceptance; missed deadline alone no cancellation/refund. |
| C41 | 02A p16 section 6.5 conflicts | HELD, CONFIRMED, DRIVER_ASSIGNMENT_PENDING, READY, IN_PROGRESS mixed | Use domain-specific catalogues: AWAITING_DRIVER replaces obsolete booking pending state; READY is trip, HELD is seat; check departures/accepted assignments/availability blocks separately. |
| C42 | 02A p18 section 7.1 Role row | REQUESTED -> UNDER_REVIEW -> APPROVED/REJECTED | PENDING -> APPROVED/REJECTED; APPROVED -> SUSPENDED; verification separate. |
| C43 | 02A p18 section 7.1 Booking row | DRAFT/HOLDING -> OWNER_ACCEPTED/DRIVER_ASSIGNMENT_PENDING -> READY | Private hire REQUESTED -> CONFIRMED for eligible self-drive or AWAITING_DRIVER for external assignment; acceptance -> CONFIRMED; rejection -> OWNER_ACTION_REQUIRED; reassignment -> AWAITING_DRIVER; Owner rejection -> REJECTED; operation CONFIRMED -> IN_PROGRESS -> COMPLETED; cancellation CANCELLED under policy. Ticket holds/payment states separate. |
| C44 | 02A p18 section 7.1 Assignment/operation row | DECLINED/REASSIGN_REQUIRED; PREPARING/STARTED/PAUSED | Use canonical assignment and trip catalogues; pending offer -> ACCEPTED/REJECTED; READY -> IN_PROGRESS on start; rejection returns booking to OWNER_ACTION_REQUIRED. NOT_REQUIRED only for applicable services. |
| C45 | 02A p18 section 7.1 Payment row | one linear capture/allocation/Owner payout status | Independent Passenger payment and Owner settlement fields/transitions; payable after completion/reconciliation; linked financial history retained. |
| C46 | 02A p18 section 7.1 Vehicle/Departure guards | approval-only publication; generic minimum-seat deadline guard | Verify both vehicle fields and document eligibility; deadline guard must implement D08. |
| C47 | 02A p20 section 10 access | Passenger bookings/public marketplace; generic Admin access | Apply D10/D11 including own documents, owned vehicle documents, authorized verification and public-safe discovery. |
| C48 | 02A p21 section 12 IVR test | No-response to IVR does not release inventory | No-response to in-app/email attendance neither cancels nor releases; no current IVR implementation. |
| C49 | 02B p3 Step 2 shared account | Passenger access; independent Owner/Driver approval without verification detail | All registration gets Passenger membership; contact verification separate; independent canonical role approval statuses. |
| C50 | 02B p4 Step 3 and p10 Step 10 user_roles | generic approval_status | Explicit D01 catalogue; contact verification belongs to users, not role state. |
| C51 | 02B p4 Step 3 and p10 Step 10 vehicles | media/statuses | Distinct verification_status and availability_status, each using its own catalogue and eligibility checks. |
| C52 | 02B p4 Step 3 and p11 Step 10 bookings/seats | generic booking status and hold booking/expiry | Canonical booking states; no DRAFT/HOLDING booking state; seat HELD/hold_expires_at; release unconfirmed holds only. |
| C53 | 02B p4 Step 3 and p11 Step 10 trips | generic assignment/status | Explicit canonical assignment/trip catalogues, IN_PROGRESS start, REJECTED assignment and OWNER_ACTION_REQUIRED booking. |
| C54 | 02B p4 Step 3 and p11 Step 10 payments | amounts/currency/status | Separate Passenger payment status and Owner settlement status; canonical Passenger catalogue; related refunds/reallocations/payouts remain payments rows. |
| C55 | 02B p8 Figure 1 payments entity | type / amount / status | type / amount / payment status / Owner settlement status; same entity/relationships. |
| C56 | 02B p13 baseline | Missing resolved deadline/access rules | Append D08/D10/D11; no additional table. |
| C57 | 03A p4 Step 3 PATCH example | PATCH /api/v1/trips/{trip_id}/start | PATCH example becomes /api/v1/vehicles/{vehicle_id}; trip start is POST /api/v1/trips/{trip_id}/start. |
| C58 | 03A p7 Role DTO | generic decision/reason/version | Applications PENDING; permitted review APPROVED/REJECTED/SUSPENDED; Passenger at registration; contact verification separate. |
| C59 | 03A p7 Vehicle DTOs | missing explicit field distinction | Responses expose verification_status and availability_status separately; no client self-approval; use canonical availability. |
| C60 | 03A p7 SeatMap/Booking/Assignment DTOs | hold_expiry; generic status/assignment_status | hold_expires_at; canonical booking/assignment catalogues; temporary hold is seat state. |
| C61 | 03A p7 BookingResponse and p8 payment DTOs | payment summary without separate settlement | Separate Passenger payment and authorized Owner settlement fields; neither replaces trip/booking status. |
| C62 | 03A pp8-9 Final rules 1/4/5/13 | generic identity/payment/replacement/configuration rules | Append D10 public boundary, D05 separate financial fields, D08 deadline protection and D12 promotions exclusion respectively. |
| C63 | 03A p9 Final rules | missing full document-owner rule | Append D11, including owned vehicle/authorized Admin verification and no public private-document exposure. |
| C64 | 03B #1 E/G/I; #7-9 G/I | generic account/role state responses | Registration includes Passenger, contact verification separate; Owner/Driver request PENDING; review canonical role states. Exact six Auth contracts now resolve generic entries. |
| C65 | 03B #11-12 G/K | Yes - Owner/Driver/Admin | Authenticated own-document user, owned-vehicle Owner or authorized verification Admin; includes pending applicants; never public. |
| C66 | 03B #15/#24/#32/#38/#79/#81 G/K/J | Yes - Public/authorized or Public/Owner; unconditional auth | Public-safe published responses may be anonymous; private detail requires authorization. 401/403 only for protected variants. Visibility/moderation rules still apply. |
| C67 | 03B #90-91 G/K/J | Yes - Public/Passenger plus unconditional auth/errors | Public/authenticated rate-limited AI discovery; bounded validation and real inventory only, no booking mutation. Remove unconditional 401/403; keep POST. |
| C68 | 03B #19-20/#34/#36 G/I | generic transition without separation | Evaluate verification_status/availability_status independently; Admin review only authorized verification; publication also checks availability/documents. |
| C69 | 03B #40 E/I | hold seats and create draft booking | Seat HELD/hold_expires_at; related booking only canonical catalogue, no DRAFT/HOLDING booking status. |
| C70 | 03B #41 E/G | release unconfirmed hold, generic validation | Release authenticated Passenger's applicable HELD rows only; do not cancel confirmed booking or release BOOKED inventory due to expiry/release alone. |
| C71 | 03B #48-50/#52-53 G/I | descriptive declined/awaiting/confirmed states | #48 booking REJECTED; #49 assignment ACCEPTED/booking CONFIRMED; #50 PENDING/AWAITING_DRIVER; #52 ACCEPTED/CONFIRMED; #53 REJECTED/OWNER_ACTION_REQUIRED. Existing assignment-decline URL need not change. |
| C72 | 03B #60-62/#64 G/I | generic ready/start/location/complete states | READY readiness; POST start -> IN_PROGRESS; only assigned active operator updates allowed active states; completion COMPLETED and sharing ends. |
| C73 | 03B #54-58/#96 G | no resolved protected-deadline guard | Apply D08 with verification/schedule/route/capacity/luggage/quality checks and material-change Passenger acceptance. |
| C74 | 03B #65-70 G/I | no explicit payment/settlement separation | Independent Passenger payment and authorized Owner settlement fields, canonical Passenger values, linked transactions; settlement/reallocation cannot overwrite payment. |
| C75 | 03B #77 F/G | generic channel | IN_APP or EMAIL only; authenticated responses; no-response does not cancel/release; IVR deferred. |
| C76 | 03B #78 I/J | future outcome and 501 while disabled | Deferred reference only; no current implemented/exposed route or runtime response contract. |
| C77 | 03B #22-23 G | generic settings validation | Bounded NBP service/operational settings only; general promotions/coupons/rules engine Phase 2; preserve accepted history. |
| C78 | 02-TRAVELLY-AUTH-MILESTONE-CONTRACT.md section 4 phone_e164 / registration UI | require explicit international +country-code input; reject ambiguous local-only numbers, without a defined country-selector UI | Registration UI uses a searchable country/region/calling-code selector defaulting to Sri Lanka +94 and a national-number field without repeated calling code. Normalize Sri Lankan local trunk entry with explicit selector context; send existing phone_e164 in E.164 form. Backend local-only API input remains invalid. Follow section 4.1 validation, generic duplicate 409 and AUTH-19 through AUTH-28; SMS provider integration remains deferred. |
| C79 | 02-TRAVELLY-AUTH-MILESTONE-CONTRACT.md section 2.1 ck_users_phone and section 4 phone length | `^[+][1-9][0-9]{7,14}$`; at most 15 digits, at least 8 in this release | Replace the target existing-column syntax check with `^[+][1-9][0-9]{1,14}$` and use maintained country-specific API validation plus the 15-digit E.164 maximum; do not exclude valid short foreign numbers with an arbitrary eight-digit floor. No new table/column; this is a dictionary correction for future implementation, not an applied migration. |
| C80 | 02A printed p5 section 4.2; Owner/Driver Contract v1.0 sections 4/12; Admin Review v1.0 sections 4/11; prerequisites v1.0 section 2.3 | Owner identity/licence and ownership/authorisation; exact evidence checklist unresolved | AR-D02/D03: Owner NIC or PASSPORT plus own VEHICLE_REGISTRATION or registered-owner/company OWNER_AUTHORISATION; no Owner driving-licence requirement. Applicant-owned documents before vehicle onboarding; separate vehicle verification. |
| C81 | 01 printed p2 Owner actor; 02A printed p5 company-conditional Owner description; prerequisites v1.0 sections 2.3/9 M1 | Owner is an individual or business; company fields conditional; company/individual onboarding branch not frozen | AR-D01: individual accounts only; company-owned vehicle managed by authorized individual. Full company accounts deferred; no company user or new company field/table. |
| C82 | 02A printed p5 Driver eligibility; Owner/Driver v1.0 section 4; prerequisites v1.0 sections 2.3/9 M1 | Driver licence required; exact issuer/identity policy unresolved | AR-D04: Sri Lanka-issued DRIVING_LICENCE (issuing_country LK) plus NIC or PASSPORT. Foreign-driver licence approval deferred; foreign Passenger registration remains supported. |
| C83 | Owner/Driver v1.0 section 7; Admin Review v1.0 section 4; prerequisites v1.0 section 2.4 | Document outcomes defined without explicit NEEDS_CORRECTION effect on role | AR-D05: NEEDS_CORRECTION keeps role PENDING. Role rejection requires a separate authorized decision. |
| C84 | Auth sections 2.2/3 Admin authorization; Owner/Driver v1.0 section 6; Admin Review v1.0 sections 2/11; prerequisites v1.0 sections 3/6 | Self-approval prohibited; finer verification-permission mapping unresolved | AR-D06: every eligible APPROVED Admin may review; no self-review, self-approval or self document verification. No new permission fields; own personal document retrieval remains allowed. |
| C85 | 02A printed p5 section 4.3 and p20 section 10; 03A printed p9 signed storage; 03B #12 secure document retrieval; prerequisites v1.0 section 2.4 internal signed retrieval; Admin Review v1.0 section 4 | Private files use short-lived access URLs; signed URLs expire quickly; signed/short-lived retrieval including possible internal provider-signed URLs | AR-D07: authenticated backend streaming only, per-request ownership/Admin authorization, no storage redirect or public/signed URL approach, including internal signed retrieval. |
| C86 | Auth implementation amendment and section 7 logging/resubmission; Owner/Driver v1.0 sections 5/6; Admin Review v1.0 section 7; prerequisites v1.0 section 7.2 | Preserve prior evidence in safe metadata logs; full historical reason store unresolved | AR-D08: retain full reason and actor/time/previous/new status in approved restricted durable audit infrastructure outside application tables; confirmation required before status commit. Ordinary logs remain metadata-only. |
| C87 | 02B printed p12 infrastructure logs/p13 advanced audit Phase 2; prerequisites v1.0 section 9 M2 | No selected approved durable full-reason history mechanism; advanced audit deferred | AR-D08 approves bounded NBP role/document decision history in restricted durable infrastructure. Provider/commit-recovery deployment remains technical; no general audit engine or application history table. |
| C88 | 03A/03B original endpoint list; Admin Review v1.0 sections 3/8/11; prerequisites v1.0 sections 3/9 M5 | Queue/detail reads and protected file operation missing from original 96-entry matrix; exact contracts awaiting acceptance | AR-D09: add the three dedicated GET contracts named above; prerequisites sections 3-7 freeze exact requests, responses, errors and version transport. Retain existing PATCH review paths. The initial business freeze left the workbook unchanged; later synchronization is recorded in C95/TR-D08. |
| C89 | Owner/Driver v1.0 section 12; Admin Review v1.0 section 11; prerequisites v1.0 sections 2.3/7.2/9 | Evidence, reviewer eligibility, retrieval and history business decisions remain unresolved | AR-D01-D09 resolve those business decisions. Revised module contracts are final business/API specifications; Readiness Stage B and section 9 technical prerequisites still govern implementation. |
| C90 | Vehicle-document UI in supporting designs; Owner/Driver document requirements; prerequisites v1.0 section 2.3 | No frozen Required / Required for your case / Optional label semantics | Apply AR-VUI verbatim. Optional never blocks submission/verification; exact vehicle operating checklist is deferred to Vehicle Management. |
| C91 | 02A sections 2.1/4; 02B grouped relational dictionary; prerequisites v1.1 sections 2.2/9 T01 | Logical column/type families but incomplete physical per-column specification | TR-D01: 02C freezes all 20 physical target definitions with explicit types/null/defaults/FKs/actions/CHECKs/indexes/audit/version/lifecycle. Original logical architecture and table identities are unchanged. |
| C92 | 03B #10 upload body; Auth generic JSON boundary when applied beyond its six APIs | Generic upload-token/file input with no exact multipart contract | TR-D02: existing POST /documents uses authenticated multipart with one file and exact 10 MiB/content/owner limits; 03C/03D define mappings/errors. Auth/review JSON remains 8 KiB. |
| C93 | Prerequisites v1.1 sections 4.3/9 T04; Admin Review v1.1 sections 4/11 | Private ingestion/storage/cleanup specification still pending | TR-D03: freeze private external root, safe opaque keys, backend stream only and reference-aware cleanup/orphan recovery; implementation is a next-stage deliverable, not a missing business decision. |
| C94 | Prerequisites v1.1 section 7/9 T02; earlier conversational technical recommendation | Audit provider/commit-recovery details pending; PostgreSQL prepared transaction option previously recommended | TR-D04-D06: restricted append-only journal, confirmed durable intent before ordinary COMMIT and xid8 outcome reconciliation; no prepared transactions/two-phase commit. Uncertain post-COMMIT result is reconciled, not falsely reported as no-change 503. |
| C95 | 03B endpoint list/#9/#11-13; prerequisites v1.1 sections 3/6/9 T03 | Three accepted GETs not indexed; generic review/errors and signed detail purpose remain | Append 97 queue, 98 application detail, 99 protected stream; retain IDs 1-96; synchronize 9-13 with exact 03C/03D including version conflicts, multipart and structured errors. IVR stays inactive. |
| C96 | Readiness section 5 requested_owner_user_id/trip owner shorthand; 02A sections 4.12/4.14/4.15; Final section 4 open physical mappings | Requested/current/operating ownership and separate settlement physical mapping not fixed | 02C uses already planned bookings.requested_owner_user_id as original selected Owner and owner_user_id as current fulfilment Owner; trips.operating_owner_user_id is the architecture field behind the Readiness owner shorthand; payments.status remains Passenger state and accepted owner_settlement_status is separate. No new ownership/history entity or complete unapproved settlement catalogue. |
| C97 | 02A section 4.1 optional users fields; Auth section 2.1 deferred broader profile/provider columns; Admin Review section 2 bootstrap | Broader user physical target deferred; controlled bootstrap process unspecified | 02C separately defines source-planned provider/subject/date_of_birth/common_profile target without changing Auth APIs or requiring their migration for Admin. TR-D07 freezes offline/operator provisioning with existing membership columns and no public signup. |
| C98 | Owner/Driver v1.1 section 12; Admin Review v1.1 section 11; prerequisites v1.1 section 9; Final v1.2 section 5 | Admin documentation gate not yet passed because physical/API/audit technical specifications remain unfinished | TR-D08: 02C/03C/03D/04/05 and synchronized 03B complete the bounded Admin documentation gate: APPROVED FOR BUILD. Code/migrations/configuration/runtime tests remain required before enablement. No later business/module gate is waived. |

## 4. Stage-specific refinements and open boundaries

The updated Readiness section 11 replaces the old all-modules build-start condition: Register/Login may begin once the users/user_roles physical schema, exact Auth API and Auth acceptance tests are frozen. Other modules require the complete 20-table physical dictionary and corresponding APIs. The Auth contract is the frozen first-stage artifact; 02C now supplies the complete physical target for the other eighteen tables, without implementing them.

The six exact Auth API descriptions also supersede generic 03A pages 6-8 DTO examples and 03B #1-5/#8 status/input/response descriptions. Owner/Driver submission and review now also use the accepted AR-D01-D09 refinements and finalized module contracts. This documentation approval does not waive Stage B or implement their APIs.

Not settled by the accepted decisions: full Owner settlement enum/transitions; complete Ticket hold/checkout persistence mapping; verification channel/provider and recovery/MFA contracts; remaining later-module API payloads and business policies. These remain later-stage requirements, not reasons to add a table or silently implement another module. Source claims that the whole application is already implementation-ready are subject to the staged gate.

D13 settles international registration input and normalization, not contact ownership or SMS delivery. The Contact Verification module must later freeze its provider/delivery/verification contract. The earlier international-phone amendment changed Final Decisions and Auth only. The earlier Admin business finalization changed Final Decisions and module contracts 02/03/04. This technical stage changes only the documentation artifacts listed in TR-D08; application source, tests, migrations, frontend UI, original PDFs and live schema/configuration remain unchanged.

## 5. Technical documentation-stage change scope and verdict

Original PDFs are not overwritten/regenerated. Editable 03B now has 99 stable numbered entries: prior 1-96 retained, accepted reads appended as 97-99. Inactive references #47/#78 remain inactive; planned workbook active entries are 97, not a count of implemented backend routes. Targeted edits cover review/document/upload/version/error consistency and full-reason resubmission preservation; unrelated cells retain their values/styles.

02C defines exactly 20 planned application tables. 03C/03D freezes the corresponding bounded Admin/document API and 05 its technical acceptance checklist. No code, live database/configuration, migrations, tests or UI changes occur. Existing Auth and business decisions remain binding.

**Admin Application Review Technical Readiness Gate: APPROVED FOR BUILD.** This is documentation approval to implement the limited module and its prerequisites, not a production/deployment or runtime-test PASS. No unresolved specification blocks that bounded work; actual secure storage/journal adapters, affected migrations, controlled provisioning and acceptance execution are next implementation deliverables. Later booking/vehicle/payment/Social/verification modules retain their own business/API gates; the exact future settlement/record vocabulary and vehicle operating-document checklist are not invented here.


## Auth update accepted 26 October 2026 (AU-01 through AU-07)

These explicit user-approved rules supersede earlier conflicting Auth-only deferrals and password rules, without changing the one-account role model or adding a twenty-first table.

- AU-01: Trim only outer email whitespace; reject internal whitespace and invalid public-address syntax, including leading/trailing/consecutive local-part dots. Normalize email case consistently with CITEXT uniqueness; never remove provider dots or plus tags. Concurrent duplicates remain atomic; registration may give a helpful conflict, while login/recovery stay non-enumerating.
- AU-02: New/changed passwords use 12-128 Unicode code points, at least one uppercase, lowercase, decimal digit and punctuation/symbol, no whitespace or control characters. Do not trim, normalize or truncate. Existing passwords continue to authenticate under their existing Argon2id hashes.
- AU-03: New email/password accounts require single-use, expiring Travelly email verification before normal sessions/dashboard access. Email syntax or provider send acknowledgement does not verify contact ownership. Existing accounts remain usable and get a verification path. Unverified describes email state; retain the established PENDING_VERIFICATION account enum until trusted contact verification permits ACTIVE. Blocked/suspended/closed accounts are never reactivated by verification.
- AU-04: Configurable local capture/Brevo delivery, explicit captured/provider-accepted/failure/quota outcomes, rate-limited resends, no unsupported delivery guarantee. Secrets remain environment-only. Token state uses existing Redis infrastructure; never return email-link tokens in APIs or logs.
- AU-05: Google Identity Services validates signed tokens server-side and identifies users by issuer/provider plus stable subject. Only verified Gmail or verified hosted-domain Google email is authoritative; third-party Google email requires Travelly verification. New Google identities complete required registration details and terms before account creation. Phone verification stays separate.
- AU-06: Matching email NEVER links accounts. Authenticate the existing account, explicitly confirm linking and prove the Google identity; Profile supports the same flow. Existing roles, account ID and future bookings remain on that user. Reuse the planned users external_auth_provider/external_auth_subject pair with a unique constraint; no identity table.
- AU-07: Only approved Passenger membership is created by either registration method. Owner/Driver approval, account restrictions and private evidence rules remain independent.

Exact API, transitional schema and verification security are recorded in [Auth extension contract](../03-API/03E-TRAVELLY-AUTH-EXTENSION.md). Contact-required policy and recovery scope are resolved by AU-08/AU-09 below.


### Owner clarification accepted 26 October 2026 - AU-08 / AU-09

The owner explicitly selected: **Require email and phone for all new accounts** and **Add verified-email password recovery**. These choices resolve the pending conflicts above and supersede older email-only/phone-only NEW registration and recovery-deferral wording. Existing accounts remain usable regardless of missing contacts; neither login nor migration invents or verifies contacts. Both new registration methods require normalized email, valid international phone, full name and explicit terms acceptance.

Recovery: POST /api/v1/auth/password/forgot accepts email and always returns the same non-enumerating 202 response regardless of existence, verification, throttled recipient or provider outcome. It never claims delivery. Only an eligible account's already verified email receives a single-use 30-minute link. POST /api/v1/auth/password/reset accepts token and new password under AU-02, atomically consumes the token and locks the bound user; it updates the hash, clears password failure state, increments auth_version to revoke all old access/refresh sessions and requires a fresh login. Verified-email ownership can establish a password on the same Google account as well; it never unlinks Google, changes roles or creates a replacement account. Unverified-email/phone-only accounts cannot recover through this channel; the UI states this limitation without revealing account existence. Invalid/used/expired links share a safe response. Provider outages/quota handling never reveals whether an email exists.
