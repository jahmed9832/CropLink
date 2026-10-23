"""Price forecasting: HistGradientBoosting (log-ratio target), baseline-er sathe compare kora."""
import json
import math
import os
from datetime import date, timedelta

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

from ..config import settings
from ..i18n import t
from ..engine.constants import BASE_PRICE, CROPS, MARKETS

HORIZONS = (7, 14)
LAGS = (1, 3, 7, 14)
MIN_HISTORY = 15
PEAK_DOY = {"tomato": 20, "potato": 80, "onion": 300, "brinjal": 200, "chili": 330, "cabbage": 340, "rice": 120}
MARKET_MULT = {"Dhaka": 1.08, "Chattogram": 1.04, "Rajshahi": 0.95, "Bogura": 0.93, "Khulna": 0.99}


def synthetic_prices(days=1825, seed=42, end=None):
    """Seasonal + multi-harmonic cycles + climate shocks + trend + AR noise. Generates 5 years of rich daily market data."""
    rng = np.random.default_rng(seed)
    end = end or date.today()
    start = end - timedelta(days=days - 1)
    rows = []
    for crop in CROPS:
        for mk in MARKETS:
            noise, trend = 0.0, 1.0
            for i in range(days):
                d = start + timedelta(days=i)
                doy = d.timetuple().tm_yday
                # Primary annual harvest cycle
                seas1 = 0.28 * math.cos(2 * math.pi * (doy - PEAK_DOY[crop]) / 365)
                # Secondary mid-season / monsoon supply fluctuation
                seas2 = 0.08 * math.sin(4 * math.pi * (doy - 100) / 365)
                seas = 1.0 + seas1 + seas2

                # Auto-regressive price inertia
                noise = 0.94 * noise + rng.normal(0, 0.014)
                trend *= 1 + rng.normal(0.0001, 0.0012)

                # Realistic supply shock (flood, strike, Ramadan demand peak)
                spike = 1.0
                if rng.random() < 0.008:
                    spike = 1 + rng.uniform(0.08, 0.28)

                p = BASE_PRICE[crop] * MARKET_MULT[mk] * seas * trend * math.exp(noise) * spike
                rows.append((d.isoformat(), crop, mk, round(max(5.0, p), 2)))
    return pd.DataFrame(rows, columns=["date", "crop", "market", "price"])


def load_prices():
    path = os.path.join(settings.DATA_DIR, "dam_prices.csv")
    if os.path.exists(path):
        df = pd.read_csv(path)
        need = {"date", "crop", "market", "price"}
        if need.issubset(df.columns):
            return df[list(need)].dropna(), "real_csv"
    return synthetic_prices(), "synthetic"


def features(prices, d, crop, market):
    """prices: list (oldest->latest), len >= 15."""
    p = prices[-1]
    f = [p / prices[-1 - l] for l in LAGS]
    f.append(float(np.std(prices[-7:]) / p))
    f.append(p / float(np.mean(prices[-30:])))
    doy = d.timetuple().tm_yday
    f += [math.sin(2 * math.pi * doy / 365), math.cos(2 * math.pi * doy / 365)]
    f += [1.0 if crop == c else 0.0 for c in CROPS]
    f += [1.0 if market == m else 0.0 for m in MARKETS]
    return f


