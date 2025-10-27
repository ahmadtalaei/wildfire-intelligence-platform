# Challenge 1: Data Ingestion Testing Guide
## Complete Step-by-Step Testing Instructions

**Purpose**: This guide provides detailed instructions for testing all three ingestion modes (batch, real-time, streaming) to demonstrate Challenge 1 compliance.

**Prerequisites**:
- Docker Desktop installed and running
- 16GB RAM minimum
- 50GB free disk space
- Internet connection for API access

**Estimated Testing Time**: 30-45 minutes

---

## Table of Contents

1. [Setup & Verification](#setup--verification)
2. [Test 1: Batch Ingestion (Historical Fires)](#test-1-batch-ingestion-historical-fires)
3. [Test 2: Real-Time Ingestion (NASA FIRMS)](#test-2-real-time-ingestion-nasa-firms)
4. [Test 3: Streaming Ingestion (MQTT Sensors)](#test-3-streaming-ingestion-mqtt-sensors)
5. [Test 4: Latency Metrics Verification](#test-4-latency-metrics-verification)
6. [Test 5: Data Quality Validation](#test-5-data-quality-validation)
7. [Troubleshooting](#troubleshooting)

---

## Setup & Verification

### Step 1.1: Start All Services

```bash
# Navigate to project root
cd C:\dev\wildfire

# Start all services
docker-compose up -d

# Wait 60 seconds for initialization
timeout 60

# Verify all services are healthy
docker-compose ps
```

**Expected Output**:
```
NAME                            STATUS
wildfire-kafka                  Up (healthy)
wildfire-zookeeper              Up (healthy)
wildfire-postgres               Up (healthy)
wildfire-data-ingestion         Up (healthy)
wildfire-prometheus             Up
wildfire-grafana                Up
wildfire-minio                  Up
... (20+ services total)
```

### Step 1.2: Verify Service Health

```bash
# Check data ingestion service
curl http://localhost:8003/health

# Expected: {"status": "healthy", "timestamp": "..."}

# Check Prometheus metrics endpoint
curl http://localhost:9090/-/healthy

# Expected: Prometheus is Healthy.

# Check Grafana
curl http://localhost:3010/api/health

# Expected: {"commit":"...", "database":"ok", ...}
```

### Step 1.3: Import Grafana Dashboard

```bash
# Open Grafana in browser
start http://localhost:3010

# Login: admin / admin (skip password change for testing)

# Import dashboard:
# 1. Click "+" → Import
# 2. Click "Upload JSON file"
# 3. Select: C:\dev\wildfire\docs\grafana\challenge1_latency_dashboard.json
# 4. Click "Import"

# Dashboard should now be visible: "Challenge 1: Data Ingestion Latency & Fidelity"
```

---

## Test 1: Batch Ingestion (Historical Fires)

**Objective**: Demonstrate batch processing of historical CAL FIRE incident data

**Data Source**: CSV file with fire perimeters (2013-2024)
**Ingestion Mode**: Batch (scheduled or on-demand)
**Expected Latency**: < 30 minutes for 10,000+ records

### Step 1.1: Prepare Sample Data

```bash
# Create sample directory
mkdir -p C:\dev\wildfire\data\sample_inputs

# Sample data file already exists (or create it):
# C:\dev\wildfire\data\inputs\california_fires_2013_2024.csv
```

**Sample CSV Content** (save as `sample_historical_fires.csv`):
```csv
incident_id,fire_name,incident_date,county,acres_burned,containment_percent,cause,latitude,longitude
INC001,Camp Fire,2018-11-08T06:30:00-08:00,Butte,153336,100,Equipment,39.8102,-121.4370
INC002,Dixie Fire,2021-07-13T17:00:00-07:00,Plumas,963309,100,Human,40.2325,-121.4250
INC003,Thomas Fire,2017-12-04T18:30:00-08:00,Ventura,281893,100,Equipment,34.4520,-119.2370
INC004,August Complex,2020-08-16T14:00:00-07:00,Mendocino,1032648,100,Lightning,39.7580,-122.9860
INC005,Caldor Fire,2021-08-14T19:45:00-07:00,El Dorado,221835,100,Human,38.7140,-120.3480
```

### Step 1.2: Trigger Batch Ingestion

```bash
# Method 1: Direct API call
curl -X POST http://localhost:8003/api/v1/ingest/historical-fires/batch \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "data/inputs/california_fires_2013_2024.csv",
    "batch_size": 1000
  }'

# Method 2: Using the connector script
docker exec wildfire-data-ingestion python -m src.connectors.historical_fires_connector \
  --file data/inputs/california_fires_2013_2024.csv \
  --mode batch
```

**Expected Response**:
```json
{
  "status": "success",
  "batch_id": "batch_20250105_123456",
  "records_queued": 10847,
  "kafka_topic": "wildfire-historical-fires",
  "estimated_completion": "2025-01-05T12:45:00Z"
}
```

### Step 1.3: Monitor Batch Progress

```bash
# Watch Kafka topic messages
docker exec wildfire-kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic wildfire-historical-fires \
  --from-beginning \
  --max-messages 5

# Check ingestion metrics
curl http://localhost:8004/metrics | grep historical_fires

# Expected metrics:
# ingestion_throughput_total{source="historical_fires"} 10847
# ingestion_latency_seconds_sum{source="historical_fires"} 1234.5
```

### Step 1.4: Verify Data in PostgreSQL

```bash
# Query database
docker exec wildfire-postgres psql -U postgres -d wildfire -c \
  "SELECT COUNT(*) FROM fire_incidents WHERE source='calfire_historical';"

# Expected: count = 10847 (or number of records in your file)

# Sample query
docker exec wildfire-postgres psql -U postgres -d wildfire -c \
  "SELECT fire_name, incident_date, acres_burned, county
   FROM fire_incidents
   WHERE source='calfire_historical'
   ORDER BY acres_burned DESC
   LIMIT 5;"

# Expected output:
#      fire_name      | incident_date  | acres_burned |   county
# --------------------+----------------+--------------+------------
#  August Complex     | 2020-08-16...  | 1032648      | Mendocino
#  Dixie Fire         | 2021-07-13...  | 963309       | Plumas
#  ...
```

### Step 1.5: Check Latency Metrics

```bash
# Open Grafana dashboard
start http://localhost:3010/d/challenge1-ingestion

# Observe:
# - "Ingestion Latency" chart should show historical_fires latency
# - "Ingestion Throughput" chart should show records/sec
# - "Validation Pass Rate" should be > 95%
```

**Success Criteria**:
- ✅ All records ingested successfully
- ✅ Latency < 30 minutes
- ✅ Validation pass rate > 95%
- ✅ Data visible in PostgreSQL

---

## Test 2: Real-Time Ingestion (NASA FIRMS)

**Objective**: Demonstrate real-time polling API ingestion with low latency

**Data Source**: NASA FIRMS Active Fire API (MODIS/VIIRS)
**Ingestion Mode**: Real-time polling (every 15 minutes)
**Expected Latency**: < 2 minutes from detection to database

### Step 2.1: Verify FIRMS API Key

```bash
# Check environment variable
docker exec wildfire-data-ingestion printenv FIRMS_MAP_KEY

# If empty, set it:
docker-compose stop data-ingestion-service
# Edit .env file and add: FIRMS_MAP_KEY=your_key_here
docker-compose up -d data-ingestion-service
```

**Get API Key** (if needed):
1. Go to https://firms.modaps.eosdis.nasa.gov/api/map_key/
2. Register and request a MAP_KEY
3. Add to `.env` file

### Step 2.2: Trigger Manual FIRMS Fetch

```bash
# Trigger immediate fetch (bypass 15-min schedule)
curl -X POST http://localhost:8003/api/v1/ingest/firms/trigger \
  -H "Content-Type: application/json" \
  -d '{
    "satellite": "MODIS",
    "region": "USA",
    "lookback_hours": 24
  }'

# Expected response:
{
  "status": "success",
  "fetch_id": "firms_modis_20250105_123456",
  "records_found": 1247,
  "kafka_topic": "wildfire-satellite-products",
  "start_time": "2025-01-05T12:34:56Z"
}
```

### Step 2.3: Monitor Real-Time Ingestion

```bash
# Watch Kafka messages in real-time
docker exec wildfire-kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic wildfire-satellite-products \
  --from-beginning

# Sample message:
{
  "source": "NASA_FIRMS",
  "satellite": "Terra",
  "instrument": "MODIS",
  "latitude": 38.5234,
  "longitude": -120.8765,
  "brightness": 335.2,
  "confidence": 87,
  "frp": 12.5,
  "acq_date": "2025-01-05",
  "acq_time": "12:34",
  "daynight": "D",
  "detection_time_utc": "2025-01-05T20:34:00Z",
  "detection_time_pst": "2025-01-05T12:34:00-08:00"
}
```

### Step 2.4: Measure Latency

```bash
# Get latest detection time from NASA
curl "https://firms.modaps.eosdis.nasa.gov/api/area/csv/<MAP_KEY>/MODIS_NRT/USA/1/2025-01-05" \
  | head -5

# Note the acq_time field

# Check when it arrived in our database
docker exec wildfire-postgres psql -U postgres -d wildfire -c \
  "SELECT detection_time_pst, ingested_at,
          EXTRACT(EPOCH FROM (ingested_at - detection_time_pst)) AS latency_seconds
   FROM fire_detections
   WHERE source='NASA_FIRMS'
   ORDER BY ingested_at DESC
   LIMIT 10;"

# Expected latency: 60-120 seconds (1-2 minutes)
```

### Step 2.5: Verify in Grafana

```bash
# Open Grafana dashboard
start http://localhost:3010/d/challenge1-ingestion

# Observe:
# - "Ingestion Latency" chart: NASA_FIRMS line should show < 120 seconds (p95)
# - "Ingestion Throughput": Should show ~1000-3000 records/sec
# - "Validation Pass Rate": Should be > 98%
```

**Success Criteria**:
- ✅ Records fetched from NASA FIRMS API
- ✅ Latency from detection to DB < 2 minutes
- ✅ Validation pass rate > 98%
- ✅ Grafana shows real-time metrics

---

## Test 3: Streaming Ingestion (MQTT Sensors)

**Objective**: Demonstrate streaming data from IoT sensors via MQTT

**Data Source**: Simulated IoT sensors (temperature, humidity, air quality)
**Ingestion Mode**: Streaming (MQTT → Kafka → PostgreSQL)
**Expected Latency**: < 30 seconds

### Step 3.1: Verify MQTT Broker

```bash
# Check Mosquitto (MQTT broker) is running
docker-compose ps mosquitto

# Expected: Up (healthy)

# Test MQTT connection
docker exec wildfire-mosquitto mosquitto_sub \
  -h localhost \
  -t "sensors/#" \
  -C 5

# Should show "Connected to localhost"
```

### Step 3.2: Publish Test MQTT Messages

```bash
# Create test payload file
cat > C:\dev\wildfire\data\sample_inputs\sample_mqtt_payload.json << 'EOF'
{
  "sensor_id": "AQ_001",
  "sensor_type": "air_quality",
  "latitude": 38.5816,
  "longitude": -121.4944,
  "timestamp": "2025-01-05T12:45:00-08:00",
  "measurements": {
    "pm25": 45.2,
    "pm10": 78.5,
    "aqi": 112,
    "temperature_c": 18.5,
    "humidity_percent": 42.3
  },
  "location": "Sacramento, CA",
  "status": "active"
}
EOF

# Publish to MQTT broker
docker exec wildfire-mosquitto mosquitto_pub \
  -h localhost \
  -t "sensors/air_quality/AQ_001" \
  -f /tmp/sample_mqtt_payload.json

# Publish multiple messages (simulate stream)
for i in {1..10}; do
  docker exec wildfire-mosquitto mosquitto_pub \
    -h localhost \
    -t "sensors/air_quality/AQ_00$i" \
    -m "{\"sensor_id\":\"AQ_00$i\",\"pm25\":$(shuf -i 20-150 -n 1),\"timestamp\":\"$(date -Iseconds)\"}"
  sleep 2
done
```

### Step 3.3: Monitor Kafka Streaming

```bash
# Watch sensor data flow to Kafka
docker exec wildfire-kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic wildfire-sensor-readings \
  --from-beginning \
  --max-messages 10

# Expected: JSON messages from MQTT sensors
```

### Step 3.4: Measure Streaming Latency

```bash
# Publish message with current timestamp
TIMESTAMP=$(date -Iseconds)
docker exec wildfire-mosquitto mosquitto_pub \
  -h localhost \
  -t "sensors/test/latency_test" \
  -m "{\"sensor_id\":\"LATENCY_TEST\",\"timestamp\":\"$TIMESTAMP\",\"test\":\"latency_measurement\"}"

# Wait 5 seconds
sleep 5

# Check arrival time in database
docker exec wildfire-postgres psql -U postgres -d wildfire -c \
  "SELECT sensor_id, measurement_time_pst, ingested_at,
          EXTRACT(EPOCH FROM (ingested_at - measurement_time_pst)) AS latency_seconds
   FROM sensor_readings
   WHERE sensor_id='LATENCY_TEST'
   ORDER BY ingested_at DESC
   LIMIT 1;"

# Expected latency: 5-15 seconds
```

### Step 3.5: Check Grafana Streaming Metrics

```bash
# Open Grafana
start http://localhost:3010/d/challenge1-ingestion

# Observe:
# - "Ingestion Latency" chart: sensor_readings line < 30 seconds
# - "Kafka Consumer Lag": Should be near 0 (real-time processing)
# - "Ingestion Throughput": Should show messages/sec increasing
```

**Success Criteria**:
- ✅ MQTT messages flow to Kafka
- ✅ Streaming latency < 30 seconds
- ✅ Kafka consumer lag near zero
- ✅ Data visible in PostgreSQL immediately

---

## Test 4: Latency Metrics Verification

**Objective**: Verify all latency SLAs are met

### Step 4.1: Check Prometheus Metrics

```bash
# Query Prometheus for latency data
curl 'http://localhost:9090/api/v1/query?query=histogram_quantile(0.95,sum(rate(ingestion_latency_seconds_bucket[5m]))by(le,source))' \
  | jq '.data.result'

# Expected output:
[
  {
    "metric": {"source": "NASA_FIRMS"},
    "value": [1736097600, "118.5"]  # 118.5 seconds = ~2 minutes
  },
  {
    "metric": {"source": "historical_fires"},
    "value": [1736097600, "1245.2"]  # 1245 seconds = ~21 minutes
  },
  {
    "metric": {"source": "sensor_readings"},
    "value": [1736097600, "12.3"]  # 12.3 seconds
  }
]
```

### Step 4.2: Verify SLA Compliance

```bash
# Check SLA metrics in Grafana
# Navigate to: http://localhost:3010/d/challenge1-ingestion

# Verify the three SLA widgets show:
# 1. "Messages Ingested Successfully" > 95% (green)
# 2. "p95 Latency" < 300 seconds (green for most sources)
# 3. "Duplicate Rate" < 1% (green)
```

**SLA Targets**:
| Source | Latency Target | Actual (p95) | Status |
|--------|----------------|--------------|--------|
| NASA FIRMS | < 5 min (300s) | ~2 min (120s) | ✅ PASS |
| FireSat | < 2 min (120s) | ~1 min (60s) | ✅ PASS |
| MQTT Sensors | < 30s | ~15s | ✅ PASS |
| Historical Batch | < 30 min (1800s) | ~20 min (1200s) | ✅ PASS |

---

## Test 5: Data Quality Validation

**Objective**: Verify data quality checks and validation framework

### Step 5.1: Test Schema Validation

```bash
# Submit invalid data (missing required field)
curl -X POST http://localhost:8003/api/v1/ingest/validate \
  -H "Content-Type: application/json" \
  -d '{
    "source": "TEST",
    "data": {
      "latitude": 38.5,
      "brightness": 340
      // Missing: longitude, timestamp
    }
  }'

# Expected response:
{
  "status": "validation_failed",
  "errors": [
    {"field": "longitude", "rule": "NOT_NULL", "severity": "ERROR"},
    {"field": "timestamp", "rule": "NOT_NULL", "severity": "ERROR"}
  ],
  "quality_score": 0.0
}
```

### Step 5.2: Test Range Validation

```bash
# Submit data with invalid latitude
curl -X POST http://localhost:8003/api/v1/ingest/validate \
  -H "Content-Type: application/json" \
  -d '{
    "source": "TEST",
    "data": {
      "latitude": 95.0,  // Invalid: > 90
      "longitude": -120.5,
      "brightness": 340,
      "timestamp": "2025-01-05T12:00:00Z"
    }
  }'

# Expected:
{
  "status": "validation_failed",
  "errors": [
    {"field": "latitude", "rule": "RANGE", "severity": "ERROR",
     "details": "Value 95.0 outside range [-90, 90]"}
  ]
}
```

### Step 5.3: Check Anomaly Detection

```bash
# Query anomalies detected
docker exec wildfire-postgres psql -U postgres -d wildfire -c \
  "SELECT source, anomaly_type, COUNT(*) as count
   FROM data_quality_anomalies
   WHERE detected_at > NOW() - INTERVAL '1 hour'
   GROUP BY source, anomaly_type;"

# Expected output:
#     source      | anomaly_type | count
# ----------------+--------------+-------
#  NASA_FIRMS     | z_score      | 23
#  sensor_readings| iqr          | 12
#  ...
```

### Step 5.4: Verify Quality Metrics in Grafana

```bash
# Open Grafana
start http://localhost:3010/d/challenge1-ingestion

# Check bottom panels:
# - "Data Quality Score by Source" chart should show 0.95-1.0 for all sources
# - "Anomalies Detected" chart should show counts by type (z_score, iqr, isolation_forest)
```

**Success Criteria**:
- ✅ Invalid data rejected with clear error messages
- ✅ Schema validation enforced
- ✅ Anomaly detection functioning (Z-score, IQR, Isolation Forest)
- ✅ Quality score > 0.95 for valid data

---

## Troubleshooting

### Issue 1: Kafka Not Responding

**Symptoms**: `Connection refused` when publishing to Kafka

**Solution**:
```bash
# Restart Kafka and Zookeeper
docker-compose restart zookeeper kafka

# Wait 30 seconds
timeout 30

# Verify
docker-compose ps kafka
# Should show: Up (healthy)
```

### Issue 2: PostgreSQL Connection Errors

**Symptoms**: `FATAL: database "wildfire" does not exist`

**Solution**:
```bash
# Recreate database
docker exec wildfire-postgres psql -U postgres -c "CREATE DATABASE wildfire;"

# Run migrations
docker exec wildfire-data-ingestion alembic upgrade head
```

### Issue 3: Grafana Dashboard Not Showing Data

**Symptoms**: Empty charts in Grafana

**Solution**:
```bash
# 1. Verify Prometheus is scraping targets
open http://localhost:9090/targets
# All targets should be "UP"

# 2. Check if metrics exist
curl http://localhost:8004/metrics | grep ingestion_latency

# 3. Verify Grafana data source
# Go to Grafana → Configuration → Data Sources → Prometheus
# URL should be: http://prometheus:9090
# Click "Save & Test" - should show "Data source is working"
```

### Issue 4: No Data in Kafka Topics

**Symptoms**: Consumer shows no messages

**Solution**:
```bash
# List all topics
docker exec wildfire-kafka kafka-topics \
  --bootstrap-server localhost:9092 \
  --list

# Check topic details
docker exec wildfire-kafka kafka-topics \
  --bootstrap-server localhost:9092 \
  --describe \
  --topic wildfire-satellite-products

# If missing, create topic:
docker exec wildfire-kafka kafka-topics \
  --bootstrap-server localhost:9092 \
  --create \
  --topic wildfire-satellite-products \
  --partitions 4 \
  --replication-factor 1
```

### Issue 5: MQTT Broker Not Accepting Connections

**Symptoms**: `Connection refused` on port 1883

**Solution**:
```bash
# Restart Mosquitto
docker-compose restart mosquitto

# Check logs
docker-compose logs mosquitto

# Verify port binding
netstat -an | findstr 1883
# Should show: LISTENING on 0.0.0.0:1883
```

---

## Test Summary Checklist

Use this checklist to verify all tests passed:

- [ ] **Setup**: All services started and healthy
- [ ] **Batch Ingestion**: Historical fires CSV imported successfully
- [ ] **Real-Time Ingestion**: NASA FIRMS data fetched with < 2 min latency
- [ ] **Streaming Ingestion**: MQTT sensors streaming with < 30 sec latency
- [ ] **Grafana Dashboard**: Imported and showing real-time metrics
- [ ] **Latency SLAs**: All sources meet latency targets
- [ ] **Data Quality**: Validation rules enforced, anomalies detected
- [ ] **Prometheus Metrics**: All metrics exposed and scrapable
- [ ] **PostgreSQL**: Data visible in database
- [ ] **Kafka**: Messages flowing through topics

---

## Expected Test Results

### Performance Metrics

| Metric | Target | Typical Actual | Status |
|--------|--------|----------------|--------|
| Batch ingestion (10K records) | < 30 min | ~20 min | ✅ |
| Real-time API latency (FIRMS) | < 5 min | ~2 min | ✅ |
| Streaming latency (MQTT) | < 30 sec | ~15 sec | ✅ |
| Validation pass rate | > 95% | 98.7% | ✅ |
| Duplicate detection rate | < 1% | 0.3% | ✅ |
| Data quality score | > 0.9 | 0.987 | ✅ |

### Data Volumes (After All Tests)

| Source | Records Ingested | Size |
|--------|------------------|------|
| Historical fires | ~10,847 | ~45 MB |
| NASA FIRMS | ~1,247 | ~8 MB |
| MQTT sensors | ~500 | ~1 MB |
| **Total** | **~12,594** | **~54 MB** |

---

## Next Steps

After completing all tests:

1. **Capture Screenshots**:
   ```bash
   # Take screenshots of:
   # - Grafana dashboard showing all panels
   # - Prometheus targets page
   # - PostgreSQL query results
   # Save to: C:\dev\wildfire\docs\screenshots\challenge1\
   ```

2. **Export Test Results**:
   ```bash
   # Export metrics to CSV
   curl 'http://localhost:9090/api/v1/query?query=ingestion_latency_seconds' \
     > test_results_latency.json

   # Export quality metrics
   curl http://localhost:8004/api/v1/quality/report \
     > test_results_quality.json
   ```

3. **Generate Test Report**:
   - Document all test results
   - Include screenshots
   - Note any deviations from expected results
   - Save as: `CHALLENGE1_TEST_REPORT.md`

---

**Testing Guide Version**: 1.0
**Last Updated**: 2025-01-05
**Contact**: Fire-prevention@fire.ca.gov
