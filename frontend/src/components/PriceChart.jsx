import { useState } from "react";
import { formatDate, formatINR, formatNumber } from "../utils/format.js";

// Hand-written SVG line chart (no chart library): easy to read and to explain.
const W = 800;
const H = 300;
const PAD = { top: 16, right: 16, bottom: 28, left: 64 };

export default function PriceChart({ history }) {
  const [hover, setHover] = useState(null); // index of the hovered / focused point
  if (!history || history.length < 2) return <p className="muted">Not enough price history to draw a chart.</p>;

  const closes = history.map((d) => d.close);
  const lo = Math.min(...closes);
  const hi = Math.max(...closes);
  const span = hi - lo || 1;
  const yMin = lo - span * 0.1;
  const yMax = hi + span * 0.1;

  const innerW = W - PAD.left - PAD.right;
  const innerH = H - PAD.top - PAD.bottom;
  const x = (i) => PAD.left + (i / (history.length - 1)) * innerW;
  const y = (v) => PAD.top + (1 - (v - yMin) / (yMax - yMin)) * innerH;

  const line = history.map((d, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(d.close).toFixed(1)}`).join(" ");
  const area = `${line} L${x(history.length - 1).toFixed(1)},${H - PAD.bottom} L${x(0).toFixed(1)},${H - PAD.bottom} Z`;
  const up = closes[closes.length - 1] >= closes[0];
  const color = up ? "var(--gain)" : "var(--loss)";

  const yTicks = [0, 1, 2, 3].map((k) => yMin + ((yMax - yMin) * k) / 3);
  const xTicks = [0, Math.floor((history.length - 1) / 2), history.length - 1];

  function onMove(e) {
    const rect = e.currentTarget.getBoundingClientRect();
    const px = ((e.clientX - rect.left) / rect.width) * W; // mouse x in SVG units
    const i = Math.round(((px - PAD.left) / innerW) * (history.length - 1));
    setHover(Math.max(0, Math.min(history.length - 1, i)));
  }

  const point = hover !== null ? history[hover] : null;

  return (
    <div className="chart">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-label={`Closing price for the last ${history.length} trading days, from ${formatINR(closes[0])} to ${formatINR(closes[closes.length - 1])}`}
        onMouseMove={onMove}
        onMouseLeave={() => setHover(null)}
      >
        {yTicks.map((t) => (
          <g key={t}>
            <line x1={PAD.left} x2={W - PAD.right} y1={y(t)} y2={y(t)} className="chart-grid" />
            <text x={PAD.left - 8} y={y(t) + 4} textAnchor="end" className="chart-label">
              {Math.round(t).toLocaleString("en-IN")}
            </text>
          </g>
        ))}
        {xTicks.map((i) => (
          <text key={i} x={x(i)} y={H - 8} textAnchor={i === 0 ? "start" : i === history.length - 1 ? "end" : "middle"} className="chart-label">
            {formatDate(history[i].date)}
          </text>
        ))}
        <path d={area} fill={color} opacity="0.08" />
        <path d={line} fill="none" stroke={color} strokeWidth="2" strokeLinejoin="round" />
        {point && (
          <g>
            <line x1={x(hover)} x2={x(hover)} y1={PAD.top} y2={H - PAD.bottom} className="chart-guide" />
            <circle cx={x(hover)} cy={y(point.close)} r="5" fill={color} stroke="var(--surface)" strokeWidth="2" />
          </g>
        )}
      </svg>

      {point && (
        <div className="chart-tooltip" style={{ left: `${(x(hover) / W) * 100}%` }} role="status">
          <strong>{formatDate(point.date)}</strong>
          <div>Close {formatINR(point.close)}</div>
          <div className="muted">
            O {formatINR(point.open)} · H {formatINR(point.high)} · L {formatINR(point.low)}
          </div>
          <div className="muted">Vol {formatNumber(point.volume)}</div>
        </div>
      )}
    </div>
  );
}
