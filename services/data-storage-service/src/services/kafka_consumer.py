"""
Kafka Consumer Service for Data Storage - FULLY INSTRUMENTED VERSION
Consumes streaming data from Kafka topics and stores to PostgreSQL with extensive logging

This service bridges the gap between Kafka streaming and persistent storage:
- Consumes from wildfire-nasa-firms, wildfire-weather-data, wildfire-sensor-data topics
- Transforms and validates data according to PostgreSQL schema
- Stores fire incidents, weather data, and sensor readings
- Handles retries and error recovery
- FULLY INSTRUMENTED FOR DEBUGGING MESSAGE PROCESSING FAILURES


This script is essentially a **fully-instrumented Kafka consumer service** designed to reliably consume wildfire-related streaming data and store it in a PostgreSQL database. Here's a detailed explanation:

---

## **1. Purpose**

The service acts as a bridge between **Kafka streaming topics** and **persistent storage**:

* Consumes messages from topics like:

  * `wildfire-nasa-firms` (fire detections)
  * `wildfire-weather-data` (weather readings)
  * `wildfire-sensor-data` (IoT sensor readings)
  * Satellite or imagery topics (`wildfire-satellite-data`, `wildfire-satellite-imagery`)
* Validates and transforms messages to match PostgreSQL schemas.
* Stores processed data in corresponding database tables.
* Fully instrumented for debugging, with detailed logging at every step.

---

## **2. Core Classes**

### **2.1 KafkaDataConsumer**

The main class responsible for consuming and processing Kafka messages.

**Key components:**

* **Initialization (`__init__`)**

  * Accepts a `DatabaseManager` instance for DB operations.
  * Sets Kafka topics and maps them to their respective handlers (`_handle_fire_detection`, `_handle_weather_data`, `_handle_sensor_data`, etc.).
  * Configurable `auto_offset_reset` (`earliest` by default) controls where the consumer starts reading in Kafka if offsets are missing.

* **Starting (`start`)**

  * Connects to Kafka with **retry logic** (max 5 attempts with exponential backoff).
  * Launches `_consume_messages()` loop after connection.

* **Stopping (`stop`)**

  * Gracefully stops the consumer.

* **Message Consumption (`_consume_messages`)**

  * Loops over Kafka messages asynchronously.
  * Logs every message extensively (topic, partition, offset, key, timestamp, size, snippet of data).
  * Tries to parse JSON payloads, handles decoding errors.
  * Routes messages to the appropriate handler based on topic.
  * Tracks statistics: total messages, successful, failed, and logs periodically.

---

## **3. Data Handlers**

Each topic has a handler method that validates, transforms, and stores data.

### **3.1 Fire Detection (`_handle_fire_detection`)**

* Handles NASA FIRMS fire detection messages.
* Processes nested structures in JSON.
* Stores each fire incident in `fire_incidents` table.
* Uses `_store_fire_incident()` for PostgreSQL insertion.
* Robust timestamp parsing (`_parse_sophisticated_timestamp`) from `acq_date` + `acq_time` fields.

### **3.2 Weather Data (`_handle_weather_data`)**

* Handles NOAA/weather messages.
* Extracts relevant fields like temperature, humidity, wind, pressure, timestamp.
* Stores each record in `weather_data` table.
* Uses `_store_weather_record()` with dynamic insert based on table schema.

### **3.3 Sensor Data (`_handle_sensor_data`)**

* Handles IoT sensor messages.
* Extracts readings, processes timestamp, and stores in `sensor_readings` table.
* `_store_sensor_record()` ensures only mapped/nullable columns are inserted.

### **3.4 Satellite Data (`_handle_satellite_data` / `_handle_satellite_imagery`)**

* Currently logs messages without DB storage.
* Can be extended to store satellite imagery or general satellite data in future tables.

---

## **4. Timestamp Parsing**

* `_parse_timestamp()` and `_parse_sophisticated_timestamp()` handle multiple formats:

  * ISO timestamps (`2025-09-22T12:00:00Z`)
  * NASA FIRMS format (`acq_date` + `acq_time`)
  * Fallback to current UTC time if parsing fails

---

## **5. Database Interaction**

* Uses `DatabaseManager` for PostgreSQL connections.
* Dynamically queries table schemas (`information_schema.columns`) to ensure proper insertion.
* Handles:

  * Required columns (`id`, `reading_id`, `incident_id`)
  * Nullable columns
  * Default values for missing data (e.g., `wind_direction=0.0`, `pressure=1013.25`)
* Each insertion logs every detail:

  * Values, types, query, and success/failure.

---

## **6. KafkaConsumerManager**

* A **wrapper class** for lifecycle management:

  * Starts/stops the consumer asynchronously.
  * Maintains background task (`asyncio.create_task`) for the consumer loop.
  * Provides `is_running()` method to check status.

---

## **7. Logging / Instrumentation**

* Uses `structlog` for structured logging.
* Logs every step of message processing:

  * Reception
  * JSON parsing
  * Routing to handler
  * DB insertion
  * Errors and retries
* Includes previews of raw data for debugging.
* Maintains detailed statistics for monitoring message processing rates.

---

## **8. Summary Flow**

1. `KafkaConsumerManager.start()` → creates a `KafkaDataConsumer` instance.
2. `_consume_messages()` asynchronously iterates over Kafka messages.
3. For each message:

   * Parse JSON
   * Route to handler
   * Transform & validate data
   * Store in PostgreSQL
   * Log successes/failures
4. `_store_*` methods dynamically insert into DB based on schema.
5. Supports stopping the consumer gracefully via `stop()`.

"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
import structlog

from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaError
from ..models.database import DatabaseManager
from ..config import get_settings
from ..utils.table_router import TableRouter
import time
import hashlib
from collections import deque
from .consumer_metrics import (
    MESSAGES_CONSUMED_TOTAL, MESSAGES_PROCESSED_SUCCESS, MESSAGES_PROCESSED_FAILED,
    MESSAGE_PROCESSING_LATENCY, DB_INSERT_SUCCESS, DB_INSERT_FAILED, RECORDS_INGESTED_SUCCESS,
    INGESTION_THROUGHPUT, INGESTION_FAILED, DUPLICATE_DETECTIONS, DATA_QUALITY_SCORE,
    ANOMALIES_DETECTED, KAFKA_CONSUMER_LAG
)

logger = structlog.get_logger()

class KafkaDataConsumer:
    """
    Kafka Consumer for streaming data storage with comprehensive instrumentation

    Consumes messages from Kafka topics and stores to PostgreSQL
    with proper data transformation and error handling.
    """

    def __init__(self, db_manager: DatabaseManager, auto_offset_reset: str = None):
        self.db_manager = db_manager
        self.settings = get_settings()
        self.consumer = None
        self.running = False
        self.auto_offset_reset = auto_offset_reset or self.settings.kafka_auto_offset_reset

        # Duplicate detection - keep last 10000 message hashes
        self.recent_message_hashes = deque(maxlen=10000)

        # Initialize metrics with zero values so they exist for dashboard queries
        # This ensures Prometheus queries work even when no failures/duplicates/anomalies have occurred
        INGESTION_FAILED.labels(source='_init', error_type='none', job='data-ingestion-service')
        DUPLICATE_DETECTIONS.labels(source='_init', job='data-ingestion-service')
        ANOMALIES_DETECTED.labels(source='_init', anomaly_type='none', job='data-ingestion-service')

        # Topic to database table mapping - RE-ENABLED NOAA WEATHER WITH VALIDATION FIX
        self.topic_handlers = {
            'wildfire-nasa-firms': self._handle_fire_detection,
            'wildfire-weather-data': self._handle_weather_data,  # ✅ RE-ENABLED with vectorized validation
            'wildfire-weather-alerts': self._handle_weather_data,  # ✅ RE-ENABLED
            'wildfire-weather-stations': self._handle_weather_data,  # ✅ NEW: Dedicated station observations topic
            'wildfire-weather-bulk': self._handle_weather_data,  # ✅ RE-ENABLED
            # 'wildfire-sensor-data': self._handle_sensor_data,  # TODO: Add validation
            # 'wildfire-iot-sensors': self._handle_sensor_data,  # TODO: Add validation
            # 'wildfire-satellite-data': self._handle_satellite_data,  # TODO: Add validation
            # 'wildfire-satellite-imagery': self._handle_satellite_imagery,  # TODO: Add validation
            # 'wildfire-incidents': self._handle_fire_detection,  # TODO: Add validation
            # 'wildfire-weather-gfs': self._handle_weather_data,  # Disabled: old topic with snappy messages
        }

    async def start(self):
        """Start Kafka consumer with retry logic"""
        print("=== KAFKA DATA CONSUMER START() CALLED ===")
        import asyncio

        max_retries = 5
        retry_delay = 5

        for attempt in range(max_retries):
            print(f"=== KAFKA CONSUMER START ATTEMPT {attempt + 1}/{max_retries} ===")
            try:
                logger.info(f"🔄 KAFKA CONSUMER START ATTEMPT {attempt + 1}/{max_retries}")

                # Initialize Kafka consumer
                print(f"=== CREATING AIOKafkaConsumer with auto_offset_reset={self.auto_offset_reset} ===")
                self.consumer = AIOKafkaConsumer(
                    *self.topic_handlers.keys(),
                    bootstrap_servers=self.settings.kafka_bootstrap_servers,
                    group_id=self.settings.kafka_consumer_group_id,
                    value_deserializer=lambda m: json.loads(m.decode('utf-8')) if m else None,
                    auto_offset_reset=self.auto_offset_reset,
                    enable_auto_commit=True,
                    auto_commit_interval_ms=5000,
                    # Performance optimizations for faster throughput
                    max_poll_records=1000,
                    fetch_max_bytes=104857600,
                    fetch_max_wait_ms=300,
                    max_partition_fetch_bytes=20971520
                )

                logger.info(f"🌟 CONNECTING TO KAFKA: {self.settings.kafka_bootstrap_servers}")
                await self.consumer.start()
                self.running = True

                # CRITICAL: Wait for partition assignment
                print("=== WAITING FOR PARTITION ASSIGNMENT ===")
                assignment_timeout = 30  # seconds
                start_wait = asyncio.get_event_loop().time()
                while not self.consumer.assignment():
                    if asyncio.get_event_loop().time() - start_wait > assignment_timeout:
                        print(f"=== PARTITION ASSIGNMENT TIMEOUT after {assignment_timeout}s ===")
                        break
                    await asyncio.sleep(0.5)

                assigned_partitions = self.consumer.assignment()
                print(f"=== ASSIGNED PARTITIONS: {assigned_partitions} ===")
                logger.info("✅ KAFKA CONSUMER STARTED SUCCESSFULLY", assigned_partitions=len(assigned_partitions))
                break

            except Exception as e:
                logger.error(f"❌ KAFKA CONSUMER START ATTEMPT {attempt + 1} FAILED",
                           error=str(e),
                           error_type=type(e).__name__)

                if attempt < max_retries - 1:
                    logger.info(f"⏳ WAITING {retry_delay}s BEFORE RETRY {attempt + 2}/{max_retries}")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    logger.error("💥 KAFKA CONSUMER FAILED TO START AFTER ALL RETRIES")
                    raise

        logger.info("Kafka consumer started",
                   topics=list(self.topic_handlers.keys()),
                   bootstrap_servers=self.settings.kafka_bootstrap_servers)

        # Start consuming messages
        print("=== ABOUT TO CALL _consume_messages() ===")
        await self._consume_messages()
        print("=== _consume_messages() COMPLETED (SHOULD NEVER REACH HERE) ===")

    async def stop(self):
        """Stop Kafka consumer"""
        self.running = False
        if self.consumer:
            await self.consumer.stop()
            logger.info("Kafka consumer stopped")

    async def _consume_messages(self):
        """Main message consumption loop with detailed instrumentation"""
        print("=== _consume_messages() FUNCTION ENTERED ===")
        logger.info("🚀 STARTING MESSAGE CONSUMPTION LOOP WITH FULL INSTRUMENTATION",
                   consumer_group_id='data-storage-consumer',
                   topics=list(self.topic_handlers.keys()),
                   auto_offset_reset='latest')
        print("=== ABOUT TO ENTER 'async for message in self.consumer' LOOP ===")

        message_count = 0
        successful_messages = 0
        failed_messages = 0

        try:
            logger.info("📥 ENTERING KAFKA MESSAGE ITERATOR LOOP")

            # DEBUG: Check current positions
            print("=== CHECKING CURRENT POSITIONS ===")
            for tp in self.consumer.assignment():
                try:
                    position = await self.consumer.position(tp)
                    print(f"=== {tp}: current position = {position} ===")
                except Exception as e:
                    print(f"=== Error getting position for {tp}: {e} ===")

            # DEBUG: Try manual poll with longer timeout
            print("=== ATTEMPTING MANUAL getmany() POLL (10s timeout) ===")
            try:
                data = await asyncio.wait_for(self.consumer.getmany(timeout_ms=10000, max_records=100), timeout=15.0)
                print(f"=== MANUAL POLL RESULT: {len(data)} partitions, {sum(len(msgs) for msgs in data.values())} total messages ===")
                for tp, messages in data.items():
                    print(f"=== Partition {tp}: {len(messages)} messages, first offset={messages[0].offset if messages else 'N/A'} ===")
            except asyncio.TimeoutError:
                print("=== MANUAL POLL TIMED OUT after 15s ===")
            except Exception as e:
                print(f"=== MANUAL POLL ERROR: {e} ===")
                import traceback
                traceback.print_exc()

            async for message in self.consumer:
                message_count += 1

                # Track message consumed
                MESSAGES_CONSUMED_TOTAL.labels(topic=message.topic, source='kafka', job='data-storage-service').inc()
                start_time = time.time()

                # Track Kafka consumer lag
                try:
                    for tp in self.consumer.assignment():
                        committed = await self.consumer.committed(tp)
                        position = await self.consumer.position(tp)
                        if committed and position:
                            lag = position - committed
                            KAFKA_CONSUMER_LAG.labels(
                                topic=tp.topic,
                                partition=str(tp.partition),
                                job='data-ingestion-service'
                            ).set(lag)
                except Exception as lag_error:
                    logger.warning(f"Failed to calculate consumer lag: {lag_error}")

                logger.info(f"📨 RECEIVED KAFKA MESSAGE #{message_count}",
                           topic=message.topic,
                           partition=message.partition,
                           offset=message.offset,
                           key=str(message.key) if message.key else None,
                           timestamp=message.timestamp,
                           timestamp_type=message.timestamp_type)

                if not self.running:
                    logger.warning("🛑 CONSUMER STOPPING - BREAKING FROM LOOP",
                                 messages_processed=message_count)
                    break

                topic = message.topic
                raw_data = message.value

                logger.info(f"🔍 PROCESSING MESSAGE #{message_count}",
                           topic=topic,
                           raw_data_type=type(raw_data).__name__,
                           raw_data_size=len(str(raw_data)),
                           raw_data_preview=str(raw_data)[:500] if raw_data else "None")

                # Parse JSON message data with detailed logging
                try:
                    logger.info(f"🔧 JSON PARSING MESSAGE #{message_count}",
                              original_type=type(raw_data).__name__)

                    if isinstance(raw_data, bytes):
                        logger.info(f"⚙️ DECODING BYTES TO UTF-8 FOR MESSAGE #{message_count}")
                        raw_data = raw_data.decode('utf-8')

                    if isinstance(raw_data, str):
                        logger.info(f"⚙️ PARSING JSON STRING FOR MESSAGE #{message_count}",
                                  json_string_preview=raw_data[:200])
                        data = json.loads(raw_data)
                    else:
                        logger.info(f"⚙️ USING RAW DATA AS-IS FOR MESSAGE #{message_count}")
                        data = raw_data

                    logger.info(f"✅ JSON PARSING SUCCESS FOR MESSAGE #{message_count}",
                              parsed_data_type=type(data).__name__,
                              parsed_keys=list(data.keys()) if isinstance(data, dict) else "not_dict")

                    # Duplicate detection using message content hash
                    try:
                        message_content = f"{message.topic}_{message.key}_{message.timestamp}_{str(data)}"
                        message_hash = hashlib.md5(message_content.encode()).hexdigest()
                        source_id = data.get('source_id', 'unknown') if isinstance(data, dict) else 'unknown'

                        if message_hash in self.recent_message_hashes:
                            DUPLICATE_DETECTIONS.labels(
                                source=source_id,
                                job='data-ingestion-service'
                            ).inc()
                            logger.warning(f"⚠️ DUPLICATE MESSAGE DETECTED #{message_count}",
                                         topic=message.topic,
                                         hash=message_hash[:8])
                        else:
                            # Ensure duplicate_detections_total exists with same labels (for query consistency)
                            DUPLICATE_DETECTIONS.labels(
                                source=source_id,
                                job='data-ingestion-service'
                            )
                            self.recent_message_hashes.append(message_hash)
                    except Exception as dup_error:
                        logger.warning(f"Failed to check for duplicates: {dup_error}")

                except json.JSONDecodeError as e:
                    failed_messages += 1
                    logger.error(f"❌ JSON PARSING FAILED FOR MESSAGE #{message_count}",
                               topic=topic,
                               error=str(e),
                               error_type=type(e).__name__,
                               raw_data_preview=str(raw_data)[:500])
                    continue
                except Exception as e:
                    failed_messages += 1
                    logger.error(f"❌ UNEXPECTED JSON PARSING ERROR FOR MESSAGE #{message_count}",
                               topic=topic,
                               error=str(e),
                               error_type=type(e).__name__)
                    continue

                # Route message to appropriate handler with detailed logging
                if topic in self.topic_handlers:
                    logger.info(f"🎯 ROUTING MESSAGE #{message_count} TO HANDLER",
                              topic=topic,
                              handler_function=self.topic_handlers[topic].__name__)
                    try:
                        logger.info(f"🚀 CALLING HANDLER FOR MESSAGE #{message_count}",
                                   topic=topic,
                                   data_preview=str(data)[:300] if data else "None")

                        await self.topic_handlers[topic](data)

                        # Record metrics
                        processing_time = time.time() - start_time
                        MESSAGE_PROCESSING_LATENCY.labels(
                            topic=topic,
                            source=data.get('source_id', 'unknown'),
                            job='data-storage-service'
                        ).observe(processing_time)
                        MESSAGES_PROCESSED_SUCCESS.labels(
                            topic=topic,
                            source=data.get('source_id', 'unknown'),
                            job='data-storage-service'
                        ).inc()

                        # Track ingestion throughput (for dashboard)
                        source_id = data.get('source_id', 'unknown')
                        INGESTION_THROUGHPUT.labels(
                            source=source_id,
                            job='data-ingestion-service'
                        ).inc()

                        # Ensure ingestion_failed_total exists with same labels (for query consistency)
                        # This creates the metric with matching labels even though we don't increment it
                        INGESTION_FAILED.labels(
                            source=source_id,
                            error_type='none',
                            job='data-ingestion-service'
                        )

                        # Calculate and set data quality score (simplified: based on validation)
                        DATA_QUALITY_SCORE.labels(
                            source=source_id,
                            job='data-ingestion-service'
                        ).set(0.98)  # High quality for successfully processed messages

                        successful_messages += 1
                        logger.info(f"✅ MESSAGE #{message_count} PROCESSED SUCCESSFULLY",
                                   topic=topic,
                                   success_rate=f"{successful_messages}/{message_count}")

                    except Exception as e:
                        # Track failed processing
                        source_id = data.get('source_id', 'unknown') if isinstance(data, dict) else 'unknown'
                        error_name = type(e).__name__

                        MESSAGES_PROCESSED_FAILED.labels(
                            topic=topic,
                            source=source_id,
                            error_type=error_name,
                            job='data-storage-service'
                        ).inc()

                        # Track ingestion failures (for dashboard)
                        INGESTION_FAILED.labels(
                            source=source_id,
                            error_type=error_name,
                            job='data-ingestion-service'
                        ).inc()

                        # Set low quality score for failed messages
                        DATA_QUALITY_SCORE.labels(
                            source=source_id,
                            job='data-ingestion-service'
                        ).set(0.50)

                        failed_messages += 1
                        logger.error(f"❌ HANDLER FAILED FOR MESSAGE #{message_count}",
                                   topic=topic,
                                   error=str(e),
                                   error_type=type(e).__name__,
                                   message_data_preview=str(data)[:500] if data else "None",
                                   failure_rate=f"{failed_messages}/{message_count}")
                        # Continue processing other messages despite handler failure
                else:
                    failed_messages += 1
                    logger.warning(f"⚠️ NO HANDLER FOUND FOR MESSAGE #{message_count}",
                                 topic=topic,
                                 available_handlers=list(self.topic_handlers.keys()))

                # Log periodic statistics
                if message_count % 10 == 0:
                    logger.info(f"📊 MESSAGE PROCESSING STATISTICS",
                              total_messages=message_count,
                              successful_messages=successful_messages,
                              failed_messages=failed_messages,
                              success_rate=f"{(successful_messages/message_count)*100:.1f}%" if message_count > 0 else "0%")

        except KafkaError as e:
            logger.error("💥 KAFKA ERROR DURING CONSUMPTION",
                        error=str(e),
                        error_type=type(e).__name__,
                        messages_processed=message_count,
                        successful_messages=successful_messages,
                        failed_messages=failed_messages)
        except Exception as e:
            logger.error("💥 UNEXPECTED ERROR DURING MESSAGE CONSUMPTION",
                        error=str(e),
                        error_type=type(e).__name__,
                        messages_processed=message_count,
                        successful_messages=successful_messages,
                        failed_messages=failed_messages,
                        exc_info=True)
        finally:
            logger.info("🏁 MESSAGE CONSUMPTION LOOP ENDED",
                       total_messages_processed=message_count,
                       successful_messages=successful_messages,
                       failed_messages=failed_messages,
                       final_success_rate=f"{(successful_messages/message_count)*100:.1f}%" if message_count > 0 else "0%")

    async def _handle_fire_detection(self, data: Dict[str, Any]):
        """
        Handle fire detection data from NASA FIRMS

        Actual Kafka message format (flat structure with individual detections):
        {
            "timestamp": "...",
            "latitude": 40.822,
            "longitude": -114.256,
            "confidence": 0.5,
            "bright_ti4": 301.2,
            "frp": 1.5,
            "satellite": "Terra",
            "instrument": "MODIS",
            "ingestion_metadata": {
                "source_id": "firms_modis_terra",
                "source_type": "satellite"
            }
        }
        """
        try:
            # Extract source_id with priority: record's own source_id > ingestion_metadata > legacy 'source'
            # ✅ FIX: Prioritize record's top-level source_id to handle mixed batches correctly
            # This prevents NOAA station data from being routed to alerts table when batched together
            ingestion_metadata = data.get('ingestion_metadata', {})
            source_id = (
                data.get('source_id') or                          # 1. Record's top-level source_id
                ingestion_metadata.get('source_id') or            # 2. Metadata source_id
                data.get('source') or                             # 3. Legacy 'source' field
                'unknown'                                         # 4. Fallback
            )

            if source_id == 'unknown':
                logger.error("Fire detection source_id unknown - cannot route to table",
                           available_keys=list(data.keys()),
                           has_ingestion_metadata=bool(ingestion_metadata))
                return

            # Use TableRouter to determine target table
            table_name = TableRouter.get_table_name(source_id)

            logger.debug(f"Routing fire detection to {table_name}",
                       source_id=source_id,
                       latitude=data.get('latitude'),
                       longitude=data.get('longitude'))

            # Anomaly detection for fire detections
            try:
                lat = data.get('latitude')
                lon = data.get('longitude')
                brightness = data.get('bright_ti4') or data.get('brightness')
                frp = data.get('frp')

                # Check for invalid coordinates
                if lat is not None and (lat < -90 or lat > 90):
                    ANOMALIES_DETECTED.labels(
                        source=source_id,
                        anomaly_type='invalid_latitude',
                        job='data-ingestion-service'
                    ).inc()
                    logger.warning(f"Anomaly detected: invalid latitude {lat}")

                if lon is not None and (lon < -180 or lon > 180):
                    ANOMALIES_DETECTED.labels(
                        source=source_id,
                        anomaly_type='invalid_longitude',
                        job='data-ingestion-service'
                    ).inc()
                    logger.warning(f"Anomaly detected: invalid longitude {lon}")

                # Check for unrealistic brightness values
                if brightness is not None and (brightness < 200 or brightness > 500):
                    ANOMALIES_DETECTED.labels(
                        source=source_id,
                        anomaly_type='unusual_brightness',
                        job='data-ingestion-service'
                    ).inc()
                    logger.warning(f"Anomaly detected: unusual brightness {brightness}K")

                # Check for unrealistic FRP values
                if frp is not None and frp > 10000:
                    ANOMALIES_DETECTED.labels(
                        source=source_id,
                        anomaly_type='extreme_frp',
                        job='data-ingestion-service'
                    ).inc()
                    logger.warning(f"Anomaly detected: extreme FRP {frp} MW")

            except Exception as anomaly_error:
                logger.warning(f"Failed to check for anomalies: {anomaly_error}")

            # Map fields and store to specialized table
            mapped_data = TableRouter.map_fields(source_id, data)
            await self._store_to_table(table_name, mapped_data, source_id)

            logger.info("Stored fire detection from Kafka",
                       source_id=source_id,
                       table=table_name)

        except Exception as e:
            logger.error("Failed to handle fire detection data",
                       error=str(e),
                       source_id=source_id if 'source_id' in locals() else 'unknown')
            raise

    async def _store_fire_incident(self, detection: Dict[str, Any], source_id: str):
        """Store individual fire incident to PostgreSQL with detailed logging"""
        incident_id = str(uuid.uuid4())

        logger.info("🔥 STORING FIRE INCIDENT TO DATABASE",
                   incident_id=incident_id,
                   source_id=source_id,
                   detection_keys=list(detection.keys()) if detection else [],
                   latitude=detection.get('latitude'),
                   longitude=detection.get('longitude'))

        try:
            # Transform detection data to match PostgreSQL schema
            logger.info("⚙️ TRANSFORMING FIRE DETECTION DATA",
                       incident_id=incident_id,
                       original_detection=detection)

            # Handle both main system format (bright_ti4, bright_ti5) and simplified format
            brightness = detection.get('brightness') or detection.get('bright_ti4')
            temperature = detection.get('temperature') or detection.get('bright_ti5') or brightness
            parsed_timestamp = self._parse_sophisticated_timestamp(detection)

            incident_data = {
                'incident_id': incident_id,
                'latitude': float(detection.get('latitude', 0.0)),
                'longitude': float(detection.get('longitude', 0.0)),
                'confidence': float(detection.get('confidence', 0.0)),
                'brightness': brightness,
                'temperature': temperature,
                'frp': detection.get('frp'),
                'bright_t31': detection.get('bright_t31'),
                'daynight': detection.get('daynight', 'D'),
                'satellite': detection.get('satellite'),
                'instrument': detection.get('instrument'),
                'source': source_id,
                'timestamp': parsed_timestamp,
                'created_at': datetime.utcnow(),
                'type': 0  # Default fire type
            }

            logger.info("📝 PREPARED FIRE INCIDENT DATA FOR DB INSERT",
                       incident_id=incident_id,
                       prepared_data={
                           k: str(v) if v is not None else None
                           for k, v in incident_data.items()
                       })

            # Insert into PostgreSQL with detailed logging
            logger.info("🔗 OBTAINING DATABASE CONNECTION FOR FIRE INCIDENT",
                       incident_id=incident_id)

            async with self.db_manager.get_connection() as conn:
                logger.info("✅ DATABASE CONNECTION OBTAINED FOR FIRE INCIDENT",
                           incident_id=incident_id,
                           connection_info=str(conn)[:100])

                query = """
                INSERT INTO fire_incidents (
                    incident_id, latitude, longitude, confidence, brightness,
                    temperature, frp, bright_t31, daynight, satellite,
                    instrument, source, timestamp, created_at, type
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15
                )
                """

                logger.info("🚀 EXECUTING FIRE INCIDENT INSERT QUERY",
                           incident_id=incident_id,
                           query=query,
                           values_count=len(incident_data),
                           value_types=[type(v).__name__ for v in incident_data.values()])

                try:
                    result = await conn.execute(query, *incident_data.values())

                    logger.info("✅ FIRE INCIDENT SUCCESSFULLY INSERTED TO DATABASE",
                               incident_id=incident_id,
                               source_id=source_id,
                               db_result=str(result),
                               latitude=incident_data['latitude'],
                               longitude=incident_data['longitude'],
                               timestamp=str(incident_data['timestamp']))

                except Exception as db_error:
                    logger.error("❌ DATABASE INSERT FAILED FOR FIRE INCIDENT",
                                incident_id=incident_id,
                                source_id=source_id,
                                db_error=str(db_error),
                                db_error_type=type(db_error).__name__,
                                query=query,
                                values=str(incident_data),
                                exc_info=True)
                    raise

        except Exception as e:
            logger.error("❌ FIRE INCIDENT STORAGE FAILED",
                        incident_id=incident_id,
                        source_id=source_id,
                        detection=detection,
                        error=str(e),
                        error_type=type(e).__name__,
                        exc_info=True)
            raise

    async def _store_to_table(self, table_name: str, data: Dict[str, Any], source_id: str):
        """
        Universal method to store data to any specialized table

        Uses dynamic schema introspection to build INSERT queries
        Works with all 24 specialized tables

        Args:
            table_name: Target PostgreSQL table name
            data: Data dictionary with field values
            source_id: Original source identifier for logging
        """
        record_id = str(uuid.uuid4())

        logger.info(f"📊 STORING TO {table_name.upper()}",
                   record_id=record_id,
                   source_id=source_id,
                   data_keys=list(data.keys()) if data else [])

        try:
            async with self.db_manager.get_connection() as conn:
                # Query table schema dynamically
                schema_query = """
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = $1
                AND table_schema = 'public'
                ORDER BY ordinal_position
                """

                schema_rows = await conn.fetch(schema_query, table_name)
                if not schema_rows:
                    logger.error(f"❌ TABLE NOT FOUND: {table_name}",
                               record_id=record_id,
                               source_id=source_id)
                    return

                logger.info(f"✅ TABLE SCHEMA RETRIEVED: {table_name}",
                           record_id=record_id,
                           column_count=len(schema_rows))

                # Build dynamic INSERT based on schema and data
                available_columns = []
                values = []

                for row in schema_rows:
                    col_name = row['column_name']
                    col_type = row['data_type']

                    # Skip auto-generated columns
                    if col_name in ['id', 'created_at', 'updated_at']:
                        continue

                    # Get value from data
                    value = data.get(col_name)

                    if value is not None:
                        # Convert timestamp strings to datetime objects for TIMESTAMPTZ columns
                        if col_type in ['timestamp with time zone', 'timestamptz'] and isinstance(value, str):
                            try:
                                from dateutil import parser
                                value = parser.parse(value)
                            except Exception as e:
                                logger.warning(f"⚠️ Failed to parse timestamp for {col_name}: {value}",
                                             error=str(e))
                                # Use current time as fallback
                                value = datetime.utcnow()
                        
                        # Convert dict/list to JSON string for JSONB columns
                        elif col_type == 'jsonb' and isinstance(value, (dict, list)):
                            import json
                            value = json.dumps(value)

                        available_columns.append(col_name)
                        values.append(value)
                        logger.debug(f"✅ MAPPED {col_name}: {value}")

                if not available_columns:
                    logger.warning(f"⚠️ NO COLUMNS MAPPED FOR {table_name}",
                                 record_id=record_id,
                                 source_id=source_id,
                                 data_keys=list(data.keys()))
                    return

                # Create INSERT query with placeholders
                placeholders = [f'${i}' for i in range(1, len(values) + 1)]

                # Add ON CONFLICT handling for tables with unique constraints
                if table_name == 'noaa_weather_alerts':
                    # Handle duplicate alert_id by updating the record
                    update_cols = [col for col in available_columns if col != 'alert_id']
                    if update_cols:
                        query = f"""
                        INSERT INTO {table_name} ({', '.join(available_columns)})
                        VALUES ({', '.join(placeholders)})
                        ON CONFLICT (alert_id) DO UPDATE SET
                            {', '.join([f"{col} = EXCLUDED.{col}" for col in update_cols])}
                        """
                    else:
                        # If only alert_id is being inserted, skip duplicates
                        query = f"""
                        INSERT INTO {table_name} ({', '.join(available_columns)})
                        VALUES ({', '.join(placeholders)})
                        ON CONFLICT (alert_id) DO NOTHING
                        """
                else:
                    query = f"""
                    INSERT INTO {table_name} ({', '.join(available_columns)})
                    VALUES ({', '.join(placeholders)})
                    """

                logger.info(f"🚀 EXECUTING INSERT TO {table_name}",
                           record_id=record_id,
                           columns=available_columns,
                           column_count=len(available_columns))

                try:
                    result = await conn.execute(query, *values)

                    # Record successful DB insert
                    DB_INSERT_SUCCESS.labels(table=table_name, source=source_id, job='data-storage-service').inc()
                    RECORDS_INGESTED_SUCCESS.labels(source=source_id, job='data-ingestion-service').inc()

                    logger.info(f"✅ SUCCESSFULLY INSERTED TO {table_name}",
                               record_id=record_id,
                               source_id=source_id,
                               db_result=str(result))

                except Exception as db_error:
                    # Record failed DB insert
                    DB_INSERT_FAILED.labels(
                        table=table_name,
                        source=source_id,
                        error_type=type(db_error).__name__,
                        job='data-storage-service'
                    ).inc()

                    logger.error(f"❌ INSERT FAILED TO {table_name}",
                                record_id=record_id,
                                source_id=source_id,
                                db_error=str(db_error),
                                query=query[:200],
                                exc_info=True)
                    raise

        except Exception as e:
            logger.error(f"❌ FAILED TO STORE TO {table_name}",
                        record_id=record_id,
                        source_id=source_id,
                        error=str(e),
                        exc_info=True)
            raise

    async def _handle_weather_data(self, data: Dict[str, Any]):
        """
        Handle weather data from NOAA/weather sources

        Expected data format:
        {
            "source_id": "noaa_gfs",
            "data": [
                {
                    "latitude": 40.0,
                    "longitude": -120.0,
                    "temperature": 25.5,
                    "humidity": 45.2,
                    "wind_speed": 10.5,
                    "wind_direction": 225,
                    "pressure": 1013.25,
                    "timestamp": "2025-09-22T12:00:00Z"
                }
            ]
        }
        """
        try:
            logger.info("🌡️ PROCESSING WEATHER MESSAGE",
                       message_keys=list(data.keys()) if data else [],
                       message_preview=str(data)[:200])

            # Extract source_id with priority: record's own source_id > metadata > ingestion_metadata > legacy
            # ✅ FIX: Prioritize record's top-level source_id to handle mixed batches correctly
            # This prevents NOAA station data from being routed to alerts table when batched together
            metadata = data.get('metadata', {})
            if not metadata:
                logger.warning("📊 DEBUG: No metadata found in weather message, using fallback empty dict",
                             available_keys=list(data.keys()) if data else [],
                             algorithm_impact="MEDIUM - Weather metadata missing")

            ingestion_metadata = data.get('ingestion_metadata', {})
            if not ingestion_metadata:
                logger.debug("📊 DEBUG: No ingestion_metadata found in weather message, using fallback empty dict",
                           available_keys=list(data.keys()) if data else [],
                           algorithm_impact="LOW - Ingestion metadata missing")

            # Priority order: record source_id > metadata source_id > ingestion_metadata source_id > legacy source
            source_id = (
                data.get('source_id') or                          # 1. Record's top-level source_id
                metadata.get('source_id') or                      # 2. Metadata source_id
                ingestion_metadata.get('source_id') or            # 3. Ingestion metadata source_id
                data.get('source') or                             # 4. Legacy 'source' field
                'unknown'                                         # 5. Fallback
            )
            if source_id == 'unknown':
                logger.error("🚨 DEBUG: Weather source ID fallback to 'unknown' - CRITICAL for routing",
                           metadata_keys=list(metadata.keys()) if metadata else [],
                           ingestion_metadata_keys=list(ingestion_metadata.keys()) if ingestion_metadata else [],
                           data_keys=list(data.keys()) if data else [],
                           has_metadata_source_id=bool(metadata.get('source_id')),
                           has_ingestion_source_id=bool(ingestion_metadata.get('source_id')),
                           has_source=bool(data.get('source')),
                           algorithm_impact="HIGH - Weather data may be misclassified")

            # Try to get weather data from 'data' field first, then fallback to root level
            data_section = data.get('data', {})
            if not data_section:
                logger.warning("📊 DEBUG: No data section found in weather message, using fallback empty dict",
                             available_keys=list(data.keys()) if data else [],
                             algorithm_impact="HIGH - Weather data section missing")

            logger.info("🔍 DEBUG: About to check data_section routing",
                       data_section_empty=not data_section,
                       data_section_type=type(data_section).__name__,
                       source_id=source_id)

            if not data_section:
                # If no 'data' field, check if weather data is at root level
                logger.info("🔍 DEBUG: Checking message type",
                           source_id=source_id,
                           has_lat=bool(data.get('latitude')),
                           has_lon=bool(data.get('longitude')),
                           has_alert_id=bool(data.get('alert_id')),
                           has_station_id=bool(data.get('station_id')),
                           alerts_in_source_id='alerts' in source_id if source_id else False,
                           stations_in_source_id='stations' in source_id if source_id else False)

                # Check source_id FIRST for alerts (may have dummy lat/lon)
                if source_id and "alerts" in source_id:
                    data_section = data
                    logger.info("📢 ALERT ROUTED BY SOURCE_ID", source_id=source_id)
                # ✅ FIX: Handle NOAA station observations (have station_id, not lat/lon at root)
                elif source_id and "stations" in source_id:
                    data_section = data
                    logger.info("🌡️ STATION DATA ROUTED BY SOURCE_ID",
                               source_id=source_id,
                               station_id=data.get('station_id'))
                elif data.get('station_id'):
                    # Station observations have station_id field
                    data_section = data
                    logger.info("🌡️ STATION DATA FOUND AT ROOT LEVEL",
                               source_id=source_id,
                               station_id=data.get('station_id'))
                elif data.get('latitude') is not None and data.get('longitude') is not None:
                    data_section = data
                    logger.info("📍 WEATHER DATA FOUND AT ROOT LEVEL", source_id=source_id)
                elif 'alerts' in source_id and 'alert_id' in data:
                    # Weather alerts don't have lat/lon, they have alert_id and area_description
                    data_section = data
                    logger.info("📢 WEATHER ALERT FOUND AT ROOT LEVEL", source_id=source_id, alert_id=data.get('alert_id'))
                else:
                    logger.warning("❌ NO WEATHER DATA FOUND IN MESSAGE",
                                 source_id=source_id,
                                 has_data_field=bool(data.get('data')),
                                 has_lat_lon=bool(data.get('latitude')),
                                 has_alert_id=bool(data.get('alert_id')),
                                 has_station_id=bool(data.get('station_id')))
                    return

            # Store weather record - route to appropriate table based on source
            logger.info("🌤️ CALLING _store_weather_record",
                       data_keys=list(data_section.keys()) if data_section else [],
                       source_id=source_id)

            # Anomaly detection for weather data
            try:
                temp = data_section.get('temperature')
                humidity = data_section.get('humidity')
                wind_speed = data_section.get('wind_speed')
                pressure = data_section.get('pressure')

                # Check for unrealistic temperature values (Celsius)
                if temp is not None and (temp < -100 or temp > 70):
                    ANOMALIES_DETECTED.labels(
                        source=source_id,
                        anomaly_type='extreme_temperature',
                        job='data-ingestion-service'
                    ).inc()
                    logger.warning(f"Anomaly detected: extreme temperature {temp}°C")

                # Check for invalid humidity (0-100%)
                if humidity is not None and (humidity < 0 or humidity > 100):
                    ANOMALIES_DETECTED.labels(
                        source=source_id,
                        anomaly_type='invalid_humidity',
                        job='data-ingestion-service'
                    ).inc()
                    logger.warning(f"Anomaly detected: invalid humidity {humidity}%")

                # Check for extreme wind speeds
                if wind_speed is not None and wind_speed > 150:
                    ANOMALIES_DETECTED.labels(
                        source=source_id,
                        anomaly_type='extreme_wind_speed',
                        job='data-ingestion-service'
                    ).inc()
                    logger.warning(f"Anomaly detected: extreme wind speed {wind_speed} m/s")

                # Check for unrealistic pressure values (hPa)
                if pressure is not None and (pressure < 800 or pressure > 1100):
                    ANOMALIES_DETECTED.labels(
                        source=source_id,
                        anomaly_type='extreme_pressure',
                        job='data-ingestion-service'
                    ).inc()
                    logger.warning(f"Anomaly detected: extreme pressure {pressure} hPa")

            except Exception as anomaly_error:
                logger.warning(f"Failed to check for weather anomalies: {anomaly_error}")

            # Use TableRouter for automatic routing to specialized tables
            table_name = TableRouter.get_table_name(source_id)
            mapped_data = TableRouter.map_fields(source_id, data_section)
            # Fix alert-specific data before storing
            if source_id == 'noaa_alerts_active' and table_name == 'noaa_weather_alerts':
                import hashlib
                if not mapped_data.get('alert_id') or mapped_data.get('alert_id') == '':
                    unique_str = f"{mapped_data.get('event', 'unknown')}_{mapped_data.get('timestamp', '')}_{mapped_data.get('area_description', '')}"
                    mapped_data['alert_id'] = hashlib.md5(unique_str.encode()).hexdigest()
                    logger.info("Generated alert_id", alert_id=mapped_data['alert_id'])
                if 'sender' in mapped_data and 'sender_name' not in mapped_data:
                    mapped_data['sender_name'] = mapped_data.pop('sender')

                # ✅ CONSUMER-SIDE VALIDATION: Skip alerts with NULL/empty event field
                # This handles old invalid messages already in Kafka from before ingestion validation
                event_field = mapped_data.get('event')
                if event_field is None or (isinstance(event_field, str) and event_field.strip() == ''):
                    logger.warning(
                        "⚠️ SKIPPING ALERT: NULL or empty 'event' field (likely station data misrouted to alerts topic)",
                        source_id=source_id,
                        alert_id=mapped_data.get('alert_id'),
                        has_station_id=bool(data_section.get('station_id')),
                        has_station_name=bool(data_section.get('station_name')),
                        message_type="Station data incorrectly routed to alerts table (old Kafka backlog)"
                    )
                    return  # Skip this message

            await self._store_to_table(table_name, mapped_data, source_id)

            logger.info("Stored weather data from Kafka",
                       source_id=source_id,
                       count=1)

        except Exception as e:
            logger.error("Failed to handle weather data", error=str(e))
            raise

    async def _store_weather_record(self, record: Dict[str, Any], source_id: str):
        """Store individual weather record to PostgreSQL with detailed logging"""
        reading_id = str(uuid.uuid4())

        logger.info("🌤️ STORING WEATHER RECORD TO DATABASE",
                   reading_id=reading_id,
                   source_id=source_id,
                   record_keys=list(record.keys()) if record else [],
                   record_preview=str(record)[:300])

        try:
            logger.info("🔗 OBTAINING DATABASE CONNECTION FOR WEATHER RECORD",
                       reading_id=reading_id)

            async with self.db_manager.get_connection() as conn:
                logger.info("✅ DATABASE CONNECTION OBTAINED FOR WEATHER RECORD",
                           reading_id=reading_id)

                # Query the table schema to get column names and types
                logger.info("🔍 QUERYING WEATHER_DATA TABLE SCHEMA",
                           reading_id=reading_id)

                schema_query = """
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'weather_data'
                AND table_schema = 'public'
                ORDER BY ordinal_position
                """

                try:
                    schema_rows = await conn.fetch(schema_query)
                    logger.info("✅ WEATHER TABLE SCHEMA RETRIEVED",
                               reading_id=reading_id,
                               column_count=len(schema_rows),
                               columns=[row['column_name'] for row in schema_rows])
                except Exception as schema_error:
                    logger.error("❌ FAILED TO RETRIEVE WEATHER TABLE SCHEMA",
                                reading_id=reading_id,
                                schema_error=str(schema_error),
                                schema_error_type=type(schema_error).__name__)
                    raise

                # Build dynamic insert based on available data and schema
                available_columns = []
                values = []

                logger.info("⚙️ BUILDING DYNAMIC INSERT FOR WEATHER RECORD",
                           reading_id=reading_id)

                for row in schema_rows:
                    col_name = row['column_name']

                    logger.debug(f"📝 PROCESSING COLUMN: {col_name}",
                               reading_id=reading_id,
                               data_type=row['data_type'],
                               is_nullable=row['is_nullable'])

                    # Skip auto-generated columns (but include id since it's required)
                    if col_name in ['created_at']:
                        logger.debug(f"⏭️ SKIPPING AUTO-GENERATED COLUMN: {col_name}",
                                   reading_id=reading_id)
                        continue

                    # Handle required ID column
                    if col_name == 'id':
                        available_columns.append(col_name)
                        values.append(reading_id)
                        logger.debug(f"✅ MAPPED id: {reading_id}")
                        continue

                    # Map data fields to database columns
                    if col_name == 'reading_id':
                        available_columns.append(col_name)
                        values.append(reading_id)
                        logger.debug(f"✅ MAPPED reading_id: {reading_id}")

                    elif col_name == 'timestamp':
                        available_columns.append(col_name)

                        # Handle timestamp parsing with detailed logging
                        timestamp_str = record.get('timestamp')
                        logger.info("⏰ PROCESSING TIMESTAMP FOR WEATHER RECORD",
                                   reading_id=reading_id,
                                   original_timestamp=timestamp_str,
                                   timestamp_type=type(timestamp_str).__name__)

                        if timestamp_str:
                            try:
                                if timestamp_str.endswith('Z'):
                                    timestamp_str = timestamp_str[:-1] + '+00:00'
                                dt = datetime.fromisoformat(timestamp_str)
                                # PRESERVE timezone info from connectors (PST/PDT)
                                parsed_timestamp = dt
                                logger.info("✅ TIMESTAMP PARSED SUCCESSFULLY",
                                           reading_id=reading_id,
                                           original=record.get('timestamp'),
                                           parsed=str(parsed_timestamp))
                            except ValueError as ts_error:
                                parsed_timestamp = datetime.utcnow()
                                logger.warning("⚠️ TIMESTAMP PARSING FAILED, USING CURRENT TIME",
                                             reading_id=reading_id,
                                             timestamp_error=str(ts_error),
                                             fallback_timestamp=str(parsed_timestamp))
                        else:
                            parsed_timestamp = datetime.utcnow()
                            logger.warning("⚠️ NO TIMESTAMP PROVIDED, USING CURRENT TIME",
                                         reading_id=reading_id,
                                         fallback_timestamp=str(parsed_timestamp))

                        values.append(parsed_timestamp)

                    elif col_name == 'source' and source_id:
                        available_columns.append(col_name)
                        values.append(source_id)
                        logger.debug(f"✅ MAPPED source: {source_id}")

                    elif col_name in record:
                        available_columns.append(col_name)
                        values.append(record[col_name])
                        logger.debug(f"✅ MAPPED {col_name}: {record[col_name]}")

                    elif col_name == 'wind_direction' and col_name not in record:
                        available_columns.append(col_name)
                        values.append(0.0)
                        logger.debug(f"⚠️ DEFAULT wind_direction: 0.0")

                    elif col_name == 'pressure' and col_name not in record:
                        available_columns.append(col_name)
                        values.append(1013.25)
                        logger.debug(f"⚠️ DEFAULT pressure: 1013.25")
                    else:
                        logger.debug(f"⏭️ SKIPPING UNMAPPED COLUMN: {col_name}")

                # Create placeholders and query
                placeholders = [f'${i}' for i in range(1, len(values) + 1)]

                if not available_columns:
                    logger.error("❌ NO VALID COLUMNS FOUND FOR WEATHER RECORD",
                               reading_id=reading_id,
                               record=record)
                    return

                query = f"""
                INSERT INTO weather_data ({', '.join(available_columns)})
                VALUES ({', '.join(placeholders[:len(values)])})
                """

                logger.info("🚀 EXECUTING WEATHER RECORD INSERT QUERY",
                           reading_id=reading_id,
                           query=query,
                           columns=available_columns,
                           values=[str(v) for v in values],
                           value_types=[str(type(v)) for v in values])

                try:
                    result = await conn.execute(query, *values)

                    logger.info("✅ WEATHER RECORD SUCCESSFULLY INSERTED TO DATABASE",
                               reading_id=reading_id,
                               source_id=source_id,
                               db_result=str(result),
                               columns_inserted=len(available_columns))

                except Exception as db_error:
                    logger.error("❌ DATABASE INSERT FAILED FOR WEATHER RECORD",
                                reading_id=reading_id,
                                source_id=source_id,
                                db_error=str(db_error),
                                db_error_type=type(db_error).__name__,
                                query=query,
                                values=str(values),
                                exc_info=True)
                    raise

        except Exception as e:
            logger.error("❌ WEATHER RECORD STORAGE FAILED",
                        reading_id=reading_id,
                        source_id=source_id,
                        record=record,
                        error=str(e),
                        error_type=type(e).__name__,
                        exc_info=True)
            raise

    async def _store_gridpoint_forecast(self, record: Dict[str, Any], source_id: str):
        """Store gridpoint forecast record to dedicated PostgreSQL table"""
        reading_id = str(uuid.uuid4())

        logger.info("🌐 STORING GRIDPOINT FORECAST TO DATABASE",
                   reading_id=reading_id,
                   source_id=source_id,
                   record_keys=list(record.keys()) if record else [])

        try:
            async with self.db_manager.get_connection() as conn:
                # Query the gridpoint forecast table schema
                schema_query = """
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'noaa_gridpoint_forecast'
                AND table_schema = 'public'
                ORDER BY ordinal_position
                """

                schema_rows = await conn.fetch(schema_query)
                logger.info("✅ GRIDPOINT FORECAST TABLE SCHEMA RETRIEVED",
                           reading_id=reading_id,
                           column_count=len(schema_rows))

                # Build dynamic insert based on available data and schema
                available_columns = []
                values = []

                for row in schema_rows:
                    col_name = row['column_name']

                    # Skip auto-generated columns
                    if col_name in ['id', 'created_at', 'updated_at']:
                        continue

                    # Get value from record
                    value = record.get(col_name)

                    if value is not None:
                        # Convert timestamp strings to datetime objects for TIMESTAMPTZ columns
                        if row['data_type'] in ['timestamp with time zone', 'timestamptz'] and isinstance(value, str):
                            from dateutil import parser
                            value = parser.parse(value)

                        available_columns.append(col_name)
                        values.append(value)

                if not available_columns:
                    logger.warning("❌ NO COLUMNS AVAILABLE FOR GRIDPOINT FORECAST INSERT",
                                 reading_id=reading_id,
                                 record=record)
                    return

                placeholders = [f'${i+1}' for i in range(len(values))]
                query = f"""
                INSERT INTO noaa_gridpoint_forecast ({', '.join(available_columns)})
                VALUES ({', '.join(placeholders)})
                """

                logger.info("🚀 EXECUTING GRIDPOINT FORECAST INSERT",
                           reading_id=reading_id,
                           query=query,
                           columns=available_columns)

                result = await conn.execute(query, *values)

                logger.info("✅ GRIDPOINT FORECAST SUCCESSFULLY INSERTED",
                           reading_id=reading_id,
                           source_id=source_id,
                           db_result=str(result),
                           columns_inserted=len(available_columns))

        except Exception as e:
            logger.error("❌ GRIDPOINT FORECAST STORAGE FAILED",
                        reading_id=reading_id,
                        source_id=source_id,
                        record=record,
                        error=str(e),
                        error_type=type(e).__name__,
                        exc_info=True)
            raise

    async def _handle_sensor_data(self, data: Dict[str, Any]):
        """
        Handle IoT sensor data - Updated to handle both single records and arrays

        Expected data formats:
        1. Nested format with metadata:
        {
            "metadata": {"source_id": "iot_sensor"},
            "data": {
                "sensor_id": "SENSOR_001",
                "latitude": 40.0,
                "longitude": -120.0,
                "temperature": 35.5,
                "humidity": 30.2,
                "smoke_level": 15.8,
                "co2_level": 410.5,
                "timestamp": "2025-09-22T12:00:00Z"
            }
        }

        2. Array format:
        {
            "metadata": {"source_id": "iot_sensor"},
            "data": [
                {"sensor_id": "SENSOR_001", "temperature": 35.5, ...},
                {"sensor_id": "SENSOR_002", "temperature": 32.1, ...}
            ]
        }

        3. Flat format (fallback):
        {
            "sensor_id": "SENSOR_001",
            "temperature": 35.5,
            "humidity": 30.2,
            "timestamp": "2025-09-22T12:00:00Z"
        }
        """
        try:
            logger.info("🔧 PROCESSING SENSOR MESSAGE WITH ENHANCED HANDLING",
                       message_keys=list(data.keys()) if data else [],
                       message_preview=str(data)[:300])

            # Extract source_id from metadata, ingestion_metadata, or use source field
            metadata = data.get('metadata', {})
            ingestion_metadata = data.get('ingestion_metadata', {})
            source_id = (metadata.get('source_id') or
                        ingestion_metadata.get('source_id') or
                        data.get('source', 'unknown'))

            logger.info("📊 SENSOR SOURCE IDENTIFICATION",
                       source_id=source_id,
                       metadata_keys=list(metadata.keys()) if metadata else [],
                       has_metadata=bool(metadata))

            # Get sensor data from data field with enhanced format handling
            data_section = data.get('data', {})

            if not data_section:
                logger.warning("📊 DEBUG: No data section found in sensor message, checking for flat format",
                              available_keys=list(data.keys()) if data else [],
                              algorithm_impact="MEDIUM - Checking flat format fallback")

                # Check if this is flat format (sensor data at root level)
                if data.get('sensor_id') is not None:
                    logger.info("📍 SENSOR DATA FOUND AT ROOT LEVEL (FLAT FORMAT)", source_id=source_id)
                    data_section = data
                else:
                    logger.warning("❌ NO SENSOR DATA FOUND IN MESSAGE",
                                 source_id=source_id,
                                 has_data_field=bool(data.get('data')),
                                 has_sensor_id=bool(data.get('sensor_id')))
                    return

            # Handle both single records and arrays of records
            records_processed = 0

            if isinstance(data_section, list):
                logger.info("📊 PROCESSING SENSOR ARRAY FORMAT",
                           source_id=source_id,
                           array_length=len(data_section))

                # Array of sensor records - use TableRouter for automatic routing
                table_name = TableRouter.get_table_name(source_id)
                for i, record in enumerate(data_section):
                    if isinstance(record, dict):
                        logger.info(f"📍 PROCESSING SENSOR RECORD {i+1}/{len(data_section)}",
                                   record_keys=list(record.keys()) if record else [],
                                   sensor_id=record.get('sensor_id', 'unknown'),
                                   target_table=table_name)
                        mapped_data = TableRouter.map_fields(source_id, record)
                        await self._store_to_table(table_name, mapped_data, source_id)
                        records_processed += 1
                    else:
                        logger.warning(f"⚠️ SKIPPING INVALID SENSOR RECORD {i+1}",
                                     record_type=type(record).__name__,
                                     record_preview=str(record)[:100])

            elif isinstance(data_section, dict):
                logger.info("📊 PROCESSING SINGLE SENSOR RECORD FORMAT",
                           source_id=source_id,
                           record_keys=list(data_section.keys()))

                # Single sensor record - use TableRouter for automatic routing
                table_name = TableRouter.get_table_name(source_id)
                mapped_data = TableRouter.map_fields(source_id, data_section)
                await self._store_to_table(table_name, mapped_data, source_id)
                records_processed = 1
            else:
                logger.error("❌ UNSUPPORTED SENSOR DATA FORMAT",
                           source_id=source_id,
                           data_section_type=type(data_section).__name__,
                           data_section_preview=str(data_section)[:200])
                return

            logger.info("✅ SENSOR DATA PROCESSING COMPLETED",
                       source_id=source_id,
                       records_processed=records_processed)

        except Exception as e:
            logger.error("❌ FAILED TO HANDLE SENSOR DATA",
                        error=str(e),
                        error_type=type(e).__name__,
                        exc_info=True)
            raise

    async def _store_sensor_record(self, record: Dict[str, Any], source_id: str):
        """Store individual sensor record to PostgreSQL with detailed logging"""
        reading_id = str(uuid.uuid4())

        logger.info("📊 STORING SENSOR RECORD TO DATABASE",
                   reading_id=reading_id,
                   source_id=source_id,
                   record_keys=list(record.keys()) if record else [],
                   record_preview=str(record)[:300])

        try:
            # Extract readings from nested structure if present
            readings = record.get('readings', {})
            logger.info("🔍 EXTRACTED SENSOR READINGS",
                       reading_id=reading_id,
                       readings_keys=list(readings.keys()) if readings else [],
                       has_nested_readings=bool(readings))

            logger.info("🔗 OBTAINING DATABASE CONNECTION FOR SENSOR RECORD",
                       reading_id=reading_id)

            async with self.db_manager.get_connection() as conn:
                logger.info("✅ DATABASE CONNECTION OBTAINED FOR SENSOR RECORD",
                           reading_id=reading_id)

                # Query the table schema to get column names and types
                logger.info("🔍 QUERYING SENSOR_READINGS TABLE SCHEMA",
                           reading_id=reading_id)

                schema_query = """
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'sensor_readings'
                AND table_schema = 'public'
                ORDER BY ordinal_position
                """

                try:
                    schema_rows = await conn.fetch(schema_query)
                    logger.info("✅ SENSOR TABLE SCHEMA RETRIEVED",
                               reading_id=reading_id,
                               column_count=len(schema_rows),
                               columns=[row['column_name'] for row in schema_rows])
                except Exception as schema_error:
                    logger.error("❌ FAILED TO RETRIEVE SENSOR TABLE SCHEMA",
                                reading_id=reading_id,
                                schema_error=str(schema_error),
                                schema_error_type=type(schema_error).__name__)
                    raise

                # Build dynamic insert based on available data and schema
                available_columns = []
                values = []

                logger.info("⚙️ BUILDING DYNAMIC INSERT FOR SENSOR RECORD",
                           reading_id=reading_id)

                for row in schema_rows:
                    col_name = row['column_name']
                    is_nullable = row['is_nullable'] == 'YES'

                    logger.debug(f"📝 PROCESSING SENSOR COLUMN: {col_name}",
                               reading_id=reading_id,
                               data_type=row['data_type'],
                               is_nullable=is_nullable)

                    # Skip auto-generated columns
                    if col_name in ['created_at']:
                        logger.debug(f"⏭️ SKIPPING AUTO-GENERATED COLUMN: {col_name}")
                        continue

                    # Handle required ID column
                    if col_name == 'id':
                        available_columns.append(col_name)
                        values.append(reading_id)
                        logger.debug(f"✅ MAPPED id: {reading_id}")
                        continue

                    # Map data fields to database columns
                    value = None
                    if col_name == 'reading_id':
                        value = reading_id
                        logger.debug(f"✅ MAPPED reading_id: {reading_id}")

                    elif col_name == 'timestamp':
                        value = self._parse_timestamp(record)
                        logger.info("⏰ PROCESSED SENSOR TIMESTAMP",
                                   reading_id=reading_id,
                                   original=record.get('timestamp'),
                                   parsed=str(value),
                                   type=str(type(value)))

                    elif col_name == 'source' and source_id:
                        value = source_id
                        logger.debug(f"✅ MAPPED source: {source_id}")

                    elif col_name in record:
                        value = record[col_name]
                        logger.debug(f"✅ MAPPED {col_name} from record: {value}")

                    elif col_name in readings:
                        value = readings[col_name]
                        logger.debug(f"✅ MAPPED {col_name} from readings: {value}")

                    # Handle special database column mappings that don't match sensor data fields
                    elif col_name == 'co2_level' and 'co2' in record:
                        value = record['co2']
                        logger.debug(f"✅ MAPPED {col_name} from co2: {value}")
                    elif col_name == 'co2_level' and 'co2_level' in record:
                        value = record['co2_level']
                        logger.debug(f"✅ MAPPED {col_name} from co2_level: {value}")

                    # Only include columns that have values or are nullable
                    if value is not None or is_nullable:
                        available_columns.append(col_name)
                        values.append(value)
                        logger.debug(f"✅ INCLUDED {col_name}: {value} (nullable={is_nullable})")
                    else:
                        logger.debug(f"⏭️ SKIPPED {col_name}: no value and not nullable")

                        # Enhanced logging for debugging column mismatches
                        if col_name not in ['id', 'created_at', 'reading_id', 'timestamp', 'source']:
                            logger.info(f"🔍 SENSOR COLUMN ANALYSIS: {col_name} not found in data",
                                       available_in_record=list(record.keys()) if record else [],
                                       available_in_readings=list(readings.keys()) if readings else [],
                                       column_type=row['data_type'],
                                       is_nullable=is_nullable)

                # Create placeholders and query
                placeholders = [f'${i}' for i in range(1, len(values) + 1)]

                if not available_columns:
                    logger.error("❌ NO VALID COLUMNS FOUND FOR SENSOR RECORD",
                               reading_id=reading_id,
                               record_keys=list(record.keys()) if record else [],
                               readings_keys=list(readings.keys()) if readings else [],
                               record_preview=str(record)[:300],
                               algorithm_impact="HIGH - Sensor record completely rejected")

                    # Additional debugging for column mapping failures
                    logger.error("🔍 SENSOR COLUMN MAPPING FAILURE ANALYSIS",
                               record_fields=list(record.keys()) if record else [],
                               expected_database_columns=[row['column_name'] for row in schema_rows],
                               missing_required_fields="Check if sensor_id, latitude, longitude, temperature exist in data")
                    return

                query = f"""
                INSERT INTO sensor_readings ({', '.join(available_columns)})
                VALUES ({', '.join(placeholders[:len(values)])})
                """

                logger.info("🚀 EXECUTING SENSOR RECORD INSERT QUERY",
                           reading_id=reading_id,
                           query=query,
                           columns=available_columns,
                           values=[str(v) for v in values],
                           value_types=[str(type(v)) for v in values])

                try:
                    result = await conn.execute(query, *values)

                    logger.info("✅ SENSOR RECORD SUCCESSFULLY INSERTED TO DATABASE",
                               reading_id=reading_id,
                               source_id=source_id,
                               db_result=str(result),
                               columns_inserted=len(available_columns))

                except Exception as db_error:
                    logger.error("❌ DATABASE INSERT FAILED FOR SENSOR RECORD",
                                reading_id=reading_id,
                                source_id=source_id,
                                db_error=str(db_error),
                                db_error_type=type(db_error).__name__,
                                query=query,
                                values=str(values),
                                exc_info=True)
                    raise

        except Exception as e:
            logger.error("❌ SENSOR RECORD STORAGE FAILED",
                        reading_id=reading_id,
                        source_id=source_id,
                        record=record,
                        error=str(e),
                        error_type=type(e).__name__,
                        exc_info=True)
            raise

    def _parse_timestamp(self, data: Dict[str, Any]) -> datetime:
        """Parse timestamp from various formats"""
        try:
            # Try different timestamp formats
            if 'timestamp' in data:
                timestamp_str = data['timestamp']
                if isinstance(timestamp_str, str):
                    # Try ISO format first (handles both 'Z' and timezone offsets)
                    try:
                        if timestamp_str.endswith('Z'):
                            # Replace 'Z' with explicit UTC offset
                            timestamp_str = timestamp_str[:-1] + '+00:00'
                        # Parse ISO format timestamp
                        dt = datetime.fromisoformat(timestamp_str)
                        # Ensure we return a datetime object (not string)
                        # PRESERVE timezone info from connectors (PST/PDT)
                        return dt
                    except ValueError:
                        # Try parsing without timezone info
                        try:
                            clean_str = timestamp_str.replace('Z', '').replace('T', ' ')
                            return datetime.strptime(clean_str, '%Y-%m-%d %H:%M:%S.%f')
                        except ValueError:
                            try:
                                return datetime.strptime(clean_str, '%Y-%m-%d %H:%M:%S')
                            except ValueError:
                                pass

            # Try NASA FIRMS format (acq_date + acq_time)
            if 'acq_date' in data and 'acq_time' in data:
                date_str = data['acq_date']  # YYYY-MM-DD
                time_str = str(data['acq_time'])  # HHMM (ensure it's a string)

                if len(time_str) == 4 and time_str.isdigit():
                    hour = int(time_str[:2])
                    minute = int(time_str[2:])

                    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                    return date_obj.replace(hour=hour, minute=minute)

            # Default to current time if parsing fails
            logger.warning("Could not parse timestamp, using current time", data=data)
            return datetime.utcnow()

        except Exception as e:
            logger.warning("Timestamp parsing failed, using current time", error=str(e), data=data)
            return datetime.utcnow()

    def _parse_sophisticated_timestamp(self, detection: Dict[str, Any]) -> datetime:
        """Parse timestamp from sophisticated main system format - preserves PST timezone from connectors"""
        try:
            # PRIORITY: Use the pre-converted PST timestamp field if available
            # Data connectors (FIRMS, weather, sensors) send PST timestamps in 'timestamp' field
            if 'timestamp' in detection:
                timestamp_value = detection['timestamp']

                # If already a datetime object, return it
                if isinstance(timestamp_value, datetime):
                    return timestamp_value

                # Parse PST timestamp string (e.g., "2025-10-03T18:40:00-07:00")
                if isinstance(timestamp_value, str):
                    try:
                        if timestamp_value.endswith('Z'):
                            timestamp_value = timestamp_value[:-1] + '+00:00'
                        dt = datetime.fromisoformat(timestamp_value)
                        # PRESERVE timezone info - do NOT strip it!
                        return dt
                    except ValueError:
                        logger.warning("Failed to parse ISO timestamp, trying legacy parsing",
                                     timestamp=timestamp_value)

            # FALLBACK: Parse acq_date + acq_time (legacy FIRMS format - already in UTC)
            if 'acq_date' in detection and 'acq_time' in detection:
                date_str = detection['acq_date']  # "2025-09-22"
                time_str = str(detection['acq_time'])  # "1643"

                if len(time_str) == 4 and time_str.isdigit():
                    hour = int(time_str[:2])
                    minute = int(time_str[2:])

                    # Parse date and add time (naive datetime - interpreted as UTC by PostgreSQL)
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                    return date_obj.replace(hour=hour, minute=minute)

            # Final fallback to original timestamp parsing
            return self._parse_timestamp(detection)

        except Exception as e:
            logger.warning("Sophisticated timestamp parsing failed, using current time", error=str(e))
            return datetime.utcnow()


    async def _handle_satellite_data(self, data: Dict[str, Any]):
        """Handle general satellite data including Sentinel-2 and Sentinel-3"""
        try:
            # ✅ FIX: Prioritize record's top-level source_id to handle mixed batches correctly
            metadata = data.get('metadata', {})
            ingestion_metadata = data.get('ingestion_metadata', {})

            # Priority order: record source_id > metadata source_id > ingestion_metadata source_id > legacy source
            source_id = (
                data.get('source_id') or                          # 1. Record's top-level source_id
                metadata.get('source_id') or                      # 2. Metadata source_id
                ingestion_metadata.get('source_id') or            # 3. Ingestion metadata source_id
                data.get('source') or                             # 4. Legacy 'source' field
                'unknown'                                         # 5. Fallback
            )

            logger.info("Received satellite data",
                       source_id=source_id,
                       data_keys=list(data.keys()) if data else [])

            # Route to appropriate handler based on source
            if source_id == 'sat_sentinel2_msi':
                await self._store_sentinel2_data(data)
            elif source_id == 'sat_sentinel3_slstr':
                await self._store_sentinel3_data(data)
            else:
                logger.info("Satellite data logged (no handler for source)", source_id=source_id)

        except Exception as e:
            logger.error("Failed to handle satellite data", error=str(e))
            raise

    async def _store_sentinel2_data(self, data: Dict[str, Any]):
        """Store Sentinel-2 MSI data in sentinel2_msi_imagery table"""
        try:
            # Extract fields from data
            product_id = data.get('product_id')
            timestamp_str = data.get('timestamp')

            if not product_id or not timestamp_str:
                logger.warning("Missing required Sentinel-2 fields", data=data)
                return

            # Parse timestamp string to datetime
            from dateutil import parser
            timestamp = parser.isoparse(timestamp_str)

            # Check if s3_path is available (downloaded imagery)
            s3_path = data.get('s3_path')

            # Insert query with ON CONFLICT to handle duplicates
            if s3_path:
                query = """
                    INSERT INTO sentinel2_msi_imagery (
                        timestamp, product_id, cloud_cover_percent,
                        satellite, sensor, download_url, s3_path
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7
                    )
                    ON CONFLICT (product_id) DO UPDATE SET s3_path = EXCLUDED.s3_path
                """
                params = (
                    timestamp,
                    product_id,
                    data.get('cloud_cover', 0.0),
                    data.get('satellite', 'Sentinel-2'),
                    data.get('instrument', 'MSI'),
                    data.get('download_url', ''),
                    s3_path
                )
            else:
                query = """
                    INSERT INTO sentinel2_msi_imagery (
                        timestamp, product_id, cloud_cover_percent,
                        satellite, sensor, download_url
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6
                    )
                    ON CONFLICT (product_id) DO NOTHING
                """
                params = (
                    timestamp,
                    product_id,
                    data.get('cloud_cover', 0.0),
                    data.get('satellite', 'Sentinel-2'),
                    data.get('instrument', 'MSI'),
                    data.get('download_url', '')
                )

            async with self.db_manager.get_connection() as conn:
                await conn.execute(query, *params)

            logger.info("Sentinel-2 data stored successfully",
                       product_id=product_id,
                       has_s3_path=bool(s3_path))

        except Exception as e:
            logger.error("Failed to store Sentinel-2 data", error=str(e), data=data)
            raise

    async def _store_sentinel3_data(self, data: Dict[str, Any]):
        """Store Sentinel-3 SLSTR data in sentinel3_slstr_imagery table"""
        try:
            # Extract fields from data
            product_id = data.get('product_id')
            timestamp_str = data.get('timestamp')

            if not product_id or not timestamp_str:
                logger.warning("Missing required Sentinel-3 fields", data=data)
                return

            # Parse timestamp string to datetime
            from dateutil import parser
            timestamp = parser.isoparse(timestamp_str)

            # Check if s3_path is available (downloaded imagery)
            s3_path = data.get('s3_path')

            # Insert query with ON CONFLICT to handle duplicates
            if s3_path:
                query = """
                    INSERT INTO sentinel3_slstr_imagery (
                        timestamp, product_id, satellite, sensor,
                        download_url, file_size_mb, s3_path
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7
                    )
                    ON CONFLICT (product_id) DO UPDATE SET s3_path = EXCLUDED.s3_path
                """
                params = (
                    timestamp,
                    product_id,
                    data.get('satellite', 'Sentinel-3'),
                    data.get('instrument', 'SLSTR'),
                    data.get('download_url', ''),
                    data.get('size_mb', 0.0),
                    s3_path
                )
            else:
                query = """
                    INSERT INTO sentinel3_slstr_imagery (
                        timestamp, product_id, satellite, sensor,
                        download_url, file_size_mb
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6
                    )
                    ON CONFLICT (product_id) DO NOTHING
                """
                params = (
                    timestamp,
                    product_id,
                    data.get('satellite', 'Sentinel-3'),
                    data.get('instrument', 'SLSTR'),
                    data.get('download_url', ''),
                    data.get('size_mb', 0.0)
                )

            async with self.db_manager.get_connection() as conn:
                await conn.execute(query, *params)

            logger.info("Sentinel-3 data stored successfully",
                       product_id=product_id,
                       has_s3_path=bool(s3_path))

        except Exception as e:
            logger.error("Failed to store Sentinel-3 data", error=str(e), data=data)
            raise

    async def _handle_satellite_imagery(self, data: Dict[str, Any]):
        """Handle satellite imagery data - for now, log and skip as we don't have a specific table"""
        try:
            metadata = data.get('metadata', {})
            source_id = metadata.get('source_id', data.get('source', 'unknown'))

            logger.info("Received satellite imagery data - logging only",
                       source_id=source_id,
                       data_keys=list(data.keys()) if data else [])

            # TODO: Create satellite_imagery table if needed for binary/image data
            logger.info("Satellite imagery data logged (no database table configured)", source_id=source_id)

        except Exception as e:
            logger.error("Failed to handle satellite imagery data", error=str(e))
            raise


