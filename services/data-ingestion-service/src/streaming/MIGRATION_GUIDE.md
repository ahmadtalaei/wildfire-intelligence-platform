# StreamManager V1 → V2 Migration Guide

## Overview

This guide helps you migrate from the old monolithic `StreamManager` to the new refactored `StreamManagerV2` with all modular components.

---

## What Changed?

### Before (V1): Monolithic

```python
# Old way - Everything mixed together
stream_manager = StreamManager(kafka_producer)
stream_id = await stream_manager.start_streaming(connector, config)
```

**Problems**:
- All logic in one class (polling, sending, throttling, topic routing)
- No configuration file support
- Fixed ingestion mode (real-time only)
- No priority queuing
- No backpressure handling

### After (V2): Modular

```python
# New way - Configuration-driven with modular components
stream_manager = StreamManagerV2(config_file="stream_config.yaml")
await stream_manager.start()
stream_id = await stream_manager.start_stream("noaa_weather_ca", connector)
```

**Benefits**:
- ✅ 7 specialized components (single responsibility)
- ✅ YAML/JSON configuration (no code changes for tuning)
- ✅ 3 ingestion modes (batch, real-time, continuous streaming)
- ✅ Priority queuing (4 levels)
- ✅ Dynamic throttling (exponential backoff based on consumer lag)
- ✅ Comprehensive metrics and health checks

---

## Migration Paths

### Option 1: Use Backward Compatibility Wrapper (Easiest)

**No code changes required!** The compatibility wrapper converts V1 calls to V2 internally.

```python
# Your existing code continues to work
from streaming.stream_manager_v2 import StreamManager  # ← Same import, new implementation

kafka_producer = KafkaDataProducer("localhost:9092")
await kafka_producer.start()

stream_manager = StreamManager(kafka_producer)  # ← Compatibility wrapper

config = StreamingConfig(
    source_id="noaa_weather",
    polling_interval_seconds=30
)

stream_id = await stream_manager.start_streaming(connector, config)  # ← Old method still works
```

**What happens under the hood**:
- Creates default `StreamManagerConfig`
- Converts `StreamingConfig` to `SourceConfig`
- Uses all refactored components internally
- Returns same `stream_id` format

**When to use**: Quick migration with zero code changes

---

### Option 2: Migrate to V2 with Configuration File (Recommended)

**Migration steps**:

#### Step 1: Create Configuration File

```yaml
# config/stream_config.yaml

kafka:
  bootstrap_servers: "localhost:9092"
  client_id: "wildfire-stream-manager"
  compression_type: "gzip"
  batch_size: 500
  max_retries: 3
  retry_backoff_base: 2.0

throttling:
  enabled: true
  min_send_rate: 1.0
  max_send_rate: 1000.0
  target_consumer_lag: 1000
  critical_consumer_lag: 5000

queue_max_size: 10000
queue_overflow_strategy: "drop_oldest"
enable_dlq: true

sources:
  noaa_weather_ca:
    source_type: "noaa_weather"
    enabled: true
    topic: "wildfire-weather-data"
    ingestion:
      mode: "continuous_streaming"  # ← Choose: batch, real_time, continuous_streaming
      polling_interval_seconds: 30
      buffer_size: 100
    rate_limit_per_minute: 120
    timeout_seconds: 30.0
    cache_ttl_seconds: 60
```

#### Step 2: Update Code

**Before (V1)**:
```python
from streaming.stream_manager import StreamManager
from streaming.kafka_producer import KafkaDataProducer
from models.ingestion import StreamingConfig

# Initialize Kafka
kafka_producer = KafkaDataProducer("localhost:9092")
await kafka_producer.start()

# Create StreamManager
stream_manager = StreamManager(kafka_producer)

# Start streaming
config = StreamingConfig(
    source_id="noaa_weather",
    polling_interval_seconds=30
)

stream_id = await stream_manager.start_streaming(noaa_connector, config)
```

**After (V2)**:
```python
from streaming.stream_manager_v2 import StreamManagerV2
from connectors.noaa_connector import NOAAConnector

# Create StreamManager with config file
stream_manager = StreamManagerV2(config_file="config/stream_config.yaml")

# Start all components (Kafka, queue consumer, etc.)
await stream_manager.start()

# Create connector
noaa_connector = NOAAConnector(api_key="your_key")

# Start stream (source_id must be in config file)
stream_id = await stream_manager.start_stream(
    source_id="noaa_weather_ca",
    connector=noaa_connector
)

print(f"Stream started: {stream_id}")
```

#### Step 3: Monitor

