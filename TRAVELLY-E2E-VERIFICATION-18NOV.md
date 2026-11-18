# Travelly end-to-end workflow verification — 18 November 2026

Branch: `feature/pending-screens`

This report records what was actually exercised. Travelly is **not fully verified**: authenticated browser automation, real Google sign-in, live payments, Driver Availability management, and some policy-dependent scheduled-ticket behavior remain blocked or incomplete.

## Runtime and test data

- Live local path exercised: `http://127.0.0.1:5173` → Vite proxy → API `127.0.0.1:8000` → local PostgreSQL/Redis.
- Isolated live test account identifier: `e2e-1794984448988`. Its email, phone, tokens, and database UUID are intentionally omitted. It has Passenger access and a PENDING Owner application only.
- Database revision: `0023_vehicle_hire_location`; read-only counts during verification: 10 vehicles and 12 scheduled trips.
- Automated backend tests used random `travelly_test_<uuid>` PostgreSQL schemas, real local PostgreSQL and Redis, capture mail, sandbox payment, temporary private storage, and isolated review-writer processes. Schemas were dropped after each run.
- No production database, real email/SMS, live payment, push, or deployment was used.

## Scenario matrix

| Service | Scenario | Expected | Actual | Status | Evidence | Fix / remaining issue |
|---|---|---|---|---|---|---|
| Runtime | Owner screens shared API load | Vehicles, Ticket, Rental, Maintenance load real data | Before: vehicle/scheduled-trip ORM reads returned 503 with PostgreSQL `42703` because live DB was at 0022. After non-destructive 0023 migration, ORM reads succeed and Vite proxies to 8000 | PASS (API/runtime) | Live revision `0023_vehicle_hire_location`; Vehicle query 10 rows; ScheduledTrip query 12 rows; public proxy request 200 | Browser rendering remains separately blocked below |
| Authentication | Register → login → persisted profile | Same stored user is returned after login | Live proxy registration/login returned the same persisted account; role was Passenger | PASS | Live test `e2e-1794984448988`; `POST /auth/register`, `POST /auth/login`, `GET /users/me` | Registration now reads app-scoped verification configuration at `Backend/app/api/routers/api.py:92` |
| Authentication | Email verification | Verification required when configured; no real email | Capture-mail verification and replay behavior passed in isolated integration tests; live demo configuration does not require verification | PASS (configured test mode) | `test_registration_verification_and_atomic_replay`; auth batch | Live demo's verification-off setting means this exact live account did not receive email |
| Authentication | Session metadata, persistence, logout | Device is visible; logout revokes session | Live session listed `Chrome on Android`; logout returned 204 | PASS | Live `GET /users/me/sessions`, `POST /auth/logout`; `Backend/app/api/routers/api.py:22` | Restored session metadata removed by an earlier merge |
| Authentication | 2FA and account reactivation | Challenge on 2FA; deactivated account can reactivate safely | Integration scenarios pass, including backup codes, lockout, and reactivation | PASS | `test_two_step_and_closure.py`; 15/15 targeted auth/session tests | Restored approved login branches at `Backend/app/api/routers/api.py:121` |
| Authentication | Role permission denial | Passenger cannot use Owner vehicle API | Live request returned 403; Owner application persisted as PENDING after reread | PASS | Live test account; `GET /owners/me/vehicles`, `POST /users/me/role-requests`, `GET /users/me/roles` | No approval was forced or inserted directly |
| Authentication | Google sign-in | Real configured Google flow completes | Signed-token/challenge integration tests pass; real Google account/browser flow was not attempted | BLOCKED | `test_auth_extension.py`; browser automation failure | Requires permitted external Google flow and working browser automation |
| Owner vehicle | Create draft and unique registration | Authenticated approved Owner creates one persistent draft | Isolated authenticated API tests pass, including duplicate registration and persistence/projection | PASS (integration) | `test_draft_authorization_unique_registration_and_private_feedback_projection` | Actual running Owner-browser click remains BLOCKED below |
| Owner vehicle | Details, evidence, submit, approval/rejection, correction/resubmission | State/version/audit transitions persist and reject unauthorized actions | Vehicle, document, correction, resubmission, suspension and audit-failure tests pass | PASS | `test_vehicles.py`, `test_admin_review.py`; vehicle/review batch 114 passed, 1 skipped; two repaired cases retested 2/2 | No review/audit bypass introduced |
| Owner vehicle | Review writer isolation | Web identity has bounded IPC only; outage fails closed | Isolated writer and vehicle projection tests pass; web sandbox cannot read journal integrity key | PASS (security integration) | `test_isolated_writer_acknowledges_without_runtime_history_access`; `test_separate_writer_projects_only_owned_latest_feedback_without_history_access`; direct journal-key read denied | Port-8001 temporary backend was removed because its identity could not access the writer pipe; documented port 8000 runtime retained |
| Owner vehicle | Hire-location persistence and privacy | Base/radius/current position persist; unrelated edit does not refresh observation; public response has no coordinates | Tests pass; radius now serializes with contracted two decimals | PASS | `test_owner_controls_hire_location_without_exposing_coordinates_or_refreshing_it_on_other_edits`; `Backend/app/api/routers/vehicle_api.py:42` | Fixed `"50"` → `"50.00"` contract |
| Owner vehicle | Publish/unpublish and Passenger visibility | Only eligible approved/published vehicles are public | Publication, evidence expiry, privacy, retirement and revocation tests pass | PASS | `test_normalized_photo_moderation_publication_privacy_and_revocation`, `test_evidence_renewal_requires_explicit_republication` | Browser presentation not directly observed |
| Hire matching | Fresh Colombo location; immediate Colombo pickup | Vehicle can be AVAILABLE if accepting, free, in radius and reachable with preparation | AVAILABLE | PASS | `test_fresh_colombo_position_can_match_immediate_colombo_pickup`; `Backend/app/services/location_matching.py` | 2-hour/15-minute/15-minute approved constants are exercised |
| Hire matching | Fresh Colombo location; immediate Jaffna pickup | Must not be shown available if it cannot reach/violates radius | UNREACHABLE / `PICKUP_DISTANCE_EXCEEDED` | PASS | `test_fresh_colombo_position_cannot_match_immediate_jaffna_pickup` | Correct result for the Jaffna/Colombo example |
| Hire matching | Bookings OFF | Presence never overrides willingness | `BOOKINGS_OFF` wins | PASS | `test_bookings_off_wins_even_when_vehicle_is_nearby` | Hard restriction cannot be owner-confirmed away |
| Hire matching | Stale/missing position or unknown routing | Owner confirmation required; not AVAILABLE | Returns `CONFIRMATION_REQUIRED` | PASS | `test_stale_immediate_location_requires_owner_confirmation`, `test_unknown_routing_requires_confirmation_and_cannot_be_available` | Missing/stale data does not silently pass |
| Hire matching | Preparation and adjacent commitments | Routed travel + 15 minutes must fit before pickup and next commitment | Unreachable requests are blocked | PASS | `test_preparation_time_is_added_to_pickup_travel_time`, `test_future_booking_checks_repositioning_from_before_and_to_after_commitments` | Search distance type fixed at `Backend/app/services/location_matching.py:117` |
| Hire matching | Future request without prior commitment | Usual base area, not today's stale distant position | Uses `BASE_LOCATION` | PASS | `test_future_request_uses_base_not_todays_distant_position` | Completed old trip does not override base as a current commitment |
| Hire matching | No fare before vehicle selection | Search exposes feasibility, then selected-vehicle endpoint calculates fare | Local and Event searches return `price: null`; selection returns price | PASS | `test_vehicle_list_hides_price_until_the_passenger_selects`, updated Event search test | Fixed search 500 caused by string-vs-number distance comparison |
| Hire matching | Owner confirmation flow | Positioning confirmation must rerun reachability and cannot bypass hard restrictions | Endpoint and unit protections exist; full browser flow not directly exercised | PASS (API logic) / BLOCKED (browser) | Location tests plus `POST /bookings/{id}/positioning-confirmation` implementation | Add a dedicated browser/API integration case with an approved runtime Owner |
| Private hire | Request → quote → acceptance → Owner-driving | Price snapshot and vehicle commitment persist | Passed | PASS | `test_hire_pricing.py`; private-hire batch 117/117 | Exact-route changes now require an explicit reusable route quote |
| Private hire | External Driver assignment/accept/decline/reassignment | Only eligible Driver; conflicts protected | Passed integration scenarios | PASS | `test_trip_operations.py`, `test_hire_pricing.py` | Driver-wide unavailability remains separate/incomplete |
| Private hire | Pickup PIN/start, odometer evidence, completion | Pickup verification retained; required proof and odometer rules enforced | Passed | PASS | `test_pickup_codes.py`, `test_odometer_proof.py` | Fixed booking detail overwriting `verified_at` at `Backend/app/api/routers/hire_api.py:539` |
| Private hire | Route change | Exact-route fare cannot silently price an added stop; explicit quote, Passenger acceptance and Owner review required | Normal flow applies after all three steps; conflict blocks quote and preserves agreement | PASS | Corrected `test_change_passenger_acceptance_totals_and_notifications`, conflict and in-progress tests | Route detection fixed at `Backend/app/api/routers/hire_api.py:1223` |
| Private hire | Duplicate/retry protection | Same idempotency key does not duplicate booking/payment | Passed | PASS | Private-hire and payment integration suites | No live provider used |
| Payments | Sandbox fare/payment history/cash receipt | Sandbox/cash paths persist without real money | Passed | PASS | `test_private_hire_payments.py`, `test_payments.py`, rental payment tests | Test settings now explicitly blank PayHere credentials |
| Payments | Provider configuration isolation | Test/app instance config controls provider availability | PayHere is unavailable in isolated tests even if machine `.env` has credentials | PASS | `Backend/app/services/payment_providers.py:126`, `:183`; `Backend/app/api/routers/payment_api.py:528` | Fixed global-settings leak; no external PayHere call made |
| Payments | Real PayHere | Real gateway round trip | Not run | BLOCKED | Deliberately excluded by task safety rules | Requires sandbox merchant credentials and controlled external callback environment |
| Driver Availability | Create/edit/withdraw Driver unavailability | Driver-level availability records and APIs exist | No Driver unavailability model/table/API exists | INCOMPLETE | Repository inspection; no matching migration/router/model | Requires approved business contract and implementation; do not infer from vehicle blocks |
| Driver Availability | Accepted/active conflict and cross-owner conflict | Accepted trips prevent overlapping assignment without private detail leakage | Accepted Driver/vehicle trip conflicts are checked; pending offers are not a general availability calendar | PARTIAL | Trip assignment/conflict tests | Missing Driver availability lifecycle and pending-offer policy |
| Scheduled tickets | Seat layout, route, departure, Driver, publish, search/book | Complete scheduled workflow persists | Passed integration suites | PASS | Scheduled/fulfilment batch 59/59; `test_departure_trips.py` | UI still requires manual browser observation |
| Scheduled tickets | Last-seat concurrency | Only one hold succeeds | Passed | PASS | `test_concurrent_requests_cannot_hold_the_same_seat` | PostgreSQL locking prevents oversell |
| Scheduled tickets | Cancellation/release/cutoff | Seats release and closed booking windows are enforced | Passed | PASS | `test_ticket_holds.py` | — |
| Scheduled tickets | Boarding verification | Implemented Traveller boarding works | Paid traveller boards; unpaid traveller is refused | PASS (implemented behavior) | `test_the_driver_boards_a_paid_traveller_and_only_a_paid_one` | QR versus OTP product policy remains unresolved; no new rule invented |
| Rental | Terms/publication → request/licence → decision → handover → return → final bill/payment | Existing contract persists and authorizes each stage | Passed | PASS | `test_rental.py`; included in 117/117 batch | No real payment provider used |
| Maintenance | Records, reminders, odometer and availability blocks | Owner-only records persist; reminders once; blocks affect scheduling | Passed | PASS | `test_vehicle_records.py`, `test_reminders.py`, conflict tests | — |
| Replacement | Request/options/accept/decline/refund/reallocation | Protected fulfilment preserves passengers and money | Passed | PASS | `test_fulfilment.py`; 59/59 batch | — |
| Owner–Driver linking | Link/lookup and assignment permissions | Minimal public lookup and approved relation behavior | Passed implemented tests | PASS | vehicle preferred-driver tests, departure Driver lookup tests | Not a substitute for Driver Availability |
| Settlements | Commission statements and payout | Owner sees own; Admin records payout once; refunds prorate | Passed | PASS | `test_settlements.py`; 59/59 batch | — |
| Admin/audit | Approval actions, concurrency, fail-closed audit | One versioned decision; journal failure prevents commit | Passed | PASS | `test_admin_review.py`, writer tests | Journal/history/keys preserved |
| Frontend | Unit/model/i18n regressions | English/Tamil/Sinhala keys and affected models pass | 184/184 passed | PASS | `npm.cmd test` | This is not visual browser evidence |
| Frontend | Production build | Build succeeds | Succeeded; one existing >500 kB chunk warning | PASS | `npm.cmd run build` | Code splitting is a performance follow-up, not this workflow defect |
| Browser | Authenticated desktop/mobile at 1280×585 and relevant mobile sizes | Actual UI actions and persistence observed | Automation runtime fails before browser control with `failed to write kernel assets ... os error 3` | BLOCKED | Computer-use initialization failure | Requires repaired automation runtime or user-performed checklist below |
| Browser | My vehicles/Ticket/Rental/Maintenance and actual Create draft persistence | Existing data loads; no false empty state; draft survives refresh/relogin | Not directly re-observed after fixes | BLOCKED | Backend/API tests pass, but no admissible browser evidence | Must not mark resolved until manual/automated UI verification is captured |

