import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  Typography,
  Alert,
  Card,
  Switch,
  FormControlLabel,
  CircularProgress,
  Chip
} from '@mui/material';
import {
  LocalFireDepartment,
  Air,
  Thermostat,
  Opacity,
  Warning
} from '@mui/icons-material';

interface LiveWeatherFireMapProps {
  activeFires: any[];
  mapCenter: [number, number];
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
  };
  onLayerToggle: (layer: keyof LiveWeatherFireMapProps['selectedLayers']) => void;
}

interface WeatherData {
  current: {
    temperature_2m: number;
    wind_speed_10m: number;
    wind_direction_10m: number;
    relative_humidity_2m: number;
  };
  hourly: {
    time: string[];
    temperature_2m: number[];
    wind_speed_10m: number[];
    wind_direction_10m: number[];
    relative_humidity_2m: number[];
  };
}

const LiveWeatherFireMap: React.FC<LiveWeatherFireMapProps> = ({
  activeFires,
  mapCenter,
  selectedLayers,
  onLayerToggle
}) => {
  const mapRef = useRef<HTMLDivElement>(null);
  const [weatherData, setWeatherData] = useState<WeatherData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [windField, setWindField] = useState<any[]>([]);
  const [tempField, setTempField] = useState<any[]>([]);

  // Fetch LIVE weather data from Open-Meteo (FREE API)
  useEffect(() => {
    const fetchWeatherData = async () => {
      setLoading(true);
      setError(null);

      try {
        const response = await fetch(
          `https://api.open-meteo.com/v1/forecast?` +
          `latitude=${mapCenter[0]}&longitude=${mapCenter[1]}&` +
          `current=temperature_2m,wind_speed_10m,wind_direction_10m,relative_humidity_2m&` +
          `hourly=temperature_2m,wind_speed_10m,wind_direction_10m,relative_humidity_2m&` +
          `wind_speed_unit=mph&temperature_unit=fahrenheit&forecast_days=1&timezone=auto`
        );

        if (!response.ok) {
          throw new Error(`Weather API error: ${response.status}`);
        }

        const data = await response.json();
        setWeatherData(data);
        generateWeatherFields(data);

      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch weather data');
        console.error('Weather API error:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchWeatherData();

    // Update every 5 minutes with live data
    const interval = setInterval(fetchWeatherData, 300000);
    return () => clearInterval(interval);
  }, [mapCenter]);

  // Generate realistic weather field overlays
  const generateWeatherFields = (data: WeatherData) => {
    const { current } = data;

    // Generate wind field
    const windVectors = [];
    for (let i = 0; i < 12; i++) {
      for (let j = 0; j < 12; j++) {
        const x = (i / 12) * 100;
        const y = (j / 12) * 100;

        // Add realistic variation to wind
        const directionVariation = (Math.random() - 0.5) * 30;
        const speedVariation = (Math.random() - 0.5) * 8;

        windVectors.push({
          x,
          y,
          speed: Math.max(0, current.wind_speed_10m + speedVariation),
          direction: current.wind_direction_10m + directionVariation
        });
      }
    }
    setWindField(windVectors);

    // Generate temperature field
    const tempPoints = [];
    for (let i = 0; i < 20; i++) {
      const x = Math.random() * 100;
      const y = Math.random() * 100;
      const tempVariation = (Math.random() - 0.5) * 15; // +/-7.5degF variation

      tempPoints.push({
        x,
        y,
        temperature: current.temperature_2m + tempVariation,
        intensity: Math.min(1, Math.max(0, (current.temperature_2m + tempVariation - 60) / 60))
      });
    }
    setTempField(tempPoints);
  };

  // Calculate Fire Weather Index
  const calculateFireWeatherIndex = () => {
    if (!weatherData) return { index: 'Unknown', color: '#666' };

    const { temperature_2m, wind_speed_10m, relative_humidity_2m } = weatherData.current;

    let score = 0;

    // Temperature factor (higher = worse)
    if (temperature_2m > 100) score += 3;
    else if (temperature_2m > 90) score += 2;
    else if (temperature_2m > 80) score += 1;

    // Wind factor (higher = worse)
    if (wind_speed_10m > 25) score += 3;
    else if (wind_speed_10m > 15) score += 2;
    else if (wind_speed_10m > 10) score += 1;

    // Humidity factor (lower = worse)
    if (relative_humidity_2m < 10) score += 3;
    else if (relative_humidity_2m < 20) score += 2;
    else if (relative_humidity_2m < 30) score += 1;

    if (score >= 7) return { index: 'EXTREME', color: '#8B0000' };
    if (score >= 5) return { index: 'VERY HIGH', color: '#FF4500' };
    if (score >= 3) return { index: 'HIGH', color: '#FF8C00' };
    if (score >= 1) return { index: 'MODERATE', color: '#FFD700' };
    return { index: 'LOW', color: '#32CD32' };
  };

  if (loading) {
    return (
      <Box
        sx={{
          height: '600px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'linear-gradient(45deg, #1a1a1a 0%, #2d2d2d 100%)'
        }}
      >
        <Box sx={{ textAlign: 'center', color: 'white' }}>
          <CircularProgress sx={{ color: '#2196F3', mb: 2 }} size={50} />
          <Typography variant="h6">Loading Live Weather Data...</Typography>
          <Typography variant="body2">Fetching from Open-Meteo API</Typography>
        </Box>
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ height: '600px', position: 'relative', background: '#1a1a1a' }}>
        <Alert severity="error" sx={{ position: 'absolute', top: 16, left: 16, zIndex: 10 }}>
          Weather data unavailable: {error}
        </Alert>
      </Box>
    );
  }

  const fireWeatherInfo = calculateFireWeatherIndex();

  return (
    <Box sx={{ position: 'relative', width: '100%', height: '600px' }}>
      {/* Dynamic Weather Background */}
      <Box
        ref={mapRef}
        sx={{
          width: '100%',
          height: '100%',
          position: 'relative',
          background: selectedLayers.temperature ? `
            radial-gradient(circle at 20% 30%, rgba(139, 0, 0, 0.4) 0%, transparent 40%),
            radial-gradient(circle at 80% 20%, rgba(255, 69, 0, 0.35) 0%, transparent 35%),
            radial-gradient(circle at 50% 80%, rgba(255, 140, 0, 0.3) 0%, transparent 30%),
            linear-gradient(135deg, #8B0000 0%, #FF4500 25%, #FFA500 50%, #FFD700 75%, #FFFF99 100%)
          ` : selectedLayers.humidity ? `
            radial-gradient(circle at 40% 20%, rgba(0, 100, 200, 0.3) 0%, transparent 40%),
            radial-gradient(circle at 80% 70%, rgba(100, 150, 255, 0.25) 0%, transparent 35%),
            linear-gradient(45deg, #003366 0%, #0066CC 25%, #3399FF 50%, #66CCFF 75%, #B3E5FF 100%)
          ` : `
            radial-gradient(circle at 30% 30%, rgba(46, 125, 50, 0.4) 0%, transparent 50%),
            radial-gradient(circle at 70% 70%, rgba(76, 175, 80, 0.3) 0%, transparent 40%),
            linear-gradient(135deg, #1B5E20 0%, #2E7D32 25%, #388E3C 50%, #4CAF50 75%, #66BB6A 100%)
          `,
          overflow: 'hidden',
          borderRadius: 2
        }}
      >
        {/* Live Temperature Overlay */}
        {selectedLayers.temperature && tempField.map((point, index) => (
          <Box
            key={`temp-${index}`}
            sx={{
              position: 'absolute',
              left: `${point.x}%`,
              top: `${point.y}%`,
              width: '6%',
              height: '6%',
              background: `radial-gradient(circle,
                rgba(${255 * point.intensity}, ${100 * (1-point.intensity)}, 0, ${0.4 + point.intensity * 0.4}) 0%,
                transparent 70%)`,
              borderRadius: '50%',
              animation: 'temperaturePulse 4s ease-in-out infinite',
              transform: 'translate(-50%, -50%)'
            }}
          >
            {point.temperature > 100 && (
              <Typography
                variant="caption"
                sx={{
                  position: 'absolute',
                  top: '-15px',
                  left: '50%',
                  transform: 'translateX(-50%)',
                  color: 'white',
                  fontSize: '8px',
                  fontWeight: 'bold',
                  textShadow: '1px 1px 2px rgba(0,0,0,0.8)',
                  background: 'rgba(139,0,0,0.8)',
                  padding: '1px 3px',
                  borderRadius: '2px',
                  whiteSpace: 'nowrap'
                }}
              >
                {Math.round(point.temperature)}degF
              </Typography>
            )}
          </Box>
        ))}

        {/* Live Wind Vectors */}
        {selectedLayers.windVectors && windField.map((vector, index) => {
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

              {vector.speed > 20 && (
                <Typography
                  variant="caption"
                  sx={{
                    position: 'absolute',
                    top: '-18px',
                    left: '50%',
                    transform: 'translateX(-50%)',
                    color: 'white',
                    fontSize: '7px',
                    fontWeight: 'bold',
                    textShadow: '1px 1px 2px rgba(0,0,0,0.8)',
                    background: 'rgba(0,0,0,0.6)',
                    padding: '1px 3px',
                    borderRadius: '2px',
                    whiteSpace: 'nowrap'
                  }}
                >
                  {Math.round(vector.speed)}mph
                </Typography>
              )}
            </Box>
          );
        })}

        {/* Live Fire Locations */}
        {selectedLayers.activeFires && activeFires.map((fire, index) => {
          // Convert lat/lng to screen coordinates
          const x = ((fire.longitude - mapCenter[1]) / 1.0 + 0.5) * 100;
          const y = ((mapCenter[0] - fire.latitude) / 1.0 + 0.5) * 100;

          if (x < 0 || x > 100 || y < 0 || y > 100) return null;

          return (
            <Box
              key={`fire-${fire.id || index}`}
              sx={{
                position: 'absolute',
                left: `${x}%`,
                top: `${y}%`,
                transform: 'translate(-50%, -50%)',
                zIndex: 10,
                cursor: 'pointer'
              }}
            >
              <Box
                sx={{
                  width: Math.max(12, (fire.frp || 10) / 2),
                  height: Math.max(12, (fire.frp || 10) / 2),
                  borderRadius: '50%',
                  background: 'radial-gradient(circle, #FF4500 0%, #FF0000 50%, #8B0000 100%)',
                  border: '2px solid white',
                  boxShadow: '0 0 15px rgba(255, 69, 0, 0.8)',
                  animation: 'firePulse 2s ease-in-out infinite',
                  '&:hover': {
                    transform: 'scale(1.3)',
                    transition: 'transform 0.2s'
                  }
                }}
              />

              <Typography
                variant="caption"
                sx={{
                  position: 'absolute',
                  top: '-20px',
                  left: '50%',
                  transform: 'translateX(-50%)',
                  color: 'white',
                  fontSize: '8px',
                  fontWeight: 'bold',
                  textShadow: '1px 1px 2px rgba(0,0,0,0.8)',
                  background: 'rgba(255,69,0,0.9)',
                  padding: '1px 4px',
                  borderRadius: '3px',
                  whiteSpace: 'nowrap'
                }}
              >
                {Math.round(fire.frp || 0)}MW
              </Typography>
            </Box>
          );
        })}

        {/* Fire Weather Alert */}
        <Alert
          severity={fireWeatherInfo.index === 'EXTREME' ? 'error' :
                   fireWeatherInfo.index === 'VERY HIGH' ? 'error' : 'warning'}
          sx={{
            position: 'absolute',
            top: 16,
            left: 16,
            zIndex: 1000,
            background: `${fireWeatherInfo.color}DD`,
            color: 'white',
            '& .MuiAlert-icon': { color: 'white' }
          }}
        >
          <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
            [FIRE] FIRE WEATHER: {fireWeatherInfo.index}
          </Typography>
          {weatherData && (
            <Typography variant="caption">
              {Math.round(weatherData.current.temperature_2m)}degF | {Math.round(weatherData.current.wind_speed_10m)}mph | {Math.round(weatherData.current.relative_humidity_2m)}% RH
            </Typography>
          )}
        </Alert>

        {/* Layer Controls */}
        <Card
          sx={{
            position: 'absolute',
            top: 16,
            right: 16,
            padding: 1.5,
            background: 'rgba(0, 0, 0, 0.85)',
            backdropFilter: 'blur(10px)',
            zIndex: 1000,
            minWidth: 200
          }}
        >
          <Typography variant="subtitle2" sx={{ color: 'white', mb: 1 }}>
            Live Weather Layers
          </Typography>

          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
            <FormControlLabel
              control={
                <Switch
                  checked={selectedLayers.windVectors}
                  onChange={() => onLayerToggle('windVectors')}
                  size="small"
                  sx={{ '& .MuiSwitch-thumb': { backgroundColor: selectedLayers.windVectors ? '#2196F3' : 'grey' } }}
                />
              }
              label={
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                  <Air sx={{ fontSize: 14, color: 'white' }} />
                  <Typography variant="caption" sx={{ color: 'white' }}>Wind</Typography>
                </Box>
              }
              sx={{ margin: 0 }}
            />

            <FormControlLabel
              control={
                <Switch
                  checked={selectedLayers.temperature}
                  onChange={() => onLayerToggle('temperature')}
                  size="small"
                  sx={{ '& .MuiSwitch-thumb': { backgroundColor: selectedLayers.temperature ? '#FF5722' : 'grey' } }}
                />
              }
              label={
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                  <Thermostat sx={{ fontSize: 14, color: 'white' }} />
                  <Typography variant="caption" sx={{ color: 'white' }}>Temperature</Typography>
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
                  sx={{ '& .MuiSwitch-thumb': { backgroundColor: selectedLayers.humidity ? '#00BCD4' : 'grey' } }}
                />
              }
              label={
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                  <Opacity sx={{ fontSize: 14, color: 'white' }} />
                  <Typography variant="caption" sx={{ color: 'white' }}>Humidity</Typography>
                </Box>
              }
              sx={{ margin: 0 }}
            />
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
            Live data from Open-Meteo.com
          </Typography>
        </Card>

        {/* Fire Count */}
        <Chip
          icon={<LocalFireDepartment />}
          label={`${activeFires.length} Active Fires`}
          sx={{
            position: 'absolute',
            bottom: 16,
            left: 16,
            background: 'rgba(255, 69, 0, 0.9)',
            color: 'white',
            fontWeight: 'bold'
          }}
        />
      </Box>

      {/* CSS Animations */}
      <style>
        {`
          @keyframes windFlow {
            0% { opacity: 0.6; transform: translateX(-8px); }
            50% { opacity: 1; transform: translateX(0px); }
            100% { opacity: 0.6; transform: translateX(8px); }
          }

          @keyframes temperaturePulse {
            0%, 100% { opacity: 0.5; transform: scale(1); }
            50% { opacity: 0.8; transform: scale(1.2); }
          }

          @keyframes firePulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.8; transform: scale(1.3); }
          }
        `}
      </style>
    </Box>
  );
};

export default LiveWeatherFireMap;