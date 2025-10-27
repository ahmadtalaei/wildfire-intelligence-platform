import axios from 'axios';

export interface EmergencyInfrastructure {
  id: string;
  type: 'fire_station' | 'hospital' | 'police' | 'helipad' | 'water_source' | 'communication_tower' | 'evacuation_route';
  name: string;
  latitude: number;
  longitude: number;
  status: 'operational' | 'limited' | 'offline';
  capacity?: number;
  contact?: string;
  updated_at: string;
}

export interface WeatherStation {
  id: string;
  station_id: string;
  name: string;
  latitude: number;
  longitude: number;
  temperature_f: number;
  wind_speed_mph: number;
  humidity_percent: number;
  pressure_inhg?: number;
  visibility_mi?: number;
  last_updated: string;
}

class InfrastructureService {
  private baseURL = process.env.REACT_APP_API_BASE_URL || '';

  async getEmergencyInfrastructure(): Promise<EmergencyInfrastructure[]> {
    try {
      console.log('[INFRASTRUCTURE] Fetching real emergency infrastructure data...');
      const response = await axios.get(`${this.baseURL}/api/infrastructure/emergency`);
      return response.data;
    } catch (error) {
      console.error('[INFRASTRUCTURE] Failed to fetch real data:', error);

      // Fallback to backend query for fire stations, hospitals etc from our database
      try {
        const dbResponse = await axios.get(`${this.baseURL}/api/emergency-services/all`);
        return dbResponse.data.map((service: any) => ({
          id: service.id,
          type: this.mapServiceType(service.type || service.service_type),
          name: service.name || service.facility_name,
          latitude: parseFloat(service.latitude),
          longitude: parseFloat(service.longitude),
          status: service.status || 'operational',
          capacity: service.capacity,
          contact: service.contact_info,
          updated_at: service.updated_at || new Date().toISOString()
        }));
      } catch (dbError) {
        console.error('[INFRASTRUCTURE] Database fallback failed:', dbError);
        return [];
      }
    }
  }

  async getWeatherStations(): Promise<WeatherStation[]> {
    try {
      console.log('[WEATHER] Fetching real RAWS weather station data...');
      const response = await axios.get(`${this.baseURL}/api/weather/raws-stations`);
      return response.data;
    } catch (error) {
      console.error('[WEATHER] Failed to fetch RAWS data:', error);

      // Try NOAA Weather API
      try {
        console.log('[WEATHER] Trying NOAA Weather API...');
        const noaaResponse = await axios.get('https://api.weather.gov/stations?state=CA&limit=50');

        const stationPromises = noaaResponse.data.features.slice(0, 10).map(async (station: any) => {
          try {
            const obsResponse = await axios.get(
              `https://api.weather.gov/stations/${station.properties.stationIdentifier}/observations/latest`
            );
            const props = obsResponse.data.properties;

            return {
              id: station.properties.stationIdentifier,
              station_id: station.properties.stationIdentifier,
              name: station.properties.name,
              latitude: station.geometry.coordinates[1],
              longitude: station.geometry.coordinates[0],
              temperature_f: props.temperature?.value ? Math.round(props.temperature.value * 9/5 + 32) : 0,
              wind_speed_mph: props.windSpeed?.value ? Math.round(props.windSpeed.value * 2.237) : 0,
              humidity_percent: props.relativeHumidity?.value ? Math.round(props.relativeHumidity.value) : 0,
              pressure_inhg: props.barometricPressure?.value ? Math.round(props.barometricPressure.value * 0.0002953) : undefined,
              visibility_mi: props.visibility?.value ? Math.round(props.visibility.value * 0.0006214) : undefined,
              last_updated: props.timestamp || new Date().toISOString()
            };
          } catch {
            return null;
          }
        });

        const stations = await Promise.all(stationPromises);
        return stations.filter(station => station !== null) as WeatherStation[];
      } catch (noaaError) {
        console.error('[WEATHER] NOAA API failed:', noaaError);

        // Final fallback: try our cached weather data
        try {
          const cacheResponse = await axios.get(`${this.baseURL}/api/weather/cached`);
          return cacheResponse.data.map((station: any) => ({
            id: station.id,
            station_id: station.station_id || `WS${station.id}`,
            name: station.name || `Weather Station ${station.id}`,
            latitude: parseFloat(station.latitude),
            longitude: parseFloat(station.longitude),
            temperature_f: Math.round(station.temperature_f || 0),
            wind_speed_mph: Math.round(station.wind_speed_mph || 0),
            humidity_percent: Math.round(station.humidity_percent || 0),
            pressure_inhg: station.pressure_inhg,
            visibility_mi: station.visibility_mi,
            last_updated: station.last_updated || new Date().toISOString()
          }));
        } catch (cacheError) {
          console.error('[WEATHER] All weather sources failed:', cacheError);
          return [];
        }
      }
    }
  }

  private mapServiceType(type: string): EmergencyInfrastructure['type'] {
    const typeMap: { [key: string]: EmergencyInfrastructure['type'] } = {
      'fire_department': 'fire_station',
      'fire_station': 'fire_station',
      'hospital': 'hospital',
      'medical_center': 'hospital',
      'police_station': 'police',
      'police': 'police',
      'heliport': 'helipad',
      'helipad': 'helipad',
      'helicopter_landing': 'helipad',
      'water_source': 'water_source',
      'reservoir': 'water_source',
      'communication': 'communication_tower',
      'tower': 'communication_tower',
      'evacuation': 'evacuation_route',
      'route': 'evacuation_route'
    };

    return typeMap[type.toLowerCase()] || 'fire_station';
  }

  async getFireIncidents(): Promise<any[]> {
    try {
      console.log('[FIRE] Fetching real fire incident data...');
      const response = await axios.get(`${this.baseURL}/api/fire-incidents/active`);
      return response.data;
    } catch (error) {
      console.error('[FIRE] Failed to fetch fire incidents:', error);
      return [];
    }
  }
}

export const infrastructureService = new InfrastructureService();