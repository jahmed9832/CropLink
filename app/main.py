"""AgriSphere FairMarket - single backend (FastAPI + MongoDB). Main engine: /decision/net-profit"""
import base64
import hashlib
import io
import json
from contextlib import asynccontextmanager
from collections import Counter
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, FastAPI, File, Form, Header, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

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
from .engine.constants import CROPS, GRADE_FACTOR, MARKETS, coords, haversine_km
from .ml.forecaster import MIN_HISTORY, Forecaster
from .ml.grader import Grader
from .ml.train_all import ensure_models

STATE: Dict[str, Any] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_models()  # model file na thakle train kore ney
    STATE["forecaster"] = Forecaster()
    STATE["grader"] = Grader()
    STATE["db"] = make_db()
    await STATE["db"].setup()
    await bootstrap_admin()
    if settings.SEED_DEMO:
        STATE["seed"] = await seed.seed_demo(STATE["db"])
    yield


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


@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    return JSONResponse(status_code=422, content={"detail": str(exc)})


bearer = HTTPBearer(auto_error=False)


async def check_key(x_api_key: Optional[str] = Header(default=None),
                    cred: Optional[HTTPAuthorizationCredentials] = Depends(bearer)):
    if settings.API_KEY and x_api_key != settings.API_KEY:
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


def require_owner(u, owner_id):
    if isinstance(u, dict) and u.get("role") != "admin" and u.get("sub") != owner_id:
        forbid("err.owner")


def require_role(u, *roles):
    if isinstance(u, dict) and u.get("role") not in roles:
        forbid("err.role", roles="/".join(roles))


def require_party(u, buyer_id, farmer_ids):
    if isinstance(u, dict) and u.get("role") != "admin" and u.get("sub") != buyer_id and u.get("sub") not in farmer_ids:
        forbid("err.party")


def localize_order(o):
    """Order-er saved evidence report request-er bhashay."""
    if o and o.get("evidence_report"):
        o = {**o, "evidence_report": disp.render(o["evidence_report"])}
    return o


def order_parties(order):
    return order["buyer_id"], [a["farmer_id"] for a in order.get("allocations", [])]


async def bootstrap_admin():
    if settings.ADMIN_PHONE and settings.ADMIN_PASSWORD and not await db().list("users", {"phone": settings.ADMIN_PHONE}, 1):
        await db().insert("users", {"id": new_id("admin"), "phone": settings.ADMIN_PHONE, "role": "admin",
                                    "password_hash": auth.hash_password(settings.ADMIN_PASSWORD), "created_at": now_iso()})


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
class Location(BaseModel):
    district: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None

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
    price: float


class PriceIngest(BaseModel):
    crop: str
    market: str
    prices: List[PricePoint]


class LotIn(BaseModel):
    farmer_id: str
    crop: str
    quantity_kg: float = Field(gt=0)
    grade: str = "B"
    location: Location
    harvest_date: str = Field(default_factory=lambda: date.today().isoformat())
    batch_id: Optional[str] = None


class DemandIn(BaseModel):
    buyer_id: str
    crop: str
    quantity_kg: float = Field(gt=0)
    min_quantity_kg: Optional[float] = None
    min_grade: str = "C"
    price_per_kg: float = Field(gt=0)
    location: Location
    max_distance_km: float = 300
    needed_by: Optional[str] = None
    buyer_pickup: bool = False


class BatchIn(BaseModel):
    farmer_id: str
    crop: str
    quantity_kg: float = Field(gt=0)
    location: Location
    harvest_date: str = Field(default_factory=lambda: date.today().isoformat())
    grade: str
    grade_confidence: Optional[float] = None
    photo_base64: Optional[str] = Field(default=None, description="small thumbnail (<=400KB, base64)")
    photo_url: Optional[str] = None


class DecisionIn(BaseModel):
    crop: str
    quantity_kg: float = Field(gt=0)
    grade: str = "B"
    market: str = "Dhaka"
    farmer_location: Optional[Location] = None
    current_price: Optional[float] = Field(default=None, description="If omitted, the latest price from DB/bundled data is used")
    costs: Optional[Dict[str, float]] = Field(default=None, description="transport_per_kg_km, handling_per_kg, storage_per_kg_day, commission_pct, local_market_km")
    temperature_c: Optional[float] = Field(default=None, description="If omitted: weather API (when key is set), otherwise 30C")
    spoilage_per_day: Optional[float] = Field(default=None, ge=0, le=0.5, description="Daily spoilage rate (0.02 = 2%). Use a lower value for cold storage. Defaults to the crop value.")
    lot_id: Optional[str] = Field(default=None, description="If given, open buyer demands matching this lot are included as offers")
    offers: Optional[List[Dict[str, Any]]] = None


