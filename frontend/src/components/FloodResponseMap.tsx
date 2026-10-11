import { useCallback, useEffect, useRef, useState } from 'react';
import type { Map as MapLibreMap, StyleSpecification } from 'maplibre-gl';
import type { ColonyStatusPin, ReplayTimelineStep } from '../data/floodScenarioData';
import { Icon } from './Shared';

interface FloodResponseMapProps {
  timelineStep: ReplayTimelineStep;
  selectedColonyId: string;
  onSelectColony: (colonyId: string) => void;
}

const ESRI_DARK_STYLE: StyleSpecification = {
  version: 8,
  sources: {
    'esri-dark-base': {
      type: 'raster',
      tiles: [
        'https://services.arcgisonline.com/arcgis/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}',
      ],
      tileSize: 256,
      attribution: '© Esri, HERE, Garmin, OpenStreetMap contributors',
      maxzoom: 16,
    },
    'esri-dark-ref': {
      type: 'raster',
      tiles: [
        'https://services.arcgisonline.com/arcgis/rest/services/Canvas/World_Dark_Gray_Reference/MapServer/tile/{z}/{y}/{x}',
      ],
      tileSize: 256,
      maxzoom: 16,
    },
  },
  layers: [
    {
      id: 'esri-dark-base-tiles',
      type: 'raster',
      source: 'esri-dark-base',
      minzoom: 0,
      maxzoom: 19,
    },
    {
      id: 'esri-dark-ref-tiles',
      type: 'raster',
      source: 'esri-dark-ref',
      minzoom: 0,
      maxzoom: 19,
    },
  ],
};

// Severed Ring Road segment GeoJSON (ISBT to Salimgarh bypass)
const SEVERED_RING_ROAD_GEOJSON: GeoJSON.FeatureCollection = {
  type: 'FeatureCollection',
  features: [
    {
      type: 'Feature',
      properties: { name: 'Ring Road Severed Section', status: 'severed' },
      geometry: {
        type: 'LineString',
        coordinates: [
          [77.2285, 28.6690], // ISBT Kashmere Gate
          [77.2340, 28.6640],
          [77.2390, 28.6580], // Yamuna Bazar
          [77.2420, 28.6510], // Lal Qila Bypass
          [77.2450, 28.6440], // Salimgarh / Ring Road
        ],
      },
    },
    {
      type: 'Feature',
      properties: { name: 'Noida Link Road Alternate Route', status: 'alternate' },
      geometry: {
        type: 'LineString',
        coordinates: [
          [77.2600, 28.6480], // Geeta Colony bridge
          [77.2750, 28.6320], // Vikas Marg
          [77.2920, 28.6180], // Noida Link Road
          [77.2980, 28.6040], // Mayur Vihar
        ],
      },
    },
  ],
};

