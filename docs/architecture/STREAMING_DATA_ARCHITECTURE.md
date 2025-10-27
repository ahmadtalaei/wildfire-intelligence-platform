# 🌊 Robust Streaming Data Architecture for Wildfire Intelligence Platform

## Executive Summary

This document proposes a **production-grade, scalable streaming data architecture** for the CAL FIRE Wildfire Intelligence Platform. This architecture addresses:

✅ High-frequency streaming of satellite/fire/weather data
✅ Large-scale datasets (images, rasters, time series)
✅ Historical storage without excessive cleanup
✅ Dynamic scalability for fire season peaks
✅ Efficient query performance
✅ Low operational maintenance

---

## 1. Current Architecture Analysis

### ✅ Strengths
- **Kafka-based event streaming** already implemented
- **Multi-tier storage** (PostgreSQL, Redis, MinIO, Elasticsearch)
- **Microservices architecture** with clear separation of concerns
- **Docker-based deployment** for portability

### ⚠️ Gaps Identified
1. **No automated data retention policies** → Manual cleanup required (as we just experienced!)
2. **No tiered storage lifecycle** → All data stays in hot storage
3. **Limited batch processing** → No historical data archival automation
4. **No object storage partitioning** → 205GB of Sentinel data with no organization
5. **No streaming data compaction** → Kafka retention set to 7 days only
6. **Limited metadata catalog** → Hard to query historical data efficiently

---

## 2. Recommended Production Architecture

### 2.A. **Streaming Ingestion Layer** (Already Partially Implemented)

```
┌─────────────────────────────────────────────────────────────────┐
│                   DATA SOURCES (Producers)                       │
├─────────────────────────────────────────────────────────────────┤
│ MODIS/VIIRS  │  ERA5/NAM  │  RAWS  │  Sentinel  │  IoT Sensors  │
│  (Kafka)     │  (Kafka)   │ (Kafka)│   (MinIO)  │    (MQTT)     │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│              KAFKA CLUSTER (Event Streaming)                     │
├─────────────────────────────────────────────────────────────────┤
│ Topics:                                                          │
│  • firms.viirs.detections    (Retention: 30 days)                │
│  • weather.era5.hourly       (Retention: 90 days)                │
│  • weather.nam.forecasts     (Retention: 7 days)                 │
│  • sensors.iot.readings      (Retention: 30 days)                │
│  • satellite.sentinel.raw    (Retention: 1 day → Move to MinIO)  │
├─────────────────────────────────────────────────────────────────┤
│ Configuration:                                                   │
│  • Compression: gzip/snappy/lz4                                  │
│  • Partitioning: By region (CA-North, CA-South, CA-Central)      │
│  • Replication Factor: 3 (for production)                        │
│  • Min In-Sync Replicas: 2                                       │
└─────────────────────────────────────────────────────────────────┘
```

**Key Improvements:**
- **Topic-specific retention**: Don't keep forecasts as long as observations
- **Compression enabled**: Reduce storage by 70-80%
- **Partitioning by region**: Parallel processing, easier queries
- **Large files (Sentinel) bypass Kafka**: Go directly to MinIO with metadata in Kafka

---

### 2.B. **Storage Layer - Tiered Architecture**

