from datetime import date, datetime
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

Money = Numeric(12, 2)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)  # null for Google-only accounts
    google_sub: Mapped[str | None] = mapped_column(String(64), unique=True, index=True, nullable=True)
    token_version: Mapped[int] = mapped_column(Integer, default=0, server_default="0")  # bumped on password reset; older tokens die
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, server_default=sa.false())
    default_currency: Mapped[str] = mapped_column(String(3), default="INR")
    email_reminders: Mapped[bool] = mapped_column(Boolean, default=False, server_default=sa.false())
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Account(Base):
    __tablename__ = "accounts"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    type: Mapped[str] = mapped_column(String(30), default="bank")
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    opening_balance: Mapped[Decimal] = mapped_column(Money, default=0)


class Category(Base):
    __tablename__ = "categories"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    kind: Mapped[str] = mapped_column(String(10), default="expense")  # expense | income
    color: Mapped[str] = mapped_column(String(9), default="#6366f1")
    icon: Mapped[str | None] = mapped_column(String(40), nullable=True)


class Transaction(Base):
    __tablename__ = "transactions"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    amount: Mapped[Decimal] = mapped_column(Money)
    kind: Mapped[str] = mapped_column(String(10), default="expense")
    date: Mapped[date] = mapped_column(Date)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    subscription_id: Mapped[int | None] = mapped_column(ForeignKey("subscriptions.id", ondelete="SET NULL"), nullable=True)
    recurring_rule_id: Mapped[int | None] = mapped_column(ForeignKey("recurring_rules.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    category: Mapped["Category | None"] = relationship(lazy="joined")
    account: Mapped["Account | None"] = relationship(lazy="joined")


class Budget(Base):
    __tablename__ = "budgets"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id", ondelete="CASCADE"), nullable=True)
    amount: Mapped[Decimal] = mapped_column(Money)
    period: Mapped[str] = mapped_column(String(10), default="monthly")


class Subscription(Base):
    __tablename__ = "subscriptions"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    amount: Mapped[Decimal] = mapped_column(Money)
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    cycle: Mapped[str] = mapped_column(String(10), default="monthly")  # weekly|monthly|quarterly|yearly
    next_billing_date: Mapped[date] = mapped_column(Date)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[str] = mapped_column(String(10), default="active")  # active|paused|cancelled
    remind_days_before: Mapped[int] = mapped_column(Integer, default=3)
    auto_post: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class RecurringRule(Base):
    __tablename__ = "recurring_rules"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    amount: Mapped[Decimal] = mapped_column(Money)
    kind: Mapped[str] = mapped_column(String(10), default="expense")
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    frequency: Mapped[str] = mapped_column(String(10), default="monthly")  # daily|weekly|monthly|yearly
    next_run: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    message: Mapped[str] = mapped_column(String(300))
    dedupe_key: Mapped[str] = mapped_column(String(100), index=True)
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Transfer(Base):
    __tablename__ = "transfers"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    from_account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"))
    to_account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"))
    amount: Mapped[Decimal] = mapped_column(Money)
    date: Mapped[date] = mapped_column(Date)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)


class Goal(Base):
    __tablename__ = "goals"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    target_amount: Mapped[Decimal] = mapped_column(Money)
    saved_amount: Mapped[Decimal] = mapped_column(Money, default=0)
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    color: Mapped[str] = mapped_column(String(9), default="#02775e")


class Attachment(Base):
    __tablename__ = "attachments"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    transaction_id: Mapped[int] = mapped_column(ForeignKey("transactions.id", ondelete="CASCADE"), index=True)
    filename: Mapped[str] = mapped_column(String(200))
    content_type: Mapped[str] = mapped_column(String(100))
    size: Mapped[int] = mapped_column(Integer)
    stored_name: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)  # sha256 of the emailed token
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
