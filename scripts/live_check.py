#!/usr/bin/env python3
"""AgriSphere backend: ek command-e shob test.

Use (IntelliJ terminal, .venv active):
    python scripts/live_check.py https://<your-app>.onrender.com        # Render
    python scripts/live_check.py http://127.0.0.1:8000                  # PC-te local server

Demo account (SEED_DEMO=true) lagbe: farmer 01700000001, buyer 01700000002, admin 01700000003, password demo1234.
Kono secret (MongoDB/JWT) lage na. Eta nijer data (lot, demand, order) toiri kore, tai demo data-te kichu notun entry jabe.
"""
import io
import json
import random
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

if len(sys.argv) < 2:
    sys.exit("Use: python live_check.py https://<your-app>.onrender.com")
BASE = sys.argv[1].rstrip("/")
PW = "demo1234"
BN = re.compile(r"[\u0980-\u09FF]")
results = []


def parse(raw):
    try:
        return json.loads(raw.decode("utf-8"))
    except Exception:
        return {"raw": raw.decode("utf-8", "replace")[:300]}


def call(method, path, body=None, token=None, lang=None, query=None, files=None, fields=None, timeout=100):
    url = BASE + path + ("?" + urllib.parse.urlencode(query) if query else "")
    headers = {"Accept": "application/json"}
    if lang:
        headers["Accept-Language"] = lang
    if token:
        headers["Authorization"] = "Bearer " + token
    data = None
    if files is not None:
        boundary = "----agri" + str(random.randint(10**9, 10**10))
        parts = []
        for k, v in (fields or {}).items():
            parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
        for k, (fn, content, ctype) in files.items():
            parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"; filename="{fn}"\r\nContent-Type: {ctype}\r\n\r\n'.encode() + content + b"\r\n")
        parts.append(f"--{boundary}--\r\n".encode())
        data = b"".join(parts)
        headers["Content-Type"] = "multipart/form-data; boundary=" + boundary
    elif body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    elif method in ("POST", "PUT"):
        data = b"{}"
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, parse(r.read())
    except urllib.error.HTTPError as e:
        return e.code, parse(e.read())
    except Exception as e:
        return 0, {"detail": f"{type(e).__name__}: {e}"}


def check(name, ok, hint=""):
    results.append((name, ok, hint))
    print(("  PASS  " if ok else "  FAIL  ") + name + ("" if ok else f"\n        -> {hint}"))
    return ok


def short(x, n=160):
    return json.dumps(x, ensure_ascii=False)[:n]


def is_bn(x): return bool(BN.search(str(x)))


def section(t): print(f"\n== {t}")


def login(phone):
    c, r = call("POST", "/auth/login", {"phone": phone, "password": PW})
    return (r.get("token"), r.get("user_id"), r.get("role")) if c == 200 else (None, None, c)


def make_image():
    try:
        from PIL import Image, ImageDraw
    except Exception:
        return None
    img = Image.new("RGB", (160, 160), (240, 240, 240))
    d = ImageDraw.Draw(img)
    d.ellipse([30, 30, 130, 130], fill=(200, 50, 40))
    d.ellipse([70, 60, 80, 70], fill=(60, 40, 20))
    buf = io.BytesIO()
    img.save(buf, "JPEG")
    return buf.getvalue()


# ------------------------------------------------------------------ 1. server
section("1. Server ar database")
ok = False
for i in range(3):
    c, h = call("GET", "/health", timeout=120)
    if c == 200:
        ok = True
        break
    print(f"  (server ghumiye chhilo, abar chesta {i + 1}/3 ...)")
check("Server chalu (/health 200)", ok, f"code={c} {short(h)}. Render-e Live ache ki dekhun, ba URL thik ache ki.")
if not ok:
    sys.exit("\nServer-i pawa jachhe na, baki test hobe na.")
check("Database = mongodb", h.get("database") == "mongodb",
      f"database='{h.get('database')}'. Render Environment-e MONGODB_URI ache ki, Atlas-e IP allow (0.0.0.0/0) ache ki dekhun. (Local-e memory thakle normal.)")
