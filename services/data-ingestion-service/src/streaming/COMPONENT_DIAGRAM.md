# StreamManager V2 - Component Architecture Diagram

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         StreamManagerV2                                  │
│                     (Orchestration Layer)                                │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                ┌───────────────────┼───────────────────┐
                │                   │                   │
                ▼                   ▼                   ▼
    ┌────────────────────┐ ┌────────────────┐ ┌────────────────────┐
    │  stream_config.py  │ │ api_client.py  │ │ ingestion_modes.py │
    │   ConfigManager    │ │ APIClient      │ │ IngestionMode      │
    │                    │ │ ConnectorAPI   │ │ BatchMode          │
    │ Loads YAML/JSON    │ │ Rate limiting  │ │ RealTimeMode       │
    │ Validates config   │ │ Caching        │ │ ContinuousMode     │
    └────────────────────┘ └────────────────┘ └────────────────────┘
                │                   │                   │
                └───────────────────┼───────────────────┘
                                    ▼
                        ┌────────────────────┐
                        │  queue_manager.py  │
                        │   QueueManager     │
                        │ Priority queuing   │
                        │ Overflow handling  │
                        └────────────────────┘
                                    │
                ┌───────────────────┼───────────────────┐
                │                   │                   │
                ▼                   ▼                   ▼
    ┌────────────────────┐ ┌────────────────┐ ┌────────────────────┐
    │throttling_mgr.py   │ │topic_resolver  │ │producer_wrapper.py │
    │ThrottlingManager   │ │TopicResolver   │ │ProducerWrapper     │
    │                    │ │                │ │                    │
    │Consumer lag check  │ │Pattern routing │ │Retry with backoff  │
    │Exponential backoff │ │Content routing │ │DLQ integration     │
    │Auto-recovery       │ │Custom mappings │ │Batch sending       │
    └────────────────────┘ └────────────────┘ └────────────────────┘
                                                        │
                                                        ▼
                                                  ┌──────────┐
                                                  │  Kafka   │
                                                  └──────────┘
```

---

## Data Flow Sequence

```
┌─────────────┐
│  External   │
│    API      │  (NASA FIRMS, NOAA, IoT Sensors)
└──────┬──────┘
       │
       │ (1) HTTP Request
       ▼
┌─────────────────────────────────────────────────────────────┐
│ api_client.py                                               │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ ConnectorAPIClient                                       │ │
│ │ • Rate limiting: 60 requests/min                         │ │
│ │ • Timeout: 30 seconds                                    │ │
│ │ • Response caching: 60s TTL                              │ │
│ └─────────────────────────────────────────────────────────┘ │
└──────┬──────────────────────────────────────────────────────┘
       │
       │ (2) Returns List[Dict]
       ▼
┌─────────────────────────────────────────────────────────────┐
│ ingestion_modes.py                                          │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ IngestionMode (Strategy Pattern)                         │ │
│ │                                                           │ │
│ │ ┌─────────────┐  ┌──────────────┐  ┌─────────────────┐ │ │
│ │ │ BatchMode   │  │ RealTimeMode │  │ ContinuousMode  │ │ │
│ │ │ (Scheduled) │  │ (Polling)    │  │ (Streaming)     │ │ │
│ │ └─────────────┘  └──────────────┘  └─────────────────┘ │ │
│ │                                                           │ │
│ │ Invokes: data_fetcher() → data_processor()               │ │
│ └─────────────────────────────────────────────────────────┘ │
└──────┬──────────────────────────────────────────────────────┘
       │
       │ (3) Enqueue individual records
       ▼
┌─────────────────────────────────────────────────────────────┐
│ queue_manager.py                                            │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ QueueManager (Priority Queue)                            │ │
│ │                                                           │ │
│ │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐ │ │
│ │  │CRITICAL  │  │   HIGH   │  │  NORMAL  │  │   LOW   │ │ │
│ │  │ Queue    │  │  Queue   │  │  Queue   │  │  Queue  │ │ │
│ │  └──────────┘  └──────────┘  └──────────┘  └─────────┘ │ │
│ │                                                           │ │
│ │  Max Size: 10,000  |  Overflow: drop_oldest              │ │
│ └─────────────────────────────────────────────────────────┘ │
└──────┬──────────────────────────────────────────────────────┘
       │
       │ (4) PriorityQueueConsumer dequeues batches
       ▼
