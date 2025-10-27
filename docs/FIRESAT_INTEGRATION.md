# FireSat Integration Guide

## Overview

This document provides comprehensive instructions for integrating FireSat ultra-high resolution satellite fire detection data into the Wildfire Intelligence Platform.

**FireSat** is a constellation of 50+ satellites designed to detect fires as small as 5x5 meters with a 20-minute global refresh rate. The system uses AI-powered thermal infrared imaging to identify wildfires in their earliest stages.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Architecture](#architecture)
3. [Data Sources](#data-sources)
4. [Configuration](#configuration)
5. [Setup Instructions](#setup-instructions)
6. [Usage Examples](#usage-examples)
7. [Database Schema](#database-schema)
8. [API Endpoints](#api-endpoints)
9. [Monitoring](#monitoring)
10. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- PostgreSQL with TimescaleDB and PostGIS extensions
- Kafka for data streaming
- Python 3.10+
- FireSat API key (optional - system works in mock mode without it)

### 5-Minute Setup

```batch
# 1. Run setup script
cd C:\dev\wildfire
scripts\setup_firesat.bat

# 2. Configure environment (optional)
copy services\data-ingestion-service\.env.firesat.example .env
# Edit .env and add your FIRESAT_API_KEY if available

# 3. Start services
docker-compose up -d

# 4. Test ingestion
python scripts\test_firesat_ingestion.py

# 5. Start streaming
python scripts\start_firesat_streaming.py
```

---

## Architecture

### Data Flow

```
FireSat API / Testbed
        ↓
FireSat Connector (with Mock Mode)
        ↓
Data Validation & Quality Scoring
        ↓
Kafka Producer (topic routing)
        ↓
Data Storage Service
        ↓
TimescaleDB (specialized tables)
        ↓
Dashboard / Analytics APIs
```

### Components

- **FireSat Connector** (`firesat_connector.py`): Main data ingestion connector
- **FireSat Client** (`firesat_client.py`): NOS Testbed integration and local simulator
- **Table Router** (`table_router.py`): Routes data to specialized PostgreSQL tables
- **Database Schema** (`012_create_firesat_tables.sql`): TimescaleDB hypertables and indexes
- **Test Suite** (`test_firesat_connector.py`): Comprehensive automated tests

---

## Data Sources

FireSat provides three primary data products:

### 1. Fire Detections (`firesat_detections`)

- **Update Frequency**: Every 20 minutes
- **Spatial Resolution**: 5 meters
- **Coverage**: Global (California-filtered for this platform)
- **Key Fields**:
  - Latitude/longitude
  - Brightness temperature (Kelvin)
  - Fire Radiative Power (MW)
  - AI confidence score (0-1)
  - Satellite ID
  - Data quality score
  - Anomaly flags

### 2. Fire Perimeters (`firesat_perimeters`)

- **Update Frequency**: Every 20 minutes
- **Spatial Resolution**: Sub-hectare accuracy
- **Format**: GeoJSON polygons
- **Key Fields**:
  - Fire ID
  - Perimeter geometry (polygon)
  - Area (hectares)
  - Perimeter length (km)
  - Confidence score

### 3. Thermal Imagery (`firesat_thermal`)

- **Update Frequency**: Scene-based
- **Spatial Resolution**: 5 meters
- **Storage**: Metadata in PostgreSQL, imagery in S3
- **Key Fields**:
  - Scene ID
  - Acquisition time
  - Scene bounds (polygon)
  - S3 bucket/key
  - Cloud cover %
  - Quality metrics

---

## Configuration

### Environment Variables

Copy `.env.firesat.example` to `.env` and configure:

#### Required Settings

```bash
# FireSat API Key (optional - mock mode works without it)
FIRESAT_API_KEY=your_api_key_here

# API URL
FIRESAT_API_URL=https://api.firesat.earthfirealliance.org/v1

# Mock mode (true/false)
FIRESAT_MOCK_MODE=false
```

#### Optional Settings

```bash
# Data quality thresholds
FIRESAT_MIN_CONFIDENCE=0.7
FIRESAT_MIN_DATA_QUALITY=0.6

# Geographic bounds (California)
FIRESAT_LAT_MIN=32.534156
FIRESAT_LAT_MAX=42.009518
FIRESAT_LON_MIN=-124.482003
FIRESAT_LON_MAX=-114.131211

# Polling intervals
FIRESAT_BATCH_INTERVAL_HOURS=6
FIRESAT_STREAMING_INTERVAL_SECONDS=60

# S3 storage
FIRESAT_S3_BUCKET=wildfire-firesat-thermal
FIRESAT_S3_REGION=us-west-2

# Kafka topics
FIRESAT_KAFKA_TOPIC_DETECTIONS=firesat.detections
FIRESAT_KAFKA_TOPIC_PERIMETERS=firesat.perimeters
FIRESAT_KAFKA_TOPIC_THERMAL=firesat.thermal
```

---

## Setup Instructions

### Step 1: Obtain FireSat API Access

1. Apply for Early Adopter access at: https://www.earthfirealliance.org/firesat-early-adopters
2. Receive API key via email
3. Add to `.env` file

**Note**: If you don't have an API key yet, the connector automatically runs in **Mock Mode**, generating realistic simulated data for development and testing.

### Step 2: Run Database Migration

```batch
# Using setup script (recommended)
scripts\setup_firesat.bat

# OR manually
docker-compose exec data-storage-service psql -U postgres -d wildfire_intelligence -f /migrations/012_create_firesat_tables.sql
```

This creates:
- `firesat_detections` hypertable
- `firesat_perimeters` hypertable
- `firesat_thermal_scenes` table
- `firesat_ingestion_metrics` table
- Indexes and continuous aggregates
- Helper functions

### Step 3: Register FireSat Connector

```bash
python scripts\register_firesat_connector.py
```

This:
- Registers all three FireSat data sources
- Creates connector instance
- Runs health check
- Saves configuration to `config/firesat_sources.json`

### Step 4: Verify Setup

```bash
# Test health check
curl http://localhost:8000/health

# Check that firesat connector is listed
curl http://localhost:8000/sources | grep firesat

# Run test ingestion
python scripts\test_firesat_ingestion.py
```

---

## Usage Examples

### Batch Ingestion

Fetch historical fire detection data:

```python
import asyncio
from datetime import date, timedelta
from connectors.firesat_connector import FireSatConnector
from models.ingestion import BatchConfig

async def fetch_detections():
    connector = FireSatConnector()

    config = BatchConfig(
        source_id="firesat_detections",
        start_date=date.today() - timedelta(days=7),
        end_date=date.today(),
        spatial_bounds={
            'lat_min': 32.534156,
            'lat_max': 42.009518,
            'lon_min': -124.482003,
            'lon_max': -114.131211
        },
        format="json"
    )

    detections = await connector.fetch_batch_data(config)
    print(f"Fetched {len(detections)} detections")

    return detections

asyncio.run(fetch_detections())
```

### Real-Time Streaming

Start continuous monitoring:

```python
import asyncio
from connectors.firesat_connector import FireSatConnector
from models.ingestion import StreamingConfig

async def start_monitoring():
    connector = FireSatConnector()

    config = StreamingConfig(
        source_id="firesat_detections",
        polling_interval_seconds=60
    )

    stream_id = await connector.start_streaming(config)
    print(f"Stream started: {stream_id}")

    # Monitor active streams
    while True:
        streams = await connector.get_active_streams()
        for stream in streams:
            print(f"Stream {stream['stream_id']}: "
                  f"{stream['records_received']} records")
        await asyncio.sleep(30)

asyncio.run(start_monitoring())
```

### Using the NOS Testbed Simulator

Generate simulated satellite passes and detections:

```python
from datetime import datetime, timedelta
from connectors.firesat_client import FireSatSimulator

simulator = FireSatSimulator(seed=42)

# Generate satellite passes for 24 hours
start_time = datetime.now()
end_time = start_time + timedelta(hours=24)

california_bounds = {
    'lat_min': 32.5,
    'lat_max': 42.0,
    'lon_min': -124.5,
    'lon_max': -114.1
}

passes = simulator.generate_satellite_passes(
    start_time, end_time, california_bounds
)

print(f"Generated {len(passes)} satellite passes")

# Simulate fire detections
detections = simulator.simulate_fire_detections(
    passes,
    fire_probability=0.15,
    bounds=california_bounds
)

print(f"Simulated {len(detections)} fire detections")

# Calculate coverage metrics
metrics = simulator.calculate_coverage_metrics(passes, 24)
print(f"Average revisit time: {metrics['avg_revisit_time_min']:.1f} minutes")
```

---

## Database Schema

### FireSat Detections Table

```sql
CREATE TABLE firesat_detections (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    location GEOGRAPHY(POINT, 4326),
    brightness_kelvin DOUBLE PRECISION,
    fire_radiative_power DOUBLE PRECISION,
    fire_area_m2 DOUBLE PRECISION,
    confidence DOUBLE PRECISION CHECK (confidence >= 0 AND confidence <= 1),
    ai_model_version VARCHAR(50),
    satellite_id VARCHAR(50),
    source_id VARCHAR(100) DEFAULT 'firesat_detections',
    data_quality DOUBLE PRECISION,
    anomaly_flags TEXT[],
    detection_id VARCHAR(100) UNIQUE
);
```

### Query Examples

**Get recent high-confidence detections in California:**

```sql
SELECT * FROM get_recent_firesat_detections_ca(24, 0.8);
```

**Detection heatmap (grid-based density):**

```sql
SELECT * FROM firesat_detection_heatmap(
    NOW() - INTERVAL '24 hours',
    NOW(),
    0.1  -- 0.1 degree grid cells
);
```

**Hourly statistics:**

```sql
SELECT
    hour,
    detection_count,
    avg_confidence,
    avg_frp,
    total_fire_area_m2
FROM firesat_detections_hourly
WHERE hour >= NOW() - INTERVAL '24 hours'
ORDER BY hour DESC;
```

---

## API Endpoints

### Health Check

```bash
GET /health
```

Response includes FireSat connector status.

### List Data Sources

```bash
GET /sources
```

Returns all configured data sources including FireSat.

### Start Streaming

```bash
POST /stream/start
Content-Type: application/json

{
  "source_id": "firesat_detections",
  "polling_interval_seconds": 60
}
```

### Stop Streaming

```bash
POST /stream/stop/{stream_id}
```

### Batch Ingestion

```bash
POST /ingest/batch
Content-Type: application/json

{
  "source_id": "firesat_detections",
  "start_date": "2025-10-01",
  "end_date": "2025-10-03",
  "format": "json"
}
```

---

## Monitoring

### Metrics

FireSat connector exposes Prometheus metrics:

- `firesat_detections_total` - Total detections ingested
- `firesat_ingestion_latency_seconds` - Ingestion latency
- `firesat_data_quality_score` - Average quality score
- `firesat_api_requests_total` - API request count
- `firesat_api_errors_total` - API error count

### Logs

Structured JSON logs include:

```json
{
  "timestamp": "2025-10-03T10:30:00Z",
  "level": "INFO",
  "connector": "firesat",
  "source_id": "firesat_detections",
  "records_fetched": 42,
  "avg_confidence": 0.89,
  "mock_mode": false
}
```

### Database Metrics

Query ingestion metrics:

```sql
SELECT
    source_id,
    ingestion_time,
    records_ingested,
    avg_confidence,
    avg_data_quality,
    status
FROM firesat_ingestion_metrics
ORDER BY ingestion_time DESC
LIMIT 10;
```

---

## Troubleshooting

### Issue: Connector running in Mock Mode

**Symptom**: Logs show "FireSat running in MOCK MODE"

**Solution**:
1. Check if `FIRESAT_API_KEY` is set in `.env`
2. Apply for Early Adopter access
3. Mock mode is intentional for development without API access

### Issue: No detections found

**Symptom**: Batch ingestion returns 0 records

**Possible Causes**:
1. No active fires in time period/region
2. Quality filters too strict
3. API connectivity issues

**Solutions**:
```bash
# Lower quality thresholds
FIRESAT_MIN_CONFIDENCE=0.5
FIRESAT_MIN_DATA_QUALITY=0.5

# Check health
python scripts/test_firesat_ingestion.py

# Verify geographic bounds
# Ensure bounds match California
```

### Issue: High latency

**Symptom**: Slow data ingestion

**Solutions**:
1. Reduce batch size: `FIRESAT_MAX_BATCH_SIZE=5000`
2. Increase timeout: `FIRESAT_REQUEST_TIMEOUT=60`
3. Enable caching in connector
4. Check network connectivity to FireSat API

### Issue: Database performance

**Symptom**: Slow queries on `firesat_detections`

**Solutions**:
```sql
-- Analyze table statistics
ANALYZE firesat_detections;

-- Rebuild indexes
REINDEX TABLE firesat_detections;

-- Check hypertable chunks
SELECT * FROM timescaledb_information.chunks
WHERE hypertable_name = 'firesat_detections';

-- Refresh continuous aggregates
CALL refresh_continuous_aggregate('firesat_detections_hourly', NULL, NULL);
```

### Issue: Mock data not realistic

**Symptom**: Simulated data doesn't match expected patterns

**Solution**: Adjust simulator parameters in `firesat_client.py`:

```python
simulator = FireSatSimulator(seed=42)
simulator.num_satellites = 50
simulator.revisit_time_minutes = 20
simulator.spatial_resolution_m = 5.0
```

---

## Additional Resources

- **FireSat Official Site**: https://www.earthfirealliance.org/firesat
- **FireSat+ NOS Testbed**: https://nost-tools.readthedocs.io/en/stable/examples/firesat/
- **Early Adopter Program**: https://www.earthfirealliance.org/firesat-early-adopters
- **API Documentation**: *(Coming soon - currently in Early Adopter phase)*
- **GitHub Issues**: https://github.com/your-org/wildfire-intelligence-platform/issues

---

## Support

For issues related to:

- **FireSat API**: Contact Earth Fire Alliance support
- **Integration issues**: Open GitHub issue or contact platform team
- **Bug reports**: Use the test suite and report with logs
- **Feature requests**: Submit via GitHub Issues

---

## Changelog

### Version 1.0.0 (October 2025)

- Initial FireSat integration
- Mock mode support
- Three data sources (detections, perimeters, thermal)
- TimescaleDB hypertables
- Continuous aggregates
- Comprehensive test suite
- NOS Testbed integration
- California-specific filtering

---

**Last Updated**: October 3, 2025
**Maintained By**: Wildfire Intelligence Platform Team
