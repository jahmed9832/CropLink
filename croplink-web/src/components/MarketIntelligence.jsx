import { useMemo, useRef, useState } from 'react';
import SampleBadge from './SampleBadge.jsx';
import { SAMPLE_CROPS, HISTORY_DAYS, FORECAST_DAYS, formatBDT } from '../data/sample.js';
import { useInView } from '../hooks/useInView.js';

const W = 800;
const H = 360;
const PAD = { l: 54, r: 18, t: 20, b: 34 };

export default function MarketIntelligence() {
  const [crop, setCrop] = useState(SAMPLE_CROPS[0]);
  const [hover, setHover] = useState(null);
  const [ref, seen] = useInView(0.25);
  const svgRef = useRef(null);

  const geo = useMemo(() => {
    const total = HISTORY_DAYS + FORECAST_DAYS;
    const lows = [...crop.history, ...crop.forecast.low];
    const highs = [...crop.history, ...crop.forecast.high];
    const min = Math.floor(Math.min(...lows) - 2);
    const max = Math.ceil(Math.max(...highs) + 2);
    const x = (i) => PAD.l + (i / (total - 1)) * (W - PAD.l - PAD.r);
    const y = (v) => PAD.t + (1 - (v - min) / (max - min)) * (H - PAD.t - PAD.b);
    const todayIdx = HISTORY_DAYS - 1;
    const line = (vals, start) => vals.map((v, i) => `${i ? 'L' : 'M'}${x(start + i).toFixed(1)} ${y(v).toFixed(1)}`).join(' ');
    const histPath = line(crop.history, 0);
    const basePath = line([crop.current, ...crop.forecast.base], todayIdx);
    const up = [crop.current, ...crop.forecast.high].map((v, i) => `${x(todayIdx + i).toFixed(1)} ${y(v).toFixed(1)}`);
    const dn = [crop.current, ...crop.forecast.low].map((v, i) => `${x(todayIdx + i).toFixed(1)} ${y(v).toFixed(1)}`).reverse();
    const band = `M${up.join(' L')} L${dn.join(' L')} Z`;
    const ticks = [0, 1, 2, 3].map((k) => {
      const v = min + ((max - min) * k) / 3;
      return { v, y: y(v) };
    });
    const oppIdx = todayIdx + crop.bestDay;
    const oppVal = crop.bestDay === 0 ? crop.current : crop.forecast.base[crop.bestDay - 1];
    return { x, y, histPath, basePath, band, ticks, todayIdx, oppIdx, oppVal, total };
  }, [crop]);

  const valueAt = (i) => {
    if (i <= geo.todayIdx) return { v: crop.history[i], range: null, label: `${geo.todayIdx - i}d ago` };
    const k = i - geo.todayIdx - 1;
    return { v: crop.forecast.base[k], range: [crop.forecast.low[k], crop.forecast.high[k]], label: `+${k + 1}d (forecast)` };
  };

  const onMove = (e) => {
    const r = svgRef.current.getBoundingClientRect();
    const px = ((e.clientX - r.left) / r.width) * W;
    const i = Math.round(((px - PAD.l) / (W - PAD.l - PAD.r)) * (geo.total - 1));
    setHover(Math.max(0, Math.min(geo.total - 1, i)));
  };

  const hv = hover == null ? null : valueAt(hover);
  const up = crop.change7d >= 0;

  return (
    <section id="intelligence" className="intel" ref={ref}>
      <div className="wrap">
        <p className="eyebrow" data-rise>
          Market intelligence
        </p>
        <h2 className="display display--center" data-rise>
          Every Decision.
          <br />
          A Little Smarter.
        </h2>

        <div className={`intel__panel ${seen ? 'is-in' : ''}`} data-rise>
          <div className="intel__head">
            <div className="dash__tabs" role="tablist" aria-label="Sample crop">
              {SAMPLE_CROPS.map((c) => (
                <button key={c.id} role="tab" aria-selected={c.id === crop.id} className={c.id === crop.id ? 'is-on' : ''} onClick={() => { setCrop(c); setHover(null); }}>
                  {c.name}
                </button>
              ))}
            </div>
            <SampleBadge>Demonstration data</SampleBadge>
          </div>

          <div className="intel__body">
            <div className="chart" onPointerMove={onMove} onPointerLeave={() => setHover(null)}>
              <svg ref={svgRef} key={crop.id} viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Sample ${crop.name} price chart with forecast range`}>
                {geo.ticks.map((t) => (
                  <g key={t.v}>
                    <line x1={PAD.l} x2={W - PAD.r} y1={t.y} y2={t.y} className="chart__grid" />
                    <text x={PAD.l - 10} y={t.y + 4} textAnchor="end" className="chart__tick">
                      ৳{Math.round(t.v)}
                    </text>
                  </g>
                ))}
                <text x={PAD.l} y={H - 8} className="chart__tick">−30 days</text>
                <text x={geo.x(geo.todayIdx)} y={H - 8} textAnchor="middle" className="chart__tick">Today</text>
                <text x={W - PAD.r} y={H - 8} textAnchor="end" className="chart__tick">+14 days</text>

                <line x1={geo.x(geo.todayIdx)} x2={geo.x(geo.todayIdx)} y1={PAD.t} y2={H - PAD.b} className="chart__today" />
                <path d={geo.band} className={`chart__band ${seen ? 'is-in' : ''}`} />
                <path d={geo.histPath} pathLength="1" className={`chart__line ${seen ? 'is-drawn' : ''}`} />
                <path d={geo.basePath} pathLength="1" className={`chart__base ${seen ? 'is-drawn' : ''}`} />

                <circle cx={geo.x(geo.todayIdx)} cy={geo.y(crop.current)} r="5" className="chart__now" />
                <g className={`chart__opp ${seen ? 'is-in' : ''}`}>
                  <circle cx={geo.x(geo.oppIdx)} cy={geo.y(geo.oppVal)} r="11" className="chart__opp-halo" />
                  <circle cx={geo.x(geo.oppIdx)} cy={geo.y(geo.oppVal)} r="5.5" className="chart__opp-dot" />
                </g>

                {hover != null && (
                  <g>
                    <line x1={geo.x(hover)} x2={geo.x(hover)} y1={PAD.t} y2={H - PAD.b} className="chart__cursor" />
                    <circle cx={geo.x(hover)} cy={geo.y(hv.v)} r="4.5" className="chart__cursor-dot" />
                  </g>
                )}
              </svg>
              {hv && (
                <div className="chart__tip" style={{ left: `clamp(70px, ${(geo.x(hover) / W) * 100}%, calc(100% - 70px))` }}>
                  <strong>৳{hv.v.toFixed(1)}</strong>
                  <span>{hv.label}</span>
                  {hv.range && (
                    <span>
                      range ৳{hv.range[0].toFixed(0)}–{hv.range[1].toFixed(0)}
                    </span>
                  )}
                </div>
              )}
              <div className="chart__legend">
                <span><i className="lg lg--line" /> Sample history</span>
                <span><i className="lg lg--band" /> Forecast range (not a confirmed price)</span>
                <span><i className="lg lg--opp" /> Sample selling window</span>
              </div>
            </div>

            <aside className="intel__stats">
              <div>
                <span className="dash__label">Current crop price</span>
                <strong className="stat">৳{crop.current.toFixed(1)}<small>/kg</small></strong>
              </div>
              <div>
                <span className="dash__label">Price trend · 7 days</span>
                <strong className={`stat stat--sm ${up ? 'is-up' : 'is-down'}`}>{up ? '+' : ''}{crop.change7d}%</strong>
              </div>
              <div className="stat-opp">
                <span className="dash__label">Selling opportunity</span>
                <strong className="stat stat--sm">{crop.bestDay === 0 ? 'Now' : `~${crop.bestDay} days out`}</strong>
                <em>{crop.recommendation}</em>
              </div>
              <div>
                <span className="dash__label">Estimated profit</span>
                <strong className="stat stat--sm">{formatBDT(crop.profitNow)} → {formatBDT(crop.bestProfit)}</strong>
                <em>now vs. best case · {crop.qty} kg · sample assumptions</em>
              </div>
            </aside>
          </div>
          <p className="intel__note">
            Demonstration data for illustration only. These are not real market prices or accurate forecasts. In CropLink, forecasts are presented as ranges and are never a guarantee.
          </p>
        </div>
      </div>
    </section>
  );
}
