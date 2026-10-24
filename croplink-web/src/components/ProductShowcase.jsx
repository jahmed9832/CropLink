import { useRef, useState } from 'react';
import { TrendingUp, TrendingDown, Sparkles } from 'lucide-react';
import Sparkline from './Sparkline.jsx';
import SampleBadge from './SampleBadge.jsx';
import { SAMPLE_CROPS, formatBDT } from '../data/sample.js';
import { useInView } from '../hooks/useInView.js';
import { useCountUp } from '../hooks/useCountUp.js';

function Dashboard() {
  const [crop, setCrop] = useState(SAMPLE_CROPS[0]);
  const [ref, seen] = useInView(0.3);
  const tilt = useRef(null);
  const price = useCountUp(crop.current, seen);
  const profit = useCountUp(crop.bestProfit, seen);
  const up = crop.change7d >= 0;

  const onMove = (e) => {
    const el = tilt.current;
    if (!el || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const r = el.getBoundingClientRect();
    const x = (e.clientX - r.left) / r.width - 0.5;
    const y = (e.clientY - r.top) / r.height - 0.5;
    el.style.setProperty('--rx', `${(-y * 5).toFixed(2)}deg`);
    el.style.setProperty('--ry', `${(x * 7).toFixed(2)}deg`);
  };
  const onLeave = () => {
    tilt.current?.style.setProperty('--rx', '0deg');
    tilt.current?.style.setProperty('--ry', '0deg');
  };

  return (
    <div className="dash-wrap" ref={ref} onPointerMove={onMove} onPointerLeave={onLeave}>
      <div className={`dash ${seen ? 'is-in' : ''}`} ref={tilt}>
        <div className="dash__top">
          <div className="dash__tabs" role="tablist" aria-label="Sample crop">
            {SAMPLE_CROPS.map((c) => (
              <button key={c.id} role="tab" aria-selected={c.id === crop.id} className={c.id === crop.id ? 'is-on' : ''} onClick={() => setCrop(c)}>
                {c.name}
              </button>
            ))}
          </div>
          <SampleBadge>Sample data</SampleBadge>
        </div>

        <div className="dash__main">
          <div>
            <span className="dash__label">Current market price</span>
            <div className="dash__price">
              ৳{price.toFixed(1)}
              <small>/kg</small>
            </div>
            <span className={`dash__chg ${up ? 'is-up' : 'is-down'}`}>
              {up ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
              {up ? '+' : ''}
              {crop.change7d}% · 7 days
            </span>
          </div>
          <div className="dash__spark">
            <Sparkline key={crop.id} data={crop.history} width={260} height={74} drawn={seen} />
            <span className="dash__label">30-day trend</span>
          </div>
        </div>

        <div className="dash__grid">
          <div className="dash__cell">
            <span className="dash__label">Estimated profit</span>
            <strong>{formatBDT(profit)}</strong>
            <em>
              best case in sample · {crop.qty} kg
            </em>
          </div>
          <div className="dash__cell">
            <span className="dash__label">Market demand</span>
            <strong>{crop.demand}</strong>
            <div className="dash__meter">
              <span style={{ width: seen ? `${crop.demandPct}%` : '0%' }} />
            </div>
          </div>
        </div>

        <div className="dash__ai">
          <Sparkles size={16} />
          <div>
            <span className="dash__label">Recommendation</span>
            <p>{crop.recommendation}</p>
          </div>
        </div>
      </div>
      <p className="dash__note">Illustrative sample values — not live prices, and not financial advice.</p>
    </div>
  );
}

export default function ProductShowcase() {
  return (
    <section id="platform" className="showcase">
      <div className="wrap showcase__grid">
        <div className="showcase__copy">
          <p className="eyebrow" data-rise>
            The platform
          </p>
          <h2 className="display" data-rise>
            An Intelligent Market.
            <br />
            Built Around the Farmer.
          </h2>
          <p className="lead" data-rise>
            CropLink brings market intelligence, agricultural insights, and farmer-buyer connections together in one connected platform.
          </p>
          <ul className="showcase__list" data-rise>
            <li>Net-profit decisions: sell now, wait, or take an offer</li>
            <li>Price forecasts shown as ranges</li>
            <li>Buyer matching, cooperative pooling and negotiation help</li>
          </ul>
        </div>
        <Dashboard />
      </div>
    </section>
  );
}
