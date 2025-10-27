import React, { useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Grid,
  Card,
  CardContent,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  LinearProgress,
  Alert,
  IconButton,
  Tooltip,
  Avatar,
  List,
  ListItem,
  ListItemText,
  ListItemAvatar,
  Divider,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  Tabs,
  Tab,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from '@mui/material';
import {
  LocalFireDepartment,
  Groups,
  FlightTakeoff,
  Engineering,
  WaterDrop,
  Map,
  Timeline,
  Assessment,
  PlayArrow,
  Pause,
  Stop,
  Warning,
  CheckCircle,
  Schedule,
  Speed,
  ThermostatAuto,
  Air,
  Visibility,
  ExpandMore,
  Phone,
  Radio,
  GpsFixed,
} from '@mui/icons-material';

interface IncidentResource {
  id: string;
  type: 'ground_crew' | 'aircraft' | 'dozer' | 'engine' | 'water_tender';
  name: string;
  status: 'available' | 'deployed' | 'returning' | 'maintenance';
  personnel: number;
  eta?: string;
  assignedSector?: string;
  gpsLocation?: { lat: number; lng: number };
}

interface IncidentDetails {
  id: string;
  name: string;
  incidentCommander: string;
  priority: 'low' | 'medium' | 'high' | 'critical';
  threatLevel: 'minimal' | 'moderate' | 'high' | 'extreme';
  weather: {
    temperature: number;
    humidity: number;
    windSpeed: number;
    windDirection: string;
  };
  resources: IncidentResource[];
  tacticalObjectives: string[];
  constraints: string[];
  safetyIssues: string[];
  progressUpdate: string;
  nextOperationalPeriod: string;
}

interface EnhancedIncidentManagementProps {
  incidentId: string;
  onClose: () => void;
}

const EnhancedIncidentManagement: React.FC<EnhancedIncidentManagementProps> = ({ incidentId, onClose }) => {
  const [selectedTab, setSelectedTab] = useState(0);
  const [deployResourceDialog, setDeployResourceDialog] = useState(false);
  const [selectedResourceType, setSelectedResourceType] = useState('');

  // Mock incident data with realistic CAL FIRE details
  const incident: IncidentDetails = {
    id: incidentId,
    name: 'Saddleridge Fire',
    incidentCommander: 'Chief Maria Santos, Battalion 12',
    priority: 'high',
    threatLevel: 'high',
    weather: {
      temperature: 92,
      humidity: 8,
      windSpeed: 25,
      windDirection: 'NE'
    },
    resources: [
      {
        id: 'eng-4512',
        type: 'engine',
        name: 'Engine 4512 (Type 1)',
        status: 'deployed',
        personnel: 4,
        assignedSector: 'Division Alpha',
        gpsLocation: { lat: 34.2608, lng: -118.4661 }
      },
      {
        id: 'crew-890',
        type: 'ground_crew',
        name: 'Hotshot Crew 890',
        status: 'deployed',
        personnel: 20,
        assignedSector: 'Division Bravo',
        gpsLocation: { lat: 34.2580, lng: -118.4680 }
      },
      {
        id: 'helo-512',
        type: 'aircraft',
        name: 'Helicopter 512 (Super Huey)',
        status: 'returning',
        personnel: 3,
        eta: '15 minutes',
        gpsLocation: { lat: 34.2700, lng: -118.4500 }
      },
      {
        id: 'dozer-203',
        type: 'dozer',
        name: 'Dozer 203 (Cat D8)',
        status: 'deployed',
        personnel: 2,
        assignedSector: 'Division Charlie',
        gpsLocation: { lat: 34.2620, lng: -118.4720 }
      }
    ],
    tacticalObjectives: [
      'Establish containment line on east flank by 1800 hours',
      'Protect structures in Olive View subdivision',
      'Complete evacuation of Zone 7 residents',
      'Establish water supply from Porter Ranch hydrants'
    ],
    constraints: [
      'Steep terrain limiting dozer access',
      'Limited water supply - nearest hydrant 2 miles',
      'Overhead power lines in Division Alpha',
      'Civilian traffic hampering equipment movement'
    ],
    safetyIssues: [
      'Erratic wind patterns - gusts up to 40mph',
      'Visibility reduced due to smoke',
      'Unstable slopes after recent rainfall',
      'Radio dead zones in canyon areas'
    ],
    progressUpdate: 'Fire has grown to 850 acres with 15% containment. Main fire progression halted on north flank. Structure protection successful - no losses to date. Air operations suspended due to winds.',
    nextOperationalPeriod: 'Focus on eastern containment line construction, reinforce structure protection groups, establish night shift operations with thermal imaging.'
  };

  const getResourceIcon = (type: string) => {
    switch (type) {
      case 'ground_crew': return <Groups />;
      case 'aircraft': return <FlightTakeoff />;
      case 'dozer': return <Engineering />;
      case 'engine': return <LocalFireDepartment />;
      case 'water_tender': return <WaterDrop />;
      default: return <Groups />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'deployed': return 'success';
      case 'available': return 'info';
      case 'returning': return 'warning';
      case 'maintenance': return 'error';
      default: return 'default';
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'critical': return 'error';
      case 'high': return 'warning';
      case 'medium': return 'info';
      case 'low': return 'success';
      default: return 'default';
    }
  };

  const handleDeployResource = () => {
    // Implementation for resource deployment
    setDeployResourceDialog(false);
    console.log('Deploying resource:', selectedResourceType);
  };

  return (
    <Dialog open={true} onClose={onClose} maxWidth="xl" fullWidth>
      <DialogTitle>
        <Box display="flex" alignItems="center" justifyContent="space-between">
          <Box display="flex" alignItems="center" gap={2}>
            <LocalFireDepartment color="error" />
            <Box>
              <Typography variant="h5">{incident.name}</Typography>
              <Typography variant="subtitle2" color="textSecondary">
                IC: {incident.incidentCommander}
              </Typography>
            </Box>
            <Chip
              label={incident.priority.toUpperCase()}
              color={getPriorityColor(incident.priority) as any}
              variant="filled"
            />
          </Box>
          <Box display="flex" gap={1}>
            <Button
              variant="contained"
              startIcon={<Groups />}
              onClick={() => setDeployResourceDialog(true)}
            >
              Deploy Resources
            </Button>
            <Button variant="outlined" startIcon={<Map />}>
              Tactical Map
            </Button>
          </Box>
        </Box>
      </DialogTitle>

      <DialogContent>
        <Tabs value={selectedTab} onChange={(e, newValue) => setSelectedTab(newValue)} sx={{ mb: 2 }}>
          <Tab label="Incident Overview" />
          <Tab label="Resource Management" />
          <Tab label="Tactical Operations" />
          <Tab label="Weather & Environment" />
        </Tabs>

        {/* Incident Overview Tab */}
        {selectedTab === 0 && (
          <Grid container spacing={3}>
            {/* Current Status */}
            <Grid item xs={12} md={6}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>Current Status</Typography>
                  <Typography variant="body1" paragraph>
                    {incident.progressUpdate}
                  </Typography>

                  <Alert severity="warning" sx={{ mb: 2 }}>
                    <Typography variant="body2">
                      <strong>Threat Level: {incident.threatLevel.toUpperCase()}</strong>
                    </Typography>
                  </Alert>

                  <Box sx={{ mt: 2 }}>
                    <Typography variant="body2" gutterBottom>Containment Progress</Typography>
                    <LinearProgress variant="determinate" value={15} sx={{ mb: 1, height: 8 }} />
                    <Typography variant="caption">15% contained * 850 acres</Typography>
                  </Box>
                </CardContent>
              </Card>
            </Grid>

            {/* Key Metrics */}
            <Grid item xs={12} md={6}>
              <Grid container spacing={2}>
                <Grid item xs={6}>
                  <Card>
                    <CardContent sx={{ textAlign: 'center' }}>
                      <Typography variant="h4" color="error">850</Typography>
                      <Typography variant="body2">Acres Burned</Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={6}>
                  <Card>
                    <CardContent sx={{ textAlign: 'center' }}>
                      <Typography variant="h4" color="success">0</Typography>
                      <Typography variant="body2">Structures Lost</Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={6}>
                  <Card>
                    <CardContent sx={{ textAlign: 'center' }}>
                      <Typography variant="h4" color="info">{incident.resources.length}</Typography>
                      <Typography variant="body2">Resources Deployed</Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={6}>
                  <Card>
                    <CardContent sx={{ textAlign: 'center' }}>
                      <Typography variant="h4" color="warning">156</Typography>
                      <Typography variant="body2">Personnel on Scene</Typography>
                    </CardContent>
                  </Card>
                </Grid>
              </Grid>
            </Grid>

            {/* Tactical Objectives */}
            <Grid item xs={12} md={6}>
              <Paper sx={{ p: 2 }}>
                <Typography variant="h6" gutterBottom>Tactical Objectives</Typography>
                <List dense>
                  {incident.tacticalObjectives.map((objective, index) => (
                    <ListItem key={index}>
                      <ListItemAvatar>
                        <Avatar sx={{ width: 24, height: 24, fontSize: '0.8rem' }}>
                          {index + 1}
                        </Avatar>
                      </ListItemAvatar>
                      <ListItemText primary={objective} />
                    </ListItem>
                  ))}
                </List>
              </Paper>
            </Grid>

            {/* Safety Issues */}
            <Grid item xs={12} md={6}>
              <Paper sx={{ p: 2 }}>
                <Typography variant="h6" gutterBottom color="warning.main">
                  <Warning sx={{ mr: 1, verticalAlign: 'middle' }} />
                  Safety Issues
                </Typography>
                <List dense>
                  {incident.safetyIssues.map((issue, index) => (
                    <ListItem key={index}>
                      <ListItemAvatar>
                        <Warning color="warning" fontSize="small" />
                      </ListItemAvatar>
                      <ListItemText primary={issue} />
                    </ListItem>
                  ))}
                </List>
              </Paper>
            </Grid>

            {/* Next Operational Period */}
            <Grid item xs={12}>
              <Paper sx={{ p: 2 }}>
                <Typography variant="h6" gutterBottom>
                  <Schedule sx={{ mr: 1, verticalAlign: 'middle' }} />
                  Next Operational Period
                </Typography>
                <Typography variant="body1">
                  {incident.nextOperationalPeriod}
                </Typography>
              </Paper>
            </Grid>
          </Grid>
        )}

        {/* Resource Management Tab */}
        {selectedTab === 1 && (
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <Paper sx={{ p: 2 }}>
                <Typography variant="h6" gutterBottom>Deployed Resources</Typography>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Resource</TableCell>
                      <TableCell>Type</TableCell>
                      <TableCell>Personnel</TableCell>
                      <TableCell>Status</TableCell>
                      <TableCell>Assignment</TableCell>
                      <TableCell>Actions</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {incident.resources.map((resource) => (
                      <TableRow key={resource.id}>
                        <TableCell>
                          <Box display="flex" alignItems="center" gap={1}>
                            {getResourceIcon(resource.type)}
                            <Typography variant="body2">{resource.name}</Typography>
                          </Box>
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={resource.type.replace('_', ' ').toUpperCase()}
                            size="small"
                            variant="outlined"
                          />
                        </TableCell>
                        <TableCell>{resource.personnel}</TableCell>
                        <TableCell>
                          <Chip
                            label={resource.status.toUpperCase()}
                            color={getStatusColor(resource.status) as any}
                            size="small"
                          />
                          {resource.eta && (
                            <Typography variant="caption" display="block">
                              ETA: {resource.eta}
                            </Typography>
                          )}
                        </TableCell>
                        <TableCell>{resource.assignedSector || 'Unassigned'}</TableCell>
                        <TableCell>
                          <Tooltip title="Radio Contact">
                            <IconButton size="small">
                              <Radio />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="GPS Location">
                            <IconButton size="small">
                              <GpsFixed />
                            </IconButton>
                          </Tooltip>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </Paper>
            </Grid>
          </Grid>
        )}

        {/* Tactical Operations Tab */}
        {selectedTab === 2 && (
          <Grid container spacing={3}>
            <Grid item xs={12} md={8}>
              <Paper sx={{ p: 2 }}>
                <Typography variant="h6" gutterBottom>Tactical Map</Typography>
                <Box
                  sx={{
                    height: 400,
                    bgcolor: 'grey.100',
                    border: 1,
                    borderColor: 'grey.300',
                    borderRadius: 1,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                  }}
                >
                  <Box textAlign="center">
                    <Map sx={{ fontSize: 48, color: 'grey.500', mb: 1 }} />
                    <Typography variant="h6" color="grey.600">
                      Tactical Situation Map
                    </Typography>
                    <Typography variant="body2" color="grey.600">
                      Fire perimeter, resource locations, and tactical assignments
                    </Typography>
                  </Box>
                </Box>
              </Paper>
            </Grid>

            <Grid item xs={12} md={4}>
              <Paper sx={{ p: 2 }}>
                <Typography variant="h6" gutterBottom>Division Assignments</Typography>

                <Accordion defaultExpanded>
                  <AccordionSummary expandIcon={<ExpandMore />}>
                    <Typography variant="subtitle1">Division Alpha</Typography>
                  </AccordionSummary>
                  <AccordionDetails>
                    <Typography variant="body2" gutterBottom>
                      <strong>Objective:</strong> Eastern containment line
                    </Typography>
                    <Typography variant="body2" gutterBottom>
                      <strong>Resources:</strong> Engine 4512, Crew 445
                    </Typography>
                    <Typography variant="body2">
                      <strong>Status:</strong> Good progress, 60% complete
                    </Typography>
                  </AccordionDetails>
                </Accordion>

                <Accordion>
                  <AccordionSummary expandIcon={<ExpandMore />}>
                    <Typography variant="subtitle1">Division Bravo</Typography>
                  </AccordionSummary>
                  <AccordionDetails>
                    <Typography variant="body2" gutterBottom>
                      <strong>Objective:</strong> Structure protection
                    </Typography>
                    <Typography variant="body2" gutterBottom>
                      <strong>Resources:</strong> Hotshot Crew 890, Engine 3201
                    </Typography>
                    <Typography variant="body2">
                      <strong>Status:</strong> Defensive positions established
                    </Typography>
                  </AccordionDetails>
                </Accordion>

                <Accordion>
                  <AccordionSummary expandIcon={<ExpandMore />}>
                    <Typography variant="subtitle1">Division Charlie</Typography>
                  </AccordionSummary>
                  <AccordionDetails>
                    <Typography variant="body2" gutterBottom>
                      <strong>Objective:</strong> Fireline construction
                    </Typography>
                    <Typography variant="body2" gutterBottom>
                      <strong>Resources:</strong> Dozer 203, Hand Crew 567
                    </Typography>
                    <Typography variant="body2">
                      <strong>Status:</strong> Terrain challenges, slow progress
                    </Typography>
                  </AccordionDetails>
                </Accordion>
              </Paper>
            </Grid>
          </Grid>
        )}

        {/* Weather & Environment Tab */}
        {selectedTab === 3 && (
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>Current Weather</Typography>
                  <Grid container spacing={2}>
                    <Grid item xs={6}>
                      <Box display="flex" alignItems="center" gap={1}>
                        <ThermostatAuto color="error" />
                        <Box>
                          <Typography variant="h4">{incident.weather.temperature}degF</Typography>
                          <Typography variant="caption">Temperature</Typography>
                        </Box>
                      </Box>
                    </Grid>
                    <Grid item xs={6}>
                      <Box display="flex" alignItems="center" gap={1}>
                        <WaterDrop color="primary" />
                        <Box>
                          <Typography variant="h4">{incident.weather.humidity}%</Typography>
                          <Typography variant="caption">Humidity</Typography>
                        </Box>
                      </Box>
                    </Grid>
                    <Grid item xs={6}>
                      <Box display="flex" alignItems="center" gap={1}>
                        <Air color="info" />
                        <Box>
                          <Typography variant="h4">{incident.weather.windSpeed}</Typography>
                          <Typography variant="caption">mph {incident.weather.windDirection}</Typography>
                        </Box>
                      </Box>
                    </Grid>
                    <Grid item xs={6}>
                      <Box display="flex" alignItems="center" gap={1}>
                        <Visibility color="warning" />
                        <Box>
                          <Typography variant="h4">2</Typography>
                          <Typography variant="caption">miles visibility</Typography>
                        </Box>
                      </Box>
                    </Grid>
                  </Grid>
                </CardContent>
              </Card>
            </Grid>

            <Grid item xs={12} md={6}>
              <Paper sx={{ p: 2 }}>
                <Typography variant="h6" gutterBottom>Environmental Constraints</Typography>
                <List>
                  {incident.constraints.map((constraint, index) => (
                    <ListItem key={index}>
                      <ListItemAvatar>
                        <Warning color="warning" />
                      </ListItemAvatar>
                      <ListItemText primary={constraint} />
                    </ListItem>
                  ))}
                </List>
              </Paper>
            </Grid>

            <Grid item xs={12}>
              <Paper sx={{ p: 2 }}>
                <Typography variant="h6" gutterBottom>Weather Forecast</Typography>
                <Alert severity="error" sx={{ mb: 2 }}>
                  <strong>Red Flag Warning:</strong> Critical fire weather conditions expected through 2100 hours.
                  Winds increasing to 35-45 mph with gusts to 65 mph. Humidity dropping to 5%.
                </Alert>
                <Typography variant="body2">
                  <strong>Tonight:</strong> Winds decreasing to 15-20 mph, humidity recovery to 15-20%.
                  Temperature dropping to 68degF by 0600 hours.
                </Typography>
                <Typography variant="body2" sx={{ mt: 1 }}>
                  <strong>Tomorrow:</strong> Another round of Santa Ana winds developing by 1000 hours.
                  Similar conditions to today expected.
                </Typography>
              </Paper>
            </Grid>
          </Grid>
        )}
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose}>Close</Button>
        <Button variant="contained" startIcon={<Assessment />}>
          Generate IAP
        </Button>
      </DialogActions>

      {/* Deploy Resource Dialog */}
      <Dialog
        open={deployResourceDialog}
        onClose={() => setDeployResourceDialog(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Deploy Additional Resources</DialogTitle>
        <DialogContent>
          <FormControl fullWidth sx={{ mt: 2 }}>
            <InputLabel>Resource Type</InputLabel>
            <Select
              value={selectedResourceType}
              onChange={(e) => setSelectedResourceType(e.target.value)}
              label="Resource Type"
            >
              <MenuItem value="engine">Fire Engine</MenuItem>
              <MenuItem value="crew">Hand Crew</MenuItem>
              <MenuItem value="dozer">Bulldozer</MenuItem>
              <MenuItem value="aircraft">Aircraft</MenuItem>
              <MenuItem value="water_tender">Water Tender</MenuItem>
            </Select>
          </FormControl>
          <TextField
            fullWidth
            label="Assignment/Division"
            sx={{ mt: 2 }}
            placeholder="e.g., Division Alpha, Structure Protection"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeployResourceDialog(false)}>Cancel</Button>
          <Button onClick={handleDeployResource} variant="contained">
            Deploy Resource
          </Button>
        </DialogActions>
      </Dialog>
    </Dialog>
  );
};

export default EnhancedIncidentManagement;