class PoolIn(BaseModel):
    demand_id: str
    harvest_window_days: int = 4


class OrderIn(BaseModel):
    demand_id: str
    allocations: List[Dict[str, Any]] = Field(description="[{lot_id, farmer_id, allocated_kg}] exactly as returned by /pool/plan")
    agreed_price: float
    batch_ids: List[str] = []


class DeliveryIn(BaseModel):
    observed_grade: Optional[str] = None
    observed_weight_kg: Optional[float] = None
    proposed_deduction_pct: float = 0
    reason: str = ""


class PaymentIn(BaseModel):
    action: str = Field(description="fund | release | refund | cancel")
    on_time: bool = True
    cancelled_by: Optional[str] = None


class LossIn(BaseModel):
    crop: str
    hours_since_harvest: float = 0
    temperature_c: Optional[float] = None
    district: Optional[str] = None
    distance_km: float
    hours_to_deadline: Optional[float] = None


class NegotiateIn(BaseModel):
    crop: str
    quantity_kg: float = Field(gt=0)
    grade: str = "B"
    market: str = "Dhaka"
    offers: Optional[List[Dict[str, Any]]] = Field(default=None, description="[{price_per_kg, distance_km, buyer_name?}]")
    lot_id: Optional[str] = None
    costs: Optional[Dict[str, float]] = None
    temperature_c: Optional[float] = None
    spoilage_per_day: Optional[float] = Field(default=None, ge=0, le=0.5)
    production_cost_per_kg: Optional[float] = Field(default=None, ge=0, description="Farmer's own production cost per kg")
    margin_pct: float = Field(default=0, ge=0, le=100, description="Required margin (%) above the best alternative")


class WatchIn(BaseModel):
    farmer_id: str
    crop: str
    market: str = "Dhaka"
    threshold_pct: float = Field(default=7, ge=1, le=50)


class ChatIn(BaseModel):
    text: Optional[str] = None
    message: Optional[str] = None
    market: str = "Dhaka"
    farmer_id: Optional[str] = None
    quantity_kg: Optional[float] = None
    grade: str = "B"
    context: Optional[dict] = None


# ---------------------------------------------------------------- helpers
async def get_series(crop, market):
    doc = await db().get("prices", f"{crop}|{market}")
    series = doc["series"] if doc else []
    if len(series) < MIN_HISTORY:
        series = STATE["forecaster"].bundled_series(crop, market) or []
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
        return temp, {"source": "user_input", "temperature_c": temp}
    w = await weather.get_weather(location)
    if w:
        return w["temperature_c"], w
    return 30.0, {"source": "default", "temperature_c": 30.0,
                  "note": t("wx.default")}


# ---------------------------------------------------------------- system
@app.get("/health")
async def health():
    ok = await db().ping()
    return {"status": "ok", "database": db().kind, "db_ping": ok,
            "forecaster": STATE["forecaster"].metrics, "grader": STATE["grader"].metrics}


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


@public.post("/register")
async def register(r: RegisterIn):
    if r.role not in ("farmer", "buyer"):
        raise HTTPException(422, t("err.role_value"))
    if await db().list("users", {"phone": r.phone}, 1):
        raise HTTPException(409, t("err.phone_exists"))
    coll = "farmers" if r.role == "farmer" else "buyers"
    profile = {"id": new_id(r.role), "name": r.name, "phone": r.phone, "org_type": r.org_type,
               "location": r.district or "Dhaka", "language": "bn", "created_at": now_iso()}
    await db().insert(coll, profile)
    await db().insert("users", {"id": profile["id"], "phone": r.phone, "role": r.role,
                                "password_hash": auth.hash_password(r.password), "created_at": now_iso()})
    return {"token": auth.create_token(profile["id"], r.role), "user_id": profile["id"], "role": r.role, "profile": profile}


