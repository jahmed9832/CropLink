# AgriSphere FairMarket - API Guide (Frontend/App team-er jonno)

Backend ready. Ekta-i backend, shob logic (price forecast, net-profit decision, grading, matching, pooling, dispute, alerts...) server-e. **App-er kaj holo: screen banano, ar ei API call kora.** Kono AI/hishab app-e korar dorkar nai.

- **Base URL:** `https://<RENDER_URL>` (deploy-er por ei jaygay boshan). Local test: `http://127.0.0.1:8000`
- **Live docs (try kora jay):** `<BASE_URL>/docs` - sob endpoint, field, example ekhanei.
- **Machine-readable spec:** `<BASE_URL>/openapi.json` (Postman import / client generate kora jay).
- **Health:** `GET /health` - app open hole prothome eta hit korben (neeche "Render ghumay" dekhen).

## 1. Prothome ei 7ta jinis jene nin
1. **Auth lagbe.** Register/login kore `token` nin, tarpor protiti request-e header: `Authorization: Bearer <token>`. Token 7 din cholbe.
2. **`user_id` = profile id.** Register-er response-er `user_id`-i farmer hole `farmer_id`, buyer hole `buyer_id`. Lot, demand ityadi toiri-te eta-i lagbe.
3. **Location duibhabe dewa jay:** `{"district": "Gazipur"}` **ba** `{"lat": 23.99, "lon": 90.42}`. District list: dhaka, chattogram, rajshahi, khulna, sylhet, barishal, rangpur, mymensingh, bogura, jashore, comilla, narayanganj, gazipur, dinajpur, pabna, kushtia, tangail, jamalpur, coxsbazar.
4. **Fixed value:** crop = `tomato potato onion brinjal chili cabbage rice`; market = `Dhaka Chattogram Rajshahi Bogura Khulna`; grade = `A B C`. `GET /meta` theke dropdown-er list ante paren.
5. **Error format:** `{"detail": "..."}` - `401` login lagbe, `404` paoa jay nai, `409` conflict (jemon ei phone-e account ache), `422` input bhul. `detail`-er lekha user-ke dekhaben na, nijer vasay message dien.
6. **Bhasha (Bangla/English):** header `Accept-Language: bn` ba `en` (ba `?lang=en`) pathale backend-er shob user-facing text oi bhashay ashe. Default `bn`. Details: section 23.
7. **Render ghumay (free plan):** 15 min kew call na korle server ghumay, prothom call-e 30-50 sec lage. Tai request timeout **60 sec** rakhun, ar app open-e `/health` call kore loading dekhan.

## 2. Farmer journey -> kon screen-e kon API (proposal onujayi)
| Screen | API |
|---|---|
| Sign up / Login / Profile | `POST /auth/register`, `POST /auth/login`, `GET/PUT /auth/me` |
| **Home (farmer)** | `GET /dashboard/farmer/{id}` (ek call-e lot, order, offer, alert summary) + `GET /prices/today` |
| **Home (buyer)** | `GET /dashboard/buyer/{id}` |
| Market price screen / chart | `GET /prices/today?market=`, `GET /prices/history?crop=&market=&days=` |
| Amar order-gulo | `GET /orders` (login role onujayi nijer-gulo) |
| 1. Capture (photo tola) + Grade + Batch | camera app-e; chhobi **`POST /batches/from-photo`** (ek call-e grade + save + batch), ba shudhu grade dekhte `POST /grade` |
| 2. Grade dekhano | `/grade`-er response (grade, confidence, `needs_manual_review`) |
| Batch save + QR | `POST /batches`, `GET /batches/{id}/passport` (`qr_payload` diye QR draw korun) |
| Harvest listing | `POST /lots`, `GET /lots?farmer_id=` |
| 3. Decide: "becbo na opekkha korbo?" | **`POST /decision/net-profit`** (main screen) |
| Dam forecast chart | `GET /forecast?crop=&market=` |
| 4. Match: buyer offer | `GET /lots/{lot_id}/offers` |
| Pooling | `POST /pool/plan`, tarpor `POST /orders` |
| Dor-koshakoshi | `POST /negotiation/counter-offer` |
| Alert / notification | `GET /alerts/farmer/{id}`, `POST /alerts/watch`, `GET /alerts/scan` |
| Nosto-er jhunki | `POST /loss/assess` |
| Bangla assistant (text/voice) | `POST /assistant/chat` |
| 5. Delivery + dispute | `POST /orders/{id}/delivery`, `GET /orders/{id}/evidence` |
| 6. Payment (simulated) | `POST /orders/{id}/payment` |
| Weather | `GET /weather?district=` |

