"""
Data Storage Service - Main Application
Scalable data storage service for wildfire intelligence platform with TimescaleDB and S3 integration
"""

import os
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse, Response
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
import structlog

from .config import get_settings
from .models.database import DatabaseManager
from .models.timeseries import TimeseriesManager
from .models.blob_storage import BlobStorageManager
from .models.data_models import (
    StorageRequest, StorageResponse, QueryRequest, QueryResponse,
    BulkStorageRequest, MetadataRequest
)
from .middleware.monitoring import PrometheusMiddleware
from .middleware.security import SecurityMiddleware
from .utils.health import HealthChecker
from .services.data_archiver import DataArchiver
from .services.data_optimizer import DataOptimizer
from .services.kafka_consumer import KafkaConsumerManager

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

# Prometheus metrics - using try/except to avoid duplicate registrations
try:
    STORAGE_OPERATIONS = Counter('storage_operations_total', 'Total storage operations', ['operation', 'status', 'data_type'])
except ValueError:
    from prometheus_client import REGISTRY
    STORAGE_OPERATIONS = REGISTRY._names_to_collectors.get('storage_operations_total')

try:
    STORAGE_LATENCY = Histogram('storage_operation_duration_seconds', 'Storage operation duration', ['operation'])
except ValueError:
    from prometheus_client import REGISTRY
    STORAGE_LATENCY = REGISTRY._names_to_collectors.get('storage_operation_duration_seconds')

try:
    DATA_VOLUME = Counter('data_volume_bytes_total', 'Total data volume processed', ['data_type'])
except ValueError:
    from prometheus_client import REGISTRY
    DATA_VOLUME = REGISTRY._names_to_collectors.get('data_volume_bytes_total')

try:
    ACTIVE_CONNECTIONS = Counter('database_connections_active', 'Active database connections')
except ValueError:
    from prometheus_client import REGISTRY
    ACTIVE_CONNECTIONS = REGISTRY._names_to_collectors.get('database_connections_active')

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    try:
        print("=== LIFESPAN STARTUP STARTING ===")  # Debug print
        logger.info("Starting Data Storage Service", version="1.0.0")

        # Initialize database manager
        db_manager = DatabaseManager()
        await db_manager.initialize()
        app.state.db_manager = db_manager

        # Initialize timeseries manager (temporarily disabled to debug connection issues)
        # timeseries_manager = TimeseriesManager(db_manager)
        # await timeseries_manager.initialize()
        # app.state.timeseries_manager = timeseries_manager
        app.state.timeseries_manager = None

        # Initialize blob storage manager
        blob_manager = BlobStorageManager()
        await blob_manager.initialize()
        app.state.blob_manager = blob_manager

        # Initialize data archiver
        archiver = DataArchiver(db_manager, blob_manager)
        app.state.archiver = archiver

        # Initialize data optimizer (temporarily disabled due to timeseries manager)
        # optimizer = DataOptimizer(db_manager, timeseries_manager)
        # app.state.optimizer = optimizer
        app.state.optimizer = None

        # Initialize health checker
        health_checker = HealthChecker()
        app.state.health_checker = health_checker

        # Initialize Kafka consumer (if enabled)
        kafka_consumer_manager = None
        if settings.kafka_enable_consumer:
            try:
                logger.info("🚀 INITIALIZING KAFKA CONSUMER", kafka_enabled=True)
                kafka_consumer_manager = KafkaConsumerManager(db_manager)
                app.state.kafka_consumer = kafka_consumer_manager

                # Start consumer in background to avoid blocking startup
                async def start_consumer():
                    print("=== START_CONSUMER FUNCTION CALLED ===")
                    try:
                        print("=== ABOUT TO CALL kafka_consumer_manager.start() ===")
                        logger.info("📡 STARTING KAFKA CONSUMER BACKGROUND TASK")
                        await kafka_consumer_manager.start()
                        print("=== kafka_consumer_manager.start() COMPLETED ===")
                        logger.info("✅ KAFKA CONSUMER STARTED SUCCESSFULLY")
                    except Exception as e:
                        print(f"=== EXCEPTION IN START_CONSUMER: {e} ===")
                        import traceback
                        traceback.print_exc()
                        logger.error("❌ KAFKA CONSUMER STARTUP FAILED", error=str(e), exc_info=True)

                # Store task reference to prevent garbage collection
                print("=== CREATING BACKGROUND TASK FOR start_consumer() ===")
                app.state.kafka_consumer_task = asyncio.create_task(start_consumer())
                print("=== BACKGROUND TASK CREATED ===")
                logger.info("🎯 KAFKA CONSUMER BACKGROUND TASK CREATED")
            except Exception as e:
                logger.error("❌ FAILED TO INITIALIZE KAFKA CONSUMER MANAGER", error=str(e), exc_info=True)
                app.state.kafka_consumer = None
        else:
            logger.info("⚠️  KAFKA CONSUMER DISABLED", kafka_enable_consumer=False)
            app.state.kafka_consumer = None

        logger.info("Data Storage Service initialized successfully")
        print("=== LIFESPAN STARTUP COMPLETE ===")  # Debug print

        yield

    except Exception as e:
        print(f"=== 🔥 LIFESPAN STARTUP FAILED: {e} ===")
        import traceback
        traceback.print_exc()
        logger.exception(f"🔥 Lifespan startup failed: {e}")
        raise
    finally:
        # Cleanup
        logger.info("Shutting down Data Storage Service")

        # Stop Kafka consumer
        try:
            if hasattr(app.state, 'kafka_consumer') and app.state.kafka_consumer:
                await app.state.kafka_consumer.stop()
        except Exception as e:
            logger.error("Error stopping Kafka consumer", error=str(e))

        try:
            if 'db_manager' in locals():
                await db_manager.cleanup()
        except Exception as e:
            logger.error("Error cleaning up database manager", error=str(e))

        try:
            if 'blob_manager' in locals():
                await blob_manager.cleanup()
        except Exception as e:
            logger.error("Error cleaning up blob manager", error=str(e))

