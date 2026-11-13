"""Monthly Admin report (owner decision 13 Nov 2026; not in the PRD, read-only, nothing stored).

One calendar month (Sri Lanka time) for the whole platform, in the same Travelly look as the Owner report:
1. Summary      - bookings made in the month by service, trips finished, km, cancellations, new users.
2. Money        - per service: collected, Travelly commission, Owners' share, refunds paid; payouts paid to Owners;
                  today's open balances (owed to Owners, commission due from Owners, refunds waiting).
3. People       - role decisions in the month (approved / rejected per role), applications waiting now.
4. Attention    - as of today: departures needing a decision, refunds needing action, documents expired or expiring
                  within 30 days, the oldest waiting applications.
5. Month result - Travelly's income for the month = commission earned (online and cash), and how much of the cash
                  commission is still to be collected from Owners.
"""
import io
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from sqlalchemy import func, select
from app.models import User, UserRole
from app.models.hire_models import Booking, Route, ScheduledTrip, Trip
from app.models.payment_models import Payment
from app.models.review_models import Document, Vehicle
from app.services.owner_report import COLOMBO, SOON_DAYS, ZERO, km, label, local, masked, money, month_bounds

SERVICES = (('PRIVATE_HIRE', 'Private hire'), ('TICKET_HIRE', 'Tickets'), ('RENTAL', 'Rental'))
KEPT = ('PAID', 'PARTIALLY_REFUNDED')
PROBLEMS = {'PAYHERE_REFUND_FAILED': 'PayHere refused: retry or refund in the PayHere portal',
            'PAYHERE_MANUAL_REQUIRED': 'Not a card: refund by bank transfer',
            'PAYHERE_REQUESTED': 'Sent to PayHere, no answer yet: check the portal'}


