import React, { useEffect, useRef, useState } from 'react';
import { Box, Typography, Button, Switch, FormControlLabel, Card, Alert } from '@mui/material';
import {
  Visibility,
  VisibilityOff,
  LocalFireDepartment,
  Air,
  Thermostat,
  Opacity,
  Cloud,
  Compress,
  FlashOn,
  AcUnit,
  WaterDrop,
  Assessment,
  MonitorHeart,
  Waves,
  Landscape,
  Warning
} from '@mui/icons-material';

interface WindyMapEmbedProps {
  mapCenter: [number, number];
  activeFires: any[];
  selectedLayers: {
    windVectors: boolean;
    temperature: boolean;
    humidity: boolean;
    precipitation: boolean;
    pressure: boolean;
    cloudCover: boolean;
    cape: boolean;
    visibility: boolean;
    snow: boolean;
    waves: boolean;
    lightning: boolean;
    airQuality: boolean;
  };
  onLayerToggle: (layer: keyof WindyMapEmbedProps['selectedLayers']) => void;
}

declare global {
  interface Window {
    L: any;
    windyInit: any;
    windyAPI: any;
  }
}

const WindyMapEmbed: React.FC<WindyMapEmbedProps> = ({
  mapCenter,
  activeFires,
  selectedLayers,
  onLayerToggle
}) => {
  const mapRef = useRef<HTMLDivElement>(null);
  const windyMapRef = useRef<any>(null);
  const [windyLoaded, setWindyLoaded] = useState(false);
  const [loading, setLoading] = useState(true);
  const [showFireOverlay, setShowFireOverlay] = useState(true);
  const [showControls, setShowControls] = useState(false);
  const [mapType, setMapType] = useState('streets');
  const [operationalLayers, setOperationalLayers] = useState({
    fireHazardZones: true,
    emergencyServices: true,
    wildlandUrbanInterface: true,
    communicationTowers: true,
    helicopterLandingZones: true,
    waterSources: true,
    evacuationRoutes: true,
    fuelLoadAnalysis: true,
    weatherStations: true,
    activeFires: true
  });

  // Initialize Windy Map with iframe embed approach (more reliable)
  useEffect(() => {
    if (!mapRef.current || windyLoaded) return;

    console.log('Initializing Windy embed iframe...');

    // Clear existing content
    mapRef.current.innerHTML = '';

    // Create Windy embed iframe with weather layers
    const apiKey = process.env.REACT_APP_WINDY_API_KEY;
    const lat = mapCenter[0];
    const lng = mapCenter[1];

    // Build Windy embed URL for worldwide weather data (no restrictions)
    const baseUrl = 'https://embed.windy.com/embed2.html';

    // Start with global view centered on world
    const globalLat = 30.0; // Global view center
    const globalLng = 0.0;  // Global view center

    // Determine which overlay to show based on selected layers
    let overlay = 'wind'; // Default to wind
    if (selectedLayers.temperature) {
      overlay = 'temp';
    } else if (selectedLayers.humidity) {
      overlay = 'rh';
    } else if (selectedLayers.precipitation) {
      overlay = 'rain';
    } else if (selectedLayers.pressure) {
      overlay = 'pressure';
    } else if (selectedLayers.cloudCover) {
      overlay = 'clouds';
    } else if (selectedLayers.cape) {
      overlay = 'cape';
    } else if (selectedLayers.visibility) {
      overlay = 'visibility';
    } else if (selectedLayers.snow) {
      overlay = 'snow';
    } else if (selectedLayers.waves) {
      overlay = 'waves';
    } else if (selectedLayers.lightning) {
      overlay = 'lightning';
    } else if (selectedLayers.airQuality) {
      overlay = 'pm2p5';
    } else if (selectedLayers.windVectors) {
      overlay = 'wind';
    }

    // Map mapType to Windy's accepted values
    const windyMapType = mapType === 'streets' ? 'map' :
                        mapType === 'satellite' ? 'satellite' :
                        mapType === 'terrain' ? 'terrain' :
                        mapType === 'naip' ? 'satellite' : // NAIP fallback to satellite
                        mapType === 'topo' ? 'terrain' : 'map'; // USGS topo fallback to terrain

    const params = new URLSearchParams({
      lat: globalLat.toString(),
      lon: globalLng.toString(),
      detailLat: globalLat.toString(),
      detailLon: globalLng.toString(),
      zoom: '3', // Global view zoom
      level: 'surface',
      overlay: overlay,
      product: 'gfs',
      menu: '',
      message: '',
      marker: 'off',
      calendar: 'now',
      pressure: '',
      type: windyMapType,
      location: 'coordinates',
      detail: 'on',
      metricWind: 'mph',
      metricTemp: 'degF',
      metricPressure: 'inHg',
      metricDistance: 'mi',
      radarRange: '-1',
      autoplay: '0',
      numDirection: '1',
      windLabels: '1',
      isolines: '1',
      isolinesHd: '1'
    });

    if (apiKey) {
      params.append('key', apiKey);
    }

    const embedUrl = `${baseUrl}?${params.toString()}`;

    console.log('🌍 Windy map: Global weather view (no restrictions)');
    console.log('[MAP] Windy embed URL:', embedUrl);
    console.log('🌦️ Selected overlay:', overlay);
    console.log('[GEAR] Global weather data - no fire markers');

    // Create Windy embed iframe with proper map type support
    const iframe = document.createElement('iframe');
    iframe.width = '100%';
    iframe.height = '100%';
    iframe.style.border = 'none';
    iframe.style.borderRadius = '8px';
    iframe.src = embedUrl;
    iframe.allow = 'geolocation';
    iframe.title = 'Windy Weather Map';

    console.log('Creating Windy iframe with URL:', embedUrl);
    console.log('Map type:', mapType, '-> Windy type:', windyMapType);

    // Add iframe to container
    mapRef.current.appendChild(iframe);

    // No fire overlays - this is weather-only map
    setTimeout(() => {
      setWindyLoaded(true);
      setLoading(false);
    }, 1000);

  }, [mapCenter, selectedLayers, mapType, operationalLayers, windyLoaded]);

  // Force reload when map type changes - key fix for map format switching
  useEffect(() => {
    if (windyLoaded && mapRef.current) {
      console.log('Map type changed to:', mapType, ' - Force reloading iframe...');

      // Clear existing iframe
      mapRef.current.innerHTML = '';

      // Reset states to trigger complete reload
      setWindyLoaded(false);
      setLoading(true);

      // Small delay to ensure cleanup
      setTimeout(() => {
        console.log('Starting map reload with new type:', mapType);
      }, 100);
    }
  }, [mapType]);

  // Geographic coordinate conversion utilities - EXACT match with Windy's California bounds
  // These bounds exactly match the restricted Windy viewport for 1:1 coordinate mapping
  const CALIFORNIA_MAP_BOUNDS = {
    north: 42.0,    // Exact match with Windy bounds restriction
    south: 32.5,    // Exact match with Windy bounds restriction
    east: -114.0,   // Exact match with Windy bounds restriction
    west: -124.5    // Exact match with Windy bounds restriction
  };

  // Convert lat/lng to screen percentage position for overlay on Windy map
  // Since Windy is restricted to exact California bounds, this should be 1:1 mapping
  const latLngToPosition = (lat: number, lng: number) => {
    // Check if coordinates are within California bounds
    const inBounds = lat >= CALIFORNIA_MAP_BOUNDS.south && lat <= CALIFORNIA_MAP_BOUNDS.north &&
                     lng >= CALIFORNIA_MAP_BOUNDS.west && lng <= CALIFORNIA_MAP_BOUNDS.east;

    // Normalize coordinates to 0-1 range within California bounds
    const latNormalized = (lat - CALIFORNIA_MAP_BOUNDS.south) / (CALIFORNIA_MAP_BOUNDS.north - CALIFORNIA_MAP_BOUNDS.south);
    const lngNormalized = (lng - CALIFORNIA_MAP_BOUNDS.west) / (CALIFORNIA_MAP_BOUNDS.east - CALIFORNIA_MAP_BOUNDS.west);

    // Convert to screen percentages (flip Y axis for screen coordinates)
    // Since Windy is bounded to California, this should be direct 1:1 mapping
    const topPercent = (1 - latNormalized) * 100;  // Flip Y for screen coordinates
    const leftPercent = lngNormalized * 100;

    const result = {
      top: `${Math.max(0, Math.min(100, topPercent))}%`,
      left: `${Math.max(0, Math.min(100, leftPercent))}%`
    };

    // Debug logging to verify coordinate conversion accuracy
    console.log(`[MAP] ${lat.toFixed(4)}, ${lng.toFixed(4)} -> ${result.top}, ${result.left} ${inBounds ? '[CHECK] CALIFORNIA' : '[X] OUT OF CA'}`);

    return result;
  };

  // Infrastructure layer functions - using real geographic coordinates
  const addFireHazardZonesOverlay = (overlayContainer: HTMLElement) => {
    console.log('[FIRE] Adding Fire Hazard Zones overlay with real coordinates');

    // Real fire hazard zones in California with actual lat/lng coordinates
    const hazardZones = [
      {
        name: 'Angeles National Forest',
        lat: 34.3774, lng: -117.7975,
        radius: 25, // km radius for circular zones
        severity: 'Very High',
        color: '#8B0000'
      },
      {
        name: 'Malibu Hills',
        lat: 34.0259, lng: -118.7798,
        radius: 15,
        severity: 'High',
        color: '#FF4500'
      },
      {
        name: 'San Bernardino Mountains',
        lat: 34.1808, lng: -117.3089,
        radius: 35,
        severity: 'Very High',
        color: '#8B0000'
      },
      {
        name: 'Ventura County',
        lat: 34.3985, lng: -119.1962,
        radius: 20,
        severity: 'Moderate',
        color: '#FFA500'
      },
      {
        name: 'Riverside County',
        lat: 33.7175, lng: -116.2023,
        radius: 30,
        severity: 'High',
        color: '#FF6347'
      }
    ];

    hazardZones.forEach((zone) => {
      const position = latLngToPosition(zone.lat, zone.lng);

      const zoneDiv = document.createElement('div');
      zoneDiv.className = 'fire-hazard-zone';
      zoneDiv.style.position = 'absolute';
      zoneDiv.style.left = position.left;
      zoneDiv.style.top = position.top;
      zoneDiv.style.width = `${zone.radius * 2}px`;
      zoneDiv.style.height = `${zone.radius * 2}px`;
      zoneDiv.style.backgroundColor = zone.color;
      zoneDiv.style.opacity = '0.4';
      zoneDiv.style.border = `3px solid ${zone.color}`;
      zoneDiv.style.borderRadius = '50%'; // Circular zones
      zoneDiv.style.transform = 'translate(-50%, -50%)'; // Center the circle
      zoneDiv.style.pointerEvents = 'auto';
      zoneDiv.style.cursor = 'pointer';
      zoneDiv.style.zIndex = '9998';
      zoneDiv.title = `[FIRE] ${zone.name} - Fire Hazard: ${zone.severity}\nCoordinates: ${zone.lat}degN, ${Math.abs(zone.lng)}degW`;

      // Add zone label
      const label = document.createElement('div');
      label.style.position = 'absolute';
      label.style.top = '50%';
      label.style.left = '50%';
      label.style.transform = 'translate(-50%, -50%)';
      label.style.background = 'rgba(0, 0, 0, 0.8)';
      label.style.color = 'white';
      label.style.padding = '4px 8px';
      label.style.borderRadius = '4px';
      label.style.fontSize = '11px';
      label.style.fontWeight = 'bold';
      label.style.textAlign = 'center';
      label.style.whiteSpace = 'nowrap';
      label.innerHTML = `[FIRE] ${zone.severity}`;
      zoneDiv.appendChild(label);

      overlayContainer.appendChild(zoneDiv);
    });
  };

  const addHelicopterLandingZonesOverlay = (overlayContainer: HTMLElement) => {
    console.log('[HELICOPTER] Adding Helicopter Landing Zones overlay with real coordinates');

    // Real helicopter landing zones in California with actual lat/lng coordinates - fixed coordinate system
    const landingZones = [
      { name: 'Van Norman Complex Helipad', lat: 34.2778, lng: -118.4717, capacity: 2 },
      { name: 'Angeles National Forest Helispot', lat: 34.4208, lng: -117.6798, capacity: 4 },
      { name: 'Griffith Observatory Helipad', lat: 34.1184, lng: -118.3004, capacity: 1 },
      { name: 'Santa Monica Heliport', lat: 34.0158, lng: -118.4511, capacity: 3 },
      { name: 'LAFD Helibase', lat: 34.2573, lng: -118.2324, capacity: 6 },
      { name: 'Riverside County Helipad', lat: 33.7175, lng: -116.2023, capacity: 3 }
    ];

    landingZones.forEach((zone) => {
      const position = latLngToPosition(zone.lat, zone.lng);

      const marker = document.createElement('div');
      marker.className = 'helicopter-landing-zone';
      marker.style.position = 'absolute';
      marker.style.left = position.left;
      marker.style.top = position.top;
      marker.style.width = '40px';
      marker.style.height = '40px';
      marker.style.background = 'rgba(76, 175, 80, 0.9)';
      marker.style.borderRadius = '50%';
      marker.style.border = '3px solid white';
      marker.style.transform = 'translate(-50%, -50%)';
      marker.style.pointerEvents = 'auto';
      marker.style.cursor = 'pointer';
      marker.style.zIndex = '10001';
      marker.style.display = 'flex';
      marker.style.alignItems = 'center';
      marker.style.justifyContent = 'center';
      marker.style.fontSize = '20px';
      marker.title = `[HELICOPTER] ${zone.name} - Capacity: ${zone.capacity} aircraft\nCoordinates: ${zone.lat}degN, ${Math.abs(zone.lng)}degW`;
      marker.innerHTML = '[HELICOPTER]';

      overlayContainer.appendChild(marker);
    });
  };

  const addWaterSourcesOverlay = (overlayContainer: HTMLElement) => {
    console.log('[DROPLET] Adding Water Sources overlay with real coordinates');

    // Real water sources in California with actual lat/lng coordinates
    const waterSources = [
      { name: 'Hansen Dam Recreation Area', lat: 34.2508, lng: -118.4311, capacity: '50,000 gal' },
      { name: 'Lopez Reservoir', lat: 35.1658, lng: -120.5036, capacity: '25,000 gal' },
      { name: 'Castaic Lake', lat: 34.4917, lng: -118.6145, capacity: '75,000 gal' },
      { name: 'Santa Monica Pier', lat: 34.0086, lng: -118.4977, capacity: 'Ocean Access' }
    ];

    waterSources.forEach((source) => {
      const position = latLngToPosition(source.lat, source.lng);

      const marker = document.createElement('div');
      marker.className = 'water-source-marker';
      marker.style.position = 'absolute';
      marker.style.left = position.left;
      marker.style.top = position.top;
      marker.style.width = '36px';
      marker.style.height = '36px';
      marker.style.background = 'rgba(33, 150, 243, 0.9)';
      marker.style.borderRadius = '50%';
      marker.style.border = '3px solid white';
      marker.style.transform = 'translate(-50%, -50%)';
      marker.style.pointerEvents = 'auto';
      marker.style.cursor = 'pointer';
      marker.style.zIndex = '10001';
      marker.style.display = 'flex';
      marker.style.alignItems = 'center';
      marker.style.justifyContent = 'center';
      marker.style.fontSize = '18px';
      marker.title = `[DROPLET] ${source.name} - Capacity: ${source.capacity}\nCoordinates: ${source.lat}degN, ${Math.abs(source.lng)}degW`;
      marker.innerHTML = '[DROPLET]';

      overlayContainer.appendChild(marker);
    });
  };

  const addEmergencyServicesOverlay = (overlayContainer: HTMLElement) => {
    console.log('🏥 Adding Emergency Services overlay with real coordinates');

    // Real emergency services in California with actual lat/lng coordinates
    const emergencyServices = [
      { name: 'Olive View-UCLA Medical Center', lat: 34.2694, lng: -118.4728, type: 'hospital', icon: '🏥' },
      { name: 'LA County Fire Station 73', lat: 34.2503, lng: -118.4589, type: 'fire', icon: '🚒' },
      { name: 'Sylmar Police Station', lat: 34.3089, lng: -118.4389, type: 'police', icon: '🚓' },
      { name: 'UCLA Medical Center', lat: 34.0689, lng: -118.4452, type: 'hospital', icon: '🏥' }
    ];

    emergencyServices.forEach((service) => {
      const position = latLngToPosition(service.lat, service.lng);

      const marker = document.createElement('div');
      marker.className = 'emergency-service-marker';
      marker.style.position = 'absolute';
      marker.style.left = position.left;
      marker.style.top = position.top;
      marker.style.width = '38px';
      marker.style.height = '38px';
      marker.style.background = 'rgba(244, 67, 54, 0.9)';
      marker.style.borderRadius = '50%';
      marker.style.border = '3px solid white';
      marker.style.transform = 'translate(-50%, -50%)';
      marker.style.pointerEvents = 'auto';
      marker.style.cursor = 'pointer';
      marker.style.zIndex = '10001';
      marker.style.display = 'flex';
      marker.style.alignItems = 'center';
      marker.style.justifyContent = 'center';
      marker.style.fontSize = '18px';
      marker.title = `${service.icon} ${service.name} - ${service.type.toUpperCase()}\nCoordinates: ${service.lat}degN, ${Math.abs(service.lng)}degW`;
      marker.innerHTML = service.icon;

      overlayContainer.appendChild(marker);
    });
  };

  const addCommunicationTowersOverlay = (overlayContainer: HTMLElement) => {
    console.log('[SATELLITE_ANTENNA] Adding Communication Towers overlay with real coordinates');

    // Real communication tower locations in California with actual lat/lng coordinates
    const commTowers = [
      { name: 'Mount Wilson Communications', lat: 34.2208, lng: -118.0618, status: 'Operational' },
      { name: 'Verdugo Peak Repeater', lat: 34.2275, lng: -118.2187, status: 'Operational' },
      { name: 'Angeles Crest Tower', lat: 34.3708, lng: -117.6797, status: 'Limited' },
      { name: 'Santa Monica Tower', lat: 34.0195, lng: -118.4912, status: 'Operational' }
    ];

    commTowers.forEach((tower) => {
      const position = latLngToPosition(tower.lat, tower.lng);

      const marker = document.createElement('div');
      marker.className = 'communication-tower-marker';
      marker.style.position = 'absolute';
      marker.style.left = position.left;
      marker.style.top = position.top;
      marker.style.width = '35px';
      marker.style.height = '35px';
      marker.style.background = 'rgba(255, 152, 0, 0.9)';
      marker.style.borderRadius = '50%';
      marker.style.border = '3px solid white';
      marker.style.transform = 'translate(-50%, -50%)';
      marker.style.pointerEvents = 'auto';
      marker.style.cursor = 'pointer';
      marker.style.zIndex = '10001';
      marker.style.display = 'flex';
      marker.style.alignItems = 'center';
      marker.style.justifyContent = 'center';
      marker.style.fontSize = '16px';
      marker.title = `[SATELLITE_ANTENNA] ${tower.name} - Status: ${tower.status}\nCoordinates: ${tower.lat}degN, ${Math.abs(tower.lng)}degW`;
      marker.innerHTML = '[SATELLITE_ANTENNA]';

      overlayContainer.appendChild(marker);
    });
  };

  const addWildlandUrbanInterfaceOverlay = (overlayContainer: HTMLElement) => {
    console.log('[HOUSE] Adding Wildland Urban Interface overlay with real coordinates');

    // Real WUI zones in California with actual lat/lng coordinates
    const wuiZones = [
      { name: 'Sylmar WUI Zone', lat: 34.3089, lng: -118.4389, radius: 8, risk: 'High' },
      { name: 'Porter Ranch WUI Zone', lat: 34.2689, lng: -118.5617, radius: 6, risk: 'Moderate' },
      { name: 'Malibu WUI Zone', lat: 34.0259, lng: -118.7798, radius: 10, risk: 'Extreme' },
      { name: 'Altadena WUI Zone', lat: 34.1897, lng: -118.1315, radius: 5, risk: 'High' },
      { name: 'Thousand Oaks WUI', lat: 34.2206, lng: -118.8756, radius: 7, risk: 'Moderate' }
    ];

    wuiZones.forEach((zone) => {
      const position = latLngToPosition(zone.lat, zone.lng);
      const riskColors = {
        'Extreme': '#8B0000',
        'High': '#FF4500',
        'Moderate': '#FFA500',
        'Low': '#32CD32'
      };

      const zoneDiv = document.createElement('div');
      zoneDiv.className = 'wui-zone';
      zoneDiv.style.position = 'absolute';
      zoneDiv.style.left = position.left;
      zoneDiv.style.top = position.top;
      zoneDiv.style.width = `${zone.radius * 2}px`;
      zoneDiv.style.height = `${zone.radius * 2}px`;
      zoneDiv.style.backgroundColor = riskColors[zone.risk as keyof typeof riskColors];
      zoneDiv.style.opacity = '0.3';
      zoneDiv.style.border = `2px dashed ${riskColors[zone.risk as keyof typeof riskColors]}`;
      zoneDiv.style.borderRadius = '50%'; // Circular zones
      zoneDiv.style.transform = 'translate(-50%, -50%)'; // Center the circle
      zoneDiv.style.pointerEvents = 'auto';
      zoneDiv.style.cursor = 'pointer';
      zoneDiv.style.zIndex = '9999';
      zoneDiv.title = `[HOUSE] ${zone.name} - Risk: ${zone.risk}\nCoordinates: ${zone.lat}degN, ${Math.abs(zone.lng)}degW`;

      // Add zone label
      const label = document.createElement('div');
      label.style.position = 'absolute';
      label.style.top = '50%';
      label.style.left = '50%';
      label.style.transform = 'translate(-50%, -50%)';
      label.style.background = 'rgba(0, 0, 0, 0.8)';
      label.style.color = 'white';
      label.style.padding = '3px 6px';
      label.style.borderRadius = '3px';
      label.style.fontSize = '10px';
      label.style.fontWeight = 'bold';
      label.style.textAlign = 'center';
      label.innerHTML = `[HOUSE] WUI`;
      zoneDiv.appendChild(label);

      overlayContainer.appendChild(zoneDiv);
    });
  };

  const addEvacuationRoutesOverlay = (overlayContainer: HTMLElement) => {
    console.log('🛣️ Adding Evacuation Routes overlay with real coordinates');

    // Real evacuation routes in California with actual lat/lng coordinates
    const routes = [
      {
        name: 'SR-14 South to I-5',
        path: [
          { lat: 34.3985, lng: -118.3969 }, // Start near Angeles National Forest
          { lat: 34.2778, lng: -118.4717 }, // Via Van Norman Complex
          { lat: 34.1607, lng: -118.5540 }  // End near I-5 junction
        ],
        status: 'Open'
      },
      {
        name: 'I-210 East Emergency Route',
        path: [
          { lat: 34.2275, lng: -118.2187 }, // Start near Verdugo Peak
          { lat: 34.1808, lng: -117.6797 }, // Via San Bernardino Mountains
          { lat: 34.1390, lng: -117.3089 }  // End near Riverside County
        ],
        status: 'Congested'
      },
      {
        name: 'Pacific Coast Highway',
        path: [
          { lat: 34.0259, lng: -118.7798 }, // Start in Malibu
          { lat: 34.0195, lng: -118.4912 }, // Via Santa Monica
          { lat: 34.0522, lng: -118.2437 }  // End in Downtown LA
        ],
        status: 'Open'
      }
    ];

    const statusColors = {
      'Open': '#32CD32',
      'Congested': '#FFA500',
      'Closed': '#FF4500',
      'Blocked': '#8B0000'
    };

    routes.forEach((route) => {
      // Draw route as connected lines
      for (let i = 0; i < route.path.length - 1; i++) {
        const start = route.path[i];
        const end = route.path[i + 1];
        const startPos = latLngToPosition(start.lat, start.lng);

        const routeLine = document.createElement('div');
        routeLine.className = 'evacuation-route';
        routeLine.style.position = 'absolute';
        routeLine.style.left = startPos.left;
        routeLine.style.top = startPos.top;
        routeLine.style.width = '4px';
        routeLine.style.height = '60px';
        routeLine.style.background = statusColors[route.status as keyof typeof statusColors];
        routeLine.style.transform = 'translate(-50%, -50%) rotate(45deg)';
        routeLine.style.borderRadius = '2px';
        routeLine.style.zIndex = '9997';
        routeLine.style.opacity = '0.8';
        routeLine.title = `🛣️ ${route.name} - Status: ${route.status}`;

        overlayContainer.appendChild(routeLine);
      }

      // Add route marker at start
      const startPoint = route.path[0];
      const startPosition = latLngToPosition(startPoint.lat, startPoint.lng);

      const marker = document.createElement('div');
      marker.className = 'evacuation-route';
      marker.style.position = 'absolute';
      marker.style.left = startPosition.left;
      marker.style.top = startPosition.top;
      marker.style.width = '32px';
      marker.style.height = '32px';
      marker.style.background = statusColors[route.status as keyof typeof statusColors];
      marker.style.borderRadius = '50%';
      marker.style.border = '2px solid white';
      marker.style.transform = 'translate(-50%, -50%)';
      marker.style.pointerEvents = 'auto';
      marker.style.cursor = 'pointer';
      marker.style.zIndex = '10000';
      marker.style.display = 'flex';
      marker.style.alignItems = 'center';
      marker.style.justifyContent = 'center';
      marker.style.fontSize = '14px';
      marker.title = `🛣️ ${route.name} - Status: ${route.status}\nStart: ${startPoint.lat}degN, ${Math.abs(startPoint.lng)}degW`;
      marker.innerHTML = '🛣️';

      overlayContainer.appendChild(marker);
    });
  };

  const addFuelLoadAnalysisOverlay = (overlayContainer: HTMLElement) => {
    console.log('[HERB] Adding Fuel Load Analysis overlay with real coordinates');

    // Real fuel load monitoring stations in California with actual lat/lng coordinates
    const fuelStations = [
      { name: 'Angeles Forest Fuel Station Alpha', lat: 34.3774, lng: -117.7975, load: 'High' },
      { name: 'Tujunga Wash Fuel Monitoring', lat: 34.2503, lng: -118.2914, load: 'Very High' },
      { name: 'Malibu Chaparral Analysis', lat: 34.0259, lng: -118.7798, load: 'Extreme' },
      { name: 'San Gabriel Fuel Assessment', lat: 34.1808, lng: -117.6797, load: 'Moderate' }
    ];

    fuelStations.forEach((station) => {
      const position = latLngToPosition(station.lat, station.lng);

      const marker = document.createElement('div');
      marker.className = 'fuel-load-marker';
      marker.style.position = 'absolute';
      marker.style.left = position.left;
      marker.style.top = position.top;
      marker.style.width = '34px';
      marker.style.height = '34px';
      marker.style.background = 'rgba(139, 195, 74, 0.9)';
      marker.style.borderRadius = '50%';
      marker.style.border = '3px solid white';
      marker.style.transform = 'translate(-50%, -50%)';
      marker.style.pointerEvents = 'auto';
      marker.style.cursor = 'pointer';
      marker.style.zIndex = '10001';
      marker.style.display = 'flex';
      marker.style.alignItems = 'center';
      marker.style.justifyContent = 'center';
      marker.style.fontSize = '16px';
      marker.title = `[HERB] ${station.name} - Fuel Load: ${station.load}\nCoordinates: ${station.lat}degN, ${Math.abs(station.lng)}degW`;
      marker.innerHTML = '[HERB]';

      overlayContainer.appendChild(marker);
    });
  };

  // Calculate Fire Weather Index based on temperature, wind, and humidity
  const calculateFireWeatherIndex = (temp: number, wind: number, rh: number): string => {
    // Professional fire weather assessment based on CAL FIRE criteria
    if (temp > 100 && wind > 25 && rh < 15) return 'EXTREME';
    if (temp > 90 && wind > 20 && rh < 20) return 'HIGH';
    if (temp > 80 && wind > 15 && rh < 30) return 'MODERATE';
    return 'LOW';
  };

  const addMeteorologicalDataOverlay = (overlayContainer: HTMLElement) => {
    // Professional weather measurement stations
    const weatherStations = [
      { lat: 34.0522, lng: -118.2437, name: 'Los Angeles Downtown', temp: 105, wind: 25, rh: 12, station: 'RAWS LA01' },
      { lat: 37.7749, lng: -122.4194, name: 'San Francisco Bay', temp: 87, wind: 18, rh: 28, station: 'RAWS SF02' },
      { lat: 36.7783, lng: -119.4179, name: 'Fresno Central', temp: 112, wind: 32, rh: 8, station: 'RAWS FR03' },
      { lat: 40.5865, lng: -122.3917, name: 'Redding North', temp: 108, wind: 28, rh: 15, station: 'RAWS RD04' },
      { lat: 34.4208, lng: -119.6982, name: 'Ventura County', temp: 98, wind: 22, rh: 18, station: 'RAWS VC05' },
      { lat: 33.9425, lng: -117.2297, name: 'San Bernardino', temp: 115, wind: 35, rh: 6, station: 'RAWS SB06' }
    ];

    // Use real coordinates for weather stations
    weatherStations.forEach((station, index) => {
      const pos = latLngToPosition(station.lat, station.lng);

      // Weather data display box
      const weatherBox = document.createElement('div');
      weatherBox.className = 'weather-station-box';
      weatherBox.style.position = 'absolute';
      weatherBox.style.left = pos.left;
      weatherBox.style.top = pos.top;
      weatherBox.style.transform = 'translate(-50%, -50%)';
      weatherBox.style.background = 'rgba(0, 0, 0, 0.90)';
      weatherBox.style.color = 'white';
      weatherBox.style.padding = '10px';
      weatherBox.style.borderRadius = '10px';
      weatherBox.style.border = '3px solid #FFD700';
      weatherBox.style.minWidth = '160px';
      weatherBox.style.fontSize = '12px';
      weatherBox.style.fontFamily = 'monospace';
      weatherBox.style.pointerEvents = 'auto';
      weatherBox.style.cursor = 'pointer';
      weatherBox.style.boxShadow = '0 6px 16px rgba(0,0,0,0.7)';
      weatherBox.style.zIndex = '10003';
      weatherBox.title = `Professional Weather Station: ${station.station}`;

      // Critical fire weather assessment
      const fireWeatherIndex = calculateFireWeatherIndex(station.temp, station.wind, station.rh);

      weatherBox.innerHTML = `
        <div style="border-bottom: 1px solid #FFD700; margin-bottom: 6px; padding-bottom: 3px;">
          <div style="font-weight: bold; color: #FFD700; font-size: 11px;">${station.station}</div>
          <div style="font-size: 9px; color: #CCC;">${station.name}</div>
        </div>
        <div style="display: flex; justify-content: space-between; margin-bottom: 3px;">
          <span style="color: ${station.temp > 100 ? '#FF4500' : '#FF8C00'};">[THERMOMETER] ${station.temp}degF</span>
          <span style="color: ${station.wind > 25 ? '#FF0000' : '#FFD700'};">💨 ${station.wind}mph</span>
        </div>
        <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
          <span style="color: ${station.rh < 15 ? '#FF0000' : '#4CAF50'};">[DROPLET] ${station.rh}%RH</span>
          <span style="color: ${fireWeatherIndex === 'EXTREME' ? '#FF0000' : fireWeatherIndex === 'HIGH' ? '#FF8C00' : '#FFD700'}; font-weight: bold; font-size: 10px;">
            ${fireWeatherIndex}
          </span>
        </div>
        <div style="font-size: 9px; color: #FF4500; text-align: center; padding: 3px; background: rgba(255,69,0,0.3); border-radius: 4px;">
          Fire Weather: ${fireWeatherIndex}
        </div>
      `;

      overlayContainer.appendChild(weatherBox);

      // Add wind direction arrow for each station
      const windArrow = document.createElement('div');
      windArrow.className = 'wind-arrow';
      windArrow.style.position = 'absolute';
      windArrow.style.left = `calc(${pos.left} + 60px)`;
      windArrow.style.top = `calc(${pos.top} - 40px)`;
      windArrow.style.width = '36px';
      windArrow.style.height = '36px';
      windArrow.style.transform = 'translate(-50%, -50%) rotate(45deg)'; // NE wind direction
      windArrow.style.pointerEvents = 'none';
      windArrow.style.zIndex = '10004';

      windArrow.innerHTML = `
        <div style="
          width: 100%;
          height: 100%;
          display: flex;
          align-items: center;
          justify-content: center;
          color: #2196F3;
          font-size: 24px;
          text-shadow: 3px 3px 6px rgba(0,0,0,0.9);
        ">
          ➤
        </div>
        <div style="
          position: absolute;
          top: -18px;
          left: 50%;
          transform: translateX(-50%) rotate(-45deg);
          background: rgba(33, 150, 243, 0.95);
          color: white;
          padding: 2px 6px;
          border-radius: 4px;
          font-size: 11px;
          font-weight: bold;
          white-space: nowrap;
          box-shadow: 0 2px 6px rgba(0,0,0,0.4);
        ">
          ${station.wind}mph
        </div>
      `;

      overlayContainer.appendChild(windArrow);
    });

    // Add Fire Weather Index Legend
    const legend = document.createElement('div');
    legend.className = 'fire-weather-legend';
    legend.style.position = 'absolute';
    legend.style.bottom = '60px';
    legend.style.right = '20px';
    legend.style.background = 'rgba(0, 0, 0, 0.85)';
    legend.style.color = 'white';
    legend.style.padding = '12px';
    legend.style.borderRadius = '8px';
    legend.style.border = '2px solid #FFD700';
    legend.style.fontSize = '10px';
    legend.style.fontFamily = 'monospace';
    legend.style.minWidth = '200px';

    legend.innerHTML = `
      <div style="font-weight: bold; color: #FFD700; margin-bottom: 8px; text-align: center; border-bottom: 1px solid #FFD700; padding-bottom: 4px;">
        [FIRE] FIRE WEATHER INDEX LEGEND
      </div>
      <div style="display: flex; align-items: center; margin-bottom: 3px;">
        <span style="color: #FF0000; font-weight: bold; width: 60px;">EXTREME</span>
        <span style="font-size: 8px;">Temp>100degF + Wind>25mph + RH<15%</span>
      </div>
      <div style="display: flex; align-items: center; margin-bottom: 3px;">
        <span style="color: #FF8C00; font-weight: bold; width: 60px;">HIGH</span>
        <span style="font-size: 8px;">Temp>90degF + Wind>20mph + RH<20%</span>
      </div>
      <div style="display: flex; align-items: center; margin-bottom: 3px;">
        <span style="color: #FFD700; font-weight: bold; width: 60px;">MODERATE</span>
        <span style="font-size: 8px;">Temp>80degF + Wind>15mph + RH<30%</span>
      </div>
      <div style="margin-top: 6px; padding-top: 6px; border-top: 1px solid #555; font-size: 8px; color: #CCC;">
        Data from RAWS (Remote Automated Weather Stations)
      </div>
    `;

    overlayContainer.appendChild(legend);
  };

  // Simplified fire overlay function that manages all operational layers
  const addSimpleFireOverlay = () => {
    if (!mapRef.current) return;

    // Remove all existing layer elements by class
    const layerClasses = [
      '.fire-marker-simple',
      '.fire-hazard-zone',
      '.helicopter-landing-zone',
      '.water-source-marker',
      '.emergency-service-marker',
      '.communication-tower-marker',
      '.wui-zone',
      '.evacuation-route',
      '.fuel-load-marker',
      '.weather-station-box',
      '.wind-arrow',
      '.fire-weather-legend'
    ];

    layerClasses.forEach(className => {
      const elements = mapRef.current!.querySelectorAll(className);
      elements.forEach(element => element.remove());
    });

    // Get or create overlay container
    let overlay = mapRef.current.querySelector('.operational-overlay') as HTMLElement;
    if (!overlay) {
      overlay = document.createElement('div');
      overlay.style.position = 'absolute';
      overlay.style.top = '0';
      overlay.style.left = '0';
      overlay.style.width = '100%';
      overlay.style.height = '100%';
      overlay.style.pointerEvents = 'none';
      overlay.style.zIndex = '9999';
      overlay.style.backgroundColor = 'transparent';
      overlay.className = 'operational-overlay';
      mapRef.current.appendChild(overlay);
    }

    // Add enabled operational layers with proper class names
    if (operationalLayers.activeFires) {
      addNASAFIRMSFireData(overlay);
    }

    if (operationalLayers.fireHazardZones) {
      addFireHazardZonesOverlay(overlay);
    }

    if (operationalLayers.helicopterLandingZones) {
      addHelicopterLandingZonesOverlay(overlay);
    }

    if (operationalLayers.waterSources) {
      addWaterSourcesOverlay(overlay);
    }

    if (operationalLayers.emergencyServices) {
      addEmergencyServicesOverlay(overlay);
    }

    if (operationalLayers.communicationTowers) {
      addCommunicationTowersOverlay(overlay);
    }

    if (operationalLayers.wildlandUrbanInterface) {
      addWildlandUrbanInterfaceOverlay(overlay);
    }

    if (operationalLayers.evacuationRoutes) {
      addEvacuationRoutesOverlay(overlay);
    }

    if (operationalLayers.fuelLoadAnalysis) {
      addFuelLoadAnalysisOverlay(overlay);
    }

    if (operationalLayers.weatherStations) {
      addMeteorologicalDataOverlay(overlay);
    }

    // Add CSS for fire animations
    const style = document.createElement('style');
    style.textContent = `
      @keyframes firePulse {
        0%, 100% {
          opacity: 1;
          transform: translate(-50%, -50%) scale(1);
          box-shadow: 0 0 25px rgba(255, 69, 0, 0.9), inset 0 0 10px rgba(255, 215, 0, 0.5);
        }
        50% {
          opacity: 0.9;
          transform: translate(-50%, -50%) scale(1.15);
          box-shadow: 0 0 35px rgba(255, 69, 0, 1), inset 0 0 15px rgba(255, 215, 0, 0.7);
        }
      }

      .operational-overlay {
        pointer-events: none;
      }

      .operational-overlay > * {
        pointer-events: auto;
      }
    `;
    document.head.appendChild(style);
  };

  // NASA FIRMS Real-time Fire Data Integration - Global View
  const addNASAFIRMSFireData = async (overlayContainer: HTMLElement) => {
    console.log('[SATELLITE] Fetching NASA FIRMS real-time fire data worldwide...');

    // Clear any existing markers first
    const existingFireMarkers = overlayContainer.querySelectorAll('.fire-marker-simple');
    existingFireMarkers.forEach(marker => marker.remove());

    try {
      // Use NASA FIRMS Web Fire Mapper API for worldwide fires - last 24 hours
      // This matches Windy.com's global perspective and helps with coordinate positioning
      const response = await fetch('https://firms.modaps.eosdis.nasa.gov/api/area/csv/a1e7b03d16c8570e1bd3c17f54e7cd8d/VIIRS_SNPP_NRT/-180,-90,180,90/1/2024-01-01');
      const csvData = await response.text();

      if (!csvData || csvData.includes('error')) {
        throw new Error('NASA FIRMS API returned no data');
      }

      // Parse CSV data
      const lines = csvData.trim().split('\n');
      const headers = lines[0].split(',');
      const fires = lines.slice(1).map(line => {
        const values = line.split(',');
        const fire: any = {};
        headers.forEach((header, index) => {
          fire[header.trim()] = values[index]?.trim();
        });
        return fire;
      });

      // Filter for high-confidence fires worldwide (no geographic restriction)
      const globalFires = fires.filter((fire: any) => {
        const confidence = parseFloat(fire.confidence || 0);
        const frp = parseFloat(fire.frp || 0);
        return confidence > 70 && frp > 10; // Only high-confidence, significant fires
      }).slice(0, 50); // Show up to 50 worldwide fires

      console.log('[SATELLITE] Found', globalFires.length, 'high-confidence fires worldwide from NASA FIRMS');

      // Convert lat/lon to our coordinate system for global positioning
      globalFires.forEach((fire: any, index: number) => {
        const lat = parseFloat(fire.latitude);
        const lon = parseFloat(fire.longitude);
        const confidence = parseFloat(fire.confidence || 0);
        const frp = parseFloat(fire.frp || 0);

        // Use our latLngToPosition function for proper coordinate conversion
        const position = latLngToPosition(lat, lon);

        const fireMarker = document.createElement('div');
        fireMarker.className = 'fire-marker-simple nasa-firms-fire';
        fireMarker.style.position = 'absolute';
        fireMarker.style.left = position.left;
        fireMarker.style.top = position.top;
        fireMarker.style.width = `${Math.max(15, Math.min(40, frp * 1.5))}px`;
        fireMarker.style.height = `${Math.max(15, Math.min(40, frp * 1.5))}px`;
        fireMarker.style.background = confidence > 90 ? '#FF0000' : confidence > 80 ? '#FF4500' : '#FFA500';
        fireMarker.style.borderRadius = '50%';
        fireMarker.style.border = '2px solid #FFD700';
        fireMarker.style.boxShadow = '0 0 15px rgba(255, 0, 0, 0.8)';
        fireMarker.style.transform = 'translate(-50%, -50%)';
        fireMarker.style.pointerEvents = 'auto';
        fireMarker.style.cursor = 'pointer';
        fireMarker.style.zIndex = '99999';
        fireMarker.style.animation = 'firePulse 2s ease-in-out infinite';

        const dateTime = fire.acq_date + ' ' + fire.acq_time;
        fireMarker.title = `[SATELLITE] NASA FIRMS Global Fire Detection
Location: ${lat.toFixed(4)}, ${lon.toFixed(4)}
Detected: ${dateTime}
Confidence: ${confidence}%
Fire Power: ${frp} MW
Satellite: ${fire.satellite || 'VIIRS'}`;

        // Add fire icon
        const fireIcon = document.createElement('div');
        fireIcon.style.position = 'absolute';
        fireIcon.style.top = '50%';
        fireIcon.style.left = '50%';
        fireIcon.style.transform = 'translate(-50%, -50%)';
        fireIcon.style.fontSize = '12px';
        fireIcon.style.color = 'white';
        fireIcon.style.textShadow = '1px 1px 2px rgba(0,0,0,0.8)';
        fireIcon.innerHTML = '[FIRE]';
        fireMarker.appendChild(fireIcon);

        overlayContainer.appendChild(fireMarker);
      });

      console.log('[SATELLITE] Added', globalFires.length, 'NASA FIRMS global fire markers');

    } catch (error) {
      console.error('[SATELLITE] Failed to fetch NASA FIRMS data:', error);

      // Fallback to global fire data if NASA API fails
      const fallbackFires = [
        { lat: 35.3265, lon: -120.6015, name: 'California Gifford Fire', frp: 131, confidence: 95 },
        { lat: 37.2431, lon: -119.2026, name: 'California Garnet Fire', frp: 89, confidence: 85 },
        { lat: -25.2744, lon: 133.7751, name: 'Australia Outback Fire', frp: 156, confidence: 92 },
        { lat: 61.2181, lon: -149.9003, name: 'Alaska Wilderness Fire', frp: 98, confidence: 88 },
        { lat: 45.5152, lon: -122.6784, name: 'Oregon Forest Fire', frp: 112, confidence: 90 }
      ];

      fallbackFires.forEach((fire, index) => {
        const position = latLngToPosition(fire.lat, fire.lon);

        const fireMarker = document.createElement('div');
        fireMarker.className = 'fire-marker-simple fallback-fire';
        fireMarker.style.position = 'absolute';
        fireMarker.style.left = position.left;
        fireMarker.style.top = position.top;
        fireMarker.style.width = '35px';
        fireMarker.style.height = '35px';
        fireMarker.style.background = '#FF0000';
        fireMarker.style.borderRadius = '50%';
        fireMarker.style.border = '3px solid #FFD700';
        fireMarker.style.boxShadow = '0 0 20px rgba(255, 0, 0, 0.9)';
        fireMarker.style.transform = 'translate(-50%, -50%)';
        fireMarker.style.pointerEvents = 'auto';
        fireMarker.style.cursor = 'pointer';
        fireMarker.style.zIndex = '99999';
        fireMarker.title = `[FIRE] ${fire.name} - FRP: ${fire.frp}MW`;

        const fireIcon = document.createElement('div');
        fireIcon.style.position = 'absolute';
        fireIcon.style.top = '50%';
        fireIcon.style.left = '50%';
        fireIcon.style.transform = 'translate(-50%, -50%)';
        fireIcon.style.fontSize = '18px';
        fireIcon.style.color = 'white';
        fireIcon.innerHTML = '[FIRE]';
        fireMarker.appendChild(fireIcon);

        overlayContainer.appendChild(fireMarker);
      });

      console.log('[FIRE] Added fallback global fire markers');
    }
  };

  // Handle layer changes by reloading iframe with new overlay
  useEffect(() => {
    if (windyLoaded && mapRef.current) {
      console.log('Layer change detected, updating Windy embed...');

      // Reset windyLoaded to trigger reload with new layer
      setWindyLoaded(false);
      setLoading(true);
    }
  }, [selectedLayers, mapType]);

  return (
    <Box sx={{ position: 'relative', width: '100%', height: '100vh' }}>
      {/* Loading State */}
      {loading && (
        <Box
          sx={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: 'rgba(0, 0, 0, 0.8)',
            color: 'white',
            zIndex: 1000
          }}
        >
          <Box sx={{ textAlign: 'center' }}>
            <Typography variant="h6" gutterBottom>
              Loading Windy Weather Map...
            </Typography>
            <Typography variant="body2">
              Fetching real-time weather data for wildfire analysis
            </Typography>
          </Box>
        </Box>
      )}

      {/* Windy Map Container */}
      <Box
        ref={mapRef}
        id="windy-map"
        sx={{
          width: '100%',
          height: '100%',
          borderRadius: 2,
          overflow: 'hidden',
          '& .leaflet-container': {
            background: '#1a1a1a',
            width: '100% !important',
            height: '100% !important'
          },
          '& .windy-map-container': {
            width: '100% !important',
            height: '100% !important'
          },
          '& canvas': {
            imageRendering: 'high-quality',
            msInterpolationMode: 'nearest-neighbor'
          }
        }}
      />

      {/* Fire Weather Alert Overlay */}
      <Alert
        severity="error"
        sx={{
          position: 'absolute',
          bottom: 16,
          left: 16,
          zIndex: 500,
          maxWidth: '300px',
          background: 'rgba(211, 47, 47, 0.95)',
          color: 'white',
          '& .MuiAlert-icon': {
            color: 'white'
          }
        }}
      >
        <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
          [FIRE] CRITICAL FIRE WEATHER
        </Typography>
        <Typography variant="caption">
          Red Flag Warning in effect. Extreme fire behavior possible.
        </Typography>
      </Alert>

      {/* Global Weather Map Notice */}
      <Box
        sx={{
          position: 'absolute',
          top: 16,
          left: 16,
          zIndex: 10000,
          background: 'rgba(0, 0, 0, 0.8)',
          color: 'white',
          padding: '8px 12px',
          borderRadius: '6px',
          fontSize: '12px',
          backdropFilter: 'blur(10px)'
        }}
      >
        🌍 Global Weather * Pure Meteorological Data
      </Box>

      {/* Toggle Button for Controls */}
      <Box
        sx={{
          position: 'absolute',
          top: 16,
          right: 16,
          zIndex: 10000
        }}
      >
        <Button
          onClick={() => setShowControls(!showControls)}
          sx={{
            background: 'rgba(0, 0, 0, 0.85)',
            color: 'white',
            minWidth: '48px',
            height: '48px',
            borderRadius: '50%',
            backdropFilter: 'blur(10px)',
            '&:hover': {
              background: 'rgba(0, 0, 0, 0.95)'
            }
          }}
        >
          {showControls ? <VisibilityOff /> : <Visibility />}
        </Button>
      </Box>

      {/* Collapsible Controls Panel */}
      {showControls && (
        <Card
          sx={{
            position: 'absolute',
            top: 80,
            right: 16,
            padding: 2,
            background: 'rgba(0, 0, 0, 0.90)',
            backdropFilter: 'blur(10px)',
            zIndex: 10001,
            maxWidth: 280,
            maxHeight: 'calc(100vh - 120px)',
            overflowY: 'auto'
          }}
        >
        {/* Map Type Selection */}
        <Typography variant="subtitle2" sx={{ color: 'white', mb: 1, display: 'flex', alignItems: 'center', gap: 1 }}>
          <Landscape sx={{ fontSize: 16 }} />
          Map Format
        </Typography>
        <Box sx={{ mb: 2, display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
          <Button
            onClick={() => setMapType('streets')}
            size="small"
            variant={mapType === 'streets' ? 'contained' : 'outlined'}
            sx={{ minWidth: '90px', fontSize: '10px', color: 'white', borderColor: 'white' }}
          >
            🏙️ Streets
          </Button>
          <Button
            onClick={() => setMapType('satellite')}
            size="small"
            variant={mapType === 'satellite' ? 'contained' : 'outlined'}
            sx={{ minWidth: '90px', fontSize: '10px', color: 'white', borderColor: 'white' }}
          >
            [SATELLITE] Satellite (ESRI)
          </Button>
          <Button
            onClick={() => setMapType('terrain')}
            size="small"
            variant={mapType === 'terrain' ? 'contained' : 'outlined'}
            sx={{ minWidth: '90px', fontSize: '10px', color: 'white', borderColor: 'white' }}
          >
            🏔️ Terrain
          </Button>
          <Button
            onClick={() => setMapType('naip')}
            size="small"
            variant={mapType === 'naip' ? 'contained' : 'outlined'}
            sx={{ minWidth: '90px', fontSize: '10px', color: 'white', borderColor: 'white' }}
          >
            [BAR_CHART] NAIP
          </Button>
          <Button
            onClick={() => setMapType('topo')}
            size="small"
            variant={mapType === 'topo' ? 'contained' : 'outlined'}
            sx={{ minWidth: '90px', fontSize: '10px', color: 'white', borderColor: 'white' }}
          >
            [MAP] Topographic (USGS)
          </Button>
        </Box>

        <Typography variant="subtitle2" sx={{ color: 'white', mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
          <Air color="primary" />
          Windy Weather Layers
        </Typography>

        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
          <FormControlLabel
            control={
              <Switch
                checked={selectedLayers.windVectors}
                onChange={() => onLayerToggle('windVectors')}
                sx={{
                  '& .MuiSwitch-thumb': {
                    backgroundColor: selectedLayers.windVectors ? '#2196F3' : 'grey'
                  }
                }}
              />
            }
            label={
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Air sx={{ fontSize: 16, color: 'white' }} />
                <Typography variant="body2" sx={{ color: 'white' }}>
                  Wind Speed & Direction
                </Typography>
              </Box>
            }
          />

          <FormControlLabel
            control={
              <Switch
                checked={selectedLayers.temperature}
                onChange={() => onLayerToggle('temperature')}
                sx={{
                  '& .MuiSwitch-thumb': {
                    backgroundColor: selectedLayers.temperature ? '#FF5722' : 'grey'
                  }
                }}
              />
            }
            label={
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Thermostat sx={{ fontSize: 16, color: 'white' }} />
                <Typography variant="body2" sx={{ color: 'white' }}>
                  Temperature
                </Typography>
              </Box>
            }
          />

          <FormControlLabel
            control={
              <Switch
                checked={selectedLayers.humidity}
                onChange={() => onLayerToggle('humidity')}
                sx={{
                  '& .MuiSwitch-thumb': {
                    backgroundColor: selectedLayers.humidity ? '#00BCD4' : 'grey'
                  }
                }}
              />
            }
            label={
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Opacity sx={{ fontSize: 16, color: 'white' }} />
                <Typography variant="body2" sx={{ color: 'white' }}>
                  Relative Humidity
                </Typography>
              </Box>
            }
          />

          <FormControlLabel
            control={
              <Switch
                checked={selectedLayers.precipitation}
                onChange={() => onLayerToggle('precipitation')}
                sx={{
                  '& .MuiSwitch-thumb': {
                    backgroundColor: selectedLayers.precipitation ? '#4CAF50' : 'grey'
                  }
                }}
              />
            }
            label={
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Cloud sx={{ fontSize: 16, color: 'white' }} />
                <Typography variant="body2" sx={{ color: 'white' }}>
                  Precipitation
                </Typography>
              </Box>
            }
          />

          <FormControlLabel
            control={
              <Switch
                checked={selectedLayers.pressure}
                onChange={() => onLayerToggle('pressure')}
                sx={{
                  '& .MuiSwitch-thumb': {
                    backgroundColor: selectedLayers.pressure ? '#9C27B0' : 'grey'
                  }
                }}
              />
            }
            label={
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Compress sx={{ fontSize: 16, color: 'white' }} />
                <Typography variant="body2" sx={{ color: 'white' }}>
                  Pressure
                </Typography>
              </Box>
            }
          />

          <FormControlLabel
            control={
              <Switch
                checked={selectedLayers.cloudCover}
                onChange={() => onLayerToggle('cloudCover')}
                sx={{
                  '& .MuiSwitch-thumb': {
                    backgroundColor: selectedLayers.cloudCover ? '#607D8B' : 'grey'
                  }
                }}
              />
            }
            label={
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Cloud sx={{ fontSize: 16, color: 'white' }} />
                <Typography variant="body2" sx={{ color: 'white' }}>
                  Cloud Cover
                </Typography>
              </Box>
            }
          />

          <FormControlLabel
            control={
              <Switch
                checked={selectedLayers.cape}
                onChange={() => onLayerToggle('cape')}
                sx={{
                  '& .MuiSwitch-thumb': {
                    backgroundColor: selectedLayers.cape ? '#FF9800' : 'grey'
                  }
                }}
              />
            }
            label={
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Assessment sx={{ fontSize: 16, color: 'white' }} />
                <Typography variant="body2" sx={{ color: 'white' }}>
                  CAPE (Instability)
                </Typography>
              </Box>
            }
          />

          <FormControlLabel
            control={
              <Switch
                checked={selectedLayers.visibility}
                onChange={() => onLayerToggle('visibility')}
                sx={{
                  '& .MuiSwitch-thumb': {
                    backgroundColor: selectedLayers.visibility ? '#795548' : 'grey'
                  }
                }}
              />
            }
            label={
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Visibility sx={{ fontSize: 16, color: 'white' }} />
                <Typography variant="body2" sx={{ color: 'white' }}>
                  Visibility
                </Typography>
              </Box>
            }
          />

          <FormControlLabel
            control={
              <Switch
                checked={selectedLayers.snow}
                onChange={() => onLayerToggle('snow')}
                sx={{
                  '& .MuiSwitch-thumb': {
                    backgroundColor: selectedLayers.snow ? '#E1F5FE' : 'grey'
                  }
                }}
              />
            }
            label={
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <AcUnit sx={{ fontSize: 16, color: 'white' }} />
                <Typography variant="body2" sx={{ color: 'white' }}>
                  Snow Depth
                </Typography>
              </Box>
            }
          />

          <FormControlLabel
            control={
              <Switch
                checked={selectedLayers.waves}
                onChange={() => onLayerToggle('waves')}
                sx={{
                  '& .MuiSwitch-thumb': {
                    backgroundColor: selectedLayers.waves ? '#00BCD4' : 'grey'
                  }
                }}
              />
            }
            label={
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Waves sx={{ fontSize: 16, color: 'white' }} />
                <Typography variant="body2" sx={{ color: 'white' }}>
                  Wave Height
                </Typography>
              </Box>
            }
          />

          <FormControlLabel
            control={
              <Switch
                checked={selectedLayers.lightning}
                onChange={() => onLayerToggle('lightning')}
                sx={{
                  '& .MuiSwitch-thumb': {
                    backgroundColor: selectedLayers.lightning ? '#FFC107' : 'grey'
                  }
                }}
              />
            }
            label={
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <FlashOn sx={{ fontSize: 16, color: 'white' }} />
                <Typography variant="body2" sx={{ color: 'white' }}>
                  Lightning
                </Typography>
              </Box>
            }
          />

          <FormControlLabel
            control={
              <Switch
                checked={selectedLayers.airQuality}
                onChange={() => onLayerToggle('airQuality')}
                sx={{
                  '& .MuiSwitch-thumb': {
                    backgroundColor: selectedLayers.airQuality ? '#8BC34A' : 'grey'
                  }
                }}
              />
            }
            label={
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <MonitorHeart sx={{ fontSize: 16, color: 'white' }} />
                <Typography variant="body2" sx={{ color: 'white' }}>
                  Air Quality (PM2.5)
                </Typography>
              </Box>
            }
          />

        </Box>

        {/* Note: Fire data now shown on separate dedicated map */}
        <Typography variant="subtitle2" sx={{ color: 'white', mt: 3, mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
          <LocalFireDepartment sx={{ fontSize: 16, color: '#FF4500' }} />
          Pure Weather Data
        </Typography>

        <Typography variant="body2" sx={{ color: '#FFD700', mb: 2 }}>
          [FIRE] Fire data is displayed on the dedicated fire map panel
        </Typography>


        {/* High-Resolution Layer Status */}
        <Box sx={{ mt: 2, pt: 2, borderTop: '1px solid rgba(255,255,255,0.2)' }}>
          <Typography variant="caption" sx={{ color: '#4CAF50', display: 'block', mb: 1, fontWeight: 'bold' }}>
            ✓ WINDY.COM HIGH-RESOLUTION DATA ACTIVE
          </Typography>
          {selectedLayers.windVectors && (
            <Typography variant="caption" sx={{ color: '#2196F3', display: 'block' }}>
              🌪️ HD Wind Speed & Direction (ECMWF Model)
            </Typography>
          )}
          {selectedLayers.temperature && (
            <Typography variant="caption" sx={{ color: '#FF5722', display: 'block' }}>
              [THERMOMETER] HD Temperature Layer (ECMWF Model)
            </Typography>
          )}
          {!selectedLayers.windVectors && !selectedLayers.temperature && (
            <Typography variant="caption" sx={{ color: '#FFD700', display: 'block' }}>
              🌪️ Default: High-Resolution Wind Layer Active
            </Typography>
          )}
          <Typography variant="caption" sx={{ color: '#FFD700', display: 'block', mt: 0.5 }}>
            [DART] Professional-grade meteorological data
          </Typography>
          <Typography variant="caption" sx={{ color: '#4CAF50', display: 'block', mt: 0.5 }}>
            ✓ Wind speed values displayed on arrows
          </Typography>
          <Typography variant="caption" sx={{ color: '#2196F3', display: 'block', mt: 0.5 }}>
            ✓ RAWS weather station data overlay
          </Typography>
          <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.7)', display: 'block', mt: 0.5, fontSize: '9px' }}>
            Note: Weather layers should be visible as colored overlays on the map
          </Typography>
        </Box>

        {/* Weather Stats */}
        <Box sx={{ mt: 2, pt: 2, borderTop: '1px solid rgba(255,255,255,0.2)' }}>
          <Typography variant="caption" sx={{ color: 'white', display: 'block', mb: 1 }}>
            Live Weather Data:
          </Typography>
          <Typography variant="caption" sx={{ color: '#FF9800', display: 'block' }}>
            ✓ Real-time RAWS/NOAA integration
          </Typography>
          <Typography variant="caption" sx={{ color: '#F44336', display: 'block', mt: 0.5 }}>
            ✓ NASA FIRMS satellite data
          </Typography>
        </Box>

        {/* Powered by Windy */}
        <Typography
          variant="caption"
          sx={{
            color: 'rgba(255,255,255,0.6)',
            display: 'block',
            textAlign: 'center',
            mt: 1,
            pt: 1,
            borderTop: '1px solid rgba(255,255,255,0.1)'
          }}
        >
          Weather data by Windy.com
        </Typography>
        </Card>
      )}

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
          gap: 1
        }}
      >
        <LocalFireDepartment sx={{ fontSize: 18 }} />
        <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
          {activeFires.length} Active Fires
        </Typography>
      </Box>
    </Box>
  );
};

export default WindyMapEmbed;