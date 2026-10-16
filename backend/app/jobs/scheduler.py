"""Idempotent daily jobs: recurring transactions, subscription auto-post, reminders."""
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models import Budget, Category, Notification, RecurringRule, Subscription, Transaction, User
from app.services import stats
from app.services.email import send_email
from app.services.dates import advance


def _notify(db: Session, user_id: int, key: str, message: str):
    exists = db.scalar(select(Notification.id).where(Notification.user_id == user_id, Notification.dedupe_key == key))
    if exists:
        return
    db.add(Notification(user_id=user_id, dedupe_key=key, message=message))
    user = db.get(User, user_id)
    if user and user.email_reminders:
        send_email(user.email, "Money Tracker reminder", message)


def run_jobs(db: Session, today: date | None = None, user_id: int | None = None):
    today = today or date.today()
    only = (lambda m: m.user_id == user_id) if user_id else (lambda m: True)

    for r in db.scalars(select(RecurringRule).where(RecurringRule.active, RecurringRule.next_run <= today, only(RecurringRule))):
        while r.next_run <= today and (r.end_date is None or r.next_run <= r.end_date):
            db.add(Transaction(user_id=r.user_id, account_id=r.account_id, category_id=r.category_id,
                               amount=r.amount, kind=r.kind, date=r.next_run, note=r.note,
                               tags=[], recurring_rule_id=r.id))
            r.next_run = advance(r.next_run, r.frequency)
        if r.end_date and r.next_run > r.end_date:
            r.active = False

    for s in db.scalars(select(Subscription).where(Subscription.status == "active", only(Subscription))):
        if s.auto_post:
            while s.next_billing_date <= today:
                db.add(Transaction(user_id=s.user_id, account_id=s.account_id, category_id=s.category_id,
                                   amount=s.amount, kind="expense", date=s.next_billing_date,
                                   note=f"Subscription: {s.name}", tags=["subscription"], subscription_id=s.id))
                s.next_billing_date = advance(s.next_billing_date, s.cycle)
        days = (s.next_billing_date - today).days
        if 0 <= days <= s.remind_days_before:
            when = "today" if days == 0 else f"in {days} day{'s' if days != 1 else ''}"
            _notify(db, s.user_id, f"sub:{s.id}:{s.next_billing_date}",
                    f"{s.name} renews {when} ({s.currency} {s.amount})")
    _budget_alerts(db, today, user_id)
    db.commit()


def _budget_alerts(db: Session, today: date, user_id: int | None):
    first, last = stats.month_bounds(today)
    q = select(Budget)
    if user_id:
        q = q.where(Budget.user_id == user_id)
    db.flush()
    for b in db.scalars(q).all():
        user = db.get(User, b.user_id)
        spent = stats.total(db, user, first, last, "expense", b.category_id, overall=b.category_id is None)
        pct = float(spent / b.amount * 100) if b.amount else 0
        level = 100 if pct >= 100 else 80 if pct >= 80 else 0
        if not level:
            continue
        cat = db.get(Category, b.category_id) if b.category_id else None
        name = cat.name if cat else "Overall"
        text = "is over budget" if level == 100 else "has used 80% of its budget"
        _notify(db, b.user_id, f"budget:{b.id}:{first:%Y-%m}:{level}",
                f"{name} {text} ({user.default_currency} {spent} of {b.amount})")


def job():
    with SessionLocal() as db:
        run_jobs(db)
