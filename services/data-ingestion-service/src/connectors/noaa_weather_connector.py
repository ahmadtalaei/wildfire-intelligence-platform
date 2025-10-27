"""
NOAA Weather Station Data Connector
Real-time weather data from NOAA/NWS API and MADIS system

✅ How to run:
cd C:\\dev\\wildfire\\services\\data-ingestion-service
python -m src.connectors.noaa_weather_connector

### 🔧 **Purpose**

* Acts as a **connector service** for ingesting weather and alert data from NOAA/NWS into your wildfire/data-ingestion system.
* Standardizes different NOAA endpoints (stations, observations, forecasts, alerts) into a consistent format.
* Supports **batch fetching** and **streaming (real-time polling)**.

---

### 📡 **Key Features**

1. **Initialization**

   * Requires a `NOAA_USER_AGENT` environment variable (per NOAA API rules).
   * Defines multiple built-in NOAA data sources:

     * Current station observations (`/stations/{id}/observations/latest`)
     * Historical station observations (`/stations/{id}/observations`)
     * Forecasts on NOAA gridpoints (`/gridpoints/{office}/{x},{y}/forecast`)
     * Active weather alerts (`/alerts/active`)

2. **Health Check**

   * Verifies API availability (`/` and `/stations` endpoints).

3. **Station Management**

   * Fetches metadata for NOAA stations in California (station ID, name, lat/lon, elevation, county, etc.).
   * Caches station info for later use.

4. **Batch Data Fetching**

   * Handles requests for:

     * **Current station observations** → processes temperature, humidity, wind, visibility, METAR, etc.
     * **Historical observations** (placeholder).
     * **Forecasts** (placeholder).
     * **Active weather alerts** → processes event type, severity, urgency, affected area, start/end times, etc.

5. **Streaming**

   * Can continuously poll NOAA data (default every hour) and stream results into a message broker (Kafka is referenced, but not yet implemented).
   * Tracks stream status, number of records processed, last update, etc.

6. **Data Quality & Parsing**

   * Extracts clean numeric values from NOAA’s JSON measurement objects.
   * Converts cloud layer codes (`FEW`, `SCT`, `BKN`, `OVC`, etc.) into percentage cloud coverage.
   * Assigns a quality score based on missing/invalid readings.


### ⚠️ **Limitations / TODOs**
* Historical observations and gridpoint forecasts are placeholders (not yet implemented).
* Kafka streaming integration is referenced but not wired up.

Documentation: https://www.weather.gov/documentation/services-web-api
MADIS Info: https://madis-data.ncep.noaa.gov/
"""

import asyncio
import aiohttp
import json
import os
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional, Union
import structlog
import time
from ..models.ingestion import DataSource, StreamingConfig, BatchConfig

# Import centralized conversion utilities
from .timezone_converter import utc_to_pacific, utcnow_pacific
from .unit_converter import convert_temperature, convert_pressure
from .metrics import INGESTION_LATENCY, VALIDATION_TOTAL, VALIDATION_PASSED, RECORDS_PROCESSED

# Import vectorized validator
from ..utils.data_validator import VectorizedDataValidator

logger = structlog.get_logger()