```
┌────────────────────────────────────────────────────────────────────┐
│                    TIERED STORAGE STRATEGY                         │
└────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│ HOT TIER (0-7 days) - Real-Time Access                           │
├──────────────────────────────────────────────────────────────────┤
│ • Redis (In-Memory Cache) - 10GB                                 │
│   - Active fire detections                                       │
│   - Current weather readings                                     │
│   - Risk scores (last 24 hours)                                  │
│   - User sessions                                                │
│   TTL: 1 hour (auto-expire)                                      │
│                                                                  │
│ • PostgreSQL (Relational + TimescaleDB)                          │
│   - Fire detections (indexed by time + location)                 │
│   - Weather observations (hypertable, 1-day chunks)              │
│   - Sensor readings (compressed, 1-hour chunks)                  │
│   - Forecast data (compressed)                                   │
│   Retention: 7 days → Auto-move to WARM                          │
│   Compression: Enabled on TimescaleDB hypertables                │
│   Size Estimate: 15-20GB                                         │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│ WARM TIER (7-90 days) - Analytical Queries                       │
├──────────────────────────────────────────────────────────────────┤
│ • MinIO (Object Storage) - Partitioned by Date                   │
│   s3://wildfire-data/                                            │
│   ├── weather/                                                   │
│   │   ├── era5/YYYY/MM/DD/era5_YYYYMMDD.parquet                  │
│   │   ├── nam/YYYY/MM/DD/nam_YYYYMMDD.parquet                    │
│   ├── fires/                                                     │
│   │   ├── viirs/YYYY/MM/DD/viirs_YYYYMMDD.parquet                │
│   │   ├── modis/YYYY/MM/DD/modis_YYYYMMDD.parquet                │
│   ├── satellite/                                                 │
│   │   ├── sentinel2/YYYY/MM/DD/tile_name.tif (compressed)        │
│   │   ├── landsat8/YYYY/MM/DD/scene_id.tif (COG format)          │
│   Compression: Parquet (70% reduction), GeoTIFF with LZW          │
│   Size Estimate: 50-100GB                                        │
│                                                                  │
│ • PostgreSQL (Aggregated Data)                                   │
│   - Daily fire summaries                                         │
│   - Hourly weather aggregates                                    │
│   Retention: 90 days → Auto-move to COLD                         │
│   Size Estimate: 5-10GB                                          │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│ COLD TIER (90-365 days) - Historical Analysis                    │
├──────────────────────────────────────────────────────────────────┤
│ • MinIO with Intelligent Tiering (or Cloud S3 Standard-IA)       │
│   s3://wildfire-archive/                                         │
│   ├── weather/YYYY/quarter/Q1_weather.parquet                    │
│   ├── fires/YYYY/month/MM_fires.parquet                          │
│   ├── satellite/YYYY/month/tiles/ (sparse, key scenes only)      │
│   Compression: Delta Lake format with Z-ordering                 │
│   Access: 5-10 second query latency                              │
│   Size Estimate: 200-500GB                                       │
│                                                                  │
│ • Delta Lake / Iceberg (Optional for Advanced Analytics)         │
│   - ACID transactions on object storage                          │
│   - Time travel capabilities                                     │
│   - Incremental updates                                          │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│ ARCHIVE TIER (>365 days) - Compliance & Research                 │
├──────────────────────────────────────────────────────────────────┤
│ • Cloud Storage (AWS Glacier / Azure Archive)                    │
│   - Multi-year fire history                                      │
│   - Satellite imagery mosaics (annual composites)                │
│   - Model training datasets                                      │
│   Retrieval: 1-12 hours                                          │
│   Cost: $0.001/GB/month                                          │
│   Size Estimate: Unlimited (grows 100GB/year)                    │
└──────────────────────────────────────────────────────────────────┘
```

---

### 2.C. **Processing Layer - Stream + Batch**

```
┌─────────────────────────────────────────────────────────────────┐
│              STREAM PROCESSING (Real-Time)                       │
├─────────────────────────────────────────────────────────────────┤
│ • Kafka Streams / Apache Flink                                  │
│   ├── Fire Detection Enrichment                                 │
│   │   - Join weather data with fire detections                  │
│   │   - Calculate Fire Weather Index (FWI)                      │
│   │   - Geospatial clustering (nearby fires)                    │
│   ├── Anomaly Detection                                         │
│   │   - Sudden temperature spikes                               │
│   │   - Humidity drops                                          │
│   │   - Wind speed increases                                    │
│   ├── Real-Time Risk Scoring                                    │
│   │   - ML model inference (ensemble)                           │
│   │   - Alert generation (high-risk areas)                      │
│   Output: Processed events → PostgreSQL + Redis + UI WebSocket  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│              BATCH PROCESSING (Historical ETL)                   │
├─────────────────────────────────────────────────────────────────┤
│ • Apache Airflow (Orchestration) + Spark/Dask                   │
│   ├── Daily Jobs (12:00 AM PST)                                 │
│   │   - Move HOT → WARM tier (PostgreSQL → MinIO Parquet)       │
│   │   - Compress and partition data                             │
│   │   - Generate daily fire summary reports                     │
│   ├── Weekly Jobs (Sundays)                                     │
│   │   - Move WARM → COLD tier (MinIO → Cloud S3-IA)             │
│   │   - Delete old Sentinel tiles (keep only key scenes)        │
│   │   - Retrain ML models on updated data                       │
│   ├── Monthly Jobs                                              │
│   │   - Move COLD → ARCHIVE tier (S3-IA → Glacier)              │
│   │   - Create monthly data snapshots                           │
│   │   - Audit data quality metrics                              │
│   Output: Processed data in MinIO/Cloud, metadata in catalog    │
└─────────────────────────────────────────────────────────────────┘
```