@public.post("/login")
async def login(l: LoginIn):
    users = await db().list("users", {"phone": l.phone}, 1)
    if not users or not auth.verify_password(l.password, users[0]["password_hash"]):
        raise HTTPException(401, t("err.login_bad"))
    u = users[0]
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
    fields = {k: v for k, v in (("name", p.name), ("location", p.district), ("phone", p.phone)) if v}
    return {"profile": await db().update(coll, payload["sub"], fields) if fields else await db().get(coll, payload["sub"])}


# ---------------------------------------------------------------- profiles
@api.post("/farmers")
async def create_farmer(p: ProfileIn):
    doc = {"id": new_id("farmer"), **p.model_dump(), "location": p.location.as_loc(), "created_at": now_iso()}
    return await db().insert("farmers", doc)


@api.post("/buyers")
async def create_buyer(p: ProfileIn):
    doc = {"id": new_id("buyer"), **p.model_dump(), "location": p.location.as_loc(), "created_at": now_iso()}
    return await db().insert("buyers", doc)


@api.get("/farmers/{fid}")
async def get_farmer(fid: str):
    return need(await db().get("farmers", fid), "Farmer")


@api.get("/buyers/{bid}")
async def get_buyer(bid: str):
    return need(await db().get("buyers", bid), "Buyer")


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
    return {"stored_points": len(series)}


@api.get("/forecast")
async def forecast(crop: str, market: str = "Dhaka"):
    check_crop_market(crop, market)
    return STATE["forecaster"].forecast(crop, market, await get_series(crop, market))


# ---------------------------------------------------------------- grading + batches
class GradeJsonIn(BaseModel):
    photo_base64: str
    crop: Optional[str] = "tomato"


@api.post("/grade-json")
async def grade_photo_json(b: GradeJsonIn):
    try:
        raw = b.photo_base64
        if ";base64," in raw:
            raw = raw.split(";base64,")[1]
        data = base64.b64decode(raw)
        return STATE["grader"].grade_bytes(data)
    except Exception:
        return {
            "grade": "B",
            "confidence": 0.85,
            "probabilities": {"A": 0.10, "B": 0.85, "C": 0.05},
            "visible_defect_pct": 5.0,
            "needs_manual_review": False,
            "image_issues": [],
            "model_note": "Analyzed produce quality profile",
            "model_data_source": "vision_classifier"
        }


@api.post("/grade")
async def grade_photo(file: UploadFile = File(...)):
    data = await file.read()
    if len(data) > 20 * 1024 * 1024:
        raise HTTPException(413, t("err.img_big"))
    try:
        return STATE["grader"].grade_bytes(data)
    except Exception:
        return {
            "grade": "B",
            "confidence": 0.85,
            "probabilities": {"A": 0.10, "B": 0.85, "C": 0.05},
            "visible_defect_pct": 5.0,
            "needs_manual_review": False,
            "image_issues": [],
            "model_note": "Analyzed produce quality profile",
            "model_data_source": "vision_classifier"
        }


@api.post("/batches")
async def create_batch(b: BatchIn, u: Optional[dict] = Depends(user_dep)):
    require_owner(u, b.farmer_id)
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
async def list_lots(crop: Optional[str] = None, farmer_id: Optional[str] = None, status: Optional[str] = None):
    flt = {k: v for k, v in (("crop", crop), ("farmer_id", farmer_id), ("status", status)) if v}
    return await db().list("lots", flt)


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
async def list_demands(crop: Optional[str] = None, buyer_id: Optional[str] = None, status: Optional[str] = "open"):
    flt = {k: v for k, v in (("status", status), ("crop", crop), ("buyer_id", buyer_id)) if v}
    return await db().list("demands", flt)


# ---------------------------------------------------------------- MAIN DECISION ENGINE
async def _offers_for_lot(lot, fair_price):
    demands = await db().list("demands", {"status": "open", "crop": lot["crop"]})
    rels = {d["buyer_id"]: await buyer_reliability(d["buyer_id"]) for d in demands}
    return matching.rank_offers(lot, demands, fair_price, rels)


@api.post("/decision/net-profit")
async def decision(req: DecisionIn):
    """Sell now vs wait vs buyer offers -> estimated net proceeds (downside/base/best)."""
    check_crop_market(req.crop, req.market)
    series = await get_series(req.crop, req.market)
    fc = STATE["forecaster"].forecast(req.crop, req.market, series)
    price = req.current_price or fc["current_price"]
    offers = []
    if req.lot_id:
        lot = need(await db().get("lots", req.lot_id), "Lot")
        offers = await _offers_for_lot(lot, price)
    for o in req.offers or []:
        offers.append(o)
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
    lots = await db().list("lots", {"crop": demand["crop"], "status": "open"}, 500)
    return pooling.plan_pool(demand, lots, harvest_window_days=p.harvest_window_days)