c, r = call("GET", "/")
check("Root page (/) 200", c == 200 and r.get("status") == "running", f"code={c}. Notun app folder upload hoyeche ki?")

# ------------------------------------------------------------------ 2. language basics
section("2. Bangla / English")
c, m_en = call("GET", "/meta", lang="en")
c2, m_bn = call("GET", "/meta", query={"lang": "bn"})
check("/meta Accept-Language: en", c == 200 and m_en.get("language") == "en", short(m_en, 120))
check("/meta ?lang=bn", c2 == 200 and m_bn.get("language") == "bn", short(m_bn, 120))
check("/meta-te fosholer Bangla naam (tomato = টমেটো)", m_bn.get("names", {}).get("crops", {}).get("tomato", {}).get("bn") == "টমেটো", "names nai: notun version deploy hoyeche ki?")

# ------------------------------------------------------------------ 3. login + roles
section("3. Login ar role")
ftok, fid, frole = login("01700000001")
btok, bid, brole = login("01700000002")
atok, aid, arole = login("01700000003")
check("Demo farmer login", bool(ftok) and frole == "farmer", f"code={frole}. Render-e SEED_DEMO=true dilen ki? (dile redeploy hoye logs-e 'seeded' hoy)")
check("Demo buyer login", bool(btok) and brole == "buyer", "SEED_DEMO=true lagbe")
check("Demo admin login", bool(atok) and arole == "admin", "SEED_DEMO=true lagbe")
if not (ftok and btok and atok):
    sys.exit("\nDemo account nai, baki test hobe na. Render-e SEED_DEMO=true diye redeploy korun.")
c, r = call("POST", "/auth/login", {"phone": "01700000001", "password": "wrong"}, lang="en")
check("Bhul password -> 401 (English message)", c == 401 and not is_bn(r.get("detail")), short(r))
c, r = call("POST", "/auth/login", {"phone": "01700000001", "password": "wrong"}, lang="bn")
check("Bhul password -> 401 (Bangla message)", c == 401 and is_bn(r.get("detail")), short(r))
c, r = call("GET", "/prices/today")
check("Token chhara -> 401", c == 401, f"code={c}")
phone = "0179" + str(random.randint(1000000, 9999999))
c, r = call("POST", "/auth/register", {"name": "Live Test", "phone": phone, "password": "test1234", "role": "farmer", "district": "Gazipur"})
check("Notun user register", c == 200 and r.get("token"), short(r))
if c == 200:
    c, r2 = call("PUT", "/auth/me", {"name": "Live Test 2"}, token=r["token"])
    check("Profile update (PUT /auth/me)", c == 200 and r2["profile"]["name"] == "Live Test 2", short(r2))
c, r = call("GET", f"/dashboard/buyer/{bid}", token=ftok)
check("Farmer onner (buyer) dashboard dekhte parbe na -> 403", c == 403, f"code={c}")
c, r = call("GET", "/dashboard/admin", token=ftok)
check("Farmer admin dashboard dekhte parbe na -> 403", c == 403, f"code={c}")

# ------------------------------------------------------------------ 4. decision engine + language
section("4. Main decision engine (duitei bhasha)")
body = {"crop": "tomato", "quantity_kg": 500, "grade": "A", "market": "Dhaka"}
c, d_en = call("POST", "/decision/net-profit", body, token=ftok, lang="en")
c2, d_bn = call("POST", "/decision/net-profit", body, token=ftok, lang="bn")
check("Decision (English) 200 + recommended", c == 200 and d_en.get("recommended") and len(d_en.get("options", [])) >= 3, short(d_en))
check("Decision English text-e Bangla nai", c == 200 and not any(is_bn(x) for x in d_en.get("explanation", []) + [d_en.get("disclaimer", "")]), short(d_en.get("explanation")))
check("Decision Bangla text Bangla-te", c2 == 200 and all(is_bn(x) for x in d_bn.get("explanation", [])) and is_bn(d_bn.get("disclaimer")), short(d_bn.get("explanation")))
check("Net income range (downside <= base <= best)", c == 200 and all(o["net"]["downside"] <= o["net"]["base"] <= o["net"]["best"] for o in d_en["options"]), "")
c, r = call("POST", "/decision/net-profit", dict(body, spoilage_per_day=0.002, temperature_c=25), token=ftok, lang="en")
check("Spoilage/temperature input edit kaj kore", c == 200 and r["assumptions"]["spoilage_per_day"] == 0.002, short(r.get("assumptions")))
c, r = call("POST", "/decision/net-profit", {"crop": "banana", "quantity_kg": 10}, token=ftok, lang="en")
check("Bhul crop -> 422", c == 422, f"code={c}")

