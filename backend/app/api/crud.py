"""Simple per-user CRUD routers for categories, accounts, budgets, recurring rules, subscriptions."""
from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models, schemas
from app.core.db import get_db
from app.core.security import current_user
from app.services.ownership import check_refs, get_owned


def make_router(prefix, model, in_schema, out_schema, order=None, refs=()):
    router = APIRouter(prefix=prefix, tags=[prefix.strip("/")])

    def validate(db, user, data):
        if refs:
            check_refs(db, user.id, data.get("category_id"), data.get("account_id"))

    @router.get("", response_model=list[out_schema])
    def list_(db: Session = Depends(get_db), user=Depends(current_user)):
        q = select(model).where(model.user_id == user.id).order_by(order or model.id)
        return db.scalars(q).all()

    @router.post("", response_model=out_schema, status_code=201)
    def create(body: in_schema, db: Session = Depends(get_db), user=Depends(current_user)):
        data = body.model_dump()
        validate(db, user, data)
        obj = model(user_id=user.id, **data)
        db.add(obj)
        db.commit()
        return obj

    @router.put("/{obj_id}", response_model=out_schema)
    def update(obj_id: int, body: in_schema, db: Session = Depends(get_db), user=Depends(current_user)):
        obj = get_owned(db, model, obj_id, user.id)
        data = body.model_dump()
        validate(db, user, data)
        for k, v in data.items():
            setattr(obj, k, v)
        db.commit()
        return obj

    @router.delete("/{obj_id}", status_code=204)
    def delete(obj_id: int, db: Session = Depends(get_db), user=Depends(current_user)):
        db.delete(get_owned(db, model, obj_id, user.id))
        db.commit()
        return Response(status_code=204)

    return router


categories = make_router("/categories", models.Category, schemas.CategoryIn, schemas.CategoryOut, models.Category.name)
accounts = make_router("/accounts", models.Account, schemas.AccountIn, schemas.AccountOut, models.Account.name)
budgets = make_router("/budgets", models.Budget, schemas.BudgetIn, schemas.BudgetOut, refs=("category_id",))
recurring = make_router("/recurring-rules", models.RecurringRule, schemas.RecurringIn, schemas.RecurringOut,
                        models.RecurringRule.next_run, refs=("category_id", "account_id"))
subscriptions = make_router("/subscriptions", models.Subscription, schemas.SubscriptionIn,
                            schemas.SubscriptionOut, models.Subscription.next_billing_date,
                            refs=("category_id", "account_id"))
