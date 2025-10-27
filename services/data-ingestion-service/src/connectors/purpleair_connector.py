"""
PurpleAir API Connector
Real-time air quality sensor data from PurpleAir sensor network
Fetches data from real IoT sensors across California

API Documentation: https://api.purpleair.com
"""

import asyncio
import aiohttp
from datetime import datetime
from typing import List, Dict, Any, Optional
import structlog
import time

# Import centralized conversion utilities
from .timezone_converter import utc_to_pacific, utcnow_pacific
from .unit_converter import convert_temperature, convert_pressure
from .metrics import INGESTION_LATENCY, VALIDATION_TOTAL, VALIDATION_PASSED, RECORDS_PROCESSED

logger = structlog.get_logger()

# Import centralized geographic bounds with configuration fallback
try:
    from ..geo_config.geographic_bounds import CALIFORNIA_BOUNDS_BBOX
except ImportError:
    try:
        from geo_config.geographic_bounds import CALIFORNIA_BOUNDS_BBOX
    except ImportError:
        # Fallback bounds from configuration settings
        from ..config import get_settings
        settings = get_settings()
        CALIFORNIA_BOUNDS_BBOX = {
            'nwlng': settings.CA_lon_min,
            'nwlat': settings.CA_lat_max,
            'selng': settings.CA_lon_max,
            'selat': settings.CA_lat_min
        }