# ------------------------------------------------------------------ 5. prices, forecast, alerts
section("5. Dam, forecast, alert")
c, r = call("GET", "/prices/today", token=ftok, query={"market": "Dhaka"})
check("/prices/today (7 foshol)", c == 200 and len(r.get("prices", [])) == 7, short(r))
c, r = call("GET", "/prices/history", token=ftok, query={"crop": "tomato", "market": "Dhaka", "days": 30})
check("/prices/history (chart data)", c == 200 and len(r.get("points", [])) >= 15, short(r, 100))
c, r = call("GET", "/forecast", token=ftok, query={"crop": "tomato", "market": "Dhaka"}, lang="bn")
check("/forecast low<=base<=high + Bangla note", c == 200 and r["h7"]["low"] <= r["h7"]["base"] <= r["h7"]["high"] and is_bn(r.get("note")), short(r, 120))
c, r = call("GET", "/alerts/scan", token=ftok, query={"spike_pct": 1, "forecast_pct": 1}, lang="en")
check("/alerts/scan", c == 200 and "alerts" in r, short(r, 100))
if c == 200 and r["alerts"]:
    a = r["alerts"][0]["alerts"][0]
    check("Alert-e message (en) + message_bn + message_en", not is_bn(a["message"]) and is_bn(a["message_bn"]) and a["message_en"], short(a))
c, r = call("POST", "/alerts/watch", {"farmer_id": fid, "crop": "tomato", "market": "Dhaka", "threshold_pct": 1}, token=ftok)
check("Crop watch", c == 200, short(r))
c, r = call("GET", f"/alerts/farmer/{fid}", token=ftok)
check("Farmer alerts", c == 200 and r.get("watching", 0) >= 1, short(r, 100))
c, r = call("POST", "/loss/assess", {"crop": "tomato", "hours_since_harvest": 40, "temperature_c": 36, "distance_km": 200, "hours_to_deadline": 2}, token=ftok, lang="bn")
check("Loss assess (Bangla advice)", c == 200 and r["advice"] and all(is_bn(x) for x in r["advice"]), short(r, 120))

# ------------------------------------------------------------------ 6. assistant + negotiation
section("6. Assistant ar dor-koshakoshi")
c, r = call("POST", "/assistant/chat", {"text": "৫০০ কেজি টমেটো এখন বিক্রি করব নাকি অপেক্ষা করব?"}, token=ftok, lang="bn")
check("Assistant: Bangla proshno -> Bangla uttor", c == 200 and is_bn(r.get("reply")), short(r))
c, r = call("POST", "/assistant/chat", {"text": "tomato price"}, token=ftok, lang="en")
check("Assistant: English proshno -> English uttor", c == 200 and r.get("reply") and not is_bn(r["reply"]), short(r))
c, r = call("POST", "/assistant/chat", {"text": "I have 200 kg tomato, buyer is giving 50 tk"}, token=ftok, lang="en")
check("Assistant: dor-koshakoshi (English)", c == 200 and "minimum" in r.get("reply", "").lower(), short(r))
c, r = call("POST", "/negotiation/counter-offer", {"crop": "tomato", "quantity_kg": 400, "grade": "A", "market": "Dhaka",
            "offers": [{"price_per_kg": 40, "distance_km": 30}, {"price_per_kg": 200, "distance_km": 30}], "production_cost_per_kg": 40}, token=ftok, lang="en")
o = r.get("offers", [{}, {}]) if c == 200 else [{}, {}]
check("Counter-offer: kom offer -> counter, beshi offer -> accept", c == 200 and o[0].get("action") == "counter" and o[1].get("action") == "accept", short(r, 150))
check("Draft message: message (en), message_bn (Bangla)", c == 200 and not is_bn(o[0]["draft_message"]) and is_bn(o[0]["draft_message_bn"]), "")

