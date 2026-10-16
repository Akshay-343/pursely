from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import current_user
from app.jobs.scheduler import run_jobs
from app.models import Account, Budget, Category, Notification, Subscription, Transaction
from app.schemas import NotificationOut
from app.services import stats
from app.services.dates import MONTHLY_FACTOR

router = APIRouter(tags=["dashboard"])


def _range(from_, to):
    to = to or date.today()
    from_ = from_ or to.replace(day=1)
    return from_, to


def _base(user, from_, to):
    return stats.base(user, from_, to)


def _sum(db, user, from_, to, kind):
    return stats.total(db, user, from_, to, kind, overall=True)


@router.get("/dashboard/summary")
def summary(from_: date | None = Query(None, alias="from"), to: date | None = None,
            db: Session = Depends(get_db), user=Depends(current_user)):
    from_, to = _range(from_, to)
    spent, income = _sum(db, user, from_, to, "expense"), _sum(db, user, from_, to, "income")
    days = (to - from_).days + 1
    return {"from": from_, "to": to, "currency": user.default_currency, "total_spent": spent,
            "total_income": income, "net": income - spent, "avg_per_day": round(spent / days, 2)}


@router.get("/dashboard/by-category")
def by_category(from_: date | None = Query(None, alias="from"), to: date | None = None, kind: str = "expense",
                db: Session = Depends(get_db), user=Depends(current_user)):
    from_, to = _range(from_, to)
    sub = _base(user, from_, to).where(Transaction.kind == kind).subquery()
    rows = db.execute(
        select(sub.c.category_id, Category.name, Category.color, func.sum(sub.c.amount).label("total"))
        .outerjoin(Category, sub.c.category_id == Category.id)
        .group_by(sub.c.category_id, Category.name, Category.color).order_by(func.sum(sub.c.amount).desc())
    ).all()
    return [{"category_id": r.category_id, "name": r.name or "Uncategorized", "color": r.color or "#94a3b8",
             "total": r.total} for r in rows]


@router.get("/dashboard/timeseries")
def timeseries(from_: date | None = Query(None, alias="from"), to: date | None = None,
               granularity: str = Query("day", pattern="^(day|week|month)$"),
               db: Session = Depends(get_db), user=Depends(current_user)):
    from_, to = _range(from_, to)
    sub = _base(user, from_, to).subquery()
    rows = db.execute(
        select(sub.c.date, sub.c.kind, func.sum(sub.c.amount)).group_by(sub.c.date, sub.c.kind)
    ).all()
    buckets: dict[date, dict] = defaultdict(lambda: {"expense": Decimal(0), "income": Decimal(0)})
    for d, kind, total in rows:
        key = d if granularity == "day" else d - timedelta(days=d.weekday()) if granularity == "week" else d.replace(day=1)
        buckets[key][kind] += total
    return [{"period": k, **v} for k, v in sorted(buckets.items())]


@router.get("/budgets/status")
def budget_status(month: str | None = None, db: Session = Depends(get_db), user=Depends(current_user)):
    first = date.fromisoformat(f"{month}-01") if month else date.today().replace(day=1)
    last = (first.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    out = []
    for b in db.scalars(select(Budget).where(Budget.user_id == user.id)):
        q = _base(user, first, last).where(Transaction.kind == "expense")
        if b.category_id:
            q = q.where(Transaction.category_id == b.category_id)
        sub = q.subquery()
        spent = db.scalar(select(func.coalesce(func.sum(sub.c.amount), 0))) or Decimal(0)
        cat = db.get(Category, b.category_id) if b.category_id else None
        pct = float(spent / b.amount * 100) if b.amount else 0
        out.append({"id": b.id, "category_id": b.category_id, "category": cat.name if cat else "Overall",
                    "color": cat.color if cat else "#6366f1", "budget": b.amount, "spent": spent,
                    "percent": round(pct, 1), "state": "over" if pct >= 100 else "warning" if pct >= 80 else "ok"})
    return out


@router.get("/subscriptions/summary")
def subscription_summary(db: Session = Depends(get_db), user=Depends(current_user)):
    subs = db.scalars(select(Subscription).where(Subscription.user_id == user.id, Subscription.status == "active")).all()
    monthly: dict[str, float] = defaultdict(float)
    by_cat: dict[str, float] = defaultdict(float)
    cats = {c.id: c for c in db.scalars(select(Category).where(Category.user_id == user.id))}
    for s in subs:
        m = float(s.amount) * MONTHLY_FACTOR[s.cycle]
        monthly[s.currency] += m
        if s.currency == user.default_currency:
            by_cat[cats[s.category_id].name if s.category_id in cats else "Uncategorized"] += m
    horizon = date.today() + timedelta(days=30)
    upcoming = sorted((s for s in subs if s.next_billing_date <= horizon), key=lambda s: s.next_billing_date)
    return {
        "currency": user.default_currency,
        "active_count": len(subs),
        "monthly_by_currency": {k: round(v, 2) for k, v in monthly.items()},
        "yearly_by_currency": {k: round(v * 12, 2) for k, v in monthly.items()},
        "monthly_by_category": [{"name": k, "total": round(v, 2)} for k, v in sorted(by_cat.items(), key=lambda x: -x[1])],
        "upcoming": [{"id": s.id, "name": s.name, "amount": s.amount, "currency": s.currency,
                      "date": s.next_billing_date, "days": (s.next_billing_date - date.today()).days} for s in upcoming],
    }


@router.get("/notifications", response_model=list[NotificationOut])
def notifications(db: Session = Depends(get_db), user=Depends(current_user)):
    run_jobs(db, user_id=user.id)  # catch up recurring/subscription work on demand
    return db.scalars(select(Notification).where(Notification.user_id == user.id)
                      .order_by(Notification.id.desc()).limit(30)).all()


@router.post("/notifications/read-all", status_code=204)
def read_all(db: Session = Depends(get_db), user=Depends(current_user)):
    for n in db.scalars(select(Notification).where(Notification.user_id == user.id, Notification.read.is_(False))):
        n.read = True
    db.commit()
