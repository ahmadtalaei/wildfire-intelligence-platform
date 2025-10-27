-- =====================================================================
-- Metadata Catalog Schema for Wildfire Intelligence Platform
-- =====================================================================
-- Purpose: Track all data files across storage tiers (HOT/WARM/COLD/ARCHIVE)
-- Enables: Fast queries without scanning object storage, lifecycle management
-- Author: Wildfire Platform Team
-- Date: 2025-10-08
-- =====================================================================

-- Create metadata catalog table (ENHANCED with checksum, access tracking, partitioning)
CREATE TABLE IF NOT EXISTS data_catalog (
    id SERIAL PRIMARY KEY,
    source_table VARCHAR(200),  -- Original PostgreSQL table name
    partition_date DATE NOT NULL,  -- Date-based partition key
    file_path TEXT NOT NULL UNIQUE,
    data_source VARCHAR(100) NOT NULL,  -- e.g., 'firms_viirs', 'era5', 'sentinel2'
    record_count BIGINT DEFAULT 0,
    size_bytes BIGINT DEFAULT 0,

    -- Data integrity
    checksum VARCHAR(64),  -- SHA256 checksum for data validation
    compression_type VARCHAR(20) DEFAULT 'snappy',  -- snappy, gzip, lz4, etc.
    file_format VARCHAR(20) DEFAULT 'parquet',  -- parquet, csv, json, etc.

    -- Temporal bounds
    min_timestamp TIMESTAMP WITH TIME ZONE,
    max_timestamp TIMESTAMP WITH TIME ZONE,

    -- Spatial bounds (for geospatial data)
    min_latitude DOUBLE PRECISION,
    max_latitude DOUBLE PRECISION,
    min_longitude DOUBLE PRECISION,
    max_longitude DOUBLE PRECISION,

    -- Storage tier management
    storage_tier VARCHAR(20) NOT NULL CHECK (storage_tier IN ('HOT', 'WARM', 'COLD', 'ARCHIVE', 'DELETED')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ingested_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),  -- When data first entered system
    last_accessed_at TIMESTAMP WITH TIME ZONE,  -- Track access patterns for cold storage decisions
    access_count INTEGER DEFAULT 0,  -- How many times file has been queried

    -- Migration timestamps
    migrated_to_warm_at TIMESTAMP WITH TIME ZONE,
    migrated_to_cold_at TIMESTAMP WITH TIME ZONE,
    migrated_to_archive_at TIMESTAMP WITH TIME ZONE,
    deleted_at TIMESTAMP WITH TIME ZONE,
    deletion_reason TEXT,

    -- Data quality metrics
    quality_score DOUBLE PRECISION DEFAULT 1.0,
    completeness_score DOUBLE PRECISION,
    accuracy_score DOUBLE PRECISION,
    timeliness_score DOUBLE PRECISION,
    validation_errors JSONB,

    -- Deduplication tracking
    is_duplicate BOOLEAN DEFAULT FALSE,
    duplicate_of_id INTEGER REFERENCES data_catalog(id),

    -- Flexible metadata storage
    metadata JSONB,

    -- Constraints
    CONSTRAINT valid_quality_score CHECK (quality_score BETWEEN 0 AND 1),
    CONSTRAINT valid_partition_date CHECK (partition_date IS NOT NULL)
);

-- Create indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_data_catalog_source ON data_catalog(data_source);
CREATE INDEX IF NOT EXISTS idx_data_catalog_tier ON data_catalog(storage_tier);
CREATE INDEX IF NOT EXISTS idx_data_catalog_created_at ON data_catalog(created_at);
CREATE INDEX IF NOT EXISTS idx_data_catalog_partition_date ON data_catalog(partition_date DESC);
CREATE INDEX IF NOT EXISTS idx_data_catalog_timestamp_range ON data_catalog(min_timestamp, max_timestamp);
CREATE INDEX IF NOT EXISTS idx_data_catalog_spatial ON data_catalog(min_latitude, max_latitude, min_longitude, max_longitude);
CREATE INDEX IF NOT EXISTS idx_data_catalog_metadata ON data_catalog USING GIN (metadata);
CREATE INDEX IF NOT EXISTS idx_data_catalog_checksum ON data_catalog(checksum) WHERE checksum IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_data_catalog_last_accessed ON data_catalog(last_accessed_at) WHERE last_accessed_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_data_catalog_duplicates ON data_catalog(is_duplicate, duplicate_of_id) WHERE is_duplicate = TRUE;

-- Create composite index for lifecycle queries
CREATE INDEX IF NOT EXISTS idx_data_catalog_lifecycle
ON data_catalog(storage_tier, created_at, data_source);

-- Composite index for partition-based queries
CREATE INDEX IF NOT EXISTS idx_data_catalog_partition_lifecycle
ON data_catalog(partition_date, storage_tier, data_source);

-- Comment the table
COMMENT ON TABLE data_catalog IS 'Metadata catalog tracking all data files across storage tiers';

