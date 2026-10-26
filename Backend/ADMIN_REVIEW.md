# Admin Application Review operations

This is the bounded Owner/Driver application review module. Passenger remains permanent/default. There is no general Admin dashboard, public Admin signup, company account, vehicle workflow, IVR or promotion engine.

## Local setup

Use PostgreSQL `travelly_dev` / `travelly_app` and the existing Redis session service. Install `Backend/requirements.txt`. From `D:\Travelly\Backend`:

```powershell
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m app.review_operator init --operator YOUR_OPERATOR_ID --confirm-environment development
..\.venv\Scripts\python.exe -m app.review_writer
```

Run the writer in its own service/terminal; run Uvicorn separately. `.env.example` lists the private paths, IPC endpoint and independent database/restore identity. Initialization never overwrites an existing integrity key, IPC key or journal. Do not store private bytes/keys under this repository or a webroot. Windows development directories are restricted to the local operator. The backend never statically mounts them.

The named pipe uses authenticated, bounded JSON messages; no TCP listener or pickle payload is exposed. The web adapter uses only the IPC credential. It cannot request historical records. The writer owns the integrity key and append-only journal; offline operator/recovery tooling has separately controlled read access. Production must run the writer and web process under different OS identities: deny the web identity all journal/key access; permit it only the protected IPC connection/credential and document storage. Production Settings requires an isolated writer endpoint. Embedded journal mode exists for isolated tests/offline development, not production.

## Controlled Admin membership

An account must already exist through normal registration and retain APPROVED Passenger membership. No account is automatically promoted by server startup. Obtain the exact user UUID through the authorized own-profile API or restricted database operator tooling, then run offline:

```powershell
..\.venv\Scripts\python.exe -m app.review_operator provision-admin --user-id EXISTING_USER_UUID --operator YOUR_OPERATOR_ID --confirm-environment development
```

Repeated provisioning reports the existing membership without reinstating or overwriting it. The initial bootstrap permits `approved_by = NULL` under the Auth contract; operator identity/time/full transition are durably journaled. The same login remains in use; after sign-in/profile refresh, an approved Admin sees an explicit **Application review** link. Login still lands at `/dashboard`. The review routes are `/admin/applications` and `/admin/applications/{role_id}`.

Restricted operator revocation preserves Passenger and uses the existing SUSPENDED role state:

```powershell
..\.venv\Scripts\python.exe -m app.review_operator revoke-admin --user-id EXISTING_USER_UUID --reason "Applicant-visible reason" --operator YOUR_OPERATOR_ID --confirm-environment development
```

Production uses the corresponding restricted operator job, explicit `--confirm-environment production`, restricted credentials and independently verified target. Never expose these commands through HTTP, a frontend control or a signup payload. Runtime authorization reads current account/session/ADMIN membership on every request, so cached tokens cannot retain revoked review authority.

## Tables and migration

`0003_review_documents` follows `0002_international_phone`. It creates **vehicles, then documents**, with the frozen 02C columns/types/defaults/named constraints/FKs/indexes. It does not change users/user_roles or migrate the other sixteen planned entities. No audit/session/outbox/history table is added. The implemented application inventory is users, user_roles, vehicles, documents; the planned architecture remains twenty tables. `alembic_version` and PostgreSQL extension tables are infrastructure.

## APIs

All paths begin `/api/v1` and require the existing Bearer/session/account checks:

| Method | Path | Access |
|---|---|---|
| GET | /admin/role-requests | Current APPROVED Admin, own applications excluded before counting |
| GET | /admin/role-requests/{role_id} | Current APPROVED Admin, no self detail |
| PATCH | /admin/role-requests/{role_id}/review | Current APPROVED Admin, no self review |
| POST | /documents | Authenticated applicant/owned vehicle, multipart one-file upload |
| GET | /documents | Scoped owner/Admin metadata |
| GET | /documents/{document_id} | Scoped owner/Admin metadata |
| GET | /documents/{document_id}/file | Scoped owner/Admin private stream, checked per fetch |
| PATCH | /admin/documents/{document_id}/review | Current APPROVED Admin, no own-file verification |

Queue/detail/upload/stream/review DTOs, errors and query bounds follow 03C/03D. Runtime `/openapi.json` incorporates those exact eight approved operations. Deploy the authoritative `docs/03-API/03C-TRAVELLY-ADMIN-REVIEW-OPENAPI.json` with this repository. Existing Auth/own-role contracts are preserved; rejected resubmission now uses the durable-history guard.

