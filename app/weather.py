"""Real-time weather integration.
Supports Open-Meteo (100% free, zero API key needed) and OpenWeatherMap (if API key provided)."""
import asyncio
import json
import time
import urllib.parse
import urllib.request
import logging

from .config import settings
from .engine.constants import coords

logger = logging.getLogger(__name__)

_cache = {}
LAST_ERROR = {"msg": None}


def fetch_weather(loc):
    lat, lon = coords(loc)
    ck = (round(lat, 1), round(lon, 1))
    hit = _cache.get(ck)
    if hit and time.time() - hit[0] < 1800:
        return hit[1]

    # 1. OpenWeatherMap (if user provided key)
    key = settings.OPENWEATHER_API_KEY
    if key:
        url = "https://api.openweathermap.org/data/2.5/weather?" + urllib.parse.urlencode(
            {"lat": lat, "lon": lon, "units": "metric", "appid": key})
        try:
            with urllib.request.urlopen(url, timeout=6) as r:
                d = json.load(r)
            out = {
                "temperature_c": float(d["main"]["temp"]),
                "humidity": d["main"].get("humidity"),
                "description": d["weather"][0]["description"],
                "source": "openweathermap",
            }
            LAST_ERROR["msg"] = None
            _cache[ck] = (time.time(), out)
            return out
        except Exception as e:
            logger.warning("OpenWeatherMap failed: %s, falling back to Open-Meteo", e)

    # 2. Open-Meteo (100% free, no API key needed, highly accurate for Bangladesh)
    open_meteo_url = (
        f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
        "&current=temperature_2m,relative_humidity_2m"
    )
    try:
        req = urllib.request.Request(
            open_meteo_url,
            headers={"User-Agent": "CropLink/1.0 (Agriculture Decision Platform)"}
        )
        with urllib.request.urlopen(req, timeout=6) as r:
            data = json.load(r)
            current = data.get("current", {})
            out = {
                "temperature_c": float(current.get("temperature_2m", 30.0)),
                "humidity": current.get("relative_humidity_2m", 70),
                "description": "Clear to normal",
                "source": "open-meteo",
            }
            LAST_ERROR["msg"] = None
            _cache[ck] = (time.time(), out)
            return out
    except Exception as e:
        LAST_ERROR["msg"] = f"Open-Meteo error: {e}"
        logger.warning("Open-Meteo failed: %s", e)

    # 3. Default fallback if completely offline
    fallback = {
        "temperature_c": 30.0,
        "humidity": 65,
        "description": "Default baseline",
        "source": "default_fallback",
    }
    return fallback


async def get_weather(loc):
    return await asyncio.to_thread(fetch_weather, loc)
