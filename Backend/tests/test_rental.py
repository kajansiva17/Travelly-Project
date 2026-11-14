"""Self-drive rental: day rate + pooled free km, Owner photographs the odometer at handover and return, bill from the readings."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID, uuid4
from sqlalchemy import select
from app.models.hire_models import Booking, Trip
from app.models.rate_models import ServiceType, VehicleService
from conftest import bearer
from test_rates import rate_owner  # noqa: F401
from test_hire_pricing import hire_setup  # noqa: F401

TERMS = {'expected_version': 0, 'enabled': True, 'day_rate': '8000', 'free_km_per_day': '100', 'extra_km_rate': '40',
         'late_hour_rate': '500', 'max_days': 7, 'extras': [{'id': '11111111-1111-4111-8111-111111111111', 'name': 'Child seat', 'price': '300', 'per': 'DAY'}, {'id': '22222222-2222-4222-8222-222222222222', 'name': 'GPS', 'price': '1000', 'per': 'ONCE'}], 'notes': 'Rs 20000 deposit in cash. Return with the same fuel.', 'cash_accepted': True}


def setup_rental(client, c):
    saved = client.put(f'/api/v1/vehicles/{c.vehicle_id}/rental', headers=bearer(c.owner), json=TERMS)
    assert saved.status_code == 200, saved.text
    return saved.json()


def start(hours=30):
    return datetime.now(timezone.utc) + timedelta(hours=hours)


def ask(client, c, begin=None, days=2, key=None):
    return client.post('/api/v1/rentals', headers=bearer(c.passenger), json={'vehicle_id': str(c.vehicle_id), 'start_at': (begin or start()).isoformat(),
                                                                                'days': days, 'licence_number': 'B1234567', 'idempotency_key': key or uuid4().hex})


def bring_forward(client, booking_id):
    """Move the rental to start in one hour, so handover is allowed now."""
    with client.app.state.sessions() as db:
        row = db.get(Booking, UUID(booking_id)); days = row.end_at - row.start_at
        row.start_at = datetime.now(timezone.utc) + timedelta(hours=1); row.end_at = row.start_at + days
        for trip in db.scalars(select(Trip).where(Trip.booking_id == row.id)):
            trip.scheduled_start_at, trip.scheduled_end_at = row.start_at, row.end_at
        db.commit()


def post(client, who, path, body):
    return client.post('/api/v1' + path, headers=bearer(who), json=body)


def accepted(client, c, **kw):
    row = ask(client, c, **kw).json()
    row = post(client, c.owner, f"/rentals/{row['id']}/accept", {'expected_version': row['version']}).json()
    assert row['status'] == 'CONFIRMED' and row['vehicle_committed'], row
    return row


def test_search_shows_the_owner_rates_and_the_base_price(client, hire_setup):
    c = hire_setup; setup_rental(client, c)
    found = client.post('/api/v1/rentals/search', json={'start_at': start().isoformat(), 'days': 3})
    assert found.status_code == 200, found.text
    item = found.json()['items'][0]['rental']
    assert (item['base_price'], item['free_km_total'], item['extra_km_rate']) == ('24000.00', '300', '40') and 'deposit' in item['notes']
    too_long = client.post('/api/v1/rentals/search', json={'start_at': start().isoformat(), 'days': 9})
    assert too_long.json()['items'] == []
    shown = {e['name']: e['amount'] for e in found.json()['items'][0]['rental']['extras']}
    assert shown == {'Child seat': '900.00', 'GPS': '1000.00'}   # 300 x 3 days, once


def test_full_rental_bill_comes_from_the_two_odometer_readings(client, hire_setup):
    c = hire_setup; setup_rental(client, c)
    row = accepted(client, c)
    early = post(client, c.owner, f"/rentals/{row['id']}/handover", {'expected_version': row['version'], 'start_odometer_km': '5000', 'licence_checked': True})
    assert early.status_code == 409 and early.json()['code'] == 'RENTAL_NOT_READY'
    bring_forward(client, row['id'])
    row = client.get(f"/api/v1/bookings/{row['id']}", headers=bearer(c.owner)).json()
    unchecked = post(client, c.owner, f"/rentals/{row['id']}/handover", {'expected_version': row['version'], 'start_odometer_km': '5000', 'licence_checked': False})
    assert unchecked.status_code == 422
    out = post(client, c.owner, f"/rentals/{row['id']}/handover", {'expected_version': row['version'], 'start_odometer_km': '5000', 'licence_checked': True, 'note': 'Full tank'})
    assert out.status_code == 200, out.text
    row = out.json(); assert row['status'] == 'IN_PROGRESS'
    confirmed = post(client, c.passenger, f"/rentals/{row['id']}/confirm", {'stage': 'HANDOVER'})
    assert confirmed.status_code == 200 and confirmed.json()['itinerary']['rental']['handover']['passenger_confirmed_at']
    row = confirmed.json()
    back = post(client, c.owner, f"/rentals/{row['id']}/return", {'expected_version': row['version'], 'end_odometer_km': '5350.5'})
    assert back.status_code == 200, back.text
    done = back.json(); final = done['price']['final']
    # 2 days x 8000 + (350.5 km - 200 free km) x 40 = 16000 + 6020 ; returned on time
    assert done['status'] == 'COMPLETED' and done['total_amount'] == '22020.00' and final['total'] == '22020.00'
    assert final['distance_km'] == '350.5' and final['late_hours'] == '0'
    c2 = post(client, c.passenger, f"/rentals/{row['id']}/confirm", {'stage': 'RETURN'})
    assert c2.status_code == 200
    with client.app.state.sessions() as db:
        trip = db.scalar(select(Trip).where(Trip.booking_id == UUID(row['id'])))
        assert trip.status == 'COMPLETED' and trip.start_odometer_km == Decimal('5000.0') and trip.end_odometer_km == Decimal('5350.5')


def test_late_return_is_charged_per_hour_after_the_grace_hour(client, hire_setup):
    c = hire_setup; setup_rental(client, c)
    row = accepted(client, c, days=1); bring_forward(client, row['id'])
    row = client.get(f"/api/v1/bookings/{row['id']}", headers=bearer(c.owner)).json()
    row = post(client, c.owner, f"/rentals/{row['id']}/handover", {'expected_version': row['version'], 'start_odometer_km': '100', 'licence_checked': True}).json()
    with client.app.state.sessions() as db:   # the vehicle was handed over 26.5 hours ago: 24 + 1 grace + 1.5 late hours, charged as 2
        trip = db.scalar(select(Trip).where(Trip.booking_id == UUID(row['id']))); trip.actual_start_at = datetime.now(timezone.utc) - timedelta(hours=26, minutes=30)
        db.commit()
    back = post(client, c.owner, f"/rentals/{row['id']}/return", {'expected_version': row['version'], 'end_odometer_km': '180'}).json()
    assert back['price']['final']['late_hours'] == '2' and back['total_amount'] == '9000.00'   # 8000 + 2 x 500, 80 km is within 100 free


def test_rental_is_paid_after_the_return_online_or_in_cash(client, hire_setup):
    c = hire_setup; setup_rental(client, c)
    row = accepted(client, c, days=1); bring_forward(client, row['id'])
    row = client.get(f"/api/v1/bookings/{row['id']}", headers=bearer(c.owner)).json()
    early = client.get(f"/api/v1/bookings/{row['id']}/payment-summary", headers=bearer(c.passenger)).json()
    assert early['payment_due'] is False
    row = post(client, c.owner, f"/rentals/{row['id']}/handover", {'expected_version': row['version'], 'start_odometer_km': '10', 'licence_checked': True}).json()
    row = post(client, c.owner, f"/rentals/{row['id']}/return", {'expected_version': row['version'], 'end_odometer_km': '60'}).json()
    s = client.get(f"/api/v1/bookings/{row['id']}/payment-summary", headers=bearer(c.passenger)).json()
    assert s['payment_due'] and s['amount_due'] == '8000.00' and s['cash_accepted'] is True
    intent = post(client, c.passenger, f"/bookings/{row['id']}/payment-intents", {'amount': '8000.00', 'currency': 'LKR', 'method': 'SANDBOX', 'idempotency_key': uuid4().hex})
    assert intent.status_code == 201, intent.text
    paid = post(client, c.passenger, f"/payments/{intent.json()['id']}/sandbox-outcome", {'outcome': 'SUCCEEDED'})
    assert paid.status_code == 200 and paid.json()['status'] == 'PAID'


def test_cancel_decline_and_rules(client, hire_setup):
    c = hire_setup; setup_rental(client, c)
    first = ask(client, c).json()
    fixed = start(200)
    again = ask(client, c, begin=fixed, key='k' * 20); replay = ask(client, c, begin=fixed, key='k' * 20)
    assert again.status_code == 201 and replay.json()['id'] == again.json()['id']   # the same key gives the same booking
    assert ask(client, c, begin=fixed, days=3, key='k' * 20).status_code == 409                  # ...but not a different request
    declined = post(client, c.owner, f"/rentals/{first['id']}/decline", {'expected_version': first['version'], 'reason': 'Not available'})
    assert declined.status_code == 200 and declined.json()['status'] == 'REJECTED'
    second = accepted(client, c, begin=start(100))
    clash = ask(client, c, begin=start(100))
    assert clash.status_code == 409 and clash.json()['code'] == 'VEHICLE_SCHEDULE_CONFLICT'
    stranger = post(client, c.passenger, f"/rentals/{second['id']}/handover", {'expected_version': second['version'], 'start_odometer_km': '1', 'licence_checked': True})
    assert stranger.status_code == 404
    cancelled = post(client, c.passenger, f"/rentals/{second['id']}/cancel", {'expected_version': second['version'], 'reason': 'Plans changed'})
    assert cancelled.status_code == 200 and cancelled.json()['status'] == 'CANCELLED' and not cancelled.json()['vehicle_committed']
    assert ask(client, c, begin=start(100)).status_code == 201   # the dates are free again
    off = client.put(f'/api/v1/vehicles/{c.vehicle_id}/rental', headers=bearer(c.owner), json={**TERMS, 'expected_version': 1, 'enabled': False})
    assert off.status_code == 200
    assert ask(client, c, begin=start(300)).status_code == 409


def test_owner_opens_the_odometer_camera_on_a_rental_trip(client, hire_setup):
    c = hire_setup; setup_rental(client, c)
    row = accepted(client, c)
    with client.app.state.sessions() as db:
        trip = db.scalar(select(Trip).where(Trip.booking_id == UUID(row['id'])))
        trip_id = str(trip.id)
    opened = post(client, c.owner, f'/trips/{trip_id}/odometer-session', {'stage': 'START'})
    assert opened.status_code == 200 and opened.json()['capture_code']
    assert post(client, c.passenger, f'/trips/{trip_id}/odometer-session', {'stage': 'START'}).status_code == 404   # the renter does not take it


def test_chosen_extras_are_added_to_the_estimate_and_the_bill(client, hire_setup):
    c = hire_setup; setup_rental(client, c)
    body = {'vehicle_id': str(c.vehicle_id), 'start_at': start().isoformat(), 'days': 2, 'licence_number': 'B1234567', 'idempotency_key': uuid4().hex,
            'extras': ['11111111-1111-4111-8111-111111111111', '22222222-2222-4222-8222-222222222222']}
    row = client.post('/api/v1/rentals', headers=bearer(c.passenger), json=body)
    assert row.status_code == 201, row.text
    row = row.json()
    assert row['price']['estimate']['extras_price'] == '1600.00' and row['price']['estimate']['base_price'] == '17600.00'   # 16000 + 2x300 + 1000
    bad = client.post('/api/v1/rentals', headers=bearer(c.passenger), json={**body, 'idempotency_key': uuid4().hex, 'extras': [str(uuid4())]})
    assert bad.status_code == 422 and bad.json()['code'] == 'EXTRA_UNAVAILABLE'
    row = post(client, c.owner, f"/rentals/{row['id']}/accept", {'expected_version': row['version']}).json()
    bring_forward(client, row['id'])
    row = client.get(f"/api/v1/bookings/{row['id']}", headers=bearer(c.owner)).json()
    row = post(client, c.owner, f"/rentals/{row['id']}/handover", {'expected_version': row['version'], 'start_odometer_km': '100', 'licence_checked': True}).json()
    done = post(client, c.owner, f"/rentals/{row['id']}/return", {'expected_version': row['version'], 'end_odometer_km': '150'}).json()
    assert done['total_amount'] == '17600.00' and [l['code'] for l in done['price']['final']['breakdown']][-2:] == ['EXTRA_1', 'EXTRA_2']


def test_a_rental_does_not_block_the_owner_as_a_driver_and_shows_as_a_rental_trip(client, hire_setup):
    from app.services.hire_services import no_conflict
    c = hire_setup; setup_rental(client, c)
    row = accepted(client, c)
    with client.app.state.sessions() as db:
        owner_id = db.get(Booking, UUID(row['id'])).owner_user_id
        no_conflict(db, uuid4(), start(30), start(60), driver_id=owner_id)   # no DRIVER_SCHEDULE_CONFLICT
    bring_forward(client, row['id'])
    row = client.get(f"/api/v1/bookings/{row['id']}", headers=bearer(c.owner)).json()
    post(client, c.owner, f"/rentals/{row['id']}/handover", {'expected_version': row['version'], 'start_odometer_km': '100', 'licence_checked': True})
    for who in (c.owner, c.passenger):
        items = client.get('/api/v1/trips/active', headers=bearer(who)).json()['items']
        assert [i['kind'] for i in items] == ['RENTAL']


def test_rental_reminders_go_out_once_each(client, hire_setup):
    from app.services.reminders import run_reminders
    from app.models.hire_models import Notification
    c = hire_setup; setup_rental(client, c)
    req = ask(client, c, begin=start(40)).json()      # a request nobody answered
    row = accepted(client, c, begin=start(100))       # a confirmed rental
    booking_id = UUID(row['id'])
    def run(moment):
        with client.app.state.sessions() as db:
            out = run_reminders(db, client.app.state.settings, None, moment); db.commit(); return out['rental']
    now = datetime.now(timezone.utc)
    assert run(now) == 0
    assert run(now + timedelta(days=1, hours=1)) == 1     # the unanswered request, to the Owner
    assert run(now + timedelta(days=1, hours=2)) == 0     # never twice
    soon = run(now + timedelta(hours=100 - 5))            # the confirmed one starts within 24 hours: renter + Owner
    assert soon >= 2
    with client.app.state.sessions() as db:
        stages = {n.action_payload['stage'] for n in db.scalars(select(Notification).where(Notification.action_payload['booking_id'].astext == str(booking_id)))
                  if 'stage' in n.action_payload}
        assert 'STARTS_SOON' in stages
    assert run(now + timedelta(hours=100 + 2)) >= 2       # start passed and no handover
