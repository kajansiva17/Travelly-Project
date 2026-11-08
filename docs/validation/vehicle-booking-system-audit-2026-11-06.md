# Travelly vehicle booking system development audit

**7 November follow-up:** relevant Final Decisions, dictionary, pricing/vehicle/calendar contracts and delivery records have now been recovered as explicitly labelled page-text sources; the missing Admin Review OpenAPI JSON was restored exactly from Git and matched to the compiled source. This partially addresses the source-availability blocker below, without resolving CF01-CF12 or restoring every original document. The focused live-contract rerun was blocked by unavailable local Redis before assertions. See [recovery report](contract-recovery-2026-11-07.md) for provenance, changed files and current verification. The audit results below remain historical.

**Date:** 6 November 2026  
**Mode:** Audit only. No application feature, business rule, schema, environment setting, or live application record was changed.

## Executive summary

The project has a working, bounded vehicle/private-hire foundation, not a complete vehicle booking system. The current supported operational slice is Owner fleet onboarding and review, explicit vehicle publication, reusable Long-distance pricing, Passenger private-hire requests and quotes, Owner commitment/Driver assignment, Driver acceptance and trip start, and a shared per-vehicle occupancy calendar.

Registration, password and Google authentication, contact verification/recovery, separate Owner/Driver applications, Super Admin review, and current-role workspace checks are implemented. The Passenger, Owner, Driver, and Super Admin dashboards exist, but several prominent dashboard destinations intentionally show unavailable placeholders rather than operational features.

The next phase is gated by missing approved source contracts and unresolved finance/status decisions. Do not infer rules for other hire types, payments, refunds, post-confirmation cancellations, trip completion, or tracking. The current checkout only prices explicitly classified `PRIVATE_HIRE` services with `pricing_scope=LONG_DISTANCE`.

## Audit scope and evidence

Reviewed the current working tree's frontend and backend route composition, models, schemas/services, workspace components, migrations, focused tests and available project documentation. The relevant available documentation included the NBP context, current role-approval module amendment and latest approval-status delivery report. The tagged `Backend/.env` was not opened.

The working tree already contains extensive source moves/reorganization (old flat modules marked deleted and new package directories untracked), along with pre-existing documentation changes. Findings describe the current working tree, not only committed `HEAD`. Those existing changes were left untouched.

The current focused integration run used a random PostgreSQL test schema, a test Redis namespace, and isolated private storage. The fixtures drop the random schema and their Redis keys; no application records were edited.

## Completed features (within current bounded scope)

| Area | Verified implementation |
|---|---|
| Authentication | Registration/login, memory-only frontend credentials, Redis-backed session/refresh/revocation, email verification, password recovery, Google sign-in and explicit account linking. Current account and approved roles are read from the server; protected access fails closed when required dependencies are unavailable. |
| Role applications and Admin review | Passenger membership is retained; Owner and Driver approvals are independent. Super Admin can review role applications and their private evidence, with readiness checks, versioned decisions, rejection/resubmission, and current-session access refresh. |
| Vehicle management | Owner vehicle drafts/facts, private evidence, photos, submission, Admin verification/description/photo review, publication/retirement and preferred Driver are implemented. Current approval/publication gates check owner, evidence and photo eligibility. This is the documented first fleet delivery, not a complete vehicle lifecycle. |
| Rates and private-hire pricing | Owner-configured reusable rules, route/location validation, trusted route measurement, price previews, Passenger acceptance of exact quote snapshots, and reuse of accepted rates are implemented for explicitly approved Long-distance private hire. |
| Booking/assignment baseline | Passenger request (including idempotency), Owner quote, Passenger price acceptance, Owner self-drive/Driver assignment, Driver accept/decline and trip start exist. Changes/cancellation are deliberately bounded; confirmed/funded journeys cannot be cancelled through the basic request endpoint. |
| Availability | Owner calendar and read-only Admin support calendar use the same occupancy service as hire/booking checks. Owner dated blocks are versioned and audited; emergency blocks retain commitments and generate Admin support notices. |
| Workspace access | All four role shells/dashboards and route/menu handling exist. Workspace access is based on current server profile and role membership, not a frontend-only role selection. |

These are implementation-scope findings, not a claim that every external provider, live deployment, or every browser journey was rerun during this audit.

## Partially implemented features

| Area | Current boundary |
|---|---|
| Role dashboards | Real data is shown for current approved workflows. Earnings, wallet/payments, global Admin booking/revenue summaries, Driver availability, road alerts, reporting and other named destinations are explicit placeholders or unavailable states. |
| Driver management | Driver onboarding, approval/evidence, licence-category checks, assignment eligibility and trip actions exist. A dedicated Driver roster/management workspace, availability schedule and online-status controls do not. |
| Vehicle search | Browse and itinerary search exist; search checks capacity, vehicle eligibility, saved Long-distance rates and availability. `POST /api/v1/search/vehicles` currently reads only the first 100 published vehicles, with no page/offset or continuation metadata, so eligible inventory beyond that query window can be missed. |
| Booking and trip management | The supported flow reaches trip start and can propose/accept bounded changes. There is no complete trip finish, tracking, operational incident, financial adjustment, or post-confirmation cancellation workflow. |
| Shared availability calendar | A single per-vehicle occupancy function unions `BOOKING`, `DEPARTURE`, accepted `TRIP`, and `BLOCK` sources in one database query. It returns an incomplete-availability error rather than partial data and is used by current booking checks. This is a sound reuse point; coverage across future hire products is not established because those product flows/contracts are absent. |
| Admin operations | Super Admin role/document and vehicle review are present. Platform-wide booking operations, payments, service/route administration UI, reporting, and complete protected-fulfilment case management are not available. |

