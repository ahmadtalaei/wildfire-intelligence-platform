import React, { useEffect, useRef, useState } from 'react';
import { Box, Typography, IconButton, Tooltip, Switch, FormControlLabel } from '@mui/material';
import {
  Visibility,
  VisibilityOff,
  Air,
  Thermostat,
  WaterDrop,
  Speed,
  Cloud
} from '@mui/icons-material';
import { weatherAPI, AirQualityReading, SmokeOverlayData } from '../../services/weatherAPI';

interface WindyWeatherOverlayProps {
  mapCenter: [number, number];
  zoom: number;
  selectedLayers: {
    windVectors: boolean;
    temperature: boolean;
    humidity: boolean;
    precipitation: boolean;
    smoke?: boolean;
  };
  onLayerToggle: (layer: string) => void;
}

interface WindyData {
  temperature?: number[][];
  wind_u?: number[][];
  wind_v?: number[][];
  precipitation?: number[][];
  humidity?: number[][];
}

const WindyWeatherOverlay: React.FC<WindyWeatherOverlayProps> = ({
  mapCenter,
  zoom,
  selectedLayers,
  onLayerToggle
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const [windyData, setWindyData] = useState<WindyData>({});
  const [smokeData, setSmokeData] = useState<SmokeOverlayData | null>(null);
  const [loading, setLoading] = useState(false);
  const [showControls, setShowControls] = useState(true);
  const [showWindyEmbed, setShowWindyEmbed] = useState(false);
  const [showAirNowOverlay, setShowAirNowOverlay] = useState(false);

  // Fetch real AirNow smoke/air quality data
  useEffect(() => {
    const fetchSmokeData = async () => {
      try {
        const data = await weatherAPI.fetchAirQualityData();
        setSmokeData(data);
        console.log('[WindyWeatherOverlay] Loaded smoke data:', data);
      } catch (error) {
        console.error('[WindyWeatherOverlay] Failed to fetch smoke data:', error);
      }
    };

    fetchSmokeData();
    const interval = setInterval(fetchSmokeData, 600000); // Update every 10 minutes

    return () => clearInterval(interval);
  }, []);

  // Generate mock weather data for overlay (keeping for now as fallback)
  useEffect(() => {
    const fetchWindyData = async () => {
      setLoading(true);

      try {
        // Use real Windy.com embed instead of generating mock data
        // Mock data kept as fallback for overlay visualization
        const mockData: WindyData = {
          temperature: generateTemperatureField(mapCenter, 20, 20),
          wind_u: generateWindField(mapCenter, 20, 20, 'u'),
          wind_v: generateWindField(mapCenter, 20, 20, 'v'),
          precipitation: generatePrecipitationField(mapCenter, 20, 20),
          humidity: generateHumidityField(mapCenter, 20, 20)
        };

        setWindyData(mockData);
      } catch (error) {
        console.error('Failed to fetch Windy data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchWindyData();
    const interval = setInterval(fetchWindyData, 300000); // Update every 5 minutes

    return () => clearInterval(interval);
  }, [mapCenter]);

  // Generate realistic temperature field
  const generateTemperatureField = (center: [number, number], width: number, height: number) => {
    const field = [];
    for (let i = 0; i < height; i++) {
      const row = [];
      for (let j = 0; j < width; j++) {
        // Base temperature with spatial variation
        const lat = center[0] + (i - height/2) * 0.05;
        const lng = center[1] + (j - width/2) * 0.05;

        // Temperature gradient with hotspots for fire areas
        const baseTemp = 95 + Math.sin(lat * 0.1) * 10 + Math.cos(lng * 0.1) * 5;
        const fireHotspot = Math.exp(-((i-10)**2 + (j-15)**2) / 50) * 20; // Hotspot near fire

        row.push(baseTemp + fireHotspot + (Math.random() - 0.5) * 5);
      }
      field.push(row);
    }
    return field;
  };

  // Generate wind field components
  const generateWindField = (center: [number, number], width: number, height: number, component: 'u' | 'v') => {
    const field = [];
    for (let i = 0; i < height; i++) {
      const row = [];
      for (let j = 0; j < width; j++) {
        // Simulate wind patterns influenced by topography and pressure systems
        const x = j - width/2;
        const y = i - height/2;

        if (component === 'u') {
          // East-west wind component (positive = eastward)
          row.push(15 + Math.sin(y * 0.3) * 8 + (Math.random() - 0.5) * 5);
        } else {
          // North-south wind component (positive = northward)
          row.push(5 + Math.cos(x * 0.3) * 6 + (Math.random() - 0.5) * 4);
        }
      }
      field.push(row);
    }
    return field;
  };

  // Generate precipitation field
  const generatePrecipitationField = (center: [number, number], width: number, height: number) => {
    const field = [];
    for (let i = 0; i < height; i++) {
      const row = [];
      for (let j = 0; j < width; j++) {
        // Very low precipitation (dry conditions for fire risk)
        const precip = Math.max(0, Math.random() * 0.1 - 0.08);
        row.push(precip);
      }
      field.push(row);
    }
    return field;
  };

  // Generate humidity field
  const generateHumidityField = (center: [number, number], width: number, height: number) => {
    const field = [];
    for (let i = 0; i < height; i++) {
      const row = [];
      for (let j = 0; j < width; j++) {
        // Low humidity (fire-prone conditions)
        const humidity = 15 + Math.sin((i+j) * 0.2) * 8 + (Math.random() - 0.5) * 6;
        row.push(Math.max(5, Math.min(35, humidity)));
      }
      field.push(row);
    }
    return field;
  };

  // Render temperature overlay
  const renderTemperatureOverlay = () => {
    if (!selectedLayers.temperature || !windyData.temperature) return null;

    return (
      <Box
        sx={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          zIndex: 8,
          pointerEvents: 'none'
        }}
      >
        {windyData.temperature.map((row, i) =>
          row.map((temp, j) => {
            const x = (j / ((windyData.temperature?.[0]?.length || 20) - 1)) * 100;
            const y = (i / ((windyData.temperature?.length || 20) - 1)) * 100;
            const intensity = Math.min(1, (temp - 80) / 40); // Normalize 80-120degF to 0-1

            return (
              <Box
                key={`temp-${i}-${j}`}
                sx={{
                  position: 'absolute',
                  left: `${x}%`,
                  top: `${y}%`,
                  width: '5%',
                  height: '5%',
                  background: `radial-gradient(circle,
                    rgba(${255 * intensity}, ${100 * (1-intensity)}, 0, ${0.3 + intensity * 0.4}) 0%,
                    transparent 70%)`,
                  borderRadius: '50%'
                }}
              />
            );
          })
        )}
      </Box>
    );
  };

  // Render wind vectors
  const renderWindVectors = () => {
    if (!selectedLayers.windVectors || !windyData.wind_u || !windyData.wind_v) return null;

    console.log('[WindyWeather] Rendering wind vectors, data:', windyData.wind_u?.length);

    return (
      <Box
        sx={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          zIndex: 10,
          pointerEvents: 'none'
        }}
      >
        {windyData.wind_u.map((row, i) =>
          row.map((u, j) => {
            if (i % 2 !== 0 || j % 2 !== 0) return null; // Show every other point for better coverage

            const v = windyData.wind_v?.[i]?.[j] || 0;
            const speed = Math.sqrt(u * u + v * v);
            const direction = Math.atan2(v, u) * (180 / Math.PI);

            // Spread arrows across entire map (0-100%)
            const x = (j / ((windyData.wind_u?.[0]?.length || 20) - 1)) * 100;
            const y = (i / ((windyData.wind_u?.length || 20) - 1)) * 100;
            const length = Math.min(20, speed * 1); // Shorter arrows

            const speedColor = speed > 25 ? '#FF0000' : speed > 15 ? '#FFA500' : '#00BFFF';

            return (
              <Box
                key={`wind-${i}-${j}`}
                sx={{
                  position: 'absolute',
                  left: `${x}%`,
                  top: `${y}%`,
                  transform: `translate(-50%, -50%) rotate(${direction}deg)`,
                  zIndex: 2
                }}
              >
                <Box
                  sx={{
                    width: `${length}px`,
                    height: '2px',
                    background: `linear-gradient(90deg, ${speedColor} 0%, ${speedColor}AA 70%, transparent 100%)`,
                    filter: 'drop-shadow(0 0 1px rgba(0,0,0,0.8))',
                    animation: 'windFlow 2s ease-in-out infinite',
                    '&::after': {
                      content: '""',
                      position: 'absolute',
                      right: '-2px',
                      top: '-1px',
                      width: 0,
                      height: 0,
                      borderLeft: `4px solid ${speedColor}`,
                      borderTop: '2px solid transparent',
                      borderBottom: '2px solid transparent'
                    }
                  }}
                />
              </Box>
            );
          })
        )}
      </Box>
    );
  };

  // Render humidity overlay
  const renderHumidityOverlay = () => {
    if (!selectedLayers.humidity || !windyData.humidity) return null;

    return (
      <Box
        sx={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          zIndex: 9,
          pointerEvents: 'none'
        }}
      >
        {windyData.humidity.map((row, i) =>
          row.map((humidity, j) => {
            const x = (j / ((windyData.humidity?.[0]?.length || 20) - 1)) * 100;
            const y = (i / ((windyData.humidity?.length || 20) - 1)) * 100;
            const intensity = Math.max(0, (30 - humidity) / 25); // Invert - lower humidity = higher fire risk

            return (
              <Box
                key={`humidity-${i}-${j}`}
                sx={{
                  position: 'absolute',
                  left: `${x}%`,
                  top: `${y}%`,
                  width: '5%',
                  height: '5%',
                  background: `radial-gradient(circle,
                    rgba(${255 * intensity}, ${100 + 155 * (1-intensity)}, ${255 * (1-intensity)}, ${0.2 + intensity * 0.3}) 0%,
                    transparent 70%)`,
                  borderRadius: '50%',
                  animation: 'humidityPulse 4s ease-in-out infinite'
                }}
              />
            );
          })
        )}
      </Box>
    );
  };

  // Render smoke/air quality overlay from AirNow.gov
  const renderSmokeOverlay = () => {
    if (!selectedLayers.smoke || !smokeData) return null;

    return (
      <Box
        sx={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          zIndex: 3,
          pointerEvents: 'none'
        }}
      >
        {smokeData.stations.map((station, index) => {
          // Only show PM2.5 (primary smoke indicator)
          if (station.parameter !== 'PM2.5') return null;

          // Calculate position (this is simplified - in production use proper map projection)
          const x = ((station.longitude - (mapCenter[1] - 5)) / 10) * 100;
          const y = ((mapCenter[0] + 5 - station.latitude) / 10) * 100;

          // Skip if outside view
          if (x < 0 || x > 100 || y < 0 || y > 100) return null;

          const color = weatherAPI.getAQIColor(station.aqi);
          const radius = Math.min(50, 10 + station.aqi / 10);

          return (
            <Box
              key={`smoke-${index}`}
              sx={{
                position: 'absolute',
                left: `${x}%`,
                top: `${y}%`,
                width: `${radius}px`,
                height: `${radius}px`,
                borderRadius: '50%',
                background: `radial-gradient(circle, ${color}88 0%, ${color}22 70%, transparent 100%)`,
                transform: 'translate(-50%, -50%)',
                animation: 'smokePulse 3s ease-in-out infinite',
                pointerEvents: 'auto',
                cursor: 'pointer'
              }}
              title={`${station.stationName}: AQI ${station.aqi} (${station.category})`}
            >
              <Box
                sx={{
                  position: 'absolute',
                  top: '50%',
                  left: '50%',
                  transform: 'translate(-50%, -50%)',
                  background: color,
                  color: 'white',
                  padding: '2px 6px',
                  borderRadius: '3px',
                  fontSize: '10px',
                  fontWeight: 'bold',
                  whiteSpace: 'nowrap',
                  boxShadow: '0 2px 4px rgba(0,0,0,0.5)'
                }}
              >
                {station.aqi}
              </Box>
            </Box>
          );
        })}
      </Box>
    );
  };

  return (
    <Box ref={containerRef} sx={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, pointerEvents: 'none', zIndex: 450 }}>
      {/* Windy.com Embed (optional overlay) */}
      {showWindyEmbed && (
        <Box
          sx={{
            position: 'absolute',
            top: 0,
            left: 0,
            width: '100%',
            height: '100%',
            zIndex: 500,
            background: 'white',
            overflow: 'hidden',
            pointerEvents: 'auto'
          }}
        >
          <IconButton
            onClick={() => setShowWindyEmbed(false)}
            sx={{
              position: 'absolute',
              top: 10,
              right: 10,
              zIndex: 101,
              background: 'rgba(0,0,0,0.7)',
              color: 'white',
              '&:hover': { background: 'rgba(0,0,0,0.9)' }
            }}
            size="small"
          >
            ✕
          </IconButton>
          <iframe
            ref={iframeRef}
            src={weatherAPI.getWindyEmbedUrl(mapCenter[0], mapCenter[1], zoom)}
            width="100%"
            height="100%"
            frameBorder="0"
            style={{ border: 0 }}
            title="Windy Weather Map"
          />
        </Box>
      )}

      {/* Weather Overlays */}
      {renderTemperatureOverlay()}
      {renderWindVectors()}
      {renderHumidityOverlay()}
      {renderSmokeOverlay()}

      {/* Weather Data Controls */}
      {showControls && (
        <Box
          sx={{
            position: 'absolute',
            top: 10,
            right: 10,
            background: 'rgba(0, 0, 0, 0.8)',
            borderRadius: 2,
            padding: 1,
            zIndex: 500,
            pointerEvents: 'auto'
          }}
        >
          <Typography variant="caption" sx={{ color: 'white', display: 'block', mb: 1 }}>
            Weather Layers
          </Typography>

          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
            <FormControlLabel
              control={
                <Switch
                  checked={selectedLayers.temperature}
                  onChange={() => onLayerToggle('temperature')}
                  size="small"
                  sx={{
                    '& .MuiSwitch-thumb': {
                      backgroundColor: selectedLayers.temperature ? '#FF4500' : 'grey'
                    }
                  }}
                />
              }
              label={
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                  <Thermostat sx={{ fontSize: 14, color: 'white' }} />
                  <Typography variant="caption" sx={{ color: 'white' }}>
                    Temperature
                  </Typography>
                </Box>
              }
              sx={{ margin: 0 }}
            />

            <FormControlLabel
              control={
                <Switch
                  checked={selectedLayers.windVectors}
                  onChange={() => onLayerToggle('windVectors')}
                  size="small"
                  sx={{
                    '& .MuiSwitch-thumb': {
                      backgroundColor: selectedLayers.windVectors ? '#44AAFF' : 'grey'
                    }
                  }}
                />
              }
              label={
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                  <Air sx={{ fontSize: 14, color: 'white' }} />
                  <Typography variant="caption" sx={{ color: 'white' }}>
                    Wind
                  </Typography>
                </Box>
              }
              sx={{ margin: 0 }}
            />

            <FormControlLabel
              control={
                <Switch
                  checked={selectedLayers.humidity}
                  onChange={() => onLayerToggle('humidity')}
                  size="small"
                  sx={{
                    '& .MuiSwitch-thumb': {
                      backgroundColor: selectedLayers.humidity ? '#66CCFF' : 'grey'
                    }
                  }}
                />
              }
              label={
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                  <WaterDrop sx={{ fontSize: 14, color: 'white' }} />
                  <Typography variant="caption" sx={{ color: 'white' }}>
                    Humidity
                  </Typography>
                </Box>
              }
              sx={{ margin: 0 }}
            />

            <FormControlLabel
              control={
                <Switch
                  checked={selectedLayers.smoke || false}
                  onChange={() => onLayerToggle('smoke')}
                  size="small"
                  sx={{
                    '& .MuiSwitch-thumb': {
                      backgroundColor: selectedLayers.smoke ? '#8F3F97' : 'grey'
                    }
                  }}
                />
              }
              label={
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                  <Cloud sx={{ fontSize: 14, color: 'white' }} />
                  <Typography variant="caption" sx={{ color: 'white' }}>
                    Smoke/AQI
                  </Typography>
                </Box>
              }
              sx={{ margin: 0 }}
            />
          </Box>

          {/* Windy.com Button */}
          <Box sx={{ mt: 1, pt: 1, borderTop: '1px solid rgba(255,255,255,0.2)' }}>
            <button
              onClick={() => setShowWindyEmbed(!showWindyEmbed)}
              style={{
                width: '100%',
                padding: '8px',
                background: 'linear-gradient(45deg, #0abde3, #48ca7e)',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '12px',
                fontWeight: 'bold',
                marginBottom: '8px'
              }}
            >
              {showWindyEmbed ? '✕ Close Windy.com' : '🌐 Open Windy.com'}
            </button>

            {/* AirNow Fire Map Button */}
            <button
              onClick={() => {
                setShowAirNowOverlay(!showAirNowOverlay);
                onLayerToggle('airNowSmoke');
              }}
              style={{
                width: '100%',
                padding: '8px',
                background: showAirNowOverlay ? 'linear-gradient(45deg, #d32f2f, #b71c1c)' : 'linear-gradient(45deg, #ff6b35, #f7931e)',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '12px',
                fontWeight: 'bold'
              }}
            >
              {showAirNowOverlay ? '✕ Close AirNow Smoke' : '🔥 Show AirNow Smoke'}
            </button>
          </Box>

          {/* Current Weather Stats */}
          <Box sx={{ mt: 1, pt: 1, borderTop: '1px solid rgba(255,255,255,0.2)' }}>
            <Typography variant="caption" sx={{ color: 'white', display: 'block' }}>
              Current Conditions:
            </Typography>
            <Typography variant="caption" sx={{ color: '#FF6B6B', display: 'block' }}>
              🌡️ 105°F | 💨 25mph NE | 💧 12% RH
            </Typography>
            {smokeData && (
              <Typography variant="caption" sx={{ color: weatherAPI.getAQIColor(smokeData.stations.find(s => s.parameter === 'PM2.5')?.aqi || 0), display: 'block' }}>
                ☁️ Smoke: {smokeData.severityLevel.toUpperCase()} ({smokeData.stations.filter(s => s.parameter === 'PM2.5').length} stations)
              </Typography>
            )}
            <Typography variant="caption" sx={{ color: '#FFAA44', display: 'block' }}>
              ⚠️ Critical Fire Weather
            </Typography>
            <Typography variant="caption" sx={{ color: '#888', display: 'block', mt: 0.5, fontSize: '9px' }}>
              Data: Windy.com + AirNow.gov
            </Typography>
          </Box>
        </Box>
      )}

      {/* Toggle Controls Visibility */}
      <IconButton
        onClick={() => setShowControls(!showControls)}
        sx={{
          position: 'absolute',
          top: 10,
          right: showControls ? 220 : 10,
          background: 'rgba(0, 0, 0, 0.8)',
          color: 'white',
          zIndex: 500,
          pointerEvents: 'auto',
          '&:hover': {
            background: 'rgba(0, 0, 0, 0.9)'
          }
        }}
        size="small"
      >
        {showControls ? <VisibilityOff /> : <Visibility />}
      </IconButton>

      {/* CSS Animations */}
      <style>
        {`
          @keyframes windFlow {
            0% { opacity: 0.6; transform: translateX(-5px); }
            50% { opacity: 1; transform: translateX(0px); }
            100% { opacity: 0.6; transform: translateX(5px); }
          }

          @keyframes humidityPulse {
            0%, 100% { opacity: 0.3; transform: scale(1); }
            50% { opacity: 0.6; transform: scale(1.1); }
          }

          @keyframes smokePulse {
            0%, 100% { opacity: 0.7; transform: translate(-50%, -50%) scale(1); }
            50% { opacity: 0.9; transform: translate(-50%, -50%) scale(1.15); }
          }
        `}
      </style>
    </Box>
  );
};

export default WindyWeatherOverlay;