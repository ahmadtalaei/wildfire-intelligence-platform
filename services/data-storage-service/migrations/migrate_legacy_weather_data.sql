-- =====================================================
-- Legacy Weather Data Migration to Specialized Tables
-- =====================================================
-- Migrates 2.6M+ records from weather_data_legacy to specialized tables
-- Created: 2025-10-02
-- Status: READY TO RUN

BEGIN;

-- =====================================================
-- 1. ERA5-Land Reanalysis (1,152,141 records)
-- =====================================================
INSERT INTO era5_land_reanalysis (
    timestamp,
    latitude,
    longitude,
    temperature_2m_celsius,
    surface_pressure_pa,
    source,
    created_at
)
SELECT
    timestamp,
    latitude::DOUBLE PRECISION,
    longitude::DOUBLE PRECISION,
    temperature::DOUBLE PRECISION,
    pressure::DOUBLE PRECISION,
    'ERA5-Land Reanalysis',
    created_at
FROM weather_data_legacy
WHERE source = 'wx_era5_land'
ON CONFLICT DO NOTHING;

-- Log progress
DO $$
BEGIN
    RAISE NOTICE 'Migrated ERA5-Land: % records',
        (SELECT COUNT(*) FROM era5_land_reanalysis WHERE source = 'ERA5-Land Reanalysis');
END $$;

-- =====================================================
-- 2. NAM Forecasts (859,980 records)
-- =====================================================
INSERT INTO nam_forecasts (
    timestamp,
    latitude,
    longitude,
    temperature_celsius,
    surface_pressure_pa,
    source,
    created_at
)
SELECT
    timestamp,
    latitude::DOUBLE PRECISION,
    longitude::DOUBLE PRECISION,
    temperature::DOUBLE PRECISION,
    pressure::DOUBLE PRECISION,
    'NAM Forecast',
    created_at
FROM weather_data_legacy
WHERE source = 'wx_nam_forecast'
ON CONFLICT DO NOTHING;

DO $$
BEGIN
    RAISE NOTICE 'Migrated NAM Forecasts: % records',
        (SELECT COUNT(*) FROM nam_forecasts WHERE source = 'NAM Forecast');
END $$;

-- =====================================================
-- 3. ERA5 Reanalysis (373,332 records)
-- =====================================================
INSERT INTO era5_reanalysis (
    timestamp,
    latitude,
    longitude,
    temperature_celsius,
    relative_humidity_percent,
    surface_pressure_pa,
    source,
    created_at
)
SELECT
    timestamp,
    latitude::DOUBLE PRECISION,
    longitude::DOUBLE PRECISION,
    temperature::DOUBLE PRECISION,
    humidity::DOUBLE PRECISION,
    pressure::DOUBLE PRECISION,
    'ERA5 Reanalysis',
    created_at
FROM weather_data_legacy
WHERE source = 'wx_era5_reanalysis'
ON CONFLICT DO NOTHING;

DO $$
BEGIN
    RAISE NOTICE 'Migrated ERA5 Reanalysis: % records',
        (SELECT COUNT(*) FROM era5_reanalysis WHERE source = 'ERA5 Reanalysis');
END $$;

-- =====================================================
-- 4. GFS Forecasts (173,384 records)
-- =====================================================
INSERT INTO gfs_forecasts (
    timestamp,
    latitude,
    longitude,
    temperature_celsius,
    surface_pressure_pa,
    source,
    created_at
)
SELECT
    timestamp,
    latitude::DOUBLE PRECISION,
    longitude::DOUBLE PRECISION,
    temperature::DOUBLE PRECISION,
    pressure::DOUBLE PRECISION,
    'GFS Forecast',
    created_at
FROM weather_data_legacy
WHERE source = 'wx_gfs_forecast'
ON CONFLICT DO NOTHING;

DO $$
BEGIN
    RAISE NOTICE 'Migrated GFS Forecasts: % records',
        (SELECT COUNT(*) FROM gfs_forecasts WHERE source = 'GFS Forecast');
END $$;

-- =====================================================
-- 5. NOAA Station Observations (69,601 records)
-- =====================================================
INSERT INTO noaa_station_observations (
    timestamp,
    latitude,
    longitude,
    temperature_celsius,
    relative_humidity_percent,
    wind_speed_ms,
    wind_direction_degrees,
    barometric_pressure_pa,
    source,
    created_at
)
SELECT
    timestamp,
    latitude::DOUBLE PRECISION,
    longitude::DOUBLE PRECISION,
    temperature::DOUBLE PRECISION,
    humidity::DOUBLE PRECISION,
    wind_speed::DOUBLE PRECISION,
    wind_direction,
    pressure::DOUBLE PRECISION,
    'NOAA Weather Stations',
    created_at
FROM weather_data_legacy
WHERE source IN ('noaa_stations_current', 'noaa_stations_historical')
ON CONFLICT DO NOTHING;

