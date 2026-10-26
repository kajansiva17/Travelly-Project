"""The eight frozen Admin Review/document operations (03C/03D)."""
import re
from datetime import date, datetime, timezone
from typing import Literal
from uuid import UUID
from zoneinfo import ZoneInfo
from urllib.parse import quote
import pycountry
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator, model_validator, ValidationError
from sqlalchemy import select, func, or_, exists
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile
from .api import current, allowed_account, touch
from .database import get_db
from .errors import ApiError, unauthorized
from .models import User, UserRole
from .schemas import RoleResponse
from .review_models import Document, Vehicle
from .review_audit import decision_evidence
from .private_infrastructure import file_lock, unavailable
from .private_documents import DOCUMENT_TYPES, DOCUMENT_STATES, document_summary, document_detail

class UTCJSONResponse(JSONResponse):
    def render(self, content):
        def utc(value):
            if isinstance(value, dict):
                return {key: val[:-6] + 'Z' if key.endswith('_at') and isinstance(val, str) and val.endswith('+00:00') else utc(val) for key, val in value.items()}
            if isinstance(value, list): return [utc(v) for v in value]
            return value
        return super().render(utc(content))


router = APIRouter(prefix='/api/v1', default_response_class=UTCJSONResponse)
ROLE_STATES = ('PENDING', 'APPROVED', 'REJECTED', 'SUSPENDED')


def validation(field='request'):
    return ApiError(422, 'VALIDATION_ERROR', 'Request validation failed.',
                    [{'field': field, 'code': 'invalid_value', 'message': 'Invalid or unsupported value.'}])


