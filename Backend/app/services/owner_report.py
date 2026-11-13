"""Monthly Owner report (owner decision 13 Nov 2026; not in the PRD, read-only, nothing stored).

One calendar month (Sri Lanka time) for one Owner, built from the existing tables:
1. Trips and km   - trips the Owner operated that finished in the month: route, vehicle, driver, odometer start/end, km
                    (`trips`, the readings recorded with the odometer photo proof).
2. Earnings       - the Owner's share rows captured in the month (gross, commission, Owner net, refunded), payouts
                    Travelly paid in the month, and today's open balance (payable / commission due).
3. Maintenance    - service, repair, fuel and charging records of the Owner's vehicles in the month, the spend, and
                    the next due items as of today (`vehicle_records` + the PRD 4.16 summary).
4. Documents      - the Owner's and the vehicles' current documents with expiry state as of today.
English only. Downloaded on demand as a PDF; the same data is also served as JSON for an on-screen preview.
"""
import io
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo
from sqlalchemy import func, or_, select
from app.models import User
from app.models.hire_models import Booking, Route, ScheduledTrip, Trip, VehicleRecord
from app.models.payment_models import Payment
from app.models.review_models import Document, Vehicle

COLOMBO = ZoneInfo('Asia/Colombo')
ZERO = Decimal('0')
SPEND = ('OIL_CHANGE', 'OIL_FILTER_CHANGE', 'TYRE_CHANGE', 'TYRE_ROTATION', 'WHEEL_ALIGNMENT', 'WHEEL_BALANCING', 'GENERAL_SERVICE',
         'BRAKE_SERVICE', 'BATTERY_SERVICE', 'REPAIR', 'FUEL_PURCHASE', 'EV_CHARGING')
SOON_DAYS = 30


def month_bounds(year, month):
    start = datetime.combine(date(year, month, 1), time(0), COLOMBO)
    nxt = date(year + (month == 12), month % 12 + 1, 1)
    return start.astimezone(timezone.utc), datetime.combine(nxt, time(0), COLOMBO).astimezone(timezone.utc)


def money(value):
    return format((value or ZERO).quantize(Decimal('0.01')), '.2f')


def km(value):
    return None if value is None else format(Decimal(value).quantize(Decimal('0.1')), '.1f')


def label(code):
    if code in ('NIC',):
        return code
    return (code or '').replace('_', ' ').title()


def local(moment):
    return moment.astimezone(COLOMBO) if moment else None


def masked(number):
    if not number:
        return None
    return '••••' + number[-4:] if len(number) > 4 else number


def vehicle_name(v):
    extra = ' '.join(filter(None, [v.make, v.model]))
    return f'{v.registration_number}' + (f' ({extra})' if extra else '')


