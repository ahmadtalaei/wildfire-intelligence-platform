import React from 'react';
import {
  Paper,
  Typography,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Chip,
  Box,
  IconButton,
  Tooltip,
  Divider,
} from '@mui/material';
import {
  LocalFireDepartment,
  Visibility,
  LocationOn,
  Schedule,
} from '@mui/icons-material';

interface Incident {
  id: string;
  name: string;
  location: string;
  status: 'active' | 'contained' | 'controlled' | 'extinguished';
  severity: 'low' | 'medium' | 'high' | 'critical';
  startTime: string;
  acres: number;
  containment: number;
}

interface ActiveIncidentsListProps {
  incidents?: Incident[];
  loading?: boolean;
  onViewDetails?: (incident: Incident) => void;
}

const ActiveIncidentsList: React.FC<ActiveIncidentsListProps> = ({
  incidents = [],
  loading = false,
  onViewDetails,
}) => {
  // Mock data if no incidents provided
  const mockIncidents: Incident[] = [
    {
      id: '1',
      name: 'Riverside Fire',
      location: 'Riverside County',
      status: 'active',
      severity: 'high',
      startTime: '2 hours ago',
      acres: 2450,
      containment: 25,
    },
    {
      id: '2',
      name: 'Mountain View Fire',
      location: 'San Bernardino County',
      status: 'contained',
      severity: 'medium',
      startTime: '1 day ago',
      acres: 850,
      containment: 85,
    },
    {
      id: '3',
      name: 'Desert Hills Fire',
      location: 'Imperial County',
      status: 'active',
      severity: 'critical',
      startTime: '30 minutes ago',
      acres: 125,
      containment: 0,
    },
  ];

  const displayIncidents = incidents.length > 0 ? incidents : mockIncidents;

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'error';
      case 'contained':
        return 'warning';
      case 'controlled':
        return 'info';
      case 'extinguished':
        return 'success';
      default:
        return 'default';
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'error';
      case 'high':
        return 'warning';
      case 'medium':
        return 'info';
      case 'low':
        return 'success';
      default:
        return 'default';
    }
  };

  if (loading) {
    return (
      <Paper sx={{ p: 2 }}>
        <Typography variant="h6" gutterBottom>
          Active Incidents
        </Typography>
        <Box display="flex" justifyContent="center" py={4}>
          <Typography color="text.secondary">Loading incidents...</Typography>
        </Box>
      </Paper>
    );
  }

  return (
    <Paper sx={{ p: 2 }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="h6">
          Active Incidents
        </Typography>
        <Chip
          label={`${displayIncidents.filter(i => i.status === 'active').length} Active`}
          color="error"
          size="small"
        />
      </Box>

      {displayIncidents.length === 0 ? (
        <Box textAlign="center" py={4}>
          <LocalFireDepartment sx={{ fontSize: 48, color: 'text.disabled', mb: 1 }} />
          <Typography color="text.secondary">
            No active incidents at this time
          </Typography>
        </Box>
      ) : (
        <List dense>
          {displayIncidents.map((incident, index) => (
            <React.Fragment key={incident.id}>
              <ListItem
                sx={{
                  px: 0,
                  '&:hover': {
                    backgroundColor: 'action.hover',
                    borderRadius: 1,
                  },
                }}
              >
                <ListItemIcon>
                  <LocalFireDepartment 
                    color={getSeverityColor(incident.severity) as any}
                  />
                </ListItemIcon>
                
                <ListItemText
                  primary={
                    <Box display="flex" alignItems="center" gap={1}>
                      <Typography variant="subtitle2" fontWeight="medium">
                        {incident.name}
                      </Typography>
                      <Chip
                        label={incident.status.toUpperCase()}
                        size="small"
                        color={getStatusColor(incident.status) as any}
                      />
                      <Chip
                        label={incident.severity.toUpperCase()}
                        size="small"
                        variant="outlined"
                        color={getSeverityColor(incident.severity) as any}
                      />
                    </Box>
                  }
                  secondary={
                    <Box>
                      <Box display="flex" alignItems="center" gap={0.5} mb={0.5}>
                        <LocationOn fontSize="small" color="action" />
                        <Typography variant="body2" color="text.secondary">
                          {incident.location}
                        </Typography>
                      </Box>
                      
                      <Box display="flex" alignItems="center" gap={2} flexWrap="wrap">
                        <Box display="flex" alignItems="center" gap={0.5}>
                          <Schedule fontSize="small" color="action" />
                          <Typography variant="body2" color="text.secondary">
                            {incident.startTime}
                          </Typography>
                        </Box>
                        
                        <Typography variant="body2" color="text.secondary">
                          {incident.acres.toLocaleString()} acres
                        </Typography>
                        
                        <Typography variant="body2" color="text.secondary">
                          {incident.containment}% contained
                        </Typography>
                      </Box>
                    </Box>
                  }
                />

                <Box display="flex" alignItems="center">
                  <Tooltip title="View Details">
                    <IconButton
                      size="small"
                      onClick={() => onViewDetails?.(incident)}
                    >
                      <Visibility fontSize="small" />
                    </IconButton>
                  </Tooltip>
                </Box>
              </ListItem>
              
              {index < displayIncidents.length - 1 && <Divider />}
            </React.Fragment>
          ))}
        </List>
      )}
    </Paper>
  );
};

export default ActiveIncidentsList;