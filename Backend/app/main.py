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
from app.api.routers.api import router
from app.core.config import get_settings
from app.dependencies.database import make_engine, session_factory
from app.core.errors import ApiError
from app.core.sessions import SessionStore
from app.core import session_cookie
from app.api.routers.fulfilment_api import router as fulfilment_router
from app.api.routers.road_alerts_api import router as road_alerts_router
from app.api.routers.ai_api import router as ai_router
from app.api.routers.odometer_api import router as odometer_router
from app.api.routers.social_api import router as social_router
from app.api.routers.account_settings_api import router as account_settings_router
from app.api.routers.account_security_api import router as account_security_router
from app.api.routers.airport_api import router as airport_router
from app.api.routers.report_api import router as report_router
from app.schemas import MIN_PASSWORD_LENGTH, password_requirements
from app.api.routers.auth_extension import router as auth_extension_router
from app.services.auth_services import AuthState, Mailer, GoogleIdentity
from app.api.routers.review_api import router as review_router
from app.services.review_audit import AuditJournal
from app.services.private_documents import PrivateDocuments, MAX_MULTIPART
from app.core.private_infrastructure import file_lock
from app.api.routers.rate_api import router as rate_router
from app.services.rate_locations import RateLocations
from app.api.routers.hire_api import router as hire_router
from app.api.routers.rental_api import router as rental_router
from app.services.hire_routing import HireRouting
from app.api.routers.vehicle_api import router as vehicle_router
from app.api.routers.stage5_admin_api import router as stage5_admin_router
from app.api.routers.ticket_booking_api import router as ticket_router
from app.api.routers.route_api import router as route_router
from app.api.routers.scheduled_trip_api import router as scheduled_trip_router
from app.api.routers.payment_api import router as payment_router
from app.api.routers.refund_api import router as refund_router
from app.api.routers.settlement_api import router as settlement_router
from app.api.routers.vehicle_records_api import router as vehicle_records_router
from app.api.routers.favourite_api import router as favourite_router
from app.api.routers.owner_driver_api import router as owner_driver_router
from app.api.routers.driver_payment_api import router as driver_payment_router
from app.api.routers.live_vehicle_api import router as live_vehicle_router
from app.api.routers.ride_now_api import router as ride_now_router
from app.api.routers.saved_place_api import router as saved_place_router
from app.api.routers.support_api import router as support_router
from app.api.routers.owner_expense_api import router as owner_expense_router
from app.api.routers.trip_review_api import router as trip_review_router
from app.api.routers.seat_inventory_api import router as seat_inventory_router
from app.api.routers.charge_report_api import router as charge_report_router
from app.api.routers.trip_km_api import router as trip_km_router
from app.api.routers.admin_summary_api import router as admin_summary_router
from app.services.vehicle_media import VehiclePhotos
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
            app.state.hire_routing.close()

    app = FastAPI(title='Travelly API', version='1.0.0', lifespan=lifespan, swagger_ui_parameters={'persistAuthorization': False})
    app.state.settings = settings
    app.state.vehicle_photos = VehiclePhotos(settings)
    app.state.engine = engine or make_engine(settings.database_url)
    app.state.sessions = session_factory(app.state.engine)
    app.state.store = store or SessionStore(settings.redis_url)
    app.state.auth_state = AuthState(app.state.store)
    app.state.mailer = Mailer(settings, app.state.store)
    app.state.google = GoogleIdentity(settings.google_client_id)
    app.state.audit = AuditJournal(settings, app.state.engine)
    app.state.documents = PrivateDocuments(settings)
    app.state.rate_locations = RateLocations(settings)
    app.state.hire_routing = HireRouting(settings, app.state.rate_locations)

    @app.exception_handler(ApiError)
    async def api_error(request, exc):
        return error_response(request, exc)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        # No input values/context from Pydantic: passwords and tokens must never be echoed.
        fields = []
        for error in exc.errors():
            message = 'Invalid or unsupported value.'
            if request.url.path.startswith(('/api/v1/vehicles/', '/api/v1/bookings/', '/api/v1/search/')):
                if error['type'] == 'missing': message = 'This field is required.'
                elif error['type'] == 'value_error': message = str(error.get('ctx', {}).get('error', 'Enter a valid value.'))
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
        if request.url.path.startswith('/api/v1/search/'):   # where, never what: field names and error types only, so a developer can see the cause in the terminal
            logging.getLogger('uvicorn.error').warning('validation failed on %s: %s', request.url.path, [(f['field'], f['code']) for f in fields])
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
                multipart = request.method == 'POST' and (request.url.path == '/api/v1/documents' or (request.url.path.startswith('/api/v1/vehicles/') and name=='photos') or (request.url.path.startswith('/api/v1/trips/') and name=='odometer-photo'))
                social_upload = request.method == 'POST' and request.url.path == '/api/v1/social/posts'
                multipart = multipart or social_upload
                if review_path:
                    group, limit, seconds = ('files', 100, 60) if name == 'file' else ('review', 100, 60) if request.method == 'PATCH' else ('upload', 30, 900) if multipart else ('metadata', 300, 60)
                app.state.store.rate(f'ip:{group}:{ip}', limit, seconds)
                query_route = request.method == 'GET' and request.url.path in ('/api/v1/documents', '/api/v1/admin/role-requests', '/api/v1/locations', '/api/v1/vehicles','/api/v1/admin/vehicles','/api/v1/owners/me/vehicles','/api/v1/routes','/api/v1/scheduled-trips')
                if request.method == 'GET' and request.url.path.startswith(('/api/v1/vehicles/', '/api/v1/admin/vehicles/')) and request.url.path.endswith('/calendar'):
                    query_route = True
                if request.method == 'GET' and request.url.path == '/api/v1/bookings' and set(request.query_params) <= {'as', 'hidden'}:
                    query_route = True
                if request.method == 'GET' and request.url.path == '/api/v1/admin/owner-settlements' and set(request.query_params) <= {'overdue'}:
                    query_route = True
                if request.method == 'GET' and request.url.path == '/api/v1/road-alerts' and set(request.query_params) <= {'trip_id'}:
                    query_route = True
                if request.method == 'GET' and request.url.path == '/api/v1/admin/road-alerts' and set(request.query_params) <= {'status'}:
                    query_route = True
                if (request.method == 'GET' and request.url.path.startswith('/api/v1/scheduled-trips/')
                        and request.url.path.endswith('/replacement-options') and set(request.query_params) <= {'reference'}):
                    query_route = True
                if request.method == 'GET' and request.url.path == '/api/v1/drivers/me/owner-search' and set(request.query_params) <= {'q'}:
                    query_route = True
                if request.method == 'GET' and request.url.path in ('/api/v1/social/feed', '/api/v1/admin/social/posts'):
                    query_route = True   # each endpoint checks its own filters
                if (request.method == 'GET' and request.url.path.startswith('/api/v1/social/posts/')
                        and request.url.path.endswith(('/media', '/thumbnail')) and set(request.query_params) <= {'t'}):
                    query_route = True
                if request.method == 'GET' and request.url.path == '/api/v1/hire/nearby-now' and set(request.query_params) <= {'latitude', 'longitude', 'radius_km'}:
                    query_route = True   # Passenger: vehicles online near a place
                if request.query_params and not query_route:
                    raise ApiError(422, 'VALIDATION_ERROR', 'Query parameters are not supported.')
                if request.method in ('POST', 'PATCH', 'PUT'):
                    # PayHere notifies with a form post, every other JSON API stays JSON-only.
                    media = 'multipart/form-data' if multipart else 'application/x-www-form-urlencoded' \
                        if request.url.path == '/api/v1/payments/webhooks/payhere' else 'application/json'
                    if request.headers.get('content-type', '').split(';')[0].lower() != media:
                        raise ApiError(415, 'UNSUPPORTED_MEDIA_TYPE', 'Use ' + media + '.')
                    chunks, length = [], 0
                    async for chunk in request.stream():
                        length += len(chunk)
                        rate_body = ('/vehicles/' in request.url.path and request.url.path.endswith(('/services', '/services/preview', '/event-packages'))) or request.url.path.startswith(('/api/v1/bookings/', '/api/v1/search/'))
                        profile_body = request.method == 'PATCH' and request.url.path == '/api/v1/users/me'
                        if length > ((app.state.settings.social_reel_max_mb + 11) * 1024 * 1024 if social_upload else MAX_MULTIPART if multipart else 1_410_000 if profile_body else 65536 if rate_body else 8192):
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
                    if raw and media == 'application/json':
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
        session_cookie.apply(request, response, app.state.settings)
        response.headers['Cache-Control'] = 'no-store'
        response.headers['Pragma'] = 'no-cache'
        response.headers['X-Request-ID'] = request.state.trace_id
        response.headers['X-Content-Type-Options'] = 'nosniff'
        return response

    app.include_router(router)
    app.include_router(auth_extension_router)
    app.include_router(review_router)
    app.include_router(rate_router)
    app.include_router(hire_router)
    app.include_router(rental_router)
    app.include_router(vehicle_router)
    app.include_router(stage5_admin_router)
    app.include_router(fulfilment_router)
    app.include_router(road_alerts_router)
    app.include_router(ai_router)
    app.include_router(odometer_router)
    app.include_router(social_router)
    app.include_router(account_settings_router)
    app.include_router(account_security_router)
    app.include_router(airport_router)
    app.include_router(report_router)
    app.include_router(ticket_router)
    app.include_router(route_router)
    app.include_router(scheduled_trip_router)
    app.include_router(payment_router)
    app.include_router(refund_router)
    app.include_router(settlement_router)
    app.include_router(vehicle_records_router)
    app.include_router(favourite_router)
    app.include_router(owner_driver_router)
    app.include_router(driver_payment_router)
    app.include_router(live_vehicle_router)
    app.include_router(ride_now_router)
    app.include_router(saved_place_router)
    app.include_router(support_router)
    app.include_router(owner_expense_router)
    app.include_router(trip_review_router)
    app.include_router(seat_inventory_router)
    app.include_router(charge_report_router)
    app.include_router(trip_km_router)
    app.include_router(admin_summary_router)
    from app.api.routers.calendar_api import router as calendar_router
    app.include_router(calendar_router)
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
                       allow_methods=['GET', 'POST', 'PATCH', 'PUT', 'OPTIONS'], allow_headers=['Authorization', 'Content-Type'],
                       expose_headers=['Retry-After', 'X-Request-ID'])
    return app


app = create_app()
