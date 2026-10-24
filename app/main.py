"""AgriSphere FairMarket - single backend (FastAPI + MongoDB). Main engine: /decision/net-profit"""
import asyncio
import base64
import hashlib
import io
import json
import re
import time
from contextlib import asynccontextmanager
from collections import Counter
from datetime import date, timedelta
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, FastAPI, File, Form, Header, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, field_validator, model_validator

from . import auth, i18n, seed, weather
from .config import settings
from .db import make_db, new_id, now_iso
from .i18n import t
from .engine import assistant as asst
from .engine import dispute as disp
from .engine import loss as lossmod
from .engine import alerts as alertmod
from .engine import demand as demandmod
from .engine import matching, negotiation, netprofit, pooling, reliability
from .engine.constants import CROPS, GRADE_FACTOR, GRADE_RANK, MARKETS, coords, haversine_km, dhaka_today
from .ml.forecaster import MIN_HISTORY, Forecaster
from .ml.grader import Grader, ImageDecodeError
from .ml.train_all import ensure_models


STATE: Dict[str, Any] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    env = getattr(settings, "ENVIRONMENT", "development")
    if env != "development":
        secret = settings.JWT_SECRET or ""
        if secret in ("dev-only-change-me", "change-me-long-random") or len(secret) < 32:
            raise RuntimeError(f"JWT_SECRET is insecure in {env} environment: must be at least 32 characters and not default")
        if not settings.AUTH_REQUIRED:
            raise RuntimeError(f"AUTH_REQUIRED=false is only allowed in development environment")
    if env == "production" and not settings.MONGODB_URI:
        raise RuntimeError("MONGODB_URI cannot be empty in production environment")

    ensure_models()  # model file na thakle train kore ney
    STATE["forecaster"] = Forecaster()
    STATE["grader"] = Grader()
    STATE["db"] = make_db()
    await STATE["db"].setup()
    await bootstrap_admin()
    if settings.SEED_DEMO:
        STATE["seed"] = await seed.seed_demo(STATE["db"])
    try:
        yield
    finally:
        if "db" in STATE and hasattr(STATE["db"], "close"):
            await STATE["db"].close()


app = FastAPI(title="AgriSphere FairMarket API", version="1.0.0", lifespan=lifespan,
              description="Net-profit decision engine + price forecast + photo grading + matching + pooling + dispute evidence")
app.add_middleware(CORSMiddleware, allow_origins=settings.ALLOWED_ORIGINS, allow_methods=["*"], allow_headers=["*"])


@app.middleware("http")
async def language_middleware(request, call_next):
    """Response language: Accept-Language: bn|en header or ?lang=bn|en (default bn)."""
    token = i18n.LANG.set(i18n.detect(request.query_params.get("lang"), request.headers.get("accept-language")))
    try:
        return await call_next(request)
    finally:
        i18n.LANG.reset(token)


@app.middleware("http")
async def failure_logging_middleware(request, call_next):
    import logging
    logger = logging.getLogger("croplink.http")
    response = await call_next(request)
    if response.status_code >= 400:
        logger.info("Request failed: %s %s -> HTTP %s", request.method, request.url.path, response.status_code)
    return response


@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    import logging
    logging.getLogger("croplink.error").info("ValueError: %s", exc)
    return JSONResponse(status_code=422, content={"detail": str(exc) if str(exc) else "Invalid value"})


bearer = HTTPBearer(auto_error=False)


async def check_key(x_api_key: Optional[str] = Header(default=None),
                    cred: Optional[HTTPAuthorizationCredentials] = Depends(bearer)):
    if settings.API_KEY:
        if not x_api_key or not hmac.compare_digest(x_api_key, settings.API_KEY):
            raise HTTPException(401, t("err.apikey"))
    if settings.AUTH_REQUIRED:
        payload = auth.decode_token(cred.credentials) if cred else None
        if not payload:
            raise HTTPException(401, t("err.login"))
        return payload
    return None


async def user_dep(cred: Optional[HTTPAuthorizationCredentials] = Depends(bearer)):
    """Token payload ({sub, role}) of the logged-in user, or None."""
    return auth.decode_token(cred.credentials) if cred else None


def forbid(key="err.forbid", **kw):
    raise HTTPException(403, t(key, **kw))


def _check_auth_caller(u):
    if u is None:
        if settings.AUTH_REQUIRED:
            raise HTTPException(401, t("err.login"))
        if getattr(settings, "ENVIRONMENT", "development") != "development":
            raise HTTPException(401, t("err.login"))
        return None
    return u


def require_owner(u, owner_id):
    u = _check_auth_caller(u)
    if u is None:
        return
    if u.get("role") != "admin" and u.get("sub") != owner_id:
        forbid("err.owner")


def require_role(u, *roles):
    u = _check_auth_caller(u)
    if u is None:
        return
    if u.get("role") not in roles:
        forbid("err.role", roles="/".join(roles))


def require_party(u, buyer_id, farmer_ids):
    u = _check_auth_caller(u)
    if u is None:
        return
    if u.get("role") != "admin" and u.get("sub") != buyer_id and u.get("sub") not in farmer_ids:
        forbid("err.party")



def localize_order(o):
    """Order-er saved evidence report request-er bhashay."""
    if o and o.get("evidence_report"):
        o = {**o, "evidence_report": disp.render(o["evidence_report"])}
    return o


def order_parties(order):
    return order["buyer_id"], [a["farmer_id"] for a in order.get("allocations", [])]


async def bootstrap_admin():
    admin_phone = auth.normalize_phone(settings.ADMIN_PHONE) if settings.ADMIN_PHONE else None
    if admin_phone and settings.ADMIN_PASSWORD and not await db().list("users", {"phone": admin_phone}, 1):
        pwd_hash = await asyncio.to_thread(auth.hash_password, settings.ADMIN_PASSWORD)
        await db().insert("users", {"id": new_id("admin"), "phone": admin_phone, "role": "admin",
                                    "password_hash": pwd_hash, "created_at": now_iso()})


async def lang_param(lang: Optional[str] = Query(default=None, description="Response language: bn or en (the Accept-Language header also works)")):
    """Sirf Swagger-e `lang` field dekhanor jonno; asol bhasha middleware thik kore."""
    return lang


api = APIRouter(dependencies=[Depends(check_key), Depends(lang_param)])
public = APIRouter(prefix="/auth", tags=["auth"], dependencies=[Depends(lang_param)])


def db():
    return STATE["db"]


def need(doc, what):
    if not doc:
        raise HTTPException(404, t("err.notfound", what=what))
    return doc


# ---------------------------------------------------------------- schemas
def _clean_grade(v):
    if v is None:
        return v
    if isinstance(v, str):
        v = v.strip().upper()
    return v


def _validate_iso_date(v):
    if v is None:
        return v
    try:
        date.fromisoformat(str(v)[:10])
        return v
    except Exception:
        raise ValueError(f"Invalid ISO date: '{v}'. Expected YYYY-MM-DD")


class Location(BaseModel):
    district: Optional[str] = None
    lat: Optional[float] = Field(default=None, ge=-90.0, le=90.0)
    lon: Optional[float] = Field(default=None, ge=-180.0, le=180.0)

    def as_loc(self):
        if self.lat is not None and self.lon is not None:
            return {"lat": self.lat, "lon": self.lon}
        return self.district or "Dhaka"


class ProfileIn(BaseModel):
    name: str
    phone: Optional[str] = None
    org_type: Optional[str] = Field(default=None, description="buyer: wholesaler/retailer/hotel/exporter/aggregator")
    location: Location = Location()
    language: str = "bn"


class PricePoint(BaseModel):
    date: str
    price: float = Field(gt=0)

    @field_validator("date", mode="before")
    def val_date(cls, v):
        return _validate_iso_date(v)


class PriceIngest(BaseModel):
    crop: str
    market: str
    prices: List[PricePoint]


class LotIn(BaseModel):
    farmer_id: str
    crop: str
    quantity_kg: float = Field(gt=0)
    grade: Literal["A", "B", "C"] = "B"
    location: Location
    harvest_date: str = Field(default_factory=lambda: dhaka_today().isoformat())
    batch_id: Optional[str] = None

    @field_validator("grade", mode="before")
    def val_grade(cls, v):
        return _clean_grade(v)

    @field_validator("harvest_date", mode="before")
    def val_harvest_date(cls, v):
        return _validate_iso_date(v)


