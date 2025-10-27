import React from 'react';
import {
  Paper,
  Typography,
  Grid,
  Box,
  Chip,
  LinearProgress,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Avatar,
  Divider,
} from '@mui/material';
import {
  LocalFireDepartment,
  AirplanemodeActive,
  DirectionsCarFilled,
  People,
  CheckCircle,
  Warning,
  Build,
  Cancel,
} from '@mui/icons-material';

interface ResourceData {
  type: 'engine' | 'helicopter' | 'crew' | 'aircraft';
  name: string;
  status: 'available' | 'deployed' | 'maintenance' | 'offline';
  location?: string;
  personnel?: number;
}

interface ResourceStats {
  total: number;
  available: number;
  deployed: number;
  maintenance: number;
  offline: number;
}

interface ResourceStatusProps {
  resources?: ResourceData[];
  stats?: ResourceStats;
  loading?: boolean;
}

const ResourceStatus: React.FC<ResourceStatusProps> = ({
  resources = [],
  stats,
  loading = false,
}) => {
  // Mock data if no resources provided
  const mockResources: ResourceData[] = [
    {
      type: 'engine',
      name: 'Engine 15',
      status: 'deployed',
      location: 'Riverside Fire',
      personnel: 4,
    },
    {
      type: 'helicopter',
      name: 'Air Rescue 1',
      status: 'available',
      location: 'Base Station',
      personnel: 2,
    },
    {
      type: 'crew',
      name: 'Hotshot Crew Alpha',
      status: 'deployed',
      location: 'Mountain Fire',
      personnel: 20,
    },
    {
      type: 'aircraft',
      name: 'Air Tanker 42',
      status: 'maintenance',
      location: 'Maintenance Hangar',
      personnel: 2,
    },
    {
      type: 'engine',
      name: 'Engine 22',
      status: 'available',
      location: 'Station 22',
      personnel: 4,
    },
  ];

  // Mock stats if not provided
  const mockStats: ResourceStats = {
    total: 25,
    available: 18,
    deployed: 5,
    maintenance: 2,
    offline: 0,
  };

  const displayResources = resources.length > 0 ? resources : mockResources;
  const displayStats = stats || mockStats;

  const getResourceIcon = (type: string) => {
    switch (type) {
      case 'engine':
        return <LocalFireDepartment />;
      case 'helicopter':
      case 'aircraft':
        return <AirplanemodeActive />;
      case 'crew':
        return <People />;
      default:
        return <DirectionsCarFilled />;
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'available':
        return <CheckCircle color="success" />;
      case 'deployed':
        return <Warning color="warning" />;
      case 'maintenance':
        return <Build color="info" />;
      case 'offline':
        return <Cancel color="error" />;
      default:
        return <CheckCircle />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'available':
        return 'success';
      case 'deployed':
        return 'warning';
      case 'maintenance':
        return 'info';
      case 'offline':
        return 'error';
      default:
        return 'default';
    }
  };

  if (loading) {
    return (
      <Paper sx={{ p: 2 }}>
        <Typography variant="h6" gutterBottom>
          Resource Status
        </Typography>
        <Box display="flex" justifyContent="center" py={4}>
          <Typography color="text.secondary">Loading resource data...</Typography>
        </Box>
      </Paper>
    );
  }

  return (
    <Paper sx={{ p: 2 }}>
      <Typography variant="h6" gutterBottom>
        Resource Status
      </Typography>

      {/* Resource Statistics */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={3}>
          <Box textAlign="center">
            <Typography variant="h4" color="primary" fontWeight="bold">
              {displayStats.total}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Total
            </Typography>
          </Box>
        </Grid>

        <Grid item xs={3}>
          <Box textAlign="center">
            <Typography variant="h4" color="success.main" fontWeight="bold">
              {displayStats.available}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Available
            </Typography>
          </Box>
        </Grid>

        <Grid item xs={3}>
          <Box textAlign="center">
            <Typography variant="h4" color="warning.main" fontWeight="bold">
              {displayStats.deployed}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Deployed
            </Typography>
          </Box>
        </Grid>

        <Grid item xs={3}>
          <Box textAlign="center">
            <Typography variant="h4" color="info.main" fontWeight="bold">
              {displayStats.maintenance}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Maintenance
            </Typography>
          </Box>
        </Grid>
      </Grid>

      {/* Availability Progress Bar */}
      <Box sx={{ mb: 2 }}>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
          <Typography variant="body2" color="text.secondary">
            Resource Availability
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {Math.round((displayStats.available / displayStats.total) * 100)}%
          </Typography>
        </Box>
        <LinearProgress
          variant="determinate"
          value={(displayStats.available / displayStats.total) * 100}
          color="success"
          sx={{
            height: 8,
            borderRadius: 4,
            backgroundColor: 'grey.200',
          }}
        />
      </Box>

      <Divider sx={{ mb: 2 }} />

      {/* Recent Resource Activity */}
      <Box>
        <Typography variant="subtitle2" gutterBottom fontWeight="medium">
          Recent Activity
        </Typography>
        
        <List dense sx={{ maxHeight: 300, overflow: 'auto' }}>
          {displayResources.slice(0, 5).map((resource, index) => (
            <ListItem key={index} sx={{ px: 0 }}>
              <ListItemIcon>
                <Avatar sx={{ width: 32, height: 32, bgcolor: 'primary.light' }}>
                  {getResourceIcon(resource.type)}
                </Avatar>
              </ListItemIcon>
              
              <ListItemText
                primary={
                  <Box display="flex" alignItems="center" gap={1}>
                    <Typography variant="subtitle2">
                      {resource.name}
                    </Typography>
                    <Chip
                      label={resource.status.toUpperCase()}
                      size="small"
                      color={getStatusColor(resource.status) as any}
                      icon={getStatusIcon(resource.status)}
                    />
                  </Box>
                }
                secondary={
                  <Box>
                    <Typography variant="body2" color="text.secondary">
                      {resource.location}
                    </Typography>
                    {resource.personnel && (
                      <Typography variant="body2" color="text.secondary">
                        Personnel: {resource.personnel}
                      </Typography>
                    )}
                  </Box>
                }
              />
            </ListItem>
          ))}
        </List>
      </Box>

      {/* Quick Actions */}
      <Box sx={{ mt: 2, p: 1, backgroundColor: 'grey.50', borderRadius: 1 }}>
        <Typography variant="body2" color="text.secondary" gutterBottom>
          Quick Actions:
        </Typography>
        <Box display="flex" gap={1} flexWrap="wrap">
          <Chip
            label="Request Resource"
            size="small"
            variant="outlined"
            color="primary"
            clickable
          />
          <Chip
            label="View All Resources"
            size="small"
            variant="outlined"
            color="primary"
            clickable
          />
          <Chip
            label="Deployment Map"
            size="small"
            variant="outlined"
            color="primary"
            clickable
          />
        </Box>
      </Box>
    </Paper>
  );
};

export default ResourceStatus;