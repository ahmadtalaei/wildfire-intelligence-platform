"""
Data Storage Service - Prometheus Monitoring Middleware
Custom middleware for detailed metrics collection and monitoring
"""

import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from prometheus_client import Counter, Histogram, Gauge
import structlog

logger = structlog.get_logger()

# Prometheus metrics
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code', 'data_type']
)

REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint', 'status_code'],
    buckets=(0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0)
)

REQUEST_SIZE = Histogram(
    'http_request_size_bytes',
    'HTTP request size in bytes',
    ['method', 'endpoint'],
    buckets=(1024, 4096, 16384, 65536, 262144, 1048576, 4194304, 16777216)
)

RESPONSE_SIZE = Histogram(
    'http_response_size_bytes', 
    'HTTP response size in bytes',
    ['method', 'endpoint', 'status_code'],
    buckets=(1024, 4096, 16384, 65536, 262144, 1048576, 4194304, 16777216)
)

ACTIVE_REQUESTS = Gauge(
    'http_requests_active',
    'Number of active HTTP requests',
    ['method', 'endpoint']
)

DATA_THROUGHPUT = Counter(
    'data_throughput_bytes_total',
    'Total data throughput in bytes',
    ['operation', 'data_type', 'direction']
)

ERROR_RATE = Counter(
    'http_errors_total',
    'Total HTTP errors',
    ['method', 'endpoint', 'error_type', 'status_code']
)

STORAGE_OPERATIONS_LATENCY = Histogram(
    'storage_operation_latency_seconds',
    'Storage operation latency',
    ['backend', 'operation', 'data_type'],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0)
)

DATABASE_CONNECTIONS = Gauge(
    'database_connections_active',
    'Active database connections',
    ['database_type', 'pool_name']
)

