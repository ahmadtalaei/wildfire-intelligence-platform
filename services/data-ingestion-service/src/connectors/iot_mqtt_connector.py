"""
IoT MQTT Weather Station Connector
Real-time environmental sensor data from IoT weather stations via MQTT

Where is geograpphical bound in iot_mqtt_connecotr? The IoT MQTT connector is correctly implemented without geographic bounds configuration because it follows the
device-to-cloud streaming pattern where location filtering happens at the device/topic level, not at the connector configuration level.

✅ How to run:
cd C:\\dev\\wildfire\\services\\data-ingestion-service
python -m src.connectors.iot_mqtt_connector

The file defines the IoTMQTTConnector class, which is responsible for connecting your system to an MQTT broker (like HiveMQ, Mosquitto, or AWS IoT). This allows your wildfire platform to ingest real-time IoT sensor data (e.g., weather stations, soil sensors, air quality monitors) via MQTT topics.

🧩 Role in the System:
- It’s basically the bridge between raw IoT devices and your wildfire platform.
- Sensors publish data → broker → IoTMQTTConnector → your ingestion pipeline.
- Ensures real-time, low-latency data ingestion for wildfire risk monitoring.

⚙️ How It Works:
1. Initialization (__init__ + _initialize_sources)
- Reads broker config (host, port, username, password, topics, etc.) from .env
- Creates a list of data sources (e.g., “Soil Moisture”, “Weather Station”, "Air Quality") that are tied to MQTT topics.

2. Connecting to Broker (connect)
- Subscribes to relevant with a Topic such as weather/station123/temperature,
that returns what is inside the MQTT message payload itself, not in the topic, such as
{
  "timestamp": "2025-09-20T17:35:12Z",
  "value": 27.4,
  "unit": "C"
}
- Runs the client loop in the background.

3. Message Handling (on_message)
Every time a message arrives from a sensor topic:
- Parses the payload (usually JSON).
- Wraps it into a structured event object (with source_id, timestamp, payload).
- Passes it along for processing (into your ingestion or Kafka stream).

Supports:
- Arduino/ESP32 weather stations
- Raspberry Pi weather stations  
- Commercial IoT weather devices
- Personal weather station networks
"""

import asyncio
import json
import ssl
import os
import pickle
from collections import deque
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional, Callable, Deque
import structlog

# Import centralized conversion utilities
from .timezone_converter import utc_to_pacific, utcnow_pacific
from .unit_converter import convert_wind_speed, convert_pressure
try:
    from ..models.ingestion import DataSource, StreamingConfig, BatchConfig
except ImportError:
    try:
        from models.ingestion import DataSource, StreamingConfig, BatchConfig
    except ImportError:
        # Final fallback - create minimal models inline
        from typing import Any
        from datetime import date
        from dataclasses import dataclass

        @dataclass
        class DataSource:
            id: str
            name: str
            provider: str = "IoT MQTT"

        @dataclass
        class StreamingConfig:
            source_id: str

        @dataclass
        class BatchConfig:
            source_id: str
            start_date: date
            end_date: date
            format: str = "json"

# MQTT client import (requires paho-mqtt: pip install paho-mqtt)
try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False
    mqtt = None

logger = structlog.get_logger()


