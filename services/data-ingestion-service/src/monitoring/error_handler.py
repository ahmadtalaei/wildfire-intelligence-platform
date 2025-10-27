"""Comprehensive error handling and monitoring for wildfire intelligence platform"""

import asyncio
import logging
import traceback
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import json
import uuid
import threading
from collections import defaultdict, deque
from pathlib import Path

try:
    import psutil
except ImportError:
    psutil = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ErrorSeverity(Enum):
    """Error severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

class ErrorCategory(Enum):
    """Error categories for classification"""
    DATA_INGESTION = "data_ingestion"
    VALIDATION = "validation"
    PROCESSING = "processing"
    STORAGE = "storage"
    STREAMING = "streaming"
    NETWORK = "network"
    AUTHENTICATION = "authentication"
    CONFIGURATION = "configuration"
    SYSTEM_RESOURCE = "system_resource"
    UNKNOWN = "unknown"

@dataclass
class ErrorRecord:
    """Structured error record"""
    error_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
    category: ErrorCategory = ErrorCategory.UNKNOWN
    component: str = "unknown"
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    exception_type: str = ""
    exception_traceback: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    resolved: bool = False
    resolution_notes: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'error_id': self.error_id,
            'timestamp': self.timestamp.isoformat(),
            'severity': self.severity.value,
            'category': self.category.value,
            'component': self.component,
            'message': self.message,
            'details': self.details,
            'exception_type': self.exception_type,
            'exception_traceback': self.exception_traceback,
            'context': self.context,
            'resolved': self.resolved,
            'resolution_notes': self.resolution_notes
        }

@dataclass
class PerformanceMetric:
    """Performance monitoring metric"""
    metric_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    component: str = "unknown"
    operation: str = ""
    duration_ms: float = 0.0
    memory_used_mb: float = 0.0
    cpu_percent: float = 0.0
    success: bool = True
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'metric_id': self.metric_id,
            'timestamp': self.timestamp.isoformat(),
            'component': self.component,
            'operation': self.operation,
            'duration_ms': self.duration_ms,
            'memory_used_mb': self.memory_used_mb,
            'cpu_percent': self.cpu_percent,
            'success': self.success,
            'details': self.details
        }

class ErrorHandler:
    """Comprehensive error handling system"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.error_storage = deque(maxlen=self.config.get('max_errors', 10000))
        self.error_counts = defaultdict(int)
        self.alert_callbacks: List[Callable] = []
        self.error_log_file = self.config.get('error_log_file', 'errors.log')
        self.alert_thresholds = self.config.get('alert_thresholds', {
            ErrorSeverity.CRITICAL: 1,
            ErrorSeverity.HIGH: 5,
            ErrorSeverity.MEDIUM: 20,
            ErrorSeverity.LOW: 50
        })
        
        # Setup file logging if specified
        if self.error_log_file:
            file_handler = logging.FileHandler(self.error_log_file)
            file_handler.setLevel(logging.ERROR)
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
    
    async def handle_error(self, 
                          error: Exception,
                          component: str,
                          severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                          category: ErrorCategory = ErrorCategory.UNKNOWN,
                          context: Dict[str, Any] = None) -> ErrorRecord:
        """Handle and log an error"""
        try:
            error_record = ErrorRecord(
                severity=severity,
                category=category,
                component=component,
                message=str(error),
                exception_type=type(error).__name__,
                exception_traceback=traceback.format_exc(),
                context=context or {}
            )
            
            # Store error
            self.error_storage.append(error_record)
            self.error_counts[f"{severity.value}_{category.value}"] += 1
            
            # Log error based on severity
            if severity in [ErrorSeverity.CRITICAL, ErrorSeverity.HIGH]:
                logger.error(f"[{severity.value.upper()}] {component}: {error_record.message}")
            elif severity == ErrorSeverity.MEDIUM:
                logger.warning(f"[{severity.value.upper()}] {component}: {error_record.message}")
            else:
                logger.info(f"[{severity.value.upper()}] {component}: {error_record.message}")
            
            # Check for alert conditions
            await self._check_alert_conditions(error_record)
            
            return error_record
            
        except Exception as handler_error:
            logger.critical(f"Error handler failed: {handler_error}")
            # Create basic error record even if handler fails
            return ErrorRecord(
                component=component,
                message=f"Handler error: {handler_error}",
                severity=ErrorSeverity.CRITICAL,
                category=ErrorCategory.SYSTEM_RESOURCE
            )
    
    async def handle_validation_error(self, validation_result, component: str, context: Dict[str, Any] = None) -> List[ErrorRecord]:
        """Handle validation errors from ValidationResult"""
        error_records = []
        
        try:
            # Handle validation errors
            for error in validation_result.errors:
                error_record = ErrorRecord(
                    severity=ErrorSeverity.HIGH,
                    category=ErrorCategory.VALIDATION,
                    component=component,
                    message=f"Validation error in {error.field}: {error.message}",
                    details={
                        'field': error.field,
                        'value': error.value,
                        'validation_timestamp': error.timestamp.isoformat()
                    },
                    context=context or {}
                )
                self.error_storage.append(error_record)
                error_records.append(error_record)
            
            # Handle validation warnings as low severity errors
            for warning in validation_result.warnings:
                warning_record = ErrorRecord(
                    severity=ErrorSeverity.LOW,
                    category=ErrorCategory.VALIDATION,
                    component=component,
                    message=f"Validation warning in {warning.field}: {warning.message}",
                    details={
                        'field': warning.field,
                        'value': warning.value,
                        'validation_timestamp': warning.timestamp.isoformat()
                    },
                    context=context or {}
                )
                self.error_storage.append(warning_record)
                error_records.append(warning_record)
            
            if error_records:
                logger.warning(f"Handled {len(error_records)} validation issues in {component}")
            
        except Exception as e:
            logger.error(f"Failed to handle validation errors: {e}")
        
        return error_records
    
    async def _check_alert_conditions(self, error_record: ErrorRecord):
        """Check if error conditions warrant alerts"""
        try:
            # Count recent errors of this severity
            cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=5)
            recent_errors = [
                err for err in self.error_storage
                if err.severity == error_record.severity and err.timestamp > cutoff_time
            ]
            
            threshold = self.alert_thresholds.get(error_record.severity, 999)
            if len(recent_errors) >= threshold:
                await self._send_alert(error_record, len(recent_errors))
                
        except Exception as e:
            logger.error(f"Alert condition check failed: {e}")
    
    async def _send_alert(self, error_record: ErrorRecord, count: int):
        """Send alert to registered callbacks"""
        alert_data = {
            'alert_type': 'error_threshold',
            'severity': error_record.severity.value,
            'category': error_record.category.value,
            'component': error_record.component,
            'count': count,
            'recent_error': error_record.to_dict(),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        for callback in self.alert_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(alert_data)
                else:
                    callback(alert_data)
            except Exception as e:
                logger.error(f"Alert callback failed: {e}")
    
    def register_alert_callback(self, callback: Callable):
        """Register callback for alerts"""
        self.alert_callbacks.append(callback)
        logger.info(f"Registered alert callback: {callback.__name__}")
    
    def get_error_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get error summary for specified time period"""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            recent_errors = [err for err in self.error_storage if err.timestamp > cutoff_time]
            
            summary = {
                'time_period_hours': hours,
                'total_errors': len(recent_errors),
                'by_severity': defaultdict(int),
                'by_category': defaultdict(int),
                'by_component': defaultdict(int),
                'unresolved_count': 0,
                'most_common_errors': []
            }
            
            error_messages = defaultdict(int)
            
            for error in recent_errors:
                summary['by_severity'][error.severity.value] += 1
                summary['by_category'][error.category.value] += 1
                summary['by_component'][error.component] += 1
                
                if not error.resolved:
                    summary['unresolved_count'] += 1
                
                error_messages[error.message] += 1
            
            # Most common error messages
            summary['most_common_errors'] = sorted(
                error_messages.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to generate error summary: {e}")
            return {'error': str(e)}
    
    def get_recent_errors(self, limit: int = 100, severity: ErrorSeverity = None) -> List[Dict[str, Any]]:
        """Get recent errors with optional severity filter"""
        try:
            errors = list(self.error_storage)
            
            if severity:
                errors = [err for err in errors if err.severity == severity]
            
            # Sort by timestamp (most recent first)
            errors.sort(key=lambda x: x.timestamp, reverse=True)
            
            return [err.to_dict() for err in errors[:limit]]
            
        except Exception as e:
            logger.error(f"Failed to retrieve recent errors: {e}")
            return []
    
    async def resolve_error(self, error_id: str, resolution_notes: str = "") -> bool:
        """Mark an error as resolved"""
        try:
            for error in self.error_storage:
                if error.error_id == error_id:
                    error.resolved = True
                    error.resolution_notes = resolution_notes
                    logger.info(f"Resolved error {error_id}: {resolution_notes}")
                    return True
            
            logger.warning(f"Error {error_id} not found for resolution")
            return False
            
        except Exception as e:
            logger.error(f"Failed to resolve error {error_id}: {e}")
            return False

class PerformanceMonitor:
    """Performance monitoring system"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.metrics_storage = deque(maxlen=self.config.get('max_metrics', 50000))
        self.performance_thresholds = self.config.get('performance_thresholds', {
            'duration_ms': 10000,  # 10 seconds
            'memory_mb': 1000,  # 1GB
            'cpu_percent': 80  # 80%
        })
        self.alert_callbacks: List[Callable] = []
        
    class PerformanceContext:
        """Context manager for performance monitoring"""
        
        def __init__(self, monitor: 'PerformanceMonitor', component: str, operation: str, details: Dict[str, Any] = None):
            self.monitor = monitor
            self.component = component
            self.operation = operation
            self.details = details or {}
            self.start_time = None
            self.start_memory = None
            self.start_cpu = None
            
        async def __aenter__(self):
            self.start_time = time.time()
            if psutil:
                process = psutil.Process()
                self.start_memory = process.memory_info().rss / 1024 / 1024  # MB
                self.start_cpu = process.cpu_percent()
            return self
            
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            end_time = time.time()
            duration_ms = (end_time - self.start_time) * 1000
            
            memory_used = 0
            cpu_percent = 0
            
            if psutil:
                process = psutil.Process()
                end_memory = process.memory_info().rss / 1024 / 1024  # MB
                memory_used = end_memory - (self.start_memory or 0)
                cpu_percent = process.cpu_percent()
            
            metric = PerformanceMetric(
                component=self.component,
                operation=self.operation,
                duration_ms=duration_ms,
                memory_used_mb=memory_used,
                cpu_percent=cpu_percent,
                success=exc_type is None,
                details=self.details
            )
            
            await self.monitor._record_metric(metric)
    
    def monitor_performance(self, component: str, operation: str, details: Dict[str, Any] = None) -> PerformanceContext:
        """Create performance monitoring context"""
        return self.PerformanceContext(self, component, operation, details)
    
    async def _record_metric(self, metric: PerformanceMetric):
        """Record performance metric"""
        try:
            self.metrics_storage.append(metric)
            
            # Check for performance alerts
            await self._check_performance_alerts(metric)
            
            # Log if performance is poor
            if (metric.duration_ms > self.performance_thresholds.get('duration_ms', 10000) or
                metric.memory_used_mb > self.performance_thresholds.get('memory_mb', 1000) or
                metric.cpu_percent > self.performance_thresholds.get('cpu_percent', 80)):
                
                logger.warning(
                    f"Performance issue in {metric.component}.{metric.operation}: "
                    f"duration={metric.duration_ms:.1f}ms, "
                    f"memory={metric.memory_used_mb:.1f}MB, "
                    f"cpu={metric.cpu_percent:.1f}%"
                )
                
        except Exception as e:
            logger.error(f"Failed to record performance metric: {e}")
    
    async def _check_performance_alerts(self, metric: PerformanceMetric):
        """Check if performance metric warrants alert"""
        try:
            alert_conditions = []
            
            if metric.duration_ms > self.performance_thresholds.get('duration_ms', 10000):
                alert_conditions.append(f"slow_operation_{metric.duration_ms:.0f}ms")
                
            if metric.memory_used_mb > self.performance_thresholds.get('memory_mb', 1000):
                alert_conditions.append(f"high_memory_{metric.memory_used_mb:.0f}MB")
                
            if metric.cpu_percent > self.performance_thresholds.get('cpu_percent', 80):
                alert_conditions.append(f"high_cpu_{metric.cpu_percent:.0f}%")
            
            if alert_conditions:
                alert_data = {
                    'alert_type': 'performance_degradation',
                    'component': metric.component,
                    'operation': metric.operation,
                    'conditions': alert_conditions,
                    'metric': metric.to_dict(),
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
                
                for callback in self.alert_callbacks:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(alert_data)
                        else:
                            callback(alert_data)
                    except Exception as e:
                        logger.error(f"Performance alert callback failed: {e}")
                        
        except Exception as e:
            logger.error(f"Performance alert check failed: {e}")
    
    def register_alert_callback(self, callback: Callable):
        """Register callback for performance alerts"""
        self.alert_callbacks.append(callback)
        logger.info(f"Registered performance alert callback: {callback.__name__}")
    
    def get_performance_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get performance summary for specified time period"""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            recent_metrics = [metric for metric in self.metrics_storage if metric.timestamp > cutoff_time]
            
            if not recent_metrics:
                return {'message': 'No metrics available for specified time period'}
            
            # Calculate statistics
            durations = [m.duration_ms for m in recent_metrics]
            memory_usage = [m.memory_used_mb for m in recent_metrics if m.memory_used_mb > 0]
            cpu_usage = [m.cpu_percent for m in recent_metrics if m.cpu_percent > 0]
            
            summary = {
                'time_period_hours': hours,
                'total_operations': len(recent_metrics),
                'successful_operations': len([m for m in recent_metrics if m.success]),
                'failed_operations': len([m for m in recent_metrics if not m.success]),
                'average_duration_ms': sum(durations) / len(durations) if durations else 0,
                'max_duration_ms': max(durations) if durations else 0,
                'min_duration_ms': min(durations) if durations else 0,
                'average_memory_mb': sum(memory_usage) / len(memory_usage) if memory_usage else 0,
                'max_memory_mb': max(memory_usage) if memory_usage else 0,
                'average_cpu_percent': sum(cpu_usage) / len(cpu_usage) if cpu_usage else 0,
                'max_cpu_percent': max(cpu_usage) if cpu_usage else 0,
                'by_component': defaultdict(int),
                'by_operation': defaultdict(int),
                'slow_operations': []
            }
            
            # Component and operation breakdowns
            for metric in recent_metrics:
                summary['by_component'][metric.component] += 1
                summary['by_operation'][metric.operation] += 1
            
            # Slow operations (top 10)
            slow_ops = sorted(
                recent_metrics,
                key=lambda x: x.duration_ms,
                reverse=True
            )[:10]
            
            summary['slow_operations'] = [
                {
                    'component': op.component,
                    'operation': op.operation,
                    'duration_ms': op.duration_ms,
                    'timestamp': op.timestamp.isoformat()
                }
                for op in slow_ops
            ]
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to generate performance summary: {e}")
            return {'error': str(e)}

class SystemMonitor:
    """System-wide monitoring and health checks"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.health_checks: Dict[str, Callable] = {}
        self.system_metrics = deque(maxlen=1000)
        self.alert_callbacks: List[Callable] = []
        
    def register_health_check(self, name: str, check_func: Callable):
        """Register a health check function"""
        self.health_checks[name] = check_func
        logger.info(f"Registered health check: {name}")
    
    async def run_health_checks(self) -> Dict[str, Any]:
        """Run all registered health checks"""
        results = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'overall_status': 'healthy',
            'checks': {}
        }
        
        failed_checks = 0
        
        for name, check_func in self.health_checks.items():
            try:
                if asyncio.iscoroutinefunction(check_func):
                    result = await check_func()
                else:
                    result = check_func()
                
                results['checks'][name] = {
                    'status': 'healthy' if result else 'unhealthy',
                    'result': result,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
                
                if not result:
                    failed_checks += 1
                    
            except Exception as e:
                results['checks'][name] = {
                    'status': 'error',
                    'error': str(e),
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
                failed_checks += 1
        
        # Determine overall status
        total_checks = len(self.health_checks)
        if failed_checks == 0:
            results['overall_status'] = 'healthy'
        elif failed_checks < total_checks / 2:
            results['overall_status'] = 'degraded'
        else:
            results['overall_status'] = 'unhealthy'
        
        results['failed_checks'] = failed_checks
        results['total_checks'] = total_checks
        
        return results
    
    async def get_system_metrics(self) -> Dict[str, Any]:
        """Get current system metrics"""
        metrics = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'system': {}
        }
        
        if psutil:
            try:
                # CPU metrics
                metrics['system']['cpu_percent'] = psutil.cpu_percent(interval=1)
                metrics['system']['cpu_count'] = psutil.cpu_count()
                
                # Memory metrics
                memory = psutil.virtual_memory()
                metrics['system']['memory_total_gb'] = memory.total / 1024 / 1024 / 1024
                metrics['system']['memory_used_gb'] = memory.used / 1024 / 1024 / 1024
                metrics['system']['memory_percent'] = memory.percent
                
                # Disk metrics
                disk = psutil.disk_usage('/')
                metrics['system']['disk_total_gb'] = disk.total / 1024 / 1024 / 1024
                metrics['system']['disk_used_gb'] = disk.used / 1024 / 1024 / 1024
                metrics['system']['disk_percent'] = (disk.used / disk.total) * 100
                
                # Network metrics (if available)
                network = psutil.net_io_counters()
                metrics['system']['network_bytes_sent'] = network.bytes_sent
                metrics['system']['network_bytes_recv'] = network.bytes_recv
                
            except Exception as e:
                metrics['system']['error'] = f"Failed to get system metrics: {e}"
        else:
            metrics['system']['error'] = "psutil not available - install with: pip install psutil"
        
        # Store metrics for trending
        self.system_metrics.append(metrics)
        
        return metrics
    
    def register_alert_callback(self, callback: Callable):
        """Register callback for system alerts"""
        self.alert_callbacks.append(callback)
        logger.info(f"Registered system alert callback: {callback.__name__}")

class MonitoringManager:
    """Central monitoring manager that coordinates all monitoring systems"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.error_handler = ErrorHandler(config.get('error_handling', {}))
        self.performance_monitor = PerformanceMonitor(config.get('performance', {}))
        self.system_monitor = SystemMonitor(config.get('system', {}))
        
        # Setup common alert callbacks
        self._setup_common_alerts()
        
    def _setup_common_alerts(self):
        """Setup common alert handling"""
        async def log_alert(alert_data):
            alert_type = alert_data.get('alert_type', 'unknown')
            logger.warning(f"ALERT [{alert_type}]: {json.dumps(alert_data, default=str)}")
        
        self.error_handler.register_alert_callback(log_alert)
        self.performance_monitor.register_alert_callback(log_alert)
        self.system_monitor.register_alert_callback(log_alert)
    
    async def handle_error(self, error: Exception, component: str, severity: ErrorSeverity = ErrorSeverity.MEDIUM, 
                          category: ErrorCategory = ErrorCategory.UNKNOWN, context: Dict[str, Any] = None) -> ErrorRecord:
        """Handle error through error handler"""
        return await self.error_handler.handle_error(error, component, severity, category, context)
    
    def monitor_performance(self, component: str, operation: str, details: Dict[str, Any] = None):
        """Create performance monitoring context"""
        return self.performance_monitor.monitor_performance(component, operation, details)
    
    async def get_comprehensive_status(self) -> Dict[str, Any]:
        """Get comprehensive monitoring status"""
        try:
            return {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'error_summary': self.error_handler.get_error_summary(),
                'performance_summary': self.performance_monitor.get_performance_summary(),
                'health_checks': await self.system_monitor.run_health_checks(),
                'system_metrics': await self.system_monitor.get_system_metrics()
            }
        except Exception as e:
            logger.error(f"Failed to get comprehensive status: {e}")
            return {'error': str(e), 'timestamp': datetime.now(timezone.utc).isoformat()}
    
    def register_health_check(self, name: str, check_func: Callable):
        """Register health check with system monitor"""
        self.system_monitor.register_health_check(name, check_func)
    
    def register_alert_callback(self, callback: Callable):
        """Register alert callback with all monitoring systems"""
        self.error_handler.register_alert_callback(callback)
        self.performance_monitor.register_alert_callback(callback)
        self.system_monitor.register_alert_callback(callback)