-- =====================================================================
-- Storage Metrics Table (for Grafana dashboards)
-- =====================================================================

CREATE TABLE IF NOT EXISTS storage_metrics (
    id SERIAL PRIMARY KEY,
    tier VARCHAR(20) NOT NULL,
    file_count INTEGER NOT NULL,
    size_gb DOUBLE PRECISION NOT NULL,
    record_count BIGINT NOT NULL,
    measured_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_storage_metrics_time ON storage_metrics(measured_at DESC);
CREATE INDEX IF NOT EXISTS idx_storage_metrics_tier ON storage_metrics(tier, measured_at DESC);

COMMENT ON TABLE storage_metrics IS 'Time-series storage metrics for monitoring dashboards';

-- =====================================================================
-- Data Lineage Table (tracks data transformations)
-- =====================================================================

CREATE TABLE IF NOT EXISTS data_lineage (
    id SERIAL PRIMARY KEY,
    source_catalog_id INTEGER REFERENCES data_catalog(id),
    transformation_job VARCHAR(200) NOT NULL,  -- e.g., 'daily_hot_to_warm_migration'
    transformation_type VARCHAR(50) NOT NULL,  -- 'MIGRATION', 'AGGREGATION', 'TRANSFORMATION'
    output_catalog_id INTEGER REFERENCES data_catalog(id),
    job_start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    job_end_time TIMESTAMP WITH TIME ZONE,
    job_status VARCHAR(20) CHECK (job_status IN ('PENDING', 'RUNNING', 'SUCCESS', 'FAILED')),
    error_message TEXT,
    metadata JSONB
);

CREATE INDEX IF NOT EXISTS idx_data_lineage_source ON data_lineage(source_catalog_id);
CREATE INDEX IF NOT EXISTS idx_data_lineage_output ON data_lineage(output_catalog_id);
CREATE INDEX IF NOT EXISTS idx_data_lineage_job ON data_lineage(transformation_job, job_start_time DESC);

COMMENT ON TABLE data_lineage IS 'Data lineage tracking for auditing and impact analysis';

-- =====================================================================
-- Satellite Scenes Table (specialized metadata for satellite imagery)
-- =====================================================================

CREATE TABLE IF NOT EXISTS satellite_scenes (
    id SERIAL PRIMARY KEY,
    catalog_id INTEGER REFERENCES data_catalog(id) UNIQUE,
    scene_id VARCHAR(200) NOT NULL UNIQUE,
    satellite_name VARCHAR(100) NOT NULL,  -- 'Sentinel-2', 'Landsat-8', etc.
    sensor_type VARCHAR(50),  -- 'MSI', 'OLI', 'SLSTR'
    acquisition_date TIMESTAMP WITH TIME ZONE NOT NULL,

    -- Scene properties
    cloud_cover_percent DOUBLE PRECISION CHECK (cloud_cover_percent BETWEEN 0 AND 100),
    sun_azimuth DOUBLE PRECISION,
    sun_elevation DOUBLE PRECISION,

    -- Processing level
    processing_level VARCHAR(50),  -- 'L1C', 'L2A', etc.

    -- Quality flags
    has_fire_detection BOOLEAN DEFAULT FALSE,
    has_smoke_detection BOOLEAN DEFAULT FALSE,
    has_burn_scar BOOLEAN DEFAULT FALSE,

    -- Tags for retention decisions
    tags TEXT[],
    keep_indefinitely BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_satellite_scenes_satellite ON satellite_scenes(satellite_name, acquisition_date DESC);
CREATE INDEX IF NOT EXISTS idx_satellite_scenes_cloud ON satellite_scenes(cloud_cover_percent);
CREATE INDEX IF NOT EXISTS idx_satellite_scenes_fire ON satellite_scenes(has_fire_detection) WHERE has_fire_detection = TRUE;
CREATE INDEX IF NOT EXISTS idx_satellite_scenes_tags ON satellite_scenes USING GIN (tags);

COMMENT ON TABLE satellite_scenes IS 'Specialized metadata for satellite imagery with retention policy attributes';

-- =====================================================================
-- Retention Policy Audit Log
-- =====================================================================

CREATE TABLE IF NOT EXISTS retention_audit_log (
    id SERIAL PRIMARY KEY,
    catalog_id INTEGER REFERENCES data_catalog(id),
    action VARCHAR(50) NOT NULL,  -- 'MIGRATED', 'DELETED', 'RETAINED'
    from_tier VARCHAR(20),
    to_tier VARCHAR(20),
    policy_rule VARCHAR(200),  -- e.g., 'Delete Sentinel >30% cloud after 90 days'
    executed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    executed_by VARCHAR(100),  -- DAG name or user
    file_path TEXT,
    size_bytes BIGINT,
    reason TEXT
);

CREATE INDEX IF NOT EXISTS idx_retention_audit_action ON retention_audit_log(action, executed_at DESC);
CREATE INDEX IF NOT EXISTS idx_retention_audit_catalog ON retention_audit_log(catalog_id);

COMMENT ON TABLE retention_audit_log IS 'Audit trail for all retention policy actions';

-- =====================================================================
-- Helper Views
-- =====================================================================

-- View: Storage tier distribution
CREATE OR REPLACE VIEW v_storage_distribution AS
SELECT
    storage_tier,
    COUNT(*) as file_count,
    SUM(size_bytes) / 1024.0 / 1024.0 / 1024.0 as total_gb,
    SUM(record_count) as total_records,
    AVG(quality_score) as avg_quality_score
FROM data_catalog
WHERE storage_tier != 'DELETED'
GROUP BY storage_tier
ORDER BY
    CASE storage_tier
        WHEN 'HOT' THEN 1
        WHEN 'WARM' THEN 2
        WHEN 'COLD' THEN 3
        WHEN 'ARCHIVE' THEN 4
    END;

-- View: Files needing migration
CREATE OR REPLACE VIEW v_files_for_migration AS
SELECT
    id,
    file_path,
    data_source,
    storage_tier,
    size_bytes / 1024.0 / 1024.0 as size_mb,
    created_at,
    EXTRACT(DAY FROM NOW() - created_at) as age_days
FROM data_catalog
WHERE
    (storage_tier = 'HOT' AND created_at < NOW() - INTERVAL '7 days')
    OR (storage_tier = 'WARM' AND created_at < NOW() - INTERVAL '90 days')
    OR (storage_tier = 'COLD' AND created_at < NOW() - INTERVAL '365 days')
ORDER BY created_at;

-- View: Sentinel scenes eligible for deletion
CREATE OR REPLACE VIEW v_sentinel_cleanup_candidates AS
SELECT
    dc.id,
    dc.file_path,
    dc.size_bytes / 1024.0 / 1024.0 / 1024.0 as size_gb,
    dc.created_at,
    EXTRACT(DAY FROM NOW() - dc.created_at) as age_days,
    ss.cloud_cover_percent,
    ss.has_fire_detection,
    ss.tags
FROM data_catalog dc
JOIN satellite_scenes ss ON dc.id = ss.catalog_id
WHERE
    dc.data_source LIKE 'sentinel%'
    AND dc.storage_tier = 'WARM'
    AND dc.created_at < NOW() - INTERVAL '90 days'
    AND ss.cloud_cover_percent > 30
    AND ss.has_fire_detection = FALSE
    AND NOT ss.keep_indefinitely
ORDER BY dc.created_at;

-- =====================================================================
-- Helper Functions
-- =====================================================================

-- Function: Calculate storage cost estimate
CREATE OR REPLACE FUNCTION calculate_storage_cost()
RETURNS TABLE(tier VARCHAR, cost_usd NUMERIC) AS $$
BEGIN
    RETURN QUERY
    SELECT
        storage_tier,
        CASE storage_tier
            WHEN 'HOT' THEN SUM(size_bytes) / 1024.0 / 1024.0 / 1024.0 * 0.50
            WHEN 'WARM' THEN SUM(size_bytes) / 1024.0 / 1024.0 / 1024.0 * 0.125
            WHEN 'COLD' THEN SUM(size_bytes) / 1024.0 / 1024.0 / 1024.0 * 0.004
            WHEN 'ARCHIVE' THEN SUM(size_bytes) / 1024.0 / 1024.0 / 1024.0 * 0.001
            ELSE 0
        END as monthly_cost_usd
    FROM data_catalog
    WHERE storage_tier != 'DELETED'
    GROUP BY storage_tier;
END;
$$ LANGUAGE plpgsql;

-- Function: Get data catalog summary
CREATE OR REPLACE FUNCTION get_catalog_summary()
RETURNS TABLE(
    total_files BIGINT,
    total_gb NUMERIC,
    total_records BIGINT,
    avg_quality NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*)::BIGINT,
        (SUM(size_bytes) / 1024.0 / 1024.0 / 1024.0)::NUMERIC,
        SUM(record_count)::BIGINT,
        AVG(quality_score)::NUMERIC
    FROM data_catalog
    WHERE storage_tier != 'DELETED';
END;
$$ LANGUAGE plpgsql;

-- =====================================================================
-- Initial Data Setup (Create Airflow DB)
-- =====================================================================

CREATE DATABASE IF NOT EXISTS airflow_db;
GRANT ALL PRIVILEGES ON DATABASE airflow_db TO wildfire_user;

-- =====================================================================
-- Success Message
-- =====================================================================

DO $$
BEGIN
    RAISE NOTICE '✅ Metadata catalog schema created successfully!';
    RAISE NOTICE '📊 Tables: data_catalog, storage_metrics, data_lineage, satellite_scenes, retention_audit_log';
    RAISE NOTICE '📈 Views: v_storage_distribution, v_files_for_migration, v_sentinel_cleanup_candidates';
    RAISE NOTICE '⚡ Functions: calculate_storage_cost(), get_catalog_summary()';
END $$;
