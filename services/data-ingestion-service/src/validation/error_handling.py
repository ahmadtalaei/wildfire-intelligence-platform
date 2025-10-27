"""
Challenge 1 Deliverable: Error Handling & Validation Framework
Data quality assurance modules and protocols for schema validation, retries, deduplication, and fault tolerance
"""

import asyncio
import hashlib
import json
import logging
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Any, Optional, Set, Callable
from dataclasses import dataclass
import traceback

class ValidationLevel(Enum):
    """Validation strictness levels"""
    STRICT = "strict"      # Fail on any validation error
    MODERATE = "moderate"  # Allow minor issues, log warnings
    PERMISSIVE = "permissive"  # Accept most data, minimal validation

class ErrorSeverity(Enum):
    """Error severity classification"""
    CRITICAL = "critical"  # System-level failures
    HIGH = "high"         # Data corruption or major issues
    MEDIUM = "medium"     # Validation failures
    LOW = "low"          # Minor format issues
    INFO = "info"        # Informational messages

@dataclass
class ValidationError:
    """Structured validation error information"""
    field: str
    value: Any
    error_type: str
    severity: ErrorSeverity
    message: str
    timestamp: str
    record_id: Optional[str] = None

@dataclass
class ValidationResult:
    """Result of validation process"""
    is_valid: bool
    errors: List[ValidationError]
    warnings: List[ValidationError]
    corrected_data: Optional[Dict[str, Any]]
    validation_time_ms: float

class DataDeduplicator:
    """Handles data deduplication to prevent duplicate ingestion"""

    def __init__(self, window_hours: int = 24):
        self.seen_hashes: Set[str] = set()
        self.window_hours = window_hours
        self.last_cleanup = time.time()

    def generate_hash(self, record: Dict[str, Any]) -> str:
        """Generate deterministic hash for record deduplication"""
        # Extract key fields for deduplication
        dedup_fields = []

        # Common deduplication keys across data types
        for field in ['timestamp', 'latitude', 'longitude', 'sensor_id', 'source_id']:
            if field in record:
                dedup_fields.append(f"{field}:{record[field]}")

        # Add data-specific fields
        if 'acq_date' in record and 'acq_time' in record:
            dedup_fields.append(f"acq:{record['acq_date']}:{record['acq_time']}")

        if 'station_id' in record:
            dedup_fields.append(f"station:{record['station_id']}")

        dedup_string = "|".join(sorted(dedup_fields))
        return hashlib.md5(dedup_string.encode()).hexdigest()

    def is_duplicate(self, record: Dict[str, Any]) -> bool:
        """Check if record is a duplicate"""
        record_hash = self.generate_hash(record)

        if record_hash in self.seen_hashes:
            return True

        self.seen_hashes.add(record_hash)
        self._cleanup_old_hashes()
        return False

    def _cleanup_old_hashes(self):
        """Periodically cleanup old hashes to prevent memory bloat"""
        current_time = time.time()
        if current_time - self.last_cleanup > 3600:  # Cleanup every hour
            # In production, implement time-based cleanup
            # For now, limit size
            if len(self.seen_hashes) > 100000:
                # Keep only recent 50000 hashes
                recent_hashes = list(self.seen_hashes)[-50000:]
                self.seen_hashes = set(recent_hashes)

            self.last_cleanup = current_time