def build(db, owner, year, month, moment=None):
    moment = moment or datetime.now(timezone.utc)
    today = moment.astimezone(COLOMBO).date()
    start, end = month_bounds(year, month)
    vehicles = db.scalars(select(Vehicle).where(Vehicle.owner_user_id == owner.id).order_by(Vehicle.registration_number)).all()
    by_vehicle = {v.id: v for v in vehicles}

    # 1. Trips and km ------------------------------------------------------------------------------
    trips = db.scalars(select(Trip).where(Trip.operating_owner_user_id == owner.id, Trip.status == 'COMPLETED',
                                          Trip.actual_end_at >= start, Trip.actual_end_at < end)
                       .order_by(Trip.actual_end_at)).all()
    drivers = {u.id: u for u in db.scalars(select(User).where(User.id.in_({t.driver_user_id for t in trips if t.driver_user_id})))} if trips else {}
    trip_rows, per_vehicle = [], {}
    for t in trips:
        vehicle = by_vehicle.get(t.vehicle_id) or db.get(Vehicle, t.vehicle_id)
        if t.scheduled_trip_id:
            departure = db.get(ScheduledTrip, t.scheduled_trip_id)
            route = db.get(Route, departure.route_id) if departure else None
            reference = departure.departure_reference if departure else None
            where = f'{route.origin_name} → {route.destination_name}' if route else None
            kind = 'Ticket departure'
        else:
            booking = db.get(Booking, t.booking_id) if t.booking_id else None
            reference = booking.booking_reference if booking else None
            where = f'{booking.origin_text} → {booking.destination_text}' if booking and booking.origin_text else None
            kind = 'Private hire'
        distance = t.calculated_distance_km if t.calculated_distance_km is not None else (
            t.end_odometer_km - t.start_odometer_km if t.end_odometer_km is not None and t.start_odometer_km is not None else None)
        driver = drivers.get(t.driver_user_id)
        trip_rows.append({'date': local(t.actual_end_at).date().isoformat(), 'reference': reference, 'kind': kind, 'route': where,
                          'vehicle': vehicle.registration_number if vehicle else None,
                          'driver': (driver.display_name or driver.full_name) if driver else None,
                          'start_km': km(t.start_odometer_km), 'end_km': km(t.end_odometer_km), 'distance_km': km(distance)})
        bucket = per_vehicle.setdefault(t.vehicle_id, {'vehicle': vehicle_name(vehicle) if vehicle else '-', 'trips': 0, 'km': ZERO})
        bucket['trips'] += 1
        bucket['km'] += distance or ZERO
    total_km = sum((b['km'] for b in per_vehicle.values()), ZERO)

    # 2. Earnings -------------------------------------------------------------------------------------
    from app.api.routers.settlement_api import OWNER_SHARE, payable_share, refunded, settlement_for
    shares = db.scalars(select(Payment).where(
        Payment.payee_owner_user_id == owner.id, Payment.transaction_type.in_(OWNER_SHARE),
        func.coalesce(Payment.captured_at, Payment.created_at) >= start, func.coalesce(Payment.captured_at, Payment.created_at) < end)
        .order_by(func.coalesce(Payment.captured_at, Payment.created_at))).all()
    books = {b.id: b for b in db.scalars(select(Booking).where(Booking.id.in_({p.booking_id for p in shares})))} if shares else {}
    earning_rows = []
    totals = {'gross': ZERO, 'commission': ZERO, 'owner_net': ZERO, 'refunded': ZERO}
    for p in shares:
        if p.status not in ('PAID', 'PARTIALLY_REFUNDED', 'REFUNDED'):
            continue
        back = refunded(db, p)
        net = payable_share(db, p) if p.status != 'REFUNDED' else ZERO
        gross = p.amount if p.transaction_type == 'PAYMENT' else ZERO   # a reallocated share was collected once, on the original
        booking = books.get(p.booking_id)
        earning_rows.append({'date': local(p.captured_at or p.created_at).date().isoformat(),
                             'booking': booking.booking_reference if booking else None,
                             'method': label(p.payment_method), 'type': 'Replacement trip' if p.transaction_type == 'REALLOCATION' else 'Payment',
                             'amount': money(gross), 'commission': money(p.commission_amount), 'refunded': money(back),
                             'owner_net': money(net), 'status': label(p.owner_settlement_status or p.status)})
        totals['gross'] += gross
        totals['commission'] += (p.commission_amount or ZERO) if p.status != 'REFUNDED' else ZERO
        totals['owner_net'] += net
        totals['refunded'] += back
    payouts = db.scalars(select(Payment).where(Payment.payee_owner_user_id == owner.id, Payment.transaction_type == 'OWNER_PAYOUT',
                                               Payment.status == 'PAID', func.coalesce(Payment.captured_at, Payment.created_at) >= start,
                                               func.coalesce(Payment.captured_at, Payment.created_at) < end)
                         .order_by(Payment.created_at)).all()
    payout_rows = [{'date': local(p.captured_at or p.created_at).date().isoformat(), 'reference': p.provider_reference or p.payment_reference,
                    'method': label(p.payment_method), 'amount': money(p.amount)} for p in payouts]
    balance = settlement_for(db, owner.id)

    # 3. Maintenance -----------------------------------------------------------------------------------
    from app.api.routers.vehicle_records_api import summarise
    records = db.scalars(select(VehicleRecord).where(VehicleRecord.vehicle_id.in_(list(by_vehicle)), VehicleRecord.record_type.in_(SPEND),
                                                     VehicleRecord.recorded_at >= start, VehicleRecord.recorded_at < end)
                         .order_by(VehicleRecord.recorded_at)).all() if by_vehicle else []
    record_rows, spend = [], {'service_and_repair': ZERO, 'fuel_and_charging': ZERO}
    for r in records:
        record_rows.append({'date': local(r.recorded_at).date().isoformat(), 'vehicle': by_vehicle[r.vehicle_id].registration_number,
                            'type': label(r.record_type), 'odometer_km': km(r.odometer_km), 'amount': None if r.amount is None else money(r.amount),
                            'provider': r.service_provider, 'notes': (r.notes or '')[:120] or None})
        bucket = 'fuel_and_charging' if r.record_type in ('FUEL_PURCHASE', 'EV_CHARGING') else 'service_and_repair'
        spend[bucket] += r.amount or ZERO
    coming = []
    for v in vehicles:
        summary = summarise(db, v, moment)
        for item in summary['items']:
            if item['status'] in ('OVERDUE', 'DUE', 'UPCOMING'):
                coming.append({'vehicle': v.registration_number, 'task': label(item['task']), 'status': label(item['status']),
                               'due': item['estimated_due_date'] or item['genuine_calendar_due_date'],
                               'remaining_km': item['remaining_km']})
    coming.sort(key=lambda i: ({'Overdue': 0, 'Due': 1, 'Upcoming': 2}[i['status']], i['due'] or '9999'))

    # 4. Documents -------------------------------------------------------------------------------------
    docs = db.scalars(select(Document).where(
        or_(Document.user_id == owner.id, Document.vehicle_id.in_(list(by_vehicle)) if by_vehicle else False),
        Document.status.not_in(('SUPERSEDED', 'DRAFT'))).order_by(Document.expiry_date.nulls_last())).all()
    document_rows, attention = [], 0
    for d in docs:
        if d.expiry_date is None:
            state = 'No expiry'
        elif d.expiry_date < today or d.status == 'EXPIRED':
            state = 'Expired'
        elif d.expiry_date <= today + timedelta(days=SOON_DAYS):
            state = f'Expires in {(d.expiry_date - today).days} days'
        else:
            state = 'Valid'
        if d.status in ('REJECTED', 'NEEDS_CORRECTION'):
            state = label(d.status)
        if state not in ('Valid', 'No expiry'):
            attention += 1
        document_rows.append({'document': label(d.document_type), 'for': by_vehicle[d.vehicle_id].registration_number if d.vehicle_id in by_vehicle else 'You',
                              'number': masked(d.document_number), 'expiry_date': d.expiry_date.isoformat() if d.expiry_date else None,
                              'status': label(d.status), 'state': state})

    # 5. Month result: what the Owner earned minus the costs recorded in Travelly (owner request 13 Nov 2026).
    expenses = spend['service_and_repair'] + spend['fuel_and_charging']
    profit = totals['owner_net'] - expenses
    result = {'income': money(totals['owner_net']), 'expenses_service_and_repair': money(spend['service_and_repair']),
              'expenses_fuel_and_charging': money(spend['fuel_and_charging']), 'expenses_total': money(expenses),
              'profit': money(profit), 'is_loss': profit < 0,
              'note': 'Income is your share of trips paid this month after Travelly commission and refunds. Expenses are the '
                      'maintenance, fuel and charging records entered in Travelly for this month; other costs (driver pay, loans, '
                      'insurance premiums) are not included.'}

    return {
        'owner': {'name': owner.display_name or owner.full_name, 'reference': owner.public_user_reference},
        'period': f'{year:04d}-{month:02d}', 'period_label': date(year, month, 1).strftime('%B %Y'),
        'generated_at': local(moment).isoformat(timespec='minutes'), 'currency': 'LKR',
        'summary': {'vehicles': len(vehicles), 'completed_trips': len(trip_rows), 'total_km': km(total_km),
                    'gross_collected': money(totals['gross']), 'commission': money(totals['commission']),
                    'refunded': money(totals['refunded']), 'owner_net': money(totals['owner_net']),
                    'payouts_received': money(sum((p.amount for p in payouts), ZERO)),
                    'maintenance_spend': money(spend['service_and_repair']), 'fuel_and_charging_spend': money(spend['fuel_and_charging']),
                    'documents_needing_attention': attention, 'expenses_total': money(expenses), 'profit': money(profit)},
        'trips': {'per_vehicle': [{'vehicle': b['vehicle'], 'trips': b['trips'], 'km': km(b['km'])} for b in per_vehicle.values()],
                  'items': trip_rows},
        'earnings': {'items': earning_rows, 'payouts': payout_rows,
                     'open_balance_today': {'payable_to_you': balance['payable_amount'], 'commission_due_from_you': balance['commission_due_amount'],
                                            'waiting_for_refunds': len(balance['needs_review'])}},
        'maintenance': {'items': record_rows, 'coming_up_today': coming[:15]},
        'documents': {'items': document_rows},
        'result': result,
    }


