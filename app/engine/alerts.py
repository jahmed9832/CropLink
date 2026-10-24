"""Price-spike / forecast alerts. App eta periodically poll kore notification dekhabe.
Protiti alert-e `message` (request-er bhasha) + `message_bn` + `message_en` ashe."""
import numpy as np

from ..i18n import crop_name, market_name, t


def _msgs(key, crop, market=None, **kw):
    out = {}
    for lang in ("bn", "en"):
        extra = {"market": market_name(market, lang)} if market else {}
        out[lang] = t(key, lang, crop=crop_name(crop, lang), **extra, **kw)
    return {"message": t(key, crop=crop_name(crop), **({"market": market_name(market)} if market else {}), **kw),
            "message_bn": out["bn"], "message_en": out["en"]}


def compute(crop, market, forecast, series, spike_pct=10.0, forecast_pct=7.0):
    prices = [float(p) for _, p in series]
    cur = forecast["current_price"]
    avg30 = float(np.mean(prices[-30:])) if prices else 0.0
    if avg30 == 0 or cur == 0:
        return {"crop": crop, "market": market, "current_price": cur, "avg_30d": round(avg30, 2),
                "alerts": [], "has_alert": False, "skip_reason": "Zero price or zero 30-day average",
                "as_of": forecast.get("as_of")}
    out = []
    dev = (cur / avg30 - 1) * 100
    if dev >= spike_pct:
        out.append({"type": "price_spike", "severity": "high" if dev >= 20 else "medium", "change_pct": round(dev, 1),
                    **_msgs("alert.spike", crop, market, pct=f"{dev:.0f}")})
    elif dev <= -spike_pct:
        out.append({"type": "price_drop", "severity": "high" if dev <= -20 else "medium", "change_pct": round(dev, 1),
                    **_msgs("alert.drop", crop, market, pct=f"{abs(dev):.0f}")})
    for h, days in (("h7", 7), ("h14", 14)):
        ch = (forecast[h]["base"] / cur - 1) * 100
        if abs(ch) >= forecast_pct:
            up = ch > 0
            out.append({"type": "forecast_rise" if up else "forecast_fall", "horizon": h, "severity": "medium",
                        "change_pct": round(ch, 1), "range": [forecast[h]["low"], forecast[h]["base"], forecast[h]["high"]],
                        **_msgs("alert.fc_up" if up else "alert.fc_down", crop, None, pct=f"{abs(ch):.0f}", days=days)})
    return {"crop": crop, "market": market, "current_price": cur, "avg_30d": round(avg30, 2),
            "alerts": out, "has_alert": bool(out), "as_of": forecast["as_of"]}
