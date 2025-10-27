-- =====================================================================
-- Dead Letter Queue Tables & PostGIS Spatial Indexing Extensions
-- =====================================================================
-- Purpose: Add DLQ tracking and spatial indexing capabilities
-- Date: 2025-10-08
-- =====================================================================

-- Enable PostGIS extension for spatial indexing
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

-- =====================================================================
-- Failed Messages Table (Dead Letter Queue)
-- =====================================================================

CREATE TABLE IF NOT EXISTS failed_messages (
    id SERIAL PRIMARY KEY,
    message_id VARCHAR(100) UNIQUE NOT NULL,
    source_topic VARCHAR(200) NOT NULL,
    failure_reason VARCHAR(100) NOT NULL,
    error_details TEXT,
    retry_count INTEGER DEFAULT 0,
    status VARCHAR(50) NOT NULL CHECK (status IN ('queued_for_retry', 'permanent_failure', 'retry_success', 'replayed')),
    original_message JSONB NOT NULL,
    retry_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    retry_success_at TIMESTAMP WITH TIME ZONE
);

-- Indexes for DLQ queries
CREATE INDEX IF NOT EXISTS idx_failed_messages_status ON failed_messages(status);
CREATE INDEX IF NOT EXISTS idx_failed_messages_retry_at ON failed_messages(retry_at) WHERE status = 'queued_for_retry';
CREATE INDEX IF NOT EXISTS idx_failed_messages_created_at ON failed_messages(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_failed_messages_failure_reason ON failed_messages(failure_reason);
CREATE INDEX IF NOT EXISTS idx_failed_messages_source_topic ON failed_messages(source_topic);

COMMENT ON TABLE failed_messages IS 'Dead Letter Queue for failed ingestion messages with retry tracking';

-- =====================================================================
-- Add Spatial Columns to Existing Tables
-- =====================================================================

-- Add geometry column to data_catalog for spatial indexing
ALTER TABLE data_catalog ADD COLUMN IF NOT EXISTS geom geometry(POLYGON, 4326);

-- Create spatial index on geometry column
CREATE INDEX IF NOT EXISTS idx_data_catalog_geom ON data_catalog USING GIST (geom);

-- Function to update geometry from bounding box
CREATE OR REPLACE FUNCTION update_data_catalog_geometry()
RETURNS TRIGGER AS $$
BEGIN
    -- Create polygon from bounding box coordinates
    IF NEW.min_latitude IS NOT NULL AND NEW.max_latitude IS NOT NULL
       AND NEW.min_longitude IS NOT NULL AND NEW.max_longitude IS NOT NULL THEN

        NEW.geom := ST_MakeEnvelope(
            NEW.min_longitude,
            NEW.min_latitude,
            NEW.max_longitude,
            NEW.max_latitude,
            4326  -- WGS84 SRID
        );
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to automatically update geometry on insert/update
DROP TRIGGER IF EXISTS trg_update_data_catalog_geometry ON data_catalog;
CREATE TRIGGER trg_update_data_catalog_geometry
    BEFORE INSERT OR UPDATE ON data_catalog
    FOR EACH ROW
    EXECUTE FUNCTION update_data_catalog_geometry();

-- =====================================================================
-- Spatial Query Helper Functions
-- =====================================================================

-- Function: Find files intersecting with bounding box
CREATE OR REPLACE FUNCTION find_files_in_bbox(
    min_lon DOUBLE PRECISION,
    min_lat DOUBLE PRECISION,
    max_lon DOUBLE PRECISION,
    max_lat DOUBLE PRECISION
)
RETURNS TABLE(
    file_id INTEGER,
    file_path TEXT,
    data_source VARCHAR,
    storage_tier VARCHAR,
    size_mb DOUBLE PRECISION,
    record_count BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        dc.id,
        dc.file_path,
        dc.data_source,
        dc.storage_tier,
        dc.size_bytes / 1024.0 / 1024.0 as size_mb,
        dc.record_count
    FROM data_catalog dc
    WHERE dc.geom IS NOT NULL
      AND ST_Intersects(
          dc.geom,
          ST_MakeEnvelope(min_lon, min_lat, max_lon, max_lat, 4326)
      )
    ORDER BY dc.created_at DESC;
END;
$$ LANGUAGE plpgsql;

-- Function: Find files within radius of point (in kilometers)
CREATE OR REPLACE FUNCTION find_files_near_point(
    center_lon DOUBLE PRECISION,
    center_lat DOUBLE PRECISION,
    radius_km DOUBLE PRECISION
)
RETURNS TABLE(
    file_id INTEGER,
    file_path TEXT,
    data_source VARCHAR,
    distance_km DOUBLE PRECISION
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        dc.id,
        dc.file_path,
        dc.data_source,
        ST_Distance(
            dc.geom::geography,
            ST_SetSRID(ST_MakePoint(center_lon, center_lat), 4326)::geography
        ) / 1000.0 as distance_km
    FROM data_catalog dc
    WHERE dc.geom IS NOT NULL
      AND ST_DWithin(
          dc.geom::geography,
          ST_SetSRID(ST_MakePoint(center_lon, center_lat), 4326)::geography,
          radius_km * 1000  -- Convert km to meters
      )
    ORDER BY distance_km;
END;
$$ LANGUAGE plpgsql;

-- Function: Get spatial coverage statistics by data source
CREATE OR REPLACE FUNCTION get_spatial_coverage_stats()
RETURNS TABLE(
    data_source VARCHAR,
    file_count BIGINT,
    total_area_sq_km DOUBLE PRECISION,
    avg_area_sq_km DOUBLE PRECISION,
    bbox_json TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        dc.data_source,
        COUNT(*)::BIGINT as file_count,
        SUM(ST_Area(dc.geom::geography) / 1000000.0) as total_area_sq_km,
        AVG(ST_Area(dc.geom::geography) / 1000000.0) as avg_area_sq_km,
        ST_AsGeoJSON(ST_Extent(dc.geom))::TEXT as bbox_json
    FROM data_catalog dc
    WHERE dc.geom IS NOT NULL
      AND dc.storage_tier != 'DELETED'
    GROUP BY dc.data_source
    ORDER BY file_count DESC;
END;
$$ LANGUAGE plpgsql;

-- =====================================================================
-- Backpressure Monitoring Table
-- =====================================================================

CREATE TABLE IF NOT EXISTS ingestion_backpressure_metrics (
    id SERIAL PRIMARY KEY,
    source_id VARCHAR(100) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    queue_depth INTEGER NOT NULL,
    processing_rate_per_sec DOUBLE PRECISION,
    rejection_count INTEGER DEFAULT 0,
    avg_latency_ms DOUBLE PRECISION,
    backpressure_active BOOLEAN DEFAULT FALSE,
    throttle_percentage INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_backpressure_timestamp ON ingestion_backpressure_metrics(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_backpressure_source ON ingestion_backpressure_metrics(source_id, timestamp DESC);

COMMENT ON TABLE ingestion_backpressure_metrics IS 'Tracks backpressure metrics during high ingestion periods';

-- =====================================================================
-- Image Deduplication Hash Table
-- =====================================================================

CREATE TABLE IF NOT EXISTS image_hashes (
    id SERIAL PRIMARY KEY,
    catalog_id INTEGER REFERENCES data_catalog(id),
    image_hash VARCHAR(64) UNIQUE NOT NULL,  -- SHA256 hash
    perceptual_hash VARCHAR(32),  -- pHash for near-duplicate detection
    file_size_bytes BIGINT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    duplicate_of_id INTEGER REFERENCES image_hashes(id)
);

CREATE INDEX IF NOT EXISTS idx_image_hashes_hash ON image_hashes(image_hash);
CREATE INDEX IF NOT EXISTS idx_image_hashes_perceptual ON image_hashes(perceptual_hash);
CREATE INDEX IF NOT EXISTS idx_image_hashes_catalog ON image_hashes(catalog_id);

COMMENT ON TABLE image_hashes IS 'Stores image hashes for duplicate detection';

-- =====================================================================
-- API Rate Limiting Table
-- =====================================================================

CREATE TABLE IF NOT EXISTS api_rate_limits (
    id SERIAL PRIMARY KEY,
    api_key VARCHAR(100),
    ip_address INET,
    endpoint VARCHAR(200) NOT NULL,
    request_count INTEGER DEFAULT 1,
    window_start TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    window_end TIMESTAMP WITH TIME ZONE DEFAULT NOW() + INTERVAL '1 minute',
    blocked_until TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_rate_limits_api_key ON api_rate_limits(api_key, endpoint, window_start DESC);
CREATE INDEX IF NOT EXISTS idx_rate_limits_ip ON api_rate_limits(ip_address, endpoint, window_start DESC);

COMMENT ON TABLE api_rate_limits IS 'Tracks API request rates for rate limiting';

-- Function: Check rate limit
CREATE OR REPLACE FUNCTION check_rate_limit(
    p_api_key VARCHAR,
    p_ip_address INET,
    p_endpoint VARCHAR,
    p_max_requests INTEGER DEFAULT 100,
    p_window_minutes INTEGER DEFAULT 1
)
RETURNS TABLE(
    allowed BOOLEAN,
    current_count INTEGER,
    limit_count INTEGER,
    reset_at TIMESTAMP WITH TIME ZONE
) AS $$
DECLARE
    v_count INTEGER;
    v_window_start TIMESTAMP WITH TIME ZONE;
    v_window_end TIMESTAMP WITH TIME ZONE;
BEGIN
    v_window_start := NOW() - (p_window_minutes || ' minutes')::INTERVAL;
    v_window_end := NOW();

    -- Get current count for this key/IP and endpoint
    SELECT COUNT(*)
    INTO v_count
    FROM api_rate_limits
    WHERE (api_key = p_api_key OR ip_address = p_ip_address)
      AND endpoint = p_endpoint
      AND window_start >= v_window_start;

    -- Insert new request record
    INSERT INTO api_rate_limits (api_key, ip_address, endpoint, window_start, window_end)
    VALUES (p_api_key, p_ip_address, p_endpoint, v_window_start, v_window_end);

    -- Return result
    RETURN QUERY SELECT
        (v_count < p_max_requests) as allowed,
        v_count as current_count,
        p_max_requests as limit_count,
        v_window_end as reset_at;
END;
$$ LANGUAGE plpgsql;

-- =====================================================================
-- Views for DLQ Monitoring
-- =====================================================================

-- View: DLQ Statistics
CREATE OR REPLACE VIEW v_dlq_statistics AS
SELECT
    DATE_TRUNC('hour', created_at) as hour,
    failure_reason,
    status,
    COUNT(*) as message_count,
    AVG(retry_count) as avg_retry_count
FROM failed_messages
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY DATE_TRUNC('hour', created_at), failure_reason, status
ORDER BY hour DESC, message_count DESC;

-- View: Active Retry Queue
CREATE OR REPLACE VIEW v_active_retry_queue AS
SELECT
    message_id,
    source_topic,
    failure_reason,
    retry_count,
    retry_at,
    created_at,
    EXTRACT(EPOCH FROM (retry_at - NOW())) as seconds_until_retry
FROM failed_messages
WHERE status = 'queued_for_retry'
  AND retry_at > NOW()
ORDER BY retry_at;

-- =====================================================================
-- Cleanup Jobs
-- =====================================================================

-- Function: Cleanup old DLQ messages
CREATE OR REPLACE FUNCTION cleanup_old_dlq_messages(retention_days INTEGER DEFAULT 30)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM failed_messages
    WHERE created_at < NOW() - (retention_days || ' days')::INTERVAL
      AND status IN ('retry_success', 'replayed');

    GET DIAGNOSTICS deleted_count = ROW_COUNT;

    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Function: Cleanup old rate limit records
CREATE OR REPLACE FUNCTION cleanup_old_rate_limits(retention_hours INTEGER DEFAULT 24)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM api_rate_limits
    WHERE window_end < NOW() - (retention_hours || ' hours')::INTERVAL;

    GET DIAGNOSTICS deleted_count = ROW_COUNT;

    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- =====================================================================
-- Success Message
-- =====================================================================

DO $$
BEGIN
    RAISE NOTICE '✅ DLQ and Spatial Extensions created successfully!';
    RAISE NOTICE '📦 Tables: failed_messages, image_hashes, api_rate_limits, ingestion_backpressure_metrics';
    RAISE NOTICE '🗺️  PostGIS enabled with spatial indexing on data_catalog';
    RAISE NOTICE '🔍 Spatial functions: find_files_in_bbox(), find_files_near_point(), get_spatial_coverage_stats()';
    RAISE NOTICE '🚫 Rate limiting function: check_rate_limit()';
    RAISE NOTICE '🧹 Cleanup functions: cleanup_old_dlq_messages(), cleanup_old_rate_limits()';
END $$;
