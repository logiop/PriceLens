import os
import tempfile

# Point the app at an isolated test database BEFORE importing anything.
_TEST_DIR = tempfile.mkdtemp(prefix="pricelens-test-")
os.environ["PRICELENS_DATABASE_URL"] = f"sqlite:///{_TEST_DIR}/test.db"
os.environ["PRICELENS_SCHEDULER_ENABLED"] = "0"  # disable the background scheduler in tests

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def token(client):
    resp = client.post(
        "/api/auth/login",
        json={"email": "demo@pricelens.it", "password": "demo1234"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest.fixture()
def auth(token):
    return {"Authorization": f"Bearer {token}"}