**Buyer screen:** `POST /demands`, `GET /demands?buyer_id=`, `POST /demands/{id}/close`, `GET /buyers/{id}/reliability`, `GET /demand-radar`.
**Admin screen:** `GET /dashboard/admin`, `POST /orders/{id}/dispute/resolve`, `POST /prices` (daily DAM price push), `POST /admin/seed-demo`.

## 3. Main engine: `POST /decision/net-profit`
Request (shudhu `crop` ar `quantity_kg` must, baki optional):
```json
{ "crop": "tomato", "quantity_kg": 500, "grade": "A", "market": "Dhaka",
  "lot_id": "lot_xxx",
  "costs": {"transport_per_kg_km": 0.02, "handling_per_kg": 0.5, "storage_per_kg_day": 0.3, "commission_pct": 2, "local_market_km": 15},
  "spoilage_per_day": 0.035, "temperature_c": 30 }
```
- `lot_id` dile oi lot-er jonno open buyer offer gulo auto option-e ashe.
- `costs`, `spoilage_per_day`, `temperature_c` farmer edit korte parbe (proposal: "farmer cost correct korte parbe") - UI-te editable field rakhun, notun value diye abar call korun.
- `temperature_c` na dile server weather API (key thakle) ba 30C dhore.

Response (sankhep):
```json
{
  "recommended": "sell_now",
  "safest": "sell_now",
  "uplift_vs_sell_now_pct": 0.0,
  "options": [
    {
      "id": "sell_now",
      "label": "Sell now at the local market",
      "kind": "market",
      "net": {
        "downside": 45507.0,
        "base": 45507.0,
        "best": 45507.0
      }
    },
    {
      "id": "wait_7d",
      "label": "Wait 7 days, then sell",
      "kind": "wait",
      "net": {
        "downside": 31117.0,
        "base": 32551.0,
        "best": 33943.0
      },
      "forecast_price_range": [
        85.16,
        88.91,
        92.55
      ]
    }
  ],
  "explanation": [
    "Best option: Sell now at the local market. Estimated net income 45507 BDT (range 45507 to 45507)."
  ],
  "disclaimer": "This is an estimate, not guaranteed income. Adjust costs or quantity and recalculate.",
  "forecast": {
    "current_price": 86.82,
    "h7": {
      "low": 85.16,
      "base": 88.91,
      "high": 92.55
    },
    "h14": {
      "low": 87.05,
      "base": 91.85,
      "high": 96.62
    },
    "trend": "flat",
    "data_source": "synthetic"
  },
  "weather": {
    "source": "user_input",
    "temperature_c": 30
  },
  "matched_offers": []
}
```
UI-te dekhan: `recommended` option, protiti option-er `net.downside / base / best` (range), `explanation` (list), `safest`. **Net income ek ta number hishabe dekhaben na, range dekhan** (proposal-er niyom).

## 4. Auth
`POST /auth/register`
```json
{ "name": "Rahim Mia", "phone": "01711111111", "password": "test1234", "role": "farmer", "district": "Gazipur" }
```
`role` = `farmer` ba `buyer`. Response:
```json
{
  "token": "eyJhbGciOiAiSFMyNTYiLCAidHlwIj...(lomba token)",
  "user_id": "farmer_8d31157caf",
  "role": "farmer",
  "profile": {
    "id": "farmer_8d31157caf",
    "name": "Rahim Mia",
    "phone": "01711111111",
    "org_type": null,
    "location": "Gazipur",
    "language": "bn",
    "created_at": "2026-10-22T08:14:56.731647+00:00"
  }
}
```
`POST /auth/login` `{ "phone": "...", "password": "..." }` -> `token`, `user_id`, `role`.