class PrometheusMiddleware(BaseHTTPMiddleware):
    """
    Advanced Prometheus monitoring middleware for data storage service
    
    Collects comprehensive metrics:
    - Request/response timing and sizes
    - Error rates and types
    - Data throughput metrics
    - Storage operation performance
    - Database connection health
    """
    
    def __init__(self, app):
        super().__init__(app)
        self.excluded_paths = {'/health', '/metrics', '/favicon.ico'}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and collect metrics"""
        # Skip metrics for excluded paths
        if request.url.path in self.excluded_paths:
            return await call_next(request)
        
        # Extract request information
        method = request.method
        endpoint = self._normalize_endpoint(request.url.path)
        
        # Get request size
        request_size = int(request.headers.get('content-length', 0))
        
        # Track active requests
        ACTIVE_REQUESTS.labels(method=method, endpoint=endpoint).inc()
        
        # Record request size
        if request_size > 0:
            REQUEST_SIZE.labels(method=method, endpoint=endpoint).observe(request_size)
        
        start_time = time.time()
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate request duration
            duration = time.time() - start_time
            
            # Get response information
            status_code = str(response.status_code)
            response_size = int(response.headers.get('content-length', 0))
            
            # Extract data type from request if available
            data_type = self._extract_data_type(request)
            
            # Record metrics
            REQUEST_COUNT.labels(
                method=method,
                endpoint=endpoint,
                status_code=status_code,
                data_type=data_type or 'unknown'
            ).inc()
            
            REQUEST_DURATION.labels(
                method=method,
                endpoint=endpoint,
                status_code=status_code
            ).observe(duration)
            
            if response_size > 0:
                RESPONSE_SIZE.labels(
                    method=method,
                    endpoint=endpoint,
                    status_code=status_code
                ).observe(response_size)
            
            # Record data throughput for storage operations
            if endpoint in ['/store', '/store/bulk', '/query']:
                direction = 'inbound' if method in ['POST', 'PUT'] else 'outbound'
                size = request_size if direction == 'inbound' else response_size
                
                if size > 0 and data_type:
                    DATA_THROUGHPUT.labels(
                        operation=endpoint.lstrip('/'),
                        data_type=data_type,
                        direction=direction
                    ).inc(size)
            
            # Log slow requests
            if duration > 1.0:  # Requests taking more than 1 second
                logger.warning("Slow request detected",
                             method=method,
                             endpoint=endpoint,
                             duration_seconds=duration,
                             status_code=status_code)
            
            # Record error metrics for non-2xx responses
            if not (200 <= response.status_code < 300):
                error_type = self._classify_error(response.status_code)
                ERROR_RATE.labels(
                    method=method,
                    endpoint=endpoint,
                    error_type=error_type,
                    status_code=status_code
                ).inc()
            
            return response
            
        except Exception as e:
            duration = time.time() - start_time
            
            # Record error metrics
            ERROR_RATE.labels(
                method=method,
                endpoint=endpoint,
                error_type='exception',
                status_code='500'
            ).inc()
            
            logger.error("Request processing failed",
                        method=method,
                        endpoint=endpoint,
                        duration_seconds=duration,
                        error=str(e))
            
            raise
            
        finally:
            # Decrement active requests counter
            ACTIVE_REQUESTS.labels(method=method, endpoint=endpoint).dec()

    def _normalize_endpoint(self, path: str) -> str:
        """Normalize endpoint path to reduce cardinality"""
        # Replace UUIDs and IDs with placeholders
        import re
        
        # Replace UUID patterns
        path = re.sub(r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', '/{id}', path)
        
        # Replace numeric IDs
        path = re.sub(r'/\d+', '/{id}', path)
        
        # Handle common patterns
        path = re.sub(r'/data/[^/]+', '/data/{storage_id}', path)
        
        return path

    def _extract_data_type(self, request: Request) -> str:
        """Extract data type from request for metrics labeling"""
        try:
            # Check query parameters
            if 'data_type' in request.query_params:
                return request.query_params['data_type']
            
            # For POST requests, try to extract from body (if already parsed)
            if hasattr(request.state, 'json_body'):
                body = request.state.json_body
                if isinstance(body, dict) and 'data_type' in body:
                    return body['data_type']
            
            return None
            
        except Exception:
            return None

    def _classify_error(self, status_code: int) -> str:
        """Classify HTTP error types"""
        if 400 <= status_code < 500:
            if status_code == 400:
                return 'bad_request'
            elif status_code == 401:
                return 'unauthorized'
            elif status_code == 403:
                return 'forbidden'
            elif status_code == 404:
                return 'not_found'
            elif status_code == 422:
                return 'validation_error'
            elif status_code == 429:
                return 'rate_limited'
            else:
                return 'client_error'
        elif 500 <= status_code < 600:
            if status_code == 500:
                return 'internal_error'
            elif status_code == 502:
                return 'bad_gateway'
            elif status_code == 503:
                return 'service_unavailable'
            elif status_code == 504:
                return 'gateway_timeout'
            else:
                return 'server_error'
        else:
            return 'unknown_error'


def record_storage_operation(backend: str, operation: str, data_type: str, duration: float):
    """Record storage operation metrics"""
    STORAGE_OPERATIONS_LATENCY.labels(
        backend=backend,
        operation=operation,
        data_type=data_type
    ).observe(duration)


def update_database_connections(database_type: str, pool_name: str, count: int):
    """Update database connection count metrics"""
    DATABASE_CONNECTIONS.labels(
        database_type=database_type,
        pool_name=pool_name
    ).set(count)


def record_data_processing(operation: str, data_type: str, bytes_processed: int, processing_time: float):
    """Record data processing metrics"""
    # Record throughput
    DATA_THROUGHPUT.labels(
        operation=operation,
        data_type=data_type,
        direction='processed'
    ).inc(bytes_processed)
    
    # Record processing latency
    STORAGE_OPERATIONS_LATENCY.labels(
        backend='processing',
        operation=operation,
        data_type=data_type
    ).observe(processing_time)


class MetricsCollector:
    """Utility class for collecting custom application metrics"""
    
    @staticmethod
    def record_bulk_operation(operation: str, data_type: str, item_count: int, total_bytes: int, duration: float):
        """Record metrics for bulk operations"""
        # Record operation count
        REQUEST_COUNT.labels(
            method='BULK',
            endpoint=f'/{operation}',
            status_code='200',
            data_type=data_type
        ).inc(item_count)
        
        # Record data throughput
        DATA_THROUGHPUT.labels(
            operation=operation,
            data_type=data_type,
            direction='bulk_inbound'
        ).inc(total_bytes)
        
        # Record operation latency
        STORAGE_OPERATIONS_LATENCY.labels(
            backend='bulk_processing',
            operation=operation,
            data_type=data_type
        ).observe(duration)
    
    @staticmethod
    def record_compression_metrics(original_size: int, compressed_size: int, compression_time: float):
        """Record compression operation metrics"""
        compression_ratio = compressed_size / original_size if original_size > 0 else 1.0
        
        # Create compression-specific metrics
        COMPRESSION_RATIO = Histogram(
            'data_compression_ratio',
            'Data compression ratio (compressed/original)',
            buckets=(0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0)
        )
        
        COMPRESSION_TIME = Histogram(
            'data_compression_time_seconds',
            'Time taken for data compression',
            buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
        )
        
        COMPRESSION_RATIO.observe(compression_ratio)
        COMPRESSION_TIME.observe(compression_time)
        
        # Log significant compression results
        if compression_ratio < 0.5:  # > 50% compression
            logger.info("High compression achieved",
                       original_size=original_size,
                       compressed_size=compressed_size,
                       compression_ratio=compression_ratio,
                       time_seconds=compression_time)
    
    @staticmethod
    def record_query_performance(data_type: str, result_count: int, query_time: float, cache_hit: bool = False):
        """Record query performance metrics"""
        QUERY_PERFORMANCE = Histogram(
            'query_performance_seconds',
            'Query execution time',
            ['data_type', 'result_size_category', 'cache_hit'],
            buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0)
        )
        
        # Categorize result size
        if result_count == 0:
            size_category = 'empty'
        elif result_count <= 10:
            size_category = 'small'
        elif result_count <= 100:
            size_category = 'medium'
        elif result_count <= 1000:
            size_category = 'large'
        else:
            size_category = 'xlarge'
        
        QUERY_PERFORMANCE.labels(
            data_type=data_type,
            result_size_category=size_category,
            cache_hit=str(cache_hit)
        ).observe(query_time)


# Export metrics collectors for use in other modules
__all__ = [
    'PrometheusMiddleware',
    'record_storage_operation',
    'update_database_connections', 
    'record_data_processing',
    'MetricsCollector'
]