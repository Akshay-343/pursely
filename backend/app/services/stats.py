"""Shared aggregation helpers (SQL-side) used by dashboard, insights, reports and jobs."""
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, or_, select

from app.models import Account, Transaction


def base(user, from_: date, to: date):
    """User's transactions in a date range, in the default currency (or with no account)."""
    return (
        select(Transaction)
        .outerjoin(Account, Transaction.account_id == Account.id)
        .where(Transaction.user_id == user.id, Transaction.date >= from_, Transaction.date <= to,
               or_(Account.id.is_(None), Account.currency == user.default_currency))
    )


def total(db, user, from_: date, to: date, kind="expense", category_id=None, overall=False) -> Decimal:
    q = base(user, from_, to).where(Transaction.kind == kind)
    if category_id and not overall:
        q = q.where(Transaction.category_id == category_id)
    sub = q.subquery()
    return db.scalar(select(func.coalesce(func.sum(sub.c.amount), 0))) or Decimal(0)


def month_bounds(first: date) -> tuple[date, date]:
    first = first.replace(day=1)
    last = (first.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    return first, last


def shift_month(first: date, n: int) -> date:
    m = first.month - 1 + n
    return date(first.year + m // 12, m % 12 + 1, 1)
