import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Alert,
  Chip,
  IconButton,
  Collapse,
  Badge,
  Button,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  ListItemSecondaryAction,
  Drawer,
  AppBar,
  Toolbar,
  Divider,
  Tooltip,
  Avatar,
  Snackbar,
  Paper,
} from '@mui/material';
import {
  Close,
  NotificationImportant,
  LocalFireDepartment,
  Warning,
  CheckCircle,
  Schedule,
  ExpandLess,
  ExpandMore,
  Notifications,
  NotificationsActive,
  PriorityHigh,
  ReportProblem,
  InfoOutlined,
  Satellite,
  Sensors,
  Air,
  People,
  LocationOn,
  AccessTime,
  Info,
} from '@mui/icons-material';

interface RealTimeNotification {
  id: string;
  type: 'fire_detection' | 'weather_alert' | 'resource_update' | 'system_alert' | 'evacuation' | 'air_quality';
  priority: 'low' | 'medium' | 'high' | 'critical';
  title: string;
  message: string;
  timestamp: Date;
  source: string;
  location?: string;
  isRead: boolean;
  actionRequired: boolean;
  expiresAt?: Date;
}

interface RealTimeNotificationsProps {
  onNotificationClick?: (notification: RealTimeNotification) => void;
}

const RealTimeNotifications: React.FC<RealTimeNotificationsProps> = ({ onNotificationClick }) => {
  const [notifications, setNotifications] = useState<RealTimeNotification[]>([]);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set());
  const [snackbarOpen, setSnackbarOpen] = useState(false);
  const [latestNotification, setLatestNotification] = useState<RealTimeNotification | null>(null);

  // Mock real-time data simulation
  useEffect(() => {
    const mockNotifications: RealTimeNotification[] = [
      {
        id: '1',
        type: 'fire_detection',
        priority: 'critical',
        title: 'Fire Detection Alert',
        message: 'MODIS satellite detected new fire hotspot with 95% confidence. Location: Angeles National Forest, coordinates 34.2089, -118.1712',
        timestamp: new Date(),
        source: 'NASA FIRMS',
        location: 'Angeles National Forest',
        isRead: false,
        actionRequired: true,
      },
      {
        id: '2',
        type: 'weather_alert',
        priority: 'high',
        title: 'Red Flag Warning Extended',
        message: 'Red Flag Warning extended until 9 PM PDT. Winds gusting 45-60 mph, humidity dropping to 5%. Extreme fire behavior possible.',
        timestamp: new Date(Date.now() - 300000),
        source: 'National Weather Service',
        location: 'Los Angeles County',
        isRead: false,
        actionRequired: false,
      },
      {
        id: '3',
        type: 'resource_update',
        priority: 'medium',
        title: 'Aircraft Deployed',
        message: 'Super Scoop 911 dispatched to Riverside Fire. ETA 12 minutes. Water drop operations commencing.',
        timestamp: new Date(Date.now() - 600000),
        source: 'CAL FIRE Dispatch',
        location: 'Riverside County',
        isRead: false,
        actionRequired: false,
      },
      {
        id: '4',
        type: 'air_quality',
        priority: 'medium',
        title: 'Air Quality Alert',
        message: 'AQI readings exceed 200 (Very Unhealthy) in Pasadena area due to smoke. Recommend N95 masks for outdoor personnel.',
        timestamp: new Date(Date.now() - 900000),
        source: 'IoT Air Quality Network',
        location: 'Pasadena, CA',
        isRead: true,
        actionRequired: false,
      }
    ];

    setNotifications(mockNotifications);

    // Simulate real-time notifications
    const interval = setInterval(() => {
      const newNotifications = [
        {
          id: Date.now().toString(),
          type: Math.random() > 0.5 ? 'fire_detection' : 'weather_alert',
          priority: Math.random() > 0.7 ? 'critical' : Math.random() > 0.5 ? 'high' : 'medium',
          title: 'Live Update',
          message: `Automated alert generated at ${new Date().toLocaleTimeString()}`,
          timestamp: new Date(),
          source: 'Real-time System',
          isRead: false,
          actionRequired: Math.random() > 0.6,
        } as RealTimeNotification
      ];

      setNotifications(prev => [...newNotifications, ...prev].slice(0, 20)); // Keep only latest 20
      setLatestNotification(newNotifications[0]);
      setSnackbarOpen(true);
    }, 30000); // New notification every 30 seconds

    return () => clearInterval(interval);
  }, []);

  const getNotificationIcon = (type: string) => {
    switch (type) {
      case 'fire_detection': return <LocalFireDepartment color="error" />;
      case 'weather_alert': return <Warning color="warning" />;
      case 'resource_update': return <People color="info" />;
      case 'system_alert': return <Info color="primary" />;
      case 'evacuation': return <PriorityHigh color="error" />;
      case 'air_quality': return <Air color="secondary" />;
      default: return <NotificationImportant />;
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

  const getPriorityIcon = (priority: string) => {
    switch (priority) {
      case 'critical': return <PriorityHigh />;
      case 'high': return <ReportProblem />;
      case 'medium': return <InfoOutlined />;
      default: return <Info />;
    }
  };

  const markAsRead = (notificationId: string) => {
    setNotifications(prev =>
      prev.map(notification =>
        notification.id === notificationId
          ? { ...notification, isRead: true }
          : notification
      )
    );
  };

  const toggleExpanded = (notificationId: string) => {
    setExpandedItems(prev => {
      const newSet = new Set(prev);
      if (newSet.has(notificationId)) {
        newSet.delete(notificationId);
      } else {
        newSet.add(notificationId);
      }
      return newSet;
    });
  };

  const unreadCount = notifications.filter(n => !n.isRead).length;
  const criticalCount = notifications.filter(n => n.priority === 'critical' && !n.isRead).length;

  return (
    <>
      {/* Notification Bell Icon */}
      <Tooltip title="Notifications">
        <IconButton
          size="large"
          onClick={() => setDrawerOpen(true)}
          color="inherit"
          sx={{ position: 'relative' }}
        >
          <Badge
            badgeContent={unreadCount}
            color="error"
            overlap="circular"
          >
            {criticalCount > 0 ? (
              <NotificationsActive sx={{ animation: 'pulse 1s infinite' }} />
            ) : (
              <Notifications />
            )}
          </Badge>
        </IconButton>
      </Tooltip>

      {/* Floating Critical Alerts */}
      {notifications.filter(n => n.priority === 'critical' && !n.isRead).slice(0, 2).map((notification, index) => (
        <Box
          key={notification.id}
          sx={{
            position: 'fixed',
            top: 100 + (index * 120),
            right: 20,
            width: 350,
            zIndex: 1300,
            animation: 'slideInRight 0.3s ease-out'
          }}
        >
          <Alert
            severity="error"
            variant="filled"
            sx={{ mb: 1 }}
            action={
              <IconButton
                aria-label="close"
                color="inherit"
                size="small"
                onClick={() => markAsRead(notification.id)}
              >
                <Close fontSize="inherit" />
              </IconButton>
            }
          >
            <Box>
              <Typography variant="subtitle2" fontWeight="bold">
                {notification.title}
              </Typography>
              <Typography variant="body2">
                {notification.message.length > 100
                  ? notification.message.substring(0, 100) + '...'
                  : notification.message
                }
              </Typography>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 1 }}>
                {notification.location && (
                  <Chip
                    icon={<LocationOn />}
                    label={notification.location}
                    size="small"
                    variant="outlined"
                    sx={{ color: 'white', borderColor: 'white' }}
                  />
                )}
                <Typography variant="caption">
                  {notification.timestamp.toLocaleTimeString()}
                </Typography>
              </Box>
            </Box>
          </Alert>
        </Box>
      ))}

      {/* Notifications Drawer */}
      <Drawer
        anchor="right"
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        sx={{
          '& .MuiDrawer-paper': {
            width: 400,
            boxSizing: 'border-box',
          },
        }}
      >
        <AppBar position="static" elevation={0}>
          <Toolbar>
            <NotificationsActive sx={{ mr: 2 }} />
            <Typography variant="h6" sx={{ flexGrow: 1 }}>
              Real-time Alerts
            </Typography>
            <Badge badgeContent={unreadCount} color="error">
              <Typography variant="body2">{notifications.length}</Typography>
            </Badge>
            <IconButton
              edge="end"
              color="inherit"
              onClick={() => setDrawerOpen(false)}
              sx={{ ml: 1 }}
            >
              <Close />
            </IconButton>
          </Toolbar>
        </AppBar>

        <Box sx={{ p: 2 }}>
          <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
            <Button
              size="small"
              onClick={() => setNotifications(prev => prev.map(n => ({ ...n, isRead: true })))}
            >
              Mark All Read
            </Button>
            <Button size="small" variant="outlined">
              Filter
            </Button>
          </Box>

          <List sx={{ p: 0 }}>
            {notifications.map((notification) => (
              <React.Fragment key={notification.id}>
                <ListItem
                  alignItems="flex-start"
                  sx={{
                    bgcolor: notification.isRead ? 'transparent' : 'action.hover',
                    borderRadius: 1,
                    mb: 1,
                    border: notification.priority === 'critical' ? 2 : 0,
                    borderColor: 'error.main',
                    cursor: 'pointer'
                  }}
                  onClick={() => {
                    markAsRead(notification.id);
                    if (onNotificationClick) {
                      onNotificationClick(notification);
                    }
                  }}
                >
                  <ListItemIcon sx={{ minWidth: 40 }}>
                    <Avatar sx={{ bgcolor: getPriorityColor(notification.priority) + '.main' }}>
                      {getNotificationIcon(notification.type)}
                    </Avatar>
                  </ListItemIcon>

                  <ListItemText
                    primary={
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Typography
                          variant="subtitle2"
                          fontWeight={notification.isRead ? 'normal' : 'bold'}
                        >
                          {notification.title}
                        </Typography>
                        <Chip
                          icon={getPriorityIcon(notification.priority)}
                          label={notification.priority.toUpperCase()}
                          color={getPriorityColor(notification.priority) as any}
                          size="small"
                        />
                      </Box>
                    }
                    secondary={
                      <Box>
                        <Typography variant="body2" color="text.secondary" paragraph>
                          {expandedItems.has(notification.id)
                            ? notification.message
                            : notification.message.length > 80
                            ? notification.message.substring(0, 80) + '...'
                            : notification.message
                          }
                        </Typography>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
                          <Chip
                            label={notification.source}
                            size="small"
                            variant="outlined"
                          />
                          {notification.location && (
                            <Chip
                              icon={<LocationOn />}
                              label={notification.location}
                              size="small"
                              variant="outlined"
                            />
                          )}
                          <Typography variant="caption" color="text.secondary">
                            <AccessTime sx={{ fontSize: 12, mr: 0.5 }} />
                            {notification.timestamp.toLocaleString()}
                          </Typography>
                        </Box>
                        {notification.actionRequired && (
                          <Button
                            size="small"
                            color="primary"
                            sx={{ mt: 1 }}
                            onClick={(e) => {
                              e.stopPropagation();
                              // Handle action
                            }}
                          >
                            Take Action
                          </Button>
                        )}
                      </Box>
                    }
                  />

                  <ListItemSecondaryAction>
                    <IconButton
                      edge="end"
                      size="small"
                      onClick={(e) => {
                        e.stopPropagation();
                        toggleExpanded(notification.id);
                      }}
                    >
                      {expandedItems.has(notification.id) ? <ExpandLess /> : <ExpandMore />}
                    </IconButton>
                  </ListItemSecondaryAction>
                </ListItem>
              </React.Fragment>
            ))}
          </List>

          {notifications.length === 0 && (
            <Box sx={{ textAlign: 'center', py: 4 }}>
              <CheckCircle sx={{ fontSize: 48, color: 'success.main', mb: 1 }} />
              <Typography variant="h6">No Active Alerts</Typography>
              <Typography variant="body2" color="text.secondary">
                All systems operating normally
              </Typography>
            </Box>
          )}
        </Box>
      </Drawer>

      {/* Toast Notification for New Alerts */}
      <Snackbar
        open={snackbarOpen}
        autoHideDuration={6000}
        onClose={() => setSnackbarOpen(false)}
        anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
      >
        <Alert
          severity={latestNotification?.priority === 'critical' ? 'error' : 'info'}
          onClose={() => setSnackbarOpen(false)}
          sx={{ width: '100%' }}
        >
          <Typography variant="subtitle2">
            New Alert: {latestNotification?.title}
          </Typography>
        </Alert>
      </Snackbar>

      <style>
        {`
          @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
          }

          @keyframes slideInRight {
            from {
              transform: translateX(100%);
              opacity: 0;
            }
            to {
              transform: translateX(0);
              opacity: 1;
            }
          }
        `}
      </style>
    </>
  );
};

export default RealTimeNotifications;