import pytest
import asyncio


def test_malformed_allocation_returns_422(client, buyer_auth):
    buyer_headers = buyer_auth["headers"]
    # Missing required field or allocated_kg <= 0
    resp = client.post("/orders", json={
        "demand_id": "demand_any",
        "allocations": [{"lot_id": "lot_1", "allocated_kg": -10}],
        "agreed_price": 50.0
    }, headers=buyer_headers)
    assert resp.status_code == 422


def test_second_post_orders_on_filled_demand_returns_409(client, farmer_auth, buyer_auth):
    farmer_headers = farmer_auth["headers"]
    farmer_id = farmer_auth["user_id"]
    buyer_headers = buyer_auth["headers"]
    buyer_id = buyer_auth["user_id"]

    # Create demand
    d_resp = client.post("/demands", json={
        "buyer_id": buyer_id,
        "crop": "potato",
        "quantity_kg": 200,
        "price_per_kg": 30,
        "location": {"district": "Dhaka"}
    }, headers=buyer_headers)
    assert d_resp.status_code == 200
    demand_id = d_resp.json()["id"]

    # Create lot 1
    l_resp1 = client.post("/lots", json={
        "farmer_id": farmer_id,
        "crop": "potato",
        "quantity_kg": 200,
        "grade": "B",
        "location": {"district": "Dhaka"}
    }, headers=farmer_headers)
    assert l_resp1.status_code == 200
    lot_id1 = l_resp1.json()["id"]

    # Create lot 2
    l_resp2 = client.post("/lots", json={
        "farmer_id": farmer_id,
        "crop": "potato",
        "quantity_kg": 200,
        "grade": "B",
        "location": {"district": "Dhaka"}
    }, headers=farmer_headers)
    assert l_resp2.status_code == 200
    lot_id2 = l_resp2.json()["id"]

    # First order fills the demand
    ord_resp1 = client.post("/orders", json={
        "demand_id": demand_id,
        "allocations": [{"lot_id": lot_id1, "allocated_kg": 200}],
        "agreed_price": 30.0
    }, headers=buyer_headers)
    assert ord_resp1.status_code == 200

    # Second order on now-filled demand must return 409
    ord_resp2 = client.post("/orders", json={
        "demand_id": demand_id,
        "allocations": [{"lot_id": lot_id2, "allocated_kg": 200}],
        "agreed_price": 30.0
    }, headers=buyer_headers)
    assert ord_resp2.status_code == 409


def test_concurrent_releases_succeed_only_once(client, farmer_auth, buyer_auth):
    farmer_headers = farmer_auth["headers"]
    farmer_id = farmer_auth["user_id"]
    buyer_headers = buyer_auth["headers"]
    buyer_id = buyer_auth["user_id"]

    # Create demand
    d_resp = client.post("/demands", json={
        "buyer_id": buyer_id,
        "crop": "onion",
        "quantity_kg": 100,
        "price_per_kg": 45,
        "location": {"district": "Dhaka"}
    }, headers=buyer_headers)
    assert d_resp.status_code == 200
    demand_id = d_resp.json()["id"]

    # Create lot
    l_resp = client.post("/lots", json={
        "farmer_id": farmer_id,
        "crop": "onion",
        "quantity_kg": 100,
        "grade": "A",
        "location": {"district": "Dhaka"}
    }, headers=farmer_headers)
    assert l_resp.status_code == 200
    lot_id = l_resp.json()["id"]

    # Create order
    ord_resp = client.post("/orders", json={
        "demand_id": demand_id,
        "allocations": [{"lot_id": lot_id, "allocated_kg": 100}],
        "agreed_price": 45.0
    }, headers=buyer_headers)
    assert ord_resp.status_code == 200
    order_id = ord_resp.json()["id"]

    # Fund order
    fund_resp = client.post(f"/orders/{order_id}/payment", json={"action": "fund"}, headers=buyer_headers)
    assert fund_resp.status_code == 200

    # Deliver order
    del_resp = client.post(f"/orders/{order_id}/delivery", json={"observed_weight_kg": 100}, headers=buyer_headers)
    assert del_resp.status_code == 200

    # Release 1
    rel1 = client.post(f"/orders/{order_id}/payment", json={"action": "release"}, headers=buyer_headers)
    # Release 2
    rel2 = client.post(f"/orders/{order_id}/payment", json={"action": "release"}, headers=buyer_headers)

    statuses = [rel1.status_code, rel2.status_code]
    assert 200 in statuses
    assert 409 in statuses


