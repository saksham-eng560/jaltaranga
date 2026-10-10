import React, { useEffect, useRef } from 'react';
import maplibregl from 'maplibre-gl';

interface MapViewProps {
  onSelectColony?: (colonyId: string) => void;
  selectedColonyId?: string;
  floodGeoJsonUrl?: string;
}

export const MapView: React.FC<MapViewProps> = ({
  onSelectColony,
  selectedColonyId,
  floodGeoJsonUrl,
}) => {
  const mapContainer = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);

  useEffect(() => {
    if (!mapContainer.current || mapRef.current) return;

    const map = new maplibregl.Map({
      container: mapContainer.current,
      style: {
        version: 8,
        sources: {
          osm: {
            type: 'raster',
            tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
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
          },
        ],
      },
      center: [77.245, 28.655], // Yamuna Corridor, Delhi
      zoom: 12.5,
    });

    map.addControl(new maplibregl.NavigationControl(), 'top-right');

    map.on('load', () => {
      // Add Yamuna River Line / Channel
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
        id: 'yamuna-line',
        type: 'line',
        source: 'yamuna-channel',
        paint: {
          'line-color': '#0284c7',
          'line-width': 8,
          'line-opacity': 0.8,
        },
      });

      // Add Sample Colony Markers
      const colonies = [
        { id: 'DEL-YP-04', name: 'Yamuna Pushta Sector C', coords: [77.245, 28.655], status: 'red' },
        { id: 'DEL-MKT-01', name: 'Majnu ka Tilla', coords: [77.23, 28.7], status: 'amber' },
        { id: 'DEL-MV-02', name: 'Mayur Vihar Ext Phase 1', coords: [77.295, 28.605], status: 'amber' },
        { id: 'DEL-CP-01', name: 'Connaught Place', coords: [77.218, 28.632], status: 'green' },
      ];

      colonies.forEach((col) => {
        const el = document.createElement('div');
        el.style.width = '24px';
        el.style.height = '24px';
        el.style.borderRadius = '50%';
        el.style.backgroundColor =
          col.status === 'red' ? '#ef4444' : col.status === 'amber' ? '#f59e0b' : '#10b981';
        el.style.border = '2px solid white';
        el.style.cursor = 'pointer';
        el.title = col.name;

        el.addEventListener('click', () => {
          if (onSelectColony) onSelectColony(col.id);
        });

        new maplibregl.Marker({ element: el })
          .setLngLat(col.coords as [number, number])
          .addTo(map);
      });
    });

    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  return <div ref={mapContainer} style={{ width: '100%', height: '100%' }} />;
};
