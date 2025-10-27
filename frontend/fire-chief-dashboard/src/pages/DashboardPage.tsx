import React, { useEffect, useState } from 'react';
import {
  Grid,
  Paper,
  Typography,
  Box,
  Card,
  CardContent,
  IconButton,
  Chip,
  CircularProgress,
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  TrendingUp,
  LocalFireDepartment,
  Warning,
  People,
  Speed,
  Landscape,
  EmojiEvents,
  CheckCircle,
  Whatshot,
} from '@mui/icons-material';
import { useDispatch, useSelector } from 'react-redux';

import { RootState } from '../store/store';
import { fetchDashboardData } from '../store/slices/dashboardSlice';
import MetricCard from '../components/Dashboard/MetricCard';
import SimpleMap from '../components/WildfireMap/SimpleMap';
import ActiveIncidentsList from '../components/Dashboard/ActiveIncidentsList';
import ResourceStatus from '../components/Dashboard/ResourceStatus';
import NASAFIRMSWidget from '../components/Dashboard/NASAFIRMSWidget';
import RAWSWeatherWidget from '../components/Dashboard/RAWSWeatherWidget';
import HistoricalFirePerimeters from '../components/Dashboard/HistoricalFirePerimeters';
import IoTSensorNetwork from '../components/Dashboard/IoTSensorNetwork';
import LandsatVegetationIndex from '../components/Dashboard/LandsatVegetationIndex';
import CALFIRERiskModel from '../components/Dashboard/CALFIRERiskModel';
import { formatDistanceToNow } from 'date-fns';

