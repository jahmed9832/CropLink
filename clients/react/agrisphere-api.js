// AgriSphere FairMarket API client (React / JavaScript, kono extra library lage na).
// Use:
//   import api from "./agrisphere-api";
//   api.setBaseUrl("https://<RENDER_URL>");        // ba .env: VITE_API_URL / REACT_APP_API_URL
//   api.setLang("en");                              // "bn" (default) | "en": backend-er shob text ei bhashay ashe, localStorage-e save hoy
//   await api.health();                             // app open-e (server ghumay, 30-50 sec lage)
//   await api.login({ phone, password });           // token localStorage-e save hoy
//   const d = await api.decide({ crop: "tomato", quantityKg: 500, grade: "A", market: "Dhaka" });
// Error: ApiError(status, message) - e.status === 401 hole abar login korte bolun.

export class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.name = "ApiError";
    this.status = status; // 0 = network/timeout
  }
}

const TOKEN_KEY = "agrisphere_token";
const LANG_KEY = "agrisphere_lang";
const TIMEOUT_MS = 60000;

const envUrl =
  (typeof import.meta !== "undefined" && import.meta.env && import.meta.env.VITE_API_URL) ||
  (typeof process !== "undefined" && process.env && process.env.REACT_APP_API_URL) ||
  "http://127.0.0.1:8000";

const state = { baseUrl: envUrl.replace(/\/+$/, ""), token: null, lang: "bn" };

function store(op, value) {
  try {
    if (typeof localStorage === "undefined") return null;
    if (op === "get") return localStorage.getItem(TOKEN_KEY);
    if (op === "set") localStorage.setItem(TOKEN_KEY, value);
    if (op === "del") localStorage.removeItem(TOKEN_KEY);
  } catch (_) {}
  return null;
}
state.token = store("get");
try { if (typeof localStorage !== "undefined") state.lang = localStorage.getItem(LANG_KEY) || "bn"; } catch (_) {}

function errorMessage(data) {
  const d = data && data.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d)) return d.map((e) => `${(e.loc || []).slice(-1)[0] ?? ""}: ${e.msg}`).join("; ");
  return "Something went wrong";
}

async function request(method, path, { body, query, form } = {}) {
  const url = new URL(state.baseUrl + path);
  Object.entries(query || {}).forEach(([k, v]) => {
    if (v !== undefined && v !== null) url.searchParams.set(k, v);
  });
  const headers = { "Accept-Language": state.lang };
  if (state.token) headers.Authorization = `Bearer ${state.token}`;
  let payload;
  if (form) payload = form; // browser nijei multipart boundary dey
  else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), TIMEOUT_MS);
  let res;
  try {
    res = await fetch(url, { method, headers, body: payload, signal: ctrl.signal });
  } catch (e) {
    throw new ApiError(0, e.name === "AbortError" ? "Server shara dichhe na (timeout). Abar chesta korun." : `Network problem: ${e.message}`);
  } finally {
    clearTimeout(timer);
  }
  let data = null;
  const text = await res.text();
  try { data = text ? JSON.parse(text) : null; } catch (_) { data = text; }
  if (!res.ok) throw new ApiError(res.status, errorMessage(data));
  return data;
}

const get = (p, query) => request("GET", p, { query });
const post = (p, body = {}, query) => request("POST", p, { body, query });
const clean = (o) => Object.fromEntries(Object.entries(o).filter(([, v]) => v !== undefined && v !== null));

