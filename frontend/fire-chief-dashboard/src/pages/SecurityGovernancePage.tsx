import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Grid,
  Card,
  CardContent,
  CardHeader,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Switch,
  FormControlLabel,
  Alert,
  Tabs,
  Tab,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  ListItemSecondaryAction,
  Avatar,
  Badge,
  LinearProgress,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Divider,
  Tooltip,
} from '@mui/material';
import {
  Security,
  People,
  Visibility,
  VisibilityOff,
  Edit,
  Delete,
  Add,
  Warning,
  CheckCircle,
  Error,
  Info,
  Shield,
  Lock,
  Key,
  AdminPanelSettings,
  Group,
  Assignment,
  History,
  NotificationImportant,
  VpnKey,
  Fingerprint,
  ExpandMore,
  Download,
  Refresh,
  Settings,
  AccountCircle,
  AccessTime,
  Computer,
  PhoneIphone,
} from '@mui/icons-material';

interface User {
  id: string;
  name: string;
  email: string;
  role: 'admin' | 'fire_chief' | 'analyst' | 'operator';
  status: 'active' | 'inactive' | 'locked';
  lastLogin: string;
  mfaEnabled: boolean;
  department: string;
  permissions: string[];
}

interface AuditLog {
  id: string;
  timestamp: string;
  userId: string;
  userName: string;
  action: string;
  resource: string;
  details: string;
  ipAddress: string;
  userAgent: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
}

interface SecurityAlert {
  id: string;
  title: string;
  description: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  timestamp: string;
  status: 'active' | 'investigating' | 'resolved';
  category: 'access' | 'data' | 'system' | 'compliance';
}

