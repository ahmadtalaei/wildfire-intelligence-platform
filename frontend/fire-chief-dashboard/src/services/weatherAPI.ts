/**
 * Weather API Service
 * Integrates Windy.com for weather visualization and AirNow.gov for smoke/air quality
 */

const AIRNOW_API_KEY = 'FE7F4E19-79E7-455D-B8B9-2F9D49D80CEB';
const AIRNOW_BASE_URL = 'https://www.airnowapi.org/aq';

export interface AirQualityReading {
  latitude: number;
  longitude: number;
  aqi: number;
  category: string; // 'Good', 'Moderate', 'Unhealthy for Sensitive Groups', 'Unhealthy', 'Very Unhealthy', 'Hazardous'
  parameter: string; // 'PM2.5', 'PM10', 'O3'
  stationName: string;
  reportingArea: string;
  dateObserved: string;
}

export interface SmokeOverlayData {
  stations: AirQualityReading[];
  timestamp: string;
  severityLevel: 'none' | 'light' | 'moderate' | 'heavy' | 'extreme';
}

class WeatherAPIService {
  /**
   * Fetch air quality data from AirNow.gov for California
   * Includes PM2.5, PM10, and O3 readings (smoke indicators)
   */
  async fetchAirQualityData(
    minLat: number = 32.0,
    maxLat: number = 42.0,
    minLon: number = -125.0,
    maxLon: number = -114.0
  ): Promise<SmokeOverlayData> {
    try {
      // AirNow API: Get current observations by bounding box
      const url = `${AIRNOW_BASE_URL}/observation/latLong/current/?` +
        `format=application/json&` +
        `latitude=${(minLat + maxLat) / 2}&` +
        `longitude=${(minLon + maxLon) / 2}&` +
        `distance=300&` + // 300 miles radius to cover all of California
        `API_KEY=${AIRNOW_API_KEY}`;

      console.log('[WeatherAPI] Fetching AirNow data:', url.replace(AIRNOW_API_KEY, 'XXXXX'));

      const response = await fetch(url);

      if (!response.ok) {
        throw new Error(`AirNow API error: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();
      console.log('[WeatherAPI] AirNow response:', data);

      const stations: AirQualityReading[] = data.map((reading: any) => ({
        latitude: reading.Latitude,
        longitude: reading.Longitude,
        aqi: reading.AQI,
        category: reading.Category.Name,
        parameter: reading.ParameterName,
        stationName: reading.ReportingArea,
        reportingArea: reading.StateCode,
        dateObserved: reading.DateObserved
      }));

      // Calculate overall severity based on PM2.5 readings (primary smoke indicator)
      const pm25Readings = stations.filter(s => s.parameter === 'PM2.5');
      const avgAQI = pm25Readings.length > 0
        ? pm25Readings.reduce((sum, s) => sum + s.aqi, 0) / pm25Readings.length
        : 0;

      let severityLevel: 'none' | 'light' | 'moderate' | 'heavy' | 'extreme' = 'none';
      if (avgAQI > 300) severityLevel = 'extreme';
      else if (avgAQI > 200) severityLevel = 'heavy';
      else if (avgAQI > 150) severityLevel = 'moderate';
      else if (avgAQI > 50) severityLevel = 'light';

      return {
        stations,
        timestamp: new Date().toISOString(),
        severityLevel
      };

    } catch (error) {
      console.error('[WeatherAPI] Failed to fetch AirNow data:', error);

      // Return mock data as fallback
      return {
        stations: this.getMockAirQualityData(),
        timestamp: new Date().toISOString(),
        severityLevel: 'moderate'
      };
    }
  }

  /**
   * Get Windy.com embed URL for weather visualization
   * Note: Windy.com provides free embeds with comprehensive weather data
   */
  getWindyEmbedUrl(lat: number = 37.0, lon: number = -119.0, zoom: number = 6): string {
    // Windy.com embed parameters:
    // - lat, lon: Center coordinates
    // - zoom: Map zoom level (6 = state level, 10 = city level)
    // - overlay: wind, temp, clouds, rain, etc.
    // - product: ecmwf (best global), gfs, nam (US)
    return `https://embed.windy.com/embed2.html?` +
      `lat=${lat}&` +
      `lon=${lon}&` +
      `detailLat=${lat}&` +
      `detailLon=${lon}&` +
      `width=650&` +
      `height=450&` +
      `zoom=${zoom}&` +
      `level=surface&` +
      `overlay=wind&` +
      `product=ecmwf&` +
      `menu=&` +
      `message=true&` +
      `marker=&` +
      `calendar=now&` +
      `pressure=&` +
      `type=map&` +
      `location=coordinates&` +
      `detail=&` +
      `metricWind=default&` +
      `metricTemp=default&` +
      `radarRange=-1`;
  }

  /**
   * Mock air quality data for fallback/demo
   */
  private getMockAirQualityData(): AirQualityReading[] {
    return [
      {
        latitude: 37.7749,
        longitude: -122.4194,
        aqi: 155,
        category: 'Unhealthy for Sensitive Groups',
        parameter: 'PM2.5',
        stationName: 'San Francisco',
        reportingArea: 'CA',
        dateObserved: new Date().toISOString()
      },
      {
        latitude: 34.0522,
        longitude: -118.2437,
        aqi: 178,
        category: 'Unhealthy',
        parameter: 'PM2.5',
        stationName: 'Los Angeles',
        reportingArea: 'CA',
        dateObserved: new Date().toISOString()
      },
      {
        latitude: 38.5816,
        longitude: -121.4944,
        aqi: 142,
        category: 'Unhealthy for Sensitive Groups',
        parameter: 'PM2.5',
        stationName: 'Sacramento',
        reportingArea: 'CA',
        dateObserved: new Date().toISOString()
      },
      {
        latitude: 32.7157,
        longitude: -117.1611,
        aqi: 95,
        category: 'Moderate',
        parameter: 'PM2.5',
        stationName: 'San Diego',
        reportingArea: 'CA',
        dateObserved: new Date().toISOString()
      },
      {
        latitude: 39.5296,
        longitude: -121.5014,
        aqi: 215,
        category: 'Very Unhealthy',
        parameter: 'PM2.5',
        stationName: 'Paradise (Butte County)',
        reportingArea: 'CA',
        dateObserved: new Date().toISOString()
      }
    ];
  }

  /**
   * Get AQI color coding for visualization
   */
  getAQIColor(aqi: number): string {
    if (aqi <= 50) return '#00E400'; // Good - Green
    if (aqi <= 100) return '#FFFF00'; // Moderate - Yellow
    if (aqi <= 150) return '#FF7E00'; // Unhealthy for Sensitive Groups - Orange
    if (aqi <= 200) return '#FF0000'; // Unhealthy - Red
    if (aqi <= 300) return '#8F3F97'; // Very Unhealthy - Purple
    return '#7E0023'; // Hazardous - Maroon
  }

  /**
   * Get AQI category name
   */
  getAQICategory(aqi: number): string {
    if (aqi <= 50) return 'Good';
    if (aqi <= 100) return 'Moderate';
    if (aqi <= 150) return 'Unhealthy for Sensitive Groups';
    if (aqi <= 200) return 'Unhealthy';
    if (aqi <= 300) return 'Very Unhealthy';
    return 'Hazardous';
  }
}

export const weatherAPI = new WeatherAPIService();