```python
# Get comprehensive metrics
metrics = await stream_manager.get_metrics()

print(f"Active streams: {metrics['stream_manager']['active_streams']}")
print(f"Queue size: {metrics['queue']['size']}")
print(f"Throttle state: {metrics['throttling']['current_state']}")
print(f"Records sent: {metrics['producer']['total_sent']}")
print(f"Records failed: {metrics['producer']['total_failed']}")
```

#### Step 4: Graceful Shutdown

```python
# Stop specific stream
await stream_manager.stop_stream(stream_id)

# Or stop all streams and components
await stream_manager.stop()
```

**When to use**: Production deployment with full configuration control

---

### Option 3: Programmatic Configuration (No YAML file)

If you prefer to configure in code instead of YAML:

```python
from streaming.stream_manager_v2 import StreamManagerV2
from streaming.stream_config import (
    StreamManagerConfig,
    KafkaConfig,
    ThrottlingConfig,
    SourceConfig,
    IngestionConfig
)

# Build configuration programmatically
config = StreamManagerConfig(
    kafka=KafkaConfig(
        bootstrap_servers="localhost:9092",
        compression_type="gzip",
        batch_size=500,
        max_retries=3
    ),
    throttling=ThrottlingConfig(
        enabled=True,
        target_consumer_lag=1000,
        critical_consumer_lag=5000
    ),
    queue_max_size=10000,
    queue_overflow_strategy="drop_oldest",
    enable_dlq=True,
    sources={
        "noaa_weather_ca": SourceConfig(
            source_id="noaa_weather_ca",
            source_type="noaa_weather",
            enabled=True,
            topic="wildfire-weather-data",
            ingestion=IngestionConfig(
                mode="continuous_streaming",
                polling_interval_seconds=30,
                buffer_size=100
            ),
            rate_limit_per_minute=120,
            timeout_seconds=30.0,
            cache_ttl_seconds=60
        )
    }
)

# Initialize with config object
stream_manager = StreamManagerV2(config=config)
await stream_manager.start()

# Start stream
stream_id = await stream_manager.start_stream("noaa_weather_ca", connector)
```

**When to use**: Dynamic configuration or when YAML is not preferred

---

## Feature Comparison

| Feature | V1 | V2 |
|---------|----|----|
| **Configuration** | Code only | YAML/JSON/Code |
| **Ingestion Modes** | Real-time only | Batch, Real-time, Continuous streaming |
| **Rate Limiting** | Fixed per connector | Configurable per source + API client |
| **Throttling** | None | Dynamic with exponential backoff |
| **Priority Queuing** | None | 4 levels (CRITICAL, HIGH, NORMAL, LOW) |
| **Dead Letter Queue** | Manual handling | Automatic with retry |
| **Topic Routing** | Manual | Pattern + content + custom mappings |
| **Response Caching** | None | TTL-based per source |
| **Retry Logic** | Basic | Exponential backoff with configurable retries |
| **Metrics** | Basic Kafka metrics | Comprehensive per-component metrics |
| **Health Checks** | None | All components with detailed status |
| **Batch Sending** | Manual | Automatic with size and timeout triggers |
| **Overflow Handling** | None | 3 strategies (drop_oldest, drop_newest, block) |
| **Horizontal Scaling** | Limited | Full support (one manager per source) |

---

## Ingestion Mode Migration

### V1: Fixed Real-Time Mode

```python
# V1 - Always polls at fixed interval
config = StreamingConfig(
    source_id="weather",
    polling_interval_seconds=30  # Fixed
)
```

### V2: Choose Mode Based on Use Case

#### Batch Mode (Hourly/Daily)
**Best for**: Historical data, scheduled reports, large datasets

```yaml
sources:
  firms_historical:
    ingestion:
      mode: "batch"
      batch_size: 1000
      schedule_interval_seconds: 3600  # Every hour
```

#### Real-Time Mode (Frequent Polling)
**Best for**: Weather alerts, fire detections, time-sensitive data

```yaml
sources:
  noaa_alerts:
    ingestion:
      mode: "real_time"
      polling_interval_seconds: 30  # Every 30 seconds
      max_records_per_poll: 100
```

#### Continuous Streaming Mode (High-Frequency)
**Best for**: IoT sensors, live streams, high-volume data

```yaml
sources:
  iot_sensors:
    ingestion:
      mode: "continuous_streaming"
      polling_interval_seconds: 10  # Very frequent
      buffer_size: 200
      buffer_flush_interval_seconds: 5
```

---

## Configuration Migration Examples

### Example 1: Simple Source

**V1 Code**:
```python
config = StreamingConfig(
    source_id="noaa_weather",
    polling_interval_seconds=60
)
stream_id = await manager.start_streaming(connector, config)
```

