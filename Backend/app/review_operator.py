"""Restricted offline tooling. Run as the private-storage operator, never expose over HTTP."""
import argparse
import json
import os
import secrets
import subprocess
from pathlib import Path
from uuid import UUID, uuid4
from datetime import datetime, timezone
from sqlalchemy import select, func
from .config import get_settings
from .database import make_engine, session_factory
from .models import User, UserRole
from .review_audit import FileAuditJournal, decision_evidence
from .private_infrastructure import file_lock, private_root, sync_directory
from .private_documents import PrivateDocuments


def restrict_directory(path):
    path.mkdir(parents=True, exist_ok=True)
    private_root(path)
    if os.name == 'nt':
        # Explicit local operator-only development ACL, no inherited Users/Everyone grants.
        import getpass
        identity = os.environ.get('USERDOMAIN', '') + '\\' + getpass.getuser()
        subprocess.run(['icacls', str(path), '/inheritance:r', '/grant:r', identity + ':(OI)(CI)F'], check=True, capture_output=True)
    else:
        path.chmod(0o700)


def initialize(settings, restrict_acl=True):
    roots = (settings.private_document_root, settings.review_audit_root)
    if not all(roots) or not settings.review_database_identity:
        raise ValueError('Configure both private roots and an independent restore-continuity identity first.')
    if Path(roots[0]).absolute() == Path(roots[1]).absolute() or any(Path(a).absolute().is_relative_to(Path(b).absolute()) for a, b in [roots, roots[::-1]]):
        raise ValueError('Private document and journal roots must be separate.')
    for root in roots:
        if restrict_acl:
            restrict_directory(Path(root))
        else:
            # Isolated test fixture under the test runner's private temporary parent.
            Path(root).mkdir(parents=True, exist_ok=True)
    audit_root = private_root(settings.review_audit_root)
    # Never overwrite keys/history on repeated provisioning.
    for name, data in [('integrity.key', secrets.token_bytes(32)), ('events.journal', b''), ('coordinator.lock', b'0')]:
        try:
            fd = os.open(audit_root / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            continue
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data); stream.flush(); os.fsync(stream.fileno())
    sync_directory(audit_root)
    if settings.review_audit_auth_file:
        credentials = settings.review_audit_auth_file.parent
        if restrict_acl: restrict_directory(credentials)
        else: credentials.mkdir(parents=True, exist_ok=True)
        try:
            fd = os.open(settings.review_audit_auth_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError: pass
        else:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(secrets.token_bytes(32)); stream.flush(); os.fsync(stream.fileno())
            sync_directory(credentials)


def provision(db, journal, user_id, operator, trace_id):
    with journal.coordinated():
        person = db.scalar(select(User).where(User.id == user_id).with_for_update())
        if not person or person.account_status not in ('ACTIVE', 'PENDING_VERIFICATION'):
            raise ValueError('An existing eligible registered account is required.')
        memberships = db.scalars(select(UserRole).where(UserRole.user_id == person.id).order_by(UserRole.id).with_for_update()).all()
        existing = next((r for r in memberships if r.role_code == 'ADMIN'), None)
        if existing:
            return 'Existing ADMIN membership: ' + existing.approval_status + ' (unchanged)'
        if not any(r.role_code == 'PASSENGER' and r.approval_status == 'APPROVED' for r in memberships):
            raise ValueError('Permanent Passenger membership is required.')
        role = UserRole(user_id=person.id, role_code='ADMIN', approval_status='APPROVED', approved_at=db.scalar(select(func.now())))
        db.add(role); db.flush()
        journal.commit(db, actor='operator:' + operator,
                       target={'resource': 'user_roles', 'id': str(role.id), 'applicant': str(person.id), 'role': 'ADMIN'},
                       previous_status=None, new_status='APPROVED', previous_version=None, new_version=1,
                       full_reason=None, previous_decision_evidence={}, trace_id=trace_id)
        return 'APPROVED ADMIN membership created; Passenger retained.'


def revoke(db, journal, user_id, operator, reason, trace_id):
    reason = reason.strip()
    if not 1 <= len(reason) <= 2000:
        raise ValueError('An applicant-visible reason of 1-2000 characters is required.')
    with journal.coordinated():
        person = db.scalar(select(User).where(User.id == user_id).with_for_update())
        if not person: raise ValueError('An existing account is required.')
        role = db.scalar(select(UserRole).where(UserRole.user_id == user_id, UserRole.role_code == 'ADMIN').with_for_update())
        if not role or role.approval_status != 'APPROVED':
            return 'No approved ADMIN membership to revoke (unchanged).'
        evidence, version = decision_evidence(role), role.version
        now = db.scalar(select(func.clock_timestamp()))
        role.approval_status = 'SUSPENDED'
        role.suspended_at = role.updated_at = now
        role.suspension_reason = reason; role.version += 1
        journal.commit(db, actor='operator:' + operator,
            target={'resource': 'user_roles', 'id': str(role.id), 'applicant': str(person.id), 'role': 'ADMIN'},
            previous_status='APPROVED', new_status='SUSPENDED', previous_version=version, new_version=role.version,
            full_reason=reason, previous_decision_evidence=evidence, trace_id=trace_id)
        return 'ADMIN membership suspended; Passenger retained.'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['init', 'recover', 'orphans', 'history', 'provision-admin', 'revoke-admin'])
    parser.add_argument('--operator', required=True)
    parser.add_argument('--user-id', type=UUID)
    parser.add_argument('--target-id', type=UUID)
    parser.add_argument('--reason')
    parser.add_argument('--confirm-environment', required=True)
    args = parser.parse_args()
    settings = get_settings()
    if args.confirm_environment != settings.environment or not args.operator.strip():
        parser.error('Explicit environment and restricted operator identity are required.')
    if args.command == 'init':
        initialize(settings)
        print('PASS: private infrastructure initialized without overwriting existing history.')
        return
    engine = make_engine(settings.database_url)
    journal, storage = FileAuditJournal(settings, engine), PrivateDocuments(settings)
    with session_factory(engine)() as db:
        if args.command in ('provision-admin', 'revoke-admin'):
            if not args.user_id: parser.error('--user-id must identify an existing account')
            if args.command == 'revoke-admin':
                if not args.reason: parser.error('--reason is required')
                print(revoke(db, journal, args.user_id, args.operator.strip(), args.reason, str(uuid4())))
            else:
                print(provision(db, journal, args.user_id, args.operator.strip(), str(uuid4())))
        else:
            with journal.coordinated():
                if args.command == 'orphans':
                    with file_lock(storage.root() / 'upload.lock'): storage.recover(db)
                if args.command == 'history':
                    if not args.target_id: parser.error('History must be scoped with --target-id')
                    records, _, _ = journal.records()
                    committed = {r['correlation_id'] for r in records if r['outcome'] == 'committed'}
                    projection = [r for r in records if r['outcome'] == 'intent' and r['correlation_id'] in committed and r['target']['id'] == str(args.target_id)]
                    journal.append(dict(correlation_id=str(uuid4()), outcome='history_read', actor='operator:' + args.operator.strip(),
                                        target={'id': str(args.target_id)}, trace_id=str(uuid4())))
                    print(json.dumps(projection, ensure_ascii=False))
                else:
                    print('PASS: reconciliation completed; no unresolved intent.')


if __name__ == '__main__':
    main()