## 5. Photo grading `POST /grade`
`multipart/form-data`, field name `file` (jpg/png, max 8MB). Response:
```json
{
  "grade": "B",
  "confidence": 0.74,
  "probabilities": {
    "A": 0.16,
    "B": 0.74,
    "C": 0.1
  },
  "visible_defect_pct": 4.2,
  "needs_manual_review": false,
  "image_issues": [],
  "model_note": "This is a suggested grade, not final. If confidence is low, check it manually.",
  "model_data_source": "synthetic"
}
```
`needs_manual_review: true` hole farmer-ke bolun "chhobi abar tulun/ manual check korun". Grade ekta **suggestion**, final na - UI-te eta spasto likhun.

## 6. Lot, offer, pooling, order
`POST /lots`: `{ "farmer_id", "crop", "quantity_kg", "grade", "location": {...}, "harvest_date": "2026-10-21" }`
```json
{
  "id": "lot_68489e09c8",
  "farmer_id": "farmer_9b168f960f",
  "crop": "tomato",
  "quantity_kg": 400,
  "grade": "A",
  "location": "Gazipur",
  "harvest_date": "2026-10-22",
  "batch_id": null,
  "status": "open",
  "created_at": "2026-10-22T08:14:56.797603+00:00"
}
```
`GET /lots/{lot_id}/offers` (match score, fairness, reliability soho):
```json
[
  {
    "demand_id": "demand_ece32532a6",
    "buyer_id": "buyer_6b2ecf38f2",
    "buyer_name": "Karwan Wholesale",
    "price_per_kg": 95,
    "distance_km": 25.1,
    "match_score": 65.7,
    "reliability": {
      "label": "limited_history",
      "label_text": "Limited history",
      "score": null,
      "verified_transactions": 0,
      "reasons": [
        "Fewer than 5 verified transactions, so no score was given (this is not treated as poor)."
      ],
      "contestable": true
    },
    "fairness": {
      "label": "fair",
      "label_text": "Fair price",
      "ratio": 1.013,
      "reference_price": 93.8
    },
    "needs_pooling": true,
    "min_quantity_kg": 800,
    "buyer_pickup": false
  }
]
```
`needs_pooling: true` mane lot-er quantity buyer-er minimum-er cheye kom, pooling dorkar. `POST /pool/plan` `{ "demand_id": "..." }`:
```json
{
  "demand_id": "demand_ece32532a6",
  "feasible": true,
  "required_kg": 1000.0,
  "min_quantity_kg": 800.0,
  "pooled_kg": 1000.0,
  "fill_rate_pct": 100.0,
  "shortfall_kg": 0,
  "allocations": [
    {
      "lot_id": "lot_220136f798",
      "farmer_id": "farmer_a98e0d6b0d",
      "allocated_kg": 400.0,
      "distance_km": 25.1,
      "status": "planned",
      "share_pct": 40.0,
      "logistics_share": 141,
      "gross": 38000,
      "commission": 760,
      "expected_payment": 37099
    }
  ],
  "rejected": [],
  "note": "Each lot is tracked separately; one participant's issue does not silently affect the others' allocations."
}
```
Plan thik hole `POST /orders` e `allocations` (plan theke hubohu) + `demand_id` + `agreed_price` pathan.

