# Owner/Driver document upload form — 26 October 2026

This is an implementation/validation record, not an amendment to the approved contracts.

## Authority inspected before editing

- [Final Decisions](../00-READ-FIRST/01-TRAVELLY-NBP-FINAL-DECISIONS.md): AR-D01–AR-D04, AR-VUI and the binding evidence interpretation.
- [Build Readiness](../00-READ-FIRST/00-TRAVELLY-BACKEND-BUILD-READINESS.md): independent roles, private documents and separate vehicle verification.
- [Owner/Driver Applications](../04-MODULE-CONTRACTS/02-OWNER-DRIVER-APPLICATIONS.md): sections 4.1–4.2 and OD-19–OD-21.
- [Admin Review](../04-MODULE-CONTRACTS/03-ADMIN-APPLICATION-REVIEW.md): section 4.1.
- [Review Prerequisites](../04-MODULE-CONTRACTS/04-ADMIN-REVIEW-PREREQUISITES.md): sections 2.2–2.3 and 4.5.
- [Upload API contract](../03-API/03D-TRAVELLY-ADMIN-REVIEW-API-CONTRACT.md): section 4 explicitly makes number, issuing country, issue date and expiry date optional at upload.
- Existing `UploadMetadata`, `evidence_ready`, private file validation, review tests and `OwnDocuments` form.

## Document and ownership guidance

The identity group is labelled **Required**: either NIC or Passport, with the second alternative optional. Each identity option is labelled **Required for your case** and explains that choice. Driving licence is **Required for your case** for Driver approval only. Owner and Driver approvals remain independent.

| Registration name | Frozen Owner role evidence | Form guidance |
|---|---|---|
| Applicant | NIC or Passport plus VEHICLE_REGISTRATION | Registration is Required for your case; authorization is Optional. |
| Another individual | NIC or Passport plus OWNER_AUTHORISATION from that registered individual | Authorization must identify the applicant and relevant vehicle. |
| Company | NIC or Passport plus OWNER_AUTHORISATION establishing registered-company authority | Applicant remains an individual; no company account or compulsory business/bank documents. |

The user expressly selected **Preserve the frozen role checklist**. No extra registration attachment is required for the latter two role-application branches. The form explicitly says authorization does not replace registration and that vehicle registration/verification remain separate, including for another individual's or a company's vehicle. Ownership guidance is transient UI only; it is not sent as an authoritative application field.

## Fields and validation

| Document type | Number label | Issuing country | Issue date | Expiry date |
|---|---|---|---|---|
| NIC | Identity card number — Optional | Optional country-name selector; no assumed issuer | Optional, copy printed issue date | Optional, revealed only when user indicates a printed expiry |
| Passport | Passport number — Optional | Optional country-name selector; no assumed issuer | Optional | Optional at upload; visible explanation of existing approval expiry check |
| Driving licence | Driving licence number — Optional | Optional at upload; defaults to Sri Lanka; LK requirement for Driver approval explained | Optional | Optional at upload; existing approval expiry requirement explained |
| Vehicle registration | Registration document number — Optional | Optional country-name selector; no assumed issuer | Optional | Optional, revealed for printed expiry |
| Owner/company authorization | Authorization reference number — Optional | Hidden: this form describes permission from the registered individual/company, not government-issued identity evidence | Optional | Optional, revealed for printed expiry |

Document type and file are **Required** for every upload. All visible fields have a short helper and an explicit Required/Optional label. Missing printed numbers/dates are left blank, not invented. The country's two-letter ISO value is internal; the selector displays country names using the same 249-code catalogue as backend validation. It does not infer nationality or issuer from a phone number.

Frontend and backend validate supplied number length, valid ISO countries, valid dates and expiry on/after issue date. Optional metadata may be omitted for every supported type. Field errors are associated with inputs; server errors focus the first invalid input after controls are re-enabled, retaining editable values and the selected file. Switching document type clears prior metadata/file to avoid submitting stale evidence under a different type.

One PDF, JPG/JPEG or PNG is allowed, maximum **10 MiB (10,485,760 bytes)**. File guidance wraps on mobile. Browser checks empty/oversize files and extension/MIME consistency. The backend retains actual-content validation, malformed/encrypted PDF rejection, authorization and durable storage checks. Backend oversize errors now identify the file input. Private access, audit and role-approval conditions are unchanged.

## Business decision still not fully frozen

The authorities refer to document-type expiry applicability but do not enumerate a complete matrix. Specifically, which NIC, vehicle-registration and authorization variants are genuinely non-expiring, and when must a printed expiry be supplied before approval? Any exemption for a non-expiring Passport would also need an explicit decision because the current backend requires Passport expiry for role approval.

No new expiry requirements or exemptions were selected. The existing approval gate remains: Passport/licence need expiry, Driver licence must have issuer LK, supplied dates cannot describe expired or future-issued evidence at approval, and other required evidence still undergoes ownership/currentness/relevance review. The upload API's optional metadata fields remain optional.

## Verification

- Frontend unit tests: 28 passed, including all five types, ISO countries, omitted metadata, date order and exact file-size boundary.
- Backend: 39 targeted metadata/Admin Review tests passed, plus four added real-upload/ownership-case tests. The updated oversize-file inline-error test also passed. These used real PostgreSQL/Redis, isolated database schemas, private temporary files and test-only session namespaces.
- Browser: all 20 desktop/mobile scenarios passed, covering the five document types across all three ownership cases (30 layout combinations), optional metadata submission, country-code transport, hidden/reset fields, date order, file limits and inline server errors. Browser fixtures emulate API responses; real persistence/content validation is covered by the backend tests above. Screenshot review prompted shorter ownership selector labels for narrow screens; the six ownership/layout scenarios were rerun for that adjustment.
- Windows runner limitation: after reporting all 20 cases successful, the full run stalled during managed Vite teardown and was stopped manually. The focused error-handling rerun (2 tests) and final layout rerun (6 tests) exited successfully. Final screenshots were visually reviewed on desktop and mobile; component captures hide unrelated sticky navigation only during capture, while layout assertions run without that override.
- Production build: passed; existing bundle-size advisory remains. Backend tests retain the pre-existing TestClient/httpx deprecation warning.
- No `.env`, schema, role transitions, frozen contracts or live applicant records were changed.
