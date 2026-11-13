"""Cash commission overdue rule (owner decision 13 Nov 2026).

A cash trip leaves the Owner owing Travelly the commission (payments.owner_settlement_status = COMMISSION_DUE). The age
of the Owner's debt is counted from their OLDEST unpaid cash payment (captured_at):

    day 0 - 14   FREE     trips carry on; pay each commission, or all of it together
    day 14 - 18  GRACE    reminders; paying keeps everything as it is
    day 18 +     BLOCKED  the Owner's vehicles are hidden from search and take NO NEW bookings, automatically

Blocked means new bookings only: bookings already confirmed, trips under way and assigned drivers are never cancelled.
When the Owner's commission is recorded as received the block ends by itself (it is computed, never stored). An Admin
may give a stated number of extra days (stored on the Owner role row in `role_profile`, with an audit record).
Days: COMMISSION_FREE_DAYS (14) and COMMISSION_BLOCK_DAYS (18). No new table.
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from sqlalchemy import func, select
from app.models import UserRole
from app.models.payment_models import Payment

OWNER_SHARE = ('PAYMENT', 'REALLOCATION')
ZERO = Decimal('0')
EXTENSION_KEY = 'commission_extended_until'


def _due(owner_id=None):
    where = [Payment.owner_settlement_status == 'COMMISSION_DUE', Payment.transaction_type.in_(OWNER_SHARE),
             Payment.commission_amount > 0]
    if owner_id is not None:
        where.append(Payment.payee_owner_user_id == owner_id)
    return where


def extension_until(db, owner_id):
    role = db.scalar(select(UserRole).where(UserRole.user_id == owner_id, UserRole.role_code == 'OWNER'))
    raw = (role.role_profile or {}).get(EXTENSION_KEY) if role else None
    try:
        return datetime.fromisoformat(raw) if raw else None
    except ValueError:
        return None


def standing(db, settings, owner_id, now=None):
    """Where this Owner stands: stage NONE | FREE | GRACE | BLOCKED, with the dates and the amount."""
    now = now or datetime.now(timezone.utc)
    oldest, amount = db.execute(select(func.min(func.coalesce(Payment.captured_at, Payment.created_at)),
                                       func.coalesce(func.sum(Payment.commission_amount), 0)).where(*_due(owner_id))).one()
    free, block = settings.commission_free_days, settings.commission_block_days
    if oldest is None:
        return {'stage': 'NONE', 'days_open': 0, 'amount_due': '0.00', 'oldest_due_at': None, 'free_until': None,
                'blocked_from': None, 'extended_until': None, 'free_days': free, 'block_days': block, 'blocked': False}
    days = max(0, (now - oldest).days)
    extended = extension_until(db, owner_id)
    stage = 'FREE' if days < free else 'GRACE' if days < block else 'BLOCKED'
    blocked = stage == 'BLOCKED' and not (extended and now < extended)
    return {'stage': stage, 'days_open': days, 'amount_due': format(Decimal(amount), '.2f'),
            'oldest_due_at': oldest.isoformat(), 'free_until': (oldest + timedelta(days=free)).isoformat(),
            'blocked_from': (oldest + timedelta(days=block)).isoformat(),
            'extended_until': extended.isoformat() if extended else None, 'free_days': free, 'block_days': block,
            'blocked': blocked}


def blocked_owner_ids(db, settings, now=None):
    """Owners whose new bookings are stopped now."""
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=settings.commission_block_days)
    late = db.execute(select(Payment.payee_owner_user_id).where(*_due()).group_by(Payment.payee_owner_user_id)
                      .having(func.min(func.coalesce(Payment.captured_at, Payment.created_at)) <= cutoff)).scalars().all()
    return {o for o in late if o is not None and not ((e := extension_until(db, o)) and now < e)}


def is_blocked(db, settings, owner_id, now=None):
    return standing(db, settings, owner_id, now)['blocked']
