import React, { useState, useEffect } from 'react';
import {
  Card,
  CardHeader,
  CardContent,
  Typography,
  Box,
  Grid,
  Avatar,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  Alert,
  LinearProgress,
  IconButton,
  Tooltip,
  Divider,
} from '@mui/material';
import {
  Thermostat,
  Air,
  WaterDrop,
  Visibility,
  Speed,
  Refresh,
  Warning,
  CheckCircle,
  TrendingUp,
  TrendingDown,
  TrendingFlat,
  LocationOn,
  Schedule,
} from '@mui/icons-material';

interface RAWSStation {
  id: string;
  name: string;
  location: string;
  latitude: number;
  longitude: number;
  elevation: number;
  temperature: number;
  humidity: number;
  windSpeed: number;
  windDirection: number;
  windGust: number;
  precipitation: number;
  fuelTemperature: number;
  fuelMoisture: number;
  solarRadiation: number;
  lastUpdate: Date;
  status: 'online' | 'offline' | 'maintenance';
  fireRiskIndex: number;
}

const RAWSWeatherWidget: React.FC = () => {
  const [stations, setStations] = useState<RAWSStation[]>([]);
  const [selectedStation, setSelectedStation] = useState<string>('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // Mock RAWS data - in real implementation, would fetch from NIFC/CAL FIRE APIs
    const mockStations: RAWSStation[] = [
      {
        id: 'RAWS001',
        name: 'Angeles Crest',
        location: 'Angeles National Forest',
        latitude: 34.3774,
        longitude: -118.0167,
        elevation: 5950,
        temperature: 92,
        humidity: 8,
        windSpeed: 25,
        windDirection: 45,
        windGust: 42,
        precipitation: 0.0,
        fuelTemperature: 88,
        fuelMoisture: 4,
        solarRadiation: 850,
        lastUpdate: new Date(Date.now() - 300000),
        status: 'online',
        fireRiskIndex: 95
      },
      {
        id: 'RAWS002',
        name: 'Simi Hills',
        location: 'Ventura County',
        latitude: 34.2694,
        longitude: -118.7317,
        elevation: 1840,
        temperature: 89,
        humidity: 12,
        windSpeed: 18,
        windDirection: 315,
        windGust: 28,
        precipitation: 0.0,
        fuelTemperature: 85,
        fuelMoisture: 6,
        solarRadiation: 920,
        lastUpdate: new Date(Date.now() - 180000),
        status: 'online',
        fireRiskIndex: 87
      },
      {
        id: 'RAWS003',
        name: 'Mount Wilson',
        location: 'Los Angeles County',
        latitude: 34.2257,
        longitude: -118.0608,
        elevation: 5710,
        temperature: 78,
        humidity: 22,
        windSpeed: 12,
        windDirection: 270,
        windGust: 18,
        precipitation: 0.0,
        fuelTemperature: 76,
        fuelMoisture: 12,
        solarRadiation: 780,
        lastUpdate: new Date(Date.now() - 120000),
        status: 'online',
        fireRiskIndex: 65
      },
      {
        id: 'RAWS004',
        name: 'Santiago Peak',
        location: 'Orange County',
        latitude: 33.7107,
        longitude: -117.5318,
        elevation: 5680,
        temperature: 85,
        humidity: 15,
        windSpeed: 22,
        windDirection: 60,
        windGust: 35,
        precipitation: 0.0,
        fuelTemperature: 82,
        fuelMoisture: 8,
        solarRadiation: 880,
        lastUpdate: new Date(Date.now() - 240000),
        status: 'online',
        fireRiskIndex: 82
      }
    ];

    setStations(mockStations);
    setSelectedStation(mockStations[0].id);
  }, []);

  const refreshData = async () => {
    setLoading(true);
    setTimeout(() => {
      setLoading(false);
      // Update timestamps
      setStations(prev => prev.map(station => ({
        ...station,
        lastUpdate: new Date()
      })));
    }, 2000);
  };

  const getWindDirection = (degrees: number) => {
    const directions = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW'];
    return directions[Math.round(degrees / 22.5) % 16];
  };

  const getRiskColor = (risk: number) => {
    if (risk >= 90) return 'error';
    if (risk >= 70) return 'warning';
    if (risk >= 50) return 'info';
    return 'success';
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'online': return <CheckCircle color="success" />;
      case 'offline': return <Warning color="error" />;
      case 'maintenance': return <Warning color="warning" />;
      default: return <CheckCircle />;
    }
  };

  const selectedStationData = stations.find(s => s.id === selectedStation) || stations[0];
  const criticalStations = stations.filter(s => s.fireRiskIndex >= 90).length;
  const offlineStations = stations.filter(s => s.status === 'offline').length;

  return (
    <Card sx={{ height: '100%' }}>
      <CardHeader
        avatar={
          <Avatar sx={{ bgcolor: 'info.main' }}>
            <Thermostat />
          </Avatar>
        }
        title="RAWS Weather Network"
        subheader={
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 1 }}>
            <Typography variant="caption" color="text.secondary">
              Remote Automatic Weather Stations
            </Typography>
            <Chip
              label={`${stations.filter(s => s.status === 'online').length}/${stations.length} ONLINE`}
              color="success"
              size="small"
            />
          </Box>
        }
        action={
          <Tooltip title="Refresh Weather Data">
            <IconButton onClick={refreshData} disabled={loading}>
              <Refresh />
            </IconButton>
          </Tooltip>
        }
      />

      <CardContent>
        {loading && <LinearProgress sx={{ mb: 2 }} />}

        {/* Alert for Critical Conditions */}
        {criticalStations > 0 && (
          <Alert severity="error" sx={{ mb: 2 }}>
            <Typography variant="body2">
              <strong>Red Flag Conditions:</strong> {criticalStations} station{criticalStations > 1 ? 's' : ''}
              reporting extreme fire weather conditions.
            </Typography>
          </Alert>
        )}

        {offlineStations > 0 && (
          <Alert severity="warning" sx={{ mb: 2 }}>
            <Typography variant="body2">
              <strong>Network Status:</strong> {offlineStations} station{offlineStations > 1 ? 's' : ''} offline.
            </Typography>
          </Alert>
        )}

        {/* Current Conditions - Featured Station */}
        {selectedStationData && (
          <Box sx={{ mb: 3 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
              <LocationOn color="action" />
              <Typography variant="h6">
                {selectedStationData.name}
              </Typography>
              <Chip
                label={`Risk: ${selectedStationData.fireRiskIndex}%`}
                color={getRiskColor(selectedStationData.fireRiskIndex) as any}
                size="small"
              />
            </Box>

            <Grid container spacing={3}>
              <Grid item xs={6} md={3}>
                <Box sx={{ textAlign: 'center', p: 2, bgcolor: 'error.light', borderRadius: 1, color: 'white' }}>
                  <Thermostat sx={{ fontSize: 32, mb: 1 }} />
                  <Typography variant="h4">{selectedStationData.temperature}degF</Typography>
                  <Typography variant="body2">Temperature</Typography>
                </Box>
              </Grid>

              <Grid item xs={6} md={3}>
                <Box sx={{ textAlign: 'center', p: 2, bgcolor: 'primary.light', borderRadius: 1, color: 'white' }}>
                  <WaterDrop sx={{ fontSize: 32, mb: 1 }} />
                  <Typography variant="h4">{selectedStationData.humidity}%</Typography>
                  <Typography variant="body2">Humidity</Typography>
                </Box>
              </Grid>

              <Grid item xs={6} md={3}>
                <Box sx={{ textAlign: 'center', p: 2, bgcolor: 'info.light', borderRadius: 1, color: 'white' }}>
                  <Air sx={{ fontSize: 32, mb: 1 }} />
                  <Typography variant="h4">{selectedStationData.windSpeed}</Typography>
                  <Typography variant="body2">mph {getWindDirection(selectedStationData.windDirection)}</Typography>
                </Box>
              </Grid>

              <Grid item xs={6} md={3}>
                <Box sx={{ textAlign: 'center', p: 2, bgcolor: 'warning.light', borderRadius: 1, color: 'white' }}>
                  <Speed sx={{ fontSize: 32, mb: 1 }} />
                  <Typography variant="h4">{selectedStationData.windGust}</Typography>
                  <Typography variant="body2">Gust (mph)</Typography>
                </Box>
              </Grid>
            </Grid>

            {/* Fuel Moisture */}
            <Box sx={{ mt: 2, p: 2, bgcolor: 'grey.100', borderRadius: 1 }}>
              <Typography variant="subtitle2" gutterBottom>
                Critical Fire Weather Parameters
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={4}>
                  <Typography variant="body2" color="text.secondary">Fuel Moisture</Typography>
                  <Typography variant="h6" color={selectedStationData.fuelMoisture < 10 ? 'error.main' : 'text.primary'}>
                    {selectedStationData.fuelMoisture}%
                  </Typography>
                </Grid>
                <Grid item xs={4}>
                  <Typography variant="body2" color="text.secondary">Fuel Temperature</Typography>
                  <Typography variant="h6">{selectedStationData.fuelTemperature}degF</Typography>
                </Grid>
                <Grid item xs={4}>
                  <Typography variant="body2" color="text.secondary">Solar Radiation</Typography>
                  <Typography variant="h6">{selectedStationData.solarRadiation} W/m²</Typography>
                </Grid>
              </Grid>
            </Box>
          </Box>
        )}

        <Divider sx={{ my: 2 }} />

        {/* All Stations Summary */}
        <Typography variant="h6" gutterBottom>
          Network Status
        </Typography>

        <TableContainer sx={{ maxHeight: 250 }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Station</TableCell>
                <TableCell>Temp</TableCell>
                <TableCell>Humidity</TableCell>
                <TableCell>Wind</TableCell>
                <TableCell>Risk</TableCell>
                <TableCell>Status</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {stations.map((station) => (
                <TableRow
                  key={station.id}
                  hover
                  onClick={() => setSelectedStation(station.id)}
                  sx={{ cursor: 'pointer', bgcolor: selectedStation === station.id ? 'action.selected' : 'inherit' }}
                >
                  <TableCell>
                    <Box>
                      <Typography variant="body2" fontWeight="medium">
                        {station.name}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {station.location}
                      </Typography>
                    </Box>
                  </TableCell>

                  <TableCell>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                      <Typography variant="body2" color={station.temperature > 85 ? 'error.main' : 'text.primary'}>
                        {station.temperature}degF
                      </Typography>
                      {station.temperature > 90 ? <TrendingUp color="error" fontSize="small" /> :
                       station.temperature < 75 ? <TrendingDown color="success" fontSize="small" /> :
                       <TrendingFlat color="action" fontSize="small" />}
                    </Box>
                  </TableCell>

                  <TableCell>
                    <Typography variant="body2" color={station.humidity < 15 ? 'error.main' : 'text.primary'}>
                      {station.humidity}%
                    </Typography>
                  </TableCell>

                  <TableCell>
                    <Box>
                      <Typography variant="body2">
                        {station.windSpeed} mph
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {getWindDirection(station.windDirection)} * G{station.windGust}
                      </Typography>
                    </Box>
                  </TableCell>

                  <TableCell>
                    <Chip
                      label={`${station.fireRiskIndex}%`}
                      color={getRiskColor(station.fireRiskIndex) as any}
                      size="small"
                    />
                  </TableCell>

                  <TableCell>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                      {getStatusIcon(station.status)}
                      <Typography variant="caption">
                        {Math.round((Date.now() - station.lastUpdate.getTime()) / 60000)}m ago
                      </Typography>
                    </Box>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>

        <Alert severity="info" sx={{ mt: 2 }}>
          <Typography variant="body2">
            <strong>RAWS Network:</strong> Remote Automatic Weather Stations operated by CAL FIRE,
            NIFC, and partner agencies provide critical fire weather data for decision making.
          </Typography>
        </Alert>
      </CardContent>
    </Card>
  );
};

export default RAWSWeatherWidget;