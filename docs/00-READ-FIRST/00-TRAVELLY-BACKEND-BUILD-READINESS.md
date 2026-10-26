# Travelly NBP — Backend Build Readiness Contract

**Status:** Staged pre-implementation baseline; Auth documentation frozen 23 October 2026  
**Scope:** One-month NBP, PostgreSQL, final 20 application tables  
**Excluded:** Telephony/IVR (deferred), subscriptions/billing, secondary-owner delegation, general promotions/coupons, conversational AI calling, production wallet, automatic cross-owner settlement

Read `01-TRAVELLY-NBP-FINAL-DECISIONS.md` for document precedence and the exact superseded PDF/API statements. That file overrides only its listed conflicts. Read `02-TRAVELLY-AUTH-MILESTONE-CONTRACT.md` for the frozen users/user_roles physical schema, six Auth APIs and acceptance tests. Original PDFs remain unchanged references.

## 1. Locked account and role model

- One person has one `users` account.
- Every registered account receives `PASSENGER` membership. Contact verification is stored separately from role approval; Owner and Driver approvals remain independent. The Auth milestone creates the Passenger role as `APPROVED` while the account is `PENDING_VERIFICATION` until trusted verification.
- The same account may also hold `OWNER` and `DRIVER` roles.
- `OWNER` and `DRIVER` approvals are independent.
- Driver eligibility requires approved, unexpired required documents.
- An Owner who wants to self-drive must also be an approved Driver.
- A multi-role user changes dashboard context through a role switcher; no second account is created.
- Owner self-drive is accepted from Owner Dashboard after eligibility and availability checks. The Owner does not need to repeat the acceptance in Driver Dashboard.
- External Driver assignments require the selected Driver to accept or reject.
- The NBP uses trip-specific Driver assignment. A permanent Owner–Driver network table is Phase 2.

## 2. Locked private-hire workflow

1. Passenger selects an Owner/vehicle and submits trip requirements.
2. Booking becomes `REQUESTED`.
3. Owner can `REJECT`, choose `SELF_DRIVE`, or `ASSIGN_DRIVER`.
4. Self-drive checks the Owner's approved Driver role, documents, schedule and vehicle availability.
5. Valid self-drive creates an accepted trip assignment and confirms the booking.
6. External assignment creates a pending trip assignment; booking becomes `AWAITING_DRIVER`.
7. Driver acceptance confirms the booking. Driver rejection returns it to `OWNER_ACTION_REQUIRED`.
8. Only the assigned eligible Driver can start and complete the trip. Start uses `POST /api/v1/trips/{trip_id}/start` and sets trip status to `IN_PROGRESS`; assignment rejection uses `REJECTED`.
9. Passenger and Owner can track the active trip.
10. Completion stops tracking and exposes the authorized payment/trip summary.

## 3. Required status catalogues

### Role approval

`PENDING`, `APPROVED`, `REJECTED`, `SUSPENDED`

### Booking

`REQUESTED`, `AWAITING_DRIVER`, `OWNER_ACTION_REQUIRED`, `CONFIRMED`, `IN_PROGRESS`, `COMPLETED`, `REJECTED`, `CANCELLED`

Temporary Ticket holds are stored only as `scheduled_trip_seats.seat_status = HELD` with `hold_expires_at` and the existing hold linkage. `DRAFT`/`HOLDING` are not booking statuses. Payment/refund status is separate from booking status.

### Driver assignment

`NOT_REQUIRED`, `PENDING`, `ACCEPTED`, `REJECTED`, `CANCELLED`

### Trip

`READY`, `IN_PROGRESS`, `BREAKDOWN`, `ASSISTANCE_REQUIRED`, `COMPLETED`, `CANCELLED`

### Passenger payment

`PENDING`, `PROCESSING`, `PAID`, `CASH_AWAITING_CONFIRMATION`, `FAILED`, `REFUNDED`, `PARTIALLY_REFUNDED`

Passenger payment status and Owner settlement status are separate fields. Settlement values such as `OWNER_PAYABLE`/`OWNER_PAID` must not overwrite Passenger payment status. Preserve linked financial transaction history; the complete settlement catalogue is frozen at its later module gate.

### Vehicle verification

`DRAFT`, `SUBMITTED`, `APPROVED`, `REJECTED`, `SUSPENDED`

