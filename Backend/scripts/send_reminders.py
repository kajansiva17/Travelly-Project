"""Send document expiry, maintenance and cash-commission reminders (see app/services/reminders.py for the rules).

Run from the project folder, for example once a day at 08:00 from Windows Task Scheduler (demo) or cron (server):
    .venv\\Scripts\\python.exe Backend\\scripts\\send_reminders.py
Safe to run as often as you like: a reminder is never sent twice. Email copies go out only when .env has
REMINDER_EMAIL_ENABLED=true and real email delivery is configured.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import create_app  # noqa: E402
from app.services.reminders import run_reminders  # noqa: E402


def run(app):
    with app.state.sessions() as db:
        counts = run_reminders(db, app.state.settings, app.state.mailer)
        db.commit()
    return counts


if __name__ == '__main__':
    counts = run(create_app())
    print(f"Reminders sent: {counts['documents']} document, {counts['maintenance']} maintenance, {counts['commission']} commission, {counts['rental']} rental. Unanswered price requests closed: {counts['expired_requests']}.")
