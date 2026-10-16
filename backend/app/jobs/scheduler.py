"""Idempotent daily jobs: recurring transactions, subscription auto-post, reminders."""
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models import Notification, RecurringRule, Subscription, Transaction
from app.services.dates import advance


def _notify(db: Session, user_id: int, key: str, message: str):
    exists = db.scalar(select(Notification.id).where(Notification.user_id == user_id, Notification.dedupe_key == key))
    if not exists:
        db.add(Notification(user_id=user_id, dedupe_key=key, message=message))


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
    db.commit()


def job():
    with SessionLocal() as db:
        run_jobs(db)
