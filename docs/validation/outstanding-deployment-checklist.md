# outstanding-deployment-checklist

> Recovered source text, 7 November 2026. Source: documentation collection, pages 321-321, original path `docs/validation/outstanding-deployment-checklist.md`. This is the saved page-text extraction, not the original Markdown. Line wrapping and table layout reflect the compilation; no policy wording has been rewritten. Later approved amendments recorded in `docs/00-READ-FIRST/Travelly_NBP_Codex_Context.md` take precedence.

~~~~text
Outstanding deployment checklist
Updated 29 October 2026. Local verification does not establish production readiness. Preserve these earlier obligations
alongside the calendar and role-workspace deliveries.
- [ ] Provision the separate VEHICLE_PHOTO_ROOT outside repository/webroot and disjoint from private documents/audit storage.
Verify production OS identities/ACLs, derivative durability, backup/restore and retained/orphan media maintenance. Deploy
matching web and restricted audit-writer versions together; web identity must not read the journal/key or full history.
- [ ] Verify private-document/audit storage identity, append-only writer permissions, physical durability, restore identity, recovery
and failure behavior on deployed infrastructure. Calendar block create/edit/withdraw must retain acknowledged before/after
evidence; do not deploy using the embedded test writer.
- [ ] Confirm migration 0006_private_hire_pricing and schema check. Calendar adds no migration. Any pre-existing
NULL/unclassified AVAILABILITY_BLOCK remains restrictive; review its provenance through restricted operator tooling before
classification. Never bulk-release or guess categories.
- [ ] Check all four occupancy sources and concurrent block/commitment rejection against deployment PostgreSQL. Provision
approved Admin support recipients and verify emergency notifications/calendar access and the operational fulfilment/support
handoff. Calendar does not implement protected replacement, cancellation, refund or financial resolution.
- [ ] Configure the actual routing provider/key and verify live geocoding/directions, complete coverage and route-time/night
allocation. Local deterministic routing fixtures are not live provider verification.
- [ ] Configure the real Google Web client, approved origins and consent/branding; verify real sign-in, first-time account
completion and explicit existing-account linking.
- [ ] Configure Brevo credentials and verified sender/domain, actual HTTPS frontend URL and provider limits; verify inbox/spam
delivery, verification/resend/reset links and failure handling. Submission acceptance is not final inbox delivery.
- [ ] Supply and connect official Terms and Privacy destinations before public signup; retain preview notices until then.
- [ ] Complete the next protected departure/booking support and fulfilment slice under its own contract. New departure writers
must acquire the same vehicle lock and call the shared occupancy guard before committing. Local/Airport/Event numeric pricing
and unrelated financial modules remain deferred.
- [ ] Smoke-test the four frontend workspaces on deployed desktop/tablet/mobile with actual approved, pending and revoked
memberships. Confirm existing vehicle/calendar, booking/assignment, document/review and logout journeys. Dashboard fixture
tests do not establish live production routing, mail, identity-provider or fulfilment readiness. Deferred modules must retain explicit
unavailable pages until their approved APIs exist.
No environment secret was changed or provisioned by the calendar or role-workspace work. Earlier Vehicle/Owner and
Account/Profile fixes remain accepted; their historical reports are retained.
~~~~
