import pytest
from app.engine.constants import CROPS

def test_pooling_contract(client, farmer_auth, buyer_auth):
    # Create demand
    d_res = client.post("/demands", json={
        "buyer_id": buyer_auth["user_id"],
        "crop": "tomato",
        "quantity_kg": 600,
        "min_quantity_kg": 200,
        "price_per_kg": 80,
        "min_grade": "B",
        "location": {"lat": 23.81, "lon": 90.41, "district": "Dhaka"}
    }, headers=buyer_auth["headers"])
    assert d_res.status_code == 200
    demand_id = d_res.json()["id"]

    # Check /demands returns expected keys
    demands_res = client.get("/demands", headers=buyer_auth["headers"])
    assert demands_res.status_code == 200
    demands = demands_res.json()
    assert len(demands) > 0
    d = demands[0]
    assert "id" in d
    assert "crop" in d
    assert "price_per_kg" in d
    assert "min_grade" in d
    assert "location" in d

    # Create lots
    client.post("/lots", json={
        "farmer_id": farmer_auth["user_id"],
        "crop": "tomato",
        "quantity_kg": 400,
        "grade": "A",
        "location": {"lat": 23.82, "lon": 90.42, "district": "Dhaka"}
    }, headers=farmer_auth["headers"])

    # Test /pool/plan contract
    plan_res = client.post("/pool/plan", json={"demand_id": demand_id}, headers=farmer_auth["headers"])
    assert plan_res.status_code == 200
    plan = plan_res.json()
    assert "pooled_kg" in plan
    assert "required_kg" in plan
    assert "fill_rate_pct" in plan
    assert "allocations" in plan
    assert isinstance(plan["allocations"], list)
    if plan["allocations"]:
        alloc = plan["allocations"][0]
        assert "farmer_id" in alloc
        assert "allocated_kg" in alloc
        assert "expected_payment" in alloc
        assert "logistics_share" in alloc

def test_orders_and_evidence_contract(client, farmer_auth, buyer_auth):
    # Setup demand and lot
    d_res = client.post("/demands", json={
        "buyer_id": buyer_auth["user_id"],
        "crop": "tomato", "quantity_kg": 500, "price_per_kg": 75, "min_grade": "B",
        "location": {"lat": 23.81, "lon": 90.41, "district": "Dhaka"}
    }, headers=buyer_auth["headers"])
    did = d_res.json()["id"]

    l_res = client.post("/lots", json={
        "farmer_id": farmer_auth["user_id"],
        "crop": "tomato", "quantity_kg": 500, "grade": "B",
        "location": {"lat": 23.81, "lon": 90.41, "district": "Dhaka"}
    }, headers=farmer_auth["headers"])
    lid = l_res.json()["id"]

    # Create order
    o_res = client.post("/orders", json={
        "demand_id": did,
        "agreed_price": 75,
        "allocations": [{"lot_id": lid, "allocated_kg": 500, "farmer_id": farmer_auth["user_id"]}]
    }, headers=buyer_auth["headers"])
    assert o_res.status_code == 200
    oid = o_res.json()["id"]

    # Check /orders contract
    orders_res = client.get("/orders", headers=buyer_auth["headers"])
    assert orders_res.status_code == 200
    orders = orders_res.json()
    o = next(item for item in orders if item["id"] == oid)
    assert "id" in o
    assert "total_kg" in o
    assert "agreed_price" in o
    assert "allocations" in o
    assert "status" in o

    # Check 404 on unrecorded evidence
    ev_404 = client.get(f"/orders/{oid}/evidence", headers=buyer_auth["headers"])
    assert ev_404.status_code == 404

    # Record delivery
    deliv_res = client.post(f"/orders/{oid}/delivery", json={
        "observed_grade": "B",
        "observed_weight_kg": 490,
        "proposed_deduction_pct": 2.0,
        "reason": "Slight transit shrinkage"
    }, headers=buyer_auth["headers"])
    assert deliv_res.status_code == 200

    # Check /evidence contract
    ev_res = client.get(f"/orders/{oid}/evidence", headers=buyer_auth["headers"])
    assert ev_res.status_code == 200
    ev = ev_res.json()
    assert "pre_sale" in ev
    assert "at_delivery" in ev
    assert "discrepancies" in ev
    assert "notes" in ev
    assert "statement" in ev

def test_assistant_and_negotiation_contract(client, farmer_headers):
    # Test negotiation counter-offer contract
    neg_res = client.post("/negotiation/counter-offer", json={
        "crop": "tomato",
        "quantity_kg": 500,
        "production_cost_per_kg": 45,
        "offers": [{"price_per_kg": 50}]
    }, headers=farmer_headers)
    assert neg_res.status_code == 200
    neg = neg_res.json()
    assert "minimum_acceptable_price_per_kg" in neg
    assert "offers" in neg
    assert len(neg["offers"]) > 0
    off = neg["offers"][0]
    assert "action" in off
    assert "suggested_counter_price" in off
    assert "draft_message_bn" in off
    assert "draft_message_en" in off

    # Test /assistant/chat contract
    chat_res = client.post("/assistant/chat", json={"text": "hello"}, headers=farmer_headers)
    assert chat_res.status_code == 200
    chat = chat_res.json()
    assert "reply" in chat
    assert "source" in chat
    assert "parsed" in chat

def test_market_prices_and_forecast_contract(client, farmer_headers):
    # Test /forecast contract
    fc_res = client.get("/forecast?crop=tomato&market=Dhaka", headers=farmer_headers)
    assert fc_res.status_code == 200
    fc = fc_res.json()
    assert "current_price" in fc
    assert "h7" in fc
    assert "h14" in fc
    assert "trend" in fc
    assert "data_source" in fc
    assert "is_synthetic" in fc
    assert "data_age_days" in fc

    # Test /prices/today contract
    tp_res = client.get("/prices/today?market=Dhaka", headers=farmer_headers)
    assert tp_res.status_code == 200
    tp = tp_res.json()
    assert "prices" in tp
    assert isinstance(tp["prices"], list)

def test_auth_me_contract(client, farmer_headers):
    me_res = client.get("/auth/me", headers=farmer_headers)
    assert me_res.status_code == 200
    me = me_res.json()
    assert "user_id" in me
    assert "role" in me
    assert "profile" in me
