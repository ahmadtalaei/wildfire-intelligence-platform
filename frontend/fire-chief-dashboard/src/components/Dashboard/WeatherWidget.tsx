import React from 'react';
import {
  Paper,
  Typography,
  Grid,
  Box,
  Chip,
  LinearProgress,
  Divider,
} from '@mui/material';
import {
  Thermostat,
  Air,
  WaterDrop,
  Visibility,
  Warning,
} from '@mui/icons-material';

interface WeatherData {
  location: string;
  temperature: number;
  humidity: number;
  windSpeed: number;
  windDirection: string;
  fireRiskIndex: number;
  visibility: number;
  conditions: string;
}

interface WeatherWidgetProps {
  data?: WeatherData;
  loading?: boolean;
}

const WeatherWidget: React.FC<WeatherWidgetProps> = ({
  data,
  loading = false,
}) => {
  // Mock weather data if none provided
  const mockData: WeatherData = {
    location: 'Riverside County',
    temperature: 95,
    humidity: 15,
    windSpeed: 25,
    windDirection: 'SW',
    fireRiskIndex: 8.5,
    visibility: 10,
    conditions: 'Clear',
  };

  const weatherData = data || mockData;

  const getFireRiskColor = (index: number) => {
    if (index >= 8) return 'error';
    if (index >= 6) return 'warning';
    if (index >= 4) return 'info';
    return 'success';
  };

  const getFireRiskLabel = (index: number) => {
    if (index >= 8) return 'EXTREME';
    if (index >= 6) return 'HIGH';
    if (index >= 4) return 'MODERATE';
    return 'LOW';
  };

  const getHumidityColor = (humidity: number) => {
    if (humidity < 20) return 'error';
    if (humidity < 40) return 'warning';
    return 'success';
  };

  const getWindSpeedColor = (speed: number) => {
    if (speed >= 25) return 'error';
    if (speed >= 15) return 'warning';
    return 'success';
  };

  if (loading) {
    return (
      <Paper sx={{ p: 2 }}>
        <Typography variant="h6" gutterBottom>
          Weather Conditions
        </Typography>
        <Box display="flex" justifyContent="center" py={4}>
          <Typography color="text.secondary">Loading weather data...</Typography>
        </Box>
      </Paper>
    );
  }

  return (
    <Paper sx={{ p: 2 }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="h6">
          Weather Conditions
        </Typography>
        <Typography variant="body2" color="text.secondary">
          {weatherData.location}
        </Typography>
      </Box>

      <Grid container spacing={2}>
        {/* Temperature */}
        <Grid item xs={6}>
          <Box display="flex" alignItems="center" gap={1}>
            <Thermostat color="primary" />
            <Box>
              <Typography variant="h5" fontWeight="bold" color="primary">
                {weatherData.temperature}degF
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Temperature
              </Typography>
            </Box>
          </Box>
        </Grid>

        {/* Humidity */}
        <Grid item xs={6}>
          <Box display="flex" alignItems="center" gap={1}>
            <WaterDrop color={getHumidityColor(weatherData.humidity)} />
            <Box>
              <Typography 
                variant="h5" 
                fontWeight="bold" 
                color={`${getHumidityColor(weatherData.humidity)}.main`}
              >
                {weatherData.humidity}%
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Humidity
              </Typography>
            </Box>
          </Box>
        </Grid>

        {/* Wind */}
        <Grid item xs={6}>
          <Box display="flex" alignItems="center" gap={1}>
            <Air color={getWindSpeedColor(weatherData.windSpeed)} />
            <Box>
              <Typography 
                variant="h6" 
                fontWeight="bold" 
                color={`${getWindSpeedColor(weatherData.windSpeed)}.main`}
              >
                {weatherData.windSpeed} mph
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Wind {weatherData.windDirection}
              </Typography>
            </Box>
          </Box>
        </Grid>

        {/* Visibility */}
        <Grid item xs={6}>
          <Box display="flex" alignItems="center" gap={1}>
            <Visibility color="info" />
            <Box>
              <Typography variant="h6" fontWeight="bold" color="info.main">
                {weatherData.visibility} mi
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Visibility
              </Typography>
            </Box>
          </Box>
        </Grid>
      </Grid>

      <Divider sx={{ my: 2 }} />

      {/* Fire Risk Index */}
      <Box>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
          <Box display="flex" alignItems="center" gap={1}>
            <Warning color={getFireRiskColor(weatherData.fireRiskIndex)} />
            <Typography variant="subtitle2" fontWeight="medium">
              Fire Risk Index
            </Typography>
          </Box>
          <Chip
            label={getFireRiskLabel(weatherData.fireRiskIndex)}
            color={getFireRiskColor(weatherData.fireRiskIndex) as any}
            size="small"
            icon={<Warning />}
          />
        </Box>

        <Box display="flex" alignItems="center" gap={2}>
          <LinearProgress
            variant="determinate"
            value={(weatherData.fireRiskIndex / 10) * 100}
            color={getFireRiskColor(weatherData.fireRiskIndex) as any}
            sx={{ 
              flexGrow: 1, 
              height: 8, 
              borderRadius: 4,
            }}
          />
          <Typography 
            variant="h6" 
            fontWeight="bold"
            color={`${getFireRiskColor(weatherData.fireRiskIndex)}.main`}
          >
            {weatherData.fireRiskIndex}/10
          </Typography>
        </Box>

        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
          Based on temperature, humidity, wind speed, and fuel moisture
        </Typography>
      </Box>

      {/* Conditions Summary */}
      <Box sx={{ mt: 2, p: 1, backgroundColor: 'grey.50', borderRadius: 1 }}>
        <Typography variant="body2" color="text.secondary">
          Current Conditions: <strong>{weatherData.conditions}</strong>
        </Typography>
        {weatherData.fireRiskIndex >= 6 && (
          <Typography variant="body2" color="warning.main" sx={{ mt: 0.5 }}>
            [WARNING] Elevated fire conditions - exercise extreme caution
          </Typography>
        )}
      </Box>
    </Paper>
  );
};

export default WeatherWidget;