import React, { useEffect, useState } from 'react';
import {
  Card,
  CardContent,
  Typography,
  Box,
  Chip,
  CircularProgress,
  List,
  ListItem,
  ListItemText,
  IconButton,
  Tooltip,
  Grid,
} from '@mui/material';
import {
  Satellite,
  Refresh as RefreshIcon,
  Whatshot,
  Speed,
  LocationOn,
} from '@mui/icons-material';
import { formatDistanceToNow } from 'date-fns';

interface FireSatDetection {
  id: number;
  timestamp: string;
  latitude: number;
  longitude: number;
  brightness_kelvin: number;
  fire_radiative_power: number;
  fire_area_m2: number;
  confidence: number;
  satellite_id: string;
  detection_id: string;
  simulation_mode?: string;
}

interface FireSatWidgetProps {
  autoRefresh?: boolean;
  refreshInterval?: number;
}

const FireSatWidget: React.FC<FireSatWidgetProps> = ({
  autoRefresh = true,
  refreshInterval = 30000,
}) => {
  const [detections, setDetections] = useState<FireSatDetection[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  const fetchDetections = async () => {
    try {
      setIsLoading(true);
      const response = await fetch(
        'http://localhost:8004/consume/latest/firesat_detections?limit=50'
      );

      if (!response.ok) {
        throw new Error('Failed to fetch FireSat data');
      }

      const data = await response.json();
      setDetections(data.data || []);
      setLastUpdate(new Date());
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      console.error('Error fetching FireSat data:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchDetections();
  }, []);

  useEffect(() => {
    if (autoRefresh) {
      const interval = setInterval(fetchDetections, refreshInterval);
      return () => clearInterval(interval);
    }
  }, [autoRefresh, refreshInterval]);

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.9) return 'success';
    if (confidence >= 0.7) return 'warning';
    return 'error';
  };

  const totalFRP = detections.reduce((sum, d) => sum + (d.fire_radiative_power || 0), 0);
  const avgConfidence = detections.length > 0
    ? detections.reduce((sum, d) => sum + d.confidence, 0) / detections.length
    : 0;
  const highConfidenceCount = detections.filter(d => d.confidence >= 0.8).length;

  return (
    <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <CardContent>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
          <Box display="flex" alignItems="center" gap={1}>
            <Satellite color="primary" />
            <Typography variant="h6">
              🛰️ FireSat Detections
            </Typography>
          </Box>
          <Box display="flex" alignItems="center" gap={1}>
            <Typography variant="caption" color="textSecondary">
              {formatDistanceToNow(lastUpdate, { addSuffix: true })}
            </Typography>
            <IconButton size="small" onClick={fetchDetections} disabled={isLoading}>
              <RefreshIcon />
            </IconButton>
          </Box>
        </Box>

        {/* Summary Stats */}
        <Grid container spacing={2} sx={{ mb: 2 }}>
          <Grid item xs={4}>
            <Box textAlign="center">
              <Typography variant="h4" color="error">
                {detections.length}
              </Typography>
              <Typography variant="caption" color="textSecondary">
                Total Detections
              </Typography>
            </Box>
          </Grid>
          <Grid item xs={4}>
            <Box textAlign="center">
              <Typography variant="h4" color="warning.main">
                {highConfidenceCount}
              </Typography>
              <Typography variant="caption" color="textSecondary">
                High Confidence
              </Typography>
            </Box>
          </Grid>
          <Grid item xs={4}>
            <Box textAlign="center">
              <Typography variant="h4" color="info.main">
                {totalFRP.toFixed(0)}
              </Typography>
              <Typography variant="caption" color="textSecondary">
                Total FRP (MW)
              </Typography>
            </Box>
          </Grid>
        </Grid>

        {isLoading && detections.length === 0 ? (
          <Box display="flex" justifyContent="center" p={3}>
            <CircularProgress />
          </Box>
        ) : error ? (
          <Box p={2} bgcolor="error.light" borderRadius={1}>
            <Typography color="error">{error}</Typography>
          </Box>
        ) : detections.length === 0 ? (
          <Box p={2} bgcolor="info.light" borderRadius={1}>
            <Typography color="info.dark">
              No active FireSat detections in the past 24 hours
            </Typography>
            <Typography variant="caption" color="info.dark">
              NOS Testbed simulation may not have generated detections due to orbital mechanics
            </Typography>
          </Box>
        ) : (
          <List sx={{ maxHeight: 400, overflow: 'auto' }}>
            {detections.slice(0, 10).map((detection) => (
              <ListItem
                key={detection.detection_id}
                sx={{
                  border: '1px solid',
                  borderColor: 'divider',
                  borderRadius: 1,
                  mb: 1,
                }}
              >
                <ListItemText
                  primary={
                    <Box display="flex" alignItems="center" gap={1} flexWrap="wrap">
                      <Chip
                        label={detection.satellite_id || 'Unknown'}
                        size="small"
                        color="primary"
                        variant="outlined"
                      />
                      <Chip
                        label={`${(detection.confidence * 100).toFixed(0)}%`}
                        size="small"
                        color={getConfidenceColor(detection.confidence)}
                      />
                      {detection.simulation_mode && (
                        <Chip
                          label={detection.simulation_mode}
                          size="small"
                          color="info"
                          variant="outlined"
                        />
                      )}
                    </Box>
                  }
                  secondary={
                    <Box mt={1}>
                      <Box display="flex" alignItems="center" gap={2} flexWrap="wrap">
                        <Tooltip title="Location">
                          <Box display="flex" alignItems="center" gap={0.5}>
                            <LocationOn fontSize="small" />
                            <Typography variant="caption">
                              {detection.latitude.toFixed(4)}, {detection.longitude.toFixed(4)}
                            </Typography>
                          </Box>
                        </Tooltip>
                        <Tooltip title="Fire Radiative Power">
                          <Box display="flex" alignItems="center" gap={0.5}>
                            <Whatshot fontSize="small" />
                            <Typography variant="caption">
                              {detection.fire_radiative_power?.toFixed(1) || 0} MW
                            </Typography>
                          </Box>
                        </Tooltip>
                        <Tooltip title="Temperature">
                          <Box display="flex" alignItems="center" gap={0.5}>
                            <Speed fontSize="small" />
                            <Typography variant="caption">
                              {detection.brightness_kelvin?.toFixed(0) || 0} K
                            </Typography>
                          </Box>
                        </Tooltip>
                      </Box>
                      <Typography variant="caption" color="textSecondary" display="block" mt={0.5}>
                        {formatDistanceToNow(new Date(detection.timestamp), { addSuffix: true })}
                      </Typography>
                    </Box>
                  }
                />
              </ListItem>
            ))}
          </List>
        )}

        {detections.length > 10 && (
          <Box mt={1}>
            <Typography variant="caption" color="textSecondary">
              Showing 10 of {detections.length} detections
            </Typography>
          </Box>
        )}
      </CardContent>
    </Card>
  );
};

export default FireSatWidget;
