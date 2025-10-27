import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { incidentsAPI, Incident, IncidentFilters } from '../../services/incidentsAPI';
import { ActiveIncident } from './dashboardSlice';

export interface IncidentDetails extends ActiveIncident {
  description: string;
  cause: string | null;
  weather: {
    temperature: number;
    humidity: number;
    windSpeed: number;
    windDirection: number;
  };
  resources: {
    engines: number;
    crews: number;
    helicopters: number;
    dozers: number;
  };
  timeline: {
    timestamp: string;
    event: string;
    description: string;
  }[];
  evacuation: {
    zonesEvacuated: string[];
    peopleEvacuated: number;
    sheltersOpen: number;
  };
  structures: {
    threatened: number;
    damaged: number;
    destroyed: number;
  };
  costs: {
    suppressionCost: number;
    estimatedDamages: number;
  };
}

export interface NewIncidentData {
  name: string;
  location: {
    latitude: number;
    longitude: number;
  };
  description: string;
  reportedBy: string;
  priority: 'low' | 'medium' | 'high' | 'critical';
}

interface IncidentsState {
  incidents: ActiveIncident[];
  selectedIncident: IncidentDetails | null;
  filters: {
    status: string[];
    priority: string[];
    dateRange: {
      start: string | null;
      end: string | null;
    };
  };
  isLoading: boolean;
  isCreating: boolean;
  isUpdating: boolean;
  error: string | null;
}

const initialState: IncidentsState = {
  incidents: [],
  selectedIncident: null,
  filters: {
    status: [],
    priority: [],
    dateRange: {
      start: null,
      end: null,
    },
  },
  isLoading: false,
  isCreating: false,
  isUpdating: false,
  error: null,
};

// Helper function to convert Incident to ActiveIncident
const mapIncidentToActiveIncident = (incident: Incident): ActiveIncident => ({
  id: incident.id,
  name: incident.name,
  location: {
    latitude: incident.location.latitude,
    longitude: incident.location.longitude,
  },
  status: incident.status === 'extinguished' ? 'out' : incident.status as any,
  acresBurned: incident.acres,
  containment: incident.containmentPercentage,
  startTime: incident.startDate,
  resourcesAssigned: incident.assignedResources.length,
  priority: incident.severity as any,
});

// Helper function to convert ActiveIncident to Incident creation data
const mapNewIncidentDataToIncident = (data: NewIncidentData): Omit<Incident, 'id' | 'updates'> => ({
  name: data.name,
  type: 'wildfire',
  status: 'active',
  severity: data.priority,
  location: {
    latitude: data.location.latitude,
    longitude: data.location.longitude,
    address: '',
    county: '',
    state: 'CA',
  },
  startDate: new Date().toISOString(),
  acres: 0,
  containmentPercentage: 0,
  threatenedStructures: 0,
  destroyedStructures: 0,
  injuries: 0,
  fatalities: 0,
  assignedResources: [],
  description: data.description,
});

// Async thunks
export const fetchIncidents = createAsyncThunk(
  'incidents/fetchIncidents',
  async (filters: IncidentFilters = {}, { rejectWithValue }) => {
    try {
      const response = await incidentsAPI.getIncidents(filters);
      return response.data;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.message || 'Failed to fetch incidents');
    }
  }
);

export const fetchIncidentDetails = createAsyncThunk(
  'incidents/fetchIncidentDetails',
  async (incidentId: string, { rejectWithValue }) => {
    try {
      const response = await incidentsAPI.getIncident(incidentId);
      return response.data;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.message || 'Failed to fetch incident details');
    }
  }
);

export const createIncident = createAsyncThunk(
  'incidents/createIncident',
  async (incidentData: NewIncidentData, { rejectWithValue }) => {
    try {
      const mappedData = mapNewIncidentDataToIncident(incidentData);
      const response = await incidentsAPI.createIncident(mappedData);
      return response.data;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.message || 'Failed to create incident');
    }
  }
);

export const updateIncident = createAsyncThunk(
  'incidents/updateIncident',
  async ({ id, data }: { id: string; data: Partial<Incident> }, { rejectWithValue }) => {
    try {
      const response = await incidentsAPI.updateIncident(id, data);
      return response.data;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.message || 'Failed to update incident');
    }
  }
);

export const assignResources = createAsyncThunk(
  'incidents/assignResources',
  async ({ incidentId, resourceId }: { incidentId: string; resourceId: string }, { rejectWithValue }) => {
    try {
      const response = await incidentsAPI.assignResource(incidentId, resourceId);
      // Use response if needed: console.log(response);
      return { incidentId, resourceId };
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.message || 'Failed to assign resources');
    }
  }
);

