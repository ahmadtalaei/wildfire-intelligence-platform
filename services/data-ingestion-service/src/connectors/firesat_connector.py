"""
FireSat Wildfire Detection Connector
Integrates Google/Earth Fire Alliance FireSat satellite constellation data

FireSat is a constellation of 50+ satellites designed to detect wildfires as small as
5x5 meters within 20 minutes using AI-powered thermal infrared imaging.

API Status: As of 2025, FireSat API is in Early Adopter program phase.
This connector is designed for production use once API access is available.

Data Products:
- Real-time fire detections (5m resolution, 20-minute refresh)
- Fire perimeter tracking
- Radiative power measurements
- Multi-spectral thermal IR data
- AI confidence scores

Documentation: https://sites.research.google/gr/wildfires/firesat/
Early Access: https://www.earthfirealliance.org/

Environment Variables Required:
    FIRESAT_API_KEY: API key from Earth Fire Alliance
    FIRESAT_API_URL: Base API endpoint (default: https://api.firesat.earthfirealliance.org/v1)
    FIRESAT_EARLY_ACCESS_TOKEN: Early adopter program access token
"""

import asyncio
import aiohttp
import os
import json
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
import structlog
import numpy as np
from .firesat_nost_client import FireSatNOSSimulator
import time
from .metrics import INGESTION_LATENCY, VALIDATION_TOTAL, VALIDATION_PASSED, RECORDS_PROCESSED

# Import centralized utilities
from .timezone_converter import utc_to_pacific, utcnow_pacific
from .unit_converter import convert_temperature
from ..models.ingestion import DataSource, StreamingConfig, BatchConfig

# Import geographic bounds
try:
    from ..geo_config.geographic_bounds import CALIFORNIA_BOUNDS
except ImportError:
    CALIFORNIA_BOUNDS = {
        'lat_min': 32.534156,
        'lat_max': 42.009518,
        'lon_min': -124.482003,
        'lon_max': -114.131211
    }

logger = structlog.get_logger()