# --------------------------------------------------------------------------------------------------- PDF

def render_pdf(data):
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_RIGHT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    # Travelly brand (website logo): navy #002155 and red; logo from Frontend/public branding, copied to app/assets.
    navy, brand = colors.HexColor('#002155'), colors.HexColor('#E8141B')
    ink, muted, line = colors.HexColor('#1F2937'), colors.HexColor('#6B7280'), colors.HexColor('#E3E8F0')
    soft, wash = colors.HexColor('#FDECEC'), colors.HexColor('#F3F6FB')
    from pathlib import Path
    logo = Path(__file__).resolve().parents[1] / 'assets' / 'travelly-logo.png'
    base = getSampleStyleSheet()
    h1 = ParagraphStyle('h1', parent=base['Title'], fontName='Helvetica-Bold', fontSize=18, textColor=navy, alignment=TA_RIGHT, spaceAfter=0, leading=21)
    h2 = ParagraphStyle('h2', parent=base['Heading2'], fontName='Helvetica-Bold', fontSize=12.5, textColor=navy, spaceBefore=0, spaceAfter=0, leading=15)
    body = ParagraphStyle('body', parent=base['Normal'], fontName='Helvetica', fontSize=8.5, leading=11, textColor=ink)
    small = ParagraphStyle('small', parent=body, fontSize=7.5, leading=9.5, textColor=muted)
    cell = ParagraphStyle('cell', parent=body, fontSize=7.5, leading=9.5)
    right = ParagraphStyle('right', parent=cell, alignment=TA_RIGHT)

    def cash(value):
        try:
            return f'{Decimal(str(value)):,.2f}'
        except Exception:   # noqa: BLE001 - not a number: show as given
            return value

    def dist(value):
        try:
            return f'{Decimal(str(value)):,.1f}'
        except Exception:   # noqa: BLE001
            return value

    def esc(value):
        return '' if value is None else str(value).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

    def grid(headers, rows, widths, numeric=(), empty='Nothing in this month.'):
        if not rows:
            return Paragraph(empty, small)
        head = [Paragraph(f'<font color="white"><b>{esc(h)}</b></font>', right if i in numeric else cell) for i, h in enumerate(headers)]
        body_rows = [[Paragraph(esc(v) if v not in (None, '') else '-', right if i in numeric else cell) for i, v in enumerate(r)] for r in rows]
        table = Table([head] + body_rows, colWidths=[w * mm for w in widths], repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), navy), ('LINEBELOW', (0, 0), (-1, 0), 1.2, brand),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, wash]),
            ('LINEBELOW', (0, 1), (-1, -1), 0.3, line), ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 3), ('RIGHTPADDING', (0, 0), (-1, -1), 3)]))
        return table

    s, cur = data['summary'], data['currency']
    out = io.BytesIO()
    doc = SimpleDocTemplate(out, pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm, topMargin=20 * mm, bottomMargin=18 * mm,
                            title=f"Travelly monthly report {data['period']}", author='Travelly')

    def section(title):
        bar = Table([['', Paragraph(esc(title), h2)]], colWidths=[1.6 * mm, 180 * mm])
        bar.setStyle(TableStyle([('BACKGROUND', (0, 0), (0, 0), brand), ('LEFTPADDING', (0, 0), (0, 0), 0), ('RIGHTPADDING', (0, 0), (0, 0), 0),
                                 ('LEFTPADDING', (1, 0), (1, 0), 6), ('TOPPADDING', (0, 0), (-1, -1), 2), ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                                 ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))
        return [Spacer(1, 10), bar, Spacer(1, 5)]

    def footer(canvas, document):
        canvas.saveState()
        width, height = A4
        # top: navy and red rule like the website header; small logo on later pages
        canvas.setFillColor(navy); canvas.rect(0, height - 5 * mm, width, 5 * mm, stroke=0, fill=1)
        canvas.setFillColor(brand); canvas.rect(0, height - 6.2 * mm, width, 1.2 * mm, stroke=0, fill=1)
        if document.page > 1 and logo.exists():
            canvas.drawImage(str(logo), 14 * mm, height - 17 * mm, width=30 * mm, height=9.7 * mm, mask='auto')
            canvas.setFont('Helvetica', 7.5); canvas.setFillColor(muted)
            canvas.drawRightString(width - 14 * mm, height - 13 * mm, f"Monthly Owner report \u2022 {data['period_label']}")
        # bottom: navy band with the tagline and page number
        canvas.setFillColor(navy); canvas.rect(0, 0, width, 11 * mm, stroke=0, fill=1)
        canvas.setFont('Helvetica', 7); canvas.setFillColor(colors.white)
        canvas.drawString(14 * mm, 4.3 * mm, f"Travelly \u2022 Vehicles \u2022 Tickets \u2022 Rentals   |   {data['owner']['name']} \u2022 {data['period_label']}")
        canvas.setFillColor(colors.HexColor('#FF6B6B')); canvas.setFont('Helvetica-Bold', 7.5)
        canvas.drawRightString(width - 14 * mm, 4.3 * mm, f'Page {document.page}')
        canvas.restoreState()

    from reportlab.platypus import Image as Picture
    title = [Paragraph('Monthly Owner Report', h1),
             Paragraph(f"<font size=11 color='#E8141B'><b>{esc(data['period_label'])}</b></font>", ParagraphStyle('p', parent=body, alignment=TA_RIGHT, leading=14)),
             Paragraph(f"{esc(data['owner']['name'])} \u2022 {esc(data['owner']['reference'])}", ParagraphStyle('o', parent=small, alignment=TA_RIGHT)),
             Paragraph(f"Generated {esc(data['generated_at'].replace('T', ' '))} (Sri Lanka time)", ParagraphStyle('g', parent=small, alignment=TA_RIGHT))]
    mark = Picture(str(logo), width=62 * mm, height=20 * mm) if logo.exists() else Paragraph('<b>Travelly</b>', h1)
    masthead = Table([[mark, title]], colWidths=[72 * mm, 110 * mm])
    masthead.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0)]))
    story = [Spacer(1, 2), masthead, Spacer(1, 8)]
    tiles = [('Completed trips', s['completed_trips']), ('Total km', dist(s['total_km'])), (f'Gross collected ({cur})', cash(s['gross_collected'])),
             (f'Your income ({cur})', cash(s['owner_net'])), (f'Your expenses ({cur})', cash(s['expenses_total'])),
             (('Month loss' if data['result']['is_loss'] else 'Month profit') + f' ({cur})', cash(s['profit'])),
             (f'Payouts received ({cur})', cash(s['payouts_received'])), ('Documents to check', s['documents_needing_attention'])]
    loss = data['result']['is_loss']
    tile = ParagraphStyle('tile', parent=body, leading=17)   # room for the 14 pt value under the label
    tile_rows = [[Paragraph(f'<font size=7 color="#6B7280">{esc(k).upper()}</font><br/><font size=14 color="#002155"><b>{esc(v)}</b></font>', tile)
                  for k, v in tiles[i:i + 4]] for i in (0, 4)]
    summary = Table(tile_rows, colWidths=[45.5 * mm] * 4)
    profit_cell = (1, 1)   # the profit tile: second row, second column
    summary.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), wash), ('LINEABOVE', (0, 0), (-1, 0), 2.2, navy),
                                 ('LINEABOVE', (0, 1), (-1, 1), 2.2, navy), ('LINEAFTER', (0, 0), (-2, -1), 3, colors.white),
                                 ('LINEABOVE', profit_cell, profit_cell, 2.2, brand if loss else colors.HexColor('#15803D')),
                                 ('BACKGROUND', profit_cell, profit_cell, soft if loss else colors.HexColor('#ECFDF3')),
                                 ('TOPPADDING', (0, 0), (-1, -1), 7), ('BOTTOMPADDING', (0, 0), (-1, -1), 7), ('LEFTPADDING', (0, 0), (-1, -1), 8)]))
    story += [summary]

    t = data['trips']
    story += [*section('1. Trips and kilometres'),
              grid(['Vehicle', 'Trips', 'Km'], [[r['vehicle'], r['trips'], dist(r['km'])] for r in t['per_vehicle']], [120, 30, 32], numeric=(1, 2)),
              Spacer(1, 5),
              grid(['Date', 'Reference', 'Type', 'Route', 'Vehicle', 'Driver', 'Start km', 'End km', 'Km'],
                   [[r['date'], r['reference'], r['kind'], r['route'], r['vehicle'], r['driver'], dist(r['start_km']) if r['start_km'] else None, dist(r['end_km']) if r['end_km'] else None, dist(r['distance_km']) if r['distance_km'] else None] for r in t['items']],
                   [17, 22, 18, 34, 23, 24, 16, 16, 12], numeric=(6, 7, 8)),
              Paragraph('Odometer readings are the ones entered with the photo proof at trip start and finish.', small)]

    e = data['earnings']
    story += [*section('2. Earnings'),
              grid(['Date', 'Booking', 'Type', 'Method', f'Amount', 'Commission', 'Refunded', 'Your net', 'Status'],
                   [[r['date'], r['booking'], r['type'], r['method'], cash(r['amount']), cash(r['commission']), cash(r['refunded']), cash(r['owner_net']), r['status']] for r in e['items']],
                   [17, 24, 20, 14, 19, 19, 17, 19, 33], numeric=(4, 5, 6, 7)),
              Spacer(1, 4),
              Paragraph(f"Totals: gross {cur} {esc(cash(s['gross_collected']))} • commission {esc(cash(s['commission']))} • refunded {esc(cash(s['refunded']))} "
                        f"• <b>your net {esc(cash(s['owner_net']))}</b>", body),
              Spacer(1, 4), Paragraph('<b>Payouts Travelly paid you this month</b>', body),
              grid(['Date', 'Reference', 'Method', f'Amount ({cur})'], [[r['date'], r['reference'], r['method'], cash(r['amount'])] for r in e['payouts']],
                   [25, 80, 40, 37], numeric=(3,)),
              Spacer(1, 4),
              Paragraph(f"Open balance today: payable to you {cur} {esc(cash(e['open_balance_today']['payable_to_you']))} • commission due from you "
                        f"{esc(cash(e['open_balance_today']['commission_due_from_you']))}" + (f" • {e['open_balance_today']['waiting_for_refunds']} payment(s) waiting for a refund to settle" if e['open_balance_today']['waiting_for_refunds'] else ''), small)]

    m = data['maintenance']
    story += [*section('3. Maintenance'),
              grid(['Date', 'Vehicle', 'Work', 'Odometer', f'Amount ({cur})', 'Provider', 'Notes'],
                   [[r['date'], r['vehicle'], r['type'], dist(r['odometer_km']) if r['odometer_km'] else None, cash(r['amount']) if r['amount'] else None, r['provider'], r['notes']] for r in m['items']],
                   [17, 20, 26, 18, 20, 30, 51], numeric=(3, 4)),
              Paragraph(f"Service and repair {cur} {esc(cash(s['maintenance_spend']))} • fuel and charging {cur} {esc(cash(s['fuel_and_charging_spend']))}", small),
              Spacer(1, 4), Paragraph('<b>Coming up (as of today)</b>', body),
              grid(['Vehicle', 'Task', 'Status', 'Due', 'Km left'], [[r['vehicle'], r['task'], r['status'], r['due'], r['remaining_km']] for r in m['coming_up_today']],
                   [30, 50, 25, 45, 32], numeric=(4,), empty='Nothing due soon.')]

    d = data['documents']
    story += [KeepTogether([*section('4. Documents (as of today)'),
              grid(['Document', 'For', 'Number', 'Expiry', 'Review status', 'State'],
                   [[r['document'], r['for'], r['number'], r['expiry_date'], r['status'], r['state']] for r in d['items']],
                   [44, 26, 22, 22, 30, 38], empty='No documents on file.')]),
              Spacer(1, 4)]

    r = data['result']
    good, bad = colors.HexColor('#15803D'), colors.HexColor('#B91C1C')
    tone = bad if r['is_loss'] else good
    rows = [[Paragraph('<b>Income</b>', body), ''],
            [Paragraph('Your share of trips (after Travelly commission and refunds)', cell), Paragraph(cash(r['income']), right)],
            [Paragraph('<b>Expenses</b>', body), ''],
            [Paragraph('Service and repair', cell), Paragraph(f"\u2212 {cash(r['expenses_service_and_repair'])}", right)],
            [Paragraph('Fuel and charging', cell), Paragraph(f"\u2212 {cash(r['expenses_fuel_and_charging'])}", right)],
            [Paragraph('Total expenses', cell), Paragraph(f"<b>\u2212 {cash(r['expenses_total'])}</b>", right)],
            [Paragraph(f"<font size=11><b>{'Month loss' if r['is_loss'] else 'Month profit'}</b></font>", body),
             Paragraph(f"<font size=12 color='{tone.hexval().replace('0x', '#')}'><b>{cur} {cash(r['profit'])}</b></font>", right)]]
    sheet = Table(rows, colWidths=[132 * mm, 50 * mm])
    sheet.setStyle(TableStyle([('BOX', (0, 0), (-1, -1), 0.6, line), ('LINEBELOW', (0, 1), (-1, 1), 0.3, line),
                               ('LINEBELOW', (0, 4), (-1, 4), 0.3, line), ('LINEABOVE', (0, -1), (-1, -1), 1.2, tone),
                               ('BACKGROUND', (0, 0), (-1, 0), soft), ('BACKGROUND', (0, 2), (-1, 2), soft),
                               ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#F0FDF4') if not r['is_loss'] else colors.HexColor('#FEF2F2')),
                               ('TOPPADDING', (0, 0), (-1, -1), 4), ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                               ('LEFTPADDING', (0, 0), (-1, -1), 6), ('RIGHTPADDING', (0, 0), (-1, -1), 6), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))
    story += [KeepTogether([*section(f"5. Month result \u2013 {data['period_label']}"), sheet, Spacer(1, 3), Paragraph(esc(r['note']), small)]),
              Spacer(1, 8),
              Paragraph('This report is generated from Travelly records. Amounts are in Sri Lankan rupees. Prices follow the accepted '
                        'booking and approved extras; odometer distance is shown as a record, not as a charge.', small)]
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return out.getvalue()
