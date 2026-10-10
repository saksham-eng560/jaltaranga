import { useEffect, useRef, useState } from 'react';
import type { Map, StyleSpecification } from 'maplibre-gl';
import type { EvacuationPlan, ReplayStep, Shelter } from '../shared/types';
import { lineCoordinates } from '../lib/geo';

const STYLE_URL = import.meta.env.VITE_BASEMAP_STYLE_URL || '';
const TILES_BASE = (import.meta.env.VITE_TILES_BASE || '').replace(/\/$/, '');
const TERRAIN_BASE = (import.meta.env.VITE_TERRAIN_BASE || '').replace(/\/$/, '');

function defaultRasterStyle(): StyleSpecification {
  return {
    version: 8,
    sources: {
      osm: {
        type: 'raster',
        tiles: ['https://tile.openstreetmap.de/{z}/{x}/{y}.png'],
        tileSize: 256,
        attribution: '© OpenStreetMap contributors',
      },
    },
    layers: [
      {
        id: 'osm-tiles',
        type: 'raster',
        source: 'osm',
        minzoom: 0,
        maxzoom: 19,
        paint: {
          'raster-saturation': -0.15,
          'raster-contrast': 0.1,
        },
      },
    ],
  };
}

async function styleForMap(): Promise<unknown | null> {
  if (STYLE_URL) return STYLE_URL;
  if (TILES_BASE) {
    try {
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
        layers: layers('protomaps', namedFlavor('dark')),
      };
    } catch {
      // Fallback to OSM raster if PMTiles protocol fails
    }
  }
  return defaultRasterStyle();
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

        const coordinates = plan?.primary?.route_geojson ? lineCoordinates(plan.primary.route_geojson) : [];
        const center = coordinates.length ? coordinates[Math.floor(coordinates.length / 2)] : [77.24, 28.66];
        const mapInstance = new maplibre.Map({
          container: element.current,
          style: style as string | StyleSpecification,
          center: center as [number, number],
          zoom: 12.5,
          pitch: 35,
        });
        map = mapInstance;
        mapInstance.addControl(new maplibre.NavigationControl({ showCompass: true, showZoom: true }), 'top-right');

        mapInstance.once('load', () => {
          const empty: GeoJSON.FeatureCollection = { type: 'FeatureCollection', features: [] };

          // 1. Yamuna River Channel Guide
          mapInstance.addSource('yamuna-river', {
            type: 'geojson',
            data: {
              type: 'FeatureCollection',
              features: [
                {
                  type: 'Feature',
                  properties: { name: 'Yamuna River' },
                  geometry: {
                    type: 'LineString',
                    coordinates: [
                      [77.23, 28.71],
                      [77.235, 28.69],
                      [77.245, 28.66],
                      [77.255, 28.63],
                      [77.28, 28.58],
                      [77.31, 28.54],
                    ],
                  },
                },
              ],
            },
          });
          mapInstance.addLayer({
            id: 'yamuna-river-halo',
            type: 'line',
            source: 'yamuna-river',
            paint: { 'line-color': '#ffffff', 'line-width': 10, 'line-opacity': 0.6 },
          });
          mapInstance.addLayer({
            id: 'yamuna-river-line',
            type: 'line',
            source: 'yamuna-river',
            paint: { 'line-color': '#0284c7', 'line-width': 6, 'line-opacity': 0.85 },
          });

          // 2. Road Network & Inundation State
          mapInstance.addSource('roads', { type: 'geojson', data: asCollection(step.roadGeometry), promoteId: 'edge_id' });
          mapInstance.addLayer({
            id: 'roads-state',
            type: 'line',
            source: 'roads',
            paint: {
              'line-color': ['match', ['feature-state', 'status'], 'red', '#c84037', 'amber', '#c18924', 'green', '#2a8b6f', '#8d9997'],
              'line-width': ['interpolate', ['linear'], ['zoom'], 10, 1.5, 15, 4],
              'line-dasharray': ['case', ['==', ['feature-state', 'status'], 'red'], ['literal', [1, 1]], ['literal', [1, 0]]],
            },
          });
          (step.roads || []).forEach((status) => {
            try { mapInstance.setFeatureState({ source: 'roads', id: status.edge_id }, { status: status.status }); } catch { /* Ignore */ }
          });

          // 3. Flood Depth Polygons
          mapInstance.addSource('flood', { type: 'geojson', data: step.flood || empty });
          mapInstance.addLayer({
            id: 'flood-depth',
            type: 'fill',
            source: 'flood',
            paint: {
              'fill-color': ['match', ['get', 'depth_class'], '0.05-0.3', '#60c9ff', '0.3-1', '#249bff', '1-2', '#126de0', '>2', '#1246a0', '#4aaeff'],
              'fill-opacity': 0.62,
            },
          });

          // 4. Primary Route
          const routeFeature = plan?.primary.route_geojson as unknown as GeoJSON.Feature | undefined;
          mapInstance.addSource('primary-route', { type: 'geojson', data: routeFeature || empty });
          mapInstance.addLayer({
            id: 'primary-route-halo',
            type: 'line',
            source: 'primary-route',
            paint: { 'line-color': '#0f172a', 'line-width': 8, 'line-opacity': 0.7 },
          });
          mapInstance.addLayer({
            id: 'primary-route-line',
            type: 'line',
            source: 'primary-route',
            paint: { 'line-color': '#38bdf8', 'line-width': 5, 'line-opacity': 0.95 },
          });

          // 5. Backup Route
          const backupFeature = plan?.backup?.route_geojson as unknown as GeoJSON.Feature | undefined;
          mapInstance.addSource('backup-route', { type: 'geojson', data: backupFeature || empty });
          mapInstance.addLayer({
            id: 'backup-route-line',
            type: 'line',
            source: 'backup-route',
            paint: { 'line-color': '#fbbf24', 'line-width': 3.5, 'line-dasharray': [2, 2] },
          });

          // 6. Route Origin Pin
          if (coordinates.length > 0) {
            mapInstance.addSource('route-origin', {
              type: 'geojson',
              data: {
                type: 'Feature',
                geometry: { type: 'Point', coordinates: coordinates[0] },
                properties: { title: plan?.colony_id || 'Colony' },
              },
            });
            mapInstance.addLayer({
              id: 'route-origin-point',
              type: 'circle',
              source: 'route-origin',
              paint: {
                'circle-radius': 7,
                'circle-color': '#ef4444',
                'circle-stroke-width': 3,
                'circle-stroke-color': '#ffffff',
              },
            });
          }

          // 7. Shelters
          const sheltersGeo: GeoJSON.FeatureCollection = {
            type: 'FeatureCollection',
            features: step.shelters.map((item) => ({
              type: 'Feature',
              geometry: { type: 'Point', coordinates: item.location },
              properties: { id: item.shelter_id, name_en: item.name_en },
            })),
          };
          mapInstance.addSource('shelters', { type: 'geojson', data: sheltersGeo });
          mapInstance.addLayer({
            id: 'shelter-points',
            type: 'circle',
            source: 'shelters',
            paint: {
              'circle-radius': 6,
              'circle-color': '#10b981',
              'circle-stroke-width': 2,
              'circle-stroke-color': '#ffffff',
            },
          });

          // 8. Terrain support if configured
          if (TERRAIN_BASE && mapInstance.getCanvas().getContext('webgl2')) {
            mapInstance.addSource('terrain-dem', {
              type: 'raster-dem',
              tiles: [`${TERRAIN_BASE}/{z}/{x}/{y}.png`],
              encoding: 'terrarium',
              tileSize: 256,
              minzoom: 8,
              maxzoom: 13,
              bounds: [77.2, 28.53, 77.33, 28.75],
            });
            mapInstance.setTerrain({ source: 'terrain-dem', exaggeration: 6 });
            setMode('2.5D');
          } else {
            setMode('2D');
          }

          // 9. Camera Fit
          if (coordinates.length > 1) {
            const bounds = new maplibre.LngLatBounds(coordinates[0] as [number, number], coordinates[0] as [number, number]);
            coordinates.forEach((point) => bounds.extend(point as [number, number]));
            mapInstance.fitBounds(bounds, { padding: 60, maxZoom: 14.5 });
          }

          const selected = step.shelters.find((item) => item.shelter_id === shelter?.shelter_id);
          if (selected && coordinates.length <= 1) {
            mapInstance.setCenter(selected.location);
          }
        });

        mapInstance.on('error', (event) => {
          if (event.error?.message) {
            onFallback('Basemap tiles could not be loaded; route details remain available below.');
          }
        });
      } catch {
        if (!cancelled) onFallback('Map engine could not initialize; the route SVG remains available.');
      }
    })();

    return () => {
      cancelled = true;
      map?.remove();
    };
  }, [onFallback, plan, shelter, step]);

  return (
    <div className="maplibre-shell" style={{ position: 'relative', width: '100%', height: '100%', minHeight: '320px' }}>
      <div
        className="maplibre-canvas"
        ref={element}
        aria-label="Interactive flood and evacuation map"
        role="img"
        style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, width: '100%', height: '100%' }}
      />
      <span className="map-mode-pill">{mode}</span>
    </div>
  );
}
