import React, { useEffect, useRef, useState, useCallback } from 'react';
import { Box, Typography, Card, Switch, FormControlLabel, Alert, CircularProgress, Collapse, IconButton, Select, MenuItem, FormControl, InputLabel, Divider } from '@mui/material';
import {
  Air,
  Thermostat,
  Opacity,
  Cloud,
  LocalFireDepartment,
  Visibility,
  Speed,
  ExpandMore,
  ExpandLess,
  Close
} from '@mui/icons-material';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

interface ProfessionalWeatherMapProps {
  mapCenter?: [number, number];
  activeFires: any[];
  selectedLayers: {
    activeFires: boolean;
    firePerimeters: boolean;
    windVectors: boolean;
    temperature: boolean;
    humidity: boolean;
    vegetation: boolean;
    population: boolean;
    infrastructure: boolean;
    predictions: boolean;
    iotSensors: boolean;
    precipitation: boolean;
    hazardZones: boolean;
    helicopterLanding: boolean;
    waterSources: boolean;
    emergencyServices: boolean;
    communicationTowers: boolean;
    wildlandUrbanInterface: boolean;
    evacuationRoutes: boolean;
    fuelAnalysis: boolean;
    weatherStations: boolean;
  };
  onLayerToggle: (layer: keyof ProfessionalWeatherMapProps['selectedLayers']) => void;
  criticalInfrastructure?: any[];
  fireHazardZones?: any[];
  wildlandUrbanInterface?: any[];
  evacuationRoutes?: any[];
  weatherStations?: any[];
}

interface WeatherData {
  current: {
    temperature_2m: number;
    wind_speed_10m: number;
    wind_direction_10m: number;
    relative_humidity_2m: number;
    precipitation: number;
    visibility: number;
  };
}

// Leaflet is now imported directly, no need for L

