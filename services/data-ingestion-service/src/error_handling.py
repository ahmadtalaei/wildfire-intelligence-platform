"""
Enhanced Error Handling Framework for Challenge 1
Comprehensive error handling, validation, and resilience mechanisms
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import structlog
import json
from collections import defaultdict, deque
import statistics

logger = structlog.get_logger()

class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ErrorCategory(Enum):
    """Error categories for classification"""
    NETWORK = "network"
    DATA_QUALITY = "data_quality"
    AUTHENTICATION = "authentication"
    RATE_LIMIT = "rate_limit"
    PARSING = "parsing"
    VALIDATION = "validation"
    TIMEOUT = "timeout"
    RESOURCE = "resource"

@dataclass
class ErrorEvent:
    """Error event tracking"""
    timestamp: datetime
    source: str
    category: ErrorCategory
    severity: ErrorSeverity
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    resolved: bool = False

@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration"""
    failure_threshold: int = 5
    recovery_timeout: int = 60  # seconds
    half_open_max_calls: int = 3

class CircuitBreakerState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreaker:
    """Circuit breaker pattern implementation"""

    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.half_open_calls = 0

    async def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection"""

        if self.state == CircuitBreakerState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitBreakerState.HALF_OPEN
                self.half_open_calls = 0
            else:
                raise Exception("Circuit breaker is OPEN")

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e

    def _should_attempt_reset(self) -> bool:
        """Check if circuit breaker should attempt reset"""
        return (self.last_failure_time and
                time.time() - self.last_failure_time > self.config.recovery_timeout)

    def _on_success(self):
        """Handle successful call"""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.half_open_calls += 1
            if self.half_open_calls >= self.config.half_open_max_calls:
                self.state = CircuitBreakerState.CLOSED
                self.failure_count = 0

    def _on_failure(self):
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.config.failure_threshold:
            self.state = CircuitBreakerState.OPEN

class RetryStrategy:
    """Intelligent retry strategy with exponential backoff"""

    def __init__(self,
                 max_retries: int = 3,
                 base_delay: float = 1.0,
                 max_delay: float = 60.0,
                 exponential_base: float = 2.0,
                 jitter: bool = True):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter

    async def execute(self, func: Callable, *args, **kwargs):
        """Execute function with retry strategy"""
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries:
                    delay = self._calculate_delay(attempt)
                    logger.warning("Retry attempt failed",
                                 attempt=attempt + 1,
                                 max_retries=self.max_retries,
                                 delay=delay,
                                 error=str(e))
                    await asyncio.sleep(delay)

        raise last_exception

    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for retry attempt"""
        delay = self.base_delay * (self.exponential_base ** attempt)
        delay = min(delay, self.max_delay)

        if self.jitter:
            import random
            delay *= (0.5 + random.random() * 0.5)  # Add 0-50% jitter

        return delay

