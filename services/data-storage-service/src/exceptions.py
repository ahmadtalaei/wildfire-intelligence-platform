"""
Data Storage Service - Custom Exceptions
Comprehensive error handling and validation exceptions
"""

from typing import Any, Dict, Optional, List
from fastapi import HTTPException, status
import structlog

logger = structlog.get_logger()

class DataStorageException(Exception):
    """Base exception for data storage service"""
    
    def __init__(self, message: str, details: Dict[str, Any] = None, 
                 error_code: str = None, status_code: int = 500):
        self.message = message
        self.details = details or {}
        self.error_code = error_code
        self.status_code = status_code
        super().__init__(self.message)

class ValidationError(DataStorageException):
    """Raised when data validation fails"""
    
    def __init__(self, message: str, field: str = None, value: Any = None, 
                 validation_errors: List[Dict] = None):
        details = {
            "field": field,
            "value": str(value) if value is not None else None,
            "validation_errors": validation_errors or []
        }
        super().__init__(
            message=message,
            details=details,
            error_code="VALIDATION_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
        )

class DatabaseError(DataStorageException):
    """Raised when database operations fail"""
    
    def __init__(self, message: str, operation: str = None, table: str = None,
                 original_error: Exception = None):
        details = {
            "operation": operation,
            "table": table,
            "original_error": str(original_error) if original_error else None
        }
        super().__init__(
            message=message,
            details=details,
            error_code="DATABASE_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

class StorageError(DataStorageException):
    """Raised when storage operations fail"""
    
    def __init__(self, message: str, storage_backend: str = None, 
                 operation: str = None, storage_id: str = None):
        details = {
            "storage_backend": storage_backend,
            "operation": operation,
            "storage_id": storage_id
        }
        super().__init__(
            message=message,
            details=details,
            error_code="STORAGE_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

class BlobStorageError(StorageError):
    """Raised when blob storage operations fail"""
    
    def __init__(self, message: str, bucket: str = None, key: str = None,
                 operation: str = None):
        details = {
            "storage_backend": "blob_storage",
            "bucket": bucket,
            "key": key,
            "operation": operation
        }
        super().__init__(
            message=message,
            storage_backend="blob_storage",
            operation=operation
        )
        self.details.update(details)

class TimescaleDBError(DatabaseError):
    """Raised when TimescaleDB operations fail"""
    
    def __init__(self, message: str, hypertable: str = None, chunk: str = None,
                 operation: str = None):
        details = {
            "database_type": "timescaledb",
            "hypertable": hypertable,
            "chunk": chunk,
            "operation": operation
        }
        super().__init__(
            message=message,
            operation=operation,
            table=hypertable
        )
        self.details.update(details)

class ConnectionError(DataStorageException):
    """Raised when connection to external services fails"""
    
    def __init__(self, message: str, service: str = None, host: str = None,
                 port: int = None, timeout: float = None):
        details = {
            "service": service,
            "host": host,
            "port": port,
            "timeout": timeout
        }
        super().__init__(
            message=message,
            details=details,
            error_code="CONNECTION_ERROR",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )

class AuthenticationError(DataStorageException):
    """Raised when authentication fails"""
    
    def __init__(self, message: str = "Authentication failed", 
                 auth_method: str = None):
        details = {
            "auth_method": auth_method
        }
        super().__init__(
            message=message,
            details=details,
            error_code="AUTHENTICATION_ERROR",
            status_code=status.HTTP_401_UNAUTHORIZED
        )

class AuthorizationError(DataStorageException):
    """Raised when authorization fails"""
    
    def __init__(self, message: str = "Access denied", 
                 required_permission: str = None, resource: str = None):
        details = {
            "required_permission": required_permission,
            "resource": resource
        }
        super().__init__(
            message=message,
            details=details,
            error_code="AUTHORIZATION_ERROR",
            status_code=status.HTTP_403_FORBIDDEN
        )

class RateLimitError(DataStorageException):
    """Raised when rate limit is exceeded"""
    
    def __init__(self, message: str = "Rate limit exceeded", 
                 limit: int = None, window_seconds: int = None,
                 client_id: str = None):
        details = {
            "limit": limit,
            "window_seconds": window_seconds,
            "client_id": client_id
        }
        super().__init__(
            message=message,
            details=details,
            error_code="RATE_LIMIT_ERROR",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS
        )

class DataNotFoundError(DataStorageException):
    """Raised when requested data is not found"""
    
    def __init__(self, message: str = "Data not found", 
                 resource_type: str = None, resource_id: str = None):
        details = {
            "resource_type": resource_type,
            "resource_id": resource_id
        }
        super().__init__(
            message=message,
            details=details,
            error_code="DATA_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND
        )

class ConfigurationError(DataStorageException):
    """Raised when configuration is invalid"""
    
    def __init__(self, message: str, config_key: str = None, 
                 config_value: str = None):
        details = {
            "config_key": config_key,
            "config_value": config_value
        }
        super().__init__(
            message=message,
            details=details,
            error_code="CONFIGURATION_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

class DataIntegrityError(DataStorageException):
    """Raised when data integrity constraints are violated"""
    
    def __init__(self, message: str, constraint: str = None, 
                 table: str = None, data: Dict = None):
        details = {
            "constraint": constraint,
            "table": table,
            "data": data
        }
        super().__init__(
            message=message,
            details=details,
            error_code="DATA_INTEGRITY_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
        )

class ArchivalError(DataStorageException):
    """Raised when data archival operations fail"""
    
    def __init__(self, message: str, archive_id: str = None,
                 data_type: str = None, operation: str = None):
        details = {
            "archive_id": archive_id,
            "data_type": data_type,
            "operation": operation
        }
        super().__init__(
            message=message,
            details=details,
            error_code="ARCHIVAL_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

class OptimizationError(DataStorageException):
    """Raised when optimization operations fail"""
    
    def __init__(self, message: str, optimization_type: str = None,
                 component: str = None):
        details = {
            "optimization_type": optimization_type,
            "component": component
        }
        super().__init__(
            message=message,
            details=details,
            error_code="OPTIMIZATION_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

class HealthCheckError(DataStorageException):
    """Raised when health check operations fail"""
    
    def __init__(self, message: str, component: str = None,
                 check_type: str = None):
        details = {
            "component": component,
            "check_type": check_type
        }
        super().__init__(
            message=message,
            details=details,
            error_code="HEALTH_CHECK_ERROR",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )

class CompressionError(DataStorageException):
    """Raised when compression/decompression operations fail"""
    
    def __init__(self, message: str, algorithm: str = None,
                 operation: str = None, size: int = None):
        details = {
            "algorithm": algorithm,
            "operation": operation,
            "size": size
        }
        super().__init__(
            message=message,
            details=details,
            error_code="COMPRESSION_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

# Error handling utilities
class ErrorHandler:
    """Centralized error handling utilities"""
    
    @staticmethod
    def to_http_exception(error: DataStorageException) -> HTTPException:
        """Convert custom exception to FastAPI HTTPException"""
        return HTTPException(
            status_code=error.status_code,
            detail={
                "message": error.message,
                "error_code": error.error_code,
                "details": error.details,
                "type": error.__class__.__name__
            }
        )
    
    @staticmethod
    def log_error(error: Exception, context: Dict[str, Any] = None):
        """Log error with structured context"""
        context = context or {}
        
        if isinstance(error, DataStorageException):
            logger.error(
                "Data storage error occurred",
                error_type=error.__class__.__name__,
                error_code=error.error_code,
                message=error.message,
                details=error.details,
                **context
            )
        else:
            logger.error(
                "Unexpected error occurred",
                error_type=error.__class__.__name__,
                message=str(error),
                **context,
                exc_info=True
            )
    
    @staticmethod
    def handle_database_error(error: Exception, operation: str = None, 
                            table: str = None) -> DataStorageException:
        """Handle and classify database errors"""
        error_msg = str(error).lower()
        
        # Connection errors
        if any(keyword in error_msg for keyword in ['connection', 'timeout', 'network']):
            return ConnectionError(
                message=f"Database connection failed: {str(error)}",
                service="postgresql"
            )
        
        # Constraint violations
        if any(keyword in error_msg for keyword in ['constraint', 'unique', 'foreign key']):
            return DataIntegrityError(
                message=f"Data integrity constraint violated: {str(error)}",
                table=table
            )
        
        # Permission errors
        if any(keyword in error_msg for keyword in ['permission', 'access denied']):
            return AuthorizationError(
                message=f"Database access denied: {str(error)}"
            )
        
        # Generic database error
        return DatabaseError(
            message=f"Database operation failed: {str(error)}",
            operation=operation,
            table=table,
            original_error=error
        )
    
    @staticmethod
    def handle_storage_error(error: Exception, backend: str = None,
                           operation: str = None, storage_id: str = None) -> DataStorageException:
        """Handle and classify storage errors"""
        error_msg = str(error).lower()
        
        # S3/Blob storage specific errors
        if backend == "blob_storage" or any(keyword in error_msg for keyword in ['s3', 'bucket', 'minio']):
            if 'not found' in error_msg or '404' in error_msg:
                return DataNotFoundError(
                    message=f"Blob object not found: {storage_id}",
                    resource_type="blob_object",
                    resource_id=storage_id
                )
            elif 'access denied' in error_msg or '403' in error_msg:
                return AuthorizationError(
                    message=f"Blob storage access denied: {str(error)}"
                )
            else:
                return BlobStorageError(
                    message=f"Blob storage operation failed: {str(error)}",
                    operation=operation
                )
        
        # Generic storage error
        return StorageError(
            message=f"Storage operation failed: {str(error)}",
            storage_backend=backend,
            operation=operation,
            storage_id=storage_id
        )

# Validation utilities
class DataValidator:
    """Data validation utilities"""
    
    @staticmethod
    def validate_data_type(data_type: str) -> bool:
        """Validate data type string"""
        from .models.data_models import DataType
        try:
            DataType(data_type)
            return True
        except ValueError:
            return False
    
    @staticmethod
    def validate_storage_request(request_data: Dict[str, Any]) -> List[str]:
        """Validate storage request data and return list of errors"""
        errors = []
        
        # Required fields
        required_fields = ['data_type', 'data']
        for field in required_fields:
            if field not in request_data:
                errors.append(f"Missing required field: {field}")
        
        # Data type validation
        if 'data_type' in request_data:
            if not DataValidator.validate_data_type(request_data['data_type']):
                errors.append(f"Invalid data_type: {request_data['data_type']}")
        
        # Data validation
        if 'data' in request_data:
            data = request_data['data']
            if data is None:
                errors.append("Data cannot be null")
            elif isinstance(data, str) and len(data) == 0:
                errors.append("Data cannot be empty string")
            elif isinstance(data, (list, dict)) and len(data) == 0:
                errors.append("Data cannot be empty")
        
        # Size validation
        if 'data' in request_data:
            import json
            try:
                data_size = len(json.dumps(request_data['data']).encode('utf-8'))
                if data_size > 100 * 1024 * 1024:  # 100MB limit
                    errors.append("Data size exceeds maximum limit (100MB)")
            except (TypeError, ValueError):
                pass  # Skip size check for non-serializable data
        
        return errors
    
    @staticmethod
    def validate_query_request(request_data: Dict[str, Any]) -> List[str]:
        """Validate query request data and return list of errors"""
        errors = []
        
        # Required fields
        if 'data_type' not in request_data:
            errors.append("Missing required field: data_type")
        
        # Data type validation
        if 'data_type' in request_data:
            if not DataValidator.validate_data_type(request_data['data_type']):
                errors.append(f"Invalid data_type: {request_data['data_type']}")
        
        # Time range validation
        if 'start_time' in request_data and 'end_time' in request_data:
            try:
                from datetime import datetime
                start_time = datetime.fromisoformat(request_data['start_time'].replace('Z', '+00:00'))
                end_time = datetime.fromisoformat(request_data['end_time'].replace('Z', '+00:00'))
                if start_time >= end_time:
                    errors.append("start_time must be before end_time")
            except (ValueError, AttributeError):
                errors.append("Invalid datetime format for start_time or end_time")
        
        # Limit validation
        if 'limit' in request_data:
            limit = request_data['limit']
            if not isinstance(limit, int) or limit < 1 or limit > 10000:
                errors.append("Limit must be an integer between 1 and 10000")
        
        # Offset validation
        if 'offset' in request_data:
            offset = request_data['offset']
            if not isinstance(offset, int) or offset < 0:
                errors.append("Offset must be a non-negative integer")
        
        return errors

# Context manager for error handling
class ErrorContext:
    """Context manager for handling errors in operations"""
    
    def __init__(self, operation: str, component: str = None, **context):
        self.operation = operation
        self.component = component
        self.context = context
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        if exc_value:
            # Log the error with context
            ErrorHandler.log_error(
                exc_value, 
                {
                    "operation": self.operation,
                    "component": self.component,
                    **self.context
                }
            )
            
            # Convert to appropriate custom exception if needed
            if not isinstance(exc_value, DataStorageException):
                if "database" in self.operation.lower():
                    raise ErrorHandler.handle_database_error(
                        exc_value, 
                        operation=self.operation,
                        table=self.context.get("table")
                    )
                elif "storage" in self.operation.lower():
                    raise ErrorHandler.handle_storage_error(
                        exc_value,
                        backend=self.context.get("backend"),
                        operation=self.operation,
                        storage_id=self.context.get("storage_id")
                    )
        
        return False  # Don't suppress exceptions

# Export all exceptions and utilities
__all__ = [
    # Base exceptions
    'DataStorageException', 'ValidationError', 'DatabaseError', 'StorageError',
    
    # Specific exceptions
    'BlobStorageError', 'TimescaleDBError', 'ConnectionError', 
    'AuthenticationError', 'AuthorizationError', 'RateLimitError',
    'DataNotFoundError', 'ConfigurationError', 'DataIntegrityError',
    'ArchivalError', 'OptimizationError', 'HealthCheckError', 'CompressionError',
    
    # Utilities
    'ErrorHandler', 'DataValidator', 'ErrorContext'
]