┌─────────────────────────────────────────────────────────────┐
│ throttling_manager.py                                       │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ ThrottlingManager                                        │ │
│ │                                                           │ │
│ │  Consumer Lag Check:                                     │ │
│ │  ┌────────────────────────────────────────────────────┐ │ │
│ │  │ Lag < 1000    → Allow (no delay)                   │ │ │
│ │  │ Lag 1000-5000 → Moderate throttle (1s delay)       │ │ │
│ │  │ Lag > 5000    → Critical throttle (exponential)    │ │ │
│ │  │                 2^level seconds (2s, 4s, 8s, 16s)  │ │ │
│ │  └────────────────────────────────────────────────────┘ │ │
│ │                                                           │ │
│ │  If throttled → Re-enqueue messages to queue             │ │
│ └─────────────────────────────────────────────────────────┘ │
└──────┬──────────────────────────────────────────────────────┘
       │
       │ (5) If allowed, resolve topic
       ▼
┌─────────────────────────────────────────────────────────────┐
│ topic_resolver.py                                           │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ TopicResolver                                            │ │
│ │                                                           │ │
│ │  Resolution Order:                                       │ │
│ │  1. Custom mappings  (source_id → topic)                │ │
│ │  2. Content rules    (data.field == value → topic)      │ │
│ │  3. Pattern matching (regex on source_id → topic)       │ │
│ │  4. Default fallback (wildfire-default)                 │ │
│ └─────────────────────────────────────────────────────────┘ │
└──────┬──────────────────────────────────────────────────────┘
       │
       │ (6) Send to Kafka with retry
       ▼
┌─────────────────────────────────────────────────────────────┐
│ producer_wrapper.py                                         │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ ProducerWrapper                                          │ │
│ │                                                           │ │
│ │  Retry Logic:                                            │ │
│ │  ┌────────────────────────────────────────────────────┐ │ │
│ │  │ Attempt 1 → Fail → Wait 1s                         │ │ │
│ │  │ Attempt 2 → Fail → Wait 2s                         │ │ │
│ │  │ Attempt 3 → Fail → Wait 4s                         │ │ │
│ │  │ Max retries → Send to DLQ                          │ │ │
│ │  └────────────────────────────────────────────────────┘ │ │
│ │                                                           │ │
│ │  Batch Sending: Accumulate 500 records OR 5s timeout    │ │
│ └─────────────────────────────────────────────────────────┘ │
└──────┬──────────────────────────────────────────────────────┘
       │
       │ (7) Kafka write
       ▼
