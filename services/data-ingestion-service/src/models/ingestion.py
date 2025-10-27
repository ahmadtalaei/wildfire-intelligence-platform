"""Data ingestion models"""
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import date

class DataSource(BaseModel):
    id: str
    name: str
    source_type: str
    description: Optional[str] = None
    provider: Optional[str] = None
    formats: Optional[List[str]] = None
    update_frequency: Optional[str] = None
    spatial_resolution: Optional[str] = None
    temporal_resolution: Optional[str] = None
    is_active: Optional[bool] = True
    api_endpoint: Optional[str] = None
    authentication_required: Optional[bool] = False
    
class IngestionRequest(BaseModel):
    request_id: str
    source_id: str
    
class IngestionResponse(BaseModel):
    request_id: str
    status: str
    records_processed: int
    data_quality_score: float
    processing_time_seconds: float
    
class StreamingConfig(BaseModel):
    source_id: str
    stream_type: str = "real_time"
    buffer_size: int = 500
    batch_interval_seconds: int = 60
    polling_interval_seconds: int = 300
    timeout_seconds: float = 30.0  # API request timeout (increase for large files like GRIB2)
    max_retries: int = 3
    retry_delay_seconds: int = 30
    spatial_bounds: Optional[Dict[str, float]] = None
    preferred_format: str = "csv"
    
class BatchConfig(BaseModel):
    request_id: str = "batch_001"
    source_id: str
    source_type: str = "satellite"
    start_date: date
    end_date: date
    spatial_bounds: Optional[Dict[str, float]] = None
    format: str = "csv"
    validation_enabled: bool = True
    validation_config: Optional[Dict[str, Any]] = None
    processing_config: Optional[Dict[str, Any]] = None
    
class ValidationConfig(BaseModel):
    enabled: bool = True