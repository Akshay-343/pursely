from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db

oauth2 = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
ALGO = "HS256"


def hash_password(p: str) -> str:
    return bcrypt.hashpw(p.encode()[:72], bcrypt.gensalt()).decode()


def verify_password(p: str, h: str) -> bool:
    try:
        return bcrypt.checkpw(p.encode()[:72], h.encode())
    except ValueError:
        return False


def make_token(user_id: int, kind: str, delta: timedelta, version: int = 0) -> str:
    exp = datetime.now(UTC) + delta
    return jwt.encode({"sub": str(user_id), "type": kind, "v": version, "exp": exp}, settings.secret_key, ALGO)


def access_token(uid: int, version: int = 0) -> str:
    return make_token(uid, "access", timedelta(minutes=settings.access_token_minutes), version)


def refresh_token(uid: int, version: int = 0) -> str:
    return make_token(uid, "refresh", timedelta(days=settings.refresh_token_days), version)


def decode_claims(token: str, kind: str) -> tuple[int, int]:
    """Returns (user id, token version)."""
    try:
        data = jwt.decode(token, settings.secret_key, algorithms=[ALGO])
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token") from None
    if data.get("type") != kind:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Wrong token type")
    return int(data["sub"]), int(data.get("v", 0))


def ensure_fresh(user, version: int) -> None:
    """Reject tokens minted before the last password reset (a reset must end old sessions)."""
    if version != (user.token_version or 0):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session expired. Please sign in again.")


def current_user(token: str = Depends(oauth2), db: Session = Depends(get_db)):
    from app.models import User

    uid, ver = decode_claims(token, "access")
    user = db.get(User, uid)
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
    ensure_fresh(user, ver)
    return user
