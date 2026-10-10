import { useEffect, useRef, useState } from 'react';
import type { Map, StyleSpecification } from 'maplibre-gl';
import type { EvacuationPlan, ReplayStep, Shelter } from '../shared/types';

const STYLE_URL = import.meta.env.VITE_BASEMAP_STYLE_URL || '';
const TILES_BASE = (import.meta.env.VITE_TILES_BASE || '').replace(/\/$/, '');
const TERRAIN_BASE = (import.meta.env.VITE_TERRAIN_BASE || '').replace(/\/$/, '');

async function styleForMap(): Promise<unknown | null> {
  if (STYLE_URL) return STYLE_URL;
  if (!TILES_BASE) return null;
  const [{ Protocol }, { layers, namedFlavor }] = await Promise.all([import('pmtiles'), import('@protomaps/basemaps')]);
  const protocol = new Protocol();
  const maplibre = await import('maplibre-gl');
  maplibre.addProtocol('pmtiles', protocol.tile);
  return {
    version: 8,
    sources: {
      protomaps: {
        type: 'vector',
        url: `pmtiles://${TILES_BASE}/tiles/basemap/delhi.pmtiles`,
        attribution: '© OpenStreetMap contributors',
      },
    },
    layers: layers('protomaps', namedFlavor('light')),
  };
}

function asCollection(value: unknown): GeoJSON.FeatureCollection {
  return (value as GeoJSON.FeatureCollection | null) || { type: 'FeatureCollection', features: [] };
}

export function MapLibreCanvas({ step, plan, shelter, onFallback }: {
  step: ReplayStep; plan: EvacuationPlan | null; shelter: Shelter | null; onFallback: (reason: string) => void;
}) {
  const element = useRef<HTMLDivElement>(null);
  const [mode, setMode] = useState('2D');
  useEffect(() => {
    let cancelled = false;
    let map: Map | undefined;
    void (async () => {
      try {
        const style = await styleForMap();
        if (!style || !element.current || cancelled) return;
        const maplibre = await import('maplibre-gl');
        await import('maplibre-gl/dist/maplibre-gl.css');
        if (cancelled || !element.current) return;
        const coordinates = plan?.primary.route_geojson.geometry.coordinates || [];
        const center = coordinates.length ? coordinates[Math.floor(coordinates.length / 2)] : [77.24, 28.66];
        const mapInstance = new maplibre.Map({ container: element.current, style: style as string | StyleSpecification, center: center as [number, number], zoom: 12.5, pitch: 35 });
        map = mapInstance;
        mapInstance.addControl(new maplibre.NavigationControl({ showCompass: true, showZoom: true }), 'top-right');
        mapInstance.once('load', () => {
          const empty: GeoJSON.FeatureCollection = { type: 'FeatureCollection', features: [] };
          mapInstance.addSource('roads', { type: 'geojson', data: asCollection(step.roadGeometry), promoteId: 'edge_id' });
          mapInstance.addLayer({ id: 'roads-state', type: 'line', source: 'roads', paint: {
            'line-color': ['match', ['feature-state', 'status'], 'red', '#c84037', 'amber', '#c18924', 'green', '#2a8b6f', '#8d9997'],
            'line-width': ['interpolate', ['linear'], ['zoom'], 10, 1.5, 15, 4],
            'line-dasharray': ['case', ['==', ['feature-state', 'status'], 'red'], ['literal', [1, 1]], ['literal', [1, 0]]],
          } });
          (step.roads || []).forEach((status) => {
            try { mapInstance.setFeatureState({ source: 'roads', id: status.edge_id }, { status: status.status }); } catch { /* Feature may be outside the current tile. */ }
          });
          mapInstance.addSource('flood', { type: 'geojson', data: step.flood || empty });
          mapInstance.addLayer({ id: 'flood-depth', type: 'fill', source: 'flood', paint: {
            'fill-color': ['match', ['get', 'depth_class'], '0.05-0.3', '#84c9d0', '0.3-1', '#4da7bd', '1-2', '#3378a0', '>2', '#254f78', '#68b7c5'],
            'fill-opacity': 0.55,
          } });
          const routeFeature = plan?.primary.route_geojson as unknown as GeoJSON.Feature | undefined;
          mapInstance.addSource('primary-route', { type: 'geojson', data: routeFeature || empty });
          mapInstance.addLayer({ id: 'primary-route-line', type: 'line', source: 'primary-route', paint: { 'line-color': '#167e66', 'line-width': 5, 'line-opacity': 0.92 } });
          const backupFeature = plan?.backup?.route_geojson as unknown as GeoJSON.Feature | undefined;
          mapInstance.addSource('backup-route', { type: 'geojson', data: backupFeature || empty });
          mapInstance.addLayer({ id: 'backup-route-line', type: 'line', source: 'backup-route', paint: { 'line-color': '#6f6bb1', 'line-width': 3, 'line-dasharray': [2, 2] } });
          const sheltersGeo: GeoJSON.FeatureCollection = {
            type: 'FeatureCollection', features: step.shelters.map((item) => ({ type: 'Feature', geometry: { type: 'Point', coordinates: item.location }, properties: { id: item.shelter_id, name_en: item.name_en } })),
          };
          mapInstance.addSource('shelters', { type: 'geojson', data: sheltersGeo });
          mapInstance.addLayer({ id: 'shelter-points', type: 'circle', source: 'shelters', paint: { 'circle-radius': 5, 'circle-color': '#28735f', 'circle-stroke-width': 2, 'circle-stroke-color': '#fff' } });
          if (TERRAIN_BASE && mapInstance.getCanvas().getContext('webgl2')) {
            mapInstance.addSource('terrain-dem', { type: 'raster-dem', tiles: [`${TERRAIN_BASE}/{z}/{x}/{y}.png`], encoding: 'terrarium', tileSize: 256, minzoom: 8, maxzoom: 13, bounds: [77.2, 28.53, 77.33, 28.75] });
            mapInstance.setTerrain({ source: 'terrain-dem', exaggeration: 6 });
            setMode('2.5D');
          } else setMode('2D');
          if (coordinates.length > 1) {
            const bounds = new maplibre.LngLatBounds(coordinates[0] as [number, number], coordinates[0] as [number, number]);
            coordinates.forEach((point) => bounds.extend(point as [number, number]));
            mapInstance.fitBounds(bounds, { padding: 70, maxZoom: 14 });
          }
          const selected = step.shelters.find((item) => item.shelter_id === shelter?.shelter_id);
          if (selected) mapInstance.setCenter(selected.location);
        });
        mapInstance.on('error', (event) => {
          if (event.error?.message) onFallback('Basemap tiles could not be loaded; route details remain available below.');
        });
      } catch {
        if (!cancelled) onFallback('Map engine could not initialize; the route SVG remains available.');
      }
    })();
    return () => { cancelled = true; map?.remove(); };
  }, [onFallback, plan, shelter, step]);

  return <div className="maplibre-shell"><div className="maplibre-canvas" ref={element} aria-label="Interactive flood and evacuation map" role="img"/><span className="map-mode-pill">{mode}</span></div>;
}