**Airflow DAG Example:**
```python
# airflow/dags/daily_data_lifecycle.py
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

def move_hot_to_warm():
    """Move 7-day-old data from PostgreSQL to MinIO Parquet"""
    # Query PostgreSQL for data older than 7 days
    # Export to Parquet with date partitioning
    # Upload to MinIO: s3://wildfire-data/weather/YYYY/MM/DD/
    # Delete from PostgreSQL after verification
    pass

dag = DAG(
    'daily_data_lifecycle',
    schedule_interval='0 0 * * *',  # Daily at midnight
    start_date=datetime(2025, 1, 1),
    catchup=False
)

hot_to_warm = PythonOperator(
    task_id='move_hot_to_warm',
    python_callable=move_hot_to_warm,
    dag=dag
)
```

---

### 2.D. **Metadata & Indexing Layer**

```
┌─────────────────────────────────────────────────────────────────┐
│                    METADATA CATALOG                              │
├─────────────────────────────────────────────────────────────────┤
│ • PostgreSQL Metadata Tables                                    │
│   ├── data_catalog                                              │
│   │   - file_path, timestamp, data_source, size_bytes           │
│   │   - min_lat, max_lat, min_lon, max_lon (spatial bounds)     │
│   │   - record_count, quality_score                             │
│   ├── satellite_scenes                                          │
│   │   - scene_id, satellite, cloud_cover_percent                │
│   │   - ingestion_date, storage_tier (HOT/WARM/COLD/ARCHIVE)    │
│   ├── data_lineage                                              │
│   │   - source_id, transformation_job, output_id, timestamp     │
│   Output: Fast metadata queries without scanning object storage │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    QUERY OPTIMIZATION                            │
├─────────────────────────────────────────────────────────────────┤
│ • Spatial Indexing (PostGIS)                                    │
│   - Bounding box queries for fire/weather by region             │
│   - KNN searches (nearest weather station to fire)              │
│ • Time Indexing (TimescaleDB)                                   │
│   - Optimized for time-range queries                            │
│   - Continuous aggregates (pre-computed hourly/daily stats)     │
│ • Elasticsearch (Future)                                        │
│   - Full-text search on fire incident reports                   │
│   - Aggregations for analytics dashboards                       │
└─────────────────────────────────────────────────────────────────┘
```

---

### 2.E. **Automated Retention & Lifecycle Policies**

```yaml
# config/data_retention_policies.yaml
policies:
  fire_detections:
    hot_tier: 7 days
    warm_tier: 90 days
    cold_tier: 365 days
    archive_tier: 7 years  # CAL FIRE compliance
    deletion: never  # Keep forever for research

  weather_forecasts:
    hot_tier: 3 days
    warm_tier: 30 days
    cold_tier: 90 days
    archive_tier: 1 year
    deletion: after_archive  # Can delete old forecasts

  weather_observations:
    hot_tier: 7 days
    warm_tier: 90 days
    cold_tier: 365 days
    archive_tier: 10 years
    deletion: never

  satellite_imagery:
    sentinel2:
      hot_tier: 1 day  # Move immediately after processing
      warm_tier: 30 days  # Keep recent clear-sky scenes
      cold_tier: 90 days  # Keep only <10% cloud cover scenes
      archive_tier: key_scenes_only  # Fire events + clear composites
      deletion_criteria:
        cloud_cover: ">30%"
        age: ">90 days"
        not_tagged_as: "fire_event"

    landsat8:
      # Similar policy but 16-day revisit, so more selective
      warm_tier: 60 days
      cold_tier: 180 days
      archive_tier: annual_composites

  sensor_readings:
    hot_tier: 1 day
    warm_tier: 30 days
    cold_tier: 365 days
    archive_tier: aggregated_only  # Keep hourly averages, not raw
    deletion: after_aggregation

automation:
  airflow_dags:
    - daily_hot_to_warm_migration
    - weekly_warm_to_cold_migration
    - monthly_cold_to_archive_migration
    - quarterly_data_quality_audit

  alerts:
    - storage_usage_80_percent
    - retention_policy_failures
    - data_quality_degradation
```

---

## 3. Data Formats & Compression Strategy

### Recommended Formats by Data Type

| Data Type | Raw Format | Storage Format | Compression | Size Reduction |
|-----------|------------|----------------|-------------|----------------|
| Fire detections (points) | CSV/JSON | Parquet | Snappy | 80% |
| Weather grids (NetCDF) | NetCDF4 | Zarr/Parquet | Blosc/Snappy | 70% |
| Satellite imagery | GeoTIFF | Cloud-Optimized GeoTIFF (COG) | LZW/Deflate | 50-70% |
| Time series (sensors) | JSON | Parquet (columnar) | Snappy | 85% |
| Metadata | JSON | PostgreSQL JSONB | Built-in | 40% |

