import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { alertsAPI } from '../../services/alertsAPI';

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
  expiresAt?: string;
}

export interface AlertRule {
  id: string;
  name: string;
  description: string;
  type: string;
  condition: string;
  severity: string;
  isActive: boolean;
  channels: string[];
  recipients: string[];
  cooldown: number;
  createdAt: string;
  updatedAt: string;
}

interface AlertsState {
  alerts: Alert[];
  rules: AlertRule[];
  unreadCount: number;
  filters: {
    severity: string[];
    type: string[];
    isRead: boolean | null;
    dateRange: {
      start: string | null;
      end: string | null;
    };
  };
  isLoading: boolean;
  error: string | null;
}

const initialState: AlertsState = {
  alerts: [],
  rules: [],
  unreadCount: 0,
  filters: {
    severity: [],
    type: [],
    isRead: null,
    dateRange: {
      start: null,
      end: null,
    },
  },
  isLoading: false,
  error: null,
};

// Async thunks
export const fetchAlerts = createAsyncThunk(
  'alerts/fetchAlerts',
  async (filters: any = {}, { rejectWithValue }) => {
    try {
      const response = await alertsAPI.getAlerts(filters);
      return response.data;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.message || 'Failed to fetch alerts');
    }
  }
);

// export const fetchAlertRules = createAsyncThunk(
//   'alerts/fetchAlertRules',
//   async (_, { rejectWithValue }) => {
//     try {
//       const response = await alertsAPI.getAlerts();
//       return response.data;
//     } catch (error: any) {
//       return rejectWithValue(error.response?.data?.message || 'Failed to fetch alert rules');
//     }
//   }
// );

export const acknowledgeAlert = createAsyncThunk(
  'alerts/acknowledgeAlert',
  async (alertId: string, { rejectWithValue }) => {
    try {
      const response = await alertsAPI.acknowledgeAlert(alertId);
      return { alertId, ...response.data };
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.message || 'Failed to acknowledge alert');
    }
  }
);

export const markAlertAsRead = createAsyncThunk(
  'alerts/markAlertAsRead',
  async (alertId: string, { rejectWithValue }) => {
    try {
      await alertsAPI.markAsRead(alertId);
      return alertId;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.message || 'Failed to mark alert as read');
    }
  }
);

export const markAllAlertsAsRead = createAsyncThunk(
  'alerts/markAllAlertsAsRead',
  async (_, { rejectWithValue }) => {
    try {
      await alertsAPI.markAllAsRead();
      return null;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.message || 'Failed to mark all alerts as read');
    }
  }
);

export const createAlertRule = createAsyncThunk(
  'alerts/createAlertRule',
  async (ruleData: any, { rejectWithValue }) => {
    try {
      const response = await alertsAPI.createAlert(ruleData);
      return response.data;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.message || 'Failed to create alert rule');
    }
  }
);

// export const updateAlertRule = createAsyncThunk(
//   'alerts/updateAlertRule',
//   async ({ id, data }: { id: string; data: Partial<AlertRule> }, { rejectWithValue }) => {
//     try {
//       const response = await alertsAPI.updateAlertRule(id, data);
//       return response.data;
//     } catch (error: any) {
//       return rejectWithValue(error.response?.data?.message || 'Failed to update alert rule');
//     }
//   }
// );

// export const deleteAlertRule = createAsyncThunk(
//   'alerts/deleteAlertRule',
//   async (ruleId: string, { rejectWithValue }) => {
//     try {
//       await alertsAPI.deleteAlertRule(ruleId);
//       return ruleId;
//     } catch (error: any) {
//       return rejectWithValue(error.response?.data?.message || 'Failed to delete alert rule');
//     }
//   }
// );

const alertsSlice = createSlice({
  name: 'alerts',
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = null;
    },
    addNewAlert: (state, action: PayloadAction<Alert>) => {
      state.alerts.unshift(action.payload);
      if (!action.payload.isRead) {
        state.unreadCount += 1;
      }
    },
    updateFilters: (state, action: PayloadAction<Partial<typeof initialState.filters>>) => {
      state.filters = { ...state.filters, ...action.payload };
    },
    clearFilters: (state) => {
      state.filters = initialState.filters;
    },
    removeExpiredAlerts: (state) => {
      const now = new Date().toISOString();
      state.alerts = state.alerts.filter(alert => 
        !alert.expiresAt || alert.expiresAt > now
      );
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch alerts
      .addCase(fetchAlerts.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(fetchAlerts.fulfilled, (state, action) => {
        state.isLoading = false;
        state.alerts = action.payload;
        state.unreadCount = state.alerts.filter(alert => !alert.isRead).length;
        state.error = null;
      })
      .addCase(fetchAlerts.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      })

      // // Fetch alert rules
      // .addCase(fetchAlertRules.fulfilled, (state, action) => {
      //   state.rules = action.payload;
      // })
      // .addCase(fetchAlertRules.rejected, (state, action) => {
      //   state.error = action.payload as string;
      // })

      // Acknowledge alert
      .addCase(acknowledgeAlert.fulfilled, (state, action) => {
        const alert = state.alerts.find(a => a.id === action.payload.alertId);
        if (alert) {
          alert.isAcknowledged = true;
          alert.acknowledgedBy = action.payload.acknowledgedBy;
          alert.acknowledgedAt = action.payload.acknowledgedAt;
        }
      })
      .addCase(acknowledgeAlert.rejected, (state, action) => {
        state.error = action.payload as string;
      })

      // Mark alert as read
      .addCase(markAlertAsRead.fulfilled, (state, action) => {
        const alert = state.alerts.find(a => a.id === action.payload);
        if (alert && !alert.isRead) {
          alert.isRead = true;
          state.unreadCount = Math.max(0, state.unreadCount - 1);
        }
      })
      .addCase(markAlertAsRead.rejected, (state, action) => {
        state.error = action.payload as string;
      })

      // Mark all alerts as read
      .addCase(markAllAlertsAsRead.fulfilled, (state) => {
        state.alerts.forEach(alert => {
          alert.isRead = true;
        });
        state.unreadCount = 0;
      })
      .addCase(markAllAlertsAsRead.rejected, (state, action) => {
        state.error = action.payload as string;
      })

      // // Create alert rule
      // .addCase(createAlertRule.fulfilled, (state, action) => {
      //   state.rules.unshift(action.payload);
      // })
      // .addCase(createAlertRule.rejected, (state, action) => {
      //   state.error = action.payload as string;
      // })

      // Update alert rule
      // .addCase(updateAlertRule.fulfilled, (state, action) => {
      //   const index = state.rules.findIndex(rule => rule.id === action.payload.id);
      //   if (index !== -1) {
      //     state.rules[index] = action.payload;
      //   }
      // })
      // .addCase(updateAlertRule.rejected, (state, action) => {
      //   state.error = action.payload as string;
      // })

      // // Delete alert rule
      // .addCase(deleteAlertRule.fulfilled, (state, action) => {
      //   state.rules = state.rules.filter(rule => rule.id !== action.payload);
      // })
      // .addCase(deleteAlertRule.rejected, (state, action) => {
      //   state.error = action.payload as string;
      // });
  },
});

export const {
  clearError,
  addNewAlert,
  updateFilters,
  clearFilters,
  removeExpiredAlerts,
} = alertsSlice.actions;

export default alertsSlice.reducer;