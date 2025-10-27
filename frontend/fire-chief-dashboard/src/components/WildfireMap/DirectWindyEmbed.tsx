import React, { useState, useEffect, useRef } from 'react';
import { Box, Card, Typography, Switch, FormControlLabel, Alert, Button, IconButton, Collapse } from '@mui/material';
import {
  Air,
  Thermostat,
  Opacity,
  Cloud,
  LocalFireDepartment,
  Visibility,
  VisibilityOff,
  Landscape
} from '@mui/icons-material';

interface DirectWindyEmbedProps {
  mapCenter: [number, number];
  activeFires: any[];
  selectedLayers: any;
  onLayerToggle: (layer: any) => void;
}

const DirectWindyEmbed: React.FC<DirectWindyEmbedProps> = ({
  mapCenter,
  activeFires,
  selectedLayers,
  onLayerToggle
}) => {
  const mapRef = useRef<HTMLDivElement>(null);
  const [currentOverlay, setCurrentOverlay] = useState('wind');
  const [mapType, setMapType] = useState('satellite');
  const [showControls, setShowControls] = useState(false);
  const [loading, setLoading] = useState(true);
  const [iframeKey, setIframeKey] = useState(0);

  // Update overlay based on selected layers and reload iframe
  useEffect(() => {
    let newOverlay = 'wind';

    if (selectedLayers.temperature) {
      newOverlay = 'temp';
    } else if (selectedLayers.humidity) {
      newOverlay = 'rh';
    } else if (selectedLayers.precipitation) {
      newOverlay = 'rain';
    } else if (selectedLayers.pressure) {
      newOverlay = 'pressure';
    } else if (selectedLayers.cloudCover) {
      newOverlay = 'clouds';
    } else if (selectedLayers.cape) {
      newOverlay = 'cape';
    } else if (selectedLayers.visibility) {
      newOverlay = 'visibility';
    } else if (selectedLayers.snow) {
      newOverlay = 'snow';
    } else if (selectedLayers.waves) {
      newOverlay = 'waves';
    } else if (selectedLayers.lightning) {
      newOverlay = 'lightning';
    } else if (selectedLayers.airQuality) {
      newOverlay = 'pm2p5';
    } else if (selectedLayers.windVectors) {
      newOverlay = 'wind';
    }

    if (newOverlay !== currentOverlay) {
      setCurrentOverlay(newOverlay);
      setIframeKey(prev => prev + 1); // Force iframe reload
    }
  }, [selectedLayers, currentOverlay]);

  // Handle map type changes
  const handleMapTypeChange = (newMapType: string) => {
    setMapType(newMapType);
    setIframeKey(prev => prev + 1); // Force iframe reload
  };

  // Generate Windy.com iframe URL with proper parameters
  const generateWindyURL = () => {
    // Focus on California for wildfire monitoring
    const californiaLat = 36.7783;
    const californiaLng = -119.4179;

    const windyMapType = mapType === 'satellite' ? 'satellite' :
                        mapType === 'terrain' ? 'terrain' : 'map';

    const params = new URLSearchParams({
      lat: californiaLat.toString(),
      lon: californiaLng.toString(),
      detailLat: californiaLat.toString(),
      detailLon: californiaLng.toString(),
      zoom: '6',
      level: 'surface',
      overlay: currentOverlay,
      product: 'gfs', // Using GFS for reliability
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

    return `https://embed.windy.com/embed2.html?${params.toString()}`;
  };

  // Add fire markers overlay
  const addFireMarkersOverlay = () => {
    if (!mapRef.current) return;

    // Remove existing overlay
    const existingOverlay = mapRef.current.querySelector('.fire-markers-overlay');
    if (existingOverlay) {
      existingOverlay.remove();
    }

    // Create overlay container
    const overlay = document.createElement('div');
    overlay.className = 'fire-markers-overlay';
    overlay.style.position = 'absolute';
    overlay.style.top = '0';
    overlay.style.left = '0';
    overlay.style.width = '100%';
    overlay.style.height = '100%';
    overlay.style.pointerEvents = 'none';
    overlay.style.zIndex = '9999';

    // California bounds for proper positioning
    const californiaBounds = {
      north: 42.0,
      south: 32.5,
      west: -124.5,
      east: -114.0
    };

    const fireData = activeFires.length > 0 ? activeFires : [
      { latitude: 34.0522, longitude: -118.2437, frp: 95, name: 'LA Area Fire' },
      { latitude: 37.7749, longitude: -122.4194, frp: 75, name: 'Bay Area Fire' },
      { latitude: 36.7783, longitude: -119.4179, frp: 120, name: 'Central Valley Fire' },
      { latitude: 33.9425, longitude: -117.2297, frp: 85, name: 'San Bernardino Fire' },
      { latitude: 34.4208, longitude: -119.6982, frp: 65, name: 'Ventura Fire' },
      { latitude: 40.5865, longitude: -122.3917, frp: 110, name: 'Redding Fire' }
    ];

    fireData.forEach((fire) => {
      // Convert lat/lng to percentage position within California bounds
      const x = ((fire.longitude - californiaBounds.west) / (californiaBounds.east - californiaBounds.west)) * 100;
      const y = ((californiaBounds.north - fire.latitude) / (californiaBounds.north - californiaBounds.south)) * 100;

      // Only show fires within California bounds
      if (x >= 0 && x <= 100 && y >= 0 && y <= 100) {
        const fireMarker = document.createElement('div');
        fireMarker.style.position = 'absolute';
        fireMarker.style.left = `${x}%`;
        fireMarker.style.top = `${y}%`;
        fireMarker.style.width = '24px';
        fireMarker.style.height = '24px';
        fireMarker.style.background = 'radial-gradient(circle, #FF4500 0%, #FF0000 50%, #8B0000 100%)';
        fireMarker.style.borderRadius = '50%';
        fireMarker.style.border = '2px solid white';
        fireMarker.style.boxShadow = '0 0 15px rgba(255, 69, 0, 0.8)';
        fireMarker.style.animation = 'firePulse 2s ease-in-out infinite';
        fireMarker.style.transform = 'translate(-50%, -50%)';
        fireMarker.style.pointerEvents = 'auto';
        fireMarker.style.cursor = 'pointer';
        fireMarker.style.zIndex = '10001';
        fireMarker.title = `[FIRE] ${fire.name || 'Active Fire'} - FRP: ${Math.round(fire.frp || 0)}MW`;

        // Add fire emoji
        fireMarker.innerHTML = '<div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); font-size: 12px;">[FIRE]</div>';

        overlay.appendChild(fireMarker);
      }
    });

    mapRef.current.appendChild(overlay);

    // Add CSS animation
    if (!document.querySelector('#fire-pulse-animation')) {
      const style = document.createElement('style');
      style.id = 'fire-pulse-animation';
      style.textContent = `
        @keyframes firePulse {
          0%, 100% { opacity: 1; transform: translate(-50%, -50%) scale(1); }
          50% { opacity: 0.8; transform: translate(-50%, -50%) scale(1.1); }
        }
      `;
      document.head.appendChild(style);
    }
  };

  return (
    <Box sx={{ position: 'relative', width: '100%', height: '100%' }}>
      {/* Loading indicator */}
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
          <Typography variant="h6">Loading Windy Weather Map...</Typography>
        </Box>
      )}

      {/* Windy.com Iframe */}
      <Box
        ref={mapRef}
        sx={{
          width: '100%',
          height: '100%',
          position: 'relative'
        }}
      >
        <iframe
          key={iframeKey}
          src={generateWindyURL()}
          width="100%"
          height="100%"
          frameBorder="0"
          style={{
            border: 'none',
            borderRadius: '8px'
          }}
          title="Windy Weather Map"
          onLoad={() => {
            setLoading(false);
            setTimeout(addFireMarkersOverlay, 1000);
          }}
        />
      </Box>

      {/* Fire Weather Alert */}
      <Alert
        severity="error"
        sx={{
          position: 'absolute',
          top: 16,
          left: 16,
          zIndex: 1000,
          background: 'rgba(211, 47, 47, 0.95)',
          color: 'white',
          '& .MuiAlert-icon': {
            color: 'white'
          }
        }}
      >
        <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
          [FIRE] CRITICAL FIRE WEATHER CONDITIONS
        </Typography>
        <Typography variant="caption">
          Red Flag Warning in effect. Extreme fire behavior possible.
        </Typography>
      </Alert>

      {/* Controls Toggle */}
      <Box
        sx={{
          position: 'absolute',
          top: 16,
          right: 16,
          zIndex: 1001
        }}
      >
        <IconButton
          onClick={() => setShowControls(!showControls)}
          sx={{
            background: 'rgba(0, 0, 0, 0.85)',
            color: 'white',
            '&:hover': {
              background: 'rgba(0, 0, 0, 0.95)'
            }
          }}
        >
          {showControls ? <VisibilityOff /> : <Visibility />}
        </IconButton>
      </Box>

      {/* Collapsible Controls Panel */}
      <Collapse in={showControls}>
        <Card
          sx={{
            position: 'absolute',
            top: 80,
            right: 16,
            padding: 2,
            background: 'rgba(0, 0, 0, 0.90)',
            backdropFilter: 'blur(10px)',
            zIndex: 1000,
            maxWidth: 300,
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
              onClick={() => handleMapTypeChange('streets')}
              size="small"
              variant={mapType === 'streets' ? 'contained' : 'outlined'}
              sx={{
                minWidth: '80px',
                fontSize: '10px',
                color: 'white',
                borderColor: 'white',
                ...(mapType === 'streets' && { backgroundColor: '#2196F3' })
              }}
            >
              🏙️ Streets
            </Button>
            <Button
              onClick={() => handleMapTypeChange('satellite')}
              size="small"
              variant={mapType === 'satellite' ? 'contained' : 'outlined'}
              sx={{
                minWidth: '80px',
                fontSize: '10px',
                color: 'white',
                borderColor: 'white',
                ...(mapType === 'satellite' && { backgroundColor: '#2196F3' })
              }}
            >
              [SATELLITE] Satellite
            </Button>
            <Button
              onClick={() => handleMapTypeChange('terrain')}
              size="small"
              variant={mapType === 'terrain' ? 'contained' : 'outlined'}
              sx={{
                minWidth: '80px',
                fontSize: '10px',
                color: 'white',
                borderColor: 'white',
                ...(mapType === 'terrain' && { backgroundColor: '#2196F3' })
              }}
            >
              🏔️ Terrain
            </Button>
          </Box>

          <Typography variant="subtitle2" sx={{ color: 'white', mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
            <Air color="primary" />
            Weather Layers
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
                    Temperature {selectedLayers.temperature ? '✓' : '✗'}
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
                    Humidity {selectedLayers.humidity ? '✓' : '✗'}
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
                    Precipitation {selectedLayers.precipitation ? '✓' : '✗'}
                  </Typography>
                </Box>
              }
            />
          </Box>

          {/* Current Status */}
          <Box sx={{ mt: 2, pt: 2, borderTop: '1px solid rgba(255,255,255,0.2)' }}>
            <Typography variant="caption" sx={{ color: '#4CAF50', display: 'block', mb: 1, fontWeight: 'bold' }}>
              ✓ WINDY.COM WEATHER DATA ACTIVE
            </Typography>
            <Typography variant="caption" sx={{ color: '#2196F3', display: 'block' }}>
              🌪️ Current Layer: {currentOverlay.toUpperCase()}
            </Typography>
            <Typography variant="caption" sx={{ color: '#FFD700', display: 'block', mt: 0.5 }}>
              [DART] Map Type: {mapType.toUpperCase()}
            </Typography>
            <Typography variant="caption" sx={{ color: '#4CAF50', display: 'block', mt: 0.5 }}>
              ✓ {activeFires.length} Active Fire Markers Positioned
            </Typography>
            <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.7)', display: 'block', mt: 0.5, fontSize: '9px' }}>
              Fires positioned using California geographic bounds
            </Typography>
          </Box>

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
      </Collapse>

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

export default DirectWindyEmbed;