import json
from datetime import date

import httpx
import pytest

from app.api import ai as ai_api
from app.core.config import settings
from app.services import ai
from tests.conftest import register


@pytest.fixture()
def groq(monkeypatch):
    """Fake Groq: records each request and answers with whatever the test puts in `reply`."""
    monkeypatch.setattr(settings, "groq_api_key", "test-key")
    ai_api._tips_cache.clear()
    ai_api.ai_limiter.reset()
    calls, reply = [], {"text": json.dumps({"summary": "Food is up.", "tips": [
        {"title": "Cook at home", "detail": "Food & Dining is 150.", "kind": "saving"},
        {"title": "Odd kind", "detail": "x", "kind": "bogus"}]})}

    def fake(messages, json_mode=False, max_tokens=900):
        calls.append(messages)
        return reply["text"]
    monkeypatch.setattr(ai, "_complete", fake)
    return calls, reply


def _spend(client, h):
    cat = next(c["id"] for c in client.get("/api/v1/categories", headers=h).json() if c["name"] == "Food & Dining")
    client.post("/api/v1/transactions", headers=h, json={"amount": "150", "date": str(date.today()), "category_id": cat, "note": "Swiggy"})


def test_ai_disabled_without_key(client):
    h = register(client)
    assert client.get("/api/v1/auth/config").json()["ai_enabled"] is False
    assert client.get("/api/v1/ai/tips", headers=h).status_code == 503
    assert client.post("/api/v1/ai/ask", headers=h, json={"question": "how do I save?"}).status_code == 503


def test_tips_cached_until_data_changes(client, groq):
    calls, _ = groq
    h = register(client)
    assert client.get("/api/v1/auth/config").json()["ai_enabled"] is True
    assert client.get("/api/v1/ai/tips", headers=h).json()["tips"] == []  # no data: no model call
    assert calls == []
    _spend(client, h)
    r = client.get("/api/v1/ai/tips", headers=h).json()
    assert r["summary"] == "Food is up." and [t["kind"] for t in r["tips"]] == ["saving", "saving"]
    client.get("/api/v1/ai/tips", headers=h)
    assert len(calls) == 1  # served from cache
    _spend(client, h)
    client.get("/api/v1/ai/tips", headers=h)
    assert len(calls) == 2  # new data, new tips
    # the model sees aggregates of this user's data, not their email
    sent = json.dumps(calls[-1])
    assert "swiggy" in sent and "a@example.com" not in sent


def test_ask_uses_only_own_data(client, groq):
    calls, reply = groq
    a, b = register(client, "a@example.com"), register(client, "b@example.com")
    _spend(client, a)
    reply["text"] = "Spend less on food."
    r = client.post("/api/v1/ai/ask", headers=b, json={"question": "How can I reduce spending?",
                                                         "history": [{"role": "assistant", "content": "Hi"}]})
    assert r.json() == {"answer": "Spend less on food."}
    assert "swiggy" not in json.dumps(calls[-1])
    assert calls[-1][-1] == {"role": "user", "content": "How can I reduce spending?"}
    assert client.post("/api/v1/ai/ask", headers=b, json={"question": "x" * 501}).status_code == 422


def test_bad_model_output_and_rate_limit(client, groq, monkeypatch):
    _, reply = groq
    h = register(client)
    _spend(client, h)
    reply["text"] = "not json"
    assert client.get("/api/v1/ai/tips", headers=h).status_code == 502
    monkeypatch.setattr(ai_api.ai_limiter, "limit", 2)
    ai_api.ai_limiter.reset()
    for _ in range(2):
        assert client.post("/api/v1/ai/ask", headers=h, json={"question": "tips?"}).status_code == 200
    assert client.post("/api/v1/ai/ask", headers=h, json={"question": "tips?"}).status_code == 429



def test_groq_429_is_retried_once(monkeypatch):
    monkeypatch.setattr(settings, "groq_api_key", "test-key")
    monkeypatch.setattr(ai.time, "sleep", lambda s: None)
    req = httpx.Request("POST", ai.GROQ_URL)
    replies = [httpx.Response(429, headers={"retry-after": "1"}, request=req),
               httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]}, request=req),
               httpx.Response(429, request=req), httpx.Response(429, request=req)]
    monkeypatch.setattr(ai.httpx, "post", lambda *a, **k: replies.pop(0))
    assert ai._complete([{"role": "user", "content": "hi"}]) == "ok"
    with pytest.raises(ai.AiUnavailable):
        ai._complete([{"role": "user", "content": "hi"}])  # second 429 in a row gives up
    assert replies == []
