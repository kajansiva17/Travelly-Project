"""Isolated browser fixture server, never deployment or live application data.

Routing responses are deterministic TEST fixtures; normal HTTP APIs and actual
PostgreSQL/Redis/audit persistence are used. No test/seed endpoint is exposed.
"""
import json
import os
import secrets
import sys
import tempfile
import threading
from pathlib import Path
from datetime import datetime, timezone, timedelta
from uuid import uuid4
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import uvicorn
from alembic import command
from alembic.config import Config
from sqlalchemy import text, func
from app.core.config import get_settings
from app.dependencies.database import make_engine, session_factory
from app.main import create_app
from app.models import User, UserRole
from app.models.review_models import Vehicle, Document
from app.models.rate_models import ServiceType
from app.core.security import hasher
from app.core.sessions import SessionStore
from app.services.review_operator import initialize
from app.services.hire_services import vehicle_evidence

root=Path(__file__).resolve().parents[2]
run=uuid4().hex
data_root=Path(tempfile.mkdtemp(prefix='travelly-pricing-browser-'))
settings=get_settings().model_copy(update={'jwt_secret':secrets.token_urlsafe(48),'jwt_refresh_secret':secrets.token_urlsafe(48),
    'vehicle_photo_root':data_root/'photos','private_document_root':data_root/'documents','review_audit_root':data_root/'audit','review_database_identity':str(uuid4()),
    'review_audit_endpoint':None,'review_audit_auth_file':None,'mail_backend':'capture','mail_capture_dir':data_root/'mail',
    'frontend_url':'http://127.0.0.1:5182','cors_origins':['http://127.0.0.1:5182'],'google_client_id':'','routing_api_key':''})
