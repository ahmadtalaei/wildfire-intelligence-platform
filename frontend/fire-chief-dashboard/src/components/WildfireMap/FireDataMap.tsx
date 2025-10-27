import React, { useEffect, useRef, useState } from 'react';
import { Box, Typography, Button, Card } from '@mui/material';
import { LocalFireDepartment, Refresh } from '@mui/icons-material';

interface FireDataMapProps {
  activeFires: any[];
}

const FireDataMap: React.FC<FireDataMapProps> = ({ activeFires }) => {
  const mapRef = useRef<HTMLDivElement>(null);
  const [loading, setLoading] = useState(true);
  const [fireCount, setFireCount] = useState(0);

  // US bounds for nationwide fire data
  const US_BOUNDS = {
    north: 49.0,    // Canadian border
    south: 25.0,    // Southern Florida/Texas
    east: -66.0,    // Eastern seaboard
    west: -125.0    // Pacific coast
  };

  // Convert lat/lng to screen percentage for US map
  const latLngToPosition = (lat: number, lng: number) => {
    const latNormalized = (lat - US_BOUNDS.south) / (US_BOUNDS.north - US_BOUNDS.south);
    const lngNormalized = (lng - US_BOUNDS.west) / (US_BOUNDS.east - US_BOUNDS.west);

    const topPercent = (1 - latNormalized) * 100;
    const leftPercent = lngNormalized * 100;

    return {
      top: `${Math.max(0, Math.min(100, topPercent))}%`,
      left: `${Math.max(0, Math.min(100, leftPercent))}%`
    };
  };

  // Fetch NASA FIRMS fire data nationwide
  const fetchNationwideFireData = async () => {
    console.log('[FIRE] Fetching nationwide fire data from NASA FIRMS...');
    setLoading(true);

    try {
      // Use environment variable for NASA FIRMS API key
      const firmsApiKey = process.env.REACT_APP_FIRMS_MAP_KEY;
      if (!firmsApiKey) {
        throw new Error('NASA FIRMS API key not configured');
      }

      // Fetch real-time US fire data from NASA FIRMS (last 24 hours)
      const today = new Date();
      const yesterday = new Date(today);
      yesterday.setDate(yesterday.getDate() - 1);
      const dateStr = yesterday.toISOString().split('T')[0];

      console.log(`[FIRE] Fetching NASA FIRMS data for ${dateStr}...`);
      const response = await fetch(`https://firms.modaps.eosdis.nasa.gov/api/country/csv/${firmsApiKey}/VIIRS_SNPP_NRT/USA/1/${dateStr}`);
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

      // Filter for high-confidence fires
      const nationalFires = fires.filter((fire: any) => {
        const lat = parseFloat(fire.latitude);
        const lon = parseFloat(fire.longitude);
        const confidence = parseFloat(fire.confidence || 0);
        const frp = parseFloat(fire.frp || 0);

        // Filter for high-confidence fires within US bounds
        return confidence > 75 &&
               frp > 5 &&
               lat >= US_BOUNDS.south &&
               lat <= US_BOUNDS.north &&
               lon >= US_BOUNDS.west &&
               lon <= US_BOUNDS.east &&
               !isNaN(lat) && !isNaN(lon) &&
               lat !== 0 && lon !== 0; // Filter out invalid coordinates
      }).slice(0, 100); // Show up to 100 fires

      setFireCount(nationalFires.length);
      displayFireMarkers(nationalFires);

    } catch (error) {
      console.error('[FIRE] Failed to fetch fire data:', error);
      displayFallbackFires();
    }

    setLoading(false);
  };

  // Add operational infrastructure markers
  const addInfrastructureMarkers = () => {
    if (!mapRef.current) return;

    // Clear existing infrastructure markers
    const existingInfra = mapRef.current.querySelectorAll('.infrastructure-marker');
    existingInfra.forEach(marker => marker.remove());

    // Sample operational infrastructure data
    const infrastructure = [
      { type: 'hospital', lat: 34.0522, lng: -118.2437, name: 'LA Medical Center' },
      { type: 'fire_station', lat: 37.7749, lng: -122.4194, name: 'SF Fire Station 1' },
      { type: 'helicopter', lat: 39.7392, lng: -104.9903, name: 'Denver Helipad' },
      { type: 'water', lat: 40.7128, lng: -74.0060, name: 'Water Source' },
      { type: 'communication', lat: 41.8781, lng: -87.6298, name: 'Radio Tower' },
      { type: 'evacuation', lat: 29.7604, lng: -95.3698, name: 'Evacuation Route' },
      { type: 'weather', lat: 33.4484, lng: -112.0740, name: 'Weather Station' },
      { type: 'fuel', lat: 45.5152, lng: -122.6784, name: 'Fuel Analysis Zone' },
    ];

    infrastructure.forEach((infra) => {
      const position = latLngToPosition(infra.lat, infra.lng);

      let icon = '🏥', color = '#e74c3c', bgColor = 'rgba(231, 76, 60, 0.1)';
      switch (infra.type) {
        case 'fire_station': icon = '🚒'; color = '#e74c3c'; break;
        case 'helicopter': icon = '🚁'; color = '#3498db'; break;
        case 'water': icon = '💧'; color = '#3498db'; break;
        case 'communication': icon = '📡'; color = '#9b59b6'; break;
        case 'evacuation': icon = '🛣️'; color = '#f39c12'; break;
        case 'weather': icon = '🌡️'; color = '#27ae60'; break;
        case 'fuel': icon = '🌿'; color = '#2ecc71'; break;
      }

      const infraMarker = document.createElement('div');
      infraMarker.className = 'infrastructure-marker';
      infraMarker.style.position = 'absolute';
      infraMarker.style.left = position.left;
      infraMarker.style.top = position.top;
      infraMarker.style.width = '24px';
      infraMarker.style.height = '24px';
      infraMarker.style.fontSize = '16px';
      infraMarker.style.display = 'flex';
      infraMarker.style.alignItems = 'center';
      infraMarker.style.justifyContent = 'center';
      infraMarker.style.background = bgColor;
      infraMarker.style.border = `2px solid ${color}`;
      infraMarker.style.borderRadius = '50%';
      infraMarker.style.cursor = 'pointer';
      infraMarker.style.zIndex = '999';
      infraMarker.style.transform = 'translate(-50%, -50%)';
      infraMarker.innerHTML = icon;
      infraMarker.title = `${infra.name}\nType: ${infra.type}\nLocation: ${infra.lat.toFixed(4)}, ${infra.lng.toFixed(4)}`;

      mapRef.current!.appendChild(infraMarker);
    });
  };

  // Display fire markers on the map
  const displayFireMarkers = (fires: any[]) => {
    if (!mapRef.current) return;

    // Clear existing markers
    const existingMarkers = mapRef.current.querySelectorAll('.fire-marker');
    existingMarkers.forEach(marker => marker.remove());

    // Add infrastructure markers
    addInfrastructureMarkers();

    fires.forEach((fire, index) => {
      const lat = parseFloat(fire.latitude);
      const lon = parseFloat(fire.longitude);
      const confidence = parseFloat(fire.confidence || 0);
      const frp = parseFloat(fire.frp || 0);

      // Check if fire is within US bounds
      if (lat < US_BOUNDS.south || lat > US_BOUNDS.north ||
          lon < US_BOUNDS.west || lon > US_BOUNDS.east) {
        return;
      }

      const position = latLngToPosition(lat, lon);

      const fireMarker = document.createElement('div');
      fireMarker.className = 'fire-marker';
      fireMarker.style.position = 'absolute';
      fireMarker.style.left = position.left;
      fireMarker.style.top = position.top;
      fireMarker.style.width = `${Math.max(8, Math.min(30, frp * 1.2))}px`;
      fireMarker.style.height = `${Math.max(8, Math.min(30, frp * 1.2))}px`;
      fireMarker.style.background = confidence > 90 ? '#FF0000' : confidence > 80 ? '#FF4500' : '#FFA500';
      fireMarker.style.borderRadius = '50%';
      fireMarker.style.border = '2px solid #FFD700';
      fireMarker.style.boxShadow = '0 0 10px rgba(255, 0, 0, 0.8)';
      fireMarker.style.transform = 'translate(-50%, -50%)';
      fireMarker.style.cursor = 'pointer';
      fireMarker.style.zIndex = '1000';
      fireMarker.style.animation = 'firePulse 2s ease-in-out infinite';

      const dateTime = fire.acq_date + ' ' + fire.acq_time;
      fireMarker.title = `[FIRE] Fire Detection
Location: ${lat.toFixed(4)}, ${lon.toFixed(4)}
Detected: ${dateTime}
Confidence: ${confidence}%
Fire Power: ${frp} MW
Satellite: ${fire.satellite || 'VIIRS'}`;

      mapRef.current!.appendChild(fireMarker);
    });

    console.log(`[FIRE] Displayed ${fires.length} fire markers nationwide`);
  };

  // Display fallback fire data if API fails
  const displayFallbackFires = () => {
    console.log('[FIRE] Using fallback - loading fire incidents from backend...');

    // Try to fetch from our backend first
    fetch('/api/fire-incidents/active')
      .then(response => {
        if (response.ok) {
          return response.json();
        }
        throw new Error('Backend not available');
      })
      .then(fireIncidents => {
        if (fireIncidents.length > 0) {
          const backendFires = fireIncidents.map((incident: any) => ({
            latitude: parseFloat(incident.latitude),
            longitude: parseFloat(incident.longitude),
            confidence: parseFloat(incident.confidence || 0.8) * 100,
            frp: incident.frp || 30,
            acq_date: incident.created_at ? incident.created_at.split('T')[0] : new Date().toISOString().split('T')[0],
            acq_time: incident.created_at ? incident.created_at.split('T')[1].split(':').slice(0,2).join('') : '0000',
            satellite: 'DATABASE'
          })).filter((fire: any) =>
            !isNaN(fire.latitude) && !isNaN(fire.longitude) &&
            fire.latitude >= US_BOUNDS.south &&
            fire.latitude <= US_BOUNDS.north &&
            fire.longitude >= US_BOUNDS.west &&
            fire.longitude <= US_BOUNDS.east
          );

          console.log(`[FIRE] Loaded ${backendFires.length} fire incidents from database`);
          setFireCount(backendFires.length);
          displayFireMarkers(backendFires);
        } else {
          // If no backend data, show empty state
          setFireCount(0);
        }
      })
      .catch(() => {
        // If all fails, show empty state
        console.log('[FIRE] No fire data sources available');
        setFireCount(0);
      });
  };

  useEffect(() => {
    fetchNationwideFireData();
  }, []);

  const handleRefresh = () => {
    fetchNationwideFireData();
  };

  return (
    <Box sx={{ position: 'relative', width: '100%', height: '100%', background: '#f5f5f5' }}>
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
            zIndex: 2000
          }}
        >
          <Typography variant="h6">Loading Nationwide Fire Data...</Typography>
        </Box>
      )}

      {/* Map Container with US background */}
      <Box
        ref={mapRef}
        sx={{
          width: '100%',
          height: '100%',
          position: 'relative',
          background: 'linear-gradient(135deg, #e8f5e8 0%, #d4f1d4 50%, #c0edc0 100%)',
          border: '2px solid #333',
          borderRadius: 2,
          overflow: 'hidden'
        }}
      >
        {/* Simple US Map Outline */}
        <Box
          sx={{
            position: 'absolute',
            top: '10%',
            left: '10%',
            width: '80%',
            height: '70%',
            border: '3px solid #333',
            borderRadius: '20px 10px 30px 15px',
            background: 'rgba(255, 255, 255, 0.3)',
            '&::before': {
              content: '""',
              position: 'absolute',
              top: '20%',
              right: '-15%',
              width: '20%',
              height: '40%',
              border: '3px solid #333',
              borderRadius: '5px',
              background: 'rgba(255, 255, 255, 0.3)'
            }
          }}
        />

        {/* State Labels */}
        <Typography sx={{ position: 'absolute', top: '25%', left: '15%', fontSize: '10px', fontWeight: 'bold', color: '#666' }}>CA</Typography>
        <Typography sx={{ position: 'absolute', top: '35%', left: '45%', fontSize: '10px', fontWeight: 'bold', color: '#666' }}>TX</Typography>
        <Typography sx={{ position: 'absolute', top: '45%', left: '75%', fontSize: '10px', fontWeight: 'bold', color: '#666' }}>FL</Typography>
        <Typography sx={{ position: 'absolute', top: '15%', left: '55%', fontSize: '10px', fontWeight: 'bold', color: '#666' }}>CO</Typography>
        <Typography sx={{ position: 'absolute', top: '20%', left: '85%', fontSize: '10px', fontWeight: 'bold', color: '#666' }}>NY</Typography>
      </Box>

      {/* Fire Count Badge */}
      <Box
        sx={{
          position: 'absolute',
          top: 16,
          left: 16,
          background: 'rgba(255, 69, 0, 0.9)',
          color: 'white',
          padding: '8px 16px',
          borderRadius: 20,
          zIndex: 1500,
          display: 'flex',
          alignItems: 'center',
          gap: 1
        }}
      >
        <LocalFireDepartment sx={{ fontSize: 18 }} />
        <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
          {fireCount} Active Fires Nationwide
        </Typography>
      </Box>

      {/* Refresh Button */}
      <Button
        onClick={handleRefresh}
        sx={{
          position: 'absolute',
          top: 16,
          right: 16,
          background: 'rgba(0, 0, 0, 0.8)',
          color: 'white',
          minWidth: '48px',
          height: '48px',
          borderRadius: '50%',
          zIndex: 1500,
          '&:hover': {
            background: 'rgba(0, 0, 0, 0.9)'
          }
        }}
      >
        <Refresh />
      </Button>

      {/* Legend */}
      <Card
        sx={{
          position: 'absolute',
          bottom: 16,
          right: 16,
          padding: 2,
          background: 'rgba(0, 0, 0, 0.9)',
          color: 'white',
          zIndex: 1500,
          minWidth: 280,
          maxHeight: '70%',
          overflowY: 'auto'
        }}
      >
        <Typography variant="subtitle2" sx={{ mb: 1, color: '#FFD700', fontWeight: 'bold' }}>
          🔥 Operational Intelligence Map
        </Typography>

        {/* Fire Legend */}
        <Typography variant="caption" sx={{ display: 'block', mt: 1, mb: 0.5, color: '#FF6B6B', fontWeight: 'bold' }}>
          Fire Intensity:
        </Typography>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.3, ml: 1 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Box sx={{ width: 10, height: 10, borderRadius: '50%', background: '#FF0000' }} />
            <Typography variant="caption" sx={{ fontSize: '10px' }}>High Confidence (&gt;90%)</Typography>
          </Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Box sx={{ width: 10, height: 10, borderRadius: '50%', background: '#FF4500' }} />
            <Typography variant="caption" sx={{ fontSize: '10px' }}>Medium (80-90%)</Typography>
          </Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Box sx={{ width: 10, height: 10, borderRadius: '50%', background: '#FFA500' }} />
            <Typography variant="caption" sx={{ fontSize: '10px' }}>Lower (&lt;80%)</Typography>
          </Box>
        </Box>

        {/* Infrastructure Legend */}
        <Typography variant="caption" sx={{ display: 'block', mt: 1, mb: 0.5, color: '#4ECDC4', fontWeight: 'bold' }}>
          Operational Overlays:
        </Typography>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.3, ml: 1 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <span style={{ fontSize: '12px' }}>🏥</span>
            <Typography variant="caption" sx={{ fontSize: '10px' }}>Emergency Services</Typography>
          </Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <span style={{ fontSize: '12px' }}>🚒</span>
            <Typography variant="caption" sx={{ fontSize: '10px' }}>Fire Stations</Typography>
          </Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <span style={{ fontSize: '12px' }}>🚁</span>
            <Typography variant="caption" sx={{ fontSize: '10px' }}>Helicopter Landing Zones</Typography>
          </Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <span style={{ fontSize: '12px' }}>💧</span>
            <Typography variant="caption" sx={{ fontSize: '10px' }}>Water Sources</Typography>
          </Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <span style={{ fontSize: '12px' }}>📡</span>
            <Typography variant="caption" sx={{ fontSize: '10px' }}>Communication Towers</Typography>
          </Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <span style={{ fontSize: '12px' }}>🛣️</span>
            <Typography variant="caption" sx={{ fontSize: '10px' }}>Evacuation Routes</Typography>
          </Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <span style={{ fontSize: '12px' }}>🌡️</span>
            <Typography variant="caption" sx={{ fontSize: '10px' }}>Weather Station Data</Typography>
          </Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <span style={{ fontSize: '12px' }}>🌿</span>
            <Typography variant="caption" sx={{ fontSize: '10px' }}>Fuel Load Analysis</Typography>
          </Box>
        </Box>

        <Typography variant="caption" sx={{ display: 'block', mt: 1, color: '#FFD700', fontSize: '9px' }}>
          Click markers for detailed information
        </Typography>
      </Card>

      {/* Fire Pulse Animation */}
      <style>
        {`
          @keyframes firePulse {
            0%, 100% {
              opacity: 1;
              transform: translate(-50%, -50%) scale(1);
            }
            50% {
              opacity: 0.7;
              transform: translate(-50%, -50%) scale(1.2);
            }
          }
        `}
      </style>
    </Box>
  );
};

export default FireDataMap;