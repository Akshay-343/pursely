import io
from collections import defaultdict
from datetime import date

from fastapi import APIRouter, Depends, Query, Response
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import current_user
from app.models import Account, Category, Transaction
from app.services import stats

router = APIRouter(tags=["insights"])


def _by_category(db, user, first, last):
    sub = stats.base(user, first, last).where(Transaction.kind == "expense").subquery()
    rows = db.execute(select(sub.c.category_id, func.sum(sub.c.amount)).group_by(sub.c.category_id)).all()
    names = {c.id: c.name for c in db.scalars(select(Category).where(Category.user_id == user.id))}
    return {names.get(cid, "Uncategorized"): float(t) for cid, t in rows}


@router.get("/insights/overview")
def overview(months: int = Query(6, ge=2, le=24), db: Session = Depends(get_db), user=Depends(current_user)):
    today = date.today()
    this_first = today.replace(day=1)
    trend = []
    for i in range(months - 1, -1, -1):
        f = stats.shift_month(this_first, -i)
        f, l = stats.month_bounds(f)
        spent, inc = stats.total(db, user, f, l, "expense", overall=True), stats.total(db, user, f, l, "income", overall=True)
        trend.append({"month": f.strftime("%Y-%m"), "spent": spent, "income": inc,
                      "savings_rate": round(float((inc - spent) / inc * 100), 1) if inc else None})

    cur_f, cur_l = stats.month_bounds(this_first)
    prev_f, prev_l = stats.month_bounds(stats.shift_month(this_first, -1))
    cur, prev = _by_category(db, user, cur_f, cur_l), _by_category(db, user, prev_f, prev_l)
    changes = sorted(({"name": n, "current": cur.get(n, 0), "previous": prev.get(n, 0),
                       "delta": round(cur.get(n, 0) - prev.get(n, 0), 2)} for n in set(cur) | set(prev)),
                     key=lambda r: -abs(r["delta"]))

    spent_so_far = float(stats.total(db, user, cur_f, today, "expense", overall=True))
    days_in_month = (cur_l - cur_f).days + 1
    projected = round(spent_so_far / today.day * days_in_month, 2)

    sub = stats.base(user, cur_f.replace(year=cur_f.year - 1) if months > 12 else stats.shift_month(this_first, -(months - 1)), cur_l) \
        .where(Transaction.kind == "expense", Transaction.note.is_not(None)).subquery()
    merchants = db.execute(
        select(func.lower(func.trim(sub.c.note)).label("n"), func.count(), func.sum(sub.c.amount))
        .group_by("n").order_by(func.sum(sub.c.amount).desc()).limit(8)).all()

    sub2 = stats.base(user, cur_f, cur_l).where(Transaction.kind == "expense").subquery()
    biggest = db.execute(select(sub2.c.date, sub2.c.note, sub2.c.amount).order_by(sub2.c.amount.desc()).limit(5)).all()

    return {
        "currency": user.default_currency, "trend": trend, "category_changes": changes,
        "projection": {"spent_so_far": spent_so_far, "projected_month_end": projected,
                       "previous_month": float(stats.total(db, user, prev_f, prev_l, "expense", overall=True))},
        "top_merchants": [{"name": n, "count": c, "total": t} for n, c, t in merchants],
        "biggest_this_month": [{"date": d, "note": n, "amount": a} for d, n, a in biggest],
    }


@router.get("/reports/monthly.pdf")
def monthly_pdf(month: str | None = None, db: Session = Depends(get_db), user=Depends(current_user)):
    first = date.fromisoformat(f"{month}-01") if month else date.today().replace(day=1)
    first, last = stats.month_bounds(first)
    cur = user.default_currency
    spent, inc = stats.total(db, user, first, last, "expense", overall=True), stats.total(db, user, first, last, "income", overall=True)
    cats = sorted(_by_category(db, user, first, last).items(), key=lambda kv: -kv[1])
    txs = db.scalars(stats.base(user, first, last).order_by(Transaction.date)).unique().all()

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, title=f"Report {first:%B %Y}")
    st = getSampleStyleSheet()
    grid = TableStyle([("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e6f2f0")),
                       ("FONTSIZE", (0, 0), (-1, -1), 9), ("ALIGN", (-1, 0), (-1, -1), "RIGHT")])
    el = [Paragraph(f"Money Tracker report: {first:%B %Y}", st["Title"]), Paragraph(user.email, st["Normal"]), Spacer(1, 12)]
    el.append(Table([["Spent", "Income", "Net"], [f"{cur} {spent}", f"{cur} {inc}", f"{cur} {inc - spent}"]], style=grid))
    el += [Spacer(1, 14), Paragraph("Spending by category", st["Heading2"])]
    el.append(Table([["Category", f"Amount ({cur})"]] + [[n, f"{v:,.2f}"] for n, v in cats] if cats else [["No spending", ""]], style=grid))
    el += [Spacer(1, 14), Paragraph("Transactions", st["Heading2"])]
    rows = [["Date", "Type", "Category", "Note", "Amount"]]
    for t in txs:
        rows.append([str(t.date), t.kind, (t.category.name if t.category else "")[:22], (t.note or "")[:34], f"{t.amount:,.2f}"])
    el.append(Table(rows if len(rows) > 1 else [["No transactions"]], repeatRows=1, style=grid))
    doc.build(el)
    return Response(buf.getvalue(), media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename=report-{first:%Y-%m}.pdf"})
