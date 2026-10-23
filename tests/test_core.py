import asyncio, io, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import numpy as np
from app.db import MemoryDB
from app.engine import assistant, dispute, loss, matching, netprofit, pooling, reliability
from app.ml.forecaster import Forecaster
from app.ml.grader import Grader, synth_image


def test_forecast_and_decision():
    f = Forecaster()
    s = f.bundled_series("tomato", "Dhaka")
    fc = f.forecast("tomato", "Dhaka", s)
    assert fc["h7"]["low"] < fc["h7"]["base"] < fc["h7"]["high"]
    dec = netprofit.decide("tomato", 500, "A", fc["current_price"], fc,
                           offers=[{"buyer_id": "b1", "price_per_kg": fc["current_price"] * 1.1, "distance_km": 60,
                                    "reliability": {"score": None, "label": "limited_history"}}])
    assert dec["options"][0]["net"]["base"] >= dec["options"][-1]["net"]["base"]
    assert dec["recommended"] and dec["explanation"]
    print("decision ->", dec["recommended"], dec["explanation"][0])


def test_grader():
    g = Grader()
    rng = np.random.default_rng(99)
    ok = 0
    for grade in "ABC":
        for _ in range(20):
            buf = io.BytesIO(); synth_image(grade, rng).save(buf, "JPEG")
            ok += g.grade_bytes(buf.getvalue())["grade"] == grade
    print("grader jpeg acc", ok / 60)
    assert ok / 60 > 0.8
    blank = io.BytesIO(); __import__("PIL.Image", fromlist=["x"]).new("RGB", (50, 50), (240, 240, 240)).save(blank, "PNG")
    assert g.grade_bytes(blank.getvalue())["needs_manual_review"]


def test_pooling_matching_reliability_dispute_loss():
    demand = {"id": "d1", "buyer_id": "b1", "crop": "tomato", "quantity_kg": 1000, "min_quantity_kg": 800,
              "min_grade": "B", "price_per_kg": 62, "location": "Dhaka", "max_distance_km": 200}
    lots = [{"id": f"l{i}", "farmer_id": f"f{i}", "crop": "tomato", "quantity_kg": 400, "grade": "A",
             "location": "Gazipur", "harvest_date": "2026-10-20", "status": "open"} for i in range(3)]
    lots.append({"id": "bad", "farmer_id": "fx", "crop": "tomato", "quantity_kg": 300, "grade": "C",
                 "location": "Gazipur", "harvest_date": "2026-10-20"})
    plan = pooling.plan_pool(demand, lots)
    assert plan["feasible"] and plan["pooled_kg"] == 1000 and len(plan["allocations"]) == 3
    assert any(r["lot_id"] == "bad" for r in plan["rejected"])
    offers = matching.rank_offers({**lots[0], "quantity_kg": 400}, [demand], 60, {})
    assert offers and offers[0]["needs_pooling"]
    assert reliability.score_buyer([])["label"] == "limited_history"
    orders = [{"status": "completed", "payment_on_time": True}] * 8
    assert reliability.score_buyer(orders)["label"] == "high"
    rep = dispute.build_report({"grade": "A", "grade_confidence": .9, "quantity_kg": 100, "photo_base64": "x", "created_at": "t"},
                               {"id": "o1", "agreed_price": 60}, {"observed_grade": "B", "observed_weight_kg": 90, "proposed_deduction_pct": 10})
    assert rep["needs_human_review"] and len(rep["discrepancies"]) == 3
    assert loss.assess("tomato", 30, 35, 120)["risk_level"] in ("medium", "high")


def test_assistant():
    p = assistant.parse("৫০০ কেজি টমেটো এখন বিক্রি করব নাকি অপেক্ষা করব?")
    assert p == {"intent": "sell", "crop": "tomato", "quantity_kg": 500.0}
    assert assistant.parse("alu er dam koto")["intent"] == "price"


def test_memorydb():
    async def run():
        d = MemoryDB(); await d.insert("x", {"id": "1", "a": 1})
        assert (await d.update("x", "1", {"a": 2}))["a"] == 2
        assert len(await d.list("x", {"a": 2})) == 1
    asyncio.run(run())


if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"):
            f(); print("PASS", n)