## 7. Dor-koshakoshi `POST /negotiation/counter-offer`
```json
{ "crop": "tomato", "quantity_kg": 400, "grade": "A", "market": "Dhaka",
  "offers": [{"price_per_kg": 60, "distance_km": 30}],
  "production_cost_per_kg": 40, "margin_pct": 5 }
```
`lot_id` dile oi lot-er shob buyer offer-o ashe. Response:
```json
{
  "minimum_acceptable_price_per_kg": 93.8,
  "basis": {
    "best_alternative": "Sell now at the local market",
    "best_alternative_net": 36406.0,
    "margin_pct": 0,
    "note": null
  },
  "offers": [
    {
      "buyer_id": null,
      "buyer_name": null,
      "offer_price": 60.0,
      "minimum_acceptable_price": 98.1,
      "below_minimum": true,
      "market_reference_price": 93.8,
      "action": "counter",
      "suggested_counter_price": 101.0,
      "draft_message": "Thank you for your offer of 60 BDT/kg. I have 400 kg of Tomato (Grade A). Based on current market rates and quality I can supply at 101 BDT/kg. Please let me know if that works.",
      "draft_message_bn": "আপনার প্রস্তাব ৬০ টাকা/কেজি পেয়েছি। আমার ৪০০ কেজি টমেটো (গ্রেড এ) আছে। বর্তমান বাজারদর ও মান অনুযায়ী ১০১ টাকা/কেজি দরে দিতে পারব। এই দরে রাজি হলে জানান।",
      "draft_message_en": "Thank you for your offer of 60 BDT/kg. I have 400 kg of Tomato (Grade A). Based on current market rates and quality I can supply at 101 BDT/kg. Please let me know if that works.",
      "payment_risk_pct": 4.0
    }
  ],
  "disclaimer": "The farmer reviews and sends the draft; the system never sends anything itself. Do not show your minimum price to the buyer.",
  "weather": {
    "source": "user_input",
    "temperature_c": 30
  }
}
```
`draft_message_bn` farmer-ke dekhan, **farmer review kore tarpor pathabe** (auto pathaben na). `minimum_acceptable_price_per_kg` buyer-ke **dekhaben na**.

## 8. Alerts
`GET /alerts/price?crop=tomato&market=Dhaka`:
```json
{
  "crop": "tomato",
  "market": "Dhaka",
  "current_price": 86.82,
  "avg_30d": 81.8,
  "alerts": [],
  "has_alert": false,
  "as_of": "2026-10-21"
}
```
Push notification backend pathay na. App **protti 15-30 min-e ba app open-e** `GET /alerts/farmer/{id}` call kore `has_alert: true` hole local notification dekhabe. Age `POST /alerts/watch` `{farmer_id, crop, market, threshold_pct}` diye crop watch korte hobe.

## 9. Forecast `GET /forecast?crop=tomato&market=Dhaka`
```json
{
  "current_price": 86.82,
  "as_of": "2026-10-21",
  "h7": {
    "low": 85.16,
    "base": 88.91,
    "high": 92.55
  },
  "h14": {
    "low": 87.05,
    "base": 91.85,
    "high": 96.62
  },
  "trend": "flat",
  "data_source": "synthetic",
  "note": "This is a forecast, not a confirmed price. Decide using the range (low to high)."
}
```
Chart-e `low/base/high` range dekhan, "forecast, nishchit noy" likhun.

## 10. Nosto-er jhunki `POST /loss/assess`
```json
{ "crop": "tomato", "hours_since_harvest": 30, "temperature_c": 34, "distance_km": 120, "hours_to_deadline": 10 }
```
```json
{
  "urgency_score": 46,
  "risk_level": "medium",
  "expected_loss_pct": 7.4,
  "transit_hours": 3.4,
  "advice": [
    "It is hot. Keep it in the shade and transport at night or early morning."
  ],
  "assumptions": {
    "spoilage_per_day": 0.035,
    "heat_factor": 1.54,
    "transit_kmh": 35
  },
  "weather": {
    "source": "user_input",
    "temperature_c": 34
  }
}
```

