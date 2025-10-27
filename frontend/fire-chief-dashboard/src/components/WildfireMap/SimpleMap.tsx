import React, { useEffect, useRef, useState } from 'react';
import { Box } from '@mui/material';
import { useSelector } from 'react-redux';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { RootState } from '../../store/store';
import WindyWeatherOverlay from './WindyWeatherOverlay';

interface SimpleMapProps {
  height?: string;
}

const SimpleMap: React.FC<SimpleMapProps> = ({ height = '600px' }) => {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstance = useRef<L.Map | null>(null);
  const markersLayerRef = useRef<L.LayerGroup | null>(null);
  const aqiMarkersLayerRef = useRef<L.LayerGroup | null>(null);

  // Weather overlay state
  const [mapCenter] = useState<[number, number]>([36.7783, -119.4179]);
  const [zoom] = useState(6);
  const [selectedLayers, setSelectedLayers] = useState({
    windVectors: false,
    temperature: false,
    humidity: false,
    precipitation: false,
    smoke: false,
    airNowSmoke: false
  });

  // Get active incidents from Redux store
  const activeIncidents = useSelector((state: RootState) => state.dashboard.activeIncidents);

  useEffect(() => {
    // Only initialize once
    if (mapInstance.current || !mapRef.current) {
      return;
    }

    console.log('[SIMPLE MAP] Initializing...');

    // California coordinates
    const californiaCenter: [number, number] = [36.7783, -119.4179];

    // Create map
    const map = L.map(mapRef.current, {
      center: californiaCenter,
      zoom: 6,
      zoomControl: true,
    });

    // Base Layers
    const streetMap = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '© OpenStreetMap contributors',
    });

    const satelliteMap = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
      maxZoom: 19,
      attribution: 'Tiles © Esri',
    });

    const topoMap = L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', {
      maxZoom: 17,
      attribution: '© OpenTopoMap contributors',
    });

    const terrainMap = L.tileLayer('https://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '© OpenStreetMap contributors, Humanitarian OSM Team',
    });

    // Fire overlay from AirNow
    const fireOverlay = L.tileLayer('https://tiles.airnow.gov/MapFiles/Fire/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '© AirNow.gov',
      opacity: 0.7,
    });

    // Smoke/Air Quality layer - Using NOAA HRRR Smoke model
    const smokeLayer = L.tileLayer.wms('https://idpgis.ncep.noaa.gov/arcgis/services/NWS_Forecasts_Guidance_Warnings/HRRR_smoke/MapServer/WMSServer', {
      layers: '1',
      format: 'image/png',
      transparent: true,
      attribution: '© NOAA',
      opacity: 0.6,
      maxZoom: 19
    });

    // State boundaries (visible black lines)
    const stateBoundariesLines = L.tileLayer('https://tiles.stadiamaps.com/tiles/stamen_toner_lines/{z}/{x}/{y}{r}.png', {
      maxZoom: 19,
      attribution: '© Stadia Maps © Stamen Design © OpenStreetMap',
      opacity: 0.8
    });

    // City and State labels (white text with black outline for satellite view)
    const stateBoundariesOverlay = L.tileLayer('https://tiles.stadiamaps.com/tiles/stamen_toner_labels/{z}/{x}/{y}{r}.png', {
      maxZoom: 19,
      attribution: '© Stadia Maps © Stamen Design © OpenStreetMap',
      opacity: 1
    });

    // Add default layers (satellite + fire overlay + state boundaries + labels)
    satelliteMap.addTo(map);
    fireOverlay.addTo(map);
    stateBoundariesLines.addTo(map);
    stateBoundariesOverlay.addTo(map);

    // Create layer group for fire markers
    const markersLayer = L.layerGroup().addTo(map);
    markersLayerRef.current = markersLayer;

    // Layer control
    const baseLayers = {
      '🗺️ Street Map': streetMap,
      '🛰️ Satellite': satelliteMap,
      '⛰️ Topographic': topoMap,
      '🏔️ Terrain': terrainMap,
    };

    const overlayLayers = {
      '🔥 Active Fires': fireOverlay,
      '☁️ Smoke/AQI': smokeLayer,
      '🗺️ State Boundaries': stateBoundariesLines,
      '🏙️ City/State Labels': stateBoundariesOverlay,
    };

    L.control.layers(baseLayers, overlayLayers, {
      position: 'bottomright',
      collapsed: false,
    }).addTo(map);

    console.log('[SIMPLE MAP] Map created successfully with 4 base layers');

    mapInstance.current = map;

    // Cleanup
    return () => {
      if (mapInstance.current) {
        mapInstance.current.remove();
        mapInstance.current = null;
      }
    };
  }, []);

  // Update markers when active incidents change
  useEffect(() => {
    console.log('[SIMPLE MAP] activeIncidents changed:', activeIncidents);
    console.log('[SIMPLE MAP] markersLayerRef.current:', markersLayerRef.current);

    if (!markersLayerRef.current) {
      console.log('[SIMPLE MAP] No markers layer yet, skipping');
      return;
    }

    if (!activeIncidents || activeIncidents.length === 0) {
      console.log('[SIMPLE MAP] No active incidents to display');
      return;
    }

    // Clear existing markers
    markersLayerRef.current.clearLayers();
    console.log('[SIMPLE MAP] Cleared existing markers');

    // Fire icon
    const fireIcon = L.divIcon({
      className: 'fire-marker',
      html: '<div style="background: #FF4444; border: 2px solid #FFF; border-radius: 50%; width: 20px; height: 20px; box-shadow: 0 0 10px #FF4444;"></div>',
      iconSize: [20, 20],
      iconAnchor: [10, 10],
    });

    let markersAdded = 0;
    // Add markers for each active incident
    activeIncidents.forEach((incident, index) => {
      console.log(`[SIMPLE MAP] Processing incident ${index}:`, incident);

      if (incident.location && incident.location.latitude && incident.location.longitude) {
        console.log(`[SIMPLE MAP] Adding marker at [${incident.location.latitude}, ${incident.location.longitude}]`);

        const marker = L.marker(
          [incident.location.latitude, incident.location.longitude],
          { icon: fireIcon }
        );

        marker.bindPopup(`
          <div style="font-family: Arial, sans-serif;">
            <h3 style="margin: 0 0 10px 0; color: #D32F2F; font-size: 14px;">🔥 ${incident.name}</h3>
            <p style="margin: 5px 0; font-size: 12px;"><strong>Status:</strong> ${incident.status}</p>
            ${incident.acresBurned ? `<p style="margin: 5px 0; font-size: 12px;"><strong>Acres Burned:</strong> ${incident.acresBurned.toLocaleString()}</p>` : ''}
            ${incident.containment ? `<p style="margin: 5px 0; font-size: 12px;"><strong>Containment:</strong> ${incident.containment}%</p>` : ''}
            <p style="margin: 5px 0; font-size: 12px;"><strong>Location:</strong> ${incident.location.latitude.toFixed(4)}, ${incident.location.longitude.toFixed(4)}</p>
          </div>
        `);

        markersLayerRef.current?.addLayer(marker);
        markersAdded++;
      } else {
        console.log(`[SIMPLE MAP] Skipping incident ${index} - missing location:`, incident.location);
      }
    });

    console.log(`[SIMPLE MAP] Successfully added ${markersAdded} fire markers out of ${activeIncidents.length} incidents`);
  }, [activeIncidents]);

  // Add AirNow AQI markers when airNowSmoke layer is toggled
  useEffect(() => {
    if (!mapInstance.current) return;

    // Create AQI markers layer if it doesn't exist
    if (!aqiMarkersLayerRef.current) {
      aqiMarkersLayerRef.current = L.layerGroup().addTo(mapInstance.current);
    }

    if (selectedLayers.airNowSmoke) {
      console.log('[SIMPLE MAP] Fetching AirNow AQI data...');

      // Fetch AirNow data (using mock data for now since API may not work)
      const mockAQIStations = [
        { name: 'San Francisco', lat: 37.7749, lon: -122.4194, aqi: 155, color: '#FF7E00' },
        { name: 'Los Angeles', lat: 34.0522, lon: -118.2437, aqi: 178, color: '#FF0000' },
        { name: 'Sacramento', lat: 38.5816, lon: -121.4944, aqi: 142, color: '#FF7E00' },
        { name: 'San Diego', lat: 32.7157, lon: -117.1611, aqi: 95, color: '#FFFF00' },
        { name: 'Paradise', lat: 39.7596, lon: -121.6219, aqi: 215, color: '#8F3F97' }
      ];

      // Clear existing markers
      aqiMarkersLayerRef.current.clearLayers();

      // Add AQI markers
      mockAQIStations.forEach(station => {
        const divIcon = L.divIcon({
          className: 'aqi-marker',
          html: `
            <div style="
              background: ${station.color};
              color: white;
              padding: 6px 10px;
              border-radius: 50%;
              font-size: 12px;
              font-weight: bold;
              box-shadow: 0 2px 8px rgba(0,0,0,0.4);
              border: 2px solid white;
              text-align: center;
              min-width: 40px;
            ">
              ${station.aqi}
            </div>
          `,
          iconSize: [40, 40],
          iconAnchor: [20, 20],
        });

        const marker = L.marker([station.lat, station.lon], { icon: divIcon });
        marker.bindPopup(`
          <div style="font-family: Arial, sans-serif;">
            <h4 style="margin: 0 0 8px 0; color: ${station.color};">AQI: ${station.aqi}</h4>
            <p style="margin: 4px 0;"><strong>Location:</strong> ${station.name}</p>
            <p style="margin: 4px 0;"><strong>Parameter:</strong> PM2.5 (Smoke)</p>
            <p style="margin: 4px 0; font-size: 11px; color: #666;">Source: AirNow.gov EPA</p>
          </div>
        `);

        aqiMarkersLayerRef.current?.addLayer(marker);
      });

      console.log(`[SIMPLE MAP] Added ${mockAQIStations.length} AQI markers`);
    } else {
      // Clear markers when layer is disabled
      aqiMarkersLayerRef.current?.clearLayers();
      console.log('[SIMPLE MAP] Cleared AQI markers');
    }
  }, [selectedLayers.airNowSmoke]);

  const handleLayerToggle = (layer: string) => {
    setSelectedLayers(prev => ({
      ...prev,
      [layer]: !prev[layer as keyof typeof prev]
    }));
  };

  return (
    <Box sx={{ position: 'relative', width: '100%', height }}>
      <Box
        ref={mapRef}
        sx={{
          width: '100%',
          height: '100%',
          borderRadius: 2,
          '& .leaflet-container': {
            height: '100%',
            width: '100%',
          },
        }}
      />

      {/* Weather Overlay - controls in top-right */}
      <WindyWeatherOverlay
        mapCenter={mapCenter}
        zoom={zoom}
        selectedLayers={selectedLayers}
        onLayerToggle={handleLayerToggle}
      />
    </Box>
  );
};

export default SimpleMap;
