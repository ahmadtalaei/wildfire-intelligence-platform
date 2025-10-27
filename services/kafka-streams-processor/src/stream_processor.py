"""
Advanced Kafka Streams Processor for Wildfire Intelligence Platform
Implements stateful stream processing with complex event correlation
"""

import os
import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum

import numpy as np
from confluent_kafka import Consumer, Producer, KafkaError
from confluent_kafka.avro import AvroProducer, AvroConsumer
from confluent_kafka.schema_registry import SchemaRegistryClient
import rocksdb
import redis
from prometheus_client import Counter, Histogram, Gauge, start_http_server
import uvloop

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Metrics
EVENTS_PROCESSED = Counter('kafka_streams_events_processed', 'Total events processed', ['topic', 'processor'])
PROCESSING_TIME = Histogram('kafka_streams_processing_time_seconds', 'Processing time', ['processor'])
STATE_STORE_SIZE = Gauge('kafka_streams_state_store_size_bytes', 'State store size')
WINDOWS_CREATED = Counter('kafka_streams_windows_created', 'Time windows created', ['window_type'])
ANOMALIES_DETECTED = Counter('kafka_streams_anomalies_detected', 'Anomalies detected', ['severity'])
CORRELATIONS_FOUND = Counter('kafka_streams_correlations_found', 'Event correlations found')

class FireEventType(Enum):
    """Types of fire-related events"""
    DETECTION = "fire_detection"
    WEATHER_UPDATE = "weather_update"
    SENSOR_READING = "sensor_reading"
    EVACUATION_ORDER = "evacuation_order"
    RESOURCE_DISPATCH = "resource_dispatch"

@dataclass
class FireEvent:
    """Unified fire event model"""
    event_id: str
    event_type: FireEventType
    timestamp: datetime
    location: Tuple[float, float]  # (latitude, longitude)
    severity: float  # 0.0 to 1.0
    confidence: float  # 0.0 to 1.0
    source: str
    data: Dict[str, Any]

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            **asdict(self),
            'event_type': self.event_type.value,
            'timestamp': self.timestamp.isoformat(),
            'location': list(self.location)
        }

class StateStore:
    """RocksDB-backed state store for fault-tolerant processing"""

    def __init__(self, path: str = "/var/kafka-streams/state"):
        """Initialize RocksDB state store"""
        self.path = path
        os.makedirs(path, exist_ok=True)

        # Configure RocksDB for optimal performance
        opts = rocksdb.Options()
        opts.create_if_missing = True
        opts.max_open_files = 300000
        opts.write_buffer_size = 67108864  # 64MB
        opts.max_write_buffer_number = 3
        opts.target_file_size_base = 67108864

        # Enable compression
        opts.compression = rocksdb.CompressionType.zstd_compression

        # Bloom filter for faster lookups
        opts.table_factory = rocksdb.BlockBasedTableFactory(
            filter_policy=rocksdb.BloomFilterPolicy(10),
            block_cache=rocksdb.LRUCache(2 * 1024 * 1024 * 1024),  # 2GB cache
            block_cache_compressed=rocksdb.LRUCache(500 * 1024 * 1024)  # 500MB compressed cache
        )

        self.db = rocksdb.DB(f"{path}/main", opts)
        self.windows = rocksdb.DB(f"{path}/windows", opts)

        # Track state store size
        self._update_metrics()

    def _update_metrics(self):
        """Update state store metrics"""
        try:
            size = sum(os.path.getsize(os.path.join(dirpath, filename))
                      for dirpath, _, filenames in os.walk(self.path)
                      for filename in filenames)
            STATE_STORE_SIZE.set(size)
        except Exception as e:
            logger.error(f"Error updating metrics: {e}")

    def put(self, key: str, value: Dict) -> None:
        """Store key-value pair"""
        self.db.put(key.encode(), json.dumps(value).encode())
        self._update_metrics()

    def get(self, key: str) -> Optional[Dict]:
        """Retrieve value by key"""
        value = self.db.get(key.encode())
        return json.loads(value.decode()) if value else None

    def put_window(self, window_key: str, events: List[Dict]) -> None:
        """Store events in a time window"""
        self.windows.put(window_key.encode(), json.dumps(events).encode())
        WINDOWS_CREATED.labels(window_type='tumbling').inc()

    def get_window(self, window_key: str) -> List[Dict]:
        """Retrieve events from a time window"""
        value = self.windows.get(window_key.encode())
        return json.loads(value.decode()) if value else []

    def scan_windows(self, start_time: datetime, end_time: datetime) -> Dict[str, List[Dict]]:
        """Scan windows within time range"""
        results = {}
        it = self.windows.iterator()

        for key, value in it:
            window_key = key.decode()
            # Parse timestamp from window key
            if window_key.startswith("window_"):
                window_time = datetime.fromisoformat(window_key.split("_")[1])
                if start_time <= window_time <= end_time:
                    results[window_key] = json.loads(value.decode())

        return results