class ReviewBody(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    decision: str
    version: StrictInt = Field(ge=1)
    reason: str | None = None

    @field_validator('reason')
    @classmethod
    def clean_reason(cls, value):
        if value is not None:
            value = value.strip()
            if not 1 <= len(value) <= 2000 or any(ord(c) < 32 and c not in '\n\r\t' for c in value):
                raise ValueError('Invalid reason')
        return value

    @model_validator(mode='after')
    def reason_rule(self):
        if (self.decision in ('REJECTED', 'SUSPENDED', 'NEEDS_CORRECTION')) != (self.reason is not None):
            raise ValueError('Invalid reason')
        return self


class RoleReview(ReviewBody):
    decision: Literal['APPROVED', 'REJECTED', 'SUSPENDED']


class DocumentReview(ReviewBody):
    decision: Literal['UNDER_REVIEW', 'APPROVED', 'REJECTED', 'NEEDS_CORRECTION']


class UploadMetadata(BaseModel):
    model_config = ConfigDict(extra='forbid')
    owner_type: Literal['USER', 'VEHICLE']
    owner_id: UUID
    document_type: str
    number: str | None = Field(default=None, min_length=1, max_length=100)
    issuing_country: str | None = None
    issue_date: date | None = None
    expiry_date: date | None = None

    @field_validator('number', mode='before')
    @classmethod
    def trim(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator('issue_date', 'expiry_date', mode='before')
    @classmethod
    def iso_dates(cls, value):
        if value is not None and (not isinstance(value, str) or not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', value)):
            raise ValueError()
        return value

    @field_validator('document_type')
    @classmethod
    def valid_type(cls, value):
        if value not in DOCUMENT_TYPES:
            raise ValueError()
        return value

    @field_validator('issuing_country')
    @classmethod
    def valid_country(cls, value):
        if value is not None and (not re.fullmatch(r'[A-Z]{2}', value) or pycountry.countries.get(alpha_2=value) is None):
            raise ValueError()
        return value

    @field_validator('expiry_date')
    @classmethod
    def valid_expiry(cls, value, info):
        if value and info.data.get('issue_date') and value < info.data['issue_date']:
            raise ValueError('date_order')
        return value


def upload_metadata_error(exc):
    # Never echo inputs or Pydantic exception context into private-file errors.
    messages = {
        'number': 'Enter 1–100 characters, or leave this optional field blank.',
        'issuing_country': 'Choose the country that issued the document, or leave it blank.',
        'issue_date': 'Enter a valid date, or leave this optional field blank.',
        'expiry_date': 'Enter a valid date, or leave this optional field blank.',
        'document_type': 'Choose a supported document type.',
    }
    fields = []
    for error in exc.errors():
        field = str(error['loc'][0]) if error['loc'] else 'request'
        # Allowlist field names too: unknown multipart names are untrusted input.
        field = field if field in UploadMetadata.model_fields else 'request'
        message = messages.get(field, 'Invalid or unsupported value.')
        if field == 'expiry_date' and error['type'] == 'value_error':
            message = 'Expiry date must be on or after the issue date.' if error.get('ctx', {}).get('error') and str(error['ctx']['error']) == 'date_order' else message
        fields.append({'field': field, 'code': 'invalid_value', 'message': message})
    return ApiError(422, 'VALIDATION_ERROR', 'Check the highlighted fields.', fields)


def is_admin(db, user):
    return bool(db.scalar(select(UserRole.id).where(UserRole.user_id == user.id, UserRole.role_code == 'ADMIN', UserRole.approval_status == 'APPROVED')))


def admin(user=Depends(current), db: Session = Depends(get_db)):
    if not is_admin(db, user):
        raise ApiError(403, 'ADMIN_REQUIRED', 'Admin access is required.')
    return user


def locked_authority(db, request, user, applicant_id, require_admin=True):
    # Deterministic identity then membership locks; recheck live session/account/role.
    ids = sorted({user.id, applicant_id}, key=str)
    rows = db.scalars(select(User).where(User.id.in_(ids)).order_by(User.id).with_for_update().execution_options(populate_existing=True)).all()
    caller = next(r for r in rows if r.id == user.id)
    allowed_account(caller)
    claims = request.state.auth_claims
    if claims.get('av', 0) != caller.auth_version: raise unauthorized()
    request.app.state.store.get(claims['sid'], claims['sub'])
    db.scalars(select(UserRole).where(UserRole.user_id.in_(ids)).order_by(UserRole.user_id, UserRole.id).with_for_update().execution_options(populate_existing=True)).all()
    if require_admin and not is_admin(db, caller):
        raise ApiError(403, 'ADMIN_REQUIRED', 'Admin access is required.')


def application(db, role_id, user, lock=False):
    query = select(UserRole).where(UserRole.id == role_id, UserRole.role_code.in_(('OWNER', 'DRIVER')))
    if lock:
        query = query.with_for_update().execution_options(populate_existing=True)
    row = db.scalar(query)
    if not row:
        raise ApiError(404, 'APPLICATION_NOT_FOUND', 'Application not found.')
    if row.user_id == user.id:
        raise ApiError(403, 'REVIEW_FORBIDDEN', 'Self review is not permitted.')
    return row


def query_values(request, allowed):
    pairs = list(request.query_params.multi_items())
    if any(k not in allowed for k, _ in pairs) or len({k for k, _ in pairs}) != len(pairs):
        raise validation('query')
    return dict(pairs)


def pagination(params):
    values = []
    for name, default, maximum in [('page', 1, None), ('page_size', 20, 100)]:
        value = params.get(name, str(default))
        if not re.fullmatch(r'[0-9]+', value) or len(value) > 10 or not 1 <= int(value) <= (maximum or 2147483647):
            raise validation('query.' + name)
        values.append(int(value))
    return values


def page_result(items, page, size, total):
    return dict(items=items, page=page, page_size=size, total=total, has_next=page * size < total)


def current_documents(db, user_id, role=None, lock=False):
    replacement = Document.__table__.alias('replacement')
    types = ('NIC', 'PASSPORT', 'VEHICLE_REGISTRATION', 'OWNER_AUTHORISATION') if role == 'OWNER' else ('NIC', 'PASSPORT', 'DRIVING_LICENCE')
    query = select(Document).where(Document.user_id == user_id, Document.document_type.in_(types),
                                  Document.status != 'SUPERSEDED', ~exists(select(replacement.c.id).where(replacement.c.superseded_document_id == Document.id))).order_by(Document.id)
    if lock:
        query = query.with_for_update().execution_options(populate_existing=True)
    return db.scalars(query).all()


@router.get('/admin/role-requests')
def queue(request: Request, user=Depends(admin), db: Session = Depends(get_db)):
    p = query_values(request, {'page', 'page_size', 'status', 'role_code', 'q'})
    page, size = pagination(p)
    raw_q = p.get('q', '')
    status, role, q = p.get('status', 'PENDING'), p.get('role_code'), raw_q.strip()
    if status not in (*ROLE_STATES, 'ALL') or (role is not None and role not in ('OWNER', 'DRIVER')) or len(q) > 100 or any(ord(c) < 32 or ord(c) == 127 for c in raw_q):
        raise validation('query')
    clauses = [UserRole.role_code.in_(('OWNER', 'DRIVER')), UserRole.user_id != user.id]
    if status != 'ALL': clauses.append(UserRole.approval_status == status)
    if role: clauses.append(UserRole.role_code == role)
    if q:
        literal = '%' + q.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%'
        clauses.append(or_(User.full_name.ilike(literal, escape='\\'), User.public_user_reference.ilike(literal, escape='\\')))
    query = select(UserRole, User).join(User, User.id == UserRole.user_id).where(*clauses)
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    rows = db.execute(query.order_by(UserRole.requested_at, UserRole.id).offset((page - 1) * size).limit(size)).all()
    return page_result([{**{k: getattr(role, k) for k in ('id', 'role_code', 'approval_status', 'requested_at', 'version')},
                         'applicant': {k: getattr(person, k) for k in ('id', 'public_user_reference', 'full_name')}} for role, person in rows], page, size, total)


@router.get('/admin/role-requests/{role_id}')
def detail(role_id: UUID, request: Request, user=Depends(admin), db: Session = Depends(get_db)):
    row = application(db, role_id, user)
    person = db.get(User, row.user_id)
    return {'application': {**RoleResponse.model_validate(row).model_dump(), **{k: getattr(row, k) for k in ('approved_by', 'updated_by', 'updated_at')}},
            'applicant': {k: getattr(person, k) for k in ('id', 'public_user_reference', 'full_name', 'display_name', 'email', 'phone_e164', 'account_status', 'email_verified_at', 'phone_verified_at')},
            'documents': [document_summary(d) for d in current_documents(db, row.user_id, row.role_code)]}


def evidence_ready(db, request, row):
    today = datetime.now(ZoneInfo('Asia/Colombo')).date()
    eligible = []
    for doc in current_documents(db, row.user_id, row.role_code, lock=True):
        if doc.status != 'APPROVED' or not doc.verified_by or not doc.verified_at or doc.verified_by == row.user_id:
            continue
        if (doc.expiry_date and doc.expiry_date < today) or (doc.issue_date and doc.issue_date > today):
            continue
        if doc.document_type in ('DRIVING_LICENCE', 'PASSPORT') and not doc.expiry_date:
            continue
        with request.app.state.documents.open_verified(doc):
            pass
        eligible.append(doc)
    types = {d.document_type for d in eligible}
    identity = bool(types & {'NIC', 'PASSPORT'})
    other = bool(types & {'VEHICLE_REGISTRATION', 'OWNER_AUTHORISATION'}) if row.role_code == 'OWNER' else any(d.document_type == 'DRIVING_LICENCE' and d.issuing_country == 'LK' for d in eligible)
    if not identity or not other:
        raise ApiError(409, 'REQUIRED_EVIDENCE_NOT_VERIFIED', 'Required evidence must be verified before approval.')


@router.patch('/admin/role-requests/{role_id}/review', response_model=RoleResponse)
def review_role(role_id: UUID, body: RoleReview, request: Request, user=Depends(admin), db: Session = Depends(get_db)):
    journal = request.app.state.audit
    with journal.coordinated():
        row = application(db, role_id, user)
        locked_authority(db, request, user, row.user_id)
        row = application(db, role_id, user, lock=True)
        if body.version != row.version:
            raise ApiError(409, 'VERSION_CONFLICT', 'This application has changed. Refresh before reviewing.')
        if (row.approval_status, body.decision) not in [('PENDING', 'APPROVED'), ('PENDING', 'REJECTED'), ('APPROVED', 'SUSPENDED')]:
            raise ApiError(409, 'INVALID_REVIEW_TRANSITION', 'This decision is not available for the current status.')
        if body.decision == 'APPROVED': evidence_ready(db, request, row)
        before, evidence, version = row.approval_status, decision_evidence(row), row.version
        now = datetime.now(timezone.utc)
        row.approval_status = body.decision
        if body.decision == 'APPROVED': row.approved_by, row.approved_at = user.id, now
        elif body.decision == 'REJECTED': row.rejection_reason = body.reason
        else: row.suspended_at, row.suspension_reason = now, body.reason
        touch(row); row.updated_by = user.id
        result = RoleResponse.model_validate(row)
        journal.commit(db, actor=user.id, target={'resource': 'user_roles', 'id': str(row.id), 'applicant': str(row.user_id), 'role': row.role_code},
                       previous_status=before, new_status=row.approval_status, previous_version=version, new_version=row.version,
                       full_reason=body.reason, previous_decision_evidence=evidence, trace_id=request.state.trace_id)
        return result


def document_owner(db, doc, lock=False):
    if doc.user_id: return doc.user_id
    query = select(Vehicle).where(Vehicle.id == doc.vehicle_id)
    if lock: query = query.with_for_update().execution_options(populate_existing=True)
    vehicle = db.scalar(query)
    if not vehicle: raise unavailable()
    return vehicle.owner_user_id


def owned_document(db, document_id, user):
    doc = db.get(Document, document_id)
    if not doc or (document_owner(db, doc) != user.id and not is_admin(db, user)):
        raise ApiError(404, 'DOCUMENT_NOT_FOUND', 'Document not found.')
    return doc


@router.get('/documents')
def documents(request: Request, user=Depends(current), db: Session = Depends(get_db)):
    p = query_values(request, {'page', 'page_size', 'user_id', 'vehicle_id', 'document_type', 'status'})
    page, size = pagination(p)
    if ('user_id' in p and 'vehicle_id' in p) or ('document_type' in p and p['document_type'] not in DOCUMENT_TYPES) or ('status' in p and p['status'] not in DOCUMENT_STATES):
        raise validation('query')
    clauses = []
    for key in ('user_id', 'vehicle_id'):
        if key not in p: continue
        try: value = UUID(p[key])
        except ValueError: raise validation('query.' + key) from None
        if not is_admin(db, user):
            owner = value if key == 'user_id' else db.scalar(select(Vehicle.owner_user_id).where(Vehicle.id == value))
            if owner != user.id: raise ApiError(404, 'DOCUMENT_NOT_FOUND', 'Document not found.')
        clauses.append(getattr(Document, key) == value)
    if not is_admin(db, user):
        clauses.append(or_(Document.user_id == user.id, Document.vehicle_id.in_(select(Vehicle.id).where(Vehicle.owner_user_id == user.id))))
    for key in ('document_type', 'status'):
        if key in p: clauses.append(getattr(Document, key) == p[key])
    query = select(Document).where(*clauses)
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    rows = db.scalars(query.order_by(Document.submitted_at.desc().nullslast(), Document.id).offset((page - 1) * size).limit(size)).all()
    return page_result([document_summary(d) for d in rows], page, size, total)


@router.get('/documents/{document_id}')
def get_document(document_id: UUID, user=Depends(current), db: Session = Depends(get_db)):
    return document_detail(owned_document(db, document_id, user))


@router.get('/documents/{document_id}/file')
def stream_document(document_id: UUID, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    doc = owned_document(db, document_id, user)
    stream = request.app.state.documents.open_verified(doc)
    def chunks():
        with stream:
            while chunk := stream.read(65536):
                yield chunk
    return StreamingResponse(chunks(), media_type=doc.mime_type, headers={
        'Content-Length': str(doc.file_size_bytes), 'Content-Disposition': "inline; filename=\"document\"; filename*=UTF-8''" + quote(doc.original_file_name, safe=''),
        'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'})


@router.patch('/admin/documents/{document_id}/review')
def review_document(document_id: UUID, body: DocumentReview, request: Request, user=Depends(admin), db: Session = Depends(get_db)):
    with request.app.state.audit.coordinated():
        doc = owned_document(db, document_id, user)
        owner = document_owner(db, doc, lock=True)
        if owner == user.id: raise ApiError(403, 'REVIEW_FORBIDDEN', 'Self review is not permitted.')
        locked_authority(db, request, user, owner)
        doc = db.scalar(select(Document).where(Document.id == document_id).with_for_update().execution_options(populate_existing=True))
        if doc.version != body.version: raise ApiError(409, 'VERSION_CONFLICT', 'This document has changed. Refresh before reviewing.')
        if (doc.status, body.decision) not in [('SUBMITTED', 'UNDER_REVIEW'), ('UNDER_REVIEW', 'APPROVED'), ('UNDER_REVIEW', 'REJECTED'), ('UNDER_REVIEW', 'NEEDS_CORRECTION')]:
            raise ApiError(409, 'INVALID_REVIEW_TRANSITION', 'This decision is not available for the current status.')
        if db.scalar(select(Document.id).where(Document.superseded_document_id == doc.id).limit(1)):
            raise ApiError(409, 'INVALID_REVIEW_TRANSITION', 'This document has been replaced.')
        with request.app.state.documents.open_verified(doc): pass
        before, evidence, version = doc.status, decision_evidence(doc), doc.version
        doc.status = body.decision; touch(doc); doc.updated_by = user.id
        if body.decision != 'UNDER_REVIEW':
            doc.verified_by, doc.verified_at, doc.rejection_reason = user.id, datetime.now(timezone.utc), body.reason
        result = {**document_summary(doc), 'verified_by': doc.verified_by}
        request.app.state.audit.commit(db, actor=user.id, target={'resource': 'documents', 'id': str(doc.id), 'applicant': str(owner)},
            previous_status=before, new_status=doc.status, previous_version=version, new_version=doc.version, full_reason=body.reason,
            previous_decision_evidence=evidence, trace_id=request.state.trace_id)
        return result


def save_upload(meta, upload, request, user, db):
    storage, journal = request.app.state.documents, request.app.state.audit
    with journal.coordinated(), file_lock(storage.root() / 'upload.lock'):
        locked_authority(db, request, user, user.id, require_admin=False)
        owner = user.id if meta.owner_type == 'USER' else db.scalar(select(Vehicle.owner_user_id).where(Vehicle.id == meta.owner_id).with_for_update())
        if owner != user.id or (meta.owner_type == 'USER' and meta.owner_id != user.id):
            raise ApiError(404, 'DOCUMENT_NOT_FOUND', 'Document not found.')
        storage.recover(db)
        # Replacement rows link the most recent same-owner/type file; old rows/bytes/reasons are retained.
        fk = 'user_id' if meta.owner_type == 'USER' else 'vehicle_id'
        prior = db.scalar(select(Document).where(getattr(Document, fk) == meta.owner_id, Document.document_type == meta.document_type).order_by(Document.created_at.desc(), Document.id.desc()).limit(1).with_for_update())
        file_data = storage.place(upload)
        row = Document(**file_data, **{fk: meta.owner_id}, document_type=meta.document_type, document_number=meta.number,
                       issuing_country=meta.issuing_country, issue_date=meta.issue_date, expiry_date=meta.expiry_date,
                       status='SUBMITTED', submitted_at=datetime.now(timezone.utc), created_by=user.id,
                       superseded_document_id=prior.id if prior else None)
        try:
            db.add(row); db.flush()
            result = document_detail(row)
            storage.mark_transaction(row.storage_key, db)
            db.commit()
            storage.finish_transaction(row.storage_key)
            return result
        except Exception:
            # Uncertain COMMIT: retain placed bytes. The locked maintenance pass checks references later.
            db.close()
            raise unavailable() from None


@router.post('/documents', status_code=201)
async def upload_document(request: Request, user=Depends(current), db: Session = Depends(get_db)):
    try:
        async with request.form(max_files=2, max_fields=12, max_part_size=8192) as form:
            pairs = list(form.multi_items())
            if len({k for k, _ in pairs}) != len(pairs): raise validation()
            upload = form.get('file')
            if not isinstance(upload, UploadFile) or sum(isinstance(v, UploadFile) for _, v in pairs) != 1:
                raise validation('file')
            fields = {k: v for k, v in pairs if k != 'file'}
            if any(not isinstance(v, str) for v in fields.values()) or sum(len(v.encode('utf-8')) for v in fields.values()) > 8192:
                raise ApiError(413, 'REQUEST_TOO_LARGE', 'Multipart fields exceed 8 KiB.')
            if any(v == 'null' for v in fields.values()): raise validation()
            try: meta = UploadMetadata.model_validate(fields)
            except ValidationError as exc: raise upload_metadata_error(exc) from None
            return await run_in_threadpool(save_upload, meta, upload, request, user, db)
    except ApiError: raise
    except Exception as exc:
        # Malformed multipart must never escape as a parser traceback.
        from starlette.exceptions import HTTPException
        if isinstance(exc, HTTPException) and 'Part exceeded maximum size' in str(exc.detail):
            raise ApiError(413, 'REQUEST_TOO_LARGE', 'Multipart fields exceed 8 KiB.') from None
        if isinstance(exc, (HTTPException, ValueError)): raise validation('file') from None
        raise unavailable() from None
