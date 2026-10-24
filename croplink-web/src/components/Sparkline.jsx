// Tiny SVG line. pathLength=1 lets CSS animate the stroke draw without measuring.
export default function Sparkline({ data, width = 120, height = 36, drawn = true, className = '' }) {
  const min = Math.min(...data);
  const max = Math.max(...data);
  const span = max - min || 1;
  const pts = data.map((v, i) => [(i / (data.length - 1)) * width, height - 3 - ((v - min) / span) * (height - 6)]);
  const d = pts.map((p, i) => `${i ? 'L' : 'M'}${p[0].toFixed(1)} ${p[1].toFixed(1)}`).join(' ');
  const last = pts[pts.length - 1];
  return (
    <svg className={`spark ${drawn ? 'is-drawn' : ''} ${className}`} viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none" aria-hidden="true">
      <path d={d} pathLength="1" className="spark__line" />
      <circle cx={last[0]} cy={last[1]} r="2.6" className="spark__dot" />
    </svg>
  );
}
