# Data Flow Architecture

## Overview

The Wildfire Intelligence Platform implements a comprehensive data pipeline that processes diverse data sources in real-time and batch modes. This document details the data flow patterns, processing stages, and integration points.

## Data Sources & Ingestion

### 1. Satellite Data Sources

```mermaid
graph TD
    A[NASA FIRMS API] --> B[Satellite Connector]
    C[MODIS Active Fire] --> B
    D[VIIRS Fire Detection] --> B
    E[Landsat Thermal] --> B
    F[Sentinel-2 MSI] --> B
    G[Sentinel-3 SLSTR] --> B
    
    B --> H[Data Validation]
    H --> I[Format Standardization]
    I --> J[Kafka: wildfire-satellite-raw]
```

**Satellite Data Flow Details:**
- **Frequency**: Every 12-24 hours (depending on satellite)
- **Volume**: ~50,000 fire detection points/day (California)
- **Format**: CSV, JSON, GeoTIFF, NetCDF
- **Processing**: Real-time validation, coordinate transformation, quality scoring

### 2. Weather Data Sources

```mermaid
graph TD
    A[Copernicus CDS API] --> B[Weather Connector]
    C[ERA5 Reanalysis] --> B
    D[ERA5-Land] --> B
    E[NOAA GFS Forecast] --> B
    F[NAM Forecast] --> B
    G[METAR Stations] --> B
    
    B --> H[Data Processing]
    H --> I[Unit Conversion]
    I --> J[Derived Variables]
    J --> K[Kafka: wildfire-weather-raw]
```

**Weather Data Flow Details:**
- **Frequency**: Hourly updates, 3-hour batches
- **Volume**: ~100MB NetCDF files per day
- **Coverage**: 0.25deg grid resolution (California)
- **Variables**: Temperature, humidity, wind, precipitation, pressure

### 3. IoT Sensor Data

```mermaid
graph TD
    A[AWS IoT Core] --> B[IoT Connector]
    C[LoRaWAN Gateway] --> B
    D[Cellular Sensors] --> B
    E[Satellite Sensors] --> B
    
    B --> F[Message Validation]
    F --> G[Time Synchronization]
    G --> H[Anomaly Detection]
    H --> I[Kafka: wildfire-sensors-raw]
```

**IoT Sensor Data Flow Details:**
- **Frequency**: Real-time streaming (1-15 minute intervals)
- **Volume**: ~10,000 sensor readings/hour
- **Types**: Temperature, humidity, smoke, air quality, wind
- **Protocol**: MQTT, LoRaWAN, HTTP POST

## Data Processing Pipeline

### 1. Real-Time Stream Processing

```mermaid
graph LR
    A[Kafka Raw Topics] --> B[Stream Processor]
    B --> C[Data Enrichment]
    C --> D[Feature Engineering]
    D --> E[ML Feature Store]
    E --> F[Real-time Predictions]
    F --> G[Alert Generation]
    G --> H[Notification Service]
    
    B --> I[Data Quality Checks]
    I --> J[Quality Metrics]
    
    C --> K[Geospatial Indexing]
    K --> L[Spatial Queries]
```

**Stream Processing Details:**
- **Technology**: Kafka Streams, Apache Flink
- **Latency**: < 100ms end-to-end
- **Throughput**: 10,000+ events/second
- **Features**: Windowing, aggregations, joins, pattern detection

### 2. Batch Processing Pipeline

```mermaid
graph TD
    A[Scheduled Jobs] --> B[Data Lake]
    B --> C[ETL Pipeline]
    C --> D[Data Warehouse]
    D --> E[Analytics Engine]
    E --> F[ML Training Pipeline]
    F --> G[Model Registry]
    
    C --> H[Data Quality Reports]
    E --> I[Business Intelligence]
    F --> J[Model Validation]
```

**Batch Processing Details:**
- **Technology**: Apache Airflow, Apache Spark
- **Schedule**: Hourly, daily, weekly jobs
- **Volume**: TB-scale historical data processing
- **Operations**: Aggregations, ML training, report generation

### 3. Machine Learning Pipeline