class DataQualityValidator:
    """Data quality validation and scoring"""

    def __init__(self):
        self.validation_rules = {
            'required_fields': [],
            'field_types': {},
            'value_ranges': {},
            'custom_validators': []
        }

    def validate_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Validate single data record"""
        errors = []
        warnings = []
        score = 100.0

        # Check required fields
        for field in self.validation_rules['required_fields']:
            if field not in record or record[field] is None:
                errors.append(f"Missing required field: {field}")
                score -= 20

        # Check field types
        for field, expected_type in self.validation_rules['field_types'].items():
            if field in record and not isinstance(record[field], expected_type):
                warnings.append(f"Unexpected type for {field}: {type(record[field])}")
                score -= 5

        # Check value ranges
        for field, (min_val, max_val) in self.validation_rules['value_ranges'].items():
            if field in record:
                value = record[field]
                if isinstance(value, (int, float)) and not (min_val <= value <= max_val):
                    warnings.append(f"Value out of range for {field}: {value}")
                    score -= 10

        # Custom validators
        for validator in self.validation_rules['custom_validators']:
            try:
                validator_result = validator(record)
                if not validator_result['valid']:
                    warnings.extend(validator_result.get('warnings', []))
                    score -= validator_result.get('score_penalty', 5)
            except Exception as e:
                errors.append(f"Validator error: {str(e)}")
                score -= 15

        return {
            'valid': len(errors) == 0,
            'score': max(0, score),
            'errors': errors,
            'warnings': warnings
        }

class ErrorHandlingFramework:
    """Comprehensive error handling and monitoring framework"""

    def __init__(self):
        self.error_history: deque = deque(maxlen=1000)
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.retry_strategies: Dict[str, RetryStrategy] = {}
        self.validators: Dict[str, DataQualityValidator] = {}
        self.metrics = {
            'total_errors': 0,
            'errors_by_category': defaultdict(int),
            'errors_by_source': defaultdict(int),
            'average_resolution_time': 0,
            'uptime_percentage': 100.0
        }
        self._initialize_defaults()

    def _initialize_defaults(self):
        """Initialize default configurations"""
        # Default circuit breaker
        default_cb_config = CircuitBreakerConfig(
            failure_threshold=5,
            recovery_timeout=60,
            half_open_max_calls=3
        )
        self.circuit_breakers['default'] = CircuitBreaker(default_cb_config)

        # Default retry strategy
        self.retry_strategies['default'] = RetryStrategy(
            max_retries=3,
            base_delay=1.0,
            max_delay=30.0
        )

        # Default validator
        self.validators['default'] = DataQualityValidator()

    def register_circuit_breaker(self, name: str, config: CircuitBreakerConfig):
        """Register named circuit breaker"""
        self.circuit_breakers[name] = CircuitBreaker(config)

    def register_retry_strategy(self, name: str, strategy: RetryStrategy):
        """Register named retry strategy"""
        self.retry_strategies[name] = strategy

    def register_validator(self, name: str, validator: DataQualityValidator):
        """Register named validator"""
        self.validators[name] = validator

    async def execute_with_protection(self,
                                    func: Callable,
                                    source: str,
                                    *args,
                                    circuit_breaker: str = 'default',
                                    retry_strategy: str = 'default',
                                    **kwargs):
        """Execute function with full error protection"""

        cb = self.circuit_breakers.get(circuit_breaker, self.circuit_breakers['default'])
        if circuit_breaker != 'default' and circuit_breaker not in self.circuit_breakers:
            logger.warning("📊 DEBUG: Circuit breaker fallback to 'default'",
                         requested_breaker=circuit_breaker,
                         available_breakers=list(self.circuit_breakers.keys()),
                         algorithm_impact="MEDIUM - Using default circuit breaker instead of specific one")

        retry = self.retry_strategies.get(retry_strategy, self.retry_strategies['default'])
        if retry_strategy != 'default' and retry_strategy not in self.retry_strategies:
            logger.warning("📊 DEBUG: Retry strategy fallback to 'default'",
                         requested_strategy=retry_strategy,
                         available_strategies=list(self.retry_strategies.keys()),
                         algorithm_impact="MEDIUM - Using default retry strategy instead of specific one")

        try:
            # Execute with circuit breaker and retry protection
            return await cb.call(retry.execute, func, *args, **kwargs)
        except Exception as e:
            # Log error event
            error_event = ErrorEvent(
                timestamp=datetime.utcnow(),
                source=source,
                category=self._categorize_error(e),
                severity=self._assess_severity(e),
                message=str(e),
                details={'function': func.__name__, 'args': str(args)[:100]}
            )
            self._record_error(error_event)
            raise e

    def validate_data(self, data: Union[Dict, List[Dict]],
                     validator: str = 'default') -> Dict[str, Any]:
        """Validate data using specified validator"""

        val = self.validators.get(validator, self.validators['default'])

        if isinstance(data, dict):
            return val.validate_record(data)
        elif isinstance(data, list):
            results = [val.validate_record(record) for record in data]

            total_score = statistics.mean([r['score'] for r in results])
            all_errors = [error for r in results for error in r['errors']]
            all_warnings = [warning for r in results for warning in r['warnings']]

            return {
                'valid': all(r['valid'] for r in results),
                'score': total_score,
                'errors': all_errors,
                'warnings': all_warnings,
                'records_processed': len(results)
            }

    def _categorize_error(self, error: Exception) -> ErrorCategory:
        """Categorize error type"""
        error_str = str(error).lower()

        if 'network' in error_str or 'connection' in error_str:
            return ErrorCategory.NETWORK
        elif 'timeout' in error_str:
            return ErrorCategory.TIMEOUT
        elif 'auth' in error_str or 'permission' in error_str:
            return ErrorCategory.AUTHENTICATION
        elif 'rate' in error_str or 'limit' in error_str:
            return ErrorCategory.RATE_LIMIT
        elif 'parse' in error_str or 'json' in error_str:
            return ErrorCategory.PARSING
        elif 'validation' in error_str:
            return ErrorCategory.VALIDATION
        else:
            return ErrorCategory.RESOURCE

    def _assess_severity(self, error: Exception) -> ErrorSeverity:
        """Assess error severity"""
        error_str = str(error).lower()

        if any(term in error_str for term in ['critical', 'fatal', 'crash']):
            return ErrorSeverity.CRITICAL
        elif any(term in error_str for term in ['error', 'failed', 'exception']):
            return ErrorSeverity.HIGH
        elif any(term in error_str for term in ['warning', 'deprecated']):
            return ErrorSeverity.MEDIUM
        else:
            return ErrorSeverity.LOW

    def _record_error(self, error_event: ErrorEvent):
        """Record error event and update metrics"""
        self.error_history.append(error_event)
        self.metrics['total_errors'] += 1
        self.metrics['errors_by_category'][error_event.category.value] += 1
        self.metrics['errors_by_source'][error_event.source] += 1

        logger.error("Error recorded",
                    source=error_event.source,
                    category=error_event.category.value,
                    severity=error_event.severity.value,
                    message=error_event.message)

    def get_error_analytics(self) -> Dict[str, Any]:
        """Get comprehensive error analytics"""
        recent_errors = [e for e in self.error_history
                        if e.timestamp > datetime.utcnow() - timedelta(hours=24)]

        return {
            'total_errors_24h': len(recent_errors),
            'error_rate_per_hour': len(recent_errors) / 24,
            'errors_by_category': dict(self.metrics['errors_by_category']),
            'errors_by_source': dict(self.metrics['errors_by_source']),
            'severity_distribution': {
                severity.value: len([e for e in recent_errors if e.severity == severity])
                for severity in ErrorSeverity
            },
            'circuit_breaker_states': {
                name: cb.state.value for name, cb in self.circuit_breakers.items()
            },
            'top_error_sources': sorted(
                self.metrics['errors_by_source'].items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
        }

# Global error handling framework instance
error_framework = ErrorHandlingFramework()

# Decorator for easy error handling
def with_error_handling(source: str,
                       circuit_breaker: str = 'default',
                       retry_strategy: str = 'default'):
    """Decorator for automatic error handling"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            return await error_framework.execute_with_protection(
                func, source, *args,
                circuit_breaker=circuit_breaker,
                retry_strategy=retry_strategy,
                **kwargs
            )
        return wrapper
    return decorator