class NOAAWeatherConnector:
    """NOAA weather station data connector using api.weather.gov"""
    
    def __init__(self, user_agent: Optional[str] = None, kafka_producer=None, redis_client=None):
        """
        Initialize NOAA weather connector

        Args:
            user_agent: User agent string for API requests (required by api.weather.gov)
            kafka_producer: Kafka producer instance for streaming data
            redis_client: Redis client for caching gridpoints
        """
        self.user_agent = user_agent or os.getenv("NOAA_USER_AGENT")
        if not self.user_agent:
            raise ValueError("NOAA_USER_AGENT environment variable is required for api.weather.gov access")
        self.base_url = "https://api.weather.gov"
        self.kafka_producer = kafka_producer
        self.redis_client = redis_client
        self.active_streams: Dict[str, Dict] = {}
        self.data_sources = []
        self.station_cache = {}  # Cache for station metadata
        self.gridpoint_cache_key = "noaa:gridpoints:california"
        self.gridpoint_cache_ttl = 86400  # 24 hours
        self._initialize_sources()
    
    def _initialize_sources(self):
        """Initialize NOAA weather data sources"""
        self.data_sources = [
            DataSource(
                id="noaa_stations_current",
                name="NOAA Weather Stations - Current Observations",
                source_type="weather",
                description="Current weather observations from NOAA weather stations",
                provider="NOAA/NWS",
                formats=["json", "xml", "csv"],
                update_frequency="Hourly",
                spatial_resolution="Point measurements",
                temporal_resolution="Hourly",
                is_active=True,
                api_endpoint=f"{self.base_url}/stations/{{station_id}}/observations/latest",
                authentication_required=False
            ),
            DataSource(
                id="noaa_stations_historical",
                name="NOAA Weather Stations - Historical Observations",
                source_type="weather",
                description="Historical weather observations from NOAA weather stations",
                provider="NOAA/NWS",
                formats=["json", "xml", "csv"],
                update_frequency="Daily archive updates",
                spatial_resolution="Point measurements",
                temporal_resolution="Hourly to daily",
                is_active=False,  # Disabled - historical data should use batch API only, not streaming
                api_endpoint=f"{self.base_url}/stations/{{station_id}}/observations",
                authentication_required=False
            ),
            DataSource(
                id="noaa_gridpoints_forecast",
                name="NOAA Grid Forecast Data",
                source_type="weather",
                description="Gridded forecast data from NOAA/NWS",
                provider="NOAA/NWS",
                formats=["json", "xml"],
                update_frequency="6 times daily",
                spatial_resolution="2.5km grid",
                temporal_resolution="Hourly forecasts",
                is_active=True,
                api_endpoint=f"{self.base_url}/gridpoints/{{office}}/{{grid_x}},{{grid_y}}/forecast",
                authentication_required=False
            ),
            DataSource(
                id="noaa_alerts_active",
                name="NOAA Weather Alerts",
                source_type="weather",
                description="Active weather alerts and warnings",
                provider="NOAA/NWS",
                formats=["json", "xml", "atom", "cap"],
                update_frequency="Real-time (as issued)",
                spatial_resolution="County/zone level",
                temporal_resolution="Event-driven",
                is_active=True,
                api_endpoint=f"{self.base_url}/alerts/active",
                authentication_required=False
            )
        ]
    
    async def health_check(self) -> bool:
        """Check NOAA API connectivity"""
        try:
            headers = {'User-Agent': self.user_agent}
            
            async with aiohttp.ClientSession() as session:
                # Test basic API connectivity
                async with session.get(f"{self.base_url}/", headers=headers) as response:
                    if response.status != 200:
                        logger.warning("NOAA API health check failed", status=response.status)
                        return False
                    
                    # Test stations endpoint
                    async with session.get(f"{self.base_url}/stations", 
                                         headers=headers, 
                                         params={'limit': 1}) as stations_response:
                        healthy = stations_response.status == 200
                        
                        if healthy:
                            logger.info("NOAA API health check passed")
                        else:
                            logger.warning("NOAA stations API failed", 
                                         status=stations_response.status)
                        
                        return healthy
                        
        except Exception as e:
            logger.error("NOAA API health check error", error=str(e))
            return False
    
    async def get_sources(self) -> List[DataSource]:
        """Get available NOAA weather data sources"""
        return self.data_sources

    async def add_source(self, source: DataSource) -> DataSource:
        """Add a new NOAA weather data source"""
        try:
            # Validate that this is a weather source
            if source.source_type not in ["weather", "noaa"]:
                raise ValueError(f"Invalid source type for NOAA weather connector: {source.source_type}")

            # Check if source already exists
            existing_source = next((s for s in self.data_sources if s.id == source.id), None)
            if existing_source:
                logger.warning("NOAA weather source already exists", source_id=source.id)
                return existing_source

            # Set connector-specific properties
            source.is_active = True
            if source.api_endpoint is None:
                source.api_endpoint = f"{self.base_url}/stations"
            source.authentication_required = False

            # Add to our data sources list
            self.data_sources.append(source)

            logger.info("NOAA weather data source added successfully",
                       source_id=source.id,
                       source_name=source.name)

            return source

        except Exception as e:
            logger.error("Failed to add NOAA weather data source",
                        source_id=source.id if source else "unknown",
                        error=str(e))
            raise
    
    async def get_california_stations(self, limit: int = 500) -> List[Dict[str, Any]]:
        """Get list of NOAA weather stations in California"""
        try:
            headers = {'User-Agent': self.user_agent}
            
            # California bounding box (The NOAA weather API supports state/region filters rather than explicit coordinate bounding boxes)
            params = {
                'limit': limit,
                'state': 'CA'  # Filter for California stations
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/stations",
                                     headers=headers,
                                     params=params) as response:

                    if response.status != 200:
                        # Log the exact URL and response for debugging
                        actual_url = str(response.url)
                        logger.error("NOAA stations API request failed",
                                   url=actual_url,
                                   status=response.status,
                                   headers=dict(response.headers))
                        try:
                            error_text = await response.text()
                            logger.error("NOAA API error response", error_body=error_text[:500])
                        except:
                            pass
                        raise RuntimeError(f"NOAA stations API error: {response.status}")
                    
                    data = await response.json()
                    stations = data.get('features', [])
                    
                    # Process station data
                    processed_stations = []
                    for station in stations:
                        props = station.get('properties', {})
                        geom = station.get('geometry', {})
                        coords = geom.get('coordinates', [0, 0])
                        
                        processed_station = {
                            'station_id': props.get('stationIdentifier', ''),
                            'name': props.get('name', 'Unknown'),
                            'latitude': coords[1] if len(coords) > 1 else 0.0,
                            'longitude': coords[0] if len(coords) > 0 else 0.0,
                            'elevation_m': props.get('elevation', {}).get('value', 0),
                            'county': props.get('county', ''),
                            'state': props.get('state', 'CA'),
                            'time_zone': props.get('timeZone', 'America/Los_Angeles'),
                            'forecast_office': props.get('forecast', ''),
                            'forecast_grid_x': props.get('gridX'),
                            'forecast_grid_y': props.get('gridY')
                        }
                        
                        processed_stations.append(processed_station)
                        
                        # Cache station metadata
                        self.station_cache[processed_station['station_id']] = processed_station
                    
                    logger.info("Retrieved NOAA California stations", count=len(processed_stations))
                    return processed_stations
                    
        except Exception as e:
            logger.error("Failed to get NOAA California stations", error=str(e))
            raise
    
    async def fetch_data(self, config=None, **kwargs) -> List[Dict[str, Any]]:
        """
        Generic fetch_data method for stream_manager compatibility.
        Fetches current observations and active alerts

        ⚠️ IMPORTANT: This method returns MIXED data types in a single list:
            - Station observations (source_id='noaa_stations_current')
            - Weather alerts (source_id='noaa_alerts_active')

        Each record has its own 'source_id' field that MUST be preserved when sending to Kafka.
        The kafka_producer will now respect per-record source_id values.

        **kwargs: Accepts max_records and other parameters from ingestion modes (ignored)
        """
        try:
            # Default to fetching current station observations
            batch_config = BatchConfig(
                source_id="noaa_stations_current",
                start_date=date.today(),
                end_date=date.today()
            )

            # Fetch current observations
            data = await self.fetch_batch_data(batch_config)

            # Also fetch active alerts
            alert_config = BatchConfig(
                source_id="noaa_alerts_active",
                start_date=date.today(),
                end_date=date.today()
            )
            alerts = await self.fetch_batch_data(alert_config)

            # ✅ Combine both data sources with warning
            # Each record maintains its own source_id field for correct routing
            combined_data = data + alerts

            if data and alerts:
                logger.info(
                    "fetch_data returns mixed source types - per-record source_id will be preserved",
                    station_observations=len(data),
                    weather_alerts=len(alerts),
                    total_records=len(combined_data)
                )

            return combined_data
        except Exception as e:
            logger.error("Failed in fetch_data", error=str(e))
            return []

    async def fetch_batch_data(self, config: BatchConfig) -> List[Dict[str, Any]]:
        """
        Fetch batch weather data from NOAA stations

        Supports:
        - Current observations from multiple stations
        - Historical observations for date ranges
        - Weather alerts for specified areas
        """
        try:
            logger.info("Fetching NOAA batch data",
                       source_id=config.source_id,
                       date_range=f"{config.start_date} to {config.end_date}")
            
            # Get data source configuration
            source = next((s for s in self.data_sources if s.id == config.source_id), None)
            if not source:
                raise ValueError(f"Unknown NOAA source ID: {config.source_id}")
            
            # Route to appropriate fetcher based on source
            if "stations_current" in config.source_id:
                data = await self._fetch_current_observations(config, source)
            elif "stations_historical" in config.source_id:
                data = await self._fetch_historical_observations(config, source)
            elif "gridpoints_forecast" in config.source_id:
                data = await self._fetch_gridpoint_forecasts(config, source)
            elif "alerts_active" in config.source_id:
                data = await self._fetch_weather_alerts(config, source)
            else:
                raise ValueError(f"Unsupported NOAA source: {config.source_id}")
            
            logger.info("NOAA batch data fetched successfully",
                       source_id=config.source_id,
                       records=len(data))
            
            return data
            
        except Exception as e:
            logger.error("Failed to fetch NOAA batch data",
                        source_id=config.source_id, error=str(e))
            raise
    
    async def _fetch_current_observations(self, config: BatchConfig, source: DataSource) -> List[Dict[str, Any]]:
        """Fetch current weather observations from NOAA stations"""
        try:
            # Get California stations if not cached
            if not self.station_cache:
                await self.get_california_stations()
            
            headers = {'User-Agent': self.user_agent}
            standardized_data = []
            
            # Limit to reasonable number of stations
            stations_to_fetch = list(self.station_cache.keys())[:100]  # Top 100 stations
            
            async with aiohttp.ClientSession() as session:
                # Fetch observations from multiple stations concurrently
                tasks = []
                for station_id in stations_to_fetch:
                    task = self._fetch_station_observation(session, station_id, headers)
                    tasks.append(task)
                
                # Execute concurrent requests (limit to avoid overwhelming API)
                results = []
                batch_size = 10
                for i in range(0, len(tasks), batch_size):
                    batch = tasks[i:i + batch_size]
                    batch_results = await asyncio.gather(*batch, return_exceptions=True)
                    results.extend(batch_results)
                    
                    # Small delay between batches
                    if i + batch_size < len(tasks):
                        await asyncio.sleep(0.5)
                
                # Process results
                for result in results:
                    if isinstance(result, Exception):
                        logger.warning("Station observation fetch failed", error=str(result))
                        continue
                    
                    if result:
                        standardized_data.append(result)
            
            return standardized_data
            
        except Exception as e:
            logger.error("Failed to fetch current observations", error=str(e))
            raise
    
    async def _fetch_station_observation(self, session: aiohttp.ClientSession, 
                                       station_id: str, headers: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Fetch observation from a single station"""
        try:
            url = f"{self.base_url}/stations/{station_id}/observations/latest"
            
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    return None
                
                data = await response.json()
                obs = data.get('properties', {})
                
                # Get station metadata
                station_info = self.station_cache.get(station_id, {})
                
                # Standardize observation data
                standardized_record = {
                    'timestamp': utc_to_pacific(obs.get('timestamp')) if obs.get('timestamp') else utcnow_pacific(),
                    'station_id': station_id,
                    'station_name': station_info.get('name', 'Unknown'),
                    'latitude': station_info.get('latitude', 0.0),
                    'longitude': station_info.get('longitude', 0.0),
                    'elevation_m': station_info.get('elevation_m', 0.0),
                    'temperature_celsius': self._extract_value(obs.get('temperature')),
                    'dewpoint_celsius': self._extract_value(obs.get('dewpoint')),
                    'relative_humidity_percent': self._extract_value(obs.get('relativeHumidity')),
                    'wind_direction_degrees': self._extract_value(obs.get('windDirection')),
                    'wind_speed_ms': self._extract_value(obs.get('windSpeed')),
                    'wind_gust_ms': self._extract_value(obs.get('windGust')),
                    'barometric_pressure_pa': self._extract_value(obs.get('barometricPressure')),
                    'sea_level_pressure_pa': self._extract_value(obs.get('seaLevelPressure')),
                    'visibility_m': self._extract_value(obs.get('visibility')),
                    'precipitation_last_hour_mm': self._extract_value(obs.get('precipitationLastHour')),
                    'heat_index_celsius': self._extract_value(obs.get('heatIndex')),
                    'wind_chill_celsius': self._extract_value(obs.get('windChill')),
                    'cloud_coverage_percent': self._parse_cloud_coverage(obs.get('cloudLayers', [])),
                    'weather_description': obs.get('textDescription', ''),
                    'source': 'NOAA/NWS',
                    'source_id': 'noaa_stations_current',  # For TableRouter routing to noaa_station_observations table
                    'provider': 'National Weather Service',
                    'data_quality': self._assess_observation_quality(obs),
                    'raw_metar': obs.get('rawMessage', '')
                }
                
                return standardized_record
                
        except Exception as e:
            logger.debug("Failed to fetch station observation", 
                        station_id=station_id, error=str(e))
            return None
    
    async def _fetch_weather_alerts(self, config: BatchConfig, source: DataSource) -> List[Dict[str, Any]]:
        """Fetch active weather alerts from NOAA"""
        try:
            headers = {'User-Agent': self.user_agent}
            
            # Build query parameters for California
            params = {
                'area': 'CA',  # California
                'status': 'actual',
                'message_type': 'alert'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/alerts/active", 
                                     headers=headers, 
                                     params=params) as response:
                    
                    if response.status != 200:
                        raise RuntimeError(f"NOAA alerts API error: {response.status}")
                    
                    data = await response.json()
                    alerts = data.get('features', [])
                    
                    standardized_data = []
                    for alert in alerts:
                        props = alert.get('properties', {})
                        geom = alert.get('geometry', {})
                        
                        # Extract alert information
                        standardized_record = {
                            'timestamp': utc_to_pacific(props.get('sent')) if props.get('sent') else utcnow_pacific(),
                            'alert_id': props.get('identifier', ''),
                            'event': props.get('event', ''),
                            'headline': props.get('headline', ''),
                            'description': props.get('description', ''),
                            'instruction': props.get('instruction', ''),
                            'urgency': props.get('urgency', ''),
                            'severity': props.get('severity', ''),
                            'certainty': props.get('certainty', ''),
                            'area_description': props.get('areaDesc', ''),
                            'effective': props.get('effective', ''),
                            'onset': props.get('onset', ''),
                            'expires': props.get('expires', ''),
                            'ends': props.get('ends', ''),
                            'status': props.get('status', ''),
                            'message_type': props.get('messageType', ''),
                            'category': props.get('category', ''),
                            'sender': props.get('senderName', 'National Weather Service'),
                            'source': 'NOAA/NWS Alerts',
                            'source_id': source.id,  # Add source_id for proper routing in consumer
                            'provider': 'National Weather Service',
                            'geometry': geom,
                            'data_quality': 1.0  # NWS alerts are authoritative
                        }
                        
                        standardized_data.append(standardized_record)
                    
                    return standardized_data
                    
        except Exception as e:
            logger.error("Failed to fetch weather alerts", error=str(e))
            raise
    
    async def start_streaming(self, config: StreamingConfig) -> str:
        """Start real-time streaming of NOAA weather data"""
        try:
            stream_id = f"noaa_stream_{config.source_id}_{datetime.now().timestamp()}"
            
            logger.info("Starting NOAA weather data stream",
                       stream_id=stream_id,
                       source_id=config.source_id)
            
            # Create stream configuration
            stream_config = {
                'stream_id': stream_id,
                'source_id': config.source_id,
                'config': config,
                'status': 'active',
                'start_time': datetime.now(),
                'last_update': None,
                'records_streamed': 0,
                'last_observation_time': None
            }
            
            self.active_streams[stream_id] = stream_config
            
            # Start background streaming task
            asyncio.create_task(self._run_noaa_stream(stream_config))
            
            logger.info("NOAA weather data stream started", stream_id=stream_id)
            return stream_id
            
        except Exception as e:
            logger.error("Failed to start NOAA data stream", error=str(e))
            raise
    
    async def _run_noaa_stream(self, stream_config: Dict[str, Any]):
        """Background task for continuous NOAA weather data streaming"""
        stream_id = stream_config['stream_id']
        config = stream_config['config']
        
        logger.info("Starting NOAA stream processing loop", stream_id=stream_id)
        
        try:
            while stream_config['status'] == 'active':
                # Fetch latest weather data
                batch_config = BatchConfig(
                    source_id=config.source_id,
                    start_date=date.today(),
                    end_date=date.today(),
                    spatial_bounds=config.spatial_bounds,
                    format="json"
                )
                
                try:
                    # Start timing for latency measurement
                    start_time = time.time()

                    data = await self.fetch_batch_data(batch_config)

                    # Record ingestion latency
                    latency = time.time() - start_time
                    INGESTION_LATENCY.labels(source=config.source_id, job='data-ingestion-service').observe(latency)

                    if data:
                        # ✅ VECTORIZED VALIDATION: Defend at the stem!
                        # Separate and validate by source_id (stations vs alerts)
                        valid_by_source, invalid_records = VectorizedDataValidator.validate_and_split(
                            data=data,
                            source_id_field='source_id'
                        )

                        # Log invalid records for debugging
                        if invalid_records:
                            logger.warning(
                                f"Filtered {len(invalid_records)} invalid NOAA records before Kafka",
                                stream_id=stream_id,
                                sample_errors=[r.get('_validation_error', 'unknown') for r in invalid_records[:3]]
                            )

                        # Update metrics
                        total_valid = sum(len(records) for records in valid_by_source.values())
                        VALIDATION_TOTAL.labels(source=config.source_id, job='data-ingestion-service').inc(len(data))
                        VALIDATION_PASSED.labels(source=config.source_id, job='data-ingestion-service').inc(total_valid)
                        RECORDS_PROCESSED.labels(source=config.source_id, job='data-ingestion-service').inc(total_valid)

                        # Send each source type separately with correct source_id
                        if self.kafka_producer:
                            for source_id, records in valid_by_source.items():
                                try:
                                    await self.kafka_producer.send_batch_data(
                                        data=records,
                                        source_type="weather",
                                        source_id=source_id  # ✅ Use individual source_id!
                                    )
                                    logger.info("NOAA data sent to Kafka successfully",
                                               stream_id=stream_id,
                                               source_id=source_id,
                                               records=len(records))
                                except Exception as e:
                                    logger.error("Failed to send NOAA data to Kafka",
                                               stream_id=stream_id,
                                               source_id=source_id,
                                               error=str(e))
                        else:
                            logger.warning("No Kafka producer available for NOAA streaming",
                                          stream_id=stream_id)

                        stream_config['records_streamed'] += len(data)
                        stream_config['last_update'] = datetime.now()

                        logger.info("NOAA stream data processed",
                                   stream_id=stream_id,
                                   records=len(data),
                                   total_streamed=stream_config['records_streamed'],
                                   latency_seconds=latency)
                
                except Exception as e:
                    logger.error("NOAA stream processing error",
                                stream_id=stream_id, error=str(e))
                
                # Wait for next polling interval (NOAA updates hourly)
                await asyncio.sleep(config.polling_interval_seconds or 3600)  # Default 1 hour
                
        except asyncio.CancelledError:
            logger.info("NOAA stream cancelled", stream_id=stream_id)
        except Exception as e:
            logger.error("NOAA stream processing failed", stream_id=stream_id, error=str(e))
            stream_config['status'] = 'error'
    
    def _extract_value(self, measurement: Optional[Dict[str, Any]]) -> Optional[float]:
        """Extract numeric value from NOAA measurement object"""
        if not measurement or not isinstance(measurement, dict):
            return None
        
        try:
            value = measurement.get('value')
            if value is None:
                return None
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def _parse_cloud_coverage(self, cloud_layers: List[Dict[str, Any]]) -> Optional[float]:
        """Parse cloud coverage from NOAA cloud layer data"""
        if not cloud_layers:
            return None
        
        try:
            # Calculate total cloud coverage percentage
            total_coverage = 0
            for layer in cloud_layers:
                amount = layer.get('amount', 'CLR').upper()
                
                coverage_map = {
                    'SKC': 0,   # Sky Clear
                    'CLR': 0,   # Clear
                    'FEW': 25,  # Few (1/8 to 2/8)
                    'SCT': 50,  # Scattered (3/8 to 4/8)
                    'BKN': 75,  # Broken (5/8 to 7/8)
                    'OVC': 100  # Overcast (8/8)
                }
                
                total_coverage = max(total_coverage, coverage_map.get(amount, 0))
            
            return float(total_coverage)
            
        except Exception:
            return None
    
    def _assess_observation_quality(self, obs: Dict[str, Any]) -> float:
        """Assess weather observation data quality"""
        quality_score = 1.0

        # Check for missing critical measurements
        critical_fields = ['temperature', 'dewpoint', 'barometricPressure']
        missing_count = sum(1 for field in critical_fields if not obs.get(field))
        quality_score -= missing_count * 0.1

        # Check for reasonable temperature values
        temp = self._extract_value(obs.get('temperature'))
        if temp is not None:
            if temp < -50 or temp > 60:  # Extreme temperatures in Celsius
                quality_score -= 0.2
        else:
            quality_score -= 0.2

        # Check for reasonable pressure values
        pressure = self._extract_value(obs.get('barometricPressure'))
        if pressure is not None:
            pressure_hpa = pressure / 100  # Convert Pa to hPa
            if pressure_hpa < 800 or pressure_hpa > 1100:
                quality_score -= 0.1

        return max(0.0, quality_score)

    def set_kafka_producer(self, kafka_producer):
        """Set the Kafka producer for streaming data"""
        self.kafka_producer = kafka_producer
        logger.info("Kafka producer configured for NOAA Weather connector")
    
    async def _fetch_historical_observations(self, config: BatchConfig, source: DataSource) -> List[Dict[str, Any]]:
        """Fetch historical weather observations (placeholder)"""
        logger.info("Historical observations fetching not fully implemented yet")
        return []
    
    async def _fetch_gridpoint_forecasts(self, config: BatchConfig, source: DataSource) -> List[Dict[str, Any]]:
        """Fetch gridpoint forecast data from NOAA"""
        try:
            headers = {'User-Agent': self.user_agent}
            standardized_data = []


            # Fallback gridpoints covering major California regions (used if API fails)
            fallback_gridpoints = [
                ('LOX', 154, 45),   # Los Angeles
                ('MTR', 85, 105),   # San Francisco Bay Area
                ('SGX', 55, 15),    # San Diego
                ('HNX', 60, 90),    # Fresno/Central Valley
                ('STO', 45, 75),    # Sacramento
                ('EKA', 40, 85),    # Eureka/North Coast
                ('REV', 120, 75),   # Reno/Lake Tahoe
                ('VEF', 115, 95),   # Las Vegas (near CA border)
            ]

            # Try to load gridpoints from Redis cache first
            gridpoints_set = await self._load_cached_gridpoints()

            if gridpoints_set:
                # Cache hit - use cached gridpoints
                logger.info(f"Using {len(gridpoints_set)} cached gridpoints from Redis")
            else:
                # Cache miss - discover gridpoints from API
                logger.info("No cached gridpoints found, discovering from NOAA API...")
                stations_url = f"{self.base_url}/stations?state=CA&limit=50"
                gridpoints_set = set()  # Use set to avoid duplicates

                async with aiohttp.ClientSession() as session:
                    try:
                        # Try to discover gridpoints from stations (limit to 50 for faster response)
                        async with session.get(stations_url, headers=headers, timeout=aiohttp.ClientTimeout(total=20)) as response:
                            if response.status == 200:
                                stations_data = await response.json()
                                features = stations_data.get('features', [])

                                # Extract gridpoint info from each station
                                for feature in features:
                                    props = feature.get('properties', {})
                                    forecast_url = props.get('forecast')
                                    if forecast_url:
                                        # Extract office and grid from forecast URL
                                        # URL format: https://api.weather.gov/gridpoints/LOX/154,45/forecast
                                        try:
                                            parts = forecast_url.split('/gridpoints/')
                                            if len(parts) > 1:
                                                grid_info = parts[1].split('/')[0]  # Gets "LOX/154,45"
                                                if '/' in grid_info:
                                                    office_grid = grid_info.split('/')
                                                    office = office_grid[0]
                                                    if ',' in office_grid[1]:
                                                        coords = office_grid[1].split(',')
                                                        grid_x = int(coords[0])
                                                        grid_y = int(coords[1])
                                                        gridpoints_set.add((office, grid_x, grid_y))
                                        except:
                                            continue

                                logger.info(f"Discovered {len(gridpoints_set)} unique gridpoints from CA stations")
                                # Save to cache for 24 hours
                                await self._save_cached_gridpoints(gridpoints_set)
                            else:
                                logger.warning(f"Failed to fetch CA stations (status {response.status}), using fallback gridpoints")
                                gridpoints_set = set(fallback_gridpoints)

                    except asyncio.TimeoutError:
                        logger.warning("Station discovery timed out, using fallback gridpoints")
                        gridpoints_set = set(fallback_gridpoints)
                    except Exception as e:
                        logger.warning(f"Station discovery failed: {str(e)}, using fallback gridpoints")
                        gridpoints_set = set(fallback_gridpoints)

                    # If we still have no gridpoints, use fallback
                    if not gridpoints_set:
                        logger.warning("No gridpoints discovered, using fallback gridpoints")
                        gridpoints_set = set(fallback_gridpoints)

            async with aiohttp.ClientSession() as session:

                # Fetch forecasts for discovered gridpoints
                for office, grid_x, grid_y in gridpoints_set:
                    try:
                        url = f"{self.base_url}/gridpoints/{office}/{grid_x},{grid_y}/forecast"

                        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                            if response.status != 200:
                                logger.debug(f"Failed to fetch gridpoint {office}/{grid_x},{grid_y}: {response.status}")
                                continue

                            data = await response.json()
                            properties = data.get('properties', {})
                            periods = properties.get('periods', [])

                            # Get location info
                            geometry = data.get('geometry', {})
                            coordinates = geometry.get('coordinates', [[[]]])[0][0] if geometry.get('coordinates') else []
                            lat = coordinates[1] if len(coordinates) > 1 else 0.0
                            lon = coordinates[0] if len(coordinates) > 0 else 0.0

                            # Process each forecast period
                            for period in periods:
                                standardized_record = {
                                    'timestamp': utc_to_pacific(period.get('startTime')) if period.get('startTime') else utcnow_pacific(),
                                    'forecast_end_time': period.get('endTime', ''),
                                    'latitude': lat,
                                    'longitude': lon,
                                    'grid_office': office,
                                    'grid_x': grid_x,
                                    'grid_y': grid_y,
                                    'forecast_period': period.get('name', ''),
                                    'temperature_celsius': convert_temperature(period.get('temperature'), from_unit=period.get('temperatureUnit', 'F')),
                                    'temperature_trend': period.get('temperatureTrend', ''),
                                    'wind_speed_description': period.get('windSpeed', ''),
                                    'wind_direction': period.get('windDirection', ''),
                                    'forecast_short': period.get('shortForecast', ''),
                                    'forecast_detailed': period.get('detailedForecast', ''),
                                    'is_daytime': period.get('isDaytime', True),
                                    'probability_of_precipitation': period.get('probabilityOfPrecipitation', {}).get('value', 0),
                                    'dewpoint_celsius': self._extract_value(period.get('dewpoint')),
                                    'relative_humidity_percent': self._extract_value(period.get('relativeHumidity')),
                                    'source': 'NOAA/NWS Gridpoint Forecast',
                                    'source_id': 'noaa_gridpoints_forecast',  # For TableRouter routing to noaa_gridpoint_forecast table
                                    'provider': 'National Weather Service',
                                    'data_quality': 0.9  # Forecasts are generally high quality
                                }
                                standardized_data.append(standardized_record)

                        # Small delay between gridpoints
                        await asyncio.sleep(0.2)

                    except Exception as e:
                        logger.debug(f"Failed to fetch gridpoint {office}/{grid_x},{grid_y}", error=str(e))
                        continue

            logger.info(f"Fetched {len(standardized_data)} gridpoint forecast records")
            return standardized_data

        except Exception as e:
            logger.error("Failed to fetch gridpoint forecasts", error=str(e), exc_info=True)
            return []  # Return empty list instead of raising to keep stream alive

    async def _load_cached_gridpoints(self) -> Optional[set]:
        """Load gridpoints from Redis cache"""
        if not self.redis_client:
            return None

        try:
            cached_data = await self.redis_client.get(self.gridpoint_cache_key)
            if cached_data:
                gridpoints_list = json.loads(cached_data)
                gridpoints_set = set(tuple(gp) for gp in gridpoints_list)
                logger.info(f"Loaded {len(gridpoints_set)} gridpoints from Redis cache")
                return gridpoints_set
        except Exception as e:
            logger.warning(f"Failed to load gridpoints from cache: {str(e)}")

        return None

    async def _save_cached_gridpoints(self, gridpoints_set: set):
        """Save gridpoints to Redis cache for 24 hours"""
        if not self.redis_client:
            return

        try:
            gridpoints_list = [list(gp) for gp in gridpoints_set]
            cached_data = json.dumps(gridpoints_list)
            await self.redis_client.setex(
                self.gridpoint_cache_key,
                self.gridpoint_cache_ttl,
                cached_data
            )
            logger.info(f"Saved {len(gridpoints_set)} gridpoints to Redis cache (TTL: 24h)")
        except Exception as e:
            logger.warning(f"Failed to save gridpoints to cache: {str(e)}")