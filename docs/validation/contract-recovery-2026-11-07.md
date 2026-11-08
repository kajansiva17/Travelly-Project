# Approved contract source recovery - 7 November 2026

## Completed scope

Recovered the missing source material needed to review the current Long-distance vehicle-search milestone. No application behavior, business decision, environment setting, application table or live application record was changed.

The Git baseline is the initial commit and predates the pricing, vehicle, calendar and V2 amendments visible in the saved documentation collection. Restoring its Final Decisions as the latest authority would discard those amendments. Instead, recovered 14 documents from the already available page-text extraction of the documentation collection. Each document identifies its original path and source page range and preserves the extracted body in a text block. These are source-text recoveries, not byte-identical original Markdown: wrapping, flattened tables and extracted glyphs remain unchanged. Do not infer missing formatting or silently repair uncertain wording. The current 6 November amendments in the NBP context and module 10 retain precedence over conflicting older text.

Recovered the Admin Review OpenAPI JSON byte-for-byte from Git HEAD after checking that its entire text matches collection pages 175-219 when whitespace is ignored. The JSON parses and contains the eight scoped operations. This confirms recovery provenance, not compatibility with every current API behavior.

## Changed files

Recovered contracts and rules:

- `docs/00-READ-FIRST/00-TRAVELLY-BACKEND-BUILD-READINESS.md` (pages 3-7).
- `docs/00-READ-FIRST/01-TRAVELLY-NBP-FINAL-DECISIONS.md` (pages 8-25, including V2 and CF01-CF12).
- `docs/02-DATABASE/02C-TRAVELLY-PHYSICAL-DATA-DICTIONARY.md` (pages 106-141).
- `docs/03-API/03C-TRAVELLY-ADMIN-REVIEW-OPENAPI.json` (exact Git blob; collection pages 175-219).
- `docs/03-API/03D-TRAVELLY-ADMIN-REVIEW-API-CONTRACT.md` (pages 220-223).
- `docs/03-API/03F-TRAVELLY-REUSABLE-RATE-CONTRACT.md` (pages 227-231).
- `docs/03-API/03G-TRAVELLY-VEHICLE-OWNER-CONTRACT.md` (pages 232-233).
- `docs/04-MODULE-CONTRACTS/06-VEHICLE-OWNER-BUSINESS-DECISION-GATE.md` (pages 274-280).
- `docs/04-MODULE-CONTRACTS/07-LONG-DISTANCE-PRICING-AND-REUSABLE-RATES.md` (pages 281-285).
- `docs/04-MODULE-CONTRACTS/08-VEHICLE-OWNER-FIRST-DELIVERY.md` (pages 286-287).
- `docs/04-MODULE-CONTRACTS/09-VEHICLE-AVAILABILITY-CALENDAR.md` (pages 288-289).

Recovered relevant historical delivery/deployment records:

- `docs/validation/long-distance-pricing-2026-10-27.md` (pages 315-317).
- `docs/validation/outstanding-deployment-checklist.md` (page 321).
- `docs/validation/vehicle-availability-calendar-2026-10-28.md` (pages 345-347).
- `docs/validation/vehicle-owner-first-delivery-2026-10-27.md` (pages 348-350).

New records: this report and `contract-recovery-2026-11-07-manifest.json`, which records source/target SHA-256 hashes, source page ranges and the Git commit. Updated the NBP context and added a follow-up to the vehicle-booking audit. Existing documents were not overwritten during recovery; unrelated working-tree changes were preserved.

## Verification

- PASS: all 15 recovered-file hashes and the source-extraction hash match the manifest.
- PASS: all 14 recovered text bodies equal the complete identified source page ranges after removing only collection headers, footers and document wrappers. No source wording was rewritten.
- PASS: recovered OpenAPI bytes equal the Git blob, match the complete compiled source ignoring whitespace, and parse as JSON with eight operations.
- BLOCKED: `..\.venv\Scripts\python.exe -m pytest tests/test_admin_review.py::test_controlled_admin_revocation_and_live_openapi_contract -q` from `Backend` ended with one setup error because Redis at localhost:6379 refused the connection. The isolated PostgreSQL fixture completed migration setup; the test assertions did not run. One existing Starlette/httpx deprecation warning. The missing JSON file is restored, but this is not a passing live-contract test.

## Deferred scope, blockers and next dependency

Recovery does not resolve CF01-CF12. In particular, competing advance-payment, fee and settlement sources still require primary approval evidence; no payment or financial status policy was selected. Search pagination, session restoration, Redis startup changes and all other implementation remain deferred to separate bounded tasks.

Original Markdown formatting and source documents outside this recovery's relevant scope remain unavailable in the current docs tree. Do not describe the entire original documentation collection as restored. Recovered table text may require checking the original page layout before interpreting an ambiguous row.

Next development dependency: review the recovered Final Decisions, module 07, API 03F and dictionary sections against the existing supported search before implementing the audit's bounded pagination milestone. Preserve current service scope, pricing, eligibility, occupancy failure behavior and privacy. Rerunning the blocked live-contract test requires available Redis; historical passing tests are not current verification.
