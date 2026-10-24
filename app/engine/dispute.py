"""Quality dispute evidence report. Kono party-ke automatically doshi bole na - human review lage."""
from ..i18n import grade_name, t
from .constants import GRADE_FACTOR


def build_report(batch, order, observation, low_conf_threshold=0.6):
    pre_weight = order.get("total_kg") or batch.get("quantity_kg")
    pre = {
        "grade": batch.get("grade"),
        "confidence": batch.get("grade_confidence"),
        "weight_kg": pre_weight,
        "agreed_price": order.get("agreed_price"),
        "photo_recorded": bool(batch.get("photo_base64") or batch.get("photo_url")),
        "recorded_at": batch.get("created_at")
    }
    post = {
        "grade": observation.get("observed_grade"),
        "weight_kg": observation.get("observed_weight_kg"),
        "proposed_deduction_pct": observation.get("proposed_deduction_pct", 0),
        "reason": observation.get("reason", "")
    }
    items = []   # code + params save hoy; lekha porar shomoy request-er bhashay toiri hoy
    if pre["weight_kg"] and post["weight_kg"]:
        diff = (post["weight_kg"] - pre["weight_kg"]) / pre["weight_kg"] * 100
        if abs(diff) > 3:
            items.append({"key": "disp.weight", "params": {"pct": f"{diff:+.1f}"}})
    if pre["grade"] and post["grade"] and str(pre["grade"]).upper() != str(post["grade"]).upper():
        pre_factor = GRADE_FACTOR.get(str(pre["grade"]).upper(), 1.0)
        post_factor = GRADE_FACTOR.get(str(post["grade"]).upper(), 1.0)
        gdiff = (post_factor / pre_factor - 1) * 100
        items.append({"key": "disp.grade", "params": {"pre": pre["grade"], "post": post["grade"], "diff": f"{gdiff:+.0f}"}})
    if post["proposed_deduction_pct"] and post["proposed_deduction_pct"] > 0:
        items.append({"key": "disp.deduction", "params": {"pct": post["proposed_deduction_pct"]}})
    needs_review = bool(items)
    note_items = []

    conf = pre.get("confidence")
    if conf is None or conf < low_conf_threshold:
        note_items.append({"key": "disp.lowconf", "params": {}})
        needs_review = True
    if not pre["photo_recorded"]:
        note_items.append({"key": "disp.nophoto", "params": {}})
        needs_review = True
    if not post["reason"] and post["proposed_deduction_pct"]:
        note_items.append({"key": "disp.noreason", "params": {}})
    return render({
        "order_id": order.get("id"),
        "pre_sale": pre,
        "at_delivery": post,
        "items": items,
        "note_items": note_items,
        "needs_human_review": needs_review,
        "status": "open_for_review" if needs_review else "no_discrepancy"
    })


def _text(item):
    p = dict(item["params"])
    if item["key"] == "disp.grade":
        p["pre"], p["post"] = grade_name(p["pre"]), grade_name(p["post"])
    return t(item["key"], **p)


def render(report):
    """Saved report theke ekhon-er bhashay discrepancies/notes/statement banay."""
    r = dict(report)
    r["discrepancies"] = [_text(i) for i in report.get("items", [])]
    r["notes"] = [_text(i) for i in report.get("note_items", [])]
    r["statement"] = t("disp.statement")
    return r