export function FloodResponseMap({
  timelineStep,
  selectedColonyId,
  onSelectColony,
}: FloodResponseMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const markersRef = useRef<Array<{ remove: () => void }>>([]);
  const [activeTooltip, setActiveTooltip] = useState<ColonyStatusPin | null>(null);
  const [webGlSupported, setWebGlSupported] = useState(true);

  // Initialize MapLibre
  useEffect(() => {
    let active = true;

    const checkWebGl = () => {
      try {
        const canvas = document.createElement('canvas');
        return Boolean(
          window.WebGLRenderingContext &&
            (canvas.getContext('webgl') || canvas.getContext('experimental-webgl'))
        );
      } catch {
        return false;
      }
    };

    if (!checkWebGl()) {
      setWebGlSupported(false);
      return;
    }

    void (async () => {
      try {
        const maplibre = await import('maplibre-gl');
        await import('maplibre-gl/dist/maplibre-gl.css');

        if (typeof maplibre.setWorkerUrl === 'function') {
          maplibre.setWorkerUrl('/maplibre-gl-worker.mjs');
        }

        if (!active || !containerRef.current) return;

        // Centered around the Yamuna River corridor in central Delhi
        const map = new maplibre.Map({
          container: containerRef.current,
          style: ESRI_DARK_STYLE,
          center: [77.258, 28.654],
          zoom: 11.85,
          attributionControl: false,
        });

        mapRef.current = map;

        map.once('load', () => {
          if (!active) return;
          map.resize();

          // 1. Add Flood Inundation Source & Layers
          map.addSource('flood-inundation', {
            type: 'geojson',
            data: timelineStep.floodGeoJson,
          });

          // Flood Water Glow / Halo
          map.addLayer({
            id: 'flood-glow',
            type: 'line',
            source: 'flood-inundation',
            paint: {
              'line-color': '#38bdf8',
              'line-width': 3,
              'line-opacity': 0.95,
            },
          });

          // Flood Water Body Fill
          map.addLayer({
            id: 'flood-fill',
            type: 'fill',
            source: 'flood-inundation',
            paint: {
              'fill-color': [
                'match',
                ['get', 'depth_class'],
                '>2',
                '#0284c7', // deep water
                '1-2',
                '#0ea5e9', // medium flood
                '#38bdf8', // low/edge flood
              ],
              'fill-opacity': 0.76,
            },
          });

          // 2. Add Severed Road & Alternate Route Layer on top
          map.addSource('severed-roads', {
            type: 'geojson',
            data: SEVERED_RING_ROAD_GEOJSON,
          });

          // Alternate route glow
          map.addLayer({
            id: 'alternate-road-line',
            type: 'line',
            source: 'severed-roads',
            filter: ['==', ['get', 'status'], 'alternate'],
            paint: {
              'line-color': '#38bdf8',
              'line-width': 4.5,
              'line-opacity': 0.85,
              'line-dasharray': [2, 1],
            },
          });

          // Severed Ring Road (Bright Red dashed alert line)
          map.addLayer({
            id: 'severed-road-glow',
            type: 'line',
            source: 'severed-roads',
            filter: ['==', ['get', 'status'], 'severed'],
            paint: {
              'line-color': '#ef4444',
              'line-width': 8,
              'line-opacity': 0.5,
            },
          });
          map.addLayer({
            id: 'severed-road-line',
            type: 'line',
            source: 'severed-roads',
            filter: ['==', ['get', 'status'], 'severed'],
            paint: {
              'line-color': '#ff4757',
              'line-width': 3.5,
              'line-dasharray': [2, 2],
            },
          });

          renderMarkers(map, timelineStep.pins, maplibre);
        });
      } catch (err) {
        console.warn('MapLibre init error:', err);
        setWebGlSupported(false);
      }
    })();

    return () => {
      active = false;
      markersRef.current.forEach((m) => m.remove());
      markersRef.current = [];
      mapRef.current?.remove();
      mapRef.current = null;
    };
  }, []);

  // Custom DOM Marker rendering
  const renderMarkers = useCallback(
    (map: MapLibreMap, pins: ColonyStatusPin[], maplibreModule?: unknown) => {
      // Clear existing markers
      markersRef.current.forEach((m) => m.remove());
      markersRef.current = [];

      void (async () => {
        const ml = maplibreModule || (await import('maplibre-gl'));
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const MarkerClass = (ml as any).Marker;

        pins.forEach((pin) => {
          const isSelected = pin.id === selectedColonyId;
          const el = document.createElement('div');
          el.className = `colony-map-pin pin-${pin.status} ${isSelected ? 'pin-selected' : ''}`;
          el.setAttribute('role', 'button');
          el.setAttribute('tabindex', '0');
          el.setAttribute('aria-label', `${pin.name} status ${pin.status}`);

          // Custom pin icon with colored teardrop and dot
          const pinColor =
            pin.status === 'critical'
              ? '#ef4444'
              : pin.status === 'warning'
              ? '#f59e0b'
              : '#10b981';

          el.innerHTML = `
            <svg width="28" height="34" viewBox="0 0 28 34" fill="none" xmlns="http://www.w3.org/2000/svg">
              <filter id="shadow-${pin.id}" x="0" y="0" width="28" height="34" filterUnits="userSpaceOnUse">
                <feDropShadow dx="0" dy="2" stdDeviation="2" flood-color="black" flood-opacity="0.6"/>
              </filter>
              <g filter="url(#shadow-${pin.id})">
                <path d="M14 0C6.268 0 0 6.268 0 14C0 24.5 14 32 14 32C14 32 28 24.5 28 14C28 6.268 21.732 0 14 0Z" fill="${pinColor}"/>
                <circle cx="14" cy="14" r="5.5" fill="#0f172a"/>
                <circle cx="14" cy="14" r="3" fill="#ffffff"/>
              </g>
            </svg>
          `;

          el.addEventListener('click', (e) => {
            e.stopPropagation();
            onSelectColony(pin.id);
            setActiveTooltip(pin);
          });

          const marker = new MarkerClass({ element: el, anchor: 'bottom' })
            .setLngLat(pin.coordinates)
            .addTo(map);

          markersRef.current.push(marker);
        });
      })();
    },
    [selectedColonyId, onSelectColony]
  );

  // Update map data when timeline step or selected colony changes
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;

    // 1. Update Flood polygons
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const floodSource = map.getSource('flood-inundation') as any;
    if (floodSource && floodSource.setData) {
      floodSource.setData(timelineStep.floodGeoJson);
    }

    // 2. Re-render markers for the current timeline step
    renderMarkers(map, timelineStep.pins);
  }, [timelineStep, renderMarkers]);

  // Map Controls
  const handleZoomIn = () => mapRef.current?.zoomIn();
  const handleZoomOut = () => mapRef.current?.zoomOut();
  const handleReset = () => {
    mapRef.current?.flyTo({ center: [77.258, 28.654], zoom: 11.85, pitch: 0, bearing: 0 });
  };

  return (
    <div className="flood-map-wrapper">
      {/* Map Header Overlay */}
      <div className="flood-map-header-bar">
        <h2 className="flood-map-title">FLOOD RESPONSE MAP</h2>
      </div>

      {/* MapLibre Canvas Container */}
      <div className="flood-map-canvas-container" ref={containerRef}>
        {!webGlSupported && (
          <div className="flood-map-fallback-banner">
            <Icon name="shield" size={16} />
            <span>WebGL unavailable in current mode. Displaying schematic view.</span>
          </div>
        )}
      </div>

      {/* Map Controls Top-Left (+ / - / Compass / Reset) */}
      <div className="flood-map-controls">
        <button
          className="map-ctrl-btn"
          onClick={handleZoomIn}
          aria-label="Zoom in"
          title="Zoom in"
        >
          <Icon name="plus" size={16} />
        </button>
        <button
          className="map-ctrl-btn"
          onClick={handleZoomOut}
          aria-label="Zoom out"
          title="Zoom out"
        >
          <Icon name="minus" size={16} />
        </button>
        <button
          className="map-ctrl-btn"
          onClick={handleReset}
          aria-label="Reset orientation"
          title="Reset orientation"
        >
          <Icon name="compass" size={16} />
        </button>
        <button
          className="map-ctrl-btn"
          onClick={handleReset}
          aria-label="Recenter map"
          title="Recenter"
        >
          <Icon name="target" size={16} />
        </button>
      </div>

      {/* Map Controls Bottom-Right (Recenter / + / -) */}
      <div className="flood-map-controls-bottom-right">
        <button
          className="map-ctrl-btn"
          onClick={handleReset}
          aria-label="Recenter map"
          title="Recenter"
        >
          <Icon name="target" size={16} />
        </button>
        <button
          className="map-ctrl-btn"
          onClick={handleZoomIn}
          aria-label="Zoom in"
          title="Zoom in"
        >
          <Icon name="plus" size={16} />
        </button>
        <button
          className="map-ctrl-btn"
          onClick={handleZoomOut}
          aria-label="Zoom out"
          title="Zoom out"
        >
          <Icon name="minus" size={16} />
        </button>
      </div>

      {/* Legend Overlay Top-Right: COLONY STATUS (Red, Amber, Green with descriptions) */}
      <div className="flood-map-legend-card legend-top-right" aria-label="Colony status detailed legend">
        <div className="legend-header">COLONY STATUS</div>
        <div className="legend-items">
          <div className="legend-row">
            <span className="status-dot dot-red" />
            <span className="legend-label">
              <strong>RED</strong> (Critical/Active Evacuation)
            </span>
          </div>
          <div className="legend-row">
            <span className="status-dot dot-amber" />
            <span className="legend-label">
              <strong>AMBER</strong> (Warning/Pending)
            </span>
          </div>
          <div className="legend-row">
            <span className="status-dot dot-green" />
            <span className="legend-label">
              <strong>GREEN</strong> (Monitoring/Safe)
            </span>
          </div>
        </div>
      </div>

      {/* Legend Overlay Bottom-Left: COLONY STATUS */}
      <div className="flood-map-legend-card legend-bottom-left" aria-label="Colony status compact legend">
        <div className="legend-header">COLONY STATUS</div>
        <div className="legend-items">
          <div className="legend-row">
            <span className="status-dot dot-red" />
            <span className="legend-label">Critical/Active Evacuation</span>
          </div>
          <div className="legend-row">
            <span className="status-dot dot-amber" />
            <span className="legend-label">Warning/Pending</span>
          </div>
          <div className="legend-row">
            <span className="status-dot dot-green" />
            <span className="legend-label">Monitoring/Safe</span>
          </div>
        </div>
      </div>

      {/* Active Pin Tooltip Popup */}
      {activeTooltip && (
        <div
          className="active-pin-tooltip"
          role="dialog"
          aria-label={`${activeTooltip.name} details`}
        >
          <button
            className="tooltip-close"
            onClick={() => setActiveTooltip(null)}
            aria-label="Close"
          >
            ×
          </button>
          <div className="tooltip-title">{activeTooltip.name}</div>
          <div className="tooltip-body">
            <span className={`status-tag status-${activeTooltip.status}`}>
              {activeTooltip.status.toUpperCase()}
            </span>
            {activeTooltip.leadTime && <span>Lead time: {activeTooltip.leadTime}</span>}
            {activeTooltip.population && <span>Pop: {activeTooltip.population}</span>}
          </div>
        </div>
      )}
    </div>
  );
}
