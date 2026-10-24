"""CropLink AI Assistant: Google Gemini integration with robust conversational & domain fallback."""
import json
import logging
import re
import time
import urllib.error
import urllib.request

from ..config import settings
from ..i18n import crop_name, t

logger = logging.getLogger(__name__)

CROP_WORDS = {
    "tomato": ["টমেটো", "tomato", "tometo"],
    "potato": ["আলু", "potato", "alu"],
    "onion": ["পেঁয়াজ", "পেয়াজ", "onion", "peyaj", "piyaj"],
    "brinjal": ["বেগুন", "brinjal", "begun"],
    "chili": ["মরিচ", "chili", "chilli", "morich"],
    "cabbage": ["বাঁধাকপি", "বাধাকপি", "cabbage", "badhakopi"],
    "rice": ["ধান", "চাল", "rice", "dhan", "chal"],
}
SELL = ["বিক্রি", "বেচ", "bikri", "sell", "wait", "অপেক্ষা", "opekkha", "কখন", "kokhon"]
PRICE = ["দাম", "দর", "dam", "dor", "price", "ভবিষ্যৎ"]
LOSS = ["পচে", "নষ্ট", "পচন", "loss", "spoil", "pochon"]
NEG = ["অফার", "offer", "giving", "pay", "bargain", "দিচ্ছে", "দিতে চাইছে", "চাইছে", "কষাকষি", "negotiat", "counter", "দর কম", "dam kom"]
GREETING = ["কেমন", "hello", "hi", "সালাম", "assalamu", "valo", "bhalo", "নমস্কার", "nomoshkar"]
BN_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")


def _matches_word(w: str, text: str) -> bool:
    if re.search(r"[a-zA-Z]", w):
        return bool(re.search(rf"\b{re.escape(w)}\b", text))
    return w in text


def _matches_any(words: list, text: str) -> bool:
    return any(_matches_word(w, text) for w in words)


def parse(text):
    if not text:
        return {"intent": "help", "crop": None, "quantity_kg": None, "offer_price": None}
    t_clean = text.lower().translate(BN_DIGITS)
    crop = next((c for c, ws in CROP_WORDS.items() if _matches_any(ws, t_clean)), None)
    m = re.search(r"(\d+(?:\.\d+)?)\s*(কেজি|kg\b|মণ|mon\b|maund\b)", t_clean)
    qty = None
    if m:
        qty = float(m.group(1)) * (40 if m.group(2) in ("মণ", "mon", "maund") else 1)
    mp = re.search(r"(\d+(?:\.\d+)?)\s*(টাকা|tk\b|bdt\b|taka\b|৳)", t_clean)
    offer_price = float(mp.group(1)) if mp and _matches_any(NEG, t_clean) else None

    if _matches_any(GREETING, t_clean) and not crop and not offer_price:
        intent = "greeting"
    elif offer_price:
        intent = "negotiate"
    elif _matches_any(LOSS, t_clean):
        intent = "loss"
    elif _matches_any(SELL, t_clean):
        intent = "sell"
    elif _matches_any(PRICE, t_clean):
        intent = "price"
    else:
        intent = "general"

    res = {"intent": intent, "crop": crop, "quantity_kg": qty}
    if offer_price is not None:
        res["offer_price"] = offer_price
    return res


def fmt_forecast(crop, fc):
    return t("chat.price", crop=crop_name(crop), price=f"{fc['current_price']:.0f}", trend=t("trend." + fc["trend"]),
             low=f"{fc['h7']['low']:.0f}", high=f"{fc['h7']['high']:.0f}", base=f"{fc['h7']['base']:.0f}")


def fmt_decision(crop, dec, qty):
    best = next(o for o in dec["options"] if o["id"] == dec["recommended"])
    now = next(o for o in dec["options"] if o["id"] == "sell_now")
    txt = t("chat.sell", qty=f"{qty:.0f}", crop=crop_name(crop), label=best["label"], base=f"{best['net']['base']:.0f}",
            low=f"{best['net']['downside']:.0f}", high=f"{best['net']['best']:.0f}", now=f"{now['net']['base']:.0f}")
    if dec["safest"] != dec["recommended"]:
        txt += t("chat.sell_safe")
    return txt + t("chat.sell_tail")


def ask_gemini(user_prompt: str, context: dict, lang: str = "bn") -> str:
    """Calls Google Gemini API using the standard Gemini 1.5 / 2.0 endpoint."""
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        return ""

    model = settings.GEMINI_MODEL or "gemini-3.1-flash-lite"
    if model.startswith("models/"):
        model_endpoint = model.replace("models/", "")
    else:
        model_endpoint = model

    system_instruction = (
        "You are CropLink AI, the official agricultural decision assistant for smallholder farmers and buyers across Bangladesh. "
        "You understand Bengali (বাংলা), English, and Banglish (phonetic Romanized Bengali, e.g. 'tomator daam kemon thakbe?', 'alu koto kore bikri korbo?', 'pata holud dag hoile ki korbo?'). "
        "RESPONSE RULES: "
        "1. Respond directly in the SAME language and style the user asked in. If asked in Banglish, reply in friendly, concise Banglish or clear simple Bengali. If asked in Bangla script, reply in fluent Bengali. If English, reply in English. "
        "2. Keep replies practical, accurate, and concise (2 to 4 sentences). Never include internal monologue or thinking tags. "
        "3. Provide actionable advice for Bangladeshi farming, market prices (BDT/kg), disease/pest remedies, and selling vs holding decisions. "
        "4. Mention CropLink features (Decide, Fair Price Forecast, Smart Grading) when relevant."
    )

    context_str = json.dumps(context, ensure_ascii=False) if context else ""
    full_prompt = f"{user_prompt}\n\n[Context: {context_str}]" if context_str else user_prompt

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": full_prompt}]
            }
        ],
        "systemInstruction": {
            "parts": [{"text": system_instruction}]
        },
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 300,
            "topP": 0.9
        }
    }

    # Try primary model, fallback to alternate flash-lite model if needed (up to 3 sequential calls, 8s total budget)
    models_to_try = [model_endpoint, "gemini-3.1-flash-lite", "gemini-3.5-flash-lite"]
    start_time = time.time()
    total_budget = 8.0
    for m in dict.fromkeys(models_to_try):
        remaining = total_budget - (time.time() - start_time)
        if remaining <= 0:
            break
        timeout = min(6.0, remaining)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent"
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "x-goog-api-key": api_key
                }
            )
            with urllib.request.urlopen(req, timeout=timeout) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                candidates = res_data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        return parts[0].get("text", "").strip()
        except Exception as e:
            logger.warning("Gemini model %s call failed: %s", m, e)
            continue
    return ""
