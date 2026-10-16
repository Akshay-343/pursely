from app.core import db as dbmod
from app.seed_demo import seed
from tests.conftest import register


def test_seed_demo_is_repeatable_and_isolated(client):
    other = register(client, "someone@example.com")
    with dbmod.SessionLocal() as s:
        seed(s)
        seed(s)  # second run resets instead of duplicating

    r = client.post("/api/v1/auth/login", data={"username": "demo@example.com", "password": "demo1234"})
    assert r.status_code == 200, r.text
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}

    assert client.get("/api/v1/transactions", headers=h).json()["total"] > 50
    assert len(client.get("/api/v1/subscriptions", headers=h).json()) == 5
    assert len(client.get("/api/v1/goals", headers=h).json()) == 3
    assert client.get("/api/v1/dashboard/summary", headers=h).status_code == 200

    # the other user's data is untouched and they see none of the demo data
    assert client.get("/api/v1/transactions", headers=other).json()["total"] == 0


def test_demo_login_only_in_demo_mode(client, monkeypatch):
    from app.core.config import settings

    assert client.get("/api/v1/auth/config").json()["demo"] is False
    assert client.post("/api/v1/auth/demo").status_code == 404

    monkeypatch.setattr(settings, "demo_mode", True)
    assert client.get("/api/v1/auth/config").json()["demo"] is True
    r = client.post("/api/v1/auth/demo")  # seeds on first use
    assert r.status_code == 200, r.text
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {r.json()['access_token']}"})
    assert me.json()["email"] == "demo@example.com"
