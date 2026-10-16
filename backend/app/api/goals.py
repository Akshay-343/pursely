from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import schemas
from app.api.crud import make_router
from app.core.db import get_db
from app.core.security import current_user
from app.models import Goal
from app.services.dates import add_months
from app.services.ownership import get_owned

router = make_router("/goals", Goal, schemas.GoalIn, schemas.GoalOut, Goal.id)


def _months_left(deadline: date, today: date) -> int:
    n = (deadline.year - today.year) * 12 + deadline.month - today.month
    return max(n, 0) + (1 if deadline.day >= today.day or n == 0 else 0)


@router.post("/{gid}/contribute", response_model=schemas.GoalOut)
def contribute(gid: int, body: schemas.ContributeIn, db: Session = Depends(get_db), user=Depends(current_user)):
    g = get_owned(db, Goal, gid, user.id)
    g.saved_amount = max(g.saved_amount + body.amount, 0)
    db.commit()
    return g


@router.get("/{gid}/plan")
def plan(gid: int, db: Session = Depends(get_db), user=Depends(current_user)):
    g = get_owned(db, Goal, gid, user.id)
    remaining = max(g.target_amount - g.saved_amount, 0)
    out = {"remaining": remaining, "percent": round(float(g.saved_amount / g.target_amount * 100), 1),
           "monthly_needed": None, "months_left": None, "status": "done" if remaining == 0 else "open"}
    if g.deadline and remaining:
        today = date.today()
        if g.deadline < today:
            out["status"] = "overdue"
        else:
            m = max(_months_left(g.deadline, today), 1)
            out.update(months_left=m, monthly_needed=round(remaining / m, 2))
    return out
