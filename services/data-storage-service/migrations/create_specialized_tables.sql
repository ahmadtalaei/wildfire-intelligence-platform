-- ============================================================================
-- SPECIALIZED DATA TABLES FOR WILDFIRE INTELLIGENCE PLATFORM
-- ============================================================================
-- Each data source gets its own optimized table with source-specific fields
-- This improves data fidelity, query performance, and storage efficiency
-- ============================================================================

-- ============================================================================
-- 1. WEATHER STATION OBSERVATIONS
-- ============================================================================

-- METAR Aviation Weather Observations
CREATE TABLE IF NOT EXISTS metar_observations (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    station_id VARCHAR(10) NOT NULL,
    station_name VARCHAR(255),
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    elevation_m DOUBLE PRECISION,

    -- Temperature & Moisture
    temperature_celsius DOUBLE PRECISION,
    dewpoint_celsius DOUBLE PRECISION,
    relative_humidity_percent DOUBLE PRECISION,
    heat_index_celsius DOUBLE PRECISION,
    wind_chill_celsius DOUBLE PRECISION,

    -- Wind
    wind_speed_ms DOUBLE PRECISION,
    wind_gust_ms DOUBLE PRECISION,
    wind_direction_degrees INTEGER,

    -- Pressure
    altimeter_setting_pa DOUBLE PRECISION,
    sea_level_pressure_pa DOUBLE PRECISION,

    -- Visibility & Sky
    visibility_m DOUBLE PRECISION,
    cloud_coverage_percent INTEGER,
    cloud_layers JSONB,

    -- Weather Conditions
    weather_description TEXT,
    present_weather_codes TEXT[],

    -- Quality & Metadata
    raw_metar TEXT,
    data_quality DOUBLE PRECISION,
    flight_category VARCHAR(10), -- VFR, MVFR, IFR, LIFR

    source VARCHAR(50) DEFAULT 'wx_station_metar',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_metar_station_time ON metar_observations(station_id, timestamp DESC);
CREATE INDEX idx_metar_timestamp ON metar_observations(timestamp DESC);
CREATE INDEX idx_metar_location ON metar_observations(latitude, longitude);
CREATE INDEX idx_metar_created ON metar_observations(created_at DESC);

-- NOAA Weather Station Current Observations
CREATE TABLE IF NOT EXISTS noaa_station_observations (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    station_id VARCHAR(20) NOT NULL,
    station_name VARCHAR(255),
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    elevation_m DOUBLE PRECISION,
    county VARCHAR(100),
    state VARCHAR(2),

    -- Temperature & Moisture
    temperature_celsius DOUBLE PRECISION,
    dewpoint_celsius DOUBLE PRECISION,
    relative_humidity_percent DOUBLE PRECISION,
    heat_index_celsius DOUBLE PRECISION,
    wind_chill_celsius DOUBLE PRECISION,

    -- Wind
    wind_speed_ms DOUBLE PRECISION,
    wind_gust_ms DOUBLE PRECISION,
    wind_direction_degrees INTEGER,

    -- Pressure
    barometric_pressure_pa DOUBLE PRECISION,
    sea_level_pressure_pa DOUBLE PRECISION,
    pressure_tendency VARCHAR(20),

    -- Visibility & Sky
    visibility_m DOUBLE PRECISION,
    cloud_coverage_percent DOUBLE PRECISION,
    cloud_layers JSONB,

    -- Precipitation
    precipitation_last_hour_mm DOUBLE PRECISION,
    precipitation_last_3hours_mm DOUBLE PRECISION,
    precipitation_last_6hours_mm DOUBLE PRECISION,

    -- Weather Conditions
    weather_description TEXT,

    -- Quality & Metadata
    raw_metar TEXT,
    data_quality DOUBLE PRECISION,

    source VARCHAR(50) DEFAULT 'noaa_stations_current',
    provider VARCHAR(100) DEFAULT 'National Weather Service',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_noaa_obs_station_time ON noaa_station_observations(station_id, timestamp DESC);
CREATE INDEX idx_noaa_obs_timestamp ON noaa_station_observations(timestamp DESC);
CREATE INDEX idx_noaa_obs_location ON noaa_station_observations(latitude, longitude);
CREATE INDEX idx_noaa_obs_county ON noaa_station_observations(county, timestamp DESC);
CREATE INDEX idx_noaa_obs_created ON noaa_station_observations(created_at DESC);

-- ============================================================================
-- 2. WEATHER MODEL FORECASTS (Grid-based)
-- ============================================================================

-- ERA5-Land Reanalysis (High-resolution land reanalysis)
CREATE TABLE IF NOT EXISTS era5_land_reanalysis (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    forecast_time TIMESTAMPTZ,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,

    -- Surface Variables
    temperature_2m_celsius DOUBLE PRECISION,
    dewpoint_2m_celsius DOUBLE PRECISION,
    surface_pressure_pa DOUBLE PRECISION,

    -- Wind (10m height)
    u_wind_10m_ms DOUBLE PRECISION,
    v_wind_10m_ms DOUBLE PRECISION,
    wind_speed_10m_ms DOUBLE PRECISION,
    wind_direction_10m_degrees INTEGER,

    -- Precipitation & Moisture
    total_precipitation_mm DOUBLE PRECISION,
    soil_moisture_level1 DOUBLE PRECISION,
    soil_moisture_level2 DOUBLE PRECISION,
    soil_moisture_level3 DOUBLE PRECISION,
    soil_moisture_level4 DOUBLE PRECISION,

    -- Radiation
    surface_solar_radiation_wm2 DOUBLE PRECISION,
    surface_thermal_radiation_wm2 DOUBLE PRECISION,

    -- Snow
    snow_depth_m DOUBLE PRECISION,
    snow_cover_percent DOUBLE PRECISION,

    -- Evaporation
    evaporation_mm DOUBLE PRECISION,
    potential_evaporation_mm DOUBLE PRECISION,

    -- Quality
    data_quality DOUBLE PRECISION,

    source VARCHAR(50) DEFAULT 'wx_era5_land',
    provider VARCHAR(100) DEFAULT 'ECMWF Copernicus',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_era5_land_time_location ON era5_land_reanalysis(timestamp DESC, latitude, longitude);
CREATE INDEX idx_era5_land_location ON era5_land_reanalysis(latitude, longitude);
CREATE INDEX idx_era5_land_created ON era5_land_reanalysis(created_at DESC);

-- ERA5 Standard Reanalysis (Global atmospheric reanalysis)
CREATE TABLE IF NOT EXISTS era5_reanalysis (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    forecast_time TIMESTAMPTZ,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    pressure_level_hpa INTEGER, -- 1000, 925, 850, 700, 500, etc.

    -- Atmospheric Variables
    temperature_celsius DOUBLE PRECISION,
    geopotential_height_m DOUBLE PRECISION,
    relative_humidity_percent DOUBLE PRECISION,

    -- Wind
    u_wind_ms DOUBLE PRECISION,
    v_wind_ms DOUBLE PRECISION,
    wind_speed_ms DOUBLE PRECISION,
    wind_direction_degrees INTEGER,
    vertical_velocity_pas DOUBLE PRECISION,

    -- Surface Variables (when pressure_level is NULL)
    surface_pressure_pa DOUBLE PRECISION,
    total_precipitation_mm DOUBLE PRECISION,

    -- Quality
    data_quality DOUBLE PRECISION,

    source VARCHAR(50) DEFAULT 'wx_era5_reanalysis',
    provider VARCHAR(100) DEFAULT 'ECMWF Copernicus',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_era5_time_location ON era5_reanalysis(timestamp DESC, latitude, longitude);
CREATE INDEX idx_era5_pressure_level ON era5_reanalysis(pressure_level, timestamp DESC);
CREATE INDEX idx_era5_location ON era5_reanalysis(latitude, longitude);
CREATE INDEX idx_era5_created ON era5_reanalysis(created_at DESC);

-- GFS Global Forecast System
CREATE TABLE IF NOT EXISTS gfs_forecasts (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    forecast_time TIMESTAMPTZ NOT NULL,
    forecast_hour INTEGER, -- 0, 3, 6, 9, ... 384
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,

    -- Surface Variables
    temperature_celsius DOUBLE PRECISION,
    dewpoint_celsius DOUBLE PRECISION,
    surface_pressure_pa DOUBLE PRECISION,

    -- Wind (10m)
    u_wind_10m_ms DOUBLE PRECISION,
    v_wind_10m_ms DOUBLE PRECISION,
    wind_speed_10m_ms DOUBLE PRECISION,
    wind_direction_10m_degrees INTEGER,
    wind_gust_ms DOUBLE PRECISION,

    -- Precipitation
    precipitation_rate_kgm2s DOUBLE PRECISION,
    total_precipitation_mm DOUBLE PRECISION,
    convective_precipitation_mm DOUBLE PRECISION,

    -- Categorical Precipitation
    rain_flag BOOLEAN,
    snow_flag BOOLEAN,
    freezing_rain_flag BOOLEAN,
    ice_pellets_flag BOOLEAN,

    -- Cloud & Radiation
    total_cloud_cover_percent DOUBLE PRECISION,
    downward_shortwave_radiation_wm2 DOUBLE PRECISION,
    downward_longwave_radiation_wm2 DOUBLE PRECISION,

    -- Visibility & Instability
    visibility_m DOUBLE PRECISION,
    cape_jkg DOUBLE PRECISION, -- Convective Available Potential Energy
    cin_jkg DOUBLE PRECISION,  -- Convective Inhibition

    -- Quality
    data_quality DOUBLE PRECISION,

    source VARCHAR(50) DEFAULT 'wx_gfs_forecast',
    provider VARCHAR(100) DEFAULT 'NOAA NCEP',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_gfs_forecast_time_location ON gfs_forecasts(forecast_time DESC, latitude, longitude);
CREATE INDEX idx_gfs_timestamp ON gfs_forecasts(timestamp DESC);
CREATE INDEX idx_gfs_location ON gfs_forecasts(latitude, longitude);
CREATE INDEX idx_gfs_forecast_hour ON gfs_forecasts(forecast_hour);
CREATE INDEX idx_gfs_created ON gfs_forecasts(created_at DESC);

-- NAM North American Mesoscale Forecast
CREATE TABLE IF NOT EXISTS nam_forecasts (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    forecast_time TIMESTAMPTZ NOT NULL,
    forecast_hour INTEGER, -- 0, 1, 2, 3, ... 84
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,

    -- Surface Variables
    temperature_celsius DOUBLE PRECISION,
    dewpoint_celsius DOUBLE PRECISION,
    surface_pressure_pa DOUBLE PRECISION,

    -- Wind (10m)
    u_wind_10m_ms DOUBLE PRECISION,
    v_wind_10m_ms DOUBLE PRECISION,
    wind_speed_10m_ms DOUBLE PRECISION,
    wind_direction_10m_degrees INTEGER,
    wind_gust_ms DOUBLE PRECISION,

    -- Precipitation
    precipitation_rate_kgm2s DOUBLE PRECISION,
    total_precipitation_mm DOUBLE PRECISION,
    convective_precipitation_mm DOUBLE PRECISION,

    -- Categorical Precipitation
    rain_flag BOOLEAN,
    snow_flag BOOLEAN,
    freezing_rain_flag BOOLEAN,
    ice_pellets_flag BOOLEAN,

    -- Snow
    snow_depth_m DOUBLE PRECISION,
    snow_water_equivalent_mm DOUBLE PRECISION,

    -- Soil
    soil_moisture_kgm2 DOUBLE PRECISION,
    soil_temperature_celsius DOUBLE PRECISION,

    -- Cloud & Radiation
    total_cloud_cover_percent DOUBLE PRECISION,
    downward_shortwave_radiation_wm2 DOUBLE PRECISION,
    downward_longwave_radiation_wm2 DOUBLE PRECISION,

    -- Visibility & Instability
    visibility_m DOUBLE PRECISION,
    cape_jkg DOUBLE PRECISION,
    cin_jkg DOUBLE PRECISION,
    lifted_index_celsius DOUBLE PRECISION,

    -- Quality
    data_quality DOUBLE PRECISION,

    source VARCHAR(50) DEFAULT 'wx_nam_forecast',
    provider VARCHAR(100) DEFAULT 'NOAA NCEP',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_nam_forecast_time_location ON nam_forecasts(forecast_time DESC, latitude, longitude);
CREATE INDEX idx_nam_timestamp ON nam_forecasts(timestamp DESC);
CREATE INDEX idx_nam_location ON nam_forecasts(latitude, longitude);
CREATE INDEX idx_nam_forecast_hour ON nam_forecasts(forecast_hour);
CREATE INDEX idx_nam_created ON nam_forecasts(created_at DESC);

-- ============================================================================
-- 3. WEATHER ALERTS
-- ============================================================================

CREATE TABLE IF NOT EXISTS noaa_weather_alerts (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    alert_id VARCHAR(255) UNIQUE NOT NULL,

    -- Alert Classification
    event VARCHAR(255) NOT NULL, -- Red Flag Warning, Fire Weather Watch, etc.
    headline TEXT,
    description TEXT,
    instruction TEXT,

    -- Severity & Urgency
    severity VARCHAR(50), -- Extreme, Severe, Moderate, Minor
    urgency VARCHAR(50),  -- Immediate, Expected, Future
    certainty VARCHAR(50), -- Observed, Likely, Possible

    -- Time Windows
    effective TIMESTAMPTZ,
    onset TIMESTAMPTZ,
    expires TIMESTAMPTZ,
    ends TIMESTAMPTZ,

    -- Location
    area_description TEXT,
    affected_zones TEXT[],
    affected_counties TEXT[],
    geometry JSONB, -- GeoJSON polygon

    -- Issuer
    sender_name VARCHAR(255),
    sender_code VARCHAR(50),

    -- Status
    status VARCHAR(50), -- Actual, Exercise, Test
    message_type VARCHAR(50), -- Alert, Update, Cancel
    category VARCHAR(50), -- Met (Meteorological), Fire, etc.

    -- Quality
    data_quality DOUBLE PRECISION DEFAULT 1.0,

    source VARCHAR(50) DEFAULT 'noaa_alerts_active',
    provider VARCHAR(100) DEFAULT 'National Weather Service',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_noaa_alerts_event ON noaa_weather_alerts(event, timestamp DESC);
CREATE INDEX idx_noaa_alerts_severity ON noaa_weather_alerts(severity, expires DESC);
CREATE INDEX idx_noaa_alerts_effective ON noaa_weather_alerts(effective DESC);
CREATE INDEX idx_noaa_alerts_expires ON noaa_weather_alerts(expires DESC);
CREATE INDEX idx_noaa_alerts_geometry ON noaa_weather_alerts USING GIN(geometry);
CREATE INDEX idx_noaa_alerts_created ON noaa_weather_alerts(created_at DESC);

-- ============================================================================
-- 4. FIRE DETECTION SATELLITES
-- ============================================================================

-- FIRMS VIIRS S-NPP Fire Detections
CREATE TABLE IF NOT EXISTS firms_viirs_snpp_detections (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,

    -- Fire Characteristics
    brightness_kelvin DOUBLE PRECISION,
    brightness_temperature_i4 DOUBLE PRECISION,
    brightness_temperature_i5 DOUBLE PRECISION,
    fire_radiative_power_mw DOUBLE PRECISION,

    -- Detection Quality
    confidence VARCHAR(10), -- low, nominal, high
    confidence_percent INTEGER,

    -- Satellite Info
    scan_angle DOUBLE PRECISION,
    track_degrees DOUBLE PRECISION,

    -- Day/Night
    daynight VARCHAR(1), -- D or N

    -- Acquisition
    satellite VARCHAR(20) DEFAULT 'Suomi-NPP',
    instrument VARCHAR(20) DEFAULT 'VIIRS',
    version VARCHAR(10),

    source VARCHAR(50) DEFAULT 'firms_viirs_snpp',
    provider VARCHAR(100) DEFAULT 'NASA FIRMS',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_firms_snpp_time_location ON firms_viirs_snpp_detections(timestamp DESC, latitude, longitude);
CREATE INDEX idx_firms_snpp_location ON firms_viirs_snpp_detections(latitude, longitude);
CREATE INDEX idx_firms_snpp_confidence ON firms_viirs_snpp_detections(confidence, timestamp DESC);
CREATE INDEX idx_firms_snpp_frp ON firms_viirs_snpp_detections(fire_radiative_power_mw DESC);
CREATE INDEX idx_firms_snpp_created ON firms_viirs_snpp_detections(created_at DESC);

-- FIRMS VIIRS NOAA-20 Fire Detections
CREATE TABLE IF NOT EXISTS firms_viirs_noaa20_detections (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,

    -- Fire Characteristics
    brightness_kelvin DOUBLE PRECISION,
    brightness_temperature_i4 DOUBLE PRECISION,
    brightness_temperature_i5 DOUBLE PRECISION,
    fire_radiative_power_mw DOUBLE PRECISION,

    -- Detection Quality
    confidence VARCHAR(10),
    confidence_percent INTEGER,

    -- Satellite Info
    scan_angle DOUBLE PRECISION,
    track_degrees DOUBLE PRECISION,

    -- Day/Night
    daynight VARCHAR(1),

    -- Acquisition
    satellite VARCHAR(20) DEFAULT 'NOAA-20',
    instrument VARCHAR(20) DEFAULT 'VIIRS',
    version VARCHAR(10),

    source VARCHAR(50) DEFAULT 'firms_viirs_noaa20',
    provider VARCHAR(100) DEFAULT 'NASA FIRMS',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_firms_noaa20_time_location ON firms_viirs_noaa20_detections(timestamp DESC, latitude, longitude);
CREATE INDEX idx_firms_noaa20_location ON firms_viirs_noaa20_detections(latitude, longitude);
CREATE INDEX idx_firms_noaa20_confidence ON firms_viirs_noaa20_detections(confidence, timestamp DESC);
CREATE INDEX idx_firms_noaa20_frp ON firms_viirs_noaa20_detections(fire_radiative_power_mw DESC);
CREATE INDEX idx_firms_noaa20_created ON firms_viirs_noaa20_detections(created_at DESC);

-- FIRMS VIIRS NOAA-21 Fire Detections
CREATE TABLE IF NOT EXISTS firms_viirs_noaa21_detections (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,

    -- Fire Characteristics
    brightness_kelvin DOUBLE PRECISION,
    brightness_temperature_i4 DOUBLE PRECISION,
    brightness_temperature_i5 DOUBLE PRECISION,
    fire_radiative_power_mw DOUBLE PRECISION,

    -- Detection Quality
    confidence VARCHAR(10),
    confidence_percent INTEGER,

    -- Satellite Info
    scan_angle DOUBLE PRECISION,
    track_degrees DOUBLE PRECISION,

    -- Day/Night
    daynight VARCHAR(1),

    -- Acquisition
    satellite VARCHAR(20) DEFAULT 'NOAA-21',
    instrument VARCHAR(20) DEFAULT 'VIIRS',
    version VARCHAR(10),

    source VARCHAR(50) DEFAULT 'firms_viirs_noaa21',
    provider VARCHAR(100) DEFAULT 'NASA FIRMS',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_firms_noaa21_time_location ON firms_viirs_noaa21_detections(timestamp DESC, latitude, longitude);
CREATE INDEX idx_firms_noaa21_location ON firms_viirs_noaa21_detections(latitude, longitude);
CREATE INDEX idx_firms_noaa21_confidence ON firms_viirs_noaa21_detections(confidence, timestamp DESC);
CREATE INDEX idx_firms_noaa21_frp ON firms_viirs_noaa21_detections(fire_radiative_power_mw DESC);
CREATE INDEX idx_firms_noaa21_created ON firms_viirs_noaa21_detections(created_at DESC);

-- FIRMS MODIS Terra Fire Detections
CREATE TABLE IF NOT EXISTS firms_modis_terra_detections (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,

    -- Fire Characteristics
    brightness_kelvin DOUBLE PRECISION,
    fire_radiative_power_mw DOUBLE PRECISION,

    -- Detection Quality
    confidence INTEGER, -- 0-100

    -- Satellite Info
    scan_angle DOUBLE PRECISION,
    track_degrees DOUBLE PRECISION,

    -- Day/Night
    daynight VARCHAR(1),

    -- Type (0 = presumed vegetation fire, 1-3 = other)
    type INTEGER,

    -- Acquisition
    satellite VARCHAR(20) DEFAULT 'Terra',
    instrument VARCHAR(20) DEFAULT 'MODIS',
    version VARCHAR(10),

    source VARCHAR(50) DEFAULT 'firms_modis_terra',
    provider VARCHAR(100) DEFAULT 'NASA FIRMS',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_firms_terra_time_location ON firms_modis_terra_detections(timestamp DESC, latitude, longitude);
CREATE INDEX idx_firms_terra_location ON firms_modis_terra_detections(latitude, longitude);
CREATE INDEX idx_firms_terra_confidence ON firms_modis_terra_detections(confidence, timestamp DESC);
CREATE INDEX idx_firms_terra_frp ON firms_modis_terra_detections(fire_radiative_power_mw DESC);
CREATE INDEX idx_firms_terra_created ON firms_modis_terra_detections(created_at DESC);

-- FIRMS MODIS Aqua Fire Detections
CREATE TABLE IF NOT EXISTS firms_modis_aqua_detections (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,

    -- Fire Characteristics
    brightness_kelvin DOUBLE PRECISION,
    fire_radiative_power_mw DOUBLE PRECISION,

    -- Detection Quality
    confidence INTEGER,

    -- Satellite Info
    scan_angle DOUBLE PRECISION,
    track_degrees DOUBLE PRECISION,

    -- Day/Night
    daynight VARCHAR(1),

    -- Type
    type INTEGER,

    -- Acquisition
    satellite VARCHAR(20) DEFAULT 'Aqua',
    instrument VARCHAR(20) DEFAULT 'MODIS',
    version VARCHAR(10),

    source VARCHAR(50) DEFAULT 'firms_modis_aqua',
    provider VARCHAR(100) DEFAULT 'NASA FIRMS',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_firms_aqua_time_location ON firms_modis_aqua_detections(timestamp DESC, latitude, longitude);
CREATE INDEX idx_firms_aqua_location ON firms_modis_aqua_detections(latitude, longitude);
CREATE INDEX idx_firms_aqua_confidence ON firms_modis_aqua_detections(confidence, timestamp DESC);
CREATE INDEX idx_firms_aqua_frp ON firms_modis_aqua_detections(fire_radiative_power_mw DESC);
CREATE INDEX idx_firms_aqua_created ON firms_modis_aqua_detections(created_at DESC);

-- Landsat NRT Fire Detections
CREATE TABLE IF NOT EXISTS landsat_nrt_detections (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,

    -- Fire Characteristics
    brightness_kelvin DOUBLE PRECISION,
    fire_radiative_power_mw DOUBLE PRECISION,

    -- Detection Quality
    confidence VARCHAR(10),

    -- Satellite Info
    satellite VARCHAR(20), -- Landsat-8, Landsat-9
    instrument VARCHAR(20) DEFAULT 'OLI/TIRS',
    version VARCHAR(10),

    source VARCHAR(50) DEFAULT 'landsat_nrt',
    provider VARCHAR(100) DEFAULT 'NASA FIRMS',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_landsat_time_location ON landsat_nrt_detections(timestamp DESC, latitude, longitude);
CREATE INDEX idx_landsat_location ON landsat_nrt_detections(latitude, longitude);
CREATE INDEX idx_landsat_confidence ON landsat_nrt_detections(confidence, timestamp DESC);
CREATE INDEX idx_landsat_created ON landsat_nrt_detections(created_at DESC);

-- ============================================================================
-- 5. SATELLITE IMAGERY METADATA
-- ============================================================================

-- Landsat Thermal Imagery
CREATE TABLE IF NOT EXISTS landsat_thermal_imagery (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    scene_id VARCHAR(255) UNIQUE NOT NULL,

    -- Coverage
    center_latitude DOUBLE PRECISION,
    center_longitude DOUBLE PRECISION,
    bbox_min_lat DOUBLE PRECISION,
    bbox_min_lon DOUBLE PRECISION,
    bbox_max_lat DOUBLE PRECISION,
    bbox_max_lon DOUBLE PRECISION,

    -- Thermal Bands
    band_10_brightness_temp_k DOUBLE PRECISION, -- TIRS1
    band_11_brightness_temp_k DOUBLE PRECISION, -- TIRS2

    -- Quality
    cloud_cover_percent DOUBLE PRECISION,
    data_quality VARCHAR(20),

    -- Satellite
    satellite VARCHAR(20), -- Landsat-8, Landsat-9
    sensor VARCHAR(20) DEFAULT 'OLI/TIRS',
    path INTEGER,
    row INTEGER,

    -- Processing
    processing_level VARCHAR(20), -- L1T, L2
    collection_number INTEGER,

    -- Storage
    thumbnail_url TEXT,
    download_url TEXT,
    file_size_mb DOUBLE PRECISION,

    source VARCHAR(50) DEFAULT 'sat_landsat_thermal',
    provider VARCHAR(100) DEFAULT 'USGS',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_landsat_thermal_time ON landsat_thermal_imagery(timestamp DESC);
CREATE INDEX idx_landsat_thermal_location ON landsat_thermal_imagery(center_latitude, center_longitude);
CREATE INDEX idx_landsat_thermal_scene ON landsat_thermal_imagery(scene_id);
CREATE INDEX idx_landsat_thermal_created ON landsat_thermal_imagery(created_at DESC);

-- Sentinel-2 MSI Imagery
CREATE TABLE IF NOT EXISTS sentinel2_msi_imagery (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    product_id VARCHAR(255) UNIQUE NOT NULL,

    -- Coverage
    center_latitude DOUBLE PRECISION,
    center_longitude DOUBLE PRECISION,
    bbox_min_lat DOUBLE PRECISION,
    bbox_min_lon DOUBLE PRECISION,
    bbox_max_lat DOUBLE PRECISION,
    bbox_max_lon DOUBLE PRECISION,

    -- Multispectral Bands (13 bands)
    band_1_coastal_aerosol DOUBLE PRECISION,
    band_2_blue DOUBLE PRECISION,
    band_3_green DOUBLE PRECISION,
    band_4_red DOUBLE PRECISION,
    band_8_nir DOUBLE PRECISION,
    band_11_swir1 DOUBLE PRECISION,
    band_12_swir2 DOUBLE PRECISION,

    -- Vegetation Indices
    ndvi DOUBLE PRECISION, -- Normalized Difference Vegetation Index
    nbr DOUBLE PRECISION,  -- Normalized Burn Ratio

    -- Quality
    cloud_cover_percent DOUBLE PRECISION,
    data_quality VARCHAR(20),

    -- Satellite
    satellite VARCHAR(20), -- Sentinel-2A, Sentinel-2B
    sensor VARCHAR(20) DEFAULT 'MSI',
    tile_id VARCHAR(10),
    orbit_number INTEGER,

    -- Processing
    processing_level VARCHAR(20), -- L1C, L2A

    -- Storage
    thumbnail_url TEXT,
    download_url TEXT,
    file_size_mb DOUBLE PRECISION,

    source VARCHAR(50) DEFAULT 'sat_sentinel2_msi',
    provider VARCHAR(100) DEFAULT 'ESA Copernicus',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_sentinel2_time ON sentinel2_msi_imagery(timestamp DESC);
CREATE INDEX idx_sentinel2_location ON sentinel2_msi_imagery(center_latitude, center_longitude);
CREATE INDEX idx_sentinel2_product ON sentinel2_msi_imagery(product_id);
CREATE INDEX idx_sentinel2_ndvi ON sentinel2_msi_imagery(ndvi);
CREATE INDEX idx_sentinel2_created ON sentinel2_msi_imagery(created_at DESC);

-- Sentinel-3 SLSTR Thermal Imagery
CREATE TABLE IF NOT EXISTS sentinel3_slstr_imagery (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    product_id VARCHAR(255) UNIQUE NOT NULL,

    -- Coverage
    center_latitude DOUBLE PRECISION,
    center_longitude DOUBLE PRECISION,
    bbox_min_lat DOUBLE PRECISION,
    bbox_min_lon DOUBLE PRECISION,
    bbox_max_lat DOUBLE PRECISION,
    bbox_max_lon DOUBLE PRECISION,

    -- Thermal Bands
    brightness_temperature_s7_k DOUBLE PRECISION, -- 3.7 μm
    brightness_temperature_s8_k DOUBLE PRECISION, -- 10.85 μm
    brightness_temperature_s9_k DOUBLE PRECISION, -- 12.0 μm

    -- Fire Detection
    fire_radiative_power_mw DOUBLE PRECISION,
    active_fire_flag BOOLEAN,

    -- Quality
    cloud_cover_percent DOUBLE PRECISION,
    data_quality VARCHAR(20),

    -- Satellite
    satellite VARCHAR(20), -- Sentinel-3A, Sentinel-3B
    sensor VARCHAR(20) DEFAULT 'SLSTR',
    orbit_number INTEGER,

    -- Processing
    processing_level VARCHAR(20),

    -- Storage
    thumbnail_url TEXT,
    download_url TEXT,
    file_size_mb DOUBLE PRECISION,

    source VARCHAR(50) DEFAULT 'sat_sentinel3_slstr',
    provider VARCHAR(100) DEFAULT 'ESA Copernicus',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_sentinel3_time ON sentinel3_slstr_imagery(timestamp DESC);
CREATE INDEX idx_sentinel3_location ON sentinel3_slstr_imagery(center_latitude, center_longitude);
CREATE INDEX idx_sentinel3_product ON sentinel3_slstr_imagery(product_id);
CREATE INDEX idx_sentinel3_fire ON sentinel3_slstr_imagery(active_fire_flag, timestamp DESC);
CREATE INDEX idx_sentinel3_created ON sentinel3_slstr_imagery(created_at DESC);

-- ============================================================================
-- 6. IoT SENSORS
-- ============================================================================

-- IoT Weather Stations
CREATE TABLE IF NOT EXISTS iot_weather_stations (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    device_id VARCHAR(100) NOT NULL,
    device_name VARCHAR(255),
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    elevation_m DOUBLE PRECISION,

    -- Temperature & Moisture
    temperature_celsius DOUBLE PRECISION,
    humidity_percent DOUBLE PRECISION,
    dewpoint_celsius DOUBLE PRECISION,

    -- Wind
    wind_speed_ms DOUBLE PRECISION,
    wind_gust_ms DOUBLE PRECISION,
    wind_direction_degrees INTEGER,

    -- Pressure
    pressure_pa DOUBLE PRECISION,

    -- Precipitation
    rainfall_mm DOUBLE PRECISION,
    rainfall_rate_mmh DOUBLE PRECISION,

    -- Solar
    solar_radiation_wm2 DOUBLE PRECISION,
    uv_index DOUBLE PRECISION,

    -- Battery & Status
    battery_voltage DOUBLE PRECISION,
    battery_percent DOUBLE PRECISION,
    signal_strength_dbm INTEGER,
    status VARCHAR(20),

    -- Quality
    data_quality DOUBLE PRECISION,

    source VARCHAR(50) DEFAULT 'iot_weather_stations',
    provider VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_iot_weather_device_time ON iot_weather_stations(device_id, timestamp DESC);
CREATE INDEX idx_iot_weather_timestamp ON iot_weather_stations(timestamp DESC);
CREATE INDEX idx_iot_weather_location ON iot_weather_stations(latitude, longitude);
CREATE INDEX idx_iot_weather_created ON iot_weather_stations(created_at DESC);

-- IoT Soil Moisture Sensors
CREATE TABLE IF NOT EXISTS iot_soil_moisture_sensors (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    device_id VARCHAR(100) NOT NULL,
    device_name VARCHAR(255),
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    elevation_m DOUBLE PRECISION,

    -- Soil Moisture (multiple depths)
    moisture_5cm_percent DOUBLE PRECISION,
    moisture_10cm_percent DOUBLE PRECISION,
    moisture_20cm_percent DOUBLE PRECISION,
    moisture_40cm_percent DOUBLE PRECISION,
    moisture_60cm_percent DOUBLE PRECISION,
    moisture_100cm_percent DOUBLE PRECISION,

    -- Soil Temperature
    soil_temp_5cm_celsius DOUBLE PRECISION,
    soil_temp_10cm_celsius DOUBLE PRECISION,
    soil_temp_20cm_celsius DOUBLE PRECISION,
    soil_temp_40cm_celsius DOUBLE PRECISION,

    -- Salinity
    salinity_ds_m DOUBLE PRECISION,

    -- Battery & Status
    battery_voltage DOUBLE PRECISION,
    battery_percent DOUBLE PRECISION,
    signal_strength_dbm INTEGER,
    status VARCHAR(20),

    -- Quality
    data_quality DOUBLE PRECISION,

    source VARCHAR(50) DEFAULT 'iot_soil_moisture_sensors',
    provider VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_iot_soil_device_time ON iot_soil_moisture_sensors(device_id, timestamp DESC);
CREATE INDEX idx_iot_soil_timestamp ON iot_soil_moisture_sensors(timestamp DESC);
CREATE INDEX idx_iot_soil_location ON iot_soil_moisture_sensors(latitude, longitude);
CREATE INDEX idx_iot_soil_created ON iot_soil_moisture_sensors(created_at DESC);

-- ============================================================================
-- 7. AIR QUALITY
-- ============================================================================

-- PurpleAir Sensors (PM2.5, temperature, humidity)
-- Note: Keep existing sensor_readings table for backward compatibility
-- Or migrate to this specialized table

-- AirNow Air Quality Observations
CREATE TABLE IF NOT EXISTS airnow_observations (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    station_id VARCHAR(100),
    station_name VARCHAR(255),
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,

    -- Air Quality Index
    aqi INTEGER,
    aqi_category VARCHAR(50), -- Good, Moderate, Unhealthy, etc.
    primary_pollutant VARCHAR(20), -- PM2.5, PM10, O3, etc.

    -- Pollutant Concentrations
    pm25_ugm3 DOUBLE PRECISION,
    pm10_ugm3 DOUBLE PRECISION,
    ozone_ppm DOUBLE PRECISION,
    co_ppm DOUBLE PRECISION,
    no2_ppb DOUBLE PRECISION,
    so2_ppb DOUBLE PRECISION,

    -- Health Messaging
    health_message TEXT,

    -- Reporting Agency
    agency_name VARCHAR(255),

    source VARCHAR(50) DEFAULT 'airnow_california',
    provider VARCHAR(100) DEFAULT 'EPA AirNow',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_airnow_station_time ON airnow_observations(station_id, timestamp DESC);
CREATE INDEX idx_airnow_timestamp ON airnow_observations(timestamp DESC);
CREATE INDEX idx_airnow_location ON airnow_observations(latitude, longitude);
CREATE INDEX idx_airnow_aqi ON airnow_observations(aqi DESC);
CREATE INDEX idx_airnow_created ON airnow_observations(created_at DESC);

-- ============================================================================
-- 8. SOURCE ROUTING TABLE
-- ============================================================================

-- Lookup table for efficient routing in kafka_consumer.py
CREATE TABLE IF NOT EXISTS data_source_routing (
    source_id VARCHAR(100) PRIMARY KEY,
    table_name VARCHAR(100) NOT NULL,
    description TEXT,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Populate routing table
INSERT INTO data_source_routing (source_id, table_name, description) VALUES
    -- Weather Stations
    ('wx_station_metar', 'metar_observations', 'METAR aviation weather observations'),
    ('noaa_stations_current', 'noaa_station_observations', 'NOAA weather station current observations'),

    -- Weather Model Forecasts
    ('wx_era5_land', 'era5_land_reanalysis', 'ERA5-Land high-resolution reanalysis'),
    ('wx_era5_reanalysis', 'era5_reanalysis', 'ERA5 global atmospheric reanalysis'),
    ('wx_gfs_forecast', 'gfs_forecasts', 'GFS Global Forecast System'),
    ('wx_nam_forecast', 'nam_forecasts', 'NAM North American Mesoscale'),

    -- Weather Alerts
    ('noaa_alerts_active', 'noaa_weather_alerts', 'NOAA active weather alerts'),
    ('noaa_gridpoints_forecast', 'noaa_gridpoint_forecast', 'NOAA gridpoint forecasts'),

    -- Fire Detection Satellites
    ('firms_viirs_snpp', 'firms_viirs_snpp_detections', 'VIIRS S-NPP fire detections'),
    ('firms_viirs_noaa20', 'firms_viirs_noaa20_detections', 'VIIRS NOAA-20 fire detections'),
    ('firms_viirs_noaa21', 'firms_viirs_noaa21_detections', 'VIIRS NOAA-21 fire detections'),
    ('firms_modis_terra', 'firms_modis_terra_detections', 'MODIS Terra fire detections'),
    ('firms_modis_aqua', 'firms_modis_aqua_detections', 'MODIS Aqua fire detections'),
    ('landsat_nrt', 'landsat_nrt_detections', 'Landsat near-real-time fire detections'),

    -- Satellite Imagery
    ('sat_landsat_thermal', 'landsat_thermal_imagery', 'Landsat thermal imagery metadata'),
    ('sat_sentinel2_msi', 'sentinel2_msi_imagery', 'Sentinel-2 MSI multispectral imagery'),
    ('sat_sentinel3_slstr', 'sentinel3_slstr_imagery', 'Sentinel-3 SLSTR thermal imagery'),

    -- IoT Sensors
    ('iot_weather_stations', 'iot_weather_stations', 'IoT weather station sensors'),
    ('iot_soil_moisture_sensors', 'iot_soil_moisture_sensors', 'IoT soil moisture sensors'),
    ('iot_air_quality_sensors', 'sensor_readings', 'IoT air quality sensors (PurpleAir)'),

    -- Air Quality
    ('purpleair_california', 'sensor_readings', 'PurpleAir air quality sensors'),
    ('airnow_california', 'airnow_observations', 'EPA AirNow air quality observations')
ON CONFLICT (source_id) DO NOTHING;

-- ============================================================================
-- CLEANUP: Mark old generic table for migration
-- ============================================================================

-- Rename old table (don't drop yet, for backward compatibility)
ALTER TABLE IF EXISTS weather_data RENAME TO weather_data_legacy;

-- ============================================================================
-- GRANT PERMISSIONS
-- ============================================================================

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO wildfire_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO wildfire_user;
