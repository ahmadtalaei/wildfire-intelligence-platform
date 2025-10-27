"""
Fire Risk Service - Main Application
Advanced ML-powered fire risk prediction service with real-time inference
"""

import os
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any, List

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse, Response
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
import structlog

from .config import get_settings
from .models.database import get_database
from .models.prediction import FireRiskPredictor, PredictionRequest, PredictionResponse
from .models.ml_models import ModelManager
from .middleware.monitoring import PrometheusMiddleware
from .middleware.security import SecurityMiddleware
from .utils.health import HealthChecker

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
REQUEST_COUNT = Counter('fire_risk_requests_total', 'Total fire risk prediction requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('fire_risk_request_duration_seconds', 'Fire risk prediction request duration')
PREDICTION_COUNT = Counter('fire_risk_predictions_total', 'Total fire risk predictions', ['risk_level'])

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("Starting Fire Risk Service", version="1.0.0")
    
    # Initialize model manager
    model_manager = ModelManager()
    await model_manager.load_models()
    app.state.model_manager = model_manager
    
    # Initialize predictor
    predictor = FireRiskPredictor(model_manager)
    app.state.predictor = predictor
    
    # Initialize health checker
    health_checker = HealthChecker()
    app.state.health_checker = health_checker
    
    logger.info("Fire Risk Service initialized successfully")
    
    yield
    
    # Cleanup
    logger.info("Shutting down Fire Risk Service")
    await model_manager.cleanup()

# Create FastAPI application
app = FastAPI(
    title="Wildfire Intelligence - Fire Risk Service",
    description="Advanced ML-powered fire risk prediction service with real-time inference capabilities",
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
        "service": "fire-risk-service",
        "version": "1.0.0",
        "description": "Advanced ML-powered fire risk prediction service",
        "status": "operational",
        "capabilities": [
            "real-time fire risk prediction",
            "ensemble ML models",
            "geospatial analysis",
            "weather integration",
            "satellite data processing"
        ],
        "supported_models": [
            "Random Forest",
            "XGBoost", 
            "LightGBM",
            "Neural Network",
            "Ensemble"
        ]
    }

# =============================================================================
# FIRE RISK PREDICTION ENDPOINTS
# =============================================================================

@app.post("/predict", response_model=PredictionResponse)
async def predict_fire_risk(
    request: PredictionRequest,
    background_tasks: BackgroundTasks
):
    """
    Predict fire risk for given location and conditions
    
    This endpoint provides real-time fire risk predictions using ensemble ML models
    that consider weather conditions, historical fire data, vegetation indices,
    and satellite observations.
    """
    try:
        logger.info("Fire risk prediction request", 
                   latitude=request.latitude, 
                   longitude=request.longitude,
                   date=request.date)
        
        predictor = app.state.predictor
        prediction = await predictor.predict(request)
        
        # Update metrics
        PREDICTION_COUNT.labels(risk_level=prediction.risk_level).inc()
        
        # Log prediction for audit trail
        background_tasks.add_task(log_prediction, request, prediction)
        
        logger.info("Fire risk prediction completed", 
                   risk_level=prediction.risk_level,
                   confidence=prediction.confidence)
        
        return prediction
        
    except Exception as e:
        logger.error("Fire risk prediction failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")

@app.post("/predict/batch", response_model=List[PredictionResponse])
async def predict_fire_risk_batch(
    requests: List[PredictionRequest],
    background_tasks: BackgroundTasks
):
    """
    Batch fire risk prediction for multiple locations
    
    Efficiently processes multiple prediction requests with optimized model inference.
    Maximum batch size is 1000 requests.
    """
    if len(requests) > 1000:
        raise HTTPException(status_code=400, detail="Batch size cannot exceed 1000 requests")
    
    try:
        logger.info("Batch fire risk prediction request", batch_size=len(requests))
        
        predictor = app.state.predictor
        predictions = await predictor.predict_batch(requests)
        
        # Update metrics for each prediction
        for prediction in predictions:
            PREDICTION_COUNT.labels(risk_level=prediction.risk_level).inc()
        
        # Log batch prediction
        background_tasks.add_task(log_batch_prediction, requests, predictions)
        
        logger.info("Batch fire risk prediction completed", 
                   batch_size=len(predictions))
        
        return predictions
        
    except Exception as e:
        logger.error("Batch fire risk prediction failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Batch prediction failed: {str(e)}")

@app.get("/models/status")
async def model_status():
    """Get status of all loaded ML models"""
    try:
        model_manager = app.state.model_manager
        status = await model_manager.get_status()
        return status
    except Exception as e:
        logger.error("Failed to get model status", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get model status: {str(e)}")

@app.post("/models/reload")
async def reload_models():
    """Reload ML models (admin endpoint)"""
    try:
        model_manager = app.state.model_manager
        await model_manager.reload_models()
        logger.info("Models reloaded successfully")
        return {"status": "success", "message": "Models reloaded successfully"}
    except Exception as e:
        logger.error("Failed to reload models", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to reload models: {str(e)}")

# =============================================================================
# GEOSPATIAL ANALYSIS ENDPOINTS
# =============================================================================

@app.post("/analyze/region")
async def analyze_region_risk(
    region_data: Dict[str, Any]
):
    """
    Analyze fire risk for a geographic region
    
    Accepts GeoJSON polygon and provides comprehensive fire risk analysis
    including risk distribution, hotspots, and trend analysis.
    """
    try:
        logger.info("Region risk analysis request")
        
        predictor = app.state.predictor
        analysis = await predictor.analyze_region(region_data)
        
        logger.info("Region risk analysis completed")
        return analysis
        
    except Exception as e:
        logger.error("Region risk analysis failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Region analysis failed: {str(e)}")

@app.get("/risk/hotspots")
async def get_fire_risk_hotspots(
    bounds: str = None,
    min_risk: str = "medium",
    limit: int = 100
):
    """
    Get current fire risk hotspots
    
    Returns locations with elevated fire risk within specified bounds.
    """
    try:
        logger.info("Fire risk hotspots request", bounds=bounds, min_risk=min_risk)
        
        predictor = app.state.predictor
        hotspots = await predictor.get_hotspots(bounds, min_risk, limit)
        
        logger.info("Fire risk hotspots retrieved", count=len(hotspots))
        return {"hotspots": hotspots, "count": len(hotspots)}
        
    except Exception as e:
        logger.error("Failed to get fire risk hotspots", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get hotspots: {str(e)}")

# =============================================================================
# BACKGROUND TASKS
# =============================================================================

async def log_prediction(request: PredictionRequest, prediction: PredictionResponse):
    """Log prediction for audit trail and model monitoring"""
    try:
        # Store prediction in database for monitoring and improvement
        # This would be implemented with actual database connection
        pass
    except Exception as e:
        logger.error("Failed to log prediction", error=str(e))

async def log_batch_prediction(requests: List[PredictionRequest], predictions: List[PredictionResponse]):
    """Log batch predictions for audit trail"""
    try:
        # Store batch predictions in database
        pass
    except Exception as e:
        logger.error("Failed to log batch prediction", error=str(e))

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
        port=8000,
        reload=True,
        log_level="info"
    )