def build(db, year, month, moment=None):
    from app.api.routers.settlement_api import payable_share, refunded
    from app.services.refunds import REFUNDS
    moment = moment or datetime.now(timezone.utc)
    today = moment.astimezone(COLOMBO).date()
    start, end = month_bounds(year, month)
    when = func.coalesce(Payment.captured_at, Payment.created_at)
    in_month = (when >= start, when < end)

    # 1. Summary ---------------------------------------------------------------------------------------
    made = dict(db.execute(select(Booking.booking_type, func.count()).where(Booking.created_at >= start, Booking.created_at < end)
                           .group_by(Booking.booking_type)).all())
    cancelled = db.scalar(select(func.count()).select_from(Booking).where(Booking.status == 'CANCELLED', Booking.updated_at >= start,
                                                                          Booking.updated_at < end, Booking.created_at < end)) or 0
    finished = db.execute(select(func.count(), func.coalesce(func.sum(Trip.calculated_distance_km), 0)).where(
        Trip.status == 'COMPLETED', Trip.actual_end_at >= start, Trip.actual_end_at < end)).one()
    new_users = db.scalar(select(func.count()).select_from(User).where(User.created_at >= start, User.created_at < end)) or 0
    live_vehicles = db.scalar(select(func.count()).select_from(Vehicle).where(Vehicle.is_published.is_(True))) or 0

    # 2. Money -----------------------------------------------------------------------------------------
    rows = db.execute(select(Payment, Booking.booking_type).join(Booking, Booking.id == Payment.booking_id).where(
        Payment.transaction_type == 'PAYMENT', Payment.status.in_(KEPT + ('REFUNDED',)), *in_month)).all()
    per = {code: {'service': name, 'payments': 0, 'collected': ZERO, 'commission': ZERO, 'owner_share': ZERO, 'refunded': ZERO}
           for code, name in SERVICES}
    online = cash_in = commission_online = commission_cash = ZERO
    for payment, kind in rows:
        bucket = per.setdefault(kind, {'service': label(kind), 'payments': 0, 'collected': ZERO, 'commission': ZERO, 'owner_share': ZERO, 'refunded': ZERO})
        bucket['payments'] += 1
        bucket['collected'] += payment.amount
        bucket['refunded'] += refunded(db, payment)
        if payment.status in KEPT:
            fee = payment.commission_amount or ZERO
            bucket['commission'] += fee
            bucket['owner_share'] += payable_share(db, payment)
            if payment.payment_method == 'CASH':
                commission_cash += fee
            else:
                commission_online += fee
        if payment.payment_method == 'CASH':
            cash_in += payment.amount
        else:
            online += payment.amount
    services = [{**b, 'collected': money(b['collected']), 'commission': money(b['commission']), 'owner_share': money(b['owner_share']),
                 'refunded': money(b['refunded'])} for b in per.values() if b['payments'] or b['service'] != 'Rental']
    refunds_paid = db.scalar(select(func.coalesce(func.sum(Payment.amount), 0)).where(
        Payment.transaction_type.in_(REFUNDS), Payment.status == 'PAID', func.coalesce(Payment.refunded_at, Payment.updated_at) >= start,
        func.coalesce(Payment.refunded_at, Payment.updated_at) < end)) or ZERO
    payouts = db.execute(select(func.count(), func.coalesce(func.sum(Payment.amount), 0)).where(
        Payment.transaction_type == 'OWNER_PAYOUT', Payment.status == 'PAID', *in_month)).one()
    owed = sum((payable_share(db, p) for p in db.scalars(select(Payment).where(
        Payment.owner_settlement_status == 'OWNER_PAYABLE', Payment.status.in_(KEPT)))), ZERO)
    commission_due = db.scalar(select(func.coalesce(func.sum(Payment.commission_amount), 0)).where(
        Payment.owner_settlement_status == 'COMMISSION_DUE')) or ZERO
    waiting = db.scalars(select(Payment).where(Payment.transaction_type.in_(REFUNDS), Payment.status.in_(('PENDING', 'PROCESSING', 'FAILED')))).all()
    cash_month_due = db.scalar(select(func.coalesce(func.sum(Payment.commission_amount), 0)).where(
        Payment.transaction_type == 'PAYMENT', Payment.payment_method == 'CASH', Payment.owner_settlement_status == 'COMMISSION_DUE', *in_month)) or ZERO

    # 3. People ----------------------------------------------------------------------------------------
    people = []
    for role in ('OWNER', 'DRIVER'):
        approved = db.scalar(select(func.count()).select_from(UserRole).where(UserRole.role_code == role, UserRole.approved_at >= start,
                                                                              UserRole.approved_at < end)) or 0
        rejected = db.scalar(select(func.count()).select_from(UserRole).where(UserRole.role_code == role, UserRole.approval_status == 'REJECTED',
                                                                              UserRole.updated_at >= start, UserRole.updated_at < end)) or 0
        pending = db.scalar(select(func.count()).select_from(UserRole).where(UserRole.role_code == role, UserRole.approval_status == 'PENDING')) or 0
        suspended = db.scalar(select(func.count()).select_from(UserRole).where(UserRole.role_code == role, UserRole.approval_status == 'SUSPENDED')) or 0
        people.append({'role': label(role), 'approved': approved, 'rejected': rejected, 'waiting_now': pending, 'suspended_now': suspended})
    newly = db.execute(select(UserRole, User).join(User, User.id == UserRole.user_id).where(
        UserRole.role_code.in_(('OWNER', 'DRIVER')), UserRole.approved_at >= start, UserRole.approved_at < end)
        .order_by(UserRole.approved_at).limit(50)).all()
    approved_list = [{'date': local(r.approved_at).date().isoformat(), 'name': u.display_name or u.full_name, 'reference': u.public_user_reference,
                      'role': label(r.role_code)} for r, u in newly]

    # 4. Attention (as of today) ----------------------------------------------------------------------
    stuck = db.execute(select(ScheduledTrip, Route).join(Route, Route.id == ScheduledTrip.route_id).where(
        ScheduledTrip.status.in_(('DECISION_REQUIRED', 'DISRUPTED'))).order_by(ScheduledTrip.departure_at).limit(30)).all()
    departures = [{'reference': d.departure_reference, 'route': f'{r.origin_name} → {r.destination_name}',
                   'departs': local(d.departure_at).strftime('%Y-%m-%d %H:%M'), 'status': label(d.status)} for d, r in stuck]
    books = {b.id: b for b in db.scalars(select(Booking).where(Booking.id.in_({p.booking_id for p in waiting})))} if waiting else {}
    refunds = [{'booking': books[p.booking_id].booking_reference if p.booking_id in books else None, 'amount': money(p.amount),
                'method': label(p.payment_method), 'status': label(p.status),
                'problem': PROBLEMS.get(p.failure_code, label(p.failure_code)) if p.failure_code else ('Failed' if p.status == 'FAILED' else 'Waiting to be paid'),
                'since': local(p.created_at).date().isoformat()} for p in waiting[:30]]
    expiring = db.execute(select(Document, User, Vehicle).join(User, User.id == Document.user_id).outerjoin(Vehicle, Vehicle.id == Document.vehicle_id)
                          .where(Document.status == 'APPROVED', Document.expiry_date.is_not(None),
                                 Document.expiry_date <= today + timedelta(days=SOON_DAYS)).order_by(Document.expiry_date).limit(40)).all()
    documents = [{'document': label(d.document_type), 'holder': u.display_name or u.full_name,
                  'vehicle': v.registration_number if v else None, 'number': masked(d.document_number), 'expiry_date': d.expiry_date.isoformat(),
                  'state': 'Expired' if d.expiry_date < today else f'Expires in {(d.expiry_date - today).days} days'} for d, u, v in expiring]
    oldest = db.execute(select(UserRole, User).join(User, User.id == UserRole.user_id).where(
        UserRole.role_code.in_(('OWNER', 'DRIVER')), UserRole.approval_status == 'PENDING').order_by(UserRole.requested_at).limit(10)).all()
    applications = [{'name': u.display_name or u.full_name, 'reference': u.public_user_reference, 'role': label(r.role_code),
                     'waiting_days': (today - local(r.requested_at).date()).days} for r, u in oldest]

    # 5. Month result ----------------------------------------------------------------------------------
    commission = commission_online + commission_cash
    result = {'commission_online': money(commission_online), 'commission_cash': money(commission_cash), 'income': money(commission),
              'cash_commission_still_due': money(cash_month_due),
              'note': 'Travelly income is the commission on trips paid this month (online and cash), after refunds. Commission on cash '
                      'trips is collected from Owners; the part not yet received is shown separately. Payment gateway fees, staff and '
                      'running costs are not recorded in Travelly and are not included.'}

    return {
        'period': f'{year:04d}-{month:02d}', 'period_label': date(year, month, 1).strftime('%B %Y'),
        'generated_at': local(moment).isoformat(timespec='minutes'), 'currency': 'LKR',
        'summary': {'private_hire_bookings': made.get('PRIVATE_HIRE', 0), 'ticket_bookings': made.get('TICKET_HIRE', 0),
                    'cancelled_bookings': cancelled, 'completed_trips': finished[0], 'total_km': km(finished[1]),
                    'new_users': new_users, 'published_vehicles_today': live_vehicles,
                    'collected_online': money(online), 'collected_cash': money(cash_in), 'collected_total': money(online + cash_in),
                    'travelly_commission': money(commission), 'refunds_paid': money(refunds_paid),
                    'payouts_paid': money(payouts[1]), 'payouts_count': payouts[0],
                    'needs_attention': len(departures) + len(refunds) + len(documents)},
        'money': {'per_service': services,
                  'open_balance_today': {'owed_to_owners': money(owed), 'commission_due_from_owners': money(commission_due),
                                         'refunds_waiting': len(waiting), 'refunds_waiting_amount': money(sum((p.amount for p in waiting), ZERO))}},
        'people': {'roles': people, 'approved': approved_list},
        'attention': {'departures': departures, 'refunds': refunds, 'documents': documents, 'applications': applications},
        'result': result,
    }


