"""
Data Consumption Service - Main Application
High-performance data consumption service with real-time streaming and batch processing
"""

import os
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse, Response, StreamingResponse
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
import structlog
import json

from .config import get_settings
from .models.database import DatabaseManager
from .models.streaming import StreamingManager, WebSocketManager
from .models.data_models import (
    ConsumptionRequest, ConsumptionResponse, StreamingRequest,
    SubscriptionRequest, FilterConfig, AggregationConfig
)
from .middleware.monitoring import PrometheusMiddleware
from .middleware.security import SecurityMiddleware
from .utils.health import HealthChecker
from .services.data_transformer import DataTransformer
from .services.alert_processor import AlertProcessor
from .services.export_manager import ExportManager

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

# Prometheus metrics
CONSUMPTION_REQUESTS = Counter('consumption_requests_total', 'Total data consumption requests', ['endpoint', 'data_type', 'status'])
CONSUMPTION_LATENCY = Histogram('consumption_request_duration_seconds', 'Data consumption request duration', ['endpoint'])
STREAMING_CONNECTIONS = Counter('streaming_connections_total', 'Total streaming connections', ['connection_type'])
ACTIVE_WEBSOCKETS = Counter('active_websockets', 'Active WebSocket connections')
DATA_EXPORTED = Counter('data_exported_bytes_total', 'Total data exported', ['format', 'data_type'])

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("Starting Data Consumption Service", version="1.0.0")
    
    # Initialize database manager
    db_manager = DatabaseManager()
    await db_manager.initialize()
    app.state.db_manager = db_manager
    
    # Initialize streaming manager
    streaming_manager = StreamingManager(db_manager)
    await streaming_manager.initialize()
    app.state.streaming_manager = streaming_manager
    
    # Initialize WebSocket manager
    websocket_manager = WebSocketManager()
    app.state.websocket_manager = websocket_manager
    
    # Initialize data transformer
    transformer = DataTransformer()
    app.state.transformer = transformer
    
    # Initialize alert processor
    alert_processor = AlertProcessor()
    app.state.alert_processor = alert_processor
    
    # Initialize export manager
    export_manager = ExportManager()
    app.state.export_manager = export_manager
    
    # Initialize health checker
    health_checker = HealthChecker()
    app.state.health_checker = health_checker
    
    logger.info("Data Consumption Service initialized successfully")
    
    yield
    
    # Cleanup
    logger.info("Shutting down Data Consumption Service")
    await db_manager.cleanup()
    await streaming_manager.cleanup()

