"""Cooperative supply pooling: compatible lots combine kore bulk order fulfil."""
from datetime import date

from ..i18n import t
from .constants import GRADE_RANK, haversine_km
from .netprofit import DEFAULT_COSTS


def _days(a, b):
    try:
        return abs((date.fromisoformat(a[:10]) - date.fromisoformat(b[:10])).days)
    except Exception:
        return 0


def plan_pool(demand, lots, costs=None, harvest_window_days=4, logistics_cost_per_kg_km=None):
    c = {**DEFAULT_COSTS, **(costs or {})}
    per_km = logistics_cost_per_kg_km or c["transport_per_kg_km"] * 0.7  # shared truck discount (assumption)
    need = float(demand["quantity_kg"])
    min_q = float(demand.get("min_quantity_kg", need))
    cands, rejected = [], []
    for lot in lots:
        why = []
        if lot.get("crop") != demand.get("crop"):
            why.append(t("pool.crop"))
        lot_grade_str = str(lot.get("grade", "")).upper()
        lot_rank = GRADE_RANK.get(lot_grade_str)
        demand_rank = GRADE_RANK.get(str(demand.get("min_grade", "C")).upper(), 1)
        if lot_rank is None:
            why.append("invalid_lot_grade")
        elif lot_rank < demand_rank:
            why.append(t("pool.grade"))
        dist = haversine_km(lot.get("location"), demand.get("location"))
        if dist > demand.get("max_distance_km", 300):
            why.append(t("pool.dist"))
        if demand.get("needed_by") and lot.get("harvest_date") and str(lot["harvest_date"])[:10] > str(demand["needed_by"])[:10]:
            why.append(t("pool.deadline"))
        if lot.get("status", "open") != "open":
            why.append(t("pool.notopen"))
        (rejected if why else cands).append({"lot": lot, "dist": dist, "why": why})

    # harvest-date compatibility: anchor = earliest candidate; window check
    if cands:
        anchor = min(x["lot"].get("harvest_date", "9999")[:10] for x in cands)
        keep = []
        for x in cands:
            if x["lot"].get("harvest_date") and anchor != "9999" and _days(x["lot"]["harvest_date"], anchor) > harvest_window_days:
                rejected.append({**x, "why": [t("pool.window", days=harvest_window_days)]})
            else:
                keep.append(x)
        cands = keep

    cands.sort(key=lambda x: (-GRADE_RANK.get(str(x["lot"].get("grade", "B")).upper(), 1), x["dist"]))
    remaining, alloc = need, []
    for x in cands:
        if remaining <= 0:
            break
        q = min(float(x["lot"]["quantity_kg"]), remaining)
        lot_hdate = x["lot"].get("harvest_date")
        age_days = (date.today() - date.fromisoformat(lot_hdate[:10])).days if lot_hdate else None
        alloc.append({
            "lot_id": x["lot"]["id"],
            "farmer_id": x["lot"]["farmer_id"],
            "allocated_kg": round(q, 1),
            "distance_km": x["dist"],
            "harvest_age_days": age_days,
            "status": "planned"
        })
        remaining -= q

    filled = need - max(0, remaining)
    total = sum(a["allocated_kg"] for a in alloc)
    price = float(demand["price_per_kg"])
    buyer_pickup = bool(demand.get("buyer_pickup", False))

    for a in alloc:
        share = a["allocated_kg"] / total if total else 0
        logistics = 0.0 if buyer_pickup else a["allocated_kg"] * a["distance_km"] * per_km
        gross = a["allocated_kg"] * price
        comm = gross * c["commission_pct"] / 100
        a.update({
            "share_pct": round(share * 100, 1),
            "logistics_share": round(logistics),
            "gross": round(gross),
            "commission": round(comm),
            "expected_payment": round(gross - logistics - comm)
        })

    feasible = (filled + 1e-6) >= min_q
    return {
        "demand_id": demand["id"],
        "feasible": feasible,
        "required_kg": need,
        "min_quantity_kg": min_q,
        "pooled_kg": round(filled, 1),
        "fill_rate_pct": round(filled / need * 100, 1) if need else 0,
        "shortfall_kg": round(max(0, min_q - filled), 1),
        "allocations": alloc,
        "rejected": [{"lot_id": r["lot"]["id"], "reasons": r["why"]} for r in rejected],
        "note": t("pool.note")
    }
