import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Card,
  CardContent,
  Grid,
  Chip,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Tooltip,
  LinearProgress,
} from '@mui/material';
import {
  LocalFireDepartment,
  AirplanemodeActive,
  DirectionsCarFilled,
  People,
  Visibility,
  LocationOn,
} from '@mui/icons-material';

interface Resource {
  id: string;
  type: 'engine' | 'helicopter' | 'crew' | 'aircraft';
  name: string;
  location: string;
  status: 'available' | 'deployed' | 'maintenance' | 'offline';
  personnel: number;
  assignedIncident?: string;
}

const ResourcesPage: React.FC = () => {
  const [resources, setResources] = useState<Resource[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Simulate API call
    const fetchResources = async () => {
      setLoading(true);
      try {
        // Mock data - replace with actual API call
        const mockResources: Resource[] = [
          {
            id: '1',
            type: 'engine',
            name: 'Engine 15',
            location: 'Station 15, Riverside',
            status: 'deployed',
            personnel: 4,
            assignedIncident: 'Riverside Fire',
          },
          {
            id: '2',
            type: 'helicopter',
            name: 'Air Rescue 1',
            location: 'Air Base, San Bernardino',
            status: 'available',
            personnel: 2,
          },
          {
            id: '3',
            type: 'crew',
            name: 'Hotshot Crew Alpha',
            location: 'Base Camp, Riverside',
            status: 'deployed',
            personnel: 20,
            assignedIncident: 'Riverside Fire',
          },
          {
            id: '4',
            type: 'aircraft',
            name: 'Air Tanker 42',
            location: 'Air Base, Ontario',
            status: 'maintenance',
            personnel: 2,
          },
        ];
        
        setResources(mockResources);
      } catch (error) {
        console.error('Failed to fetch resources:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchResources();
  }, []);

  const getResourceIcon = (type: string) => {
    switch (type) {
      case 'engine': return <LocalFireDepartment />;
      case 'helicopter': 
      case 'aircraft': return <AirplanemodeActive />;
      case 'crew': return <People />;
      default: return <DirectionsCarFilled />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'available': return 'success';
      case 'deployed': return 'warning';
      case 'maintenance': return 'info';
      case 'offline': return 'error';
      default: return 'default';
    }
  };

  const getResourceStats = () => {
    const total = resources.length;
    const available = resources.filter(r => r.status === 'available').length;
    const deployed = resources.filter(r => r.status === 'deployed').length;
    const maintenance = resources.filter(r => r.status === 'maintenance').length;
    
    return { total, available, deployed, maintenance };
  };

  const stats = getResourceStats();

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <Typography>Loading resources...</Typography>
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Resource Management
      </Typography>

      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" mb={1}>
                <LocalFireDepartment color="primary" sx={{ mr: 1 }} />
                <Typography variant="h6">Total Resources</Typography>
              </Box>
              <Typography variant="h4" color="primary">
                {stats.total}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" mb={1}>
                <Typography variant="h6">Available</Typography>
              </Box>
              <Typography variant="h4" color="success">
                {stats.available}
              </Typography>
              <LinearProgress
                variant="determinate"
                value={(stats.available / stats.total) * 100}
                color="success"
                sx={{ mt: 1 }}
              />
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" mb={1}>
                <Typography variant="h6">Deployed</Typography>
              </Box>
              <Typography variant="h4" color="warning">
                {stats.deployed}
              </Typography>
              <LinearProgress
                variant="determinate"
                value={(stats.deployed / stats.total) * 100}
                color="warning"
                sx={{ mt: 1 }}
              />
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" mb={1}>
                <Typography variant="h6">Maintenance</Typography>
              </Box>
              <Typography variant="h4" color="info">
                {stats.maintenance}
              </Typography>
              <LinearProgress
                variant="determinate"
                value={(stats.maintenance / stats.total) * 100}
                color="info"
                sx={{ mt: 1 }}
              />
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Paper>
        <Box p={2}>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
            <Typography variant="h6">Resource Details</Typography>
            <Button variant="contained" color="primary">
              Request Resource
            </Button>
          </Box>

          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Type</TableCell>
                  <TableCell>Name</TableCell>
                  <TableCell>Location</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Personnel</TableCell>
                  <TableCell>Assignment</TableCell>
                  <TableCell>Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {resources.map((resource) => (
                  <TableRow key={resource.id} hover>
                    <TableCell>
                      <Box display="flex" alignItems="center">
                        {getResourceIcon(resource.type)}
                        <Typography variant="body2" sx={{ ml: 1, textTransform: 'capitalize' }}>
                          {resource.type}
                        </Typography>
                      </Box>
                    </TableCell>
                    <TableCell>
                      <Typography variant="subtitle2">
                        {resource.name}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Box display="flex" alignItems="center">
                        <LocationOn fontSize="small" sx={{ mr: 0.5 }} />
                        {resource.location}
                      </Box>
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={resource.status.toUpperCase()}
                        color={getStatusColor(resource.status) as any}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>
                      <Box display="flex" alignItems="center">
                        <People fontSize="small" sx={{ mr: 0.5 }} />
                        {resource.personnel}
                      </Box>
                    </TableCell>
                    <TableCell>
                      {resource.assignedIncident ? (
                        <Typography variant="body2" color="primary">
                          {resource.assignedIncident}
                        </Typography>
                      ) : (
                        <Typography variant="body2" color="text.secondary">
                          Unassigned
                        </Typography>
                      )}
                    </TableCell>
                    <TableCell>
                      <Tooltip title="View Details">
                        <IconButton size="small">
                          <Visibility />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="View on Map">
                        <IconButton size="small">
                          <LocationOn />
                        </IconButton>
                      </Tooltip>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </Box>
      </Paper>
    </Box>
  );
};

export default ResourcesPage;