## Root causes and fixes

1. **Live schema drift:** the running database was revision 0022 while code queried 0023 vehicle-location fields. A non-destructive upgrade to `0023_vehicle_hire_location` restored the shared vehicle and scheduled-trip ORM paths; no data reset occurred.
2. **Authentication merge regression:** a later merge removed 2FA challenge, account reactivation and session metadata from `/auth/login`. The previously approved behavior was restored in `Backend/app/api/routers/api.py`.
3. **App/global configuration leak:** registration and payment-provider checks read global cached settings rather than the active app instance. They now use `request.app.state.settings`; isolated tests explicitly disable real mail/payment credentials.
4. **Search 500:** reachability returned a distance string, while ordering compared it to a numeric threshold. The public approximate distance is now numeric.
5. **Pickup verification loss:** booking detail replaced the complete pickup object with only `required`; it now merges the flag and retains `verified_at`, attempts and issued state.
6. **Exact-route change conflict:** added stops were only treated as unpriced for `FIXED_ROUTE`; all `coverage.kind == ROUTE` rules now require an explicit changed-route quote.
7. **Vehicle-location formatting:** `NUMERIC(8,2)` pickup radius now returns two decimals consistently.
8. **Runtime IPC identity:** the temporary port-8001 API ran as the sandbox identity and could not connect to the normal service identity's named pipe. It was removed. Vite was restored to documented port 8000, retaining the existing separately started writer/API runtime. The sandbox identity received only read/traverse on `review-client` and read on `pipe.key`; it still cannot read the audit journal integrity key.

