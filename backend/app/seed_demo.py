"""Create (or reset) a demo account filled with ~6 months of realistic data.

Usage: python -m app.seed_demo [email] [password]
Defaults to demo@example.com / demo1234. Re-running wipes the demo user and rebuilds it relative to today,
so the dashboard always shows current data. Never touches other users.
"""
import random
import sys
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.api.auth import _create_user
from app.core import security as sec
from app.core.db import SessionLocal
from app.models import Account, Attachment, Budget, Category, Goal, Notification, RecurringRule, Subscription, Transaction, Transfer, User
from app.services.dates import advance

DEMO_EMAIL = "demo@example.com"
DEMO_PASSWORD = "demo1234"

# (category, notes, min, max, times per month)
SPENDING = [
    ("Food & Dining", ["Swiggy order", "Lunch with team", "Groceries", "Cafe", "Dinner out"], 120, 1400, 14),
    ("Transport", ["Uber", "Metro card recharge", "Fuel", "Auto"], 60, 900, 8),
    ("Shopping", ["Amazon", "Clothes", "Electronics accessory", "Home supplies"], 300, 3500, 3),
    ("Entertainment", ["Movie tickets", "Concert", "Bowling"], 250, 1800, 2),
    ("Health", ["Pharmacy", "Doctor visit"], 150, 1500, 1),
]


def _d(v: float) -> Decimal:
    return Decimal(str(round(v, 2)))


def seed(db: Session, email: str = DEMO_EMAIL, password: str = DEMO_PASSWORD, today: date | None = None) -> User:
    today = today or date.today()
    rng = random.Random(42)
    if old := db.scalar(select(User).where(User.email == email)):
        # explicit child deletes: SQLite does not enforce ON DELETE CASCADE unless foreign keys are switched on
        for model in (Attachment, Transaction, Transfer, Subscription, RecurringRule, Budget, Goal, Account, Category, Notification):
            db.execute(delete(model).where(model.user_id == old.id))
        db.execute(delete(User).where(User.id == old.id))
        db.commit()

    user = _create_user(db, email, "INR", sec.hash_password(password))
    cats = {c.name: c for c in db.scalars(select(Category).where(Category.user_id == user.id))}
    cash = db.scalar(select(Account).where(Account.user_id == user.id))
    bank = Account(user_id=user.id, name="HDFC Savings", type="bank", currency="INR", opening_balance=_d(85000))
    card = Account(user_id=user.id, name="Credit Card", type="card", currency="INR", opening_balance=_d(0))
    db.add_all([bank, card])
    db.flush()

    def tx(amount, cat, day, note, kind="expense", account=None, tags=None):
        db.add(Transaction(user_id=user.id, amount=_d(amount), kind=kind, date=day, note=note, tags=tags or [],
                           category_id=cats[cat].id, account_id=(account or rng.choice([cash, bank, card])).id))

    first = date(today.year, today.month, 1)
    months = [first]
    for _ in range(5):
        months.insert(0, (months[0] - timedelta(days=1)).replace(day=1))

    for m in months:
        end = min(today, advance(m, "monthly") - timedelta(days=1))
        days = (end - m).days + 1
        tx(95000, "Salary", m, "Monthly salary", kind="income", account=bank)
        if days >= 3:
            tx(24000, "Rent & Bills", m + timedelta(days=2), "Rent", account=bank, tags=["home"])
        if days >= 10:
            tx(rng.uniform(1400, 2600), "Rent & Bills", m + timedelta(days=9), "Electricity bill", account=bank, tags=["home"])
        for cat, notes, lo, hi, per_month in SPENDING:
            for _ in range(max(1, round(per_month * days / 30))):
                tx(rng.uniform(lo, hi), cat, m + timedelta(days=rng.randrange(days)), rng.choice(notes))
        if m != first and rng.random() < 0.6:
            tx(rng.uniform(3000, 12000), "Other Income", m + timedelta(days=rng.randrange(10, 25)), "Freelance project",
               kind="income", account=bank, tags=["side-hustle"])

    db.add_all([
        Subscription(user_id=user.id, name=n, amount=_d(a), cycle=c, next_billing_date=today + timedelta(days=dd),
                     category_id=cats["Subscriptions"].id, account_id=card.id, remind_days_before=3)
        for n, a, c, dd in [("Netflix", 649, "monthly", 2), ("Spotify", 119, "monthly", 9), ("iCloud+", 75, "monthly", 15),
                            ("Gym membership", 1800, "monthly", 20), ("Amazon Prime", 1499, "yearly", 120)]
    ])
    db.add_all([
        Budget(user_id=user.id, category_id=cats[n].id, amount=_d(a))
        for n, a in [("Food & Dining", 9000), ("Transport", 3500), ("Shopping", 6000), ("Entertainment", 2500)]
    ])
    db.add(Budget(user_id=user.id, category_id=None, amount=_d(55000)))
    db.add_all([
        Goal(user_id=user.id, name="Emergency fund", target_amount=_d(300000), saved_amount=_d(184000), color="#02775e"),
        Goal(user_id=user.id, name="Goa trip", target_amount=_d(40000), saved_amount=_d(12500),
             deadline=today + timedelta(days=120), color="#f97316"),
        Goal(user_id=user.id, name="New laptop", target_amount=_d(120000), saved_amount=_d(30000),
             deadline=today + timedelta(days=240), color="#6366f1"),
    ])
    db.add(RecurringRule(user_id=user.id, amount=_d(5000), kind="expense", account_id=bank.id, note="SIP: index fund",
                         frequency="monthly", next_run=advance(first, "monthly")))
    db.add(Transfer(user_id=user.id, from_account_id=bank.id, to_account_id=card.id, amount=_d(18000),
                    date=first + timedelta(days=4), note="Credit card bill payment"))
    db.commit()
    return user


if __name__ == "__main__":
    email = sys.argv[1] if len(sys.argv) > 1 else DEMO_EMAIL
    password = sys.argv[2] if len(sys.argv) > 2 else DEMO_PASSWORD
    with SessionLocal() as session:
        seed(session, email, password)
    # Only echo the well-known demo password, never one passed on the command line.
    print(f"Demo account ready: {email} / {DEMO_PASSWORD}" if password == DEMO_PASSWORD else f"Demo account ready: {email}")