# Create FastAPI application
app = FastAPI(
    title="Wildfire Intelligence - Data Storage Service",
    description="Scalable data storage service with TimescaleDB and S3 integration for wildfire intelligence platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc", 
    openapi_url="/openapi.json",
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

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.allowed_hosts
)

app.add_middleware(PrometheusMiddleware)
app.add_middleware(SecurityMiddleware)
# =============================================================================
# HEALTH AND MONITORING ENDPOINTS
# =============================================================================

@app.get("/health", response_model=Dict[str, Any])
async def health_check():
    """Comprehensive health check endpoint"""
    try:
        health_checker = app.state.health_checker
        health_status = await health_checker.check_all()
        status_code = 200 if health_status["status"] == "healthy" else 503
        return JSONResponse(content=health_status, status_code=status_code)
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        print(f"=== HEALTH CHECK ERROR ===")
        print(f"Error: {str(e)}")
        print(f"Traceback:\n{tb}")
        print(f"=== END ERROR ===")
        logger.error("Health check failed", error=str(e), traceback=tb)
        return JSONResponse(
            content={
                "status": "degraded",
                "service": "data-storage-service",
                "version": "1.0.0",
                "message": "Basic health check - comprehensive monitoring failed",
                "error": str(e)
            },
            status_code=200
        )

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/info")
async def service_info():
    """Service information endpoint"""
    return {
        "service": "data-storage-service",
        "version": "1.0.0",
        "description": "Scalable data storage service for wildfire intelligence platform",
        "status": "operational",
        "capabilities": [
            "timeseries data storage",
            "blob storage (S3/MinIO)",
            "real-time data ingestion",
            "historical data archiving",
            "data compression optimization",
            "geospatial indexing"
        ],
        "storage_backends": [
            "TimescaleDB (timeseries)",
            "PostgreSQL (metadata)",
            "S3/MinIO (blob storage)",
            "Redis (caching)",
            "Kafka (streaming ingestion)"
        ],
        "kafka_consumer_status": "running" if (app.state.kafka_consumer and app.state.kafka_consumer.is_running()) else "stopped"
    }

# =============================================================================
# DATA STORAGE ENDPOINTS
# =============================================================================

@app.post("/store", response_model=StorageResponse)
async def store_data(
    request: StorageRequest,
    background_tasks: BackgroundTasks
):
    """
    Store data in appropriate storage backend
    
    Automatically routes data to:
    - TimescaleDB for time-series data (weather, sensor readings)
    - Blob storage for large objects (satellite images, model files)
    - PostgreSQL for metadata and relationships
    """
    try:
        logger.info("Data storage request",
                   data_type=request.data_type,
                   size_kb=len(str(request.data)) / 1024)
        
        # Route to appropriate storage backend
        if request.data_type in ["weather", "sensor", "fire_detection", "predictions"]:
            # Time-series data
            timeseries_manager = app.state.timeseries_manager
            result = await timeseries_manager.store(request)
            
        elif request.data_type in ["satellite_image", "model_file", "archive"]:
            # Blob storage
            blob_manager = app.state.blob_manager
            result = await blob_manager.store(request)
            
        else:
            # Metadata storage
            db_manager = app.state.db_manager
            result = await db_manager.store(request)
        
        # Update metrics
        STORAGE_OPERATIONS.labels(
            operation="store",
            status="success", 
            data_type=request.data_type
        ).inc()
        
        DATA_VOLUME.labels(data_type=request.data_type).inc(len(str(request.data)))
        
        # Schedule background optimization
        background_tasks.add_task(optimize_storage, request.data_type)
        
        logger.info("Data stored successfully",
                   storage_id=result.storage_id,
                   data_type=request.data_type)
        
        return result
        
    except Exception as e:
        STORAGE_OPERATIONS.labels(
            operation="store",
            status="error",
            data_type=request.data_type
        ).inc()
        
        logger.error("Data storage failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Storage failed: {str(e)}")

