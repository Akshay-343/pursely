import re
import socket
from datetime import timedelta

import pytest
from aiosmtpd.controller import Controller

from app.api import auth as auth_mod
from app.core import db as dbmod
from app.core.config import settings
from app.models import PasswordResetToken
from app.services import email as email_mod
from app.services.dates import utcnow
from tests.conftest import register

API = "/api/v1/auth"


@pytest.fixture()
def outbox(monkeypatch):
    sent = []
    monkeypatch.setattr(auth_mod, "send_email", lambda to, subject, body, html=None: sent.append((to, subject, body, html)))
    return sent


def _token_from(body: str) -> str:
    return re.search(r"reset-password\?token=([\w-]+)", body).group(1)


def test_welcome_email_on_signup(client, outbox):
    register(client, "new@example.com")
    assert len(outbox) == 1 and outbox[0][0] == "new@example.com" and "Welcome" in outbox[0][1]
    assert "<a href=" in outbox[0][3]


def test_forgot_and_reset_password_flow(client, outbox):
    old = register(client, "me@example.com")
    outbox.clear()
    # unknown email: identical response, nothing sent (no account enumeration)
    unknown = client.post(f"{API}/forgot-password", json={"email": "ghost@example.com"})
    known = client.post(f"{API}/forgot-password", json={"email": "me@example.com"})
    assert unknown.status_code == known.status_code == 202 and unknown.json() == known.json()
    assert [m[0] for m in outbox] == ["me@example.com"]
    token = _token_from(outbox[0][2])

    # the DB stores only a hash of the token
    with dbmod.SessionLocal() as db:
        row = db.query(PasswordResetToken).one()
        assert row.token_hash != token and token not in row.token_hash

    assert client.post(f"{API}/reset-password", json={"token": token, "password": "short"}).status_code == 422
    assert client.post(f"{API}/reset-password", json={"token": token, "password": "brand-new-pass"}).status_code == 204
    # single use
    assert client.post(f"{API}/reset-password", json={"token": token, "password": "another-pass1"}).status_code == 400
    assert any("changed" in m[1] for m in outbox)
    # old password no longer works, new one does
    assert client.post(f"{API}/login", data={"username": "me@example.com", "password": "password123"}).status_code == 401
    r = client.post(f"{API}/login", data={"username": "me@example.com", "password": "brand-new-pass"})
    assert r.status_code == 200
    # the session from before the reset is dead, the new one works
    assert client.get(f"{API}/me", headers=old).status_code == 401
    assert client.get(f"{API}/me", headers={"Authorization": f"Bearer {r.json()['access_token']}"}).status_code == 200


def test_reset_token_expiry_and_invalid(client, outbox):
    register(client, "me@example.com")
    outbox.clear()
    client.post(f"{API}/forgot-password", json={"email": "me@example.com"})
    token = _token_from(outbox[0][2])
    with dbmod.SessionLocal() as db:
        row = db.query(PasswordResetToken).one()
        row.expires_at = utcnow() - timedelta(minutes=1)
        db.commit()
    assert client.post(f"{API}/reset-password", json={"token": token, "password": "brand-new-pass"}).status_code == 400
    assert client.post(f"{API}/reset-password", json={"token": "x" * 43, "password": "brand-new-pass"}).status_code == 400


def test_forgot_password_is_capped_per_user(client, outbox):
    register(client, "me@example.com")
    outbox.clear()
    for _ in range(6):
        assert client.post(f"{API}/forgot-password", json={"email": "me@example.com"}).status_code == 202
    assert len(outbox) == settings.reset_max_per_hour


def test_second_reset_link_is_revoked_when_first_is_used(client, outbox):
    register(client, "me@example.com")
    outbox.clear()
    client.post(f"{API}/forgot-password", json={"email": "me@example.com"})
    client.post(f"{API}/forgot-password", json={"email": "me@example.com"})
    t1, t2 = (_token_from(m[2]) for m in outbox)
    assert client.post(f"{API}/reset-password", json={"token": t1, "password": "brand-new-pass"}).status_code == 204
    assert client.post(f"{API}/reset-password", json={"token": t2, "password": "attacker-pass1"}).status_code == 400


def test_login_rate_limit(client):
    register(client, "me@example.com")
    codes = [client.post(f"{API}/login", data={"username": "me@example.com", "password": "wrong-pass"}).status_code for _ in range(22)]
    assert codes[0] == 401 and codes[-1] == 429


# ---- Google sign-in -------------------------------------------------------------------------------------------------

