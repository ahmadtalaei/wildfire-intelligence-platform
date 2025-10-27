import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';

export interface Resource {
  id: string;
  type: 'engine' | 'helicopter' | 'crew' | 'aircraft';
  name: string;
  location: string;
  status: 'available' | 'deployed' | 'maintenance' | 'offline';
  personnel: number;
  assignedIncident?: string;
  coordinates?: {
    lat: number;
    lng: number;
  };
}

interface ResourcesState {
  resources: Resource[];
  loading: boolean;
  error: string | null;
  selectedResource: Resource | null;
  filters: {
    type: string;
    status: string;
    location: string;
  };
}

const initialState: ResourcesState = {
  resources: [],
  loading: false,
  error: null,
  selectedResource: null,
  filters: {
    type: 'all',
    status: 'all',
    location: 'all',
  },
};

// Async thunks
export const fetchResources = createAsyncThunk(
  'resources/fetchResources',
  async (_, { rejectWithValue }) => {
    try {
      // TODO: Replace with actual API call
      const response = await fetch('/api/resources');
      if (!response.ok) {
        throw new Error('Failed to fetch resources');
      }
      return await response.json();
    } catch (error) {
      return rejectWithValue(error instanceof Error ? error.message : 'Unknown error');
    }
  }
);

export const updateResourceStatus = createAsyncThunk(
  'resources/updateResourceStatus',
  async ({ resourceId, status }: { resourceId: string; status: Resource['status'] }, { rejectWithValue }) => {
    try {
      // TODO: Replace with actual API call
      const response = await fetch(`/api/resources/${resourceId}/status`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ status }),
      });
      
      if (!response.ok) {
        throw new Error('Failed to update resource status');
      }
      
      return await response.json();
    } catch (error) {
      return rejectWithValue(error instanceof Error ? error.message : 'Unknown error');
    }
  }
);

export const assignResourceToIncident = createAsyncThunk(
  'resources/assignResourceToIncident',
  async ({ resourceId, incidentId }: { resourceId: string; incidentId: string }, { rejectWithValue }) => {
    try {
      // TODO: Replace with actual API call
      const response = await fetch(`/api/resources/${resourceId}/assign`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ incidentId }),
      });
      
      if (!response.ok) {
        throw new Error('Failed to assign resource');
      }
      
      return await response.json();
    } catch (error) {
      return rejectWithValue(error instanceof Error ? error.message : 'Unknown error');
    }
  }
);

const resourcesSlice = createSlice({
  name: 'resources',
  initialState,
  reducers: {
    setSelectedResource: (state, action: PayloadAction<Resource | null>) => {
      state.selectedResource = action.payload;
    },
    updateFilters: (state, action: PayloadAction<Partial<ResourcesState['filters']>>) => {
      state.filters = { ...state.filters, ...action.payload };
    },
    clearError: (state) => {
      state.error = null;
    },
    addResource: (state, action: PayloadAction<Resource>) => {
      state.resources.push(action.payload);
    },
    updateResource: (state, action: PayloadAction<Resource>) => {
      const index = state.resources.findIndex(r => r.id === action.payload.id);
      if (index !== -1) {
        state.resources[index] = action.payload;
      }
    },
    removeResource: (state, action: PayloadAction<string>) => {
      state.resources = state.resources.filter(r => r.id !== action.payload);
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch resources
      .addCase(fetchResources.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchResources.fulfilled, (state, action) => {
        state.loading = false;
        state.resources = action.payload;
        state.error = null;
      })
      .addCase(fetchResources.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      })
      
      // Update resource status
      .addCase(updateResourceStatus.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(updateResourceStatus.fulfilled, (state, action) => {
        state.loading = false;
        const index = state.resources.findIndex(r => r.id === action.payload.id);
        if (index !== -1) {
          state.resources[index] = action.payload;
        }
        state.error = null;
      })
      .addCase(updateResourceStatus.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      })
      
      // Assign resource to incident
      .addCase(assignResourceToIncident.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(assignResourceToIncident.fulfilled, (state, action) => {
        state.loading = false;
        const index = state.resources.findIndex(r => r.id === action.payload.id);
        if (index !== -1) {
          state.resources[index] = action.payload;
        }
        state.error = null;
      })
      .addCase(assignResourceToIncident.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      });
  },
});

export const {
  setSelectedResource,
  updateFilters,
  clearError,
  addResource,
  updateResource,
  removeResource,
} = resourcesSlice.actions;

export default resourcesSlice.reducer;