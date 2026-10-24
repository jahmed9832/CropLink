import pytest
from app.config import settings
from app.engine.reliability import score_buyer


def test_forecast_flag_off_returns_503(client, farmer_headers):
    old_flag = settings.ALLOW_SYNTHETIC_DATA
    try:
        settings.ALLOW_SYNTHETIC_DATA = False
        res = client.get("/forecast?crop=tomato&market=Dhaka", headers=farmer_headers)
        assert res.status_code == 503
        data = res.json()
        assert data.get("code") == "no_real_price_data"
    finally:
        settings.ALLOW_SYNTHETIC_DATA = old_flag


def test_forecast_flag_on_includes_synthetic_meta(client, farmer_headers):
    old_flag = settings.ALLOW_SYNTHETIC_DATA
    try:
        settings.ALLOW_SYNTHETIC_DATA = True
        res = client.get("/forecast?crop=tomato&market=Dhaka", headers=farmer_headers)
        assert res.status_code == 200
        data = res.json()
        assert data.get("is_synthetic") is True
        assert data.get("data_source") == "synthetic"
        assert "as_of" in data
        assert "data_age_days" in data
    finally:
        settings.ALLOW_SYNTHETIC_DATA = old_flag


def test_demo_orders_ignored_by_reliability():
    # 10 orders marked demo: True should be filtered out
    demo_orders = [
        {"status": "completed", "payment_on_time": True, "demo": True}
        for _ in range(10)
    ]
    res_demo = score_buyer(demo_orders)
    assert res_demo["label"] == "limited_history"
    assert res_demo["score"] is None
    assert res_demo["verified_transactions"] == 0

    # Real non-demo completed orders should be scored
    real_orders = [
        {"status": "completed", "payment_on_time": True}
        for _ in range(8)
    ]
    res_real = score_buyer(real_orders)
    assert res_real["label"] == "high"
    assert res_real["score"] is not None
    assert res_real["verified_transactions"] == 8