## 11. Bangla assistant `POST /assistant/chat`
`{ "text": "আলুর দাম কেমন থাকবে", "market": "Dhaka", "quantity_kg": 500, "grade": "B" }`
```json
{
  "reply": "The current price of Potato is about 36 BDT/kg. In 7 days it may stay about the same: roughly 35 to 38 BDT (likely 37). This is a forecast, not a confirmed price.",
  "parsed": {
    "intent": "price",
    "crop": "potato",
    "quantity_kg": null,
    "offer_price": null
  }
}
```
Bhalo kaj kore: dam jiggesh, "৫০০ কেজি টমেটো বিক্রি করব নাকি অপেক্ষা", nosto, "ক্রেতা ৫০ টাকা দিচ্ছে". Free-form proshno bojhe na (rule-based) - `reply` ta screen-e dekhan/ pore shonan.

## 12. Delivery, dispute evidence, payment
Buyer delivery-te `POST /orders/{id}/delivery`:
`{ "observed_grade": "B", "observed_weight_kg": 950, "proposed_deduction_pct": 8, "reason": "..." }` -> `evidence_report`:
```json
{
  "order_id": "order_e9f1980108",
  "pre_sale": {
    "grade": "A",
    "confidence": 0.9,
    "weight_kg": 1000,
    "agreed_price": 95,
    "photo_recorded": true,
    "recorded_at": "2026-10-22T08:14:56.810810+00:00"
  },
  "at_delivery": {
    "grade": "B",
    "weight_kg": 950,
    "proposed_deduction_pct": 8,
    "reason": "কিছু টমেটোতে দাগ"
  },
  "items": [
    {
      "key": "disp.weight",
      "params": {
        "pct": "-5.0"
      }
    },
    {
      "key": "disp.grade",
      "params": {
        "pre": "A",
        "post": "B",
        "diff": "-7"
      }
    },
    {
      "key": "disp.deduction",
      "params": {
        "pct": 8
      }
    }
  ],
  "note_items": [],
  "needs_human_review": true,
  "status": "open_for_review",
  "discrepancies": [
    "Weight difference of -5.0% (could be transit loss or a weighing error)",
    "Grade mismatch: Grade A to Grade B (price band difference -7%)",
    "The buyer proposed a 8% price deduction"
  ],
  "notes": [],
  "statement": "This is a side-by-side evidence report. The system does not declare either party at fault; a person will review it."
}
```
Eta side-by-side dekhan (pre-sale vs delivery). **Kono party-ke doshi dekhaben na**, `needs_human_review: true` hole "review-er jonno pathano hoyeche" dekhan. Admin `POST /orders/{id}/dispute/resolve?outcome=resolved_split` (`resolved_for_buyer | resolved_against_buyer | resolved_split | no_fault`).

Payment (**simulated**, real taka jay na): `POST /orders/{id}/payment` `{ "action": "fund" }` -> `"release"` (ba `"refund"`, `"cancel"`). Order status: `confirmed -> delivered -> completed` (`cancelled`). UI-te "Demo payment" likhe rakhun.

## 13. Baki
`GET /buyers/{id}/reliability`:
```json
{
  "label": "limited_history",
  "label_text": "Limited history",
  "score": null,
  "verified_transactions": 0,
  "reasons": [
    "Fewer than 5 verified transactions, so no score was given (this is not treated as poor)."
  ],
  "contestable": true
}
```
`label: "limited_history"` hole "notun buyer, history kom" dekhan, **kharap bolben na**.

`GET /demand-radar?crop=tomato`:
```json
{
  "crop": "tomato",
  "confirmed_demand_kg": 0,
  "open_supply_kg": 0,
  "oversupply_risk": "unknown",
  "predicted_demand": {
    "status": "insufficient_data",
    "weeks_of_history": 0,
    "required_weeks": 8,
    "note": "This is a prediction, not a confirmed order. At least 8 weeks of completed-order history is needed."
  },
  "data_freshness": "2026-10-22T08:14:56.814452+00:00"
}
```
`confirmed_demand_kg` (confirmed) ar `predicted_demand` (anumanik) **alada section-e** dekhan, mishabhen na.

