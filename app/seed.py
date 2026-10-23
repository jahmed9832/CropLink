"""Demo data + demo accounts, jate frontend team khali app dekhe na ekdom. SEED_DEMO=true hole startup-e (ekbar) chole.
Demo login (password sobar: demo1234):  admin 01700000003 | farmer 01700000001 | buyer 01700000002"""
from datetime import date, timedelta

from . import auth
from .db import new_id, now_iso

PW = "demo1234"


async def _user(db, role, name, phone, district, org_type=None, uid=None):
    uid = uid or new_id(role)
    prof = {"id": uid, "name": name, "phone": phone, "org_type": org_type, "location": district, "language": "bn",
            "created_at": now_iso()}
    if role in ("farmer", "buyer"):
        await db.insert("farmers" if role == "farmer" else "buyers", prof)
    await db.insert("users", {"id": uid, "phone": phone, "role": role, "password_hash": auth.hash_password(PW),
                              "created_at": now_iso()})
    return uid


async def seed_demo(db):
    if await db.list("users", {"phone": "01700000001"}, 1):
        return {"seeded": False, "reason": "demo data already ache"}
    admin = await _user(db, "admin", "Demo Admin", "01700000003", "Dhaka")
    f1 = await _user(db, "farmer", "Rahim Mia", "01700000001", "Gazipur")
    f2 = await _user(db, "farmer", "Karim Uddin", "01700000011", "Gazipur")
    f3 = await _user(db, "farmer", "Salma Begum", "01700000012", "Mymensingh")
    b1 = await _user(db, "buyer", "Karwan Wholesale", "01700000002", "Dhaka", "wholesaler")
    b2 = await _user(db, "buyer", "Chattogram Hotel Supply", "01700000021", "Chattogram", "hotel")
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
    await db.insert("batches", {
        "id": new_id("batch"), "farmer_id": f1, "crop": "tomato", "quantity_kg": 400, "location": "Gazipur",
        "harvest_date": today.isoformat(), "grade": "A", "grade_confidence": 0.88, "photo_base64": None, "photo_url": None,
        "passport_hash": "demo", "created_at": now_iso()})
    return {"seeded": True, "demo_password": PW,
            "accounts": {"admin": "01700000003", "farmer": "01700000001", "farmer2": "01700000011", "farmer3": "01700000012",
                         "buyer": "01700000002", "buyer2": "01700000021"},
            "ids": {"admin": admin, "farmer": f1, "buyer": b1, "tomato_lot": l1["id"], "tomato_demand": d1["id"]}}