## Automated results

- Frontend unit/model/i18n: **184 passed**.
- Frontend production build: **passed** (large-chunk warning only).
- Private hire, location, Event, trip, pickup, odometer, payments and rental: **117 passed**.
- Scheduled tickets, fulfilment, settlements and commission: **59 passed**.
- Road alerts, routes, history, workspace/report/Admin oversight and Driver expiry: **42 passed**.
- Auth/profile/session batch: **118 passed**, one timestamp-fixture failure; corrected parametrized case then **2/2 passed**.
- Vehicle/review/rates/calendar/records batch: **114 passed, 1 skipped**; the two initial failures were corrected and independently retested **2/2 passed**.
- Warnings retained: FastAPI TestClient deprecation, unknown pytest `cache_dir`, and Vite large chunk.
- Task commit: **none created**. No push or deploy occurred.

## Changed files

- `Backend/app/api/routers/api.py`
- `Backend/app/api/routers/hire_api.py`
- `Backend/app/api/routers/payment_api.py`
- `Backend/app/api/routers/vehicle_api.py`
- `Backend/app/services/location_matching.py`
- `Backend/app/services/payment_providers.py`
- `Backend/tests/conftest.py`
- `Backend/tests/test_auth.py`
- `Backend/tests/test_auth_extension.py`
- `Backend/tests/test_event_hire.py`
- `Backend/tests/test_hire_pricing.py`
- `TRAVELLY-E2E-VERIFICATION-18NOV.md`