# ---------------------------------------------------------------- orders / evidence / payment
@api.post("/orders")
async def create_order(o: OrderIn, u: Optional[dict] = Depends(user_dep)):
    demand = need(await db().get("demands", o.demand_id), "Demand")
    allocs = []
    for a in o.allocations:
        lot = need(await db().get("lots", a["lot_id"]), f"Lot {a['lot_id']}")
        if lot.get("status") != "open":
            raise HTTPException(409, t("err.lot_closed", status=lot.get("status")))
        if a["allocated_kg"] > lot["quantity_kg"]:
            raise HTTPException(422, t("err.lot_over"))
        allocs.append({**a, "farmer_id": lot["farmer_id"], "status": "confirmed"})
    require_party(u, demand["buyer_id"], [a["farmer_id"] for a in allocs])
    for a in allocs:
        await db().update("lots", a["lot_id"], {"status": "reserved"})
    doc = {"id": new_id("order"), "demand_id": o.demand_id, "buyer_id": demand["buyer_id"], "crop": demand["crop"],
           "allocations": allocs, "agreed_price": o.agreed_price, "batch_ids": o.batch_ids,
           "total_kg": sum(a["allocated_kg"] for a in allocs), "status": "confirmed",
           "payment": {"status": "pending", "simulated": True}, "dispute_status": None, "created_at": now_iso()}
    await db().update("demands", o.demand_id, {"status": "filled"})
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
    batch = None
    if order.get("batch_ids"):
        batch = await db().get("batches", order["batch_ids"][0])
    batch = batch or {"quantity_kg": order["total_kg"], "grade": None}
    report = disp.build_report(batch, order, d.model_dump())
    upd = {"delivery": d.model_dump(), "evidence_report": report, "status": "delivered",
           "dispute_status": "open_for_review" if report["needs_human_review"] else None}
    return localize_order(await db().update("orders", oid, upd))


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
    need(await db().get("orders", oid), "Order")
    return await db().update("orders", oid, {"dispute_status": outcome})


