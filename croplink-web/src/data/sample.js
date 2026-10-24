// ──────────────────────────────────────────────────────────────────────────
// ILLUSTRATIVE SAMPLE DATA. These are NOT real or live market prices and are
// not produced by the CropLink backend. Anonymous visitors cannot call the
// price/forecast endpoints (they require login), so the landing page only
// ever shows labelled demonstration values. Everything here is deterministic.
// ──────────────────────────────────────────────────────────────────────────

const HIST = 30;
const HORIZON = 14;

function make({ id, name, base, seed, vol, drift, trend, cost, qty, spoil, demand, demandPct }) {
  const history = [];
  for (let i = 0; i < HIST; i += 1) {
    const v =
      base *
      (1 + vol * Math.sin(i / 4.2 + seed) + vol * 0.4 * Math.sin(i / 1.7 + seed * 2) + (drift * (i - (HIST - 1))) / (HIST - 1));
    history.push(Math.round(v * 10) / 10);
  }
  const last = history[HIST - 1];
  const fBase = [];
  const fLow = [];
  const fHigh = [];
  for (let k = 1; k <= HORIZON; k += 1) {
    const b = last * (1 + trend * (k / HORIZON) + 0.012 * Math.sin(k / 2.3 + seed));
    fBase.push(Math.round(b * 10) / 10);
    fLow.push(Math.round(b * (1 - 0.022 - 0.004 * k) * 10) / 10);
    fHigh.push(Math.round(b * (1 + 0.022 + 0.004 * k) * 10) / 10);
  }
  // Sample net-income model: base forecast minus spoilage, minus cost, × quantity.
  const net = (price, days) => Math.round((price * (1 - spoil * days) - cost) * qty);
  const profitNow = net(last, 0);
  let bestDay = 0;
  let bestProfit = profitNow;
  fBase.forEach((b, i) => {
    const p = net(b, i + 1);
    if (p > bestProfit) {
      bestProfit = p;
      bestDay = i + 1;
    }
  });
  const week = history[HIST - 8];
  return {
    id,
    name,
    history,
    forecast: { base: fBase, low: fLow, high: fHigh },
    current: last,
    change7d: Math.round(((last / week - 1) * 100) * 10) / 10,
    cost,
    qty,
    profitNow,
    bestDay,
    bestProfit,
    demand,
    demandPct,
    recommendation:
      bestDay === 0
        ? 'Selling now looks strongest in this sample scenario.'
        : `Waiting about ${bestDay} day${bestDay > 1 ? 's' : ''} looks strongest in this sample scenario.`,
  };
}

export const SAMPLE_CROPS = [
  make({ id: 'tomato', name: 'Tomato', base: 64, seed: 0.6, vol: 0.06, drift: 0.05, trend: 0.07, cost: 41, qty: 500, spoil: 0.02, demand: 'Rising', demandPct: 72 }),
  make({ id: 'potato', name: 'Potato', base: 38, seed: 1.9, vol: 0.04, drift: 0.02, trend: 0.09, cost: 26, qty: 800, spoil: 0.004, demand: 'Steady', demandPct: 58 }),
  make({ id: 'onion', name: 'Onion', base: 58, seed: 3.1, vol: 0.05, drift: -0.04, trend: -0.03, cost: 40, qty: 600, spoil: 0.006, demand: 'Softening', demandPct: 41 }),
];

export const HISTORY_DAYS = HIST;
export const FORECAST_DAYS = HORIZON;
export const formatBDT = (n) => `৳${Math.round(n).toLocaleString('en-US')}`;
