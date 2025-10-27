"""
Data Storage Service - Logging Configuration
Comprehensive logging, observability, and telemetry configuration
"""

import logging
import logging.config
import sys
import traceback
from datetime import datetime
from typing import Dict, Any, Optional, List
from contextvars import ContextVar
from pathlib import Path
import json

import structlog
from structlog.types import FilteringBoundLogger

# Context variables for distributed tracing
request_id_context: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
user_id_context: ContextVar[Optional[str]] = ContextVar('user_id', default=None)
operation_context: ContextVar[Optional[str]] = ContextVar('operation', default=None)

class CustomJSONRenderer:
    """Custom JSON renderer with additional formatting"""
    
    def __call__(self, logger: FilteringBoundLogger, method_name: str, event_dict: Dict[str, Any]) -> str:
        """Render log record as JSON"""
        # Add context variables
        if request_id_context.get():
            event_dict['request_id'] = request_id_context.get()
        if user_id_context.get():
            event_dict['user_id'] = user_id_context.get()
        if operation_context.get():
            event_dict['operation'] = operation_context.get()
        
        # Add service metadata
        event_dict.update({
            'service': 'data-storage-service',
            'version': '1.0.0',
            'environment': 'production',  # Would be set via config
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        })
        
        # Clean up None values and ensure JSON serialization
        cleaned_dict = {}
        for key, value in event_dict.items():
            if value is not None:
                try:
                    json.dumps(value)  # Test serialization
                    cleaned_dict[key] = value
                except (TypeError, ValueError):
                    cleaned_dict[key] = str(value)
        
        return json.dumps(cleaned_dict, separators=(',', ':'))