class DemandIn(BaseModel):
    buyer_id: str
    crop: str
    quantity_kg: float = Field(gt=0)
    min_quantity_kg: Optional[float] = None
    min_grade: Literal["A", "B", "C"] = "C"
    price_per_kg: float = Field(gt=0)
    location: Location
    max_distance_km: float = Field(default=300.0, ge=0)
    needed_by: Optional[str] = None
    buyer_pickup: bool = False

    @field_validator("min_grade", mode="before")
    def val_grade(cls, v):
        return _clean_grade(v)

    @field_validator("needed_by", mode="before")
    def val_needed_by(cls, v):
        return _validate_iso_date(v)

    @model_validator(mode="after")
    def val_min_qty(self):
        if self.min_quantity_kg is not None:
            if self.min_quantity_kg < 0 or self.min_quantity_kg > self.quantity_kg:
                raise ValueError("min_quantity_kg must be between 0 and quantity_kg")
        return self


class BatchIn(BaseModel):
    farmer_id: str
    crop: str
    quantity_kg: float = Field(gt=0)
    location: Location
    harvest_date: str = Field(default_factory=lambda: dhaka_today().isoformat())
    grade: Literal["A", "B", "C"]
    grade_confidence: Optional[float] = None
    photo_base64: Optional[str] = Field(default=None, description="small thumbnail (<=400KB, base64)")
    photo_url: Optional[str] = None

    @field_validator("grade", mode="before")
    def val_grade(cls, v):
        return _clean_grade(v)

    @field_validator("harvest_date", mode="before")
    def val_harvest_date(cls, v):
        return _validate_iso_date(v)


class OfferIn(BaseModel):
    buyer_id: Optional[str] = None
    buyer_name: Optional[str] = None
    price_per_kg: float = Field(gt=0)
    distance_km: Optional[float] = Field(default=None, ge=0)
    location: Optional[Any] = None
    min_quantity_kg: Optional[float] = Field(default=None, ge=0)
    reliability: Optional[Dict[str, Any]] = None
    buyer_pickup: Optional[bool] = False


class DecisionIn(BaseModel):
    crop: str
    quantity_kg: float = Field(gt=0)
    grade: Literal["A", "B", "C"] = "B"
    market: str = "Dhaka"
    farmer_location: Optional[Location] = None
    current_price: Optional[float] = Field(default=None, gt=0, description="If omitted, the latest price from DB/bundled data is used")
    costs: Optional[Dict[str, float]] = Field(default=None, description="transport_per_kg_km, handling_per_kg, storage_per_kg_day, commission_pct, local_market_km")
    temperature_c: Optional[float] = Field(default=None, description="If omitted: weather API (when key is set), otherwise 30C")
    spoilage_per_day: Optional[float] = Field(default=None, ge=0, le=0.5, description="Daily spoilage rate (0.02 = 2%). Use a lower value for cold storage. Defaults to the crop value.")
    lot_id: Optional[str] = Field(default=None, description="If given, open buyer demands matching this lot are included as offers")
    offers: Optional[List[OfferIn]] = None

    @field_validator("grade", mode="before")
    def val_grade(cls, v):
        return _clean_grade(v)

    @field_validator("costs")
    def val_costs(cls, v):
        if v is not None:
            for k, val in v.items():
                if val is not None and val < 0:
                    raise ValueError(f"Cost parameter '{k}' cannot be negative: {val}")
            if v.get("commission_pct", 0) >= 100:
                raise ValueError("commission_pct must be less than 100")
        return v


class PoolIn(BaseModel):
    demand_id: str
    harvest_window_days: int = 4


class AllocationItem(BaseModel):
    lot_id: str
    allocated_kg: float = Field(gt=0)
    farmer_id: Optional[str] = None


class OrderIn(BaseModel):
    demand_id: str
    allocations: List[AllocationItem] = Field(description="[{lot_id, farmer_id, allocated_kg}]")
    agreed_price: float = Field(gt=0)
    batch_ids: List[str] = []


class DeliveryIn(BaseModel):
    observed_grade: Optional[Literal["A", "B", "C"]] = None
    observed_weight_kg: Optional[float] = Field(default=None, gt=0)
    proposed_deduction_pct: float = Field(default=0, ge=0, le=100)
    reason: str = ""

    @field_validator("observed_grade", mode="before")
    def val_observed_grade(cls, v):
        return _clean_grade(v)


class PaymentIn(BaseModel):
    action: str = Field(description="fund | release | refund | cancel")
    on_time: Optional[bool] = None
    cancelled_by: Optional[str] = None


class LossIn(BaseModel):
    crop: str
    hours_since_harvest: float = Field(default=0, ge=0)
    temperature_c: Optional[float] = Field(default=None, ge=-10.0, le=60.0)
    district: Optional[str] = None
    distance_km: float = Field(ge=0)
    hours_to_deadline: Optional[float] = None


class NegotiateIn(BaseModel):
    crop: str
    quantity_kg: float = Field(gt=0)
    grade: Literal["A", "B", "C"] = "B"
    market: str = "Dhaka"
    offers: Optional[List[OfferIn]] = Field(default=None, description="[{price_per_kg, distance_km, buyer_name?}]")
    lot_id: Optional[str] = None
    costs: Optional[Dict[str, float]] = None
    temperature_c: Optional[float] = None
    spoilage_per_day: Optional[float] = Field(default=None, ge=0, le=0.5)
    production_cost_per_kg: Optional[float] = Field(default=None, ge=0, description="Farmer's own production cost per kg")
    margin_pct: float = Field(default=0, ge=0, le=100, description="Required margin (%) above the best alternative")

    @field_validator("grade", mode="before")
    def val_grade(cls, v):
        return _clean_grade(v)

    @field_validator("costs")
    def val_costs(cls, v):
        if v is not None:
            for k, val in v.items():
                if val is not None and val < 0:
                    raise ValueError(f"Cost parameter '{k}' cannot be negative: {val}")
            if v.get("commission_pct", 0) >= 100:
                raise ValueError("commission_pct must be less than 100")
        return v


class WatchIn(BaseModel):
    farmer_id: str
    crop: str
    market: str = "Dhaka"
    threshold_pct: float = Field(default=7, ge=1, le=50)


class ChatIn(BaseModel):
    text: Optional[str] = Field(default=None, max_length=1000)
    message: Optional[str] = Field(default=None, max_length=1000)
    market: str = "Dhaka"
    farmer_id: Optional[str] = None
    quantity_kg: Optional[float] = None
    grade: Literal["A", "B", "C"] = "B"
    context: Optional[dict] = None

    @field_validator("grade", mode="before")
    def val_grade(cls, v):
        return _clean_grade(v)



class NoRealPriceDataException(HTTPException):
    def __init__(self, detail="Real price data not available"):
        super().__init__(status_code=503, detail=detail)


@app.exception_handler(NoRealPriceDataException)
async def no_real_price_data_handler(request, exc):
    return JSONResponse(status_code=503, content={"detail": exc.detail, "code": "no_real_price_data"})


async def get_series_meta(crop, market):
    doc = await db().get("prices", f"{crop}|{market}")
    series = doc["series"] if doc else []
    if len(series) >= MIN_HISTORY:
        as_of_str = str(series[-1][0])[:10]
        try:
            as_of_date = date.fromisoformat(as_of_str)
            data_age = max(0, (date.today() - as_of_date).days)
        except Exception:
            data_age = 0
        meta = {
            "data_source": "dam_prices",
            "is_synthetic": False,
            "as_of": as_of_str,
            "data_age_days": data_age
        }
        return series, meta

    # Bundled synthetic series
    if not getattr(settings, "ALLOW_SYNTHETIC_DATA", False):
        raise NoRealPriceDataException("Real price data is required; synthetic data is disallowed")

    series = STATE["forecaster"].bundled_series(crop, market) or []
    if not series:
        raise NoRealPriceDataException("No price data available")

    as_of_str = str(series[-1][0])[:10]
    try:
        as_of_date = date.fromisoformat(as_of_str)
        data_age = max(0, (date.today() - as_of_date).days)
    except Exception:
        data_age = 0

    meta = {
        "data_source": "synthetic",
        "is_synthetic": True,
        "as_of": as_of_str,
        "data_age_days": data_age
    }
    return series, meta


# ---------------------------------------------------------------- helpers
async def get_series(crop, market):
    series, _ = await get_series_meta(crop, market)
    return series


async def buyer_reliability(buyer_id):
    orders = await db().list("orders", {"buyer_id": buyer_id}, 500)
    return reliability.score_buyer(orders)


def check_crop_market(crop, market=None):
    if crop not in CROPS:
        raise HTTPException(422, t("err.crop", list=", ".join(CROPS)))
    if market and market not in MARKETS:
        raise HTTPException(422, t("err.market", list=", ".join(MARKETS)))


