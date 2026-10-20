export type Series = {
  name: string;
  color: string;
  points: { x: number; y: number | null }[];
  dashed?: boolean;
  dotsOnly?: boolean;
};

type Props = {
  series: Series[];
  xLabels: { x: number; label: string }[];
  yLabel: string;
  height?: number;
  highlightFrom?: number;
  highlightLabel?: string;
  ariaLabel: string;
};

const W = 720;
const PAD = { left: 48, right: 16, top: 16, bottom: 32 };

export function LineChart({ series, xLabels, yLabel, height = 260, highlightFrom, highlightLabel, ariaLabel }: Props) {
  const all = series.flatMap((s) => s.points).filter((p): p is { x: number; y: number } => p.y !== null);
  const xs = all.map((p) => p.x).concat(xLabels.map((l) => l.x));
  const ys = all.map((p) => p.y);
  const [xMin, xMax] = [Math.min(...xs), Math.max(...xs)];
  const span = Math.max(...ys) - Math.min(...ys) || 1;
  const [yMin, yMax] = [Math.min(...ys) - span * 0.1, Math.max(...ys) + span * 0.1];
  const x = (v: number) => PAD.left + ((v - xMin) / (xMax - xMin || 1)) * (W - PAD.left - PAD.right);
  const y = (v: number) => PAD.top + (1 - (v - yMin) / (yMax - yMin)) * (height - PAD.top - PAD.bottom);
  const ticks = Array.from({ length: 5 }, (_, i) => yMin + ((yMax - yMin) * i) / 4);

  return (
    <figure className="chart">
      <svg viewBox={`0 0 ${W} ${height}`} role="img" aria-label={ariaLabel}>
        {highlightFrom !== undefined && (
          <>
            <rect x={x(highlightFrom)} y={PAD.top} width={W - PAD.right - x(highlightFrom)}
              height={height - PAD.top - PAD.bottom} className="chart-highlight" />
            {highlightLabel && <text x={x(highlightFrom) + 8} y={PAD.top + 14} className="chart-note">{highlightLabel}</text>}
          </>
        )}
        {ticks.map((t) => (
          <g key={t}>
            <line x1={PAD.left} x2={W - PAD.right} y1={y(t)} y2={y(t)} className="chart-grid" />
            <text x={PAD.left - 8} y={y(t) + 4} textAnchor="end" className="chart-axis">{t.toFixed(1)}</text>
          </g>
        ))}
        {xLabels.map((l) => (
          <text key={l.x} x={x(l.x)} y={height - 10} textAnchor="middle" className="chart-axis">{l.label}</text>
        ))}
        <text x={14} y={height / 2} transform={`rotate(-90 14 ${height / 2})`} textAnchor="middle" className="chart-axis">
          {yLabel}
        </text>
        {series.map((s) => {
          const pts = s.points.filter((p): p is { x: number; y: number } => p.y !== null);
          const d = pts.map((p, i) => `${i ? "L" : "M"}${x(p.x).toFixed(1)},${y(p.y).toFixed(1)}`).join(" ");
          return (
            <g key={s.name}>
              {!s.dotsOnly && <path d={d} fill="none" stroke={s.color} strokeWidth={2} strokeDasharray={s.dashed ? "5 5" : undefined} />}
              {pts.map((p) => (
                <circle key={p.x} cx={x(p.x)} cy={y(p.y)} r={s.dotsOnly ? 5 : 3} fill={s.color}>
                  <title>{`${s.name}: ${p.y.toFixed(2)}`}</title>
                </circle>
              ))}
            </g>
          );
        })}
      </svg>
      <figcaption className="legend">
        {series.map((s) => (
          <span key={s.name}>
            <i style={{ background: s.color }} className={s.dashed ? "dashed" : undefined} /> {s.name}
          </span>
        ))}
      </figcaption>
    </figure>
  );
}
