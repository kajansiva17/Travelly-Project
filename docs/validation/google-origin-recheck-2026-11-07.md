# Google local-origin recheck - 7 November 2026

## Completed scope

The user confirmed both local origins were added to the existing Google OAuth Web application client and saved. Rechecked anonymous Login and Register on `http://127.0.0.1:5173` and `http://localhost:5173`. Read the current NBP context, multilingual/Google delivery report and relevant AU-05/AU-06/AU-07 rules before the check. Existing token verification, account-completion/linking, roles and memory-only credentials remain unchanged.

The initial real-page check still returned Google's origin rejection. Investigation also found an app-side integration issue: the document's default `no-referrer` policy hides the origin GIS needs for its allowlist check. Google's official [setup guidance](https://developers.google.com/identity/gsi/web/guides/get-google-api-clientid) specifies a compatible referrer policy. An isolated origin-only comparison changed the button response from 400 to 403, with Google still rejecting the supplied origin. This did not establish a successful login or prove which saved Cloud client settings are currently effective.

Applied a narrow frontend correction in `GoogleSignIn.jsx`: while a Google control is mounted, a reference-counted lease sets document referrers to `strict-origin`, including an explicit script policy. Only the public origin can be transmitted; paths, query strings and private references are excluded, and HTTPS downgrades suppress the referrer. Unmount restores the previous policy. The global `Frontend/index.html` remains `no-referrer`; private-media elements retain their own stricter policies. The GIS host also stays measurable during initialization instead of being hidden with `display:none`; inactive controls remain inert and the existing loading/unavailable placeholder is retained.

## Current live result

Fresh anonymous Chrome contexts, real FastAPI and real Google GIS, outside the sandbox:

| Origin | Page | Backend challenge | Google script | Google button | Origin-only referrer | Result |
|---|---|---|---|---|---|---|
| `http://127.0.0.1:5173` | `/login` | 200 | 200 | 403 | Yes | Origin rejected |
| `http://127.0.0.1:5173` | `/register` | 200 | 200 | 403 | Yes | Origin rejected |
| `http://localhost:5173` | `/login` | 200 | 200 | 403 | Yes | Origin rejected |
| `http://localhost:5173` | `/register` | 200 | 200 | 403 | Yes | Origin rejected |

Google's logger reports **The given origin is not allowed for the given client ID.** No API transport failures occurred in this final check. The active API's public client ID matches the current backend environment configuration; the Cloud console's selected client was not directly inspected. A configured client, 200 challenge or loaded script is not proof that Google accepts the origin.

The first sandbox browser check could not load the external script and was repeated with approved escalation. A test-only intercepted-HTML comparison interfered with the browser's API request and was discarded; the valid comparison used the original served page and a test-browser meta-policy override. The final four results above use the actual corrected application with no test policy override.

No account was selected, created, linked or signed in during the live checks. No provider credential, challenge, client secret or client ID was printed. Google Cloud and `.env` were not edited. No backend application source, migration, application table or live application record changed.

## Tests

- `auth-google.spec.js`, desktop and mobile: **24 passed (2.2 minutes)**, including the new browser request-header privacy/restoration scenario. Existing registration completion, same-email conflict, explicit linking, invalid-token, retry and duplicate-callback cases remain covered with mocked GIS/accounts.
- Final focused origin-policy scenario: **2 passed (17.2 seconds)**. A real browser-generated iframe request sends exactly the public origin from an auth URL containing synthetic private path/query/fragment fixtures. The SDK receives a measurable host, and navigation away restores `no-referrer`.
- Frontend unit tests: **63 passed**.
- Production build: **PASS**, 209 modules, existing large-chunk advisory remains. No backend suite rerun was needed for this frontend-only correction; live backend challenges returned 200 as recorded above. Previous backend Google test results remain historical.

## Changed files

- `Frontend/src/features/auth/GoogleSignIn.jsx` - scoped origin-only referrers and measurable GIS host.
- `Frontend/tests/browser/auth-google.spec.js` - origin-header privacy, measurable host and policy-restoration coverage.
- `.tools/check-google-local-origins.mjs` - anonymous four-page live check; logs only safe status/policy results.
- This report, the prior multilingual report's follow-up and `docs/00-READ-FIRST/Travelly_NBP_Codex_Context.md`.

## Deferred scope, blocker and next dependency

**Google sign-in remains blocked by the provider's origin rejection.** The user has confirmed saving the origins; Google acceptance is not yet verified. Google's [OAuth client documentation](https://support.google.com/cloud/answer/15549257?hl=en) says configuration changes can take five minutes to a few hours to take effect. Propagation is a possible explanation, not a confirmed diagnosis. If rejection persists after propagation, compare the edited Web client's Client ID with the backend's existing `GOOGLE_CLIENT_ID`; do not share a client secret or replace configuration speculatively.

Next dependency: Google's saved origin settings must be effective for the same Web client used by Travelly. Then repeat the live check and complete a real user-controlled provider sign-in. No authentication bypass or fabricated successful Google login was introduced. Existing UI and booking work is preserved.
