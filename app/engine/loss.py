"""Harvest-to-market loss prevention: urgency + delivery risk."""
from ..i18n import t
from .constants import SPOILAGE_PER_DAY


def assess(crop, hours_since_harvest, temp_c, distance_km, hours_to_deadline=None, transit_kmh=35):
    if hours_since_harvest < 0 or distance_km < 0 or (hours_to_deadline is not None and hours_to_deadline < 0):
        raise ValueError("hours_since_harvest, distance_km, and hours_to_deadline must be non-negative")
    rate = SPOILAGE_PER_DAY.get(crop, 0.02)
    heat = 1.0 + max(0.0, temp_c - 25) * 0.06
    transit_h = distance_km / transit_kmh
    total_days = max(0.0, (hours_since_harvest + transit_h) / 24)
    # Clamp rate * heat below 1 to prevent negative base in exponentiation producing complex numbers
    daily_decay = min(0.99, max(0.0, rate * heat))
    exp_loss = max(0.0, min(1.0, 1.0 - (1.0 - daily_decay) ** total_days))
    deadline_risk = 0.0
    if hours_to_deadline is not None:
        deadline_risk = 1.0 if transit_h > hours_to_deadline else max(0.0, 1 - (hours_to_deadline - transit_h) / 24)
    urgency = min(100, round(100 * (0.6 * min(1, rate * heat * 12) + 0.25 * min(1, exp_loss * 4) + 0.15 * deadline_risk)))
    level = "high" if urgency >= 65 else "medium" if urgency >= 35 else "low"
    adv = []
    if level == "high":
        adv.append(t("loss.high"))
    if temp_c >= 33:
        adv.append(t("loss.heat"))
    if deadline_risk >= 1:
        adv.append(t("loss.deadline"))
    return {
        "urgency_score": urgency,
        "risk_level": level,
        "expected_loss_pct": round(exp_loss * 100, 1),
        "transit_hours": round(transit_h, 1),
        "advice": adv,
        "assumptions": {"spoilage_per_day": rate, "heat_factor": round(heat, 2), "transit_kmh": transit_kmh}
    }
