"""
Data Storage Service - Data Models
Pydantic models for data storage operations
"""

from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from pydantic import BaseModel, Field
from enum import Enum


class DataType(str, Enum):
    WEATHER = "weather"
    SENSOR = "sensor"  
    FIRE_DETECTION = "fire_detection"
    PREDICTIONS = "predictions"
    SATELLITE_IMAGE = "satellite_image"
    MODEL_FILE = "model_file"
    ARCHIVE = "archive"
    METADATA = "metadata"


class StorageBackend(str, Enum):
    TIMESCALE = "timescale"
    POSTGRESQL = "postgresql" 
    S3_MINIO = "s3_minio"
    REDIS = "redis"


class StorageRequest(BaseModel):
    """Request model for storing data"""
    data_type: DataType
    data: Union[Dict[str, Any], List[Dict[str, Any]]]
    metadata: Optional[Dict[str, Any]] = None
    source_id: Optional[str] = None
    timestamp: Optional[datetime] = Field(default_factory=datetime.now)
    tags: Optional[List[str]] = None
    retention_days: Optional[int] = None


class BulkStorageRequest(BaseModel):
    """Request model for bulk data storage"""
    data_type: DataType
    data_items: List[Dict[str, Any]]
    metadata: Optional[Dict[str, Any]] = None
    source_id: Optional[str] = None
    batch_timestamp: Optional[datetime] = Field(default_factory=datetime.now)
    tags: Optional[List[str]] = None


class StorageResponse(BaseModel):
    """Response model for storage operations"""
    storage_id: str
    data_type: DataType
    backend: StorageBackend
    size_bytes: int
    timestamp: datetime
    status: str = "stored"


class QueryRequest(BaseModel):
    """Request model for querying stored data"""
    data_type: DataType
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    filters: Optional[Dict[str, Any]] = None
    spatial_bounds: Optional[Dict[str, float]] = None
    limit: Optional[int] = 1000
    offset: Optional[int] = 0
    aggregation: Optional[Dict[str, Any]] = None
    include_metadata: bool = False


class QueryResponse(BaseModel):
    """Response model for query operations"""
    data: List[Dict[str, Any]]
    total_records: int
    data_type: DataType
    query_time_ms: float
    metadata: Optional[Dict[str, Any]] = None


class MetadataRequest(BaseModel):
    """Request model for metadata operations"""
    storage_id: str
    metadata: Dict[str, Any]
    operation: str = "update"  # update, append, replace


class ArchiveRequest(BaseModel):
    """Request model for data archiving"""
    data_type: DataType
    older_than_days: int = 90
    destination: str = "cold_storage"
    compress: bool = True
    delete_original: bool = False