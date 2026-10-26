"""Acknowledged append-only HMAC journal + normal PostgreSQL transaction reconciliation.

No row-state inference, prepared transactions, history tables or best-effort logging.
The operator provisions the integrity key/segment; requests only append to that segment.
"""
import hashlib
import hmac
import json
import os
import logging
from contextlib import contextmanager
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import text
from .errors import ApiError
from .private_infrastructure import private_root, file_lock, unavailable


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, default=str).encode('utf-8')


class FileAuditJournal:
    def __init__(self, settings, engine):
        self.settings, self.engine = settings, engine

    def root(self):
        return private_root(self.settings.review_audit_root)

    def identity(self, db):
        if not self.settings.review_database_identity:
            raise unavailable()
        row = db.execute(text("SELECT current_database(), current_schema(), oid::text FROM pg_database WHERE datname=current_database()" )).one()
        return [self.settings.review_database_identity, *row]

    def records(self):
        root = self.root()
        key = (root / 'integrity.key').read_bytes()
        if len(key) != 32:
            raise unavailable()
        previous, records = '0' * 64, []
        with (root / 'events.journal').open('rb') as stream:
            for line in stream:
                if len(line) > 65536 or not line.endswith(b'\n'):
                    raise unavailable()
                frame = json.loads(line)
                data = canonical(frame['event'])
                digest = hashlib.sha256(data).hexdigest()
                tag = hmac.new(key, (previous + digest).encode(), hashlib.sha256).hexdigest()
                if frame['length'] != len(data) or frame['previous'] != previous or frame['digest'] != digest or not hmac.compare_digest(frame['tag'], tag):
                    raise unavailable()
                if frame['event']['sequence'] != len(records) + 1:
                    raise unavailable()
                previous = hashlib.sha256(line).hexdigest()
                records.append(frame['event'])
        return records, previous, key

    def append(self, event):
        records, previous, key = self.records()
        event = {**event, 'sequence': len(records) + 1, 'timestamp': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')}
        data = canonical(event)
        digest = hashlib.sha256(data).hexdigest()
        frame = canonical({'event': event, 'length': len(data), 'previous': previous, 'digest': digest,
                           'tag': hmac.new(key, (previous + digest).encode(), hashlib.sha256).hexdigest()}) + b'\n'
        fd = os.open(self.root() / 'events.journal', os.O_WRONLY | os.O_APPEND)
        try:
            view = memoryview(frame)
            while view:
                written = os.write(fd, view)
                if not written:
                    raise OSError('Audit append failed')
                view = view[written:]
            os.fsync(fd)  # Windows CRT _commit -> FlushFileBuffers
        finally:
            os.close(fd)
        return event

    def reconcile(self):
        records, _, _ = self.records()
        intents, terminals = {}, {}
        for event in records:
            cid, outcome = event['correlation_id'], event['outcome']
            if outcome == 'intent':
                if cid in intents:
                    raise unavailable()
                intents[cid] = event
            elif outcome in ('committed', 'aborted'):
                if cid not in intents or cid in terminals:
                    raise unavailable()
                terminals[cid] = outcome
            elif outcome != 'history_read':
                raise unavailable()
        for cid, event in intents.items():
            if cid in terminals:
                continue
            with self.engine.connect() as connection:
                if self.identity(connection) != event['database_identity']:
                    raise unavailable()
                outcome = self.transaction_status(connection, event['postgres_xid8'])
            if outcome not in ('committed', 'aborted'):
                raise unavailable()
            self.append({**event, 'outcome': outcome})

    def transaction_status(self, connection, xid):
        return connection.scalar(text('SELECT pg_xact_status(CAST(:xid AS xid8))'), {'xid': xid})

    def outcome(self, correlation_id):
        records, _, _ = self.records()
        return next((r['outcome'] for r in records if r['correlation_id'] == correlation_id and r['outcome'] in ('committed', 'aborted')), None)

    @contextmanager
    def coordinated(self):
        try:
            with file_lock(self.root() / 'coordinator.lock'):
                self.reconcile()
                yield
        except ApiError:
            raise
        except Exception as exc:
            logging.getLogger('travelly').warning('review_dependency_failure type=%s', type(exc).__name__)
            diag = getattr(getattr(exc, 'orig', None), 'diag', None)
            if diag:
                logging.getLogger('travelly').warning('review_constraint_failure constraint=%s', diag.constraint_name)
            raise unavailable() from None

    def commit(self, db, *, actor, target, previous_status, new_status, previous_version,
               new_version, full_reason, previous_decision_evidence, trace_id):
        """Caller holds coordinator + row locks. A failed intent never reaches COMMIT."""
        try:
            db.execute(text('SET LOCAL synchronous_commit = on'))
            if db.scalar(text('SHOW fsync')) != 'on':
                raise unavailable()
            db.flush()
            event = dict(correlation_id=str(uuid4()), actor=str(actor), target=target,
                         previous_status=previous_status, new_status=new_status,
                         previous_version=previous_version, new_version=new_version,
                         full_reason=full_reason, previous_decision_evidence=previous_decision_evidence,
                         trace_id=trace_id, postgres_xid8=str(db.scalar(text('SELECT pg_current_xact_id()::text'))),
                         database_identity=self.identity(db), outcome='intent')
            self.append(event)
        except Exception:
            db.rollback()
            raise unavailable() from None
        try:
            db.commit()
            self.append({**event, 'outcome': 'committed'})
        except Exception:
            # Closing the uncertain connection establishes no outcome by itself.
            db.close()
            try:
                self.reconcile()
                if self.outcome(event['correlation_id']) == 'committed':
                    return
            except Exception:
                pass
            raise ApiError(500, 'INTERNAL_ERROR', 'The decision outcome could not be confirmed. Refresh before retrying.') from None


def decision_evidence(row):
    names = ('approved_by', 'approved_at', 'rejection_reason', 'suspended_at', 'suspension_reason',
             'verified_by', 'verified_at', 'updated_by', 'updated_at')
    return {name: (str(getattr(row, name)) if getattr(row, name) is not None else None)
            for name in names if hasattr(row, name)}


class AuditJournal(FileAuditJournal):
    """Runtime adapter. Isolated writer IPC gives the web identity no journal/key access.

    Embedded mode is retained for isolated unit fixtures/offline development only.
    Production configuration requires the external writer endpoint.
    """
    def __init__(self, settings, engine):
        super().__init__(settings, engine)
        import threading
        self.connection = threading.local()

    def rpc(self, action, event=None):
        connection = getattr(self.connection, 'value', None)
        if connection is None:
            raise unavailable()
        connection.send_bytes(canonical({'action': action, 'event': event}))
        if not connection.poll(20):
            raise unavailable()
        result = json.loads(connection.recv_bytes(65536))
        if result.get('ok') is not True:
            raise unavailable()
        return result.get('event')

    @contextmanager
    def coordinated(self):
        if not self.settings.review_audit_endpoint:
            with super().coordinated():
                yield
            return
        from multiprocessing.connection import Client
        from .review_writer import endpoint_family
        try:
            key = self.settings.review_audit_auth_file.read_bytes()
            if len(key) != 32:
                raise unavailable()
            connection = Client(self.settings.review_audit_endpoint, family=endpoint_family(self.settings.review_audit_endpoint), authkey=key)
            self.connection.value = connection
            self.rpc('begin')
            try:
                yield
            finally:
                # Closing releases the writer's OS coordination lock even when a web worker crashes.
                try:
                    self.rpc('end')
                except Exception:
                    # No status assertion depends on releasing a lock; socket close releases it.
                    pass
                finally:
                    connection.close(); self.connection.value = None
        except ApiError:
            raise
        except Exception:
            raise unavailable() from None

    def append(self, event):
        if self.settings.review_audit_endpoint:
            return self.rpc('append', event)
        return super().append(event)

    def reconcile(self):
        if self.settings.review_audit_endpoint:
            if getattr(self.connection, 'value', None) is not None:
                return self.rpc('recover')
            with self.coordinated():
                return
        return super().reconcile()

    def records(self):
        if self.settings.review_audit_endpoint:
            # Historical reads are restricted offline operations, never a web-identity RPC.
            raise unavailable()
        return super().records()

    def outcome(self, correlation_id):
        if self.settings.review_audit_endpoint:
            return self.rpc('outcome', {'correlation_id': correlation_id})
        return super().outcome(correlation_id)