class SchemaValidator:
    """Validates data against expected schemas"""

    def __init__(self):
        self.schemas = self._load_schemas()

    def _load_schemas(self) -> Dict[str, Dict]:
        """Load validation schemas for different data types"""
        return {
            'nasa_firms': {
                'required_fields': ['latitude', 'longitude', 'brightness', 'confidence'],
                'optional_fields': ['acq_date', 'acq_time', 'satellite', 'version'],
                'field_types': {
                    'latitude': float,
                    'longitude': float,
                    'brightness': (int, float),
                    'confidence': int
                },
                'field_ranges': {
                    'latitude': (-90, 90),
                    'longitude': (-180, 180),
                    'brightness': (0, 1000),
                    'confidence': (0, 100)
                }
            },
            'noaa_weather': {
                'required_fields': ['station_id', 'timestamp', 'temperature'],
                'optional_fields': ['humidity', 'wind_speed', 'pressure', 'precipitation'],
                'field_types': {
                    'station_id': str,
                    'temperature': (int, float),
                    'humidity': (int, float),
                    'wind_speed': (int, float),
                    'pressure': (int, float)
                },
                'field_ranges': {
                    'temperature': (-50, 60),
                    'humidity': (0, 100),
                    'wind_speed': (0, 200),
                    'pressure': (800, 1100)
                }
            },
            'iot_sensor': {
                'required_fields': ['sensor_id', 'timestamp'],
                'optional_fields': ['temperature', 'humidity', 'smoke_level', 'pm25'],
                'field_types': {
                    'sensor_id': str,
                    'temperature': (int, float),
                    'humidity': (int, float),
                    'smoke_level': (int, float),
                    'pm25': (int, float)
                },
                'field_ranges': {
                    'temperature': (-40, 70),
                    'humidity': (0, 100),
                    'smoke_level': (0, 1000),
                    'pm25': (0, 500)
                }
            }
        }

    def validate_record(self, record: Dict[str, Any], data_type: str,
                       validation_level: ValidationLevel = ValidationLevel.MODERATE) -> ValidationResult:
        """Validate a single record against schema"""
        start_time = time.time()
        errors = []
        warnings = []
        corrected_data = record.copy()

        if data_type not in self.schemas:
            errors.append(ValidationError(
                field='data_type',
                value=data_type,
                error_type='unknown_schema',
                severity=ErrorSeverity.HIGH,
                message=f"Unknown data type: {data_type}",
                timestamp=datetime.now(timezone.utc).isoformat()
            ))
            return ValidationResult(False, errors, warnings, None,
                                  (time.time() - start_time) * 1000)

        schema = self.schemas[data_type]

        # Check required fields
        for field in schema['required_fields']:
            if field not in record:
                severity = ErrorSeverity.HIGH if validation_level == ValidationLevel.STRICT else ErrorSeverity.MEDIUM
                errors.append(ValidationError(
                    field=field,
                    value=None,
                    error_type='missing_required_field',
                    severity=severity,
                    message=f"Required field '{field}' is missing",
                    timestamp=datetime.now(timezone.utc).isoformat()
                ))

        # Validate field types and ranges
        for field, value in record.items():
            if field in schema.get('field_types', {}):
                expected_type = schema['field_types'][field]
                if not isinstance(value, expected_type):
                    # Try to convert
                    try:
                        if expected_type == float or expected_type == (int, float):
                            corrected_data[field] = float(value)
                        elif expected_type == int:
                            corrected_data[field] = int(value)
                        elif expected_type == str:
                            corrected_data[field] = str(value)
                        else:
                            raise ValueError(f"Cannot convert {value} to {expected_type}")

                        warnings.append(ValidationError(
                            field=field,
                            value=value,
                            error_type='type_conversion',
                            severity=ErrorSeverity.LOW,
                            message=f"Converted {field} from {type(value)} to {expected_type}",
                            timestamp=datetime.now(timezone.utc).isoformat()
                        ))
                    except (ValueError, TypeError):
                        severity = ErrorSeverity.HIGH if validation_level == ValidationLevel.STRICT else ErrorSeverity.MEDIUM
                        errors.append(ValidationError(
                            field=field,
                            value=value,
                            error_type='invalid_type',
                            severity=severity,
                            message=f"Field '{field}' has invalid type. Expected {expected_type}, got {type(value)}",
                            timestamp=datetime.now(timezone.utc).isoformat()
                        ))

            # Validate ranges
            if field in schema.get('field_ranges', {}) and field in corrected_data:
                min_val, max_val = schema['field_ranges'][field]
                field_value = corrected_data[field]
                if isinstance(field_value, (int, float)):
                    if field_value < min_val or field_value > max_val:
                        severity = ErrorSeverity.MEDIUM if validation_level != ValidationLevel.PERMISSIVE else ErrorSeverity.LOW
                        errors.append(ValidationError(
                            field=field,
                            value=field_value,
                            error_type='out_of_range',
                            severity=severity,
                            message=f"Field '{field}' value {field_value} outside valid range [{min_val}, {max_val}]",
                            timestamp=datetime.now(timezone.utc).isoformat()
                        ))

        # Determine overall validity
        critical_errors = [e for e in errors if e.severity in [ErrorSeverity.CRITICAL, ErrorSeverity.HIGH]]
        is_valid = len(critical_errors) == 0

        if validation_level == ValidationLevel.STRICT:
            is_valid = len(errors) == 0

        validation_time = (time.time() - start_time) * 1000

        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            corrected_data=corrected_data if is_valid else None,
            validation_time_ms=validation_time
        )

