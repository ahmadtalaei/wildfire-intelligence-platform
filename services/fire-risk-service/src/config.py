"""
Configuration management for Fire Risk Service
"""

import os
from functools import lru_cache
from typing import List, Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Application Settings
    app_name: str = "Fire Risk Service"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # API Settings
    api_prefix: str = "/api/v1"
    allowed_hosts: List[str] = ["localhost", "127.0.0.1", "*"]
    allowed_origins: List[str] = ["*"]
    
    # Database Settings
    database_url: str = "postgresql://wildfire_user:wildfire_password@postgres:5432/wildfire_db"
    database_pool_size: int = 20
    database_max_overflow: int = 30
    
    # Redis Settings
    redis_url: str = "redis://:redispassword@redis:6379/0"
    redis_max_connections: int = 100
    
    # InfluxDB Settings (for time-series data)
    influxdb_url: str = "http://influxdb:8086"
    influxdb_token: str = "wildfire-admin-token"
    influxdb_org: str = "wildfire"
    influxdb_bucket: str = "sensors"
    
    # Kafka Settings
    kafka_bootstrap_servers: str = "kafka:29092"
    kafka_consumer_group: str = "fire-risk-service"
    kafka_auto_offset_reset: str = "latest"
    
    # ML Model Settings
    model_path: str = "/app/models"
    model_cache_ttl: int = 3600  # 1 hour
    prediction_timeout: int = 30  # 30 seconds
    
    # Feature Store Settings
    feature_store_path: str = "/app/data/features"
    feature_cache_size: int = 10000
    
    # Geospatial Settings
    default_crs: str = "EPSG:4326"
    max_prediction_distance_km: float = 50.0
    
    # Weather Data Settings
    weather_data_retention_days: int = 365
    weather_update_interval_minutes: int = 60
    
    # Security Settings
    secret_key: str = "your-super-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Monitoring Settings
    enable_metrics: bool = True
    metrics_port: int = 9090
    log_level: str = "INFO"
    
    # External APIs
    nasa_firms_api_key: Optional[str] = None
    copernicus_cds_api_key: Optional[str] = None
    
    # Performance Settings
    max_batch_size: int = 1000
    prediction_cache_ttl: int = 300  # 5 minutes
    concurrent_predictions: int = 100
    
    # Storage Settings
    minio_endpoint: str = "minio:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadminpassword"
    minio_bucket_name: str = "wildfire-data"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings"""
    return Settings()