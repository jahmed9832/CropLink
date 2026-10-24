import pytest
from unittest.mock import patch
from datetime import datetime
from app.engine.constants import dhaka_today, DHAKA_TZ
import app.seed as seed
from app.main import db

def test_pagination_and_limits(client, farmer_auth, buyer_auth):
    # Test limit validation (>200 should return 422)
    res = client.get("/lots?limit=201", headers=farmer_auth["headers"])
    assert res.status_code == 422

    res = client.get("/demands?limit=201", headers=buyer_auth["headers"])
    assert res.status_code == 422

    res = client.get("/orders?limit=201", headers=buyer_auth["headers"])
    assert res.status_code == 422

    res = client.get("/batches?limit=201", headers=farmer_auth["headers"])
    assert res.status_code == 422

    # Create multiple demands
    for i in range(3):
        client.post("/demands", json={
            "buyer_id": buyer_auth["user_id"],
            "crop": "potato",
            "quantity_kg": 100 + i * 10,
            "price_per_kg": 40,
            "min_grade": "C",
            "location": {"lat": 23.81, "lon": 90.41, "district": "Dhaka"}
        }, headers=buyer_auth["headers"])

    # Test skip and limit
    res_all = client.get("/demands?crop=potato&limit=3", headers=buyer_auth["headers"])
    assert res_all.status_code == 200
    items_all = res_all.json()
    assert len(items_all) >= 3

    res_page = client.get("/demands?crop=potato&skip=1&limit=2", headers=buyer_auth["headers"])
    assert res_page.status_code == 200
    items_page = res_page.json()
    assert len(items_page) == 2
    assert items_page[0]["id"] == items_all[1]["id"]

def test_orders_queried_by_allocation_farmer_id(client, farmer_auth, farmer2_auth, buyer_auth):
    # Setup lot for farmer 1
    l_res = client.post("/lots", json={
        "farmer_id": farmer_auth["user_id"],
        "crop": "chili",
        "quantity_kg": 50,
        "grade": "A",
        "location": {"lat": 23.81, "lon": 90.41, "district": "Dhaka"}
    }, headers=farmer_auth["headers"])
    lid = l_res.json()["id"]

    # Setup demand
    d_res = client.post("/demands", json={
        "buyer_id": buyer_auth["user_id"],
        "crop": "chili",
        "quantity_kg": 50,
        "price_per_kg": 120,
        "min_grade": "A",
        "location": {"lat": 23.81, "lon": 90.41, "district": "Dhaka"}
    }, headers=buyer_auth["headers"])
    did = d_res.json()["id"]

    # Create order allocated to farmer 1
    o_res = client.post("/orders", json={
        "demand_id": did,
        "agreed_price": 120,
        "allocations": [{"lot_id": lid, "allocated_kg": 50, "farmer_id": farmer_auth["user_id"]}]
    }, headers=buyer_auth["headers"])
    assert o_res.status_code == 200
    oid = o_res.json()["id"]

    # Farmer 1 list_orders should see it
    f1_orders = client.get("/orders", headers=farmer_auth["headers"]).json()
    assert any(o["id"] == oid for o in f1_orders)

    # Farmer 2 list_orders should NOT see it
    f2_orders = client.get("/orders", headers=farmer2_auth["headers"]).json()
    assert not any(o["id"] == oid for o in f2_orders)

    # Farmer 1 dashboard should include it in orders_by_status
    dash1 = client.get(f"/dashboard/farmer/{farmer_auth['user_id']}", headers=farmer_auth["headers"]).json()
    assert dash1["orders_by_status"].get("confirmed", 0) >= 1

def test_seed_batch_passport_hash_valid():
    import asyncio
    async def _test():
        await seed.seed_demo(db())
        batches = await db().list("batches", {"crop": "tomato"})
        assert len(batches) > 0
        import hashlib, json
        for b in batches:
            core = {k: b[k] for k in ("id", "farmer_id", "crop", "quantity_kg", "harvest_date", "grade", "created_at")}
            computed = hashlib.sha256(json.dumps(core, sort_keys=True).encode()).hexdigest()
            assert b["passport_hash"] == computed
    asyncio.run(_test())

def test_dhaka_today_timezone():
    now_dhaka = datetime.now(DHAKA_TZ).date()
    assert dhaka_today() == now_dhaka