## Missing features

- Local, Airport, Event, scheduled-ticket/seat-inventory, and rental booking flows. The service schema has broader categories, but current search/rate code intentionally exposes only classified Long-distance private-hire services.
- Payment initiation/capture/provider webhooks, ledger, wallet, payout, refunds, partial refunds, and financial reconciliation. The booking model has a payment-status snapshot, but there are no payment/refund routes or payment UI workflows.
- Complete trip lifecycle: finish/odometer confirmation, tracking/location, arrival/estimate updates, incident/breakdown actions, and the approved cancellation/refund path for confirmed or funded journeys.
- Driver availability calendar/status management and the full owner/admin operational management surfaces described by the navigation.
- Cross-service acceptance evidence proving that every NBP-approved hire type participates in the shared vehicle calendar and atomic conflict checks.

## Critical issues and phase blockers

| Priority | Finding | Impact / required action |
|---|---|---|
| Blocker | **Authoritative contracts are missing from the current `docs/` tree.** Only the concise NBP context, module contract 10, API contract 03H and recent validation reports are present. The README references missing Final Decisions/data dictionary and 03C/03E/03F/03G/module 09 contracts and several vehicle/pricing delivery reports. | The missing files are also needed to verify exact approval/openAPI behavior. Restore the approved sources before expanding service, booking, payment or schema scope. Do not use the README or current implementation to invent policy. |
| Blocker | **Financial and terminal lifecycle decisions remain unresolved.** The NBP context records CF01-CF12 as unresolved; the current basic cancellation endpoint refuses confirmed/in-progress/funded cases, and no payment/refund API exists. | A complete production booking journey cannot be delivered until the authoritative cancellation, payment, refund and trip-status decisions/contracts are reviewed and approved. |
| High | **Product scope is intentionally narrow.** Price and search require explicitly classified Long-distance private hire; Local/Airport/Event policy is unavailable. | Do not activate other pricing scopes or treat a vehicle's availability as a quote or booking promise. Implement each additional service only from its approved contract. |
| High | **Deployment integrations are external prerequisites.** PostgreSQL and Redis are required; production auth fails closed on dependency failure. Production review also requires the isolated audit writer/IPC identity and protected document/photo storage; priced routes require configured trusted routing/location provider access. | Current source and test presence do not prove these services are provisioned/healthy in the target deployment. Validate them in the target environment before launch. |
| Medium | **Vehicle search is bounded to the first 100 published rows without pagination.** | This can omit eligible inventory as the fleet grows. Address as a small, behavior-preserving first development milestone below. |
| Medium | **The current backend integration suite is not green in this checkout.** 227 passed; two failed. | One existing auth-extension test seeds an APPROVED role with an application-clock `approved_at` while the database supplies `requested_at`; clock ordering violates `ck_user_roles_timestamps`. This is a fixture construction failure, not evidence that the actual delayed Admin approval route fails. Another test cannot read the absent approved Admin Review OpenAPI JSON contract. Fix/recover these test inputs/docs before treating the full audit suite as a release gate. |
| Medium | **The working tree is not a clean committed baseline.** | Source/package moves and new files are already present but uncommitted/untracked. Audit findings apply to this working tree; verify the intended move set is retained and rerun checks from the eventual commit before release. |

## Reusable components, models and APIs

### Backend models and services

The current migrated Travelly application-table inventory is 13 of the approved 20-table target: `users`, `user_roles`, `vehicles`, `documents`, `service_types`, `vehicle_services`, `routes`, `route_stops`, `scheduled_trips`, `bookings`, `trips`, `vehicle_records`, and `notifications`. These are registered through the existing SQLAlchemy models and migrations `0001`-`0006`; do not add a table without approval and the missing data dictionary.

Reusable logic includes:

- `app.services.availability.occupancy`, `protected`, and `no_vehicle_conflict` for calendar, search, booking, assignment, and trip checks.
- `app.services.hire_services` for current evidence, vehicle eligibility, Driver licence compatibility, conflict checks, pricing snapshots, and notifications.
- `app.services.rate_calculation`, `rate_locations`, `hire_routing`, and `pricing_scope` for validated Long-distance pricing and trusted route measurements.
- Existing `User`/`UserRole`, `Vehicle`/`Document`, `ServiceType`/`VehicleService`, and `Booking`/`Trip`/`ScheduledTrip`/`VehicleRecord`/`Notification` models.
- Existing review journal/writer and private-document/photo services for versioned decisions, evidence and protected media.

