import pytest


def test_invalid_values_return_422(client, farmer_auth, buyer_auth):
    farmer_headers = farmer_auth["headers"]
    farmer_id = farmer_auth["user_id"]
    buyer_headers = buyer_auth["headers"]
    buyer_id = buyer_auth["user_id"]

    # Negative quantity in lot
    resp = client.post("/lots", json={
        "farmer_id": farmer_id,
        "crop": "tomato",
        "quantity_kg": -10,
        "grade": "A",
        "location": {"district": "Bogura"}
    }, headers=farmer_headers)
    assert resp.status_code == 422

    # Invalid grade (not A, B, C)
    resp = client.post("/lots", json={
        "farmer_id": farmer_id,
        "crop": "tomato",
        "quantity_kg": 100,
        "grade": "Z",
        "location": {"district": "Bogura"}
    }, headers=farmer_headers)
    assert resp.status_code == 422

    # Lat/Lon out of range
    resp = client.post("/lots", json={
        "farmer_id": farmer_id,
        "crop": "tomato",
        "quantity_kg": 100,
        "grade": "A",
        "location": {"lat": 120.0, "lon": 50.0}
    }, headers=farmer_headers)
    assert resp.status_code == 422

    # Invalid ISO harvest_date
    resp = client.post("/lots", json={
        "farmer_id": farmer_id,
        "crop": "tomato",
        "quantity_kg": 100,
        "grade": "A",
        "harvest_date": "yesterday",
        "location": {"district": "Bogura"}
    }, headers=farmer_headers)
    assert resp.status_code == 422

    # min_quantity_kg > quantity_kg
    resp = client.post("/demands", json={
        "buyer_id": buyer_id,
        "crop": "tomato",
        "quantity_kg": 100,
        "min_quantity_kg": 200,
        "price_per_kg": 50,
        "location": {"district": "Dhaka"}
    }, headers=buyer_headers)
    assert resp.status_code == 422

    # commission_pct >= 100 in Decision
    resp = client.post("/decision/net-profit", json={
        "crop": "tomato",
        "quantity_kg": 100,
        "costs": {"commission_pct": 100.0}
    }, headers=farmer_headers)
    assert resp.status_code == 422

    # Negative hours or bad temp in loss
    resp = client.post("/loss/assess", json={
        "crop": "tomato",
        "hours_since_harvest": -5,
        "distance_km": 10
    }, headers=farmer_headers)
    assert resp.status_code == 422


def test_lowercase_grade_accepted_and_stored_as_uppercase(client, farmer_auth):
    farmer_headers = farmer_auth["headers"]
    farmer_id = farmer_auth["user_id"]

    resp = client.post("/lots", json={
        "farmer_id": farmer_id,
        "crop": "tomato",
        "quantity_kg": 100,
        "grade": "  a  ",
        "location": {"district": "Bogura"}
    }, headers=farmer_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["grade"] == "A"


def test_bad_grade_lot_does_not_break_pool_plan(client, farmer_auth, buyer_auth):
    # Direct DB injection or tolerant engine: even if a lot with bad grade 'Z' or None exists in DB,
    # /pool/plan should not raise 500 KeyError
    from app.main import db

    buyer_headers = buyer_auth["headers"]
    buyer_id = buyer_auth["user_id"]
    farmer_id = farmer_auth["user_id"]

    # Create demand
    d_resp = client.post("/demands", json={
        "buyer_id": buyer_id,
        "crop": "tomato",
        "quantity_kg": 500,
        "price_per_kg": 40,
        "location": {"district": "Dhaka"}
    }, headers=buyer_headers)
    assert d_resp.status_code == 200
    demand_id = d_resp.json()["id"]

    # Directly insert a lot with invalid/unexpected grade into DB
    import asyncio
    asyncio.run(db().insert("lots", {
        "id": "lot_bad_grade_test",
        "farmer_id": farmer_id,
        "crop": "tomato",
        "quantity_kg": 200,
        "grade": "Z",
        "status": "open",
        "location": {"district": "Dhaka"},
        "harvest_date": "2026-10-24"
    }))

    # Call /pool/plan
    resp = client.post("/pool/plan", json={"demand_id": demand_id}, headers=buyer_headers)
    assert resp.status_code == 200
    plan = resp.json()
    assert "allocations" in plan
