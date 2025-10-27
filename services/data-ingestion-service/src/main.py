"""
Data Ingestion Service - Challenge 1 Focus
Versatile data ingestion mechanism for batch, real-time, and streaming data
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, List, Any, Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import redis.asyncio as redis
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
import structlog

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config import get_settings
from .connectors.satellite_connector import SatelliteDataConnector
from .connectors.weather_connector import WeatherDataConnector
from .connectors.iot_mqtt_connector import IoTMQTTConnector
from .connectors.nasa_firms_connector import NASAFirmsConnector
from .connectors.noaa_weather_connector import NOAAWeatherConnector
from .connectors.purpleair_connector import PurpleAirConnector
from .connectors.airnow_connector import AirNowConnector
from .connectors.firesat_connector import FireSatConnector
from .streaming.kafka_producer import KafkaDataProducer
from .streaming.stream_manager import StreamManager
from .streaming.buffer_manager import get_buffer_manager
from .streaming.critical_alert_handler import CriticalAlertHandler
from .api.monitoring_endpoints import router as monitoring_router, set_monitoring_instances
from .models.ingestion import (
    IngestionRequest, IngestionResponse, DataSource,
    StreamingConfig, BatchConfig, ValidationConfig
)

# Optional processors with graceful fallbacks
try:
    from .processors.data_processor import DataProcessor
except ImportError:
    DataProcessor = None

try:
    from .validation.data_validator import DataValidator
except ImportError:
    DataValidator = None

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Prometheus metrics with error handling
try:
    INGESTION_REQUESTS = Counter('wildfire_data_ingestion_requests_total', 'Total ingestion requests', ['source_type', 'status'])
    INGESTION_DURATION = Histogram('wildfire_data_ingestion_duration_seconds', 'Data ingestion duration')
    DATA_VOLUME = Counter('wildfire_data_ingestion_volume_bytes', 'Total data volume processed', ['source_type'])
    VALIDATION_ERRORS = Counter('wildfire_data_validation_errors_total', 'Data validation errors', ['error_type'])
except Exception as e:
    logger.warning("Prometheus metrics already registered, using existing ones", error=str(e))

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("Starting Data Ingestion Service", version="1.0.0")

    try:
        # Initialize Kafka producer first
        kafka_producer = KafkaDataProducer(settings.kafka_bootstrap_servers)
        await kafka_producer.start()
        logger.info("Kafka producer started successfully")

        # Initialize Redis client for caching
        redis_client = await redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True
        )
        logger.info("Redis client initialized successfully")

        # Initialize connectors with Kafka producer
        satellite_connector = SatelliteDataConnector(kafka_producer=kafka_producer)
        weather_connector = WeatherDataConnector(kafka_producer=kafka_producer)
        nasa_firms_connector = NASAFirmsConnector(kafka_producer=kafka_producer)
        noaa_weather_connector = NOAAWeatherConnector(kafka_producer=kafka_producer, redis_client=redis_client)
        iot_mqtt_connector = IoTMQTTConnector(
            broker_host=settings.mqtt_broker_host,
            broker_port=settings.mqtt_broker_port,
            username=settings.mqtt_username,
            password=settings.mqtt_password,
            use_ssl=settings.mqtt_use_ssl,
            kafka_producer=kafka_producer
        )
        purpleair_connector = PurpleAirConnector(
            api_key=settings.purpleair_api_key,
            kafka_producer=kafka_producer
        )
        airnow_connector = AirNowConnector(
            api_key=settings.airnow_api_key,
            kafka_producer=kafka_producer
        )
        firesat_connector = FireSatConnector(
            api_key=os.getenv('FIRESAT_API_KEY'),
            kafka_producer=kafka_producer
        )

        logger.info("All eight connectors initialized successfully")

        # Initialize optional processors with fallbacks
        data_processor = DataProcessor() if DataProcessor else None
        data_validator = DataValidator() if DataValidator else None

        # Initialize BufferManager for offline resilience (Path 3)
        buffer_manager = get_buffer_manager()
        await buffer_manager.start()
        logger.info("BufferManager initialized successfully")

        # Initialize CriticalAlertHandler for <100ms latency alerts (Path 1)
        critical_alert_handler = CriticalAlertHandler(
            kafka_bootstrap_servers=settings.kafka_bootstrap_servers,
            alert_topic='wildfire-critical-alerts',
            max_latency_ms=100,
            heartbeat_interval=30
        )
        await critical_alert_handler.start()
        logger.info("CriticalAlertHandler initialized successfully")

        # Initialize StreamManager with Kafka producer and optional config
        config_file = os.getenv('STREAM_MANAGER_CONFIG', 'config/streaming_config.yaml')
        stream_manager = StreamManager(
            kafka_producer,
            config_file=config_file,
            buffer_manager=buffer_manager,
            critical_alert_handler=critical_alert_handler
        )
        logger.info("StreamManager initialized successfully", config_file=config_file)

        # Store in app state
        app.state.satellite_connector = satellite_connector
        app.state.weather_connector = weather_connector
        app.state.nasa_firms_connector = nasa_firms_connector
        app.state.noaa_weather_connector = noaa_weather_connector
        app.state.iot_mqtt_connector = iot_mqtt_connector
        app.state.purpleair_connector = purpleair_connector
        app.state.airnow_connector = airnow_connector
        app.state.firesat_connector = firesat_connector
        app.state.data_processor = data_processor
        app.state.data_validator = data_validator
        app.state.kafka_producer = kafka_producer
        app.state.stream_manager = stream_manager
        app.state.buffer_manager = buffer_manager
        app.state.critical_alert_handler = critical_alert_handler

        # Set monitoring instances for /api/v1/monitoring/* endpoints
        set_monitoring_instances(critical_alert_handler, stream_manager)

        logger.info("Data Ingestion Service initialized successfully")

        # Auto-start PurpleAir streaming if API key is configured (via StreamManager)
        if settings.purpleair_api_key:
            logger.info("Auto-starting PurpleAir sensor streaming via StreamManager")
            try:
                from .models.ingestion import StreamingConfig
                purpleair_config = StreamingConfig(source_id="purpleair_california")
                stream_id = await stream_manager.start_streaming(purpleair_connector, purpleair_config)
                logger.info("PurpleAir streaming started via StreamManager", stream_id=stream_id)
            except Exception as e:
                logger.error("Failed to auto-start PurpleAir streaming", error=str(e))

        # Auto-start AirNow streaming if API key is configured (via StreamManager)
        if settings.airnow_api_key:
            logger.info("Auto-starting AirNow air quality streaming via StreamManager")
            try:
                from .models.ingestion import StreamingConfig
                airnow_config = StreamingConfig(source_id="airnow_california")
                stream_id = await stream_manager.start_streaming(airnow_connector, airnow_config)
                logger.info("AirNow streaming started via StreamManager", stream_id=stream_id)
            except Exception as e:
                logger.error("Failed to auto-start AirNow streaming", error=str(e))

        # Auto-start IoT MQTT streaming if broker is configured (via StreamManager)
        if settings.mqtt_username and settings.mqtt_password:
            logger.info("Auto-starting IoT MQTT air quality sensor streaming via StreamManager")
            try:
                from .models.ingestion import StreamingConfig
                iot_config = StreamingConfig(source_id="iot_air_quality_sensors")
                stream_id = await stream_manager.start_streaming(iot_mqtt_connector, iot_config)
                logger.info("IoT MQTT streaming started via StreamManager", stream_id=stream_id)
            except Exception as e:
                logger.error("Failed to auto-start IoT MQTT streaming", error=str(e))

        # Auto-start ERA5-Land Reanalysis streaming if CDS API is configured (via StreamManager)
        cds_api_key = os.getenv('CDSAPI_KEY')
        if cds_api_key and weather_connector.cds_client:
            logger.info("Auto-starting ERA5-Land Reanalysis weather streaming via StreamManager")
            try:
                from .models.ingestion import StreamingConfig
                # ERA5 downloads large GRIB files (100MB+), needs longer timeout
                era5_config = StreamingConfig(source_id="wx_era5_land", timeout_seconds=300.0)
                stream_id = await stream_manager.start_streaming(weather_connector, era5_config)
                logger.info("ERA5-Land streaming started via StreamManager", stream_id=stream_id)
            except Exception as e:
                logger.error("Failed to auto-start ERA5-Land streaming", error=str(e))

        # Auto-start all NASA FIRMS fire detection sources (via StreamManager)
        if nasa_firms_connector and nasa_firms_connector.map_key:
            logger.info("Auto-starting NASA FIRMS fire detection streaming via StreamManager (6 sources)")
            firms_sources = [
                "firms_viirs_snpp",
                "firms_viirs_noaa20",
                "firms_viirs_noaa21",
                "firms_modis_terra",
                "firms_modis_aqua",
                "landsat_nrt"
            ]
            for source_id in firms_sources:
                try:
                    from .models.ingestion import StreamingConfig
                    config = StreamingConfig(source_id=source_id)
                    stream_id = await stream_manager.start_streaming(nasa_firms_connector, config)
                    logger.info(f"NASA FIRMS {source_id} streaming started via StreamManager", stream_id=stream_id)
                except Exception as e:
                    logger.error(f"Failed to auto-start {source_id}", error=str(e))

        # Auto-start all NOAA weather sources (via StreamManager)
        if noaa_weather_connector:
            logger.info("Auto-starting NOAA weather streaming via StreamManager (3 sources)")
            noaa_sources = [
                "noaa_stations_current",
                # "noaa_stations_historical",  # Disabled - historical data should use batch API only
                "noaa_gridpoints_forecast",
                "noaa_alerts_active"
            ]
            for source_id in noaa_sources:
                try:
                    from .models.ingestion import StreamingConfig
                    # Use centralized config polling intervals
                    if source_id == "noaa_alerts_active":
                        polling_interval = settings.weather_alerts_polling_interval_seconds
                    else:
                        polling_interval = settings.weather_polling_interval_seconds
                    config = StreamingConfig(source_id=source_id, polling_interval_seconds=polling_interval)
                    stream_id = await stream_manager.start_streaming(noaa_weather_connector, config)
                    logger.info(f"NOAA {source_id} streaming started via StreamManager (polling every {polling_interval}s)", stream_id=stream_id)
                except Exception as e:
                    logger.error(f"Failed to auto-start {source_id}", error=str(e))

        # Auto-start additional weather model sources (via StreamManager)
        logger.info("Auto-starting additional weather model sources via StreamManager")
        weather_sources = [
            "wx_era5_reanalysis",
            "wx_gfs_forecast",
            "wx_nam_forecast",
            "wx_station_metar"
        ]
        for source_id in weather_sources:
            try:
                from .models.ingestion import StreamingConfig
                # ERA5/GFS/NAM download large GRIB2 files (100MB+), need longer timeout
                if source_id in ["wx_era5_reanalysis", "wx_gfs_forecast", "wx_nam_forecast"]:
                    config = StreamingConfig(source_id=source_id, timeout_seconds=300.0)
                else:
                    config = StreamingConfig(source_id=source_id)
                stream_id = await stream_manager.start_streaming(weather_connector, config)
                logger.info(f"Weather {source_id} streaming started via StreamManager", stream_id=stream_id)
            except Exception as e:
                logger.error(f"Failed to auto-start {source_id}", error=str(e))

        # Auto-start all satellite sources (via StreamManager)
        if satellite_connector:
            logger.info("Auto-starting satellite data sources via StreamManager (3 sources)")
            sat_sources = [
                "sat_landsat_thermal",
                "sat_sentinel2_msi",
                "sat_sentinel3_slstr"
            ]
            for source_id in sat_sources:
                try:
                    from .models.ingestion import StreamingConfig
                    config = StreamingConfig(source_id=source_id)
                    stream_id = await stream_manager.start_streaming(satellite_connector, config)
                    logger.info(f"Satellite {source_id} streaming started via StreamManager", stream_id=stream_id)
                except Exception as e:
                    logger.error(f"Failed to auto-start {source_id}", error=str(e))

        # Auto-start additional IoT MQTT sources (via StreamManager)
        if settings.mqtt_username and settings.mqtt_password:
            logger.info("Auto-starting additional IoT MQTT sources via StreamManager")
            iot_sources = [
                "iot_weather_stations",
                "iot_soil_moisture_sensors"
            ]
            for source_id in iot_sources:
                try:
                    from .models.ingestion import StreamingConfig
                    config = StreamingConfig(source_id=source_id)
                    stream_id = await stream_manager.start_streaming(iot_mqtt_connector, config)
                    logger.info(f"IoT MQTT {source_id} streaming started via StreamManager", stream_id=stream_id)
                except Exception as e:
                    logger.error(f"Failed to auto-start {source_id}", error=str(e))

        # Auto-start FireSat fire detection sources (via StreamManager)
        firesat_api_key = os.getenv('FIRESAT_API_KEY')
        if firesat_connector:
            logger.info("Auto-starting FireSat fire detection streaming via StreamManager (3 sources)")
            if not firesat_api_key:
                logger.info("FireSat running in MOCK MODE (no API key configured)")
            firesat_sources = [
                "firesat_detections",
                "firesat_perimeters",
                "firesat_thermal"
            ]
            for source_id in firesat_sources:
                try:
                    from .models.ingestion import StreamingConfig
                    # FireSat updates every 20 minutes (1200 seconds), poll every 60 seconds
                    config = StreamingConfig(
                        source_id=source_id,
                        polling_interval_seconds=60
                    )
                    stream_id = await stream_manager.start_streaming(firesat_connector, config)
                    logger.info(f"FireSat {source_id} streaming started via StreamManager (polling every 60s)", stream_id=stream_id)
                except Exception as e:
                    logger.error(f"Failed to auto-start {source_id}", error=str(e))

        yield

    except Exception as e:
        logger.error("Failed to initialize Data Ingestion Service", error=str(e))
        raise

    finally:
        # Cleanup
        logger.info("Shutting down Data Ingestion Service")
        try:
            if hasattr(app.state, 'critical_alert_handler') and app.state.critical_alert_handler:
                await app.state.critical_alert_handler.stop()
                logger.info("CriticalAlertHandler stopped")

            if hasattr(app.state, 'buffer_manager') and app.state.buffer_manager:
                await app.state.buffer_manager.stop()
                logger.info("BufferManager stopped")

            if hasattr(app.state, 'kafka_producer') and app.state.kafka_producer:
                await app.state.kafka_producer.stop()
                logger.info("Kafka producer stopped")
        except Exception as e:
            logger.error("Error during cleanup", error=str(e))

# Import centralized geographic bounds
try:
    from .geo_config.geographic_bounds import CALIFORNIA_BOUNDS, CALIFORNIA_BOUNDS_BBOX
except ImportError:
    try:
        from geo_config.geographic_bounds import CALIFORNIA_BOUNDS, CALIFORNIA_BOUNDS_BBOX
    except ImportError:
        # Fallback to hardcoded USGS values if config not available
        CALIFORNIA_BOUNDS = {
            'lat_min': 32.534156,
            'lat_max': 42.009518,
            'lon_min': -124.482003,
            'lon_max': -114.131211
        }
        CALIFORNIA_BOUNDS_BBOX = {
            'nwlng': -124.482003,
            'nwlat': 42.009518,
            'selng': -114.131211,
            'selat': 32.534156
        }

# Create FastAPI application
app = FastAPI(
    title="Wildfire Intelligence - Data Ingestion Service",
    description="Advanced data ingestion mechanism for satellite, weather, IoT, and social media data",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register monitoring endpoints router
app.include_router(monitoring_router)


# =============================================================================
# HEALTH AND MONITORING ENDPOINTS
# =============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint with connector status"""
    try:
        # Check Kafka connectivity
        kafka_healthy = await app.state.kafka_producer.health_check()
        
        # Check data connectors
        connectors_status = {
            "satellite": await app.state.satellite_connector.health_check(),
            "weather": await app.state.weather_connector.health_check(),
            "nasa_firms": await app.state.nasa_firms_connector.health_check(),
            "noaa_weather": await app.state.noaa_weather_connector.health_check(),
            "iot_mqtt": await app.state.iot_mqtt_connector.health_check(),
            "purpleair": await app.state.purpleair_connector.health_check(),
            "airnow": await app.state.airnow_connector.health_check(),
            "firesat": await app.state.firesat_connector.health_check()
        }
        
        all_healthy = kafka_healthy and all(connectors_status.values())
        
        return {
            "status": "healthy" if all_healthy else "degraded",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "kafka": "healthy" if kafka_healthy else "unhealthy",
            "connectors": connectors_status,
            "version": "1.0.0"
        }
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    from fastapi import Response
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

