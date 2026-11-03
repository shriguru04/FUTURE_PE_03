import os
import tempfile

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["AI_PROVIDER"] = "mock"
os.environ["SECRET_KEY"] = "test-secret-key-test-secret-key-1234"
os.environ["RATE_LIMIT_ENABLED"] = "false"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from app.core.db import Base, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.security import ratelimit  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    ratelimit.reset()
    yield


def make_client(email="a@example.com", role="business_owner"):
    c = TestClient(app)
    r = c.post("/api/v1/auth/register", json={"email": email, "password": "correct-horse-battery", "role": role})
    assert r.status_code == 201, r.text
    c.headers["X-CSRF-Token"] = c.cookies.get("csrf_token")
    return c


@pytest.fixture
def client():
    return make_client()


@pytest.fixture
def other():
    return make_client("b@example.com", "seo_professional")