# ------------------------------------------------------------------ 7. full trade flow
section("7. Pura flow: lot -> demand -> pooling -> order -> delivery -> dispute -> payment")
tokens = [(ftok, fid)]
for ph in ("01700000011", "01700000012"):
    t, i, _ = login(ph)
    tokens.append((t, i))
lots = []
for t, i in tokens:
    c, r = call("POST", "/lots", {"farmer_id": i, "crop": "tomato", "quantity_kg": 400, "grade": "A", "location": {"district": "Gazipur"}}, token=t)
    lots.append(r.get("id") if c == 200 else None)
check("3 farmer 3ta lot toiri kore", all(lots), short(lots))
c, r = call("POST", "/lots", {"farmer_id": bid, "crop": "tomato", "quantity_kg": 10, "grade": "A", "location": {"district": "Gazipur"}}, token=ftok, lang="en")
check("Farmer onner id diye lot banate parbe na -> 403", c == 403, f"code={c}")
c, r = call("POST", "/demands", {"buyer_id": bid, "crop": "tomato", "quantity_kg": 1000, "min_quantity_kg": 800, "min_grade": "B", "price_per_kg": 95, "location": {"district": "Dhaka"}}, token=btok)
demand_id = r.get("id") if c == 200 else None
check("Buyer demand toiri kore", bool(demand_id), short(r))
c, r = call("GET", f"/lots/{lots[0]}/offers", token=ftok, lang="en")
check("Lot-er jonno buyer offer + fairness label", c == 200 and r and r[0].get("fairness", {}).get("label_text"), short(r, 150))
c, plan = call("POST", "/pool/plan", {"demand_id": demand_id}, token=btok, lang="en")
check("Pooling plan feasible", c == 200 and plan.get("feasible") and plan.get("pooled_kg", 0) >= 800, short(plan, 150))
img = make_image()
batch_id = None
if img:
    c, r = call("POST", "/batches/from-photo", token=ftok, files={"file": ("p.jpg", img, "image/jpeg")},
                fields={"farmer_id": fid, "crop": "tomato", "quantity_kg": 400, "district": "Gazipur"}, lang="en")
    batch_id = r.get("batch", {}).get("id") if c == 200 else None
    check("Photo -> grade -> batch (ek call-e)", bool(batch_id) and r["grading"]["grade"] in "ABC", short(r, 150))
    c, r = call("POST", "/grade", token=ftok, files={"file": ("p.jpg", img, "image/jpeg")}, lang="bn")
    check("/grade (Bangla note)", c == 200 and is_bn(r.get("model_note")), short(r, 120))
    c, r = call("POST", "/grade", token=ftok, files={"file": ("p.jpg", b"not an image", "image/jpeg")}, lang="en")
    check("Bhul image -> 422", c == 422, f"code={c}")
else:
    print("  SKIP  Photo test (Pillow nai; .venv active kore chalale hobe)")
