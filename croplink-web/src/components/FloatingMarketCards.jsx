import Sparkline from './Sparkline.jsx';
import SampleBadge from './SampleBadge.jsx';
import { SAMPLE_CROPS } from '../data/sample.js';

const tomato = SAMPLE_CROPS[0];

// Small DOM cards orbiting the island. They respond to the cursor via --mx/--my
// (set by usePointerVars on the hero element). All values are labelled samples.
export default function FloatingMarketCards() {
  return (
    <div className="fcards" aria-hidden="true">
      <div className="fcard fcard--1" style={{ '--d': 16 }}>
        <div className="fcard__in">
          <div className="fcard__row">
            <span className="fcard__label">Tomato · market price</span>
            <SampleBadge />
          </div>
          <div className="fcard__big">
            ৳{tomato.current.toFixed(0)}
            <small>/kg</small>
          </div>
          <Sparkline data={tomato.history.slice(-16)} width={150} height={32} />
        </div>
      </div>
      <div className="fcard fcard--2" style={{ '--d': 26 }}>
        <div className="fcard__in">
          <span className="fcard__label">Selling window</span>
          <div className="fcard__med">Forecast range, not a promise</div>
          <div className="fcard__bar">
            <span />
          </div>
        </div>
      </div>
      <div className="fcard fcard--3" style={{ '--d': 12 }}>
        <div className="fcard__in">
          <span className="fcard__label">Demand radar</span>
          <div className="fcard__med">
            <i className="pulse-dot" /> Buyers nearby
          </div>
        </div>
      </div>
    </div>
  );
}
