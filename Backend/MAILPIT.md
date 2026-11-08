# Local email verification with Mailpit

Local development sends verification and password-reset links to Mailpit, not to an external inbox. Redis remains the authority for purpose-bound, single-use links, expiry and resend limits. Production continues to require Brevo over HTTPS; the Mailpit backend is rejected by production settings.

## Native Mailpit on Windows

Mailpit listens on SMTP `127.0.0.1:1025` and its web inbox `http://127.0.0.1:8025`. It accepts unauthenticated, unencrypted SMTP by default. Keep both services bound to loopback; do not expose Mailpit publicly.

Check that the already-installed Mailpit service is listening:

```powershell
Test-NetConnection 127.0.0.1 -Port 1025
Test-NetConnection 127.0.0.1 -Port 8025
```

To start the native executable yourself, set `$mailpitExe` to its installed path in a separate PowerShell window. Mailpit's SQLite database is placed under the current Windows user's local application data so messages survive restarts:

```powershell
$mailpitExe = 'D:\Travelly\.tools\mailpit\mailpit.exe'
$mailpitData = Join-Path $env:LOCALAPPDATA 'Travelly\Mailpit'
New-Item -ItemType Directory -Force -Path $mailpitData | Out-Null
$env:MP_DATABASE = Join-Path $mailpitData 'mailpit.db'
$env:MP_SMTP_BIND_ADDR = '127.0.0.1:1025'
$env:MP_UI_BIND_ADDR = '127.0.0.1:8025'
& $mailpitExe
```

Use this startup command instead of an existing Mailpit instance; stop that instance through its own console/service controls first. The current already-running instance was left untouched.

## Configure and run Travelly

The local defaults already use Mailpit. If `Backend\.env` overrides them, set only these mail values there, preserving unrelated local settings:

```dotenv
ENVIRONMENT=development
MAIL_BACKEND=mailpit
MAIL_SMTP_HOST=127.0.0.1
MAIL_SMTP_PORT=1025
MAIL_FROM_EMAIL=no-reply@example.com
```

Do not copy or replace database, Redis, JWT, audit, or other existing local settings while applying these mail-only values. No SMTP username, password, TLS or STARTTLS is used by Travelly's local Mailpit transport.

Start the API in another PowerShell window after confirming Redis and PostgreSQL are running:

```powershell
Set-Location D:\Travelly\Backend
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Start the frontend in a third PowerShell window:

```powershell
Set-Location D:\Travelly\Frontend
npm.cmd run dev -- --host 127.0.0.1 --port 5173
```

Register a test account, open the email in `http://127.0.0.1:8025`, follow the link and explicitly confirm verification, then sign in. The link is opaque and single-use, and expires after 30 minutes. Use the existing resend action to test replacement and throttling.

## Production separation

Production must set `ENVIRONMENT=production`, `MAIL_BACKEND=brevo`, a private `BREVO_API_KEY`, a verified sender, HTTPS `FRONTEND_URL`, and authenticated TLS Redis. Never use Mailpit or local capture for production. The application does not log the verification token, message body, SMTP error details or credentials.
