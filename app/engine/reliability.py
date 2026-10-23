"""Buyer reliability - verified transaction history theke, explainable."""
from ..i18n import t


def score_buyer(orders):
    """orders: buyer-er order list (dict). Verified = completed/cancelled/disputed status-wala."""
    completed = [o for o in orders if o.get("status") == "completed"]
    cancelled = [o for o in orders if o.get("status") == "cancelled" and o.get("cancelled_by") == "buyer"]
    disputed = [o for o in orders if o.get("dispute_status") in ("resolved_against_buyer", "resolved_split")]
    n_verified = len(completed) + len(cancelled)
    if n_verified < 5:
        return {"label": "limited_history", "label_text": t("rel.label.limited_history"), "score": None, "verified_transactions": n_verified,
                "reasons": [t("rel.limited")],
                "contestable": True}
    on_time = sum(1 for o in completed if o.get("payment_on_time", True))
    # Beta-smoothed rates (prior = 2 good / 1 bad)
    pay = (on_time + 2) / (len(completed) + 3)
    complete = (len(completed) + 2) / (n_verified + 3)
    dispute_pen = min(0.3, 0.1 * len(disputed) / max(1, len(completed)) * 3)
    score = round(100 * (0.5 * pay + 0.4 * complete + 0.1) - 100 * dispute_pen, 1)
    score = max(0.0, min(100.0, score))
    label = "high" if score >= 80 else "medium" if score >= 60 else "low"
    return {"label": label, "label_text": t("rel.label." + label), "score": score, "verified_transactions": n_verified,
            "reasons": [t("rel.ontime", ok=on_time, n=len(completed)), t("rel.cancel", n=len(cancelled)),
                        t("rel.dispute", n=len(disputed))],
            "contestable": True}


def payment_risk(rel):
    """Net-profit engine er jonno expected payment haircut (0..1)."""
    if rel.get("score") is None:
        return 0.04  # limited history: neutral, ektu conservative
    return round((100 - rel["score"]) / 100 * 0.25, 3)