async def resolve_temp(temp, location):
    """(temperature, info) - user dile seta; na hole weather API; na hole 30."""
    if temp is not None:
        return temp, {"source": "user_input", "temperature_c": temp, "is_fallback": False}
    w = await weather.get_weather(location)
    if w and not w.get("is_fallback"):
        return w["temperature_c"], w
    return 30.0, {"source": "default_fallback", "is_fallback": True, "temperature_c": 30.0,
                  "note": t("wx.default")}


# ---------------------------------------------------------------- system
@app.get("/health")
async def health():
    try:
        ok = await db().ping()
        if not ok:
            return JSONResponse(status_code=503, content={"status": "degraded", "database": db().kind, "db_ping": False})
    except Exception:
        return JSONResponse(status_code=503, content={"status": "degraded", "database": db().kind, "db_ping": False})

    fc = STATE.get("forecaster")
    gr = STATE.get("grader")
    fc_metrics = fc.metrics if fc else {}
    gr_metrics = gr.metrics if gr else {}

    return {
        "status": "ok",
        "database": db().kind,
        "db_ping": ok,
        "forecaster": fc_metrics,
        "grader": gr_metrics,
        "warnings": {
            "forecaster": fc_metrics.get("warning"),
            "grader": gr_metrics.get("warning")
        }
    }



@app.get("/")
async def root():
    return {"name": "AgriSphere FairMarket API", "status": "running", "docs": "/docs", "health": "/health",
            "languages": list(i18n.SUPPORTED)}


@app.get("/meta")
async def meta(lang: Optional[str] = Query(default=None, description="bn or en")):
    """Ids plus Bangla/English names for dropdowns and labels (no login needed)."""
    return {"crops": CROPS, "markets": MARKETS, "grades": list(GRADE_FACTOR), "languages": list(i18n.SUPPORTED),
            "language": i18n.LANG.get(),
            "names": {"crops": i18n.CROP_NAMES, "markets": i18n.MARKET_NAMES, "grades": i18n.GRADE_NAMES,
                      "statuses": i18n.STATUS_NAMES}}


# ---------------------------------------------------------------- auth (MongoDB users)
class RegisterIn(BaseModel):
    name: str
    phone: str = Field(min_length=6)
    password: str = Field(min_length=6)
    role: str = Field(description="farmer | buyer")
    district: Optional[str] = "Dhaka"
    org_type: Optional[str] = None


class LoginIn(BaseModel):
    phone: str
    password: str


# In-memory rate limiter for auth (login/register)
# 10 failures within 10 minutes (600s) triggers 429 per IP and per phone
# Note: Multi-instance production deployments require a shared distributed cache (e.g. Redis).
AUTH_FAILURES: Dict[str, List[float]] = {}
AUTH_RATE_LIMIT_WINDOW = 600
AUTH_MAX_FAILURES = 10


def _check_auth_rate_limit(keys: List[str]):
    now = time.time()
    for k in keys:
        failures = [t for t in AUTH_FAILURES.get(k, []) if now - t < AUTH_RATE_LIMIT_WINDOW]
        AUTH_FAILURES[k] = failures
        if len(failures) >= AUTH_MAX_FAILURES:
            raise HTTPException(429, "Too many failed attempts. Please try again later.")


def _record_auth_failure(keys: List[str]):
    now = time.time()
    for k in keys:
        failures = [t for t in AUTH_FAILURES.setdefault(k, []) if now - t < AUTH_RATE_LIMIT_WINDOW]
        failures.append(now)
        AUTH_FAILURES[k] = failures


def _clear_auth_failure(keys: List[str]):
    for k in keys:
        AUTH_FAILURES.pop(k, None)


@public.post("/register")
async def register(r: RegisterIn, request: Request):
    phone = auth.normalize_phone(r.phone)
    client_ip = request.client.host if request.client else "unknown"
    rate_keys = [f"ip:{client_ip}", f"phone:{phone}"]
    _check_auth_rate_limit(rate_keys)

    if r.role not in ("farmer", "buyer"):
        _record_auth_failure(rate_keys)
        raise HTTPException(422, t("err.role_value"))

    uid = new_id(r.role)
    pwd_hash = await asyncio.to_thread(auth.hash_password, r.password)
    user_doc = {
        "id": uid,
        "phone": phone,
        "role": r.role,
        "password_hash": pwd_hash,
        "created_at": now_iso()
    }

    # Insert user record FIRST to catch duplicate-key error
    try:
        await db().insert("users", user_doc)
    except Exception:
        _record_auth_failure(rate_keys)
        raise HTTPException(409, t("err.phone_exists"))

    coll = "farmers" if r.role == "farmer" else "buyers"
    profile = {
        "id": uid,
        "name": r.name,
        "phone": phone,
        "org_type": r.org_type,
        "location": r.district or "Dhaka",
        "language": "bn",
        "created_at": now_iso()
    }
    try:
        await db().insert(coll, profile)
    except Exception:
        # Roll back user record on profile insert failure
        await db().delete("users", uid)
        _record_auth_failure(rate_keys)
        raise

    _clear_auth_failure(rate_keys)
    return {
        "token": auth.create_token(uid, r.role),
        "user_id": uid,
        "role": r.role,
        "profile": profile
    }


@public.post("/login")
async def login(l: LoginIn, request: Request):
    phone = auth.normalize_phone(l.phone)
    client_ip = request.client.host if request.client else "unknown"
    rate_keys = [f"ip:{client_ip}", f"phone:{phone}"]
    _check_auth_rate_limit(rate_keys)

    users = await db().list("users", {"phone": phone}, 1)
    if not users:
        _record_auth_failure(rate_keys)
        raise HTTPException(401, t("err.login_bad"))

    u = users[0]
    valid = await asyncio.to_thread(auth.verify_password, l.password, u["password_hash"])
    if not valid:
        _record_auth_failure(rate_keys)
        raise HTTPException(401, t("err.login_bad"))

    _clear_auth_failure(rate_keys)
    return {"token": auth.create_token(u["id"], u["role"]), "user_id": u["id"], "role": u["role"]}


@public.get("/me")
async def me(cred: Optional[HTTPAuthorizationCredentials] = Depends(bearer)):
    payload = auth.decode_token(cred.credentials) if cred else None
    if not payload:
        raise HTTPException(401, t("err.token"))
    coll = {"farmer": "farmers", "buyer": "buyers"}.get(payload["role"])
    profile = await db().get(coll, payload["sub"]) if coll else {"id": payload["sub"], "name": "Admin"}
    return {"user_id": payload["sub"], "role": payload["role"], "profile": profile}


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    district: Optional[str] = None
    phone: Optional[str] = None


@public.put("/me")
async def update_me(p: ProfileUpdate, cred: Optional[HTTPAuthorizationCredentials] = Depends(bearer)):
    payload = auth.decode_token(cred.credentials) if cred else None
    if not payload:
        raise HTTPException(401, t("err.token"))
    coll = {"farmer": "farmers", "buyer": "buyers"}.get(payload["role"])
    if not coll:
        raise HTTPException(422, t("err.admin_edit"))
    
    fields = {}
    if p.name:
        fields["name"] = p.name
    if p.district:
        fields["location"] = p.district
    if p.phone:
        norm_phone = auth.normalize_phone(p.phone)
        existing = await db().list("users", {"phone": norm_phone}, 1)
        if existing and existing[0]["id"] != payload["sub"]:
            raise HTTPException(409, t("err.phone_exists"))
        fields["phone"] = norm_phone
        await db().update("users", payload["sub"], {"phone": norm_phone})

    prof = await db().update(coll, payload["sub"], fields) if fields else await db().get(coll, payload["sub"])
    return {"profile": prof}


def _public_profile(p: dict) -> dict:
    loc = p.get("location")
    district = loc.get("district") if isinstance(loc, dict) else (loc if isinstance(loc, str) else None)
    return {
        "id": p.get("id"),
        "name": p.get("name"),
        "location": district or "Dhaka",
        "org_type": p.get("org_type")
    }


@api.post("/farmers")
async def create_farmer(p: ProfileIn, u: Optional[dict] = Depends(user_dep)):
    require_role(u, "admin")
    doc = {"id": new_id("farmer"), **p.model_dump(), "location": p.location.as_loc(), "created_at": now_iso()}
    return await db().insert("farmers", doc)


@api.post("/buyers")
async def create_buyer(p: ProfileIn, u: Optional[dict] = Depends(user_dep)):
    require_role(u, "admin")
    doc = {"id": new_id("buyer"), **p.model_dump(), "location": p.location.as_loc(), "created_at": now_iso()}
    return await db().insert("buyers", doc)