c, order = call("POST", "/orders", {"demand_id": demand_id, "allocations": plan.get("allocations", []), "agreed_price": 95, "batch_ids": [batch_id] if batch_id else []}, token=btok)
oid = order.get("id") if c == 200 else None
check("Buyer order toiri kore", bool(oid), short(order))
c, r = call("GET", "/orders", token=btok)
check("Buyer nijer order list-e dekhe", c == 200 and any(x["id"] == oid for x in r), short(r, 100))
c, r = call("POST", f"/orders/{oid}/delivery", {"observed_grade": "B", "observed_weight_kg": 900, "proposed_deduction_pct": 8, "reason": "some spots"}, token=ftok)
check("Farmer delivery record korte parbe na -> 403", c == 403, f"code={c}")
c, r = call("POST", f"/orders/{oid}/delivery", {"observed_grade": "B", "observed_weight_kg": 900, "proposed_deduction_pct": 8, "reason": "some spots"}, token=btok, lang="en")
check("Buyer delivery record -> dispute evidence", c == 200 and r["evidence_report"]["needs_human_review"], short(r.get("evidence_report"), 150))
c, e_en = call("GET", f"/orders/{oid}/evidence", token=btok, lang="en")
c2, e_bn = call("GET", f"/orders/{oid}/evidence", token=btok, lang="bn")
check("Evidence report English-e", c == 200 and e_en["discrepancies"] and not any(is_bn(x) for x in e_en["discrepancies"]), short(e_en.get("discrepancies")))
check("Same evidence Bangla-te (bhasha bodlale text bodlay)", c2 == 200 and all(is_bn(x) for x in e_bn["discrepancies"]), short(e_bn.get("discrepancies")))
c, r = call("POST", f"/orders/{oid}/payment", {"action": "fund"}, token=ftok)
check("Farmer payment fund korte parbe na -> 403", c == 403, f"code={c}")
c, r = call("POST", f"/orders/{oid}/payment", {"action": "fund"}, token=btok)
check("Buyer payment fund (simulated)", c == 200 and r["payment"]["status"] == "funded", short(r.get("payment")))
c, r = call("POST", f"/orders/{oid}/dispute/resolve", token=btok, query={"outcome": "resolved_split"})
check("Buyer dispute resolve korte parbe na -> 403", c == 403, f"code={c}")
c, r = call("POST", f"/orders/{oid}/dispute/resolve", token=atok, query={"outcome": "resolved_split"})
check("Admin dispute resolve", c == 200 and r["dispute_status"] == "resolved_split", short(r, 100))
c, r = call("POST", f"/orders/{oid}/payment", {"action": "release"}, token=btok)
check("Buyer payment release -> order completed", c == 200 and r["status"] == "completed", short(r, 100))
c, r = call("GET", f"/buyers/{bid}/reliability", token=ftok, lang="en")
check("Buyer reliability score + label_text", c == 200 and r.get("label_text"), short(r, 150))

# ------------------------------------------------------------------ 8. dashboards, lists, admin
section("8. Dashboard, list, admin")
c, r = call("GET", f"/dashboard/farmer/{fid}", token=ftok)
check("Farmer dashboard", c == 200 and "lots_by_status" in r, short(r, 120))
c, r = call("GET", f"/dashboard/buyer/{bid}", token=btok)
check("Buyer dashboard", c == 200 and "reliability" in r, short(r, 120))
c, r = call("GET", "/dashboard/admin", token=atok)
check("Admin dashboard", c == 200 and "users_by_role" in r, short(r, 120))
c, r = call("GET", "/demand-radar", token=btok, query={"crop": "tomato"}, lang="en")
check("Demand radar (confirmed + predicted)", c == 200 and r[0]["predicted_demand"]["status"] in ("ok", "insufficient_data"), short(r, 150))
c, r = call("POST", f"/lots/{lots[1]}/withdraw", token=tokens[1][0])
check("Lot withdraw (nijer lot)", c in (200, 409), short(r, 100))
c, r = call("GET", "/lots/nope", token=ftok, lang="bn")
check("404 message Bangla-te", c == 404 and is_bn(r.get("detail")), short(r))
c, r = call("GET", "/lots/nope", token=ftok, lang="en")
check("404 message English-e", c == 404 and not is_bn(r.get("detail")), short(r))
c, r = call("POST", "/admin/seed-demo", token=atok)
check("Admin seed-demo (idempotent)", c == 200 and r.get("seeded") is False, short(r, 100))
c, r = call("GET", "/weather", token=ftok, query={"district": "Dhaka"})
print(f"  INFO  Weather: {'chalu' if r.get('available') else 'OPENWEATHER_API_KEY nai (optional, default 30C cholbe)'}")

# ------------------------------------------------------------------ summary
failed = [r for r in results if not r[1]]
print("\n" + "=" * 60)
print(f"Mot {len(results)}ta check: {len(results) - len(failed)} PASS, {len(failed)} FAIL")
if failed:
    print("FAIL howa check gulo:")
    for n, _, h in failed:
        print(f" - {n}")
    sys.exit(1)
print("SOB TEST PASS. Backend thik moto kaj korche.")
