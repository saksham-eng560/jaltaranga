import React, { useEffect, useRef } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { COLONIES, REPLAY_STEPS, riskForColony } from '../shared/mockData';

interface MapViewProps {
  onSelectColony?: (colonyId: string) => void;
  selectedColonyId?: string;
  stageLevel?: number;
}

export const MapView: React.FC<MapViewProps> = ({ onSelectColony, selectedColonyId, stageLevel }) => {
  const mapContainer = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const markersRef = useRef(new Map<string, maplibregl.Marker>());

  useEffect(() => {
    if (!mapContainer.current || mapRef.current) return undefined;

    const map = new maplibregl.Map({
      container: mapContainer.current,
      style: {
        version: 8,
        sources: {
          osm: {
            type: 'raster',
            tiles: [
              'https://tile.openstreetmap.de/{z}/{x}/{y}.png',
            ],
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
              'raster-saturation': -1,
              'raster-contrast': 0.12,
              'raster-opacity': 0.82,
            },
          },
        ],
      },
      center: [77.245, 28.655],
      zoom: 12.5,
      attributionControl: false,
    });

    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right');
    map.addControl(new maplibregl.AttributionControl({ compact: true }), 'bottom-right');

    map.on('load', () => {
      map.addSource('yamuna-channel', {
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

      map.addLayer({
        id: 'yamuna-halo',
        type: 'line',
        source: 'yamuna-channel',
        paint: {
          'line-color': '#ffffff',
          'line-width': 13,
          'line-opacity': 0.85,
        },
      });
      map.addLayer({
        id: 'yamuna-line',
        type: 'line',
        source: 'yamuna-channel',
        paint: {
          'line-color': '#171717',
          'line-width': 5,
          'line-opacity': 0.78,
        },
      });

      for (const colony of COLONIES) {
        const risk = riskForColony(stageLevel ?? REPLAY_STEPS[2].level, colony.wetLevelM);
        const marker = document.createElement('button');
        marker.type = 'button';
        marker.className = `map-marker risk-${risk}${colony.id === selectedColonyId ? ' is-selected' : ''}`;
        marker.setAttribute('aria-label', colony.name);
        marker.title = colony.name;
        marker.innerHTML = '<span></span>';
        marker.addEventListener('click', () => onSelectColony?.(colony.id));
        const mapMarker = new maplibregl.Marker({ element: marker, anchor: 'center' })
          .setLngLat(colony.coordinates)
          .addTo(map);
        markersRef.current.set(colony.id, mapMarker);
      }

      map.resize();
    });

    mapRef.current = map;
    return () => {
      markersRef.current.clear();
      map.remove();
      mapRef.current = null;
    };
  }, [onSelectColony]);

  useEffect(() => {
    const level = stageLevel ?? REPLAY_STEPS[2].level;
    markersRef.current.forEach((marker, colonyId) => {
      const colony = COLONIES.find((item) => item.id === colonyId);
      if (!colony) return;
      const element = marker.getElement();
      element.classList.remove('risk-critical', 'risk-watch', 'risk-safe');
      element.classList.add(`risk-${riskForColony(level, colony.wetLevelM)}`);
    });
  }, [stageLevel]);

  useEffect(() => {
    const selected = COLONIES.find((colony) => colony.id === selectedColonyId);
    markersRef.current.forEach((marker, colonyId) => {
      marker.getElement().classList.toggle('is-selected', colonyId === selectedColonyId);
    });
    if (selected && mapRef.current) {
      mapRef.current.easeTo({ center: selected.coordinates, duration: 550 });
    }
  }, [selectedColonyId]);

  return <div ref={mapContainer} className="maplibre-canvas" style={{ width: '100%', height: '100%' }} />;
};
