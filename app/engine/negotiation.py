"""Voice Negotiation Assistant (backend part): minimum acceptable price + counter-offer draft.
Farmer nijer cost input dey; system draft dey, farmer review kore nijei pathay (auto pathay na)."""
from ..i18n import crop_name, grade_name, t
from .constants import GRADE_FACTOR
from .netprofit import DEFAULT_COSTS, TRANSIT_KMH, _spoil, decide
from .reliability import payment_risk


def min_price_for_target(crop, qty, target_net, km, costs, spoilage_per_day, heat, haircut, pickup=False):
    """Net(P) = P*qty*(1-spoil)*(1-haircut)*(1-comm) - transport - handling  =>  P ber kora."""
    c = {**DEFAULT_COSTS, **(costs or {})}
    sp = _spoil(crop, km / TRANSIT_KMH / 24 * heat, spoilage_per_day)
    fixed = (0 if pickup else qty * km * c["transport_per_kg_km"]) + qty * c["handling_per_kg"]
    comm_pct = min(99.99, max(0.0, c.get("commission_pct", 0)))
    denom = qty * (1 - sp) * (1 - haircut) * (1 - comm_pct / 100)
    if denom <= 0:
        return target_net + fixed
    return (target_net + fixed) / denom



def _draft(lang, crop, qty, grade, offer, counter, action):
    kw = dict(offer=f"{offer:.0f}", qty=f"{qty:.0f}", crop=crop_name(crop, lang), grade=grade_name(grade, lang))
    if action == "accept":
        return t("neg.accept_draft", lang, **kw)
    return t("neg.counter_draft", lang, counter=f"{counter:.0f}", **kw)


def counter_offers(crop, qty, grade, current_price, forecast, offers, costs=None, heat=1.0,
                   spoilage_per_day=None, margin_pct=0.0, production_cost_per_kg=None):
    c = {**DEFAULT_COSTS, **(costs or {})}
    base = decide(crop, qty, grade, current_price, forecast, None, c, heat, spoilage_per_day)
    alt = max(base["options"], key=lambda o: o["net"]["base"])
    target = alt["net"]["base"] * (1 + margin_pct / 100)
    floor_note = None
    if production_cost_per_kg:
        pc = qty * production_cost_per_kg
        if pc > target:
            target, floor_note = pc, t("neg.floor")
    fair = current_price * GRADE_FACTOR.get(grade, 1.0)
    results = []
    for o in offers:
        km_val = o.get("distance_km")
        km = float(km_val if km_val is not None else c["local_market_km"])
        risk = payment_risk(o.get("reliability", {"score": None}))
        mp = min_price_for_target(crop, qty, target, km, c, spoilage_per_day, heat, risk, bool(o.get("buyer_pickup")))
        offer = float(o["price_per_kg"])
        if offer >= mp and offer >= fair * 0.97:
            action, counter = "accept", offer
        else:
            counter = round(max(mp * 1.03, fair * 0.98, offer), 1)
            action = "accept" if counter <= offer else "counter"
        results.append({"buyer_id": o.get("buyer_id"), "buyer_name": o.get("buyer_name"), "offer_price": offer,
                        "minimum_acceptable_price": round(mp, 1), "below_minimum": offer < mp,
                        "market_reference_price": round(fair, 1), "action": action,
                        "suggested_counter_price": round(counter, 1),
                        "draft_message": _draft(None, crop, qty, grade, offer, counter, action),
                        "draft_message_bn": _draft("bn", crop, qty, grade, offer, counter, action),
                        "draft_message_en": _draft("en", crop, qty, grade, offer, counter, action),
                        "payment_risk_pct": round(risk * 100, 1)})
    local_min = min_price_for_target(crop, qty, target, c["local_market_km"], c, spoilage_per_day, heat, 0.0)
    return {"minimum_acceptable_price_per_kg": round(min(local_min, *[r["minimum_acceptable_price"] for r in results]), 1)
            if results else round(local_min, 1),
            "basis": {"best_alternative": alt["label"], "best_alternative_net": alt["net"]["base"],
                      "margin_pct": margin_pct, "note": floor_note},
            "offers": results,
            "disclaimer": t("neg.disclaimer")}