@app.post("/store/bulk", response_model=List[StorageResponse])
async def store_bulk_data(
    request: BulkStorageRequest,
    background_tasks: BackgroundTasks
):
    """
    Bulk data storage for high-throughput ingestion
    
    Optimized for batch processing of large datasets with transaction management
    and automatic partitioning for time-series data.
    """
    if len(request.data_items) > 10000:
        raise HTTPException(status_code=400, detail="Bulk storage limited to 10,000 items per request")
    
    try:
        logger.info("Bulk data storage request", 
                   batch_size=len(request.data_items),
                   data_type=request.data_type)
        
        # Route to appropriate bulk storage
        if request.data_type in ["weather", "sensor", "fire_detection"]:
            timeseries_manager = app.state.timeseries_manager
            results = await timeseries_manager.store_bulk(request)
        else:
            db_manager = app.state.db_manager
            results = await db_manager.store_bulk(request)
        
        # Update metrics
        STORAGE_OPERATIONS.labels(
            operation="bulk_store",
            status="success",
            data_type=request.data_type
        ).inc()
        
        total_size = sum(len(str(item)) for item in request.data_items)
        DATA_VOLUME.labels(data_type=request.data_type).inc(total_size)
        
        # Schedule background archiving for old data
        background_tasks.add_task(archive_old_data, request.data_type)
        
        logger.info("Bulk data stored successfully",
                   batch_size=len(results))
        
        return results
        
    except Exception as e:
        STORAGE_OPERATIONS.labels(
            operation="bulk_store", 
            status="error",
            data_type=request.data_type
        ).inc()
        
        logger.error("Bulk data storage failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Bulk storage failed: {str(e)}")

# =============================================================================
# DATA RETRIEVAL ENDPOINTS  
# =============================================================================

