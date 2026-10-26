"""Local browser-test server: isolated PostgreSQL schema/Redis namespace and capture only.

Run from Backend with the project's Python. Ctrl+C cleans up only this server's fixtures.
Never use for deployment. No public fixture/seed route is exposed.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from uuid import uuid4
from alembic import command
from alembic.config import Config
from sqlalchemy import text
import uvicorn
from app.config import get_settings
from app.database import make_engine, session_factory
from app.main import create_app
from app.models import User, UserRole
from app.security import hasher
from app.sessions import SessionStore

root = Path(__file__).resolve().parents[2]
settings = get_settings().model_copy(update={'review_audit_root': None, 'private_document_root': None,
    'review_audit_endpoint': None, 'review_audit_auth_file': None, 'mail_backend': 'capture',
    'mail_capture_dir': root / '.tools' / 'auth-browser-mail', 'google_client_id': '',
    'frontend_url': 'http://127.0.0.1:5181', 'cors_origins': ['http://127.0.0.1:5181']})
schema = 'travelly_test_' + uuid4().hex
control = make_engine(settings.database_url)
engine = make_engine(settings.database_url, connect_args={'options': f'-csearch_path={schema},public'})
store = SessionStore(settings.redis_url, prefix='travelly-test-browser:' + uuid4().hex + ':')
try:
    with control.begin() as connection: connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    config = Config(str(root / 'Backend' / 'alembic.ini'))
    with engine.begin() as connection:
        config.attributes.update(connection=connection, schema=schema)
        command.upgrade(config, 'head')
    with session_factory(engine)() as db:
        for device in ('desktop', 'mobile'):
            user = User(public_user_reference='USR-' + uuid4().hex[:16].upper(), full_name='Legacy Browser Passenger',
                email=f'legacy-{device}@example.com', password_hash=hasher.hash('old password with spaces'), email_login_required=False)
            db.add(user); db.flush()
            db.add(UserRole(user_id=user.id, role_code='PASSENGER', approval_status='APPROVED', approved_at=user.created_at))
        db.commit()
    print('ISOLATED_AUTH_BROWSER_READY', flush=True)
    uvicorn.run(create_app(settings, engine, store), host='127.0.0.1', port=8001, access_log=False)
finally:
    keys = list(store.client.scan_iter(store.prefix + '*'))
    if keys: store.client.delete(*keys)
    store.client.close(); engine.dispose()
    with control.begin() as connection: connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
    control.dispose()