def train(df=None, source=None):
    if df is None:
        df, source = load_prices()
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    X = {h: [] for h in HORIZONS}
    y = {h: [] for h in HORIZONS}
    dates = {h: [] for h in HORIZONS}
    naive = {h: [] for h in HORIZONS}
    for (crop, mk), g in df.groupby(["crop", "market"]):
        g = g.sort_values("date")
        pr = g["price"].tolist()
        ds = g["date"].dt.date.tolist()
        for i in range(30, len(pr) - max(HORIZONS), 2):
            f = features(pr[: i + 1], ds[i], crop, mk)
            for h in HORIZONS:
                X[h].append(f)
                y[h].append(math.log(pr[i + h] / pr[i]))
                dates[h].append(ds[i])
                naive[h].append((pr[i], pr[i + h]))
    models, metrics = {}, {"data_source": source, "horizons": {}}
    for h in HORIZONS:
        Xh, yh = np.array(X[h]), np.array(y[h])
        order = np.argsort(np.array(dates[h], dtype="datetime64[D]"))
        cut = int(len(order) * 0.85)
        tr, te = order[:cut], order[cut:]
        m = HistGradientBoostingRegressor(max_iter=200, learning_rate=0.06, max_depth=5, random_state=0)
        m.fit(Xh[tr], yh[tr])
        pred = m.predict(Xh[te])
        res = yh[te] - pred
        nv = np.array(naive[h])[te]
        actual = nv[:, 1]
        pm = nv[:, 0] * np.exp(pred)
        mape = float(np.mean(np.abs(pm - actual) / actual) * 100)
        mape_naive = float(np.mean(np.abs(nv[:, 0] - actual) / actual) * 100)
        mae = float(np.mean(np.abs(pm - actual)))
        m.fit(Xh, yh)  # final: all data
        models[h] = {"model": m, "q10": float(np.quantile(res, 0.10)), "q90": float(np.quantile(res, 0.90))}
        metrics["horizons"][str(h)] = {"mape_pct": round(mape, 2), "mape_naive_pct": round(mape_naive, 2),
                                       "mae_bdt": round(mae, 2), "n_test": int(len(te))}
    # bundled latest history (fallback jodi DB-te price na thake)
    latest = {}
    for (crop, mk), g in df.groupby(["crop", "market"]):
        g = g.sort_values("date").tail(120)
        latest[f"{crop}|{mk}"] = [[str(d.date()), float(p)] for d, p in zip(g["date"], g["price"])]
    os.makedirs(settings.MODELS_DIR, exist_ok=True)
    joblib.dump(models, os.path.join(settings.MODELS_DIR, "forecaster.joblib"))
    with open(os.path.join(settings.MODELS_DIR, "latest_prices.json"), "w") as fh:
        json.dump(latest, fh)
    with open(os.path.join(settings.MODELS_DIR, "forecaster_metrics.json"), "w") as fh:
        json.dump(metrics, fh, indent=2)
    return metrics


class Forecaster:
    def __init__(self):
        self.models = joblib.load(os.path.join(settings.MODELS_DIR, "forecaster.joblib"))
        with open(os.path.join(settings.MODELS_DIR, "latest_prices.json")) as fh:
            self.latest = json.load(fh)
        with open(os.path.join(settings.MODELS_DIR, "forecaster_metrics.json")) as fh:
            self.metrics = json.load(fh)

    def bundled_series(self, crop, market):
        return self.latest.get(f"{crop}|{market}")

    def forecast(self, crop, market, series, as_of=None):
        """series: [[date, price], ...] oldest->latest. Returns h7/h14 low/base/high."""
        if len(series) < MIN_HISTORY:
            raise ValueError(t("fc.short", n=MIN_HISTORY))
        prices = [float(p) for _, p in series]
        d = as_of or date.fromisoformat(str(series[-1][0])[:10])
        f = np.array([features(prices, d, crop, market)])
        out = {"current_price": round(prices[-1], 2), "as_of": str(d)}
        for h in HORIZONS:
            m = self.models[h]
            lr = float(m["model"].predict(f)[0])
            p = prices[-1]
            out[f"h{h}"] = {"low": round(p * math.exp(lr + m["q10"]), 2), "base": round(p * math.exp(lr), 2),
                            "high": round(p * math.exp(lr + m["q90"]), 2)}
        b7 = out["h7"]["base"]
        out["trend"] = "up" if b7 > prices[-1] * 1.03 else "down" if b7 < prices[-1] * 0.97 else "flat"
        out["data_points_used"] = len(prices)
        out["metrics"] = {k: v for k, v in self.metrics["horizons"].items()}
        out["data_source"] = self.metrics.get("data_source")
        out["note"] = t("fc.note")
        return out
