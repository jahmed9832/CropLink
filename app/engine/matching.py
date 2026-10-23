"""Rule-based eligibility + weighted ranking."""
from ..i18n import t
from .constants import GRADE_FACTOR, GRADE_RANK, haversine_km

W = {"price": 0.40, "distance": 0.20, "grade": 0.15, "reliability": 0.15, "timing": 0.10}


def fairness(offer_price, fair_price, grade):
    ref = fair_price * GRADE_FACTOR.get(grade, 1.0)
    ratio = offer_price / ref if ref else 1
    label = "below_fair" if ratio < 0.92 else "above_fair" if ratio > 1.08 else "fair"
    return {"label": label, "label_text": t("fair." + label), "ratio": round(ratio, 3), "reference_price": round(ref, 1)}


def eligible(lot, demand):
    reasons = []
    if lot["crop"] != demand["crop"]:
        reasons.append(t("pool.crop"))
    if GRADE_RANK[lot["grade"]] < GRADE_RANK[demand.get("min_grade", "C")]:
        reasons.append(t("pool.grade"))
    d = haversine_km(lot["location"], demand["location"])
    if d > demand.get("max_distance_km", 300):
        reasons.append(t("pool.dist"))
    return (not reasons), reasons, d


def rank_offers(lot, demands, fair_price, reliabilities):
    """lot: farmer harvest lot. demands: open buyer demands. reliabilities: {buyer_id: rel dict}."""
    out = []
    for d in demands:
        ok, reasons, dist = eligible(lot, d)
        if not ok:
            continue
        rel = reliabilities.get(d["buyer_id"], {"score": None, "label": "limited_history"})
        rel_s = 0.5 if rel.get("score") is None else rel["score"] / 100
        price_s = max(0.0, min(1.0, (d["price_per_kg"] / (fair_price * GRADE_FACTOR[lot["grade"]]) - 0.7) / 0.6))
        dist_s = max(0.0, 1 - dist / max(1, d.get("max_distance_km", 300)))
        grade_s = GRADE_RANK[lot["grade"]] / 3
        qty_ok = lot["quantity_kg"] >= d.get("min_quantity_kg", 0)
        timing_s = 1.0 if qty_ok else 0.4
        score = (W["price"] * price_s + W["distance"] * dist_s + W["grade"] * grade_s
                 + W["reliability"] * rel_s + W["timing"] * timing_s)
        out.append({"demand_id": d["id"], "buyer_id": d["buyer_id"], "buyer_name": d.get("buyer_name"),
                    "price_per_kg": d["price_per_kg"], "distance_km": dist,
                    "match_score": round(score * 100, 1), "reliability": rel,
                    "fairness": fairness(d["price_per_kg"], fair_price, lot["grade"]),
                    "needs_pooling": not qty_ok, "min_quantity_kg": d.get("min_quantity_kg", 0),
                    "buyer_pickup": d.get("buyer_pickup", False)})
    out.sort(key=lambda x: x["match_score"], reverse=True)
    return out