class MetricsProcessor:
    """Processor to collect metrics from log events"""
    
    def __init__(self):
        self.metrics_collector = None  # Would integrate with Prometheus
    
    def __call__(self, logger: FilteringBoundLogger, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Process log events for metrics collection"""
        
        # Collect performance metrics
        if 'duration_ms' in event_dict:
            # Record latency metrics
            operation = event_dict.get('operation', 'unknown')
            duration = event_dict['duration_ms']
            # Would send to Prometheus here
        
        # Collect error metrics
        if method_name in ['error', 'critical']:
            error_type = event_dict.get('error_type', 'unknown')
            # Would increment error counters here
        
        # Collect business metrics
        if 'data_type' in event_dict and 'size_bytes' in event_dict:
            # Record data volume metrics
            data_type = event_dict['data_type']
            size = event_dict['size_bytes']
            # Would send to Prometheus here
        
        return event_dict

class SecurityProcessor:
    """Processor to handle security-sensitive information"""
    
    SENSITIVE_FIELDS = {
        'password', 'token', 'api_key', 'secret', 'authorization',
        'credit_card', 'ssn', 'private_key', 'session_id'
    }
    
    def __call__(self, logger: FilteringBoundLogger, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize security-sensitive information from logs"""
        
        def sanitize_value(key: str, value: Any) -> Any:
            """Sanitize sensitive values"""
            if isinstance(key, str) and any(sensitive in key.lower() for sensitive in self.SENSITIVE_FIELDS):
                if isinstance(value, str) and len(value) > 4:
                    return f"{value[:4]}{'*' * (len(value) - 4)}"
                else:
                    return "[REDACTED]"
            return value
        
        def sanitize_dict(d: Dict[str, Any]) -> Dict[str, Any]:
            """Recursively sanitize dictionary"""
            sanitized = {}
            for k, v in d.items():
                if isinstance(v, dict):
                    sanitized[k] = sanitize_dict(v)
                elif isinstance(v, list):
                    sanitized[k] = [sanitize_dict(item) if isinstance(item, dict) else sanitize_value(k, item) for item in v]
                else:
                    sanitized[k] = sanitize_value(k, v)
            return sanitized
        
        return sanitize_dict(event_dict)

class PerformanceProcessor:
    """Processor to add performance context"""
    
    def __call__(self, logger: FilteringBoundLogger, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Add performance context to log events"""
        
        # Add memory usage if available
        try:
            import psutil
            process = psutil.Process()
            event_dict['memory_usage_mb'] = round(process.memory_info().rss / 1024 / 1024, 2)
            event_dict['cpu_percent'] = process.cpu_percent()
        except ImportError:
            pass
        
        # Add database connection stats if available
        # Would integrate with connection pool metrics
        
        return event_dict

def configure_logging(log_level: str = "INFO", log_file: Optional[str] = None,
                     enable_json: bool = True, enable_console: bool = True) -> None:
    """Configure structured logging with multiple outputs"""
    
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        SecurityProcessor(),  # Sanitize sensitive data
        MetricsProcessor(),   # Collect metrics
        PerformanceProcessor(),  # Add performance context
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]
    
    # Configure output processors
    if enable_json:
        processors.append(CustomJSONRenderer())
    else:
        processors.append(structlog.processors.JSONRenderer())
    
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Configure standard library logging
    handlers = []
    
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, log_level.upper()))
        if enable_json:
            console_handler.setFormatter(logging.Formatter('%(message)s'))
        else:
            console_handler.setFormatter(
                logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
            )
        handlers.append(console_handler)
    
    if log_file:
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=100*1024*1024, backupCount=5  # 100MB rotation
        )
        file_handler.setLevel(getattr(logging, log_level.upper()))
        file_handler.setFormatter(logging.Formatter('%(message)s'))
        handlers.append(file_handler)
    
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
        handlers=handlers
    )

class LoggingContext:
    """Context manager for adding context to logs"""
    
    def __init__(self, request_id: str = None, user_id: str = None, 
                 operation: str = None, **extra_context):
        self.request_id = request_id
        self.user_id = user_id
        self.operation = operation
        self.extra_context = extra_context
        self.tokens = {}
    
    def __enter__(self):
        if self.request_id:
            self.tokens['request_id'] = request_id_context.set(self.request_id)
        if self.user_id:
            self.tokens['user_id'] = user_id_context.set(self.user_id)
        if self.operation:
            self.tokens['operation'] = operation_context.set(self.operation)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        for token in self.tokens.values():
            token.reset()

class OperationLogger:
    """Utility for logging operations with timing and metrics"""
    
    def __init__(self, operation_name: str, logger: Optional[structlog.BoundLogger] = None):
        self.operation_name = operation_name
        self.logger = logger or structlog.get_logger()
        self.start_time = None
        self.context = {}
    
    def __enter__(self):
        self.start_time = datetime.utcnow()
        self.logger.info(
            "Operation started",
            operation=self.operation_name,
            start_time=self.start_time.isoformat()
        )
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        end_time = datetime.utcnow()
        duration_ms = (end_time - self.start_time).total_seconds() * 1000
        
        if exc_type:
            self.logger.error(
                "Operation failed",
                operation=self.operation_name,
                duration_ms=duration_ms,
                error_type=exc_type.__name__,
                error_message=str(exc_val),
                **self.context
            )
        else:
            self.logger.info(
                "Operation completed",
                operation=self.operation_name,
                duration_ms=duration_ms,
                **self.context
            )
    
    def add_context(self, **context):
        """Add context information to the operation log"""
        self.context.update(context)

class AuditLogger:
    """Specialized logger for audit events"""
    
    def __init__(self):
        self.logger = structlog.get_logger("audit")
    
    def log_data_access(self, user_id: str, data_type: str, operation: str,
                       resource_id: str = None, ip_address: str = None,
                       success: bool = True, **extra_context):
        """Log data access events"""
        self.logger.info(
            "Data access event",
            event_type="data_access",
            user_id=user_id,
            data_type=data_type,
            operation=operation,
            resource_id=resource_id,
            ip_address=ip_address,
            success=success,
            **extra_context
        )
    
    def log_security_event(self, event_type: str, severity: str = "medium",
                          ip_address: str = None, user_id: str = None,
                          description: str = None, **extra_context):
        """Log security-related events"""
        self.logger.warning(
            "Security event",
            event_type=event_type,
            security_event=True,
            severity=severity,
            ip_address=ip_address,
            user_id=user_id,
            description=description,
            **extra_context
        )
    
    def log_system_event(self, event_type: str, component: str,
                        status: str, **extra_context):
        """Log system events"""
        self.logger.info(
            "System event",
            event_type=event_type,
            component=component,
            status=status,
            system_event=True,
            **extra_context
        )

class AlertManager:
    """Manager for handling alerts based on log events"""
    
    def __init__(self):
        self.alert_rules = {
            'high_error_rate': {
                'condition': lambda events: len([e for e in events if e.get('level') == 'error']) > 10,
                'action': self._send_error_alert
            },
            'slow_operations': {
                'condition': lambda events: any(e.get('duration_ms', 0) > 30000 for e in events),
                'action': self._send_performance_alert
            },
            'security_events': {
                'condition': lambda events: any(e.get('security_event') for e in events),
                'action': self._send_security_alert
            }
        }
        self.recent_events = []
        self.max_events = 1000
    
    def process_event(self, event_dict: Dict[str, Any]):
        """Process log event for alerting"""
        self.recent_events.append(event_dict)
        if len(self.recent_events) > self.max_events:
            self.recent_events.pop(0)
        
        # Check alert conditions
        for rule_name, rule in self.alert_rules.items():
            if rule['condition'](self.recent_events):
                rule['action'](rule_name, event_dict)
    
    def _send_error_alert(self, rule_name: str, event: Dict[str, Any]):
        """Send error rate alert"""
        # Would integrate with alerting system (Slack, email, PagerDuty, etc.)
        pass
    
    def _send_performance_alert(self, rule_name: str, event: Dict[str, Any]):
        """Send performance alert"""
        # Would integrate with alerting system
        pass
    
    def _send_security_alert(self, rule_name: str, event: Dict[str, Any]):
        """Send security alert"""
        # Would integrate with alerting system
        pass

def setup_observability(service_name: str = "data-storage-service") -> Dict[str, Any]:
    """Setup comprehensive observability stack"""
    
    # Configure logging
    configure_logging(
        log_level="INFO",
        log_file=f"/var/log/{service_name}/app.log",
        enable_json=True,
        enable_console=True
    )
    
    # Initialize audit logger
    audit_logger = AuditLogger()
    
    # Initialize alert manager
    alert_manager = AlertManager()
    
    # Setup health monitoring
    health_logger = structlog.get_logger("health")
    
    # Setup performance monitoring
    performance_logger = structlog.get_logger("performance")
    
    return {
        'audit_logger': audit_logger,
        'alert_manager': alert_manager,
        'health_logger': health_logger,
        'performance_logger': performance_logger
    }

# Utility functions for common logging patterns
def log_request_start(logger: structlog.BoundLogger, method: str, path: str, 
                     client_ip: str = None, user_id: str = None):
    """Log request start"""
    logger.info(
        "HTTP request started",
        http_method=method,
        http_path=path,
        client_ip=client_ip,
        user_id=user_id,
        event_type="request_start"
    )

def log_request_end(logger: structlog.BoundLogger, method: str, path: str,
                   status_code: int, duration_ms: float,
                   response_size: int = None):
    """Log request completion"""
    logger.info(
        "HTTP request completed",
        http_method=method,
        http_path=path,
        http_status_code=status_code,
        duration_ms=duration_ms,
        response_size_bytes=response_size,
        event_type="request_end"
    )

def log_database_operation(logger: structlog.BoundLogger, operation: str,
                          table: str, duration_ms: float, rows_affected: int = None):
    """Log database operation"""
    logger.info(
        "Database operation",
        db_operation=operation,
        db_table=table,
        duration_ms=duration_ms,
        rows_affected=rows_affected,
        event_type="database_operation"
    )

def log_storage_operation(logger: structlog.BoundLogger, operation: str,
                         backend: str, data_type: str, size_bytes: int = None):
    """Log storage operation"""
    logger.info(
        "Storage operation",
        storage_operation=operation,
        storage_backend=backend,
        data_type=data_type,
        size_bytes=size_bytes,
        event_type="storage_operation"
    )

# Export main components
__all__ = [
    'configure_logging', 'LoggingContext', 'OperationLogger', 'AuditLogger',
    'AlertManager', 'setup_observability', 'request_id_context',
    'log_request_start', 'log_request_end', 'log_database_operation',
    'log_storage_operation'
]