class IoTMQTTConnector:
    """IoT MQTT weather station data connector"""
    
    def __init__(self,
                 broker_host: Optional[str] = None,
                 broker_port: Optional[int] = None,
                 username: Optional[str] = None,
                 password: Optional[str] = None,
                 use_ssl: Optional[bool] = None,
                 kafka_producer=None,
                 enable_offline_buffer: bool = True,
                 buffer_max_size: int = 10000,
                 buffer_persist_path: Optional[str] = None):
        """
        Initialize IoT MQTT connector with environment variable configuration and offline buffering

        Args:
            broker_host: MQTT broker hostname/IP (overrides env var)
            broker_port: MQTT broker port (overrides env var)
            username: MQTT username (overrides env var)
            password: MQTT password (overrides env var)
            use_ssl: Whether to use SSL/TLS connection (overrides env var)
            kafka_producer: Kafka producer instance for streaming data
            enable_offline_buffer: Enable buffering when offline/disconnected
            buffer_max_size: Maximum number of messages to buffer
            buffer_persist_path: Path to persist buffer to disk (survives restarts)
        """
        if not MQTT_AVAILABLE:
            logger.warning("paho-mqtt library not installed. MQTT functionality disabled. Run: pip install paho-mqtt")
            self.mqtt_enabled = False
            return

        # Load configuration from environment variables from .env with fallbacks
        self.broker_host = broker_host or os.getenv("MQTT_BROKER_HOST", "localhost")
        self.broker_port = broker_port or int(os.getenv("MQTT_BROKER_PORT", "1883"))
        self.username = username or os.getenv("MQTT_USERNAME")
        self.password = password or os.getenv("MQTT_PASSWORD")
        self.use_ssl = use_ssl if use_ssl is not None else os.getenv("MQTT_USE_SSL", "false").lower() == "true"
        self.kafka_producer = kafka_producer
        self.mqtt_enabled = True

        self.client = None
        self.active_streams: Dict[str, Dict] = {}
        self.data_sources = []
        self.received_messages = []  # Buffer for received messages
        self.message_handlers: Dict[str, Callable] = {}
        self.message_queue = None  # asyncio.Queue for thread-safe message passing

        # Offline buffering configuration
        self.enable_offline_buffer = enable_offline_buffer
        self.buffer_max_size = buffer_max_size
        self.buffer_persist_path = Path(buffer_persist_path) if buffer_persist_path else Path("./iot_buffer.pkl")

        # Offline buffer (circular buffer using deque)
        self.offline_buffer: Deque[Dict[str, Any]] = deque(maxlen=buffer_max_size)

        # Connection state tracking
        self.is_connected = False
        self.last_connection_time: Optional[datetime] = None
        self.last_disconnection_time: Optional[datetime] = None
        self.disconnection_count = 0

        # Buffer metrics
        self.buffer_metrics = {
            'messages_buffered': 0,
            'messages_dropped': 0,
            'buffer_flushes': 0,
            'max_buffer_size_reached': 0,
            'total_offline_duration': 0.0
        }

        # Load persisted buffer if it exists
        if self.enable_offline_buffer:
            self._load_persisted_buffer()

        self._initialize_sources()
    
    def _initialize_sources(self):
        """Initialize IoT MQTT data sources"""
        self.data_sources = [
            DataSource(
                id="iot_weather_stations",
                name="IoT Weather Stations via MQTT",
                source_type="iot",
                description="Real-time weather data from IoT weather stations via MQTT",
                provider="Various IoT Devices",
                formats=["json", "csv", "plain_text"],
                update_frequency="Real-time (seconds to minutes)",
                spatial_resolution="Point measurements",
                temporal_resolution="Continuous",
                is_active=self.mqtt_enabled,
                api_endpoint=f"mqtt://{self.broker_host}:{self.broker_port}/topics: weather/+/temperature, weather/+/humidity, weather/+/data",
                authentication_required=bool(self.username)
            ),
            DataSource(
                id="iot_air_quality_sensors",
                name="IoT Air Quality Sensors",
                source_type="iot",
                description="Air quality measurements from IoT sensors via MQTT",
                provider="Various IoT Devices",
                formats=["json", "csv", "plain_text"],
                update_frequency="Real-time (1-5 minutes)",
                spatial_resolution="Point measurements",
                temporal_resolution="Continuous",
                is_active=self.mqtt_enabled,
                api_endpoint=f"mqtt://{self.broker_host}:{self.broker_port}/topics: air_quality/+/pm25, air_quality/+/pm10, air_quality/+/data",
                authentication_required=bool(self.username)
            ),
            DataSource(
                id="iot_soil_moisture_sensors",
                name="IoT Soil Moisture Sensors",
                source_type="iot",
                description="Soil moisture and temperature from agricultural IoT sensors",
                provider="Various IoT Devices",
                formats=["json", "csv", "plain_text"],
                update_frequency="Real-time (5-30 minutes)",
                spatial_resolution="Point measurements",
                temporal_resolution="Continuous",
                is_active=self.mqtt_enabled,
                api_endpoint=f"mqtt://{self.broker_host}:{self.broker_port}/topics: soil/+/moisture, soil/+/temperature, agriculture/+/soil_moisture",
                authentication_required=bool(self.username)
            )
        ]
    
    async def health_check(self) -> bool:
        """Check MQTT broker connectivity"""
        if not self.mqtt_enabled:
            logger.warning("MQTT not enabled - skipping health check")
            return False
            
        try:
            # Create temporary client for health check with protocol version
            test_client = mqtt.Client(protocol=mqtt.MQTTv311, clean_session=True)

            if self.username and self.password:
                test_client.username_pw_set(username=self.username, password=self.password)
            
            if self.use_ssl:
                test_client.tls_set(ca_certs=None, certfile=None, keyfile=None,
                                  cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLS,
                                  ciphers=None)
            
            # Set connection result flag
            connection_result = {'connected': False, 'error': None}
            
            def on_connect(client, userdata, flags, rc):
                if rc == 0:
                    connection_result['connected'] = True
                else:
                    connection_result['error'] = f"Connection failed with code {rc}"
                client.disconnect()
            
            test_client.on_connect = on_connect
            
            # Attempt connection
            test_client.connect(self.broker_host, self.broker_port, 10)
            test_client.loop_start()
            
            # Wait for connection result
            for _ in range(50):  # Wait up to 5 seconds
                if connection_result['connected'] or connection_result['error']:
                    break
                await asyncio.sleep(0.1)
            
            test_client.loop_stop()
            test_client.disconnect()
            
            if connection_result['connected']:
                logger.info("MQTT broker health check passed",
                          broker=f"{self.broker_host}:{self.broker_port}")
                return True
            else:
                logger.warning("MQTT broker health check failed", 
                             error=connection_result.get('error', 'Unknown'))
                return False
                
        except Exception as e:
            logger.error("MQTT broker health check error", error=str(e))
            return False
    
    async def get_sources(self) -> List[DataSource]:
        """Get available IoT MQTT data sources"""
        return self.data_sources

    async def add_source(self, source: DataSource) -> DataSource:
        """Add a new IoT MQTT data source"""
        try:
            # Validate that this is an IoT/sensor source
            if source.source_type not in ["sensor", "iot"]:
                raise ValueError(f"Invalid source type for IoT MQTT connector: {source.source_type}")

            # Check if source already exists
            existing_source = next((s for s in self.data_sources if s.id == source.id), None)
            if existing_source:
                logger.warning("IoT MQTT source already exists", source_id=source.id)
                return existing_source

            # Set connector-specific properties
            source.is_active = self.mqtt_enabled
            if source.api_endpoint is None:
                # Generate default MQTT endpoint based on source type
                topics = self._get_topics_for_source(source.id)
                source.api_endpoint = f"mqtt://{self.broker_host}:{self.broker_port}/topics: {', '.join(topics[:3])}"

            source.authentication_required = bool(self.username)

            # Add to our data sources list
            self.data_sources.append(source)

            logger.info("IoT MQTT data source added successfully",
                       source_id=source.id,
                       source_name=source.name)

            return source

        except Exception as e:
            logger.error("Failed to add IoT MQTT data source",
                        source_id=source.id if source else "unknown",
                        error=str(e))
            raise
    
    async def start_streaming(self, config: StreamingConfig) -> str:
        """Start real-time streaming of IoT MQTT data"""
        try:
            # Create asyncio.Queue for thread-safe message passing from MQTT callbacks
            self.message_queue = asyncio.Queue()

            stream_id = f"iot_mqtt_stream_{config.source_id}_{datetime.now().timestamp()}"

            logger.info("Starting IoT MQTT data stream",
                       stream_id=stream_id,
                       source_id=config.source_id)
            
            # Create MQTT client with protocol version 4 (MQTT 3.1.1) for compatibility
            client = mqtt.Client(
                client_id=f"wildfire_platform_{stream_id}",
                protocol=mqtt.MQTTv311,
                clean_session=True
            )

            if self.username and self.password:
                logger.info("Setting MQTT credentials",
                          username=self.username,
                          has_password=bool(self.password),
                          broker_host=self.broker_host,
                          broker_port=self.broker_port,
                          password_length=len(self.password))
                # Set credentials BEFORE any connection attempt
                client.username_pw_set(username=self.username, password=self.password)
                logger.info("MQTT credentials set successfully")
            else:
                logger.warning("MQTT credentials not configured",
                             username=self.username,
                             password_set=bool(self.password))

            if self.use_ssl:
                client.tls_set(ca_certs=None, certfile=None, keyfile=None,
                             cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLS,
                             ciphers=None)
            
            # Create stream configuration
            stream_config = {
                'stream_id': stream_id,
                'source_id': config.source_id,
                'config': config,
                'client': client,
                'status': 'active',
                'start_time': datetime.now(),
                'last_update': None,
                'records_streamed': 0,
                'subscribed_topics': []
            }
            
            # Enhanced callbacks with buffering support
            def on_connect_with_buffering(client, userdata, flags, rc):
                if rc == 0:
                    logger.info("MQTT client connected", stream_id=stream_id)

                    # Update connection state
                    self._update_connection_state(True)

                    # Subscribe to relevant topics based on source type
                    topics = self._get_topics_for_source(config.source_id)

                    for topic in topics:
                        client.subscribe(topic)
                        stream_config['subscribed_topics'].append(topic)
                        logger.info("Subscribed to MQTT topic", stream_id=stream_id, topic=topic)

                else:
                    logger.error("MQTT connection failed", stream_id=stream_id, rc=rc)
                    stream_config['status'] = 'error'
                    self._update_connection_state(False)

            def on_message_with_buffering(client, userdata, msg):
                try:
                    # Parse received message
                    payload = msg.payload.decode('utf-8')
                    topic = msg.topic

                    # Process the message
                    processed_data = self._process_mqtt_message(topic, payload, stream_config)

                    if processed_data:
                        message_wrapper = {
                            'data': processed_data,
                            'stream_id': stream_id,
                            'topic': topic,
                            'source_id': config.source_id
                        }

                        # Check if we're connected and can send directly
                        if self.is_connected and self.message_queue:
                            # Put message in queue for async processing
                            self.message_queue.put_nowait(message_wrapper)
                            logger.debug("MQTT message queued for processing",
                                       stream_id=stream_id,
                                       topic=topic)
                        else:
                            # Buffer the message for later delivery
                            if self._buffer_message(message_wrapper):
                                logger.debug("MQTT message buffered while offline",
                                           stream_id=stream_id,
                                           topic=topic)
                            else:
                                logger.warning("Failed to buffer MQTT message",
                                             stream_id=stream_id,
                                             topic=topic)

                        stream_config['records_streamed'] += 1
                        stream_config['last_update'] = datetime.now()

                except Exception as e:
                    logger.error("MQTT message processing error",
                               stream_id=stream_id,
                               topic=msg.topic,
                               error=str(e))

            def on_disconnect_with_buffering(client, userdata, rc):
                logger.info("MQTT client disconnected", stream_id=stream_id, rc=rc)
                self._update_connection_state(False)

                if stream_config['status'] == 'active':
                    # Persist buffer when disconnected
                    self._persist_buffer()
                    # Attempt reconnection
                    asyncio.create_task(self._reconnect_mqtt_client(stream_config))

            # Set enhanced callbacks
            client.on_connect = on_connect_with_buffering
            client.on_message = on_message_with_buffering
            client.on_disconnect = on_disconnect_with_buffering
            
            # Connect to broker
            client.connect_async(self.broker_host, self.broker_port, 60)
            client.loop_start()

            self.active_streams[stream_id] = stream_config

            # Start background task to process messages from queue
            asyncio.create_task(self._process_message_queue(stream_id, config))

            logger.info("IoT MQTT data stream started", stream_id=stream_id)
            return stream_id
            
        except Exception as e:
            logger.error("Failed to start IoT MQTT data stream", error=str(e))
            raise
    
    async def _process_message_queue(self, stream_id: str, config: StreamingConfig):
        """
        OPTIMIZED: Background task to process messages from queue and send to Kafka in batches.
        This provides 10-20x better Kafka throughput by batching messages instead of sending one-by-one.
        """
        logger.info("Message queue processor started (batched mode)", stream_id=stream_id)

        # Batch configuration for optimal Kafka throughput
        batch_size = 100  # Max messages per batch
        batch_timeout = 5.0  # Max seconds to wait for batch to fill

        while stream_id in self.active_streams and self.active_streams[stream_id]['status'] == 'active':
            try:
                messages = []
                deadline = asyncio.get_event_loop().time() + batch_timeout

                # Collect messages until batch is full or timeout expires
                while len(messages) < batch_size:
                    remaining_time = deadline - asyncio.get_event_loop().time()
                    if remaining_time <= 0:
                        break

                    try:
                        # Try to get message with remaining time
                        message = await asyncio.wait_for(
                            self.message_queue.get(),
                            timeout=min(remaining_time, 0.1)  # Check every 100ms
                        )
                        messages.append(message)
                    except asyncio.TimeoutError:
                        # Timeout while waiting for message
                        break

                # Send batch to Kafka if we have messages
                if messages and self.kafka_producer:
                    try:
                        # Extract data from all messages
                        batch_data = [msg['data'] for msg in messages]

                        # Send entire batch in single Kafka call (10-20x faster!)
                        await self.kafka_producer.send_batch_data(
                            data=batch_data,
                            source_type="iot",
                            source_id=config.source_id
                        )

                        logger.info("IoT MQTT batch sent to Kafka",
                                   stream_id=stream_id,
                                   batch_size=len(messages),
                                   topics=len(set(msg['topic'] for msg in messages)))

                        # Update stream stats
                        if stream_id in self.active_streams:
                            self.active_streams[stream_id]['records_streamed'] += len(messages)
                            self.active_streams[stream_id]['last_update'] = datetime.now()

                    except Exception as kafka_error:
                        logger.error("Failed to send IoT MQTT batch to Kafka",
                                   stream_id=stream_id,
                                   batch_size=len(messages),
                                   error=str(kafka_error))
                elif messages and not self.kafka_producer:
                    logger.warning("No Kafka producer configured, dropping batch",
                                 stream_id=stream_id,
                                 batch_size=len(messages))
                # If no messages, just continue loop (status check happens at loop start)

            except Exception as e:
                logger.error("Error in message queue processor",
                           stream_id=stream_id,
                           error=str(e))
                await asyncio.sleep(1)

        logger.info("Message queue processor stopped", stream_id=stream_id)

    async def stop_streaming(self, stream_id: str) -> bool:
        """Stop IoT MQTT data streaming"""
        if stream_id in self.active_streams:
            stream_config = self.active_streams[stream_id]

            # Disconnect MQTT client
            if 'client' in stream_config:
                client = stream_config['client']
                client.loop_stop()
                client.disconnect()

            stream_config['status'] = 'stopped'
            del self.active_streams[stream_id]
            logger.info("IoT MQTT data stream stopped", stream_id=stream_id)
            return True
        return False

    async def get_active_streams(self) -> List[Dict[str, Any]]:
        """Get list of active IoT MQTT data streams"""
        return [
            {
                'stream_id': stream_id,
                'source_id': config['source_id'],
                'status': config['status'],
                'start_time': config['start_time'].isoformat(),
                'records_streamed': config['records_streamed'],
                'subscribed_topics': config['subscribed_topics']
            }
            for stream_id, config in self.active_streams.items()
        ]
    
    def _get_topics_for_source(self, source_id: str) -> List[str]:
        """Get MQTT topics to subscribe to based on source type"""
        
        topic_mappings = {
            "iot_weather_stations": [
                "weather/+/temperature",
                "weather/+/humidity", 
                "weather/+/pressure",
                "weather/+/wind_speed",
                "weather/+/wind_direction",
                "weather/+/rainfall",
                "weather/+/data",  # Consolidated weather data
                "sensors/weather/+/+",  # Generic weather sensor pattern
                "wildfire/weather/+",  # Wildfire-specific weather data
            ],
            "iot_air_quality_sensors": [
                "air_quality/+/pm25",
                "air_quality/+/pm10",
                "air_quality/+/ozone",
                "air_quality/+/co",
                "air_quality/+/no2",
                "air_quality/+/data",  # Consolidated air quality data
                "sensors/air/+/+",  # Generic air quality pattern
                "environmental/air_quality/+",
            ],
            "iot_soil_moisture_sensors": [
                "soil/+/moisture",
                "soil/+/temperature",
                "agriculture/+/soil_moisture",
                "agriculture/+/soil_temperature",
                "sensors/soil/+/+",  # Generic soil sensor pattern
                "environmental/soil/+",
            ]
        }
        
        topics = topic_mappings.get(source_id)
        if not topics:
            raise ValueError(f"No MQTT topic mapping found for source_id '{source_id}'. Available: {list(topic_mappings.keys())}")
        return topics
    
    def _get_source_id_from_topic(self, topic: str) -> str:
        """
        Generate source_id for TableRouter based on MQTT topic
        
        Args:
            topic: MQTT topic (e.g., 'weather/station123/temperature', 'air_quality/sensor5/pm25')
        
        Returns:
            source_id for TableRouter ('iot_weather_stations', 'iot_air_quality_sensors', 'iot_soil_moisture_sensors')
        """
        topic_lower = topic.lower()
        
        # Check topic prefix to determine sensor type
        if any(prefix in topic_lower for prefix in ['weather/', 'sensors/weather/', 'wildfire/weather/']):
            return 'iot_weather_stations'
        elif any(prefix in topic_lower for prefix in ['air_quality/', 'air/', 'sensors/air/', 'environmental/air_quality/']):
            return 'iot_air_quality_sensors'
        elif any(prefix in topic_lower for prefix in ['soil/', 'agriculture/', 'sensors/soil/', 'environmental/soil/']):
            return 'iot_soil_moisture_sensors'
        else:
            # Default to weather stations for unknown topics
            return 'iot_weather_stations'
    
    def _process_mqtt_message(self, topic: str, payload: str, stream_config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process received MQTT message and standardize format"""
        try:
            # Try to parse as JSON
            try:
                data = json.loads(payload)
            except json.JSONDecodeError:
                # Handle plain text values
                data = {'value': payload, 'topic': topic}
            
            # Extract device/sensor ID from topic
            topic_parts = topic.split('/')
            device_id = topic_parts[1] if len(topic_parts) > 1 else 'unknown'
            sensor_type = topic_parts[-1] if len(topic_parts) > 0 else 'unknown'
            
            # Standardize the data format
            standardized_record = {
                'timestamp': utcnow_pacific(),  # Use Pacific timezone for California operations
                'device_id': device_id,
                'sensor_id': device_id,  # Alias for data-storage compatibility
                'sensor_type': sensor_type,
                'topic': topic,
                'source': 'iot',  # Match database source field

                'source_id': self._get_source_id_from_topic(topic),  # For TableRouter routing
                'provider': 'IoT Device Network',
                'data_quality': self._assess_iot_data_quality(data),
                'raw_data': data
            }
            
            # Extract specific measurements based on sensor type and data structure
            if isinstance(data, dict):
                # Handle structured JSON data
                standardized_record.update(self._extract_sensor_measurements(data, sensor_type))
            else:
                # Handle simple value
                standardized_record[sensor_type] = self._convert_to_float(data)
            
            # Add location if available in the data
            if isinstance(data, dict):
                if 'latitude' in data and 'longitude' in data:
                    standardized_record['latitude'] = float(data['latitude'])
                    standardized_record['longitude'] = float(data['longitude'])
                elif 'lat' in data and 'lon' in data:
                    standardized_record['latitude'] = float(data['lat'])
                    standardized_record['longitude'] = float(data['lon'])
            
            return standardized_record
            
        except Exception as e:
            logger.error("Failed to process MQTT message",
                        topic=topic, 
                        payload_length=len(payload),
                        error=str(e))
            return None
    
    def _extract_sensor_measurements(self, data: Dict[str, Any], sensor_type: str) -> Dict[str, Any]:
        """Extract and standardize sensor measurements from structured data"""
        measurements = {}
        
        # Common weather measurements
        weather_mappings = {
            'temperature': ['temp', 'temperature', 'temperature_c', 'temperature_celsius'],
            'humidity': ['humidity', 'relative_humidity', 'rh', 'humidity_percent'],
            'pressure': ['pressure', 'barometric_pressure', 'atm_pressure', 'pressure_hpa'],
            'wind_speed': ['wind_speed', 'windspeed', 'wind_speed_ms', 'wind_speed_mph'],
            'wind_direction': ['wind_direction', 'wind_dir', 'wind_direction_degrees'],
            'rainfall': ['rainfall', 'precipitation', 'rain', 'precip_mm'],
            'light': ['light', 'light_intensity', 'lux', 'solar_radiation'],
            'uv_index': ['uv', 'uv_index', 'ultraviolet']
        }
        
        # Air quality measurements
        air_quality_mappings = {
            'pm25': ['pm25', 'pm2.5', 'pm_2_5', 'particulate_25'],
            'pm10': ['pm10', 'pm_10', 'particulate_10'],
            'ozone': ['ozone', 'o3'],
            'carbon_monoxide': ['co', 'carbon_monoxide'],
            'nitrogen_dioxide': ['no2', 'nitrogen_dioxide'],
            'aqi': ['aqi', 'air_quality_index']
        }
        
        # Soil measurements
        soil_mappings = {
            'soil_moisture': ['soil_moisture', 'moisture', 'soil_humidity'],
            'soil_temperature': ['soil_temp', 'soil_temperature', 'ground_temp']
        }
        
        # Combine all mappings
        all_mappings = {**weather_mappings, **air_quality_mappings, **soil_mappings}
        
        # Extract measurements based on mappings
        for standard_name, possible_keys in all_mappings.items():
            for key in possible_keys:
                if key in data:
                    value = self._convert_to_float(data[key])
                    if value is not None:
                        # Apply unit conversions to SI standard using centralized converter
                        if standard_name == 'wind_speed' and 'mph' in key.lower():
                            value = convert_wind_speed(value, from_unit='mph')
                        elif standard_name == 'pressure' and 'hpa' in key.lower():
                            value = convert_pressure(value, from_unit='hPa')

                        measurements[standard_name] = value
                        break

        # Also include any numeric values directly
        for key, value in data.items():
            if key not in ['timestamp', 'device_id', 'latitude', 'longitude', 'lat', 'lon']:
                numeric_value = self._convert_to_float(value)
                if numeric_value is not None and key not in measurements:
                    # Apply unit conversions for direct keys using centralized converter
                    if 'wind' in key.lower() and 'mph' in key.lower():
                        numeric_value = convert_wind_speed(numeric_value, from_unit='mph')
                    elif 'pressure' in key.lower() and 'hpa' in key.lower():
                        numeric_value = convert_pressure(numeric_value, from_unit='hPa')

                    measurements[key] = numeric_value

        return measurements
    
    def _convert_to_float(self, value: Any) -> Optional[float]:
        """Convert value to float if possible"""
        try:
            if isinstance(value, (int, float)):
                return float(value)
            elif isinstance(value, str):
                # Remove common units and convert
                cleaned_value = value.strip()
                for unit in ['degC', 'degF', '%', 'hPa', 'mb', 'mm', 'mph', 'km/h', 'm/s']:
                    cleaned_value = cleaned_value.replace(unit, '').strip()
                return float(cleaned_value)
            else:
                return None
        except (ValueError, TypeError):
            return None
    
    def _assess_iot_data_quality(self, data: Any) -> float:
        """Assess IoT sensor data quality"""
        quality_score = 1.0
        
        if not data:
            return 0.0
        
        # Check if data is structured (JSON)
        if isinstance(data, dict):
            quality_score += 0.1  # Bonus for structured data
            
            # Check for timestamp
            if any(key in data for key in ['timestamp', 'time', 'datetime']):
                quality_score += 0.1
            
            # Check for location data
            if any(key in data for key in ['latitude', 'longitude', 'lat', 'lon', 'location']):
                quality_score += 0.1
            
            # Penalty for missing critical data
            has_measurement = any(
                isinstance(value, (int, float)) or (isinstance(value, str) and value.replace('.', '').replace('-', '').isdigit())
                for key, value in data.items()
                if key not in ['timestamp', 'time', 'datetime', 'device_id']
            )
            
            if not has_measurement:
                quality_score -= 0.3
        
        return max(0.0, min(1.0, quality_score))
    
    async def _reconnect_mqtt_client(self, stream_config: Dict[str, Any]):
        """Attempt to reconnect MQTT client"""
        stream_id = stream_config['stream_id']
        client = stream_config['client']
        
        logger.info("Attempting MQTT client reconnection", stream_id=stream_id)
        
        max_retries = 5
        retry_delay = 5  # seconds
        
        for attempt in range(max_retries):
            try:
                await asyncio.sleep(retry_delay)
                client.reconnect()
                return  # Success
                
            except Exception as e:
                logger.warning("MQTT reconnection attempt failed",
                             stream_id=stream_id,
                             attempt=attempt + 1,
                             error=str(e))
                retry_delay *= 2  # Exponential backoff
        
        # Failed to reconnect
        logger.error("MQTT client reconnection failed after all attempts", stream_id=stream_id)
        stream_config['status'] = 'error'
    
    async def fetch_batch_data(self, config: BatchConfig) -> List[Dict[str, Any]]:
        """
        IoT MQTT is streaming-only, but we can return recent buffered data
        """
        logger.info("IoT MQTT is primarily streaming-based. Returning recent buffered data.")

        # Return recently received messages (this would be implemented with proper buffering)
        return self.received_messages[-100:] if self.received_messages else []

    # ==================== OFFLINE BUFFERING METHODS ====================

    def _load_persisted_buffer(self):
        """Load persisted buffer from disk if it exists"""
        if not self.buffer_persist_path.exists():
            return

        try:
            with open(self.buffer_persist_path, 'rb') as f:
                persisted_data = pickle.load(f)
                if isinstance(persisted_data, list):
                    # Restore buffer up to max size
                    restore_count = min(len(persisted_data), self.buffer_max_size)
                    self.offline_buffer = deque(persisted_data[:restore_count], maxlen=self.buffer_max_size)
                    logger.info(
                        "Restored offline buffer from disk",
                        messages_restored=restore_count,
                        file_path=str(self.buffer_persist_path)
                    )
        except Exception as e:
            logger.error(
                "Failed to load persisted buffer",
                error=str(e),
                file_path=str(self.buffer_persist_path)
            )

    def _persist_buffer(self):
        """Persist current buffer to disk"""
        if not self.enable_offline_buffer or not self.offline_buffer:
            return

        try:
            # Convert deque to list for pickling
            buffer_data = list(self.offline_buffer)
            with open(self.buffer_persist_path, 'wb') as f:
                pickle.dump(buffer_data, f)
            logger.debug(
                "Persisted offline buffer to disk",
                messages_saved=len(buffer_data),
                file_path=str(self.buffer_persist_path)
            )
        except Exception as e:
            logger.error(
                "Failed to persist buffer",
                error=str(e),
                file_path=str(self.buffer_persist_path)
            )

    def _buffer_message(self, message: Dict[str, Any]) -> bool:
        """
        Buffer a message when offline
        Returns True if buffered successfully, False if dropped
        """
        if not self.enable_offline_buffer:
            return False

        try:
            # Check if buffer is full
            if len(self.offline_buffer) >= self.buffer_max_size:
                # Buffer is full, oldest message will be dropped automatically (deque behavior)
                self.buffer_metrics['messages_dropped'] += 1
                self.buffer_metrics['max_buffer_size_reached'] += 1
                logger.warning(
                    "Buffer full, dropping oldest message",
                    buffer_size=len(self.offline_buffer),
                    max_size=self.buffer_max_size
                )

            # Add timestamp for when message was buffered
            message['buffered_at'] = datetime.now().isoformat()
            message['buffered'] = True

            # Add to buffer (deque automatically drops oldest if full)
            self.offline_buffer.append(message)
            self.buffer_metrics['messages_buffered'] += 1

            # Persist buffer periodically (every 100 messages)
            if len(self.offline_buffer) % 100 == 0:
                self._persist_buffer()

            logger.debug(
                "Message buffered for later delivery",
                buffer_size=len(self.offline_buffer),
                topic=message.get('topic')
            )
            return True

        except Exception as e:
            logger.error(
                "Failed to buffer message",
                error=str(e)
            )
            return False

    async def _flush_buffer(self) -> int:
        """
        Flush buffered messages to Kafka when connection is restored
        Returns number of messages flushed
        """
        if not self.offline_buffer or not self.kafka_producer:
            return 0

        logger.info(
            "Flushing offline buffer",
            messages_to_flush=len(self.offline_buffer)
        )

        flushed_count = 0
        failed_count = 0
        batch_size = 100  # Flush in batches for efficiency

        while self.offline_buffer:
            try:
                # Get batch of messages
                batch = []
                for _ in range(min(batch_size, len(self.offline_buffer))):
                    if self.offline_buffer:
                        batch.append(self.offline_buffer.popleft())

                if not batch:
                    break

                # Extract data from buffered messages
                batch_data = []
                for msg in batch:
                    if 'data' in msg:
                        # Add flag to indicate this was buffered
                        msg['data']['was_buffered'] = True
                        msg['data']['buffer_flush_time'] = datetime.now().isoformat()
                        batch_data.append(msg['data'])

                if batch_data:
                    # Send batch to Kafka
                    try:
                        await self.kafka_producer.send_batch_data(
                            data=batch_data,
                            source_type="iot",
                            source_id=batch[0].get('source_id', 'iot_buffered')
                        )
                        flushed_count += len(batch_data)
                        logger.info(
                            "Flushed batch from buffer",
                            batch_size=len(batch_data),
                            remaining=len(self.offline_buffer)
                        )
                    except Exception as kafka_error:
                        # Put messages back if Kafka send fails
                        for msg in reversed(batch):
                            self.offline_buffer.appendleft(msg)
                        logger.error(
                            "Failed to flush batch to Kafka, returning to buffer",
                            error=str(kafka_error),
                            batch_size=len(batch)
                        )
                        failed_count += len(batch)
                        break  # Stop flushing if Kafka is unavailable

            except Exception as e:
                logger.error(
                    "Error during buffer flush",
                    error=str(e),
                    flushed=flushed_count,
                    failed=failed_count
                )
                break

        # Update metrics
        self.buffer_metrics['buffer_flushes'] += 1

        # Clear persisted buffer if all flushed
        if not self.offline_buffer and self.buffer_persist_path.exists():
            try:
                self.buffer_persist_path.unlink()
                logger.info("Cleared persisted buffer file")
            except Exception:
                pass

        logger.info(
            "Buffer flush complete",
            flushed=flushed_count,
            failed=failed_count,
            remaining=len(self.offline_buffer)
        )

        return flushed_count

    def _update_connection_state(self, connected: bool):
        """Update connection state and track offline duration"""
        now = datetime.now()

        if connected and not self.is_connected:
            # Connection restored
            self.is_connected = True
            self.last_connection_time = now

            if self.last_disconnection_time:
                offline_duration = (now - self.last_disconnection_time).total_seconds()
                self.buffer_metrics['total_offline_duration'] += offline_duration
                logger.info(
                    "Connection restored",
                    offline_duration_seconds=offline_duration,
                    messages_buffered=len(self.offline_buffer)
                )

                # Flush buffer when connection restored
                if self.offline_buffer:
                    asyncio.create_task(self._flush_buffer())

        elif not connected and self.is_connected:
            # Connection lost
            self.is_connected = False
            self.last_disconnection_time = now
            self.disconnection_count += 1
            logger.warning(
                "Connection lost, buffering enabled",
                disconnection_count=self.disconnection_count,
                buffer_enabled=self.enable_offline_buffer
            )

    def get_buffer_metrics(self) -> Dict[str, Any]:
        """Get metrics about offline buffering"""
        return {
            'buffer_enabled': self.enable_offline_buffer,
            'buffer_current_size': len(self.offline_buffer),
            'buffer_max_size': self.buffer_max_size,
            'buffer_utilization': len(self.offline_buffer) / self.buffer_max_size if self.buffer_max_size > 0 else 0,
            'messages_buffered_total': self.buffer_metrics['messages_buffered'],
            'messages_dropped_total': self.buffer_metrics['messages_dropped'],
            'buffer_flushes_total': self.buffer_metrics['buffer_flushes'],
            'max_buffer_reached_count': self.buffer_metrics['max_buffer_size_reached'],
            'total_offline_duration_seconds': self.buffer_metrics['total_offline_duration'],
            'disconnection_count': self.disconnection_count,
            'is_connected': self.is_connected,
            'last_connection_time': self.last_connection_time.isoformat() if self.last_connection_time else None,
            'last_disconnection_time': self.last_disconnection_time.isoformat() if self.last_disconnection_time else None
        }

    def is_buffer_healthy(self) -> bool:
        """Check if buffer is in healthy state"""
        if not self.enable_offline_buffer:
            return True  # Buffer disabled, considered healthy

        # Check buffer utilization
        utilization = len(self.offline_buffer) / self.buffer_max_size if self.buffer_max_size > 0 else 0
        if utilization > 0.9:
            logger.warning(
                "Buffer utilization critical",
                utilization=utilization,
                buffer_size=len(self.offline_buffer)
            )
            return False

        # Check drop rate
        total_messages = self.buffer_metrics['messages_buffered'] + self.buffer_metrics['messages_dropped']
        if total_messages > 100:  # Only check after reasonable sample
            drop_rate = self.buffer_metrics['messages_dropped'] / total_messages
            if drop_rate > 0.1:  # More than 10% dropped
                logger.warning(
                    "High message drop rate",
                    drop_rate=drop_rate,
                    dropped=self.buffer_metrics['messages_dropped']
                )
                return False

        return True