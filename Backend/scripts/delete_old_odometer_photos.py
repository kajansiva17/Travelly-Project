"""Delete odometer photos 7 days after their trip ended (owner decision 13 Nov 2026; see app/services/odometer_proof.py).

Run from the project folder once a day (Windows Task Scheduler for the demo, cron on a server):
    .venv\\Scripts\\python.exe Backend\\scripts\\delete_old_odometer_photos.py
The readings stay in trips; only the photo and its GPS position go. Photos are also removed when someone opens the
proof after the 7 days, so the job only keeps the disk tidy.
"""
import sys
from pathlib import Path
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import create_app  # noqa: E402
from app.models.hire_models import Trip  # noqa: E402
from app.services import odometer_proof  # noqa: E402


def run(app):
    settings, deleted = app.state.settings, 0
    folder = odometer_proof.root(settings)
    with app.state.sessions() as db:
        for child in sorted(folder.iterdir()):
            try:
                trip = db.get(Trip, UUID(child.name)) if child.is_dir() else None
            except ValueError:
                continue
            if trip is not None:
                deleted += odometer_proof.forget_photo(settings, trip)
    return deleted


if __name__ == '__main__':
    print('Odometer photos deleted:', run(create_app()))
