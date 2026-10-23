# AgriSphere FairMarket - Backend (FastAPI + MongoDB)

Ekta-i backend. Main engine = **`POST /decision/net-profit`** (sell now vs wait vs buyer offer, net income hishab).

## Ki ki ache
| Feature | Endpoint |
|---|---|
| Net-profit decision engine (MAIN) | `POST /decision/net-profit` |
| Register / Login (JWT, MongoDB users) | `POST /auth/register`, `POST /auth/login`, `GET /auth/me` |
| Voice Negotiation backend (min price + counter draft) | `POST /negotiation/counter-offer` |
| Price alerts | `GET /alerts`, `GET /alerts/scan` |
| Weather (optional) | `GET /weather` (OPENWEATHER_API_KEY lage) |
| Price forecast (7/14 din, range soho) | `GET /forecast?crop=tomato&market=Dhaka` |
| Photo grading A/B/C + confidence | `POST /grade` (multipart `file`) |
| Batch + QR passport (hash) | `POST /batches`, `GET /batches/{id}/passport` |
| Farmer lot / Buyer demand | `POST /lots`, `POST /demands` |
| Buyer matching + fairness | `GET /lots/{id}/offers` |
| Cooperative pooling | `POST /pool/plan`, `POST /orders` |
| Quality dispute evidence | `POST /orders/{id}/delivery`, `GET /orders/{id}/evidence` |
| Buyer reliability | `GET /buyers/{id}/reliability` |
| Payment (SIMULATED escrow) | `POST /orders/{id}/payment` |
| Loss prevention | `POST /loss/assess` |
| Demand radar | `GET /demand-radar` |
| Bangla assistant (price, sell/wait, loss, dor-koshakoshi) | `POST /assistant/chat` |
| Voice negotiation backend: minimum price + counter-offer draft (BN/EN) | `POST /negotiation/counter-offer` |
| Price-spike / forecast alerts | `GET /alerts/price`, `GET /alerts/scan`, `POST /alerts/watch`, `GET /alerts/farmer/{id}` |
| Weather (OpenWeatherMap) | `GET /weather?district=Dhaka` (decision/loss/negotiation auto use kore) |
| Daily price ingest | `POST /prices` |

**Frontend/app team-er jonno full guide: `docs/API_GUIDE.md`; ready-made client: `clients/flutter`, `clients/react`** (screen -> API map, request/response example, Dart/JS code).

Swagger docs (app dev-ra eta dekhe sob endpoint test korte parbe): `https://<your-app>.onrender.com/docs`

## Deploy (Render + MongoDB Atlas) - step by step
1. **MongoDB Atlas** (free): mongodb.com/atlas -> Create free M0 cluster -> Database Access-e user+password banan -> Network Access-e `0.0.0.0/0` allow -> Connect -> Drivers -> connection string copy (`mongodb+srv://...`). Password-er moddhe `@ : /` thakle URL-encode korte hobe.
2. **GitHub**: ei folder-ta ekta new GitHub repo-te push/upload korun (zip khule sob file upload).
3. **Render**: render.com -> New -> **Blueprint** (ba Web Service) -> repo select. `render.yaml` auto settings nibe.
   - Web Service manually korle: Build `pip install -r requirements.txt && python -m app.ml.train_all`, Start `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
4. Render **Environment**-e set korun: `MONGODB_URI` = Atlas string, `MONGODB_DB` = agrisphere, (optional) `API_KEY` = ekta secret.
5. Deploy hole `https://<name>.onrender.com/health` khulle `"database":"mongodb"` dekhabe. Eitai app-er **base URL**.
6. App theke call: `X-API-Key: <API_KEY>` header (jodi API_KEY set koren).

Note: Render free plan-e 15 min idle thakle sleep kore; prothom request-e ~30-50 sec lage. Demo-r age `/health` hit kore rakhun.

## Model gulo
- **Price forecaster** (HistGradientBoosting) - ekhon *synthetic* price diye train. Real DAM data dile: `data/dam_prices.csv` (columns: `date,crop,market,price`) rakhun, tarpor build/`python -m app.ml.train_all` chalan (`models/` folder muche dite hobe). Metrics: `models/forecaster_metrics.json` (naive baseline-er sathe compare kora).
- **Photo grader** - ekhon *synthetic image* diye train (pipeline kaj kore ki na dekhar jonno). Real use-er jonno `data/images/A|B|C/*.jpg` e real photo rakhun, 150+ hole auto retrain-e real data use hobe. **Real accuracy claim korben na** jotokkhon real data-te evaluate na hoy.
- Bangla assistant rule-based (kono paid API key lage na). Voice-er jonno app-e speech-to-text/text-to-speech (bn-BD) use kore text ei endpoint-e pathan.

