import { useCallback, useState } from 'react';
import type { EvacuationPlan, ReplayStep, Shelter } from '../shared/types';
import { GeoRouteMap } from './GeoRouteMap';
import { MapLibreCanvas } from './MapLibreCanvas';
import { Pill } from './Shared';

// MapLibreCanvas provides a built-in OpenStreetMap raster tile fallback,
// so the interactive map is always available unless the user explicitly requests lite mode.
const HAS_MAP_STYLE = true;

export function MapPanel({ step, plan, shelter, compact = false, lite = false }: {
  step: ReplayStep; plan: EvacuationPlan | null; shelter: Shelter | null; compact?: boolean; lite?: boolean;
}) {
  const [mapError, setMapError] = useState('');
  const onFallback = useCallback((reason: string) => setMapError(reason), []);
  const showMap = HAS_MAP_STYLE && !lite;

  return (
    <div className="map-panel" style={{ display: 'flex', flexDirection: 'column', height: '100%', minHeight: compact ? '240px' : '360px' }}>
      <div className="map-panel-top">
        <div>
          <div className="eyebrow">FIELD VIEW <span>·</span> {step.at.slice(0, 10)}</div>
          <h2>Street plan & flood extent</h2>
        </div>
        <div className="map-layer-pills">
          <Pill tone={step.sources.flood === 'missing' ? 'neutral' : 'blue'}>
            Flood {step.sources.flood === 'missing' ? 'unavailable' : 'active'}
          </Pill>
          <Pill tone={step.sources.roads === 'missing' ? 'neutral' : 'amber'}>
            Roads {step.sources.roads === 'missing' ? 'unavailable' : 'monitored'}
          </Pill>
        </div>
      </div>

      <div style={{ flex: 1, position: 'relative', width: '100%', minHeight: compact ? '200px' : '300px' }}>
        {showMap && !mapError ? (
          <MapLibreCanvas step={step} plan={plan} shelter={shelter} onFallback={onFallback} />
        ) : (
          <GeoRouteMap step={step} plan={plan} shelter={shelter} compact={compact || lite} />
        )}
      </div>

      {mapError && <p className="map-fallback-note" role="status">{mapError}</p>}
      {step.sources.flood === 'missing' && (
        <p className="map-fallback-note">
          No flood polygon is published for this timestamp. The map does not carry a previous extent forward.
        </p>
      )}
    </div>
  );
}
