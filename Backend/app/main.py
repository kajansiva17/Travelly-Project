import json
import logging
import asyncio
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from uuid import uuid4
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi
from redis.exceptions import RedisError
from sqlalchemy.exc import SQLAlchemyError
from .api import router
from .config import get_settings
from .database import make_engine, session_factory
from .errors import ApiError
from .sessions import SessionStore
from .schemas import MIN_PASSWORD_LENGTH, password_requirements
from .auth_extension import router as auth_extension_router
from .auth_services import AuthState, Mailer, GoogleIdentity
from .review_api import router as review_router
from .review_audit import AuditJournal
from .private_documents import PrivateDocuments, MAX_MULTIPART
from .private_infrastructure import file_lock
from starlette.concurrency import run_in_threadpool

logger = logging.getLogger('travelly')


def error_response(request, exc):
    return JSONResponse(status_code=exc.status, content={'code': exc.code, 'message': exc.message,
        'field_errors': exc.fields, 'trace_id': request.state.trace_id}, headers={
        'Cache-Control': 'no-store', 'X-Request-ID': request.state.trace_id, **exc.headers})


def create_app(settings=None, engine=None, store=None):
    settings = settings or get_settings()
    def maintenance(app, cleanup=False):
        if not settings.review_audit_root:
            return
        try:
            with app.state.audit.coordinated():
                if cleanup and settings.private_document_root:
                    with file_lock(app.state.documents.root() / 'upload.lock'), app.state.sessions() as db:
                        app.state.documents.recover(db)
        except Exception:
            # Auth stays available; every subsequent mutation still fails closed until recovery succeeds.
            logger.warning('review_recovery_required')

    @asynccontextmanager
    async def lifespan(app):
        await run_in_threadpool(maintenance, app, True)
        async def recovery_loop():
            while True:
                await asyncio.sleep(30)
                await run_in_threadpool(maintenance, app)
        task = asyncio.create_task(recovery_loop())
        try:
            yield
        finally:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task

    app = FastAPI(title='Travelly API', version='1.0.0', lifespan=lifespan, swagger_ui_parameters={'persistAuthorization': False})
    app.state.settings = settings
    app.state.engine = engine or make_engine(settings.database_url)
    app.state.sessions = session_factory(app.state.engine)
    app.state.store = store or SessionStore(settings.redis_url)
    app.state.auth_state = AuthState(app.state.store)
    app.state.mailer = Mailer(settings, app.state.store)
    app.state.google = GoogleIdentity(settings.google_client_id)
    app.state.audit = AuditJournal(settings, app.state.engine)
    app.state.documents = PrivateDocuments(settings)

    @app.exception_handler(ApiError)
    async def api_error(request, exc):
        return error_response(request, exc)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        # No input values/context from Pydantic: passwords and tokens must never be echoed.
        fields = []
        for error in exc.errors():
            message = 'Invalid or unsupported value.'
            if request.url.path in ('/api/v1/auth/register', '/api/v1/auth/password/reset') and error['loc'] == ('body', 'password'):
                if error['type'] == 'string_too_short':
                    message = f'Use at least {MIN_PASSWORD_LENGTH} characters.'
                elif error['type'] == 'string_too_long':
                    message = 'Use at most 128 characters.'
                elif isinstance(error.get('input'), str):
                    message = ' '.join(password_requirements(error['input'])) or 'Enter a valid password.'
            if error['loc'] == ('body', 'email'):
                message = 'Enter a valid public email address, such as name@example.com, without spaces inside it.'
            if error['loc'] == ('body', 'identifier'):
                message = 'Enter a valid email address or an international mobile number with its country code.'
            if error['loc'] == ('body', 'accept_terms'):
                message = 'Agree to the Terms and Privacy Policy to continue.'
            if error['loc'] == ('body', 'confirm'):
                message = 'Confirm that you want to connect Google to this account.'
            if error['loc'] == ('body', 'phone_e164'):
                message = 'Enter a valid international mobile number with its country code.'
            fields.append({'field': '.'.join(str(x) for x in error['loc'] if x != 'body'),
                           'code': error['type'], 'message': message})
        return error_response(request, ApiError(422, 'VALIDATION_ERROR', 'Request validation failed.', fields))

    @app.middleware('http')
    async def boundary(request: Request, call_next):
        request.state.trace_id = str(uuid4())
        try:
            if request.url.path.startswith('/api/v1/'):
                ip = request.client.host if request.client else 'unknown'
                name = request.url.path.rsplit('/', 1)[-1]
                limit, seconds = {'register': (10, 900), 'login': (30, 900), 'refresh': (60, 60), 'logout': (60, 60)}.get(name, (300, 60))
                if request.url.path.startswith('/api/v1/auth/') and name in ('challenge', 'google', 'complete', 'resend', 'verify', 'forgot', 'reset'):
                    limit, seconds = (30, 900)
                group = 'profile' if request.url.path in ('/api/v1/users/me', '/api/v1/users/me/roles') else name
                review_path = request.url.path.startswith(('/api/v1/admin/', '/api/v1/documents'))
                multipart = request.url.path == '/api/v1/documents' and request.method == 'POST'
                if review_path:
                    group, limit, seconds = ('files', 100, 60) if name == 'file' else ('review', 100, 60) if request.method == 'PATCH' else ('upload', 30, 900) if multipart else ('metadata', 300, 60)
                app.state.store.rate(f'ip:{group}:{ip}', limit, seconds)
                query_route = request.method == 'GET' and request.url.path in ('/api/v1/documents', '/api/v1/admin/role-requests')
                if request.query_params and not query_route:
                    raise ApiError(422, 'VALIDATION_ERROR', 'Query parameters are not supported.')
                if request.method in ('POST', 'PATCH'):
                    media = 'multipart/form-data' if multipart else 'application/json'
                    if request.headers.get('content-type', '').split(';')[0].lower() != media:
                        raise ApiError(415, 'UNSUPPORTED_MEDIA_TYPE', 'Use ' + media + '.')
                    chunks, length = [], 0
                    async for chunk in request.stream():
                        length += len(chunk)
                        if length > (MAX_MULTIPART if multipart else 8192):
                            raise ApiError(413, 'REQUEST_TOO_LARGE', 'Request exceeds the permitted size.')
                        chunks.append(chunk)
                    raw = b''.join(chunks)
                    request._body = raw
                    def unique_keys(pairs):
                        result = {}
                        for key, value in pairs:
                            if key in result:
                                raise ValueError()
                            result[key] = value
                        return result
                    if raw and not multipart:
                        try:
                            parsed = json.loads(raw, object_pairs_hook=unique_keys, parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
                        except (ValueError, UnicodeError):
                            raise ApiError(400, 'MALFORMED_REQUEST', 'Malformed JSON or duplicate keys.') from None
                        if not isinstance(parsed, dict):
                            raise ApiError(422, 'VALIDATION_ERROR', 'A JSON object is required.')
                elif request.method == 'GET' and await request.body():
                    raise ApiError(422, 'VALIDATION_ERROR', 'GET requests have no body.')
            response = await call_next(request)
        except ApiError as exc:
            response = error_response(request, exc)
        except (RedisError, SQLAlchemyError) as exc:
            logger.warning('auth_dependency_failure trace=%s type=%s sqlstate=%s', request.state.trace_id,
                           type(exc).__name__, getattr(getattr(exc, 'orig', None), 'sqlstate', None))
            is_review = request.url.path.startswith(('/api/v1/admin/', '/api/v1/documents'))
            response = error_response(request, ApiError(503, 'REVIEW_DEPENDENCY_UNAVAILABLE' if is_review else 'AUTH_DEPENDENCY_UNAVAILABLE', 'The service is temporarily unavailable.'))
        except Exception:
            # Do not log exception text: driver errors can contain sensitive data.
            logger.error('internal_failure trace=%s', request.state.trace_id)
            response = error_response(request, ApiError(500, 'INTERNAL_ERROR', 'An unexpected error occurred.'))
        response.headers['Cache-Control'] = 'no-store'
        response.headers['Pragma'] = 'no-cache'
        response.headers['X-Request-ID'] = request.state.trace_id
        response.headers['X-Content-Type-Options'] = 'nosniff'
        return response

    app.include_router(router)
    app.include_router(auth_extension_router)
    app.include_router(review_router)
    def contracted_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        schema = get_openapi(title='Travelly API', version='1.0.0', routes=app.routes)
        contract = json.loads((Path(__file__).parents[2] / 'docs/03-API/03C-TRAVELLY-ADMIN-REVIEW-OPENAPI.json').read_text(encoding='utf-8'))
        for path, operations in contract['paths'].items():
            schema['paths'].setdefault(path, {}).update(operations)
        for group, entries in contract['components'].items():
            schema.setdefault('components', {}).setdefault(group, {}).update(entries)
        app.openapi_schema = schema
        return schema
    app.openapi = contracted_openapi
    # CORS wraps error responses too; cross-origin clients can read safe 401/429/503 details.
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins,
                       allow_methods=['GET', 'POST', 'PATCH', 'OPTIONS'], allow_headers=['Authorization', 'Content-Type'],
                       expose_headers=['Retry-After', 'X-Request-ID'])
    return app


app = create_app()
