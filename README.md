# AgriSphere FairMarket - Backend

AI-powered fair-price market access and demand intelligence for smallholder farmers (Bangladesh first).
One FastAPI service backed by MongoDB. The **decision engine** (`POST /decision/net-profit`) is the core:
it compares selling now, waiting, and buyer offers by *estimated net income*, with a downside/base/best range.

- Live API docs: `<BASE_URL>/docs` (Swagger) - machine-readable spec: `<BASE_URL>/openapi.json`
- For the frontend team: **`docs/API_GUIDE.md`** (screen-to-endpoint map, request/response examples, roles, languages)
  and ready-made clients in `clients/flutter` and `clients/react`.

## Features

| Area | Endpoints |
|---|---|
| Auth (register/login, JWT, roles: farmer / buyer / admin) | `POST /auth/register`, `POST /auth/login`, `GET/PUT /auth/me` |
| Net-profit decision engine | `POST /decision/net-profit` |
| Price forecast (7/14 days, with range), history, today's prices | `GET /forecast`, `GET /prices/history`, `GET /prices/today` |
| Photo grading A/B/C with confidence, batch + QR passport | `POST /grade`, `POST /batches/from-photo`, `GET /batches/{id}/passport` |
| Harvest lots, buyer demands, matching with fairness indicator | `POST /lots`, `POST /demands`, `GET /lots/{id}/offers` |
| Cooperative supply pooling | `POST /pool/plan`, `POST /orders` |
| Negotiation: minimum price + counter-offer drafts (BN/EN) | `POST /negotiation/counter-offer` |
| Quality dispute evidence | `POST /orders/{id}/delivery`, `GET /orders/{id}/evidence`, `POST /orders/{id}/dispute/resolve` (admin) |
| Buyer reliability score ("limited history" for new buyers) | `GET /buyers/{id}/reliability` |
| Simulated escrow payment | `POST /orders/{id}/payment` |
| Loss prevention | `POST /loss/assess` |
| Price alerts | `GET /alerts/price`, `GET /alerts/scan`, `POST /alerts/watch`, `GET /alerts/farmer/{id}` |
| Demand radar (confirmed vs predicted) | `GET /demand-radar` |
| Bangla/English text assistant (multi-turn, with suggestions) | `POST /assistant/chat` |
| Weather (OpenWeatherMap, optional) | `GET /weather` |
| Dashboards (farmer, buyer, admin) | `GET /dashboard/farmer/{id}`, `/dashboard/buyer/{id}`, `/dashboard/admin` |

## Languages (Bangla / English)
Send `Accept-Language: bn` or `en` (or `?lang=en`) and every user-facing text in the response - decision explanations,
alerts, assistant replies, errors, dispute reports - comes back in that language. Default is `bn`
(set `DEFAULT_LANG=en` to change it). Dropdown labels (crops, markets, grades, statuses) are in `GET /meta`.
See `docs/API_GUIDE.md`, section "Languages".

## Environment variables

| Variable | Required | Purpose |
|---|---|---|
| `MONGODB_URI` | yes | MongoDB connection string (without it the app uses an in-memory database, for local demos only) |
| `JWT_SECRET` | yes (production) | Secret used to sign login tokens. Use a long random string and never change it casually |
| `PYTHON_VERSION` | Render | `3.12.3` |
| `SEED_DEMO` | no | `true` creates demo accounts and sample data at startup. Set `false` in production |
| `ADMIN_PHONE`, `ADMIN_PASSWORD` | no | Creates your own admin account |
| `OPENWEATHER_API_KEY` | no | Enables real weather. Without it the engine uses Open-Meteo or default fallback |
| `GEMINI_API_KEY` | no | Enables Google Gemini assistant for conversational chat |
| `GEMINI_MODEL` | no | Gemini model name (default: gemini-2.5-flash) |
| `ALLOW_SYNTHETIC_DATA` | no | `false` in production (503 on bundled data); `true` in local dev/tests |
| `DEFAULT_LANG` | no | `bn` (default) or `en` |
| `API_KEY` | no | Leave empty. If set, every request needs an `X-API-Key` header |
| `ALLOWED_ORIGINS` | no | CORS origins, set to specific front-end domain in production |

