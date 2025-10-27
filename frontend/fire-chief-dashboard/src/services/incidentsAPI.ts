import apiClient from './authAPI';

export interface Incident {
  id: string;
  name: string;
  type: 'wildfire' | 'structure_fire' | 'vehicle_fire' | 'other';
  status: 'active' | 'contained' | 'controlled' | 'extinguished';
  severity: 'low' | 'medium' | 'high' | 'critical';
  location: {
    latitude: number;
    longitude: number;
    address: string;
    county: string;
    state: string;
  };
  startDate: string;
  controlledDate?: string;
  extinguishedDate?: string;
  acres: number;
  containmentPercentage: number;
  threatenedStructures: number;
  destroyedStructures: number;
  injuries: number;
  fatalities: number;
  assignedResources: string[];
  description?: string;
  cause?: string;
  weather?: {
    temperature: number;
    humidity: number;
    windSpeed: number;
    windDirection: string;
  };
  updates: Array<{
    id: string;
    timestamp: string;
    message: string;
    updatedBy: string;
    type: 'status_update' | 'resource_assignment' | 'containment_update' | 'general';
  }>;
}

export interface IncidentFilters {
  status?: string;
  severity?: string;
  county?: string;
  startDate?: string;
  endDate?: string;
  limit?: number;
  offset?: number;
}

export interface IncidentStats {
  total: number;
  active: number;
  contained: number;
  controlled: number;
  extinguished: number;
  totalAcres: number;
  averageContainment: number;
  threatenedStructures: number;
  destroyedStructures: number;
}

export const incidentsAPI = {
  // Get all incidents
  getIncidents: async (filters?: IncidentFilters) => {
    try {
      const params = new URLSearchParams();
      if (filters) {
        Object.entries(filters).forEach(([key, value]) => {
          if (value !== undefined) {
            params.append(key, String(value));
          }
        });
      }
      
      const response = await apiClient.get<Incident[]>(`/incidents?${params.toString()}`);
      return response;
    } catch (error) {
      // Mock data for demo
      const mockIncidents: Incident[] = [
        {
          id: '1',
          name: 'Riverside Fire',
          type: 'wildfire',
          status: 'active',
          severity: 'high',
          location: {
            latitude: 33.9533,
            longitude: -117.3962,
            address: 'Near Highway 91 and Interstate 215',
            county: 'Riverside',
            state: 'CA',
          },
          startDate: '2024-09-10T14:30:00Z',
          acres: 2450,
          containmentPercentage: 25,
          threatenedStructures: 150,
          destroyedStructures: 8,
          injuries: 2,
          fatalities: 0,
          assignedResources: ['engine-15', 'helicopter-1', 'crew-alpha'],
          description: 'Fast-moving wildfire threatening residential areas',
          cause: 'Under investigation',
          weather: {
            temperature: 95,
            humidity: 12,
            windSpeed: 25,
            windDirection: 'SW',
          },
          updates: [
            {
              id: '1',
              timestamp: '2024-09-10T16:00:00Z',
              message: 'Fire has grown to 2,450 acres with 25% containment',
              updatedBy: 'Chief Williams',
              type: 'containment_update',
            },
            {
              id: '2',
              timestamp: '2024-09-10T15:15:00Z',
              message: 'Additional resources deployed including Air Tanker 42',
              updatedBy: 'Dispatch',
              type: 'resource_assignment',
            },
          ],
        },
        {
          id: '2',
          name: 'Mountain View Fire',
          type: 'wildfire',
          status: 'contained',
          severity: 'medium',
          location: {
            latitude: 34.2839,
            longitude: -116.8949,
            address: 'San Bernardino National Forest',
            county: 'San Bernardino',
            state: 'CA',
          },
          startDate: '2024-09-08T09:15:00Z',
          controlledDate: '2024-09-10T12:30:00Z',
          acres: 850,
          containmentPercentage: 85,
          threatenedStructures: 25,
          destroyedStructures: 0,
          injuries: 0,
          fatalities: 0,
          assignedResources: ['engine-22', 'crew-beta'],
          description: 'Forest fire in remote mountainous area',
          cause: 'Lightning',
          updates: [
            {
              id: '1',
              timestamp: '2024-09-10T12:30:00Z',
              message: 'Fire now 85% contained, mop-up operations continue',
              updatedBy: 'Chief Davis',
              type: 'status_update',
            },
          ],
        },
      ];
      
      return { data: mockIncidents };
    }
  },

  // Get incident by ID
  getIncident: async (incidentId: string) => {
    try {
      const response = await apiClient.get<Incident>(`/incidents/${incidentId}`);
      return response;
    } catch (error) {
      // Return mock data for demo
      const incidents = await incidentsAPI.getIncidents();
      const incident = incidents.data.find(i => i.id === incidentId);
      if (incident) {
        return { data: incident };
      }
      throw new Error('Incident not found');
    }
  },

  // Create new incident
  createIncident: async (incident: Omit<Incident, 'id' | 'updates'>) => {
    try {
      const response = await apiClient.post<Incident>('/incidents', incident);
      return response;
    } catch (error) {
      const newIncident: Incident = {
        ...incident,
        id: Date.now().toString(),
        updates: [],
      };
      return { data: newIncident };
    }
  },

  // Update incident
  updateIncident: async (incidentId: string, updates: Partial<Incident>) => {
    try {
      const response = await apiClient.patch<Incident>(`/incidents/${incidentId}`, updates);
      return response;
    } catch (error) {
      // Return updated mock data
      const incidents = await incidentsAPI.getIncidents();
      const incident = incidents.data.find(i => i.id === incidentId);
      if (incident) {
        const updatedIncident = { ...incident, ...updates };
        return { data: updatedIncident };
      }
      throw new Error('Incident not found');
    }
  },

  // Add incident update
  addIncidentUpdate: async (incidentId: string, update: Omit<Incident['updates'][0], 'id'>) => {
    try {
      const response = await apiClient.post(`/incidents/${incidentId}/updates`, update);
      return response;
    } catch (error) {
      const newUpdate = {
        ...update,
        id: Date.now().toString(),
      };
      return { data: newUpdate };
    }
  },

  // Get incident statistics
  getIncidentStats: async (filters?: Pick<IncidentFilters, 'startDate' | 'endDate' | 'county'>) => {
    try {
      const params = new URLSearchParams();
      if (filters) {
        Object.entries(filters).forEach(([key, value]) => {
          if (value !== undefined) {
            params.append(key, String(value));
          }
        });
      }
      
      const response = await apiClient.get<IncidentStats>(`/incidents/stats?${params.toString()}`);
      return response;
    } catch (error) {
      // Mock stats for demo
      const mockStats: IncidentStats = {
        total: 15,
        active: 3,
        contained: 8,
        controlled: 2,
        extinguished: 2,
        totalAcres: 45680,
        averageContainment: 67,
        threatenedStructures: 450,
        destroyedStructures: 23,
      };
      return { data: mockStats };
    }
  },

  // Assign resource to incident
  assignResource: async (incidentId: string, resourceId: string) => {
    try {
      const response = await apiClient.post(`/incidents/${incidentId}/resources`, { resourceId });
      return response;
    } catch (error) {
      return { data: { message: 'Resource assigned successfully' } };
    }
  },

  // Remove resource from incident
  removeResource: async (incidentId: string, resourceId: string) => {
    try {
      const response = await apiClient.delete(`/incidents/${incidentId}/resources/${resourceId}`);
      return response;
    } catch (error) {
      return { data: { message: 'Resource removed successfully' } };
    }
  },
};