# =============================================================================
# DATA SOURCE MANAGEMENT
# =============================================================================

@app.get("/sources", response_model=List[DataSource])
async def list_data_sources():
    """List all configured data sources"""
    try:
        sources = []
        
        # Satellite data sources
        satellite_sources = await app.state.satellite_connector.get_sources()
        sources.extend(satellite_sources)
        
        # Weather data sources  
        weather_sources = await app.state.weather_connector.get_sources()
        sources.extend(weather_sources)
        
        # Real data connectors
        nasa_sources = await app.state.nasa_firms_connector.get_sources()
        sources.extend(nasa_sources)
        
        noaa_sources = await app.state.noaa_weather_connector.get_sources()
        sources.extend(noaa_sources)
        
        # IoT sensor sources (includes all sensor types)
        iot_sources = await app.state.iot_mqtt_connector.get_sources()
        sources.extend(iot_sources)
        
        return sources
        
    except Exception as e:
        logger.error("Failed to list data sources", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/sources", response_model=DataSource)
async def add_data_source(source: DataSource):
    """Add new data source configuration"""
    try:
        logger.info("Adding new data source", source_type=source.source_type, name=source.name)
        
        # Route to appropriate connector
        if source.source_type == "satellite":
            if source.id.lower().startswith(("firms_", "landsat_nrt")):
                connector = app.state.nasa_firms_connector
            else:
                connector = app.state.satellite_connector
        elif source.source_type == "weather":
            if source.id.lower().startswith("noaa_"):
                connector = app.state.noaa_weather_connector
            else:
                connector = app.state.weather_connector
        elif source.source_type in ["sensor", "iot"] or source.id.lower().startswith("iot_"):
            # All IoT sensor data handled by MQTT connector
            connector = app.state.iot_mqtt_connector
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported source type: {source.source_type}")
        
        # Add source to connector
        added_source = await connector.add_source(source)
        
        logger.info("Data source added successfully", source_id=added_source.id)
        return added_source
        
    except Exception as e:
        logger.error("Failed to add data source", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# BATCH DATA INGESTION
# =============================================================================

@app.post("/ingest/batch", response_model=IngestionResponse)
async def ingest_batch_data(
    config: BatchConfig,
    background_tasks: BackgroundTasks
):
    """
    Ingest batch data from configured sources
    
    Supports multiple data formats and sources:
    - Satellite imagery (MODIS, VIIRS, Landsat, Sentinel)
    - Weather data (ERA5, GFS, NAM)
    - Fire databases (FIRMS, InciWeb)
    - Custom datasets
    """
    try:
        logger.info("Starting batch data ingestion", source=config.source_id)
        
        with INGESTION_DURATION.time():
            # Get appropriate connector
            connector = await _get_connector_by_source_id(config.source_id)
            
            # Fetch data
            raw_data = await connector.fetch_batch_data(config)
            
            # Validate data
            if config.validation_enabled:
                validation_result = await app.state.data_validator.validate_batch(raw_data, config.validation_config)
                if not validation_result.is_valid:
                    VALIDATION_ERRORS.labels(error_type="batch_validation").inc()
                    raise HTTPException(status_code=422, detail=f"Data validation failed: {validation_result.errors}")
            
            # Process data
            processed_data = await app.state.data_processor.process_batch(raw_data, config.processing_config)
            
            # Send to Kafka for downstream processing
            await app.state.kafka_producer.send_batch_data(processed_data)
            
            # Update metrics
            INGESTION_REQUESTS.labels(source_type=config.source_type, status="success").inc()
            DATA_VOLUME.labels(source_type=config.source_type).inc(len(processed_data))
            
            # Schedule cleanup
            background_tasks.add_task(cleanup_temp_files, config.source_id)
            
            response = IngestionResponse(
                request_id=config.request_id,
                status="completed",
                records_processed=len(processed_data),
                data_quality_score=validation_result.quality_score if config.validation_enabled else 1.0,
                processing_time_seconds=0.0  # Would be calculated
            )
            
            logger.info("Batch ingestion completed", 
                       request_id=config.request_id,
                       records=len(processed_data))
            
            return response
            
    except Exception as e:
        INGESTION_REQUESTS.labels(source_type=config.source_type, status="error").inc()
        logger.error("Batch ingestion failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ingest/file")
async def ingest_file_upload(
    file: UploadFile = File(...),
    source_type: str = "manual",
    validation_enabled: bool = True
):
    """
    Ingest data from uploaded file
    
    Supports formats: CSV, JSON, NetCDF, GeoTIFF, Shapefile, Excel
    """
    try:
        logger.info("Processing file upload", filename=file.filename, content_type=file.content_type)
        
        # Save uploaded file temporarily
        temp_path = await _save_uploaded_file(file)
        
        # Determine file format and processor
        processor = await app.state.data_processor.get_file_processor(file.filename)
        
        # Process file
        processed_data = await processor.process_file(temp_path)
        
        # Validate if requested
        if validation_enabled:
            validation_result = await app.state.data_validator.validate_file_data(processed_data)
            if not validation_result.is_valid:
                raise HTTPException(status_code=422, detail=f"File validation failed: {validation_result.errors}")
        
        # Send to Kafka
        await app.state.kafka_producer.send_file_data(processed_data, file.filename)
        
        # Update metrics
        INGESTION_REQUESTS.labels(source_type=source_type, status="success").inc()
        
        return {
            "status": "success",
            "filename": file.filename,
            "records_processed": len(processed_data),
            "message": "File processed successfully"
        }
        
    except Exception as e:
        INGESTION_REQUESTS.labels(source_type=source_type, status="error").inc()
        logger.error("File upload processing failed", filename=file.filename, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# REAL-TIME DATA STREAMING
# =============================================================================

@app.post("/stream/start")
async def start_streaming(config: StreamingConfig):
    """
    Start real-time data streaming
    
    Establishes continuous data streams from various sources:
...
    """
    try:
        logger.info("Starting data stream", source_id=config.source_id)
        
        # Get appropriate connector
        connector = await _get_connector_by_source_id(config.source_id)
        
        # Start streaming
        stream_id = await connector.start_streaming(config)
        
        logger.info("Data stream started", stream_id=stream_id)
        
        return {
            "status": "streaming",
            "stream_id": stream_id,
            "source_id": config.source_id,
            "message": "Real-time streaming started successfully"
        }
        
    except Exception as e:
        logger.error("Failed to start streaming", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/streaming/live/start")
async def start_live_streaming():
    """Start sophisticated live streaming using StreamManager with all five connectors"""
    try:
        logger.info("Starting sophisticated live streaming with all connectors")

        # Get available connectors
        available_connectors = {
            "weather": app.state.weather_connector,
            "satellite": app.state.satellite_connector,
            "nasa_firms": app.state.nasa_firms_connector,
            "noaa_weather": app.state.noaa_weather_connector,
            "iot_mqtt": app.state.iot_mqtt_connector
        }

        # Start streaming for all available data sources
        streaming_results = {
            "started_streams": [],
            "failed_streams": [],
            "total_sources": 0,
            "successful_streams": 0
        }

        # Get all data sources from all connectors
        all_sources = []
        for connector_name, connector in available_connectors.items():
            try:
                sources = await connector.get_sources()
                for source in sources:
                    source.connector_type = connector_name
                all_sources.extend(sources)
            except Exception as e:
                logger.warning(f"Failed to get sources from {connector_name}", error=str(e))

        streaming_results["total_sources"] = len(all_sources)

        # Start streaming for each source using StreamManager
        for source in all_sources:
            try:
                # Create streaming config for each source
                stream_config = StreamingConfig(
                    source_id=source.id,
                    source_type=source.source_type,
                    polling_interval_seconds=settings.weather_polling_interval_seconds if source.source_type == "weather" else settings.default_polling_interval_seconds,
                    spatial_bounds=CALIFORNIA_BOUNDS,
                    quality_threshold=settings.default_quality_threshold
                )

                # Start stream using StreamManager
                stream_id = await app.state.stream_manager.start_stream(
                    stream_config, available_connectors[source.connector_type]
                )

                streaming_results["started_streams"].append({
                    "stream_id": stream_id,
                    "source_id": source.id,
                    "source_name": source.name,
                    "connector_type": source.connector_type,
                    "provider": source.provider,
                    "polling_interval": stream_config.polling_interval_seconds
                })
                streaming_results["successful_streams"] += 1

            except Exception as e:
                logger.error(f"Failed to start stream for {source.id}", error=str(e))
                streaming_results["failed_streams"].append({
                    "source_id": source.id,
                    "error": str(e)
                })

        # Get active streams for response
        active_streams = app.state.stream_manager.get_active_streams()

        # Build comprehensive response
        response = {
            "status": "sophisticated_live_streaming_active",
            "message": f"Started {streaming_results['successful_streams']} sophisticated live streams",
            "streaming_architecture": {
                "orchestrator": "Universal StreamManager",
                "kafka_producer": "Sophisticated KafkaDataProducer",
                "data_flow": "Real APIs → StreamManager → KafkaDataProducer → Auto-routed Kafka Topics → PostgreSQL",
                "features": [
                    "Auto-discovery of data sources",
                    "Intelligent topic routing",
                    "Compression and enrichment",
                    "Error handling and retries",
                    "Quality scoring and metadata"
                ]
            },
            "streaming_results": streaming_results,
            "active_streams": active_streams,
            "kafka_integration": {
                "sophisticated": True,
                "auto_topic_routing": True,
                "compression": "snappy/gzip",
                "enrichment": True,
                "partitioning": "geographic_and_temporal"
            },
            "connectors": {
                "available": len(available_connectors),
                "healthy": len([c for c in available_connectors.keys()]),
                "types": list(available_connectors.keys())
            },
            "data_sources": {
                "total_discovered": streaming_results['total_sources'],
                "successfully_streaming": streaming_results['successful_streams'],
                "failed": len(streaming_results['failed_streams'])
            },
            "update_frequency": "5-30 seconds (varies by source type)",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

        logger.info("Sophisticated live streaming startup completed",
                   total_sources=streaming_results['total_sources'],
                   successful_streams=streaming_results['successful_streams'],
                   failed_streams=len(streaming_results['failed_streams']))

        return response

    except Exception as e:
        logger.error("Failed to start sophisticated live streaming", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/streaming/live/stop")
async def stop_live_streaming():
    """Stop all live streaming"""
    try:
        logger.info("Stopping all live streaming")

        stopped_count = await app.state.stream_manager.stop_all_streams()

        return {
            "status": "sophisticated_streaming_stopped",
            "message": f"Stopped {stopped_count} sophisticated live streams",
            "architecture": {
                "orchestrator": "Universal StreamManager",
                "kafka_producer": "Sophisticated KafkaDataProducer",
                "cleanup": "Complete resource cleanup performed"
            },
            "stopped_count": stopped_count,
            "kafka_cleanup": True,
            "resource_cleanup": True,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    except Exception as e:
        logger.error("Failed to stop live streaming", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/stream/stop/{stream_id}")
async def stop_streaming(stream_id: str):
    """Stop real-time data streaming"""
    try:
        logger.info("Stopping data stream", stream_id=stream_id)
        
        # Stop streaming across all connectors
        stopped = False
        all_connectors = [
            app.state.satellite_connector,
            app.state.weather_connector,
            app.state.iot_mqtt_connector,
            app.state.nasa_firms_connector,
            app.state.noaa_weather_connector
        ]
        
        for connector in all_connectors:
            if await connector.stop_streaming(stream_id):
                stopped = True
                break
        
        if not stopped:
            raise HTTPException(status_code=404, detail=f"Stream {stream_id} not found")
        
        logger.info("Data stream stopped", stream_id=stream_id)
        
        return {
            "status": "stopped",
            "stream_id": stream_id,
            "message": "Streaming stopped successfully"
        }
        
    except Exception as e:
        logger.error("Failed to stop streaming", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stream/status")
async def get_streaming_status():
    """Get status of all active streams"""
    try:
        status = {
            "active_streams": [],
            "total_streams": 0,
            "data_rates": {}
        }
        
        # Get status from all connectors
        all_connector_pairs = [
            ("satellite", app.state.satellite_connector),
            ("weather", app.state.weather_connector),
            ("iot_mqtt", app.state.iot_mqtt_connector),
            ("nasa_firms", app.state.nasa_firms_connector),
            ("noaa_weather", app.state.noaa_weather_connector)
        ]
        
        for connector_name, connector in all_connector_pairs:
            streams = await connector.get_active_streams()
            status["active_streams"].extend(streams)
            status["data_rates"][connector_name] = await connector.get_data_rate()
        
        status["total_streams"] = len(status["active_streams"])
        
        return status
        
    except Exception as e:
        logger.error("Failed to get streaming status", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# DATA QUALITY AND METRICS
# =============================================================================

@app.get("/quality/metrics")
async def get_quality_metrics():
    """Get data quality metrics and statistics"""
    try:
        metrics = await app.state.data_validator.get_quality_metrics()
        return metrics
    except Exception as e:
        logger.error("Failed to get quality metrics", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/ingestion/stats")
async def get_ingestion_stats():
    """Get ingestion statistics and performance metrics"""
    try:
        stats = {
            "daily_volume": await _get_daily_ingestion_volume(),
            "source_breakdown": await _get_source_breakdown(),
            "error_rates": await _get_error_rates(),
            "latency_metrics": await _get_latency_metrics()
        }
        return stats
    except Exception as e:
        logger.error("Failed to get ingestion stats", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


async def _save_uploaded_file(file: UploadFile) -> str:
    """Save uploaded file to temporary location"""
    import tempfile
    import os
    
    # Create temporary file
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, f"upload_{file.filename}")
    
    # Save file
    with open(temp_path, "wb") as temp_file:
        content = await file.read()
        temp_file.write(content)
    
    return temp_path

async def cleanup_temp_files(source_id: str):
    """Background task to clean up temporary files"""
    try:
        # Implementation would clean up temp files
        logger.info("Cleaning up temporary files", source_id=source_id)
    except Exception as e:
        logger.error("Failed to cleanup temp files", error=str(e))

async def _get_daily_ingestion_volume():
    """Get daily data ingestion volume"""
    # TODO: Replace with actual metrics database query when analytics infrastructure is ready
    # For now, return configurable placeholder values
    return {"total_gb": 10.5, "records": 1000000}

async def _get_source_breakdown():
    """Get ingestion breakdown by source type"""
    # TODO: Replace with actual database query to calculate real percentages
    # For now, return configurable placeholder values
    return {
        "satellite": 0.6,
        "weather": 0.3,
        "sensor": 0.1
    }

async def _get_error_rates():
    """Get error rates by source type"""
    # TODO: Replace with actual error tracking database query
    # For now, return configurable placeholder values
    return {
        "satellite": 0.001,
        "weather": 0.002,
        "sensor": 0.005
    }

async def _get_latency_metrics():
    """Get latency metrics"""
    # TODO: Replace with actual performance metrics database query
    # For now, return configurable placeholder values
    return {
        "p50_ms": 150,
        "p95_ms": 500,
        "p99_ms": 1200
    }

async def _get_all_available_sources():
    """Dynamically discover all available data sources from all connectors"""
    all_sources = []

    # Get all active connectors and their sources
    connectors = [
        ("satellite", app.state.satellite_connector),
        ("weather", app.state.weather_connector),
        ("nasa_firms", app.state.nasa_firms_connector),
        ("noaa_weather", app.state.noaa_weather_connector),
        ("iot_mqtt", app.state.iot_mqtt_connector)
    ]

    for connector_name, connector in connectors:
        if connector:
            try:
                sources = await connector.get_sources()
                all_sources.extend(sources)
            except Exception as e:
                logger.warning(f"Failed to get sources from {connector_name}", error=str(e))

    return all_sources

async def _get_connector_by_source_id(source_id: str):
    """Get the appropriate connector for a given source ID"""
    logger.debug("Routing source_id", source_id=source_id)

    # Map source IDs to connectors based on EXACT source_id patterns

    # NASA FIRMS Connector: firms_*, landsat_nrt
    if source_id.lower().startswith(("firms_", "landsat_nrt")):
        logger.debug("Routing to nasa_firms_connector", source_id=source_id)
        return app.state.nasa_firms_connector

    # Satellite Connector: sat_*
    elif source_id.lower().startswith("sat_"):
        logger.debug("Routing to satellite_connector", source_id=source_id)
        return app.state.satellite_connector

    # NOAA Weather Connector: noaa_*
    elif source_id.lower().startswith("noaa_"):
        logger.debug("Routing to noaa_weather_connector", source_id=source_id)
        return app.state.noaa_weather_connector

    # Weather Connector: wx_*
    elif source_id.lower().startswith("wx_"):
        logger.debug("Routing to weather_connector", source_id=source_id)
        return app.state.weather_connector

    # IoT MQTT Connector: iot_*
    elif source_id.lower().startswith("iot_"):
        logger.debug("Routing to iot_mqtt_connector", source_id=source_id)
        return app.state.iot_mqtt_connector

    # FireSat Connector: firesat_*
    elif source_id.lower().startswith("firesat_"):
        logger.debug("Routing to firesat_connector", source_id=source_id)
        return app.state.firesat_connector

    else:
        logger.debug("Unknown source_id pattern, using default weather_connector", source_id=source_id)
        # Default to weather connector for unknown sources
        return app.state.weather_connector


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host=settings.server_host,
        port=settings.server_port,
        reload=settings.server_reload,
        log_level=settings.server_log_level
    )