schema='travelly_test_'+run
control=make_engine(settings.database_url)
engine=make_engine(settings.database_url,connect_args={'options':f'-csearch_path={schema},public'})
store=SessionStore(settings.redis_url,prefix='travelly-test-pricing:'+run+':')
initialize(settings,restrict_acl=False)
try:
    with control.begin() as connection:connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    cfg=Config(str(root/'Backend'/'alembic.ini'))
    with engine.begin() as connection:
        cfg.attributes.update(connection=connection,schema=schema);command.upgrade(cfg,'head')
    with session_factory(engine)() as db:
        owner=User(public_user_reference='USR-'+uuid4().hex[:16].upper(),full_name='Browser Pricing Owner',email='pricing-owner@example.com',
            password_hash=hasher.hash('BrowserTravelly1!'),email_login_required=False,email_verified_at=datetime.now(timezone.utc),account_status='ACTIVE')
        passenger=User(public_user_reference='USR-'+uuid4().hex[:16].upper(),full_name='Browser Pricing Passenger',email='pricing-passenger@example.com',
            password_hash=hasher.hash('BrowserTravelly1!'),email_login_required=False,email_verified_at=datetime.now(timezone.utc),account_status='ACTIVE')
        driver=User(public_user_reference='USR-'+uuid4().hex[:16].upper(),full_name='Browser Assigned Driver',email='pricing-driver@example.com',
            password_hash=hasher.hash('BrowserTravelly1!'),email_login_required=False,email_verified_at=datetime.now(timezone.utc),account_status='ACTIVE')
        admin_user=User(public_user_reference='USR-'+uuid4().hex[:16].upper(),full_name='Browser Vehicle Admin',email='vehicle-admin@example.com',password_hash=hasher.hash('BrowserTravelly1!'),email_login_required=False,email_verified_at=datetime.now(timezone.utc),account_status='ACTIVE')
        db.add_all([owner,passenger,driver,admin_user]);db.flush()
        for person,roles in [(owner,['PASSENGER','OWNER','DRIVER']),(passenger,['PASSENGER','OWNER','DRIVER']),(driver,['PASSENGER','DRIVER']),(admin_user,['PASSENGER','ADMIN'])]:
            for role in roles:db.add(UserRole(user_id=person.id,role_code=role,approval_status='APPROVED',approved_by=owner.id if role!='PASSENGER' else None,approved_at=func.now()))
        service=ServiceType(code='TEST_LONG_DISTANCE',name='Test long-distance private hire',category='PRIVATE_HIRE',is_active=True,default_pricing_basis='DISTANCE',
            settings={'pricing_scope':'LONG_DISTANCE','licence_compatibility':{'TEST_CAR':['TEST_B']},'routing_profiles':{'TEST_CAR':'driving-car'}})
        vehicle=Vehicle(public_vehicle_reference='VEH-'+uuid4().hex[:16].upper(),owner_user_id=owner.id,registration_number='TEST-'+run[:8],
            vehicle_type_code='CAR',manufacture_year=2020,colour='White',power_type='ICE',engine_fuel_type='PETROL',make='Test',model='Browser Vehicle',seat_capacity=4,large_luggage_capacity=2,small_luggage_capacity=2,verification_status='APPROVED',availability_status='ACTIVE',
            approved_by=passenger.id,approved_at=func.now(),verified_eligibility={'owner_declaration':{'registered_owner_case':'SELF'},'category':'TEST_CAR','authorisation_required':False,'conditional_documents':{'EMISSION':False,'FITNESS':False,'ROUTE_PERMIT':False}})
        from PIL import Image
        from types import SimpleNamespace
        from app.services.vehicle_media import VehiclePhotos
        source_image=data_root/'test-vehicle.png'
        Image.new('RGB',(640,400),(170,90,70)).save(source_image,format='PNG')
        with source_image.open('rb') as stream:
            variants=VehiclePhotos(settings).place(SimpleNamespace(filename='test.png',content_type='image/png',file=stream))
        vehicle.media=[{'id':str(uuid4()),'category':'EXTERIOR','status':'APPROVED','privacy_confirmed':True,'genuine_vehicle_confirmed':True,'variants':variants}]
        db.add_all([service,vehicle]);db.flush()
        for kind in ['VEHICLE_REGISTRATION','INSURANCE','REVENUE_LICENCE','DRIVING_LICENCE']:
            db.add(Document(user_id=owner.id if kind=='DRIVING_LICENCE' else None,vehicle_id=vehicle.id if kind!='DRIVING_LICENCE' else None,
                document_type=kind,status='APPROVED',issuing_country='LK',expiry_date=datetime(2100,1,1).date(),submitted_at=func.now(),verified_at=func.now(),verified_by=passenger.id,
                storage_key=uuid4().hex,original_file_name='test-fixture.png',mime_type='image/png',file_size_bytes=1,file_checksum='0'*64,verified_categories=['TEST_B'] if kind=='DRIVING_LICENCE' else []))
        db.add(Document(user_id=driver.id,document_type='DRIVING_LICENCE',status='APPROVED',issuing_country='LK',expiry_date=datetime(2100,1,1).date(),submitted_at=func.now(),verified_at=func.now(),verified_by=passenger.id,storage_key=uuid4().hex,original_file_name='test-driver.png',mime_type='image/png',file_size_bytes=1,file_checksum='0'*64,verified_categories=['TEST_B']))
        db.flush();vehicle.verified_eligibility={**vehicle.verified_eligibility,'publication_fingerprint':vehicle_evidence(db,vehicle)};vehicle.is_published=True;db.commit()
        fixture={'vehicle_id':str(vehicle.id),'service_id':str(service.id),'image_path':str(source_image),'driver_reference':driver.public_user_reference}
    app=create_app(settings,engine,store)
    places={label:app.state.rate_locations.signed(label,lat,lon) for label,lat,lon in [('Test Pickup','6.93','79.86'),('Test Destination','7.29','80.63'),('Test Extra Stop','7.1','80.1')]}
    app.state.rate_locations.search=lambda query:{'items':[p for name,p in places.items() if query.lower() in name.lower()],'attribution':'Deterministic test fixture, not live geocoding'}
    def measure(itinerary,profile):
        for stop in itinerary.stops:app.state.rate_locations.verify(stop.place)
        km=30 if len(itinerary.stops)==2 else 45
        legs=len(itinerary.stops)-1
        segments=[{'distance':km*1000/legs,'steps':[{'distance':km*1000/legs,'duration':1800}]} for _ in range(legs)]
        geometry=[[float(s.place.longitude),float(s.place.latitude)] for s in itinerary.stops]
        result=app.state.hire_routing.from_segments(itinerary,segments,geometry);result['source']='DETERMINISTIC_TEST_FIXTURE'
        return result
    app.state.hire_routing.measure=measure
    # File control belongs only to this isolated test process, never an HTTP API.
    # This permits graceful cleanup on Windows terminals without Ctrl+C forwarding.
    stop_file=data_root/'stop'
    fixture['stop_file']=str(stop_file)
    Path(os.environ.get('TRAVELLY_PRICING_FIXTURE_PATH',root/'.tools'/'pricing-browser-fixture.json')).write_text(json.dumps(fixture),encoding='utf8')
    print('ISOLATED_PRICING_BROWSER_READY',flush=True)
    server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=8002,access_log=False))
    finished=threading.Event()
    def watch_stop():
        while not finished.wait(.2):
            if stop_file.exists():
                server.should_exit=True
                return
    watcher=threading.Thread(target=watch_stop,daemon=True)
    watcher.start()
    try: server.run()
    finally:
        finished.set();watcher.join(timeout=2)
finally:
    keys=list(store.client.scan_iter(store.prefix+'*'))
    if keys:store.client.delete(*keys)
    store.client.close();engine.dispose()
    with control.begin() as connection:connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
    control.dispose()
