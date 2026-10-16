from datetime import date, timedelta

from app.jobs.scheduler import run_jobs
from app.core import db as dbmod
from tests.conftest import register


def test_auth_and_isolation(client):
    a, b = register(client, "a@example.com"), register(client, "b@example.com")
    assert client.get("/api/v1/auth/me", headers=a).json()["email"] == "a@example.com"
    assert client.post("/api/v1/auth/register", json={"email": "a@example.com", "password": "password123"}).status_code == 409
    cats_a = client.get("/api/v1/categories", headers=a).json()
    assert len(cats_a) >= 5  # seeded defaults
    t = client.post("/api/v1/transactions", headers=a,
                    json={"amount": "12.50", "date": str(date.today()), "category_id": cats_a[0]["id"]}).json()
    # user B cannot see/modify A's data
    assert client.get("/api/v1/transactions", headers=b).json()["total"] == 0
    assert client.delete(f"/api/v1/transactions/{t['id']}", headers=b).status_code == 404
    # nor reference A's category
    r = client.post("/api/v1/transactions", headers=b,
                    json={"amount": "1", "date": str(date.today()), "category_id": cats_a[0]["id"]})
    assert r.status_code == 422
    assert client.get("/api/v1/transactions").status_code == 401


def test_login_and_refresh(client):
    register(client)
    r = client.post("/api/v1/auth/login", data={"username": "a@example.com", "password": "password123"})
    assert r.status_code == 200
    assert client.post("/api/v1/auth/login", data={"username": "a@example.com", "password": "bad"}).status_code == 401
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": r.json()["refresh_token"]}).status_code == 200
    # access token cannot be used as refresh token
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": r.json()["access_token"]}).status_code == 401


def test_dashboard_and_budget(client):
    h = register(client)
    cats = {c["name"]: c["id"] for c in client.get("/api/v1/categories", headers=h).json()}
    today = date.today()
    for amt, cat in [("100", "Food & Dining"), ("50", "Food & Dining"), ("30", "Transport")]:
        client.post("/api/v1/transactions", headers=h,
                    json={"amount": amt, "date": str(today), "category_id": cats[cat]})
    client.post("/api/v1/transactions", headers=h,
                json={"amount": "1000", "kind": "income", "date": str(today), "category_id": cats["Salary"]})
    s = client.get("/api/v1/dashboard/summary", headers=h).json()
    assert float(s["total_spent"]) == 180 and float(s["net"]) == 820
    by = client.get("/api/v1/dashboard/by-category", headers=h).json()
    assert by[0]["name"] == "Food & Dining" and float(by[0]["total"]) == 150
    ts = client.get("/api/v1/dashboard/timeseries?granularity=month", headers=h).json()
    assert len(ts) == 1 and float(ts[0]["expense"]) == 180
    client.post("/api/v1/budgets", headers=h, json={"category_id": cats["Food & Dining"], "amount": "160"})
    st = client.get("/api/v1/budgets/status", headers=h).json()[0]
    assert st["state"] == "warning" and st["percent"] == 93.8


def test_subscriptions_summary_and_autopost(client):
    h = register(client)
    today = date.today()
    client.post("/api/v1/subscriptions", headers=h, json={
        "name": "Netflix", "amount": "10", "currency": "INR", "cycle": "monthly",
        "next_billing_date": str(today - timedelta(days=1)), "auto_post": True})
    client.post("/api/v1/subscriptions", headers=h, json={
        "name": "Domain", "amount": "120", "currency": "INR", "cycle": "yearly",
        "next_billing_date": str(today + timedelta(days=2))})
    summ = client.get("/api/v1/subscriptions/summary", headers=h).json()
    assert summ["monthly_by_currency"]["INR"] == 20.0 and summ["yearly_by_currency"]["INR"] == 240.0
    with dbmod.SessionLocal() as db:
        run_jobs(db)
        run_jobs(db)  # idempotent
    txs = client.get("/api/v1/transactions", headers=h).json()
    assert txs["total"] == 1 and txs["items"][0]["note"] == "Subscription: Netflix"
    notes = client.get("/api/v1/notifications", headers=h).json()
    assert any("Domain" in n["message"] for n in notes) and len([n for n in notes if "Domain" in n["message"]]) == 1


def test_recurring_rule_generates(client):
    h = register(client)
    start = date.today() - timedelta(days=70)
    client.post("/api/v1/recurring-rules", headers=h, json={
        "amount": "500", "frequency": "monthly", "next_run": str(start), "note": "Gym"})
    with dbmod.SessionLocal() as db:
        run_jobs(db)
    assert client.get("/api/v1/transactions", headers=h).json()["total"] >= 3


def test_csv_roundtrip(client):
    h = register(client)
    csv = "date,kind,amount,category,account,note,tags\n2025-01-05,expense,42.5,Pets,Wallet,Food,a;b\n" \
          "bad,expense,x,,,,\nbad,expense,1,,,,\n2025-01-05,gift,1,,,,\n2025-01-05,expense,NaN,,,,\n"
    r = client.post("/api/v1/transactions/import", headers=h, files={"file": ("t.csv", csv, "text/csv")}).json()
    assert r["created"] == 1
    assert r["errors"] == ["line 3: amount must be a positive number", "line 4: date must be YYYY-MM-DD",
                           "line 5: kind must be expense or income", "line 6: amount must be a positive number"]
    out = client.get("/api/v1/transactions/export.csv", headers=h).text
    assert "Pets" in out and "a;b" in out
    assert client.get("/api/v1/transactions?tag=a", headers=h).json()["total"] == 1
    assert client.get("/api/v1/transactions?tag=zzz", headers=h).json()["total"] == 0