## Local-e chalano
```
pip install -r requirements.txt
python -m app.ml.train_all
uvicorn app.main:app --reload     # MONGODB_URI na dile in-memory DB
python tests/test_core.py
python scripts/seed_demo.py http://127.0.0.1:8000
```

## Proposal-er sathe mil / sima
- Payment escrow **simulated** (bKash/Nagad merchant access chhara real kora jay na) - proposal-o eta-i bole.
- Demand prediction model nai (data kom); radar confirmed demand ar oversupply risk dekhay, prediction "insufficient_data" label kore.
- Route optimization nai (proposal-er stretch goal).

## Login / Auth (MongoDB-te user thake)
- `POST /auth/register` `{name, phone, password, role: "farmer"|"buyer", district}` -> `token` ferot dey (profile o auto toiri hoy, `user_id` = profile id).
- `POST /auth/login` `{phone, password}` -> `token`.
- Baki sob endpoint-e header lagbe: `Authorization: Bearer <token>`. Password hash kore (PBKDF2) save hoy, plain text noy.
- Test korar somoy auth bondho rakhte chaile `AUTH_REQUIRED=false`.
- `/docs` e register/login kore token copy -> upore **Authorize** button-e paste.

## IntelliJ-te run korar nijom
1. Python 3.11/3.12 install (python.org). IntelliJ-e **Python plugin** (ba PyCharm Community) install.
2. Zip extract -> IntelliJ: File > Open > `agrisphere-backend` folder.
3. Bottom-er **Terminal** tab-e:
   - Windows: `python -m venv .venv` then `.venv\Scripts\activate`
   - Mac/Linux: `python3 -m venv .venv` then `source .venv/bin/activate`
   - `pip install -r requirements.txt`
   - `python -m app.ml.train_all`
   - `uvicorn app.main:app --reload`
4. Browser-e `http://127.0.0.1:8000/docs` kholen - ekhane sob API click kore test kora jay.
5. `MONGODB_URI` na dile in-memory DB (restart-e data jabe). Atlas-e connect korte terminal-e age set korun:
   Windows: `set MONGODB_URI=mongodb+srv://...`  Mac/Linux: `export MONGODB_URI="mongodb+srv://..."`

## Backend test (ek command-e, 63ta check)
```
python scripts/live_check.py https://<your-app>.onrender.com     # Render
python scripts/live_check.py http://127.0.0.1:8000               # PC-te local
```
Shob PASS hole backend thik. FAIL hole oi line-er niche hint thake. Demo account lagbe (`SEED_DEMO=true`).

## Bangla / English
Request-e header `Accept-Language: bn` ba `en` (ba `?lang=en`) dile backend-er shob user-facing text (decision explanation, alert, assistant reply, error, dispute report...) oi bhashay ashe. Default `bn`; `DEFAULT_LANG=en` env diye bodlano jay. Dropdown/label-er naam `GET /meta`-te Bangla+English duitei ache. Details: `docs/API_GUIDE.md` section 23.

## Demo data + role (frontend team-er sohoj kajer jonno)
- `SEED_DEMO=true` (Render Environment-e) dile startup-e demo account + sample lot/demand/order history toiri hoy. Password `demo1234`: farmer `01700000001`, buyer `01700000002`, admin `01700000003`. Production-e `SEED_DEMO=false`.
- Admin nijer phone/password chaile `ADMIN_PHONE` + `ADMIN_PASSWORD` set korun.
- Role: farmer/buyer nijer data-i change korte pare (onner id dile 403); admin dispute resolve, price ingest, dashboard.
- Notun endpoint: `/batches/from-photo`, `/orders`, `/prices/history`, `/prices/today`, `/dashboard/*`, `PUT /auth/me`. Details `docs/API_GUIDE.md`.

## Weather API key (optional, free)
1. openweathermap.org -> Sign up -> profile menu > **My API keys** -> key copy (active hote 10 min - 2 ghonta lagte pare).
2. **Render:** Environment-e `OPENWEATHER_API_KEY` = key. **Local (PowerShell):** `$env:OPENWEATHER_API_KEY="key"`.
3. Check: `/weather?district=Dhaka` e `"available": true` asha chai. Key na thakle backend default 30C ba request-er `temperature_c` use kore, kono error hoy na.

## Alerts / voice negotiation app-e kivabe
- Push notification backend pathay na. App periodically `GET /alerts/farmer/{id}` call kore notification dekhabe.
- Voice: app speech-to-text -> `/assistant/chat` ba `/negotiation/counter-offer` -> text uttor/ `draft_message_bn` -> text-to-speech. Draft farmer review kore pathabe.
