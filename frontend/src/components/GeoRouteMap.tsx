import { useMemo } from 'react';
import type { EvacuationPlan, ReplayStep, Shelter } from '../shared/types';
import { lineCoordinates, projectLines } from '../lib/geo';

export function GeoRouteMap({ step, plan, shelter, compact = false }: { step: ReplayStep; plan: EvacuationPlan | null; shelter: Shelter | null; compact?: boolean }) {
  const coords = useMemo(() => plan ? lineCoordinates(plan.primary.route_geojson) : [], [plan]);
  const backupCoords = useMemo(() => plan?.backup ? lineCoordinates(plan.backup.route_geojson) : [], [plan]);
  const [path, backup] = useMemo(() => projectLines([coords, backupCoords], 600, 340, 54), [coords, backupCoords]);
  const start = path.match(/^M([\d.]+),([\d.]+)/)?.slice(1).map(Number);
  const end = [...path.matchAll(/[ML]([\d.]+),([\d.]+)/g)].at(-1)?.slice(1).map(Number);
  const namedAvoids = plan?.avoid || [];
  return <div className={`route-map ${compact ? 'route-map-compact' : ''}`}>
    <div className="map-annotation"><span className="map-coordinate"><i/>Route geometry</span><span>{step.roadGeometry ? 'Road network available' : 'Basemap / road geometry unavailable'}</span></div>
    {coords.length >= 2 ? <svg className="route-map-svg" viewBox="0 0 600 340" role="img" aria-label="Evacuation route map showing the route geometry from the plan">
      <defs><pattern id="map-grid" width="28" height="28" patternUnits="userSpaceOnUse"><path d="M28 0H0V28" fill="none" stroke="#263b53" strokeWidth="1"/></pattern></defs>
      <rect width="600" height="340" fill="#101b2a"/>
      <rect width="600" height="340" fill="url(#map-grid)"/>
      <text x="22" y="30" className="map-label map-label-muted">ROUTE SKETCH · WGS84 COORDINATES</text>
      {backup && <path d={backup} className="route-line route-line-backup"/>}
      <path d={path} className="route-line route-line-primary"/>
      {start && <g><circle cx={start[0]} cy={start[1]} r="10" className="map-origin-ring"/><circle cx={start[0]} cy={start[1]} r="4" className="map-origin"/><text x={Number(start[0]) + 13} y={Number(start[1]) - 9} className="map-label">Colony route origin</text></g>}
      {end && <g><circle cx={end[0]} cy={end[1]} r="10" className="map-shelter-ring"/><path d={`M${Number(end[0]) - 3} ${Number(end[1])}h6m-3-3v6`} className="map-shelter-mark"/><text x={Number(end[0]) + 13} y={Number(end[1]) - 9} className="map-label">{shelter?.name_en || 'Plan destination'}</text></g>}
      <g className="map-north" transform="translate(555 42)"><path d="M0 22 7 0l7 22-7-5-7 5Z"/><text x="7" y="34" textAnchor="middle">N</text></g>
      <text x="20" y="320" className="map-label map-label-muted">Route line from the selected evacuation plan · no unprovided road geometry is drawn</text>
    </svg> : <div className="map-no-route"><span>—</span><strong>Route geometry unavailable</strong><small>No route is drawn until the selected plan provides coordinates.</small></div>}
    <div className="map-legend"><span><i className="map-key map-key-origin"/>Plan origin</span><span><i className="map-key map-key-route"/>Primary route</span>{backup && <span><i className="map-key map-key-backup"/>Backup</span>}<span><i className="map-key map-key-shelter"/>Destination</span></div>
    {namedAvoids.length > 0 && <div className="map-avoid-note"><strong>Do not use:</strong> {namedAvoids.map((item) => item.name_en).join(', ')} <span>— closure geometry unavailable</span></div>}
  </div>;
}
