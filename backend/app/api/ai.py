import hashlib
import json
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.core.security import current_user
from app.schemas import AskIn
from app.services import ai
from app.services.ratelimit import RateLimiter

router = APIRouter(prefix="/ai", tags=["ai"])

ai_limiter = RateLimiter(settings.ai_requests_per_hour, 3600, "You've reached the hourly limit for AI requests. Try again later.")
# (user id, date) -> (fingerprint of the data the tips were made from, tips). Tips change when the data does.
_tips_cache: dict[tuple[int, date], tuple[str, dict]] = {}


def _require_ai():
    if not ai.enabled():
        raise HTTPException(503, "AI features are not configured on this server.")


@router.get("/tips")
def tips(refresh: bool = False, db: Session = Depends(get_db), user=Depends(current_user)):
    _require_ai()
    ctx = ai.build_context(db, user)
    if not ctx["monthly_trend"] or not any(float(m["spent"]) or float(m["income"]) for m in ctx["monthly_trend"]):
        return {"summary": "Add a few transactions and Pursely will start suggesting ways to save.", "tips": []}
    fp = hashlib.sha256(json.dumps(ctx, default=str, sort_keys=True).encode()).hexdigest()
    key = (user.id, date.today())
    cached = _tips_cache.get(key)
    if cached and cached[0] == fp and not refresh:
        return cached[1]
    ai_limiter.check(f"u{user.id}")
    try:
        out = ai.tips(ctx)
    except ai.AiUnavailable:
        raise HTTPException(502, "The AI service didn't respond. Please try again in a moment.") from None
    for k in [k for k in _tips_cache if k[1] != key[1]]:
        del _tips_cache[k]  # drop earlier days
    _tips_cache[key] = (fp, out)
    return out


@router.post("/ask")
def ask(body: AskIn, db: Session = Depends(get_db), user=Depends(current_user)):
    _require_ai()
    ai_limiter.check(f"u{user.id}")
    try:
        answer = ai.ask(ai.build_context(db, user), body.question, [t.model_dump() for t in body.history])
    except ai.AiUnavailable:
        raise HTTPException(502, "The AI service didn't respond. Please try again in a moment.") from None
    return {"answer": answer}
