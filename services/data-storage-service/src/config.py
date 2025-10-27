"""
Data Storage Service Configuration
"""

import os
from typing import List
from pydantic import validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Data Storage Service settings"""
    
    # Service configuration
    service_name: str = "data-storage-service"
    service_version: str = "1.0.0"
    debug: bool = False
    
    # API configuration
    allowed_origins: List[str] = ["*"]
    allowed_hosts: List[str] = ["*"]
    
    # Database configuration
    database_url: str = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/wildfire_storage")
    timescale_url: str = os.getenv("TIMESCALE_URL", "postgresql://user:password@localhost/wildfire_timeseries")
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # Kafka configuration
    kafka_bootstrap_servers: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
    kafka_enable_consumer: bool = True
    kafka_consumer_group_id: str = os.getenv("KAFKA_CONSUMER_GROUP_ID", "data-storage-consumer")
    kafka_auto_offset_reset: str = os.getenv("KAFKA_AUTO_OFFSET_RESET", "earliest")  # earliest, latest, none
    
    # Connection pool settings
    db_pool_size: int = 5
    db_max_overflow: int = 5
    db_pool_timeout: int = 30
    
    # S3/MinIO configuration
    s3_endpoint: str = os.getenv("S3_ENDPOINT", "http://localhost:9000")
    s3_access_key: str = os.getenv("S3_ACCESS_KEY", "minioadmin")
    s3_secret_key: str = os.getenv("S3_SECRET_KEY", "minioadmin")
    s3_bucket_name: str = os.getenv("S3_BUCKET", "wildfire-data")
    s3_region: str = os.getenv("S3_REGION", "us-west-2")
    
    # Data retention policies
    weather_data_retention_days: int = 2555  # 7 years
    sensor_data_retention_days: int = 1095   # 3 years
    fire_detection_retention_days: int = 3650  # 10 years
    prediction_data_retention_days: int = 365  # 1 year
    
    # Storage optimization
    enable_compression: bool = True
    compression_algorithm: str = "lz4"
    enable_data_archiving: bool = True
    archive_threshold_days: int = 90
    
    # Performance tuning
    batch_insert_size: int = 1000
    query_timeout_seconds: int = 300
    max_concurrent_queries: int = 50
    
    # Monitoring
    enable_metrics: bool = True
    metrics_port: int = 9090
    
    class Config:
        env_file = ".env"
        case_sensitive = False

    @validator("allowed_origins", pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return v.split(",")
        return v
    
    @validator("allowed_hosts", pre=True) 
    def parse_allowed_hosts(cls, v):
        if isinstance(v, str):
            return v.split(",")
        return v


def get_settings() -> Settings:
    """Get application settings"""
    return Settings()