const SecurityGovernancePage: React.FC = () => {
  const [selectedTab, setSelectedTab] = useState(0);
  const [users, setUsers] = useState<User[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [securityAlerts, setSecurityAlerts] = useState<SecurityAlert[]>([]);
  const [userDialogOpen, setUserDialogOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // Mock data initialization
    const mockUsers: User[] = [
      {
        id: '1',
        name: 'Chief Sarah Johnson',
        email: 'sarah.johnson@calfire.ca.gov',
        role: 'fire_chief',
        status: 'active',
        lastLogin: '2024-09-14T09:30:00Z',
        mfaEnabled: true,
        department: 'CAL FIRE Operations',
        permissions: ['view_all', 'manage_incidents', 'deploy_resources']
      },
      {
        id: '2',
        name: 'Dr. Michael Chen',
        email: 'michael.chen@calfire.ca.gov',
        role: 'analyst',
        status: 'active',
        lastLogin: '2024-09-14T08:15:00Z',
        mfaEnabled: true,
        department: 'Fire Analytics Division',
        permissions: ['view_data', 'run_analysis', 'create_reports']
      },
      {
        id: '3',
        name: 'Lisa Rodriguez',
        email: 'lisa.rodriguez@calfire.ca.gov',
        role: 'operator',
        status: 'active',
        lastLogin: '2024-09-13T16:45:00Z',
        mfaEnabled: false,
        department: 'Dispatch Operations',
        permissions: ['view_alerts', 'update_status']
      },
      {
        id: '4',
        name: 'Admin Account',
        email: 'admin@calfire.ca.gov',
        role: 'admin',
        status: 'active',
        lastLogin: '2024-09-14T07:00:00Z',
        mfaEnabled: true,
        department: 'IT Security',
        permissions: ['full_access', 'user_management', 'system_config']
      }
    ];

    const mockAuditLogs: AuditLog[] = [
      {
        id: '1',
        timestamp: '2024-09-14T10:30:00Z',
        userId: '1',
        userName: 'Sarah Johnson',
        action: 'Data Export',
        resource: 'Fire Incidents Dataset',
        details: 'Exported 500 records to CSV',
        ipAddress: '10.0.1.45',
        userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        severity: 'medium'
      },
      {
        id: '2',
        timestamp: '2024-09-14T10:15:00Z',
        userId: '2',
        userName: 'Michael Chen',
        action: 'Query Execution',
        resource: 'Weather Data API',
        details: 'Executed complex analysis query',
        ipAddress: '10.0.1.52',
        userAgent: 'Chrome/118.0.0.0',
        severity: 'low'
      },
      {
        id: '3',
        timestamp: '2024-09-14T09:45:00Z',
        userId: '3',
        userName: 'Lisa Rodriguez',
        action: 'Failed Login Attempt',
        resource: 'Authentication System',
        details: 'Multiple failed login attempts detected',
        ipAddress: '192.168.1.100',
        userAgent: 'Safari/17.0',
        severity: 'high'
      }
    ];

    const mockSecurityAlerts: SecurityAlert[] = [
      {
        id: '1',
        title: 'Unusual Access Pattern Detected',
        description: 'User accessing sensitive data outside normal hours',
        severity: 'medium',
        timestamp: '2024-09-14T10:45:00Z',
        status: 'investigating',
        category: 'access'
      },
      {
        id: '2',
        title: 'MFA Disabled by User',
        description: 'Multi-factor authentication was disabled for user account',
        severity: 'high',
        timestamp: '2024-09-14T09:30:00Z',
        status: 'active',
        category: 'access'
      },
      {
        id: '3',
        title: 'Data Compliance Check Required',
        description: 'Quarterly data retention compliance review due',
        severity: 'low',
        timestamp: '2024-09-14T08:00:00Z',
        status: 'active',
        category: 'compliance'
      }
    ];

    setUsers(mockUsers);
    setAuditLogs(mockAuditLogs);
    setSecurityAlerts(mockSecurityAlerts);
  }, []);

  const getRoleColor = (role: string) => {
    switch (role) {
      case 'admin': return 'error';
      case 'fire_chief': return 'warning';
      case 'analyst': return 'info';
      case 'operator': return 'success';
      default: return 'default';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'success';
      case 'inactive': return 'warning';
      case 'locked': return 'error';
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

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'critical': return <Error />;
      case 'high': return <Warning />;
      case 'medium': return <Info />;
      case 'low': return <CheckCircle />;
      default: return <Info />;
    }
  };

  const handleEditUser = (user: User) => {
    setSelectedUser(user);
    setUserDialogOpen(true);
  };

  const handleCloseUserDialog = () => {
    setSelectedUser(null);
    setUserDialogOpen(false);
  };

  const toggleMFA = (userId: string) => {
    setUsers(prev => prev.map(user =>
      user.id === userId ? { ...user, mfaEnabled: !user.mfaEnabled } : user
    ));
  };

  const TabPanel = ({ children, value, index }: { children: React.ReactNode, value: number, index: number }) => (
    <div hidden={value !== index}>
      {value === index && <Box sx={{ pt: 2 }}>{children}</Box>}
    </div>
  );

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" gutterBottom>
          Security & Governance
        </Typography>
        <Typography variant="subtitle1" color="text.secondary">
          Access control, audit logs, and compliance management
        </Typography>
      </Box>

      {/* Security Summary Cards */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <Shield color="primary" sx={{ fontSize: 40, mr: 2 }} />
                <Box>
                  <Typography variant="h4">{users.filter(u => u.status === 'active').length}</Typography>
                  <Typography variant="body2" color="text.secondary">
                    Active Users
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <Badge badgeContent={securityAlerts.filter(a => a.status === 'active').length} color="error">
                  <NotificationImportant color="warning" sx={{ fontSize: 40, mr: 2 }} />
                </Badge>
                <Box sx={{ ml: 1 }}>
                  <Typography variant="h4">{securityAlerts.length}</Typography>
                  <Typography variant="body2" color="text.secondary">
                    Security Alerts
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <VpnKey color="success" sx={{ fontSize: 40, mr: 2 }} />
                <Box>
                  <Typography variant="h4">
                    {Math.round((users.filter(u => u.mfaEnabled).length / users.length) * 100)}%
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    MFA Enabled
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <History color="info" sx={{ fontSize: 40, mr: 2 }} />
                <Box>
                  <Typography variant="h4">{auditLogs.length}</Typography>
                  <Typography variant="body2" color="text.secondary">
                    Audit Events
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Tabs */}
      <Paper sx={{ mb: 3 }}>
        <Tabs value={selectedTab} onChange={(e, newValue) => setSelectedTab(newValue)}>
          <Tab icon={<People />} label="User Management" />
          <Tab icon={<History />} label="Audit Logs" />
          <Tab icon={<Security />} label="Security Alerts" />
          <Tab icon={<AdminPanelSettings />} label="Access Control" />
        </Tabs>
      </Paper>

      {/* User Management Tab */}
      <TabPanel value={selectedTab} index={0}>
        <Grid container spacing={3}>
          <Grid item xs={12}>
            <Paper sx={{ p: 2 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6">User Accounts</Typography>
                <Button variant="contained" startIcon={<Add />}>
                  Add User
                </Button>
              </Box>

              <TableContainer>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>User</TableCell>
                      <TableCell>Role</TableCell>
                      <TableCell>Department</TableCell>
                      <TableCell>Status</TableCell>
                      <TableCell>Last Login</TableCell>
                      <TableCell>MFA</TableCell>
                      <TableCell>Actions</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {users.map((user) => (
                      <TableRow key={user.id} hover>
                        <TableCell>
                          <Box sx={{ display: 'flex', alignItems: 'center' }}>
                            <Avatar sx={{ mr: 2, bgcolor: 'primary.main' }}>
                              {user.name.charAt(0)}
                            </Avatar>
                            <Box>
                              <Typography variant="subtitle2">{user.name}</Typography>
                              <Typography variant="caption" color="text.secondary">
                                {user.email}
                              </Typography>
                            </Box>
                          </Box>
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={user.role.replace('_', ' ').toUpperCase()}
                            color={getRoleColor(user.role) as any}
                            size="small"
                          />
                        </TableCell>
                        <TableCell>{user.department}</TableCell>
                        <TableCell>
                          <Chip
                            label={user.status.toUpperCase()}
                            color={getStatusColor(user.status) as any}
                            size="small"
                          />
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2">
                            {new Date(user.lastLogin).toLocaleDateString()}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {new Date(user.lastLogin).toLocaleTimeString()}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Switch
                            checked={user.mfaEnabled}
                            onChange={() => toggleMFA(user.id)}
                            color="primary"
                            size="small"
                          />
                        </TableCell>
                        <TableCell>
                          <Tooltip title="Edit User">
                            <IconButton size="small" onClick={() => handleEditUser(user)}>
                              <Edit />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="View Permissions">
                            <IconButton size="small">
                              <Visibility />
                            </IconButton>
                          </Tooltip>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </Paper>
          </Grid>
        </Grid>
      </TabPanel>

      {/* Audit Logs Tab */}
      <TabPanel value={selectedTab} index={1}>
        <Paper sx={{ p: 2 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="h6">Audit Log</Typography>
            <Box>
              <Button startIcon={<Refresh />} sx={{ mr: 1 }}>
                Refresh
              </Button>
              <Button startIcon={<Download />} variant="outlined">
                Export
              </Button>
            </Box>
          </Box>

          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Timestamp</TableCell>
                  <TableCell>User</TableCell>
                  <TableCell>Action</TableCell>
                  <TableCell>Resource</TableCell>
                  <TableCell>Severity</TableCell>
                  <TableCell>Details</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {auditLogs.map((log) => (
                  <TableRow key={log.id} hover>
                    <TableCell>
                      <Typography variant="body2">
                        {new Date(log.timestamp).toLocaleDateString()}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {new Date(log.timestamp).toLocaleTimeString()}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">{log.userName}</Typography>
                      <Typography variant="caption" color="text.secondary">
                        {log.ipAddress}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">{log.action}</Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">{log.resource}</Typography>
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={log.severity.toUpperCase()}
                        color={getSeverityColor(log.severity) as any}
                        size="small"
                        icon={getSeverityIcon(log.severity)}
                      />
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">{log.details}</Typography>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </Paper>
      </TabPanel>

      {/* Security Alerts Tab */}
      <TabPanel value={selectedTab} index={2}>
        <Grid container spacing={3}>
          {securityAlerts.map((alert) => (
            <Grid item xs={12} key={alert.id}>
              <Alert
                severity={alert.severity === 'critical' ? 'error' : alert.severity === 'high' ? 'warning' : 'info'}
                variant="outlined"
                sx={{ p: 2 }}
                action={
                  <Box>
                    <Button size="small" color="inherit">
                      Investigate
                    </Button>
                    <Button size="small" color="inherit">
                      Resolve
                    </Button>
                  </Box>
                }
              >
                <Box>
                  <Typography variant="h6" gutterBottom>
                    {alert.title}
                  </Typography>
                  <Typography variant="body2" paragraph>
                    {alert.description}
                  </Typography>
                  <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                    <Chip label={alert.category.toUpperCase()} size="small" variant="outlined" />
                    <Chip
                      label={alert.status.toUpperCase()}
                      size="small"
                      color={alert.status === 'resolved' ? 'success' : 'warning'}
                    />
                    <Typography variant="caption" color="text.secondary">
                      {new Date(alert.timestamp).toLocaleString()}
                    </Typography>
                  </Box>
                </Box>
              </Alert>
            </Grid>
          ))}
        </Grid>
      </TabPanel>

      {/* Access Control Tab */}
      <TabPanel value={selectedTab} index={3}>
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 2 }}>
              <Typography variant="h6" gutterBottom>
                Role-Based Access Control
              </Typography>

              <Accordion defaultExpanded>
                <AccordionSummary expandIcon={<ExpandMore />}>
                  <Typography>Fire Chief Role</Typography>
                </AccordionSummary>
                <AccordionDetails>
                  <List dense>
                    <ListItem>
                      <ListItemIcon><CheckCircle color="success" /></ListItemIcon>
                      <ListItemText primary="Full incident management" />
                    </ListItem>
                    <ListItem>
                      <ListItemIcon><CheckCircle color="success" /></ListItemIcon>
                      <ListItemText primary="Resource deployment" />
                    </ListItem>
                    <ListItem>
                      <ListItemIcon><CheckCircle color="success" /></ListItemIcon>
                      <ListItemText primary="Strategic planning access" />
                    </ListItem>
                    <ListItem>
                      <ListItemIcon><Error color="error" /></ListItemIcon>
                      <ListItemText primary="System administration" secondary="Restricted" />
                    </ListItem>
                  </List>
                </AccordionDetails>
              </Accordion>

              <Accordion>
                <AccordionSummary expandIcon={<ExpandMore />}>
                  <Typography>Analyst Role</Typography>
                </AccordionSummary>
                <AccordionDetails>
                  <List dense>
                    <ListItem>
                      <ListItemIcon><CheckCircle color="success" /></ListItemIcon>
                      <ListItemText primary="Data analysis tools" />
                    </ListItem>
                    <ListItem>
                      <ListItemIcon><CheckCircle color="success" /></ListItemIcon>
                      <ListItemText primary="Report generation" />
                    </ListItem>
                    <ListItem>
                      <ListItemIcon><CheckCircle color="success" /></ListItemIcon>
                      <ListItemText primary="Historical data access" />
                    </ListItem>
                    <ListItem>
                      <ListItemIcon><Error color="error" /></ListItemIcon>
                      <ListItemText primary="Resource deployment" secondary="Restricted" />
                    </ListItem>
                  </List>
                </AccordionDetails>
              </Accordion>

              <Accordion>
                <AccordionSummary expandIcon={<ExpandMore />}>
                  <Typography>Operator Role</Typography>
                </AccordionSummary>
                <AccordionDetails>
                  <List dense>
                    <ListItem>
                      <ListItemIcon><CheckCircle color="success" /></ListItemIcon>
                      <ListItemText primary="Alert monitoring" />
                    </ListItem>
                    <ListItem>
                      <ListItemIcon><CheckCircle color="success" /></ListItemIcon>
                      <ListItemText primary="Status updates" />
                    </ListItem>
                    <ListItem>
                      <ListItemIcon><Error color="error" /></ListItemIcon>
                      <ListItemText primary="Data export" secondary="Restricted" />
                    </ListItem>
                    <ListItem>
                      <ListItemIcon><Error color="error" /></ListItemIcon>
                      <ListItemText primary="Configuration changes" secondary="Restricted" />
                    </ListItem>
                  </List>
                </AccordionDetails>
              </Accordion>
            </Paper>
          </Grid>

          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 2 }}>
              <Typography variant="h6" gutterBottom>
                Security Compliance Status
              </Typography>

              <Box sx={{ mb: 3 }}>
                <Typography variant="body2" gutterBottom>
                  MFA Adoption Rate
                </Typography>
                <LinearProgress
                  variant="determinate"
                  value={(users.filter(u => u.mfaEnabled).length / users.length) * 100}
                  sx={{ height: 8, borderRadius: 4 }}
                />
                <Typography variant="caption" color="text.secondary">
                  {users.filter(u => u.mfaEnabled).length} of {users.length} users
                </Typography>
              </Box>

              <Box sx={{ mb: 3 }}>
                <Typography variant="body2" gutterBottom>
                  Password Policy Compliance
                </Typography>
                <LinearProgress
                  variant="determinate"
                  value={85}
                  color="warning"
                  sx={{ height: 8, borderRadius: 4 }}
                />
                <Typography variant="caption" color="text.secondary">
                  85% compliant
                </Typography>
              </Box>

              <Box sx={{ mb: 3 }}>
                <Typography variant="body2" gutterBottom>
                  Access Review Completion
                </Typography>
                <LinearProgress
                  variant="determinate"
                  value={92}
                  color="success"
                  sx={{ height: 8, borderRadius: 4 }}
                />
                <Typography variant="caption" color="text.secondary">
                  92% completed this quarter
                </Typography>
              </Box>

              <Divider sx={{ my: 2 }} />

              <Typography variant="h6" gutterBottom>
                Quick Actions
              </Typography>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                <Button startIcon={<Shield />} variant="outlined" fullWidth>
                  Run Security Audit
                </Button>
                <Button startIcon={<Key />} variant="outlined" fullWidth>
                  Force Password Reset
                </Button>
                <Button startIcon={<Fingerprint />} variant="outlined" fullWidth>
                  Enable MFA for All Users
                </Button>
                <Button startIcon={<Download />} variant="outlined" fullWidth>
                  Export Compliance Report
                </Button>
              </Box>
            </Paper>
          </Grid>
        </Grid>
      </TabPanel>

      {/* User Edit Dialog */}
      <Dialog
        open={userDialogOpen}
        onClose={handleCloseUserDialog}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Edit User</DialogTitle>
        <DialogContent>
          {selectedUser && (
            <Box sx={{ pt: 2 }}>
              <TextField
                fullWidth
                label="Full Name"
                value={selectedUser.name}
                sx={{ mb: 2 }}
              />
              <TextField
                fullWidth
                label="Email"
                value={selectedUser.email}
                sx={{ mb: 2 }}
              />
              <FormControl fullWidth sx={{ mb: 2 }}>
                <InputLabel>Role</InputLabel>
                <Select value={selectedUser.role} label="Role">
                  <MenuItem value="admin">Administrator</MenuItem>
                  <MenuItem value="fire_chief">Fire Chief</MenuItem>
                  <MenuItem value="analyst">Analyst</MenuItem>
                  <MenuItem value="operator">Operator</MenuItem>
                </Select>
              </FormControl>
              <TextField
                fullWidth
                label="Department"
                value={selectedUser.department}
                sx={{ mb: 2 }}
              />
              <FormControlLabel
                control={
                  <Switch checked={selectedUser.mfaEnabled} />
                }
                label="Multi-Factor Authentication"
              />
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseUserDialog}>Cancel</Button>
          <Button variant="contained" onClick={handleCloseUserDialog}>
            Save Changes
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default SecurityGovernancePage;