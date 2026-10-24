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

# Bounded weather cache: (timestamp, result_dict, ttl_seconds)
_cache = {}
MAX_CACHE_SIZE = 100
LAST_ERROR = {"msg": None}


def fetch_weather(loc):
    lat, lon = coords(loc)
    ck = (round(lat, 1), round(lon, 1))
    hit = _cache.get(ck)
    if hit:
        cached_time, cached_data, ttl = hit
        if time.time() - cached_time < ttl:
            return cached_data

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
                "is_fallback": False,
            }
            LAST_ERROR["msg"] = None
            if len(_cache) >= MAX_CACHE_SIZE:
                _cache.pop(next(iter(_cache)))
            _cache[ck] = (time.time(), out, 1800)  # 30 min TTL on success
            return out
        except Exception as e:
            logger.warning("OpenWeatherMap failed: %s, falling back to Open-Meteo", e)

    # 2. Open-Meteo (100% free, no API key needed, highly accurate for Bangladesh)
    open_meteo_url = (
        f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
        "&current=temperature_2m,relative_humidity_2m,weather_code"
    )
    try:
        req = urllib.request.Request(
            open_meteo_url,
            headers={"User-Agent": "CropLink/1.0 (Agriculture Decision Platform)"}
        )
        with urllib.request.urlopen(req, timeout=6) as r:
            data = json.load(r)
            current = data.get("current", {})
            temp = float(current.get("temperature_2m", 30.0))
            out = {
                "temperature_c": temp,
                "humidity": current.get("relative_humidity_2m", 70),
                "description": f"Weather code {current.get('weather_code', 0)}",
                "source": "open-meteo",
                "is_fallback": False,
            }
            LAST_ERROR["msg"] = None
            if len(_cache) >= MAX_CACHE_SIZE:
                _cache.pop(next(iter(_cache)))
            _cache[ck] = (time.time(), out, 1800)
            return out
    except Exception as e:
        LAST_ERROR["msg"] = f"Open-Meteo error: {e}"
        logger.warning("Open-Meteo failed: %s", e)

    # 3. Default fallback if completely offline (cache failures for 3 minutes)
    fallback = {
        "temperature_c": 30.0,
        "humidity": 65,
        "description": "Default baseline",
        "source": "default_fallback",
        "is_fallback": True,
    }
    if len(_cache) >= MAX_CACHE_SIZE:
        _cache.pop(next(iter(_cache)))
    _cache[ck] = (time.time(), fallback, 180)  # 3 min failure TTL
    return fallback


async def get_weather(loc):
    return await asyncio.to_thread(fetch_weather, loc)