### Backend API groups

- Auth/profile/roles: `/api/v1/auth/*`, `/api/v1/users/me`, `/api/v1/users/me/roles`, `/api/v1/users/me/role-requests`.
- Owner/Driver/Admin role review and documents: `/api/v1/admin/role-requests`, `/api/v1/admin/documents/*`, `/api/v1/documents/*`, and own role-status reads.
- Fleet and vehicle review: `/api/v1/vehicles*`, `/api/v1/owners/me/vehicles*`, `/api/v1/admin/vehicles*`, vehicle-photo and publication routes.
- Calendar: `/api/v1/vehicles/{vehicle_id}/calendar`, `/availability-blocks*`, and read-only `/api/v1/admin/vehicles/{vehicle_id}/calendar`.
- Current service/rate/search/booking: `/api/v1/service-types`, `/locations`, `/vehicles/{vehicle_id}/services*`, `/search/vehicles`, `/bookings/private-hires`, `/bookings*`, `/trips/{trip_id}/assignment-*`, and `/trips/{trip_id}/start`.

### Frontend components and services

- `services/api.js` for authenticated/public API requests, refresh serialization, and in-memory session state.
- `WorkspaceShell`, `workspaceContext`, `workspaceRoutes`, and `useWorkspaceData` for current-role shell/access, navigation and stale-request-safe data loads.
- `RoleDashboards.jsx` and `PassengerDashboard.jsx` for shared dashboard panels, real booking/fleet data and explicit unavailable states.
- `VehicleWorkspace.jsx`, `VehicleCalendar.jsx`, `OwnerRates.jsx`, and booking `TripPricing.jsx` for current fleet, calendar, rates, search, quote, and booking screens.
- Shared `RateForm`/`PlaceSearch`, `DocumentUploadForm`, `PrivateDocumentPreview`, `VehiclePhoto`, and existing auth/onboarding/Admin review components.

## Recommended implementation order

1. **Review this audit and restore the authoritative NBP1 decisions, data dictionary, module contracts, API contracts and missing current delivery reports.** Confirm CF01-CF12 and the intended service scope before implementation.
2. **First small development milestone: paginate current supported vehicle search** (details below), preserving the existing eligibility, Long-distance pricing, capacity and availability rules.
3. Before adding a hire type, write/approve its service-specific contract and acceptance matrix, then integrate its requests with the existing shared occupancy source; do not create an additional application table without explicit approval.
4. Implement approved booking/trip terminal states and financial workflows as a separately reviewed milestone. Preserve exact accepted-price snapshots and never release a protected reservation without its approved resolution.
5. Add Driver availability/management, Owner/Admin operational screens, and real dashboard summaries only as their contracts and APIs are approved.
6. Validate integrated desktop/mobile role flows, target provider/storage/audit-writer setup, migration behavior, concurrency and production observability before launch.

## First small development milestone and acceptance tests

**Milestone:** paginate `POST /api/v1/search/vehicles` for the currently supported Long-distance private-hire flow. This is a bounded search completeness improvement; it does not change eligibility, pricing, availability, booking or approval policy and needs no application-table migration.

Acceptance tests:

1. With more than 100 published vehicles and a matching eligible vehicle beyond the current first 100, a Passenger can reach that vehicle on a later page.
2. Pages preserve deterministic ordering, have no repeated or skipped vehicle IDs, and expose continuation/total metadata consistent with the existing pagination conventions.
3. Every page applies the same current approved-owner/vehicle/evidence, service-scope, passenger/luggage capacity, pricing and availability checks as the current search.
4. If any occupancy source is unavailable/incomplete, search returns the existing `AVAILABILITY_INCOMPLETE` failure instead of presenting partial results as complete.
5. Existing booking idempotency, exact-price acceptance, stale-version, conflict, role authorization and protected-reservation tests continue to pass; no new table, migration or business rule is introduced.

This milestone is proposed only. No implementation was started in this audit.

## Verification

| Check | Result |
|---|---|
| Frontend unit tests (`npm.cmd --prefix Frontend test`) | PASS — 58 tests |
| Frontend production build | PASS — 203 modules; existing Vite chunk-size advisory remains (735.64 kB minified JS chunk) |
| Focused backend integration selection: auth, Google/email extension, Admin review/readiness, vehicles, calendar, rates and Long-distance hire | 227 passed, 2 failed, 1 upstream Starlette/httpx deprecation warning |
| Real external Google, routing, mail-provider and production audit-writer checks | Not run |
| Live browser flows / target environment | Not run as part of this audit |

The backend tests use isolated PostgreSQL/Redis/private test fixtures; they do not establish that the real deployment providers or operational private-storage identities are ready.

## Changed files, deferred scope and next dependency

- **Created:** this audit report.
- **Updated:** `docs/00-READ-FIRST/Travelly_NBP_Codex_Context.md` with the audit pointer and scope gate.
- **Deferred:** all vehicle booking system implementation, migrations, business-rule changes and database-record changes.
- **Next dependency:** review/accept this audit and restore the missing approved source contracts before authorizing the first development milestone.
