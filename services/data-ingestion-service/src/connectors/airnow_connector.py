"""
AirNow API Connector
Real-time air quality and fire/smoke data from U.S. EPA's AirNow program
https://www.airnow.gov/ and https://fire.airnow.gov/

API Documentation: https://docs.airnowapi.org/
"""

import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import structlog
import time

# Import centralized conversion utilities
from .timezone_converter import utc_to_pacific, utcnow_pacific
from .metrics import INGESTION_LATENCY, VALIDATION_TOTAL, VALIDATION_PASSED, RECORDS_PROCESSED

logger = structlog.get_logger()

# Import centralized geographic bounds with configuration fallback
try:
    from ..geo_config.geographic_bounds import CALIFORNIA_BOUNDS
except ImportError:
    try:
        from geo_config.geographic_bounds import CALIFORNIA_BOUNDS
    except ImportError:
        # Fallback bounds - use hardcoded USGS values if config not available
        CALIFORNIA_BOUNDS = {
            'lat_min': 32.534156,   # Southern border (Imperial County)
            'lat_max': 42.009518,   # Northern border (Modoc County)
            'lon_min': -124.482003, # Western border (Del Norte County)
            'lon_max': -114.131211  # Eastern border (Imperial County)
        }


class AirNowConnector:
    """Connector for AirNow air quality and fire/smoke data"""

    def __init__(self, api_key: str, kafka_producer=None):
        """
        Initialize AirNow connector

        Args:
            api_key: AirNow API key from https://www.airnow.gov/airnow-api/
            kafka_producer: Kafka producer for streaming data
        """
        self.api_key = api_key
        self.base_url = "https://www.airnowapi.org/aq"
        self.base_url_root = "https://www.airnowapi.org"  # Root URL for different endpoints
        self.kafka_producer = kafka_producer
        self.active_streams = {}
        self.california_bounds = CALIFORNIA_BOUNDS
        self.monitoring_locations_cache = []  # Cache for real monitoring station locations

    async def health_check(self) -> bool:
        """Check AirNow API connectivity"""
        if not self.api_key:
            logger.warning("AirNow API key not configured")
            return False

        try:
            # Test with a simple observation request for Los Angeles
            params = {
                'format': 'application/json',
                'zipCode': '90001',  # Los Angeles
                'distance': '25',
                'API_KEY': self.api_key
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/observation/zipCode/current/",
                                     params=params,
                                     timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info("AirNow API health check passed",
                                  status=response.status,
                                  sample_data_points=len(data) if isinstance(data, list) else 0)
                        return True
                    else:
                        text = await response.text()
                        logger.warning("AirNow API health check failed",
                                     status=response.status,
                                     response=text[:200])
                        return False
        except Exception as e:
            logger.error("AirNow API health check error", error=str(e))
            return False

    async def get_current_observations_by_location(self,
                                                   latitude: float,
                                                   longitude: float,
                                                   distance: int = 25) -> List[Dict[str, Any]]:
        """
        Get current air quality observations near a location

        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            distance: Search radius in miles (default 25)

        Returns:
            List of air quality observations
        """
        try:
            params = {
                'format': 'application/json',
                'latitude': latitude,
                'longitude': longitude,
                'distance': distance,
                'API_KEY': self.api_key
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/observation/latLong/current/",
                                     params=params,
                                     timeout=30) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info("Retrieved AirNow observations by location",
                                  latitude=latitude,
                                  longitude=longitude,
                                  observations=len(data) if isinstance(data, list) else 0)
                        return data if isinstance(data, list) else []
                    else:
                        text = await response.text()
                        logger.warning("Failed to retrieve AirNow observations",
                                     status=response.status,
                                     response=text[:200])
                        return []
        except Exception as e:
            logger.error("Error retrieving AirNow observations", error=str(e))
            return []

    async def get_current_observations_by_zip(self,
                                             zip_code: str,
                                             distance: int = 25) -> List[Dict[str, Any]]:
        """
        Get current air quality observations by ZIP code

        Args:
            zip_code: US ZIP code
            distance: Search radius in miles (default 25)

        Returns:
            List of air quality observations
        """
        try:
            params = {
                'format': 'application/json',
                'zipCode': zip_code,
                'distance': distance,
                'API_KEY': self.api_key
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/observation/zipCode/current/",
                                     params=params,
                                     timeout=30) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info("Retrieved AirNow observations by ZIP",
                                  zip_code=zip_code,
                                  observations=len(data) if isinstance(data, list) else 0)
                        return data if isinstance(data, list) else []
                    else:
                        text = await response.text()
                        logger.warning("Failed to retrieve AirNow observations",
                                     status=response.status,
                                     response=text[:200])
                        return []
        except Exception as e:
            logger.error("Error retrieving AirNow observations", error=str(e))
            return []

    async def get_forecast_by_location(self,
                                      latitude: float,
                                      longitude: float,
                                      date: Optional[str] = None,
                                      distance: int = 25) -> List[Dict[str, Any]]:
        """
        Get air quality forecast near a location

        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            date: Forecast date in YYYY-MM-DD format (default today)
            distance: Search radius in miles (default 25)

        Returns:
            List of air quality forecasts
        """
        try:
            if not date:
                date = datetime.now().strftime('%Y-%m-%d')

            params = {
                'format': 'application/json',
                'latitude': latitude,
                'longitude': longitude,
                'date': date,
                'distance': distance,
                'API_KEY': self.api_key
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/forecast/latLong/",
                                     params=params,
                                     timeout=30) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info("Retrieved AirNow forecast by location",
                                  latitude=latitude,
                                  longitude=longitude,
                                  date=date,
                                  forecasts=len(data) if isinstance(data, list) else 0)
                        return data if isinstance(data, list) else []
                    else:
                        text = await response.text()
                        logger.warning("Failed to retrieve AirNow forecast",
                                     status=response.status,
                                     response=text[:200])
                        return []
        except Exception as e:
            logger.error("Error retrieving AirNow forecast", error=str(e))
            return []

    async def get_observations_by_bounding_box(self,
                                              bbox_minx: float,
                                              bbox_miny: float,
                                              bbox_maxx: float,
                                              bbox_maxy: float) -> List[Dict[str, Any]]:
        """
        Get air quality observations within a bounding box
        Uses the AirNow Data by Box endpoint to get all monitoring stations in the area

        Args:
            bbox_minx: Minimum longitude (western boundary)
            bbox_miny: Minimum latitude (southern boundary)
            bbox_maxx: Maximum longitude (eastern boundary)
            bbox_maxy: Maximum latitude (northern boundary)

        Returns:
            List of air quality observations from all stations in bounding box
        """
        try:
            params = {
                'format': 'application/json',
                'bbox': f"{bbox_minx},{bbox_miny},{bbox_maxx},{bbox_maxy}",
                'API_KEY': self.api_key
            }

            async with aiohttp.ClientSession() as session:
                # Use the bbox endpoint to get all stations
                async with session.get(f"{self.base_url}/data/",
                                     params=params,
                                     timeout=30) as response:
                    if response.status == 200:
                        data = await response.json()

                        # Update cache with unique monitoring locations
                        if isinstance(data, list) and data:
                            for obs in data:
                                lat, lon = obs.get('Latitude'), obs.get('Longitude')
                                site_name = obs.get('SiteName')
                                if lat and lon and site_name:
                                    location_key = f"{lat}_{lon}_{site_name}"
                                    if not any(loc.get('key') == location_key for loc in self.monitoring_locations_cache):
                                        self.monitoring_locations_cache.append({
                                            'key': location_key,
                                            'name': site_name,
                                            'lat': lat,
                                            'lon': lon,
                                            'agency': obs.get('AgencyName')
                                        })

                        logger.info("Retrieved AirNow observations by bounding box",
                                  observations=len(data) if isinstance(data, list) else 0,
                                  monitoring_stations=len(self.monitoring_locations_cache))
                        return data if isinstance(data, list) else []
                    else:
                        text = await response.text()
                        logger.warning("Failed to retrieve AirNow bounding box observations",
                                     status=response.status,
                                     response=text[:200])
                        return []
        except Exception as e:
            logger.error("Error retrieving AirNow bounding box observations", error=str(e))
            return []

    async def get_observations_by_state(self, state_code: str = "CA") -> List[Dict[str, Any]]:
        """
        Get air quality observations for an entire state
        Uses AirNow Files/Observations endpoint which returns all monitoring stations

        Args:
            state_code: Two-letter state code (default: CA for California)

        Returns:
            List of all air quality observations from monitoring stations in the state
        """
        try:
            # Use the observations/state endpoint
            params = {
                'format': 'application/json',
                'stateCode': state_code,
                'API_KEY': self.api_key
            }

            async with aiohttp.ClientSession() as session:
                # Build URL correctly - params will be added by aiohttp
                url = f"{self.base_url}/observation/state/current/"
                async with session.get(url,
                                     params=params,
                                     timeout=30) as response:
                    if response.status == 200:
                        data = await response.json()

                        # Update cache with unique monitoring locations
                        if isinstance(data, list) and data:
                            for obs in data:
                                lat, lon = obs.get('Latitude'), obs.get('Longitude')
                                site_name = obs.get('SiteName')
                                if lat and lon and site_name:
                                    location_key = f"{lat}_{lon}_{site_name}"
                                    if not any(loc.get('key') == location_key for loc in self.monitoring_locations_cache):
                                        self.monitoring_locations_cache.append({
                                            'key': location_key,
                                            'name': site_name,
                                            'lat': lat,
                                            'lon': lon,
                                            'agency': obs.get('AgencyName'),
                                            'reporting_area': obs.get('ReportingArea')
                                        })

                        logger.info("Retrieved AirNow observations by state",
                                  state=state_code,
                                  observations=len(data) if isinstance(data, list) else 0,
                                  unique_stations=len(self.monitoring_locations_cache))
                        return data if isinstance(data, list) else []
                    else:
                        text = await response.text()
                        logger.warning("Failed to retrieve AirNow state observations",
                                     status=response.status,
                                     state=state_code,
                                     response=text[:200])
                        return []
        except Exception as e:
            logger.error("Error retrieving AirNow state observations",
                       state=state_code,
                       error=str(e))
            return []

    async def get_california_grid_observations(self) -> List[Dict[str, Any]]:
        """
        Get air quality observations across California from real monitoring stations
        Uses major California ZIP codes to discover and retrieve data from actual AirNow stations

        Returns:
            List of air quality observations from real AirNow monitoring stations
        """
        observations = []

        # Major California ZIP codes covering different regions
        # These will discover real monitoring stations in each area
        california_zip_codes = [
            # Northern California
            '96001',  # Redding
            '96080',  # Paradise
            '95901',  # Marysville
            '95688',  # Vacaville

            # Sacramento Valley
            '95814',  # Sacramento
            '95630',  # Folsom
            '95667',  # Placerville

            # Bay Area
            '94102',  # San Francisco
            '94501',  # Alameda
            '94040',  # Mountain View
            '95110',  # San Jose
            '94952',  # Petaluma
            '94503',  # Rio Vista
            '94920',  # Belvedere Tiburon

            # Central Coast
            '93901',  # Salinas
            '93940',  # Monterey
            '93401',  # San Luis Obispo
            '93101',  # Santa Barbara

            # Central Valley
            '95350',  # Modesto
            '95301',  # Atwater
            '93611',  # Clovis/Fresno
            '93274',  # Visalia
            '93301',  # Bakersfield

            # Southern California
            '90001',  # Los Angeles
            '90201',  # Bell
            '91101',  # Pasadena
            '92101',  # San Diego
            '92503',  # Riverside
            '92801',  # Anaheim
            '91710',  # Chino
            '92373',  # Redlands
        ]

        # Query each ZIP code to discover real monitoring stations
        tasks = []
        for zip_code in california_zip_codes:
            task = self.get_current_observations_by_zip(zip_code, distance=25)
            tasks.append(task)

        # Execute all requests concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, result in enumerate(results):
            if isinstance(result, list) and result:
                # Add ZIP code context
                for obs in result:
                    obs['query_zip'] = california_zip_codes[i]

                    # Update monitoring locations cache
                    lat, lon = obs.get('Latitude'), obs.get('Longitude')
                    site_name = obs.get('SiteName')
                    if lat and lon and site_name:
                        location_key = f"{lat}_{lon}_{site_name}"
                        if not any(loc.get('key') == location_key for loc in self.monitoring_locations_cache):
                            self.monitoring_locations_cache.append({
                                'key': location_key,
                                'name': site_name,
                                'lat': lat,
                                'lon': lon,
                                'agency': obs.get('AgencyName'),
                                'reporting_area': obs.get('ReportingArea')
                            })

                observations.extend(result)
            elif isinstance(result, Exception):
                logger.debug("Failed to get observations for ZIP code",
                           zip_code=california_zip_codes[i],
                           error=str(result))

        logger.info("Retrieved California monitoring network observations",
                  total_observations=len(observations),
                  unique_stations=len(self.monitoring_locations_cache),
                  zip_codes_queried=len(california_zip_codes))

        return observations

    async def start_streaming(self, source_id: str = "airnow_california",
                            interval_seconds: int = 300) -> str:
        """
        Start streaming AirNow data to Kafka

        Args:
            source_id: Identifier for this data stream
            interval_seconds: Polling interval (default 300 = 5 minutes, API rate limit)

        Returns:
            stream_id: Unique identifier for this stream
        """
        stream_id = f"airnow_stream_{source_id}_{datetime.now().timestamp()}"

        logger.info("Starting AirNow data stream",
                   stream_id=stream_id,
                   source_id=source_id,
                   interval_seconds=interval_seconds)

        self.active_streams[stream_id] = {
            'stream_id': stream_id,
            'source_id': source_id,
            'status': 'active',
            'start_time': datetime.now(),
            'records_streamed': 0,
            'last_update': None
        }

        # Start streaming loop
        asyncio.create_task(self._stream_loop(stream_id, interval_seconds))

        return stream_id

    async def _stream_loop(self, stream_id: str, interval_seconds: int):
        """Background streaming loop"""
        stream_config = self.active_streams.get(stream_id)
        if not stream_config:
            return

        logger.info("AirNow streaming loop started", stream_id=stream_id)

        while stream_config['status'] == 'active':
            try:
                # Start timing for latency measurement
                start_time = time.time()

                # Fetch California observations
                observations = await self.get_california_grid_observations()

                # Record ingestion latency
                latency = time.time() - start_time
                INGESTION_LATENCY.labels(source='airnow', job='data-ingestion-service').observe(latency)

                if observations and self.kafka_producer:
                    # Transform to standard format and track validation
                    transformed_data = []
                    for obs in observations:
                        VALIDATION_TOTAL.labels(source='airnow', job='data-ingestion-service').inc()

                        record = self._transform_observation(obs)
                        if record:
                            VALIDATION_PASSED.labels(source='airnow', job='data-ingestion-service').inc()
                            transformed_data.append(record)

                    # Send to Kafka
                    if transformed_data:
                        # Record processed records
                        RECORDS_PROCESSED.labels(source='airnow', job='data-ingestion-service').inc(len(transformed_data))

                        await self.kafka_producer.send_batch_data(
                            data=transformed_data,
                            source_type="sensor",
                            source_id="airnow"
                        )

                        stream_config['records_streamed'] += len(transformed_data)
                        stream_config['last_update'] = datetime.now()

                        logger.info("AirNow data sent to Kafka",
                                  stream_id=stream_id,
                                  records=len(transformed_data),
                                  latency_seconds=latency)

                # Wait for next poll
                await asyncio.sleep(interval_seconds)

            except Exception as e:
                logger.error("Error in AirNow streaming loop",
                           stream_id=stream_id,
                           error=str(e))
                await asyncio.sleep(60)  # Wait 1 minute before retry

    def _transform_observation(self, obs: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Transform AirNow observation to standardized sensor format"""
        try:
            # Map AirNow parameter to sensor type
            parameter_map = {
                'PM2.5': 'pm25',
                'PM10': 'pm10',
                'O3': 'ozone',
                'CO': 'carbon_monoxide',
                'NO2': 'nitrogen_dioxide',
                'SO2': 'sulfur_dioxide'
            }

            sensor_type = parameter_map.get(obs.get('ParameterName', ''), 'air_quality')

            return {
                'sensor_id': f"airnow_{obs.get('SiteName', 'unknown').replace(' ', '_')}_{obs.get('ParameterName', 'unknown')}",
                'sensor_type': sensor_type,
                'latitude': obs.get('Latitude'),
                'longitude': obs.get('Longitude'),
                'timestamp': utc_to_pacific(obs.get('DateObserved')) if obs.get('DateObserved') else utcnow_pacific(),
                'value': obs.get('AQI'),
                'parameter': obs.get('ParameterName'),
                'unit': obs.get('Unit', 'AQI'),
                'category': obs.get('Category', {}).get('Name') if isinstance(obs.get('Category'), dict) else None,
                'site_name': obs.get('SiteName'),
                'agency': obs.get('AgencyName', 'AirNow'),
                'region': obs.get('region'),
                'source': 'AirNow',
                'source_id': 'airnow',  # For TableRouter routing to airnow_observations table
                'data_quality': 0.95  # AirNow data is highly reliable
            }
        except Exception as e:
            logger.error("Error transforming AirNow observation", error=str(e))
            return None

    async def stop_streaming(self, stream_id: str) -> bool:
        """Stop AirNow data streaming"""
        if stream_id in self.active_streams:
            self.active_streams[stream_id]['status'] = 'stopped'
            logger.info("AirNow data stream stopped", stream_id=stream_id)
            return True
        return False

    async def get_active_streams(self) -> List[Dict[str, Any]]:
        """Get list of active AirNow data streams"""
        return [
            {
                'stream_id': stream_id,
                'source_id': config['source_id'],
                'status': config['status'],
                'start_time': config['start_time'].isoformat(),
                'records_streamed': config['records_streamed'],
                'last_update': config['last_update'].isoformat() if config['last_update'] else None
            }
            for stream_id, config in self.active_streams.items()
        ]