Applicants upload and view private evidence from the existing `/account` page. Owner: NIC/PASSPORT and registration/authorization alternative. Driver: NIC/PASSPORT and a Sri Lanka-issued driving licence. No fake vehicle is needed. Admin verifies that evidence matches the applicant/ownership case; required evidence must be current, unexpired and APPROVED before role approval. NEEDS_CORRECTION changes only the document. Replacements retain earlier rows/bytes/reasons and link the prior same-owner/type document.

## Durability and recovery

Decisions acquire the cross-worker OS coordination lock through the writer, recheck authority and lock identities/memberships/evidence, compare the expected version, then stage one mutation. Full before/after evidence and PostgreSQL xid8 are framed, HMAC chained and durably flushed before ordinary PostgreSQL COMMIT. Only confirmed commit plus terminal durability returns success. There are no prepared transactions or PostgreSQL 2PC.

- Intent write/flush failure: rollback and safe 503; no changed status/version/reason.
- Lost COMMIT outcome or terminal acknowledgement: reconcile xid8 against the recorded database/restore identity. Unresolved outcome is safe 500 with refresh guidance, never a false rollback assertion. Further mutations remain blocked until recovery.
- Committed/aborted xid8: append the corresponding terminal once without reapplying SQL. In-progress/NULL/unavailable/mismatched identity: preserve bytes and block mutations. Never infer the outcome from a matching row.
- Startup and the 30-second recovery worker reconcile pending intents. A writer/client crash releases the OS lock. Restricted recovery can also run explicitly:

```powershell
..\.venv\Scripts\python.exe -m app.review_operator recover --operator YOUR_OPERATOR_ID --confirm-environment development
..\.venv\Scripts\python.exe -m app.review_operator orphans --operator YOUR_OPERATOR_ID --confirm-environment development
..\.venv\Scripts\python.exe -m app.review_operator history --target-id ROLE_OR_DOCUMENT_UUID --operator YOUR_OPERATOR_ID --confirm-environment development
```

History output contains committed projections only; scoped operator reads are themselves audited. Do not send full reasons to ordinary logs. Torn/corrupt/reordered records are preserved and fail closed. Repair is restricted forensic maintenance, never silent truncation/deletion. Account for every intent with database/WAL/backup evidence before archiving a damaged segment and establishing verified continuity.

Uploads use bounded isolated PDF/image parsing, 10 MiB actual file limits, aggregate text/request limits, safe display filenames and opaque keys. Validated original bytes are flushed and atomically placed before SUBMITTED metadata. Durable `.pending` infrastructure markers retain database identity/xid8 for an uncertain upload commit. Cleanup holds the upload lock, checks references and transaction outcome, retains in-progress/unknown bytes, and never deletes referenced/superseded evidence. No-row visibility alone cannot prove an uncertain upload aborted. Partial staging/orphan files are removed only when proven safe.

## Deployment acceptance still requiring the target environment

Local tests exercise PostgreSQL/Redis, real filesystem flushes, process exits, recovery and the separate writer. They do not simulate physical power loss or validate a production backup system. Before production enablement, operators must verify:

- Separate writer/web/recovery OS identities and private file/pipe/socket ACLs, including denial of web journal/key reads, overwrites and deletes. Local development uses one operator account with separate processes; it is not proof of production identity separation.
- Durable storage semantics, capacity monitoring, encrypted restricted backups and a coordinated database/journal/document restore drill. Hold the coordinator/upload locks when taking a filesystem snapshot, and retain database WAL/recovery evidence. Keep database and journal lineage coherent; rotate the configured restore identity for an unrelated restore and resolve old intents through restricted recovery, not row inference.
- Monitoring of unmatched intents, storage/validator failure and recovery latency before PostgreSQL outcome information ages out. Keep `fsync` and review `synchronous_commit` on; leave `max_prepared_transactions` unchanged/zero.

These are deployment checks, not new business decisions or permission to add application tables.

## Validation commands

```powershell
# Backend directory; isolated random PostgreSQL schema + Redis namespace + private temp roots
..\.venv\Scripts\python.exe -m pytest tests -q
..\.venv\Scripts\python.exe -m alembic check

# Frontend directory; Chrome installed (or install the Playwright browser)
npm test
npm run test:e2e
npm run build
```