DO $$
BEGIN
    RAISE NOTICE 'Migrated NOAA Stations: % records',
        (SELECT COUNT(*) FROM noaa_station_observations WHERE source = 'NOAA Weather Stations');
END $$;

-- =====================================================
-- 6. METAR Observations (1,056 records)
-- =====================================================
INSERT INTO metar_observations (
    timestamp,
    latitude,
    longitude,
    temperature_celsius,
    relative_humidity_percent,
    wind_speed_ms,
    wind_direction_degrees,
    altimeter_setting_pa,
    source,
    created_at
)
SELECT
    timestamp,
    latitude::DOUBLE PRECISION,
    longitude::DOUBLE PRECISION,
    temperature::DOUBLE PRECISION,
    humidity::DOUBLE PRECISION,
    wind_speed::DOUBLE PRECISION,
    wind_direction,
    pressure::DOUBLE PRECISION,
    'METAR Aviation Weather',
    created_at
FROM weather_data_legacy
WHERE source = 'wx_station_metar'
ON CONFLICT DO NOTHING;

DO $$
BEGIN
    RAISE NOTICE 'Migrated METAR Observations: % records',
        (SELECT COUNT(*) FROM metar_observations WHERE source = 'METAR Aviation Weather');
END $$;

-- =====================================================
-- 7. NOAA Weather Alerts (1,195 records)
-- =====================================================
-- Note: Alerts have different schema, may need special handling
-- Skipping for now - alerts likely need metadata fields not in legacy table

DO $$
BEGIN
    RAISE NOTICE 'Skipped NOAA Weather Alerts - requires metadata fields not in legacy table';
END $$;

-- =====================================================
-- 8. NOAA Gridpoint Forecasts (3,575 legacy records)
-- =====================================================
-- Note: Already have 1,148 new records from live streaming
-- Legacy records use generic schema, new records have specialized fields

INSERT INTO noaa_gridpoint_forecast (
    timestamp,
    latitude,
    longitude,
    temperature_celsius,
    source,
    created_at
)
SELECT
    timestamp,
    latitude::DOUBLE PRECISION,
    longitude::DOUBLE PRECISION,
    temperature::DOUBLE PRECISION,
    'NOAA/NWS Gridpoint Forecast',
    created_at
FROM weather_data_legacy
WHERE source = 'noaa_gridpoints_forecast'
ON CONFLICT DO NOTHING;

DO $$
BEGIN
    RAISE NOTICE 'Migrated NOAA Gridpoint Forecasts (legacy): % total records',
        (SELECT COUNT(*) FROM noaa_gridpoint_forecast);
END $$;

-- =====================================================
-- Summary Report
-- =====================================================
DO $$
BEGIN
    RAISE NOTICE '========================================';
    RAISE NOTICE 'MIGRATION COMPLETE';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'ERA5-Land Reanalysis: %', (SELECT COUNT(*) FROM era5_land_reanalysis);
    RAISE NOTICE 'NAM Forecasts: %', (SELECT COUNT(*) FROM nam_forecasts);
    RAISE NOTICE 'ERA5 Reanalysis: %', (SELECT COUNT(*) FROM era5_reanalysis);
    RAISE NOTICE 'GFS Forecasts: %', (SELECT COUNT(*) FROM gfs_forecasts);
    RAISE NOTICE 'NOAA Stations: %', (SELECT COUNT(*) FROM noaa_station_observations);
    RAISE NOTICE 'METAR Observations: %', (SELECT COUNT(*) FROM metar_observations);
    RAISE NOTICE 'NOAA Gridpoint Forecast: %', (SELECT COUNT(*) FROM noaa_gridpoint_forecast);
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Legacy table remains as weather_data_legacy for backup';
    RAISE NOTICE 'Drop it manually after verification: DROP TABLE weather_data_legacy;';
END $$;

COMMIT;

-- =====================================================
-- Post-Migration Verification Queries
-- =====================================================
-- Uncomment to run after migration:

-- SELECT 'era5_land_reanalysis' AS table_name, COUNT(*) AS records FROM era5_land_reanalysis
-- UNION ALL SELECT 'nam_forecasts', COUNT(*) FROM nam_forecasts
-- UNION ALL SELECT 'era5_reanalysis', COUNT(*) FROM era5_reanalysis
-- UNION ALL SELECT 'gfs_forecasts', COUNT(*) FROM gfs_forecasts
-- UNION ALL SELECT 'noaa_station_observations', COUNT(*) FROM noaa_station_observations
-- UNION ALL SELECT 'metar_observations', COUNT(*) FROM metar_observations
-- UNION ALL SELECT 'noaa_gridpoint_forecast', COUNT(*) FROM noaa_gridpoint_forecast
-- ORDER BY records DESC;
