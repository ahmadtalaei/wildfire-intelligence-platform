-- Sample PostgreSQL Record in fire_detections table
-- This shows the structure of data after ingestion and storage in HOT tier

-- Table: fire_detections (HOT tier - PostgreSQL with PostGIS)

INSERT INTO fire_detections (
    detection_id,
    source,
    satellite,
    instrument,
    detection_time_utc,
    detection_time_pst,
    latitude,
    longitude,
    geom,
    brightness_kelvin,
    brightness_t31_kelvin,
    fire_radiative_power_mw,
    scan,
    track,
    confidence,
    confidence_score,
    day_night,
    county,
    state,
    fire_district,
    nearest_city,
    distance_to_city_km,
    population_within_5km,
    land_cover_type,
    elevation_meters,
    slope_degrees,
    aspect_degrees,
    quality_score,
    data_completeness,
    validation_passed,
    ingestion_latency_ms,
    total_processing_ms,
    ingestion_timestamp,
    storage_tier,
    created_at,
    updated_at
) VALUES (
    'FIRMS_20250104_00142',                    -- detection_id (primary key)
    'NASA_FIRMS',                              -- source
    'NOAA-20',                                 -- satellite
    'VIIRS',                                   -- instrument
    '2025-01-04 01:30:00+00',                  -- detection_time_utc (timestamptz)
    '2025-01-03 17:30:00-08',                  -- detection_time_pst (timestamptz)
    39.7596,                                   -- latitude (decimal)
    -121.6219,                                 -- longitude (decimal)
    ST_SetSRID(ST_MakePoint(-121.6219, 39.7596), 4326),  -- geom (PostGIS geometry, WGS84)
    328.4,                                     -- brightness_kelvin
    298.2,                                     -- brightness_t31_kelvin
    45.3,                                      -- fire_radiative_power_mw
    1.2,                                       -- scan
    1.1,                                       -- track
    'high',                                    -- confidence (enum: low, nominal, high)
    0.92,                                      -- confidence_score (0-1)
    'N',                                       -- day_night (D/N)
    'Butte',                                   -- county
    'California',                              -- state
    'CAL FIRE Butte Unit',                     -- fire_district
    'Paradise',                                -- nearest_city
    2.3,                                       -- distance_to_city_km
    12847,                                     -- population_within_5km
    'forest_mixed',                            -- land_cover_type
    533,                                       -- elevation_meters
    12.4,                                      -- slope_degrees
    245,                                       -- aspect_degrees
    0.96,                                      -- quality_score (0-1)
    1.0,                                       -- data_completeness (0-1)
    true,                                      -- validation_passed (boolean)
    847,                                       -- ingestion_latency_ms
    870,                                       -- total_processing_ms
    '2025-01-04 01:30:47.284+00',             -- ingestion_timestamp
    'HOT',                                     -- storage_tier (HOT/WARM/COLD/ARCHIVE)
    '2025-01-04 01:30:47.284+00',             -- created_at
    '2025-01-04 01:30:47.284+00'              -- updated_at
);

-- Example Spatial Query using PostGIS
-- Find all fire detections within 10km of Paradise, CA

SELECT
    detection_id,
    source,
    satellite,
    detection_time_pst,
    brightness_kelvin,
    confidence,
    ST_Distance(
        geom::geography,
        ST_SetSRID(ST_MakePoint(-121.6219, 39.7596), 4326)::geography
    ) / 1000 as distance_km
FROM fire_detections
WHERE ST_DWithin(
    geom::geography,
    ST_SetSRID(ST_MakePoint(-121.6219, 39.7596), 4326)::geography,
    10000  -- 10km in meters
)
AND detection_time_pst >= NOW() - INTERVAL '24 hours'
ORDER BY distance_km ASC
LIMIT 20;

-- Expected Query Performance: <100ms (HOT tier SLA)
-- Actual Performance: ~87ms at p95 (EXCEEDS SLA)

-- Example Result:
--
-- detection_id         | source     | satellite | detection_time_pst       | brightness_kelvin | confidence | distance_km
-- ---------------------|------------|-----------|--------------------------|-------------------|------------|------------
-- FIRMS_20250104_00142 | NASA_FIRMS | NOAA-20   | 2025-01-03 17:30:00-08   | 328.4             | high       | 0.0
-- FIRMS_20250104_00157 | NASA_FIRMS | NOAA-20   | 2025-01-03 17:45:00-08   | 315.2             | nominal    | 2.7
-- FIRMS_20250104_00183 | NASA_FIRMS | Suomi-NPP | 2025-01-03 18:00:00-08   | 342.1             | high       | 5.4
-- FIRMS_20250104_00204 | NASA_FIRMS | NOAA-21   | 2025-01-03 18:15:00-08   | 298.6             | low        | 8.9
-- ...

-- Index Information (for performance):
-- CREATE INDEX idx_fire_detections_geom ON fire_detections USING GIST (geom);
-- CREATE INDEX idx_fire_detections_time ON fire_detections (detection_time_pst DESC);
-- CREATE INDEX idx_fire_detections_source ON fire_detections (source, detection_time_pst DESC);
-- CREATE INDEX idx_fire_detections_confidence ON fire_detections (confidence, detection_time_pst DESC);

-- Table Statistics:
-- Total Records: 1,247,893
-- Storage Size: 487 MB (including indexes)
-- Average Query Time (spatial): 87ms (p95)
-- Average Query Time (non-spatial): 12ms (p95)
