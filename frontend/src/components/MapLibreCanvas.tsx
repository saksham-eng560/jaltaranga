import { useEffect, useRef, useState } from 'react';
import type { Map, StyleSpecification, GeoJSONSource } from 'maplibre-gl';
import type { EvacuationPlan, ReplayStep, Shelter } from '../shared/types';
import { lineCoordinates } from '../lib/geo';

const STYLE_URL = import.meta.env.VITE_BASEMAP_STYLE_URL || '';
const TILES_BASE = (import.meta.env.VITE_TILES_BASE || '').replace(/\/$/, '');
const TERRAIN_BASE = (import.meta.env.VITE_TERRAIN_BASE || '').replace(/\/$/, '');

function defaultDarkStyle(): StyleSpecification {
  return {
    version: 8,
    sources: {
      'carto-dark': {
        type: 'raster',
        tiles: [
          'https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png',
          'https://b.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png',
          'https://c.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png',
          'https://d.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png',
        ],
        tileSize: 256,
        attribution: '© OpenStreetMap contributors, © CARTO',
      },
    },
    layers: [
      {
        id: 'carto-dark-tiles',
        type: 'raster',
        source: 'carto-dark',
        minzoom: 0,
        maxzoom: 19,
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
      // Fallback to raster style if PMTiles protocol fails
    }
  }
  return defaultDarkStyle();
}

function asCollection(value: unknown): GeoJSON.FeatureCollection {
  return (value as GeoJSON.FeatureCollection | null) || { type: 'FeatureCollection', features: [] };
}

const YAMUNA_RIVER_GEOJSON: GeoJSON.FeatureCollection = {
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
};

export function MapLibreCanvas({ step, plan, shelter, onFallback }: {
  step: ReplayStep; plan: EvacuationPlan | null; shelter: Shelter | null; onFallback: (reason: string) => void;
}) {
  const element = useRef<HTMLDivElement>(null);
  const mapRef = useRef<Map | null>(null);
  const isLoadedRef = useRef(false);
  const [mode, setMode] = useState('2D');

  const updateMapData = (mapInstance: Map, currentStep: ReplayStep, currentPlan: EvacuationPlan | null, currentShelter: Shelter | null) => {
    const empty: GeoJSON.FeatureCollection = { type: 'FeatureCollection', features: [] };

    // 1. Roads
    const roadsSource = mapInstance.getSource('roads') as GeoJSONSource | undefined;
    if (roadsSource) {
      roadsSource.setData(asCollection(currentStep.roadGeometry));
      (currentStep.roads || []).forEach((status) => {
        try { mapInstance.setFeatureState({ source: 'roads', id: status.edge_id }, { status: status.status }); } catch { /* Ignore */ }
      });
    }

    // 2. Flood
    const floodSource = mapInstance.getSource('flood') as GeoJSONSource | undefined;
    if (floodSource) {
      floodSource.setData(currentStep.flood || empty);
    }

    // 3. Primary Route
    const primarySource = mapInstance.getSource('primary-route') as GeoJSONSource | undefined;
    const routeFeature = currentPlan?.primary?.route_geojson as unknown as GeoJSON.Feature | undefined;
    if (primarySource) {
      primarySource.setData(routeFeature || empty);
    }

    // 4. Backup Route
    const backupSource = mapInstance.getSource('backup-route') as GeoJSONSource | undefined;
    const backupFeature = currentPlan?.backup?.route_geojson as unknown as GeoJSON.Feature | undefined;
    if (backupSource) {
      backupSource.setData(backupFeature || empty);
    }

    // 5. Origin Point
    const coordinates = currentPlan?.primary?.route_geojson ? lineCoordinates(currentPlan.primary.route_geojson) : [];
    const originSource = mapInstance.getSource('route-origin') as GeoJSONSource | undefined;
    if (originSource) {
      originSource.setData(coordinates.length > 0 ? {
        type: 'Feature',
        geometry: { type: 'Point', coordinates: coordinates[0] },
        properties: { title: currentPlan?.colony_id || 'Colony' },
      } : empty);
    }

    // 6. Shelters
    const sheltersSource = mapInstance.getSource('shelters') as GeoJSONSource | undefined;
    if (sheltersSource) {
      sheltersSource.setData({
        type: 'FeatureCollection',
        features: currentStep.shelters.map((item) => ({
          type: 'Feature',
          geometry: { type: 'Point', coordinates: item.location },
          properties: { id: item.shelter_id, name_en: item.name_en },
        })),
      });
    }

    // 7. Camera Fit
    if (coordinates.length > 1) {
      void (async () => {
        const maplibre = await import('maplibre-gl');
        const bounds = new maplibre.LngLatBounds(coordinates[0] as [number, number], coordinates[0] as [number, number]);
        coordinates.forEach((point) => bounds.extend(point as [number, number]));
        mapInstance.fitBounds(bounds, { padding: 60, maxZoom: 14.5 });
      })();
    } else {
      const selected = currentStep.shelters.find((item) => item.shelter_id === currentShelter?.shelter_id);
      if (selected) {
        mapInstance.setCenter(selected.location);
      }
    }
  };

  useEffect(() => {
    let cancelled = false;

    void (async () => {
      try {
        const maplibre = await import('maplibre-gl');
        await import('maplibre-gl/dist/maplibre-gl.css');

        if (cancelled || !element.current) return;

        const hasWebGL = Boolean(
          window.WebGLRenderingContext &&
          (document.createElement('canvas').getContext('webgl') || document.createElement('canvas').getContext('experimental-webgl'))
        );
        if (!hasWebGL) {
          onFallback('WebGL is not supported in this browser environment; falling back to vector route sketch.');
          return;
        }

        const style = await styleForMap();
        if (cancelled || !element.current || !style) return;

        const coordinates = plan?.primary?.route_geojson ? lineCoordinates(plan.primary.route_geojson) : [];
        const center = coordinates.length ? coordinates[Math.floor(coordinates.length / 2)] : [77.24, 28.66];

        const mapInstance = new maplibre.Map({
          container: element.current,
          style: style as string | StyleSpecification,
          center: center as [number, number],
          zoom: 12.5,
          pitch: 35,
        });

        mapRef.current = mapInstance;
        mapInstance.addControl(new maplibre.NavigationControl({ showCompass: true, showZoom: true }), 'top-right');

        mapInstance.once('load', () => {
          if (cancelled) return;
          isLoadedRef.current = true;
          mapInstance.resize();

          const empty: GeoJSON.FeatureCollection = { type: 'FeatureCollection', features: [] };

          // 1. Yamuna River Guide
          mapInstance.addSource('yamuna-river', {
            type: 'geojson',
            data: YAMUNA_RIVER_GEOJSON,
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

          // 2. Road Network
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

          // 3. Flood Extent
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

          // 6. Route Origin
          mapInstance.addSource('route-origin', {
            type: 'geojson',
            data: coordinates.length > 0 ? {
              type: 'Feature',
              geometry: { type: 'Point', coordinates: coordinates[0] },
              properties: { title: plan?.colony_id || 'Colony' },
            } : empty,
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

          // 7. Shelters
          mapInstance.addSource('shelters', {
            type: 'geojson',
            data: {
              type: 'FeatureCollection',
              features: step.shelters.map((item) => ({
                type: 'Feature',
                geometry: { type: 'Point', coordinates: item.location },
                properties: { id: item.shelter_id, name_en: item.name_en },
              })),
            },
          });
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

          // 8. 3D Terrain
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

          // Initial data population and fit
          updateMapData(mapInstance, step, plan, shelter);
        });

        // Log harmless tile/network events without destroying the map view
        mapInstance.on('error', (event) => {
          console.warn('MapLibre event:', event.error?.message || event);
        });
      } catch (err) {
        console.error('MapLibre init error:', err);
        if (!cancelled) onFallback('Map engine could not initialize; vector route sketch displayed.');
      }
    })();

    return () => {
      cancelled = true;
      isLoadedRef.current = false;
      mapRef.current?.remove();
      mapRef.current = null;
    };
  }, [onFallback]);

  // Update dynamic layers reactively without destroying the MapLibre canvas
  useEffect(() => {
    if (mapRef.current && isLoadedRef.current) {
      updateMapData(mapRef.current, step, plan, shelter);
    }
  }, [step, plan, shelter]);

  // Resize handler for responsive tabs and layout adjustments
  useEffect(() => {
    const handleResize = () => mapRef.current?.resize();
    window.addEventListener('resize', handleResize);
    const timer = setTimeout(handleResize, 350);
    return () => {
      window.removeEventListener('resize', handleResize);
      clearTimeout(timer);
    };
  }, []);

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