**Why Parquet?**
- Columnar storage → Only read columns you need
- Built-in compression → 70-90% size reduction
- Schema evolution → Add fields without breaking existing data
- Native support in Spark, Pandas, DuckDB

**Why Cloud-Optimized GeoTIFF (COG)?**
- HTTP range requests → Fetch only needed image tiles
- Internal tiling → Fast partial reads
- Overviews → Multi-resolution pyramids for fast rendering

---

## 4. Scalability & Cost Optimization

### 4.A. Storage Cost Projection (Per Month)

```
CURRENT (No Lifecycle Policies):
├── PostgreSQL (5GB)           $50  (SSD-backed RDS)
├── MinIO HOT (205GB)          $100 (Local NVMe)
├── Elasticsearch (5GB)        $25  (Managed service)
├── Redis (10GB)               $80  (In-memory)
└── TOTAL:                     $255/month

AFTER TIERED ARCHITECTURE:
├── PostgreSQL HOT (15GB)      $75  (7 days only)
├── Redis Cache (10GB)         $80  (1 hour TTL)
├── MinIO WARM (80GB Parquet)  $40  (7-90 days, compressed)
├── Cloud COLD (300GB S3-IA)   $40  (90-365 days, $0.0125/GB)
├── Cloud ARCHIVE (1TB Glacier) $10  (>1 year, $0.004/GB)
└── TOTAL:                     $245/month (1.2TB stored vs 225GB)

SCALABILITY (Peak Fire Season):
├── PostgreSQL HOT (30GB)      $150 (2x load)
├── Redis Cache (20GB)         $160 (2x cache)
├── MinIO WARM (150GB)         $75  (More recent data)
├── Cloud COLD (500GB)         $65  (Slower archival)
├── Cloud ARCHIVE (1.5TB)      $15  (Glacier grows slowly)
└── TOTAL:                     $465/month (2.2TB stored)

YEAR 3 PROJECTION (No Deletion, Just Archival):
├── PostgreSQL (15GB)          $75  (Fixed size with lifecycle)
├── Redis (10GB)               $80  (Fixed size, ephemeral)
├── MinIO WARM (100GB)         $50  (90-day rolling window)
├── Cloud COLD (1TB)           $130 (12 months of data)
├── Cloud ARCHIVE (10TB)       $100 (3 years of archives)
└── TOTAL:                     $435/month (11TB stored!)
```

**Key Insight:** With lifecycle policies, storage costs grow **sub-linearly** while data volume grows **linearly**.

---

### 4.B. Query Performance Optimization

```
BEFORE (All data in PostgreSQL):
├── Query last 7 days of fires:     50ms  ✅
├── Query last 30 days of fires:    2s    ⚠️
├── Query last year of fires:       30s   ❌
├── Join fires + weather (30 days): 10s   ❌

AFTER (Tiered + Indexed):
├── Query last 7 days (PostgreSQL):       30ms  ✅✅
├── Query last 30 days (MinIO Parquet):   500ms ✅
├── Query last year (DuckDB on Parquet):  2s    ✅
├── Join fires + weather (Spark on S3):   5s    ✅
```

**Optimization Techniques:**
1. **Partition Pruning**: Only scan relevant date partitions
2. **Columnar Reads**: Read only needed columns from Parquet
3. **Predicate Pushdown**: Filter at storage layer, not in memory
4. **Caching**: Redis for hot queries, CDN for static maps
5. **Pre-aggregation**: TimescaleDB continuous aggregates

---

## 5. Implementation Roadmap

### Phase 1: Foundation (Weeks 1-2) ✅ PARTIALLY COMPLETE
- [x] Kafka cluster setup
- [x] PostgreSQL with TimescaleDB
- [x] MinIO object storage
- [ ] Airflow orchestration
- [ ] Metadata catalog tables

### Phase 2: Lifecycle Automation (Weeks 3-4)
- [ ] Implement Airflow DAGs for daily migrations
- [ ] Create Parquet export scripts (PostgreSQL → MinIO)
- [ ] Add metadata tracking to data catalog
- [ ] Test hot→warm→cold transitions

### Phase 3: Cloud Integration (Weeks 5-6)
- [ ] Set up AWS S3 / Azure Blob for cold tier
- [ ] Configure Glacier/Archive for long-term storage
- [ ] Implement data replication policies
- [ ] Test failover and disaster recovery