def _google(monkeypatch, claims=None, error=None):
    monkeypatch.setattr(settings, "google_client_id", "test-client.apps.googleusercontent.com")

    def fake(token, request, audience):
        assert audience == "test-client.apps.googleusercontent.com"
        if error:
            raise error
        return claims
    monkeypatch.setattr(auth_mod.google_id_token, "verify_oauth2_token", fake)


CRED = "x" * 40


def test_google_signup_creates_account_and_sends_welcome(client, outbox, monkeypatch):
    _google(monkeypatch, {"sub": "g-1", "email": "Gina@Example.com", "email_verified": True})
    r = client.post(f"{API}/google", json={"credential": CRED})
    assert r.status_code == 200
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    me = client.get(f"{API}/me", headers=h).json()
    assert me["email"] == "gina@example.com" and me["has_password"] is False and me["google_linked"] is True
    assert len(client.get("/api/v1/categories", headers=h).json()) >= 5  # defaults seeded
    assert len(outbox) == 1 and "Welcome" in outbox[0][1]
    # signing in again reuses the account, no second welcome
    assert client.post(f"{API}/google", json={"credential": CRED}).status_code == 200
    assert len(outbox) == 1


def test_google_links_existing_password_account(client, outbox, monkeypatch):
    register(client, "me@example.com")
    _google(monkeypatch, {"sub": "g-2", "email": "me@example.com", "email_verified": True})
    assert client.post(f"{API}/google", json={"credential": CRED}).status_code == 200
    # still one account, password login still works
    assert client.post(f"{API}/login", data={"username": "me@example.com", "password": "password123"}).status_code == 200


def test_google_rejects_unverified_invalid_and_unconfigured(client, outbox, monkeypatch):
    _google(monkeypatch, {"sub": "g-3", "email": "x@example.com", "email_verified": False})
    assert client.post(f"{API}/google", json={"credential": CRED}).status_code == 401
    _google(monkeypatch, error=ValueError("bad token"))
    assert client.post(f"{API}/google", json={"credential": CRED}).status_code == 401
    monkeypatch.setattr(settings, "google_client_id", "")
    assert client.post(f"{API}/google", json={"credential": CRED}).status_code == 503
    assert client.get(f"{API}/config").json() == {"google_client_id": "", "email_enabled": False}


def test_google_only_user_can_set_a_password_via_reset(client, outbox, monkeypatch):
    _google(monkeypatch, {"sub": "g-4", "email": "gina@example.com", "email_verified": True})
    client.post(f"{API}/google", json={"credential": CRED})
    assert client.post(f"{API}/login", data={"username": "gina@example.com", "password": "anything123"}).status_code == 401
    outbox.clear()
    client.post(f"{API}/forgot-password", json={"email": "gina@example.com"})
    assert "signed up with Google" in outbox[0][2]
    token = _token_from(outbox[0][2])
    assert client.post(f"{API}/reset-password", json={"token": token, "password": "my-new-password"}).status_code == 204
    assert client.post(f"{API}/login", data={"username": "gina@example.com", "password": "my-new-password"}).status_code == 200


# ---- Real SMTP code path against a local mail server ------------------------------------------------------------------

class _Capture:
    def __init__(self):
        self.messages = []

    async def handle_DATA(self, server, session, envelope):
        self.messages.append(envelope)
        return "250 OK"


def test_send_email_over_smtp(monkeypatch):
    cap = _Capture()
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    ctl = Controller(cap, hostname="127.0.0.1", port=port)
    ctl.start()
    try:
        monkeypatch.setattr(settings, "smtp_host", "127.0.0.1")
        monkeypatch.setattr(settings, "smtp_port", port)
        monkeypatch.setattr(settings, "smtp_from", "Money Tracker <noreply@example.com>")
        monkeypatch.setattr(settings, "smtp_starttls", False)
        monkeypatch.setattr(settings, "smtp_user", "")
        assert email_mod.send_email("to@example.com", "Hi", "plain body", "<p>html body</p>") is True
    finally:
        ctl.stop()
    assert len(cap.messages) == 1
    raw = cap.messages[0].content.decode()
    assert "Subject: Hi" in raw and "plain body" in raw and "<p>html body</p>" in raw and "multipart/alternative" in raw
    assert cap.messages[0].rcpt_tos == ["to@example.com"]


def test_send_email_never_raises(monkeypatch):
    monkeypatch.setattr(settings, "smtp_host", "127.0.0.1")
    monkeypatch.setattr(settings, "smtp_port", 1)  # nothing listens here
    monkeypatch.setattr(settings, "smtp_from", "noreply@example.com")
    assert email_mod.send_email("to@example.com", "Hi", "body") is False
    monkeypatch.setattr(settings, "smtp_host", "")
    assert email_mod.send_email("to@example.com", "Hi", "body") is False