const DashboardPage: React.FC = () => {
  const dispatch = useDispatch();
  const {
    metrics,
    fireRiskData,
    activeIncidents,
    isLoading,
    lastUpdated
  } = useSelector((state: RootState) => state.dashboard);

  const [autoRefresh, setAutoRefresh] = useState(true);
  const [mapCenter] = useState<[number, number]>([37.7749, -122.4194]);
  const [selectedLayers, setSelectedLayers] = useState({
    activeFires: true,
    firePerimeters: true,
    windVectors: true,
    temperature: false,
    humidity: false,
    vegetation: true,
    population: false,
    infrastructure: true,
    predictions: false,
    iotSensors: true,
    precipitation: false,
    hazardZones: true,
    helicopterLanding: true,
    waterSources: true,
    emergencyServices: true,
    communicationTowers: true,
    wildlandUrbanInterface: true,
    evacuationRoutes: true,
    fuelAnalysis: true,
    weatherStations: true
  });

  useEffect(() => {
    dispatch(fetchDashboardData() as any);
  }, [dispatch]);

  useEffect(() => {
    let interval: NodeJS.Timeout;

    if (autoRefresh) {
      interval = setInterval(() => {
        dispatch(fetchDashboardData() as any);
      }, 30000); // Refresh every 30 seconds
    }

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [dispatch, autoRefresh]);

  const handleRefresh = () => {
    dispatch(fetchDashboardData() as any);
  };

  const handleLayerToggle = (layer: keyof typeof selectedLayers) => {
    setSelectedLayers(prev => ({
      ...prev,
      [layer]: !prev[layer]
    }));
  };

  const getRiskLevelColor = (level: string) => {
    switch (level.toLowerCase()) {
      case 'low': return 'success';
      case 'medium': return 'warning';
      case 'high': return 'error';
      case 'extreme': return 'error';
      default: return 'default';
    }
  };

  if (isLoading && !metrics) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="60vh">
        <CircularProgress size={60} />
      </Box>
    );
  }

  return (
    <Box sx={{ flexGrow: 1, p: 3 }}>
      {/* CAL FIRE Branding Header */}
      <Box sx={{
        display: 'flex',
        alignItems: 'center',
        mb: 3,
        pb: 2,
        borderBottom: '3px solid #D32F2F' // CAL FIRE red
      }}>
        <Box sx={{
          width: 60,
          height: 60,
          borderRadius: '50%',
          bgcolor: '#D32F2F',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          mr: 2
        }}>
          <Whatshot sx={{ fontSize: 40, color: 'white' }} />
        </Box>
        <Box sx={{ flex: 1 }}>
          <Typography variant="h4" fontWeight="bold" sx={{ color: '#D32F2F' }}>
            CAL FIRE Intelligence Center
          </Typography>
          <Typography variant="subtitle1" color="text.secondary">
            Fire Chief Command Dashboard
          </Typography>
        </Box>
        <Box display="flex" alignItems="center" gap={2}>
          {lastUpdated && (
            <Typography variant="body2" color="textSecondary">
              Last updated: {formatDistanceToNow(new Date(lastUpdated), { addSuffix: true })}
            </Typography>
          )}
          <IconButton onClick={handleRefresh} disabled={isLoading}>
            <RefreshIcon />
          </IconButton>
        </Box>
      </Box>

      {/* Achievement Chips */}
      <Box sx={{ mb: 2, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
        {metrics?.averageResponseTime && metrics.averageResponseTime < 15 && (
          <Chip
            icon={<EmojiEvents />}
            label="⚡ Fast Response - Under 15 min!"
            color="success"
            sx={{
              fontWeight: 'bold',
              animation: 'fadeIn 0.5s',
              '@keyframes fadeIn': {
                from: { opacity: 0, transform: 'translateY(-10px)' },
                to: { opacity: 1, transform: 'translateY(0)' }
              }
            }}
          />
        )}
        {metrics?.activeIncidents === 0 && (
          <Chip
            icon={<CheckCircle />}
            label="🌟 All Clear - No Active Incidents!"
            color="success"
            sx={{ fontWeight: 'bold' }}
          />
        )}
        {metrics?.resourcesDeployed && metrics.resourcesDeployed > 50 && (
          <Chip
            icon={<People />}
            label="💪 Full Team Deployment"
            color="info"
            sx={{ fontWeight: 'bold' }}
          />
        )}
        {metrics?.acresBurnedToday !== undefined && metrics.acresBurnedToday < 100 && (
          <Chip
            icon={<CheckCircle />}
            label="🏆 Excellent Containment Today!"
            color="success"
            sx={{ fontWeight: 'bold' }}
          />
        )}
      </Box>

      {/* Key Metrics */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={2}>
          <MetricCard
            title="Active Incidents"
            value={metrics?.activeIncidents || 0}
            icon={<LocalFireDepartment />}
            color="error"
            trend="up"
            trendValue="+2"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={2}>
          <MetricCard
            title="High Risk Areas"
            value={metrics?.highRiskAreas || 0}
            icon={<Warning />}
            color="warning"
            trend="up"
            trendValue="+15%"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={2}>
          <MetricCard
            title="Resources Deployed"
            value={metrics?.resourcesDeployed || 0}
            icon={<People />}
            color="info"
            trend="down"
            trendValue="-8%"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={2}>
          <MetricCard
            title="Acres Burned Today"
            value={metrics?.acresBurnedToday || 0}
            icon={<Landscape />}
            color="error"
            unit="acres"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={2}>
          <MetricCard
            title="Avg Response Time"
            value={metrics?.averageResponseTime || 0}
            icon={<Speed />}
            color="success"
            unit="min"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={2}>
          <MetricCard
            title="Total This Year"
            value={metrics?.totalIncidents || 0}
            icon={<TrendingUp />}
            color="info"
          />
        </Grid>
      </Grid>

      <Grid container spacing={3}>
        {/* Simple California Map */}
        <Grid item xs={12}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              California Wildfire Map
            </Typography>
            <SimpleMap height="600px" />
          </Paper>
        </Grid>

        {/* Real-time Data Sources */}
        <Grid item xs={12} lg={6}>
          <NASAFIRMSWidget />
        </Grid>

        <Grid item xs={12} lg={6}>
          <RAWSWeatherWidget />
        </Grid>

        {/* RAWS Weather Network */}
        <Grid item xs={12} lg={6}>
          <RAWSWeatherWidget />
        </Grid>

        {/* IoT Sensor Network */}
        <Grid item xs={12} lg={6}>
          <IoTSensorNetwork />
        </Grid>

        {/* CAL FIRE Proprietary Risk Model */}
        <Grid item xs={12} lg={8}>
          <CALFIRERiskModel />
        </Grid>

        {/* Landsat Vegetation Analysis */}
        <Grid item xs={12} lg={4}>
          <LandsatVegetationIndex />
        </Grid>

        {/* Historical Fire Data */}
        <Grid item xs={12}>
          <HistoricalFirePerimeters />
        </Grid>

        {/* Active Incidents */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Active Incidents
            </Typography>
            <ActiveIncidentsList />
          </Paper>
        </Grid>

        {/* Resource Status */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Resource Deployment Status
            </Typography>
            <ResourceStatus />
          </Paper>
        </Grid>

        {/* Fire Risk Summary */}
        <Grid item xs={12}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Current Fire Risk Assessment
            </Typography>
            <Grid container spacing={2}>
              {fireRiskData.slice(0, 6).map((risk) => (
                <Grid item xs={12} sm={6} md={4} lg={2} key={risk.id}>
                  <Card variant="outlined">
                    <CardContent sx={{ textAlign: 'center', py: 2 }}>
                      <Typography variant="body2" color="textSecondary" gutterBottom>
                        {risk.location.name}
                      </Typography>
                      <Chip
                        label={risk.riskLevel.toUpperCase()}
                        color={getRiskLevelColor(risk.riskLevel) as any}
                        size="small"
                        sx={{ mb: 1 }}
                      />
                      <Typography variant="h6" component="div">
                        {(risk.riskScore * 100).toFixed(0)}%
                      </Typography>
                      <Typography variant="caption" color="textSecondary">
                        Risk Score
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

export default DashboardPage;