`vehicles.verification_status` is independent of `vehicles.availability_status`. Verification approval alone does not establish operational availability. Publication/operation must satisfy both fields and required document rules.

### Vehicle availability

`DRAFT`, `PENDING_VERIFICATION`, `ACTIVE`, `BOOKED`, `ON_TRIP`, `MAINTENANCE`, `SUSPENDED`, `INACTIVE`

### Scheduled Ticket seat

`AVAILABLE`, `HELD`, `BOOKED`, `BLOCKED`

## 4. Role-permission baseline

| Action | Passenger | Driver | Owner | Admin |
|---|---:|---:|---:|---:|
| Create private-hire request | Yes | In Passenger context | In Passenger context | Support only |
| Book Ticket seat | Yes | In Passenger context | In Passenger context | Support only |
| Manage owned vehicles | No | No | Yes | Review/control |
| Accept/reject Passenger request | No | No | Requested Owner | Operational override |
| Choose self-drive | No | No | Approved Owner+Driver | No |
| Assign Driver | No | No | Requested Owner | Support |
| Accept external assignment | No | Assigned Driver | If assigned as Driver | No |
| Start/finish trip | No | Assigned Driver | If assigned as Driver | Emergency control only |
| Track active trip | Own booking | Assigned trip | Owned booking/vehicle | Authorized support |
| Verify roles/documents/vehicles | No | No | No | Yes |
| View private documents | Own documents | Own documents | Own personal and owned vehicle documents | Authorized verification |

## 5. Database specification still required before coding

The 20-table ER diagram is a logical model. Freeze the physical dictionary before the corresponding stage's migrations are written. Register/Login is governed by the frozen users/user_roles dictionary in the Auth milestone contract. All other modules require the complete 20-table dictionary. Each physical table definition must contain:

- exact column name and PostgreSQL type;
- nullable/default rules;
- primary and foreign keys;
- unique and check constraints;
- delete/update behaviour;
- indexes and partial indexes;
- enum/check-value source;
- audit timestamps;
- ownership and visibility rule.

Critical fields to confirm in the physical schema include:

- `bookings.passenger_user_id`, `requested_owner_user_id`, `vehicle_id`, `scheduled_trip_id`, itinerary/time range and `status`;
- `trips.booking_id`, `owner_user_id`, `vehicle_id`, `driver_user_id`, assignment status, trip status, timestamps, odometers and latest authorized live location;
- `user_roles.user_id`, role code and independent approval state;
- seat hold expiry and uniqueness rules;
- payment idempotency/provider reference and refund transaction linkage;
- vehicle availability time-range conflict prevention.

## 6. API contract still required before coding

Stage A uses the six exact Auth APIs and tests frozen in the Auth milestone contract. The following full-module coverage list applies to Stage B and does not delay the isolated Stage A gate.

Freeze the endpoint list with request, response, validation, permissions and errors. At minimum it must cover:

- authentication and shared profile;
- role applications and Admin approval;
- document upload metadata and review;
- Owner vehicle/service management;
- routes, stops, seat layouts and scheduled Ticket trips;
- private-hire search and request;
- Owner reject/self-drive/assign actions;
- Driver accept/reject/start/finish actions;
- seat hold, checkout, payment callback and refund state;
- active-trip latest-location update/read;
- notifications;
- vehicle records and reminders;
- Reels and interactions;
- road-alert report/read/moderation;
- AI text/voice interpretation into editable search filters.

## 7. Transaction and concurrency rules

- Seat hold and booking must lock the departure seat rows in one database transaction.
- Payment callbacks must be idempotent.
- Vehicle and Driver availability must be rechecked when Owner/Driver accepts and when a trip starts.
- Overlapping confirmed bookings for one vehicle must be rejected.
- Overlapping accepted trips for one Driver must be rejected.
- Booking, Driver-assignment, trip and payment states must be changed separately but consistently.
- No-response to reconfirmation must not automatically cancel or release inventory.
- A missed protected-departure deadline must not automatically cancel a booking, trigger a refund or establish automatic Owner commitment. Escalate to Admin and fulfil the protected journey using the original vehicle or an equivalent verified replacement. Refund for failure to fulfil only if Travelly cannot fulfil the protected journey. Material changes require Passenger acceptance; Passenger-initiated cancellation remains governed by its accepted policy.
- Completed booking, payment and trip history must not be overwritten.

