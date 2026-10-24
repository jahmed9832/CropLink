"""Demo data seeding script: registers authentic buyer and farmer accounts and seeds lots and demands.
Usage: python scripts/seed_demo.py https://<your-app>.onrender.com [API_KEY]
"""
import json
import sys
import urllib.request
import urllib.error

BASE = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://127.0.0.1:8000"
KEY = sys.argv[2] if len(sys.argv) > 2 else ""


def api_call(path, body, token=None):
    h = {"Content-Type": "application/json"}
    if KEY:
        h["X-API-Key"] = KEY
    if token:
        h["Authorization"] = "Bearer " + token
    req = urllib.request.Request(BASE + path, json.dumps(body).encode(), h)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode()
        print(f"Error {e.code} on {path}: {err_msg}")
        raise


def main():
    print(f"Seeding demo data on {BASE}...")

    # 1. Register Buyer
    buyer_res = api_call("/auth/register", {
        "name": "Karwan Wholesale",
        "phone": "01700000001",
        "password": "demo1234",
        "role": "buyer",
        "district": "Dhaka",
        "org_type": "wholesaler"
    })
    buyer_token = buyer_res["token"]
    buyer_id = buyer_res["user_id"]
    print(f"Created Buyer: {buyer_id}")

    # 2. Register Farmers and create Lots with their own tokens
    farmers = []
    for i in range(1, 4):
        f_res = api_call("/auth/register", {
            "name": f"Farmer {i}",
            "phone": f"0170000001{i}",
            "password": "demo1234",
            "role": "farmer",
            "district": "Gazipur"
        })
        f_token = f_res["token"]
        f_id = f_res["user_id"]
        farmers.append((f_id, f_token))
        lot = api_call("/lots", {
            "farmer_id": f_id,
            "crop": "tomato",
            "quantity_kg": 400,
            "grade": "A",
            "location": {"district": "Gazipur"}
        }, token=f_token)
        print(f"Created Lot {lot['id']} for Farmer {f_id}")

    # 3. Create Demand using Buyer's token
    demand = api_call("/demands", {
        "buyer_id": buyer_id,
        "crop": "tomato",
        "quantity_kg": 1000,
        "min_quantity_kg": 800,
        "min_grade": "B",
        "price_per_kg": 62,
        "location": {"district": "Dhaka"}
    }, token=buyer_token)
    print(f"Created Demand: {demand['id']}")

    # 4. Generate Pool Plan
    plan = api_call("/pool/plan", {"demand_id": demand["id"]}, token=buyer_token)
    print("Pool Plan generated successfully:")
    print(json.dumps(plan, indent=2)[:800])


if __name__ == "__main__":
    main()