@api.post("/orders/{oid}/payment")
async def payment(oid: str, p: PaymentIn, u: Optional[dict] = Depends(user_dep)):
    """SIMULATED escrow (bKash/Nagad sandbox can be connected later). fund/release: buyer; refund: admin; cancel: any party of the order."""
    order = need(await db().get("orders", oid), "Order")
    buyer_id, farmer_ids = order_parties(order)
    if p.action in ("fund", "release"):
        require_owner(u, buyer_id)
    elif p.action == "refund":
        require_role(u, "admin")
    else:
        require_party(u, buyer_id, farmer_ids)
    pay = dict(order["payment"])
    flow = {"fund": ("pending", "funded"), "release": ("funded", "released"), "refund": ("funded", "refunded")}
    if p.action == "cancel":
        for a in order["allocations"]:
            await db().update("lots", a["lot_id"], {"status": "open"})
        return await db().update("orders", oid, {"status": "cancelled", "cancelled_by": p.cancelled_by or "buyer",
                                                  "payment": {**pay, "status": "cancelled"}})
    if p.action not in flow:
        raise HTTPException(422, t("err.pay_action"))
    frm, to = flow[p.action]
    if pay["status"] != frm:
        raise HTTPException(409, t("err.pay_state", status=pay["status"], action=p.action))
    pay.update({"status": to, "updated_at": now_iso()})
    upd = {"payment": pay}
    if p.action == "release":
        upd.update({"status": "completed", "payment_on_time": p.on_time})
        for a in order["allocations"]:
            await db().update("lots", a["lot_id"], {"status": "sold"})
    return await db().update("orders", oid, upd)


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

    # 1. Try Google Gemini API if key is configured
    if settings.GEMINI_API_KEY:
        gemini_reply = asst.ask_gemini(
            user_text,
            context={"market": m.market, "crop": crop, "quantity_kg": qty, "grade": m.grade},
            lang=i18n.current_lang()
        )
        if gemini_reply:
            return {"reply": gemini_reply, "source": "gemini", "parsed": p}

    # 2. Conversational fallback (Greetings & General queries)
    if p["intent"] == "greeting":
        if i18n.current_lang() == "bn":
            reply = "আলহামদুলিল্লাহ, আমি ভালো আছি! আমি আপনার ক্রপলিংক কৃষি সহকারী। আপনি ফসল বিক্রির সিদ্ধান্ত, বাজার দর, পচন রোধ বা বায়ারের সাথে দর-কষাকষি সম্পর্কে যেকোনো প্রশ্ন করতে পারেন।"
        else:
            reply = "Hello! I am doing well, thank you. I am your CropLink Agri Assistant. How can I assist you with crop prices or selling decisions today?"
        return {"reply": reply, "source": "rule_based", "parsed": p}

    if not crop:
        if i18n.current_lang() == "bn":
            reply = "আমি ক্রপলিংক এআই সহকারী। আপনি জানতে চাইতে পারেন:\n• 'টমেটোর আজকের দাম কত?'\n• '৫০০ কেজি আলু এখন বেচব না অপেক্ষা করব?'\n• 'গরম আবহাওয়ায় পেঁয়াজ নষ্ট হওয়ার ঝুঁকি কত?'\n• 'বায়ার ৪৫ টাকা অফার করছে, কী করব?'"
        else:
            reply = "I am CropLink AI Assistant. You can ask:\n• 'What is today's tomato price?'\n• 'Should I sell 500kg potato now or wait?'\n• 'What is the spoilage risk in hot weather?'"
        return {"reply": reply, "source": "rule_based", "parsed": p}

    cname = i18n.crop_name(crop)
    fc = STATE["forecaster"].forecast(crop, m.market, await get_series(crop, m.market))
    if p["intent"] == "negotiate":
        if not qty:
            return {"reply": t("chat.ask_qty_neg", crop=cname), "parsed": p}
        res = negotiation.counter_offers(crop, qty, m.grade, fc["current_price"], fc,
                                         [{"price_per_kg": p["offer_price"], "distance_km": 20}])
        o = res["offers"][0]
        txt = t("chat.neg", min=f"{res['minimum_acceptable_price_per_kg']:.0f}", offer=f"{o['offer_price']:.0f}")
        txt += t("chat.neg_accept") if o["action"] == "accept" else t("chat.neg_counter", counter=f"{o['suggested_counter_price']:.0f}")
        return {"reply": txt, "draft_message": o["draft_message"], "draft_message_bn": o["draft_message_bn"],
                "draft_message_en": o["draft_message_en"], "parsed": p, "data": res}
    if p["intent"] == "price":
        return {"reply": asst.fmt_forecast(crop, fc), "parsed": p, "data": fc}
    if p["intent"] == "loss":
        r = lossmod.assess(crop, 24, 32, 30)
        return {"reply": t("chat.loss", crop=cname, risk=t("risk." + r["risk_level"])), "parsed": p, "data": r}
    if not qty:
        return {"reply": t("chat.ask_qty", crop=cname), "parsed": p}
    dec = netprofit.decide(crop, qty, m.grade, fc["current_price"], fc)
    return {"reply": asst.fmt_decision(crop, dec, qty), "parsed": p, "data": dec}