**V2 YAML**:
```yaml
sources:
  noaa_weather:
    source_type: "noaa_weather"
    enabled: true
    topic: "wildfire-weather-data"
    ingestion:
      mode: "real_time"
      polling_interval_seconds: 60
    rate_limit_per_minute: 60
    timeout_seconds: 30.0
```

**V2 Code**:
```python
stream_id = await manager.start_stream("noaa_weather", connector)
```

---

### Example 2: Multiple Sources

**V1 Code** (required multiple manager instances):
```python
manager1 = StreamManager(kafka_producer)
stream_id1 = await manager1.start_streaming(noaa_connector, noaa_config)

manager2 = StreamManager(kafka_producer)
stream_id2 = await manager2.start_streaming(firms_connector, firms_config)

manager3 = StreamManager(kafka_producer)
stream_id3 = await manager3.start_streaming(iot_connector, iot_config)
```

**V2 YAML**:
```yaml
sources:
  noaa_weather_ca:
    source_type: "noaa_weather"
    enabled: true
    ingestion:
      mode: "continuous_streaming"
      polling_interval_seconds: 30

  firms_viirs:
    source_type: "nasa_firms"
    enabled: true
    ingestion:
      mode: "batch"
      batch_size: 1000
      schedule_interval_seconds: 3600

  iot_sensors:
    source_type: "iot_sensor"
    enabled: true
    ingestion:
      mode: "continuous_streaming"
      polling_interval_seconds: 60
```

**V2 Code** (single manager instance):
```python
manager = StreamManagerV2(config_file="stream_config.yaml")
await manager.start()

# Start all sources
stream_id1 = await manager.start_stream("noaa_weather_ca", noaa_connector)
stream_id2 = await manager.start_stream("firms_viirs", firms_connector)
stream_id3 = await manager.start_stream("iot_sensors", iot_connector)
```

---

## Throttling Migration

### V1: No Throttling

```python
# V1 - No backpressure handling
# If consumers lag, producer keeps sending and overwhelms them
```

### V2: Dynamic Throttling

```yaml
throttling:
  enabled: true
  min_send_rate: 1.0        # Minimum messages/second
  max_send_rate: 1000.0     # Maximum messages/second
  target_consumer_lag: 1000 # Target max lag
  critical_consumer_lag: 5000  # Critical lag threshold
  adjustment_factor: 1.5    # Exponential backoff factor
```

**What happens**:
1. **Normal lag (<1000)**: No throttling, full speed
2. **High lag (1000-5000)**: Fixed 1-second delay per batch
3. **Critical lag (>5000)**: Exponential backoff (2s, 4s, 8s, 16s)
4. **Recovery**: Automatically increases rate after 10 consecutive low-lag cycles

---

## Metrics Migration

### V1: Basic Metrics

```python
# V1 - Limited metrics
metrics = stream_manager.get_metrics()
# Returns: {'messages_sent': 1000}
```

### V2: Comprehensive Metrics

```python
# V2 - Detailed per-component metrics
metrics = await stream_manager.get_metrics()

# Returns:
{
    'stream_manager': {
        'active_streams': 3,
        'is_started': True
    },
    'producer': {
        'total_sent': 10000,
        'total_failed': 5,
        'retry_count': 12,
        'batches_sent': 20
    },
    'queue': {
        'size': 150,
        'enqueued': 10000,
        'dequeued': 9850,
        'dropped': 0,
        'utilization_percent': 1.5
    },
    'throttling': {
        'current_state': 'allow',
        'backoff_level': 0,
        'rate_adjustments': 5,
        'throttled_count': 2
    },
    'topic_resolver': {
        'custom_used': 100,
        'pattern_used': 500,
        'fallback_used': 10
    },
    'streams': {
        'noaa_weather_ca_20251012_143022_a1b2c3d4': {
            'mode': {
                'records_processed': 5000,
                'errors': 2,
                'uptime_seconds': 3600
            },
            'api_client': {
                'total_requests': 120,
                'success_rate': 98.3,
                'cache_hit_rate': 65.0
            },
            'records_processed': 5000
        }
    }
}
```

---

## Health Check Migration

### V1: No Health Checks

```python
# V1 - No built-in health checks
# Had to manually check Kafka connection
```

### V2: Comprehensive Health Checks

```python
# V2 - All components health checked
health = await stream_manager.health_check()

# Returns:
{
    'healthy': True,
    'components': {
        'producer': {
            'healthy': True,
            'kafka_connected': True
        },
        'queue': {
            'healthy': True,
            'size': 150,
            'utilization_percent': 1.5
        },
        'streams': {
            'active_count': 3,
            'healthy': True
        }
    }
}
```

