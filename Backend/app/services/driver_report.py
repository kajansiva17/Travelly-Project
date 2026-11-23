"""Monthly Driver report (owner decision 23 Nov 2026; read-only, nothing stored).

One calendar month (Sri Lanka time) for one Driver:
1. Trips    - completed trips the Driver drove for an Owner in the month: route, vehicle, Owner, km.
2. Payments - what Owners recorded paying the Driver, by the day paid. Online payments count at once; cash counts once the Driver
              confirms it, until then it is shown as waiting.
English only. Served as JSON for an on-screen preview and as a PDF download.
"""
import io
from datetime import date, datetime, timezone
from decimal import Decimal
from sqlalchemy import select
from app.models import User
from app.models.driver_payment_models import DriverPayment
from app.models.hire_models import Booking, Route, ScheduledTrip, Trip
from app.models.review_models import Vehicle
from app.services.owner_report import COLOMBO, ZERO, km, label, local, money, month_bounds


def build(db, driver, year, month, moment=None):
    moment = moment or datetime.now(timezone.utc)
    start, end = month_bounds(year, month)
    first_day, next_first = date(year, month, 1), date(year + (month == 12), month % 12 + 1, 1)

    # 1. Trips ------------------------------------------------------------------------------------------
    trips = db.scalars(select(Trip).where(Trip.driver_user_id == driver.id, Trip.operating_owner_user_id != driver.id, Trip.status == 'COMPLETED',
                                          Trip.actual_end_at >= start, Trip.actual_end_at < end).order_by(Trip.actual_end_at)).all()
    owners = {u.id: u for u in db.scalars(select(User).where(User.id.in_({t.operating_owner_user_id for t in trips if t.operating_owner_user_id})))} if trips else {}
    paid_trips = set(db.scalars(select(DriverPayment.trip_id).where(DriverPayment.trip_id.in_([t.id for t in trips]), DriverPayment.status != 'DECLINED'))) if trips else set()
    trip_rows, total_km = [], ZERO
    for t in trips:
        vehicle = db.get(Vehicle, t.vehicle_id) if t.vehicle_id else None
        if t.scheduled_trip_id:
            departure = db.get(ScheduledTrip, t.scheduled_trip_id)
            route = db.get(Route, departure.route_id) if departure else None
            reference = departure.departure_reference if departure else None
            where = f'{route.origin_name} \u2192 {route.destination_name}' if route else None
        else:
            booking = db.get(Booking, t.booking_id) if t.booking_id else None
            reference = booking.booking_reference if booking else None
            where = f'{booking.origin_text} \u2192 {booking.destination_text}' if booking and booking.origin_text else None
        distance = t.calculated_distance_km if t.calculated_distance_km is not None else (
            t.end_odometer_km - t.start_odometer_km if t.end_odometer_km is not None and t.start_odometer_km is not None else None)
        total_km += distance or ZERO
        owner = owners.get(t.operating_owner_user_id)
        trip_rows.append({'date': local(t.actual_end_at).date().isoformat(), 'trip': t.trip_reference, 'reference': reference, 'route': where,
                          'vehicle': vehicle.registration_number if vehicle else None, 'owner': (owner.display_name or owner.full_name) if owner else None,
                          'distance_km': km(distance), 'payment': 'Recorded' if t.id in paid_trips else 'Not recorded yet'})

    # 2. Payments ---------------------------------------------------------------------------------------
    pays = db.execute(select(DriverPayment, Trip).join(Trip, Trip.id == DriverPayment.trip_id)
                      .where(DriverPayment.driver_user_id == driver.id, DriverPayment.status != 'DECLINED',
                             DriverPayment.paid_on >= first_day, DriverPayment.paid_on < next_first)
                      .order_by(DriverPayment.paid_on, DriverPayment.created_at)).all()
    payers = {u.id: u for u in db.scalars(select(User).where(User.id.in_({p.owner_user_id for p, _ in pays})))} if pays else {}
    pay_rows, received, waiting = [], ZERO, ZERO
    for p, trip in pays:
        payer = payers.get(p.owner_user_id)
        confirmed = p.status == 'CONFIRMED'
        pay_rows.append({'paid_on': p.paid_on.isoformat(), 'trip': trip.trip_reference, 'owner': (payer.display_name or payer.full_name) if payer else None,
                         'method': label(p.method), 'reference': p.reference, 'amount': money(p.amount),
                         'status': 'Confirmed' if confirmed else 'Waiting for you to confirm'})
        if confirmed:
            received += p.amount
        else:
            waiting += p.amount

    return {'driver': {'name': driver.display_name or driver.full_name, 'reference': driver.public_user_reference},
            'period': f'{year:04d}-{month:02d}', 'period_label': date(year, month, 1).strftime('%B %Y'),
            'generated_at': local(moment).isoformat(timespec='minutes'), 'currency': 'LKR',
            'summary': {'completed_trips': len(trip_rows), 'total_km': km(total_km), 'received_total': money(received), 'waiting_total': money(waiting),
                        'trips_without_payment': sum(1 for r in trip_rows if r['payment'] != 'Recorded')},
            'trips': {'items': trip_rows}, 'payments': {'items': pay_rows},
            'note': 'Payments are what your Owners recorded in Travelly, by the day they paid. Cash counts once you confirm it. '
                    'Trips are listed by the day they finished.'}