@app.post("/query", response_model=QueryResponse)
async def query_data(request: QueryRequest):
    """
    Query stored data with flexible filtering
    
    Supports time-range queries, geospatial filtering, aggregation functions,
    and joins across multiple data sources.
    """
    try:
        logger.info("Data query request",
                   data_type=request.data_type,
                   time_range=f"{request.start_time} to {request.end_time}")
        
        # Route query to appropriate backend
        if request.data_type in ["weather", "sensor", "fire_detection", "predictions"]:
            timeseries_manager = app.state.timeseries_manager
            result = await timeseries_manager.query(request)
        else:
            db_manager = app.state.db_manager
            result = await db_manager.query(request)
        
        STORAGE_OPERATIONS.labels(
            operation="query",
            status="success",
            data_type=request.data_type
        ).inc()
        
        logger.info("Data query completed",
                   records_returned=len(result.data))
        
        return result
        
    except Exception as e:
        STORAGE_OPERATIONS.labels(
            operation="query",
            status="error", 
            data_type=request.data_type
        ).inc()
        
        logger.error("Data query failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

@app.get("/data/{storage_id}")
async def get_data_by_id(storage_id: str):
    """Retrieve data by storage ID"""
    try:
        db_manager = app.state.db_manager
        data = await db_manager.get_by_id(storage_id)
        
        if not data:
            raise HTTPException(status_code=404, detail="Data not found")
        
        STORAGE_OPERATIONS.labels(operation="get", status="success", data_type="any").inc()
        return data
        
    except HTTPException:
        raise
    except Exception as e:
        STORAGE_OPERATIONS.labels(operation="get", status="error", data_type="any").inc()
        logger.error("Failed to get data by ID", storage_id=storage_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Retrieval failed: {str(e)}")

# =============================================================================
# DATA MANAGEMENT ENDPOINTS
# =============================================================================

@app.delete("/data/{storage_id}")
async def delete_data(storage_id: str):
    """Delete data by storage ID"""
    try:
        db_manager = app.state.db_manager
        success = await db_manager.delete(storage_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Data not found")
        
        STORAGE_OPERATIONS.labels(operation="delete", status="success", data_type="any").inc()
        
        return {"status": "deleted", "storage_id": storage_id}
        
    except HTTPException:
        raise
    except Exception as e:
        STORAGE_OPERATIONS.labels(operation="delete", status="error", data_type="any").inc()
        logger.error("Failed to delete data", storage_id=storage_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Deletion failed: {str(e)}")

@app.post("/archive")
async def archive_data(
    data_type: str,
    background_tasks: BackgroundTasks,
    older_than_days: int = 90
):
    """Archive old data to cold storage"""
    try:
        archiver = app.state.archiver
        background_tasks.add_task(archiver.archive_old_data, data_type, older_than_days)
        
        return {
            "status": "archive_scheduled",
            "data_type": data_type,
            "older_than_days": older_than_days
        }
        
    except Exception as e:
        logger.error("Failed to schedule archiving", error=str(e))
        raise HTTPException(status_code=500, detail=f"Archiving failed: {str(e)}")

@app.get("/stats")
async def storage_statistics():
    """Get storage statistics and usage metrics for homepage dashboard"""
    try:
        db_manager = app.state.db_manager

        async with db_manager.get_connection() as conn:
            # Get fire incidents count and latest
            fire_query = """
                SELECT COUNT(*) as count, MAX(created_at) as latest
                FROM fire_incidents
            """
            fire_result = await conn.fetchrow(fire_query)

            # Get weather data count and latest
            weather_query = """
                SELECT COUNT(*) as count, MAX(created_at) as latest
                FROM weather_data
            """
            weather_result = await conn.fetchrow(weather_query)

            # Get sensor readings count and latest
            sensor_query = """
                SELECT COUNT(*) as count, MAX(created_at) as latest
                FROM sensor_readings
            """
            sensor_result = await conn.fetchrow(sensor_query)

            return {
                "status": "success",
                "statistics": {
                    "fire_incidents": fire_result['count'] if fire_result else 0,
                    "latest_fire_incident": fire_result['latest'].isoformat() if fire_result and fire_result['latest'] else None,
                    "weather_readings": weather_result['count'] if weather_result else 0,
                    "latest_weather_data": weather_result['latest'].isoformat() if weather_result and weather_result['latest'] else None,
                    "sensor_readings": sensor_result['count'] if sensor_result else 0,
                    "latest_sensor_reading": sensor_result['latest'].isoformat() if sensor_result and sensor_result['latest'] else None
                }
            }

    except Exception as e:
        logger.error("Failed to get storage statistics", error=str(e))
        raise HTTPException(status_code=500, detail=f"Statistics failed: {str(e)}")

@app.get("/api/v1/stats")
async def api_v1_storage_statistics():
    """Get storage statistics and usage metrics (API v1 endpoint)"""
    return await storage_statistics()

@app.get("/api/v1/recent-fires")
async def get_recent_fire_detections(limit: int = 20):
    """Get most recent fire detections for dashboard display"""
    try:
        db_manager = app.state.db_manager

        async with db_manager.get_connection() as conn:
            # Query recent fire incidents with all relevant details
            query = """
                SELECT
                    latitude,
                    longitude,
                    confidence,
                    brightness,
                    temperature,
                    source,
                    satellite,
                    timestamp,
                    created_at
                FROM fire_incidents
                ORDER BY created_at DESC
                LIMIT $1
            """

            rows = await conn.fetch(query, limit)

            # Convert to list of dicts with formatted data
            fire_detections = []
            for row in rows:
                fire_detections.append({
                    "latitude": float(row['latitude']) if row['latitude'] else None,
                    "longitude": float(row['longitude']) if row['longitude'] else None,
                    "confidence": int(row['confidence']) if row['confidence'] else None,
                    "brightness_kelvin": float(row['brightness']) if row['brightness'] else None,
                    "temperature": float(row['temperature']) if row['temperature'] else None,
                    "source": row['source'],
                    "satellite": row['satellite'],
                    "detection_timestamp": row['timestamp'].isoformat() if row['timestamp'] else None,
                    "created_at": row['created_at'].isoformat() if row['created_at'] else None
                })

            return {
                "status": "success",
                "count": len(fire_detections),
                "fires": fire_detections
            }

    except Exception as e:
        logger.error("Failed to get recent fire detections", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to retrieve fire detections: {str(e)}")

# =============================================================================
# BACKGROUND TASKS
# =============================================================================

async def optimize_storage(data_type: str):
    """Background task to optimize storage for data type"""
    try:
        # This would implement compression, indexing optimization, etc.
        pass
    except Exception as e:
        logger.error("Storage optimization failed", data_type=data_type, error=str(e))

async def archive_old_data(data_type: str):
    """Background task to archive old data"""
    try:
        archiver = app.state.archiver
        await archiver.archive_old_data(data_type, older_than_days=90)
    except Exception as e:
        logger.error("Data archiving failed", data_type=data_type, error=str(e))

# =============================================================================
# ERROR HANDLERS
# =============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions with structured logging"""
    logger.warning("HTTP exception",
                  status_code=exc.status_code,
                  detail=exc.detail, 
                  path=request.url.path)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "status_code": exc.status_code}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions with structured logging"""
    logger.error("Unexpected error",
                error=str(exc),
                path=request.url.path,
                exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "status_code": 500}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )