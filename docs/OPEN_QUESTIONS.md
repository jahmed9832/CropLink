# CropLink Open Questions (REQ-Q)

This document tracks ambiguous agricultural business rules, external dependencies, and system policies where current behavior is maintained as specified in the audit report.

---

### REQ-Q-01: Real DAM Data Source and Staleness Limit
- **Question**: What is the authoritative Department of Agricultural Marketing (DAM) data source / API endpoint, and what is the maximum acceptable staleness (data age in days) before market prices are rejected as stale?
- **Current Behavior**: If `data/dam_prices.csv` is absent and `prices` collection has fewer than 15 points, the system falls back to the bundled synthetic series (`models/latest_prices.json`). When `ALLOW_SYNTHETIC_DATA=false`, endpoints return HTTP 503 with code `no_real_price_data`. When `ALLOW_SYNTHETIC_DATA=true`, responses flag `is_synthetic: true` with `as_of` and `data_age_days`.

### REQ-Q-02: Grade Factor on Current Price
- **Question**: Is `current_price` from DAM or forecaster considered a baseline for Grade B produce, and should `GRADE_FACTOR` (A: 1.15, B: 1.0, C: 0.8) be applied when pricing different grades?
- **Current Behavior**: The system uses `current_price` directly as the benchmark price without applying multiplicative grade adjustments unless explicitly passed by the caller.

### REQ-Q-03: Platform Commission on Direct Offers
- **Question**: Does CropLink levy a platform commission percentage on direct buyer offers in negotiation and net-profit calculations?
- **Current Behavior**: In negotiation, `commission_pct` defaults to 0% if omitted, and input validation ensures `commission_pct < 100` to prevent division by zero.

### REQ-Q-04: Storage Cost per Crop and Heat Factor
- **Question**: What are the empirical daily storage costs (BDT/kg/day) and temperature heat damage acceleration factors per crop across Bangladesh's agro-climatic zones?
- **Current Behavior**: Uses default spoilage rates per crop (e.g. potato 0.004, rice 0.0008, tomato 0.015) in net-profit decision analysis, clamped to prevent negative margins.

### REQ-Q-05: Order Creation Authority and Agreed Price Setting
- **Question**: Who is authorized to create orders and establish `agreed_price`? Does the farmer need an explicit confirmation step before the order becomes binding?
- **Current Behavior**: Demands and lots are matched into orders. For lot allocations, each farmer in the allocation must either be the caller, or the caller must be the buyer or admin. If allocated quantity is less than the lot quantity, the lot is split into a reserved portion and an open remainder lot with the same attributes and leftover kg.

### REQ-Q-06: Escrow Refund on Cancelled Funded Order
- **Question**: When a funded order is cancelled, should the funds automatically return to the buyer's balance, or does it require an admin audit / refund step?
- **Current Behavior**: Order cancellation re-opens any still-reserved lots and re-opens the demand. Escrow refund from `funded` to `refunded` requires admin role (`require_role(u, 'admin')`).

### REQ-Q-07: Local Market Distance and Dhaka Reference Price
- **Question**: What default distance should be used for local market offers when unspecified, and why is Dhaka used as the baseline market when caller location is unknown?
- **Current Behavior**: Missing offer distance defaults to `local_market_km` (15 km), matching `negotiation.py`. Dhaka is used as the default central reference market.

### REQ-Q-08: Matching Weights, Fairness Bands, and Radar Thresholds
- **Question**: What are the exact weightings for distance vs price vs reliability in offer ranking, and how are fairness bands determined?
- **Current Behavior**: Current ranking formula uses weighted linear combination of price uplift, distance penalty, and buyer reliability rating. In demand radar, confirmed orders == 0 are displayed as 0 with note.

### REQ-Q-09: Dispute Deduction Impact on Escrow Payment
- **Question**: Does the buyer's `proposed_deduction_pct` in a delivery dispute automatically deduct from the seller's final escrow payout upon release, or does it only serve as advisory evidence for admin resolution?
- **Current Behavior**: Dispute reports provide structured evidence (`discrepancies`, `needs_human_review`). Admin resolves dispute via `/orders/{id}/dispute/resolve` with one of the allowed statuses before or during fund release.

### REQ-Q-10: Gemini Model Identification and Offline Verification
- **Question**: Which Gemini model family names (`gemini-2.5-flash`, `gemini-1.5-flash`, etc.) are guaranteed available for production deployment?
- **Current Behavior**: Configured via `GEMINI_MODEL` (defaulting to `gemini-2.5-flash`). Rule-based engines handle price, sell/wait, loss, and negotiation intents; Gemini is only invoked for general greetings/chat when `GEMINI_API_KEY` is present.
