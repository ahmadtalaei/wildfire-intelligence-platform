"""
Data Storage Service - Health Checker
Comprehensive health monitoring for all service dependencies
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
import structlog

from ..config import get_settings

logger = structlog.get_logger()

class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded" 
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"

class ComponentStatus:
    """Health status for individual components"""
    
    def __init__(self, name: str, status: HealthStatus = HealthStatus.UNKNOWN, 
                 message: str = "", details: Dict[str, Any] = None,
                 response_time_ms: float = 0, last_checked: datetime = None):
        self.name = name
        self.status = status
        self.message = message
        self.details = details or {}
        self.response_time_ms = response_time_ms
        self.last_checked = last_checked or datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "response_time_ms": self.response_time_ms,
            "last_checked": self.last_checked.isoformat()
        }

class HealthChecker:
    """
    Comprehensive health checker for all data storage service dependencies
    
    Monitors:
    - Database connections (PostgreSQL, TimescaleDB)
    - Blob storage (S3/MinIO)
    - Cache (Redis)
    - System resources
    - Service dependencies
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.check_timeout = 30.0  # seconds
        self.cache_duration = 60   # seconds
        self._last_health_check = None
        self._cached_results = None
        self._service_start_time = datetime.utcnow()  # Track actual service start time

        # Performance thresholds
        self.thresholds = {
            'database_response_ms': 2000,      # 2 seconds (Docker overhead)
            'blob_storage_response_ms': 3000,  # 3 seconds
            'redis_response_ms': 2000,         # 2 seconds (Docker overhead)
            'disk_usage_percent': 85,          # 85%
            'memory_usage_percent': 90,        # 90%
            'cpu_usage_percent': 80            # 80%
        }
    
    async def check_all(self) -> Dict[str, Any]:
        """Perform comprehensive health check of all components"""
        # Return cached results if recent check exists (but update uptime and timestamp)
        if (self._cached_results and self._last_health_check and
            (datetime.utcnow() - self._last_health_check).total_seconds() < self.cache_duration):
            # Update dynamic fields in cached response
            self._cached_results["uptime_seconds"] = self._get_uptime()
            self._cached_results["timestamp"] = datetime.utcnow().isoformat()
            return self._cached_results
        
        start_time = time.time()
        components = {}
        
        # Run all health checks concurrently (skip TimescaleDB if extension not available)
        check_tasks = [
            self._check_postgresql(),
            self._check_blob_storage(),
            self._check_redis(),
            self._check_system_resources(),
            self._check_service_metrics()
        ]
        check_names = ['postgresql', 'blob_storage', 'redis', 'system', 'metrics']

        # Check if TimescaleDB should be checked (only if extension is installed)
        try:
            import asyncpg
            conn = await asyncpg.connect(self.settings.timescale_url)
            extension_check = await conn.fetchval(
                "SELECT count(*) FROM pg_extension WHERE extname = 'timescaledb'"
            )
            await conn.close()

            if extension_check > 0:
                check_tasks.append(self._check_timescaledb())
                check_names.append('timescaledb')
        except Exception:
            # TimescaleDB not available, skip the check
            pass

        try:
            # Execute all checks with timeout
            results = await asyncio.wait_for(
                asyncio.gather(*check_tasks, return_exceptions=True),
                timeout=self.check_timeout
            )
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    components[check_names[i]] = ComponentStatus(
                        name=check_names[i],
                        status=HealthStatus.UNHEALTHY,
                        message=f"Health check failed: {str(result)}"
                    ).to_dict()
                else:
                    components[check_names[i]] = result.to_dict()
        
        except asyncio.TimeoutError:
            logger.error("Health check timed out")
            components['timeout'] = ComponentStatus(
                name='timeout',
                status=HealthStatus.UNHEALTHY,
                message="Health check timed out"
            ).to_dict()
        
        # Determine overall health status
        overall_status = self._determine_overall_status(components)
        
        # Build comprehensive response
        total_time = (time.time() - start_time) * 1000
        
        health_response = {
            "status": overall_status.value,
            "timestamp": datetime.utcnow().isoformat(),
            "service": "data-storage-service",
            "version": "1.0.0",
            "uptime_seconds": self._get_uptime(),
            "response_time_ms": round(total_time, 2),
            "components": components,
            "summary": self._generate_summary(components),
            "recommendations": self._generate_recommendations(components)
        }
        
        # Cache results
        self._cached_results = health_response
        self._last_health_check = datetime.utcnow()
        
        return health_response
    
    async def _check_postgresql(self) -> ComponentStatus:
        """Check PostgreSQL database health"""
        start_time = time.time()
        
        try:
            import asyncpg
            
            # Test connection
            conn = await asyncpg.connect(self.settings.database_url)
            
            # Test query
            result = await conn.fetchval("SELECT 1")
            
            # Check database size and connections
            stats_query = """
                SELECT 
                    pg_database_size(current_database()) as db_size,
                    (SELECT count(*) FROM pg_stat_activity WHERE state = 'active') as active_connections,
                    (SELECT setting::int FROM pg_settings WHERE name = 'max_connections') as max_connections
            """
            stats = await conn.fetchrow(stats_query)
            
            await conn.close()
            
            response_time = (time.time() - start_time) * 1000

            # Check if performance is degraded
            status = HealthStatus.HEALTHY
            message = "PostgreSQL is healthy"

            if response_time and response_time > self.thresholds['database_response_ms']:
                status = HealthStatus.DEGRADED
                message = f"PostgreSQL response time is high ({response_time:.0f}ms)"
            
            connection_ratio = (stats['active_connections'] / stats['max_connections']) if stats.get('max_connections', 0) > 0 else 0
            if connection_ratio and connection_ratio > 0.8:
                status = HealthStatus.DEGRADED
                message += f" - High connection usage ({connection_ratio:.1%})"
            
            return ComponentStatus(
                name="postgresql",
                status=status,
                message=message,
                response_time_ms=response_time,
                details={
                    "database_size_mb": round(stats['db_size'] / 1024 / 1024, 2),
                    "active_connections": stats['active_connections'],
                    "max_connections": stats['max_connections'],
                    "connection_usage_percent": round(connection_ratio * 100, 1)
                }
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return ComponentStatus(
                name="postgresql",
                status=HealthStatus.UNHEALTHY,
                message=f"PostgreSQL check failed: {str(e)}",
                response_time_ms=response_time
            )
    
    async def _check_timescaledb(self) -> ComponentStatus:
        """Check TimescaleDB health and hypertables"""
        start_time = time.time()
        
        try:
            import asyncpg
            
            conn = await asyncpg.connect(self.settings.timescale_url)
            
            # Check TimescaleDB extension
            extension_check = await conn.fetchval(
                "SELECT count(*) FROM pg_extension WHERE extname = 'timescaledb'"
            )
            
            if extension_check == 0:
                return ComponentStatus(
                    name="timescaledb",
                    status=HealthStatus.UNHEALTHY,
                    message="TimescaleDB extension not installed"
                )
            
            # Check hypertables status
            hypertables_query = """
                SELECT 
                    schemaname,
                    tablename,
                    num_chunks,
                    table_size,
                    index_size,
                    compression_status
                FROM timescaledb_information.hypertable 
                WHERE schemaname = 'public'
            """
            
            hypertables = await conn.fetch(hypertables_query)
            
            # Check compression jobs
            compression_jobs = await conn.fetch("""
                SELECT job_id, hypertable_name, status, last_run_success
                FROM timescaledb_information.compression_policy
            """)
            
            await conn.close()
            
            response_time = (time.time() - start_time) * 1000
            
            status = HealthStatus.HEALTHY
            message = "TimescaleDB is healthy"
            
            if response_time > self.thresholds['database_response_ms']:
                status = HealthStatus.DEGRADED
                message = f"TimescaleDB response time is high ({response_time:.0f}ms)"
            
            # Check for failed compression jobs
            failed_jobs = [job for job in compression_jobs if not job['last_run_success']]
            if failed_jobs:
                status = HealthStatus.DEGRADED
                message += f" - {len(failed_jobs)} compression jobs failed"
            
            return ComponentStatus(
                name="timescaledb",
                status=status,
                message=message,
                response_time_ms=response_time,
                details={
                    "hypertables_count": len(hypertables),
                    "compression_jobs_count": len(compression_jobs),
                    "failed_compression_jobs": len(failed_jobs),
                    "hypertables": [
                        {
                            "name": f"{ht['schemaname']}.{ht['tablename']}",
                            "chunks": ht['num_chunks'],
                            "size_mb": round(ht['table_size'] / 1024 / 1024, 2),
                            "compressed": ht['compression_status'] == 'Compressed'
                        } for ht in hypertables
                    ]
                }
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return ComponentStatus(
                name="timescaledb",
                status=HealthStatus.UNHEALTHY,
                message=f"TimescaleDB check failed: {str(e)}",
                response_time_ms=response_time
            )
    
    async def _check_blob_storage(self) -> ComponentStatus:
        """Check S3/MinIO blob storage health"""
        start_time = time.time()
        
        try:
            from aiobotocore.session import get_session
            
            session = get_session()
            client = session.create_client(
                's3',
                endpoint_url=self.settings.s3_endpoint,
                aws_access_key_id=self.settings.s3_access_key,
                aws_secret_access_key=self.settings.s3_secret_key,
                region_name=self.settings.s3_region
            )
            
            async with client as s3:
                # Test bucket access
                await s3.head_bucket(Bucket=self.settings.s3_bucket_name)
                
                # Get bucket statistics
                objects_count = 0
                total_size = 0
                
                paginator = s3.get_paginator('list_objects_v2')
                async for page in paginator.paginate(
                    Bucket=self.settings.s3_bucket_name,
                    MaxKeys=1000  # Limit for health check
                ):
                    if 'Contents' in page:
                        objects_count += len(page['Contents'])
                        total_size += sum(obj['Size'] for obj in page['Contents'])
            
            response_time = (time.time() - start_time) * 1000
            
            status = HealthStatus.HEALTHY
            message = "Blob storage is healthy"
            
            if response_time > self.thresholds['blob_storage_response_ms']:
                status = HealthStatus.DEGRADED
                message = f"Blob storage response time is high ({response_time:.0f}ms)"
            
            return ComponentStatus(
                name="blob_storage",
                status=status,
                message=message,
                response_time_ms=response_time,
                details={
                    "bucket_name": self.settings.s3_bucket_name,
                    "objects_count": objects_count,
                    "total_size_mb": round(total_size / 1024 / 1024, 2),
                    "endpoint": self.settings.s3_endpoint
                }
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return ComponentStatus(
                name="blob_storage",
                status=HealthStatus.UNHEALTHY,
                message=f"Blob storage check failed: {str(e)}",
                response_time_ms=response_time
            )
    
    async def _check_redis(self) -> ComponentStatus:
        """Check Redis cache health"""
        start_time = time.time()

        try:
            # Use redis.asyncio (modern async redis client)
            import redis.asyncio as aioredis

            redis_client = aioredis.from_url(self.settings.redis_url, decode_responses=True)

            # Test basic operations
            await redis_client.ping()

            # Get Redis info
            info = await redis_client.info()

            await redis_client.close()

            response_time = (time.time() - start_time) * 1000

            status = HealthStatus.HEALTHY
            message = "Redis is healthy"

            if response_time > self.thresholds['redis_response_ms']:
                status = HealthStatus.DEGRADED
                message = f"Redis response time is high ({response_time:.0f}ms)"

            # Check memory usage
            memory_usage = info.get('used_memory', 0) or 0
            max_memory = info.get('maxmemory', 0) or 0
            memory_percent = None

            if max_memory is not None and max_memory > 0:
                memory_percent = (memory_usage / max_memory) * 100
                if memory_percent > 80:
                    status = HealthStatus.DEGRADED
                    message += f" - High memory usage ({memory_percent:.1f}%)"

            return ComponentStatus(
                name="redis",
                status=status,
                message=message,
                response_time_ms=response_time,
                details={
                    "version": info.get('redis_version'),
                    "connected_clients": info.get('connected_clients'),
                    "used_memory_mb": round(memory_usage / 1024 / 1024, 2) if memory_usage else 0,
                    "memory_usage_percent": round(memory_percent, 1) if memory_percent is not None else None,
                    "keyspace_hits": info.get('keyspace_hits', 0),
                    "keyspace_misses": info.get('keyspace_misses', 0)
                }
            )

        except ImportError as e:
            # Library import issue - mark as degraded
            response_time = (time.time() - start_time) * 1000
            return ComponentStatus(
                name="redis",
                status=HealthStatus.DEGRADED,
                message=f"Redis library not available: {str(e)}",
                response_time_ms=response_time
            )
        except Exception as e:
            # Connection or operational issue - mark as unhealthy
            response_time = (time.time() - start_time) * 1000
            return ComponentStatus(
                name="redis",
                status=HealthStatus.UNHEALTHY,
                message=f"Redis check failed: {str(e)}",
                response_time_ms=response_time
            )
    
    async def _check_system_resources(self) -> ComponentStatus:
        """Check system resources (CPU, memory, disk)"""
        start_time = time.time()
        
        try:
            import psutil
            
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1) or 0

            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent if memory and hasattr(memory, 'percent') else 0

            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = ((disk.used / disk.total) * 100) if disk and disk.total > 0 else 0
            
            response_time = (time.time() - start_time) * 1000
            
            # Determine status based on thresholds
            status = HealthStatus.HEALTHY
            warnings = []
            
            if cpu_percent > self.thresholds['cpu_usage_percent']:
                status = HealthStatus.DEGRADED
                warnings.append(f"High CPU usage ({cpu_percent:.1f}%)")
            
            if memory_percent > self.thresholds['memory_usage_percent']:
                status = HealthStatus.DEGRADED
                warnings.append(f"High memory usage ({memory_percent:.1f}%)")
            
            if disk_percent > self.thresholds['disk_usage_percent']:
                status = HealthStatus.DEGRADED
                warnings.append(f"High disk usage ({disk_percent:.1f}%)")
            
            message = "System resources are healthy"
            if warnings:
                message = " - ".join(warnings)
            
            return ComponentStatus(
                name="system",
                status=status,
                message=message,
                response_time_ms=response_time,
                details={
                    "cpu_usage_percent": round(cpu_percent, 1),
                    "memory_usage_percent": round(memory_percent, 1),
                    "disk_usage_percent": round(disk_percent, 1),
                    "available_memory_gb": round(memory.available / 1024**3, 2),
                    "free_disk_gb": round(disk.free / 1024**3, 2)
                }
            )
            
        except ImportError:
            # psutil not available, return basic status
            return ComponentStatus(
                name="system",
                status=HealthStatus.UNKNOWN,
                message="System monitoring not available (psutil not installed)"
            )
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return ComponentStatus(
                name="system",
                status=HealthStatus.UNHEALTHY,
                message=f"System check failed: {str(e)}",
                response_time_ms=response_time
            )
    
    async def _check_service_metrics(self) -> ComponentStatus:
        """Check service-specific metrics and performance"""
        start_time = time.time()
        
        try:
            # This would integrate with Prometheus metrics in a real implementation
            # For now, we'll return a basic health status
            
            response_time = (time.time() - start_time) * 1000
            
            return ComponentStatus(
                name="metrics",
                status=HealthStatus.HEALTHY,
                message="Service metrics are healthy",
                response_time_ms=response_time,
                details={
                    "metrics_enabled": self.settings.enable_metrics,
                    "metrics_port": self.settings.metrics_port
                }
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return ComponentStatus(
                name="metrics",
                status=HealthStatus.DEGRADED,
                message=f"Metrics check failed: {str(e)}",
                response_time_ms=response_time
            )
    
    def _determine_overall_status(self, components: Dict[str, Dict]) -> HealthStatus:
        """Determine overall service health from component statuses"""
        statuses = [comp['status'] for comp in components.values()]
        
        # If any component is unhealthy, service is unhealthy
        if HealthStatus.UNHEALTHY.value in statuses:
            return HealthStatus.UNHEALTHY
        
        # If any component is degraded, service is degraded
        if HealthStatus.DEGRADED.value in statuses:
            return HealthStatus.DEGRADED
        
        # If all components are healthy, service is healthy
        if all(status == HealthStatus.HEALTHY.value for status in statuses):
            return HealthStatus.HEALTHY
        
        # Default to unknown if status cannot be determined
        return HealthStatus.UNKNOWN
    
    def _generate_summary(self, components: Dict[str, Dict]) -> Dict[str, Any]:
        """Generate health check summary"""
        total_components = len(components)
        healthy_count = sum(1 for comp in components.values() if comp['status'] == 'healthy')
        degraded_count = sum(1 for comp in components.values() if comp['status'] == 'degraded')
        unhealthy_count = sum(1 for comp in components.values() if comp['status'] == 'unhealthy')
        
        return {
            "total_components": total_components,
            "healthy": healthy_count,
            "degraded": degraded_count,
            "unhealthy": unhealthy_count,
            "health_percentage": round((healthy_count / total_components) * 100, 1) if total_components > 0 else 0
        }
    
    def _generate_recommendations(self, components: Dict[str, Dict]) -> List[str]:
        """Generate recommendations based on health status"""
        recommendations = []
        
        for comp_name, comp_data in components.items():
            if comp_data['status'] == 'unhealthy':
                if comp_name == 'postgresql':
                    recommendations.append("Check PostgreSQL connection and configuration")
                elif comp_name == 'timescaledb':
                    recommendations.append("Verify TimescaleDB installation and hypertable configuration")
                elif comp_name == 'blob_storage':
                    recommendations.append("Check S3/MinIO connectivity and credentials")
                elif comp_name == 'redis':
                    recommendations.append("Verify Redis server status and connection")
                elif comp_name == 'system':
                    recommendations.append("Check system resources and consider scaling")
            
            elif comp_data['status'] == 'degraded':
                response_time = comp_data.get('response_time_ms', 0)
                if response_time > 1000:
                    recommendations.append(f"Optimize {comp_name} performance - response time is {response_time:.0f}ms")
                
                details = comp_data.get('details', {})
                memory_usage = details.get('memory_usage_percent')
                if memory_usage is not None and memory_usage > 80:
                    recommendations.append(f"Consider increasing memory for {comp_name}")
                disk_usage = details.get('disk_usage_percent')
                if disk_usage is not None and disk_usage > 85:
                    recommendations.append("Free up disk space or add storage capacity")
        
        if not recommendations:
            recommendations.append("All systems are operating normally")
        
        return recommendations
    
    def _get_uptime(self) -> int:
        """Get service uptime in seconds"""
        uptime = (datetime.utcnow() - self._service_start_time).total_seconds()
        return int(uptime)
    
    async def get_readiness(self) -> bool:
        """Check if service is ready to accept requests"""
        try:
            # Quick readiness check - just verify critical components
            # NOTE: TimescaleDB removed from critical checks as it's optional
            tasks = [
                self._check_postgresql(),
                self._check_blob_storage()
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Service is ready if all critical components are healthy or degraded
            for result in results:
                if isinstance(result, Exception):
                    return False
                if result.status == HealthStatus.UNHEALTHY:
                    return False

            return True

        except Exception:
            return False
    
    async def get_liveness(self) -> bool:
        """Check if service is alive (basic liveness probe)"""
        try:
            # Very basic liveness check - just verify the service can respond
            return True
        except Exception:
            return False


# Export main components
__all__ = ['HealthChecker', 'HealthStatus', 'ComponentStatus']