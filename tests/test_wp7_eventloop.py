import pytest
import asyncio


def test_login_rate_limit_returns_429(client):
    # Attempt 10 bad logins
    bad_phone = "01999999991"
    for _ in range(10):
        resp = client.post("/auth/login", json={"phone": bad_phone, "password": "wrong-password"})
        assert resp.status_code == 401

    # 11th attempt must return 429
    resp_rate_limited = client.post("/auth/login", json={"phone": bad_phone, "password": "wrong-password"})
    assert resp_rate_limited.status_code == 429


def test_duplicate_register_returns_409_and_no_orphan_profile(client):
    from app.main import db, AUTH_FAILURES
    AUTH_FAILURES.clear()

    dup_phone = "01999999992"
    # First registration
    resp1 = client.post("/auth/register", json={
        "name": "Dup User 1",
        "phone": dup_phone,
        "password": "valid-password-123",
        "role": "farmer"
    })
    assert resp1.status_code in (200, 201)

    # Second registration with same phone
    resp2 = client.post("/auth/register", json={
        "name": "Dup User 2",
        "phone": dup_phone,
        "password": "valid-password-123",
        "role": "farmer"
    })
    assert resp2.status_code == 409

    # Verify no orphan farmer profiles
    import asyncio
    farmers = asyncio.run(db().list("farmers", {"phone": dup_phone}))
    assert len(farmers) == 1
    users = asyncio.run(db().list("users", {"phone": dup_phone}))
    assert len(users) == 1


def test_weather_fallback_marked(client):
    # Test weather fallback response structure
    from app.weather import fetch_weather
    # Fetch weather for a dummy unknown location or force fallback
    from app.weather import _cache
    _cache.clear()
    
    # Simulate network failure or default fallback
    import unittest.mock as mock
    with mock.patch("urllib.request.urlopen", side_effect=Exception("Network down")):
        w = fetch_weather("Bogura")
        assert w["is_fallback"] is True
        assert w["source"] == "default_fallback"
        assert w["temperature_c"] == 30.0
