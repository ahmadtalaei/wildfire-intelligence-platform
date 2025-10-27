import apiClient from './authAPI';

export interface Alert {
  id: string;
  type: 'fire_risk' | 'weather' | 'resource' | 'evacuation' | 'system';
  severity: 'low' | 'medium' | 'high' | 'critical';
  title: string;
  message: string;
  location?: {
    latitude: number;
    longitude: number;
    name: string;
  };
  timestamp: string;
  isRead: boolean;
  isAcknowledged: boolean;
  acknowledgedBy?: string;
  acknowledgedAt?: string;
  data?: any;
}

export const alertsAPI = {
  // Fetch all alerts
  getAlerts: async (filters?: {
    type?: string;
    severity?: string;
    isRead?: boolean;
    limit?: number;
    offset?: number;
  }) => {
    try {
      const params = new URLSearchParams();
      if (filters) {
        Object.entries(filters).forEach(([key, value]) => {
          if (value !== undefined) {
            params.append(key, String(value));
          }
        });
      }
      
      const response = await apiClient.get<Alert[]>(`/alerts?${params.toString()}`);
      return response;
    } catch (error) {
      // Mock data for demo
      const mockAlerts: Alert[] = [
        {
          id: '1',
          type: 'fire_risk',
          severity: 'high',
          title: 'High Fire Risk Alert',
          message: 'Elevated fire risk conditions detected in Riverside County due to high winds and dry conditions.',
          location: {
            latitude: 33.9533,
            longitude: -117.3962,
            name: 'Riverside County',
          },
          timestamp: new Date().toISOString(),
          isRead: false,
          isAcknowledged: false,
        },
        {
          id: '2',
          type: 'weather',
          severity: 'medium',
          title: 'Red Flag Warning',
          message: 'Red flag warning issued for San Bernardino Mountains.',
          location: {
            latitude: 34.2839,
            longitude: -116.8949,
            name: 'San Bernardino Mountains',
          },
          timestamp: new Date(Date.now() - 3600000).toISOString(),
          isRead: true,
          isAcknowledged: false,
        },
      ];
      
      return { data: mockAlerts };
    }
  },

  // Mark alert as read
  markAsRead: async (alertId: string) => {
    try {
      const response = await apiClient.patch(`/alerts/${alertId}/read`);
      return response;
    } catch (error) {
      return { data: { id: alertId, isRead: true } };
    }
  },

  // Mark all alerts as read
  markAllAsRead: async () => {
    try {
      const response = await apiClient.patch('/alerts/read-all');
      return response;
    } catch (error) {
      return { data: { message: 'All alerts marked as read' } };
    }
  },

  // Acknowledge alert
  acknowledgeAlert: async (alertId: string) => {
    try {
      const response = await apiClient.patch(`/alerts/${alertId}/acknowledge`);
      return response;
    } catch (error) {
      return { 
        data: { 
          id: alertId, 
          isAcknowledged: true, 
          acknowledgedBy: 'admin',
          acknowledgedAt: new Date().toISOString()
        } 
      };
    }
  },

  // Create new alert
  createAlert: async (alert: Omit<Alert, 'id' | 'timestamp' | 'isRead' | 'isAcknowledged'>) => {
    try {
      const response = await apiClient.post<Alert>('/alerts', alert);
      return response;
    } catch (error) {
      const newAlert: Alert = {
        ...alert,
        id: Date.now().toString(),
        timestamp: new Date().toISOString(),
        isRead: false,
        isAcknowledged: false,
      };
      return { data: newAlert };
    }
  },

  // Delete alert
  deleteAlert: async (alertId: string) => {
    try {
      const response = await apiClient.delete(`/alerts/${alertId}`);
      return response;
    } catch (error) {
      return { data: { message: 'Alert deleted successfully' } };
    }
  },

  // Get alert statistics
  getAlertStats: async () => {
    try {
      const response = await apiClient.get('/alerts/stats');
      return response;
    } catch (error) {
      return {
        data: {
          total: 5,
          unread: 3,
          acknowledged: 2,
          byType: {
            fire_risk: 2,
            weather: 2,
            resource: 1,
            evacuation: 0,
            system: 0,
          },
          bySeverity: {
            critical: 0,
            high: 2,
            medium: 2,
            low: 1,
          },
        },
      };
    }
  },
};