class RetryManager:
    """Manages retry logic for failed operations"""

    def __init__(self, max_retries: int = 3, base_delay: float = 1.0, exponential_backoff: bool = True):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.exponential_backoff = exponential_backoff

    async def retry_with_backoff(self, operation: Callable, *args, **kwargs) -> Any:
        """Execute operation with retry and exponential backoff"""
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                if asyncio.iscoroutinefunction(operation):
                    return await operation(*args, **kwargs)
                else:
                    return operation(*args, **kwargs)

            except Exception as e:
                last_exception = e
                if attempt < self.max_retries:
                    delay = self.base_delay
                    if self.exponential_backoff:
                        delay = self.base_delay * (2 ** attempt)

                    logging.warning(f"Operation failed (attempt {attempt + 1}/{self.max_retries + 1}): {e}")
                    logging.info(f"Retrying in {delay} seconds...")
                    await asyncio.sleep(delay)
                else:
                    logging.error(f"Operation failed after {self.max_retries + 1} attempts: {e}")

        raise last_exception

class ErrorHandlingFramework:
    """Main error handling and validation framework"""

    def __init__(self, validation_level: ValidationLevel = ValidationLevel.MODERATE):
        self.validation_level = validation_level
        self.schema_validator = SchemaValidator()
        self.deduplicator = DataDeduplicator()
        self.retry_manager = RetryManager()
        self.error_counts = {}

        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    async def process_batch(self, records: List[Dict[str, Any]], data_type: str) -> Dict[str, Any]:
        """Process a batch of records with full error handling"""
        results = {
            'total_records': len(records),
            'valid_records': [],
            'invalid_records': [],
            'duplicate_records': [],
            'corrected_records': [],
            'validation_summary': {
                'schema_valid': 0,
                'format_valid': 0,
                'completeness': 0,
                'errors': []
            }
        }

        self.logger.info(f"🔍 Processing batch of {len(records)} {data_type} records")

        for i, record in enumerate(records):
            try:
                # Check for duplicates
                if self.deduplicator.is_duplicate(record):
                    results['duplicate_records'].append({
                        'index': i,
                        'record': record,
                        'reason': 'duplicate_detected'
                    })
                    continue

                # Validate record
                validation_result = self.schema_validator.validate_record(
                    record, data_type, self.validation_level
                )

                if validation_result.is_valid:
                    final_record = validation_result.corrected_data or record
                    results['valid_records'].append(final_record)

                    # Update validation summary
                    results['validation_summary']['schema_valid'] += 1
                    if not validation_result.errors:
                        results['validation_summary']['format_valid'] += 1
                    if len(record) >= len(self.schema_validator.schemas.get(data_type, {}).get('required_fields', [])):
                        results['validation_summary']['completeness'] += 1

                    # Track if record was corrected
                    if validation_result.corrected_data != record:
                        results['corrected_records'].append({
                            'index': i,
                            'original': record,
                            'corrected': validation_result.corrected_data,
                            'corrections': [w.message for w in validation_result.warnings]
                        })

                else:
                    results['invalid_records'].append({
                        'index': i,
                        'record': record,
                        'errors': [{'field': e.field, 'message': e.message, 'severity': e.severity.value}
                                 for e in validation_result.errors]
                    })

                    # Collect errors for summary
                    for error in validation_result.errors:
                        results['validation_summary']['errors'].append(error.message)

            except Exception as e:
                self.logger.error(f"Unexpected error processing record {i}: {e}")
                results['invalid_records'].append({
                    'index': i,
                    'record': record,
                    'errors': [{'field': 'system', 'message': str(e), 'severity': 'critical'}]
                })

        # Log results summary
        self.logger.info(f"✅ Batch processing complete:")
        self.logger.info(f"   Valid: {len(results['valid_records'])}")
        self.logger.info(f"   Invalid: {len(results['invalid_records'])}")
        self.logger.info(f"   Duplicates: {len(results['duplicate_records'])}")
        self.logger.info(f"   Corrected: {len(results['corrected_records'])}")

        return results

    def get_error_statistics(self) -> Dict[str, Any]:
        """Get comprehensive error statistics"""
        return {
            'total_errors': sum(self.error_counts.values()),
            'error_breakdown': self.error_counts.copy(),
            'deduplication_stats': {
                'unique_hashes_stored': len(self.deduplicator.seen_hashes)
            }
        }

# Global error handling framework instance
error_framework = ErrorHandlingFramework()

def get_error_framework() -> ErrorHandlingFramework:
    """Get the global error handling framework instance"""
    return error_framework