# Create FastAPI application
app = FastAPI(
    title="Wildfire Intelligence - Data Consumption Service", 
    description="High-performance data consumption service with real-time streaming and batch processing",
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
    health_checker = app.state.health_checker
    health_status = await health_checker.check_all()
    
    status_code = 200 if health_status["status"] == "healthy" else 503
    return JSONResponse(content=health_status, status_code=status_code)

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/info")
async def service_info():
    """Service information endpoint"""
    return {
        "service": "data-consumption-service",
        "version": "1.0.0", 
        "description": "High-performance data consumption service for wildfire intelligence platform",
        "status": "operational",
        "capabilities": [
            "real-time data streaming",
            "batch data consumption",
            "WebSocket connections",
            "data transformation",
            "alert processing",
            "multi-format export"
        ],
        "streaming_protocols": [
            "WebSocket",
            "Server-Sent Events",
            "Kafka Streams",
            "Redis Pub/Sub"
        ],
        "export_formats": [
            "JSON", "CSV", "Parquet",
            "GeoJSON", "KML", "Shapefile"
        ]
    }

# =============================================================================
# REAL-TIME DATA STREAMING ENDPOINTS
# =============================================================================

@app.websocket("/stream/{data_type}")
async def stream_data(websocket: WebSocket, data_type: str):
    """
    Real-time data streaming via WebSocket
    
    Provides live data feeds for:
    - Fire detection alerts
    - Weather updates
    - Sensor readings
    - Risk predictions
    """
    await websocket.accept()
    
    websocket_manager = app.state.websocket_manager
    streaming_manager = app.state.streaming_manager
    
    connection_id = await websocket_manager.add_connection(websocket, data_type)
    
    STREAMING_CONNECTIONS.labels(connection_type="websocket").inc()
    ACTIVE_WEBSOCKETS.inc()
    
    logger.info("WebSocket connection established",
               connection_id=connection_id,
               data_type=data_type)
    
    try:
        # Start streaming data for this connection
        async for data in streaming_manager.stream_data(data_type, connection_id):
            await websocket.send_text(json.dumps(data))
            
    except WebSocketDisconnect:
        logger.info("WebSocket connection closed",
                   connection_id=connection_id,
                   data_type=data_type)
    except Exception as e:
        logger.error("WebSocket streaming error",
                    connection_id=connection_id,
                    error=str(e))
    finally:
        await websocket_manager.remove_connection(connection_id)
        ACTIVE_WEBSOCKETS.dec()

@app.post("/stream/subscribe")
async def subscribe_to_stream(request: SubscriptionRequest):
    """
    Subscribe to data streams with custom filters
    
    Allows clients to subscribe to specific data types with:
    - Geographic filtering (bounding box, radius)
    - Temporal filtering (time windows)
    - Threshold-based filtering (risk levels, confidence)
    - Custom aggregation functions
    """
    try:
        streaming_manager = app.state.streaming_manager
        subscription_id = await streaming_manager.create_subscription(request)
        
        CONSUMPTION_REQUESTS.labels(
            endpoint="subscribe",
            data_type=request.data_type,
            status="success"
        ).inc()
        
        logger.info("Stream subscription created",
                   subscription_id=subscription_id,
                   data_type=request.data_type)
        
        return {
            "subscription_id": subscription_id,
            "data_type": request.data_type,
            "filters": request.filters,
            "status": "active"
        }
        
    except Exception as e:
        CONSUMPTION_REQUESTS.labels(
            endpoint="subscribe",
            data_type=request.data_type,
            status="error"
        ).inc()
        
        logger.error("Stream subscription failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Subscription failed: {str(e)}")

@app.delete("/stream/subscribe/{subscription_id}")
async def unsubscribe_from_stream(subscription_id: str):
    """Unsubscribe from data stream"""
    try:
        streaming_manager = app.state.streaming_manager
        success = await streaming_manager.remove_subscription(subscription_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Subscription not found")
        
        return {"status": "unsubscribed", "subscription_id": subscription_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Unsubscription failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Unsubscription failed: {str(e)}")

# =============================================================================
# BATCH DATA CONSUMPTION ENDPOINTS
# =============================================================================

@app.post("/consume", response_model=ConsumptionResponse)
async def consume_data(request: ConsumptionRequest):
    """
    Batch data consumption with flexible querying
    
    Supports:
    - Historical data queries
    - Aggregated data retrieval
    - Multi-source data joining
    - Custom data transformations
    """
    try:
        logger.info("Data consumption request",
                   data_type=request.data_type,
                   time_range=f"{request.start_time} to {request.end_time}")
        
        db_manager = app.state.db_manager
        transformer = app.state.transformer
        
        # Query data from storage
        raw_data = await db_manager.query_data(request)
        
        # Apply transformations if specified
        if request.transformations:
            processed_data = await transformer.transform(raw_data, request.transformations)
        else:
            processed_data = raw_data
        
        # Apply aggregations if specified
        if request.aggregation:
            final_data = await transformer.aggregate(processed_data, request.aggregation)
        else:
            final_data = processed_data
        
        CONSUMPTION_REQUESTS.labels(
            endpoint="consume",
            data_type=request.data_type,
            status="success"
        ).inc()
        
        logger.info("Data consumption completed",
                   records_returned=len(final_data))
        
        return ConsumptionResponse(
            data=final_data,
            total_records=len(final_data),
            data_type=request.data_type,
            time_range={
                "start": request.start_time,
                "end": request.end_time
            }
        )
        
    except Exception as e:
        CONSUMPTION_REQUESTS.labels(
            endpoint="consume",
            data_type=request.data_type,
            status="error"
        ).inc()
        
        logger.error("Data consumption failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Consumption failed: {str(e)}")

@app.get("/consume/latest/{data_type}")
async def consume_latest_data(
    data_type: str,
    limit: int = 100,
    spatial_bounds: Optional[str] = None
):
    """
    Get latest data for specific data type
    
    Optimized for real-time dashboard updates and monitoring applications.
    """
    try:
        logger.info("Latest data consumption request",
                   data_type=data_type,
                   limit=limit)
        
        db_manager = app.state.db_manager
        data = await db_manager.get_latest_data(data_type, limit, spatial_bounds)
        
        CONSUMPTION_REQUESTS.labels(
            endpoint="latest",
            data_type=data_type, 
            status="success"
        ).inc()
        
        return {
            "data": data,
            "count": len(data),
            "data_type": data_type,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        CONSUMPTION_REQUESTS.labels(
            endpoint="latest",
            data_type=data_type,
            status="error"
        ).inc()
        
        logger.error("Latest data consumption failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Latest data consumption failed: {str(e)}")

# =============================================================================
# DATA EXPORT ENDPOINTS
# =============================================================================

@app.post("/export/{format}")
async def export_data(
    format: str,
    request: ConsumptionRequest,
    background_tasks: BackgroundTasks
):
    """
    Export data in various formats
    
    Supported formats:
    - JSON, CSV, Parquet (tabular data)
    - GeoJSON, KML, Shapefile (geospatial data)
    - PDF (reports), PNG/JPEG (visualizations)
    """
    if format not in ["json", "csv", "parquet", "geojson", "kml", "shapefile", "pdf"]:
        raise HTTPException(status_code=400, detail="Unsupported export format")
    
    try:
        logger.info("Data export request",
                   format=format,
                   data_type=request.data_type)
        
        export_manager = app.state.export_manager
        
        # Generate export file
        export_task_id = await export_manager.create_export_task(request, format)
        
        # Process export in background
        background_tasks.add_task(process_export, export_task_id, request, format)
        
        return {
            "export_id": export_task_id,
            "format": format,
            "status": "processing",
            "download_url": f"/download/{export_task_id}"
        }
        
    except Exception as e:
        logger.error("Data export failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

@app.get("/download/{export_id}")
async def download_export(export_id: str):
    """Download exported data file"""
    try:
        export_manager = app.state.export_manager
        file_info = await export_manager.get_export_file(export_id)
        
        if not file_info:
            raise HTTPException(status_code=404, detail="Export file not found")
        
        def generate_file():
            with open(file_info["file_path"], "rb") as f:
                while chunk := f.read(8192):
                    yield chunk
        
        DATA_EXPORTED.labels(
            format=file_info["format"],
            data_type=file_info["data_type"]
        ).inc(file_info["file_size"])
        
        return StreamingResponse(
            generate_file(),
            media_type=file_info["media_type"],
            headers={
                "Content-Disposition": f"attachment; filename={file_info['filename']}"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Export download failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")

# =============================================================================
# ALERT AND NOTIFICATION ENDPOINTS
# =============================================================================

@app.post("/alerts/subscribe")
async def subscribe_to_alerts(request: SubscriptionRequest):
    """
    Subscribe to real-time alerts
    
    Alert types:
    - Fire detection alerts
    - High risk warnings
    - Weather warnings
    - System alerts
    """
    try:
        alert_processor = app.state.alert_processor
        subscription_id = await alert_processor.create_alert_subscription(request)
        
        logger.info("Alert subscription created",
                   subscription_id=subscription_id)
        
        return {
            "subscription_id": subscription_id,
            "alert_types": request.data_type,
            "status": "active"
        }
        
    except Exception as e:
        logger.error("Alert subscription failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Alert subscription failed: {str(e)}")

@app.get("/alerts/active")
async def get_active_alerts(
    alert_type: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = 50
):
    """Get currently active alerts"""
    try:
        alert_processor = app.state.alert_processor
        alerts = await alert_processor.get_active_alerts(alert_type, severity, limit)
        
        return {
            "alerts": alerts,
            "count": len(alerts),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error("Failed to get active alerts", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get alerts: {str(e)}")

# =============================================================================
# BACKGROUND TASKS
# =============================================================================

async def process_export(export_id: str, request: ConsumptionRequest, format: str):
    """Background task to process data export"""
    try:
        export_manager = app.state.export_manager
        db_manager = app.state.db_manager
        
        # Get data
        data = await db_manager.query_data(request)
        
        # Generate export file
        await export_manager.generate_export_file(export_id, data, format, request.data_type)
        
        logger.info("Export processing completed", export_id=export_id)
        
    except Exception as e:
        logger.error("Export processing failed", export_id=export_id, error=str(e))

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
        port=8002,
        reload=True,
        log_level="info"
    )