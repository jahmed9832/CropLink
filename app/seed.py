"""Demo data + demo accounts. SEED_DEMO=true hole startup-e (ekbar) chole."""
import logging
import os
import secrets
from datetime import date, timedelta

from . import auth
from .config import settings
from .db import new_id, now_iso

logger = logging.getLogger("croplink.seed")


async def _user(db, role, name, phone, district, password, org_type=None, uid=None):
    uid = uid or new_id(role)
    prof = {"id": uid, "name": name, "phone": phone, "org_type": org_type, "location": district, "language": "bn",
            "created_at": now_iso()}
    if role in ("farmer", "buyer"):
        await db.insert("farmers" if role == "farmer" else "buyers", prof)
    await db.insert("users", {"id": uid, "phone": phone, "role": role, "password_hash": auth.hash_password(password),
                              "created_at": now_iso()})
    return uid


async def seed_demo(db):
    is_render = bool(os.getenv("RENDER"))
    is_prod = (getattr(settings, "ENVIRONMENT", "development") == "production") or (os.getenv("ENVIRONMENT") == "production")
    allow_demo = getattr(settings, "ALLOW_DEMO_SEED", False) or (os.getenv("ALLOW_DEMO_SEED", "false").lower() == "true")

    if (is_render or is_prod) and not allow_demo:
        logger.warning("seed_demo refused: running on Render or production without ALLOW_DEMO_SEED=true")
        return {"seeded": False, "reason": "demo seeding refused in production/Render without ALLOW_DEMO_SEED=true"}

    demo_pw = getattr(settings, "DEMO_PASSWORD", None) or os.getenv("DEMO_PASSWORD")
    if not demo_pw:
        demo_pw = secrets.token_urlsafe(12)
        if not (is_render or is_prod):
            logger.info("Generated random DEMO_PASSWORD for local run: %s", demo_pw)
            print(f"Generated random DEMO_PASSWORD for local run: {demo_pw}")

    if await db.list("users", {"phone": "01700000001"}, 1):
        return {"seeded": False, "reason": "demo data already ache"}

    admin = await _user(db, "admin", "Demo Admin", "01700000003", "Dhaka", demo_pw)
    f1 = await _user(db, "farmer", "Rahim Mia", "01700000001", "Gazipur", demo_pw)
    f2 = await _user(db, "farmer", "Karim Uddin", "01700000011", "Gazipur", demo_pw)
    f3 = await _user(db, "farmer", "Salma Begum", "01700000012", "Mymensingh", demo_pw)
    b1 = await _user(db, "buyer", "Karwan Wholesale", "01700000002", "Dhaka", demo_pw, "wholesaler")
    b2 = await _user(db, "buyer", "Chattogram Hotel Supply", "01700000021", "Chattogram", demo_pw, "hotel")
    today = date.today()

    async def lot(fid, crop, kg, grade, loc, days_ago=1):
        d = {"id": new_id("lot"), "farmer_id": fid, "crop": crop, "quantity_kg": kg, "grade": grade, "location": loc,
             "harvest_date": (today - timedelta(days=days_ago)).isoformat(), "batch_id": None, "status": "open",
             "created_at": now_iso()}
        await db.insert("lots", d)
        return d

    l1 = await lot(f1, "tomato", 400, "A", "Gazipur")
    await lot(f2, "tomato", 400, "A", "Gazipur")
    await lot(f3, "tomato", 300, "B", "Mymensingh", 2)
    await lot(f1, "potato", 1000, "B", "Gazipur", 3)

    async def demand(bid, name, crop, kg, mn, grade, price, loc):
        d = {"id": new_id("demand"), "buyer_id": bid, "buyer_name": name, "crop": crop, "quantity_kg": kg,
             "min_quantity_kg": mn, "min_grade": grade, "price_per_kg": price, "location": loc,
             "max_distance_km": 300, "needed_by": (today + timedelta(days=4)).isoformat(), "buyer_pickup": False,
             "status": "open", "kind": "confirmed", "created_at": now_iso()}
        await db.insert("demands", d)
        return d

    d1 = await demand(b1, "Karwan Wholesale", "tomato", 1000, 800, "B", 95, "Dhaka")
    await demand(b1, "Karwan Wholesale", "tomato", 300, 300, "A", 98, "Dhaka")
    await demand(b2, "Chattogram Hotel Supply", "potato", 800, 500, "B", 38, "Chattogram")

    # buyer1-er verified history: 10 completed weekly orders -> reliability score + demand radar prediction
    for w in range(10):
        await db.insert("orders", {
            "id": new_id("order"), "demand_id": None, "buyer_id": b1, "crop": "tomato", "allocations": [],
            "agreed_price": 90, "batch_ids": [], "total_kg": 600 + 25 * (w % 4), "status": "completed",
            "payment": {"status": "released", "simulated": True}, "payment_on_time": w != 3, "dispute_status": None,
            "created_at": (today - timedelta(weeks=10 - w)).isoformat() + "T09:00:00+00:00", "demo": True})
    import hashlib
    import json
    batch_id = new_id("batch")
    batch_created_at = now_iso()
    batch_core = {
        "id": batch_id,
        "farmer_id": f1,
        "crop": "tomato",
        "quantity_kg": 400,
        "harvest_date": today.isoformat(),
        "grade": "A",
        "created_at": batch_created_at
    }
    batch_hash = hashlib.sha256(json.dumps(batch_core, sort_keys=True).encode()).hexdigest()
    await db.insert("batches", {
        "id": batch_id, "farmer_id": f1, "crop": "tomato", "quantity_kg": 400, "location": "Gazipur",
        "harvest_date": today.isoformat(), "grade": "A", "grade_confidence": 0.88, "photo_base64": None, "photo_url": None,
        "passport_hash": batch_hash, "created_at": batch_created_at})
    return {"seeded": True, "demo_password": demo_pw,
            "accounts": {"admin": "01700000003", "farmer": "01700000001", "farmer2": "01700000011", "farmer3": "01700000012",
                         "buyer": "01700000002", "buyer2": "01700000021"},
            "ids": {"admin": admin, "farmer": f1, "buyer": b1, "tomato_lot": l1["id"], "tomato_demand": d1["id"]}}