@api.get("/farmers/{fid}")
async def get_farmer(fid: str, u: Optional[dict] = Depends(user_dep)):
    f = need(await db().get("farmers", fid), "Farmer")
    u_role = u.get("role") if u else None
    u_sub = u.get("sub") if u else None
    if u_role == "admin" or u_sub == fid:
        return f
    return _public_profile(f)


@api.get("/buyers/{bid}")
async def get_buyer(bid: str, u: Optional[dict] = Depends(user_dep)):
    b = need(await db().get("buyers", bid), "Buyer")
    u_role = u.get("role") if u else None
    u_sub = u.get("sub") if u else None
    if u_role == "admin" or u_sub == bid:
        return b
    return _public_profile(b)


@api.get("/buyers/{bid}/reliability")
async def get_reliability(bid: str):
    need(await db().get("buyers", bid), "Buyer")
    return await buyer_reliability(bid)


# ---------------------------------------------------------------- prices / forecast
@api.post("/prices")
async def ingest_prices(p: PriceIngest, u: Optional[dict] = Depends(user_dep)):
    """Push daily DAM prices (admin only). The forecast uses this data."""
    require_role(u, "admin")
    check_crop_market(p.crop, p.market)
    key = f"{p.crop}|{p.market}"
    doc = await db().get("prices", key)
    merged = {d: pr for d, pr in (doc["series"] if doc else [])}
    for x in p.prices:
        merged[x.date] = x.price
    series = [[d, merged[d]] for d in sorted(merged)][-120:]
    if doc:
        await db().update("prices", key, {"series": series, "created_at": now_iso()})
    else:
        await db().insert("prices", {"id": key, "crop": p.crop, "market": p.market, "series": series, "created_at": now_iso()})
    series_ignored = len(series) < 15
    return {"stored_points": len(series), "series_ignored": series_ignored}


@api.get("/forecast")
async def forecast(crop: str, market: str = "Dhaka"):
    check_crop_market(crop, market)
    series, meta = await get_series_meta(crop, market)
    fc = STATE["forecaster"].forecast(crop, market, series)
    fc.update(meta)
    return fc



# ---------------------------------------------------------------- grading + batches
class GradeJsonIn(BaseModel):
    photo_base64: str = Field(..., max_length=28 * 1024 * 1024)
    crop: Optional[str] = "tomato"


@api.post("/grade-json")
async def grade_photo_json(b: GradeJsonIn):
    if "grader" not in STATE or STATE["grader"] is None:
        raise HTTPException(503, "Grader model not available")
    try:
        raw = b.photo_base64
        data = raw.encode() if isinstance(raw, str) else raw
        return await asyncio.to_thread(STATE["grader"].grade_bytes, data, b.crop)
    except ImageDecodeError:
        raise HTTPException(422, t("err.img_bad"))


@api.post("/grade")
async def grade_photo(file: UploadFile = File(...), crop: Optional[str] = Form("tomato")):
    if "grader" not in STATE or STATE["grader"] is None:
        raise HTTPException(503, "Grader model not available")
    chunks = []
    total = 0
    max_size = 20 * 1024 * 1024
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > max_size:
            raise HTTPException(413, t("err.img_big"))
        chunks.append(chunk)
    data = b"".join(chunks)
    if len(data) == 0:
        raise HTTPException(422, t("err.img_bad"))
    try:
        return await asyncio.to_thread(STATE["grader"].grade_bytes, data, crop)
    except ImageDecodeError:
        raise HTTPException(422, t("err.img_bad"))



@api.post("/batches")
async def create_batch(b: BatchIn, u: Optional[dict] = Depends(user_dep)):
    require_owner(u, b.farmer_id)
    need(await db().get("farmers", b.farmer_id), "Farmer")
    check_crop_market(b.crop)
    if b.photo_base64 and len(b.photo_base64) > 550_000:
        raise HTTPException(413, t("err.photo_big"))
    doc = {"id": new_id("batch"), **b.model_dump(), "location": b.location.as_loc(), "created_at": now_iso()}
    core = {k: doc[k] for k in ("id", "farmer_id", "crop", "quantity_kg", "harvest_date", "grade", "created_at")}
    doc["passport_hash"] = hashlib.sha256(json.dumps(core, sort_keys=True).encode()).hexdigest()
    return await db().insert("batches", doc)


@api.get("/batches/{bid}/passport")
async def passport(bid: str):
    b = need(await db().get("batches", bid), "Batch")
    core = {k: b[k] for k in ("id", "farmer_id", "crop", "quantity_kg", "harvest_date", "grade", "created_at")}
    ok = hashlib.sha256(json.dumps(core, sort_keys=True).encode()).hexdigest() == b["passport_hash"]
    return {"batch_id": bid, "qr_payload": f"agrisphere://batch/{bid}", "record": core,
            "origin": b["location"], "hash": b["passport_hash"], "hash_valid": ok,
            "note": t("passport.note")}


# ---------------------------------------------------------------- lots & demands
@api.post("/lots")
async def create_lot(l: LotIn, u: Optional[dict] = Depends(user_dep)):
    require_owner(u, l.farmer_id)
    check_crop_market(l.crop)
    need(await db().get("farmers", l.farmer_id), "Farmer")
    doc = {"id": new_id("lot"), **l.model_dump(), "location": l.location.as_loc(), "status": "open", "created_at": now_iso()}
    return await db().insert("lots", doc)


@api.get("/lots")
async def list_lots(crop: Optional[str] = None, farmer_id: Optional[str] = None, status: Optional[str] = None,
                    skip: int = Query(default=0, ge=0), limit: int = Query(default=200, ge=1, le=200)):
    flt = {k: v for k, v in (("crop", crop), ("farmer_id", farmer_id), ("status", status)) if v}
    return await db().list("lots", flt, limit=limit, skip=skip)


@api.post("/demands")
async def create_demand(d: DemandIn, u: Optional[dict] = Depends(user_dep)):
    require_owner(u, d.buyer_id)
    check_crop_market(d.crop)
    buyer = need(await db().get("buyers", d.buyer_id), "Buyer")
    doc = {"id": new_id("demand"), **d.model_dump(), "location": d.location.as_loc(),
           "min_quantity_kg": d.min_quantity_kg or d.quantity_kg, "buyer_name": buyer["name"],
           "status": "open", "kind": "confirmed", "created_at": now_iso()}
    return await db().insert("demands", doc)


@api.get("/demands")
async def list_demands(crop: Optional[str] = None, buyer_id: Optional[str] = None, status: Optional[str] = "open",
                       skip: int = Query(default=0, ge=0), limit: int = Query(default=200, ge=1, le=200)):
    flt = {k: v for k, v in (("status", status), ("crop", crop), ("buyer_id", buyer_id)) if v}
    return await db().list("demands", flt, limit=limit, skip=skip)


# ---------------------------------------------------------------- MAIN DECISION ENGINE
async def _offers_for_lot(lot, fair_price):
    demands = await db().list("demands", {"status": "open", "crop": lot["crop"]})
    rels = {}
    for d in demands:
        bid = d.get("buyer_id")
        if bid and bid not in rels:
            rels[bid] = await buyer_reliability(bid)
    return matching.rank_offers(lot, demands, fair_price, rels)


@api.post("/decision/net-profit")
async def decision(req: DecisionIn):
    """Sell now vs wait vs buyer offers -> estimated net proceeds (downside/base/best)."""
    check_crop_market(req.crop, req.market)
    series, meta = await get_series_meta(req.crop, req.market)
    fc = STATE["forecaster"].forecast(req.crop, req.market, series)
    fc.update(meta)
    price = req.current_price or fc["current_price"]
    offers = []
    if req.lot_id:
        lot = need(await db().get("lots", req.lot_id), "Lot")
        offers = await _offers_for_lot(lot, price)
    for o in req.offers or []:
        offers.append(o.model_dump() if hasattr(o, "model_dump") else o)

    temp, wx = await resolve_temp(req.temperature_c, req.farmer_location.as_loc() if req.farmer_location else req.market)
    heat = 1.0 + max(0.0, temp - 25) * 0.06
    if req.farmer_location:
        for o in offers:
            if "distance_km" not in o and o.get("location"):
                o["distance_km"] = haversine_km(req.farmer_location.as_loc(), o["location"])
    result = netprofit.decide(req.crop, req.quantity_kg, req.grade, price, fc, offers, req.costs, heat,
                              spoilage_per_day=req.spoilage_per_day)
    result["forecast"] = fc
    result["weather"] = wx
    result["matched_offers"] = offers
    result.update(meta)
    return result



# ---------------------------------------------------------------- matching & pooling
@api.get("/lots/{lot_id}/offers")
async def lot_offers(lot_id: str):
    lot = need(await db().get("lots", lot_id), "Lot")
    fc = STATE["forecaster"].forecast(lot["crop"], "Dhaka", await get_series(lot["crop"], "Dhaka"))
    return await _offers_for_lot(lot, fc["current_price"])