```mermaid
graph TD
    A[Raw Data] --> B[Feature Engineering]
    B --> C[Feature Store]
    C --> D[Model Training]
    D --> E[Model Validation]
    E --> F[Model Registry]
    F --> G[Model Serving]
    
    G --> H[Real-time Inference]
    G --> I[Batch Predictions]
    
    H --> J[Risk Scoring API]
    I --> K[Forecast Reports]
    
    E --> L[Performance Monitoring]
    L --> M[Model Retraining]
    M --> D
```

**ML Pipeline Details:**
- **Framework**: MLflow, Kubeflow
- **Models**: Fire risk classification, spread prediction, intensity forecasting
- **Features**: Weather patterns, vegetation indices, historical fire data
- **Serving**: REST API, batch scoring

## Data Storage Architecture

### 1. Multi-Tier Storage Strategy

```mermaid
graph TD
    A[Hot Tier - Redis] --> B[Warm Tier - PostgreSQL]
    B --> C[Cold Tier - MinIO]
    
    D[Time Series - InfluxDB] --> E[Search - Elasticsearch]
    
    F[ML Models - MLflow] --> G[Feature Store - Feast]
    
    subgraph "Data Retention"
    H[Real-time: 1 hour]
    I[Recent: 30 days]
    J[Historical: 7 years]
    K[Archive: Indefinite]
    end
```

**Storage Tier Details:**

| Tier | Technology | Purpose | Retention | Performance |
|------|------------|---------|-----------|-------------|
| Hot | Redis | Caching, sessions | 1 hour | mus latency |
| Warm | PostgreSQL/InfluxDB | Active queries | 30 days | ms latency |
| Cold | MinIO S3 | Historical analysis | 7 years | seconds |
| Archive | Glacier | Compliance | Indefinite | minutes |

### 2. Data Partitioning Strategy

```mermaid
graph TD
    A[Incoming Data] --> B{Partition Strategy}
    B -->|Geographic| C[Region-based Shards]
    B -->|Temporal| D[Time-based Partitions]
    B -->|Functional| E[Feature-based Tables]
    
    C --> F[CA-North, CA-South, CA-Central]
    D --> G[Daily, Monthly, Yearly]
    E --> H[Weather, Satellite, Sensors, ML]
```

**Partitioning Benefits:**
- **Query Performance**: Faster queries with partition pruning
- **Maintenance**: Easier backup/restore operations
- **Scalability**: Independent scaling of data segments
- **Compliance**: Data residency and retention policies

## Event-Driven Architecture

### 1. Event Types & Schema

```yaml
# Fire Detection Event
fire_detection_event:
  event_id: "uuid"
  timestamp: "iso8601"
  source: "modis|viirs|landsat"
  location:
    latitude: "float"
    longitude: "float"
    elevation: "float"
  properties:
    confidence: "integer"
    brightness: "float"
    frp: "float" # Fire Radiative Power
  quality_score: "float"

# Weather Update Event
weather_update_event:
  event_id: "uuid"
  timestamp: "iso8601"
  source: "era5|gfs|nam|station"
  location:
    latitude: "float"
    longitude: "float"
  measurements:
    temperature_c: "float"
    humidity_percent: "float"
    wind_speed_ms: "float"
    wind_direction_degrees: "float"
    precipitation_mm: "float"
  forecast_horizon_hours: "integer"

# Risk Assessment Event
risk_assessment_event:
  event_id: "uuid"
  timestamp: "iso8601"
  location:
    latitude: "float"
    longitude: "float"
    radius_km: "float"
  risk_score: "float" # 0.0 - 1.0
  risk_level: "low|medium|high|extreme"
  contributing_factors:
    - weather_conditions: "float"
    - vegetation_dryness: "float"
    - historical_patterns: "float"
  confidence: "float"
  expires_at: "iso8601"
```

### 2. Event Flow Patterns

```mermaid
sequenceDiagram
    participant S as Satellite API
    participant I as Ingestion Service
    participant K as Kafka
    participant R as Risk Service
    participant N as Notification Service
    participant U as User Interface
    
    S->>I: Fire detection data
    I->>I: Validate & transform
    I->>K: Publish fire_detection_event
    K->>R: Consume event
    R->>R: Calculate risk score
    R->>K: Publish risk_assessment_event
    K->>N: Consume high-risk event
    N->>N: Check alert rules
    N->>U: Send alert notification
    K->>U: Real-time dashboard update
```

## Data Quality & Governance

### 1. Data Quality Framework

