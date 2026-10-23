import math

CROPS = ["tomato", "potato", "onion", "brinjal", "chili", "cabbage", "rice"]
MARKETS = ["Dhaka", "Chattogram", "Rajshahi", "Bogura", "Khulna"]

# Approx base price BDT/kg (synthetic training baseline, real DAM data dile replace hobe)
BASE_PRICE = {"tomato": 60, "potato": 35, "onion": 55, "brinjal": 50, "chili": 120, "cabbage": 30, "rice": 52}
# Din-protit spoilage rate (perishability) - assumption, farmer edit korte parbe
SPOILAGE_PER_DAY = {"tomato": 0.035, "potato": 0.004, "onion": 0.006, "brinjal": 0.03,
                    "chili": 0.03, "cabbage": 0.025, "rice": 0.0008}
GRADE_FACTOR = {"A": 1.08, "B": 1.00, "C": 0.85}
GRADE_RANK = {"A": 3, "B": 2, "C": 1}

# Approx district/market coordinates (lat, lon)
LOCATIONS = {
    "dhaka": (23.81, 90.41), "chattogram": (22.36, 91.78), "rajshahi": (24.37, 88.60),
    "khulna": (22.85, 89.54), "sylhet": (24.90, 91.87), "barishal": (22.70, 90.37),
    "rangpur": (25.75, 89.25), "mymensingh": (24.75, 90.40), "bogura": (24.85, 89.37),
    "jashore": (23.17, 89.21), "comilla": (23.46, 91.18), "narayanganj": (23.62, 90.50),
    "gazipur": (23.99, 90.42), "dinajpur": (25.63, 88.64), "pabna": (24.00, 89.23),
    "kushtia": (23.90, 89.12), "tangail": (24.25, 89.92), "jamalpur": (24.92, 89.94),
    "coxsbazar": (21.43, 91.98),
}


def coords(loc):
    """loc = {"lat":..,"lon":..} or district name string."""
    if isinstance(loc, dict) and "lat" in loc and "lon" in loc:
        return float(loc["lat"]), float(loc["lon"])
    if isinstance(loc, str):
        key = loc.strip().lower().replace("'", "").replace(" ", "").replace("-", "")
        if key in LOCATIONS:
            return LOCATIONS[key]
    return LOCATIONS["dhaka"]


def haversine_km(a, b):
    la1, lo1 = coords(a)
    la2, lo2 = coords(b)
    p1, p2 = math.radians(la1), math.radians(la2)
    dphi, dl = p2 - p1, math.radians(lo2 - lo1)
    h = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return round(2 * 6371 * math.asin(math.sqrt(h)) * 1.25, 1)  # 1.25 = road factor
