"""Remove the personal data of accounts whose delete request is 30 days old (owner decision 14 Nov 2026; see app/services/account_closure.py).

Run from the project folder once a day (Windows Task Scheduler for the demo, cron on a server):
    .venv\\Scripts\\python.exe Backend\\scripts\\anonymize_deleted_accounts.py
Name, email, phone, photo, password and sign-in links are removed; the account becomes CLOSED. Booking, payment and trip
records stay under the name "Deleted user". An account that has open business again (blockers) is skipped and tried the next day.
"""
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.security import hasher  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models import User  # noqa: E402
from app.services import account_closure  # noqa: E402


def run(app, now=None):
    now = now or datetime.now(timezone.utc)
    done = skipped = 0
    with app.state.sessions() as db:
        for user_id in account_closure.due_ids(db, now):
            user = db.get(User, user_id)
            if account_closure.blockers(db, user_id):
                skipped += 1
                continue
            account_closure.anonymise(db, user, hasher, secrets)
            db.commit()
            for sid in app.state.store.sessions_of(user_id):
                app.state.store.revoke(sid)
            done += 1
    return {'anonymised': done, 'skipped': skipped}


if __name__ == '__main__':
    print(run(create_app()))
