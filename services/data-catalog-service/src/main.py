"""
Data Catalog Service - Challenge 3 Focus
Data clearinghouse with metadata management, search, and governance
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Dict, List, Any, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
import structlog
from sqlalchemy.orm import Session

from .config import get_settings
from .models.database import get_database, DataCatalogEntry, DataAccessLog, DataQualityMetric
from .models.catalog import Dataset, DatasetSearch, DataLineage, DataQualityReport
from .services.search_service import SearchService
from .services.lineage_service import LineageService
from .services.quality_service import QualityService
from .middleware.auth import get_current_user
from .utils.metadata_extractor import MetadataExtractor

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
SEARCH_REQUESTS = Counter('catalog_search_requests_total', 'Total search requests', ['search_type'])
DATASET_ACCESS = Counter('catalog_dataset_access_total', 'Dataset access count', ['dataset_id', 'user_role'])
CATALOG_OPERATIONS = Counter('catalog_operations_total', 'Catalog operations', ['operation'])
SEARCH_DURATION = Histogram('catalog_search_duration_seconds', 'Search duration')

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("Starting Data Catalog Service", version="1.0.0")
    
    # Initialize services
    search_service = SearchService()
    lineage_service = LineageService()
    quality_service = QualityService()
    metadata_extractor = MetadataExtractor()
    
    # Store in app state
    app.state.search_service = search_service
    app.state.lineage_service = lineage_service
    app.state.quality_service = quality_service
    app.state.metadata_extractor = metadata_extractor
    
    logger.info("Data Catalog Service initialized successfully")
    
    yield
    
    # Cleanup
    logger.info("Shutting down Data Catalog Service")

# Create FastAPI application
app = FastAPI(
    title="Wildfire Intelligence - Data Catalog Service",
    description="Data clearinghouse with metadata management, search, and governance capabilities",
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

# =============================================================================
# HEALTH AND MONITORING ENDPOINTS
# =============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check database connectivity
        db = next(get_database())
        db.execute("SELECT 1")
        
        # Check search service
        search_healthy = await app.state.search_service.health_check()
        
        return {
            "status": "healthy" if search_healthy else "degraded",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0",
            "database": "healthy",
            "search": "healthy" if search_healthy else "degraded"
        }
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": str(e)}
        )

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    from fastapi import Response
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

# =============================================================================
# DATA CATALOG MANAGEMENT
# =============================================================================

@app.get("/datasets", response_model=List[Dataset])
async def list_datasets(
    skip: int = 0,
    limit: int = 100,
    category: str = None,
    owner: str = None,
    db: Session = Depends(get_database),
    current_user: Dict = Depends(get_current_user)
):
    """
    List all datasets in the catalog with optional filtering
    
    Provides paginated access to the data catalog with filtering by category,
    owner, and other metadata attributes.
    """
    try:
        logger.info("Listing datasets", user_id=current_user.get('id'), skip=skip, limit=limit)
        
        query = db.query(DataCatalogEntry)
        
        if category:
            query = query.filter(DataCatalogEntry.metadata['category'] == category)
        if owner:
            query = query.filter(DataCatalogEntry.metadata['owner'] == owner)
        
        datasets = query.offset(skip).limit(limit).all()
        
        # Convert to response model
        result = []
        for dataset in datasets:
            result.append(Dataset(
                id=dataset.id,
                name=dataset.dataset_name,
                description=dataset.dataset_description,
                schema_definition=dataset.schema_definition,
                metadata=dataset.metadata,
                quality_score=float(dataset.quality_score) if dataset.quality_score else 0.0,
                created_at=dataset.created_at,
                updated_at=dataset.updated_at
            ))
        
        CATALOG_OPERATIONS.labels(operation="list_datasets").inc()
        
        logger.info("Datasets listed successfully", count=len(result))
        return result
        
    except Exception as e:
        logger.error("Failed to list datasets", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/datasets/{dataset_id}", response_model=Dataset)
async def get_dataset(
    dataset_id: int,
    db: Session = Depends(get_database),
    current_user: Dict = Depends(get_current_user)
):
    """Get detailed information about a specific dataset"""
    try:
        logger.info("Retrieving dataset", dataset_id=dataset_id, user_id=current_user.get('id'))
        
        dataset = db.query(DataCatalogEntry).filter(DataCatalogEntry.id == dataset_id).first()
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")
        
        # Log access for governance
        access_log = DataAccessLog(
            user_id=current_user.get('id'),
            dataset_id=dataset_id,
            access_type='view',
            access_time=datetime.now()
        )
        db.add(access_log)
        db.commit()
        
        # Update metrics
        DATASET_ACCESS.labels(
            dataset_id=str(dataset_id), 
            user_role=current_user.get('role', 'unknown')
        ).inc()
        
        result = Dataset(
            id=dataset.id,
            name=dataset.dataset_name,
            description=dataset.dataset_description,
            schema_definition=dataset.schema_definition,
            metadata=dataset.metadata,
            quality_score=float(dataset.quality_score) if dataset.quality_score else 0.0,
            created_at=dataset.created_at,
            updated_at=dataset.updated_at
        )
        
        logger.info("Dataset retrieved successfully", dataset_id=dataset_id)
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get dataset", dataset_id=dataset_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/datasets", response_model=Dataset)
async def register_dataset(
    dataset: Dataset,
    db: Session = Depends(get_database),
    current_user: Dict = Depends(get_current_user)
):
    """Register a new dataset in the catalog"""
    try:
        logger.info("Registering new dataset", name=dataset.name, user_id=current_user.get('id'))
        
        # Extract additional metadata
        enhanced_metadata = await app.state.metadata_extractor.extract(dataset)
        
        # Create catalog entry
        catalog_entry = DataCatalogEntry(
            dataset_name=dataset.name,
            dataset_description=dataset.description,
            schema_definition=dataset.schema_definition,
            metadata={**dataset.metadata, **enhanced_metadata},
            owner_id=current_user.get('id'),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        db.add(catalog_entry)
        db.commit()
        db.refresh(catalog_entry)
        
        # Index for search
        await app.state.search_service.index_dataset(catalog_entry)
        
        # Initialize quality metrics
        await app.state.quality_service.assess_quality(catalog_entry.id)
        
        CATALOG_OPERATIONS.labels(operation="register_dataset").inc()
        
        logger.info("Dataset registered successfully", dataset_id=catalog_entry.id)
        
        return Dataset(
            id=catalog_entry.id,
            name=catalog_entry.dataset_name,
            description=catalog_entry.dataset_description,
            schema_definition=catalog_entry.schema_definition,
            metadata=catalog_entry.metadata,
            quality_score=0.0,  # Will be updated by quality assessment
            created_at=catalog_entry.created_at,
            updated_at=catalog_entry.updated_at
        )
        
    except Exception as e:
        logger.error("Failed to register dataset", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# SEARCH AND DISCOVERY
# =============================================================================

@app.post("/search", response_model=List[Dataset])
async def search_datasets(
    search_request: DatasetSearch,
    db: Session = Depends(get_database),
    current_user: Dict = Depends(get_current_user)
):
    """
    Advanced dataset search with multiple criteria
    
    Supports full-text search across dataset names, descriptions, and metadata
    with filtering by tags, categories, quality scores, and date ranges.
    """
    try:
        logger.info("Searching datasets", query=search_request.query, user_id=current_user.get('id'))
        
        with SEARCH_DURATION.time():
            # Perform search using search service
            search_results = await app.state.search_service.search(search_request)
            
            # Convert to response format
            results = []
            for result in search_results:
                dataset = db.query(DataCatalogEntry).filter(DataCatalogEntry.id == result['id']).first()
                if dataset:
                    results.append(Dataset(
                        id=dataset.id,
                        name=dataset.dataset_name,
                        description=dataset.dataset_description,
                        schema_definition=dataset.schema_definition,
                        metadata=dataset.metadata,
                        quality_score=float(dataset.quality_score) if dataset.quality_score else 0.0,
                        created_at=dataset.created_at,
                        updated_at=dataset.updated_at
                    ))
        
        # Update metrics
        SEARCH_REQUESTS.labels(search_type='advanced').inc()
        
        # Log search for analytics
        access_log = DataAccessLog(
            user_id=current_user.get('id'),
            access_type='search',
            query_executed=search_request.query,
            access_time=datetime.now()
        )
        db.add(access_log)
        db.commit()
        
        logger.info("Search completed", results_count=len(results))
        return results
        
    except Exception as e:
        logger.error("Search failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/search/suggestions")
async def get_search_suggestions(
    q: str = Query(..., description="Partial query for suggestions"),
    current_user: Dict = Depends(get_current_user)
):
    """Get search suggestions based on partial query"""
    try:
        suggestions = await app.state.search_service.get_suggestions(q)
        return {"suggestions": suggestions}
    except Exception as e:
        logger.error("Failed to get search suggestions", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# DATA LINEAGE
# =============================================================================

@app.get("/datasets/{dataset_id}/lineage", response_model=DataLineage)
async def get_data_lineage(
    dataset_id: int,
    depth: int = Query(3, description="Lineage depth to traverse"),
    db: Session = Depends(get_database),
    current_user: Dict = Depends(get_current_user)
):
    """
    Get data lineage for a dataset
    
    Provides complete data lineage showing upstream sources and downstream
    consumers with configurable depth traversal.
    """
    try:
        logger.info("Getting data lineage", dataset_id=dataset_id, depth=depth)
        
        lineage = await app.state.lineage_service.get_lineage(dataset_id, depth)
        
        # Log access
        access_log = DataAccessLog(
            user_id=current_user.get('id'),
            dataset_id=dataset_id,
            access_type='lineage',
            access_time=datetime.now()
        )
        db.add(access_log)
        db.commit()
        
        CATALOG_OPERATIONS.labels(operation="get_lineage").inc()
        
        logger.info("Data lineage retrieved successfully", dataset_id=dataset_id)
        return lineage
        
    except Exception as e:
        logger.error("Failed to get data lineage", dataset_id=dataset_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/datasets/{dataset_id}/lineage")
async def update_data_lineage(
    dataset_id: int,
    lineage_update: Dict[str, Any],
    db: Session = Depends(get_database),
    current_user: Dict = Depends(get_current_user)
):
    """Update data lineage information for a dataset"""
    try:
        logger.info("Updating data lineage", dataset_id=dataset_id)
        
        await app.state.lineage_service.update_lineage(dataset_id, lineage_update)
        
        CATALOG_OPERATIONS.labels(operation="update_lineage").inc()
        
        logger.info("Data lineage updated successfully", dataset_id=dataset_id)
        return {"status": "success", "message": "Data lineage updated"}
        
    except Exception as e:
        logger.error("Failed to update data lineage", dataset_id=dataset_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# DATA QUALITY
# =============================================================================

@app.get("/datasets/{dataset_id}/quality", response_model=DataQualityReport)
async def get_quality_report(
    dataset_id: int,
    db: Session = Depends(get_database),
    current_user: Dict = Depends(get_current_user)
):
    """Get comprehensive data quality report for a dataset"""
    try:
        logger.info("Getting quality report", dataset_id=dataset_id)
        
        # Get latest quality metrics
        quality_metric = db.query(DataQualityMetric).filter(
            DataQualityMetric.dataset_id == dataset_id
        ).order_by(DataQualityMetric.measured_at.desc()).first()
        
        if not quality_metric:
            # Trigger quality assessment if not exists
            await app.state.quality_service.assess_quality(dataset_id)
            quality_metric = db.query(DataQualityMetric).filter(
                DataQualityMetric.dataset_id == dataset_id
            ).order_by(DataQualityMetric.measured_at.desc()).first()
        
        report = DataQualityReport(
            dataset_id=dataset_id,
            completeness_score=float(quality_metric.completeness_score) if quality_metric else 0.0,
            accuracy_score=float(quality_metric.accuracy_score) if quality_metric else 0.0,
            consistency_score=float(quality_metric.consistency_score) if quality_metric else 0.0,
            timeliness_score=float(quality_metric.timeliness_score) if quality_metric else 0.0,
            overall_score=float(quality_metric.overall_score) if quality_metric else 0.0,
            measured_at=quality_metric.measured_at if quality_metric else datetime.now()
        )
        
        # Log access
        access_log = DataAccessLog(
            user_id=current_user.get('id'),
            dataset_id=dataset_id,
            access_type='quality_report',
            access_time=datetime.now()
        )
        db.add(access_log)
        db.commit()
        
        CATALOG_OPERATIONS.labels(operation="get_quality").inc()
        
        logger.info("Quality report retrieved successfully", dataset_id=dataset_id)
        return report
        
    except Exception as e:
        logger.error("Failed to get quality report", dataset_id=dataset_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/datasets/{dataset_id}/quality/assess")
async def trigger_quality_assessment(
    dataset_id: int,
    current_user: Dict = Depends(get_current_user)
):
    """Trigger a new data quality assessment"""
    try:
        logger.info("Triggering quality assessment", dataset_id=dataset_id)
        
        await app.state.quality_service.assess_quality(dataset_id)
        
        CATALOG_OPERATIONS.labels(operation="assess_quality").inc()
        
        logger.info("Quality assessment triggered", dataset_id=dataset_id)
        return {"status": "success", "message": "Quality assessment triggered"}
        
    except Exception as e:
        logger.error("Failed to trigger quality assessment", dataset_id=dataset_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# GOVERNANCE AND AUDIT
# =============================================================================

@app.get("/audit/access")
async def get_access_logs(
    dataset_id: int = None,
    user_id: int = None,
    start_date: str = None,
    end_date: str = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_database),
    current_user: Dict = Depends(get_current_user)
):
    """Get data access audit logs with filtering options"""
    try:
        # Check if user has admin privileges
        if current_user.get('role') not in ['admin', 'fire_chief']:
            raise HTTPException(status_code=403, detail="Insufficient privileges")
        
        logger.info("Retrieving access logs", dataset_id=dataset_id, user_id=user_id)
        
        query = db.query(DataAccessLog)
        
        if dataset_id:
            query = query.filter(DataAccessLog.dataset_id == dataset_id)
        if user_id:
            query = query.filter(DataAccessLog.user_id == user_id)
        if start_date:
            query = query.filter(DataAccessLog.access_time >= start_date)
        if end_date:
            query = query.filter(DataAccessLog.access_time <= end_date)
        
        logs = query.order_by(DataAccessLog.access_time.desc()).offset(skip).limit(limit).all()
        
        result = []
        for log in logs:
            result.append({
                "id": log.id,
                "user_id": log.user_id,
                "dataset_id": log.dataset_id,
                "access_type": log.access_type,
                "query_executed": log.query_executed,
                "access_time": log.access_time.isoformat(),
                "ip_address": str(log.ip_address) if log.ip_address else None
            })
        
        logger.info("Access logs retrieved", count=len(result))
        return {"logs": result, "total": len(result)}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get access logs", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats/usage")
async def get_usage_statistics(
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_database)
):
    """Get catalog usage statistics"""
    try:
        # Basic usage stats
        total_datasets = db.query(DataCatalogEntry).count()
        total_users = db.query(DataAccessLog.user_id.distinct()).count()
        
        # Recent activity
        from sqlalchemy import func
        recent_activity = db.query(func.count(DataAccessLog.id)).filter(
            DataAccessLog.access_time >= datetime.now().date()
        ).scalar()
        
        return {
            "total_datasets": total_datasets,
            "active_users": total_users,
            "daily_activity": recent_activity,
            "average_quality_score": 0.92,  # Would be calculated from actual metrics
            "last_updated": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error("Failed to get usage statistics", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )