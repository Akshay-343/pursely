import hashlib
import logging
import secrets
from datetime import timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from google.auth.exceptions import GoogleAuthError
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core import security as sec
from app.core.config import settings
from app.core.db import get_db
from app.models import Account, Category, PasswordResetToken, User
from app.schemas import AuthConfig, ForgotIn, GoogleIn, RefreshIn, RegisterIn, ResetIn, TokenOut, UserOut, UserUpdate
from app.services import mail_templates as mail
from app.services.dates import utcnow
from app.services.email import email_enabled, send_email
from app.services.ratelimit import auth_limiter, client_ip

router = APIRouter(prefix="/auth", tags=["auth"])
log = logging.getLogger(__name__)

DEFAULT_CATEGORIES = [
    ("Food & Dining", "expense", "#f97316"), ("Transport", "expense", "#0ea5e9"),
    ("Rent & Bills", "expense", "#8b5cf6"), ("Shopping", "expense", "#ec4899"),
    ("Entertainment", "expense", "#eab308"), ("Health", "expense", "#10b981"),
    ("Subscriptions", "expense", "#6366f1"), ("Salary", "income", "#22c55e"),
    ("Other Income", "income", "#14b8a6"),
]
# Verified against when the email is unknown, so a login attempt takes about as long either way.
_DUMMY_HASH = sec.hash_password("not-a-real-password")


def _tokens(user: User) -> TokenOut:
    v = user.token_version or 0
    return TokenOut(access_token=sec.access_token(user.id, v), refresh_token=sec.refresh_token(user.id, v))


def _create_user(db: Session, email: str, currency: str, password_hash: str | None, google_sub: str | None = None) -> User:
    user = User(email=email, password_hash=password_hash, default_currency=currency,
                google_sub=google_sub, email_verified=google_sub is not None)
    db.add(user)
    db.flush()
    db.add_all(Category(user_id=user.id, name=n, kind=k, color=c) for n, k, c in DEFAULT_CATEGORIES)
    db.add(Account(user_id=user.id, name="Cash", type="cash", currency=currency))
    db.commit()
    return user


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _user_out(u: User) -> UserOut:
    return UserOut(id=u.id, email=u.email, default_currency=u.default_currency, email_reminders=u.email_reminders,
                   has_password=bool(u.password_hash), google_linked=bool(u.google_sub))


@router.get("/config", response_model=AuthConfig)
def auth_config():
    """Public values the login page needs. The Google client ID is not a secret."""
    return AuthConfig(google_client_id=settings.google_client_id, email_enabled=email_enabled())


@router.post("/register", response_model=TokenOut, status_code=201)
def register(body: RegisterIn, request: Request, tasks: BackgroundTasks, db: Session = Depends(get_db)):
    auth_limiter.check(f"register:{client_ip(request)}")
    email = body.email.lower()
    if db.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(409, "Email already registered")
    user = _create_user(db, email, body.default_currency.upper(), sec.hash_password(body.password))
    tasks.add_task(send_email, email, *mail.welcome(email))
    return _tokens(user)


@router.post("/login", response_model=TokenOut)
def login(request: Request, form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    auth_limiter.check(f"login:{client_ip(request)}")
    user = db.scalar(select(User).where(User.email == form.username.lower()))
    ok = sec.verify_password(form.password, user.password_hash if user and user.password_hash else _DUMMY_HASH)
    if not user or not user.password_hash or not ok:
        raise HTTPException(401, "Incorrect email or password")
    return _tokens(user)


@router.post("/google", response_model=TokenOut)
def google_login(body: GoogleIn, request: Request, tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Sign in or sign up with a Google ID token. The token is verified (signature, audience, expiry) by Google's library."""
    auth_limiter.check(f"google:{client_ip(request)}")
    if not settings.google_client_id:
        raise HTTPException(503, "Google sign-in is not configured")
    try:
        info = google_id_token.verify_oauth2_token(body.credential, google_requests.Request(), settings.google_client_id)
    except (ValueError, GoogleAuthError):
        raise HTTPException(401, "Google sign-in failed. Please try again.") from None
    email, sub = (info.get("email") or "").lower(), info.get("sub")
    if not email or not sub or info.get("email_verified") is not True:
        raise HTTPException(401, "Your Google email address is not verified")

    user = db.scalar(select(User).where(User.google_sub == sub))
    if user:
        return _tokens(user)
    user = db.scalar(select(User).where(User.email == email))
    if user:
        # Safe to link: Google asserts it verified this address, and the existing account is keyed by the same address.
        user.google_sub, user.email_verified = sub, True
        db.commit()
        return _tokens(user)
    user = _create_user(db, email, "INR", None, google_sub=sub)
    tasks.add_task(send_email, email, *mail.welcome(email))
    return _tokens(user)


@router.post("/forgot-password", status_code=202)
def forgot_password(body: ForgotIn, request: Request, tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Always answers the same way, so it cannot be used to discover which emails have accounts."""
    auth_limiter.check(f"forgot:{client_ip(request)}")
    reply = {"detail": "If an account exists for that email, a reset link is on its way."}
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if not user:
        return reply
    recent = db.scalar(select(func.count()).select_from(PasswordResetToken).where(
        PasswordResetToken.user_id == user.id, PasswordResetToken.created_at >= utcnow() - timedelta(hours=1)))
    if recent >= settings.reset_max_per_hour:
        return reply  # silently capped; a spammer learns nothing and the owner's inbox is protected
    token = secrets.token_urlsafe(32)
    db.add(PasswordResetToken(user_id=user.id, token_hash=_hash_token(token),
                              expires_at=utcnow() + timedelta(minutes=settings.reset_token_minutes)))
    db.commit()
    link = f"{settings.app_url.rstrip('/')}/reset-password?token={token}"
    tasks.add_task(send_email, user.email, *mail.password_reset(link, settings.reset_token_minutes, google_only=not user.password_hash))
    return reply


@router.post("/reset-password", status_code=204)
def reset_password(body: ResetIn, request: Request, tasks: BackgroundTasks, db: Session = Depends(get_db)):
    auth_limiter.check(f"reset:{client_ip(request)}")
    row = db.scalar(select(PasswordResetToken).where(PasswordResetToken.token_hash == _hash_token(body.token)))
    now = utcnow()
    if not row or row.used_at or row.expires_at < now:
        raise HTTPException(400, "This reset link is invalid or has expired. Request a new one.")
    user = db.get(User, row.user_id)
    user.password_hash = sec.hash_password(body.password)
    user.token_version = (user.token_version or 0) + 1   # signs out every existing session
    # One use only, and any other outstanding links for this user die with it.
    for t in db.scalars(select(PasswordResetToken).where(PasswordResetToken.user_id == user.id, PasswordResetToken.used_at.is_(None))):
        t.used_at = now
    db.commit()
    tasks.add_task(send_email, user.email, *mail.password_changed())


@router.post("/refresh", response_model=TokenOut)
def refresh(body: RefreshIn, db: Session = Depends(get_db)):
    uid, ver = sec.decode_claims(body.refresh_token, "refresh")
    user = db.get(User, uid)
    if not user:
        raise HTTPException(401, "User not found")
    sec.ensure_fresh(user, ver)
    return _tokens(user)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(sec.current_user)):
    return _user_out(user)


@router.patch("/me", response_model=UserOut)
def update_me(body: UserUpdate, user: User = Depends(sec.current_user), db: Session = Depends(get_db)):
    if body.default_currency:
        user.default_currency = body.default_currency.upper()
    if body.email_reminders is not None:
        user.email_reminders = body.email_reminders
    db.commit()
    return _user_out(user)
