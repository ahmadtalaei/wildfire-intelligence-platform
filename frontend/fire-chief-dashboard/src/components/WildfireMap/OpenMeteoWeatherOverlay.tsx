import React, { useEffect, useState } from 'react';
import { Box, Typography, Switch, FormControlLabel, Card, Alert, CircularProgress } from '@mui/material';
import {
  Air,
  Thermostat,
  Opacity,
  Cloud,
  Visibility,
  Speed
} from '@mui/icons-material';

interface OpenMeteoWeatherOverlayProps {
  mapCenter: [number, number];
  selectedLayers: {
    windVectors: boolean;
    temperature: boolean;
    humidity: boolean;
    precipitation: boolean;
  };
  onLayerToggle: (layer: keyof OpenMeteoWeatherOverlayProps['selectedLayers']) => void;
}

interface WeatherData {
  current: {
    temperature: number;
    wind_speed: number;
    wind_direction: number;
    relative_humidity: number;
    precipitation: number;
    visibility: number;
  };
  hourly: {
    time: string[];
    temperature_2m: number[];
    wind_speed_10m: number[];
    wind_direction_10m: number[];
    relative_humidity_2m: number[];
    precipitation: number[];
  };
}

const OpenMeteoWeatherOverlay: React.FC<OpenMeteoWeatherOverlayProps> = ({
  mapCenter,
  selectedLayers,
  onLayerToggle
}) => {
  const [weatherData, setWeatherData] = useState<WeatherData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch weather data from Open-Meteo API
  useEffect(() => {
    const fetchWeatherData = async () => {
      setLoading(true);
      setError(null);

      try {
        const [lat, lng] = mapCenter;

        // Open-Meteo API call - completely free, no API key required
        const response = await fetch(
          `https://api.open-meteo.com/v1/forecast?` +
          `latitude=${lat}&longitude=${lng}&` +
          `current=temperature_2m,wind_speed_10m,wind_direction_10m,relative_humidity_2m,precipitation,visibility&` +
          `hourly=temperature_2m,wind_speed_10m,wind_direction_10m,relative_humidity_2m,precipitation&` +
          `wind_speed_unit=mph&` +
          `temperature_unit=fahrenheit&` +
          `timezone=auto&` +
          `forecast_days=3`
        );

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        setWeatherData({
          current: {
            temperature: data.current.temperature_2m,
            wind_speed: data.current.wind_speed_10m,
            wind_direction: data.current.wind_direction_10m,
            relative_humidity: data.current.relative_humidity_2m,
            precipitation: data.current.precipitation,
            visibility: data.current.visibility / 1000 // Convert to miles
          },
          hourly: {
            time: data.hourly.time,
            temperature_2m: data.hourly.temperature_2m,
            wind_speed_10m: data.hourly.wind_speed_10m,
            wind_direction_10m: data.hourly.wind_direction_10m,
            relative_humidity_2m: data.hourly.relative_humidity_2m,
            precipitation: data.hourly.precipitation
          }
        });

      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch weather data');
        console.error('Open-Meteo API error:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchWeatherData();

    // Update every 10 minutes
    const interval = setInterval(fetchWeatherData, 600000);

    return () => clearInterval(interval);
  }, [mapCenter]);

  // Generate wind field visualization
  const generateWindField = () => {
    if (!weatherData || !selectedLayers.windVectors) return null;

    const { wind_speed, wind_direction } = weatherData.current;
    const windVectors = [];

    // Create a grid of wind vectors
    for (let i = 0; i < 10; i++) {
      for (let j = 0; j < 10; j++) {
        const x = (i / 10) * 100 + 5;
        const y = (j / 10) * 100 + 5;

        // Add some variation to wind direction and speed
        const directionVariation = (Math.random() - 0.5) * 20;
        const speedVariation = (Math.random() - 0.5) * 5;

        windVectors.push({
          x,
          y,
          speed: Math.max(0, wind_speed + speedVariation),
          direction: wind_direction + directionVariation
        });
      }
    }

    return windVectors.map((vector, index) => {
      const length = Math.min(40, vector.speed * 1.5);
      const speedColor = vector.speed > 25 ? '#FF4444' : vector.speed > 15 ? '#FFAA44' : '#44AAFF';

      return (
        <Box
          key={`wind-${index}`}
          sx={{
            position: 'absolute',
            left: `${vector.x}%`,
            top: `${vector.y}%`,
            transform: `translate(-50%, -50%) rotate(${vector.direction}deg)`,
            zIndex: 5
          }}
        >
          <Box
            sx={{
              width: `${length}px`,
              height: '3px',
              background: `linear-gradient(90deg, ${speedColor} 0%, transparent 100%)`,
              filter: 'drop-shadow(0 0 2px rgba(255,255,255,0.5))',
              animation: 'windFlow 2s ease-in-out infinite',
              '&::after': {
                content: '""',
                position: 'absolute',
                right: '-6px',
                top: '-3px',
                width: 0,
                height: 0,
                borderLeft: `8px solid ${speedColor}`,
                borderTop: '4px solid transparent',
                borderBottom: '4px solid transparent'
              }
            }}
          />
        </Box>
      );
    });
  };

  // Generate temperature heatmap
  const generateTemperatureField = () => {
    if (!weatherData || !selectedLayers.temperature) return null;

    const { temperature } = weatherData.current;
    const hotspots = [];

    // Create temperature gradient hotspots
    for (let i = 0; i < 15; i++) {
      const x = Math.random() * 100;
      const y = Math.random() * 100;
      const tempVariation = (Math.random() - 0.5) * 20; // +/-10degF variation
      const localTemp = temperature + tempVariation;

      const intensity = Math.min(1, Math.max(0, (localTemp - 70) / 50)); // Normalize 70-120degF

      hotspots.push({
        x,
        y,
        temperature: localTemp,
        intensity
      });
    }

    return hotspots.map((spot, index) => (
      <Box
        key={`temp-${index}`}
        sx={{
          position: 'absolute',
          left: `${spot.x}%`,
          top: `${spot.y}%`,
          width: '8%',
          height: '8%',
          background: `radial-gradient(circle,
            rgba(${255 * spot.intensity}, ${100 * (1-spot.intensity)}, 0, ${0.3 + spot.intensity * 0.4}) 0%,
            transparent 70%)`,
          borderRadius: '50%',
          animation: 'temperaturePulse 4s ease-in-out infinite'
        }}
      />
    ));
  };

  // Calculate fire weather index
  const calculateFireWeatherIndex = () => {
    if (!weatherData) return 'Unknown';

    const { temperature, wind_speed, relative_humidity } = weatherData.current;

    // Simplified fire weather index calculation
    let index = 0;

    // Temperature factor (higher = worse)
    if (temperature > 100) index += 3;
    else if (temperature > 90) index += 2;
    else if (temperature > 80) index += 1;

    // Wind factor (higher = worse)
    if (wind_speed > 25) index += 3;
    else if (wind_speed > 15) index += 2;
    else if (wind_speed > 10) index += 1;

    // Humidity factor (lower = worse)
    if (relative_humidity < 10) index += 3;
    else if (relative_humidity < 20) index += 2;
    else if (relative_humidity < 30) index += 1;

    if (index >= 7) return 'EXTREME';
    if (index >= 5) return 'VERY HIGH';
    if (index >= 3) return 'HIGH';
    if (index >= 1) return 'MODERATE';
    return 'LOW';
  };

  const getFireIndexColor = (index: string) => {
    switch (index) {
      case 'EXTREME': return '#8B0000';
      case 'VERY HIGH': return '#FF4500';
      case 'HIGH': return '#FF8C00';
      case 'MODERATE': return '#FFD700';
      default: return '#32CD32';
    }
  };

  if (loading) {
    return (
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
          background: 'rgba(0, 0, 0, 0.7)',
          zIndex: 10
        }}
      >
        <Box sx={{ textAlign: 'center', color: 'white' }}>
          <CircularProgress sx={{ color: 'white', mb: 2 }} />
          <Typography variant="h6">Loading Weather Data...</Typography>
          <Typography variant="body2">Fetching from Open-Meteo API</Typography>
        </Box>
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ position: 'absolute', top: 16, left: 16, zIndex: 10 }}>
        Weather data unavailable: {error}
      </Alert>
    );
  }

  return (
    <Box sx={{ position: 'relative', width: '100%', height: '100%' }}>
      {/* Weather Overlays */}
      {generateTemperatureField()}
      {generateWindField()}

      {/* Fire Weather Alert */}
      {weatherData && (
        <Alert
          severity={calculateFireWeatherIndex() === 'EXTREME' ? 'error' : 'warning'}
          sx={{
            position: 'absolute',
            top: 16,
            left: 16,
            zIndex: 1000,
            background: `rgba(${calculateFireWeatherIndex() === 'EXTREME' ? '139, 0, 0' : '255, 152, 0'}, 0.95)`,
            color: 'white'
          }}
        >
          <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
            [FIRE] FIRE WEATHER: {calculateFireWeatherIndex()}
          </Typography>
          <Typography variant="caption">
            {weatherData.current.temperature}degF | {Math.round(weatherData.current.wind_speed)}mph | {Math.round(weatherData.current.relative_humidity)}% RH
          </Typography>
        </Alert>
      )}

      {/* Weather Controls */}
      <Card
        sx={{
          position: 'absolute',
          top: 16,
          right: 16,
          padding: 2,
          background: 'rgba(0, 0, 0, 0.85)',
          backdropFilter: 'blur(10px)',
          zIndex: 1000,
          minWidth: 250
        }}
      >
        <Typography variant="subtitle2" sx={{ color: 'white', mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
          <Cloud color="primary" />
          Open-Meteo Weather
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
                  Wind Vectors
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
                  Humidity
                </Typography>
              </Box>
            }
          />
        </Box>

        {/* Current Weather Details */}
        {weatherData && (
          <Box sx={{ mt: 2, pt: 2, borderTop: '1px solid rgba(255,255,255,0.2)' }}>
            <Typography variant="caption" sx={{ color: 'white', display: 'block', mb: 1 }}>
              Current Conditions:
            </Typography>

            <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 1 }}>
              <Typography variant="caption" sx={{ color: '#FF9800' }}>
                [THERMOMETER] {Math.round(weatherData.current.temperature)}degF
              </Typography>
              <Typography variant="caption" sx={{ color: '#2196F3' }}>
                💨 {Math.round(weatherData.current.wind_speed)}mph
              </Typography>
              <Typography variant="caption" sx={{ color: '#00BCD4' }}>
                [DROPLET] {Math.round(weatherData.current.relative_humidity)}%
              </Typography>
              <Typography variant="caption" sx={{ color: '#4CAF50' }}>
                👁️ {Math.round(weatherData.current.visibility)}mi
              </Typography>
            </Box>

            <Box sx={{ mt: 1, p: 1, background: `rgba(${getFireIndexColor(calculateFireWeatherIndex()).replace('#', '').match(/.{2}/g)?.map(x => parseInt(x, 16)).join(', ')}, 0.3)`, borderRadius: 1 }}>
              <Typography
                variant="caption"
                sx={{
                  color: getFireIndexColor(calculateFireWeatherIndex()),
                  fontWeight: 'bold',
                  display: 'block'
                }}
              >
                Fire Weather Index: {calculateFireWeatherIndex()}
              </Typography>
            </Box>
          </Box>
        )}

        {/* Data Source */}
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
          Free weather data by Open-Meteo.com
        </Typography>
      </Card>

      {/* CSS Animations */}
      <style>
        {`
          @keyframes windFlow {
            0% { opacity: 0.6; transform: translateX(-5px); }
            50% { opacity: 1; transform: translateX(0px); }
            100% { opacity: 0.6; transform: translateX(5px); }
          }

          @keyframes temperaturePulse {
            0%, 100% { opacity: 0.4; transform: scale(1); }
            50% { opacity: 0.7; transform: scale(1.1); }
          }
        `}
      </style>
    </Box>
  );
};

export default OpenMeteoWeatherOverlay;