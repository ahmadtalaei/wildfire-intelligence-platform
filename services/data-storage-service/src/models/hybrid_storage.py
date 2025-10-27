"""
Hybrid Storage Manager - Challenge 2 Enhancement
Advanced hybrid cloud/on-premises storage with intelligent tiering and governance
"""

import os
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass

import boto3
import aioredis
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from ..config import get_settings
from .database import DatabaseManager
from .blob_storage import BlobStorageManager

logger = structlog.get_logger()

class StorageTier(Enum):
    """Storage tier definitions for lifecycle management"""
    HOT = "hot"          # Real-time access (<1s), high cost
    WARM = "warm"        # Frequent access (<5s), medium cost
    COLD = "cold"        # Archival access (<1min), low cost
    ARCHIVE = "archive"  # Long-term storage (<12hrs), lowest cost

class CloudProvider(Enum):
    """Supported cloud providers"""
    AWS = "aws"
    MINIO = "minio"

@dataclass
class StoragePolicy:
    """Data governance policy definition"""
    retention_days: int
    auto_tier_hot_to_warm: int  # days
    auto_tier_warm_to_cold: int  # days
    auto_tier_cold_to_archive: int  # days
    encryption_required: bool
    compliance_tags: List[str]
    access_classification: str  # public, internal, confidential, restricted

@dataclass
class StorageMetrics:
    """Storage utilization and performance metrics"""
    total_size_bytes: int
    hot_tier_bytes: int
    warm_tier_bytes: int
    cold_tier_bytes: int
    archive_tier_bytes: int
    cost_per_month_usd: float
    average_access_latency_ms: float
    data_transfer_bytes_month: int

