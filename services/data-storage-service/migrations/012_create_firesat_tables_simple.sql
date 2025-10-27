-- FireSat Data Tables (Simplified for Standard PostgreSQL)
-- Schema for storing ultra-high resolution FireSat satellite fire detection data

-- =====================================================
-- FireSat Fire Detections Table
-- Stores individual fire detections from FireSat constellation
-- =====================================================

CREATE TABLE IF NOT EXISTS firesat_detections (
    id BIGSERIAL PRIMARY KEY,

    -- Temporal
    timestamp TIMESTAMPTZ NOT NULL,
    processing_timestamp TIMESTAMPTZ,

    -- Geospatial
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,

    -- Fire Characteristics
    brightness_kelvin DOUBLE PRECISION,
    fire_radiative_power DOUBLE PRECISION,  -- MW
    fire_area_m2 DOUBLE PRECISION,
    fire_perimeter_m DOUBLE PRECISION,

    -- AI Detection Metadata
    confidence DOUBLE PRECISION CHECK (confidence >= 0 AND confidence <= 1),
    ai_model_version VARCHAR(50),
    detection_algorithm VARCHAR(100),

    -- Satellite Metadata
    satellite_id VARCHAR(50),
    sensor VARCHAR(50),
    scan_angle DOUBLE PRECISION,
    spatial_resolution_m DOUBLE PRECISION DEFAULT 5.0,
    satellite_pass_id VARCHAR(100),

    -- Source Tracking
    source VARCHAR(50) DEFAULT 'FireSat',
    source_id VARCHAR(100) DEFAULT 'firesat_detections',
    provider VARCHAR(100) DEFAULT 'Earth Fire Alliance',

    -- Quality Metrics
    data_quality DOUBLE PRECISION CHECK (data_quality >= 0 AND data_quality <= 1),
    anomaly_flags TEXT[],

    -- Identifiers
    detection_id VARCHAR(100) UNIQUE,

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_firesat_detections_timestamp
    ON firesat_detections (timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_firesat_detections_location
    ON firesat_detections (latitude, longitude);

CREATE INDEX IF NOT EXISTS idx_firesat_detections_satellite
    ON firesat_detections (satellite_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_firesat_detections_confidence
    ON firesat_detections (confidence)
    WHERE confidence >= 0.8;

CREATE INDEX IF NOT EXISTS idx_firesat_detections_frp
    ON firesat_detections (fire_radiative_power)
    WHERE fire_radiative_power > 100;

CREATE INDEX IF NOT EXISTS idx_firesat_detections_detection_id
    ON firesat_detections (detection_id);

-- Composite index for California queries
CREATE INDEX IF NOT EXISTS idx_firesat_detections_ca_recent
    ON firesat_detections (timestamp DESC, latitude, longitude)
    WHERE latitude >= 32.5 AND latitude <= 42.0
      AND longitude >= -124.5 AND longitude <= -114.1;


-- =====================================================
-- FireSat Fire Perimeters Table
-- Stores AI-generated fire perimeter polygons
-- =====================================================

CREATE TABLE IF NOT EXISTS firesat_perimeters (
    id BIGSERIAL PRIMARY KEY,

    -- Temporal
    timestamp TIMESTAMPTZ NOT NULL,

    -- Fire Identification
    fire_id VARCHAR(100) NOT NULL,

    -- Geospatial (as JSON for now, can upgrade to PostGIS later)
    perimeter_geometry_geojson TEXT,  -- Store as GeoJSON string
    centroid_lat DOUBLE PRECISION,
    centroid_lon DOUBLE PRECISION,

    -- Fire Metrics
    area_hectares DOUBLE PRECISION,
    perimeter_km DOUBLE PRECISION,

    -- Quality
    confidence DOUBLE PRECISION CHECK (confidence >= 0 AND confidence <= 1),

    -- Source Tracking
    source VARCHAR(50) DEFAULT 'FireSat',
    source_id VARCHAR(100) DEFAULT 'firesat_perimeters',
    provider VARCHAR(100) DEFAULT 'Earth Fire Alliance',
    data_quality DOUBLE PRECISION,

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_firesat_perimeters_timestamp
    ON firesat_perimeters (timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_firesat_perimeters_fire_id
    ON firesat_perimeters (fire_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_firesat_perimeters_centroid
    ON firesat_perimeters (centroid_lat, centroid_lon);


-- =====================================================
-- FireSat Thermal Imagery Metadata Table
-- Stores metadata for thermal imagery scenes (actual data in S3)
-- =====================================================

CREATE TABLE IF NOT EXISTS firesat_thermal_scenes (
    id BIGSERIAL PRIMARY KEY,

    -- Temporal
    acquisition_time TIMESTAMPTZ NOT NULL,
    processing_time TIMESTAMPTZ,

    -- Scene Metadata
    scene_id VARCHAR(100) UNIQUE NOT NULL,
    satellite_id VARCHAR(50),

    -- Geospatial Coverage (as JSON)
    scene_bounds_geojson TEXT,  -- Store as GeoJSON polygon
    center_lat DOUBLE PRECISION,
    center_lon DOUBLE PRECISION,

    -- Storage
    s3_bucket VARCHAR(100),
    s3_key VARCHAR(500),
    file_size_bytes BIGINT,
    format VARCHAR(50),  -- geotiff, netcdf, etc.

    -- Quality
    cloud_cover_percent DOUBLE PRECISION,
    data_quality DOUBLE PRECISION,

    -- Source
    source VARCHAR(50) DEFAULT 'FireSat',
    source_id VARCHAR(100) DEFAULT 'firesat_thermal',
    provider VARCHAR(100) DEFAULT 'Earth Fire Alliance',

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_firesat_thermal_acquisition
    ON firesat_thermal_scenes (acquisition_time DESC);

CREATE INDEX IF NOT EXISTS idx_firesat_thermal_scene_id
    ON firesat_thermal_scenes (scene_id);

CREATE INDEX IF NOT EXISTS idx_firesat_thermal_center
    ON firesat_thermal_scenes (center_lat, center_lon);


-- =====================================================
-- FireSat Ingestion Metrics Table
-- Track ingestion performance and data quality
-- =====================================================

CREATE TABLE IF NOT EXISTS firesat_ingestion_metrics (
    id BIGSERIAL PRIMARY KEY,

    -- Temporal
    ingestion_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    data_start_time TIMESTAMPTZ,
    data_end_time TIMESTAMPTZ,

    -- Metrics
    source_id VARCHAR(100),
    records_ingested INTEGER,
    records_failed INTEGER,
    avg_confidence DOUBLE PRECISION,
    avg_data_quality DOUBLE PRECISION,
    processing_duration_seconds DOUBLE PRECISION,

    -- Status
    status VARCHAR(50),  -- success, partial_failure, failure
    error_message TEXT,

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_firesat_metrics_time
    ON firesat_ingestion_metrics (ingestion_time DESC);

CREATE INDEX IF NOT EXISTS idx_firesat_metrics_source
    ON firesat_ingestion_metrics (source_id, ingestion_time DESC);


-- =====================================================
-- Helper Functions
-- =====================================================

-- Function to get recent high-confidence detections in California
CREATE OR REPLACE FUNCTION get_recent_firesat_detections_ca(
    hours_back INTEGER DEFAULT 24,
    min_confidence DOUBLE PRECISION DEFAULT 0.8
)
RETURNS TABLE (
    timestamp TIMESTAMPTZ,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    fire_radiative_power DOUBLE PRECISION,
    confidence DOUBLE PRECISION,
    satellite_id VARCHAR
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        d.timestamp,
        d.latitude,
        d.longitude,
        d.fire_radiative_power,
        d.confidence,
        d.satellite_id
    FROM firesat_detections d
    WHERE d.timestamp >= NOW() - (hours_back || ' hours')::INTERVAL
      AND d.confidence >= min_confidence
      AND d.latitude >= 32.5 AND d.latitude <= 42.0
      AND d.longitude >= -124.5 AND d.longitude <= -114.1
    ORDER BY d.timestamp DESC;
END;
$$ LANGUAGE plpgsql;


-- Function to calculate detection density in grid cells
CREATE OR REPLACE FUNCTION firesat_detection_heatmap(
    start_time TIMESTAMPTZ,
    end_time TIMESTAMPTZ,
    grid_size_degrees DOUBLE PRECISION DEFAULT 0.1
)
RETURNS TABLE (
    lat_bucket DOUBLE PRECISION,
    lon_bucket DOUBLE PRECISION,
    detection_count BIGINT,
    avg_frp DOUBLE PRECISION
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        FLOOR(latitude / grid_size_degrees) * grid_size_degrees AS lat_bucket,
        FLOOR(longitude / grid_size_degrees) * grid_size_degrees AS lon_bucket,
        COUNT(*) AS detection_count,
        AVG(fire_radiative_power) AS avg_frp
    FROM firesat_detections
    WHERE timestamp >= start_time AND timestamp <= end_time
    GROUP BY lat_bucket, lon_bucket
    ORDER BY detection_count DESC;
END;
$$ LANGUAGE plpgsql;


-- =====================================================
-- Comments
-- =====================================================

COMMENT ON TABLE firesat_detections IS
'FireSat satellite fire detections - ultra-high resolution (5m) AI-powered fire detection data';

COMMENT ON TABLE firesat_perimeters IS
'FireSat fire perimeter polygons - AI-generated fire boundaries';

COMMENT ON TABLE firesat_thermal_scenes IS
'FireSat thermal imagery metadata - references to thermal IR scenes in S3';

COMMENT ON TABLE firesat_ingestion_metrics IS
'FireSat data ingestion tracking and quality metrics';

COMMENT ON COLUMN firesat_detections.spatial_resolution_m IS
'FireSat native resolution is 5 meters';

COMMENT ON COLUMN firesat_detections.confidence IS
'AI model confidence score (0.0 to 1.0)';

COMMENT ON COLUMN firesat_detections.fire_radiative_power IS
'Fire Radiative Power in Megawatts';
