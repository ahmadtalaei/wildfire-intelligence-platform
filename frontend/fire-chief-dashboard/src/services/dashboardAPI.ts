import apiClient from './authAPI';

export interface DashboardStats {
  activeIncidents: number;
  totalResources: number;
  availableResources: number;
  deployedResources: number;
  unreadAlerts: number;
  criticalAlerts: number;
  totalAcresBurned: number;
  containmentProgress: number;
}

export interface RecentActivity {
  id: string;
  type: 'incident_created' | 'incident_updated' | 'resource_deployed' | 'alert_created' | 'resource_returned';
  title: string;
  description: string;
  timestamp: string;
  severity?: 'low' | 'medium' | 'high' | 'critical';
  location?: string;
}

export interface WeatherData {
  location: string;
  temperature: number;
  humidity: number;
  windSpeed: number;
  windDirection: string;
  fireRiskIndex: number;
  timestamp: string;
}

export interface MapData {
  incidents: Array<{
    id: string;
    name: string;
    latitude: number;
    longitude: number;
    status: string;
    acres: number;
  }>;
  resources: Array<{
    id: string;
    name: string;
    type: string;
    latitude: number;
    longitude: number;
    status: string;
  }>;
  weatherStations: Array<{
    id: string;
    name: string;
    latitude: number;
    longitude: number;
    temperature: number;
    windSpeed: number;
  }>;
}

export const dashboardAPI = {
  // Get dashboard statistics
  getStats: async () => {
    try {
      const response = await apiClient.get<DashboardStats>('/dashboard/stats');
      return response;
    } catch (error) {
      // Mock data for demo
      const mockStats: DashboardStats = {
        activeIncidents: 3,
        totalResources: 25,
        availableResources: 18,
        deployedResources: 7,
        unreadAlerts: 5,
        criticalAlerts: 1,
        totalAcresBurned: 12450,
        containmentProgress: 65,
      };
      return { data: mockStats };
    }
  },

  // Get recent activity
  getRecentActivity: async (limit: number = 10) => {
    try {
      const response = await apiClient.get<RecentActivity[]>(`/dashboard/activity?limit=${limit}`);
      return response;
    } catch (error) {
      // Mock data for demo
      const mockActivity: RecentActivity[] = [
        {
          id: '1',
          type: 'incident_created',
          title: 'New Fire Incident',
          description: 'Mountain View Fire reported in San Bernardino County',
          timestamp: new Date(Date.now() - 1800000).toISOString(),
          severity: 'high',
          location: 'San Bernardino County',
        },
        {
          id: '2',
          type: 'resource_deployed',
          title: 'Engine 15 Deployed',
          description: 'Engine 15 deployed to Riverside Fire incident',
          timestamp: new Date(Date.now() - 3600000).toISOString(),
          severity: 'medium',
          location: 'Riverside County',
        },
        {
          id: '3',
          type: 'alert_created',
          title: 'High Fire Risk Alert',
          description: 'Elevated fire risk conditions detected',
          timestamp: new Date(Date.now() - 7200000).toISOString(),
          severity: 'high',
          location: 'Multiple Counties',
        },
      ];
      return { data: mockActivity };
    }
  },

  // Get weather data
  getWeatherData: async () => {
    try {
      const response = await apiClient.get<WeatherData[]>('/dashboard/weather');
      return response;
    } catch (error) {
      // Mock data for demo
      const mockWeather: WeatherData[] = [
        {
          location: 'Riverside County',
          temperature: 85,
          humidity: 15,
          windSpeed: 25,
          windDirection: 'SW',
          fireRiskIndex: 8.5,
          timestamp: new Date().toISOString(),
        },
        {
          location: 'San Bernardino County',
          temperature: 82,
          humidity: 20,
          windSpeed: 18,
          windDirection: 'W',
          fireRiskIndex: 7.2,
          timestamp: new Date().toISOString(),
        },
      ];
      return { data: mockWeather };
    }
  },

  // Get map data (real fire detections from database)
  getMapData: async () => {
    try {
      // Call the real fire detection endpoint
      const response = await fetch('http://localhost:8001/api/v1/recent-fires?limit=50');
      const data = await response.json();

      if (data.status === 'success' && data.fires) {
        // Convert real fire data to MapData format
        const incidents = data.fires.map((fire: any, index: number) => ({
          id: `fire-${index}`,
          name: `${fire.satellite} Detection`,
          latitude: fire.latitude,
          longitude: fire.longitude,
          status: 'active',
          acres: 0, // Not available in detection data
        }));

        const mockMapData: MapData = {
          incidents,
          resources: [],
          weatherStations: [],
        };
        return { data: mockMapData };
      }
      throw new Error('Invalid response from fire detection API');
    } catch (error) {
      console.error('[DASHBOARD API] Failed to fetch real fire data, using fallback', error);
      // Fallback mock data if real API fails
      const mockMapData: MapData = {
        incidents: [
          {
            id: '1',
            name: 'Riverside Fire',
            latitude: 33.9533,
            longitude: -117.3962,
            status: 'active',
            acres: 2450,
          },
          {
            id: '2',
            name: 'Mountain View Fire',
            latitude: 34.2839,
            longitude: -116.8949,
            status: 'contained',
            acres: 850,
          },
        ],
        resources: [],
        weatherStations: [],
      };
      return { data: mockMapData };
    }
  },

  // Get fire risk assessment
  getFireRiskAssessment: async () => {
    try {
      const response = await apiClient.get('/dashboard/fire-risk');
      return response;
    } catch (error) {
      return {
        data: {
          overallRisk: 'high',
          riskScore: 8.2,
          factors: {
            temperature: 'high',
            humidity: 'low',
            windSpeed: 'high',
            vegetation: 'dry',
            precipitation: 'none',
          },
          predictions: {
            next24Hours: 'high',
            next7Days: 'medium',
            next30Days: 'low',
          },
        },
      };
    }
  },
};