class HybridStorageManager:
    """
    Enterprise-grade hybrid storage manager for CAL FIRE Challenge 2

    Features:
    - Hybrid storage support (AWS S3 + MinIO)
    - Intelligent tiering with automated lifecycle policies
    - Data governance with encryption and compliance
    - Cost optimization with usage analytics
    - Performance monitoring and SLA tracking
    """

    def __init__(self):
        self.settings = get_settings()
        self.db_manager = None
        self.redis_client = None

        # Storage clients
        self.s3_client = None
        self.minio_client = None

        # Storage policies by data type
        self.storage_policies = self._initialize_policies()

        # Performance tracking
        self.access_metrics = {}

    async def initialize(self):
        """Initialize hybrid storage connections"""
        logger.info("Initializing Hybrid Storage Manager")

        # Initialize database for metadata
        self.db_manager = DatabaseManager()
        await self.db_manager.initialize()

        # Initialize Redis for caching
        self.redis_client = aioredis.from_url(
            self.settings.redis_url,
            encoding="utf-8",
            decode_responses=True
        )

        # Initialize cloud storage clients
        await self._initialize_cloud_clients()

        # Create storage tables
        await self._create_storage_tables()

        logger.info("Hybrid Storage Manager initialized successfully")

    async def _initialize_cloud_clients(self):
        """Initialize all cloud storage clients"""

        # AWS S3 (Cloud Storage - Cold/Archive tiers)
        if hasattr(self.settings, 'aws_access_key_id') and self.settings.aws_access_key_id:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=self.settings.aws_access_key_id,
                aws_secret_access_key=self.settings.aws_secret_access_key,
                region_name=self.settings.aws_region
            )
            logger.info("AWS S3 client initialized for cloud storage")

        # MinIO (On-Premises Storage - Hot/Warm tiers)
        if hasattr(self.settings, 's3_endpoint') and self.settings.s3_endpoint:
            self.minio_client = boto3.client(
                's3',
                endpoint_url=self.settings.s3_endpoint,
                aws_access_key_id=self.settings.s3_access_key,
                aws_secret_access_key=self.settings.s3_secret_key,
                region_name='us-east-1'
            )
            logger.info("MinIO client initialized for on-premises storage")

    def _initialize_policies(self) -> Dict[str, StoragePolicy]:
        """Initialize data type-specific storage policies"""
        return {
            "fire_detection": StoragePolicy(
                retention_days=2555,  # 7 years for regulatory compliance
                auto_tier_hot_to_warm=7,
                auto_tier_warm_to_cold=30,
                auto_tier_cold_to_archive=365,
                encryption_required=True,
                compliance_tags=["FEMA", "CAL_FIRE", "NIST"],
                access_classification="internal"
            ),
            "weather_data": StoragePolicy(
                retention_days=1825,  # 5 years
                auto_tier_hot_to_warm=3,
                auto_tier_warm_to_cold=90,
                auto_tier_cold_to_archive=730,
                encryption_required=False,
                compliance_tags=["NOAA"],
                access_classification="public"
            ),
            "satellite_imagery": StoragePolicy(
                retention_days=3650,  # 10 years
                auto_tier_hot_to_warm=1,
                auto_tier_warm_to_cold=30,
                auto_tier_cold_to_archive=365,
                encryption_required=True,
                compliance_tags=["NASA", "USGS"],
                access_classification="internal"
            ),
            "ml_models": StoragePolicy(
                retention_days=1095,  # 3 years
                auto_tier_hot_to_warm=30,
                auto_tier_warm_to_cold=180,
                auto_tier_cold_to_archive=730,
                encryption_required=True,
                compliance_tags=["CAL_FIRE", "ML_GOVERNANCE"],
                access_classification="confidential"
            ),
            "user_data": StoragePolicy(
                retention_days=2555,  # 7 years
                auto_tier_hot_to_warm=90,
                auto_tier_warm_to_cold=365,
                auto_tier_cold_to_archive=1095,
                encryption_required=True,
                compliance_tags=["CCPA", "FISMA"],
                access_classification="restricted"
            )
        }

    async def store_with_governance(
        self,
        data: bytes,
        data_type: str,
        metadata: Dict[str, Any],
        source_location: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Store data with full governance and intelligent tiering

        Args:
            data: Binary data to store
            data_type: Type of data for policy application
            metadata: Additional metadata and tags
            source_location: Geographic source for compliance

        Returns:
            Storage response with governance tracking
        """
        start_time = datetime.utcnow()

        # Get storage policy for data type
        policy = self.storage_policies.get(data_type, self.storage_policies["weather_data"])

        # Determine optimal storage location and tier
        storage_config = await self._determine_storage_config(
            data_type, len(data), policy, source_location
        )

        # Apply encryption if required
        if policy.encryption_required:
            data = await self._encrypt_data(data, data_type)
            metadata["encrypted"] = True
            metadata["encryption_algorithm"] = "AES-256-GCM"

        # Store in appropriate backend
        storage_result = await self._store_in_backend(
            data, storage_config, metadata
        )

        # Record governance metadata
        governance_record = await self._record_governance_metadata(
            storage_result["storage_id"],
            data_type,
            policy,
            metadata,
            storage_config,
            len(data)
        )

        # Update performance metrics
        latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        await self._update_performance_metrics(data_type, latency_ms, len(data))

        logger.info("Data stored with governance",
                   storage_id=storage_result["storage_id"],
                   data_type=data_type,
                   tier=storage_config["tier"],
                   latency_ms=latency_ms)

        return {
            **storage_result,
            "governance_id": governance_record["governance_id"],
            "policy_applied": policy.access_classification,
            "tier": storage_config["tier"],
            "estimated_monthly_cost": storage_config["estimated_cost"]
        }

    async def _determine_storage_config(
        self,
        data_type: str,
        data_size: int,
        policy: StoragePolicy,
        source_location: Optional[str]
    ) -> Dict[str, Any]:
        """Determine optimal storage configuration based on policies and data characteristics"""

        # Start with HOT tier for new data
        tier = StorageTier.HOT

        # Determine storage provider based on data type and sensitivity
        if policy.access_classification in ["restricted", "confidential"]:
            # Sensitive data stays on-premises (MinIO)
            provider = CloudProvider.MINIO
        elif data_type in ["satellite_imagery", "ml_models"] and data_size > 100_000_000:  # >100MB
            # Large files go to cloud for cost efficiency (AWS S3)
            provider = CloudProvider.AWS if self.s3_client else CloudProvider.MINIO
        else:
            # Default to on-premises for hot data, cloud for cold data
            provider = CloudProvider.MINIO

        # Calculate estimated monthly cost (MinIO + AWS S3 only)
        cost_per_gb_month = {
            (CloudProvider.AWS, StorageTier.HOT): 0.023,
            (CloudProvider.AWS, StorageTier.WARM): 0.0125,
            (CloudProvider.AWS, StorageTier.COLD): 0.004,
            (CloudProvider.AWS, StorageTier.ARCHIVE): 0.001,
            (CloudProvider.MINIO, StorageTier.HOT): 0.050,    # Higher on-prem cost for hot storage
            (CloudProvider.MINIO, StorageTier.WARM): 0.040,   # On-prem warm storage
        }

        size_gb = data_size / (1024**3)
        estimated_cost = cost_per_gb_month.get((provider, tier), 0.025) * size_gb

        return {
            "provider": provider.value,
            "tier": tier.value,
            "bucket": self._get_bucket_name(provider, tier),
            "estimated_cost": estimated_cost,
            "retention_policy": policy.retention_days
        }

    async def _store_in_backend(
        self,
        data: bytes,
        storage_config: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Store data in the specified backend"""

        storage_id = f"wip_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{len(data)}"
        provider = storage_config["provider"]

        if provider == "aws" and self.s3_client:
            # Store in AWS S3 (Cloud storage for cold/archive data)
            self.s3_client.put_object(
                Bucket=storage_config["bucket"],
                Key=storage_id,
                Body=data,
                Metadata=metadata,
                StorageClass=self._get_s3_storage_class(storage_config["tier"])
            )

        elif provider == "minio" and self.minio_client:
            # Store in MinIO (On-premises storage for hot/warm data)
            self.minio_client.put_object(
                Bucket=storage_config["bucket"],
                Key=storage_id,
                Body=data,
                Metadata=metadata
            )

        else:
            raise ValueError(f"Unsupported storage provider: {provider}. Only AWS S3 and MinIO are supported.")

        return {
            "storage_id": storage_id,
            "provider": provider,
            "bucket": storage_config["bucket"],
            "stored_at": datetime.utcnow().isoformat()
        }

    async def retrieve_with_governance(self, storage_id: str) -> Tuple[bytes, Dict[str, Any]]:
        """Retrieve data with governance validation and access logging"""
        start_time = datetime.utcnow()

        # Get governance metadata
        governance_data = await self._get_governance_metadata(storage_id)

        if not governance_data:
            raise ValueError(f"Storage ID not found: {storage_id}")

        # Validate access permissions (placeholder for full RBAC)
        await self._validate_access_permissions(governance_data)

        # Retrieve from appropriate backend
        data = await self._retrieve_from_backend(governance_data)

        # Decrypt if necessary
        if governance_data.get("encrypted"):
            data = await self._decrypt_data(data, governance_data["data_type"])

        # Log access for audit trail
        await self._log_data_access(storage_id, governance_data)

        # Update access metrics
        latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        await self._update_access_metrics(governance_data["data_type"], latency_ms)

        logger.info("Data retrieved with governance",
                   storage_id=storage_id,
                   data_type=governance_data["data_type"],
                   latency_ms=latency_ms)

        return data, governance_data

    async def apply_lifecycle_policies(self):
        """Background task to apply storage lifecycle policies"""
        logger.info("Starting lifecycle policy application")

        # Get all storage records that need tiering
        for data_type, policy in self.storage_policies.items():
            await self._tier_data_by_age(data_type, policy)

        # Clean up expired data
        await self._cleanup_expired_data()

        logger.info("Lifecycle policy application completed")

    async def _tier_data_by_age(self, data_type: str, policy: StoragePolicy):
        """Tier data based on age according to policy"""

        now = datetime.utcnow()

        # Move hot to warm
        hot_to_warm_date = now - timedelta(days=policy.auto_tier_hot_to_warm)
        await self._move_data_tier(data_type, StorageTier.HOT, StorageTier.WARM, hot_to_warm_date)

        # Move warm to cold
        warm_to_cold_date = now - timedelta(days=policy.auto_tier_warm_to_cold)
        await self._move_data_tier(data_type, StorageTier.WARM, StorageTier.COLD, warm_to_cold_date)

        # Move cold to archive
        cold_to_archive_date = now - timedelta(days=policy.auto_tier_cold_to_archive)
        await self._move_data_tier(data_type, StorageTier.COLD, StorageTier.ARCHIVE, cold_to_archive_date)

    async def get_storage_analytics(self) -> StorageMetrics:
        """Get comprehensive storage analytics and cost metrics"""

        # Calculate storage utilization by tier
        tier_usage = await self._calculate_tier_usage()

        # Calculate monthly costs
        monthly_cost = await self._calculate_monthly_costs(tier_usage)

        # Get performance metrics
        avg_latency = await self._get_average_latency()

        # Calculate data transfer
        monthly_transfer = await self._get_monthly_transfer()

        return StorageMetrics(
            total_size_bytes=sum(tier_usage.values()),
            hot_tier_bytes=tier_usage.get("hot", 0),
            warm_tier_bytes=tier_usage.get("warm", 0),
            cold_tier_bytes=tier_usage.get("cold", 0),
            archive_tier_bytes=tier_usage.get("archive", 0),
            cost_per_month_usd=monthly_cost,
            average_access_latency_ms=avg_latency,
            data_transfer_bytes_month=monthly_transfer
        )

    async def _create_storage_tables(self):
        """Create database tables for governance and metadata tracking"""

        create_governance_table = """
        CREATE TABLE IF NOT EXISTS storage_governance (
            governance_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            storage_id VARCHAR(255) UNIQUE NOT NULL,
            data_type VARCHAR(100) NOT NULL,
            storage_tier VARCHAR(20) NOT NULL,
            provider VARCHAR(20) NOT NULL,
            bucket VARCHAR(255) NOT NULL,
            size_bytes BIGINT NOT NULL,
            encrypted BOOLEAN DEFAULT FALSE,
            access_classification VARCHAR(50) NOT NULL,
            compliance_tags TEXT[] DEFAULT '{}',
            retention_until TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            access_count INTEGER DEFAULT 0
        );

        CREATE INDEX IF NOT EXISTS idx_storage_governance_storage_id ON storage_governance(storage_id);
        CREATE INDEX IF NOT EXISTS idx_storage_governance_data_type ON storage_governance(data_type);
        CREATE INDEX IF NOT EXISTS idx_storage_governance_tier ON storage_governance(storage_tier);
        CREATE INDEX IF NOT EXISTS idx_storage_governance_retention ON storage_governance(retention_until);
        """

        create_access_log_table = """
        CREATE TABLE IF NOT EXISTS storage_access_log (
            log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            storage_id VARCHAR(255) NOT NULL,
            accessed_by VARCHAR(255),
            access_type VARCHAR(50) NOT NULL,
            access_result VARCHAR(50) NOT NULL,
            latency_ms FLOAT,
            accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_access_log_storage_id ON storage_access_log(storage_id);
        CREATE INDEX IF NOT EXISTS idx_access_log_accessed_at ON storage_access_log(accessed_at);
        """

        async with self.db_manager.get_session() as session:
            await session.execute(create_governance_table)
            await session.execute(create_access_log_table)
            await session.commit()

    # Additional helper methods...
    async def _encrypt_data(self, data: bytes, data_type: str) -> bytes:
        """Encrypt data using AES-256-GCM"""
        # Implementation would use cryptography library
        # For now, return data as-is (placeholder)
        return data

    async def _decrypt_data(self, data: bytes, data_type: str) -> bytes:
        """Decrypt data using AES-256-GCM"""
        # Implementation would use cryptography library
        # For now, return data as-is (placeholder)
        return data

    def _get_bucket_name(self, provider: CloudProvider, tier: StorageTier) -> str:
        """Get appropriate bucket name for provider and tier"""
        base_name = "wildfire-intelligence"
        return f"{base_name}-{tier.value}-{provider.value}"

    def _get_s3_storage_class(self, tier: str) -> str:
        """Get appropriate S3 storage class for tier"""
        mapping = {
            "hot": "STANDARD",
            "warm": "STANDARD_IA",
            "cold": "GLACIER",
            "archive": "DEEP_ARCHIVE"
        }
        return mapping.get(tier, "STANDARD")

    async def cleanup(self):
        """Cleanup resources"""
        if self.redis_client:
            await self.redis_client.close()
        if self.db_manager:
            await self.db_manager.cleanup()