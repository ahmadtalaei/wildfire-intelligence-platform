# Part 3: Data flow and processing

---

## SLIDE 1: StreamManager - Unified Orchestration Engine

    The Challenge:

    California faces 7,000+ wildfires annually across 163,000 square miles. Early detection is critical—the difference between a 1-hour and 6-hour detection can mean 10-acre containment versus 10,000-acre devastation.

    Our Solution:

    Intelligent streaming architecture processing 10,000+ events/second with <100ms critical alert latency


  1. High-Level Data Streaming Architecture

    ┌─────────────────────────────────────┐
    │  CONNECTOR LAYER                    │ ← External sources (NASA, NOAA, IoT)
    └──────────────┬──────────────────────┘
                   ▼
    ┌─────────────────────────────────────┐
    │  ORCHESTRATION (StreamManager)      │ ← Mode selection, priority, throttling
    └──────────────┬──────────────────────┘
                   ▼
    ┌─────────────────────────────────────┐
    │  QUEUE LAYER (Priority Management)  │ ← 4-level priority queues
    └──────────────┬──────────────────────┘
                   ▼
    ┌─────────────────────────────────────┐
    │  KAFKA LAYER (Event Streaming)      │ ← Topic routing, compression, storage
    └─────────────────────────────────────┘

    Key Innovation: Adaptive mode selection + priority-based processing

---
  2. Layered Architecture
    ┌─────────────────────────────────────────────────────────────────────┐
    │                    EXTERNAL DATA SOURCES                            │
    │  NASA FIRMS | NOAA Weather | Copernicus | IoT Sensors | etc.        │
    └──────────────────────────┬──────────────────────────────────────────┘
                               │
                               ▼
    ┌──────────────────────────────────────────────────────────────────────┐
    │                   CONNECTOR LAYER                                    │
    │  FirmsConnector | NOAAConnector | IoTConnector | CopernicusConnector │
    │            (Fetch raw data from external APIs/sensors)               │
    └──────────────────────────┬───────────────────────────────────────────┘
                               │
                               ▼
    ┌─────────────────────────────────────────────────────────────────────┐
    │              ORCHESTRATION LAYER (StreamManager)                    │
    │  ┌──────────────────────────────────────────────────────────────┐   │
    │  │ StreamManager (Core Orchestration Engine)                    │   │
    │  │ - Determines ingestion mode (batch/real-time/streaming)      │   │
    │  │ - Routes data to appropriate processing pipeline             │   │
    │  │ - Manages critical alert fast-path                           │   │
    │  │ - Coordinates all downstream components                      │   │
    │  └──────────────────────────────────────────────────────────────┘   │
    └──────────────────────────┬──────────────────────────────────────────┘
                               │
                 ┌─────────────┼─────────────┐
                 │             │             │
         ┌───────▼──────┐ ┌────▼────┐ ┌──────▼──────┐
         │  Batch Mode  │ │ RealTime│ │ Continuous  │
         │              │ │  Mode   │ │  Streaming  │
         |              │ │         │ │             │
         | 1h poll Freq │ │  (30s)  │ │  (instant)  │
         │  1000/batch  │ │  (500)  │ │    (100)    │
         └───────┬──────┘ └────┬────┘ └──────┬──────┘
                 │             │             │
                 └─────────────┼─────────────┘
                               │
                               ▼
    ┌─────────────────────────────────────────────────────────────────────┐
    │                   QUEUE LAYER (Priority Management)                 │
    │  ┌──────────────────────────────────────────────────────────────┐   │
    │  │ QueueManager (Priority-based buffering)                      │   │
    │  │ - CRITICAL queue (<100ms): Emergency alerts                  │   │
    │  │ - HIGH queue (<1s): NASA FIRMS, Landsat NRT                  │   │
    │  │ - NORMAL queue (<10s): Weather data, IoT sensors             │   │
    │  │ - LOW queue (<60s): Bulk data, archives                      │   │
    │  │                                                              │   │
    │  │ Throttling Manager (Backpressure control)                    │   │
    │  │ - Monitors queue depth and estimate consumer lag             │   │
    │  │ - Applies exponential backoff when needed (overloaded)       │   │
    │  └──────────────────────────────────────────────────────────────┘   │
    └──────────────────────────┬──────────────────────────────────────────┘
                               │
                               ▼
    ┌─────────────────────────────────────────────────────────────────────┐
    │              PRODUCER LAYER (Kafka Integration)                     │
    │  ┌──────────────────────────────────────────────────────────────┐   │
    │  │ ProducerWrapper (Reliability Mechanisms)                     │   │
    │  │ - Exponential backoff retry (3 attempts)                     │   │
    │  │ - Circuit breaker (OPEN after 3 failures)                    │   │
    │  │ - Dead Letter Queue routing                                  │   │
    │  └────────────────────────┬─────────────────────────────────────┘   │
    │                           │                                         │
    │  ┌────────────────────────▼─────────────────────────────────────┐   │
    │  │ KafkaDataProducer (Topic Routing & Serialization)            │   │
    │  │ - Determines target Kafka topic based on source_id           │   │
    │  │ - Applies data-type-specific compression (zstd/gzip)         │   │
    │  │ - Handles binary image routing (direct/chunks/S3)            │   │
    │  │ - Geographic partitioning (geohash-based)                    │   │
    │  └────────────────────────┬─────────────────────────────────────┘   │
    └───────────────────────────┼─────────────────────────────────────────┘
                                │
                                ▼
    ┌────────────────────────────────────────────────────────────────────┐
    │                    KAFKA TRANSPORT LAYER                           │
    │  ┌───────────────────┐  ┌──────────────┐  ┌────────────────────┐   │
    │  │ wildfire-nasa-    │  │ wildfire-    │  │ wildfire-weather-  │   │
    │  │ firms (6 parts)   │  │ iot-sensors  │  │ data (12 parts)    │   │
    │  │                   │  │ (16 parts)   │  │                    │   │
    │  └───────────────────┘  └──────────────┘  └────────────────────┘   │
    │                                                                    │
    │  ┌───────────────────┐  ┌──────────────┐  ┌────────────────────┐   │
    │  │ wildfire-         │  │ wildfire-    │  │ wildfire-critical- │   │
    │  │ satellite-imagery │  │ weather-bulk │  │ alerts (3 parts)   │   │
    │  │ (10 parts)        │  │ (8 parts)    │  │                    │   │
    │  └───────────────────┘  └──────────────┘  └────────────────────┘   │
    └────────────────────────────────────────────────────────────────────┘

