"""
TimescaleDB Time-series Data Management for Wildfire Intelligence
Optimized for high-frequency sensor data, weather measurements, and fire detection alerts
"""

import asyncio
import asyncpg
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple
import json
import uuid
from contextlib import asynccontextmanager
import structlog
import numpy as np
from statistics import mean, median, stdev

from ..config import get_settings
from .data_models import (
    StorageRequest, StorageResponse, BulkStorageRequest, QueryRequest, 
    QueryResponse, DataType, StorageBackend
)

logger = structlog.get_logger()


class TimeseriesManager:
    """Comprehensive TimescaleDB manager for time-series wildfire data"""
    
    def __init__(self, database_manager):
        self.settings = get_settings()
        self.db_manager = database_manager
        self.pool = None
        self.is_initialized = False
        
        # Time-series specific configurations
        self.compression_settings = {
            'weather': {'compress_after': '7 days', 'segment_by': 'source'},
            'sensor': {'compress_after': '3 days', 'segment_by': 'sensor_id'}, 
            'fire_detection': {'compress_after': '1 day', 'segment_by': 'satellite_sensor'},
            'predictions': {'compress_after': '1 day', 'segment_by': 'model_name'}
        }
        
        # Aggregation configurations for different time intervals
        self.aggregation_intervals = ['1 minute', '5 minutes', '15 minutes', '1 hour', '1 day']
        
    async def initialize(self):
        """Initialize TimescaleDB connection and hypertables"""
        try:
            logger.info("Initializing TimescaleDB manager")
            
            # Create separate connection pool for TimescaleDB
            self.pool = await asyncpg.create_pool(
                self.settings.timescale_url,
                min_size=10,
                max_size=self.settings.db_pool_size + 10,  # More connections for time-series
                max_queries=100000,  # Higher for time-series workloads
                max_inactive_connection_lifetime=300,
                command_timeout=self.settings.query_timeout_seconds
            )
            
            # Initialize TimescaleDB schema and hypertables
            await self._initialize_timescale_schema()
            
            # Setup continuous aggregates for performance
            await self._setup_continuous_aggregates()
            
            # Setup data retention policies
            await self._setup_retention_policies()
            
            # Setup compression policies
            await self._setup_compression_policies()
            
            self.is_initialized = True
            logger.info("TimescaleDB manager initialized successfully")
            
        except Exception as e:
            logger.error("TimescaleDB initialization failed", error=str(e))
            raise
    
    async def cleanup(self):
        """Cleanup TimescaleDB connections"""
        if self.pool:
            await self.pool.close()
            logger.info("TimescaleDB connections closed")
    
    @asynccontextmanager
    async def get_connection(self):
        """Get TimescaleDB connection from pool"""
        if not self.is_initialized:
            await self.initialize()
            
        async with self.pool.acquire() as connection:
            yield connection
    
    async def _initialize_timescale_schema(self):
        """Initialize TimescaleDB hypertables and schema"""
        async with self.get_connection() as conn:
            
            # Enable TimescaleDB extension
            await conn.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")
            await conn.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
            
            # Weather time-series hypertable
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS ts_weather_data (
                    time TIMESTAMPTZ NOT NULL,
                    location GEOGRAPHY(POINT),
                    source VARCHAR(100) NOT NULL,
                    station_id VARCHAR(100),
                    temperature REAL,
                    feels_like REAL,
                    humidity REAL,
                    dew_point REAL,
                    pressure REAL,
                    sea_level_pressure REAL,
                    wind_speed REAL,
                    wind_direction INTEGER,
                    wind_gust REAL,
                    precipitation REAL,
                    precipitation_1h REAL,
                    precipitation_3h REAL,
                    snow_depth REAL,
                    visibility REAL,
                    cloud_cover INTEGER,
                    uv_index INTEGER,
                    solar_radiation REAL,
                    evapotranspiration REAL,
                    soil_temperature REAL,
                    soil_moisture REAL,
                    fire_weather_index REAL,
                    drought_index REAL,
                    quality_score REAL,
                    forecast_model VARCHAR(50),
                    forecast_horizon_hours INTEGER,
                    raw_data JSONB,
                    
                    -- Constraints for data quality
                    CONSTRAINT valid_humidity CHECK (humidity >= 0 AND humidity <= 100),
                    CONSTRAINT valid_wind_direction CHECK (wind_direction >= 0 AND wind_direction <= 360),
                    CONSTRAINT valid_quality_score CHECK (quality_score >= 0 AND quality_score <= 1),
                    CONSTRAINT valid_cloud_cover CHECK (cloud_cover >= 0 AND cloud_cover <= 100),
                    CONSTRAINT valid_uv_index CHECK (uv_index >= 0 AND uv_index <= 15)
                )
            """)
            
            # Create hypertable if it doesn't exist
            try:
                await conn.execute("SELECT create_hypertable('ts_weather_data', 'time', if_not_exists => TRUE)")
            except Exception as e:
                if "already exists" not in str(e):
                    logger.warning("Failed to create weather hypertable", error=str(e))
            
            # Sensor time-series hypertable  
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS ts_sensor_data (
                    time TIMESTAMPTZ NOT NULL,
                    sensor_id VARCHAR(100) NOT NULL,
                    location GEOGRAPHY(POINT),
                    sensor_type VARCHAR(50) NOT NULL,
                    network VARCHAR(50),
                    deployment_type VARCHAR(50),
                    
                    -- Air quality measurements
                    pm25 REAL,
                    pm10 REAL,
                    pm1 REAL,
                    no2 REAL,
                    so2 REAL,
                    co REAL,
                    o3 REAL,
                    nh3 REAL,
                    h2s REAL,
                    tvoc REAL,
                    aqi INTEGER,
                    
                    -- Environmental measurements
                    temperature REAL,
                    humidity REAL,
                    pressure REAL,
                    noise_level REAL,
                    light_intensity REAL,
                    
                    -- Soil and vegetation
                    soil_moisture REAL,
                    soil_temperature REAL,
                    soil_ph REAL,
                    leaf_wetness REAL,
                    
                    -- Fire-specific sensors
                    smoke_density REAL,
                    flame_detected BOOLEAN,
                    heat_index REAL,
                    infrared_temp REAL,
                    
                    -- System health
                    battery_voltage REAL,
                    battery_percentage REAL,
                    signal_strength INTEGER,
                    data_transmission_rate REAL,
                    last_maintenance TIMESTAMPTZ,
                    status VARCHAR(20) DEFAULT 'active',
                    error_codes INTEGER[],
                    
                    quality_score REAL,
                    raw_measurements JSONB,
                    calibration_data JSONB,
                    
                    -- Constraints
                    CONSTRAINT valid_aqi CHECK (aqi >= 0 AND aqi <= 500),
                    CONSTRAINT valid_signal CHECK (signal_strength >= -150 AND signal_strength <= 0),
                    CONSTRAINT valid_battery CHECK (battery_percentage >= 0 AND battery_percentage <= 100),
                    CONSTRAINT valid_status CHECK (status IN ('active', 'inactive', 'maintenance', 'error', 'calibrating'))
                )
            """)
            
            try:
                await conn.execute("SELECT create_hypertable('ts_sensor_data', 'time', 'sensor_id', 2, if_not_exists => TRUE)")
            except Exception as e:
                if "already exists" not in str(e):
                    logger.warning("Failed to create sensor hypertable", error=str(e))
            
            # Fire detection time-series hypertable
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS ts_fire_detection (
                    time TIMESTAMPTZ NOT NULL,
                    location GEOGRAPHY(POINT) NOT NULL,
                    detection_id UUID DEFAULT gen_random_uuid(),
                    satellite_sensor VARCHAR(50) NOT NULL,
                    satellite_pass VARCHAR(100),
                    scan_angle REAL,
                    
                    -- Fire characteristics
                    confidence_level REAL NOT NULL,
                    brightness_temp_k REAL,
                    brightness_temp_c REAL,
                    brightness_temp_31 REAL,
                    fire_radiative_power REAL,
                    estimated_area_m2 REAL,
                    estimated_area_hectares REAL,
                    fire_intensity VARCHAR(20),
                    fire_type VARCHAR(50),
                    fuel_type VARCHAR(50),
                    
                    -- Detection quality
                    pixel_count INTEGER,
                    cloud_cover_percent INTEGER,
                    atmospheric_correction BOOLEAN,
                    terrain_correction BOOLEAN,
                    adjacent_water BOOLEAN,
                    adjacent_cloud BOOLEAN,
                    
                    -- Classification and validation
                    detection_algorithm VARCHAR(50),
                    validation_method VARCHAR(50),
                    verification_status VARCHAR(20) DEFAULT 'unverified',
                    false_positive_probability REAL,
                    
                    -- Risk assessment
                    threat_level VARCHAR(20) DEFAULT 'medium',
                    evacuation_priority INTEGER,
                    response_required BOOLEAN DEFAULT FALSE,
                    estimated_spread_rate REAL,
                    weather_risk_factor REAL,
                    
                    -- Related incidents
                    incident_id UUID,
                    cluster_id UUID,
                    related_detections UUID[],
                    
                    processing_timestamp TIMESTAMPTZ DEFAULT NOW(),
                    raw_detection_data JSONB,
                    
                    -- Constraints
                    CONSTRAINT valid_confidence CHECK (confidence_level >= 0 AND confidence_level <= 100),
                    CONSTRAINT valid_verification CHECK (verification_status IN ('unverified', 'verified', 'false_positive', 'under_review')),
                    CONSTRAINT valid_threat_level CHECK (threat_level IN ('low', 'medium', 'high', 'critical', 'extreme')),
                    CONSTRAINT valid_cloud_cover CHECK (cloud_cover_percent >= 0 AND cloud_cover_percent <= 100),
                    CONSTRAINT valid_evacuation_priority CHECK (evacuation_priority >= 1 AND evacuation_priority <= 10)
                )
            """)
            
            try:
                await conn.execute("SELECT create_hypertable('ts_fire_detection', 'time', if_not_exists => TRUE)")
            except Exception as e:
                if "already exists" not in str(e):
                    logger.warning("Failed to create fire detection hypertable", error=str(e))
            
            # Prediction time-series hypertable
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS ts_predictions (
                    time TIMESTAMPTZ NOT NULL,
                    prediction_time TIMESTAMPTZ NOT NULL,
                    forecast_time TIMESTAMPTZ NOT NULL,
                    location GEOGRAPHY(POINT),
                    region_bounds GEOGRAPHY(POLYGON),
                    
                    -- Model information
                    model_name VARCHAR(100) NOT NULL,
                    model_version VARCHAR(50),
                    model_type VARCHAR(50),
                    ensemble_member INTEGER,
                    
                    -- Prediction types and values
                    prediction_type VARCHAR(50) NOT NULL,
                    fire_risk_score REAL,
                    fire_probability REAL,
                    fire_intensity_prediction REAL,
                    expected_burned_area REAL,
                    spread_direction_degrees INTEGER,
                    spread_rate_mh REAL,
                    containment_difficulty REAL,
                    
                    -- Weather predictions
                    temp_forecast REAL,
                    humidity_forecast REAL,
                    wind_speed_forecast REAL,
                    wind_direction_forecast INTEGER,
                    precipitation_forecast REAL,
                    
                    -- Risk factors
                    drought_conditions REAL,
                    vegetation_dryness REAL,
                    fuel_moisture_content REAL,
                    topographic_risk_factor REAL,
                    human_activity_risk REAL,
                    lightning_probability REAL,
                    
                    -- Confidence and uncertainty
                    prediction_confidence REAL,
                    uncertainty_range REAL,
                    skill_score REAL,
                    bias_correction_applied BOOLEAN,
                    
                    -- Operational recommendations
                    alert_level VARCHAR(20),
                    resource_allocation_priority INTEGER,
                    evacuation_recommendation VARCHAR(50),
                    fire_suppression_strategy JSONB,
                    
                    -- Model performance tracking
                    hindcast_accuracy REAL,
                    cross_validation_score REAL,
                    feature_importance JSONB,
                    model_inputs JSONB,
                    raw_prediction_output JSONB,
                    
                    -- Constraints
                    CONSTRAINT valid_fire_risk CHECK (fire_risk_score >= 0 AND fire_risk_score <= 100),
                    CONSTRAINT valid_fire_probability CHECK (fire_probability >= 0 AND fire_probability <= 1),
                    CONSTRAINT valid_prediction_confidence CHECK (prediction_confidence >= 0 AND prediction_confidence <= 1),
                    CONSTRAINT valid_alert_level CHECK (alert_level IN ('none', 'low', 'moderate', 'high', 'extreme')),
                    CONSTRAINT valid_spread_direction CHECK (spread_direction_degrees >= 0 AND spread_direction_degrees <= 360),
                    CONSTRAINT forecast_time_logical CHECK (forecast_time >= prediction_time)
                )
            """)
            
            try:
                await conn.execute("SELECT create_hypertable('ts_predictions', 'time', if_not_exists => TRUE)")
            except Exception as e:
                if "already exists" not in str(e):
                    logger.warning("Failed to create predictions hypertable", error=str(e))
            
            # Create space-time indexes for geospatial queries
            await self._create_spacetime_indexes()
            
            logger.info("TimescaleDB schema initialized successfully")
    
    async def _create_spacetime_indexes(self):
        """Create specialized indexes for space-time queries"""
        async with self.get_connection() as conn:
            
            # Weather data indexes
            await conn.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ts_weather_location_time ON ts_weather_data USING GIST (location, time)")
            await conn.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ts_weather_source ON ts_weather_data (source, time DESC)")
            await conn.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ts_weather_station ON ts_weather_data (station_id, time DESC)")
            await conn.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ts_weather_fire_index ON ts_weather_data (fire_weather_index, time DESC) WHERE fire_weather_index IS NOT NULL")
            await conn.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ts_weather_forecast ON ts_weather_data (forecast_model, forecast_horizon_hours, time DESC)")
            
            # Sensor data indexes
            await conn.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ts_sensor_id_time ON ts_sensor_data (sensor_id, time DESC)")
            await conn.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ts_sensor_location_time ON ts_sensor_data USING GIST (location, time)")
            await conn.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ts_sensor_type ON ts_sensor_data (sensor_type, time DESC)")
            await conn.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ts_sensor_status ON ts_sensor_data (status, time DESC)")
            await conn.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ts_sensor_aqi ON ts_sensor_data (aqi, time DESC) WHERE aqi IS NOT NULL")
            await conn.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ts_sensor_pm25 ON ts_sensor_data (pm25, time DESC) WHERE pm25 IS NOT NULL")
            await conn.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ts_sensor_network ON ts_sensor_data (network, time DESC)")
            
            # Fire detection indexes  
            await conn.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ts_fire_location_time ON ts_fire_detection USING GIST (location, time)")
            await conn.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ts_fire_sensor ON ts_fire_detection (satellite_sensor, time DESC)")
            await conn.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ts_fire_confidence ON ts_fire_detection (confidence_level, time DESC)")
            await conn.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ts_fire_threat ON ts_fire_detection (threat_level, time DESC)")
            await conn.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ts_fire_verification ON ts_fire_detection (verification_status, time DESC)")
            await conn.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ts_fire_response ON ts_fire_detection (response_required, time DESC) WHERE response_required = TRUE")
            await conn.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ts_fire_cluster ON ts_fire_detection (cluster_id, time DESC) WHERE cluster_id IS NOT NULL")
            await conn.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ts_fire_incident ON ts_fire_detection (incident_id, time DESC) WHERE incident_id IS NOT NULL")
            
            # Prediction indexes
            await conn.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ts_predictions_model ON ts_predictions (model_name, time DESC)")
            await conn.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ts_predictions_location ON ts_predictions USING GIST (location, time)")
            await conn.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ts_predictions_type ON ts_predictions (prediction_type, time DESC)")
            await conn.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ts_predictions_forecast ON ts_predictions (forecast_time, prediction_time)")
            await conn.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ts_predictions_risk ON ts_predictions (fire_risk_score, time DESC) WHERE fire_risk_score IS NOT NULL")
            await conn.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ts_predictions_alert ON ts_predictions (alert_level, time DESC)")
            await conn.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ts_predictions_region ON ts_predictions USING GIST (region_bounds, time)")
            
            logger.info("Space-time indexes created successfully")
    
    async def _setup_continuous_aggregates(self):
        """Setup continuous aggregates for common query patterns"""
        async with self.get_connection() as conn:
            
            # Hourly weather aggregates
            try:
                await conn.execute("""
                    CREATE MATERIALIZED VIEW IF NOT EXISTS weather_hourly
                    WITH (timescaledb.continuous) AS
                    SELECT 
                        time_bucket('1 hour', time) AS bucket,
                        source,
                        station_id,
                        ST_X(location::geometry) as longitude,
                        ST_Y(location::geometry) as latitude,
                        AVG(temperature) as avg_temperature,
                        MAX(temperature) as max_temperature,
                        MIN(temperature) as min_temperature,
                        AVG(humidity) as avg_humidity,
                        AVG(pressure) as avg_pressure,
                        AVG(wind_speed) as avg_wind_speed,
                        MAX(wind_speed) as max_wind_speed,
                        AVG(wind_direction) as avg_wind_direction,
                        SUM(precipitation) as total_precipitation,
                        AVG(fire_weather_index) as avg_fire_weather_index,
                        MAX(fire_weather_index) as max_fire_weather_index,
                        COUNT(*) as measurement_count
                    FROM ts_weather_data
                    WHERE time > INTERVAL '1 week' AGO
                    GROUP BY bucket, source, station_id, longitude, latitude
                """)
                
                # Create refresh policy
                await conn.execute("""
                    SELECT add_continuous_aggregate_policy('weather_hourly',
                        start_offset => INTERVAL '1 day',
                        end_offset => INTERVAL '1 hour',
                        schedule_interval => INTERVAL '1 hour')
                """)
            except Exception as e:
                if "already exists" not in str(e):
                    logger.warning("Failed to create weather hourly aggregates", error=str(e))
            
            # Daily weather aggregates
            try:
                await conn.execute("""
                    CREATE MATERIALIZED VIEW IF NOT EXISTS weather_daily
                    WITH (timescaledb.continuous) AS
                    SELECT 
                        time_bucket('1 day', time) AS bucket,
                        source,
                        ST_X(location::geometry) as longitude,
                        ST_Y(location::geometry) as latitude,
                        AVG(temperature) as avg_temperature,
                        MAX(temperature) as max_temperature,
                        MIN(temperature) as min_temperature,
                        AVG(humidity) as avg_humidity,
                        MAX(wind_speed) as max_wind_speed,
                        SUM(precipitation) as total_precipitation,
                        AVG(fire_weather_index) as avg_fire_weather_index,
                        MAX(fire_weather_index) as max_fire_weather_index,
                        COUNT(*) as measurement_count
                    FROM ts_weather_data
                    WHERE time > INTERVAL '1 month' AGO
                    GROUP BY bucket, source, longitude, latitude
                """)
                
                await conn.execute("""
                    SELECT add_continuous_aggregate_policy('weather_daily',
                        start_offset => INTERVAL '1 week',
                        end_offset => INTERVAL '1 day',
                        schedule_interval => INTERVAL '1 day')
                """)
            except Exception as e:
                if "already exists" not in str(e):
                    logger.warning("Failed to create weather daily aggregates", error=str(e))
            
            # Hourly sensor aggregates
            try:
                await conn.execute("""
                    CREATE MATERIALIZED VIEW IF NOT EXISTS sensor_hourly
                    WITH (timescaledb.continuous) AS
                    SELECT 
                        time_bucket('1 hour', time) AS bucket,
                        sensor_id,
                        sensor_type,
                        network,
                        ST_X(location::geometry) as longitude,
                        ST_Y(location::geometry) as latitude,
                        AVG(pm25) as avg_pm25,
                        MAX(pm25) as max_pm25,
                        AVG(pm10) as avg_pm10,
                        MAX(pm10) as max_pm10,
                        AVG(temperature) as avg_temperature,
                        AVG(humidity) as avg_humidity,
                        AVG(aqi) as avg_aqi,
                        MAX(aqi) as max_aqi,
                        AVG(battery_percentage) as avg_battery,
                        COUNT(*) as measurement_count,
                        COUNT(*) FILTER (WHERE status = 'active') as active_count
                    FROM ts_sensor_data
                    WHERE time > INTERVAL '1 week' AGO
                    GROUP BY bucket, sensor_id, sensor_type, network, longitude, latitude
                """)
                
                await conn.execute("""
                    SELECT add_continuous_aggregate_policy('sensor_hourly',
                        start_offset => INTERVAL '1 day',
                        end_offset => INTERVAL '1 hour', 
                        schedule_interval => INTERVAL '1 hour')
                """)
            except Exception as e:
                if "already exists" not in str(e):
                    logger.warning("Failed to create sensor hourly aggregates", error=str(e))
            
            # Fire detection daily summaries
            try:
                await conn.execute("""
                    CREATE MATERIALIZED VIEW IF NOT EXISTS fire_detection_daily
                    WITH (timescaledb.continuous) AS
                    SELECT 
                        time_bucket('1 day', time) AS bucket,
                        satellite_sensor,
                        COUNT(*) as total_detections,
                        COUNT(*) FILTER (WHERE confidence_level > 80) as high_confidence_detections,
                        COUNT(*) FILTER (WHERE verification_status = 'verified') as verified_detections,
                        COUNT(*) FILTER (WHERE threat_level IN ('high', 'critical', 'extreme')) as high_threat_detections,
                        COUNT(*) FILTER (WHERE response_required = TRUE) as response_required_count,
                        AVG(confidence_level) as avg_confidence,
                        AVG(fire_radiative_power) as avg_frp,
                        SUM(estimated_area_hectares) as total_estimated_area,
                        COUNT(DISTINCT cluster_id) FILTER (WHERE cluster_id IS NOT NULL) as unique_fire_clusters
                    FROM ts_fire_detection
                    WHERE time > INTERVAL '1 month' AGO
                    GROUP BY bucket, satellite_sensor
                """)
                
                await conn.execute("""
                    SELECT add_continuous_aggregate_policy('fire_detection_daily',
                        start_offset => INTERVAL '1 week',
                        end_offset => INTERVAL '1 day',
                        schedule_interval => INTERVAL '1 day')
                """)
            except Exception as e:
                if "already exists" not in str(e):
                    logger.warning("Failed to create fire detection daily aggregates", error=str(e))
            
            logger.info("Continuous aggregates setup completed")
    
    async def _setup_retention_policies(self):
        """Setup automated data retention policies"""
        async with self.get_connection() as conn:
            
            try:
                # Weather data retention - keep detailed data for configured period
                await conn.execute(f"""
                    SELECT add_retention_policy('ts_weather_data', INTERVAL '{self.settings.weather_data_retention_days} days');
                """)
            except Exception as e:
                if "already exists" not in str(e):
                    logger.warning("Failed to create weather retention policy", error=str(e))
            
            try:
                # Sensor data retention
                await conn.execute(f"""
                    SELECT add_retention_policy('ts_sensor_data', INTERVAL '{self.settings.sensor_data_retention_days} days');
                """)
            except Exception as e:
                if "already exists" not in str(e):
                    logger.warning("Failed to create sensor retention policy", error=str(e))
            
            try:
                # Fire detection data retention - keep longer for analysis
                await conn.execute(f"""
                    SELECT add_retention_policy('ts_fire_detection', INTERVAL '{self.settings.fire_detection_retention_days} days');
                """)
            except Exception as e:
                if "already exists" not in str(e):
                    logger.warning("Failed to create fire detection retention policy", error=str(e))
            
            try:
                # Prediction data retention
                await conn.execute(f"""
                    SELECT add_retention_policy('ts_predictions', INTERVAL '{self.settings.prediction_data_retention_days} days');
                """)
            except Exception as e:
                if "already exists" not in str(e):
                    logger.warning("Failed to create prediction retention policy", error=str(e))
            
            logger.info("Data retention policies setup completed")
    
    async def _setup_compression_policies(self):
        """Setup automated compression policies for older data"""
        async with self.get_connection() as conn:
            
            for table_name, config in self.compression_settings.items():
                try:
                    ts_table = f"ts_{table_name}_data" if table_name != "fire_detection" else "ts_fire_detection"
                    if table_name == "predictions":
                        ts_table = "ts_predictions"
                    
                    # Enable compression
                    await conn.execute(f"""
                        ALTER TABLE {ts_table} SET (
                            timescaledb.compress,
                            timescaledb.compress_segmentby = '{config['segment_by']}'
                        );
                    """)
                    
                    # Add compression policy
                    await conn.execute(f"""
                        SELECT add_compression_policy('{ts_table}', INTERVAL '{config['compress_after']}');
                    """)
                    
                    logger.info(f"Compression policy setup for {ts_table}")
                    
                except Exception as e:
                    if "already exists" not in str(e) and "already enabled" not in str(e):
                        logger.warning(f"Failed to setup compression for {ts_table}", error=str(e))
            
            logger.info("Compression policies setup completed")
    
    async def store(self, request: StorageRequest) -> StorageResponse:
        """Store time-series data in appropriate hypertable"""
        async with self.get_connection() as conn:
            
            storage_id = str(uuid.uuid4())
            
            # Route to appropriate hypertable based on data type
            if request.data_type == DataType.WEATHER:
                await self._store_weather_timeseries(conn, request.data, storage_id)
            elif request.data_type == DataType.SENSOR:
                await self._store_sensor_timeseries(conn, request.data, storage_id)
            elif request.data_type == DataType.FIRE_DETECTION:
                await self._store_fire_detection_timeseries(conn, request.data, storage_id)
            elif request.data_type == DataType.PREDICTIONS:
                await self._store_predictions_timeseries(conn, request.data, storage_id)
            else:
                raise ValueError(f"Unsupported time-series data type: {request.data_type}")
            
            return StorageResponse(
                storage_id=storage_id,
                data_type=request.data_type,
                backend=StorageBackend.TIMESCALE,
                size_bytes=len(str(request.data)),
                timestamp=datetime.now()
            )
    
    async def store_bulk(self, request: BulkStorageRequest) -> List[StorageResponse]:
        """Efficiently store bulk time-series data"""
        async with self.get_connection() as conn:
            
            # Use transaction for bulk insert
            async with conn.transaction():
                responses = []
                
                # Process in optimized batches
                batch_size = min(self.settings.batch_insert_size, 5000)  # Larger batches for time-series
                
                for i in range(0, len(request.data_items), batch_size):
                    batch = request.data_items[i:i+batch_size]
                    batch_id = str(uuid.uuid4())
                    
                    # Bulk insert based on data type
                    if request.data_type == DataType.WEATHER:
                        await self._bulk_insert_weather(conn, batch, batch_id)
                    elif request.data_type == DataType.SENSOR:
                        await self._bulk_insert_sensor(conn, batch, batch_id)
                    elif request.data_type == DataType.FIRE_DETECTION:
                        await self._bulk_insert_fire_detection(conn, batch, batch_id)
                    elif request.data_type == DataType.PREDICTIONS:
                        await self._bulk_insert_predictions(conn, batch, batch_id)
                    
                    # Create responses for batch
                    for item in batch:
                        responses.append(StorageResponse(
                            storage_id=f"{batch_id}_{i}",
                            data_type=request.data_type,
                            backend=StorageBackend.TIMESCALE,
                            size_bytes=len(str(item)),
                            timestamp=datetime.now()
                        ))
                
                return responses
    
    async def _store_weather_timeseries(self, conn, data: Union[Dict, List], storage_id: str):
        """Store weather data in TimescaleDB hypertable"""
        data_items = data if isinstance(data, list) else [data]
        
        for item in data_items:
            location = None
            if 'latitude' in item and 'longitude' in item:
                location = f"POINT({item['longitude']} {item['latitude']})"
            
            await conn.execute("""
                INSERT INTO ts_weather_data (
                    time, location, source, station_id, temperature, feels_like, humidity, 
                    dew_point, pressure, sea_level_pressure, wind_speed, wind_direction, 
                    wind_gust, precipitation, precipitation_1h, precipitation_3h, snow_depth,
                    visibility, cloud_cover, uv_index, solar_radiation, evapotranspiration,
                    soil_temperature, soil_moisture, fire_weather_index, drought_index,
                    quality_score, forecast_model, forecast_horizon_hours, raw_data
                ) VALUES (
                    $1, ST_GeogFromText($2), $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, 
                    $14, $15, $16, $17, $18, $19, $20, $21, $22, $23, $24, $25, $26, $27, $28, $29, $30
                )
            """,
                item.get('timestamp', datetime.now()),
                location,
                item.get('source', 'unknown'),
                item.get('station_id'),
                item.get('temperature'),
                item.get('feels_like'),
                item.get('humidity'),
                item.get('dew_point'),
                item.get('pressure'),
                item.get('sea_level_pressure'),
                item.get('wind_speed'),
                item.get('wind_direction'),
                item.get('wind_gust'),
                item.get('precipitation'),
                item.get('precipitation_1h'),
                item.get('precipitation_3h'),
                item.get('snow_depth'),
                item.get('visibility'),
                item.get('cloud_cover'),
                item.get('uv_index'),
                item.get('solar_radiation'),
                item.get('evapotranspiration'),
                item.get('soil_temperature'),
                item.get('soil_moisture'),
                item.get('fire_weather_index'),
                item.get('drought_index'),
                item.get('quality_score'),
                item.get('forecast_model'),
                item.get('forecast_horizon_hours'),
                json.dumps(item)
            )
    
    async def _bulk_insert_weather(self, conn, batch: List[Dict], batch_id: str):
        """Bulk insert weather data for better performance"""
        
        # Prepare data for bulk insert
        insert_data = []
        for item in batch:
            location = None
            if 'latitude' in item and 'longitude' in item:
                location = f"POINT({item['longitude']} {item['latitude']})"
            
            insert_data.append((
                item.get('timestamp', datetime.now()),
                location,
                item.get('source', 'unknown'),
                item.get('station_id'),
                item.get('temperature'),
                item.get('feels_like'),
                item.get('humidity'),
                item.get('dew_point'),
                item.get('pressure'),
                item.get('sea_level_pressure'),
                item.get('wind_speed'),
                item.get('wind_direction'),
                item.get('wind_gust'),
                item.get('precipitation'),
                item.get('precipitation_1h'),
                item.get('precipitation_3h'),
                item.get('snow_depth'),
                item.get('visibility'),
                item.get('cloud_cover'),
                item.get('uv_index'),
                item.get('solar_radiation'),
                item.get('evapotranspiration'),
                item.get('soil_temperature'),
                item.get('soil_moisture'),
                item.get('fire_weather_index'),
                item.get('drought_index'),
                item.get('quality_score'),
                item.get('forecast_model'),
                item.get('forecast_horizon_hours'),
                json.dumps(item)
            ))
        
        # Use COPY for maximum performance
        await conn.copy_records_to_table(
            'ts_weather_data',
            records=insert_data,
            columns=[
                'time', 'location', 'source', 'station_id', 'temperature', 'feels_like', 
                'humidity', 'dew_point', 'pressure', 'sea_level_pressure', 'wind_speed', 
                'wind_direction', 'wind_gust', 'precipitation', 'precipitation_1h', 
                'precipitation_3h', 'snow_depth', 'visibility', 'cloud_cover', 'uv_index',
                'solar_radiation', 'evapotranspiration', 'soil_temperature', 'soil_moisture',
                'fire_weather_index', 'drought_index', 'quality_score', 'forecast_model',
                'forecast_horizon_hours', 'raw_data'
            ]
        )
    
    async def _store_sensor_timeseries(self, conn, data: Union[Dict, List], storage_id: str):
        """Store sensor data in TimescaleDB hypertable"""
        data_items = data if isinstance(data, list) else [data]
        
        for item in data_items:
            location = None
            if 'latitude' in item and 'longitude' in item:
                location = f"POINT({item['longitude']} {item['latitude']})"
            
            await conn.execute("""
                INSERT INTO ts_sensor_data (
                    time, sensor_id, location, sensor_type, network, deployment_type,
                    pm25, pm10, pm1, no2, so2, co, o3, nh3, h2s, tvoc, aqi,
                    temperature, humidity, pressure, noise_level, light_intensity,
                    soil_moisture, soil_temperature, soil_ph, leaf_wetness,
                    smoke_density, flame_detected, heat_index, infrared_temp,
                    battery_voltage, battery_percentage, signal_strength, 
                    data_transmission_rate, last_maintenance, status, error_codes,
                    quality_score, raw_measurements, calibration_data
                ) VALUES (
                    $1, $2, ST_GeogFromText($3), $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, 
                    $14, $15, $16, $17, $18, $19, $20, $21, $22, $23, $24, $25, $26, $27, $28,
                    $29, $30, $31, $32, $33, $34, $35, $36, $37, $38, $39, $40
                )
            """,
                item.get('timestamp', datetime.now()),
                item.get('sensor_id', 'unknown'),
                location,
                item.get('sensor_type', 'unknown'),
                item.get('network'),
                item.get('deployment_type'),
                item.get('pm25'),
                item.get('pm10'),
                item.get('pm1'),
                item.get('no2'),
                item.get('so2'),
                item.get('co'),
                item.get('o3'),
                item.get('nh3'),
                item.get('h2s'),
                item.get('tvoc'),
                item.get('aqi'),
                item.get('temperature'),
                item.get('humidity'),
                item.get('pressure'),
                item.get('noise_level'),
                item.get('light_intensity'),
                item.get('soil_moisture'),
                item.get('soil_temperature'),
                item.get('soil_ph'),
                item.get('leaf_wetness'),
                item.get('smoke_density'),
                item.get('flame_detected'),
                item.get('heat_index'),
                item.get('infrared_temp'),
                item.get('battery_voltage'),
                item.get('battery_percentage'),
                item.get('signal_strength'),
                item.get('data_transmission_rate'),
                item.get('last_maintenance'),
                item.get('status', 'active'),
                item.get('error_codes', []),
                item.get('quality_score'),
                json.dumps(item.get('measurements', {})),
                json.dumps(item.get('calibration_data', {}))
            )
    
    async def _bulk_insert_sensor(self, conn, batch: List[Dict], batch_id: str):
        """Bulk insert sensor data for better performance"""
        
        insert_data = []
        for item in batch:
            location = None
            if 'latitude' in item and 'longitude' in item:
                location = f"POINT({item['longitude']} {item['latitude']})"
            
            insert_data.append((
                item.get('timestamp', datetime.now()),
                item.get('sensor_id', 'unknown'),
                location,
                item.get('sensor_type', 'unknown'),
                item.get('network'),
                item.get('deployment_type'),
                item.get('pm25'),
                item.get('pm10'),
                item.get('pm1'),
                item.get('no2'),
                item.get('so2'),
                item.get('co'),
                item.get('o3'),
                item.get('nh3'),
                item.get('h2s'),
                item.get('tvoc'),
                item.get('aqi'),
                item.get('temperature'),
                item.get('humidity'),
                item.get('pressure'),
                item.get('noise_level'),
                item.get('light_intensity'),
                item.get('soil_moisture'),
                item.get('soil_temperature'),
                item.get('soil_ph'),
                item.get('leaf_wetness'),
                item.get('smoke_density'),
                item.get('flame_detected'),
                item.get('heat_index'),
                item.get('infrared_temp'),
                item.get('battery_voltage'),
                item.get('battery_percentage'),
                item.get('signal_strength'),
                item.get('data_transmission_rate'),
                item.get('last_maintenance'),
                item.get('status', 'active'),
                item.get('error_codes', []),
                item.get('quality_score'),
                json.dumps(item.get('measurements', {})),
                json.dumps(item.get('calibration_data', {}))
            ))
        
        await conn.copy_records_to_table(
            'ts_sensor_data',
            records=insert_data,
            columns=[
                'time', 'sensor_id', 'location', 'sensor_type', 'network', 'deployment_type',
                'pm25', 'pm10', 'pm1', 'no2', 'so2', 'co', 'o3', 'nh3', 'h2s', 'tvoc', 'aqi',
                'temperature', 'humidity', 'pressure', 'noise_level', 'light_intensity',
                'soil_moisture', 'soil_temperature', 'soil_ph', 'leaf_wetness',
                'smoke_density', 'flame_detected', 'heat_index', 'infrared_temp',
                'battery_voltage', 'battery_percentage', 'signal_strength', 
                'data_transmission_rate', 'last_maintenance', 'status', 'error_codes',
                'quality_score', 'raw_measurements', 'calibration_data'
            ]
        )
    
    async def _store_fire_detection_timeseries(self, conn, data: Union[Dict, List], storage_id: str):
        """Store fire detection data in TimescaleDB hypertable"""
        data_items = data if isinstance(data, list) else [data]
        
        for item in data_items:
            location = f"POINT({item['longitude']} {item['latitude']})"
            
            await conn.execute("""
                INSERT INTO ts_fire_detection (
                    time, location, detection_id, satellite_sensor, satellite_pass, scan_angle,
                    confidence_level, brightness_temp_k, brightness_temp_c, brightness_temp_31,
                    fire_radiative_power, estimated_area_m2, estimated_area_hectares,
                    fire_intensity, fire_type, fuel_type, pixel_count, cloud_cover_percent,
                    atmospheric_correction, terrain_correction, adjacent_water, adjacent_cloud,
                    detection_algorithm, validation_method, verification_status, 
                    false_positive_probability, threat_level, evacuation_priority,
                    response_required, estimated_spread_rate, weather_risk_factor,
                    incident_id, cluster_id, related_detections, raw_detection_data
                ) VALUES (
                    $1, ST_GeogFromText($2), $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13,
                    $14, $15, $16, $17, $18, $19, $20, $21, $22, $23, $24, $25, $26, $27, $28,
                    $29, $30, $31, $32, $33, $34, $35
                )
            """,
                item.get('detection_time', item.get('timestamp', datetime.now())),
                location,
                item.get('detection_id', str(uuid.uuid4())),
                item.get('satellite_sensor', item.get('sensor', 'unknown')),
                item.get('satellite_pass'),
                item.get('scan_angle'),
                item.get('confidence_level', item.get('confidence', 0)),
                item.get('brightness_temp_k'),
                item.get('brightness_temp_c', item.get('brightness')),
                item.get('brightness_temp_31', item.get('bright_t31')),
                item.get('fire_radiative_power', item.get('frp')),
                item.get('estimated_area_m2'),
                item.get('estimated_area_hectares'),
                item.get('fire_intensity'),
                item.get('fire_type'),
                item.get('fuel_type'),
                item.get('pixel_count'),
                item.get('cloud_cover_percent'),
                item.get('atmospheric_correction'),
                item.get('terrain_correction'),
                item.get('adjacent_water'),
                item.get('adjacent_cloud'),
                item.get('detection_algorithm'),
                item.get('validation_method'),
                item.get('verification_status', 'unverified'),
                item.get('false_positive_probability'),
                item.get('threat_level', 'medium'),
                item.get('evacuation_priority'),
                item.get('response_required', False),
                item.get('estimated_spread_rate'),
                item.get('weather_risk_factor'),
                item.get('incident_id'),
                item.get('cluster_id'),
                item.get('related_detections', []),
                json.dumps(item)
            )
    
    async def _bulk_insert_fire_detection(self, conn, batch: List[Dict], batch_id: str):
        """Bulk insert fire detection data"""
        
        insert_data = []
        for item in batch:
            location = f"POINT({item['longitude']} {item['latitude']})"
            
            insert_data.append((
                item.get('detection_time', item.get('timestamp', datetime.now())),
                location,
                item.get('detection_id', str(uuid.uuid4())),
                item.get('satellite_sensor', item.get('sensor', 'unknown')),
                item.get('satellite_pass'),
                item.get('scan_angle'),
                item.get('confidence_level', item.get('confidence', 0)),
                item.get('brightness_temp_k'),
                item.get('brightness_temp_c', item.get('brightness')),
                item.get('brightness_temp_31', item.get('bright_t31')),
                item.get('fire_radiative_power', item.get('frp')),
                item.get('estimated_area_m2'),
                item.get('estimated_area_hectares'),
                item.get('fire_intensity'),
                item.get('fire_type'),
                item.get('fuel_type'),
                item.get('pixel_count'),
                item.get('cloud_cover_percent'),
                item.get('atmospheric_correction'),
                item.get('terrain_correction'),
                item.get('adjacent_water'),
                item.get('adjacent_cloud'),
                item.get('detection_algorithm'),
                item.get('validation_method'),
                item.get('verification_status', 'unverified'),
                item.get('false_positive_probability'),
                item.get('threat_level', 'medium'),
                item.get('evacuation_priority'),
                item.get('response_required', False),
                item.get('estimated_spread_rate'),
                item.get('weather_risk_factor'),
                item.get('incident_id'),
                item.get('cluster_id'),
                item.get('related_detections', []),
                json.dumps(item)
            ))
        
        await conn.copy_records_to_table(
            'ts_fire_detection',
            records=insert_data,
            columns=[
                'time', 'location', 'detection_id', 'satellite_sensor', 'satellite_pass', 'scan_angle',
                'confidence_level', 'brightness_temp_k', 'brightness_temp_c', 'brightness_temp_31',
                'fire_radiative_power', 'estimated_area_m2', 'estimated_area_hectares',
                'fire_intensity', 'fire_type', 'fuel_type', 'pixel_count', 'cloud_cover_percent',
                'atmospheric_correction', 'terrain_correction', 'adjacent_water', 'adjacent_cloud',
                'detection_algorithm', 'validation_method', 'verification_status', 
                'false_positive_probability', 'threat_level', 'evacuation_priority',
                'response_required', 'estimated_spread_rate', 'weather_risk_factor',
                'incident_id', 'cluster_id', 'related_detections', 'raw_detection_data'
            ]
        )
    
    async def _store_predictions_timeseries(self, conn, data: Union[Dict, List], storage_id: str):
        """Store prediction data in TimescaleDB hypertable"""
        data_items = data if isinstance(data, list) else [data]
        
        for item in data_items:
            location = None
            if 'latitude' in item and 'longitude' in item:
                location = f"POINT({item['longitude']} {item['latitude']})"
            
            region_bounds = None
            if 'region_bounds' in item:
                bounds = item['region_bounds']
                if len(bounds) >= 3:
                    polygon_points = ",".join([f"{lng} {lat}" for lat, lng in bounds])
                    region_bounds = f"POLYGON(({polygon_points}))"
            
            await conn.execute("""
                INSERT INTO ts_predictions (
                    time, prediction_time, forecast_time, location, region_bounds,
                    model_name, model_version, model_type, ensemble_member,
                    prediction_type, fire_risk_score, fire_probability, fire_intensity_prediction,
                    expected_burned_area, spread_direction_degrees, spread_rate_mh, 
                    containment_difficulty, temp_forecast, humidity_forecast, wind_speed_forecast,
                    wind_direction_forecast, precipitation_forecast, drought_conditions,
                    vegetation_dryness, fuel_moisture_content, topographic_risk_factor,
                    human_activity_risk, lightning_probability, prediction_confidence,
                    uncertainty_range, skill_score, bias_correction_applied, alert_level,
                    resource_allocation_priority, evacuation_recommendation, 
                    fire_suppression_strategy, hindcast_accuracy, cross_validation_score,
                    feature_importance, model_inputs, raw_prediction_output
                ) VALUES (
                    $1, $2, $3, ST_GeogFromText($4), ST_GeogFromText($5), $6, $7, $8, $9, $10,
                    $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23, $24, $25,
                    $26, $27, $28, $29, $30, $31, $32, $33, $34, $35, $36, $37, $38, $39, $40, $41
                )
            """,
                item.get('timestamp', datetime.now()),
                item.get('prediction_time', datetime.now()),
                item.get('forecast_time', datetime.now() + timedelta(hours=24)),
                location,
                region_bounds,
                item.get('model_name', 'unknown'),
                item.get('model_version'),
                item.get('model_type'),
                item.get('ensemble_member'),
                item.get('prediction_type', 'fire_risk'),
                item.get('fire_risk_score'),
                item.get('fire_probability'),
                item.get('fire_intensity_prediction'),
                item.get('expected_burned_area'),
                item.get('spread_direction_degrees'),
                item.get('spread_rate_mh'),
                item.get('containment_difficulty'),
                item.get('temp_forecast'),
                item.get('humidity_forecast'),
                item.get('wind_speed_forecast'),
                item.get('wind_direction_forecast'),
                item.get('precipitation_forecast'),
                item.get('drought_conditions'),
                item.get('vegetation_dryness'),
                item.get('fuel_moisture_content'),
                item.get('topographic_risk_factor'),
                item.get('human_activity_risk'),
                item.get('lightning_probability'),
                item.get('prediction_confidence'),
                item.get('uncertainty_range'),
                item.get('skill_score'),
                item.get('bias_correction_applied', False),
                item.get('alert_level', 'none'),
                item.get('resource_allocation_priority'),
                item.get('evacuation_recommendation'),
                json.dumps(item.get('fire_suppression_strategy', {})),
                item.get('hindcast_accuracy'),
                item.get('cross_validation_score'),
                json.dumps(item.get('feature_importance', {})),
                json.dumps(item.get('model_inputs', {})),
                json.dumps(item)
            )
    
    async def _bulk_insert_predictions(self, conn, batch: List[Dict], batch_id: str):
        """Bulk insert prediction data"""
        
        insert_data = []
        for item in batch:
            location = None
            if 'latitude' in item and 'longitude' in item:
                location = f"POINT({item['longitude']} {item['latitude']})"
            
            region_bounds = None
            if 'region_bounds' in item:
                bounds = item['region_bounds']
                if len(bounds) >= 3:
                    polygon_points = ",".join([f"{lng} {lat}" for lat, lng in bounds])
                    region_bounds = f"POLYGON(({polygon_points}))"
            
            insert_data.append((
                item.get('timestamp', datetime.now()),
                item.get('prediction_time', datetime.now()),
                item.get('forecast_time', datetime.now() + timedelta(hours=24)),
                location,
                region_bounds,
                item.get('model_name', 'unknown'),
                item.get('model_version'),
                item.get('model_type'),
                item.get('ensemble_member'),
                item.get('prediction_type', 'fire_risk'),
                item.get('fire_risk_score'),
                item.get('fire_probability'),
                item.get('fire_intensity_prediction'),
                item.get('expected_burned_area'),
                item.get('spread_direction_degrees'),
                item.get('spread_rate_mh'),
                item.get('containment_difficulty'),
                item.get('temp_forecast'),
                item.get('humidity_forecast'),
                item.get('wind_speed_forecast'),
                item.get('wind_direction_forecast'),
                item.get('precipitation_forecast'),
                item.get('drought_conditions'),
                item.get('vegetation_dryness'),
                item.get('fuel_moisture_content'),
                item.get('topographic_risk_factor'),
                item.get('human_activity_risk'),
                item.get('lightning_probability'),
                item.get('prediction_confidence'),
                item.get('uncertainty_range'),
                item.get('skill_score'),
                item.get('bias_correction_applied', False),
                item.get('alert_level', 'none'),
                item.get('resource_allocation_priority'),
                item.get('evacuation_recommendation'),
                json.dumps(item.get('fire_suppression_strategy', {})),
                item.get('hindcast_accuracy'),
                item.get('cross_validation_score'),
                json.dumps(item.get('feature_importance', {})),
                json.dumps(item.get('model_inputs', {})),
                json.dumps(item)
            ))
        
        await conn.copy_records_to_table(
            'ts_predictions',
            records=insert_data,
            columns=[
                'time', 'prediction_time', 'forecast_time', 'location', 'region_bounds',
                'model_name', 'model_version', 'model_type', 'ensemble_member',
                'prediction_type', 'fire_risk_score', 'fire_probability', 'fire_intensity_prediction',
                'expected_burned_area', 'spread_direction_degrees', 'spread_rate_mh', 
                'containment_difficulty', 'temp_forecast', 'humidity_forecast', 'wind_speed_forecast',
                'wind_direction_forecast', 'precipitation_forecast', 'drought_conditions',
                'vegetation_dryness', 'fuel_moisture_content', 'topographic_risk_factor',
                'human_activity_risk', 'lightning_probability', 'prediction_confidence',
                'uncertainty_range', 'skill_score', 'bias_correction_applied', 'alert_level',
                'resource_allocation_priority', 'evacuation_recommendation', 
                'fire_suppression_strategy', 'hindcast_accuracy', 'cross_validation_score',
                'feature_importance', 'model_inputs', 'raw_prediction_output'
            ]
        )
    
    async def query(self, request: QueryRequest) -> QueryResponse:
        """Query time-series data with optimized performance"""
        start_time = datetime.now()
        
        async with self.get_connection() as conn:
            
            # Route to appropriate query method
            if request.data_type == DataType.WEATHER:
                data, total = await self._query_weather_timeseries(conn, request)
            elif request.data_type == DataType.SENSOR:
                data, total = await self._query_sensor_timeseries(conn, request)
            elif request.data_type == DataType.FIRE_DETECTION:
                data, total = await self._query_fire_detection_timeseries(conn, request)
            elif request.data_type == DataType.PREDICTIONS:
                data, total = await self._query_predictions_timeseries(conn, request)
            else:
                raise ValueError(f"Unsupported time-series query type: {request.data_type}")
            
            query_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return QueryResponse(
                data=data,
                total_records=total,
                data_type=request.data_type,
                query_time_ms=query_time,
                metadata={"request": request.dict(), "backend": "timescaledb"} if request.include_metadata else None
            )
    
    async def _query_weather_timeseries(self, conn, request: QueryRequest) -> Tuple[List[Dict], int]:
        """Query weather time-series data with optimized filtering"""
        
        where_conditions = ["1=1"]
        params = []
        param_count = 0
        
        # Time range filtering (essential for time-series)
        if request.start_time:
            param_count += 1
            where_conditions.append(f"time >= ${param_count}")
            params.append(request.start_time)
        
        if request.end_time:
            param_count += 1
            where_conditions.append(f"time <= ${param_count}")
            params.append(request.end_time)
        
        # Spatial filtering
        if request.spatial_bounds:
            bounds = request.spatial_bounds
            if all(k in bounds for k in ['min_lat', 'max_lat', 'min_lon', 'max_lon']):
                param_count += 1
                polygon = f"POLYGON(({bounds['min_lon']} {bounds['min_lat']}, {bounds['max_lon']} {bounds['min_lat']}, {bounds['max_lon']} {bounds['max_lat']}, {bounds['min_lon']} {bounds['max_lat']}, {bounds['min_lon']} {bounds['min_lat']}))"
                where_conditions.append(f"ST_Intersects(location, ST_GeogFromText(${param_count}))")
                params.append(polygon)
        
        # Additional filters
        if request.filters:
            for key, value in request.filters.items():
                if key in ['source', 'station_id', 'forecast_model']:
                    param_count += 1
                    where_conditions.append(f"{key} = ${param_count}")
                    params.append(value)
                elif key in ['temperature', 'humidity', 'wind_speed', 'fire_weather_index']:
                    if isinstance(value, dict):
                        if 'min' in value:
                            param_count += 1
                            where_conditions.append(f"{key} >= ${param_count}")
                            params.append(value['min'])
                        if 'max' in value:
                            param_count += 1
                            where_conditions.append(f"{key} <= ${param_count}")
                            params.append(value['max'])
        
        where_clause = " AND ".join(where_conditions)
        
        # Count total records
        count_query = f"SELECT COUNT(*) FROM ts_weather_data WHERE {where_clause}"
        total = await conn.fetchval(count_query, *params)
        
        # Check if we should use aggregated data for better performance
        use_aggregates = False
        if request.aggregation and 'time_bucket' in request.aggregation:
            bucket_size = request.aggregation['time_bucket']
            if bucket_size in ['1 hour', '1 day']:
                use_aggregates = True
                table_name = f"weather_{bucket_size.replace(' ', '')}"
                
                # Adjust query for aggregate table
                data_query = f"""
                    SELECT bucket as time, longitude, latitude, source, station_id,
                           avg_temperature, max_temperature, min_temperature,
                           avg_humidity, avg_pressure, avg_wind_speed, max_wind_speed,
                           total_precipitation, avg_fire_weather_index, max_fire_weather_index,
                           measurement_count
                    FROM {table_name}
                    WHERE bucket >= ${1} AND bucket <= ${2}
                """
                
                if request.spatial_bounds:
                    bounds = request.spatial_bounds
                    data_query += f" AND longitude >= {bounds['min_lon']} AND longitude <= {bounds['max_lon']}"
                    data_query += f" AND latitude >= {bounds['min_lat']} AND latitude <= {bounds['max_lat']}"
                
                data_query += " ORDER BY bucket DESC"
                
                if request.limit:
                    data_query += f" LIMIT {request.limit}"
                    if request.offset:
                        data_query += f" OFFSET {request.offset}"
                
                rows = await conn.fetch(data_query, request.start_time, request.end_time)
        
        if not use_aggregates:
            # Standard detailed query
            limit_clause = ""
            if request.limit:
                param_count += 1
                limit_clause = f"LIMIT ${param_count}"
                params.append(request.limit)
                
                if request.offset:
                    param_count += 1
                    limit_clause += f" OFFSET ${param_count}"
                    params.append(request.offset)
            
            data_query = f"""
                SELECT *,
                       ST_X(location::geometry) as longitude,
                       ST_Y(location::geometry) as latitude
                FROM ts_weather_data
                WHERE {where_clause}
                ORDER BY time DESC
                {limit_clause}
            """
            
            rows = await conn.fetch(data_query, *params)
        
        data = [dict(row) for row in rows]
        return data, total
    
    async def _query_sensor_timeseries(self, conn, request: QueryRequest) -> Tuple[List[Dict], int]:
        """Query sensor time-series data with optimized filtering"""
        
        where_conditions = ["1=1"]
        params = []
        param_count = 0
        
        # Time range filtering
        if request.start_time:
            param_count += 1
            where_conditions.append(f"time >= ${param_count}")
            params.append(request.start_time)
        
        if request.end_time:
            param_count += 1
            where_conditions.append(f"time <= ${param_count}")
            params.append(request.end_time)
        
        # Spatial filtering
        if request.spatial_bounds:
            bounds = request.spatial_bounds
            if all(k in bounds for k in ['min_lat', 'max_lat', 'min_lon', 'max_lon']):
                param_count += 1
                polygon = f"POLYGON(({bounds['min_lon']} {bounds['min_lat']}, {bounds['max_lon']} {bounds['min_lat']}, {bounds['max_lon']} {bounds['max_lat']}, {bounds['min_lon']} {bounds['max_lat']}, {bounds['min_lon']} {bounds['min_lat']}))"
                where_conditions.append(f"ST_Intersects(location, ST_GeogFromText(${param_count}))")
                params.append(polygon)
        
        # Sensor-specific filters
        if request.filters:
            for key, value in request.filters.items():
                if key in ['sensor_id', 'sensor_type', 'network', 'status']:
                    param_count += 1
                    where_conditions.append(f"{key} = ${param_count}")
                    params.append(value)
                elif key in ['pm25', 'pm10', 'aqi', 'temperature', 'humidity']:
                    if isinstance(value, dict):
                        if 'min' in value:
                            param_count += 1
                            where_conditions.append(f"{key} >= ${param_count}")
                            params.append(value['min'])
                        if 'max' in value:
                            param_count += 1
                            where_conditions.append(f"{key} <= ${param_count}")
                            params.append(value['max'])
        
        where_clause = " AND ".join(where_conditions)
        
        # Count total records
        count_query = f"SELECT COUNT(*) FROM ts_sensor_data WHERE {where_clause}"
        total = await conn.fetchval(count_query, *params)
        
        # Main data query
        limit_clause = ""
        if request.limit:
            param_count += 1
            limit_clause = f"LIMIT ${param_count}"
            params.append(request.limit)
            
            if request.offset:
                param_count += 1
                limit_clause += f" OFFSET ${param_count}"
                params.append(request.offset)
        
        data_query = f"""
            SELECT *,
                   ST_X(location::geometry) as longitude,
                   ST_Y(location::geometry) as latitude
            FROM ts_sensor_data
            WHERE {where_clause}
            ORDER BY time DESC, sensor_id
            {limit_clause}
        """
        
        rows = await conn.fetch(data_query, *params)
        data = [dict(row) for row in rows]
        
        return data, total
    
    async def _query_fire_detection_timeseries(self, conn, request: QueryRequest) -> Tuple[List[Dict], int]:
        """Query fire detection time-series data with optimized filtering"""
        
        where_conditions = ["1=1"]
        params = []
        param_count = 0
        
        # Time range filtering
        if request.start_time:
            param_count += 1
            where_conditions.append(f"time >= ${param_count}")
            params.append(request.start_time)
        
        if request.end_time:
            param_count += 1
            where_conditions.append(f"time <= ${param_count}")
            params.append(request.end_time)
        
        # Spatial filtering
        if request.spatial_bounds:
            bounds = request.spatial_bounds
            if all(k in bounds for k in ['min_lat', 'max_lat', 'min_lon', 'max_lon']):
                param_count += 1
                polygon = f"POLYGON(({bounds['min_lon']} {bounds['min_lat']}, {bounds['max_lon']} {bounds['min_lat']}, {bounds['max_lon']} {bounds['max_lat']}, {bounds['min_lon']} {bounds['max_lat']}, {bounds['min_lon']} {bounds['min_lat']}))"
                where_conditions.append(f"ST_Intersects(location, ST_GeogFromText(${param_count}))")
                params.append(polygon)
        
        # Fire-specific filters
        if request.filters:
            for key, value in request.filters.items():
                if key in ['satellite_sensor', 'verification_status', 'threat_level', 'fire_type']:
                    param_count += 1
                    where_conditions.append(f"{key} = ${param_count}")
                    params.append(value)
                elif key == 'min_confidence':
                    param_count += 1
                    where_conditions.append(f"confidence_level >= ${param_count}")
                    params.append(value)
                elif key == 'response_required':
                    param_count += 1
                    where_conditions.append(f"response_required = ${param_count}")
                    params.append(value)
                elif key == 'cluster_id':
                    param_count += 1
                    where_conditions.append(f"cluster_id = ${param_count}")
                    params.append(value)
        
        where_clause = " AND ".join(where_conditions)
        
        # Count total records
        count_query = f"SELECT COUNT(*) FROM ts_fire_detection WHERE {where_clause}"
        total = await conn.fetchval(count_query, *params)
        
        # Main data query
        limit_clause = ""
        if request.limit:
            param_count += 1
            limit_clause = f"LIMIT ${param_count}"
            params.append(request.limit)
            
            if request.offset:
                param_count += 1
                limit_clause += f" OFFSET ${param_count}"
                params.append(request.offset)
        
        data_query = f"""
            SELECT *,
                   ST_X(location::geometry) as longitude,
                   ST_Y(location::geometry) as latitude
            FROM ts_fire_detection
            WHERE {where_clause}
            ORDER BY time DESC, confidence_level DESC
            {limit_clause}
        """
        
        rows = await conn.fetch(data_query, *params)
        data = [dict(row) for row in rows]
        
        return data, total
    
    async def _query_predictions_timeseries(self, conn, request: QueryRequest) -> Tuple[List[Dict], int]:
        """Query prediction time-series data with model and time filtering"""
        
        where_conditions = ["1=1"]
        params = []
        param_count = 0
        
        # Time range filtering
        if request.start_time:
            param_count += 1
            where_conditions.append(f"time >= ${param_count}")
            params.append(request.start_time)
        
        if request.end_time:
            param_count += 1
            where_conditions.append(f"time <= ${param_count}")
            params.append(request.end_time)
        
        # Prediction-specific filters
        if request.filters:
            for key, value in request.filters.items():
                if key in ['model_name', 'model_version', 'prediction_type', 'alert_level']:
                    param_count += 1
                    where_conditions.append(f"{key} = ${param_count}")
                    params.append(value)
                elif key == 'forecast_time_range':
                    if 'start' in value:
                        param_count += 1
                        where_conditions.append(f"forecast_time >= ${param_count}")
                        params.append(value['start'])
                    if 'end' in value:
                        param_count += 1
                        where_conditions.append(f"forecast_time <= ${param_count}")
                        params.append(value['end'])
        
        where_clause = " AND ".join(where_conditions)
        
        # Count total records
        count_query = f"SELECT COUNT(*) FROM ts_predictions WHERE {where_clause}"
        total = await conn.fetchval(count_query, *params)
        
        # Main data query
        limit_clause = ""
        if request.limit:
            param_count += 1
            limit_clause = f"LIMIT ${param_count}"
            params.append(request.limit)
            
            if request.offset:
                param_count += 1
                limit_clause += f" OFFSET ${param_count}"
                params.append(request.offset)
        
        data_query = f"""
            SELECT *,
                   CASE WHEN location IS NOT NULL THEN ST_X(location::geometry) END as longitude,
                   CASE WHEN location IS NOT NULL THEN ST_Y(location::geometry) END as latitude
            FROM ts_predictions
            WHERE {where_clause}
            ORDER BY time DESC, fire_risk_score DESC
            {limit_clause}
        """
        
        rows = await conn.fetch(data_query, *params)
        data = [dict(row) for row in rows]
        
        return data, total
    
    async def get_timeseries_analytics(self, data_type: DataType, time_range: timedelta = timedelta(days=7)) -> Dict[str, Any]:
        """Get advanced analytics for time-series data"""
        async with self.get_connection() as conn:
            
            end_time = datetime.now()
            start_time = end_time - time_range
            
            analytics = {
                'data_type': data_type.value,
                'time_range': str(time_range),
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat()
            }
            
            if data_type == DataType.WEATHER:
                analytics.update(await self._get_weather_analytics(conn, start_time, end_time))
            elif data_type == DataType.SENSOR:
                analytics.update(await self._get_sensor_analytics(conn, start_time, end_time))
            elif data_type == DataType.FIRE_DETECTION:
                analytics.update(await self._get_fire_detection_analytics(conn, start_time, end_time))
            elif data_type == DataType.PREDICTIONS:
                analytics.update(await self._get_predictions_analytics(conn, start_time, end_time))
            
            return analytics
    
    async def _get_weather_analytics(self, conn, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Get weather-specific analytics"""
        
        # Basic statistics
        stats_query = """
            SELECT 
                COUNT(*) as total_measurements,
                AVG(temperature) as avg_temperature,
                MIN(temperature) as min_temperature, 
                MAX(temperature) as max_temperature,
                AVG(humidity) as avg_humidity,
                AVG(wind_speed) as avg_wind_speed,
                MAX(wind_speed) as max_wind_speed,
                SUM(precipitation) as total_precipitation,
                AVG(fire_weather_index) as avg_fire_weather_index,
                MAX(fire_weather_index) as max_fire_weather_index,
                COUNT(DISTINCT source) as unique_sources,
                COUNT(DISTINCT station_id) as unique_stations
            FROM ts_weather_data
            WHERE time >= $1 AND time <= $2
        """
        
        stats = await conn.fetchrow(stats_query, start_time, end_time)
        
        # Trend analysis (hourly averages)
        trend_query = """
            SELECT 
                time_bucket('1 hour', time) as hour,
                AVG(temperature) as avg_temp,
                AVG(humidity) as avg_humidity,
                AVG(wind_speed) as avg_wind_speed,
                AVG(fire_weather_index) as avg_fire_index
            FROM ts_weather_data
            WHERE time >= $1 AND time <= $2
            GROUP BY hour
            ORDER BY hour
        """
        
        trends = await conn.fetch(trend_query, start_time, end_time)
        
        return {
            'basic_statistics': dict(stats) if stats else {},
            'hourly_trends': [dict(row) for row in trends],
            'data_quality': {
                'completeness': float(stats['total_measurements'] / max(1, (end_time - start_time).total_seconds() / 3600)) if stats else 0,
                'temperature_range_check': -50 <= float(stats['min_temperature'] or 0) <= 70 and -50 <= float(stats['max_temperature'] or 0) <= 70 if stats else True
            }
        }
    
    async def _get_fire_detection_analytics(self, conn, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Get fire detection-specific analytics"""
        
        # Detection statistics
        stats_query = """
            SELECT 
                COUNT(*) as total_detections,
                COUNT(*) FILTER (WHERE confidence_level > 80) as high_confidence_detections,
                COUNT(*) FILTER (WHERE verification_status = 'verified') as verified_detections,
                COUNT(*) FILTER (WHERE threat_level IN ('high', 'critical', 'extreme')) as high_threat_detections,
                COUNT(*) FILTER (WHERE response_required = true) as response_required_count,
                AVG(confidence_level) as avg_confidence,
                AVG(fire_radiative_power) as avg_frp,
                SUM(estimated_area_hectares) as total_estimated_area,
                COUNT(DISTINCT satellite_sensor) as unique_sensors,
                COUNT(DISTINCT cluster_id) FILTER (WHERE cluster_id IS NOT NULL) as fire_clusters
            FROM ts_fire_detection
            WHERE time >= $1 AND time <= $2
        """
        
        stats = await conn.fetchrow(stats_query, start_time, end_time)
        
        # Detection rate over time
        rate_query = """
            SELECT 
                time_bucket('1 hour', time) as hour,
                COUNT(*) as detections_per_hour,
                AVG(confidence_level) as avg_confidence_per_hour
            FROM ts_fire_detection
            WHERE time >= $1 AND time <= $2
            GROUP BY hour
            ORDER BY hour
        """
        
        rates = await conn.fetch(rate_query, start_time, end_time)
        
        # Sensor performance
        sensor_query = """
            SELECT 
                satellite_sensor,
                COUNT(*) as detection_count,
                AVG(confidence_level) as avg_confidence,
                COUNT(*) FILTER (WHERE verification_status = 'verified') as verified_count
            FROM ts_fire_detection
            WHERE time >= $1 AND time <= $2
            GROUP BY satellite_sensor
            ORDER BY detection_count DESC
        """
        
        sensor_performance = await conn.fetch(sensor_query, start_time, end_time)
        
        return {
            'detection_statistics': dict(stats) if stats else {},
            'hourly_detection_rates': [dict(row) for row in rates],
            'sensor_performance': [dict(row) for row in sensor_performance],
            'quality_metrics': {
                'high_confidence_rate': float(stats['high_confidence_detections']) / max(1, stats['total_detections']) if stats and stats['total_detections'] else 0,
                'verification_rate': float(stats['verified_detections']) / max(1, stats['total_detections']) if stats and stats['total_detections'] else 0,
                'false_positive_rate': 1.0 - (float(stats['verified_detections']) / max(1, stats['total_detections'])) if stats and stats['total_detections'] else 0
            }
        }
    
    async def optimize_performance(self):
        """Run performance optimization tasks"""
        async with self.get_connection() as conn:
            
            # Update table statistics
            await conn.execute("ANALYZE ts_weather_data")
            await conn.execute("ANALYZE ts_sensor_data") 
            await conn.execute("ANALYZE ts_fire_detection")
            await conn.execute("ANALYZE ts_predictions")
            
            # Refresh continuous aggregates manually if needed
            try:
                await conn.execute("REFRESH MATERIALIZED VIEW weather_hourly")
                await conn.execute("REFRESH MATERIALIZED VIEW weather_daily")
                await conn.execute("REFRESH MATERIALIZED VIEW sensor_hourly")
                await conn.execute("REFRESH MATERIALIZED VIEW fire_detection_daily")
                logger.info("Continuous aggregates refreshed successfully")
            except Exception as e:
                logger.warning("Failed to refresh some continuous aggregates", error=str(e))
            
            # Run compression jobs manually if needed
            try:
                await conn.execute("SELECT compress_chunk(chunk) FROM show_chunks('ts_weather_data') AS chunk WHERE NOT is_compressed;")
                logger.info("Compression jobs completed")
            except Exception as e:
                logger.warning("Failed to run compression jobs", error=str(e))
            
            logger.info("TimescaleDB performance optimization completed")