@api.post("/pool/plan")
async def pool_plan(p: PoolIn):
    demand = need(await db().get("demands", p.demand_id), "Demand")
    all_lots = []
    skip = 0
    limit = 200
    while True:
        batch = await db().list("lots", {"crop": demand["crop"], "status": "open"}, limit=limit, skip=skip)
        all_lots.extend(batch)
        if len(batch) < limit:
            break
        skip += limit
    return pooling.plan_pool(demand, all_lots, harvest_window_days=p.harvest_window_days)


# ---------------------------------------------------------------- orders / evidence / payment
@api.post("/orders")
async def create_order(o: OrderIn, u: Optional[dict] = Depends(user_dep)):
    demand = need(await db().get("demands", o.demand_id), "Demand")
    if demand.get("status") != "open":
        raise HTTPException(409, f"Demand is not open (status: '{demand.get('status')}')")
    if o.agreed_price <= 0:
        raise HTTPException(422, "agreed_price must be > 0")
    if not o.allocations:
        raise HTTPException(422, "allocations cannot be empty")

    lot_ids = [a.lot_id for a in o.allocations]
    if len(lot_ids) != len(set(lot_ids)):
        raise HTTPException(422, "Duplicate lot_id in allocations")

    demand_crop = demand.get("crop")
    demand_rank = GRADE_RANK.get(str(demand.get("min_grade", "C")).upper(), 1)
    demand_max_dist = demand.get("max_distance_km", 300.0)

    # Authorization: farmer cannot allocate other farmer's lots
    u_role = u.get("role") if u else None
    u_sub = u.get("sub") if u else None
    is_buyer_or_admin = (u_role == "admin" or (u_role == "buyer" and u_sub == demand.get("buyer_id")))

    allocs = []
    total_allocated = 0.0

    for a in o.allocations:
        if a.allocated_kg <= 0:
            raise HTTPException(422, "allocated_kg must be > 0")
        lot = need(await db().get("lots", a.lot_id), f"Lot {a.lot_id}")
        if lot.get("status") != "open":
            raise HTTPException(409, t("err.lot_closed", status=lot.get("status")))
        if lot.get("crop") != demand_crop:
            raise HTTPException(422, f"Lot crop '{lot.get('crop')}' differs from demand crop '{demand_crop}'")
        lot_rank = GRADE_RANK.get(str(lot.get("grade", "C")).upper(), 1)
        if lot_rank < demand_rank:
            raise HTTPException(422, f"Lot grade '{lot.get('grade')}' is below demand min_grade '{demand.get('min_grade')}'")
        dist = haversine_km(lot.get("location"), demand.get("location"))
        if demand_max_dist is not None and dist > demand_max_dist:
            raise HTTPException(422, f"Distance {dist:.1f} km exceeds max_distance_km {demand_max_dist} km")
        if a.allocated_kg > lot["quantity_kg"]:
            raise HTTPException(422, t("err.lot_over"))

        lot_farmer_id = lot.get("farmer_id")
        if not is_buyer_or_admin:
            if u_role != "farmer" or u_sub != lot_farmer_id:
                raise HTTPException(403, "Farmers can only allocate their own lots")

        allocs.append({
            "lot_id": a.lot_id,
            "allocated_kg": a.allocated_kg,
            "farmer_id": lot_farmer_id,
            "status": "confirmed",
            "_lot_orig": lot
        })
        total_allocated += a.allocated_kg

    min_q = float(demand.get("min_quantity_kg") or 0.0)
    max_q = float(demand.get("quantity_kg", 0.0))
    if total_allocated < min_q or total_allocated > max_q:
        raise HTTPException(422, f"Total allocated kg ({total_allocated}) must be between {min_q} and {max_q}")

    # Reserve lots atomically with update_if(status='open' -> 'reserved')
    reserved_lot_ids = []
    for a in allocs:
        res = await db().update_if("lots", a["lot_id"], {"status": "open"}, {"status": "reserved"})
        if not res:
            for rid in reserved_lot_ids:
                await db().update("lots", rid, {"status": "open"})
            raise HTTPException(409, f"Lot {a['lot_id']} could not be reserved (no longer open)")
        reserved_lot_ids.append(a["lot_id"])

    # Atomically mark demand filled
    demand_filled = await db().update_if("demands", o.demand_id, {"status": "open"}, {"status": "filled"})
    if not demand_filled:
        for rid in reserved_lot_ids:
            await db().update("lots", rid, {"status": "open"})
        raise HTTPException(409, "Demand is no longer open")

    # Split lots: when allocated_kg < lot quantity, keep open remainder lot (documented in REQ-Q-05)
    for a in allocs:
        orig = a["_lot_orig"]
        remainder_kg = round(orig["quantity_kg"] - a["allocated_kg"], 3)
        if remainder_kg > 0:
            await db().update("lots", a["lot_id"], {"quantity_kg": a["allocated_kg"]})
            rem_lot = {
                **orig,
                "id": new_id("lot"),
                "quantity_kg": remainder_kg,
                "status": "open",
                "created_at": now_iso()
            }
            await db().insert("lots", rem_lot)
        del a["_lot_orig"]

    doc = {
        "id": new_id("order"),
        "demand_id": o.demand_id,
        "buyer_id": demand["buyer_id"],
        "crop": demand["crop"],
        "allocations": allocs,
        "agreed_price": o.agreed_price,
        "batch_ids": o.batch_ids,
        "total_kg": total_allocated,
        "status": "confirmed",
        "payment": {"status": "pending", "simulated": True},
        "dispute_status": None,
        "created_at": now_iso()
    }
    return await db().insert("orders", doc)


@api.get("/orders/{oid}")
async def get_order(oid: str, u: Optional[dict] = Depends(user_dep)):
    order = need(await db().get("orders", oid), "Order")
    require_party(u, *order_parties(order))
    return localize_order(order)


@api.post("/orders/{oid}/delivery")
async def record_delivery(oid: str, d: DeliveryIn, u: Optional[dict] = Depends(user_dep)):
    order = need(await db().get("orders", oid), "Order")
    require_owner(u, order["buyer_id"])
    if order.get("status") != "confirmed":
        raise HTTPException(409, f"Delivery can only be recorded for confirmed orders (current: {order.get('status')})")

    batch = None
    if order.get("batch_ids"):
        batch = await db().get("batches", order["batch_ids"][0])
    batch = batch or {"quantity_kg": order["total_kg"], "grade": None}
    report = disp.build_report(batch, order, d.model_dump())

    # Never overwrite an existing dispute_status that an admin resolved
    existing_dispute = order.get("dispute_status")
    resolved_outcomes = {"resolved_for_buyer", "resolved_against_buyer", "resolved_split", "no_fault"}
    if existing_dispute in resolved_outcomes:
        new_dispute = existing_dispute
    else:
        new_dispute = "open_for_review" if report["needs_human_review"] else None

    upd = {
        "delivery": d.model_dump(),
        "evidence_report": report,
        "status": "delivered",
        "dispute_status": new_dispute
    }
    res = await db().update_if("orders", oid, {"status": "confirmed"}, upd)
    if not res:
        raise HTTPException(409, "Order status is no longer confirmed")
    return localize_order(res)


@api.get("/orders/{oid}/evidence")
async def evidence(oid: str, u: Optional[dict] = Depends(user_dep)):
    order = need(await db().get("orders", oid), "Order")
    require_party(u, *order_parties(order))
    return disp.render(need(order.get("evidence_report"), "Evidence report"))


@api.post("/orders/{oid}/dispute/resolve")
async def resolve_dispute(oid: str, outcome: str = Query(description="resolved_for_buyer | resolved_against_buyer | resolved_split | no_fault"),
                          u: Optional[dict] = Depends(user_dep)):
    """Used by the human reviewer (admin)."""
    require_role(u, "admin")
    valid_outcomes = {"resolved_for_buyer", "resolved_against_buyer", "resolved_split", "no_fault"}
    if outcome not in valid_outcomes:
        raise HTTPException(422, f"Invalid dispute outcome: '{outcome}'. Expected one of {sorted(valid_outcomes)}")
    order = need(await db().get("orders", oid), "Order")
    if order.get("dispute_status") != "open_for_review":
        raise HTTPException(409, f"Order dispute_status must be 'open_for_review' to resolve (current: '{order.get('dispute_status')}')")
    res = await db().update_if("orders", oid, {"dispute_status": "open_for_review"}, {"dispute_status": outcome})
    if not res:
        raise HTTPException(409, "Dispute is no longer open for review")
    return res


