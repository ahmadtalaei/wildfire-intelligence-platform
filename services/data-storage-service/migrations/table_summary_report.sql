-- =====================================================
-- SPECIALIZED TABLES DATA SUMMARY REPORT
-- =====================================================

SELECT
    table_name AS "Table Name",
    total_records AS "Total Records",
    last_hour AS "Last Hour",
    last_day AS "Last 24h",
    oldest_record AS "Oldest Record",
    newest_record AS "Newest Record",
    CASE
        WHEN last_hour > 0 THEN 'LIVE'
        WHEN total_records > 0 THEN 'IDLE'
        ELSE 'EMPTY'
    END AS "Status"
FROM (
    -- Weather Model Forecasts
    SELECT 'nam_forecasts' AS table_name,
           COUNT(*) AS total_records,
           COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '1 hour') AS last_hour,
           COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '24 hours') AS last_day,
           MIN(created_at)::TEXT AS oldest_record,
           MAX(created_at)::TEXT AS newest_record
    FROM nam_forecasts

    UNION ALL
    SELECT 'gfs_forecasts',
           COUNT(*),
           COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '1 hour'),
           COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '24 hours'),
           MIN(created_at)::TEXT,
           MAX(created_at)::TEXT
    FROM gfs_forecasts

    UNION ALL
    SELECT 'era5_land_reanalysis',
           COUNT(*),
           COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '1 hour'),
           COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '24 hours'),
           MIN(created_at)::TEXT,
           MAX(created_at)::TEXT
    FROM era5_land_reanalysis

    UNION ALL
    SELECT 'era5_reanalysis',
           COUNT(*),
           COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '1 hour'),
           COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '24 hours'),
           MIN(created_at)::TEXT,
           MAX(created_at)::TEXT
    FROM era5_reanalysis

    -- Weather Station Observations
    UNION ALL
    SELECT 'metar_observations',
           COUNT(*),
           COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '1 hour'),
           COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '24 hours'),
           MIN(created_at)::TEXT,
           MAX(created_at)::TEXT
    FROM metar_observations

    UNION ALL
    SELECT 'noaa_station_observations',
           COUNT(*),
           COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '1 hour'),
           COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '24 hours'),
           MIN(created_at)::TEXT,
           MAX(created_at)::TEXT
    FROM noaa_station_observations

    -- Weather Alerts & Forecasts
    UNION ALL
    SELECT 'noaa_gridpoint_forecast',
           COUNT(*),
           COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '1 hour'),
           COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '24 hours'),
           MIN(created_at)::TEXT,
           MAX(created_at)::TEXT
    FROM noaa_gridpoint_forecast

    UNION ALL
    SELECT 'noaa_weather_alerts',
           COUNT(*),
           COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '1 hour'),
           COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '24 hours'),
           MIN(created_at)::TEXT,
           MAX(created_at)::TEXT
    FROM noaa_weather_alerts

    -- Fire Detection Satellites
    UNION ALL
    SELECT 'firms_viirs_snpp_detections',
           COUNT(*),
           COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '1 hour'),
           COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '24 hours'),
           MIN(created_at)::TEXT,
           MAX(created_at)::TEXT
    FROM firms_viirs_snpp_detections

    UNION ALL
    SELECT 'firms_viirs_noaa20_detections',
           COUNT(*),
           COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '1 hour'),
           COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '24 hours'),
           MIN(created_at)::TEXT,
           MAX(created_at)::TEXT
    FROM firms_viirs_noaa20_detections

    UNION ALL
    SELECT 'firms_viirs_noaa21_detections',
           COUNT(*),
           COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '1 hour'),
           COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '24 hours'),
           MIN(created_at)::TEXT,
           MAX(created_at)::TEXT
    FROM firms_viirs_noaa21_detections

    UNION ALL
    SELECT 'firms_modis_terra_detections',
           COUNT(*),
           COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '1 hour'),
           COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '24 hours'),
           MIN(created_at)::TEXT,
           MAX(created_at)::TEXT
    FROM firms_modis_terra_detections

    UNION ALL
    SELECT 'firms_modis_aqua_detections',
           COUNT(*),
           COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '1 hour'),
           COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '24 hours'),
           MIN(created_at)::TEXT,
           MAX(created_at)::TEXT
    FROM firms_modis_aqua_detections

    UNION ALL
    SELECT 'landsat_nrt_detections',
           COUNT(*),
           COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '1 hour'),
           COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '24 hours'),
           MIN(created_at)::TEXT,
           MAX(created_at)::TEXT
    FROM landsat_nrt_detections

    -- Satellite Imagery Metadata
    UNION ALL
    SELECT 'landsat_thermal_imagery',
           COUNT(*),
           COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '1 hour'),
           COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '24 hours'),
           MIN(created_at)::TEXT,
           MAX(created_at)::TEXT
    FROM landsat_thermal_imagery

    UNION ALL
    SELECT 'sentinel2_msi_imagery',
           COUNT(*),
           COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '1 hour'),
           COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '24 hours'),
           MIN(created_at)::TEXT,
           MAX(created_at)::TEXT
    FROM sentinel2_msi_imagery

    UNION ALL
    SELECT 'sentinel3_slstr_imagery',
           COUNT(*),
           COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '1 hour'),
           COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '24 hours'),
           MIN(created_at)::TEXT,
           MAX(created_at)::TEXT
    FROM sentinel3_slstr_imagery

    -- IoT Sensors
    UNION ALL
    SELECT 'iot_weather_stations',
           COUNT(*),
           COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '1 hour'),
           COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '24 hours'),
           MIN(created_at)::TEXT,
           MAX(created_at)::TEXT
    FROM iot_weather_stations

    UNION ALL
    SELECT 'iot_soil_moisture_sensors',
           COUNT(*),
           COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '1 hour'),
           COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '24 hours'),
           MIN(created_at)::TEXT,
           MAX(created_at)::TEXT
    FROM iot_soil_moisture_sensors

    -- Air Quality
    UNION ALL
    SELECT 'sensor_readings',
           COUNT(*),
           COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '1 hour'),
           COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '24 hours'),
           MIN(created_at)::TEXT,
           MAX(created_at)::TEXT
    FROM sensor_readings

    UNION ALL
    SELECT 'airnow_observations',
           COUNT(*),
           COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '1 hour'),
           COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '24 hours'),
           MIN(created_at)::TEXT,
           MAX(created_at)::TEXT
    FROM airnow_observations

    -- Fire Incidents
    UNION ALL
    SELECT 'fire_incidents',
           COUNT(*),
           COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '1 hour'),
           COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '24 hours'),
           MIN(created_at)::TEXT,
           MAX(created_at)::TEXT
    FROM fire_incidents

    -- Legacy
    UNION ALL
    SELECT 'weather_data_legacy',
           COUNT(*),
           COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '1 hour'),
           COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '24 hours'),
           MIN(created_at)::TEXT,
           MAX(created_at)::TEXT
    FROM weather_data_legacy
) AS summary
ORDER BY total_records DESC, last_hour DESC;