Unrelated Task 9/untracked files were not edited or staged.

## Manual browser verification still required

Use an isolated, already approved local Owner account; do not use or modify a real user record.

1. At `http://127.0.0.1:5173`, sign in and open My vehicles, Ticket, Rental, Maintenance and Hire prices at 1280×585, then at a relevant mobile width.
2. Capture Network evidence for each initial request: URL, method, status and response. A failed request must show the error and must not show an authoritative empty state.
3. In My vehicles, create a uniquely labelled draft, record the POST response, refresh, sign out/in, and confirm the same draft appears through `GET /owners/me/vehicles`.
4. Complete one location search for each Local, Airport, Long Distance and Event service. Verify no fare before vehicle selection, the Owner-confirmation section, and no coordinates in public payloads.
5. Repeat key pages in English, Tamil and Sinhala, checking clipping, broken Unicode, focus order and error text.
6. Preserve the browser HAR/screenshots and correlate request IDs with backend logs. Until this is done, actual browser Create draft persistence and the four affected Owner screens remain BLOCKED.

## Highest-priority next actions

1. Repair the browser automation kernel-assets installation or perform and capture the manual browser checklist above.
2. Approve a Driver Availability business/data/API contract before implementing create/edit/withdraw or pending-offer semantics.
3. Resolve the scheduled-ticket QR versus OTP boarding decision.
4. Add a dedicated integration test for the complete positioning-confirmation endpoint, including renewed location plus hard-restriction refusal.
5. Address the existing frontend chunk-size warning separately if page-load performance is a release criterion.

The required `docs/00-READ-FIRST/Travelly_NBP_Codex_Context.md` path does not exist in this checkout, so it could not be updated. This report is the task delivery record; no replacement context file was invented.