@api.post("/orders/{oid}/payment")
async def payment(oid: str, p: PaymentIn, u: Optional[dict] = Depends(user_dep)):
    """SIMULATED escrow (bKash/Nagad sandbox can be connected later). fund/release: buyer; refund: admin; cancel: any party of the order."""
    order = need(await db().get("orders", oid), "Order")
    buyer_id, farmer_ids = order_parties(order)
    if p.action in ("fund", "release"):
        require_owner(u, buyer_id)
    elif p.action == "refund":
        require_role(u, "admin")
    elif p.action == "cancel":
        require_party(u, buyer_id, farmer_ids)
    else:
        raise HTTPException(422, t("err.pay_action"))

    pay = dict(order.get("payment", {}))
    current_pay_status = pay.get("status")
    current_order_status = order.get("status")

    if p.action == "cancel":
        # cancel : only while the order is confirmed and payment is pending or funded, never from delivered / completed / cancelled
        if current_order_status != "confirmed":
            raise HTTPException(409, f"Cannot cancel order in status '{current_order_status}'. Cancellation is only allowed for confirmed orders.")
        if current_pay_status not in ("pending", "funded"):
            raise HTTPException(409, f"Cannot cancel order with payment status '{current_pay_status}'.")

        caller_role = (u.get("role") if u else "buyer")
        upd = {
            "status": "cancelled",
            "cancelled_by": caller_role,
            "payment": {**pay, "status": "cancelled", "updated_at": now_iso()}
        }
        res = await db().update_if("orders", oid, {"status": "confirmed"}, upd)
        if not res:
            raise HTTPException(409, "Order could not be cancelled (concurrent status change)")

        # Re-open only lots still reserved and re-open the demand
        for a in order.get("allocations", []):
            await db().update_if("lots", a["lot_id"], {"status": "reserved"}, {"status": "open"})
        await db().update_if("demands", order["demand_id"], {"status": "filled"}, {"status": "open"})
        return res

    if p.action == "fund":
        # fund : pending to funded
        if current_pay_status != "pending":
            raise HTTPException(409, t("err.pay_state", status=current_pay_status, action="fund"))
        new_pay = {**pay, "status": "funded", "updated_at": now_iso()}
        res = await db().update_if("orders", oid, {"payment.status": "pending"}, {"payment": new_pay})
        if not res:
            raise HTTPException(409, "Payment could not be funded (concurrent update)")
        return res

    if p.action == "refund":
        # refund : funded to refunded (admin)
        if current_pay_status != "funded":
            raise HTTPException(409, t("err.pay_state", status=current_pay_status, action="refund"))
        new_pay = {**pay, "status": "refunded", "updated_at": now_iso()}
        res = await db().update_if("orders", oid, {"payment.status": "funded"}, {"payment": new_pay})
        if not res:
            raise HTTPException(409, "Payment could not be refunded (concurrent update)")
        return res

    if p.action == "release":
        # release : funded to released only when status is delivered or confirmed
        if current_order_status not in ("delivered", "confirmed"):
            raise HTTPException(409, f"Cannot release payment for order in status '{current_order_status}'. Must be delivered or confirmed.")
        if current_pay_status != "funded":
            raise HTTPException(409, t("err.pay_state", status=current_pay_status, action="release"))

        # on_time is accepted only from admin, otherwise stored as null and treated as on time until REQ-Q defines a due date
        payment_on_time = p.on_time if (u and u.get("role") == "admin") else None
        new_pay = {**pay, "status": "released", "updated_at": now_iso()}
        upd = {
            "status": "completed",
            "payment_on_time": payment_on_time,
            "payment": new_pay
        }
        res = await db().update_if("orders", oid, {"payment.status": "funded"}, upd)
        if not res:
            raise HTTPException(409, "Payment already released or order no longer funded")

        # Mark lots sold
        for a in order.get("allocations", []):
            await db().update_if("lots", a["lot_id"], {"status": "reserved"}, {"status": "sold"})
        return res


# ---------------------------------------------------------------- loss / radar / assistant
@api.post("/loss/assess")
async def loss_assess(l: LossIn):
    check_crop_market(l.crop)
    temp, wx = await resolve_temp(l.temperature_c, l.district or "Dhaka")
    r = lossmod.assess(l.crop, l.hours_since_harvest, temp, l.distance_km, l.hours_to_deadline)
    r["weather"] = wx
    return r


@api.get("/demand-radar")
async def demand_radar(crop: Optional[str] = None):
    crops = [crop] if crop else CROPS
    out = []
    for c in crops:
        demands = await db().list("demands", {"crop": c, "status": "open"}, 500)
        lots = await db().list("lots", {"crop": c, "status": "open"}, 500)
        confirmed = sum(d["quantity_kg"] for d in demands)
        supply = sum(l["quantity_kg"] for l in lots)
        done = await db().list("orders", {"crop": c, "status": "completed"}, 2000)
        ratio = (supply / confirmed) if confirmed else None
        risk = "unknown" if ratio is None and supply == 0 else "high" if (ratio is None or ratio > 1.5) else "medium" if ratio > 1.1 else "low"
        out.append({"crop": c, "confirmed_demand_kg": confirmed, "open_supply_kg": supply, "oversupply_risk": risk,
                    "predicted_demand": demandmod.predict(done),
                    "data_freshness": now_iso()})
    return out


@api.post("/assistant/chat")
async def chat(m: ChatIn):
    """Text assistant. Supports Google Gemini API if configured, with intelligent conversational fallback."""
    user_text = (m.text or m.message or "").strip()
    p = asst.parse(user_text)
    qty = p["quantity_kg"] or m.quantity_kg
    crop = p["crop"]

    # 1. Price, sell/wait, negotiate, and loss intents MUST come from real engines (bypass LLM)
    if crop and p["intent"] in ("price", "sell", "negotiate", "loss"):
        cname = i18n.crop_name(crop)
        fc = STATE["forecaster"].forecast(crop, m.market, await get_series(crop, m.market))
        if p["intent"] == "price":
            return {"reply": asst.fmt_forecast(crop, fc), "source": "rule_based", "parsed": p, "data": fc}
        if p["intent"] == "negotiate":
            if not qty:
                return {"reply": t("chat.ask_qty_neg", crop=cname), "source": "rule_based", "parsed": p, "data": None}
            res = negotiation.counter_offers(crop, qty, m.grade, fc["current_price"], fc,
                                             [{"price_per_kg": p.get("offer_price", 0), "distance_km": 20}])
            o = res["offers"][0]
            txt = t("chat.neg", min=f"{res['minimum_acceptable_price_per_kg']:.0f}", offer=f"{o['offer_price']:.0f}")
            txt += t("chat.neg_accept") if o["action"] == "accept" else t("chat.neg_counter", counter=f"{o['suggested_counter_price']:.0f}")
            return {"reply": txt, "source": "rule_based", "parsed": p, "data": res}
        if p["intent"] == "loss":
            # Extract hours, distance, and temperature from user text if present
            hours_match = re.search(r"(\d+(?:\.\d+)?)\s*(ঘণ্টা|ঘন্টা|hour|hr|h)\b", user_text.lower())
            dist_match = re.search(r"(\d+(?:\.\d+)?)\s*(কিমি|km|কিলোমিটার|kilometer)\b", user_text.lower())
            temp_match = re.search(r"(\d+(?:\.\d+)?)\s*(ডিগ্রি|degree|c|°c)\b", user_text.lower())
            if hours_match and dist_match and temp_match:
                h = float(hours_match.group(1))
                d = float(dist_match.group(1))
                t_c = float(temp_match.group(1))
                r = lossmod.assess(crop, h, t_c, d)
                return {"reply": t("chat.loss", crop=cname, risk=t("risk." + r["risk_level"])), "source": "rule_based", "parsed": p, "data": r}
            else:
                if i18n.current_lang() == "bn":
                    ask = f"{cname} তোলার পর কত ঘণ্টা হয়েছে, পরিবহন দূরত্ব (কিমি) এবং তাপমাত্রা (°C) কত জানাবেন কি?"
                else:
                    ask = f"Could you please specify how many hours since harvest, transport distance (km), and temperature (°C) for {cname}?"
                return {"reply": ask, "source": "rule_based", "parsed": p, "data": None}
        if not qty:
            return {"reply": t("chat.ask_qty", crop=cname), "source": "rule_based", "parsed": p, "data": None}
        dec = netprofit.decide(crop, qty, m.grade, fc["current_price"], fc)
        return {"reply": asst.fmt_decision(crop, dec, qty), "source": "rule_based", "parsed": p, "data": dec}

    # 2. Greeting / general intents: use Gemini if key configured, passing grounded context
    if settings.GEMINI_API_KEY:
        context = {"market": m.market, "crop": crop, "quantity_kg": qty, "grade": m.grade}
        if crop:
            try:
                fc_ctx = STATE["forecaster"].forecast(crop, m.market, await get_series(crop, m.market))
                context["current_price"] = fc_ctx.get("current_price")
                context["trend"] = fc_ctx.get("trend")
            except Exception:
                pass
        gemini_reply = await asyncio.to_thread(
            asst.ask_gemini,
            user_text,
            context=context,
            lang=i18n.current_lang()
        )
        if gemini_reply:
            return {"reply": gemini_reply, "source": "gemini", "parsed": p, "data": None}

    # 3. Conversational fallback (Greetings & General queries without LLM)
    if p["intent"] == "greeting":
        if i18n.current_lang() == "bn":
            reply = "আলহামদুলিল্লাহ, আমি ভালো আছি! আমি আপনার ক্রপলিংক কৃষি সহকারী। আপনি ফসল বিক্রির সিদ্ধান্ত, বাজার দর, পচন রোধ বা বায়ারের সাথে দর-কষাকষি সম্পর্কে যেকোনো প্রশ্ন করতে পারেন।"
        else:
            reply = "Hello! I am doing well, thank you. I am your CropLink Agri Assistant. How can I assist you with crop prices or selling decisions today?"
        return {"reply": reply, "source": "rule_based", "parsed": p, "data": None}

    if not crop:
        if i18n.current_lang() == "bn":
            reply = "আমি ক্রপলিংক এআই সহকারী। আপনি জানতে চাইতে পারেন:\n• 'টমেটোর আজকের দাম কত?'\n• '৫০০ কেজি আলু এখন বেচব না অপেক্ষা করব?'\n• 'গরম আবহাওয়ায় পেঁয়াজ নষ্ট হওয়ার ঝুঁকি কত?'\n• 'বায়ার ৪৫ টাকা অফার করছে, কী করব?'"
        else:
            reply = "I am CropLink AI Assistant. You can ask:\n• 'What is today's tomato price?'\n• 'Should I sell 500kg potato now or wait?'\n• 'What is the spoilage risk in hot weather?'"
        return {"reply": reply, "source": "rule_based", "parsed": p, "data": None}

    reply = "I am your CropLink Assistant. Ask about prices, selling decisions, or spoilage."
    return {"reply": reply, "source": "rule_based", "parsed": p, "data": None}