## 8. Security and privacy baseline

- Hash passwords with a supported password-hashing library.
- Use server-side role and ownership authorization on every protected endpoint.
- Public-safe search, profile, departure, social and AI discovery responses may be public. Booking, payment, tracking, document and management actions require authentication and applicable role/ownership/assignment authorization. Provider callbacks require provider credentials/signatures rather than a Passenger login. Public AI discovery may use POST without authorizing booking or payment mutation.
- Authenticated users can access their own documents, including pending role applicants. Owners can access owned vehicle documents. Admin access requires authorized verification permission. Private files, keys and signed document URLs never appear in public responses.
- Passengers see the Driver's public profile and verification status, never private document files.
- Store uploaded files outside the database; store controlled metadata/URLs in `documents`.
- Validate upload type, size and ownership.
- Expose active-trip location only to the assigned Driver, booking Passenger, booking Owner and authorized Admin support.
- Stop live sharing after completion/cancellation.
- Keep secrets and provider keys in environment variables.
- Record important approval, payment and trip state changes in application logs.

## 9. Implementation foundation to create in VS Code

1. Repository structure and environment configuration.
2. PostgreSQL connection and migration system.
3. Stage A: users/user_roles migrations and Auth fixtures from the frozen Auth contract. Stage B: remaining migrations and seed data only after the complete 20-table dictionary/module contracts are frozen. No extra application table.
4. Authentication and authorization middleware.
5. API response/error format.
6. File-storage adapter for documents and vehicle/social media.
7. Notification adapter for current in-app/email channels. Telephony/IVR is deferred and must not be implemented or exposed in the current NBP.
8. Map/location adapter for active-trip tracking.
9. Payment sandbox adapter.
10. Automated tests for role access, state transitions, seat concurrency, duplicate payment callbacks and schedule conflicts.

## 10. Mandatory end-to-end acceptance scenarios

1. Passenger-only user requests a private hire from an Owner.
2. Approved Owner+Driver accepts the request as self-driver.
3. Owner assigns an external Driver; Driver accepts; Passenger sees confirmed public Driver details.
4. Assigned Driver rejects; Owner assigns another Driver without losing the Passenger request.
5. One multi-role person owns Vehicle A, assigns it to Driver B, and accepts a non-overlapping Driver assignment from Owner C.
6. System blocks the same Driver or vehicle from overlapping accepted trips.
7. Driver starts a confirmed trip; Passenger and Owner see authorized live location; tracking stops at completion.
8. Ticket Passenger holds and pays for a 2D seat; a concurrent request cannot book the same seat.
9. Failed/duplicate payment callback does not create duplicate confirmation.
10. Cash receipt requires the approved confirmation flow and is visible to the Owner.
11. Expired Driver or vehicle documents prevent assignment/start.
12. Maintenance distance and estimated reminder date update after accepted odometer changes.
13. Road alert is shown only to relevant active-route users and expires.
14. AI text/voice search produces editable filters and returns only real eligible inventory.

## 11. Staged build gate

### Stage A - Register/Login

Register/Login implementation may begin after the `users` and `user_roles` physical schema, Auth API contract and Auth acceptance tests are frozen and agree with the final decisions. `02-TRAVELLY-AUTH-MILESTONE-CONTRACT.md` version 1.0 freezes these artifacts for register, login, refresh, logout, own profile and own roles. The matching six 03B entries must reference that exact contract. Infrastructure sessions do not add an application table.

Stage A documentation gate: PASS on 23 October 2026 after documentation verification. This is not a claim that application code exists or acceptance tests have executed. This documentation task does not itself start implementation.

### Stage B - Other Travelly modules

Other Travelly modules may begin only after the complete 20-table physical PostgreSQL dictionary and corresponding API contracts are frozen. The status-transition/role-permission rules, acceptance-test lists and seed data for the affected modules must agree with those artifacts. The Stage A Auth freeze does not authorize implementation of the other eighteen tables' business modules.

General promotions/coupons and a general-purpose configuration engine remain Phase 2; current configuration is bounded to NBP operational settings. Table count remains exactly 20.

The proposal, ER diagram and UI/wireframes remain reference material. Read the final-decisions supersession register before treating any PDF text as implementation authority. Resolve any unlisted disagreement before implementing the affected endpoint.
