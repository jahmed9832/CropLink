"""Demo data dhukano (deploy-er por): python scripts/seed_demo.py https://<your-app>.onrender.com [API_KEY]"""
import json, sys, urllib.request

BASE = sys.argv[1].rstrip("/")
KEY = sys.argv[2] if len(sys.argv) > 2 else ""


TOKEN = ""


def post(path, body):
    h = {"Content-Type": "application/json", "X-API-Key": KEY}
    if TOKEN:
        h["Authorization"] = "Bearer " + TOKEN
    req = urllib.request.Request(BASE + path, json.dumps(body).encode(), h)
    return json.load(urllib.request.urlopen(req, timeout=60))


TOKEN = post("/auth/register", {"name": "Demo Admin", "phone": "01700000000", "password": "demo1234", "role": "buyer"})["token"]
buyer = post("/buyers", {"name": "Karwan Wholesale", "org_type": "wholesaler", "location": {"district": "Dhaka"}})
farmers = [post("/farmers", {"name": f"Farmer {i}", "location": {"district": "Gazipur"}}) for i in range(1, 4)]
for f in farmers:
    post("/lots", {"farmer_id": f["id"], "crop": "tomato", "quantity_kg": 400, "grade": "A",
                   "location": {"district": "Gazipur"}})
d = post("/demands", {"buyer_id": buyer["id"], "crop": "tomato", "quantity_kg": 1000, "min_quantity_kg": 800,
                      "min_grade": "B", "price_per_kg": 62, "location": {"district": "Dhaka"}})
print("demand:", d["id"])
print(json.dumps(post("/pool/plan", {"demand_id": d["id"]}), indent=2)[:800])