def render_pdf(data):
    from pathlib import Path
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_RIGHT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Image as Picture
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    navy, brand = colors.HexColor('#002155'), colors.HexColor('#E8141B')
    ink, muted, line, wash = colors.HexColor('#1F2937'), colors.HexColor('#6B7280'), colors.HexColor('#E3E8F0'), colors.HexColor('#F3F6FB')
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

    def section(title):
        bar = Table([['', Paragraph(esc(title), h2)]], colWidths=[1.6 * mm, 180 * mm])
        bar.setStyle(TableStyle([('BACKGROUND', (0, 0), (0, 0), brand), ('LEFTPADDING', (0, 0), (0, 0), 0), ('RIGHTPADDING', (0, 0), (0, 0), 0),
                                 ('LEFTPADDING', (1, 0), (1, 0), 6), ('TOPPADDING', (0, 0), (-1, -1), 2), ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                                 ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))
        return [Spacer(1, 10), bar, Spacer(1, 5)]

    def footer(canvas, document):
        canvas.saveState()
        width, height = A4
        canvas.setFillColor(navy); canvas.rect(0, height - 5 * mm, width, 5 * mm, stroke=0, fill=1)
        canvas.setFillColor(brand); canvas.rect(0, height - 6.2 * mm, width, 1.2 * mm, stroke=0, fill=1)
        canvas.setFillColor(navy); canvas.rect(0, 0, width, 11 * mm, stroke=0, fill=1)
        canvas.setFont('Helvetica', 7); canvas.setFillColor(colors.white)
        canvas.drawString(14 * mm, 4.3 * mm, f"Travelly   |   {data['driver']['name']} \u2022 {data['period_label']}")
        canvas.setFillColor(colors.HexColor('#FF6B6B')); canvas.setFont('Helvetica-Bold', 7.5)
        canvas.drawRightString(width - 14 * mm, 4.3 * mm, f'Page {document.page}')
        canvas.restoreState()

    s, cur = data['summary'], data['currency']
    out = io.BytesIO()
    doc = SimpleDocTemplate(out, pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm, topMargin=20 * mm, bottomMargin=18 * mm,
                            title=f"Travelly Driver report {data['period']}", author='Travelly')
    title = [Paragraph('Monthly Driver Report', h1),
             Paragraph(f"<font size=11 color='#E8141B'><b>{esc(data['period_label'])}</b></font>", ParagraphStyle('p', parent=body, alignment=TA_RIGHT, leading=14)),
             Paragraph(f"{esc(data['driver']['name'])} \u2022 {esc(data['driver']['reference'])}", ParagraphStyle('o', parent=small, alignment=TA_RIGHT)),
             Paragraph(f"Generated {esc(data['generated_at'].replace('T', ' '))} (Sri Lanka time)", ParagraphStyle('g', parent=small, alignment=TA_RIGHT))]
    mark = Picture(str(logo), width=62 * mm, height=20 * mm) if logo.exists() else Paragraph('<b>Travelly</b>', h1)
    masthead = Table([[mark, title]], colWidths=[72 * mm, 110 * mm])
    masthead.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0)]))
    tiles = [('Completed trips', s['completed_trips']), ('Total km', dist(s['total_km'])),
             (f'Received ({cur})', cash(s['received_total'])), (f'Waiting for you ({cur})', cash(s['waiting_total']))]
    tile = ParagraphStyle('tile', parent=body, leading=17)
    summary = Table([[Paragraph(f'<font size=7 color="#6B7280">{esc(k).upper()}</font><br/><font size=14 color="#002155"><b>{esc(v)}</b></font>', tile) for k, v in tiles]],
                    colWidths=[45.5 * mm] * 4)
    summary.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), wash), ('LINEABOVE', (0, 0), (-1, 0), 2.2, navy), ('LINEAFTER', (0, 0), (-2, -1), 3, colors.white),
                                 ('TOPPADDING', (0, 0), (-1, -1), 7), ('BOTTOMPADDING', (0, 0), (-1, -1), 7), ('LEFTPADDING', (0, 0), (-1, -1), 8)]))
    story = [Spacer(1, 2), masthead, Spacer(1, 8), summary,
             *section('1. Trips'),
             grid(['Date', 'Trip', 'Booking', 'Route', 'Vehicle', 'Owner', 'Km', 'Payment'],
                  [[r['date'], r['trip'], r['reference'], r['route'], r['vehicle'], r['owner'], dist(r['distance_km']) if r['distance_km'] else None, r['payment']] for r in data['trips']['items']],
                  [17, 22, 22, 36, 20, 28, 12, 25], numeric=(6,), empty='No completed trips this month.'),
             *section('2. Payments from your Owners'),
             grid(['Paid on', 'Trip', 'Owner', 'Method', 'Reference', f'Amount ({cur})', 'Status'],
                  [[r['paid_on'], r['trip'], r['owner'], label(r['method']), r['reference'], cash(r['amount']), r['status']] for r in data['payments']['items']],
                  [20, 26, 34, 18, 30, 24, 30], numeric=(5,), empty='No payments recorded this month.'),
             Spacer(1, 4),
             Paragraph(f"Received {cur} {esc(cash(s['received_total']))} \u2022 waiting for your confirmation {cur} {esc(cash(s['waiting_total']))}"
                       + (f" \u2022 {s['trips_without_payment']} trip(s) without a recorded payment yet" if s['trips_without_payment'] else ''), body),
             Spacer(1, 4), Paragraph(esc(data['note']), small)]
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return out.getvalue()
