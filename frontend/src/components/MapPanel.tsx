import { useCallback, useState } from 'react';
import type { EvacuationPlan, ReplayStep, Shelter } from '../shared/types';
import { GeoRouteMap } from './GeoRouteMap';
import { MapLibreCanvas } from './MapLibreCanvas';
import { Pill } from './Shared';

const HAS_MAP_STYLE = Boolean(import.meta.env.VITE_BASEMAP_STYLE_URL || import.meta.env.VITE_TILES_BASE);

export function MapPanel({ step, plan, shelter, compact = false, lite = false }: {
  step: ReplayStep; plan: EvacuationPlan | null; shelter: Shelter | null; compact?: boolean; lite?: boolean;
}) {
  const [mapError, setMapError] = useState('');
  const onFallback = useCallback((reason: string) => setMapError(reason), []);
  const showMap = HAS_MAP_STYLE && !lite;
  return <div className="map-panel">
    <div className="map-panel-top"><div><div className="eyebrow">FIELD VIEW <span>·</span> {step.at.slice(0, 10)}</div><h2>Street plan</h2></div>
      <div className="map-layer-pills"><Pill tone={step.sources.flood === 'missing' ? 'neutral' : 'blue'}>Flood {step.sources.flood === 'missing' ? 'unavailable' : 'on'}</Pill><Pill tone={step.sources.roads === 'missing' ? 'neutral' : 'amber'}>Roads {step.sources.roads === 'missing' ? 'unavailable' : 'on'}</Pill></div>
    </div>
    {showMap && !mapError ? <>
      <MapLibreCanvas step={step} plan={plan} shelter={shelter} onFallback={onFallback}/>
      <div className="map-route-underlay"><GeoRouteMap step={step} plan={plan} shelter={shelter} compact/></div>
    </> : <GeoRouteMap step={step} plan={plan} shelter={shelter} compact={compact || lite}/>}
    {mapError && <p className="map-fallback-note" role="status">{mapError}</p>}
    {step.sources.flood === 'missing' && <p className="map-fallback-note">No flood polygon is published for this timestamp. The map does not carry a previous extent forward.</p>}
  </div>;
}