class ComplexEventProcessor:
    """Advanced stream processing with complex event correlation"""

    def __init__(self, state_store: StateStore):
        self.state_store = state_store
        self.redis_client = redis.Redis(
            host=os.getenv('REDIS_HOST', 'redis'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            decode_responses=True
        )

    async def process_fire_detection(self, event: FireEvent) -> Optional[Dict]:
        """Process fire detection with correlation to weather and sensors"""
        with PROCESSING_TIME.labels(processor='fire_detection').time():
            # Check for nearby weather conditions
            weather_key = f"weather_{event.location[0]:.2f}_{event.location[1]:.2f}"
            weather_data = self.state_store.get(weather_key)

            # Check for nearby sensor readings
            sensor_pattern = f"sensor_{event.location[0]:.1f}_{event.location[1]:.1f}_*"
            sensor_data = self._get_nearby_sensors(sensor_pattern)

            # Correlate events
            correlation_score = self._calculate_correlation(event, weather_data, sensor_data)

            if correlation_score > 0.7:
                CORRELATIONS_FOUND.inc()

                # Generate enhanced fire alert
                alert = {
                    'alert_type': 'correlated_fire_detection',
                    'fire_event': event.to_dict(),
                    'weather_conditions': weather_data,
                    'sensor_readings': sensor_data,
                    'correlation_score': correlation_score,
                    'risk_level': self._calculate_risk_level(event, weather_data),
                    'recommended_actions': self._generate_recommendations(event, weather_data, sensor_data),
                    'timestamp': datetime.utcnow().isoformat()
                }

                # Store in state for future correlations
                self.state_store.put(f"fire_{event.event_id}", alert)

                # Check for anomalies
                if self._is_anomaly(event, weather_data, sensor_data):
                    severity = 'high' if correlation_score > 0.9 else 'medium'
                    ANOMALIES_DETECTED.labels(severity=severity).inc()
                    alert['anomaly_detected'] = True
                    alert['anomaly_reason'] = self._get_anomaly_reason(event, weather_data, sensor_data)

                return alert

            return None

    def _calculate_correlation(self, event: FireEvent, weather: Optional[Dict], sensors: List[Dict]) -> float:
        """Calculate correlation score between fire detection and other data sources"""
        score = event.confidence

        if weather:
            # High temperature and low humidity increase correlation
            temp = weather.get('temperature', 20)
            humidity = weather.get('humidity', 50)
            wind_speed = weather.get('wind_speed', 0)

            if temp > 30 and humidity < 30:
                score += 0.2
            if wind_speed > 20:
                score += 0.1

        if sensors:
            # Check for smoke/heat detection from IoT sensors
            for sensor in sensors:
                if sensor.get('smoke_detected') or sensor.get('temperature', 0) > 40:
                    score += 0.15
                    break

        return min(score, 1.0)

    def _calculate_risk_level(self, event: FireEvent, weather: Optional[Dict]) -> str:
        """Calculate fire risk level based on conditions"""
        risk_score = event.severity

        if weather:
            # Incorporate fire weather index calculations
            temp = weather.get('temperature', 20)
            humidity = weather.get('humidity', 50)
            wind_speed = weather.get('wind_speed', 0)

            # Simplified Fosberg Fire Weather Index
            fwi = ((110 - 1.373 * humidity - 0.54 * (10.20 - temp)) *
                   (124 * 10**(-0.0142 * humidity))) / 60

            if fwi > 50:
                risk_score += 0.3

            # Wind effect on spread
            if wind_speed > 30:
                risk_score += 0.2

        if risk_score > 0.8:
            return 'extreme'
        elif risk_score > 0.6:
            return 'high'
        elif risk_score > 0.4:
            return 'moderate'
        else:
            return 'low'

    def _generate_recommendations(self, event: FireEvent, weather: Optional[Dict], sensors: List[Dict]) -> List[str]:
        """Generate actionable recommendations based on conditions"""
        recommendations = []

        risk_level = self._calculate_risk_level(event, weather)

        if risk_level in ['extreme', 'high']:
            recommendations.append("Immediate evacuation of areas within 5km radius")
            recommendations.append("Deploy aerial firefighting resources")
            recommendations.append("Activate emergency response teams")

        if weather and weather.get('wind_speed', 0) > 20:
            recommendations.append(f"Prepare for rapid spread in {weather.get('wind_direction', 'unknown')} direction")

        if sensors and any(s.get('smoke_detected') for s in sensors):
            recommendations.append("Issue air quality warnings")
            recommendations.append("Distribute N95 masks to affected populations")

        return recommendations

    def _get_nearby_sensors(self, pattern: str) -> List[Dict]:
        """Retrieve nearby sensor data from state store"""
        # Implementation would scan state store for matching keys
        # Simplified for demonstration
        return []

    def _is_anomaly(self, event: FireEvent, weather: Optional[Dict], sensors: List[Dict]) -> bool:
        """Detect anomalous fire behavior"""
        # Check for unusual patterns
        if event.severity > 0.9 and not weather:
            return True  # High severity fire with no weather data

        if weather and weather.get('humidity', 0) > 80 and event.severity > 0.7:
            return True  # Fire in high humidity conditions

        return False

    def _get_anomaly_reason(self, event: FireEvent, weather: Optional[Dict], sensors: List[Dict]) -> str:
        """Determine reason for anomaly"""
        if event.severity > 0.9 and not weather:
            return "High severity fire detection with missing weather data"

        if weather and weather.get('humidity', 0) > 80:
            return f"Fire detected in high humidity conditions ({weather.get('humidity')}%)"

        return "Unusual fire behavior pattern detected"

class WindowedAggregator:
    """Time-windowed aggregation for stream processing"""

    def __init__(self, state_store: StateStore, window_size_ms: int = 60000):
        self.state_store = state_store
        self.window_size_ms = window_size_ms

    def add_to_window(self, event: FireEvent) -> None:
        """Add event to current time window"""
        window_start = self._get_window_start(event.timestamp)
        window_key = f"window_{window_start.isoformat()}_{event.location[0]:.1f}_{event.location[1]:.1f}"

        # Get existing window data
        window_events = self.state_store.get_window(window_key)
        window_events.append(event.to_dict())

        # Update window
        self.state_store.put_window(window_key, window_events)

    def _get_window_start(self, timestamp: datetime) -> datetime:
        """Calculate window start time"""
        window_size_seconds = self.window_size_ms / 1000
        epoch = datetime(1970, 1, 1)
        seconds_since_epoch = (timestamp - epoch).total_seconds()
        window_number = int(seconds_since_epoch / window_size_seconds)
        window_start_seconds = window_number * window_size_seconds
        return epoch + timedelta(seconds=window_start_seconds)

    def compute_aggregates(self, window_key: str) -> Dict:
        """Compute aggregates for a window"""
        events = self.state_store.get_window(window_key)

        if not events:
            return {}

        # Calculate statistics
        severities = [e['severity'] for e in events]
        confidences = [e['confidence'] for e in events]

        aggregates = {
            'window_key': window_key,
            'event_count': len(events),
            'avg_severity': np.mean(severities),
            'max_severity': np.max(severities),
            'min_severity': np.min(severities),
            'std_severity': np.std(severities),
            'avg_confidence': np.mean(confidences),
            'event_types': list(set(e['event_type'] for e in events)),
            'sources': list(set(e['source'] for e in events)),
            'timestamp': datetime.utcnow().isoformat()
        }

        # Detect patterns
        if aggregates['event_count'] > 10 and aggregates['avg_severity'] > 0.7:
            aggregates['pattern'] = 'major_fire_event'
        elif aggregates['std_severity'] > 0.3:
            aggregates['pattern'] = 'variable_conditions'

        return aggregates

class KafkaStreamsProcessor:
    """Main Kafka Streams processor with exactly-once semantics"""

    def __init__(self):
        self.state_store = StateStore()
        self.event_processor = ComplexEventProcessor(self.state_store)
        self.aggregator = WindowedAggregator(self.state_store)

        # Schema Registry client
        self.schema_registry = SchemaRegistryClient({
            'url': os.getenv('SCHEMA_REGISTRY_URL', 'http://schema-registry:8081')
        })

        # Configure consumer with exactly-once semantics
        self.consumer = Consumer({
            'bootstrap.servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:29092'),
            'group.id': os.getenv('APPLICATION_ID', 'wildfire-stream-processor'),
            'enable.auto.commit': False,
            'auto.offset.reset': 'earliest',
            'isolation.level': 'read_committed',
            'session.timeout.ms': 30000,
            'heartbeat.interval.ms': 3000,
            'max.poll.interval.ms': 300000
        })

        # Configure producer with exactly-once semantics
        self.producer = Producer({
            'bootstrap.servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:29092'),
            'transactional.id': f"{os.getenv('APPLICATION_ID')}-producer",
            'enable.idempotence': True,
            'acks': 'all',
            'compression.type': 'zstd',
            'batch.size': 32768,
            'linger.ms': 100
        })

        # Initialize transactional producer
        self.producer.init_transactions()

        # Subscribe to topics
        input_topics = os.getenv('INPUT_TOPICS', '').split(',')
        self.consumer.subscribe(input_topics)

        logger.info(f"Kafka Streams Processor initialized. Subscribed to: {input_topics}")

    async def process_message(self, message) -> Optional[Dict]:
        """Process a single message with complex event processing"""
        try:
            # Parse message
            value = json.loads(message.value().decode('utf-8'))

            # Create FireEvent
            event = FireEvent(
                event_id=value.get('id', message.key().decode('utf-8')),
                event_type=FireEventType(value.get('type', 'fire_detection')),
                timestamp=datetime.fromisoformat(value.get('timestamp', datetime.utcnow().isoformat())),
                location=(value.get('latitude', 0), value.get('longitude', 0)),
                severity=value.get('severity', 0.5),
                confidence=value.get('confidence', 0.8),
                source=value.get('source', 'unknown'),
                data=value
            )

            # Add to time window
            self.aggregator.add_to_window(event)

            # Process based on event type
            result = None
            if event.event_type == FireEventType.DETECTION:
                result = await self.event_processor.process_fire_detection(event)
            elif event.event_type == FireEventType.WEATHER_UPDATE:
                # Store weather data for correlation
                weather_key = f"weather_{event.location[0]:.2f}_{event.location[1]:.2f}"
                self.state_store.put(weather_key, event.data)
            elif event.event_type == FireEventType.SENSOR_READING:
                # Store sensor data for correlation
                sensor_key = f"sensor_{event.location[0]:.1f}_{event.location[1]:.1f}_{event.event_id}"
                self.state_store.put(sensor_key, event.data)

            # Update metrics
            EVENTS_PROCESSED.labels(
                topic=message.topic(),
                processor='kafka_streams'
            ).inc()

            return result

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return None

    async def run(self):
        """Main processing loop with exactly-once semantics"""
        logger.info("Starting Kafka Streams Processor...")

        # Start metrics server
        start_http_server(8090)

        try:
            while True:
                # Poll for messages
                messages = self.consumer.poll(timeout=1.0)

                if not messages:
                    continue

                # Begin transaction
                self.producer.begin_transaction()

                try:
                    # Process batch of messages
                    for topic_partition, msgs in messages.items():
                        for msg in msgs:
                            if msg.error():
                                logger.error(f"Consumer error: {msg.error()}")
                                continue

                            # Process message
                            result = await self.process_message(msg)

                            if result:
                                # Produce to output topic
                                output_topic = os.getenv('OUTPUT_TOPIC', 'wildfire-processed-events')
                                self.producer.produce(
                                    topic=output_topic,
                                    key=msg.key(),
                                    value=json.dumps(result).encode('utf-8')
                                )

                    # Send offsets to transaction
                    self.producer.send_offsets_to_transaction(
                        self.consumer.position(self.consumer.assignment()),
                        self.consumer.consumer_group_metadata()
                    )

                    # Commit transaction
                    self.producer.commit_transaction()

                    # Commit consumer offsets
                    self.consumer.commit()

                except Exception as e:
                    logger.error(f"Error in transaction: {e}")
                    self.producer.abort_transaction()

        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            self.consumer.close()
            logger.info("Kafka Streams Processor stopped")

async def main():
    """Main entry point"""
    # Use uvloop for better async performance
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

    processor = KafkaStreamsProcessor()
    await processor.run()

if __name__ == "__main__":
    asyncio.run(main())