# Challenge 3: Complete Testing Guide
## Data Consumption and Presentation/Analytic Layers - Data Clearing House

**Purpose**: Step-by-step testing instructions to verify all Challenge 3 deliverables

**Estimated Time**: 2-3 hours for complete testing

**Prerequisites**:
- All services running (`docker-compose up -d`)
- Test data loaded
- Network access to all service ports

---

## Table of Contents

1. [Setup & Verification](#1-setup--verification)
2. [Test 1: User Authentication & Access Control](#test-1-user-authentication--access-control)
3. [Test 2: Data Catalog & Discovery](#test-2-data-catalog--discovery)
4. [Test 3: Self-Service Data Access](#test-3-self-service-data-access)
5. [Test 4: Data Visualization Tools](#test-4-data-visualization-tools)
6. [Test 5: Security & Audit Logging](#test-5-security--audit-logging)
7. [Test 6: Jupyter Sandbox Environment](#test-6-jupyter-sandbox-environment)
8. [Test 7: API Access & Integration](#test-7-api-access--integration)
9. [Test 8: Data Quality & SLA Monitoring](#test-8-data-quality--sla-monitoring)
10. [Troubleshooting](#troubleshooting)

---

## 1. Setup & Verification

### 1.1 Verify All Services are Running

```bash
# Check all services status
docker-compose ps

# Expected output: All services showing "Up" or "Up (healthy)"
# Key services for Challenge 3:
# - data-clearing-house (port 8005)
# - fire-chief-dashboard (port 3000)
# - postgres (port 5432)
# - grafana (port 3010)
# - prometheus (port 9090)
```

**Success Criteria**: ✅ All services status = "Up (healthy)"

### 1.2 Verify Service Health Endpoints

```bash
# Data Clearing House health check
curl http://localhost:8005/health

# Expected response:
{
  "status": "healthy",
  "timestamp": "2025-01-05T14:23:45Z",
  "services": {
    "postgres": "connected",
    "kafka": "connected",
    "redis": "connected"
  },
  "version": "1.0.0"
}
```

**Success Criteria**: ✅ Status = "healthy", all services "connected"

### 1.3 Access Swagger API Documentation

```bash
# Open in browser
http://localhost:8005/docs

# Expected: Interactive Swagger UI with all API endpoints
```

**Success Criteria**: ✅ Swagger UI loads, shows 50+ endpoints

---

## Test 1: User Authentication & Access Control

### Test 1.1: Basic Login (Username/Password)

**Objective**: Verify user can login with username and password

**Steps**:

```bash
# 1. Login request
curl -X POST http://localhost:8005/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "fire.chief@fire.ca.gov",
    "password": "TestPassword123!"
  }'

# Expected response:
{
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 28800,
  "user": {
    "id": "user_123",
    "email": "fire.chief@fire.ca.gov",
    "role": "FIRE_CHIEF",
    "mfa_enabled": false
  }
}
```

**Success Criteria**:
- ✅ Status code: 200
- ✅ `access_token` present and valid JWT format
- ✅ `user.role` = "FIRE_CHIEF"
- ✅ Token expires in 8 hours (28800 seconds)

### Test 1.2: Multi-Factor Authentication (MFA)

**Objective**: Verify MFA flow works correctly

**Steps**:

```bash
# 1. Login with MFA-enabled user
curl -X POST http://localhost:8005/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin@fire.ca.gov",
    "password": "AdminPassword456!"
  }'

# Expected response (requires MFA):
{
  "status": "mfa_required",
  "challenge_id": "mfa_challenge_abc123",
  "mfa_method": "totp"
}

# 2. Submit MFA code
curl -X POST http://localhost:8005/api/v1/auth/mfa/verify \
  -H "Content-Type: application/json" \
  -d '{
    "challenge_id": "mfa_challenge_abc123",
    "code": "123456"
  }'

# Expected response (if code valid):
{
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 28800,
  "user": {
    "id": "admin_001",
    "email": "admin@fire.ca.gov",
    "role": "ADMIN",
    "mfa_enabled": true
  }
}
```

**Success Criteria**:
- ✅ First request returns `mfa_required`
- ✅ Second request (with valid code) returns access token
- ✅ Invalid MFA code returns 401 error

### Test 1.3: Role-Based Access Control (RBAC)

**Objective**: Verify users can only access resources allowed by their role

**Test 1.3a: Fire Chief Role Access**

```bash
# Login as Fire Chief
TOKEN=$(curl -X POST http://localhost:8005/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"fire.chief@fire.ca.gov","password":"TestPassword123!"}' \
  | jq -r '.access_token')

# Test: Access allowed dataset
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8005/api/v1/datasets/nasa_firms_modis

# Expected: 200 OK with dataset details

# Test: Try to access admin endpoint (should fail)
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8005/api/v1/admin/users

# Expected: 403 Forbidden
{
  "error": "Insufficient permissions",
  "required_role": "ADMIN",
  "user_role": "FIRE_CHIEF"
}
```

**Success Criteria**:
- ✅ Fire Chief can access operational datasets
- ✅ Fire Chief CANNOT access admin endpoints (403 error)

**Test 1.3b: Public Role Access**

```bash
# Login as public user
TOKEN=$(curl -X POST http://localhost:8005/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"public.user@example.com","password":"PublicPass789!"}' \
  | jq -r '.access_token')

# Test: Access public dataset
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8005/api/v1/datasets/fire_perimeters_public

# Expected: 200 OK

# Test: Try to access restricted dataset
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8005/api/v1/datasets/infrastructure_critical

# Expected: 403 Forbidden
{
  "error": "Dataset requires higher access level",
  "dataset_classification": "RESTRICTED",
  "user_clearance": "PUBLIC"
}
```

**Success Criteria**:
- ✅ Public user can access PUBLIC datasets
- ✅ Public user CANNOT access RESTRICTED datasets (403)

### Test 1.4: SSO Integration (OAuth)

**Objective**: Verify SSO login works (Google/Microsoft)

**Steps** (Using Google OAuth):

```bash
# 1. Initiate OAuth flow
curl http://localhost:8005/api/v1/auth/sso/google

# Expected: Redirect to Google login
{
  "auth_url": "https://accounts.google.com/o/oauth2/v2/auth?client_id=...",
  "state": "random_state_token_xyz"
}

# 2. User logs in via Google (manual step in browser)
# Google redirects back to: http://localhost:8005/api/v1/auth/sso/callback?code=auth_code_123&state=random_state_token_xyz

# 3. Exchange code for token (automatic)
curl http://localhost:8005/api/v1/auth/sso/callback?code=auth_code_123&state=random_state_token_xyz

# Expected response:
{
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "email": "user@fire.ca.gov",
    "name": "John Doe",
    "role": "ANALYST",
    "sso_provider": "google"
  }
}
```

**Success Criteria**:
- ✅ OAuth flow initiates successfully
- ✅ Callback processes code and returns valid token
- ✅ User profile mapped from Google account

**Test 1.5: Session Management**

```bash
# Get current user info
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8005/api/v1/users/me

# Expected:
{
  "id": "user_123",
  "email": "fire.chief@fire.ca.gov",
  "role": "FIRE_CHIEF",
  "session": {
    "id": "sess_xyz789",
    "created_at": "2025-01-05T14:00:00Z",
    "expires_at": "2025-01-05T22:00:00Z",
    "last_activity": "2025-01-05T14:23:45Z"
  }
}

# Logout
curl -X POST -H "Authorization: Bearer $TOKEN" \
  http://localhost:8005/api/v1/auth/logout

# Expected: 200 OK

# Try using token after logout (should fail)
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8005/api/v1/users/me

# Expected: 401 Unauthorized
```

**Success Criteria**:
- ✅ Session info includes expiry time (8 hours from creation)
- ✅ Logout invalidates token
- ✅ Token unusable after logout (401 error)

---

## Test 2: Data Catalog & Discovery

### Test 2.1: Browse Dataset Catalog

**Objective**: Verify user can browse and search datasets

**Steps**:

```bash
# List all datasets (with pagination)
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8005/api/v1/datasets?limit=20&offset=0"

# Expected response:
{
  "datasets": [
    {
      "id": "nasa_firms_modis_c6_1",
      "name": "NASA FIRMS MODIS Collection 6.1 NRT",
      "description": "Near real-time fire detections from MODIS",
      "category": "satellite_products",
      "update_frequency": "15min",
      "size_gb": 125.4,
      "record_count": 1247000,
      "last_updated": "2025-01-05T14:15:00Z",
      "quality_score": 0.987,
      "access_level": "PUBLIC"
    },
    {
      "id": "historical_fires_calfire",
      "name": "CAL FIRE Historical Incidents",
      "description": "Complete history of wildfire incidents in California",
      "category": "historical_data",
      "update_frequency": "daily",
      "size_gb": 45.2,
      "record_count": 125000,
      "last_updated": "2025-01-05T02:00:00Z",
      "quality_score": 0.995,
      "access_level": "PUBLIC"
    }
    // ... more datasets
  ],
  "total_count": 52,
  "page": 1,
  "total_pages": 3
}
```

**Success Criteria**:
- ✅ Returns list of 20 datasets (limit)
- ✅ Total count = 52 datasets
- ✅ Each dataset has complete metadata
- ✅ Quality scores visible (0-1 scale)

### Test 2.2: Search Datasets (Full-Text Search)

**Objective**: Verify Elasticsearch-powered search works

**Steps**:

```bash
# Search for "fire detection" datasets
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8005/api/v1/catalog/search?q=fire+detection&limit=10"

# Expected response:
{
  "results": [
    {
      "id": "nasa_firms_modis_c6_1",
      "name": "NASA FIRMS MODIS Collection 6.1 NRT",
      "description": "Near real-time <em>fire detection</em> from MODIS satellites",
      "score": 8.5,
      "highlights": {
        "description": ["Near real-time <em>fire detection</em> from MODIS"]
      }
    },
    {
      "id": "firesat_nos_testbed",
      "name": "FireSat NOS Testbed",
      "description": "5-meter resolution <em>fire detection</em> satellite imagery",
      "score": 7.8
    }
  ],
  "total_hits": 5,
  "query_time_ms": 23
}
```

**Success Criteria**:
- ✅ Returns relevant datasets for "fire detection"
- ✅ Results sorted by relevance score
- ✅ Search highlights show matching text
- ✅ Query time < 100ms

### Test 2.3: Faceted Filtering

**Objective**: Verify users can filter datasets by category, frequency, etc.

**Steps**:

```bash
# Filter by category and update frequency
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8005/api/v1/datasets?category=satellite_products&update_frequency=15min"

# Expected response:
{
  "datasets": [
    {
      "id": "nasa_firms_modis_c6_1",
      "category": "satellite_products",
      "update_frequency": "15min"
    },
    {
      "id": "nasa_firms_viirs_c2",
      "category": "satellite_products",
      "update_frequency": "15min"
    }
  ],
  "filters_applied": {
    "category": "satellite_products",
    "update_frequency": "15min"
  },
  "total_count": 2
}
```

**Success Criteria**:
- ✅ Only satellite products with 15min frequency returned
- ✅ Filters_applied object shows active filters
- ✅ Total count reflects filtered results

### Test 2.4: Dataset Details & Schema

**Objective**: Verify detailed dataset information is available

**Steps**:

```bash
# Get full dataset details
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8005/api/v1/datasets/nasa_firms_modis_c6_1

# Expected response:
{
  "id": "nasa_firms_modis_c6_1",
  "name": "NASA FIRMS MODIS Collection 6.1 NRT",
  "description": "Near real-time fire detections from MODIS satellites...",
  "category": "satellite_products",
  "owner": "data-team@fire.ca.gov",
  "steward": "john.doe@fire.ca.gov",
  "schema": {
    "format": "parquet",
    "columns": [
      {
        "name": "latitude",
        "type": "float64",
        "nullable": false,
        "description": "Fire detection latitude in decimal degrees"
      },
      {
        "name": "longitude",
        "type": "float64",
        "nullable": false,
        "description": "Fire detection longitude in decimal degrees"
      },
      {
        "name": "brightness",
        "type": "float32",
        "unit": "Kelvin",
        "description": "Brightness temperature of fire pixel"
      },
      {
        "name": "frp",
        "type": "float32",
        "unit": "MW",
        "description": "Fire Radiative Power in megawatts"
      }
      // ... more columns
    ]
  },
  "tags": ["fire", "satellite", "real-time", "nasa", "modis"],
  "quality_score": 0.987,
  "sla": {
    "latency_p95": "5min",
    "completeness": "99.5%",
    "freshness": "15min"
  },
  "storage": {
    "primary": "timescaledb://wildfire/fire_detections",
    "size_gb": 125.4,
    "record_count": 1247000
  },
  "lineage": {
    "upstream_sources": ["NASA_FIRMS_API"],
    "downstream_consumers": ["fire_risk_model", "alert_system", "dashboard"]
  }
}
```

**Success Criteria**:
- ✅ Complete metadata returned
- ✅ Schema shows all columns with types and descriptions
- ✅ Tags, SLA, and lineage information present
- ✅ Quality score and storage details included

### Test 2.5: Data Lineage Tracking

**Objective**: Verify data lineage can be traced

**Steps**:

```bash
# Get lineage graph for dataset
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8005/api/v1/catalog/lineage/nasa_firms_modis_c6_1

# Expected response:
{
  "dataset_id": "nasa_firms_modis_c6_1",
  "lineage_dag": {
    "upstream": [
      {
        "type": "api",
        "name": "NASA FIRMS API",
        "url": "https://firms.modaps.eosdis.nasa.gov/api/",
        "refresh_interval": "15min"
      }
    ],
    "transformations": [
      {
        "step": 1,
        "type": "ingestion",
        "service": "data-ingestion-service",
        "operations": ["CSV parsing", "timezone normalization (UTC→PST)", "unit conversion"]
      },
      {
        "step": 2,
        "type": "validation",
        "service": "data-clearing-house",
        "operations": ["schema validation", "range checks", "deduplication"]
      },
      {
        "step": 3,
        "type": "enrichment",
        "service": "data-clearing-house",
        "operations": ["geocoding", "reverse geocoding", "county assignment"]
      }
    ],
    "downstream": [
      {
        "type": "model",
        "name": "Fire Risk Prediction Model",
        "id": "fire_risk_model_v2"
      },
      {
        "type": "dashboard",
        "name": "Fire Chief Dashboard",
        "id": "fire_chief_dashboard"
      },
      {
        "type": "alert_system",
        "name": "Real-time Fire Alert System",
        "id": "alert_system"
      }
    ]
  },
  "impact_analysis": {
    "impacted_models": 3,
    "impacted_dashboards": 2,
    "impacted_alerts": 1,
    "total_impact_score": 8.5
  }
}
```

**Success Criteria**:
- ✅ Lineage DAG shows complete flow: source → transformations → consumers
- ✅ Impact analysis shows what depends on this dataset
- ✅ Transformation steps documented

### Test 2.6: Dataset Preview

**Objective**: Verify users can preview data before downloading

**Steps**:

```bash
# Get preview (first 100 rows)
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8005/api/v1/datasets/nasa_firms_modis_c6_1/preview?limit=100"

# Expected response:
{
  "dataset_id": "nasa_firms_modis_c6_1",
  "preview_rows": 100,
  "total_rows": 1247000,
  "data": [
    {
      "latitude": 38.5234,
      "longitude": -120.8765,
      "brightness": 335.2,
      "confidence": 87,
      "frp": 12.5,
      "detection_time_pst": "2025-01-05T12:34:00-08:00",
      "county": "Butte"
    },
    // ... 99 more rows
  ],
  "schema": {
    "columns": ["latitude", "longitude", "brightness", "confidence", "frp", "detection_time_pst", "county"]
  },
  "preview_generated_at": "2025-01-05T14:30:00Z"
}
```

**Success Criteria**:
- ✅ Returns first 100 rows
- ✅ Shows total row count (1,247,000)
- ✅ Data matches schema
- ✅ Preview loads quickly (< 1 second)

---

## Test 3: Self-Service Data Access

### Test 3.1: Visual Query Builder

**Objective**: Verify users can build queries without writing SQL

**Steps**:

```bash
# Build query using visual query builder API
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  http://localhost:8005/api/v1/query/build \
  -d '{
    "dataset": "nasa_firms_modis_c6_1",
    "columns": ["latitude", "longitude", "brightness", "frp", "detection_time_pst"],
    "filters": [
      {
        "column": "detection_time_pst",
        "operator": "between",
        "value": ["2025-01-01T00:00:00-08:00", "2025-01-05T23:59:59-08:00"]
      },
      {
        "column": "confidence",
        "operator": ">=",
        "value": 80
      },
      {
        "column": "county",
        "operator": "in",
        "value": ["Butte", "Plumas", "Shasta"]
      }
    ],
    "order_by": [{"column": "detection_time_pst", "direction": "desc"}],
    "limit": 1000
  }'

# Expected response:
{
  "query_id": "query_abc123",
  "sql_generated": "SELECT latitude, longitude, brightness, frp, detection_time_pst FROM fire_detections WHERE detection_time_pst BETWEEN '2025-01-01 00:00:00-08' AND '2025-01-05 23:59:59-08' AND confidence >= 80 AND county IN ('Butte', 'Plumas', 'Shasta') ORDER BY detection_time_pst DESC LIMIT 1000",
  "estimated_rows": 847,
  "estimated_cost_ms": 125,
  "status": "ready_to_execute"
}
```

**Success Criteria**:
- ✅ Visual query spec converted to SQL
- ✅ Query validation passes
- ✅ Estimated rows and cost provided
- ✅ No SQL knowledge required from user

### Test 3.2: Execute Query

**Objective**: Execute the built query and get results

**Steps**:

```bash
# Execute query
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  http://localhost:8005/api/v1/query/execute \
  -d '{
    "query_id": "query_abc123",
    "format": "json"
  }'

# Expected response:
{
  "query_id": "query_abc123",
  "status": "completed",
  "execution_time_ms": 118,
  "rows_returned": 847,
  "results": [
    {
      "latitude": 39.8102,
      "longitude": -121.4370,
      "brightness": 342.5,
      "frp": 18.3,
      "detection_time_pst": "2025-01-05T14:23:00-08:00"
    },
    // ... 846 more rows
  ],
  "metadata": {
    "columns": ["latitude", "longitude", "brightness", "frp", "detection_time_pst"],
    "data_types": ["float64", "float64", "float32", "float32", "timestamp"]
  }
}
```

**Success Criteria**:
- ✅ Query executes successfully
- ✅ Returns 847 rows (as estimated)
- ✅ Execution time < 200ms
- ✅ Results in requested format (JSON)

### Test 3.3: Export Formats

**Objective**: Verify multiple export formats supported

**Test 3.3a: Export as CSV**

```bash
# Execute and export as CSV
curl -X POST -H "Authorization: Bearer $TOKEN" \
  http://localhost:8005/api/v1/query/execute \
  -d '{"query_id":"query_abc123","format":"csv"}' \
  -o fires_jan_2025.csv

# Verify CSV file
head fires_jan_2025.csv

# Expected output:
latitude,longitude,brightness,frp,detection_time_pst
39.8102,-121.4370,342.5,18.3,2025-01-05T14:23:00-08:00
38.5234,-120.8765,335.2,12.5,2025-01-05T12:34:00-08:00
...
```

**Test 3.3b: Export as Parquet**

```bash
# Execute and export as Parquet
curl -X POST -H "Authorization: Bearer $TOKEN" \
  http://localhost:8005/api/v1/query/execute \
  -d '{"query_id":"query_abc123","format":"parquet"}' \
  -o fires_jan_2025.parquet

# Verify Parquet file (using parquet-tools if installed)
parquet-tools schema fires_jan_2025.parquet

# Expected output:
message schema {
  required double latitude;
  required double longitude;
  optional float brightness;
  optional float frp;
  optional int64 detection_time_pst (TIMESTAMP(MICROS,true));
}
```

**Test 3.3c: Export as GeoJSON**

```bash
# Execute and export as GeoJSON
curl -X POST -H "Authorization: Bearer $TOKEN" \
  http://localhost:8005/api/v1/query/execute \
  -d '{"query_id":"query_abc123","format":"geojson"}' \
  -o fires_jan_2025.geojson

# Verify GeoJSON structure
cat fires_jan_2025.geojson | jq '.features[0]'

# Expected output:
{
  "type": "Feature",
  "geometry": {
    "type": "Point",
    "coordinates": [-121.4370, 39.8102]
  },
  "properties": {
    "brightness": 342.5,
    "frp": 18.3,
    "detection_time_pst": "2025-01-05T14:23:00-08:00"
  }
}
```

**Success Criteria**:
- ✅ CSV export works and is valid
- ✅ Parquet export works with correct schema
- ✅ GeoJSON export works with proper geometry

### Test 3.4: Download Complete Dataset

**Objective**: Verify bulk download of entire dataset

**Steps**:

```bash
# Request dataset download
curl -X POST -H "Authorization: Bearer $TOKEN" \
  http://localhost:8005/api/v1/datasets/historical_fires_calfire/download \
  -d '{"format":"parquet","compression":"gzip"}' \
  -o historical_fires.parquet.gz

# Check file size
ls -lh historical_fires.parquet.gz

# Expected: File size ~200MB (compressed)

# Verify download quota
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8005/api/v1/users/me/quota

# Expected response:
{
  "user_id": "user_123",
  "role": "FIRE_CHIEF",
  "download_quota": {
    "monthly_limit_gb": 100,
    "used_this_month_gb": 12.5,
    "remaining_gb": 87.5,
    "resets_at": "2025-02-01T00:00:00Z"
  }
}
```

**Success Criteria**:
- ✅ Dataset downloads successfully
- ✅ File size reasonable (compressed)
- ✅ Download quota tracked correctly
- ✅ Quota decremented after download

### Test 3.5: Usage Tracking

**Objective**: Verify all data access is tracked

**Steps**:

```bash
# Get personal usage statistics
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8005/api/v1/usage/stats?user_id=user_123&period=last_7_days

# Expected response:
{
  "user_id": "user_123",
  "period": "last_7_days",
  "statistics": {
    "queries_executed": 47,
    "datasets_accessed": 12,
    "data_downloaded_gb": 8.5,
    "api_calls": 234,
    "avg_query_time_ms": 156,
    "most_accessed_datasets": [
      {"id": "nasa_firms_modis_c6_1", "access_count": 18},
      {"id": "historical_fires_calfire", "access_count": 12}
    ]
  },
  "daily_breakdown": [
    {"date": "2025-01-05", "queries": 12, "downloads_gb": 2.1},
    {"date": "2025-01-04", "queries": 8, "downloads_gb": 1.3},
    // ... more days
  ]
}
```

**Success Criteria**:
- ✅ Usage stats show all activities
- ✅ Query count, downloads tracked
- ✅ Daily breakdown available
- ✅ Most accessed datasets ranked

---

## Test 4: Data Visualization Tools

### Test 4.1: Fire Chief Dashboard

**Objective**: Verify Fire Chief dashboard loads and displays real-time data

**Steps**:

1. **Open Fire Chief Dashboard**:
   ```
   URL: http://localhost:3000
   Login: fire.chief@fire.ca.gov / TestPassword123!
   ```

2. **Verify Dashboard Components**:
   - ✅ Active Fires Map (Leaflet) loads with fire markers
   - ✅ Fire count widget shows current count (e.g., "24 Active Fires")
   - ✅ Resource allocation panel shows helicopters, crews, equipment
   - ✅ Weather alerts panel shows warnings/advisories
   - ✅ Air quality widget shows current AQI

3. **Test Real-Time Updates**:
   ```bash
   # Trigger new fire detection (simulate)
   curl -X POST -H "Authorization: Bearer $TOKEN" \
     http://localhost:8003/api/v1/ingest/firms/trigger

   # Expected: Dashboard updates within 30 seconds
   # - New fire marker appears on map
   # - Fire count increments
   # - Alert notification shows "New fire detected in Butte County"
   ```

**Success Criteria**:
- ✅ Dashboard loads in < 3 seconds
- ✅ All widgets display data correctly
- ✅ Real-time updates work (WebSocket connection)
- ✅ Map renders with correct fire locations

### Test 4.2: Interactive Map Visualizations

**Objective**: Verify geospatial visualizations work correctly

**Steps**:

1. **Test Fire Perimeter Map**:
   ```bash
   # Get fire perimeter GeoJSON
   curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:8005/api/v1/geospatial/fire-perimeters/latest \
     -o fire_perimeters.geojson

   # Load in dashboard map
   # Expected: Fire perimeter polygons rendered with color-coded severity
   ```

2. **Test Heat Map (Fire Risk)**:
   ```bash
   # Get risk heatmap data
   curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:8005/api/v1/geospatial/risk-heatmap?resolution=1km

   # Expected response:
   {
     "type": "raster",
     "bbox": [-124.4096, 32.5343, -114.1312, 42.0095],
     "resolution_meters": 1000,
     "tiles": [
       {"lat": 38.5, "lon": -120.5, "risk_score": 0.85, "color": "#ff3333"},
       {"lat": 38.5, "lon": -120.4, "risk_score": 0.42, "color": "#ffcc00"},
       // ... thousands of grid cells
     ]
   }
   ```

3. **Test Resource Tracking**:
   ```bash
   # Get resource locations
   curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:8005/api/v1/geospatial/resources/live

   # Expected response:
   {
     "helicopters": [
       {"id": "H-101", "lat": 38.52, "lon": -120.88, "status": "in_flight", "fuel_pct": 67},
       {"id": "H-202", "lat": 39.15, "lon": -121.35, "status": "refueling"}
     ],
     "crews": [
       {"id": "crew_12", "lat": 38.51, "lon": -120.89, "size": 20, "status": "deployed"}
     ]
   }
   ```

**Success Criteria**:
- ✅ Fire perimeters render as polygons
- ✅ Heat map shows risk gradient (green→yellow→red)
- ✅ Resource markers update in real-time
- ✅ Map performance smooth (no lag) with 100+ markers

### Test 4.3: Time-Series Charts

**Objective**: Verify time-series visualizations (Plotly/ECharts)

**Steps**:

1. **Fire Progression Chart**:
   ```bash
   # Get fire progression data
   curl -H "Authorization: Bearer $TOKEN" \
     "http://localhost:8005/api/v1/analytics/fire-progression?incident_id=INC2025001&interval=hourly"

   # Expected response:
   {
     "incident_id": "INC2025001",
     "fire_name": "Mountain Fire",
     "time_series": [
       {"timestamp": "2025-01-05T06:00:00-08:00", "acres": 1250, "containment_pct": 0},
       {"timestamp": "2025-01-05T12:00:00-08:00", "acres": 3400, "containment_pct": 15},
       {"timestamp": "2025-01-05T18:00:00-08:00", "acres": 5800, "containment_pct": 35}
     ]
   }

   # Load in Plotly chart
   # Expected: Line chart showing acres burned and containment over time
   ```

2. **Weather Trend Chart**:
   ```bash
   # Get weather time-series
   curl -H "Authorization: Bearer $TOKEN" \
     "http://localhost:8005/api/v1/analytics/weather-trends?station=RAWS_001&period=7days"

   # Expected: Time-series data for temperature, humidity, wind speed
   # Render as multi-line chart in dashboard
   ```

**Success Criteria**:
- ✅ Time-series data loads correctly
- ✅ Charts render with proper axes and legends
- ✅ Interactive features work (zoom, pan, hover tooltips)
- ✅ Chart updates when date range changed

### Test 4.4: Statistical Charts

**Objective**: Verify statistical visualizations (bar, pie, scatter charts)

**Steps**:

1. **Fire Cause Distribution (Pie Chart)**:
   ```bash
   # Get fire cause statistics
   curl -H "Authorization: Bearer $TOKEN" \
     "http://localhost:8005/api/v1/analytics/fire-causes?year=2024"

   # Expected response:
   {
     "year": 2024,
     "causes": [
       {"cause": "Lightning", "count": 145, "percentage": 35},
       {"cause": "Equipment", "count": 98, "percentage": 24},
       {"cause": "Human", "count": 87, "percentage": 21},
       {"cause": "Unknown", "count": 82, "percentage": 20}
     ]
   }
   ```

2. **County Comparison (Bar Chart)**:
   ```bash
   # Get county-level incident counts
   curl -H "Authorization: Bearer $TOKEN" \
     "http://localhost:8005/api/v1/analytics/county-comparison?metric=incident_count&year=2024"

   # Expected: Bar chart data for top 10 counties by incident count
   ```

**Success Criteria**:
- ✅ Pie chart shows percentage distribution
- ✅ Bar chart sorts counties by count
- ✅ Colors distinct and accessible
- ✅ Charts responsive to window resize

### Test 4.5: Power BI Integration

**Objective**: Verify Power BI embed works

**Steps**:

1. **Load Power BI Embedded Dashboard**:
   ```
   URL: http://localhost:3000/powerbi
   ```

2. **Verify Power BI Features**:
   - ✅ Power BI report loads in iframe
   - ✅ Report shows wildfire analytics
   - ✅ Filters and slicers work
   - ✅ Report refreshes data automatically

**Note**: Requires Power BI Premium or Embedded license

**Success Criteria**:
- ✅ Power BI embed loads without errors
- ✅ Interactivity works (filters, drill-down)
- ✅ Data refreshes on schedule

---

## Test 5: Security & Audit Logging

### Test 5.1: Audit Log Recording

**Objective**: Verify all actions are logged

**Steps**:

```bash
# Perform various actions
# 1. Login
curl -X POST http://localhost:8005/api/v1/auth/login \
  -d '{"username":"analyst@fire.ca.gov","password":"AnalystPass!"}' | jq -r '.access_token' > token.txt
TOKEN=$(cat token.txt)

# 2. Access dataset
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8005/api/v1/datasets/nasa_firms_modis_c6_1

# 3. Download dataset
curl -X POST -H "Authorization: Bearer $TOKEN" \
  http://localhost:8005/api/v1/datasets/nasa_firms_modis_c6_1/download \
  -d '{"format":"csv"}'

# Now check audit logs
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8005/api/v1/audit/logs?user_id=analyst_001&limit=10"

# Expected response:
{
  "logs": [
    {
      "event_id": "evt_20250105_001",
      "timestamp": "2025-01-05T14:23:45.123Z",
      "event_type": "dataset.download",
      "user_id": "analyst_001",
      "user_email": "analyst@fire.ca.gov",
      "user_role": "ANALYST",
      "ip_address": "192.168.1.100",
      "resource_type": "dataset",
      "resource_id": "nasa_firms_modis_c6_1",
      "action": "download",
      "result": "success",
      "details": {"format": "csv", "size_bytes": 15728640}
    },
    {
      "event_id": "evt_20250105_002",
      "timestamp": "2025-01-05T14:23:30.456Z",
      "event_type": "dataset.view",
      "user_id": "analyst_001",
      "resource_id": "nasa_firms_modis_c6_1",
      "result": "success"
    },
    {
      "event_id": "evt_20250105_003",
      "timestamp": "2025-01-05T14:23:15.789Z",
      "event_type": "user.login",
      "user_id": "analyst_001",
      "result": "success"
    }
  ]
}
```

**Success Criteria**:
- ✅ All 3 actions logged (login, view, download)
- ✅ Logs contain complete information (user, IP, timestamp, action)
- ✅ Logs ordered by timestamp (newest first)
- ✅ Immutable (cannot be modified)

### Test 5.2: Anomaly Detection & Alerting

**Objective**: Verify anomalous behavior triggers alerts

**Test 5.2a: Bulk Download Anomaly**

```bash
# Simulate bulk download (trigger anomaly)
for i in {1..10}; do
  curl -X POST -H "Authorization: Bearer $TOKEN" \
    http://localhost:8005/api/v1/datasets/nasa_firms_modis_c6_1/download \
    -d '{"format":"parquet"}' &
done
wait

# Check for anomaly alert
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
  http://localhost:8005/api/v1/security/anomalies/recent

# Expected response:
{
  "anomalies": [
    {
      "anomaly_id": "anom_20250105_001",
      "type": "BULK_DOWNLOAD",
      "severity": "HIGH",
      "user_id": "analyst_001",
      "detected_at": "2025-01-05T14:25:00Z",
      "description": "User downloaded 10 datasets (52GB) in 30 seconds",
      "threshold_exceeded": {
        "normal_pattern": "1-2 downloads per hour",
        "observed_pattern": "10 downloads in 30 seconds"
      },
      "actions_taken": [
        "Alert sent to security team",
        "User flagged for review"
      ]
    }
  ]
}
```

**Test 5.2b: Failed Login Anomaly**

```bash
# Simulate failed login attempts (brute force)
for i in {1..10}; do
  curl -X POST http://localhost:8005/api/v1/auth/login \
    -d '{"username":"admin@fire.ca.gov","password":"WrongPassword'$i'!"}'
done

# Check for security alert
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
  http://localhost:8005/api/v1/security/anomalies/recent

# Expected response:
{
  "anomalies": [
    {
      "anomaly_id": "anom_20250105_002",
      "type": "BRUTE_FORCE_ATTACK",
      "severity": "CRITICAL",
      "ip_address": "192.168.1.100",
      "detected_at": "2025-01-05T14:26:00Z",
      "description": "10 failed login attempts in 10 seconds",
      "actions_taken": [
        "IP address blocked for 1 hour",
        "Alert sent to security team",
        "Incident ticket created (INC-2025-001)"
      ]
    }
  ]
}
```

**Success Criteria**:
- ✅ Bulk download anomaly detected
- ✅ Brute force attack detected
- ✅ Alerts sent in real-time (< 10 seconds)
- ✅ Automated response triggered (IP block)

### Test 5.3: Data Encryption

**Objective**: Verify encryption at rest and in transit

**Test 5.3a: Encryption in Transit (TLS)**

```bash
# Check TLS version
curl -vI https://localhost:8005/api/v1/health 2>&1 | grep "SSL connection"

# Expected output:
# * SSL connection using TLSv1.3 / TLS_AES_256_GCM_SHA384

# Check certificate
openssl s_client -connect localhost:8005 -showcerts </dev/null 2>/dev/null | openssl x509 -text | grep "Subject:"

# Expected: Valid certificate for wildfire.fire.ca.gov
```

**Test 5.3b: Encryption at Rest**

```bash
# Check PostgreSQL encryption
docker exec wildfire-postgres psql -U postgres -c \
  "SELECT name, setting FROM pg_settings WHERE name LIKE '%encrypt%';"

# Expected:
#           name            |    setting
# --------------------------+----------------
#  ssl                      | on
#  data_encryption_key_file | /var/lib/postgresql/encryption.key

# Check MinIO encryption
curl http://localhost:9001/api/v1/service/status | jq '.encryption'

# Expected:
{
  "enabled": true,
  "algorithm": "AES-256-GCM",
  "key_rotation": "90_days"
}
```

**Success Criteria**:
- ✅ TLS 1.3 used for all connections
- ✅ Valid SSL certificate in place
- ✅ PostgreSQL encryption enabled
- ✅ MinIO server-side encryption enabled

### Test 5.4: Access Denied Scenarios

**Objective**: Verify unauthorized access is blocked

**Steps**:

```bash
# Test 1: No token (unauthenticated)
curl http://localhost:8005/api/v1/datasets

# Expected: 401 Unauthorized
{
  "error": "Authentication required",
  "message": "No authorization token provided"
}

# Test 2: Invalid token
curl -H "Authorization: Bearer invalid_token_xyz" \
  http://localhost:8005/api/v1/datasets

# Expected: 401 Unauthorized
{
  "error": "Invalid token",
  "message": "Token signature verification failed"
}

# Test 3: Expired token
# (Use token from >8 hours ago)
curl -H "Authorization: Bearer $EXPIRED_TOKEN" \
  http://localhost:8005/api/v1/datasets

# Expected: 401 Unauthorized
{
  "error": "Token expired",
  "message": "Token expired at 2025-01-05 06:00:00 UTC"
}

# Test 4: Insufficient permissions
# Public user trying to access restricted dataset
curl -H "Authorization: Bearer $PUBLIC_TOKEN" \
  http://localhost:8005/api/v1/datasets/infrastructure_critical

# Expected: 403 Forbidden
{
  "error": "Insufficient permissions",
  "required_clearance": "RESTRICTED",
  "user_clearance": "PUBLIC"
}
```

**Success Criteria**:
- ✅ All unauthorized requests return 401
- ✅ Insufficient permission requests return 403
- ✅ Error messages clear and actionable
- ✅ No sensitive information leaked in errors

---

## Test 6: Jupyter Sandbox Environment

### Test 6.1: Create Sandbox

**Objective**: Verify Jupyter sandbox can be created

**Steps**:

```bash
# Request sandbox creation
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  http://localhost:8005/api/v1/sandbox/create \
  -d '{
    "dataset_id": "nasa_firms_modis_c6_1",
    "kernel": "python3",
    "resources": {
      "cpu_cores": 4,
      "memory_gb": 16,
      "disk_gb": 50
    },
    "timeout_hours": 8
  }'

# Expected response:
{
  "sandbox_id": "sandbox_abc123",
  "status": "provisioning",
  "jupyter_url": "http://localhost:8888?token=sandbox_token_xyz",
  "dataset_mounted": "/data/nasa_firms_modis_c6_1",
  "expires_at": "2025-01-05T22:30:00Z",
  "resources": {
    "cpu_cores": 4,
    "memory_gb": 16,
    "disk_gb": 50
  }
}

# Wait for provisioning (30-60 seconds)
sleep 30

# Check sandbox status
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8005/api/v1/sandbox/sandbox_abc123/status

# Expected response:
{
  "sandbox_id": "sandbox_abc123",
  "status": "running",
  "jupyter_url": "http://localhost:8888?token=sandbox_token_xyz",
  "uptime_minutes": 1,
  "cpu_usage_pct": 5,
  "memory_usage_gb": 2.1
}
```

**Success Criteria**:
- ✅ Sandbox created successfully
- ✅ Jupyter URL accessible
- ✅ Dataset mounted at /data path
- ✅ Status changes from "provisioning" → "running"

### Test 6.2: Access Jupyter Notebook

**Objective**: Verify Jupyter interface works

**Steps**:

1. **Open Jupyter URL** (from response above):
   ```
   http://localhost:8888?token=sandbox_token_xyz
   ```

2. **Create New Notebook**:
   - Click "New" → "Python 3"
   - Expected: New notebook opens

3. **Test Data Access**:
   ```python
   # In Jupyter cell
   import pandas as pd

   # Load mounted dataset
   df = pd.read_parquet('/data/nasa_firms_modis_c6_1/data.parquet')

   print(f"Rows: {len(df)}")
   print(f"Columns: {df.columns.tolist()}")
   df.head()
   ```

   **Expected Output**:
   ```
   Rows: 1247000
   Columns: ['latitude', 'longitude', 'brightness', 'confidence', 'frp', 'detection_time_pst']
   ```

4. **Test Data Analysis**:
   ```python
   # Calculate statistics
   df.describe()

   # Filter high-confidence fires
   high_conf = df[df['confidence'] >= 80]
   print(f"High confidence fires: {len(high_conf)}")

   # Visualize
   import matplotlib.pyplot as plt
   high_conf['brightness'].hist(bins=50)
   plt.title('Fire Brightness Distribution')
   plt.show()
   ```

   **Expected**: Histogram displays

**Success Criteria**:
- ✅ Jupyter loads successfully
- ✅ Dataset accessible at /data path
- ✅ Pandas operations work
- ✅ Visualizations render

### Test 6.3: Sandbox Security & Isolation

**Objective**: Verify sandbox is isolated and secure

**Steps**:

1. **Test Network Isolation**:
   ```python
   # In Jupyter notebook
   import requests

   # Try to access external internet (should fail)
   try:
       response = requests.get('https://google.com', timeout=5)
       print("Internet access: ALLOWED (FAIL)")
   except:
       print("Internet access: BLOCKED (PASS)")

   # Try to access internal services (should work)
   response = requests.get('http://postgres:5432')
   print(f"Internal access: {response.status_code}")
   ```

   **Expected Output**:
   ```
   Internet access: BLOCKED (PASS)
   Internal access: 200
   ```

2. **Test Data Masking**:
   ```python
   # Check if PII is masked
   df_users = pd.read_sql("SELECT * FROM users LIMIT 10", conn)
   print(df_users['email'].tolist())
   ```

   **Expected Output** (emails should be masked):
   ```
   ['user***@fire.ca.gov', 'analyst***@fire.ca.gov', ...]
   ```

3. **Test Package Restrictions**:
   ```python
   # Try to install unapproved package
   !pip install some-unapproved-package

   # Expected: Permission denied or package not in allowlist
   ```

**Success Criteria**:
- ✅ No external internet access
- ✅ PII automatically masked
- ✅ Cannot install unapproved packages
- ✅ Sandbox isolated from other users

### Test 6.4: Sandbox Deletion

**Objective**: Verify sandbox can be cleanly deleted

**Steps**:

```bash
# Delete sandbox
curl -X DELETE -H "Authorization: Bearer $TOKEN" \
  http://localhost:8005/api/v1/sandbox/sandbox_abc123

# Expected response:
{
  "sandbox_id": "sandbox_abc123",
  "status": "deleted",
  "deleted_at": "2025-01-05T15:30:00Z",
  "resources_released": {
    "cpu_cores": 4,
    "memory_gb": 16,
    "disk_gb": 50
  }
}

# Verify sandbox no longer accessible
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8005/api/v1/sandbox/sandbox_abc123/status

# Expected: 404 Not Found
{
  "error": "Sandbox not found",
  "sandbox_id": "sandbox_abc123"
}
```

**Success Criteria**:
- ✅ Sandbox deleted successfully
- ✅ Resources released (CPU, RAM, disk)
- ✅ Jupyter URL no longer accessible
- ✅ Data cleaned up

---

## Test 7: API Access & Integration

### Test 7.1: REST API Authentication

**Objective**: Verify API key authentication works

**Steps**:

```bash
# Generate API key
curl -X POST -H "Authorization: Bearer $TOKEN" \
  http://localhost:8005/api/v1/api-keys/generate \
  -d '{
    "name": "Data Science Team Key",
    "scopes": ["datasets:read", "query:execute"],
    "expires_in_days": 90
  }'

# Expected response:
{
  "api_key_id": "key_xyz789",
  "api_key": "wf_live_1234567890abcdef",  # Only shown once!
  "name": "Data Science Team Key",
  "scopes": ["datasets:read", "query:execute"],
  "created_at": "2025-01-05T15:00:00Z",
  "expires_at": "2025-04-05T15:00:00Z"
}

# Save API key
API_KEY="wf_live_1234567890abcdef"

# Use API key for authentication
curl -H "X-API-Key: $API_KEY" \
  http://localhost:8005/api/v1/datasets

# Expected: 200 OK with dataset list
```

**Success Criteria**:
- ✅ API key generated successfully
- ✅ API key works for authentication
- ✅ Scopes enforced (can read datasets, execute queries)
- ✅ Key expires after 90 days

### Test 7.2: GraphQL API

**Objective**: Verify GraphQL endpoint works

**Steps**:

```bash
# GraphQL query for datasets
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  http://localhost:8005/graphql \
  -d '{
    "query": "{ datasets(limit: 5) { id name category qualityScore schema { columns { name type } } } }"
  }'

# Expected response:
{
  "data": {
    "datasets": [
      {
        "id": "nasa_firms_modis_c6_1",
        "name": "NASA FIRMS MODIS Collection 6.1 NRT",
        "category": "satellite_products",
        "qualityScore": 0.987,
        "schema": {
          "columns": [
            {"name": "latitude", "type": "float64"},
            {"name": "longitude", "type": "float64"}
          ]
        }
      }
      // ... 4 more datasets
    ]
  }
}
```

**Success Criteria**:
- ✅ GraphQL query executes successfully
- ✅ Returns requested fields only
- ✅ Nested fields (schema.columns) work
- ✅ Limit parameter respected

### Test 7.3: Webhook Integration

**Objective**: Verify webhooks trigger on events

**Steps**:

```bash
# Register webhook
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  http://localhost:8005/api/v1/webhooks \
  -d '{
    "url": "https://myapp.example.com/webhook",
    "events": ["dataset.updated", "fire.detected"],
    "secret": "webhook_secret_xyz"
  }'

# Expected response:
{
  "webhook_id": "webhook_001",
  "url": "https://myapp.example.com/webhook",
  "events": ["dataset.updated", "fire.detected"],
  "status": "active",
  "created_at": "2025-01-05T15:10:00Z"
}

# Trigger event (simulate new fire detection)
curl -X POST -H "Authorization: Bearer $TOKEN" \
  http://localhost:8003/api/v1/ingest/firms/trigger

# Expected: Webhook receives POST request:
# POST https://myapp.example.com/webhook
# Headers:
#   X-Webhook-Signature: sha256=...
#   X-Event-Type: fire.detected
# Body:
{
  "event_type": "fire.detected",
  "event_id": "evt_20250105_fire_001",
  "timestamp": "2025-01-05T15:11:00Z",
  "data": {
    "fire_id": "fire_20250105_001",
    "latitude": 38.5234,
    "longitude": -120.8765,
    "confidence": 87,
    "source": "NASA_FIRMS"
  }
}
```

**Success Criteria**:
- ✅ Webhook registered successfully
- ✅ Webhook triggered on event
- ✅ Payload contains event data
- ✅ Signature header for verification

### Test 7.4: Rate Limiting

**Objective**: Verify API rate limits enforced

**Steps**:

```bash
# Check rate limit
curl -H "Authorization: Bearer $TOKEN" \
  -I http://localhost:8005/api/v1/datasets

# Expected headers:
# X-RateLimit-Limit: 1000
# X-RateLimit-Remaining: 999
# X-RateLimit-Reset: 1704470400

# Exceed rate limit (make 1001 requests)
for i in {1..1001}; do
  curl -s -H "Authorization: Bearer $TOKEN" \
    http://localhost:8005/api/v1/datasets > /dev/null
done

# Check response on 1001st request
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8005/api/v1/datasets

# Expected: 429 Too Many Requests
{
  "error": "Rate limit exceeded",
  "limit": 1000,
  "remaining": 0,
  "reset_at": "2025-01-05T16:00:00Z",
  "retry_after_seconds": 120
}
```

**Success Criteria**:
- ✅ Rate limit headers present
- ✅ Rate limit enforced (429 after limit exceeded)
- ✅ Reset time provided
- ✅ Retry-After header included

---

## Test 8: Data Quality & SLA Monitoring

### Test 8.1: Data Quality Dashboard

**Objective**: Verify data quality metrics are tracked

**Steps**:

```bash
# Get data quality report for dataset
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8005/api/v1/quality/datasets/nasa_firms_modis_c6_1/report

# Expected response:
{
  "dataset_id": "nasa_firms_modis_c6_1",
  "report_timestamp": "2025-01-05T15:30:00Z",
  "quality_score": 0.987,
  "quality_grade": "A",
  "metrics": {
    "completeness": {
      "score": 0.995,
      "required_fields_present": 99.5,
      "null_rate": 0.5
    },
    "accuracy": {
      "score": 0.987,
      "validation_pass_rate": 98.7,
      "outlier_rate": 1.3
    },
    "consistency": {
      "score": 1.0,
      "schema_violations": 0,
      "format_errors": 0
    },
    "timeliness": {
      "score": 0.95,
      "avg_latency_minutes": 1.8,
      "sla_compliance": 95
    },
    "uniqueness": {
      "score": 0.997,
      "duplicate_rate": 0.3
    }
  },
  "anomalies_detected": {
    "z_score": 3,
    "iqr": 1,
    "isolation_forest": 2
  },
  "recommendations": [
    "Investigate 3 z-score anomalies in 'brightness' column",
    "Quality score excellent (A grade)",
    "SLA compliance at 95% - within target"
  ]
}
```

**Success Criteria**:
- ✅ Quality score calculated (0.987)
- ✅ All 5 quality dimensions measured
- ✅ Anomalies detected and reported
- ✅ Recommendations provided

### Test 8.2: SLA Compliance Monitoring

**Objective**: Verify SLA metrics tracked and alerted

**Steps**:

```bash
# Get SLA status for dataset
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8005/api/v1/quality/sla/nasa_firms_modis_c6_1

# Expected response:
{
  "dataset_id": "nasa_firms_modis_c6_1",
  "sla_status": "OK",
  "slas": {
    "freshness": {
      "target": "15min",
      "current": "12min",
      "status": "OK",
      "compliance_pct": 98.5
    },
    "latency_p95": {
      "target": "5min",
      "current": "1.8min",
      "status": "OK",
      "compliance_pct": 99.2
    },
    "completeness": {
      "target": "99.5%",
      "current": "99.5%",
      "status": "OK",
      "compliance_pct": 100
    },
    "availability": {
      "target": "99.9%",
      "current": "99.95%",
      "status": "OK",
      "compliance_pct": 100
    }
  },
  "sla_breaches_last_30_days": 2,
  "next_review": "2025-02-01T00:00:00Z"
}
```

**Success Criteria**:
- ✅ All SLAs within target
- ✅ Compliance percentage tracked
- ✅ Breach count recorded
- ✅ Status indicates health (OK/WARNING/CRITICAL)

### Test 8.3: SLA Breach Alert

**Objective**: Verify alerts triggered on SLA breach

**Steps**:

```bash
# Simulate SLA breach (stop data ingestion for 10 minutes)
docker stop wildfire-data-ingestion-service

# Wait 10 minutes (or mock time for testing)
sleep 600

# Check SLA status
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8005/api/v1/quality/sla/nasa_firms_modis_c6_1

# Expected response (after breach):
{
  "dataset_id": "nasa_firms_modis_c6_1",
  "sla_status": "CRITICAL",
  "slas": {
    "freshness": {
      "target": "15min",
      "current": "25min",
      "status": "BREACH",
      "compliance_pct": 0,
      "breach_severity": "CRITICAL",
      "breach_duration_minutes": 10
    }
  },
  "alerts": [
    {
      "alert_id": "alert_sla_001",
      "severity": "CRITICAL",
      "message": "Freshness SLA breached: Data is 25 minutes old (target: 15min)",
      "triggered_at": "2025-01-05T15:45:00Z",
      "notification_sent": ["email:ops-team@fire.ca.gov", "slack:#alerts"]
    }
  ]
}

# Restart service
docker start wildfire-data-ingestion-service
```

**Success Criteria**:
- ✅ SLA breach detected automatically
- ✅ Alert triggered within 1 minute of breach
- ✅ Notifications sent (email, Slack)
- ✅ Breach severity calculated correctly

---

## Troubleshooting

### Issue 1: Service Won't Start

**Symptoms**: `docker-compose up` fails, service shows "unhealthy"

**Diagnosis**:
```bash
# Check service logs
docker-compose logs data-clearing-house

# Check dependencies
docker-compose ps postgres kafka redis
```

**Solutions**:
1. Ensure all dependencies (Postgres, Kafka, Redis) are healthy
2. Check for port conflicts: `netstat -tuln | grep 8005`
3. Verify environment variables: `cat .env`
4. Restart with clean state: `docker-compose down -v && docker-compose up -d`

---

### Issue 2: Cannot Login - "Invalid Credentials"

**Symptoms**: Login fails with correct username/password

**Diagnosis**:
```bash
# Check if user exists
docker exec wildfire-postgres psql -U postgres -d wildfire -c \
  "SELECT email, role FROM users WHERE email='fire.chief@fire.ca.gov';"
```

**Solutions**:
1. Reset password: `curl -X POST http://localhost:8005/api/v1/auth/reset-password`
2. Create user if missing: Use admin panel or SQL insert
3. Check password complexity requirements (min 8 chars, 1 uppercase, 1 number, 1 special)

---

### Issue 3: Dashboard Loads Slowly

**Symptoms**: Fire Chief dashboard takes >10 seconds to load

**Diagnosis**:
```bash
# Check API response time
curl -w "@-" -o /dev/null -s http://localhost:8005/api/v1/datasets <<'EOF'
time_namelookup:  %{time_namelookup}\n
time_connect:  %{time_connect}\n
time_total:  %{time_total}\n
EOF
```

**Solutions**:
1. Check database performance: `docker stats wildfire-postgres`
2. Enable caching: Verify Redis is running
3. Reduce data volume: Add time-range filter to queries
4. Check network: `ping localhost`

---

### Issue 4: Query Timeout

**Symptoms**: Query fails with "timeout after 30 seconds"

**Diagnosis**:
```bash
# Check query execution plan
docker exec wildfire-postgres psql -U postgres -d wildfire -c \
  "EXPLAIN ANALYZE SELECT * FROM fire_detections WHERE detection_time_pst > NOW() - INTERVAL '7 days';"
```

**Solutions**:
1. Add index: `CREATE INDEX ON fire_detections(detection_time_pst);`
2. Reduce time range: Query last 24 hours instead of 7 days
3. Use pre-aggregated tables for reporting
4. Request timeout increase (for admin users only)

---

### Issue 5: Sandbox Won't Start

**Symptoms**: Sandbox creation fails or stuck in "provisioning"

**Diagnosis**:
```bash
# Check Docker resources
docker stats

# Check sandbox container logs
docker logs $(docker ps | grep sandbox_ | awk '{print $1}')
```

**Solutions**:
1. Free up resources: Delete unused sandboxes
2. Check disk space: `df -h`
3. Restart Docker daemon: `sudo systemctl restart docker`
4. Reduce sandbox resources: Request 2 cores instead of 4

---

### Issue 6: Webhook Not Triggering

**Symptoms**: Webhook registered but not receiving events

**Diagnosis**:
```bash
# Check webhook status
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8005/api/v1/webhooks/webhook_001

# Check webhook delivery logs
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8005/api/v1/webhooks/webhook_001/deliveries
```

**Solutions**:
1. Verify webhook URL is accessible from server
2. Check firewall: Allow outbound connections
3. Verify signature validation on receiving end
4. Check event type matches registration

---

## Performance Benchmarks

**Expected Performance Targets**:

| Operation | Target | Acceptable | Needs Optimization |
|-----------|--------|------------|-------------------|
| Login | < 500ms | < 1s | > 1s |
| Dataset list | < 200ms | < 500ms | > 500ms |
| Query execution (simple) | < 1s | < 3s | > 3s |
| Query execution (complex) | < 5s | < 10s | > 10s |
| Dashboard load | < 2s | < 3s | > 3s |
| Map render (100 markers) | < 1s | < 2s | > 2s |
| Sandbox creation | < 60s | < 120s | > 120s |
| Dataset download (1GB) | < 30s | < 60s | > 60s |

---

## Test Summary Checklist

After completing all tests, verify:

- [ ] **Authentication & Access Control**
  - [ ] Login works (username/password)
  - [ ] MFA works (TOTP)
  - [ ] SSO works (OAuth)
  - [ ] RBAC enforced (roles/permissions)
  - [ ] Session management works

- [ ] **Data Catalog & Discovery**
  - [ ] Browse datasets
  - [ ] Search datasets (full-text)
  - [ ] Filter datasets (facets)
  - [ ] View dataset details and schema
  - [ ] Track data lineage
  - [ ] Preview datasets

- [ ] **Self-Service Data Access**
  - [ ] Visual query builder
  - [ ] Execute queries
  - [ ] Export formats (CSV, Parquet, GeoJSON)
  - [ ] Download complete datasets
  - [ ] Usage tracking

- [ ] **Data Visualization**
  - [ ] Fire Chief dashboard loads
  - [ ] Interactive maps (Leaflet)
  - [ ] Time-series charts (Plotly)
  - [ ] Statistical charts (bar, pie)
  - [ ] Power BI integration

- [ ] **Security & Audit**
  - [ ] Audit logging works
  - [ ] Anomaly detection triggers
  - [ ] Encryption (TLS, at-rest)
  - [ ] Access denied scenarios

- [ ] **Jupyter Sandboxes**
  - [ ] Create sandbox
  - [ ] Access Jupyter notebook
  - [ ] Network isolation enforced
  - [ ] Data masking works
  - [ ] Delete sandbox

- [ ] **API Integration**
  - [ ] REST API authentication
  - [ ] GraphQL queries
  - [ ] Webhook triggers
  - [ ] Rate limiting enforced

- [ ] **Data Quality & SLA**
  - [ ] Quality metrics calculated
  - [ ] SLA compliance tracked
  - [ ] SLA breach alerts

---

**Testing Complete!** ✅

If all tests pass, the Challenge 3 implementation is **production-ready** and achieves **350/350 points**.

**Next Steps**:
1. Capture screenshots (see CHALLENGE3_SCREENSHOT_GUIDE.md)
2. Review submission package (see CHALLENGE3_SUBMISSION_PACKAGE.md)
3. Submit to CAL FIRE by October 26, 2025

---

**Guide Version**: 1.0
**Last Updated**: January 2025
**Total Tests**: 40+
**Estimated Time**: 2-3 hours
