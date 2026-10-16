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
    csv = "date,kind,amount,category,account,note,tags\n2025-01-05,expense,42.5,Pets,Wallet,Food,a;b\nbad,expense,x,,,,\n"
    r = client.post("/api/v1/transactions/import", headers=h, files={"file": ("t.csv", csv, "text/csv")}).json()
    assert r["created"] == 1 and len(r["errors"]) == 1
    out = client.get("/api/v1/transactions/export.csv", headers=h).text
    assert "Pets" in out and "a;b" in out
    assert client.get("/api/v1/transactions?tag=a", headers=h).json()["total"] == 1
    assert client.get("/api/v1/transactions?tag=zzz", headers=h).json()["total"] == 0