class FireSatConnector:
    """
    FireSat satellite constellation connector for ultra-high resolution wildfire detection

    Features:
    - 5m spatial resolution fire detection
    - 20-minute global refresh rate
    - AI-powered fire detection and tracking
    - Fire perimeter estimation
    - Real-time and historical data access
    """

    def __init__(self, api_key: Optional[str] = None, kafka_producer=None):
        """
        Initialize FireSat connector

        Args:
            api_key: FireSat API key (optional, uses env var if not provided)
            kafka_producer: Kafka producer for streaming data
        """
        # API Configuration
        self.api_key = api_key or os.getenv("FIRESAT_API_KEY")
        self.base_url = os.getenv("FIRESAT_API_URL", "https://api.firesat.earthfirealliance.org/v1")
        self.early_access_token = os.getenv("FIRESAT_EARLY_ACCESS_TOKEN")

        # Operational settings
        self.kafka_producer = kafka_producer
        self.active_streams: Dict[str, Dict] = {}
        self.data_sources = []
        self.california_bounds = CALIFORNIA_BOUNDS

        # Mock mode for development (will be disabled when API is available)
        self.mock_mode = not self.api_key
        
        # Initialize NOS Testbed simulator for realistic satellite simulation
        if self.mock_mode:
            self.nos_simulator = FireSatNOSSimulator(num_satellites=50, seed=42)
            logger.info("FireSat NOS Testbed simulator initialized for realistic orbital mechanics")
        if self.mock_mode:
            logger.warning("FireSat running in MOCK MODE - no API key configured. "
                         "Set FIRESAT_API_KEY environment variable for production use.")

        self._initialize_sources()

    def _initialize_sources(self):
        """Initialize FireSat data sources"""
        self.data_sources = [
            DataSource(
                id="firesat_detections",
                name="FireSat Real-time Fire Detections",
                source_type="satellite",
                description="AI-powered fire detections at 5m resolution with 20-minute refresh",
                provider="Earth Fire Alliance / Google Research",
                formats=["json", "geojson"],
                update_frequency="20 minutes",
                spatial_resolution="5m",
                temporal_resolution="20 minutes",
                is_active=True,
                api_endpoint=f"{self.base_url}/detections",
                authentication_required=True
            ),
            DataSource(
                id="firesat_perimeters",
                name="FireSat Fire Perimeters",
                source_type="satellite",
                description="AI-estimated fire perimeters and boundaries",
                provider="Earth Fire Alliance / Google Research",
                formats=["json", "geojson"],
                update_frequency="20 minutes",
                spatial_resolution="5m",
                temporal_resolution="20 minutes",
                is_active=True,
                api_endpoint=f"{self.base_url}/perimeters",
                authentication_required=True
            ),
            DataSource(
                id="firesat_thermal",
                name="FireSat Thermal Infrared Imagery",
                source_type="satellite",
                description="Multi-spectral thermal IR data for fire analysis",
                provider="Earth Fire Alliance / Google Research",
                formats=["geotiff", "netcdf"],
                update_frequency="20 minutes",
                spatial_resolution="5m",
                temporal_resolution="20 minutes",
                is_active=True,
                api_endpoint=f"{self.base_url}/thermal",
                authentication_required=True
            )
        ]

    async def health_check(self) -> bool:
        """Check FireSat API connectivity and authentication"""
        if self.mock_mode:
            logger.info("FireSat health check: MOCK MODE active")
            return True

        try:
            headers = self._get_auth_headers()

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/health",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info("FireSat API health check passed",
                                  api_version=data.get('version'),
                                  constellation_status=data.get('constellation_status'))
                        return True
                    else:
                        logger.warning("FireSat API health check failed",
                                     status=response.status)
                        return False
        except Exception as e:
            logger.error("FireSat API health check error", error=str(e))
            return False

    def _get_auth_headers(self) -> Dict[str, str]:
        """Generate authentication headers for FireSat API"""
        headers = {
            'User-Agent': 'WildfireIntelligence/1.0',
            'Accept': 'application/json'
        }

        if self.api_key:
            headers['X-FireSat-API-Key'] = self.api_key

        if self.early_access_token:
            headers['Authorization'] = f'Bearer {self.early_access_token}'

        return headers

    async def get_sources(self) -> List[DataSource]:
        """Get available FireSat data sources"""
        return self.data_sources

    async def fetch_batch_data(self, config: BatchConfig) -> List[Dict[str, Any]]:
        """
        Fetch batch FireSat data for specified date range

        Args:
            config: Batch configuration with date range and spatial bounds

        Returns:
            List of standardized fire detection records
        """
        try:
            logger.info("Fetching FireSat batch data",
                       source_id=config.source_id,
                       date_range=f"{config.start_date} to {config.end_date}")

            # Get data source configuration
            source = next((s for s in self.data_sources if s.id == config.source_id), None)
            if not source:
                raise ValueError(f"Unknown FireSat source ID: {config.source_id}")

            # Route to appropriate fetcher
            if config.source_id == "firesat_detections":
                data = await self._fetch_fire_detections(config, source)
            elif config.source_id == "firesat_perimeters":
                data = await self._fetch_fire_perimeters(config, source)
            elif config.source_id == "firesat_thermal":
                data = await self._fetch_thermal_imagery(config, source)
            else:
                raise ValueError(f"Unsupported FireSat source: {config.source_id}")

            logger.info("FireSat batch data fetched successfully",
                       source_id=config.source_id,
                       records=len(data))

            return data

        except Exception as e:
            logger.error("Failed to fetch FireSat batch data",
                        source_id=config.source_id, error=str(e))
            raise

    async def _fetch_fire_detections(self, config: BatchConfig, source: DataSource) -> List[Dict[str, Any]]:
        """
        Fetch FireSat fire detections

        FireSat provides ultra-high resolution fire detections with AI confidence scoring.
        Each detection includes precise geolocation, radiative power, and temporal tracking.
        """
        try:
            bounds = config.spatial_bounds or self.california_bounds

            if self.mock_mode:
                # Generate realistic mock data for development
                return self._generate_mock_detections(config, bounds)

            # Production API call
            headers = self._get_auth_headers()
            params = {
                'start_time': config.start_date.isoformat(),
                'end_time': config.end_date.isoformat(),
                'bbox': f"{bounds['lon_min']},{bounds['lat_min']},{bounds['lon_max']},{bounds['lat_max']}",
                'format': 'json',
                'confidence_min': 0.7  # Filter for high-confidence detections
            }

            standardized_data = []

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/detections",
                    headers=headers,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:

                    if response.status != 200:
                        error_text = await response.text()
                        raise RuntimeError(f"FireSat API error {response.status}: {error_text}")

                    data = await response.json()
                    detections = data.get('features', []) if data.get('type') == 'FeatureCollection' else data.get('detections', [])

                    for detection in detections:
                        standardized_record = self._parse_detection(detection)
                        if standardized_record:
                            standardized_data.append(standardized_record)

            logger.info("FireSat detections fetched",
                       count=len(standardized_data),
                       date_range=f"{config.start_date} to {config.end_date}")

            return standardized_data

        except Exception as e:
            logger.error("Failed to fetch FireSat detections", error=str(e))
            raise

    def _parse_detection(self, detection: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse FireSat detection into standardized format

        Args:
            detection: Raw detection data from FireSat API

        Returns:
            Standardized detection record compatible with platform schema
        """
        try:
            # Handle GeoJSON format
            if 'geometry' in detection:
                coords = detection['geometry'].get('coordinates', [0, 0])
                lon, lat = coords[0], coords[1]
                properties = detection.get('properties', {})
            else:
                # Handle flat JSON format
                lat = detection.get('latitude')
                lon = detection.get('longitude')
                properties = detection

            # Extract timestamp
            timestamp_raw = properties.get('detection_time') or properties.get('timestamp')
            timestamp = utc_to_pacific(timestamp_raw) if timestamp_raw else utcnow_pacific()

            # Build standardized record
            record = {
                'timestamp': timestamp,
                'latitude': float(lat),
                'longitude': float(lon),

                # Fire characteristics
                'brightness_kelvin': properties.get('brightness_temp'),
                'fire_radiative_power': properties.get('frp') or properties.get('radiative_power'),
                'fire_area_m2': properties.get('fire_area'),
                'fire_perimeter_m': properties.get('perimeter_length'),

                # AI detection metadata
                'confidence': properties.get('confidence_score'),
                'ai_model_version': properties.get('model_version'),
                'detection_algorithm': 'FireSat-AI',

                # Satellite metadata
                'satellite_id': properties.get('satellite_id'),
                'sensor': 'FireSat-TIR',  # Thermal Infrared
                'scan_angle': properties.get('scan_angle'),
                'spatial_resolution_m': 5.0,  # FireSat's 5m resolution

                # Source tracking
                'source': 'FireSat',
                'source_id': 'firesat_detections',  # For TableRouter routing
                'provider': 'Earth Fire Alliance',

                # Quality metrics
                'data_quality': self._calculate_detection_quality(properties),
                'anomaly_flags': self._check_anomalies(properties),

                # Additional metadata
                'detection_id': properties.get('id') or properties.get('detection_id'),
                'satellite_pass_id': properties.get('pass_id'),
                'processing_timestamp': properties.get('processed_at'),
            }

            return record

        except Exception as e:
            logger.error("Failed to parse FireSat detection", error=str(e))
            return None

    def _calculate_detection_quality(self, properties: Dict[str, Any]) -> float:
        """
        Calculate data quality score for FireSat detection

        Factors:
        - AI confidence score
        - Spatial resolution
        - Scan angle (nadir is best)
        - Missing critical fields
        """
        quality = 1.0

        # Check confidence score
        confidence = properties.get('confidence_score', 0)
        if confidence < 0.7:
            quality -= 0.3
        elif confidence < 0.85:
            quality -= 0.1

        # Check for missing critical data
        if not properties.get('frp') and not properties.get('radiative_power'):
            quality -= 0.2

        if not properties.get('fire_area'):
            quality -= 0.1

        # Check scan angle (prefer nadir views)
        scan_angle = properties.get('scan_angle', 0)
        if abs(scan_angle) > 30:
            quality -= 0.2
        elif abs(scan_angle) > 45:
            quality -= 0.3

        return max(0.0, min(1.0, quality))

    def _check_anomalies(self, properties: Dict[str, Any]) -> List[str]:
        """Detect anomalies in FireSat detection data"""
        anomalies = []

        # Check brightness temperature
        brightness = properties.get('brightness_temp')
        if brightness and (brightness < 300 or brightness > 1500):
            anomalies.append('unusual_brightness')

        # Check FRP
        frp = properties.get('frp') or properties.get('radiative_power')
        if frp and frp > 10000:  # Very high FRP
            anomalies.append('extreme_frp')

        # Check fire area
        area = properties.get('fire_area')
        if area and area > 1000000:  # > 1 km²
            anomalies.append('large_fire_area')

        # Low confidence but high FRP (suspicious)
        confidence = properties.get('confidence_score', 1.0)
        if confidence < 0.7 and frp and frp > 500:
            anomalies.append('confidence_frp_mismatch')

        return anomalies

    async def _fetch_fire_perimeters(self, config: BatchConfig, source: DataSource) -> List[Dict[str, Any]]:
        """
        Fetch FireSat fire perimeter data

        Perimeters are AI-generated polygon boundaries around detected fires.
        """
        try:
            bounds = config.spatial_bounds or self.california_bounds

            if self.mock_mode:
                return self._generate_mock_perimeters(config, bounds)

            # Production API implementation
            headers = self._get_auth_headers()
            params = {
                'start_time': config.start_date.isoformat(),
                'end_time': config.end_date.isoformat(),
                'bbox': f"{bounds['lon_min']},{bounds['lat_min']},{bounds['lon_max']},{bounds['lat_max']}",
                'format': 'geojson'
            }

            standardized_data = []

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/perimeters",
                    headers=headers,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:

                    if response.status != 200:
                        raise RuntimeError(f"FireSat perimeters API error: {response.status}")

                    data = await response.json()
                    features = data.get('features', [])

                    for feature in features:
                        props = feature.get('properties', {})
                        geometry = feature.get('geometry', {})

                        record = {
                            'timestamp': utc_to_pacific(props.get('observation_time')) if props.get('observation_time') else utcnow_pacific(),
                            'fire_id': props.get('fire_id'),
                            'perimeter_geometry': geometry,
                            'area_hectares': props.get('area_ha'),
                            'perimeter_km': props.get('perimeter_km'),
                            'centroid_lat': props.get('centroid_lat'),
                            'centroid_lon': props.get('centroid_lon'),
                            'confidence': props.get('confidence'),
                            'source': 'FireSat',
                            'source_id': 'firesat_perimeters',
                            'provider': 'Earth Fire Alliance',
                            'data_quality': 0.9
                        }

                        standardized_data.append(record)

            return standardized_data

        except Exception as e:
            logger.error("Failed to fetch FireSat perimeters", error=str(e))
            raise

    async def _fetch_thermal_imagery(self, config: BatchConfig, source: DataSource) -> List[Dict[str, Any]]:
        """
        Fetch FireSat thermal imagery metadata

        Returns metadata about available thermal IR scenes for download.
        Actual imagery is stored in S3/object storage.
        """
        try:
            if self.mock_mode:
                return []  # No mock imagery

            # Production implementation would fetch scene metadata
            logger.info("FireSat thermal imagery fetch not yet implemented")
            return []

        except Exception as e:
            logger.error("Failed to fetch FireSat thermal imagery", error=str(e))
            raise

    async def start_streaming(self, config: StreamingConfig) -> str:
        """
        Start real-time streaming of FireSat detections

        FireSat provides 20-minute global refresh, ideal for near-real-time monitoring.
        """
        try:
            stream_id = f"firesat_stream_{config.source_id}_{int(datetime.now().timestamp())}"

            logger.info("Starting FireSat data stream",
                       stream_id=stream_id,
                       source_id=config.source_id,
                       polling_interval=config.polling_interval_seconds)

            # Create stream configuration
            stream_config = {
                'stream_id': stream_id,
                'source_id': config.source_id,
                'config': config,
                'status': 'active',
                'start_time': datetime.now(),
                'last_update': None,
                'records_streamed': 0,
                'last_detection_time': None
            }

            self.active_streams[stream_id] = stream_config

            # Start background streaming task
            asyncio.create_task(self._run_stream(stream_config))

            logger.info("FireSat stream started",
                       stream_id=stream_id,
                       mode='mock' if self.mock_mode else 'production')

            return stream_id

        except Exception as e:
            logger.error("Failed to start FireSat stream", error=str(e))
            raise

    async def _run_stream(self, stream_config: Dict[str, Any]):
        """Background task for continuous FireSat data streaming"""
        stream_id = stream_config['stream_id']
        config = stream_config['config']

        logger.info("Starting FireSat stream processing loop", stream_id=stream_id)

        try:
            while stream_config['status'] == 'active':
                try:
                    # Start timing for latency measurement
                    start_time = time.time()

                    # Fetch latest detections (last 1 hour)
                    end_date = date.today()
                    start_date = end_date - timedelta(hours=1)

                    batch_config = BatchConfig(
                        source_id=config.source_id,
                        start_date=start_date,
                        end_date=end_date,
                        spatial_bounds=config.spatial_bounds,
                        format="json"
                    )

                    data = await self.fetch_batch_data(batch_config)

                    # Record ingestion latency
                    latency = time.time() - start_time
                    INGESTION_LATENCY.labels(source=config.source_id, job='data-ingestion-service').observe(latency)

                    if data:
                        # Validate data and record metrics
                        for record in data:
                            VALIDATION_TOTAL.labels(source=config.source_id, job='data-ingestion-service').inc()

                            # Quality check - records with valid coordinates and confidence are valid
                            if (record.get('latitude') is not None and
                                record.get('longitude') is not None and
                                record.get('confidence', 0) > 0.7):
                                VALIDATION_PASSED.labels(source=config.source_id, job='data-ingestion-service').inc()

                        # Record processed records
                        RECORDS_PROCESSED.labels(source=config.source_id, job='data-ingestion-service').inc(len(data))

                        # Send to Kafka
                        if self.kafka_producer:
                            try:
                                await self.kafka_producer.send_batch_data(
                                    data=data,
                                    source_type="satellite",
                                    source_id=config.source_id
                                )

                                stream_config['records_streamed'] += len(data)
                                stream_config['last_update'] = datetime.now()

                                logger.info("FireSat data sent to Kafka",
                                          stream_id=stream_id,
                                          records=len(data),
                                          total=stream_config['records_streamed'],
                                          latency_seconds=latency)
                            except Exception as kafka_error:
                                logger.error("Failed to send FireSat data to Kafka",
                                           stream_id=stream_id,
                                           error=str(kafka_error))

                except Exception as e:
                    logger.error("FireSat stream processing error",
                                stream_id=stream_id,
                                error=str(e))

                # Wait for next polling interval (default: 20 minutes to match FireSat refresh)
                await asyncio.sleep(config.polling_interval_seconds or 1200)

        except asyncio.CancelledError:
            logger.info("FireSat stream cancelled", stream_id=stream_id)
        except Exception as e:
            logger.error("FireSat stream failed", stream_id=stream_id, error=str(e))
            stream_config['status'] = 'error'

    async def stop_streaming(self, stream_id: str) -> bool:
        """Stop FireSat data streaming"""
        if stream_id in self.active_streams:
            self.active_streams[stream_id]['status'] = 'stopped'
            del self.active_streams[stream_id]
            logger.info("FireSat stream stopped", stream_id=stream_id)
            return True
        return False

    async def get_active_streams(self) -> List[Dict[str, Any]]:
        """Get list of active FireSat streams"""
        return [
            {
                'stream_id': stream_id,
                'source_id': config['source_id'],
                'status': config['status'],
                'start_time': config['start_time'].isoformat(),
                'records_streamed': config['records_streamed']
            }
            for stream_id, config in self.active_streams.items()
        ]

    # ===== MOCK DATA GENERATION FOR DEVELOPMENT =====

    def _generate_mock_detections(self, config: BatchConfig, bounds: Dict[str, float]) -> List[Dict[str, Any]]:
        """
        Generate realistic mock FireSat detections using NOS Testbed simulation

        Uses realistic satellite orbital mechanics to simulate fire detections.
        """
        # Check if NOS simulator is available
        if not hasattr(self, 'nos_simulator'):
            logger.error("NOS simulator not initialized, falling back to simple mock")
            return self._generate_simple_mock_detections(config, bounds)

        try:
            # Generate satellite passes for the next hour
            start_time = datetime.now()
            end_time = start_time + timedelta(hours=1)

            passes = self.nos_simulator.generate_satellite_passes(start_time, end_time, bounds)

            # Generate or reuse fire scenarios
            if not self.nos_simulator.active_fires:
                fires = self.nos_simulator.generate_fire_scenarios(start_time, num_fires=10, bounds=bounds)
            else:
                fires = self.nos_simulator.active_fires

            # Simulate fire detections from satellite passes
            detections = self.nos_simulator.simulate_fire_detections(passes, fires)

            logger.info("Generated NOS-based FireSat detections",
                       num_detections=len(detections),
                       num_passes=len(passes),
                       num_fires=len(fires),
                       simulation_mode="NOS_TESTBED")

            return detections

        except Exception as e:
            logger.error("Error generating NOS detections, falling back to simple mock", error=str(e))
            return self._generate_simple_mock_detections(config, bounds)

    def _generate_simple_mock_detections(self, config: BatchConfig, bounds: Dict[str, float]) -> List[Dict[str, Any]]:
        """
        Fallback simple mock detection generator

        Used if NOS simulator fails or is unavailable.
        """
        np.random.seed(42)  # Reproducible for testing

        # Generate 10-50 random detections
        num_detections = np.random.randint(10, 50)
        detections = []

        for i in range(num_detections):
            # Random location in California
            lat = np.random.uniform(bounds['lat_min'], bounds['lat_max'])
            lon = np.random.uniform(bounds['lon_min'], bounds['lon_max'])

            # Realistic fire parameters
            confidence = np.random.uniform(0.75, 0.99)
            brightness = np.random.uniform(350, 800)  # Kelvin
            frp = np.random.uniform(5, 500)  # MW
            fire_area = np.random.uniform(25, 2500)  # m� (5m to 50m radius)

            detection = {
                'timestamp': utcnow_pacific(),
                'latitude': lat,
                'longitude': lon,
                'brightness_kelvin': brightness,
                'fire_radiative_power': frp,
                'fire_area_m2': fire_area,
                'fire_perimeter_m': np.sqrt(fire_area / np.pi) * 2 * np.pi,
                'confidence': confidence,
                'ai_model_version': 'FireSat-AI-v1.0-mock',
                'detection_algorithm': 'FireSat-AI',
                'satellite_id': f'FIRESAT-{np.random.randint(1, 51)}',
                'sensor': 'FireSat-TIR',
                'scan_angle': np.random.uniform(-30, 30),
                'spatial_resolution_m': 5.0,
                'source': 'FireSat',
                'source_id': 'firesat_detections',
                'provider': 'Earth Fire Alliance',
                'data_quality': confidence,
                'anomaly_flags': [],
                'detection_id': f'MOCK-{i:06d}',
                'satellite_pass_id': f'PASS-{np.random.randint(1000, 9999)}',
                'processing_timestamp': utcnow_pacific(),
            }

            detections.append(detection)

        logger.info("Generated simple mock FireSat detections",
                   count=len(detections),
                   mode='SIMPLE_MOCK')

        return detections

    def _generate_mock_perimeters(self, config: BatchConfig, bounds: Dict[str, float]) -> List[Dict[str, Any]]:
        """Generate mock fire perimeter data"""
        np.random.seed(43)

        num_perimeters = np.random.randint(5, 15)
        perimeters = []

        for i in range(num_perimeters):
            centroid_lat = np.random.uniform(bounds['lat_min'], bounds['lat_max'])
            centroid_lon = np.random.uniform(bounds['lon_min'], bounds['lon_max'])
            area_ha = np.random.uniform(1, 500)

            perimeter = {
                'timestamp': utcnow_pacific(),
                'fire_id': f'FIRE-{i:04d}',
                'perimeter_geometry': {
                    'type': 'Polygon',
                    'coordinates': [[
                        [centroid_lon, centroid_lat],
                        [centroid_lon + 0.01, centroid_lat],
                        [centroid_lon + 0.01, centroid_lat + 0.01],
                        [centroid_lon, centroid_lat + 0.01],
                        [centroid_lon, centroid_lat]
                    ]]
                },
                'area_hectares': area_ha,
                'perimeter_km': np.sqrt(area_ha / 100) * 4,
                'centroid_lat': centroid_lat,
                'centroid_lon': centroid_lon,
                'confidence': np.random.uniform(0.8, 0.95),
                'source': 'FireSat',
                'source_id': 'firesat_perimeters',
                'provider': 'Earth Fire Alliance',
                'data_quality': 0.9
            }

            perimeters.append(perimeter)

        return perimeters


# Example usage and testing
async def test_firesat_connector():
    """Test FireSat connector functionality"""
    connector = FireSatConnector()

    # Health check
    healthy = await connector.health_check()
    print(f"Health check: {'✓' if healthy else '✗'}")

    # Fetch batch data
    config = BatchConfig(
        source_id="firesat_detections",
        start_date=date.today() - timedelta(days=1),
        end_date=date.today(),
        format="json"
    )

    detections = await connector.fetch_batch_data(config)
    print(f"Fetched {len(detections)} detections")

    if detections:
        print("\nSample detection:")
        print(json.dumps(detections[0], indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(test_firesat_connector())