`GET /batches/{id}/passport`:
```json
{
  "batch_id": "batch_056cefcad9",
  "qr_payload": "agrisphere://batch/batch_056cefcad9",
  "record": {
    "id": "batch_056cefcad9",
    "farmer_id": "farmer_8d31157caf",
    "crop": "tomato",
    "quantity_kg": 1000,
    "harvest_date": "2026-10-22",
    "grade": "A",
    "created_at": "2026-10-22T08:14:56.810810+00:00"
  },
  "origin": "Gazipur",
  "hash": "4ffa1f3903cd0a30a373a73271d84dca83aa0628fc5762ae5f8a7ee5c4dacd01",
  "hash_valid": true,
  "note": "Additional validation is required for export compliance."
}
```
`qr_payload` string-ta QR code-e encode korun.

## 14. App-ei korte hobe (backend kore na)
| Ki | Kivabe |
|---|---|
| Voice input/output | Flutter: `speech_to_text` (locale `bn_BD`) + `flutter_tts`; React Native: `@react-native-voice/voice` + `react-native-tts`. Voice -> text -> `/assistant/chat` -> `reply` text -> text-to-speech |
| Camera | Flutter `image_picker`/`camera`; chhobi `/grade`-e pathan. Batch-er jonno 400KB-er chhoto thumbnail `photo_base64`-e ba nijer storage-er `photo_url` |
| QR code | `qr_flutter` / `react-native-qrcode-svg` |
| Push notification | Firebase FCM ba local notification; backend theke polling |
| Offline/ low network | Last response cache korun, "purano data" likhe dekhan |
| SMS/IVR | Prototype-e nai |

## 15. UI-te ei niyom gulo mante hobe (proposal-er design principle)
- Forecast/net income **range** dekhan, "guaranteed" likhben na.
- Confirmed vs predicted alada dekhan.
- Grade, forecast = suggestion, human review-er path rakhun.
- "limited_history" buyer-ke kharap dekhaben na.
- Payment screen-e "simulated/demo" likhun.

## 16. Jana dorkar - shimaboddhota
- **Forecast ar grading ekhon synthetic data-te train kora.** Dam real bajar noy, grading real crop photo-te test hoyni. Real DAM price CSV (`data/dam_prices.csv`) ar chhobi (`data/images/A|B|C/`) dile backend team retrain korbe. Pitch-e real accuracy claim korben na.
- Payment simulated. Predicted demand-e 8 shoptaher order lagbe. SMS/IVR, route optimization nai.

## 17. Chhoto client example
**Flutter (Dart, `http` package):**
```dart
const base = 'https://<RENDER_URL>';
Future<String> login(String phone, String pass) async {
  final r = await http.post(Uri.parse('$base/auth/login'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'phone': phone, 'password': pass}))
      .timeout(const Duration(seconds: 60));
  return jsonDecode(r.body)['token'];
}
Future<Map> decide(String token) async {
  final r = await http.post(Uri.parse('$base/decision/net-profit'),
      headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer $token'},
      body: jsonEncode({'crop': 'tomato', 'quantity_kg': 500, 'grade': 'A', 'market': 'Dhaka'}))
      .timeout(const Duration(seconds: 60));
  return jsonDecode(r.body);
}
```
**JavaScript / React:**
```js
const BASE = "https://<RENDER_URL>";
async function api(path, token, body) {
  const res = await fetch(BASE + path, {
    method: body ? "POST" : "GET",
    headers: { "Content-Type": "application/json", ...(token && { Authorization: `Bearer ${token}` }) },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error((await res.json()).detail || res.status);
  return res.json();
}
// const { token } = await api("/auth/login", null, { phone, password });
// const d = await api("/decision/net-profit", token, { crop: "tomato", quantity_kg: 500, grade: "A", market: "Dhaka" });
```
Photo upload (JS): `const f = new FormData(); f.append("file", imageFile); fetch(BASE + "/grade", { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: f })`