┌─────────────────────────────────────────────────────────────┐
│ Kafka Topics                                                │
│ ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│ │ wildfire-    │  │ wildfire-    │  │ wildfire-        │  │
│ │ weather-data │  │ iot-sensors  │  │ nasa-firms       │  │
│ │ (8 partitions│  │ (12 partitions│  │ (4 partitions)   │  │
│ └──────────────┘  └──────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## Component Initialization Flow

```
StreamManagerV2.__init__()
│
├─(1) Load Configuration
│     ├─ ConfigManager.load_from_file("stream_config.yaml")
│     └─ Parse: kafka, throttling, sources, topics configs
│
├─(2) Initialize Kafka Producer
│     └─ KafkaDataProducer(bootstrap_servers, client_id)
│
├─(3) Initialize Dead Letter Queue
│     └─ DeadLetterQueue() if enable_dlq
│
├─(4) Initialize ProducerWrapper
│     ├─ kafka_producer
│     ├─ dlq
│     ├─ max_retries=3
│     ├─ retry_backoff_base=2.0
│     └─ batch_size=500
│
├─(5) Initialize QueueManager
│     ├─ max_size=10000
│     ├─ overflow_strategy="drop_oldest"
│     └─ enable_priorities=True
│
├─(6) Initialize ThrottlingManager
│     ├─ min_send_rate=1.0
│     ├─ max_send_rate=1000.0
│     ├─ target_consumer_lag=1000
│     └─ critical_consumer_lag=5000
│
└─(7) Initialize TopicResolver
      └─ custom_mappings from config
```

---

## Stream Startup Flow

```
StreamManagerV2.start_stream(source_id, connector)
│
├─(1) Get source configuration
│     └─ self.config.sources[source_id]
│
├─(2) Create APIClient
│     ├─ ConnectorAPIClient(
│     │     source_id=source_id,
│     │     connector=connector,
│     │     rate_limit_per_minute=120,
│     │     timeout_seconds=30.0,
│     │     cache_ttl_seconds=60
│     └─ )
│
├─(3) Resolve Kafka topic
│     └─ TopicResolver.resolve_topic(source_id)
│
├─(4) Create IngestionMode
│     └─ IngestionModeFactory.create_mode(
│           mode="continuous_streaming",
│           config={polling_interval_seconds: 30, buffer_size: 100}
│         )
│
├─(5) Define data flow callbacks
│     ├─ data_fetcher() → Calls api_client.poll()
│     └─ data_processor() → Enqueues to queue_manager
│
├─(6) Start ingestion mode
│     └─ mode.start(data_fetcher, data_processor)
│
└─(7) Start queue consumer (if not already running)
      └─ PriorityQueueConsumer.start()
            ├─ Continuously dequeues batches
            ├─ Checks throttling
            ├─ Resolves topic
            └─ Sends via ProducerWrapper
```

---

## Configuration File Structure

```yaml
# stream_config.yaml

kafka:                             # ← KafkaConfig dataclass
  bootstrap_servers: "localhost:9092"
  compression_type: "gzip"
  batch_size: 500
  max_retries: 3
  retry_backoff_base: 2.0

throttling:                        # ← ThrottlingConfig dataclass
  enabled: true
  min_send_rate: 1.0
  max_send_rate: 1000.0
  target_consumer_lag: 1000
  critical_consumer_lag: 5000

queue_max_size: 10000              # ← StreamManagerConfig
queue_overflow_strategy: "drop_oldest"
enable_dlq: true
enable_metrics: true

topics:                            # ← Dict[str, TopicConfig]
  wildfire-weather-data:
    partitions: 8
    retention_ms: 259200000

sources:                           # ← Dict[str, SourceConfig]
  noaa_stations_california:
    source_type: "noaa_weather"
    enabled: true
    topic: "wildfire-weather-data"
    ingestion:                     # ← IngestionConfig
      mode: "continuous_streaming"
      polling_interval_seconds: 30
      buffer_size: 100
    rate_limit_per_minute: 120
    timeout_seconds: 30.0
    cache_ttl_seconds: 60
    custom_params:
      state: "CA"
      data_types: ["temperature", "humidity"]
```

---

## Metrics Collection Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ StreamManagerV2.get_metrics()                               │
└─────────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
        ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ producer_    │  │ queue_       │  │ throttling_  │
│ wrapper.     │  │ manager.     │  │ manager.     │
│ get_metrics()│  │ get_metrics()│  │ get_metrics()│
└──────────────┘  └──────────────┘  └──────────────┘
        │                 │                 │
        ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ • total_sent │  │ • size       │  │ • state      │
│ • failures   │  │ • enqueued   │  │ • level      │
│ • retries    │  │ • dequeued   │  │ • adjustments│
└──────────────┘  └──────────────┘  └──────────────┘

        ┌─────────────────┬─────────────────┐
        │                 │                 │
        ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ topic_       │  │ ingestion_   │  │ api_client.  │
│ resolver.    │  │ mode.        │  │ get_metrics()│
│ get_metrics()│  │ get_metrics()│  │              │
└──────────────┘  └──────────────┘  └──────────────┘
        │                 │                 │
        ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ • topic_usage│  │ • records    │  │ • success_rate│
│ • resolutions│  │ • errors     │  │ • cache_hits │
└──────────────┘  └──────────────┘  └──────────────┘
```

---

## Error Handling Flow

```
┌────────────────────────────────────────────────────────────┐
│ Error occurs during data processing                        │
└─────────────────────┬──────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
        ▼             ▼             ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ API Timeout  │ │ Kafka Send   │ │ Queue Full   │
│              │ │ Failure      │ │              │
└──────┬───────┘ └──────┬───────┘ └──────┬───────┘
       │                │                │
       ▼                ▼                ▼
┌─────────────────────────────────────────────┐
│ APIClient                                   │
│ • Retry with timeout                        │
│ • Return error to ingestion mode            │
└─────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────┐
│ ProducerWrapper                             │
│ • Exponential backoff retry (3 attempts)    │
│ • Send to DLQ if all retries fail           │
└─────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────┐
│ QueueManager                                │
│ • Apply overflow strategy (drop_oldest)     │
│ • Log dropped messages                      │
└─────────────────────────────────────────────┘
```

---

## Horizontal Scaling Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                         Load Balancer                         │
└───────────────────────┬──────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│StreamManager │ │StreamManager │ │StreamManager │
│ Instance 1   │ │ Instance 2   │ │ Instance 3   │
│              │ │              │ │              │
│ Sources:     │ │ Sources:     │ │ Sources:     │
│ • NOAA-CA    │ │ • FIRMS      │ │ • IoT-CA     │
│ • Weather-CA │ │ • Satellite  │ │ • PurpleAir  │
└──────┬───────┘ └──────┬───────┘ └──────┬───────┘
       │                │                │
       └────────────────┼────────────────┘
                        │
                        ▼
              ┌──────────────────┐
              │  Kafka Cluster   │
              │  (3 brokers)     │
              └──────────────────┘
```

---

## Component Dependencies Graph

```
stream_manager_v2.py
    │
    ├─→ stream_config.py
    │       ├─→ yaml (stdlib)
    │       ├─→ json (stdlib)
    │       └─→ dataclasses (stdlib)
    │
    ├─→ producer_wrapper.py
    │       ├─→ kafka_producer.py
    │       ├─→ dead_letter_queue.py
    │       └─→ aiokafka
    │
    ├─→ queue_manager.py
    │       ├─→ asyncio (stdlib)
    │       └─→ dataclasses (stdlib)
    │
    ├─→ throttling_manager.py
    │       ├─→ asyncio (stdlib)
    │       └─→ collections (deque)
    │
    ├─→ ingestion_modes.py
    │       ├─→ asyncio (stdlib)
    │       └─→ dataclasses (stdlib)
    │
    ├─→ topic_resolver.py
    │       └─→ re (stdlib)
    │
    └─→ api_client.py
            ├─→ asyncio (stdlib)
            └─→ time (stdlib)
```

---

## Key Design Patterns Used

| Pattern | Component | Purpose |
|---------|-----------|---------|
| **Strategy Pattern** | `ingestion_modes.py` | Plug-and-play ingestion modes |
| **Factory Pattern** | `IngestionModeFactory` | Create mode instances |
| **Wrapper Pattern** | `producer_wrapper.py` | Add retry logic to Kafka producer |
| **Decorator Pattern** | `api_client.py` | Add rate limiting and caching |
| **Queue Pattern** | `queue_manager.py` | Decouple producers from consumers |
| **Chain of Responsibility** | `topic_resolver.py` | Try multiple resolution strategies |
| **Observer Pattern** | Metrics collection | Components export observable metrics |
| **Circuit Breaker Pattern** | `throttling_manager.py` | Prevent overwhelming consumers |

---

## Summary

**All components are integrated** in `StreamManagerV2`:

✅ **7 modular components** working together seamlessly
✅ **Clear separation of concerns** (each component has single responsibility)
✅ **Configuration-driven** (no code changes for tuning)
✅ **Production-ready** (retry logic, DLQ, metrics, health checks)
✅ **Scalable** (horizontal scaling, Kubernetes-ready)

**This is not just a refactor plan—it's a fully implemented, working system.**
