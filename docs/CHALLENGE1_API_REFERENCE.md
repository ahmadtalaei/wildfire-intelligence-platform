# Challenge 1: API Reference Guide
## Data Ingestion Service - Complete API Documentation

**Purpose**: Consolidated API documentation for Challenge 1 Deliverable #13
**Base URL**: http://localhost:8003
**API Version**: v1
**Interactive Docs**: http://localhost:8003/docs (Swagger UI)
**Last Updated**: 2025-01-05

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Authentication](#authentication)
3. [Ingestion Endpoints](#ingestion-endpoints)
4. [Query Endpoints](#query-endpoints)
5. [Health & Monitoring](#health--monitoring)
6. [Error Responses](#error-responses)
7. [Rate Limits](#rate-limits)
8. [Code Examples](#code-examples)

---

## Quick Start

### Base URLs

| Environment | Base URL | Status |
|-------------|----------|--------|
| **Development** | http://localhost:8003 | ✅ Running |
| **Docker Container** | http://data-ingestion-service:8003 | ✅ Running |
| **Production** (future) | https://api.calfire.gov/ingestion | 🔜 Planned |

### Interactive Documentation

**Swagger UI**: http://localhost:8003/docs
- Try all endpoints interactively
- See request/response schemas
- Test with real data

**ReDoc**: http://localhost:8003/redoc
- Alternative documentation UI
- Better for reading/printing

---

## Authentication

### Current (Development)

**No authentication required** for localhost testing.

### Future (Production)

```http
Authorization: Bearer <JWT_TOKEN>
X-API-Key: <API_KEY>
```

**Obtain JWT Token**:
```bash
curl -X POST http://localhost:8003/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin@calfire.gov", "password": "admin"}'
```

**Response**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

---

## Ingestion Endpoints

### 1. Trigger NASA FIRMS Ingestion

**Endpoint**: `POST /api/v1/ingest/firms/trigger`

**Description**: Fetch latest fire detections from NASA FIRMS API (last 24 hours)

**Request**:
```http
POST /api/v1/ingest/firms/trigger HTTP/1.1
Host: localhost:8003
Content-Type: application/json

{
  "area": "california",
  "lookback_hours": 24
}
```

**Response**:
```json
{
  "status": "success",
  "message": "NASA FIRMS ingestion triggered",
  "job_id": "firms_job_20250105_013047",
  "detections_fetched": 127,
  "detections_valid": 125,
  "detections_duplicate": 2,
  "processing_time_ms": 847,
  "next_poll_at": "2025-01-05T02:30:47Z"
}
```

**cURL Example**:
```bash
curl -X POST http://localhost:8003/api/v1/ingest/firms/trigger \
  -H "Content-Type: application/json" \
  -d '{"area": "california", "lookback_hours": 24}'
```

**Query Parameters**:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `area` | string | "california" | Geographic area (california, usa, global) |
| `lookback_hours` | integer | 24 | Hours of historical data to fetch (1-72) |

**Status Codes**:
- `200`: Success
- `429`: Rate limit exceeded (NASA FIRMS: 1,000 req/hour)
- `503`: NASA FIRMS API unavailable

---

### 2. Batch Upload Historical Fires

**Endpoint**: `POST /api/v1/ingest/historical-fires/batch`

**Description**: Upload CSV file with historical fire data

**Request**:
```http
POST /api/v1/ingest/historical-fires/batch HTTP/1.1
Host: localhost:8003
Content-Type: text/csv

latitude,longitude,fire_name,start_date,end_date,acres_burned
39.8094,-121.4378,Camp Fire,2018-11-08,2018-11-25,153336
38.4404,-122.7141,Tubbs Fire,2017-10-08,2017-10-31,36807
```

**Response**:
```json
{
  "status": "success",
  "records_uploaded": 2,
  "records_valid": 2,
  "records_invalid": 0,
  "validation_errors": [],
  "processing_time_ms": 2347,
  "kafka_topic": "wildfire-historical-fires",
  "ingestion_id": "hist_20250105_013245"
}
```

**cURL Example**:
```bash
curl -X POST http://localhost:8003/api/v1/ingest/historical-fires/batch \
  -H "Content-Type: text/csv" \
  --data-binary @services/data-ingestion-service/examples/input/sample_firms.csv
```

**CSV Format Requirements**:
- Headers required (first row)
- Columns: `latitude`, `longitude`, `fire_name`, `start_date`, `end_date`, `acres_burned`
- Encoding: UTF-8
- Max file size: 100 MB
- Max records: 1,000,000

---

### 3. Trigger Weather Data Ingestion

**Endpoint**: `POST /api/v1/ingest/weather/trigger`

**Description**: Fetch weather observations from NOAA Weather API

**Request**:
```http
POST /api/v1/ingest/weather/trigger HTTP/1.1
Host: localhost:8003
Content-Type: application/json

{
  "stations": ["KOVE", "KSMF", "KSAC"],
  "data_type": "observations"
}
```

**Response**:
```json
{
  "status": "success",
  "stations_polled": 3,
  "observations_fetched": 3,
  "observations_valid": 3,
  "cache_hits": 1,
  "cache_misses": 2,
  "processing_time_ms": 1247,
  "next_poll_at": "2025-01-05T01:45:47Z"
}
```

**Station Codes**: See https://www.weather.gov/documentation/services-web-api

---

### 4. IoT Sensor Data (MQTT)

**Protocol**: MQTT (not HTTP)

**Broker**: `localhost:1883` (Mosquitto)

**Topic Pattern**: `wildfire/sensors/{type}/{sensor_id}`

**Examples**:
- `wildfire/sensors/environmental/CAL-FIRE-SENSOR-2847`
- `wildfire/sensors/air_quality/PURPLEAIR-175429`
- `wildfire/sensors/weather_station/NOAA-KOVE`

**Publish Example**:
```bash
mosquitto_pub -h localhost -p 1883 \
  -t "wildfire/sensors/environmental/CAL-FIRE-SENSOR-2847" \
  -f services/data-ingestion-service/examples/input/sample_mqtt_sensor.json
```

**Payload Format**: See `examples/input/sample_mqtt_sensor.json`

---

### 5. Manual Fire Detection Ingestion

**Endpoint**: `POST /api/v1/ingest/fire-detection/manual`

**Description**: Manually submit a fire detection (for testing or manual reports)

**Request**:
```http
POST /api/v1/ingest/fire-detection/manual HTTP/1.1
Host: localhost:8003
Content-Type: application/json

{
  "latitude": 39.7596,
  "longitude": -121.6219,
  "brightness": 328.4,
  "confidence": "high",
  "frp": 45.3,
  "satellite": "Manual Report",
  "sensor": "CAL FIRE Observer",
  "acq_date": "2025-01-05",
  "acq_time": "0130",
  "daynight": "N"
}
```

**Response**:
```json
{
  "status": "success",
  "detection_id": "MANUAL_20250105_00001",
  "ingestion_timestamp": "2025-01-05T01:30:47.284Z",
  "validation_passed": true,
  "stored_in_tier": "HOT",
  "kafka_offset": 184729,
  "processing_time_ms": 47
}
```

---

## Query Endpoints

### 6. Get Fire Detections by Bounding Box

**Endpoint**: `GET /api/v1/query/fire-detections/bbox`

**Description**: Query fire detections within geographic bounding box (PostGIS)

**Request**:
```http
GET /api/v1/query/fire-detections/bbox?min_lat=39.0&max_lat=40.0&min_lon=-122.0&max_lon=-121.0&start_date=2025-01-04&end_date=2025-01-05 HTTP/1.1
Host: localhost:8003
```

**Response**:
```json
{
  "status": "success",
  "query_time_ms": 87,
  "count": 127,
  "detections": [
    {
      "detection_id": "FIRMS_20250104_00142",
      "latitude": 39.7596,
      "longitude": -121.6219,
      "brightness": 328.4,
      "confidence": "high",
      "frp": 45.3,
      "satellite": "NOAA-20",
      "detection_time_pst": "2025-01-04T17:30:00-08:00",
      "distance_km": 0.0
    }
  ],
  "bounding_box": {
    "min_lat": 39.0,
    "max_lat": 40.0,
    "min_lon": -122.0,
    "max_lon": -121.0
  }
}
```

**Query Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `min_lat` | float | Yes | Minimum latitude (-90 to 90) |
| `max_lat` | float | Yes | Maximum latitude (-90 to 90) |
| `min_lon` | float | Yes | Minimum longitude (-180 to 180) |
| `max_lon` | float | Yes | Maximum longitude (-180 to 180) |
| `start_date` | string | No | ISO 8601 date (e.g., 2025-01-04) |
| `end_date` | string | No | ISO 8601 date |
| `confidence` | string | No | Filter by confidence (low, nominal, high) |
| `limit` | integer | No | Max results (default: 100, max: 10,000) |

**Performance**: p95 latency **87ms** (HOT tier with PostGIS spatial index)

---

### 7. Get Fire Detections Near Point

**Endpoint**: `GET /api/v1/query/fire-detections/near`

**Description**: Find fire detections within radius of a point (PostGIS)

**Request**:
```http
GET /api/v1/query/fire-detections/near?lat=39.7596&lon=-121.6219&radius_km=10&hours=24 HTTP/1.1
Host: localhost:8003
```

**Response**:
```json
{
  "status": "success",
  "query_time_ms": 92,
  "center_point": {
    "latitude": 39.7596,
    "longitude": -121.6219,
    "name": "Paradise, CA"
  },
  "radius_km": 10,
  "count": 18,
  "detections": [
    {
      "detection_id": "FIRMS_20250104_00142",
      "latitude": 39.7596,
      "longitude": -121.6219,
      "distance_km": 0.0,
      "brightness": 328.4,
      "confidence": "high"
    },
    {
      "detection_id": "FIRMS_20250104_00157",
      "latitude": 39.7712,
      "longitude": -121.6345,
      "distance_km": 2.7,
      "brightness": 315.2,
      "confidence": "nominal"
    }
  ]
}
```

**Query Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `lat` | float | Yes | Center latitude |
| `lon` | float | Yes | Center longitude |
| `radius_km` | float | Yes | Search radius in kilometers (0.1 to 500) |
| `hours` | integer | No | Lookback hours (default: 24, max: 168) |
| `confidence` | string | No | Filter by confidence |
| `limit` | integer | No | Max results (default: 100) |

---

### 8. Get Ingestion Statistics

**Endpoint**: `GET /api/v1/stats/ingestion`

**Description**: Get ingestion metrics and statistics

**Request**:
```http
GET /api/v1/stats/ingestion?hours=24 HTTP/1.1
Host: localhost:8003
```

**Response**:
```json
{
  "status": "success",
  "time_window_hours": 24,
  "statistics": {
    "total_messages": 1247893,
    "messages_valid": 1247001,
    "messages_invalid": 892,
    "validation_pass_rate": 0.9993,
    "duplicate_rate": 0.00024,
    "avg_latency_ms": 847,
    "p95_latency_ms": 870,
    "p99_latency_ms": 1247,
    "sources": {
      "NASA_FIRMS": {
        "count": 847234,
        "avg_latency_ms": 847,
        "validation_pass_rate": 0.9998
      },
      "NOAA_WEATHER": {
        "count": 247893,
        "avg_latency_ms": 1247,
        "validation_pass_rate": 0.9994
      },
      "IOT_SENSORS": {
        "count": 152766,
        "avg_latency_ms": 470,
        "validation_pass_rate": 0.9976
      }
    }
  }
}
```

---

## Health & Monitoring

### 9. Health Check

**Endpoint**: `GET /health`

**Description**: Service health status and dependencies

**Request**:
```http
GET /health HTTP/1.1
Host: localhost:8003
```

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2025-01-05T01:30:47.284Z",
  "version": "2.1.0",
  "uptime_seconds": 847234,
  "dependencies": {
    "postgresql": {
      "status": "healthy",
      "latency_ms": 3
    },
    "kafka": {
      "status": "healthy",
      "brokers_connected": 1
    },
    "redis": {
      "status": "healthy",
      "latency_ms": 1
    },
    "nasa_firms_api": {
      "status": "healthy",
      "last_check": "2025-01-05T01:25:00Z"
    }
  }
}
```

**Status Codes**:
- `200`: All systems healthy
- `503`: One or more dependencies unhealthy

---

### 10. Prometheus Metrics

**Endpoint**: `GET /metrics`

**Description**: Prometheus-formatted metrics for monitoring

**Request**:
```http
GET /metrics HTTP/1.1
Host: localhost:8003
```

**Response**:
```
# HELP ingestion_latency_seconds Ingestion latency by source
# TYPE ingestion_latency_seconds histogram
ingestion_latency_seconds_bucket{source="NASA_FIRMS",le="0.1"} 0
ingestion_latency_seconds_bucket{source="NASA_FIRMS",le="0.5"} 42847
ingestion_latency_seconds_bucket{source="NASA_FIRMS",le="1.0"} 847234
ingestion_latency_seconds_bucket{source="NASA_FIRMS",le="+Inf"} 847234
ingestion_latency_seconds_sum{source="NASA_FIRMS"} 717842.3
ingestion_latency_seconds_count{source="NASA_FIRMS"} 847234

# HELP validation_pass_rate Validation pass rate by source
# TYPE validation_pass_rate gauge
validation_pass_rate{source="NASA_FIRMS"} 0.9998
validation_pass_rate{source="NOAA_WEATHER"} 0.9994
validation_pass_rate{source="IOT_SENSORS"} 0.9976
```

---

## Error Responses

### Standard Error Format

All errors return consistent JSON structure:

```json
{
  "status": "error",
  "error_code": "VALIDATION_ERROR",
  "message": "Field 'latitude' value 192.5847 exceeds valid range [-90, 90]",
  "details": {
    "field": "latitude",
    "value": 192.5847,
    "constraint": "[-90, 90]"
  },
  "timestamp": "2025-01-05T01:30:47.284Z",
  "request_id": "req_20250105_013047_284"
}
```

### HTTP Status Codes

| Code | Meaning | Description |
|------|---------|-------------|
| `200` | OK | Request successful |
| `201` | Created | Resource created successfully |
| `400` | Bad Request | Invalid request parameters |
| `401` | Unauthorized | Authentication required |
| `403` | Forbidden | Insufficient permissions |
| `404` | Not Found | Endpoint or resource not found |
| `422` | Unprocessable Entity | Validation failed |
| `429` | Too Many Requests | Rate limit exceeded |
| `500` | Internal Server Error | Server error |
| `503` | Service Unavailable | Dependency unavailable |

---

## Rate Limits

### Current Limits (Development)

| Endpoint Pattern | Limit | Window |
|------------------|-------|--------|
| `/api/v1/ingest/*` | 100 requests | 1 minute |
| `/api/v1/query/*` | 1000 requests | 1 minute |
| `/health` | Unlimited | - |
| `/metrics` | Unlimited | - |

### Rate Limit Headers

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 2025-01-05T01:31:00Z
```

### Rate Limit Exceeded Response

```json
{
  "status": "error",
  "error_code": "RATE_LIMIT_EXCEEDED",
  "message": "Rate limit exceeded: 100 requests per minute",
  "retry_after_seconds": 42,
  "limit": 100,
  "window": "1 minute"
}
```

---

## Code Examples

### Python (requests)

```python
import requests

# Trigger FIRMS ingestion
response = requests.post(
    "http://localhost:8003/api/v1/ingest/firms/trigger",
    json={"area": "california", "lookback_hours": 24}
)

print(f"Status: {response.status_code}")
print(f"Detections: {response.json()['detections_fetched']}")

# Query fire detections near Paradise, CA
response = requests.get(
    "http://localhost:8003/api/v1/query/fire-detections/near",
    params={
        "lat": 39.7596,
        "lon": -121.6219,
        "radius_km": 10,
        "hours": 24
    }
)

detections = response.json()['detections']
print(f"Found {len(detections)} fire detections within 10km")
```

### JavaScript (fetch)

```javascript
// Trigger FIRMS ingestion
const response = await fetch(
  'http://localhost:8003/api/v1/ingest/firms/trigger',
  {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      area: 'california',
      lookback_hours: 24
    })
  }
);

const data = await response.json();
console.log(`Detections fetched: ${data.detections_fetched}`);

// Query fire detections
const queryResponse = await fetch(
  'http://localhost:8003/api/v1/query/fire-detections/bbox?' +
  new URLSearchParams({
    min_lat: 39.0,
    max_lat: 40.0,
    min_lon: -122.0,
    max_lon: -121.0
  })
);

const queryData = await queryResponse.json();
console.log(`Found ${queryData.count} detections`);
```

### Bash (cURL)

```bash
#!/bin/bash

# Trigger NASA FIRMS ingestion
curl -X POST http://localhost:8003/api/v1/ingest/firms/trigger \
  -H "Content-Type: application/json" \
  -d '{"area": "california", "lookback_hours": 24}' \
  | jq '.detections_fetched'

# Upload historical fires CSV
curl -X POST http://localhost:8003/api/v1/ingest/historical-fires/batch \
  -H "Content-Type: text/csv" \
  --data-binary @historical_fires.csv \
  | jq '.records_uploaded'

# Query fire detections near point
curl -G http://localhost:8003/api/v1/query/fire-detections/near \
  --data-urlencode "lat=39.7596" \
  --data-urlencode "lon=-121.6219" \
  --data-urlencode "radius_km=10" \
  | jq '.count'
```

---

## Testing

### Run All API Tests

```bash
# Unit tests
pytest services/data-ingestion-service/tests/api/ -v

# Integration tests (requires running services)
pytest services/data-ingestion-service/tests/integration/ -v

# Load tests (1000 concurrent requests)
locust -f services/data-ingestion-service/tests/load/locustfile.py --headless -u 1000 -r 100
```

### Manual Testing Checklist

- [ ] Trigger FIRMS ingestion: `POST /api/v1/ingest/firms/trigger`
- [ ] Upload CSV: `POST /api/v1/ingest/historical-fires/batch`
- [ ] Query bbox: `GET /api/v1/query/fire-detections/bbox`
- [ ] Query near: `GET /api/v1/query/fire-detections/near`
- [ ] Health check: `GET /health`
- [ ] Metrics: `GET /metrics`
- [ ] Rate limit: Send 101 requests in 1 minute → expect 429

---

## Challenge 1 Deliverable Mapping

This API reference addresses:

| Deliverable | Evidence | Section |
|-------------|----------|---------|
| **#2: Data Ingestion Prototype** | Ingestion endpoints (1-5) | Ingestion Endpoints |
| **#13: API Documentation** | Complete API reference | This document |
| **#14: User Guide** | Code examples, testing | Code Examples section |

---

## Additional Resources

- **Interactive Docs (Swagger)**: http://localhost:8003/docs
- **ReDoc**: http://localhost:8003/redoc
- **OpenAPI Spec (JSON)**: http://localhost:8003/openapi.json
- **Example Files**: `services/data-ingestion-service/examples/`
- **Source Code**: `services/data-ingestion-service/src/api/`

---

**Prepared by**: CAL FIRE Wildfire Intelligence Platform Team
**Challenge**: Challenge 1 - Data Sources & Ingestion Mechanisms
**Deliverable**: #13 - API Documentation
**Document Version**: 1.0