const ProfessionalWeatherMap: React.FC<ProfessionalWeatherMapProps> = ({
  mapCenter = [37.7749, -122.4194], // Default to San Francisco
  activeFires,
  selectedLayers,
  onLayerToggle,
  criticalInfrastructure = [],
  fireHazardZones = [],
  wildlandUrbanInterface = [],
  evacuationRoutes = [],
  weatherStations = []
}) => {
  console.log('[MAP] ProfessionalWeatherMap loaded');
  console.log('[MAP] mapCenter prop received:', mapCenter);
  console.log('[MAP] mapCenter type:', typeof mapCenter, 'isArray:', Array.isArray(mapCenter));
  const mapRef = useRef<HTMLDivElement>(null);
  const leafletMapRef = useRef<any>(null);
  const [mapLoaded, setMapLoaded] = useState(false);
  const [weatherData, setWeatherData] = useState<WeatherData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [controlsExpanded, setControlsExpanded] = useState(false);
  const [alertDismissed, setAlertDismissed] = useState(false);
  const [fireMarkersLayer, setFireMarkersLayer] = useState<any>(null);
  const [windOverlayLayer, setWindOverlayLayer] = useState<any>(null);
  const [temperatureOverlayLayer, setTemperatureOverlayLayer] = useState<any>(null);
  const [humidityOverlayLayer, setHumidityOverlayLayer] = useState<any>(null);
  const [infrastructureLayer, setInfrastructureLayer] = useState<any>(null);
  const [hazardZonesLayer, setHazardZonesLayer] = useState<any>(null);
  const [weatherStationsLayer, setWeatherStationsLayer] = useState<any>(null);
  const [wuiLayer, setWuiLayer] = useState<any>(null);
  const [evacuationRoutesLayer, setEvacuationRoutesLayer] = useState<any>(null);
  const [showWindyWidget, setShowWindyWidget] = useState(false);
  const [windyOverlay, setWindyOverlay] = useState('wind');
  const [windyProduct, setWindyProduct] = useState('ecmwf');
  const [windyLevel, setWindyLevel] = useState('surface');

  // Leaflet is now bundled locally, set mapLoaded immediately
  useEffect(() => {
    console.log('[MAP] Leaflet loaded from npm package');
    setMapLoaded(true);
    setLoading(false);
  }, []);

  // Add fire markers to map
  const addFireMarkers = useCallback((map: any) => {
    if (!L || !activeFires.length) {
      console.log('No fires to display or Leaflet not loaded');
      return;
    }

    console.log(`Adding ${activeFires.length} fire markers to map`);

    // Remove existing fire markers if any
    if (fireMarkersLayer) {
      map.removeLayer(fireMarkersLayer);
    }

    // Create new layer group for fire markers
    const markersGroup = L.layerGroup();

    activeFires.forEach((fire) => {
      // Create custom fire icon
      const fireIcon = L.divIcon({
        className: 'fire-marker-icon',
        html: `
          <div style="
            width: ${Math.max(16, (fire.frp || 20) / 3)}px;
            height: ${Math.max(16, (fire.frp || 20) / 3)}px;
            background: radial-gradient(circle, #FF4500 0%, #FF0000 70%, #8B0000 100%);
            border-radius: 50%;
            border: 2px solid white;
            box-shadow: 0 0 15px rgba(255, 69, 0, 0.8);
            animation: firePulse 2s ease-in-out infinite;
            position: relative;
          ">
            <div style="
              position: absolute;
              top: -20px;
              left: 50%;
              transform: translateX(-50%);
              background: rgba(0, 0, 0, 0.8);
              color: white;
              padding: 2px 6px;
              border-radius: 4px;
              font-size: 10px;
              white-space: nowrap;
              pointer-events: none;
            ">
              ${Math.round(fire.frp || 0)}MW
            </div>
          </div>
        `,
        iconSize: [Math.max(16, (fire.frp || 20) / 3), Math.max(16, (fire.frp || 20) / 3)],
        iconAnchor: [Math.max(8, (fire.frp || 20) / 6), Math.max(8, (fire.frp || 20) / 6)]
      });

      // Add marker to group
      const marker = L.marker([fire.latitude, fire.longitude], { icon: fireIcon })
        .bindPopup(`
          <div style="min-width: 250px; font-family: Arial, sans-serif;">
            <h3 style="margin: 0 0 10px 0; color: #FF4500; display: flex; align-items: center;">
              [FIRE] Active Fire Detection
            </h3>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 10px;">
              <div><strong>Location:</strong><br>${(fire.latitude || 0).toFixed(4)}, ${(fire.longitude || 0).toFixed(4)}</div>
              <div><strong>Fire Power:</strong><br>${fire.frp}MW</div>
              <div><strong>Confidence:</strong><br>${fire.confidence}%</div>
              <div><strong>Satellite:</strong><br>${fire.satellite || 'MODIS'}</div>
            </div>
            <div><strong>Detection Time:</strong><br>${new Date(fire.acquisitionTime || Date.now()).toLocaleString()}</div>
            <div style="background: rgba(255, 69, 0, 0.1); padding: 10px; border-radius: 6px; margin-top: 10px; border-left: 4px solid #FF4500;">
              <strong style="color: #FF4500;">[WARNING] Critical Fire Weather Conditions</strong><br>
              <small>Monitor wind patterns and humidity levels for rapid fire spread potential.</small>
            </div>
          </div>
        `);

      // Add marker to group
      markersGroup.addLayer(marker);
    });

    // Add the layer group to map and store reference
    markersGroup.addTo(map);
    setFireMarkersLayer(markersGroup);

    // Add CSS for fire animation
    if (!document.querySelector('#fire-marker-styles')) {
      const style = document.createElement('style');
      style.id = 'fire-marker-styles';
      style.textContent = `
        @keyframes firePulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.8; transform: scale(1.2); }
        }
        .fire-marker-icon {
          background: none !important;
          border: none !important;
        }
        .leaflet-popup-content-wrapper {
          border-radius: 8px;
        }
        .leaflet-popup-tip {
          background: white;
        }
      `;
      document.head.appendChild(style);
    }
  }, [activeFires, fireMarkersLayer]);

  // Add Fire Hazard Severity Zones to map
  const addFireHazardZones = useCallback((map: any) => {
    if (!L) return;

    console.log('[FIRE] Adding Fire Hazard Zones to map');

    // Remove existing zones if any
    if (hazardZonesLayer) {
      map.removeLayer(hazardZonesLayer);
    }

    const zonesGroup = L.layerGroup();

    // Mock fire hazard zones for California + TEST ZONE
    const mockHazardZones = [
      { name: '🚨 TEST ZONE - BRIGHT RED', bounds: [[34.0522, -118.2437], [34.1522, -118.1437]], severity: 'Very High' },
      { name: 'Angeles National Forest - Very High', bounds: [[34.15, -118.5], [34.35, -118.1]], severity: 'Very High' },
      { name: 'Sylmar Hills - High', bounds: [[34.25, -118.45], [34.32, -118.35]], severity: 'High' },
      { name: 'Porter Ranch - Moderate', bounds: [[34.26, -118.58], [34.28, -118.53]], severity: 'Moderate' },
      { name: 'Malibu Hills - Very High', bounds: [[34.02, -118.78], [34.08, -118.65]], severity: 'Very High' },
      { name: 'Santa Monica Mountains - High', bounds: [[34.05, -118.65], [34.12, -118.55]], severity: 'High' }
    ];

    mockHazardZones.forEach((zone) => {
      const severityColors = {
        'Very High': '#8B0000',
        'High': '#FF4500',
        'Moderate': '#FFA500',
        'Low': '#FFD700'
      };

      // Make test zone super visible
      const isTestZone = zone.name.includes('TEST ZONE');

      const polygon = L.rectangle(zone.bounds as [[number, number], [number, number]], {
        color: isTestZone ? '#FF0000' : severityColors[zone.severity as keyof typeof severityColors],
        fillColor: isTestZone ? '#FF0000' : severityColors[zone.severity as keyof typeof severityColors],
        fillOpacity: isTestZone ? 0.8 : 0.3,
        weight: isTestZone ? 5 : 2
      }).bindPopup(`
        <div style="font-family: Arial, sans-serif; min-width: 200px;">
          <h3 style="margin: 0 0 8px 0; color: ${severityColors[zone.severity as keyof typeof severityColors]};">
            [FIRE] Fire Hazard Zone
          </h3>
          <div><strong>Zone:</strong> ${zone.name}</div>
          <div><strong>Severity:</strong> <span style="color: ${severityColors[zone.severity as keyof typeof severityColors]};">${zone.severity}</span></div>
          <div style="background: rgba(255, 69, 0, 0.1); padding: 8px; border-radius: 4px; margin-top: 8px;">
            <strong style="color: #FF4500;">[WARNING] Fire Risk Assessment</strong><br>
            <small>Based on vegetation type, topography, and weather patterns.</small>
          </div>
        </div>
      `);

      zonesGroup.addLayer(polygon);
    });

    zonesGroup.addTo(map);
    setHazardZonesLayer(zonesGroup);

    console.log('[CHECK] Fire Hazard Zones layer added to map with', mockHazardZones.length, 'zones');
  }, [fireHazardZones, hazardZonesLayer]);

  // Add infrastructure markers to map
  const addInfrastructureMarkers = useCallback((map: any) => {
    if (!L || !criticalInfrastructure.length) {
      console.log('No infrastructure to display or Leaflet not loaded');
      return;
    }

    console.log(`Adding ${criticalInfrastructure.length} infrastructure markers to map`);

    // Remove existing infrastructure markers if any
    if (infrastructureLayer) {
      map.removeLayer(infrastructureLayer);
    }

    // Create new layer group for infrastructure markers
    const markersGroup = L.layerGroup();

    criticalInfrastructure.forEach((infra) => {
      let iconHtml = '';
      let color = '#2196F3';
      let bgColor = 'rgba(33, 150, 243, 0.2)';

      switch (infra.type) {
        case 'helicopter_landing':
          iconHtml = '[HELICOPTER]';
          color = '#FF9800';
          bgColor = 'rgba(255, 152, 0, 0.2)';
          break;
        case 'water_source':
          iconHtml = '[DROPLET]';
          color = '#2196F3';
          bgColor = 'rgba(33, 150, 243, 0.2)';
          break;
        case 'emergency_service':
          iconHtml = '🚑';
          color = '#F44336';
          bgColor = 'rgba(244, 67, 54, 0.2)';
          break;
        case 'communication_tower':
          iconHtml = '[SATELLITE_ANTENNA]';
          color = '#9C27B0';
          bgColor = 'rgba(156, 39, 176, 0.2)';
          break;
        case 'fuel_analysis':
          iconHtml = '[HERB]';
          color = '#4CAF50';
          bgColor = 'rgba(76, 175, 80, 0.2)';
          break;
        case 'hospital':
          iconHtml = '🏥';
          color = '#F44336';
          bgColor = 'rgba(244, 67, 54, 0.2)';
          break;
        case 'powerline':
          iconHtml = '[LIGHTNING]';
          color = '#FF5722';
          bgColor = 'rgba(255, 87, 34, 0.2)';
          break;
        default:
          iconHtml = '[OFFICE_BUILDING]';
          color = '#607D8B';
          bgColor = 'rgba(96, 125, 139, 0.2)';
      }

      const infraIcon = L.divIcon({
        className: 'infrastructure-marker-icon',
        html: `
          <div style="
            width: 32px;
            height: 32px;
            background: ${color};
            border-radius: 50%;
            border: 2px solid white;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 16px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.3);
            position: relative;
          ">
            ${iconHtml}
            <div style="
              position: absolute;
              top: -25px;
              left: 50%;
              transform: translateX(-50%);
              background: rgba(0, 0, 0, 0.8);
              color: white;
              padding: 2px 6px;
              border-radius: 4px;
              font-size: 10px;
              white-space: nowrap;
              pointer-events: none;
              ${infra.status === 'Threatened' ? 'background: rgba(255, 152, 0, 0.9);' : ''}
            ">
              ${infra.name}
            </div>
          </div>
        `,
        iconSize: [32, 32],
        iconAnchor: [16, 16]
      });

      const marker = L.marker([infra.latitude, infra.longitude], { icon: infraIcon })
        .bindPopup(`
          <div style="min-width: 200px; font-family: Arial, sans-serif;">
            <h3 style="margin: 0 0 8px 0; color: ${color}; display: flex; align-items: center;">
              ${iconHtml} ${infra.name}
            </h3>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 6px; margin-bottom: 8px;">
              <div><strong>Type:</strong><br>${infra.type.replace('_', ' ')}</div>
              <div><strong>Priority:</strong><br>${infra.priority}</div>
              <div><strong>Status:</strong><br>
                <span style="color: ${infra.status === 'Operational' ? '#4CAF50' : '#FF9800'};">
                  ${infra.status}
                </span>
              </div>
              ${infra.capacity ? `<div><strong>Capacity:</strong><br>${infra.capacity}</div>` : ''}
            </div>
            ${infra.accessibility ? `<div><strong>Accessibility:</strong> ${infra.accessibility}</div>` : ''}
            <div style="background: ${infra.status === 'Threatened' ? 'rgba(255, 152, 0, 0.1)' : 'rgba(76, 175, 80, 0.1)'};
                        padding: 8px; border-radius: 4px; margin-top: 8px;
                        border-left: 4px solid ${infra.status === 'Threatened' ? '#FF9800' : '#4CAF50'};">
              <strong style="color: ${infra.status === 'Threatened' ? '#FF9800' : '#4CAF50'};">
                ${infra.status === 'Threatened' ? '[WARNING] Infrastructure at Risk' : '[CHECK] Operational Status'}
              </strong><br>
              <small>${infra.status === 'Threatened' ? 'Monitor for potential impact from wildfire.' : 'Available for emergency operations.'}</small>
            </div>
          </div>
        `);

      markersGroup.addLayer(marker);
    });

    // Add the layer group to map and store reference
    markersGroup.addTo(map);
    setInfrastructureLayer(markersGroup);

    // Add CSS for infrastructure icons
    if (!document.querySelector('#infrastructure-marker-styles')) {
      const style = document.createElement('style');
      style.id = 'infrastructure-marker-styles';
      style.textContent = `
        .infrastructure-marker-icon {
          background: none !important;
          border: none !important;
        }
      `;
      document.head.appendChild(style);
    }
  }, [criticalInfrastructure, infrastructureLayer]);

  // Add weather station markers to map
  const addWeatherStationMarkers = useCallback((map: any) => {
    if (!L || !weatherStations.length) return;

    // Remove existing weather station markers if any
    if (weatherStationsLayer) {
      map.removeLayer(weatherStationsLayer);
    }

    // Create new layer group for weather station markers
    const markersGroup = L.layerGroup();

    weatherStations.forEach((station) => {
      const stationIcon = L.divIcon({
        className: 'weather-station-marker-icon',
        html: `
          <div style="
            width: 28px;
            height: 28px;
            background: ${station.type === 'RAWS' ? '#FF9800' : '#2196F3'};
            border-radius: 50%;
            border: 2px solid white;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 14px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.3);
            position: relative;
          ">
            [THERMOMETER]
            <div style="
              position: absolute;
              top: -22px;
              left: 50%;
              transform: translateX(-50%);
              background: rgba(0, 0, 0, 0.8);
              color: white;
              padding: 1px 4px;
              border-radius: 3px;
              font-size: 9px;
              white-space: nowrap;
              pointer-events: none;
            ">
              ${station.name}
            </div>
          </div>
        `,
        iconSize: [28, 28],
        iconAnchor: [14, 14]
      });

      const marker = L.marker([station.latitude, station.longitude], { icon: stationIcon })
        .bindPopup(`
          <div style="min-width: 220px; font-family: Arial, sans-serif;">
            <h3 style="margin: 0 0 8px 0; color: #FF9800; display: flex; align-items: center;">
              [THERMOMETER] ${station.name}
            </h3>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 6px; margin-bottom: 8px;">
              <div><strong>Type:</strong><br>${station.type}</div>
              <div><strong>Status:</strong><br>
                <span style="color: ${station.status === 'Active' ? '#4CAF50' : '#FF5722'};">
                  ${station.status}
                </span>
              </div>
              <div><strong>Temperature:</strong><br>${station.temperature}degF</div>
              <div><strong>Humidity:</strong><br>${station.humidity}%</div>
              <div><strong>Wind Speed:</strong><br>${station.windSpeed}mph</div>
              <div><strong>Wind Direction:</strong><br>${station.windDirection}deg</div>
            </div>
            <div><strong>Last Update:</strong><br>${new Date(station.lastUpdate).toLocaleString()}</div>
            <div style="background: rgba(255, 152, 0, 0.1); padding: 8px; border-radius: 4px; margin-top: 8px;
                        border-left: 4px solid #FF9800;">
              <strong style="color: #FF9800;">[THERMOMETER] Live Weather Data</strong><br>
              <small>Real-time conditions for fire weather analysis.</small>
            </div>
          </div>
        `);

      markersGroup.addLayer(marker);
    });

    // Add the layer group to map and store reference
    markersGroup.addTo(map);
    setWeatherStationsLayer(markersGroup);
  }, [weatherStations, weatherStationsLayer]);

  // Add Wildland Urban Interface zones
  const addWildlandUrbanInterface = useCallback((map: any) => {
    if (!L) return;

    console.log('[HOUSE] Adding Wildland Urban Interface zones to map');

    // Remove existing WUI layer if any
    if (wuiLayer) {
      map.removeLayer(wuiLayer);
    }

    const wuiGroup = L.layerGroup();

    // Mock WUI zones for demonstration
    const mockWUIZones = [
      { name: 'Sylmar WUI Zone', bounds: [[34.28, -118.46], [34.32, -118.42]], riskLevel: 'High' },
      { name: 'Porter Ranch WUI Zone', bounds: [[34.26, -118.58], [34.29, -118.54]], riskLevel: 'Moderate' },
      { name: 'Malibu WUI Zone', bounds: [[34.02, -118.78], [34.06, -118.72]], riskLevel: 'Extreme' },
      { name: 'Altadena WUI Zone', bounds: [[34.18, -118.15], [34.20, -118.12]], riskLevel: 'High' }
    ];

    mockWUIZones.forEach((zone) => {
      const riskColors = {
        'Extreme': '#8B0000',
        'High': '#FF4500',
        'Moderate': '#FFA500',
        'Low': '#32CD32'
      };

      const polygon = L.rectangle(zone.bounds as [[number, number], [number, number]], {
        color: riskColors[zone.riskLevel as keyof typeof riskColors],
        fillColor: riskColors[zone.riskLevel as keyof typeof riskColors],
        fillOpacity: 0.2,
        weight: 2,
        dashArray: '5, 5' // Dashed border to distinguish from hazard zones
      }).bindPopup(`
        <div style="font-family: Arial, sans-serif; min-width: 200px;">
          <h3 style="margin: 0 0 8px 0; color: ${riskColors[zone.riskLevel as keyof typeof riskColors]};">
            [HOUSE] Wildland Urban Interface
          </h3>
          <div><strong>Zone:</strong> ${zone.name}</div>
          <div><strong>Risk Level:</strong> <span style="color: ${riskColors[zone.riskLevel as keyof typeof riskColors]};">${zone.riskLevel}</span></div>
          <div style="background: rgba(156, 39, 176, 0.1); padding: 8px; border-radius: 4px; margin-top: 8px;">
            <strong style="color: #9C27B0;">🏘️ Urban-Wildland Interface</strong><br>
            <small>Areas where homes and wildland vegetation meet, creating unique fire risks.</small>
          </div>
        </div>
      `);

      wuiGroup.addLayer(polygon);
    });

    wuiGroup.addTo(map);
    setWuiLayer(wuiGroup);
  }, [wuiLayer]);

  // Add Evacuation Routes
  const addEvacuationRoutes = useCallback((map: any) => {
    if (!L) return;

    console.log('🛣️ Adding Evacuation Routes to map');

    // Remove existing routes layer if any
    if (evacuationRoutesLayer) {
      map.removeLayer(evacuationRoutesLayer);
    }

    const routesGroup = L.layerGroup();

    // Mock evacuation routes
    const mockRoutes = [
      {
        name: 'SR-14 South to I-5',
        path: [[34.32, -118.44], [34.28, -118.40], [34.25, -118.35], [34.20, -118.30]],
        status: 'Open'
      },
      {
        name: 'Foothill Boulevard West',
        path: [[34.26, -118.45], [34.26, -118.50], [34.26, -118.55]],
        status: 'Congested'
      },
      {
        name: 'I-210 East Emergency Route',
        path: [[34.22, -118.20], [34.20, -118.15], [34.18, -118.10]],
        status: 'Open'
      },
      {
        name: 'Pacific Coast Highway',
        path: [[34.03, -118.75], [34.02, -118.70], [34.01, -118.65]],
        status: 'Blocked'
      }
    ];

    mockRoutes.forEach((route) => {
      const routeColors = {
        'Open': '#32CD32',
        'Congested': '#FFA500',
        'Closed': '#FF4500',
        'Blocked': '#8B0000'
      };

      const polyline = L.polyline(route.path as [number, number][], {
        color: routeColors[route.status as keyof typeof routeColors],
        weight: 6,
        opacity: 0.8,
        dashArray: route.status === 'Blocked' ? '10, 10' : undefined
      }).bindPopup(`
        <div style="font-family: Arial, sans-serif; min-width: 200px;">
          <h3 style="margin: 0 0 8px 0; color: ${routeColors[route.status as keyof typeof routeColors]};">
            🛣️ Evacuation Route
          </h3>
          <div><strong>Route:</strong> ${route.name}</div>
          <div><strong>Status:</strong> <span style="color: ${routeColors[route.status as keyof typeof routeColors]};">${route.status}</span></div>
          <div style="background: rgba(96, 125, 139, 0.1); padding: 8px; border-radius: 4px; margin-top: 8px;">
            <strong style="color: #607D8B;">[CAR] Evacuation Status</strong><br>
            <small>Real-time status of primary evacuation corridors.</small>
          </div>
        </div>
      `);

      routesGroup.addLayer(polyline);
    });

    routesGroup.addTo(map);
    setEvacuationRoutesLayer(routesGroup);
  }, [evacuationRoutesLayer]);

  // Initialize map when Leaflet is loaded
  useEffect(() => {
    if (!mapLoaded || !mapRef.current || leafletMapRef.current) {
      console.log('[MAP] Cannot initialize:', {
        mapLoaded,
        mapRefExists: !!mapRef.current,
        alreadyInitialized: !!leafletMapRef.current
      });
      return;
    }

    console.log('[MAP] Starting map initialization...');
    console.log('[MAP] Received mapCenter prop:', mapCenter);

    // Add a small delay to ensure DOM is fully ready
    const timer = setTimeout(() => {
      try {
        if (!mapRef.current) {
          console.error('[MAP] mapRef.current is null during initialization');
          setError('Map container not ready');
          setLoading(false);
          return;
        }

        // Use default California coordinates if mapCenter is invalid
        let validMapCenter: [number, number] = [37.7749, -122.4194]; // San Francisco default

        if (mapCenter && Array.isArray(mapCenter) && mapCenter.length === 2) {
          const lat = mapCenter[0];
          const lng = mapCenter[1];

          if (typeof lat === 'number' && !isNaN(lat) && typeof lng === 'number' && !isNaN(lng)) {
            validMapCenter = [lat, lng];
            console.log('[MAP] Using provided mapCenter:', validMapCenter);
          } else {
            console.warn('[MAP] Invalid coordinates in mapCenter, using default:', validMapCenter);
          }
        } else {
          console.warn('[MAP] mapCenter prop invalid, using default California coordinates:', validMapCenter);
        }

        console.log('[MAP] Creating Leaflet map with center:', validMapCenter);

        // Create the map
        const map = L.map(mapRef.current, {
          center: validMapCenter,
          zoom: 6,
          zoomControl: true,
          attributionControl: true
        });

        console.log('[MAP] Leaflet map instance created successfully');

      // Add reliable tile sources
      const baseLayers = {
        'OpenStreetMap': L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
          maxZoom: 19,
          attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
          subdomains: ['a', 'b', 'c']
        }),
        'Satellite': L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
          maxZoom: 19,
          attribution: 'Tiles &copy; Esri'
        })
      };

      // AirNow Fire and Smoke Overlay
      const overlayLayers: any = {};

      // Add AirNow Fire/Smoke Map Layer (Current year tiles)
      const currentYear = new Date().getFullYear();
      const airNowFireLayer = L.tileLayer(`https://tiles.airnowapi.org/MapFiles/${currentYear}/Fires/{z}/{x}/{y}.png`, {
        maxZoom: 14,
        opacity: 0.75,
        attribution: '🔥 Fire/Smoke &copy; <a href="https://fire.airnow.gov">AirNow</a>'
      });
      overlayLayers['🔥 Fire & Smoke (AirNow)'] = airNowFireLayer;

      // Add AirNow Air Quality PM2.5 Layer
      const airQualityLayer = L.tileLayer(`https://tiles.airnowapi.org/MapFiles/${currentYear}/PM25/{z}/{x}/{y}.png`, {
        maxZoom: 14,
        opacity: 0.65,
        attribution: '💨 Air Quality &copy; <a href="https://airnow.gov">AirNow</a>'
      });
      overlayLayers['💨 Air Quality (PM2.5)'] = airQualityLayer;

      console.log('[MAP] Added AirNow layers for year:', currentYear);

      // Add default layer (OpenStreetMap for reliability)
      baseLayers['OpenStreetMap'].addTo(map);

      // Add AirNow fire/smoke by default
      airNowFireLayer.addTo(map);

      console.log('[MAP] Base layers and AirNow overlays added successfully');

      // Add layer control with base layers and overlays
      L.control.layers(baseLayers, overlayLayers, {
        position: 'topright',
        collapsed: false
      }).addTo(map);

      // Store map reference
      leafletMapRef.current = map;

      // Add fire markers
      addFireMarkers(map);

      // Add infrastructure markers
      addInfrastructureMarkers(map);

      // Add weather station markers
      addWeatherStationMarkers(map);

      // FORCED: Add all new layers for testing
      console.log('[ROCKET] FORCE ADDING ALL NEW LAYERS FOR TESTING');
      console.log('Current selectedLayers:', selectedLayers);

      // Force add fire hazard zones
      setTimeout(() => {
        console.log('Adding fire hazard zones...');
        addFireHazardZones(map);
      }, 1000);

      // Force add wildland urban interface zones
      setTimeout(() => {
        console.log('Adding WUI zones...');
        addWildlandUrbanInterface(map);
      }, 1500);

      // Force add evacuation routes
      setTimeout(() => {
        console.log('Adding evacuation routes...');
        addEvacuationRoutes(map);
      }, 2000);

      // Set proper zoom and center to show all fires
      if (activeFires.length > 0) {
        const bounds = L.latLngBounds(activeFires.map(fire => [fire.latitude, fire.longitude]));
        map.fitBounds(bounds, { padding: [20, 20] });
      }

      console.log('Professional map initialized successfully with', activeFires.length, 'fires');
      setLoading(false);

      } catch (err) {
        console.error('Map initialization error:', err);
        setError('Failed to initialize map: ' + (err as Error).message);
        setLoading(false);
      }
    }, 100); // Small delay to ensure DOM is ready

    return () => clearTimeout(timer);
  }, [mapLoaded, mapCenter, addFireMarkers]);

  // Fetch weather data
  useEffect(() => {
    const fetchWeatherData = async () => {
      try {
        const response = await fetch(
          `https://api.open-meteo.com/v1/forecast?` +
          `latitude=${mapCenter[0]}&longitude=${mapCenter[1]}&` +
          `current=temperature_2m,wind_speed_10m,wind_direction_10m,relative_humidity_2m,precipitation,visibility&` +
          `wind_speed_unit=mph&temperature_unit=fahrenheit&timezone=auto`
        );

        if (!response.ok) {
          throw new Error(`Weather API error: ${response.status}`);
        }

        const data = await response.json();
        setWeatherData(data);

      } catch (err) {
        console.error('Weather API error:', err);
        // Use fallback weather data if API fails
        setWeatherData({
          current: {
            temperature_2m: 72,
            wind_speed_10m: 8,
            wind_direction_10m: 270,
            relative_humidity_2m: 45,
            precipitation: 0,
            visibility: 10
          }
        });
      } finally {
        setLoading(false);
      }
    };

    fetchWeatherData();

    // Update every 10 minutes
    const interval = setInterval(fetchWeatherData, 600000);
    return () => clearInterval(interval);
  }, [mapCenter]);

  // Handle layer visibility changes
  useEffect(() => {
    if (!leafletMapRef.current || !fireMarkersLayer) return;

    // Toggle fire markers visibility
    if (selectedLayers.activeFires) {
      if (!leafletMapRef.current.hasLayer(fireMarkersLayer)) {
        leafletMapRef.current.addLayer(fireMarkersLayer);
      }
    } else {
      if (leafletMapRef.current.hasLayer(fireMarkersLayer)) {
        leafletMapRef.current.removeLayer(fireMarkersLayer);
      }
    }
  }, [selectedLayers.activeFires, fireMarkersLayer]);

  // Handle infrastructure layer visibility
  useEffect(() => {
    if (!leafletMapRef.current || !infrastructureLayer) return;

    const map = leafletMapRef.current;
    const showInfrastructure = selectedLayers.helicopterLanding ||
                               selectedLayers.waterSources ||
                               selectedLayers.emergencyServices ||
                               selectedLayers.communicationTowers ||
                               selectedLayers.fuelAnalysis ||
                               selectedLayers.infrastructure;

    console.log('Infrastructure layer visibility changed:', {
      showInfrastructure,
      helicopterLanding: selectedLayers.helicopterLanding,
      waterSources: selectedLayers.waterSources,
      emergencyServices: selectedLayers.emergencyServices,
      communicationTowers: selectedLayers.communicationTowers,
      fuelAnalysis: selectedLayers.fuelAnalysis,
      infrastructure: selectedLayers.infrastructure
    });

    if (showInfrastructure) {
      if (!map.hasLayer(infrastructureLayer)) {
        console.log('Adding infrastructure layer to map');
        map.addLayer(infrastructureLayer);
      }
    } else {
      if (map.hasLayer(infrastructureLayer)) {
        console.log('Removing infrastructure layer from map');
        map.removeLayer(infrastructureLayer);
      }
    }
  }, [selectedLayers.helicopterLanding, selectedLayers.waterSources, selectedLayers.emergencyServices,
      selectedLayers.communicationTowers, selectedLayers.fuelAnalysis, selectedLayers.infrastructure,
      infrastructureLayer]);

  // Handle weather station layer visibility
  useEffect(() => {
    if (!leafletMapRef.current || !weatherStationsLayer) return;

    const map = leafletMapRef.current;

    if (selectedLayers.weatherStations) {
      if (!map.hasLayer(weatherStationsLayer)) {
        map.addLayer(weatherStationsLayer);
      }
    } else {
      if (map.hasLayer(weatherStationsLayer)) {
        map.removeLayer(weatherStationsLayer);
      }
    }
  }, [selectedLayers.weatherStations, weatherStationsLayer]);

  // Handle hazard zones layer visibility
  useEffect(() => {
    if (!leafletMapRef.current) return;

    const map = leafletMapRef.current;

    if (selectedLayers.hazardZones) {
      // Always recreate the layer to ensure it appears
      addFireHazardZones(map);
    } else {
      // Remove existing layer
      if (hazardZonesLayer && map.hasLayer(hazardZonesLayer)) {
        map.removeLayer(hazardZonesLayer);
      }
    }
  }, [selectedLayers.hazardZones]);

  // Handle Wildland Urban Interface layer visibility
  useEffect(() => {
    if (!leafletMapRef.current) return;

    const map = leafletMapRef.current;

    if (selectedLayers.wildlandUrbanInterface) {
      // Always recreate the layer to ensure it appears
      addWildlandUrbanInterface(map);
    } else {
      // Remove existing layer
      if (wuiLayer && map.hasLayer(wuiLayer)) {
        map.removeLayer(wuiLayer);
      }
    }
  }, [selectedLayers.wildlandUrbanInterface]);

  // Handle Evacuation Routes layer visibility
  useEffect(() => {
    if (!leafletMapRef.current) return;

    const map = leafletMapRef.current;

    if (selectedLayers.evacuationRoutes) {
      // Always recreate the layer to ensure it appears
      addEvacuationRoutes(map);
    } else {
      // Remove existing layer
      if (evacuationRoutesLayer && map.hasLayer(evacuationRoutesLayer)) {
        map.removeLayer(evacuationRoutesLayer);
      }
    }
  }, [selectedLayers.evacuationRoutes]);

  // Initialize layers when map is ready
  useEffect(() => {
    if (!leafletMapRef.current) return;

    const map = leafletMapRef.current;

    // Initialize all layers with timeouts to ensure proper loading
    setTimeout(() => addFireHazardZones(map), 100);
    setTimeout(() => addWildlandUrbanInterface(map), 200);
    setTimeout(() => addEvacuationRoutes(map), 300);
  }, [leafletMapRef.current, addFireHazardZones, addWildlandUrbanInterface, addEvacuationRoutes]);

  // Create wind overlay
  const createWindOverlay = useCallback((map: any) => {
    if (!L || !weatherData) return null;

    const windLayer = L.layerGroup();
    const { wind_speed_10m, wind_direction_10m } = weatherData.current;

    // Create wind vectors across the map
    for (let lat = -1; lat <= 1; lat += 0.5) {
      for (let lng = -1; lng <= 1; lng += 0.5) {
        const windLat = mapCenter[0] + lat;
        const windLng = mapCenter[1] + lng;

        // Create wind arrow
        const windArrow = L.marker([windLat, windLng], {
          icon: L.divIcon({
            className: 'wind-arrow',
            html: `
              <div style="
                width: 40px;
                height: 40px;
                transform: rotate(${wind_direction_10m}deg);
                display: flex;
                align-items: center;
                justify-content: center;
              ">
                <div style="
                  width: ${Math.min(30, wind_speed_10m)}px;
                  height: 3px;
                  background: ${wind_speed_10m > 20 ? '#FF4444' : wind_speed_10m > 10 ? '#FFAA44' : '#44AAFF'};
                  position: relative;
                ">
                  <div style="
                    position: absolute;
                    right: -6px;
                    top: -3px;
                    width: 0;
                    height: 0;
                    border-left: 8px solid ${wind_speed_10m > 20 ? '#FF4444' : wind_speed_10m > 10 ? '#FFAA44' : '#44AAFF'};
                    border-top: 4px solid transparent;
                    border-bottom: 4px solid transparent;
                  "></div>
                </div>
              </div>
            `,
            iconSize: [40, 40],
            iconAnchor: [20, 20]
          })
        }).bindTooltip(`Wind: ${Math.round(wind_speed_10m)}mph`);

        windLayer.addLayer(windArrow);
      }
    }

    return windLayer;
  }, [weatherData, mapCenter]);

  // Create temperature overlay
  const createTemperatureOverlay = useCallback((map: any) => {
    if (!L || !weatherData) return null;

    const tempLayer = L.layerGroup();
    const { temperature_2m } = weatherData.current;

    // Create temperature hotspots
    for (let lat = -0.5; lat <= 0.5; lat += 0.25) {
      for (let lng = -0.5; lng <= 0.5; lng += 0.25) {
        const tempLat = mapCenter[0] + lat;
        const tempLng = mapCenter[1] + lng;
        const tempVariation = (Math.random() - 0.5) * 10;
        const localTemp = temperature_2m + tempVariation;

        const intensity = Math.min(1, Math.max(0, (localTemp - 60) / 60));
        const color = `rgba(${255 * intensity}, ${100 * (1 - intensity)}, 0, 0.6)`;

        const tempCircle = L.circle([tempLat, tempLng], {
          radius: 2000,
          fillColor: color,
          fillOpacity: 0.4,
          color: color,
          weight: 1
        }).bindTooltip(`Temperature: ${Math.round(localTemp)}degF`);

        tempLayer.addLayer(tempCircle);
      }
    }

    return tempLayer;
  }, [weatherData, mapCenter]);

  // Create humidity overlay
  const createHumidityOverlay = useCallback((map: any) => {
    if (!L || !weatherData) return null;

    const humidityLayer = L.layerGroup();
    const { relative_humidity_2m } = weatherData.current;

    // Create humidity zones
    for (let lat = -0.4; lat <= 0.4; lat += 0.2) {
      for (let lng = -0.4; lng <= 0.4; lng += 0.2) {
        const humLat = mapCenter[0] + lat;
        const humLng = mapCenter[1] + lng;
        const humVariation = (Math.random() - 0.5) * 20;
        const localHumidity = Math.max(0, Math.min(100, relative_humidity_2m + humVariation));

        const intensity = localHumidity / 100;
        const color = `rgba(0, ${150 * intensity}, 255, 0.5)`;

        const humidityRect = L.rectangle([
          [humLat - 0.1, humLng - 0.1],
          [humLat + 0.1, humLng + 0.1]
        ], {
          fillColor: color,
          fillOpacity: 0.3,
          color: color,
          weight: 1
        }).bindTooltip(`Humidity: ${Math.round(localHumidity)}%`);

        humidityLayer.addLayer(humidityRect);
      }
    }

    return humidityLayer;
  }, [weatherData, mapCenter]);

  // Handle weather layer visibility changes
  useEffect(() => {
    if (!leafletMapRef.current || !weatherData) return;

    const map = leafletMapRef.current;

    // Wind layer toggle
    if (selectedLayers.windVectors) {
      if (!windOverlayLayer) {
        const newWindLayer = createWindOverlay(map);
        if (newWindLayer) {
          newWindLayer.addTo(map);
          setWindOverlayLayer(newWindLayer);
        }
      } else if (!map.hasLayer(windOverlayLayer)) {
        map.addLayer(windOverlayLayer);
      }
    } else if (windOverlayLayer && map.hasLayer(windOverlayLayer)) {
      map.removeLayer(windOverlayLayer);
    }

    // Temperature layer toggle
    if (selectedLayers.temperature) {
      if (!temperatureOverlayLayer) {
        const newTempLayer = createTemperatureOverlay(map);
        if (newTempLayer) {
          newTempLayer.addTo(map);
          setTemperatureOverlayLayer(newTempLayer);
        }
      } else if (!map.hasLayer(temperatureOverlayLayer)) {
        map.addLayer(temperatureOverlayLayer);
      }
    } else if (temperatureOverlayLayer && map.hasLayer(temperatureOverlayLayer)) {
      map.removeLayer(temperatureOverlayLayer);
    }

    // Humidity layer toggle
    if (selectedLayers.humidity) {
      if (!humidityOverlayLayer) {
        const newHumidityLayer = createHumidityOverlay(map);
        if (newHumidityLayer) {
          newHumidityLayer.addTo(map);
          setHumidityOverlayLayer(newHumidityLayer);
        }
      } else if (!map.hasLayer(humidityOverlayLayer)) {
        map.addLayer(humidityOverlayLayer);
      }
    } else if (humidityOverlayLayer && map.hasLayer(humidityOverlayLayer)) {
      map.removeLayer(humidityOverlayLayer);
    }

  }, [selectedLayers.windVectors, selectedLayers.temperature, selectedLayers.humidity, weatherData, windOverlayLayer, temperatureOverlayLayer, humidityOverlayLayer, createWindOverlay, createTemperatureOverlay, createHumidityOverlay]);

  // Calculate fire weather index
  const calculateFireWeatherIndex = () => {
    if (!weatherData) return { index: 'Unknown', color: '#666' };

    const { temperature_2m, wind_speed_10m, relative_humidity_2m } = weatherData.current;
    let score = 0;

    if (temperature_2m > 100) score += 3;
    else if (temperature_2m > 90) score += 2;
    else if (temperature_2m > 80) score += 1;

    if (wind_speed_10m > 25) score += 3;
    else if (wind_speed_10m > 15) score += 2;
    else if (wind_speed_10m > 10) score += 1;

    if (relative_humidity_2m < 10) score += 3;
    else if (relative_humidity_2m < 20) score += 2;
    else if (relative_humidity_2m < 30) score += 1;

    if (score >= 7) return { index: 'EXTREME', color: '#8B0000' };
    if (score >= 5) return { index: 'VERY HIGH', color: '#FF4500' };
    if (score >= 3) return { index: 'HIGH', color: '#FF8C00' };
    if (score >= 1) return { index: 'MODERATE', color: '#FFD700' };
    return { index: 'LOW', color: '#32CD32' };
  };

  if (loading && !mapLoaded) {
    return (
      <Box
        sx={{
          height: '600px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: '#f5f5f5'
        }}
      >
        <Box sx={{ textAlign: 'center' }}>
          <CircularProgress sx={{ color: '#2196F3', mb: 2 }} size={50} />
          <Typography variant="h6" color="text.primary">Loading Professional Weather Map...</Typography>
          <Typography variant="body2" color="text.secondary">Initializing Leaflet mapping engine</Typography>
        </Box>
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ height: '600px', position: 'relative', background: '#f5f5f5', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 2 }}>
        <Alert severity="error" sx={{ maxWidth: 500 }}>
          <Typography variant="h6">Map Loading Error</Typography>
          <Typography variant="body2" sx={{ mb: 1 }}>{error}</Typography>
          <Typography variant="caption" sx={{ display: 'block', mt: 1 }}>
            Common causes:
            <br />• External map library (Leaflet) failed to load from CDN
            <br />• Network connectivity issues
            <br />• Browser blocked external resources
          </Typography>
        </Alert>
        <Box sx={{ textAlign: 'center' }}>
          <Typography variant="body2" color="text.secondary">
            The map displays active fires, weather data, and critical infrastructure.
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            Check your browser console (F12) for detailed error messages.
          </Typography>
        </Box>
      </Box>
    );
  }

  if (loading || !mapLoaded) {
    return (
      <Box sx={{ height: '600px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 2 }}>
        <CircularProgress size={60} />
        <Typography variant="body1" color="text.secondary">
          Loading interactive wildfire map...
        </Typography>
        <Typography variant="caption" color="text.secondary">
          Initializing Leaflet, loading base layers, and preparing fire data visualization
        </Typography>
      </Box>
    );
  }

  const fireIndex = calculateFireWeatherIndex();

  return (
    <Box sx={{ position: 'relative', width: '100%', height: '100%', minHeight: '500px' }}>
      {/* Windy Weather Widget Toggle & Controls */}
      <Box sx={{ position: 'absolute', top: 16, right: 16, zIndex: 1001 }}>
        <Card sx={{ p: 2, background: 'rgba(255, 255, 255, 0.95)', minWidth: 280 }}>
          <FormControlLabel
            control={
              <Switch
                checked={showWindyWidget}
                onChange={(e) => setShowWindyWidget(e.target.checked)}
                color="primary"
              />
            }
            label={<Typography variant="subtitle1" fontWeight="bold">🌦️ Windy Weather</Typography>}
          />

          {showWindyWidget && (
            <Box sx={{ mt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
              <Divider />

              {/* Weather Overlay Selection */}
              <FormControl fullWidth size="small">
                <InputLabel>Weather Layer</InputLabel>
                <Select
                  value={windyOverlay}
                  label="Weather Layer"
                  onChange={(e) => setWindyOverlay(e.target.value)}
                >
                  <MenuItem value="wind">💨 Wind Speed & Direction</MenuItem>
                  <MenuItem value="temp">🌡️ Temperature</MenuItem>
                  <MenuItem value="rain">🌧️ Rain & Thunder</MenuItem>
                  <MenuItem value="clouds">☁️ Clouds</MenuItem>
                  <MenuItem value="pressure">📊 Pressure</MenuItem>
                  <MenuItem value="rh">💧 Relative Humidity</MenuItem>
                  <MenuItem value="waves">🌊 Waves (Coastal)</MenuItem>
                  <MenuItem value="gust">💨 Wind Gusts</MenuItem>
                  <MenuItem value="snowcover">❄️ Snow Cover</MenuItem>
                  <MenuItem value="cape">⚡ Lightning Risk (CAPE)</MenuItem>
                  <MenuItem value="visibility">👁️ Visibility</MenuItem>
                  <MenuItem value="lclouds">☁️ Low Clouds</MenuItem>
                  <MenuItem value="mclouds">☁️ Medium Clouds</MenuItem>
                  <MenuItem value="hclouds">☁️ High Clouds</MenuItem>
                  <MenuItem value="dewpoint">💦 Dew Point</MenuItem>
                </Select>
              </FormControl>

              {/* Weather Model Selection */}
              <FormControl fullWidth size="small">
                <InputLabel>Forecast Model</InputLabel>
                <Select
                  value={windyProduct}
                  label="Forecast Model"
                  onChange={(e) => setWindyProduct(e.target.value)}
                >
                  <MenuItem value="ecmwf">🌍 ECMWF (Most Accurate)</MenuItem>
                  <MenuItem value="gfs">🇺🇸 GFS (USA Model)</MenuItem>
                  <MenuItem value="nam">🇺🇸 NAM (North America)</MenuItem>
                  <MenuItem value="icon">🇩🇪 ICON (German Model)</MenuItem>
                  <MenuItem value="iconEu">🇪🇺 ICON-EU (Europe)</MenuItem>
                  <MenuItem value="nems">🌏 NEMS (Global)</MenuItem>
                </Select>
              </FormControl>

              {/* Altitude Level Selection */}
              <FormControl fullWidth size="small">
                <InputLabel>Altitude Level</InputLabel>
                <Select
                  value={windyLevel}
                  label="Altitude Level"
                  onChange={(e) => setWindyLevel(e.target.value)}
                >
                  <MenuItem value="surface">🏔️ Surface Level</MenuItem>
                  <MenuItem value="950h">950 hPa (~500m)</MenuItem>
                  <MenuItem value="925h">925 hPa (~750m)</MenuItem>
                  <MenuItem value="900h">900 hPa (~1km)</MenuItem>
                  <MenuItem value="850h">850 hPa (~1.5km)</MenuItem>
                  <MenuItem value="800h">800 hPa (~2km)</MenuItem>
                  <MenuItem value="700h">700 hPa (~3km)</MenuItem>
                  <MenuItem value="600h">600 hPa (~4.2km)</MenuItem>
                  <MenuItem value="500h">500 hPa (~5.5km)</MenuItem>
                  <MenuItem value="400h">400 hPa (~7km)</MenuItem>
                  <MenuItem value="300h">300 hPa (~9km)</MenuItem>
                  <MenuItem value="250h">250 hPa (~10.5km)</MenuItem>
                  <MenuItem value="200h">200 hPa (~12km)</MenuItem>
                  <MenuItem value="150h">150 hPa (~14km)</MenuItem>
                </Select>
              </FormControl>

              <Typography variant="caption" color="text.secondary">
                💡 Use surface level for firefighting operations. Higher altitudes show upper-level winds.
              </Typography>
            </Box>
          )}
        </Card>
      </Box>

      {/* Windy Weather Widget Overlay - Smaller Size */}
      {showWindyWidget && (
        <Box sx={{
          position: 'absolute',
          top: '10%',
          left: '10%',
          width: '80%',
          height: '75%',
          zIndex: 999,
          background: 'rgba(0, 0, 0, 0.5)',
          borderRadius: 2,
          boxShadow: '0 8px 32px rgba(0,0,0,0.3)'
        }}>
          <Card sx={{ width: '100%', height: '100%', position: 'relative' }}>
            <IconButton
              sx={{ position: 'absolute', top: 8, right: 8, zIndex: 1002, background: 'white' }}
              onClick={() => setShowWindyWidget(false)}
            >
              <Close />
            </IconButton>
            <Box sx={{ width: '100%', height: '100%' }}>
              <iframe
                width="100%"
                height="100%"
                src={`https://embed.windy.com/embed2.html?lat=${mapCenter[0]}&lon=${mapCenter[1]}&detailLat=${mapCenter[0]}&detailLon=${mapCenter[1]}&width=650&height=450&zoom=8&level=${windyLevel}&overlay=${windyOverlay}&product=${windyProduct}&menu=&message=true&marker=true&calendar=now&pressure=true&type=map&location=coordinates&detail=true&metricWind=mph&metricTemp=%C2%B0F&radarRange=-1`}
                frameBorder="0"
                title="Windy Weather Map"
                key={`${windyOverlay}-${windyProduct}-${windyLevel}`}
              />
            </Box>
          </Card>
        </Box>
      )}

      {/* Leaflet Map Container */}
      <Box
        ref={mapRef}
        sx={{
          width: '100%',
          height: '100%',
          borderRadius: 2,
          overflow: 'hidden',
          '& .leaflet-container': {
            height: '100%',
            width: '100%',
            fontFamily: 'Arial, sans-serif'
          },
          '& .leaflet-control-layers': {
            background: 'rgba(255, 255, 255, 0.95)',
            borderRadius: '8px',
            padding: '10px'
          },
          '& .leaflet-popup-content-wrapper': {
            borderRadius: '8px'
          }
        }}
      />

      {/* Dismissible Fire Weather Alert */}
      {weatherData && !alertDismissed && (
        <Alert
          severity={fireIndex.index === 'EXTREME' ? 'error' : fireIndex.index === 'VERY HIGH' ? 'warning' : 'info'}
          onClose={() => setAlertDismissed(true)}
          sx={{
            position: 'absolute',
            top: 16,
            left: 16,
            zIndex: 1000,
            background: `rgba(${fireIndex.color === '#8B0000' ? '139, 0, 0' : fireIndex.color === '#FF4500' ? '255, 69, 0' : '33, 150, 243'}, 0.95)`,
            color: 'white',
            '& .MuiAlert-icon': {
              color: 'white'
            },
            '& .MuiAlert-action': {
              color: 'white'
            }
          }}
        >
          <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
            [FIRE] FIRE WEATHER: {fireIndex.index}
          </Typography>
          <Typography variant="caption">
            {Math.round(weatherData.current.temperature_2m)}degF | {Math.round(weatherData.current.wind_speed_10m)}mph | {Math.round(weatherData.current.relative_humidity_2m)}% RH
          </Typography>
        </Alert>
      )}

      {/* Compact Weather Controls */}
      <Card
        sx={{
          position: 'absolute',
          top: 16,
          right: 16,
          background: 'rgba(255, 255, 255, 0.95)',
          backdropFilter: 'blur(10px)',
          zIndex: 1000,
          borderRadius: 2,
          boxShadow: '0 4px 20px rgba(0,0,0,0.15)',
          maxWidth: controlsExpanded ? 280 : 60,
          transition: 'all 0.3s ease'
        }}
      >
        {/* Header with Toggle */}
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            p: 1,
            cursor: 'pointer'
          }}
          onClick={() => setControlsExpanded(!controlsExpanded)}
        >
          {controlsExpanded && (
            <Typography variant="subtitle2" sx={{ display: 'flex', alignItems: 'center', gap: 1, fontWeight: 'bold' }}>
              <Cloud color="primary" />
              Weather Layers
            </Typography>
          )}
          <IconButton size="small">
            {controlsExpanded ? <ExpandLess /> : <ExpandMore />}
          </IconButton>
        </Box>

        {/* Collapsible Content */}
        <Collapse in={controlsExpanded}>
          <Box sx={{ px: 2, pb: 2 }}>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              <FormControlLabel
                control={
                  <Switch
                    checked={selectedLayers.activeFires}
                    onChange={() => onLayerToggle('activeFires')}
                    color="error"
                    size="small"
                  />
                }
                label={
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <LocalFireDepartment sx={{
                      fontSize: 14,
                      color: selectedLayers.activeFires ? '#FF4500' : '#999'
                    }} />
                    <Typography variant="caption" sx={{
                      color: selectedLayers.activeFires ? 'inherit' : '#999'
                    }}>
                      Active Fires ({activeFires.length}) {selectedLayers.activeFires ? '✓' : '✗'}
                    </Typography>
                  </Box>
                }
              />

              <FormControlLabel
                control={
                  <Switch
                    checked={selectedLayers.windVectors}
                    onChange={() => onLayerToggle('windVectors')}
                    color="primary"
                    size="small"
                  />
                }
                label={
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Air sx={{
                      fontSize: 14,
                      color: selectedLayers.windVectors ? '#2196F3' : '#999'
                    }} />
                    <Typography variant="caption" sx={{
                      color: selectedLayers.windVectors ? 'inherit' : '#999'
                    }}>
                      Wind Speed & Direction {selectedLayers.windVectors ? '✓' : '✗'}
                    </Typography>
                  </Box>
                }
              />

              <FormControlLabel
                control={
                  <Switch
                    checked={selectedLayers.temperature}
                    onChange={() => onLayerToggle('temperature')}
                    color="warning"
                    size="small"
                  />
                }
                label={
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Thermostat sx={{ fontSize: 14, color: '#FF9800' }} />
                    <Typography variant="caption">Temperature</Typography>
                  </Box>
                }
              />

              <FormControlLabel
                control={
                  <Switch
                    checked={selectedLayers.humidity}
                    onChange={() => onLayerToggle('humidity')}
                    color="info"
                    size="small"
                  />
                }
                label={
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Opacity sx={{ fontSize: 14, color: '#00BCD4' }} />
                    <Typography variant="caption">Humidity</Typography>
                  </Box>
                }
              />

              <FormControlLabel
                control={
                  <Switch
                    checked={selectedLayers.precipitation}
                    onChange={() => onLayerToggle('precipitation')}
                    color="info"
                    size="small"
                  />
                }
                label={
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Cloud sx={{ fontSize: 14, color: '#4CAF50' }} />
                    <Typography variant="caption">Precipitation</Typography>
                  </Box>
                }
              />
            </Box>

            {/* Current Weather Stats */}
            {weatherData && (
              <Box sx={{ mt: 2, pt: 2, borderTop: '1px solid rgba(0,0,0,0.1)' }}>
                <Typography variant="caption" sx={{ display: 'block', mb: 1, fontWeight: 'bold' }}>
                  Current Conditions:
                </Typography>

                <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 1, fontSize: '10px' }}>
                  <Typography variant="caption" sx={{ color: '#FF9800', fontSize: '10px' }}>
                    [THERMOMETER] {Math.round(weatherData.current.temperature_2m)}degF
                  </Typography>
                  <Typography variant="caption" sx={{ color: '#2196F3', fontSize: '10px' }}>
                    💨 {Math.round(weatherData.current.wind_speed_10m)}mph
                  </Typography>
                  <Typography variant="caption" sx={{ color: '#00BCD4', fontSize: '10px' }}>
                    [DROPLET] {Math.round(weatherData.current.relative_humidity_2m)}%
                  </Typography>
                  <Typography variant="caption" sx={{ color: '#4CAF50', fontSize: '10px' }}>
                    👁️ {Math.round((weatherData.current.visibility || 10000) / 1000)}mi
                  </Typography>
                </Box>

                <Box
                  sx={{
                    mt: 1,
                    p: 1,
                    background: `${fireIndex.color}20`,
                    borderRadius: 1,
                    border: `1px solid ${fireIndex.color}40`
                  }}
                >
                  <Typography
                    variant="caption"
                    sx={{
                      color: fireIndex.color,
                      fontWeight: 'bold',
                      display: 'block',
                      fontSize: '10px'
                    }}
                  >
                    Fire Weather Index: {fireIndex.index}
                  </Typography>
                </Box>
              </Box>
            )}

            {/* Data Attribution */}
            <Typography
              variant="caption"
              sx={{
                color: 'text.secondary',
                display: 'block',
                textAlign: 'center',
                mt: 1,
                pt: 1,
                borderTop: '1px solid rgba(0,0,0,0.1)',
                fontSize: '9px'
              }}
            >
              Map (C) OpenStreetMap | Weather by Open-Meteo
            </Typography>
          </Box>
        </Collapse>
      </Card>

      {/* Fire Count Badge */}
      <Box
        sx={{
          position: 'absolute',
          bottom: 16,
          left: 16,
          background: 'rgba(255, 69, 0, 0.9)',
          color: 'white',
          padding: '8px 16px',
          borderRadius: 20,
          zIndex: 1000,
          display: 'flex',
          alignItems: 'center',
          gap: 1,
          boxShadow: '0 2px 10px rgba(255, 69, 0, 0.3)'
        }}
      >
        <LocalFireDepartment sx={{ fontSize: 18 }} />
        <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
          {activeFires.length} Active Fire{activeFires.length !== 1 ? 's' : ''}
        </Typography>
      </Box>
    </Box>
  );
};

export default ProfessionalWeatherMap;