Browser tests use contract fixtures only in the test runner; application pages never display fixture applicants/journeys. Backend tests use real isolated PostgreSQL/Redis and validate actual authorization/evidence/concurrency/audit/storage behavior. The Playwright test server uses port 5180, separate from the user's preview.

## Verified implementation result — 26 October 2026

| Check | Result |
|---|---|
| Live PostgreSQL migration | PASS — `0003_review_documents (head)` on travelly_dev as travelly_app |
| Alembic schema comparison | PASS — no new upgrade operations detected |
| Full backend suite | PASS — 106 tests, including actual PostgreSQL/Redis, file validation, ownership/Admin/self-review, decisions/corrections, versions, writer outage, reason preservation, process-exit recovery and uncertain upload cleanup |
| Frontend unit tests | PASS — 20 tests, including existing international-phone cases |
| Chrome browser suite | PASS — 22 tests across 1366×900 desktop and 360×640 touch/mobile; queue/detail/confirmation/denial/revocation/empty/error/private preview/upload/footer cases |
| Frontend production build | PASS |
| Live OpenAPI smoke check | PASS — eight operations exactly equal approved 03C; anonymous Admin/document requests denied |
| Preservation | PASS — original approved docs/PDFs/matrix, supplied artwork, public/Auth page components and existing base CSS unchanged by hash comparison |

Non-failing warnings: upstream TestClient/httpx deprecation; existing main frontend bundle remains above Vite's 500 kB advisory threshold. No application contract/schema deviation is introduced. Target production identity/ACL, encrypted backup/restore and physical power-loss checks remain the deployment limitations listed above. No live user was granted Admin membership; all provisioning/review test accounts were inside isolated test schemas. Use the controlled existing-account command before reviewing through the local browser.

### Created files

- `Backend/alembic/versions/0003_review_documents.py`
- `Backend/app/review_models.py`
- `Backend/app/private_infrastructure.py`
- `Backend/app/private_documents.py`
- `Backend/app/validate_document.py`
- `Backend/app/review_audit.py`
- `Backend/app/review_writer.py`
- `Backend/app/review_operator.py`
- `Backend/app/review_api.py`
- `Backend/tests/test_admin_review.py`
- `Backend/tests/test_review_recovery.py`
- `Backend/tests/test_review_writer.py`
- `Backend/ADMIN_REVIEW.md`
- `Frontend/src/AdminApplications.jsx`
- `Frontend/src/OwnDocuments.jsx`
- `Frontend/src/PrivateDocumentPreview.jsx`
- `Frontend/src/reviewRules.js`
- `Frontend/src/review.css`
- `Frontend/playwright.config.js`
- `Frontend/tests/reviewRules.test.js`
- `Frontend/tests/browser/admin-review.spec.js`

### Updated files

- `Backend/app/api.py` — rejected-resubmission history guard; current session/rate context.
- `Backend/app/config.py` — private infrastructure/isolated writer settings and secret-safe settings representation.
- `Backend/app/main.py` — route-aware boundaries, PATCH CORS, exact review OpenAPI, startup/periodic reconciliation.
- `Backend/alembic/env.py` — register the two approved dependency models.
- `Backend/requirements.txt`, `Backend/requirements.lock.txt` — multipart/local PDF/image/ISO-country validators.
- `Backend/.env.example` — private deployment configuration examples.
- `Backend/.env` — local private paths, restore identity and IPC configuration only; existing credentials retained and never included in reports.
- `Backend/tests/conftest.py` — isolated private roots/journal fixtures.
- `Backend/tests/test_auth.py` — approved four-table inventory expectation; existing Auth behavior tests retained.
- `Frontend/src/App.jsx` — approved Admin routes, isolated route state and added review stylesheet.
- `Frontend/src/api.js` — authenticated multipart/binary requests, preserving token refresh/session behavior.
- `Frontend/src/PassengerDashboard.jsx` — approved-Admin entry link and accurate document availability text.
- `Frontend/src/RoleApplicationCard.jsx` — link to existing private profile/evidence flow.
- `Frontend/src/AccountPage.jsx` — own private evidence component.
- `Frontend/package.json`, `Frontend/package-lock.json` — Playwright browser test runner/script.
- `README.md` — current module/table inventory and operator guide link.

Only ignored build/test tooling, caches, screenshots and production build output accompany these files. General Admin dashboards, other operational modules and the remaining sixteen planned tables remain deferred.