---

  2. Complete Interaction Flow A → Z

    Step-by-Step Data Flow

    ┌─────────────────────────────────────────────────────────────────────┐
    │ STEP 1: External Data Arrival                                       │
    └─────────────────────────────────────────────────────────────────────┘

    External Source (NASA FIRMS satellite)
        │
        │ HTTP GET /api/v1/firms/active_fire
        │
        ▼
    FirmsConnector.fetch_data()
        │
        │ Returns: List[Dict[str, Any]]  (raw fire detection records)
        │
        └─────────────────────────────────────────────────────────────────▶


    ┌─────────────────────────────────────────────────────────────────────┐
    │ STEP 2: StreamManager Initialization                                │
    └─────────────────────────────────────────────────────────────────────┘

    StreamManager.__init__(kafka_producer, config_file)
        │
        ├─ Creates: self.kafka_producer = KafkaDataProducer(...)
        ├─ Creates: self.producer_wrapper = ProducerWrapper(kafka_producer)
        ├─ Creates: self.queue_manager = QueueManager(max_size=10000)
        ├─ Creates: self.throttle_manager = ThrottlingManager(...)
        ├─ Creates: self.topic_resolver = TopicResolver(...)
        └─ Creates: self.critical_alert_handler = CriticalAlertHandler(...)


    ┌─────────────────────────────────────────────────────────────────────┐
    │ STEP 3: Start Streaming Request                                     │
    └─────────────────────────────────────────────────────────────────────┘

    User calls: stream_manager.start_streaming(connector, config)

    StreamManager.start_streaming():
        │
        ├─ config.source_id = "firms_viirs_snpp"
        ├─ config.polling_interval = 60 (seconds)
        ├─ config.batch_size = 500
        │
        ├─ Check: _is_critical_alert_source("firms_viirs_snpp") → False
        │         (only 'alert' or 'emergency' sources are critical)
        │
        ├─ Determine ingestion mode:
        │   polling_interval = 60s → RealTimeMode (30s ≤ 60s ≤ 300s)
        │
        └─ Create ingestion mode instance ──────────────────────────────▶


    ┌─────────────────────────────────────────────────────────────────────┐
    │ STEP 4: Ingestion Mode Execution                                    │
    └─────────────────────────────────────────────────────────────────────┘

    RealTimeMode.start(data_fetcher, data_processor)
        │
        │ Spawns background task: _polling_loop()
        │
        └─▶ while self.is_running:
            │
            ├─ data = await connector.fetch_data(max_records=500)
            │    Returns: [
            │      {'latitude': 39.7596, 'longitude': -121.6219, 'brightness': 330.5,
            │       'confidence': 85, 'timestamp': '2025-10-17T10:00:00Z'},
            │      ...500 records...
            │    ]
            │
            ├─ result = await data_processor(data)
            │    This calls: _process_batch_wrapper() ────────────────▶


    ┌─────────────────────────────────────────────────────────────────────┐
    │ STEP 5: Priority Determination & Queue Insertion                    │
    └─────────────────────────────────────────────────────────────────────┘

    StreamManager._process_batch_wrapper(data):
        │
        ├─ For each record in data:
        │   │
        │   ├─ priority = _determine_priority(source_id="firms_viirs_snpp")
        │   │    Logic:
        │   │    if 'alert' in source_id → CRITICAL
        │   │    elif source_id.startswith('firms_') → HIGH  ✓
        │   │    elif source_id.startswith('iot_') → NORMAL
        │   │    else → LOW
        │   │
        │   ├─ queue_manager.enqueue(record, priority=HIGH)
        │   │    Inserts into: self.priority_queues[HIGH]
        │   │
        │   └─ Returns: queue_position
        │
        └─ Total enqueued: 500 records in HIGH priority queue ──────────▶


    ┌─────────────────────────────────────────────────────────────────────┐
    │ STEP 6: Queue Manager Dequeue & Batching                            │
    └─────────────────────────────────────────────────────────────────────┘

    QueueManager._queue_processor_loop():  (background task)
        │
        ├─ Check queue depths:
        │   CRITICAL: 0 messages (empty)
        │   HIGH: 500 messages  ✓ (Process this one first!)
        │   NORMAL: 1,200 messages (waiting)
        │   LOW: 300 messages (waiting)
        │
        ├─ Dequeue from HIGH queue (highest non-empty priority):
        │   batch = dequeue_batch(max_size=500, priority=HIGH)
        │   Returns: all 500 FIRMS records
        │
        └─ Send batch to producer_wrapper ────────────────────────────▶


    ┌─────────────────────────────────────────────────────────────────────┐
    │ STEP 7: Throttling Check                                            │
    └─────────────────────────────────────────────────────────────────────┘

    ThrottlingManager.should_throttle():
        │
        ├─ queue_utilization = (2000 total / 10000 max) = 20%
        ├─ estimated_lag = queue_utilization * 60s = 12s
        │
        ├─ Check thresholds:
        │   if lag > 300s → SEVERE throttling (wait 240s before next batch)
        │   elif lag > 120s → MODERATE throttling (wait 120s)
        │   elif lag > 60s → MINOR throttling (wait 60s)
        │   else → NO throttling  ✓ (full speed)
        │
        └─ Returns: (should_throttle=False, wait_time=0) ──────────────▶


    ┌─────────────────────────────────────────────────────────────────────┐
    │ STEP 8: Producer Wrapper (Retry & Circuit Breaker)                  │
    └─────────────────────────────────────────────────────────────────────┘

    ProducerWrapper.send_batch_with_retry(batch):
        │
        ├─ Check circuit breaker state:
        │   if state == OPEN → reject immediately
        │   elif state == HALF_OPEN → test with 1 request
        │   else (CLOSED) → proceed normally  ✓
        │
        ├─ Attempt 1: kafka_producer.send_batch_data(batch)
        │   │
        │   ├─ Returns: True (success)
        │   │
        │   └─ circuit_breaker.record_success()
        │       consecutive_failures = 0
        │       state = CLOSED
        │
        └─ Returns: (success=True, sent_count=500) ────────────────────▶


    ┌─────────────────────────────────────────────────────────────────────┐
    │ STEP 9: Kafka Producer - Topic Routing                              │
    └─────────────────────────────────────────────────────────────────────┘

    KafkaDataProducer.send_batch_data(data, source_id="firms_viirs_snpp"):
        │
        ├─ Check if any records contain binary image data:
        │   binary_serializer.is_image_data(record) → False (no images)
        │
        ├─ For each record:
        │   │
        │   ├─ topic = _determine_topic(record, source_id="firms_viirs_snpp")
        │   │    Logic at line 756-760:
        │   │    if source_id.startswith('firms_') → 'wildfire-nasa-firms'  ✓
        │   │
        │   ├─ key = _generate_partition_key(record)
        │   │    Logic at line 838-844:
        │   │    lat = 39.7596 → lat_grid = int(39.7596 * 10) % 100 = 95
        │   │    lon = -121.6219 → lon_grid = int(121.6219 * 10) % 100 = 16
        │   │    Returns: "geo_95_16"
        │   │
        │   ├─ enriched_record = _enrich_record(record, source_id=...)
        │   │    Adds metadata:
        │   │    {
        │   │      ...original record...,
        │   │      'ingestion_metadata': {
        │   │        'producer_id': 'wildfire-ingestion-abc123',
        │   │        'ingestion_timestamp': '2025-10-17T10:05:00Z',
        │   │        'source_id': 'firms_viirs_snpp',
        │   │        'source_name': 'NASA FIRMS',
        │   │        'real_time': False
        │   │      },
        │   │      'california_relevance': True,
        │   │      'wildfire_context': {'fire_detected': True}
        │   │    }
        │   │
        │   └─ producer.send(topic='wildfire-nasa-firms', value=enriched_record,
        │                    key='geo_95_16')
        │
        └─ Flush all 500 records ─────────────────────────────────────▶


    ┌─────────────────────────────────────────────────────────────────────┐
    │ STEP 10: Kafka Partitioning & Compression                           │
    └─────────────────────────────────────────────────────────────────────┘

    AIOKafkaProducer (inside kafka_producer):
        │
        ├─ Topic: 'wildfire-nasa-firms' (6 partitions, line 119-122)
        ├─ Compression: zstd level 3 (line 121)
        ├─ Partition selection:
        │   hash('geo_95_16') % 6 = partition 2
        │
        ├─ Serialize value to JSON bytes (line 991-997)
        ├─ Apply zstd compression
        │   Original: 250 bytes → Compressed: 65 bytes (74% reduction)
        │
        └─ Send to Kafka broker: localhost:9092/wildfire-nasa-firms/2 ─▶


    ┌─────────────────────────────────────────────────────────────────────┐
    │ STEP 11: Kafka Storage                                              │
    └─────────────────────────────────────────────────────────────────────┘

    Apache Kafka Broker:
        │
        ├─ Topic: wildfire-nasa-firms
        ├─ Partition: 2
        ├─ Offset: 1,234,567
        │
        ├─ Acknowledgment sent to producer (acks='all', line 264)
        │
        └─ Data persisted to disk ─────────────────────────────────────▶


    ┌─────────────────────────────────────────────────────────────────────┐
    │ STEP 12: Metrics & Monitoring                                       │
    └─────────────────────────────────────────────────────────────────────┘

    StreamManager.get_stream_metrics(stream_id):
        │
        └─ Returns:
            {
            'stream_id': 'firms_viirs_snpp_20251017_100000',
            'is_active': True,
            'mode': 'real_time',
            'records_processed': 500,
            'records_failed': 0,
            'queue_depth': 1700,
            'throttling_active': False,
            'circuit_breaker_state': 'CLOSED',
            'current_priority': 'HIGH',
            'latency_p95_ms': 42
            }

    
