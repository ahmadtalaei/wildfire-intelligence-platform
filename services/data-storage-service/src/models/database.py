"""
Database Management for Wildfire Intelligence Storage Service
Comprehensive PostgreSQL and connection management with advanced features
"""

import asyncio
import asyncpg
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
import json
import uuid
from contextlib import asynccontextmanager
import structlog

from ..config import get_settings
from .data_models import (
    StorageRequest, StorageResponse, BulkStorageRequest, QueryRequest, 
    QueryResponse, DataType, StorageBackend
)

logger = structlog.get_logger()


class DatabaseManager:
    """Comprehensive database manager with advanced PostgreSQL features"""
    
    def __init__(self):
        self.settings = get_settings()
        self.pool = None
        self.is_initialized = False
        
    async def initialize(self):
        """Initialize database connection pool and setup"""
        try:
            logger.info("Initializing database manager")
            
            # Create connection pool
            self.pool = await asyncpg.create_pool(
                self.settings.database_url,
                min_size=1,
                max_size=self.settings.db_pool_size,
                max_queries=50000,
                max_inactive_connection_lifetime=300,
                command_timeout=self.settings.query_timeout_seconds
            )
            
            # Initialize database schema
            await self._initialize_schema()
            
            # Create basic indexes for performance (temporarily disabled all indexes for initial testing)
            # await self._create_basic_indexes()

            # Setup partitioning (temporarily disabled)
            # await self._setup_partitioning()
            
            self.is_initialized = True
            logger.info("Database manager initialized successfully")
            
        except Exception as e:
            logger.error("Database initialization failed", error=str(e))
            raise
    
    async def cleanup(self):
        """Cleanup database connections"""
        if self.pool:
            await self.pool.close()
            logger.info("Database connections closed")
    
    @asynccontextmanager
    async def get_connection(self):
        """Get database connection from pool"""
        if not self.is_initialized:
            raise RuntimeError("Database manager not initialized. Call initialize() first.")

        async with self.pool.acquire() as connection:
            yield connection
    
    async def _initialize_schema(self):
        """Initialize minimal database schema for Kafka consumer testing"""
        async with self.pool.acquire() as conn:

            # Create basic fire_incidents table for Kafka consumer testing
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS fire_incidents (
                    incident_id VARCHAR(255) PRIMARY KEY,
                    latitude DECIMAL(10,8),
                    longitude DECIMAL(11,8),
                    confidence DECIMAL(5,2),
                    brightness DECIMAL(7,2),
                    temperature DECIMAL(7,2),
                    frp DECIMAL(10,2),
                    bright_t31 DECIMAL(7,2),
                    daynight VARCHAR(1),
                    satellite VARCHAR(50),
                    instrument VARCHAR(50),
                    source VARCHAR(100),
                    timestamp TIMESTAMPTZ,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    type INTEGER DEFAULT 0
                );
            """)

            # Create basic weather_data table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS weather_data (
                    id VARCHAR(255) PRIMARY KEY,
                    latitude DECIMAL(10,8),
                    longitude DECIMAL(11,8),
                    temperature DECIMAL(7,2),
                    humidity DECIMAL(5,2),
                    wind_speed DECIMAL(6,2),
                    wind_direction INTEGER,
                    pressure DECIMAL(8,2),
                    source VARCHAR(100),
                    timestamp TIMESTAMPTZ,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
            """)

            # Create basic sensor_readings table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS sensor_readings (
                    id VARCHAR(255) PRIMARY KEY,
                    sensor_id VARCHAR(100),
                    latitude DECIMAL(10,8),
                    longitude DECIMAL(11,8),
                    temperature DECIMAL(7,2),
                    humidity DECIMAL(5,2),
                    smoke_level DECIMAL(8,2),
                    co2_level DECIMAL(8,2),
                    source VARCHAR(100),
                    timestamp TIMESTAMPTZ,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
            """)

            logger.info("Basic database schema initialized for Kafka consumer testing")
            return
            
            # Main storage metadata table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS storage_metadata (
                    storage_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    data_type VARCHAR(50) NOT NULL,
                    source_id VARCHAR(100),
                    backend VARCHAR(20) NOT NULL,
                    size_bytes BIGINT NOT NULL DEFAULT 0,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    retention_until TIMESTAMPTZ,
                    tags TEXT[],
                    metadata JSONB,
                    latitude DECIMAL(10,8),
                    longitude DECIMAL(11,8),
                    
                    -- Indexes
                    CONSTRAINT valid_data_type CHECK (data_type IN ('weather', 'sensor', 'fire_detection', 'predictions', 'satellite_image', 'model_file', 'archive', 'metadata')),
                    CONSTRAINT valid_backend CHECK (backend IN ('timescale', 'postgresql', 's3_minio', 'redis'))
                )
            """)
            
            # Weather data table (for non-timeseries storage)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS weather_data (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    storage_id UUID REFERENCES storage_metadata(storage_id) ON DELETE CASCADE,
                    timestamp TIMESTAMPTZ NOT NULL,
                    latitude DECIMAL(10,8),
                    longitude DECIMAL(11,8),
                    temperature DECIMAL(5,2),
                    humidity DECIMAL(5,2),
                    wind_speed DECIMAL(6,2),
                    wind_direction INTEGER,
                    pressure DECIMAL(7,2),
                    precipitation DECIMAL(6,2),
                    visibility DECIMAL(6,2),
                    fire_weather_index DECIMAL(5,2),
                    source VARCHAR(100),
                    quality_score DECIMAL(3,2),
                    raw_data JSONB,
                    
                    -- Constraints
                    CONSTRAINT valid_humidity CHECK (humidity >= 0 AND humidity <= 100),
                    CONSTRAINT valid_wind_direction CHECK (wind_direction >= 0 AND wind_direction <= 360),
                    CONSTRAINT valid_quality_score CHECK (quality_score >= 0 AND quality_score <= 1)
                )
            """)
            
            # Sensor data table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS sensor_data (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    storage_id UUID REFERENCES storage_metadata(storage_id) ON DELETE CASCADE,
                    sensor_id VARCHAR(100) NOT NULL,
                    timestamp TIMESTAMPTZ NOT NULL,
                    latitude DECIMAL(10,8),
                    longitude DECIMAL(11,8),
                    sensor_type VARCHAR(50),
                    measurements JSONB NOT NULL,
                    air_quality_index INTEGER,
                    pm25 DECIMAL(8,2),
                    pm10 DECIMAL(8,2),
                    co2_ppm INTEGER,
                    battery_level DECIMAL(5,2),
                    signal_strength INTEGER,
                    status VARCHAR(20) DEFAULT 'active',
                    raw_data JSONB,
                    
                    -- Constraints
                    CONSTRAINT valid_aqi CHECK (air_quality_index >= 0 AND air_quality_index <= 500),
                    CONSTRAINT valid_status CHECK (status IN ('active', 'inactive', 'maintenance', 'error'))
                )
            """)
            
            # Fire detection data table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS fire_detection_data (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    storage_id UUID REFERENCES storage_metadata(storage_id) ON DELETE CASCADE,
                    detection_time TIMESTAMPTZ NOT NULL,
                    latitude DECIMAL(10,8) NOT NULL,
                    longitude DECIMAL(11,8) NOT NULL,
                    confidence_level DECIMAL(5,2) NOT NULL,
                    satellite_sensor VARCHAR(50),
                    brightness_temp DECIMAL(7,2),
                    fire_radiative_power DECIMAL(10,2),
                    estimated_area_hectares DECIMAL(10,2),
                    fire_type VARCHAR(50),
                    verification_status VARCHAR(20) DEFAULT 'unverified',
                    alert_level VARCHAR(20) DEFAULT 'medium',
                    response_required BOOLEAN DEFAULT FALSE,
                    incident_id UUID,
                    raw_data JSONB,
                    
                    -- Constraints
                    CONSTRAINT valid_confidence CHECK (confidence_level >= 0 AND confidence_level <= 100),
                    CONSTRAINT valid_verification CHECK (verification_status IN ('unverified', 'verified', 'false_positive')),
                    CONSTRAINT valid_alert_level CHECK (alert_level IN ('low', 'medium', 'high', 'critical'))
                )
            """)
            
            # Prediction data table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS prediction_data (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    storage_id UUID REFERENCES storage_metadata(storage_id) ON DELETE CASCADE,
                    model_name VARCHAR(100) NOT NULL,
                    model_version VARCHAR(50),
                    prediction_time TIMESTAMPTZ NOT NULL,
                    forecast_horizon_hours INTEGER NOT NULL,
                    latitude DECIMAL(10,8),
                    longitude DECIMAL(11,8),
                    region_bounds_json TEXT,
                    prediction_type VARCHAR(50) NOT NULL,
                    fire_risk_score DECIMAL(5,2),
                    weather_forecast JSONB,
                    fire_behavior_prediction JSONB,
                    evacuation_recommendations JSONB,
                    confidence_intervals JSONB,
                    model_inputs JSONB,
                    raw_predictions JSONB,
                    
                    -- Constraints
                    CONSTRAINT valid_prediction_type CHECK (prediction_type IN ('fire_risk', 'fire_behavior', 'weather_forecast', 'evacuation_planning')),
                    CONSTRAINT valid_fire_risk CHECK (fire_risk_score >= 0 AND fire_risk_score <= 100),
                    CONSTRAINT valid_horizon CHECK (forecast_horizon_hours > 0 AND forecast_horizon_hours <= 2160) -- Max 90 days
                )
            """)
            
            # Blob storage references table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS blob_storage_refs (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    storage_id UUID REFERENCES storage_metadata(storage_id) ON DELETE CASCADE,
                    blob_key VARCHAR(500) NOT NULL,
                    bucket_name VARCHAR(100) NOT NULL,
                    file_name VARCHAR(255),
                    content_type VARCHAR(100),
                    file_size BIGINT NOT NULL,
                    checksum VARCHAR(128),
                    compression_type VARCHAR(50),
                    encryption_type VARCHAR(50),
                    access_tier VARCHAR(20) DEFAULT 'hot',
                    expires_at TIMESTAMPTZ,
                    
                    -- Constraints
                    CONSTRAINT valid_access_tier CHECK (access_tier IN ('hot', 'warm', 'cold', 'archive')),
                    UNIQUE(blob_key, bucket_name)
                )
            """)
            
            # Storage statistics table for monitoring
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS storage_statistics (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    data_type VARCHAR(50) NOT NULL,
                    total_records BIGINT NOT NULL DEFAULT 0,
                    total_size_bytes BIGINT NOT NULL DEFAULT 0,
                    avg_record_size_bytes INTEGER,
                    oldest_record TIMESTAMPTZ,
                    newest_record TIMESTAMPTZ,
                    records_last_hour INTEGER DEFAULT 0,
                    records_last_day INTEGER DEFAULT 0,
                    storage_efficiency DECIMAL(5,4),
                    
                    -- Ensure only one record per data_type per hour
                    UNIQUE(data_type, date_trunc('hour', recorded_at))
                )
            """)
            
            # Archival tracking table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS archival_jobs (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    job_name VARCHAR(100) NOT NULL,
                    data_type VARCHAR(50) NOT NULL,
                    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    completed_at TIMESTAMPTZ,
                    status VARCHAR(20) NOT NULL DEFAULT 'running',
                    records_processed INTEGER DEFAULT 0,
                    bytes_processed BIGINT DEFAULT 0,
                    records_archived INTEGER DEFAULT 0,
                    compression_ratio DECIMAL(5,4),
                    error_message TEXT,
                    config JSONB,
                    
                    -- Constraints
                    CONSTRAINT valid_status CHECK (status IN ('running', 'completed', 'failed', 'paused'))
                )
            """)
            
            # User access logs for auditing
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS access_logs (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    accessed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    user_id VARCHAR(100),
                    operation VARCHAR(50) NOT NULL,
                    data_type VARCHAR(50),
                    storage_id UUID,
                    query_params JSONB,
                    response_time_ms INTEGER,
                    status_code INTEGER,
                    ip_address INET,
                    user_agent TEXT,
                    
                    -- Constraints
                    CONSTRAINT valid_operation CHECK (operation IN ('store', 'query', 'delete', 'archive', 'retrieve'))
                )
            """)
            
            logger.info("Database schema initialized successfully")

    async def _create_basic_indexes(self):
        """Create basic indexes for existing tables"""
        async with self.pool.acquire() as conn:
            # Fire incidents indexes (for Kafka consumer)
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_fire_incidents_timestamp ON fire_incidents(timestamp)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_fire_incidents_location ON fire_incidents(latitude, longitude)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_fire_incidents_source ON fire_incidents(source)")

            # Weather data indexes (for Kafka consumer)
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_weather_data_timestamp ON weather_data(timestamp)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_weather_data_location ON weather_data(latitude, longitude)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_weather_data_source ON weather_data(source)")

            # Sensor readings indexes (for Kafka consumer)
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_sensor_readings_timestamp ON sensor_readings(timestamp)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_sensor_readings_sensor_id ON sensor_readings(sensor_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_sensor_readings_location ON sensor_readings(latitude, longitude)")

            logger.info("Basic database indexes created successfully")

    async def _create_indexes(self):
        """Create performance indexes"""
        async with self.pool.acquire() as conn:
            
            # Storage metadata indexes
            await conn.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_storage_metadata_data_type ON storage_metadata(data_type)")
            await conn.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_storage_metadata_created_at ON storage_metadata(created_at)")
            await conn.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_storage_metadata_source_id ON storage_metadata(source_id)")
            await conn.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_storage_metadata_tags ON storage_metadata USING GIN(tags)")
            await conn.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_storage_metadata_metadata ON storage_metadata USING GIN(metadata)")
            await conn.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_storage_metadata_geolocation ON storage_metadata USING GIST(geolocation)")
            await conn.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_storage_metadata_retention ON storage_metadata(retention_until) WHERE retention_until IS NOT NULL")
            
            # Weather data indexes
            await conn.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_weather_data_timestamp ON weather_data(timestamp)")
            await conn.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_weather_data_location ON weather_data USING GIST(location)")
            await conn.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_weather_data_source ON weather_data(source)")
            await conn.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_weather_data_fire_index ON weather_data(fire_weather_index) WHERE fire_weather_index IS NOT NULL")
            await conn.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_weather_data_composite ON weather_data(source, timestamp)")
            
            # Sensor data indexes
            await conn.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sensor_data_sensor_id ON sensor_data(sensor_id)")
            await conn.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sensor_data_timestamp ON sensor_data(timestamp)")
            await conn.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sensor_data_location ON sensor_data USING GIST(location)")
            await conn.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sensor_data_type ON sensor_data(sensor_type)")
            await conn.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sensor_data_status ON sensor_data(status)")
            await conn.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sensor_data_measurements ON sensor_data USING GIN(measurements)")
            await conn.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sensor_data_composite ON sensor_data(sensor_id, timestamp)")
            
            # Fire detection indexes
            await conn.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_fire_detection_time ON fire_detection_data(detection_time)")
            await conn.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_fire_detection_location ON fire_detection_data USING GIST(location)")
            await conn.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_fire_detection_confidence ON fire_detection_data(confidence_level)")
            await conn.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_fire_detection_sensor ON fire_detection_data(satellite_sensor)")
            await conn.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_fire_detection_alert ON fire_detection_data(alert_level)")
            await conn.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_fire_detection_verification ON fire_detection_data(verification_status)")
            await conn.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_fire_detection_response ON fire_detection_data(response_required) WHERE response_required = TRUE")
            
            # Prediction data indexes
            await conn.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_prediction_data_model ON prediction_data(model_name)")
            await conn.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_prediction_data_time ON prediction_data(prediction_time)")
            await conn.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_prediction_data_type ON prediction_data(prediction_type)")
            await conn.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_prediction_data_location ON prediction_data USING GIST(location)")
            await conn.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_prediction_data_region ON prediction_data USING GIST(region_bounds)")
            await conn.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_prediction_data_risk ON prediction_data(fire_risk_score) WHERE fire_risk_score IS NOT NULL")
            
            # Blob storage indexes
            await conn.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_blob_storage_key ON blob_storage_refs(blob_key)")
            await conn.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_blob_storage_bucket ON blob_storage_refs(bucket_name)")
            await conn.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_blob_storage_type ON blob_storage_refs(content_type)")
            await conn.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_blob_storage_tier ON blob_storage_refs(access_tier)")
            await conn.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_blob_storage_expires ON blob_storage_refs(expires_at) WHERE expires_at IS NOT NULL")
            
            # Statistics indexes
            await conn.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_storage_stats_type_time ON storage_statistics(data_type, recorded_at)")
            await conn.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_storage_stats_recorded ON storage_statistics(recorded_at)")
            
            # Archival job indexes
            await conn.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_archival_jobs_status ON archival_jobs(status)")
            await conn.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_archival_jobs_type ON archival_jobs(data_type)")
            await conn.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_archival_jobs_started ON archival_jobs(started_at)")
            
            # Access log indexes for auditing and monitoring
            await conn.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_access_logs_accessed_at ON access_logs(accessed_at)")
            await conn.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_access_logs_operation ON access_logs(operation)")
            await conn.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_access_logs_user_id ON access_logs(user_id)")
            await conn.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_access_logs_status ON access_logs(status_code)")
            
            logger.info("Database indexes created successfully")
    
    async def _setup_partitioning(self):
        """Setup table partitioning for improved performance"""
        async with self.pool.acquire() as conn:
            
            # Partition access_logs by month for better performance and archival
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS access_logs_template (
                    LIKE access_logs INCLUDING ALL
                ) PARTITION BY RANGE (accessed_at)
            """)
            
            # Create partitions for current and next 3 months
            current_date = datetime.now()
            for i in range(4):
                partition_date = current_date.replace(day=1) + timedelta(days=32*i)
                partition_date = partition_date.replace(day=1)
                next_month = (partition_date + timedelta(days=32)).replace(day=1)
                
                partition_name = f"access_logs_y{partition_date.year}m{partition_date.month:02d}"
                
                try:
                    await conn.execute(f"""
                        CREATE TABLE IF NOT EXISTS {partition_name}
                        PARTITION OF access_logs_template
                        FOR VALUES FROM ('{partition_date.strftime("%Y-%m-%d")}') 
                        TO ('{next_month.strftime("%Y-%m-%d")}')
                    """)
                except Exception as e:
                    # Partition might already exist
                    if "already exists" not in str(e):
                        logger.warning(f"Failed to create partition {partition_name}", error=str(e))
            
            logger.info("Table partitioning setup completed")
    
    async def store(self, request: StorageRequest) -> StorageResponse:
        """Store metadata for any type of data"""
        async with self.get_connection() as conn:
            
            # Generate storage ID
            storage_id = str(uuid.uuid4())
            
            # Calculate retention date
            retention_date = None
            if request.retention_days:
                retention_date = datetime.now() + timedelta(days=request.retention_days)
            else:
                # Use default retention based on data type
                default_days = {
                    DataType.WEATHER: self.settings.weather_data_retention_days,
                    DataType.SENSOR: self.settings.sensor_data_retention_days,
                    DataType.FIRE_DETECTION: self.settings.fire_detection_retention_days,
                    DataType.PREDICTIONS: self.settings.prediction_data_retention_days
                }.get(request.data_type, 365)  # Default 1 year
                retention_date = datetime.now() + timedelta(days=default_days)
            
            # Insert metadata
            await conn.execute("""
                INSERT INTO storage_metadata 
                (storage_id, data_type, source_id, backend, size_bytes, metadata, tags, retention_until)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """, storage_id, request.data_type.value, request.source_id, 
                StorageBackend.POSTGRESQL.value, len(str(request.data)), 
                json.dumps(request.metadata) if request.metadata else None,
                request.tags, retention_date)
            
            # Store actual data based on type
            if request.data_type == DataType.WEATHER:
                await self._store_weather_data(conn, storage_id, request.data)
            elif request.data_type == DataType.SENSOR:
                await self._store_sensor_data(conn, storage_id, request.data)
            elif request.data_type == DataType.FIRE_DETECTION:
                await self._store_fire_detection_data(conn, storage_id, request.data)
            elif request.data_type == DataType.PREDICTIONS:
                await self._store_prediction_data(conn, storage_id, request.data)
            
            # Log access for auditing
            await self._log_access(conn, "store", request.data_type.value, storage_id, 200)
            
            return StorageResponse(
                storage_id=storage_id,
                data_type=request.data_type,
                backend=StorageBackend.POSTGRESQL,
                size_bytes=len(str(request.data)),
                timestamp=datetime.now()
            )
    
    async def _store_weather_data(self, conn, storage_id: str, data: Union[Dict, List[Dict]]):
        """Store weather data in optimized table"""
        data_items = data if isinstance(data, list) else [data]
        
        for item in data_items:
            location = None
            if 'latitude' in item and 'longitude' in item:
                location = f"POINT({item['longitude']} {item['latitude']})"
            
            await conn.execute("""
                INSERT INTO weather_data 
                (storage_id, timestamp, location, temperature, humidity, wind_speed, 
                 wind_direction, pressure, precipitation, visibility, fire_weather_index, 
                 source, quality_score, raw_data)
                VALUES ($1, $2, ST_GeogFromText($3), $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
            """, 
                storage_id, 
                item.get('timestamp', datetime.now()),
                location,
                item.get('temperature'),
                item.get('humidity'),
                item.get('wind_speed'), 
                item.get('wind_direction'),
                item.get('pressure'),
                item.get('precipitation'),
                item.get('visibility'),
                item.get('fire_weather_index'),
                item.get('source'),
                item.get('quality_score'),
                json.dumps(item)
            )
    
    async def _store_sensor_data(self, conn, storage_id: str, data: Union[Dict, List[Dict]]):
        """Store sensor data in optimized table"""
        data_items = data if isinstance(data, list) else [data]
        
        for item in data_items:
            location = None
            if 'latitude' in item and 'longitude' in item:
                location = f"POINT({item['longitude']} {item['latitude']})"
            
            await conn.execute("""
                INSERT INTO sensor_data 
                (storage_id, sensor_id, timestamp, location, sensor_type, measurements,
                 air_quality_index, pm25, pm10, co2_ppm, battery_level, signal_strength, 
                 status, raw_data)
                VALUES ($1, $2, $3, ST_GeogFromText($4), $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
            """,
                storage_id,
                item.get('sensor_id'),
                item.get('timestamp', datetime.now()),
                location,
                item.get('sensor_type'),
                json.dumps(item.get('measurements', {})),
                item.get('air_quality_index'),
                item.get('pm25'),
                item.get('pm10'),
                item.get('co2_ppm'),
                item.get('battery_level'),
                item.get('signal_strength'),
                item.get('status', 'active'),
                json.dumps(item)
            )
    
    async def _store_fire_detection_data(self, conn, storage_id: str, data: Union[Dict, List[Dict]]):
        """Store fire detection data in optimized table"""
        data_items = data if isinstance(data, list) else [data]
        
        for item in data_items:
            location = f"POINT({item['longitude']} {item['latitude']})"
            
            await conn.execute("""
                INSERT INTO fire_detection_data 
                (storage_id, detection_time, location, confidence_level, satellite_sensor,
                 brightness_temp, fire_radiative_power, estimated_area_hectares, fire_type,
                 verification_status, alert_level, response_required, incident_id, raw_data)
                VALUES ($1, $2, ST_GeogFromText($3), $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
            """,
                storage_id,
                item.get('detection_time', item.get('timestamp', datetime.now())),
                location,
                item.get('confidence_level', item.get('confidence', 0)),
                item.get('satellite_sensor', item.get('sensor')),
                item.get('brightness_temp', item.get('brightness')),
                item.get('fire_radiative_power', item.get('frp')),
                item.get('estimated_area_hectares'),
                item.get('fire_type'),
                item.get('verification_status', 'unverified'),
                item.get('alert_level', 'medium'),
                item.get('response_required', False),
                item.get('incident_id'),
                json.dumps(item)
            )
    
    async def _store_prediction_data(self, conn, storage_id: str, data: Union[Dict, List[Dict]]):
        """Store prediction data in optimized table"""
        data_items = data if isinstance(data, list) else [data]
        
        for item in data_items:
            location = None
            if 'latitude' in item and 'longitude' in item:
                location = f"POINT({item['longitude']} {item['latitude']})"
            
            region_bounds = None
            if 'region_bounds' in item:
                # Expecting format: [[lat, lng], [lat, lng], ...]
                bounds = item['region_bounds']
                if len(bounds) >= 3:  # Minimum for polygon
                    polygon_points = ",".join([f"{lng} {lat}" for lat, lng in bounds])
                    region_bounds = f"POLYGON(({polygon_points}))"
            
            await conn.execute("""
                INSERT INTO prediction_data 
                (storage_id, model_name, model_version, prediction_time, forecast_horizon_hours,
                 location, region_bounds, prediction_type, fire_risk_score, weather_forecast,
                 fire_behavior_prediction, evacuation_recommendations, confidence_intervals,
                 model_inputs, raw_predictions)
                VALUES ($1, $2, $3, $4, $5, ST_GeogFromText($6), ST_GeogFromText($7), $8, $9, $10, $11, $12, $13, $14, $15)
            """,
                storage_id,
                item.get('model_name', 'unknown'),
                item.get('model_version'),
                item.get('prediction_time', datetime.now()),
                item.get('forecast_horizon_hours', 24),
                location,
                region_bounds,
                item.get('prediction_type', 'fire_risk'),
                item.get('fire_risk_score'),
                json.dumps(item.get('weather_forecast', {})),
                json.dumps(item.get('fire_behavior_prediction', {})),
                json.dumps(item.get('evacuation_recommendations', {})),
                json.dumps(item.get('confidence_intervals', {})),
                json.dumps(item.get('model_inputs', {})),
                json.dumps(item)
            )
    
    async def store_bulk(self, request: BulkStorageRequest) -> List[StorageResponse]:
        """Store multiple data items efficiently using transactions"""
        async with self.get_connection() as conn:
            async with conn.transaction():
                responses = []
                
                # Process in batches for better performance
                batch_size = self.settings.batch_insert_size
                for i in range(0, len(request.data_items), batch_size):
                    batch = request.data_items[i:i+batch_size]
                    
                    for item in batch:
                        # Create individual storage request for each item
                        item_request = StorageRequest(
                            data_type=request.data_type,
                            data=item,
                            metadata=request.metadata,
                            source_id=request.source_id,
                            tags=request.tags
                        )
                        
                        response = await self.store(item_request)
                        responses.append(response)
                
                # Log bulk operation
                await self._log_access(conn, "bulk_store", request.data_type.value, None, 200, 
                                      query_params={"batch_size": len(request.data_items)})
                
                return responses
    
    async def query(self, request: QueryRequest) -> QueryResponse:
        """Query data with flexible filtering"""
        start_time = datetime.now()
        
        async with self.get_connection() as conn:
            
            # Build query based on data type
            if request.data_type == DataType.WEATHER:
                data, total = await self._query_weather_data(conn, request)
            elif request.data_type == DataType.SENSOR:
                data, total = await self._query_sensor_data(conn, request)
            elif request.data_type == DataType.FIRE_DETECTION:
                data, total = await self._query_fire_detection_data(conn, request)
            elif request.data_type == DataType.PREDICTIONS:
                data, total = await self._query_prediction_data(conn, request)
            else:
                data, total = await self._query_metadata(conn, request)
            
            query_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # Log query access
            await self._log_access(conn, "query", request.data_type.value, None, 200,
                                  query_params=request.dict(), response_time_ms=int(query_time))
            
            return QueryResponse(
                data=data,
                total_records=total,
                data_type=request.data_type,
                query_time_ms=query_time,
                metadata={"request": request.dict()} if request.include_metadata else None
            )
    
    async def _query_weather_data(self, conn, request: QueryRequest):
        """Query weather data with optimized filtering"""
        where_conditions = ["1=1"]
        params = []
        param_count = 0
        
        # Time range filtering
        if request.start_time:
            param_count += 1
            where_conditions.append(f"timestamp >= ${param_count}")
            params.append(request.start_time)
        
        if request.end_time:
            param_count += 1
            where_conditions.append(f"timestamp <= ${param_count}")
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
                if key in ['source', 'quality_score', 'fire_weather_index']:
                    param_count += 1
                    if isinstance(value, dict) and 'min' in value:
                        # Range filter
                        where_conditions.append(f"{key} >= ${param_count}")
                        params.append(value['min'])
                        if 'max' in value:
                            param_count += 1
                            where_conditions.append(f"{key} <= ${param_count}")
                            params.append(value['max'])
                    else:
                        # Exact match
                        where_conditions.append(f"{key} = ${param_count}")
                        params.append(value)
        
        where_clause = " AND ".join(where_conditions)
        
        # Count total records
        count_query = f"""
            SELECT COUNT(*) FROM weather_data wd
            JOIN storage_metadata sm ON wd.storage_id = sm.storage_id
            WHERE {where_clause}
        """
        total = await conn.fetchval(count_query, *params)
        
        # Main data query
        order_by = "timestamp DESC"
        if request.aggregation and 'order_by' in request.aggregation:
            order_by = request.aggregation['order_by']
        
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
            SELECT 
                wd.*,
                ST_X(wd.location::geometry) as longitude,
                ST_Y(wd.location::geometry) as latitude,
                sm.tags, sm.metadata as storage_metadata
            FROM weather_data wd
            JOIN storage_metadata sm ON wd.storage_id = sm.storage_id
            WHERE {where_clause}
            ORDER BY {order_by}
            {limit_clause}
        """
        
        rows = await conn.fetch(data_query, *params)
        data = [dict(row) for row in rows]
        
        return data, total
    
    async def _query_sensor_data(self, conn, request: QueryRequest):
        """Query sensor data with optimized filtering"""
        # Similar structure to weather data but for sensors
        where_conditions = ["1=1"]
        params = []
        param_count = 0
        
        # Time range filtering
        if request.start_time:
            param_count += 1
            where_conditions.append(f"timestamp >= ${param_count}")
            params.append(request.start_time)
        
        if request.end_time:
            param_count += 1
            where_conditions.append(f"timestamp <= ${param_count}")
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
                if key in ['sensor_id', 'sensor_type', 'status']:
                    param_count += 1
                    where_conditions.append(f"{key} = ${param_count}")
                    params.append(value)
        
        where_clause = " AND ".join(where_conditions)
        
        # Count total records
        count_query = f"""
            SELECT COUNT(*) FROM sensor_data sd
            JOIN storage_metadata sm ON sd.storage_id = sm.storage_id
            WHERE {where_clause}
        """
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
            SELECT 
                sd.*,
                ST_X(sd.location::geometry) as longitude,
                ST_Y(sd.location::geometry) as latitude,
                sm.tags, sm.metadata as storage_metadata
            FROM sensor_data sd
            JOIN storage_metadata sm ON sd.storage_id = sm.storage_id
            WHERE {where_clause}
            ORDER BY timestamp DESC
            {limit_clause}
        """
        
        rows = await conn.fetch(data_query, *params)
        data = [dict(row) for row in rows]
        
        return data, total
    
    async def _query_fire_detection_data(self, conn, request: QueryRequest):
        """Query fire detection data with optimized filtering"""
        where_conditions = ["1=1"]
        params = []
        param_count = 0
        
        # Time range filtering
        if request.start_time:
            param_count += 1
            where_conditions.append(f"detection_time >= ${param_count}")
            params.append(request.start_time)
        
        if request.end_time:
            param_count += 1
            where_conditions.append(f"detection_time <= ${param_count}")
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
                if key in ['satellite_sensor', 'verification_status', 'alert_level', 'fire_type']:
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
        
        where_clause = " AND ".join(where_conditions)
        
        # Count total records
        count_query = f"""
            SELECT COUNT(*) FROM fire_detection_data fd
            JOIN storage_metadata sm ON fd.storage_id = sm.storage_id
            WHERE {where_clause}
        """
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
            SELECT 
                fd.*,
                ST_X(fd.location::geometry) as longitude,
                ST_Y(fd.location::geometry) as latitude,
                sm.tags, sm.metadata as storage_metadata
            FROM fire_detection_data fd
            JOIN storage_metadata sm ON fd.storage_id = sm.storage_id
            WHERE {where_clause}
            ORDER BY detection_time DESC, confidence_level DESC
            {limit_clause}
        """
        
        rows = await conn.fetch(data_query, *params)
        data = [dict(row) for row in rows]
        
        return data, total
    
    async def _query_prediction_data(self, conn, request: QueryRequest):
        """Query prediction data with model and time filtering"""
        where_conditions = ["1=1"]
        params = []
        param_count = 0
        
        # Time range filtering
        if request.start_time:
            param_count += 1
            where_conditions.append(f"prediction_time >= ${param_count}")
            params.append(request.start_time)
        
        if request.end_time:
            param_count += 1
            where_conditions.append(f"prediction_time <= ${param_count}")
            params.append(request.end_time)
        
        # Prediction-specific filters
        if request.filters:
            for key, value in request.filters.items():
                if key in ['model_name', 'model_version', 'prediction_type']:
                    param_count += 1
                    where_conditions.append(f"{key} = ${param_count}")
                    params.append(value)
                elif key == 'forecast_horizon_hours':
                    param_count += 1
                    where_conditions.append(f"forecast_horizon_hours = ${param_count}")
                    params.append(value)
        
        where_clause = " AND ".join(where_conditions)
        
        # Count total records
        count_query = f"""
            SELECT COUNT(*) FROM prediction_data pd
            JOIN storage_metadata sm ON pd.storage_id = sm.storage_id
            WHERE {where_clause}
        """
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
            SELECT 
                pd.*,
                CASE WHEN pd.location IS NOT NULL THEN ST_X(pd.location::geometry) END as longitude,
                CASE WHEN pd.location IS NOT NULL THEN ST_Y(pd.location::geometry) END as latitude,
                sm.tags, sm.metadata as storage_metadata
            FROM prediction_data pd
            JOIN storage_metadata sm ON pd.storage_id = sm.storage_id
            WHERE {where_clause}
            ORDER BY prediction_time DESC, fire_risk_score DESC
            {limit_clause}
        """
        
        rows = await conn.fetch(data_query, *params)
        data = [dict(row) for row in rows]
        
        return data, total
    
    async def _query_metadata(self, conn, request: QueryRequest):
        """Query storage metadata for other data types"""
        where_conditions = ["data_type = $1"]
        params = [request.data_type.value]
        param_count = 1
        
        # Time range filtering
        if request.start_time:
            param_count += 1
            where_conditions.append(f"created_at >= ${param_count}")
            params.append(request.start_time)
        
        if request.end_time:
            param_count += 1
            where_conditions.append(f"created_at <= ${param_count}")
            params.append(request.end_time)
        
        # Tag filtering
        if request.filters and 'tags' in request.filters:
            param_count += 1
            where_conditions.append(f"tags @> ${param_count}")
            params.append([request.filters['tags']])
        
        where_clause = " AND ".join(where_conditions)
        
        # Count total records
        count_query = f"SELECT COUNT(*) FROM storage_metadata WHERE {where_clause}"
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
            SELECT * FROM storage_metadata 
            WHERE {where_clause}
            ORDER BY created_at DESC
            {limit_clause}
        """
        
        rows = await conn.fetch(data_query, *params)
        data = [dict(row) for row in rows]
        
        return data, total
    
    async def get_by_id(self, storage_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve data by storage ID"""
        async with self.get_connection() as conn:
            # Get metadata first
            metadata = await conn.fetchrow(
                "SELECT * FROM storage_metadata WHERE storage_id = $1",
                storage_id
            )
            
            if not metadata:
                return None
            
            result = dict(metadata)
            
            # Get actual data based on type
            data_type = metadata['data_type']
            if data_type == 'weather':
                data = await conn.fetchrow(
                    "SELECT *, ST_X(location::geometry) as longitude, ST_Y(location::geometry) as latitude FROM weather_data WHERE storage_id = $1",
                    storage_id
                )
            elif data_type == 'sensor':
                data = await conn.fetchrow(
                    "SELECT *, ST_X(location::geometry) as longitude, ST_Y(location::geometry) as latitude FROM sensor_data WHERE storage_id = $1",
                    storage_id
                )
            elif data_type == 'fire_detection':
                data = await conn.fetchrow(
                    "SELECT *, ST_X(location::geometry) as longitude, ST_Y(location::geometry) as latitude FROM fire_detection_data WHERE storage_id = $1",
                    storage_id
                )
            elif data_type == 'predictions':
                data = await conn.fetchrow(
                    "SELECT *, CASE WHEN location IS NOT NULL THEN ST_X(location::geometry) END as longitude, CASE WHEN location IS NOT NULL THEN ST_Y(location::geometry) END as latitude FROM prediction_data WHERE storage_id = $1",
                    storage_id
                )
            else:
                data = None
            
            if data:
                result['data'] = dict(data)
            
            # Log access
            await self._log_access(conn, "retrieve", data_type, storage_id, 200)
            
            return result
    
    async def delete(self, storage_id: str) -> bool:
        """Delete data by storage ID"""
        async with self.get_connection() as conn:
            async with conn.transaction():
                # Check if record exists
                metadata = await conn.fetchrow(
                    "SELECT data_type FROM storage_metadata WHERE storage_id = $1",
                    storage_id
                )
                
                if not metadata:
                    return False
                
                # Delete from specific data table first (due to foreign key)
                data_type = metadata['data_type']
                if data_type == 'weather':
                    await conn.execute("DELETE FROM weather_data WHERE storage_id = $1", storage_id)
                elif data_type == 'sensor':
                    await conn.execute("DELETE FROM sensor_data WHERE storage_id = $1", storage_id)
                elif data_type == 'fire_detection':
                    await conn.execute("DELETE FROM fire_detection_data WHERE storage_id = $1", storage_id)
                elif data_type == 'predictions':
                    await conn.execute("DELETE FROM prediction_data WHERE storage_id = $1", storage_id)
                
                # Delete blob storage references
                await conn.execute("DELETE FROM blob_storage_refs WHERE storage_id = $1", storage_id)
                
                # Delete metadata
                await conn.execute("DELETE FROM storage_metadata WHERE storage_id = $1", storage_id)
                
                # Log access
                await self._log_access(conn, "delete", data_type, storage_id, 200)
                
                return True
    
    async def get_storage_stats(self) -> Dict[str, Any]:
        """Get comprehensive storage statistics"""
        async with self.get_connection() as conn:
            
            # Basic statistics by data type
            stats_query = """
                SELECT 
                    data_type,
                    COUNT(*) as total_records,
                    SUM(size_bytes) as total_size_bytes,
                    AVG(size_bytes) as avg_size_bytes,
                    MIN(created_at) as oldest_record,
                    MAX(created_at) as newest_record
                FROM storage_metadata 
                GROUP BY data_type
            """
            
            type_stats = await conn.fetch(stats_query)
            
            # Recent activity (last 24 hours)
            activity_query = """
                SELECT 
                    data_type,
                    COUNT(*) as records_last_24h,
                    SUM(size_bytes) as bytes_last_24h
                FROM storage_metadata 
                WHERE created_at >= NOW() - INTERVAL '24 hours'
                GROUP BY data_type
            """
            
            recent_activity = await conn.fetch(activity_query)
            
            # Storage efficiency and compression ratios
            compression_query = """
                SELECT 
                    AVG(compression_ratio) as avg_compression_ratio
                FROM archival_jobs 
                WHERE status = 'completed' AND compression_ratio IS NOT NULL
            """
            
            compression_ratio = await conn.fetchval(compression_query) or 1.0
            
            # Query performance metrics
            performance_query = """
                SELECT 
                    operation,
                    AVG(response_time_ms) as avg_response_time_ms,
                    COUNT(*) as total_operations
                FROM access_logs 
                WHERE accessed_at >= NOW() - INTERVAL '24 hours'
                GROUP BY operation
            """
            
            performance_stats = await conn.fetch(performance_query)
            
            # Database size information
            db_size_query = """
                SELECT 
                    schemaname,
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
                    pg_total_relation_size(schemaname||'.'||tablename) as size_bytes
                FROM pg_tables 
                WHERE schemaname = 'public'
                ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
            """
            
            table_sizes = await conn.fetch(db_size_query)
            
            return {
                "overview": {
                    "total_records": sum(row['total_records'] for row in type_stats),
                    "total_size_bytes": sum(row['total_size_bytes'] for row in type_stats),
                    "data_types": len(type_stats),
                    "avg_compression_ratio": float(compression_ratio),
                    "database_health": "healthy"  # Could be calculated based on various metrics
                },
                "by_data_type": [dict(row) for row in type_stats],
                "recent_activity": [dict(row) for row in recent_activity],
                "performance": [dict(row) for row in performance_stats],
                "storage_distribution": [dict(row) for row in table_sizes[:10]],  # Top 10 largest tables
                "timestamp": datetime.now().isoformat()
            }
    
    async def _log_access(self, conn, operation: str, data_type: Optional[str] = None, 
                         storage_id: Optional[str] = None, status_code: int = 200,
                         query_params: Optional[Dict] = None, response_time_ms: Optional[int] = None):
        """Log access for auditing and monitoring"""
        try:
            await conn.execute("""
                INSERT INTO access_logs 
                (operation, data_type, storage_id, query_params, response_time_ms, status_code)
                VALUES ($1, $2, $3, $4, $5, $6)
            """, operation, data_type, storage_id, 
                json.dumps(query_params) if query_params else None,
                response_time_ms, status_code)
        except Exception as e:
            # Don't fail the main operation if logging fails
            logger.warning("Failed to log access", error=str(e))
    
    async def cleanup_expired_data(self):
        """Clean up expired data based on retention policies"""
        async with self.get_connection() as conn:
            
            # Find expired records
            expired_query = """
                SELECT storage_id, data_type FROM storage_metadata 
                WHERE retention_until IS NOT NULL 
                AND retention_until < NOW()
                LIMIT 1000  -- Process in batches
            """
            
            expired_records = await conn.fetch(expired_query)
            
            deleted_count = 0
            for record in expired_records:
                try:
                    success = await self.delete(record['storage_id'])
                    if success:
                        deleted_count += 1
                except Exception as e:
                    logger.warning("Failed to delete expired record", 
                                  storage_id=record['storage_id'], error=str(e))
            
            logger.info("Cleaned up expired data", deleted_count=deleted_count)
            return deleted_count
    
    async def update_storage_statistics(self):
        """Update storage statistics table for monitoring"""
        async with self.get_connection() as conn:
            
            # Update statistics for each data type
            data_types = ['weather', 'sensor', 'fire_detection', 'predictions', 'satellite_image', 'model_file', 'archive', 'metadata']
            
            for data_type in data_types:
                try:
                    # Get current statistics
                    stats_query = """
                        SELECT 
                            COUNT(*) as total_records,
                            COALESCE(SUM(size_bytes), 0) as total_size_bytes,
                            COALESCE(AVG(size_bytes), 0)::INTEGER as avg_record_size_bytes,
                            MIN(created_at) as oldest_record,
                            MAX(created_at) as newest_record
                        FROM storage_metadata 
                        WHERE data_type = $1
                    """
                    
                    stats = await conn.fetchrow(stats_query, data_type)
                    
                    # Count recent records
                    recent_hour_count = await conn.fetchval("""
                        SELECT COUNT(*) FROM storage_metadata 
                        WHERE data_type = $1 AND created_at >= NOW() - INTERVAL '1 hour'
                    """, data_type)
                    
                    recent_day_count = await conn.fetchval("""
                        SELECT COUNT(*) FROM storage_metadata 
                        WHERE data_type = $1 AND created_at >= NOW() - INTERVAL '1 day'
                    """, data_type)
                    
                    # Calculate storage efficiency (simple metric)
                    storage_efficiency = min(1.0, stats['total_records'] / max(1, stats['total_size_bytes'] / 1000))
                    
                    # Insert or update statistics
                    await conn.execute("""
                        INSERT INTO storage_statistics 
                        (data_type, total_records, total_size_bytes, avg_record_size_bytes,
                         oldest_record, newest_record, records_last_hour, records_last_day, 
                         storage_efficiency)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                        ON CONFLICT (data_type, date_trunc('hour', recorded_at))
                        DO UPDATE SET
                            total_records = EXCLUDED.total_records,
                            total_size_bytes = EXCLUDED.total_size_bytes,
                            avg_record_size_bytes = EXCLUDED.avg_record_size_bytes,
                            oldest_record = EXCLUDED.oldest_record,
                            newest_record = EXCLUDED.newest_record,
                            records_last_hour = EXCLUDED.records_last_hour,
                            records_last_day = EXCLUDED.records_last_day,
                            storage_efficiency = EXCLUDED.storage_efficiency
                    """, 
                        data_type,
                        stats['total_records'],
                        stats['total_size_bytes'], 
                        stats['avg_record_size_bytes'],
                        stats['oldest_record'],
                        stats['newest_record'],
                        recent_hour_count,
                        recent_day_count,
                        storage_efficiency
                    )
                    
                except Exception as e:
                    logger.warning("Failed to update statistics", data_type=data_type, error=str(e))
            
            logger.info("Storage statistics updated successfully")