## 18. Test-er shortcut
Auth bondho kore test korte chaile backend-e `AUTH_REQUIRED=false` (shudhu dev-e, production-e noy). `scripts/seed_demo.py <BASE_URL>` demo data (buyer, 3 farmer, lot, demand) dhukay.

Prosno/bug hole: kon endpoint, ki body pathalen, ki response ashlo (`detail` soho) - eta backend team-ke dien.

## 19. Ready-made client file (copy kore use korun)
| Team | File | Kivabe |
|---|---|---|
| Flutter | `clients/flutter/agrisphere_api.dart` | `pubspec.yaml`-e `http: ^1.2.0`. `final api = AgriSphereApi('https://<RENDER_URL>');` tarpor `api.login(...)`, `api.decide(...)` |
| React | `clients/react/agrisphere-api.js` (+ `example-DecisionScreen.jsx`) | `import api from "./agrisphere-api"; api.setBaseUrl("https://<RENDER_URL>");` Token `localStorage`-e nijei save hoy |

Dutor method-er naam ek-i (`decide`, `grade`, `lotOffers`, `poolPlan`, `counterOffer`, `farmerAlerts`, `chat`...), tai dui jon-er kaj mile jabe. Error `ApiException` (Flutter) / `ApiError` (React); `status == 401` hole abar login, `status == 0` mane network/timeout.
React client mock server-e test kora. Flutter client-e compiler chalano hoyni, prothom build-e chhoto error ashle `flutter analyze` er message backend team-ke dien.

## 20. Role, permission ar demo account (403 keno ashe)
- Tin role: **farmer**, **buyer**, **admin**. Register-e shudhu farmer/buyer hoy; admin server-e toiri hoy.
- Nijer data-i change kora jay: farmer nijer `farmer_id` diye lot/batch/watch toiri kore, buyer nijer `buyer_id` diye demand. Onner id dile **`403`**.
- Order: buyer fund/release kore, delivery record kore; order-er farmer ba buyer order dekhe ar `cancel` kore; `refund` ar `dispute/resolve` ar `POST /prices` shudhu **admin**.
- Token-er role ar `user_id` app-e save rakhun (login/register response-e ache), role onujayi screen dekhan.

**Demo account (server-e `SEED_DEMO=true` thakle auto toiri hoy, password sobar `demo1234`):**
| Role | Phone |
|---|---|
| Farmer (Rahim Mia, Gazipur) | `01700000001` (aro farmer: `01700000011`, `01700000012`) |
| Buyer (Karwan Wholesale, Dhaka) | `01700000002` (aro buyer: `01700000021`) |
| Admin | `01700000003` |

Demo data-te ache: tomato/potato lot, 3ta open demand (tomato pooling demo-r jonno), buyer-er 10 shoptaher order history (reliability score ar demand radar prediction dekhano jay). Production-e jawar age `SEED_DEMO=false` korun.

## 21. Extra endpoint (jotto khushi call korun)
| Endpoint | Ki dey |
|---|---|
| `POST /batches/from-photo` | multipart: `file`, `farmer_id`, `crop`, `quantity_kg`, `district` (ba `lat`+`lon`), `harvest_date`. Response `{grading, batch, has_photo}` |
| `GET /batches?farmer_id=` / `GET /batches/{id}` | list (photo chhara) / ekta batch (`photo_base64` soho, `data:image/jpeg;base64,` diye dekhan) |
| `GET /lots/{id}`, `POST /lots/{id}/withdraw` | lot dekha / tule neya |
| `GET /demands/{id}`, `POST /demands/{id}/close` | demand dekha / bondho |
| `GET /orders?status=` | nijer order list |
| `GET /prices/history?crop=&market=&days=` | chart-er `points[{date, price}]` + min/max/avg |
| `GET /prices/today?market=` | shob fosholer ajker dam, 1d/7d change, 7d forecast trend |
| `GET /dashboard/farmer/{id}`, `/dashboard/buyer/{id}`, `/dashboard/admin` | home screen summary |
| `PUT /auth/me` | name/district/phone update |