```mermaid
graph TD
    A[Data Ingestion] --> B[Quality Checks]
    B --> C{Quality Score}
    C -->|High| D[Accept & Process]
    C -->|Medium| E[Flag & Process]
    C -->|Low| F[Reject & Alert]
    
    D --> G[Data Catalog]
    E --> G
    F --> H[Quality Report]
    
    G --> I[Lineage Tracking]
    I --> J[Impact Analysis]
```

**Quality Dimensions:**
- **Completeness**: Missing field detection
- **Accuracy**: Value range validation
- **Consistency**: Cross-source validation
- **Timeliness**: Freshness monitoring
- **Uniqueness**: Duplicate detection

### 2. Data Lineage Tracking

```mermaid
graph LR
    A[Source System] --> B[Ingestion Job]
    B --> C[Raw Data Store]
    C --> D[Transformation Job]
    D --> E[Processed Data Store]
    E --> F[ML Training Job]
    F --> G[Model Artifact]
    G --> H[Prediction Service]
    H --> I[Dashboard/Report]
    
    subgraph "Metadata Tracking"
    J[Data Catalog Service]
    K[Schema Registry]
    L[Job Execution Log]
    M[Performance Metrics]
    end
```

## Performance & Scalability

### 1. Throughput Requirements

| Component | Current Load | Peak Load | Target SLA |
|-----------|--------------|-----------|------------|
| Satellite Data | 1K events/min | 10K events/min | 99.5% uptime |
| Weather Data | 500 events/min | 2K events/min | 99.9% uptime |
| Sensor Data | 10K events/min | 50K events/min | 99.9% uptime |
| Risk Calculations | 100/sec | 1000/sec | <100ms latency |
| Dashboard Updates | 1K queries/min | 10K queries/min | <200ms response |

### 2. Scaling Strategies

```mermaid
graph TD
    A[Load Balancer] --> B[Auto Scaling Group]
    B --> C[Service Instance 1]
    B --> D[Service Instance 2]
    B --> E[Service Instance N]
    
    F[Database] --> G[Read Replica 1]
    F --> H[Read Replica 2]
    
    I[Kafka Cluster] --> J[Partition 1]
    I --> K[Partition 2]
    I --> L[Partition N]
```

**Scaling Triggers:**
- **CPU Utilization** > 70%
- **Memory Usage** > 80%
- **Queue Depth** > 1000 messages
- **Response Time** > 500ms

### 3. Caching Strategy

```mermaid
graph TD
    A[Client Request] --> B[CDN Cache]
    B -->|Miss| C[API Gateway Cache]
    C -->|Miss| D[Application Cache]
    D -->|Miss| E[Database]
    
    E --> F[Cache Population]
    F --> D
    F --> C
    F --> B
```

**Cache Layers:**
- **CDN**: Static assets, API responses (1 hour TTL)
- **API Gateway**: Response caching (15 minutes TTL)
- **Application**: Data objects, query results (5 minutes TTL)
- **Database**: Query result cache (1 minute TTL)

## Monitoring & Alerting

### 1. Data Pipeline Monitoring

```mermaid
graph TD
    A[Data Sources] --> B[Ingestion Monitoring]
    B --> C[Processing Monitoring]
    C --> D[Storage Monitoring]
    D --> E[Serving Monitoring]
    
    B --> F[Data Quality Alerts]
    C --> G[Performance Alerts]
    D --> H[Capacity Alerts]
    E --> I[SLA Alerts]
    
    F --> J[Operations Team]
    G --> J
    H --> J
    I --> J
```

### 2. Key Performance Indicators

```yaml
Data Pipeline KPIs:
  Availability:
    - Data ingestion uptime: 99.9%
    - Processing job success rate: 99.5%
    - API availability: 99.9%
  
  Performance:
    - End-to-end latency: <5 minutes
    - Query response time: <200ms
    - Batch job completion time: <2 hours
  
  Quality:
    - Data quality score: >95%
    - Schema compliance: >99%
    - Duplicate rate: <0.1%
  
  Volume:
    - Daily data ingestion: 10GB
    - Peak event throughput: 50K/min
    - Storage growth rate: 100GB/month
```

This comprehensive data flow architecture ensures reliable, scalable, and efficient processing of wildfire-related data across the entire platform.