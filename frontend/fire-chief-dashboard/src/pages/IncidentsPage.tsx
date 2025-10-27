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
} from '@mui/material';
import {
  Warning,
  LocationOn,
  CalendarToday,
  Visibility,
  Edit,
} from '@mui/icons-material';

interface Incident {
  id: string;
  name: string;
  location: string;
  status: 'active' | 'contained' | 'controlled' | 'extinguished';
  severity: 'low' | 'medium' | 'high' | 'critical';
  startDate: string;
  acres: number;
  containmentPercentage: number;
}

const IncidentsPage: React.FC = () => {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Simulate API call
    const fetchIncidents = async () => {
      setLoading(true);
      try {
        // Mock data - replace with actual API call
        const mockIncidents: Incident[] = [
          {
            id: '1',
            name: 'Riverside Fire',
            location: 'Riverside County, CA',
            status: 'active',
            severity: 'high',
            startDate: '2024-09-10',
            acres: 2450,
            containmentPercentage: 25,
          },
          {
            id: '2',
            name: 'Mountain View Fire',
            location: 'San Bernardino County, CA',
            status: 'contained',
            severity: 'medium',
            startDate: '2024-09-08',
            acres: 850,
            containmentPercentage: 85,
          },
        ];
        
        setIncidents(mockIncidents);
      } catch (error) {
        console.error('Failed to fetch incidents:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchIncidents();
  }, []);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'error';
      case 'contained': return 'warning';
      case 'controlled': return 'info';
      case 'extinguished': return 'success';
      default: return 'default';
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'error';
      case 'high': return 'warning';
      case 'medium': return 'info';
      case 'low': return 'success';
      default: return 'default';
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <Typography>Loading incidents...</Typography>
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Active Incidents
      </Typography>

      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" mb={1}>
                <Warning color="error" sx={{ mr: 1 }} />
                <Typography variant="h6">Active Fires</Typography>
              </Box>
              <Typography variant="h4" color="error">
                {incidents.filter(i => i.status === 'active').length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" mb={1}>
                <LocationOn color="info" sx={{ mr: 1 }} />
                <Typography variant="h6">Total Acres</Typography>
              </Box>
              <Typography variant="h4" color="info">
                {incidents.reduce((sum, i) => sum + i.acres, 0).toLocaleString()}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" mb={1}>
                <CalendarToday color="warning" sx={{ mr: 1 }} />
                <Typography variant="h6">New Today</Typography>
              </Box>
              <Typography variant="h4" color="warning">
                {incidents.filter(i => i.startDate === new Date().toISOString().split('T')[0]).length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Avg Containment
              </Typography>
              <Typography variant="h4" color="success">
                {Math.round(incidents.reduce((sum, i) => sum + i.containmentPercentage, 0) / incidents.length)}%
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Paper>
        <Box p={2}>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
            <Typography variant="h6">Incident Details</Typography>
            <Button variant="contained" color="primary">
              New Incident Report
            </Button>
          </Box>

          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Incident Name</TableCell>
                  <TableCell>Location</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Severity</TableCell>
                  <TableCell>Start Date</TableCell>
                  <TableCell>Acres</TableCell>
                  <TableCell>Containment</TableCell>
                  <TableCell>Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {incidents.map((incident) => (
                  <TableRow key={incident.id} hover>
                    <TableCell>
                      <Typography variant="subtitle2">
                        {incident.name}
                      </Typography>
                    </TableCell>
                    <TableCell>{incident.location}</TableCell>
                    <TableCell>
                      <Chip
                        label={incident.status.toUpperCase()}
                        color={getStatusColor(incident.status) as any}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={incident.severity.toUpperCase()}
                        color={getSeverityColor(incident.severity) as any}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>{incident.startDate}</TableCell>
                    <TableCell>{incident.acres.toLocaleString()}</TableCell>
                    <TableCell>{incident.containmentPercentage}%</TableCell>
                    <TableCell>
                      <Tooltip title="View Details">
                        <IconButton size="small">
                          <Visibility />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Edit">
                        <IconButton size="small">
                          <Edit />
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

export default IncidentsPage;