def test_transfers_and_balances(client):
    h = register(client)
    cash = client.get("/api/v1/accounts", headers=h).json()[0]
    bank = client.post("/api/v1/accounts", headers=h, json={"name": "Bank", "currency": "INR", "opening_balance": "1000"}).json()
    client.post("/api/v1/transactions", headers=h, json={"amount": "200", "date": str(date.today()), "account_id": bank["id"]})
    t = {"from_account_id": bank["id"], "to_account_id": cash["id"], "amount": "300", "date": str(date.today())}
    assert client.post("/api/v1/transfers", headers=h, json=t).status_code == 201
    assert client.post("/api/v1/transfers", headers=h, json={**t, "to_account_id": bank["id"]}).status_code == 422
    usd = client.post("/api/v1/accounts", headers=h, json={"name": "USD", "currency": "USD"}).json()
    assert client.post("/api/v1/transfers", headers=h, json={**t, "to_account_id": usd["id"]}).status_code == 422
    b = client.get("/api/v1/accounts/balances", headers=h).json()
    by = {a["name"]: float(a["balance"]) for a in b["accounts"]}
    assert by["Bank"] == 500 and by["Cash"] == 300
    assert float(b["net_worth_by_currency"]["INR"]) == 800
    other = register(client, "z@example.com")
    assert client.post("/api/v1/transfers", headers=other, json=t).status_code == 404


def test_goals(client):
    h = register(client)
    deadline = date.today() + timedelta(days=95)
    g = client.post("/api/v1/goals", headers=h, json={"name": "Trip", "target_amount": "10000", "deadline": str(deadline)}).json()
    g = client.post(f"/api/v1/goals/{g['id']}/contribute", headers=h, json={"amount": "4000"}).json()
    assert float(g["saved_amount"]) == 4000
    p = client.get(f"/api/v1/goals/{g['id']}/plan", headers=h).json()
    assert p["percent"] == 40.0 and p["months_left"] >= 3 and p["monthly_needed"] <= 2000
    g = client.post(f"/api/v1/goals/{g['id']}/contribute", headers=h, json={"amount": "-9999"}).json()
    assert float(g["saved_amount"]) == 0  # never negative


def test_insights_and_pdf(client):
    h = register(client)
    cats = {c["name"]: c["id"] for c in client.get("/api/v1/categories", headers=h).json()}
    today = date.today()
    client.post("/api/v1/transactions", headers=h, json={"amount": "100", "date": str(today), "category_id": cats["Transport"], "note": "Uber"})
    client.post("/api/v1/transactions", headers=h, json={"amount": "50", "date": str(today), "category_id": cats["Transport"], "note": "uber "})
    client.post("/api/v1/transactions", headers=h, json={"amount": "500", "kind": "income", "date": str(today), "category_id": cats["Salary"]})
    o = client.get("/api/v1/insights/overview?months=3", headers=h).json()
    assert len(o["trend"]) == 3 and float(o["trend"][-1]["spent"]) == 150 and o["trend"][-1]["savings_rate"] == 70.0
    assert o["top_merchants"][0]["name"] == "uber" and o["top_merchants"][0]["count"] == 2
    assert o["projection"]["projected_month_end"] >= 150
    r = client.get("/api/v1/reports/monthly.pdf", headers=h)
    assert r.status_code == 200 and r.content.startswith(b"%PDF")


def test_attachments(client, tmp_path):
    from app.core.config import settings
    settings.upload_dir = str(tmp_path)
    h, other = register(client), register(client, "o@example.com")
    t = client.post("/api/v1/transactions", headers=h, json={"amount": "5", "date": str(date.today())}).json()
    png = b"\x89PNG\r\n\x1a\n" + b"0" * 20
    r = client.post(f"/api/v1/transactions/{t['id']}/attachments", headers=h, files={"file": ("r.png", png, "image/png")})
    assert r.status_code == 201
    aid = r.json()["id"]
    assert client.get(f"/api/v1/attachments/{aid}", headers=h).content == png
    assert client.get(f"/api/v1/attachments/{aid}", headers=other).status_code == 404
    bad = client.post(f"/api/v1/transactions/{t['id']}/attachments", headers=h, files={"file": ("x.png", b"not a png", "image/png")})
    assert bad.status_code == 415
    exe = client.post(f"/api/v1/transactions/{t['id']}/attachments", headers=h, files={"file": ("x.exe", b"MZ", "application/x-msdownload")})
    assert exe.status_code == 415
    assert client.post(f"/api/v1/transactions/{t['id']}/attachments", headers=other, files={"file": ("r.png", png, "image/png")}).status_code == 404
    assert client.delete(f"/api/v1/transactions/{t['id']}", headers=h).status_code == 204
    assert list(tmp_path.iterdir()) == []  # file removed with the transaction


def test_budget_alert_and_email(client, monkeypatch):
    sent = []
    from app.jobs import scheduler
    monkeypatch.setattr(scheduler, "send_email", lambda to, subj, body: sent.append((to, body)))
    h = register(client)
    client.patch("/api/v1/auth/me", headers=h, json={"email_reminders": True})
    food = next(c["id"] for c in client.get("/api/v1/categories", headers=h).json() if c["name"].startswith("Food"))
    client.post("/api/v1/budgets", headers=h, json={"category_id": food, "amount": "100"})
    client.post("/api/v1/transactions", headers=h, json={"amount": "90", "date": str(date.today()), "category_id": food})
    with dbmod.SessionLocal() as db:
        run_jobs(db)
        run_jobs(db)  # deduped
    assert len(sent) == 1 and "80%" in sent[0][1]
    client.post("/api/v1/transactions", headers=h, json={"amount": "20", "date": str(date.today()), "category_id": food})
    with dbmod.SessionLocal() as db:
        run_jobs(db)
    assert len(sent) == 2 and "over budget" in sent[1][1]
