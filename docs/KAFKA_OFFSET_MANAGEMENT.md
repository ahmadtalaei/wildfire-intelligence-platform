# Kafka Consumer Offset Management Guide

## Overview

This guide explains how to prevent and resolve Kafka consumer offset issues that prevent message reprocessing.

## Problem

When a Kafka consumer is configured with `auto_offset_reset='earliest'` but has already consumed messages, it won't reprocess historical messages because:

1. **Committed Offsets**: The consumer has already committed its position in the topic
2. **Offset Reset Behavior**: `auto_offset_reset` only applies when there's NO committed offset for the consumer group
3. **Historical Messages**: Old messages remain in Kafka (within retention period) but are skipped

## Solutions

### 1. Environment-Based Configuration (Recommended for Production)

Control consumer behavior via environment variables in `docker-compose.yml`:

```yaml
data-storage-service:
  environment:
    - KAFKA_CONSUMER_GROUP_ID=data-storage-consumer
    - KAFKA_AUTO_OFFSET_RESET=earliest  # or 'latest'
```

**When to use:**
- `earliest`: Development/testing - process all messages from the beginning
- `latest`: Production - only process new messages from now on

**To change behavior:**
1. Update `KAFKA_AUTO_OFFSET_RESET` in docker-compose.yml
2. Delete the consumer group (see method 2)
3. Restart the service

### 2. Reset Consumer Group Offsets (Quick Fix)

Use the provided batch script to reset offsets:

```bash
# Reset to earliest (reprocess all messages)
reset-consumer-offsets.bat

# Reset to latest (skip old messages, start from now)
reset-consumer-offsets.bat data-storage-consumer wildfire-sensor-data latest

# Reset specific topic
reset-consumer-offsets.bat data-storage-consumer wildfire-weather-data earliest
```

**What it does:**
1. Stops the consumer service
2. Resets Kafka offsets for the consumer group
3. Restarts the service
4. Consumer begins processing from the specified position

### 3. Manual Offset Management

#### Check Current Offsets
```bash
docker-compose exec kafka kafka-consumer-groups \
  --bootstrap-server localhost:9092 \
  --group data-storage-consumer \
  --describe
```

#### Delete Consumer Group (Force Reset)
```bash
# Stop service first
docker-compose stop data-storage-service

# Delete consumer group
docker-compose exec kafka kafka-consumer-groups \
  --bootstrap-server localhost:9092 \
  --group data-storage-consumer \
  --delete

# Restart service
docker-compose start data-storage-service
```

#### Reset to Specific Offset
```bash
docker-compose exec kafka kafka-consumer-groups \
  --bootstrap-server localhost:9092 \
  --group data-storage-consumer \
  --topic wildfire-sensor-data \
  --reset-offsets --to-offset 100 \
  --execute
```

#### Reset to Specific DateTime
```bash
docker-compose exec kafka kafka-consumer-groups \
  --bootstrap-server localhost:9092 \
  --group data-storage-consumer \
  --topic wildfire-sensor-data \
  --reset-offsets --to-datetime 2025-09-30T00:00:00.000 \
  --execute
```

### 4. Dynamic Consumer Group IDs (Development Only)

For rapid development/testing, use timestamped consumer groups:

```python
# In KafkaDataConsumer.__init__
import time
group_id = f"data-storage-consumer-{int(time.time())}"
```

**Pros:**
- Each restart creates a new consumer group
- Always reprocesses all messages

**Cons:**
- Creates orphaned consumer groups
- Not suitable for production
- No offset tracking benefits

### 5. Dual-Mode Consumer (Advanced)

Implement separate consumers for historical and live data:

```python
# Historical data processor (runs once)
historical_consumer = KafkaDataConsumer(
    db_manager,
    auto_offset_reset='earliest',
    group_id='data-storage-historical'
)

# Live data processor (always running)
live_consumer = KafkaDataConsumer(
    db_manager,
    auto_offset_reset='latest',
    group_id='data-storage-live'
)
```

## Best Practices

### Development Environment
- Use `KAFKA_AUTO_OFFSET_RESET=earliest`
- Use `reset-consumer-offsets.bat` script when needed
- Reset offsets after code changes that affect message processing

### Production Environment
- Use `KAFKA_AUTO_OFFSET_RESET=latest`
- Never reset offsets without understanding impact
- Monitor consumer lag: `docker-compose exec kafka kafka-consumer-groups --describe`
- Set appropriate Kafka retention policies

### Testing New Code
1. Stop consumer service
2. Run `reset-consumer-offsets.bat` to reset to earliest
3. Deploy new code
4. Monitor logs for successful processing
5. Verify database records

## Troubleshooting

### Consumer Not Processing Messages
```bash
# Check consumer group status
docker-compose exec kafka kafka-consumer-groups \
  --bootstrap-server localhost:9092 \
  --group data-storage-consumer \
  --describe

# Look for:
# - LAG > 0: Messages waiting to be processed
# - LAG = 0: All messages consumed
# - No output: Consumer group doesn't exist or inactive
```

### Verify Message Availability
```bash
# Check topic has messages
docker-compose exec kafka kafka-run-class kafka.tools.GetOffsetShell \
  --broker-list localhost:9092 \
  --topic wildfire-sensor-data

# Sample messages
docker-compose exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic wildfire-sensor-data \
  --from-beginning \
  --max-messages 5
```

### Reset Not Working
1. Ensure service is stopped: `docker-compose stop data-storage-service`
2. Verify consumer group is inactive
3. Try deleting the entire consumer group
4. Check Kafka logs for errors

## Configuration Reference

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `KAFKA_CONSUMER_GROUP_ID` | `data-storage-consumer` | Consumer group identifier |
| `KAFKA_AUTO_OFFSET_RESET` | `earliest` | Where to start when no offset exists (`earliest`, `latest`, `none`) |
| `KAFKA_BOOTSTRAP_SERVERS` | `kafka:29092` | Kafka broker addresses |

### Consumer Group Naming Convention

- **Service-based**: `{service-name}-consumer` (e.g., `data-storage-consumer`)
- **Environment-based**: `{service-name}-{env}-consumer` (e.g., `data-storage-prod-consumer`)
- **Feature-based**: `{service-name}-{feature}-consumer` (e.g., `data-storage-historical-consumer`)

## Related Files

- `/reset-consumer-offsets.bat` - Offset reset script
- `/services/data-storage-service/src/config.py` - Configuration settings
- `/services/data-storage-service/src/services/kafka_consumer.py` - Consumer implementation
- `/docker-compose.yml` - Service configuration

## Additional Resources

- [Kafka Consumer Offset Management](https://kafka.apache.org/documentation/#consumerconfigs_auto.offset.reset)
- [Consumer Groups Documentation](https://kafka.apache.org/documentation/#intro_concepts_and_terms)