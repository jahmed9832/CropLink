import pytest
from app.config import settings
from app.main import app, lifespan
from fastapi.testclient import TestClient
import hmac
import hashlib
import json
import base64
import time


def test_demo_login_returns_401_when_seed_demo_unset(client):
    # SEED_DEMO is false, so demo admin account 01700000003 should not exist
    res = client.post("/auth/login", json={"phone": "01700000003", "password": "demo1234"})
    assert res.status_code == 401


@pytest.mark.anyio
async def test_startup_raises_with_default_secret():
    old_env = settings.ENVIRONMENT
    old_sec = settings.JWT_SECRET
    try:
        settings.ENVIRONMENT = "production"
        settings.JWT_SECRET = "dev-only-change-me"
        with pytest.raises(RuntimeError) as exc_info:
            async with lifespan(app):
                pass
        assert "JWT_SECRET" in str(exc_info.value)

        # Also test short secret
        settings.JWT_SECRET = "short-secret"
        with pytest.raises(RuntimeError) as exc_info:
            async with lifespan(app):
                pass
        assert "JWT_SECRET" in str(exc_info.value)
    finally:
        settings.ENVIRONMENT = old_env
        settings.JWT_SECRET = old_sec


def test_anonymous_calls_denied(client, farmer_headers):
    # Anonymous calls to admin endpoints return 401
    endpoints = [
        ("POST", "/prices", {"crop": "tomato", "market": "Dhaka", "prices": []}),
        ("GET", "/dashboard/admin", None),
        ("POST", "/admin/seed-demo", None),
        ("POST", "/orders/dummy_order/dispute/resolve?outcome=resolved_for_buyer", None),
    ]

    for method, path, payload in endpoints:
        if method == "POST":
            res = client.post(path, json=payload if payload is not None else {})
        else:
            res = client.get(path)
        assert res.status_code == 401, f"Expected 401 for anonymous {method} {path}, got {res.status_code}"

    # Non-admin calls (e.g. farmer) return 403
    for method, path, payload in endpoints:
        if method == "POST":
            res = client.post(path, json=payload if payload is not None else {}, headers=farmer_headers)
        else:
            res = client.get(path, headers=farmer_headers)
        assert res.status_code == 403, f"Expected 403 for farmer {method} {path}, got {res.status_code}"


def test_token_signed_with_wrong_secret(client):
    # Create token signed with a bogus secret
    def b64(b):
        return base64.urlsafe_b64encode(b).rstrip(b"=").decode()

    head = b64(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    body = b64(json.dumps({"sub": "f_hacked", "role": "admin", "exp": int(time.time()) + 3600}).encode())
    sig = hmac.new(b"completely_wrong_secret_12345678901234", f"{head}.{body}".encode(), hashlib.sha256).digest()
    bad_token = f"{head}.{body}.{b64(sig)}"

    res = client.get("/auth/me", headers={"Authorization": f"Bearer {bad_token}"})
    assert res.status_code == 401