### Phase 4: Optimization (Weeks 7-8)
- [ ] Tune Kafka retention and compression
- [ ] Optimize Parquet partitioning strategy
- [ ] Implement Delta Lake / Iceberg (optional)
- [ ] Set up monitoring dashboards (Grafana)

### Phase 5: Production Hardening (Weeks 9-10)
- [ ] Load testing (simulate fire season peak)
- [ ] Security audit (encryption, access controls)
- [ ] Documentation and runbooks
- [ ] Training for operations team

---

## 6. Technology Stack Recommendations

### On-Premises Stack (What You Have)
- ✅ **Kafka**: Event streaming
- ✅ **PostgreSQL + TimescaleDB**: Time-series DB
- ✅ **MinIO**: S3-compatible object storage
- ✅ **Redis**: Caching
- ✅ **Docker + Docker Compose**: Container orchestration

### Add for Production
- 🆕 **Apache Airflow**: Workflow orchestration (data lifecycle)
- 🆕 **DuckDB**: Fast analytics on Parquet (alternative to Spark for small-medium data)
- 🆕 **Delta Lake / Apache Iceberg**: ACID on object storage (optional, for advanced use cases)
- 🆕 **Prometheus + Grafana**: Already have this! Just add storage dashboards

### Cloud Services (For COLD/ARCHIVE Tiers)
- **AWS**: S3 Standard-IA (warm), S3 Glacier (cold), S3 Glacier Deep Archive (archive)
- **Azure**: Blob Cool Tier, Blob Archive Tier
- **GCP**: Cloud Storage Nearline, Coldline, Archive

---

## 7. Example Queries & Access Patterns

### Query 1: "Show all fires in the last 7 days"
```sql
-- Fast! Reads from PostgreSQL HOT tier
SELECT * FROM fire_detections
WHERE detection_time >= NOW() - INTERVAL '7 days'
AND confidence > 80;
```

### Query 2: "Show all fires in the last 3 months"
```python
# Reads from MinIO Parquet WARM tier
import duckdb
con = duckdb.connect()
result = con.execute("""
    SELECT * FROM read_parquet('s3://wildfire-data/fires/viirs/2025/*/*/*.parquet')
    WHERE detection_time >= current_date - INTERVAL '90 days'
    AND confidence > 80
""").fetchdf()
```

### Query 3: "Analyze fire trends from 2020-2024"
```python
# Reads from Cloud S3 COLD tier (slower but works!)
import pyarrow.parquet as pq
import s3fs
s3 = s3fs.S3FileSystem()
dataset = pq.ParquetDataset(
    's3://wildfire-archive/fires/',
    filesystem=s3,
    filters=[('year', '>=', 2020), ('year', '<=', 2024)]
)
df = dataset.read_pandas().to_pandas()
```

---

## 8. Monitoring & Alerting

### Key Metrics to Track
```yaml
Storage Metrics:
  - Total storage used (by tier)
  - Growth rate (GB/day)
  - Cost per GB (by tier)
  - Data age distribution

Performance Metrics:
  - Query latency (p50, p95, p99)
  - Throughput (queries/sec)
  - Cache hit rate (Redis)
  - Kafka consumer lag

Data Quality Metrics:
  - Ingestion success rate
  - Schema validation failures
  - Duplicate detection rate
  - Missing data gaps

Operational Metrics:
  - Airflow DAG success rate
  - Data migration job duration
  - Backup/restore test results
  - Storage tier transition errors
```

### Grafana Dashboard Panels
1. **Storage Capacity**: Current usage vs limits (by tier)
2. **Data Lifecycle**: Flow diagram showing data movement
3. **Cost Tracking**: Monthly spend by tier
4. **Query Performance**: Latency heatmap
5. **Kafka Health**: Consumer lag, partition distribution

---

## 9. Next Steps

1. **Review this architecture** with your team
2. **Set up Airflow** for orchestration (Docker Compose service)
3. **Implement first lifecycle DAG** (hot → warm migration)
4. **Create metadata catalog schema** in PostgreSQL
5. **Test with 30 days of historical data**
6. **Gradually expand** to cloud tiers

This architecture will prevent the storage issues we just fixed and provide a scalable, maintainable foundation for your wildfire intelligence platform! 🔥

---

## Appendix: Code Examples

See separate files:
- `services/data-lifecycle-manager/` (new service)
- `airflow/dags/` (DAG examples)
- `docs/operations/data-retention-runbook.md`
