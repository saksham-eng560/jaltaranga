import type { ForecastNode, GaugeReading, Manifest } from '../shared/types';
import { formatIST } from '../lib/replay';
import { numberIN } from '../lib/format';

const WIDTH = 620, HEIGHT = 210, PAD = { left: 44, right: 18, top: 20, bottom: 34 };

export function GaugeChart({ gauges, forecasts, at, thresholds, manifest, streetLevel }: {
  gauges: GaugeReading[]; forecasts: ForecastNode[]; at: string; thresholds?: Manifest['thresholds']; manifest?: Manifest; streetLevel?: number;
}) {
  const points = gauges.filter((item) => item.level_m !== null).slice(-12);
  const forecast = forecasts.filter((item) => Number.isFinite(item.level_m)).slice().sort((a, b) => Date.parse(a.valid_at) - Date.parse(b.valid_at));
  const values = [...points.map((p) => p.level_m as number), ...forecast.flatMap((p) => [p.lo_m, p.level_m, p.hi_m]), ...(streetLevel !== undefined ? [streetLevel] : [])];
  const min = Math.floor((Math.min(...values, 203) - 0.3) * 2) / 2;
  const max = Math.ceil((Math.max(...values, 209) + 0.3) * 2) / 2;
  const times = [...points.map((p) => Date.parse(p.ts)), ...forecast.map((p) => Date.parse(p.valid_at))];
  const xMin = Math.min(...times, Date.parse(at));
  const xMax = Math.max(...times, Date.parse(at) + 1);
  const x = (t: number) => PAD.left + ((t - xMin) / (xMax - xMin)) * (WIDTH - PAD.left - PAD.right);
  const y = (v: number) => PAD.top + ((max - v) / (max - min)) * (HEIGHT - PAD.top - PAD.bottom);
  const observed = points.map((p) => `${x(Date.parse(p.ts))},${y(p.level_m as number)}`).join(' ');
  const band = forecast.length ? `${forecast.map((p) => `${x(Date.parse(p.valid_at))},${y(p.hi_m)}`).join(' ')} ${forecast.slice().reverse().map((p) => `${x(Date.parse(p.valid_at))},${y(p.lo_m)}`).join(' ')}` : '';
  const lines = [
    ['warning', thresholds?.warning ?? 204.5, 'amber'],
    ['danger', thresholds?.danger ?? 205.33, 'red'],
    ['evacuation', thresholds?.evacuation ?? 206, 'violet'],
  ] as const;
  const xAt = x(Date.parse(at));
  return <div className="gauge-chart-wrap">
    <div className="chart-legend"><span><i className="legend-swatch observed"/>Gauge anchors</span>{forecast.length > 0 && <span><i className="legend-swatch fan"/>80% forecast interval</span>}
      {streetLevel !== undefined && <span><i className="legend-swatch street"/>Colony wet threshold</span>}</div>
    <svg className="gauge-chart" viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-label="Gauge level history and forecast">
      <title>Delhi Railway Bridge gauge level (metres above MSL)</title>
      {Array.from({ length: 4 }, (_, i) => { const value = min + ((max - min) * i) / 3; return <g key={value}>
        <line x1={PAD.left} x2={WIDTH - PAD.right} y1={y(value)} y2={y(value)} className="chart-grid"/>
        <text x={PAD.left - 8} y={y(value) + 4} textAnchor="end" className="chart-axis-label">{numberIN(value, 1)}</text>
      </g>; })}
      {lines.map(([key, value, color]) => <g key={key}>
        {value >= min && value <= max && <><line x1={PAD.left} x2={WIDTH - PAD.right} y1={y(value)} y2={y(value)} className={`threshold-line threshold-${color}`}/><text x={WIDTH - PAD.right - 2} y={y(value) - 4} textAnchor="end" className={`threshold-label threshold-${color}`}>{key} {value.toFixed(2)} m</text></>}
      </g>)}
      {streetLevel !== undefined && streetLevel >= min && streetLevel <= max && <g><line x1={PAD.left} x2={WIDTH - PAD.right} y1={y(streetLevel)} y2={y(streetLevel)} className="threshold-line threshold-street"/><text x={PAD.left + 5} y={y(streetLevel) - 5} className="threshold-label threshold-street">Colony wet {streetLevel.toFixed(2)} m</text></g>}
      {band && <polygon points={band} className="forecast-band"/>}
      {forecast.length > 1 && <polyline points={forecast.map((p) => `${x(Date.parse(p.valid_at))},${y(p.level_m)}`).join(' ')} className="forecast-line"/>}
      {observed && <polyline points={observed} className="observed-line"/>}
      {points.map((point) => <circle key={point.ts} cx={x(Date.parse(point.ts))} cy={y(point.level_m as number)} r="4" className="observed-point"><title>{`${formatIST(point.ts)} · ${numberIN(point.level_m, 2)} m · ${point.source_ref || point.source}`}</title></circle>)}
      <line x1={xAt} x2={xAt} y1={PAD.top} y2={HEIGHT - PAD.bottom} className="current-time-line"/>
      <text x={xAt} y={HEIGHT - 10} textAnchor="middle" className="chart-axis-label">selected time</text>
      <text x={PAD.left} y={HEIGHT - 10} className="chart-axis-label">{formatIST(new Date(xMin).toISOString(), { day: '2-digit', month: 'short' })}</text>
      <text x={WIDTH - PAD.right} y={HEIGHT - 10} textAnchor="end" className="chart-axis-label">{formatIST(new Date(xMax).toISOString(), { day: '2-digit', month: 'short' })}</text>
    </svg>
    {forecast.length === 0 && <p className="chart-note">No forecast issuance is available at this replay time. The fan is omitted rather than backfilled from a later forecast.</p>}
    <p className="chart-source">CWC Delhi Railway Bridge · m above MSL · {manifest?.ref_station || 'DELHI_RLY_BRIDGE'} · source recorded per point</p>
  </div>;
}