# --------------------------------------------------------------------------------------------------- PDF (Owner report look)

def render_pdf(data):
    from pathlib import Path
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_RIGHT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Image as Picture
    from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    navy, brand = colors.HexColor('#002155'), colors.HexColor('#E8141B')
    ink, muted, line = colors.HexColor('#1F2937'), colors.HexColor('#6B7280'), colors.HexColor('#E3E8F0')
    soft, wash = colors.HexColor('#FDECEC'), colors.HexColor('#F3F6FB')
    logo = Path(__file__).resolve().parents[1] / 'assets' / 'travelly-logo.png'
    base = getSampleStyleSheet()
    h1 = ParagraphStyle('h1', parent=base['Title'], fontName='Helvetica-Bold', fontSize=18, textColor=navy, alignment=TA_RIGHT, spaceAfter=0, leading=21)
    h2 = ParagraphStyle('h2', parent=base['Heading2'], fontName='Helvetica-Bold', fontSize=12.5, textColor=navy, spaceBefore=0, spaceAfter=0, leading=15)
    body = ParagraphStyle('body', parent=base['Normal'], fontName='Helvetica', fontSize=8.5, leading=11, textColor=ink)
    small = ParagraphStyle('small', parent=body, fontSize=7.5, leading=9.5, textColor=muted)
    cell = ParagraphStyle('cell', parent=body, fontSize=7.5, leading=9.5)
    right = ParagraphStyle('right', parent=cell, alignment=TA_RIGHT)
    tile = ParagraphStyle('tile', parent=body, leading=17)

    def cash(value):
        try:
            return f'{Decimal(str(value)):,.2f}'
        except Exception:   # noqa: BLE001
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
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, wash]), ('LINEBELOW', (0, 1), (-1, -1), 0.3, line),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'), ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 3), ('RIGHTPADDING', (0, 0), (-1, -1), 3)]))
        return table

    def section(title):
        bar = Table([['', Paragraph(esc(title), h2)]], colWidths=[1.6 * mm, 180 * mm])
        bar.setStyle(TableStyle([('BACKGROUND', (0, 0), (0, 0), brand), ('LEFTPADDING', (0, 0), (0, 0), 0), ('RIGHTPADDING', (0, 0), (0, 0), 0),
                                 ('LEFTPADDING', (1, 0), (1, 0), 6), ('TOPPADDING', (0, 0), (-1, -1), 2), ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                                 ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))
        bar.keepWithNext = True
        gap = Spacer(1, 5)
        gap.keepWithNext = True
        return [Spacer(1, 10), bar, gap]

    def sub(text):
        para = Paragraph(f'<b>{esc(text)}</b>', body)
        para.keepWithNext = True
        gap = Spacer(1, 2)
        gap.keepWithNext = True
        return [Spacer(1, 5), para, gap]

    def frame(canvas, document):
        canvas.saveState()
        width, height = A4
        canvas.setFillColor(navy); canvas.rect(0, height - 5 * mm, width, 5 * mm, stroke=0, fill=1)
        canvas.setFillColor(brand); canvas.rect(0, height - 6.2 * mm, width, 1.2 * mm, stroke=0, fill=1)
        if document.page > 1 and logo.exists():
            canvas.drawImage(str(logo), 14 * mm, height - 17 * mm, width=30 * mm, height=9.7 * mm, mask='auto')
            canvas.setFont('Helvetica', 7.5); canvas.setFillColor(muted)
            canvas.drawRightString(width - 14 * mm, height - 13 * mm, f"Monthly Admin report • {data['period_label']}")
        canvas.setFillColor(navy); canvas.rect(0, 0, width, 11 * mm, stroke=0, fill=1)
        canvas.setFont('Helvetica', 7); canvas.setFillColor(colors.white)
        canvas.drawString(14 * mm, 4.3 * mm, f"Travelly • Vehicles • Tickets • Rentals   |   Admin • {data['period_label']} • Confidential")
        canvas.setFillColor(colors.HexColor('#FF6B6B')); canvas.setFont('Helvetica-Bold', 7.5)
        canvas.drawRightString(width - 14 * mm, 4.3 * mm, f'Page {document.page}')
        canvas.restoreState()

    s, cur, mny, r = data['summary'], data['currency'], data['money'], data['result']
    out = io.BytesIO()
    doc = SimpleDocTemplate(out, pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm, topMargin=20 * mm, bottomMargin=18 * mm,
                            title=f"Travelly admin report {data['period']}", author='Travelly')
    title = [Paragraph('Monthly Admin Report', h1),
             Paragraph(f"<font size=11 color='#E8141B'><b>{esc(data['period_label'])}</b></font>", ParagraphStyle('p', parent=body, alignment=TA_RIGHT, leading=14)),
             Paragraph('Whole platform • Confidential', ParagraphStyle('o', parent=small, alignment=TA_RIGHT)),
             Paragraph(f"Generated {esc(data['generated_at'].replace('T', ' '))} (Sri Lanka time)", ParagraphStyle('g', parent=small, alignment=TA_RIGHT))]
    mark = Picture(str(logo), width=62 * mm, height=20 * mm) if logo.exists() else Paragraph('<b>Travelly</b>', h1)
    masthead = Table([[mark, title]], colWidths=[72 * mm, 110 * mm])
    masthead.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0)]))
    story = [Spacer(1, 2), masthead, Spacer(1, 8)]

    tiles = [('Bookings made', s['private_hire_bookings'] + s['ticket_bookings']), ('Trips completed', s['completed_trips']),
             ('Total km', dist(s['total_km'])), ('New users', s['new_users']),
             (f'Collected ({cur})', cash(s['collected_total'])), (f'Travelly income ({cur})', cash(s['travelly_commission'])),
             (f'Paid to Owners ({cur})', cash(s['payouts_paid'])), ('Needs attention', s['needs_attention'])]
    tile_rows = [[Paragraph(f'<font size=7 color="#6B7280">{esc(k).upper()}</font><br/><font size=14 color="#002155"><b>{esc(v)}</b></font>', tile)
                  for k, v in tiles[i:i + 4]] for i in (0, 4)]
    summary = Table(tile_rows, colWidths=[45.5 * mm] * 4)
    income_cell = (1, 1)
    summary.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), wash), ('LINEABOVE', (0, 0), (-1, 0), 2.2, navy),
                                 ('LINEABOVE', (0, 1), (-1, 1), 2.2, navy), ('LINEAFTER', (0, 0), (-2, -1), 3, colors.white),
                                 ('LINEABOVE', income_cell, income_cell, 2.2, colors.HexColor('#15803D')),
                                 ('BACKGROUND', income_cell, income_cell, colors.HexColor('#ECFDF3')),
                                 ('LINEABOVE', (3, 1), (3, 1), 2.2, brand if s['needs_attention'] else navy),
                                 ('TOPPADDING', (0, 0), (-1, -1), 7), ('BOTTOMPADDING', (0, 0), (-1, -1), 7), ('LEFTPADDING', (0, 0), (-1, -1), 8)]))
    story += [summary]

    story += [*section('1. Summary'),
              grid(['', 'This month'], [['Private hire bookings made', s['private_hire_bookings']], ['Ticket bookings made', s['ticket_bookings']],
                                        ['Bookings cancelled', s['cancelled_bookings']], ['Trips completed', s['completed_trips']],
                                        ['Kilometres driven on completed trips', dist(s['total_km'])], ['New users registered', s['new_users']],
                                        ['Vehicles published (today)', s['published_vehicles_today']]], [132, 50], numeric=(1,))]

    ob = mny['open_balance_today']
    story += [*section('2. Money'),
              grid(['Service', 'Payments', f'Collected', 'Travelly commission', "Owners' share", 'Refunded'],
                   [[x['service'], x['payments'], cash(x['collected']), cash(x['commission']), cash(x['owner_share']), cash(x['refunded'])]
                    for x in mny['per_service']], [40, 20, 30, 34, 30, 28], numeric=(1, 2, 3, 4, 5)),
              Spacer(1, 4),
              Paragraph(f"Collected online {cur} {esc(cash(s['collected_online']))} • cash {esc(cash(s['collected_cash']))} • refunds paid "
                        f"{esc(cash(s['refunds_paid']))} • <b>payouts to Owners {esc(cash(s['payouts_paid']))}</b> ({s['payouts_count']})", body),
              Spacer(1, 3),
              Paragraph(f"Open balance today: owed to Owners {cur} {esc(cash(ob['owed_to_owners']))} • commission due from Owners "
                        f"{esc(cash(ob['commission_due_from_owners']))} • refunds waiting {ob['refunds_waiting']} "
                        f"({esc(cash(ob['refunds_waiting_amount']))})", small)]

    ppl = data['people']
    story += [*section('3. People'),
              grid(['Role', 'Approved this month', 'Rejected this month', 'Waiting now', 'Suspended now'],
                   [[x['role'], x['approved'], x['rejected'], x['waiting_now'], x['suspended_now']] for x in ppl['roles']], [42, 35, 35, 35, 35],
                   numeric=(1, 2, 3, 4)),
              *sub('Approved this month'),
              grid(['Date', 'Name', 'Reference', 'Role'], [[x['date'], x['name'], x['reference'], x['role']] for x in ppl['approved']],
                   [30, 82, 40, 30], empty='No approvals this month.')]

    att = data['attention']
    story += [*section('4. Needs attention (as of today)'),
              *sub('Departures waiting for a decision'),
              grid(['Departure', 'Route', 'Departs', 'Status'], [[x['reference'], x['route'], x['departs'], x['status']] for x in att['departures']],
                   [40, 72, 35, 35], empty='None.'),
              *sub('Refunds needing action'),
              grid(['Booking', f'Amount ({cur})', 'Method', 'Status', 'Problem', 'Since'],
                   [[x['booking'], cash(x['amount']), x['method'], x['status'], x['problem'], x['since']] for x in att['refunds']],
                   [34, 26, 20, 24, 50, 28], numeric=(1,), empty='None.'),
              *sub('Documents expired or expiring within 30 days'),
              grid(['Document', 'Holder', 'Vehicle', 'Number', 'Expiry', 'State'],
                   [[x['document'], x['holder'], x['vehicle'], x['number'], x['expiry_date'], x['state']] for x in att['documents']],
                   [34, 40, 26, 22, 24, 36], empty='None.'),
              *sub('Oldest applications waiting'),
              grid(['Name', 'Reference', 'Role', 'Waiting (days)'], [[x['name'], x['reference'], x['role'], x['waiting_days']] for x in att['applications']],
                   [80, 40, 30, 32], numeric=(3,), empty='None.')]

    green = colors.HexColor('#15803D')
    rows = [[Paragraph('<b>Travelly income (commission)</b>', body), ''],
            [Paragraph('Commission on online payments', cell), Paragraph(cash(r['commission_online']), right)],
            [Paragraph('Commission on cash trips (collected from Owners)', cell), Paragraph(cash(r['commission_cash']), right)],
            [Paragraph('<font size=11><b>Travelly income this month</b></font>', body),
             Paragraph(f"<font size=12 color='#15803D'><b>{cur} {cash(r['income'])}</b></font>", right)],
            [Paragraph('Of which cash commission still to collect from Owners', cell), Paragraph(cash(r['cash_commission_still_due']), right)]]
    sheet = Table(rows, colWidths=[132 * mm, 50 * mm])
    sheet.setStyle(TableStyle([('BOX', (0, 0), (-1, -1), 0.6, line), ('BACKGROUND', (0, 0), (-1, 0), soft),
                               ('LINEBELOW', (0, 1), (-1, 1), 0.3, line), ('LINEABOVE', (0, 3), (-1, 3), 1.2, green),
                               ('BACKGROUND', (0, 3), (-1, 3), colors.HexColor('#F0FDF4')), ('LINEABOVE', (0, 4), (-1, 4), 0.3, line),
                               ('TOPPADDING', (0, 0), (-1, -1), 4), ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                               ('LEFTPADDING', (0, 0), (-1, -1), 6), ('RIGHTPADDING', (0, 0), (-1, -1), 6), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))
    story += [KeepTogether([*section(f"5. Month result – {data['period_label']}"), sheet, Spacer(1, 3), Paragraph(esc(r['note']), small)]),
              Spacer(1, 8),
              Paragraph('Confidential: for Travelly Admins. Generated from Travelly records; amounts in Sri Lankan rupees.', small)]
    doc.build(story, onFirstPage=frame, onLaterPages=frame)
    return out.getvalue()