const api = {
  setBaseUrl(url) { state.baseUrl = url.replace(/\/+$/, ""); },
  getToken: () => state.token,
  getLang: () => state.lang,
  setLang(lang) {
    state.lang = lang === "en" ? "en" : "bn";
    try { if (typeof localStorage !== "undefined") localStorage.setItem(LANG_KEY, state.lang); } catch (_) {}
  },
  logout() { state.token = null; store("del"); },
  // location helpers
  district: (d) => ({ district: d }),
  latLon: (lat, lon) => ({ lat, lon }),

  // ---- system / auth
  health: () => get("/health"),
  meta: () => get("/meta"), // crops, markets, grades (dropdown-er jonno)
  /** role = "farmer" | "buyer". Response-er user_id = farmer_id / buyer_id */
  async register({ name, phone, password, role, district = "Dhaka", orgType }) {
    const r = await post("/auth/register", clean({ name, phone, password, role, district, org_type: orgType }));
    state.token = r.token; store("set", r.token);
    return r;
  },
  async login({ phone, password }) {
    const r = await post("/auth/login", { phone, password });
    state.token = r.token; store("set", r.token);
    return r;
  },
  me: () => get("/auth/me"),
  updateMe: ({ name, district, phone }) => request("PUT", "/auth/me", { body: clean({ name, district, phone }) }),

  // ---- MAIN decision engine
  decide: ({ crop, quantityKg, grade = "B", market = "Dhaka", lotId, currentPrice, costs, temperatureC, spoilagePerDay, farmerLocation, offers }) =>
    post("/decision/net-profit", clean({
      crop, quantity_kg: quantityKg, grade, market, lot_id: lotId, current_price: currentPrice, costs,
      temperature_c: temperatureC, spoilage_per_day: spoilagePerDay, farmer_location: farmerLocation, offers,
    })),
  forecast: (crop, market = "Dhaka") => get("/forecast", { crop, market }),

  // ---- grading, batch, lot
  /** file = <input type="file"> er File/Blob */
  grade(file) {
    const form = new FormData();
    form.append("file", file);
    return request("POST", "/grade", { form });
  },
  createBatch: ({ farmerId, crop, quantityKg, location, grade, gradeConfidence, harvestDate, photoBase64, photoUrl }) =>
    post("/batches", clean({ farmer_id: farmerId, crop, quantity_kg: quantityKg, location, grade,
      grade_confidence: gradeConfidence, harvest_date: harvestDate, photo_base64: photoBase64, photo_url: photoUrl })),
  passport: (batchId) => get(`/batches/${batchId}/passport`), // qr_payload -> QR
  createLot: ({ farmerId, crop, quantityKg, grade, location, harvestDate, batchId }) =>
    post("/lots", clean({ farmer_id: farmerId, crop, quantity_kg: quantityKg, grade, location, harvest_date: harvestDate, batch_id: batchId })),
  listLots: ({ crop, farmerId, status } = {}) => get("/lots", { crop, farmer_id: farmerId, status }),
  getLot: (lotId) => get(`/lots/${lotId}`),
  withdrawLot: (lotId) => post(`/lots/${lotId}/withdraw`),
  /** EK CALL-E: photo -> grade -> save -> batch. Response: {grading, batch, has_photo} */
  batchFromPhoto(file, { farmerId, crop, quantityKg, district = "Dhaka", lat, lon, harvestDate }) {
    const form = new FormData();
    form.append("file", file);
    Object.entries(clean({ farmer_id: farmerId, crop, quantity_kg: quantityKg, district, lat, lon, harvest_date: harvestDate }))
      .forEach(([k, v]) => form.append(k, String(v)));
    return request("POST", "/batches/from-photo", { form });
  },
  listBatches: (farmerId) => get("/batches", { farmer_id: farmerId }), // photo chhara
  getBatch: (batchId) => get(`/batches/${batchId}`), // photo_base64 soho

  // ---- buyers, matching, pooling, orders
  createDemand: ({ buyerId, crop, quantityKg, pricePerKg, location, minQuantityKg, minGrade = "C", maxDistanceKm = 300, neededBy, buyerPickup = false }) =>
    post("/demands", clean({ buyer_id: buyerId, crop, quantity_kg: quantityKg, price_per_kg: pricePerKg, location,
      min_quantity_kg: minQuantityKg, min_grade: minGrade, max_distance_km: maxDistanceKm, needed_by: neededBy, buyer_pickup: buyerPickup })),
  listDemands: ({ crop, buyerId, status } = {}) => get("/demands", { crop, buyer_id: buyerId, status }),
  getDemand: (demandId) => get(`/demands/${demandId}`),
  closeDemand: (demandId) => post(`/demands/${demandId}/close`),
  /** Nijer order-gulo (login role onujayi auto filter). Admin: filter diye */
  listOrders: ({ farmerId, buyerId, status } = {}) => get("/orders", { farmer_id: farmerId, buyer_id: buyerId, status }),

  // ---- price screens + dashboards
  priceHistory: (crop, market = "Dhaka", days = 60) => get("/prices/history", { crop, market, days }),
  pricesToday: (market = "Dhaka") => get("/prices/today", { market }),
  farmerDashboard: (farmerId) => get(`/dashboard/farmer/${farmerId}`),
  buyerDashboard: (buyerId) => get(`/dashboard/buyer/${buyerId}`),
  adminDashboard: () => get("/dashboard/admin"),
  seedDemo: () => post("/admin/seed-demo"), // admin only
  lotOffers: (lotId) => get(`/lots/${lotId}/offers`),
  buyerReliability: (buyerId) => get(`/buyers/${buyerId}/reliability`),
  poolPlan: (demandId, harvestWindowDays = 4) => post("/pool/plan", { demand_id: demandId, harvest_window_days: harvestWindowDays }),
  /** allocations = poolPlan().allocations hubohu */
  createOrder: ({ demandId, allocations, agreedPrice, batchIds = [] }) =>
    post("/orders", { demand_id: demandId, allocations, agreed_price: agreedPrice, batch_ids: batchIds }),
  getOrder: (orderId) => get(`/orders/${orderId}`),
  recordDelivery: (orderId, { observedGrade, observedWeightKg, proposedDeductionPct = 0, reason = "" }) =>
    post(`/orders/${orderId}/delivery`, clean({ observed_grade: observedGrade, observed_weight_kg: observedWeightKg,
      proposed_deduction_pct: proposedDeductionPct, reason })),
  evidence: (orderId) => get(`/orders/${orderId}/evidence`),
  /** admin: resolved_for_buyer | resolved_against_buyer | resolved_split | no_fault */
  resolveDispute: (orderId, outcome) => post(`/orders/${orderId}/dispute/resolve`, undefined, { outcome }),
  /** action = fund | release | refund | cancel (SIMULATED payment) */
  payment: (orderId, action, { onTime = true, cancelledBy } = {}) =>
    post(`/orders/${orderId}/payment`, clean({ action, on_time: onTime, cancelled_by: cancelledBy })),

  // ---- negotiation, alerts, loss, weather, radar, assistant
  counterOffer: ({ crop, quantityKg, grade = "B", market = "Dhaka", offers, lotId, productionCostPerKg, marginPct = 0, costs, temperatureC, spoilagePerDay }) =>
    post("/negotiation/counter-offer", clean({ crop, quantity_kg: quantityKg, grade, market, offers, lot_id: lotId,
      production_cost_per_kg: productionCostPerKg, margin_pct: marginPct, costs, temperature_c: temperatureC, spoilage_per_day: spoilagePerDay })),
  priceAlert: (crop, market = "Dhaka") => get("/alerts/price", { crop, market }),
  alertsScan: () => get("/alerts/scan"),
  watchCrop: (farmerId, crop, market = "Dhaka", thresholdPct = 7) =>
    post("/alerts/watch", { farmer_id: farmerId, crop, market, threshold_pct: thresholdPct }),
  /** Periodically (app open / 15-30 min) call korun; alerts_count > 0 hole notification dekhan */
  farmerAlerts: (farmerId) => get(`/alerts/farmer/${farmerId}`),
  lossAssess: ({ crop, distanceKm, hoursSinceHarvest = 0, temperatureC, district, hoursToDeadline }) =>
    post("/loss/assess", clean({ crop, distance_km: distanceKm, hours_since_harvest: hoursSinceHarvest,
      temperature_c: temperatureC, district, hours_to_deadline: hoursToDeadline })),
  weather: (district = "Dhaka") => get("/weather", { district }),
  demandRadar: (crop) => get("/demand-radar", { crop }),
  /** speech-to-text-er text ekhane dien; response.reply text-to-speech-e shonan */
  chat: (text, { market = "Dhaka", quantityKg, grade = "B" } = {}) =>
    post("/assistant/chat", clean({ text, market, quantity_kg: quantityKg, grade })),
};

export default api;
