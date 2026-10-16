from datetime import datetime, timedelta, timezone

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


def make_token(user_id: int, kind: str, delta: timedelta) -> str:
    exp = datetime.now(timezone.utc) + delta
    return jwt.encode({"sub": str(user_id), "type": kind, "exp": exp}, settings.secret_key, ALGO)


def access_token(uid: int) -> str:
    return make_token(uid, "access", timedelta(minutes=settings.access_token_minutes))


def refresh_token(uid: int) -> str:
    return make_token(uid, "refresh", timedelta(days=settings.refresh_token_days))


def decode(token: str, kind: str) -> int:
    try:
        data = jwt.decode(token, settings.secret_key, algorithms=[ALGO])
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    if data.get("type") != kind:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Wrong token type")
    return int(data["sub"])


def current_user(token: str = Depends(oauth2), db: Session = Depends(get_db)):
    from app.models import User

    user = db.get(User, decode(token, "access"))
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
    return user
