import pytest
from app.engine.netprofit import decide
from app.engine.pooling import plan_pool
from app.engine.dispute import build_report
from app.engine.demand import weekly_series
from app.engine.alerts import compute as alert_compute


def test_h10a_price_rescaling_preserves_ordering():
    # Base forecast where wait has positive uplift
    forecast = {
        "current_price": 50.0,
        "h7": {"low": 52.0, "base": 58.0, "high": 62.0},
        "h14": {"low": 55.0, "base": 65.0, "high": 70.0}
    }
    dec_normal = decide("tomato", 1000, "B", 50.0, forecast)
    rec_normal = dec_normal["recommended"]

    # Supplying 30% higher price (65.0) rescales wait options proportionately
    dec_higher = decide("tomato", 1000, "B", 65.0, forecast)
    assert dec_higher["recommended"] == rec_normal
    # Verify rescaled flag in wait option
    wait_opt = next(o for o in dec_higher["options"] if o["id"] == "wait_7d")
    assert wait_opt["rescaled"] is True


def test_h10b_offer_volume_cap_and_min_quantity_pooling():
    forecast = {"current_price": 50.0}
    # Case 1: farmer has 100 kg, offer demands 50 kg max -> sellable capped at 50 kg
    offers = [{
        "buyer_id": "b1",
        "price_per_kg": 60.0,
        "quantity_kg": 50.0,
        "min_quantity_kg": 20.0,
    }]
    dec = decide("tomato", 100.0, "B", 50.0, forecast, offers=offers)
    opt = next(o for o in dec["options"] if o["id"] == "offer_b1")
    assert opt["sellable_kg"] == 50.0

    # Case 2: farmer has 50 kg, offer demands min_quantity_kg of 200 kg -> needs pooling
    offers_big = [{
        "buyer_id": "b2",
        "price_per_kg": 60.0,
        "quantity_kg": 500.0,
        "min_quantity_kg": 200.0,
    }]
    dec2 = decide("tomato", 50.0, "B", 50.0, forecast, offers=offers_big)
    opt2 = next(o for o in dec2["options"] if o["id"] == "offer_b2")
    assert opt2["needs_pooling"] is True
    assert opt2["sellable_kg"] == 0


def test_h10c_offers_default_distance_matches_local_market_km():
    forecast = {"current_price": 50.0}
    offers = [{"buyer_id": "b_nodist", "price_per_kg": 55.0}]
    dec = decide("tomato", 100.0, "B", 50.0, forecast, offers=offers)
    opt = next(o for o in dec["options"] if o["id"] == "offer_b_nodist")
    # Transport cost should be based on local_market_km (15 km by default)
    # 100 kg * 15 km * 0.02 BDT/kg/km = 30 BDT
    assert opt["breakdown"]["transport"] == 30


def test_h10e_sell_now_single_estimate():
    forecast = {"current_price": 50.0}
    dec = decide("tomato", 100.0, "B", 50.0, forecast)
    sell_now = next(o for o in dec["options"] if o["id"] == "sell_now")
    assert sell_now["single_estimate"] is True
    assert sell_now["net"]["downside"] == sell_now["net"]["base"] == sell_now["net"]["best"]


def test_m03_post_prices_series_ignored_flag(client, admin_auth):
    headers = admin_auth["headers"]
    # Ingest only 5 points (< 15 points) -> series_ignored: True
    points = [{"date": f"2026-10-{i+1:02d}", "price": 40.0 + i} for i in range(5)]
    resp = client.post("/prices", json={"crop": "onion", "market": "Khulna", "prices": points}, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["series_ignored"] is True


def test_m05_dispute_uses_order_total_kg_and_confidence_zero_is_low():
    batch = {"grade": "A", "grade_confidence": 0.0, "quantity_kg": 400.0, "created_at": "2026-10-24"}
    order = {"id": "ord_1", "total_kg": 1200.0, "agreed_price": 40.0}
    obs = {"observed_weight_kg": 1200.0, "observed_grade": "A"}

    # Delivered weight equals order total_kg (1200 kg), so NO weight discrepancy
    report = build_report(batch, order, obs)
    weight_items = [item for item in report.get("items", []) if item.get("key") == "disp.weight"]
    assert len(weight_items) == 0

    # grade_confidence == 0.0 must trigger low confidence note
    lowconf_items = [n for n in report.get("note_items", []) if n.get("key") == "disp.lowconf"]
    assert len(lowconf_items) > 0


def test_m06_pooling_buyer_pickup_no_logistics():
    demand = {
        "id": "dem_pickup",
        "crop": "tomato",
        "quantity_kg": 100.0,
        "price_per_kg": 50.0,
        "buyer_pickup": True,
        "location": {"district": "Dhaka"}
    }
    lots = [{
        "id": "lot_p",
        "farmer_id": "f_p",
        "crop": "tomato",
        "quantity_kg": 100.0,
        "grade": "B",
        "status": "open",
        "location": {"district": "Bogura"}
    }]
    plan = plan_pool(demand, lots)
    assert plan["feasible"] is True
    alloc = plan["allocations"][0]
    # logistics_share must be 0 because buyer_pickup is True
    assert alloc["logistics_share"] == 0


def test_m15_weekly_series_excludes_current_incomplete_week():
    from datetime import date
    current_iso = date.today().isoformat()
    past_iso = "2026-01-05"
    orders = [
        {"created_at": past_iso, "total_kg": 100.0, "demo": False},
        {"created_at": current_iso, "total_kg": 500.0, "demo": False}
    ]
    series = weekly_series(orders)
    # The current week's 500 kg must be excluded from completed historical weeks
    assert 500.0 not in series