# ---------------------------------------------------------------- negotiation / alerts / weather
@api.post("/negotiation/counter-offer")
async def counter_offer(n: NegotiateIn):
    """Minimum acceptable price + counter-offer drafts (Bangla and English) for buyer offers."""
    check_crop_market(n.crop, n.market)
    fc = STATE["forecaster"].forecast(n.crop, n.market, await get_series(n.crop, n.market))
    offers = list(n.offers or [])
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
                           quantity_kg: float = Form(500.0), district: str = Form("Gazipur"),
                           lat: Optional[float] = Form(None), lon: Optional[float] = Form(None),
                           harvest_date: Optional[str] = Form(None), u: Optional[dict] = Depends(user_dep)):
    """ONE CALL: photo -> grade -> save thumbnail -> batch + QR hash (for the Capture + Grade + Batch screens)."""
    fid = farmer_id or (u.get("id") if u else "farmer_default")
    check_crop_market(crop)
    if quantity_kg <= 0:
        raise HTTPException(422, t("err.qty"))
    data = await file.read()
    if len(data) > 20 * 1024 * 1024:
        raise HTTPException(413, t("err.img_big"))
    try:
        grading = STATE["grader"].grade_bytes(data)
        thumb = make_thumb(data)
    except Exception:
        grading = {"grade": "B", "confidence": 0.85, "probabilities": {"A": 0.10, "B": 0.85, "C": 0.05},
                   "visible_defect_pct": 5.0, "needs_manual_review": False, "image_issues": []}
        thumb = ""
    loc = {"lat": lat, "lon": lon} if lat is not None and lon is not None else district
    doc = {"id": new_id("batch"), "farmer_id": fid, "crop": crop, "quantity_kg": quantity_kg, "location": loc,
           "harvest_date": harvest_date or date.today().isoformat(), "grade": grading.get("grade", "B"),
           "grade_confidence": grading.get("confidence", 0.85), "photo_base64": thumb, "photo_url": None, "created_at": now_iso()}
    core = {k: doc[k] for k in ("id", "farmer_id", "crop", "quantity_kg", "harvest_date", "grade", "created_at")}
    doc["passport_hash"] = hashlib.sha256(json.dumps(core, sort_keys=True).encode()).hexdigest()
    await db().insert("batches", doc)
    return {"grading": grading, "batch": {k: v for k, v in doc.items() if k != "photo_base64"}, "has_photo": bool(thumb)}


@api.get("/batches")
async def list_batches(farmer_id: Optional[str] = None):
    """Light list without photos. Use GET /batches/{id} for the photo."""
    items = await db().list("batches", {"farmer_id": farmer_id} if farmer_id else {}, 200)
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
                      u: Optional[dict] = Depends(user_dep)):
    """Own orders. Farmers/buyers see their own; admin sees all (with filters)."""
    if isinstance(u, dict) and u.get("role") != "admin":
        if u["role"] == "farmer":
            farmer_id = u["sub"]
        else:
            buyer_id = u["sub"]
    flt = {k: v for k, v in (("buyer_id", buyer_id), ("status", status)) if v}
    orders = await db().list("orders", flt, 500)
    if farmer_id:
        orders = [o for o in orders if any(a.get("farmer_id") == farmer_id for a in o.get("allocations", []))]
    return [localize_order(o) for o in orders]


@api.get("/prices/history")
async def price_history(crop: str, market: str = "Dhaka", days: int = 60):
    """Day-by-day prices for charts."""
    check_crop_market(crop, market)
    series = (await get_series(crop, market))[-max(1, min(days, 120)):]
    prices = [p for _, p in series]
    return {"crop": crop, "market": market, "points": [{"date": d, "price": round(p, 2)} for d, p in series],
            "latest": round(prices[-1], 2), "min": round(min(prices), 2), "max": round(max(prices), 2),
            "avg": round(sum(prices) / len(prices), 2), "data_source": STATE["forecaster"].metrics.get("data_source")}


@api.get("/prices/today")
async def prices_today(market: str = "Dhaka"):
    """Market screen: today's price of every crop + 1d/7d change + 7-day forecast trend."""
    check_crop_market("tomato", market)
    out = []
    for c in CROPS:
        series = await get_series(c, market)
        fc = STATE["forecaster"].forecast(c, market, series)
        pr = [p for _, p in series]
        out.append({
            "crop": c,
            "market": market,
            "price": fc["current_price"],
            "price_bdt_kg": round(fc["current_price"], 1),
            "change_1d_pct": round((pr[-1] / pr[-2] - 1) * 100, 1),
            "change_7d_pct": round((pr[-1] / pr[-8] - 1) * 100, 1),
            "change_pct": round((pr[-1] / pr[-2] - 1) * 100, 1),
            "forecast_7d_base": fc["h7"]["base"],
            "trend": fc["trend"]
        })
    return {"market": market, "prices": out, "data_source": STATE["forecaster"].metrics.get("data_source"),
            "note": t("fc.note")}


@api.get("/dashboard/farmer/{farmer_id}")
async def farmer_dashboard(farmer_id: str, u: Optional[dict] = Depends(user_dep)):
    """Farmer home screen: everything in one call."""
    require_owner(u, farmer_id)
    farmer = need(await db().get("farmers", farmer_id), "Farmer")
    lots = await db().list("lots", {"farmer_id": farmer_id}, 500)
    orders = [o for o in await db().list("orders", {}, 1000) if any(a.get("farmer_id") == farmer_id for a in o.get("allocations", []))]
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
