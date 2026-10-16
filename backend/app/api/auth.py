from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import security as sec
from app.core.db import get_db
from app.models import Account, Category, User
from app.schemas import RefreshIn, RegisterIn, TokenOut, UserOut, UserUpdate

router = APIRouter(prefix="/auth", tags=["auth"])

DEFAULT_CATEGORIES = [
    ("Food & Dining", "expense", "#f97316"), ("Transport", "expense", "#0ea5e9"),
    ("Rent & Bills", "expense", "#8b5cf6"), ("Shopping", "expense", "#ec4899"),
    ("Entertainment", "expense", "#eab308"), ("Health", "expense", "#10b981"),
    ("Subscriptions", "expense", "#6366f1"), ("Salary", "income", "#22c55e"),
    ("Other Income", "income", "#14b8a6"),
]


def _tokens(uid: int) -> TokenOut:
    return TokenOut(access_token=sec.access_token(uid), refresh_token=sec.refresh_token(uid))


@router.post("/register", response_model=TokenOut, status_code=201)
def register(body: RegisterIn, db: Session = Depends(get_db)):
    email = body.email.lower()
    if db.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(409, "Email already registered")
    cur = body.default_currency.upper()
    user = User(email=email, password_hash=sec.hash_password(body.password), default_currency=cur)
    db.add(user)
    db.flush()
    db.add_all(Category(user_id=user.id, name=n, kind=k, color=c) for n, k, c in DEFAULT_CATEGORIES)
    db.add(Account(user_id=user.id, name="Cash", type="cash", currency=cur))
    db.commit()
    return _tokens(user.id)


@router.post("/login", response_model=TokenOut)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == form.username.lower()))
    if not user or not sec.verify_password(form.password, user.password_hash):
        raise HTTPException(401, "Incorrect email or password")
    return _tokens(user.id)


@router.post("/refresh", response_model=TokenOut)
def refresh(body: RefreshIn, db: Session = Depends(get_db)):
    uid = sec.decode(body.refresh_token, "refresh")
    if not db.get(User, uid):
        raise HTTPException(401, "User not found")
    return _tokens(uid)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(sec.current_user)):
    return user


@router.patch("/me", response_model=UserOut)
def update_me(body: UserUpdate, user: User = Depends(sec.current_user), db: Session = Depends(get_db)):
    if body.default_currency:
        user.default_currency = body.default_currency.upper()
    if body.email_reminders is not None:
        user.email_reminders = body.email_reminders
    db.commit()
    return user
