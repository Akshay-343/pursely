import os

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["RUN_SCHEDULER"] = "false"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool

from app.core import db as dbmod

# in-memory sqlite shared across connections
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
dbmod.engine = engine
dbmod.SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

from app.main import app  # noqa: E402
from app import models  # noqa: E402,F401


@pytest.fixture()
def client():
    dbmod.Base.metadata.drop_all(engine)
    dbmod.Base.metadata.create_all(engine)
    app.dependency_overrides[dbmod.get_db] = lambda: (yield from _session())
    with TestClient(app) as c:
        yield c


def _session():
    s = dbmod.SessionLocal()
    try:
        yield s
    finally:
        s.close()


def register(client, email="a@example.com"):
    r = client.post("/api/v1/auth/register", json={"email": email, "password": "password123"})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}
