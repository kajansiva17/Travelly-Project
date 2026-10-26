"""Restricted local audit writer/recovery service, run under its own OS identity.

No TCP listener, pickle payloads, filesystem paths from clients or history-read operation.
The web identity receives only a separate IPC credential; never the integrity key/history.
"""
import json
import os
import threading
from multiprocessing.connection import Listener
from .config import get_settings
from .database import make_engine
from .review_audit import FileAuditJournal, canonical
from .private_infrastructure import unavailable


def endpoint_family(endpoint):
    if os.name == 'nt' and endpoint.startswith('\\\\.\\pipe\\TravellyReviewAudit'):
        return 'AF_PIPE'
    if os.name != 'nt' and endpoint.startswith('/'):
        return 'AF_UNIX'
    raise unavailable()


def serve_connection(connection, journal):
    def receive():
        if not connection.poll(30):
            raise unavailable()
        value = json.loads(connection.recv_bytes(65536))
        if not isinstance(value, dict) or set(value) != {'action', 'event'}:
            raise unavailable()
        return value
    try:
        first = receive()
        if first['action'] != 'begin' or first['event'] is not None:
            raise unavailable()
        with journal.coordinated():
            issued = set()
            connection.send_bytes(canonical({'ok': True}))
            while True:
                request = receive()
                action, event = request['action'], request['event']
                if action == 'end':
                    connection.send_bytes(canonical({'ok': True})); break
                if action == 'recover' and event is None:
                    journal.reconcile(); result = None
                elif action == 'append' and isinstance(event, dict) and event.get('outcome') in ('intent', 'committed', 'aborted'):
                    if event['outcome'] == 'intent': issued.add(event['correlation_id'])
                    elif event.get('correlation_id') not in issued: raise unavailable()
                    result = journal.append(event)
                elif action == 'outcome' and isinstance(event, dict) and set(event) == {'correlation_id'} and event['correlation_id'] in issued:
                    result = journal.outcome(event['correlation_id'])
                else:
                    raise unavailable()
                connection.send_bytes(canonical({'ok': True, 'event': result}))
    except Exception:
        try: connection.send_bytes(canonical({'ok': False}))
        except (OSError, EOFError): pass
    finally:
        connection.close()


def serve(settings, journal):
    endpoint = settings.review_audit_endpoint
    key = settings.review_audit_auth_file.read_bytes()
    if len(key) != 32:
        raise unavailable()
    with journal.coordinated(): pass
    with Listener(endpoint, family=endpoint_family(endpoint), authkey=key) as listener:
        while True:
            try: connection = listener.accept()
            except Exception: continue
            threading.Thread(target=serve_connection, args=(connection, journal), daemon=True).start()


def main():
    settings = get_settings()
    serve(settings, FileAuditJournal(settings, make_engine(settings.database_url)))


if __name__ == '__main__':
    main()
