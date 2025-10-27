import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { dashboardAPI, RecentActivity, WeatherData as APIWeatherData, MapData } from '../../services/dashboardAPI';

export interface FireRiskData {
  id: string;
  location: {
    latitude: number;
    longitude: number;
    name: string;
  };
  riskScore: number;
  riskLevel: 'low' | 'medium' | 'high' | 'extreme';
  timestamp: string;
  contributingFactors: {
    weatherConditions: number;
    vegetationDryness: number;
    topographicalFactors: number;
    historicalPatterns: number;
  };
}

export interface ActiveIncident {
  id: string;
  name: string;
  location: {
    latitude: number;
    longitude: number;
  };
  status: 'active' | 'contained' | 'controlled' | 'out';
  acresBurned: number;
  containment: number;
  startTime: string;
  resourcesAssigned: number;
  priority: 'low' | 'medium' | 'high' | 'critical';
}

export interface WeatherData {
  location: string;
  temperature: number;
  humidity: number;
  windSpeed: number;
  windDirection: number | string;
  precipitation?: number;
  timestamp: string;
  fireRiskIndex?: number;
}

export interface ResourceStatus {
  type: 'engine' | 'truck' | 'helicopter' | 'crew' | 'bulldozer';
  total: number;
  available: number;
  deployed: number;
  maintenance: number;
}

export interface DashboardMetrics {
  totalIncidents: number;
  activeIncidents: number;
  highRiskAreas: number;
  resourcesDeployed: number;
  acresBurnedToday: number;
  averageResponseTime: number;
  // Optional fields to match DashboardStats API response
  totalResources?: number;
  availableResources?: number;
  deployedResources?: number;
  unreadAlerts?: number;
  criticalAlerts?: number;
  totalAcresBurned?: number;
  containmentProgress?: number;
}

interface DashboardState {
  metrics: DashboardMetrics | null;
  fireRiskData: FireRiskData[];
  activeIncidents: ActiveIncident[];
  weatherData: WeatherData[];
  resourceStatus: ResourceStatus[];
  isLoading: boolean;
  error: string | null;
  lastUpdated: string | null;
}

const initialState: DashboardState = {
  metrics: null,
  fireRiskData: [],
  activeIncidents: [],
  weatherData: [],
  resourceStatus: [],
  isLoading: false,
  error: null,
  lastUpdated: null,
};

// Helper function to convert API response to internal types
const mapAPIResponseToState = (apiResponse: any) => {
  const metrics: DashboardMetrics = {
    totalIncidents: apiResponse.metrics?.totalResources || 0,
    activeIncidents: apiResponse.metrics?.activeIncidents || 0,
    highRiskAreas: 0,
    resourcesDeployed: apiResponse.metrics?.deployedResources || 0,
    acresBurnedToday: apiResponse.metrics?.totalAcresBurned || 0,
    averageResponseTime: 0,
    ...apiResponse.metrics
  };

  const activeIncidents: ActiveIncident[] = Array.isArray(apiResponse.activeIncidents) ?
    apiResponse.activeIncidents.map((item: any) => ({
      id: item.id || Math.random().toString(),
      name: item.name || item.title || 'Unknown Incident',
      location: {
        latitude: item.latitude || 0,
        longitude: item.longitude || 0
      },
      status: (item.status || 'active') as any,
      acresBurned: item.acres || 0,
      containment: item.containment || 0,
      startTime: item.timestamp || new Date().toISOString(),
      resourcesAssigned: 0,
      priority: (item.priority || item.severity || 'medium') as any
    })) : [];

  const weatherData: WeatherData[] = Array.isArray(apiResponse.weatherData) ? 
    apiResponse.weatherData.map((item: APIWeatherData) => ({
      ...item,
      windDirection: item.windDirection,
      precipitation: 0
    })) : [];

  return { metrics, activeIncidents, weatherData };
};