---
  3. Critical Alert Fast-Path (Special Case)

    Scenario: Evacuation Order (Latency < 100ms)

    ┌─────────────────────────────────────────────────────────────────────┐
    │ Special Fast-Path for Critical Alerts                               │
    └─────────────────────────────────────────────────────────────────────┘

    config.source_id = "evacuation_alert_goleta"

    StreamManager.start_streaming():
        │
        ├─ Check: _is_critical_alert_source("evacuation_alert_goleta")
        │    if 'alert' in source_id.lower() → True  ✓
        │
        ├─ BYPASS normal ingestion modes
        ├─ BYPASS priority queues
        ├─ BYPASS throttling
        │
        └─ Direct path: _start_critical_alert_stream() ───────────────────▶

    CriticalAlertHandler:
        │
        ├─ Fetches data from connector
        ├─ IMMEDIATELY sends to kafka_producer (no queue buffering)
        │
        └─ kafka_producer.send_real_time_data()
            │
            ├─ Topic: 'wildfire-critical-alerts' (3 partitions, NO compression)
            ├─ Compression: 'none' (line 97) for minimum latency
            │
            └─ Sent in <100ms total latency ──────────────────────────────▶

---
  4. COMPLETE COMPONENT RESPONSIBILITY TREE

        StreamManager (stream_manager.py:50-649)

            StreamManager's Responsibilities:
            ├─ Orchestration
            │  ├─ Determine ingestion mode (batch/real-time/streaming)
            │  ├─ Create ingestion mode instances (BatchMode, RealTimeMode, etc.)
            │  └─ Manage lifecycle of active streams
            │
            ├─ Priority Management
            │  ├─ Assign priority to records (CRITICAL/HIGH/NORMAL/LOW)
            │  └─ Route records to appropriate priority queue
            │
            ├─ Throttling Coordination
            │  ├─ Monitor queue depth
            │  ├─ Estimate consumer lag
            │  └─ Apply backpressure when needed
            │
            ├─ Critical Alert Fast-Path
            │  ├─ Detect critical alert sources
            │  └─ Bypass queues for <100ms latency
            │
            └─ Metrics & Monitoring
                ├─ Track records processed per stream
                ├─ Monitor queue depths
                └─ Report stream health status

            Key Methods:
            → start_streaming()
            → _determine_priority()
            → _process_batch_wrapper()
            → get_stream_metrics()

        ---
        IngestionModes (ingestion_modes.py:52-417)

            BatchMode (lines 52-144) | RealTimeMode (lines 147-245) | ContinuousStreamingMode (lines 248-385)

            IngestionModes' Responsibilities:
            ├─ Scheduled Data Fetching
            │  ├─ Batch: Poll every 1 hour
            │  ├─ Real-Time: Poll every 30 seconds
            │  └─ Streaming: Instant/continuous processing
            │
            ├─ Connector Integration
            │  ├─ Call external connectors to fetch data
            │  └─ Handle connector responses
            │
            ├─ Buffering & Batch Management
            │  ├─ Buffer records for efficient processing
            │  ├─ Flush buffers at configured intervals
            │  └─ Maintain optimal batch sizes
            │
            ├─ Loop State Management
            │  ├─ Track is_running flag
            │  ├─ Handle start/stop lifecycle
            │  └─ Graceful shutdown on stop
            │
            └─ Mode-Specific Metrics
                ├─ Track records processed
                ├─ Report last fetch/poll time
                └─ Count empty polls (real-time mode)

            Key Methods:
            → _batch_loop() - 1 hour intervals
            → _polling_loop() - 30 second intervals
            → _streaming_loop() - instant processing
            → _flush_buffer()

        ---
        QueueManager (stream_manager.py:400-500 approx)

            QueueManager's Responsibilities:
            ├─ Multi-Priority Queue System
            │  ├─ CRITICAL queue (<100ms latency target)
            │  ├─ HIGH queue (<1s latency target)
            │  ├─ NORMAL queue (<10s latency target)
            │  └─ LOW queue (<60s latency target)
            │
            ├─ Queue Operations
            │  ├─ Enqueue records with priority assignment
            │  ├─ Dequeue batches in priority order
            │  └─ Always process highest priority first
            │
            ├─ Capacity Management
            │  ├─ Track queue depths per priority
            │  ├─ Monitor total utilization (current/max)
            │  ├─ Drop oldest messages on overflow
            │  └─ Prevent memory exhaustion
            │
            ├─ Background Processing
            │  ├─ Run continuous queue processor loop
            │  ├─ Dequeue batches (500 records at once)
            │  └─ Send batches to ProducerWrapper
            │
            └─ Statistics & Reporting
                ├─ Track messages enqueued/dequeued
                ├─ Report queue depth per priority
                └─ Calculate queue utilization percentage

            Key Methods:
            → enqueue(record, priority)
            → dequeue_batch(max_size, priority)
            → _queue_processor_loop()
            → get_queue_depths()

        ---
        ThrottlingManager (stream_manager.py:500-600 approx)

            ThrottlingManager's Responsibilities:
            ├─ Queue Health Monitoring
            │  ├─ Monitor queue utilization (current/max capacity)
            │  ├─ Track total messages across all priorities
            │  └─ Calculate utilization percentage
            │
            ├─ Consumer Lag Estimation
            │  ├─ Estimate lag from queue depth
            │  ├─ Formula: lag = (utilization × base_lag_factor)
            │  └─ Predict processing delay
            │
            ├─ Throttle Severity Determination
            │  ├─ NONE: lag < 60s (proceed at full speed)
            │  ├─ MINOR: lag 60-120s (wait 60s)
            │  ├─ MODERATE: lag 120-300s (wait 120s)
            │  └─ SEVERE: lag > 300s (wait 240s)
            │
            ├─ Backpressure Application
            │  ├─ Return (should_throttle, wait_time) tuple
            │  ├─ Signal upstream components to slow down
            │  └─ Prevent queue overflow
            │
            └─ Adaptive Throttling
                ├─ Exponential backoff on high load
                ├─ Automatic recovery when load decreases
                └─ Real-time throttle adjustments

            Key Methods:
            → should_throttle()
            → estimate_consumer_lag()
            → determine_throttle_level()

        ---
        ProducerWrapper (stream_manager.py:686-848)

            ProducerWrapper's Responsibilities:
            ├─ Retry Logic with Exponential Backoff
            │  ├─ Attempt 1: Immediate
            │  ├─ Attempt 2: Wait 2 seconds (1s × 2¹)
            │  ├─ Attempt 3: Wait 4 seconds (1s × 2²)
            │  └─ Max retries: 3 attempts
            │
            ├─ Circuit Breaker Integration
            │  ├─ Check circuit state before each attempt
            │  ├─ CLOSED: Proceed normally
            │  ├─ OPEN: Reject immediately (60s timeout)
            │  └─ HALF_OPEN: Test with single request
            │
            ├─ Error Classification
            │  ├─ Retriable: Network errors, timeouts, rate limits
            │  ├─ Non-retriable: Schema validation, invalid data
            │  └─ Route accordingly
            │
            ├─ Dead Letter Queue Routing
            │  ├─ Detect permanent failures (max retries exceeded)
            │  ├─ Send to DLQ with error metadata
            │  ├─ Preserve original message for analysis
            │  └─ Track DLQ statistics
            │
            ├─ Failure Tracking
            │  ├─ Count consecutive failures
            │  ├─ Record failure timestamps
            │  └─ Report to circuit breaker
            │
            └─ Success Recovery
                ├─ Reset failure counters on success
                ├─ Notify circuit breaker
                └─ Return success metrics

            Key Methods:
            → send_batch_with_retry() (lines 733-800)
            → _classify_error()
            → _send_to_dlq() (lines 801-820)

        ---
        CircuitBreaker (stream_manager.py:650-684)

            CircuitBreaker's Responsibilities:
            ├─ State Machine Management
            │  ├─ CLOSED: Normal operation, all requests allowed
            │  ├─ OPEN: Failure detected, block all requests
            │  └─ HALF_OPEN: Testing recovery, allow 1 request
            │
            ├─ Failure Threshold Detection
            │  ├─ Track consecutive failures
            │  ├─ Threshold: 3 consecutive failures
            │  └─ Trigger: CLOSED → OPEN transition
            │
            ├─ Timeout & Recovery
            │  ├─ OPEN state timeout: 60 seconds
            │  ├─ After timeout: OPEN → HALF_OPEN
            │  └─ Test with single request
            │
            ├─ Recovery Testing
            │  ├─ Allow one test request in HALF_OPEN
            │  ├─ Success → HALF_OPEN → CLOSED (full recovery)
            │  └─ Failure → HALF_OPEN → OPEN (back to blocking)
            │
            ├─ Request Gating
            │  ├─ Check state before allowing requests
            │  ├─ Block requests when OPEN
            │  └─ Allow requests when CLOSED/HALF_OPEN
            │
            └─ Failure Tracking
                ├─ Record failure timestamps
                ├─ Count consecutive failures
                └─ Reset counter on success
            
            Key Methods:
            → allow_request()
            → record_success()
            → record_failure()
            → _should_attempt_reset()

        ---
        KafkaDataProducer (kafka_producer.py:47-1035)

            KafkaDataProducer's Responsibilities:
            ├─ Topic Routing (lines 732-807)
            │  ├─ Pattern matching on source_id
            │  ├─ firms_* → wildfire-nasa-firms
            │  ├─ noaa_* → wildfire-weather-data
            │  ├─ iot_* → wildfire-iot-sensors
            │  └─ 15+ topic routing rules
            │
            ├─ Geographic Partitioning (lines 834-864)
            │  ├─ Extract latitude/longitude from records
            │  ├─ Generate geohash-based partition keys
            │  ├─ Formula: geo_{lat_grid}_{lon_grid}
            │  └─ Enable spatial locality in storage
            │
            ├─ Data Serialization
            │  ├─ JSON: Convert dicts to UTF-8 bytes (lines 991-997)
            │  ├─ Binary: Raw bytes for images (no serializer)
            │  └─ Handle serialization errors gracefully
            │
            ├─ Compression Strategy (line 258)
            │  ├─ Critical alerts: No compression (lowest latency)
            │  ├─ IoT sensors: zstd level 1 (fast)
            │  ├─ NASA FIRMS: zstd level 3 (balanced)
            │  └─ Weather bulk: zstd level 6 (high compression)
            │
            ├─ Connection Management (lines 245-343)
            │  ├─ Start main JSON producer
            │  ├─ Start binary producer (for images)
            │  ├─ Initialize chunk manager
            │  ├─ Initialize S3 handler
            │  └─ Graceful shutdown on stop
            │
            ├─ Health Monitoring (lines 345-356)
            │  ├─ Check broker connectivity
            │  ├─ Verify producer is started
            │  └─ Report health status
            │
            ├─ Metadata Enrichment (lines 866-887)
            │  ├─ Add producer_id
            │  ├─ Add ingestion_timestamp
            │  ├─ Add source_type, source_id, source_name
            │  ├─ Add california_relevance flag
            │  └─ Add wildfire_context (fire_detected, etc.)
            │
            └─ Binary Image Routing
                ├─ <20MB: Direct transmission (lines 571-611)
                ├─ 20-100MB: Chunked transmission (lines 613-659)
                └─ >100MB: S3 upload with reference (lines 661-698)

            Key Methods:
            → _determine_topic()
            → _serialize_value()
            → _generate_partition_key()
            → start() / stop()
            → health_check()
            → _enrich_record()
            → send_satellite_image()
            → send_batch_data()

        ---
        BinaryImageSerializer (binary_serializer.py:18-351)

            BinaryImageSerializer's Responsibilities:
            ├─ Image Format Detection (lines 238-245)
            │  ├─ Magic byte signatures
            │  ├─ TIFF_LE: \x49\x49\x2A\x00
            │  ├─ TIFF_BE: \x4D\x4D\x00\x2A
            │  ├─ JP2: \x00\x00\x00\x0C\x6A\x50\x20\x20
            │  ├─ PNG: \x89\x50\x4E\x47
            │  └─ HDF5: \x89\x48\x44\x46
            │
            ├─ Binary Serialization (lines 59-137)
            │  ├─ Create 48-byte header
            │  ├─ Pack: version, format_code, flags, sizes, checksum
            │  ├─ Combine header + image_data
            │  └─ Return (metadata_bytes, image_packet, correlation_id)
            │
            ├─ Integrity Protection
            │  ├─ Calculate SHA-256 checksum of image data
            │  ├─ Embed checksum in packet header
            │  └─ Verify on deserialization (lines 184-187)
            │
            ├─ Correlation ID Generation
            │  ├─ Link metadata and binary data
            │  ├─ Format: {timestamp}_{size}_{partial_hash}
            │  └─ Enable reassembly of split data
            │
            ├─ Optional Compression
            │  ├─ Prefer zstandard (level 3)
            │  ├─ Fallback to zlib (level 6)
            │  └─ Only compress if >10% reduction
            │
            └─ Deserialization (lines 143-208)
                ├─ Parse 48-byte header
                ├─ Extract metadata and image data
                ├─ Decompress if FLAG_COMPRESSED set
                └─ Verify checksum integrity

            Key Methods:
            → serialize_image() (lines 59-137)
            → deserialize_image() (lines 143-208)
            → _detect_format() (lines 238-245)
            → is_image_data()

        ---
        ImageChunkManager (image_chunk_manager.py - imported)

            ImageChunkManager's Responsibilities:
            ├─ Image Chunking Strategy
            │  ├─ Target: 20-100MB images
            │  ├─ Chunk size: 5MB per chunk
            │  ├─ Calculate total_chunks: ceil(image_size / 5MB)
            │  └─ Create chunk sequence (0 to total_chunks-1)
            │
            ├─ Unique Image Identification
            │  ├─ Generate unique image_id per image
            │  ├─ Format: {source}_{timestamp}_{hash}
            │  └─ Link all chunks to same image_id
            │
            ├─ Chunk Header Creation
            │  ├─ image_id: Correlation identifier
            │  ├─ sequence: Chunk number (0-based)
            │  ├─ total_chunks: Total expected chunks
            │  ├─ chunk_data: 5MB binary slice
            │  └─ checksum: SHA-256 of chunk_data
            │
            ├─ Chunk Serialization
            │  ├─ Pack chunk metadata into binary header
            │  ├─ Combine header + chunk_data
            │  └─ Return serialized chunk for Kafka
            │
            ├─ Chunk Reassembly
            │  ├─ Collect all chunks with same image_id
            │  ├─ Sort by sequence number (0, 1, 2, ...)
            │  ├─ Verify checksums for each chunk
            │  ├─ Concatenate chunk_data in order
            │  └─ Return original complete image
            │
            └─ Integrity Validation
                ├─ Verify all chunks received
                ├─ Check sequence completeness (no gaps)
                ├─ Validate per-chunk checksums
                └─ Handle reassembly timeout (5 minutes)

            Key Methods:
            → create_chunks()
            → serialize_chunk()
            → reassemble_image()
            → validate_chunk_integrity()

        ---
        S3ReferenceHandler (s3_reference_handler.py - imported)

            S3ReferenceHandler's Responsibilities:
            ├─ Size-Based Upload Decision
            │  ├─ Threshold: Images >100MB
            │  ├─ Check: should_use_s3(image_size)
            │  └─ Return boolean decision
            │
            ├─ S3/MinIO Upload
            │  ├─ Compress image before upload (optional)
            │  ├─ Generate unique S3 object key
            │  ├─ Upload to configured bucket
            │  └─ Return S3 URL for retrieval
            │
            ├─ Reference Metadata Creation
            │  ├─ s3_url: Full path to stored image
            │  ├─ image_size_bytes: Original size
            │  ├─ checksum: SHA-256 for integrity
            │  ├─ storage_type: 's3_reference'
            │  └─ Minimal metadata for Kafka
            │
            ├─ Compression Management
            │  ├─ Optional pre-upload compression
            │  ├─ Track compression ratio
            │  └─ Store compressed size in metadata
            │
            └─ URL Generation
                ├─ Format: s3://{bucket}/{key}
                ├─ Or: https://{minio_endpoint}/{bucket}/{key}
                └─ Provide download URL for consumers

            Does NOT Handle:
            ✗ Direct Kafka sending
            ✗ Image chunking
            ✗ Kafka topic management

            Key Methods:
            → upload_image()
            → should_use_s3()
            → should_use_chunking()
            → create_reference_metadata()