Never commit real values of these variables. Set them in the Render dashboard (or your shell for local runs).

## Run locally
```
python -m venv .venv
.venv\Scripts\Activate.ps1          # Windows PowerShell   (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
python -m app.ml.train_all           # trains the forecasting and grading models
$env:MONGODB_URI="mongodb+srv://USER:PASSWORD@cluster.mongodb.net/"   # optional
$env:SEED_DEMO="true"
uvicorn app.main:app --reload --reload-dir app
```
Open `http://127.0.0.1:8000/docs`.

## Deploy (GitHub + Render + MongoDB Atlas)
1. **MongoDB Atlas:** create a free M0 cluster, add a database user, allow access from `0.0.0.0/0` (Network Access), copy the connection string and put your user/password in it.
2. **GitHub:** push this folder to a private repository (do not upload `.venv`, `models`, `data`).
3. **Render:** New > Web Service > select the repository.
   - Build command: `pip install -r requirements.txt && python -m app.ml.train_all`
   - Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - Instance type: Free, region: Singapore
   - Environment variables: `MONGODB_URI`, `JWT_SECRET`, `PYTHON_VERSION=3.12.3`, `SEED_DEMO=false`, `ENVIRONMENT=production`, `ALLOW_SYNTHETIC_DATA=false`
4. Open `<URL>/health` - it must show `"database": "mongodb"`.

The free Render plan sleeps after 15 minutes of inactivity; the first request afterwards takes 30-50 seconds.

## Test the whole backend with one command
```
python scripts/live_check.py https://<your-app>.onrender.com      # deployed
python scripts/live_check.py http://127.0.0.1:8000                # local
```
It runs about 70 checks (login and roles, decision engine in both languages, forecast, alerts, negotiation, assistant,
photo grading, the full order flow with pooling, delivery, dispute and payment, dashboards) and prints PASS/FAIL with a
hint for every failure. It needs the demo accounts (`SEED_DEMO=true`). Unit tests: `python tests/test_core.py`.

## Demo accounts (when `SEED_DEMO=true`; password for all: `demo1234`)
| Role | Phone |
|---|---|
| Farmer | `01700000001` (also `01700000011`, `01700000012`) |
| Buyer | `01700000002` (also `01700000021`) |
| Admin | `01700000003` |

## Models and data - important limitations
- The **price forecaster** and the **photo grader** are currently trained on **synthetic data**. Their reported metrics
  (`models/*_metrics.json`) are not real-world accuracy; do not present them as such. To use real data, put DAM prices in
  `data/dam_prices.csv` (`date,crop,market,price`) and labelled photos in `data/images/A|B|C/*.jpg`, delete `models/`, and re-run `python -m app.ml.train_all`.
- Payments are **simulated**; real bKash/Nagad escrow needs merchant access.
- Predicted demand needs at least 8 weeks of completed orders, otherwise it reports `insufficient_data`.
- The assistant is rule-based (prices, sell-or-wait advice, spoilage risk, negotiation). It is not a general-purpose chatbot.
- SMS/IVR and route optimization are not implemented.

## Project layout
```
app/
  main.py          API routes, auth, permissions, language middleware
  i18n.py          Bangla/English message catalog
  db.py            MongoDB layer (in-memory fallback)
  seed.py          demo accounts and sample data
  engine/          decision engine, matching, pooling, dispute, reliability, alerts, negotiation, assistant, loss, demand
  ml/              price forecaster and photo grader (training + inference)
clients/           Flutter and React API clients
docs/API_GUIDE.md  frontend integration guide
scripts/           live_check.py (end-to-end test)
tests/             unit tests
```