# ---------------------------------------------------------------- negotiation / alerts / weather
@api.post("/negotiation/counter-offer")
async def counter_offer(n: NegotiateIn):
    """Minimum acceptable price + counter-offer drafts (Bangla and English) for buyer offers."""
    check_crop_market(n.crop, n.market)
    fc = STATE["forecaster"].forecast(n.crop, n.market, await get_series(n.crop, n.market))
    offers = [o.model_dump() if hasattr(o, "model_dump") else o for o in (n.offers or [])]
    if n.lot_id:
        lot = need(await db().get("lots", n.lot_id), "Lot")
        offers += await _offers_for_lot(lot, fc["current_price"])
    temp, wx = await resolve_temp(n.temperature_c, n.market)
    heat = 1.0 + max(0.0, temp - 25) * 0.06
    for o in offers:
        if "price_per_kg" not in o:
            raise HTTPException(422, t("err.offer_price"))
    r = negotiation.counter_offers(n.crop, n.quantity_kg, n.grade, fc["current_price"], fc, offers, n.costs, heat,
                                   n.spoilage_per_day, n.margin_pct, n.production_cost_per_kg)
    r["weather"] = wx
    return r


@api.get("/alerts/price")
async def price_alert(crop: str, market: str = "Dhaka", spike_pct: float = 10, forecast_pct: float = 7):
    check_crop_market(crop, market)
    series = await get_series(crop, market)
    fc = STATE["forecaster"].forecast(crop, market, series)
    return alertmod.compute(crop, market, fc, series, spike_pct, forecast_pct)


@api.get("/alerts/scan")
async def alerts_scan(spike_pct: float = 10, forecast_pct: float = 7):
    """Scans all crop x market pairs and returns only those with an alert."""
    out = []
    for c in CROPS:
        for m in MARKETS:
            series = await get_series(c, m)
            if len(series) < MIN_HISTORY:
                continue
            a = alertmod.compute(c, m, STATE["forecaster"].forecast(c, m, series), series, spike_pct, forecast_pct)
            if a["has_alert"]:
                out.append(a)
    return {"count": len(out), "alerts": out}


@api.post("/alerts/watch")
async def alerts_watch(w: WatchIn, u: Optional[dict] = Depends(user_dep)):
    require_owner(u, w.farmer_id)
    check_crop_market(w.crop, w.market)
    need(await db().get("farmers", w.farmer_id), "Farmer")
    doc = {"id": f"{w.farmer_id}|{w.crop}|{w.market}", **w.model_dump(), "created_at": now_iso()}
    if await db().get("watches", doc["id"]):
        return await db().update("watches", doc["id"], {"threshold_pct": w.threshold_pct})
    return await db().insert("watches", doc)


@api.get("/alerts/farmer/{farmer_id}")
async def farmer_alerts(farmer_id: str, u: Optional[dict] = Depends(user_dep)):
    require_owner(u, farmer_id)
    """Alerts for the crops/markets a farmer watches. The app polls this and shows notifications."""
    watches = await db().list("watches", {"farmer_id": farmer_id}, 100)
    out = []
    for w in watches:
        series = await get_series(w["crop"], w["market"])
        fc = STATE["forecaster"].forecast(w["crop"], w["market"], series)
        a = alertmod.compute(w["crop"], w["market"], fc, series, w["threshold_pct"] + 3, w["threshold_pct"])
        out.append(a)
    return {"watching": len(watches), "results": out, "alerts_count": sum(1 for a in out if a["has_alert"])}


@api.get("/weather")
async def get_weather_ep(district: str = "Dhaka"):
    w = await weather.get_weather(district)
    if not w:
        return {"available": False, "reason": weather.LAST_ERROR["msg"]}
    return {"available": True, **w}


# ---------------------------------------------------------------- extra: lists, history, dashboards, photo->batch, admin
def make_thumb(data: bytes, max_side: int = 480) -> str:
    from .ml.grader import safe_open_image
    try:
        img = safe_open_image(data)
        img.thumbnail((max_side, max_side))
        for q in (75, 60, 45):
            buf = io.BytesIO()
            img.save(buf, "JPEG", quality=q)
            if buf.tell() <= 300_000:
                break
        return base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return ""


@api.post("/batches/from-photo")
async def batch_from_photo(file: UploadFile = File(...), farmer_id: Optional[str] = Form(None), crop: str = Form("tomato"),
                           quantity_kg: Optional[float] = Form(None), district: Optional[str] = Form(None),
                           lat: Optional[float] = Form(None), lon: Optional[float] = Form(None),
                           harvest_date: Optional[str] = Form(None), u: Optional[dict] = Depends(user_dep)):
    """ONE CALL: photo -> grade -> save thumbnail -> batch + QR hash (for the Capture + Grade + Batch screens)."""
    fid = farmer_id or (u.get("sub") if u else None)
    if not fid:
        fid = "farmer_default" if not settings.AUTH_REQUIRED else None
    if not fid:
        raise HTTPException(401, t("err.login"))
    require_owner(u, fid)
    need(await db().get("farmers", fid), "Farmer")
    check_crop_market(crop)
    if quantity_kg is None or quantity_kg <= 0:
        raise HTTPException(422, t("err.qty"))
    if not district and (lat is None or lon is None):
        raise HTTPException(422, "District or lat/lon required")

    chunks = []
    total = 0
    max_size = 20 * 1024 * 1024
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > max_size:
            raise HTTPException(413, t("err.img_big"))
        chunks.append(chunk)
    data = b"".join(chunks)
    if len(data) == 0:
        raise HTTPException(422, t("err.img_bad"))

    if "grader" not in STATE or STATE["grader"] is None:
        raise HTTPException(503, "Grader model not available")

    try:
        grading = await asyncio.to_thread(STATE["grader"].grade_bytes, data, crop)
        thumb = await asyncio.to_thread(make_thumb, data)
    except ImageDecodeError:
        raise HTTPException(422, t("err.img_bad"))

    loc = {"lat": lat, "lon": lon} if lat is not None and lon is not None else district
    doc = {"id": new_id("batch"), "farmer_id": fid, "crop": crop, "quantity_kg": quantity_kg, "location": loc,
           "harvest_date": harvest_date or date.today().isoformat(), "grade": grading.get("grade", "B"),
           "grade_confidence": grading.get("confidence", 0.85), "photo_base64": thumb, "photo_url": None, "created_at": now_iso()}
    core = {k: doc[k] for k in ("id", "farmer_id", "crop", "quantity_kg", "harvest_date", "grade", "created_at")}
    doc["passport_hash"] = hashlib.sha256(json.dumps(core, sort_keys=True).encode()).hexdigest()
    await db().insert("batches", doc)
    return {"grading": grading, "batch": {k: v for k, v in doc.items() if k != "photo_base64"}, "has_photo": bool(thumb)}