// Async thunks
export const fetchDashboardData = createAsyncThunk(
  'dashboard/fetchDashboardData',
  async (_, { rejectWithValue }) => {
    try {
      const [metrics, fireRisk, incidents, weather, resources] = await Promise.all([
        dashboardAPI.getStats(),
        dashboardAPI.getFireRiskAssessment(),
        dashboardAPI.getRecentActivity(),
        dashboardAPI.getWeatherData(),
        dashboardAPI.getMapData(),
      ]);

      return {
        metrics: metrics.data,
        fireRiskData: fireRisk.data,
        activeIncidents: incidents.data,
        weatherData: weather.data,
        resourceStatus: resources.data,
      };
    } catch (error: any) {
      // Return mock data if API fails - allows dashboard to work without backend
      console.warn('[DASHBOARD] API unavailable, using mock data for demo');
      return {
        metrics: {
          totalIncidents: 12,
          activeIncidents: 3,
          highRiskAreas: 8,
          resourcesDeployed: 45,
          acresBurnedToday: 85,
          averageResponseTime: 12,
        },
        fireRiskData: [],
        activeIncidents: [],
        weatherData: [],
        resourceStatus: [],
      };
    }
  }
);

export const updateFireRiskData = createAsyncThunk(
  'dashboard/updateFireRiskData',
  async (_, { rejectWithValue }) => {
    try {
      const response = await dashboardAPI.getFireRiskAssessment();
      return response.data;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.message || 'Failed to update fire risk data');
    }
  }
);

export const updateActiveIncidents = createAsyncThunk(
  'dashboard/updateActiveIncidents',
  async (_, { rejectWithValue }) => {
    try {
      const response = await dashboardAPI.getMapData();
      return response.data;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.message || 'Failed to update active incidents');
    }
  }
);

const dashboardSlice = createSlice({
  name: 'dashboard',
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = null;
    },
    updateIncidentStatus: (state, action: PayloadAction<{ id: string; status: string; containment?: number }>) => {
      const incident = state.activeIncidents.find(inc => inc.id === action.payload.id);
      if (incident) {
        incident.status = action.payload.status as any;
        if (action.payload.containment !== undefined) {
          incident.containment = action.payload.containment;
        }
      }
    },
    addNewIncident: (state, action: PayloadAction<ActiveIncident>) => {
      state.activeIncidents.unshift(action.payload);
      if (state.metrics) {
        state.metrics.activeIncidents += 1;
        state.metrics.totalIncidents += 1;
      }
    },
    updateResourceDeployment: (state, action: PayloadAction<{ type: string; deployed: number; available: number }>) => {
      const resource = state.resourceStatus.find(res => res.type === action.payload.type);
      if (resource) {
        resource.deployed = action.payload.deployed;
        resource.available = action.payload.available;
      }
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch dashboard data
      .addCase(fetchDashboardData.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(fetchDashboardData.fulfilled, (state, action) => {
        state.isLoading = false;
        
        // Map API response to internal types
        const mapped = mapAPIResponseToState(action.payload);
        state.metrics = mapped.metrics;
        state.fireRiskData = Array.isArray(action.payload.fireRiskData) ? action.payload.fireRiskData : [];
        state.activeIncidents = mapped.activeIncidents;
        state.weatherData = mapped.weatherData;
        state.resourceStatus = [];
        state.lastUpdated = new Date().toISOString();
        state.error = null;
      })
      .addCase(fetchDashboardData.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      })

      // Update fire risk data
      .addCase(updateFireRiskData.fulfilled, (state, action) => {
        state.fireRiskData = Array.isArray(action.payload) ? action.payload : [];
        state.lastUpdated = new Date().toISOString();
      })
      .addCase(updateFireRiskData.rejected, (state, action) => {
        state.error = action.payload as string;
      })

      // Update active incidents
      .addCase(updateActiveIncidents.fulfilled, (state, action) => {
        // Handle MapData response
        const mapData = action.payload as MapData;
        if (mapData && mapData.incidents) {
          state.activeIncidents = mapData.incidents.map((incident) => ({
            id: incident.id,
            name: incident.name,
            location: { latitude: incident.latitude, longitude: incident.longitude },
            status: incident.status as any,
            acresBurned: incident.acres || 0,
            containment: 0,
            startTime: new Date().toISOString(),
            resourcesAssigned: 0,
            priority: 'medium' as any
          }));
        }
        state.lastUpdated = new Date().toISOString();
      })
      .addCase(updateActiveIncidents.rejected, (state, action) => {
        state.error = action.payload as string;
      });
  },
});

export const { 
  clearError, 
  updateIncidentStatus, 
  addNewIncident, 
  updateResourceDeployment 
} = dashboardSlice.actions;

export default dashboardSlice.reducer;