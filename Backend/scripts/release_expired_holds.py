"""Release expired Ticket seat holds (PRD 6.3: "A scheduled job releases expired holds safely").

Run from the Backend folder, for example every minute from Windows Task Scheduler:
    ..\\.venv\\Scripts\\python.exe scripts\\release_expired_holds.py

Holds are also released lazily whenever a departure is held, read or released, so this job only tidies up
departures nobody touched. It is safe to run repeatedly and alongside the API.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from datetime import datetime, timezone  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402
from app.api.routers.ticket_booking_api import lock_trip, release_expired  # noqa: E402
from app.dependencies.database import make_engine  # noqa: E402
from app.models.seat_models import ScheduledTripSeat  # noqa: E402


def run(engine, limit=200):
    moment = datetime.now(timezone.utc)
    with Session(engine) as db:
        trip_ids = db.scalars(select(ScheduledTripSeat.scheduled_trip_id).where(
            ScheduledTripSeat.seat_status == 'HELD', ScheduledTripSeat.hold_expires_at <= moment)
            .distinct().limit(limit)).all()
    released = 0
    for trip_id in trip_ids:
        with Session(engine) as db:
            if lock_trip(db, trip_id):          # same lock order as the API: departure first
                released += release_expired(db, trip_id, moment)
            db.commit()
    return released


if __name__ == '__main__':
    print(f'Released {run(make_engine())} expired seat hold(s).')
