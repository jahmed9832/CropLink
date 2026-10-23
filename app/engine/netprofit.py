"""MAIN DECISION ENGINE: sell now vs wait vs buyer offers, net proceeds hishab."""
from ..i18n import t
from .constants import GRADE_FACTOR, SPOILAGE_PER_DAY

DEFAULT_COSTS = {"transport_per_kg_km": 0.02, "handling_per_kg": 0.5,
                 "storage_per_kg_day": 0.3, "commission_pct": 2.0, "local_market_km": 15}
TRANSIT_KMH = 35.0


def _spoil(crop, days, rate=None):
    r = rate if rate is not None else SPOILAGE_PER_DAY.get(crop, 0.02)
    return 1 - (1 - r) ** max(0.0, days)


def _net(qty, price, gf, spoil, km, days_stored, c, payment_haircut=0.0, pickup=False):
    sellable = qty * (1 - spoil)
    revenue = sellable * price * gf * (1 - payment_haircut)
    transport = 0.0 if pickup else qty * km * c["transport_per_kg_km"]
    handling = qty * c["handling_per_kg"]
    storage = qty * days_stored * c["storage_per_kg_day"]
    commission = revenue * c["commission_pct"] / 100
    return round(revenue - transport - handling - storage - commission, 0), {
        "revenue": round(revenue), "transport": round(transport), "handling": round(handling),
        "storage": round(storage), "commission": round(commission), "spoilage_pct": round(spoil * 100, 1)}


def decide(crop, qty_kg, grade, current_price, forecast, offers=None, costs=None, heat_factor=1.0,
           spoilage_per_day=None):
    """
    forecast: {"h7": {"low","base","high"}, "h14": {...}} (price/kg, grade-B reference price)
    offers: [{"buyer_id","price_per_kg","distance_km","reliability":{...},"buyer_pickup":bool}]
    """
    c = {**DEFAULT_COSTS, **(costs or {})}

    def _sp(days):
        return _spoil(crop, days, spoilage_per_day)

    gf = GRADE_FACTOR.get(grade, 1.0)
    km_local = c["local_market_km"]
    options = []

    def add(opt_id, label, kind, scen, meta=None):
        options.append({"id": opt_id, "label": label, "kind": kind, "net": scen, **(meta or {})})

    # --- Sell now (local market)
    sp = _sp(km_local / TRANSIT_KMH / 24 * heat_factor)
    nets = {}
    for s in ("downside", "base", "best"):
        nets[s], br = _net(qty_kg, current_price, gf, sp, km_local, 0, c)
    add("sell_now", t("opt.sell_now"), "market", nets, {"breakdown": br})

    # --- Wait 7 / 14 days
    for days, key in ((7, "h7"), (14, "h14")):
        f = forecast.get(key)
        if not f:
            continue
        sp = _sp(days * heat_factor + km_local / TRANSIT_KMH / 24)
        nets = {}
        for s, k in (("downside", "low"), ("base", "base"), ("best", "high")):
            nets[s], br = _net(qty_kg, f[k], gf, sp, km_local, days, c)
        add(f"wait_{days}d", t("opt.wait", days=days), "wait", nets,
            {"breakdown": br, "forecast_price_range": [f["low"], f["base"], f["high"]]})

    # --- Buyer offers
    for o in offers or []:
        km = float(o.get("distance_km", 0))
        sp = _sp(km / TRANSIT_KMH / 24 * heat_factor)
        from .reliability import payment_risk
        risk = payment_risk(o.get("reliability", {"score": None}))
        nets = {}
        for s, hm in (("downside", 2.0), ("base", 1.0), ("best", 0.5)):
            nets[s], br = _net(qty_kg, float(o["price_per_kg"]), 1.0, sp, km, 0, c,
                               payment_haircut=risk * hm, pickup=bool(o.get("buyer_pickup")))
        add(f"offer_{o.get('demand_id') or o.get('buyer_id')}",
            t("opt.offer", name=o.get("buyer_name") or o.get("buyer_id") or "", price=o["price_per_kg"]), "offer", nets,
            {"breakdown": br, "payment_risk_pct": round(risk * 100, 1),
             "reliability_label": o.get("reliability", {}).get("label", "limited_history"),
             "demand_id": o.get("demand_id"), "buyer_id": o.get("buyer_id")})

    options.sort(key=lambda x: x["net"]["base"], reverse=True)
    best = options[0]
    safest = max(options, key=lambda x: x["net"]["downside"])
    now = next(o for o in options if o["id"] == "sell_now")
    uplift = round((best["net"]["base"] - now["net"]["base"]) / max(1, abs(now["net"]["base"])) * 100, 1)

    f0 = lambda x: f"{x:.0f}"
    why = [t("dec.best", label=best["label"], base=f0(best["net"]["base"]), low=f0(best["net"]["downside"]),
             high=f0(best["net"]["best"]))]
    if best["id"] != "sell_now":
        why.append(t("dec.uplift", pct=uplift))
    if safest["id"] != best["id"]:
        why.append(t("dec.safest", label=safest["label"], low=f0(safest["net"]["downside"])))
    if best["kind"] == "wait":
        why.append(t("dec.wait_note"))
    return {"recommended": best["id"], "safest": safest["id"], "uplift_vs_sell_now_pct": uplift,
            "options": options, "explanation": why,
            "assumptions": {"costs": c, "grade": grade, "grade_factor": gf, "current_price": current_price,
                            "spoilage_per_day": spoilage_per_day if spoilage_per_day is not None else SPOILAGE_PER_DAY.get(crop), "heat_factor": heat_factor},
            "disclaimer": t("dec.disclaimer")}