---

## Common Migration Issues

### Issue 1: Source ID Not in Config

**Error**:
```
ValueError: Source not configured: noaa_weather
```

**Solution**: Add source to YAML config file
```yaml
sources:
  noaa_weather:  # ← Must match source_id in code
    source_type: "noaa_weather"
    enabled: true
    ingestion:
      mode: "real_time"
```

---

### Issue 2: Config File Not Found

**Error**:
```
FileNotFoundError: Config file not found: stream_config.yaml
```

**Solution**: Use absolute path or relative to working directory
```python
import os
config_path = os.path.join(os.path.dirname(__file__), "config", "stream_config.yaml")
stream_manager = StreamManagerV2(config_file=config_path)
```

---

### Issue 3: Kafka Not Started

**Error**:
```
RuntimeError: Failed to start Kafka producer
```

**Solution**: Ensure Kafka is running and bootstrap_servers is correct
```yaml
kafka:
  bootstrap_servers: "localhost:9092"  # ← Verify Kafka is running
```

Test connection:
```bash
docker exec wildfire-kafka kafka-broker-api-versions --bootstrap-server localhost:9092
```

---

### Issue 4: Source Disabled

**Error**:
```
ValueError: Source is disabled: noaa_weather
```

**Solution**: Enable source in config
```yaml
sources:
  noaa_weather:
    enabled: true  # ← Must be true
```

---

## Performance Tuning

### Tune Batch Size

```yaml
kafka:
  batch_size: 500  # ← Increase for higher throughput (100-1000)
```

**Trade-off**: Higher = better throughput, higher latency

---

### Tune Queue Size

```yaml
queue_max_size: 10000  # ← Increase for bursty traffic (5000-50000)
```

**Trade-off**: Higher = handles bursts better, more memory usage

---

### Tune Throttling Thresholds

```yaml
throttling:
  target_consumer_lag: 1000   # ← Lower = more aggressive throttling
  critical_consumer_lag: 5000 # ← Higher = tolerates more lag
```

---

### Tune Polling Interval

```yaml
sources:
  noaa_weather:
    ingestion:
      polling_interval_seconds: 30  # ← Decrease for fresher data (10-300)
```

**Trade-off**: Lower = fresher data, higher API usage

---

## Testing Migration

### Unit Test Example

```python
import pytest
from streaming.stream_manager_v2 import StreamManagerV2
from tests.mocks import MockConnector

@pytest.mark.asyncio
async def test_stream_manager_v2():
    # Create manager with test config
    config = {
        'kafka': {'bootstrap_servers': 'localhost:9092'},
        'sources': {
            'test_source': {
                'source_id': 'test_source',
                'source_type': 'test',
                'enabled': True,
                'ingestion': {'mode': 'real_time'}
            }
        }
    }

    manager = StreamManagerV2(config=config)
    await manager.start()

    # Start stream
    connector = MockConnector()
    stream_id = await manager.start_stream('test_source', connector)

    # Verify
    assert stream_id.startswith('test_source_')
    assert len(manager.active_streams) == 1

    # Stop
    await manager.stop()
```

---

## Rollback Plan

If migration fails, quickly rollback to V1:

```python
# Change import back to V1
from streaming.stream_manager import StreamManager  # ← Old implementation

# Use old code
kafka_producer = KafkaDataProducer("localhost:9092")
await kafka_producer.start()

stream_manager = StreamManager(kafka_producer)
stream_id = await stream_manager.start_streaming(connector, config)
```

---

## Summary

| Step | Task | Status |
|------|------|--------|
| 1 | Read this migration guide | ✅ |
| 2 | Choose migration path (Compatibility / Config file / Programmatic) | ⏳ |
| 3 | Create configuration file (if using Option 2) | ⏳ |
| 4 | Update code to use StreamManagerV2 | ⏳ |
| 5 | Test in development environment | ⏳ |
| 6 | Monitor metrics and health checks | ⏳ |
| 7 | Deploy to staging | ⏳ |
| 8 | Deploy to production | ⏳ |

---

## Need Help?

- **Documentation**: See `REFACTOR_README.md` for detailed component docs
- **Integration**: See `INTEGRATION_GUIDE.md` for how components work together
- **Architecture**: See `COMPONENT_DIAGRAM.md` for visual diagrams
- **Examples**: See `stream_config.example.yaml` for full config example

---

**Ready to migrate? Start with Option 1 (Compatibility Wrapper) for a risk-free migration!**