const incidentsSlice = createSlice({
  name: 'incidents',
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = null;
    },
    setFilters: (state, action: PayloadAction<Partial<IncidentsState['filters']>>) => {
      state.filters = { ...state.filters, ...action.payload };
    },
    clearSelectedIncident: (state) => {
      state.selectedIncident = null;
    },
    updateIncidentStatus: (state, action: PayloadAction<{ id: string; status: string; containment?: number }>) => {
      const incident = state.incidents.find(inc => inc.id === action.payload.id);
      if (incident) {
        incident.status = action.payload.status as any;
        if (action.payload.containment !== undefined) {
          incident.containment = action.payload.containment;
        }
      }
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch incidents
      .addCase(fetchIncidents.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(fetchIncidents.fulfilled, (state, action) => {
        state.isLoading = false;
        // Convert Incident[] to ActiveIncident[]
        state.incidents = action.payload.map(mapIncidentToActiveIncident);
        state.error = null;
      })
      .addCase(fetchIncidents.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      })

      // Fetch incident details
      .addCase(fetchIncidentDetails.pending, (state) => {
        state.isLoading = true;
      })
      .addCase(fetchIncidentDetails.fulfilled, (state, action) => {
        state.isLoading = false;
        // Convert Incident to IncidentDetails
        const incident = action.payload;
        state.selectedIncident = {
          ...mapIncidentToActiveIncident(incident),
          description: incident.description || '',
          cause: incident.cause || null,
          weather: {
            temperature: incident.weather?.temperature || 0,
            humidity: incident.weather?.humidity || 0,
            windSpeed: incident.weather?.windSpeed || 0,
            windDirection: 0,
          },
          resources: {
            engines: 0,
            crews: 0,
            helicopters: 0,
            dozers: 0,
          },
          timeline: incident.updates.map(update => ({
            timestamp: update.timestamp,
            event: update.type,
            description: update.message,
          })),
          evacuation: {
            zonesEvacuated: [],
            peopleEvacuated: 0,
            sheltersOpen: 0,
          },
          structures: {
            threatened: incident.threatenedStructures,
            damaged: 0,
            destroyed: incident.destroyedStructures,
          },
          costs: {
            suppressionCost: 0,
            estimatedDamages: 0,
          },
        };
      })
      .addCase(fetchIncidentDetails.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      })

      // Create incident
      .addCase(createIncident.pending, (state) => {
        state.isCreating = true;
        state.error = null;
      })
      .addCase(createIncident.fulfilled, (state, action) => {
        state.isCreating = false;
        const newActiveIncident = mapIncidentToActiveIncident(action.payload);
        state.incidents.unshift(newActiveIncident);
        state.error = null;
      })
      .addCase(createIncident.rejected, (state, action) => {
        state.isCreating = false;
        state.error = action.payload as string;
      })

      // Update incident
      .addCase(updateIncident.pending, (state) => {
        state.isUpdating = true;
        state.error = null;
      })
      .addCase(updateIncident.fulfilled, (state, action) => {
        state.isUpdating = false;
        
        // Update in incidents array
        const index = state.incidents.findIndex(inc => inc.id === action.payload.id);
        if (index !== -1) {
          state.incidents[index] = mapIncidentToActiveIncident(action.payload);
        }
        
        // Update selected incident if it's the same
        if (state.selectedIncident && state.selectedIncident.id === action.payload.id) {
          // Re-fetch details or update from payload
          const incident = action.payload;
          state.selectedIncident = {
            ...mapIncidentToActiveIncident(incident),
            description: incident.description || '',
            cause: incident.cause || null,
            weather: {
              temperature: incident.weather?.temperature || 0,
              humidity: incident.weather?.humidity || 0,
              windSpeed: incident.weather?.windSpeed || 0,
              windDirection: 0,
            },
            resources: state.selectedIncident.resources,
            timeline: state.selectedIncident.timeline,
            evacuation: state.selectedIncident.evacuation,
            structures: {
              threatened: incident.threatenedStructures,
              damaged: 0,
              destroyed: incident.destroyedStructures,
            },
            costs: state.selectedIncident.costs,
          };
        }
        
        state.error = null;
      })
      .addCase(updateIncident.rejected, (state, action) => {
        state.isUpdating = false;
        state.error = action.payload as string;
      })

      // Assign resources
      .addCase(assignResources.fulfilled, (state, action) => {
        const incident = state.incidents.find(inc => inc.id === action.payload.incidentId);
        if (incident) {
          incident.resourcesAssigned += 1;
        }
      })
      .addCase(assignResources.rejected, (state, action) => {
        state.error = action.payload as string;
      });
  },
});

export const { 
  clearError, 
  setFilters, 
  clearSelectedIncident, 
  updateIncidentStatus 
} = incidentsSlice.actions;

export default incidentsSlice.reducer;