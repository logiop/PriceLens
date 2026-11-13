import os
import tempfile

# Point the app at an isolated test database BEFORE importing anything.
_TEST_DIR = tempfile.mkdtemp(prefix="pricelens-test-")
os.environ["PRICELENS_DATABASE_URL"] = f"sqlite:///{_TEST_DIR}/test.db"
os.environ["PRICELENS_SCHEDULER_ENABLED"] = "0"  # disable the background scheduler in tests
os.environ["PRICELENS_RATE_LIMIT_ENABLED"] = "0"  # avoid 429s in the suite
os.environ["PRICELENS_SECRET_KEY_FILE"] = f"{_TEST_DIR}/secret_key"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def _login(client, email: str, password: str = "demo1234") -> str:
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest.fixture()
def token(client):
    return _login(client, "demo@pricelens.it")


@pytest.fixture()
def auth(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def colleague_token(client):
    return _login(client, "collega@pricelens.it")
