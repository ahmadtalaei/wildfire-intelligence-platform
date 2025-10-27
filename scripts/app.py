"""
Wildfire Intelligence Platform - Development Server
This script provides a simple development server for testing API endpoints
without running the full Docker Compose stack.

For production, use: docker-compose up
For development with full features, use: docker-compose -f docker-compose.dev.yml up
"""

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime
from typing import Dict, List, Any

app = FastAPI(
    title="Wildfire Intelligence Platform - Development API",
    description="Simplified API for development and testing. Use Docker Compose for full functionality.",
    version="1.0.0-dev"
)

# Add CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:3002", "http://localhost:3003"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global health status
platform_status = {
    "platform": "operational",
    "services": {
        "fire-risk-service": "healthy",
        "data-ingestion-service": "healthy",
        "data-catalog-service": "healthy",
        "user-management-service": "healthy",
        "visualization-service": "healthy",
        "notification-service": "healthy"
    },
    "last_updated": datetime.now().isoformat()
}

# =============================================================================
# PLATFORM HEALTH AND STATUS
# =============================================================================

@app.get("/health")
async def platform_health():
    """Platform-wide health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0-dev",
        "environment": "development",
        "message": "Development server running. Use Docker Compose for full functionality."
    }

@app.get("/status")
async def platform_status_endpoint():
    """Detailed platform status"""
    platform_status["last_updated"] = datetime.now().isoformat()
    return platform_status

# =============================================================================
# FIRE RISK SERVICE ENDPOINTS
# =============================================================================

@app.get("/api/v1/fire-risk/health")
async def fire_risk_health():
    """Fire Risk Service health check"""
    return {
        "status": "healthy",
        "service": "fire-risk-service",
        "capabilities": ["prediction", "batch-prediction", "model-management"],
        "model_status": "active"
    }

@app.post("/api/v1/fire-risk/predict")
async def predict_fire_risk(payload: Dict[str, Any]):
    """Single fire risk prediction (mock implementation)"""
    if "latitude" not in payload or "longitude" not in payload:
        raise HTTPException(status_code=400, detail="Missing required fields: latitude, longitude")
    
    # Mock prediction logic
    lat, lon = payload["latitude"], payload["longitude"]
    risk_score = abs(lat * lon) % 100 / 100  # Simple mock calculation
    
    if risk_score < 0.3:
        risk_level = "low"
    elif risk_score < 0.7:
        risk_level = "medium"
    else:
        risk_level = "high"
    
    return {
        "prediction": risk_level,
        "risk_score": round(risk_score, 3),
        "confidence": 0.85,
        "location": {"latitude": lat, "longitude": lon},
        "timestamp": datetime.now().isoformat(),
        "model_version": "dev-1.0",
        "factors": {
            "weather_risk": round(risk_score * 0.4, 2),
            "vegetation_risk": round(risk_score * 0.3, 2),
            "historical_risk": round(risk_score * 0.3, 2)
        }
    }

@app.post("/api/v1/fire-risk/predict/batch")
async def predict_fire_risk_batch(payload: List[Dict[str, Any]]):
    """Batch fire risk prediction (mock implementation)"""
    if len(payload) > 1000:
        raise HTTPException(status_code=400, detail="Batch size cannot exceed 1000 requests")
    
    predictions = []
    for request in payload:
        try:
            prediction = await predict_fire_risk(request)
            predictions.append(prediction)
        except Exception as e:
            predictions.append({
                "error": str(e),
                "input": request
            })
    
    return predictions

@app.get("/api/v1/fire-risk/models/status")
async def model_status():
    """ML model status"""
    return {
        "status": "active",
        "models": {
            "random_forest": {"status": "loaded", "accuracy": 0.94, "last_trained": "2024-01-01T00:00:00Z"},
            "xgboost": {"status": "loaded", "accuracy": 0.96, "last_trained": "2024-01-01T00:00:00Z"},
            "neural_network": {"status": "loaded", "accuracy": 0.93, "last_trained": "2024-01-01T00:00:00Z"},
            "ensemble": {"status": "active", "accuracy": 0.97, "last_trained": "2024-01-01T00:00:00Z"}
        },
        "performance_metrics": {
            "avg_prediction_time_ms": 45,
            "requests_per_second": 150,
            "model_drift_score": 0.02
        }
    }

# =============================================================================
# DATA INGESTION SERVICE ENDPOINTS  
# =============================================================================

@app.get("/api/v1/ingestion/health")
async def ingestion_health():
    """Data Ingestion Service health check"""
    return {
        "status": "healthy",
        "service": "data-ingestion-service",
        "connectors": {
            "satellite": "active",
            "weather": "active", 
            "sensors": "active"
        },
        "kafka_status": "connected"
    }

@app.get("/api/v1/ingestion/sources")
async def list_sources():
    """List available data sources"""
    return {
        "sources": [
            {
                "id": "sat_modis_terra",
                "name": "MODIS Terra",
                "type": "satellite",
                "status": "active",
                "data_rate": "2.5 GB/day"
            },
            {
                "id": "wx_era5_reanalysis", 
                "name": "ERA5 Reanalysis",
                "type": "weather",
                "status": "active",
                "data_rate": "1.2 GB/day"
            },
            {
                "id": "sensor_network_ca",
                "name": "California Sensor Network",
                "type": "sensor",
                "status": "active",
                "data_rate": "500 MB/day"
            }
        ],
        "total_sources": 3,
        "active_sources": 3
    }

@app.get("/api/v1/ingestion/stream/status")
async def stream_status():
    """Streaming status"""
    return {
        "streaming": True,
        "active_streams": 5,
        "total_throughput_mbps": 12.5,
        "streams": [
            {"stream_id": "stream_1", "source": "MODIS", "status": "active", "rate_mbps": 5.2},
            {"stream_id": "stream_2", "source": "Weather", "status": "active", "rate_mbps": 3.1},
            {"stream_id": "stream_3", "source": "Sensors", "status": "active", "rate_mbps": 2.8},
            {"stream_id": "stream_4", "source": "VIIRS", "status": "active", "rate_mbps": 1.4},
        ],
        "buffer_status": "healthy",
        "lag_ms": 150
    }

@app.get("/api/v1/ingestion/stats")
async def ingestion_stats():
    """Ingestion statistics"""
    return {
        "records_ingested": 1234567,
        "daily_volume_gb": 45.2,
        "error_rate": 0.001,
        "avg_latency_ms": 120,
        "data_quality_score": 0.98,
        "source_breakdown": {
            "satellite": 0.65,
            "weather": 0.25,
            "sensors": 0.10
        },
        "last_updated": datetime.now().isoformat()
    }

# =============================================================================
# ADDITIONAL API ENDPOINTS
# =============================================================================

@app.get("/api/v1/catalog/datasets")
async def list_datasets():
    """List available datasets"""
    return {
        "datasets": [
            {"id": "fires_2024", "name": "California Fires 2024", "size_gb": 15.2, "records": 45000},
            {"id": "weather_hourly", "name": "Hourly Weather Data", "size_gb": 8.9, "records": 2100000},
            {"id": "satellite_imagery", "name": "Satellite Imagery Archive", "size_gb": 120.5, "records": 12000}
        ]
    }

@app.get("/api/v1/users/profile")
async def user_profile():
    """Mock user profile"""
    return {
        "user_id": "dev_user_001",
        "username": "developer",
        "role": "fire_analyst",
        "permissions": ["read_data", "create_predictions", "view_dashboards"],
        "last_login": datetime.now().isoformat()
    }

if __name__ == "__main__":
    print("\n" + "="*60)
    print("[FIRE] WILDFIRE INTELLIGENCE PLATFORM - DEVELOPMENT SERVER")
    print("="*60)
    print("[LOCATION_PIN] This is a simplified development server for API testing.")
    print("🐳 For full functionality, run: docker-compose up")
    print("📖 API Documentation: http://localhost:8000/docs")
    print("🏥 Health Check: http://localhost:8000/health")
    print("="*60 + "\n")
    
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
