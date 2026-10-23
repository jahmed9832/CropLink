"""Predicted Buyer Demand: weekly completed-order volume theke simple exponential smoothing.
Data kom (<8 week) hole prediction dey na."""
from collections import defaultdict
from datetime import date

import numpy as np

from ..i18n import t

MIN_WEEKS = 8


def weekly_series(orders):
    by = defaultdict(float)
    for o in orders:
        try:
            y, w, _ = date.fromisoformat(o["created_at"][:10]).isocalendar()
        except Exception:
            continue
        by[(y, w)] += float(o.get("total_kg", 0))
    if not by:
        return []
    keys = sorted(by)
    first = date.fromisocalendar(keys[0][0], keys[0][1], 1)
    last = date.fromisocalendar(keys[-1][0], keys[-1][1], 1)
    out, d = [], first
    while d <= last:
        y, w, _ = d.isocalendar()
        out.append(by.get((y, w), 0.0))
        d = date.fromordinal(d.toordinal() + 7)
    return out


def predict(orders, alpha=0.5):
    s = weekly_series(orders)
    if len(s) < MIN_WEEKS:
        return {"status": "insufficient_data", "weeks_of_history": len(s), "required_weeks": MIN_WEEKS,
                "note": t("demand.short")}
    level, errs = s[0], []
    for x in s[1:]:
        errs.append(x - level)
        level = alpha * x + (1 - alpha) * level
    sd = float(np.std(errs)) if errs else 0.0
    return {"status": "ok", "method": "exponential_smoothing", "horizon": "next_week", "weeks_of_history": len(s),
            "predicted_kg": round(level), "low_kg": round(max(0, level - 1.28 * sd)), "high_kg": round(level + 1.28 * sd),
            "note": t("demand.ok")}