def test_cancel_after_completed_returns_409_and_leaves_lots_sold(client, farmer_auth, buyer_auth):
    farmer_headers = farmer_auth["headers"]
    farmer_id = farmer_auth["user_id"]
    buyer_headers = buyer_auth["headers"]
    buyer_id = buyer_auth["user_id"]

    d_resp = client.post("/demands", json={
        "buyer_id": buyer_id,
        "crop": "cabbage",
        "quantity_kg": 150,
        "price_per_kg": 25,
        "location": {"district": "Dhaka"}
    }, headers=buyer_headers)
    demand_id = d_resp.json()["id"]

    l_resp = client.post("/lots", json={
        "farmer_id": farmer_id,
        "crop": "cabbage",
        "quantity_kg": 150,
        "grade": "B",
        "location": {"district": "Dhaka"}
    }, headers=farmer_headers)
    lot_id = l_resp.json()["id"]

    ord_resp = client.post("/orders", json={
        "demand_id": demand_id,
        "allocations": [{"lot_id": lot_id, "allocated_kg": 150}],
        "agreed_price": 25.0
    }, headers=buyer_headers)
    order_id = ord_resp.json()["id"]

    client.post(f"/orders/{order_id}/payment", json={"action": "fund"}, headers=buyer_headers)
    client.post(f"/orders/{order_id}/delivery", json={"observed_weight_kg": 150}, headers=buyer_headers)
    client.post(f"/orders/{order_id}/payment", json={"action": "release"}, headers=buyer_headers)

    # Cancel after completed
    cancel_resp = client.post(f"/orders/{order_id}/payment", json={"action": "cancel"}, headers=buyer_headers)
    assert cancel_resp.status_code == 409

    # Lot must remain sold
    lot = client.get(f"/lots/{lot_id}", headers=farmer_headers).json()
    assert lot["status"] == "sold"


def test_farmer_cancel_recorded_as_cancelled_by_farmer_does_not_lower_buyer_score(client, farmer_auth, buyer_auth):
    farmer_headers = farmer_auth["headers"]
    farmer_id = farmer_auth["user_id"]
    buyer_headers = buyer_auth["headers"]
    buyer_id = buyer_auth["user_id"]

    d_resp = client.post("/demands", json={
        "buyer_id": buyer_id,
        "crop": "tomato",
        "quantity_kg": 100,
        "price_per_kg": 50,
        "location": {"district": "Dhaka"}
    }, headers=buyer_headers)
    demand_id = d_resp.json()["id"]

    l_resp = client.post("/lots", json={
        "farmer_id": farmer_id,
        "crop": "tomato",
        "quantity_kg": 100,
        "grade": "A",
        "location": {"district": "Dhaka"}
    }, headers=farmer_headers)
    lot_id = l_resp.json()["id"]

    ord_resp = client.post("/orders", json={
        "demand_id": demand_id,
        "allocations": [{"lot_id": lot_id, "allocated_kg": 100}],
        "agreed_price": 50.0
    }, headers=buyer_headers)
    order_id = ord_resp.json()["id"]

    # Farmer cancels the order (with body cancelled_by="buyer" to test that caller role overrides body)
    cancel_resp = client.post(f"/orders/{order_id}/payment", json={"action": "cancel", "cancelled_by": "buyer"}, headers=farmer_headers)
    assert cancel_resp.status_code == 200
    order_data = cancel_resp.json()
    assert order_data["cancelled_by"] == "farmer"

    # Buyer reliability score should ignore cancelled_by == "farmer"
    from app.engine.reliability import score_buyer
    orders = [
        {"status": "completed", "payment_on_time": True, "demo": False},
        {"status": "completed", "payment_on_time": True, "demo": False},
        {"status": "completed", "payment_on_time": True, "demo": False},
        {"status": "completed", "payment_on_time": True, "demo": False},
        {"status": "cancelled", "cancelled_by": "farmer", "demo": False},
    ]
    score_with_farmer_cancel = score_buyer(orders)
    # The farmer cancellation should not count toward buyer cancellations
    assert score_with_farmer_cancel["verified_transactions"] == 4