Client file-e (Dart/JS) ei sob method ache (`batchFromPhoto`, `listOrders`, `priceHistory`, `pricesToday`, `farmerDashboard`...).

## 22. Chhoto shotorkota
- `422` + `detail` = input bhul ba data kom (jemon price history 15 diner kom). `403` = permission nai. `401` = login.
- Photo grade (`/grade`, `/batches/from-photo`): `needs_manual_review: true` hole "chhobi abar tulun" dekhan.
- `batches/from-photo` photo thumbnail (480px) save kore, boro chhobi na.

## 23. Bangla / English (language switch)
**Kivabe:** protiti request-e header `Accept-Language: bn` ba `Accept-Language: en` (ba URL-e `?lang=en`). Default `bn`. Client file-e eta ready: Flutter `api.lang = 'en';`, React `api.setLang('en')`. User-er language app-e save rakhun (Flutter `shared_preferences`, React `localStorage`).

**Ki ki backend theke translate hoye ashe (Bangla script-e, Banglish na):**
| Jinis | Field |
|---|---|
| Decision engine | `options[].label`, `explanation[]`, `disclaimer` |
| Forecast / price | `note` |
| Alerts | `message` (request-er bhasha), `message_bn`, `message_en` (duitoi sob somoy ashe) |
| Negotiation | `draft_message` (request-er bhasha), `draft_message_bn`, `draft_message_en`, `disclaimer` |
| Assistant | `reply` |
| Loss | `advice[]` |
| Dispute evidence | `discrepancies[]`, `notes[]`, `statement` (order save-er pore bhasha bodlale-o notun bhashay ashe) |
| Reliability / fairness | `reasons[]`, `label_text` |
| Pooling / radar / passport / grading | `note`, `rejected[].reasons`, `model_note`, `image_issues[]` |
| Error | `{"detail": "..."}` |

**Ja translate hoy na (code, logic-e use korun):** `id`, `status`, `grade`, `crop`, `market`, `label` (reliability/fairness-er code, jemon `limited_history`), `type`, `trend`, shob number. Screen-e naam dekhate **`GET /meta`** (login lage na) theke `names.crops`, `names.markets`, `names.grades`, `names.statuses` nin, protiti-te `{bn, en}` ache. Jemon `names.crops.tomato.bn` = `টমেটো`.

**Ja app-ke nijeke korte hobe:**
- Button, menu, form-er label ityadi static text: Flutter `flutter_localizations` + `intl` (ba `easy_localization`), React `react-i18next`. Eta backend-er kaj noy.
- FastAPI-er input-validation error (body-r field bhul hole `detail` ekta list, ingreji-te ashe): eta user-ke dekhaben na, nijer message dekhan. Business error (404/403/409 ityadi) `detail` string, localized.
- User-er likha lekha (naam, dispute-er `reason`) jemon likha temni dekhay, translate hoy na.

**Digit:** Bangla text-e shongkha Bangla digit (৫০০), English-e Latin digit. JSON-er number field shob somoy Latin number (`500`), tai calculation-e shomosha nai.

**Voice:** `lang=bn` hole speech-to-text/text-to-speech locale `bn_BD`, `lang=en` hole `en_US` rakhun, tahole `/assistant/chat`-er `reply` thik bhashay shona jabe. Assistant Bangla ar English duitei proshno bojhe (jemon "tomato price", "টমেটোর দাম").

## 24. Backend test kora (ek command-e)
`python scripts/live_check.py https://<RENDER_URL>` (IntelliJ terminal, `.venv` active, shudhu Python lage). Login, decision engine (duitei bhasha), forecast, alerts, negotiation, assistant, pura order flow (pooling, delivery, dispute, payment), role/403 check, dashboard shob chalay ar PASS/FAIL dey. Demo account lagbe (`SEED_DEMO=true`). Swagger (`/docs`) e protiti endpoint-e ekta `lang` field ache (`bn` ba `en`), shetate bhasha bodle test korte paren.
