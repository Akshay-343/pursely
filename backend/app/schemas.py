from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

Kind = Literal["expense", "income"]
Cycle = Literal["weekly", "monthly", "quarterly", "yearly"]
Freq = Literal["daily", "weekly", "monthly", "yearly"]
Amount = Field(gt=0, max_digits=12, decimal_places=2)


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    default_currency: str = Field("INR", min_length=3, max_length=3)


class GoogleIn(BaseModel):
    credential: str = Field(min_length=20, max_length=4096)  # Google ID token (JWT) from Sign in with Google


class ForgotIn(BaseModel):
    email: EmailStr


class ResetIn(BaseModel):
    token: str = Field(min_length=20, max_length=200)
    password: str = Field(min_length=8, max_length=72)


class AuthConfig(BaseModel):
    google_client_id: str
    email_enabled: bool
    demo: bool = False
    ai_enabled: bool = False


class RefreshIn(BaseModel):
    refresh_token: str


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserOut(ORM):
    id: int
    email: str
    default_currency: str
    email_reminders: bool = False
    has_password: bool = True
    google_linked: bool = False


class UserUpdate(BaseModel):
    default_currency: str | None = Field(None, min_length=3, max_length=3)
    email_reminders: bool | None = None


class AccountIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    type: str = "bank"
    currency: str = Field("INR", min_length=3, max_length=3)
    opening_balance: Decimal = Decimal("0")


class AccountOut(AccountIn, ORM):
    id: int


class CategoryIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    kind: Kind = "expense"
    color: str = "#6366f1"
    icon: str | None = None


class CategoryOut(CategoryIn, ORM):
    id: int


class TransactionIn(BaseModel):
    amount: Decimal = Amount
    kind: Kind = "expense"
    date: date
    category_id: int | None = None
    account_id: int | None = None
    note: str | None = None
    tags: list[str] = []


class TransactionOut(ORM):
    id: int
    amount: Decimal
    kind: str
    date: date
    category_id: int | None
    account_id: int | None
    note: str | None
    tags: list[str]
    subscription_id: int | None
    category: CategoryOut | None = None
    account: AccountOut | None = None


class TransactionPage(BaseModel):
    items: list[TransactionOut]
    total: int
    page: int
    page_size: int


class BudgetIn(BaseModel):
    category_id: int | None = None
    amount: Decimal = Amount


class BudgetOut(BudgetIn, ORM):
    id: int


class SubscriptionIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    amount: Decimal = Amount
    currency: str = Field("INR", min_length=3, max_length=3)
    cycle: Cycle = "monthly"
    next_billing_date: date
    category_id: int | None = None
    account_id: int | None = None
    status: Literal["active", "paused", "cancelled"] = "active"
    remind_days_before: int = Field(3, ge=0, le=60)
    auto_post: bool = False
    notes: str | None = None


class SubscriptionOut(SubscriptionIn, ORM):
    id: int


class RecurringIn(BaseModel):
    amount: Decimal = Amount
    kind: Kind = "expense"
    category_id: int | None = None
    account_id: int | None = None
    note: str | None = None
    frequency: Freq = "monthly"
    next_run: date
    end_date: date | None = None
    active: bool = True


class RecurringOut(RecurringIn, ORM):
    id: int


class NotificationOut(ORM):
    id: int
    message: str
    read: bool


class TransferIn(BaseModel):
    from_account_id: int
    to_account_id: int
    amount: Decimal = Amount
    date: date
    note: str | None = None


class TransferOut(TransferIn, ORM):
    id: int


class GoalIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    target_amount: Decimal = Amount
    saved_amount: Decimal = Field(Decimal("0"), ge=0)
    deadline: date | None = None
    color: str = "#02775e"


class GoalOut(GoalIn, ORM):
    id: int


class ContributeIn(BaseModel):
    amount: Decimal = Field(max_digits=12, decimal_places=2)  # negative = withdraw


class AttachmentOut(ORM):
    id: int
    transaction_id: int
    filename: str
    content_type: str
    size: int


class AiTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=4000)


class AskIn(BaseModel):
    question: str = Field(min_length=2, max_length=500)
    history: list[AiTurn] = Field(default_factory=list, max_length=10)