class PurpleAirConnector:
    """Connector for PurpleAir real-time air quality sensor network"""

    def __init__(self, api_key: str, kafka_producer=None):
        """
        Initialize PurpleAir connector

        Args:
            api_key: PurpleAir API key
            kafka_producer: Kafka producer for streaming data
        """
        self.api_key = api_key
        self.base_url = "https://api.purpleair.com/v1"
        self.kafka_producer = kafka_producer
        self.active_streams = {}
        self.california_bounds = CALIFORNIA_BOUNDS_BBOX

    async def health_check(self) -> bool:
        """Check PurpleAir API connectivity"""
        if not self.api_key:
            logger.warning("PurpleAir API key not configured")
            return False

        try:
            headers = {"X-API-Key": self.api_key}
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/keys", headers=headers, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info("PurpleAir API health check passed",
                                  api_version=data.get('api_version'))
                        return True
                    else:
                        logger.warning("PurpleAir API health check failed", status=response.status)
                        return False
        except Exception as e:
            logger.error("PurpleAir API health check error", error=str(e))
            return False

    async def get_california_sensors(self) -> List[Dict[str, Any]]:
        """
        Get all PurpleAir sensors in California

        Returns:
            List of sensor metadata (sensor_index, name, location, etc.)
        """
        try:
            headers = {"X-API-Key": self.api_key}

            # Request sensors within California bounding box
            params = {
                'fields': 'sensor_index,name,latitude,longitude,altitude,location_type,model,hardware',
                'location_type': '0',  # Outside sensors only
                'nwlng': self.california_bounds['nwlng'],
                'nwlat': self.california_bounds['nwlat'],
                'selng': self.california_bounds['selng'],
                'selat': self.california_bounds['selat']
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/sensors",
                                     headers=headers,
                                     params=params,
                                     timeout=30) as response:

                    if response.status == 200:
                        data = await response.json()
                        sensors = []

                        if 'data' in data and data['data']:
                            fields = data.get('fields', [])
                            for sensor_data in data['data']:
                                sensor = dict(zip(fields, sensor_data))
                                sensors.append(sensor)

                        logger.info("Retrieved PurpleAir sensors in California",
                                  count=len(sensors))
                        return sensors

                    else:
                        logger.error("Failed to retrieve PurpleAir sensors",
                                   status=response.status,
                                   body=await response.text())
                        return []

        except Exception as e:
            logger.error("Error retrieving PurpleAir sensors", error=str(e))
            return []

    async def get_sensor_data(self, sensor_indices: List[int]) -> List[Dict[str, Any]]:
        """
        Get real-time data from specific sensors

        Args:
            sensor_indices: List of PurpleAir sensor indices

        Returns:
            List of sensor readings
        """
        if not sensor_indices:
            return []

        try:
            headers = {"X-API-Key": self.api_key}

            # Fields to retrieve (air quality data)
            fields = [
                'sensor_index', 'name', 'latitude', 'longitude', 'altitude',
                'pm2.5_atm', 'pm2.5_cf_1', 'pm10.0_atm', 'pm10.0_cf_1',
                'temperature', 'humidity', 'pressure',
                'voc', 'ozone1', 'analog_input',
                'rssi', 'uptime', 'pa_latency',
                'last_seen', 'last_modified'
            ]

            params = {'fields': ','.join(fields)}

            readings = []

            # PurpleAir allows multiple sensor indices in one request
            sensor_list = ','.join(map(str, sensor_indices[:10]))  # Max 10 per request

            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/sensors/{sensor_list}"
                async with session.get(url, headers=headers, params=params, timeout=30) as response:

                    if response.status == 200:
                        data = await response.json()

                        if 'data' in data:
                            field_names = data.get('fields', [])

                            for sensor_data in data['data']:
                                reading = self._parse_sensor_reading(field_names, sensor_data)
                                if reading:
                                    readings.append(reading)

                        logger.info("Retrieved PurpleAir sensor readings",
                                  count=len(readings))

                    else:
                        logger.error("Failed to retrieve PurpleAir sensor data",
                                   status=response.status)

            return readings

        except Exception as e:
            logger.error("Error retrieving PurpleAir sensor data", error=str(e))
            return []

    def _parse_sensor_reading(self, fields: List[str], data: List[Any]) -> Optional[Dict[str, Any]]:
        """Parse raw sensor data into standardized format"""
        try:
            sensor_dict = dict(zip(fields, data))

            # Convert to standardized format for Kafka
            reading = {
                'sensor_id': f"purpleair_{sensor_dict.get('sensor_index')}",
                'sensor_name': sensor_dict.get('name', 'Unknown'),
                'latitude': sensor_dict.get('latitude'),
                'longitude': sensor_dict.get('longitude'),
                'altitude': sensor_dict.get('altitude'),
                'timestamp': utcnow_pacific(),
                'source': 'purpleair',
                'source_id': 'purpleair_california',  # For TableRouter routing to sensor_readings table
                'provider': 'PurpleAir Inc',

                # Air quality measurements
                'pm25': sensor_dict.get('pm2.5_atm'),  # PM2.5 atmospheric
                'pm10': sensor_dict.get('pm10.0_atm'),  # PM10 atmospheric
                # Convert temperature from Fahrenheit to Celsius (SI standard)
                'temperature': convert_temperature(sensor_dict.get('temperature'), from_unit='F'),
                'humidity': sensor_dict.get('humidity'),
                # Convert pressure from mbar/hPa to Pascals (SI standard)
                'pressure': convert_pressure(sensor_dict.get('pressure'), from_unit='hPa'),
                'voc': sensor_dict.get('voc'),  # Volatile Organic Compounds
                'ozone': sensor_dict.get('ozone1'),

                # Sensor health
                'rssi': sensor_dict.get('rssi'),  # Signal strength
                'uptime': sensor_dict.get('uptime'),
                'last_seen': sensor_dict.get('last_seen'),

                # Metadata
                'sensor_type': 'air_quality',
                'data_quality': self._calculate_quality_score(sensor_dict)
            }

            return reading

        except Exception as e:
            logger.error("Error parsing PurpleAir sensor reading", error=str(e))
            return None

    def _calculate_quality_score(self, sensor_data: Dict[str, Any]) -> float:
        """Calculate data quality score based on sensor health"""
        quality = 1.0

        # Check for missing critical data
        if sensor_data.get('pm2.5_atm') is None:
            quality -= 0.3
        if sensor_data.get('temperature') is None:
            quality -= 0.2
        if sensor_data.get('humidity') is None:
            quality -= 0.1

        # Check signal strength
        rssi = sensor_data.get('rssi')
        if rssi and rssi < -80:
            quality -= 0.2

        return max(0.0, min(1.0, quality))

    async def start_streaming(self, config, max_sensors: int = 100) -> str:
        """
        Start streaming PurpleAir sensor data

        Args:
            config: StreamingConfig object
            max_sensors: Maximum number of sensors to stream (default 100 for manageable volume)

        Returns:
            stream_id: Unique identifier for this stream
        """
        stream_id = f"purpleair_stream_{int(datetime.now().timestamp())}"

        logger.info("Starting PurpleAir sensor stream", stream_id=stream_id, max_sensors=max_sensors)

        # Get California sensors
        sensors = await self.get_california_sensors()

        if not sensors:
            logger.error("No PurpleAir sensors found in California")
            return stream_id

        sensor_indices = [s['sensor_index'] for s in sensors if 'sensor_index' in s]

        # Limit to max_sensors for manageable data volume
        if len(sensor_indices) > max_sensors:
            # Select evenly distributed subset across California
            step = len(sensor_indices) // max_sensors
            sensor_indices = sensor_indices[::step][:max_sensors]
            logger.info(f"Limited PurpleAir sensors to {len(sensor_indices)} out of {len(sensors)} available")

        # Store stream metadata
        self.active_streams[stream_id] = {
            'sensor_indices': sensor_indices,
            'status': 'active',
            'start_time': datetime.now(),
            'records_streamed': 0
        }

        # Start background streaming task
        asyncio.create_task(self._stream_loop(stream_id, sensor_indices))

        logger.info("PurpleAir stream started",
                   stream_id=stream_id,
                   sensors=len(sensor_indices))

        return stream_id

    async def _stream_loop(self, stream_id: str, sensor_indices: List[int],
                          interval_seconds: int = 120):
        """
        Background streaming loop

        Args:
            stream_id: Stream identifier
            sensor_indices: List of sensor indices to poll
            interval_seconds: Polling interval (120s for API rate limits)
        """
        stream_meta = self.active_streams.get(stream_id)

        while stream_meta and stream_meta['status'] == 'active':
            try:
                # Start timing for latency measurement
                start_time = time.time()

                # Fetch data from sensors in batches
                all_readings = []
                for i in range(0, len(sensor_indices), 10):
                    batch = sensor_indices[i:i+10]
                    readings = await self.get_sensor_data(batch)

                    # Track validation metrics
                    for reading in readings:
                        VALIDATION_TOTAL.labels(source='purpleair', job='data-ingestion-service').inc()

                        # Quality check - valid if has PM2.5 data
                        if reading.get('pm25') is not None:
                            VALIDATION_PASSED.labels(source='purpleair', job='data-ingestion-service').inc()

                    all_readings.extend(readings)

                    # Delay between batches
                    await asyncio.sleep(2)

                # Record ingestion latency
                latency = time.time() - start_time
                INGESTION_LATENCY.labels(source='purpleair', job='data-ingestion-service').observe(latency)

                # Send to Kafka
                if self.kafka_producer and all_readings:
                    # Record processed records
                    RECORDS_PROCESSED.labels(source='purpleair', job='data-ingestion-service').inc(len(all_readings))

                    await self.kafka_producer.send_batch_data(
                        data=all_readings,
                        source_type="iot",
                        source_id="purpleair_california"
                    )

                    stream_meta['records_streamed'] += len(all_readings)

                    logger.info("PurpleAir data sent to Kafka",
                              stream_id=stream_id,
                              batch_size=len(all_readings),
                              total=stream_meta['records_streamed'],
                              latency_seconds=latency)

                # Wait before next cycle
                await asyncio.sleep(interval_seconds)

            except Exception as e:
                logger.error("Error in PurpleAir stream loop",
                           stream_id=stream_id,
                           error=str(e))
                await asyncio.sleep(30)

    async def stop_streaming(self, stream_id: str) -> bool:
        """Stop a streaming session"""
        if stream_id in self.active_streams:
            self.active_streams[stream_id]['status'] = 'stopped'
            logger.info("PurpleAir stream stopped", stream_id=stream_id)
            return True
        return False

    async def get_active_streams(self) -> List[Dict[str, Any]]:
        """Get list of active streams"""
        return [
            {
                'stream_id': sid,
                'status': meta['status'],
                'start_time': meta['start_time'].isoformat(),
                'records_streamed': meta['records_streamed'],
                'sensors': len(meta['sensor_indices'])
            }
            for sid, meta in self.active_streams.items()
        ]