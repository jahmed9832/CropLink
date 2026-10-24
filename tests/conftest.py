import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import pytest
from fastapi.testclient import TestClient

TEST_JWT_SECRET = "0123456789abcdef0123456789abcdef01234567"  # 40 chars
ADMIN_PHONE = "01800000000"
ADMIN_PASSWORD = "test-admin-password-1234"

os.environ["MONGODB_URI"] = ""
os.environ["AUTH_REQUIRED"] = "true"
os.environ["JWT_SECRET"] = TEST_JWT_SECRET
os.environ["SEED_DEMO"] = "false"
os.environ["ALLOW_SYNTHETIC_DATA"] = "true"
os.environ["ADMIN_PHONE"] = ADMIN_PHONE
os.environ["ADMIN_PASSWORD"] = ADMIN_PASSWORD
os.environ["ENVIRONMENT"] = "development"

from app.config import settings
settings.MONGODB_URI = ""
settings.AUTH_REQUIRED = True
settings.JWT_SECRET = TEST_JWT_SECRET
settings.SEED_DEMO = False
settings.ALLOW_SYNTHETIC_DATA = True
settings.ADMIN_PHONE = ADMIN_PHONE
settings.ADMIN_PASSWORD = ADMIN_PASSWORD
settings.ENVIRONMENT = "development"

from app.main import app, STATE


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def admin_auth(client):
    res = client.post("/auth/login", json={"phone": ADMIN_PHONE, "password": ADMIN_PASSWORD})
    assert res.status_code == 200, f"Admin login failed: {res.text}"
    token = res.json()["token"]
    user_id = res.json()["user_id"]
    return {"Authorization": f"Bearer {token}", "user_id": user_id, "headers": {"Authorization": f"Bearer {token}"}}


@pytest.fixture(scope="session")
def admin_headers(admin_auth):
    return {"Authorization": admin_auth["Authorization"]}


@pytest.fixture(scope="session")
def farmer_auth(client):
    res = client.post("/auth/register", json={
        "name": "Test Farmer 1",
        "phone": "01711111111",
        "password": "farmer-password-123",
        "role": "farmer",
        "district": "Gazipur"
    })
    if res.status_code == 409:
        res = client.post("/auth/login", json={"phone": "01711111111", "password": "farmer-password-123"})
    assert res.status_code in (200, 201), f"Farmer registration failed: {res.text}"
    data = res.json()
    token = data["token"]
    user_id = data["user_id"]
    return {"Authorization": f"Bearer {token}", "user_id": user_id, "headers": {"Authorization": f"Bearer {token}"}}


@pytest.fixture(scope="session")
def farmer_headers(farmer_auth):
    return {"Authorization": farmer_auth["Authorization"]}


@pytest.fixture(scope="session")
def farmer2_auth(client):
    res = client.post("/auth/register", json={
        "name": "Test Farmer 2",
        "phone": "01722222222",
        "password": "farmer2-password-123",
        "role": "farmer",
        "district": "Gazipur"
    })
    if res.status_code == 409:
        res = client.post("/auth/login", json={"phone": "01722222222", "password": "farmer2-password-123"})
    assert res.status_code in (200, 201), f"Farmer 2 registration failed: {res.text}"
    data = res.json()
    token = data["token"]
    user_id = data["user_id"]
    return {"Authorization": f"Bearer {token}", "user_id": user_id, "headers": {"Authorization": f"Bearer {token}"}}


@pytest.fixture(scope="session")
def farmer2_headers(farmer2_auth):
    return {"Authorization": farmer2_auth["Authorization"]}


@pytest.fixture(scope="session")
def buyer_auth(client):
    res = client.post("/auth/register", json={
        "name": "Test Buyer 1",
        "phone": "01733333333",
        "password": "buyer-password-123",
        "role": "buyer",
        "district": "Dhaka",
        "org_type": "wholesaler"
    })
    if res.status_code == 409:
        res = client.post("/auth/login", json={"phone": "01733333333", "password": "buyer-password-123"})
    assert res.status_code in (200, 201), f"Buyer registration failed: {res.text}"
    data = res.json()
    token = data["token"]
    user_id = data["user_id"]
    return {"Authorization": f"Bearer {token}", "user_id": user_id, "headers": {"Authorization": f"Bearer {token}"}}


@pytest.fixture(scope="session")
def buyer_headers(buyer_auth):
    return {"Authorization": buyer_auth["Authorization"]}