@api.get("/batches")
async def list_batches(farmer_id: Optional[str] = None,
                       skip: int = Query(default=0, ge=0), limit: int = Query(default=200, ge=1, le=200)):
    """Light list without photos. Use GET /batches/{id} for the photo."""
    items = await db().list("batches", {"farmer_id": farmer_id} if farmer_id else {}, limit=limit, skip=skip)
    return [{**{k: v for k, v in b.items() if k != "photo_base64"}, "has_photo": bool(b.get("photo_base64"))} for b in items]


@api.get("/batches/{bid}")
async def get_batch(bid: str):
    return need(await db().get("batches", bid), "Batch")


@api.get("/lots/{lot_id}")
async def get_lot(lot_id: str):
    return need(await db().get("lots", lot_id), "Lot")


@api.post("/lots/{lot_id}/withdraw")
async def withdraw_lot(lot_id: str, u: Optional[dict] = Depends(user_dep)):
    lot = need(await db().get("lots", lot_id), "Lot")
    require_owner(u, lot["farmer_id"])
    if lot["status"] != "open":
        raise HTTPException(409, t("err.lot_closed", status=lot["status"]))
    return await db().update("lots", lot_id, {"status": "withdrawn"})


@api.get("/demands/{demand_id}")
async def get_demand(demand_id: str):
    return need(await db().get("demands", demand_id), "Demand")


@api.post("/demands/{demand_id}/close")
async def close_demand(demand_id: str, u: Optional[dict] = Depends(user_dep)):
    d = need(await db().get("demands", demand_id), "Demand")
    require_owner(u, d["buyer_id"])
    if d["status"] != "open":
        raise HTTPException(409, t("err.demand_closed", status=d["status"]))
    return await db().update("demands", demand_id, {"status": "closed"})


@api.get("/orders")
async def list_orders(farmer_id: Optional[str] = None, buyer_id: Optional[str] = None, status: Optional[str] = None,
                      skip: int = Query(default=0, ge=0), limit: int = Query(default=200, ge=1, le=200),
                      u: Optional[dict] = Depends(user_dep)):
    """Own orders. Farmers/buyers see their own; admin sees all (with filters)."""
    if isinstance(u, dict) and u.get("role") != "admin":
        if u["role"] == "farmer":
            farmer_id = u["sub"]
        else:
            buyer_id = u["sub"]
    flt = {k: v for k, v in (("buyer_id", buyer_id), ("status", status)) if v}
    if farmer_id:
        flt["allocations.farmer_id"] = farmer_id
    orders = await db().list("orders", flt, limit=limit, skip=skip)
    return [localize_order(o) for o in orders]


@api.get("/prices/history")
async def price_history(crop: str, market: str = "Dhaka", days: int = 60):
    """Day-by-day prices for charts."""
    check_crop_market(crop, market)
    series, meta = await get_series_meta(crop, market)
    sub = series[-max(1, min(days, 120)):]
    prices = [p for _, p in sub]
    resp = {
        "crop": crop,
        "market": market,
        "points": [{"date": d, "price": round(p, 2)} for d, p in sub],
        "latest": round(prices[-1], 2) if prices else 0.0,
        "min": round(min(prices), 2) if prices else 0.0,
        "max": round(max(prices), 2) if prices else 0.0,
        "avg": round(sum(prices) / len(prices), 2) if prices else 0.0,
    }
    resp.update(meta)
    return resp


@api.get("/prices/today")
async def prices_today(market: str = "Dhaka"):
    """Market screen: today's price of every crop + 1d/7d change + 7-day forecast trend."""
    check_crop_market("tomato", market)
    out = []
    first_meta = None
    for c in CROPS:
        series, meta = await get_series_meta(c, market)
        if first_meta is None:
            first_meta = meta
        fc = STATE["forecaster"].forecast(c, market, series)
        pr = [p for _, p in series]
        change_1d = round((pr[-1] / pr[-2] - 1) * 100, 1) if len(pr) >= 2 and pr[-2] > 0 else None
        change_7d = round((pr[-1] / pr[-8] - 1) * 100, 1) if len(pr) >= 8 and pr[-8] > 0 else None
        item = {
            "crop": c,
            "market": market,
            "price": fc["current_price"],
            "price_bdt_kg": round(fc["current_price"], 1),
            "change_1d_pct": change_1d,
            "change_7d_pct": change_7d,
            "change_pct": change_1d,
            "forecast_7d_base": fc["h7"]["base"],
            "trend": fc["trend"]
        }
        item.update(meta)
        out.append(item)
    resp = {"market": market, "prices": out, "note": t("fc.note")}
    if first_meta:
        resp.update(first_meta)
    return resp



@api.get("/dashboard/farmer/{farmer_id}")
async def farmer_dashboard(farmer_id: str, u: Optional[dict] = Depends(user_dep)):
    """Farmer home screen: everything in one call."""
    require_owner(u, farmer_id)
    farmer = need(await db().get("farmers", farmer_id), "Farmer")
    lots = await db().list("lots", {"farmer_id": farmer_id}, 500)
    orders = await db().list("orders", {"allocations.farmer_id": farmer_id}, 1000)
    open_lots = []
    for l in [x for x in lots if x["status"] == "open"][:5]:
        fc = STATE["forecaster"].forecast(l["crop"], "Dhaka", await get_series(l["crop"], "Dhaka"))
        offers = await _offers_for_lot(l, fc["current_price"])
        open_lots.append({"lot_id": l["id"], "crop": l["crop"], "quantity_kg": l["quantity_kg"], "grade": l["grade"],
                          "offers_count": len(offers), "best_offer": offers[0] if offers else None})
    al = await farmer_alerts(farmer_id, u)
    gross = sum(a["allocated_kg"] * o["agreed_price"] for o in orders if o["status"] == "completed"
                for a in o["allocations"] if a.get("farmer_id") == farmer_id)
    return {"farmer": farmer, "lots_by_status": dict(Counter(l["status"] for l in lots)),
            "orders_by_status": dict(Counter(o["status"] for o in orders)),
            "active_orders": [o["id"] for o in orders if o["status"] in ("confirmed", "delivered")],
            "open_lots": open_lots, "watching": al["watching"], "alerts_count": al["alerts_count"],
            "gross_sales_completed": round(gross), "note": t("dash.gross")}


@api.get("/dashboard/buyer/{buyer_id}")
async def buyer_dashboard(buyer_id: str, u: Optional[dict] = Depends(user_dep)):
    require_owner(u, buyer_id)
    buyer = need(await db().get("buyers", buyer_id), "Buyer")
    demands = await db().list("demands", {"buyer_id": buyer_id}, 500)
    orders = await db().list("orders", {"buyer_id": buyer_id}, 1000)
    return {"buyer": buyer, "reliability": reliability.score_buyer(orders),
            "demands_by_status": dict(Counter(d["status"] for d in demands)),
            "orders_by_status": dict(Counter(o["status"] for o in orders)),
            "open_demands": [d for d in demands if d["status"] == "open"][:10]}


@api.get("/dashboard/admin")
async def admin_dashboard(u: Optional[dict] = Depends(user_dep)):
    require_role(u, "admin")
    users = await db().list("users", {}, 5000)
    orders = await db().list("orders", {}, 2000)
    return {"users_by_role": dict(Counter(x["role"] for x in users)),
            "orders_by_status": dict(Counter(o["status"] for o in orders)),
            "disputes_open": [{"order_id": o["id"], "buyer_id": o["buyer_id"], "flags": disp.render(o.get("evidence_report", {"items": []}))["discrepancies"]}
                              for o in orders if o.get("dispute_status") == "open_for_review"],
            "lots_open": len(await db().list("lots", {"status": "open"}, 5000)),
            "demands_open": len(await db().list("demands", {"status": "open"}, 5000)),
            "database": db().kind}


@api.post("/admin/seed-demo")
async def admin_seed_demo(u: Optional[dict] = Depends(user_dep)):
    """Demo accounts + sample data (idempotent). Normally done at startup with SEED_DEMO=true."""
    require_role(u, "admin")
    return await seed.seed_demo(db())


app.include_router(public)
app.include_router(api)
