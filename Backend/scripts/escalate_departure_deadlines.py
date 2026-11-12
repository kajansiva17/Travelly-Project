"""Escalate protected departures whose decision deadline passed without an Owner commitment (PRD D08).

Run from the Backend folder, for example every 15 minutes from Windows Task Scheduler:
    ..\\.venv\\Scripts\\python.exe scripts\\escalate_departure_deadlines.py

A missed deadline only moves the departure to DECISION_REQUIRED and alerts the Admin and the Owner. It never cancels,
refunds or commits anything. The same check also runs when the Admin opens the attention list or the Owner opens
their departures, so this job only covers departures nobody looked at. Safe to run repeatedly and alongside the API.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy.orm import Session  # noqa: E402
from app.api.routers.fulfilment_api import escalate_missed_deadlines  # noqa: E402
from app.dependencies.database import make_engine  # noqa: E402


def run(engine):
    with Session(engine) as db:
        count = escalate_missed_deadlines(db)
        db.commit()
    return count


if __name__ == '__main__':
    print(f'Escalated {run(make_engine())} departure(s) to the Admin.')