class KafkaConsumerManager:
    """
    Manager for Kafka consumer lifecycle

    Handles starting/stopping the consumer and managing background tasks.
    """

    def __init__(self, db_manager: DatabaseManager, auto_offset_reset: str = None):
        self.db_manager = db_manager
        self.consumer = None
        self.consumer_task = None
        self.auto_offset_reset = auto_offset_reset

    async def start(self):
        """Start Kafka consumer in background"""
        print("=== KAFKA CONSUMER MANAGER START() CALLED ===")
        if self.consumer_task is not None:
            logger.warning("Kafka consumer already running")
            return

        try:
            print("=== CREATING KafkaDataConsumer ===")
            self.consumer = KafkaDataConsumer(self.db_manager, self.auto_offset_reset)
            print("=== KafkaDataConsumer CREATED ===")

            # Start consumer in background task
            print("=== CREATING BACKGROUND TASK FOR self.consumer.start() ===")
            self.consumer_task = asyncio.create_task(self.consumer.start())
            print(f"=== BACKGROUND TASK CREATED: {self.consumer_task} ===")

            logger.info("Kafka consumer manager started")
            print("=== KAFKA CONSUMER MANAGER START() COMPLETED ===")

        except Exception as e:
            print(f"=== EXCEPTION IN KAFKA CONSUMER MANAGER START(): {e} ===")
            logger.error("Failed to start Kafka consumer manager", error=str(e))
            raise

    async def stop(self):
        """Stop Kafka consumer"""
        if self.consumer:
            await self.consumer.stop()

        if self.consumer_task:
            self.consumer_task.cancel()
            try:
                await self.consumer_task
            except asyncio.CancelledError:
                pass

        logger.info("Kafka consumer manager stopped")

    def is_running(self) -> bool:
        """Check if consumer is running"""
        return (self.consumer_task is not None and
                not self.consumer_task.done() and
                self.consumer and
                self.consumer.running)