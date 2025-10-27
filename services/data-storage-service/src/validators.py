"""
Data Storage Service - Validation Module
Comprehensive data validation and sanitization utilities
"""

import re
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union, Tuple
from pathlib import Path
import structlog

from .models.data_models import DataType, StorageBackend
from .exceptions import ValidationError, DataIntegrityError

logger = structlog.get_logger()

class DataTypeValidator:
    """Validators for specific data types"""
    
    @staticmethod
    def validate_weather_data(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate weather data structure"""
        errors = []
        required_fields = ['timestamp', 'temperature', 'humidity', 'wind_speed', 'location']
        
        # Check required fields
        for field in required_fields:
            if field not in data:
                errors.append(f"Missing required field: {field}")
        
        # Validate field types and ranges
        if 'temperature' in data:
            temp = data['temperature']
            if not isinstance(temp, (int, float)) or temp < -100 or temp > 100:
                errors.append("Temperature must be a number between -100 and 100 Celsius")
        
        if 'humidity' in data:
            humidity = data['humidity']
            if not isinstance(humidity, (int, float)) or humidity < 0 or humidity > 100:
                errors.append("Humidity must be a number between 0 and 100 percent")
        
        if 'wind_speed' in data:
            wind = data['wind_speed']
            if not isinstance(wind, (int, float)) or wind < 0 or wind > 200:
                errors.append("Wind speed must be a non-negative number less than 200 m/s")
        
        if 'location' in data:
            location = data['location']
            if not isinstance(location, dict) or 'lat' not in location or 'lon' not in location:
                errors.append("Location must be a dict with 'lat' and 'lon' keys")
            else:
                lat, lon = location.get('lat'), location.get('lon')
                if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                    errors.append("Invalid coordinates: lat must be [-90,90], lon must be [-180,180]")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_sensor_data(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate sensor data structure"""
        errors = []
        required_fields = ['sensor_id', 'timestamp', 'readings', 'location']
        
        # Check required fields
        for field in required_fields:
            if field not in data:
                errors.append(f"Missing required field: {field}")
        
        # Validate sensor ID
        if 'sensor_id' in data:
            sensor_id = data['sensor_id']
            if not isinstance(sensor_id, str) or not re.match(r'^[a-zA-Z0-9_-]+$', sensor_id):
                errors.append("Sensor ID must be alphanumeric string with underscores/hyphens")
        
        # Validate readings structure
        if 'readings' in data:
            readings = data['readings']
            if not isinstance(readings, dict):
                errors.append("Readings must be a dictionary")
            else:
                # Validate reading values
                for key, value in readings.items():
                    if not isinstance(value, (int, float)):
                        errors.append(f"Reading '{key}' must be a number")
                    elif abs(value) > 1e10:  # Sanity check for extreme values
                        errors.append(f"Reading '{key}' value seems unrealistic: {value}")
        
        # Validate location (same as weather data)
        if 'location' in data:
            location = data['location']
            if not isinstance(location, dict) or 'lat' not in location or 'lon' not in location:
                errors.append("Location must be a dict with 'lat' and 'lon' keys")
            else:
                lat, lon = location.get('lat'), location.get('lon')
                if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                    errors.append("Invalid coordinates: lat must be [-90,90], lon must be [-180,180]")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_fire_detection_data(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate fire detection data structure"""
        errors = []
        required_fields = ['detection_id', 'timestamp', 'confidence', 'location', 'source']
        
        # Check required fields
        for field in required_fields:
            if field not in data:
                errors.append(f"Missing required field: {field}")
        
        # Validate confidence score
        if 'confidence' in data:
            confidence = data['confidence']
            if not isinstance(confidence, (int, float)) or not (0 <= confidence <= 1):
                errors.append("Confidence must be a number between 0 and 1")
        
        # Validate source
        if 'source' in data:
            source = data['source']
            valid_sources = ['satellite', 'ground_sensor', 'camera', 'manual_report']
            if source not in valid_sources:
                errors.append(f"Source must be one of: {valid_sources}")
        
        # Validate detection properties
        if 'properties' in data:
            props = data['properties']
            if not isinstance(props, dict):
                errors.append("Properties must be a dictionary")
            else:
                # Validate specific fire properties
                if 'area_hectares' in props:
                    area = props['area_hectares']
                    if not isinstance(area, (int, float)) or area < 0:
                        errors.append("Fire area must be a non-negative number")
                
                if 'temperature_celsius' in props:
                    temp = props['temperature_celsius']
                    if not isinstance(temp, (int, float)) or temp < 0 or temp > 2000:
                        errors.append("Fire temperature must be between 0 and 2000 Celsius")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_prediction_data(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate prediction data structure"""
        errors = []
        required_fields = ['model_id', 'prediction_type', 'timestamp', 'predictions', 'confidence_intervals']
        
        # Check required fields
        for field in required_fields:
            if field not in data:
                errors.append(f"Missing required field: {field}")
        
        # Validate model ID
        if 'model_id' in data:
            model_id = data['model_id']
            if not isinstance(model_id, str) or not re.match(r'^[a-zA-Z0-9_-]+$', model_id):
                errors.append("Model ID must be alphanumeric string with underscores/hyphens")
        
        # Validate prediction type
        if 'prediction_type' in data:
            pred_type = data['prediction_type']
            valid_types = ['fire_risk', 'spread_rate', 'containment_time', 'evacuation_zones']
            if pred_type not in valid_types:
                errors.append(f"Prediction type must be one of: {valid_types}")
        
        # Validate predictions structure
        if 'predictions' in data:
            predictions = data['predictions']
            if not isinstance(predictions, (list, dict)):
                errors.append("Predictions must be a list or dictionary")
        
        # Validate confidence intervals
        if 'confidence_intervals' in data:
            intervals = data['confidence_intervals']
            if isinstance(intervals, dict):
                for key, interval in intervals.items():
                    if not isinstance(interval, dict) or 'lower' not in interval or 'upper' not in interval:
                        errors.append(f"Confidence interval for '{key}' must have 'lower' and 'upper' values")
                    elif interval['lower'] > interval['upper']:
                        errors.append(f"Invalid confidence interval for '{key}': lower > upper")
        
        return len(errors) == 0, errors

class GeospatialValidator:
    """Validators for geospatial data"""
    
    @staticmethod
    def validate_coordinates(lat: float, lon: float) -> bool:
        """Validate latitude and longitude coordinates"""
        return -90 <= lat <= 90 and -180 <= lon <= 180
    
    @staticmethod
    def validate_bounding_box(bounds: Dict[str, float]) -> Tuple[bool, List[str]]:
        """Validate geospatial bounding box"""
        errors = []
        required_keys = ['min_lat', 'max_lat', 'min_lon', 'max_lon']
        
        # Check required keys
        for key in required_keys:
            if key not in bounds:
                errors.append(f"Missing required key in bounds: {key}")
        
        if not errors:  # Only validate values if all keys present
            min_lat = bounds['min_lat']
            max_lat = bounds['max_lat']
            min_lon = bounds['min_lon']
            max_lon = bounds['max_lon']
            
            # Validate coordinate ranges
            if not (-90 <= min_lat <= 90) or not (-90 <= max_lat <= 90):
                errors.append("Latitude values must be between -90 and 90")
            
            if not (-180 <= min_lon <= 180) or not (-180 <= max_lon <= 180):
                errors.append("Longitude values must be between -180 and 180")
            
            # Validate logical order
            if min_lat >= max_lat:
                errors.append("min_lat must be less than max_lat")
            
            if min_lon >= max_lon:
                errors.append("min_lon must be less than max_lon")
            
            # Check for reasonable bounding box size (not too large)
            if (max_lat - min_lat) > 90 or (max_lon - min_lon) > 180:
                errors.append("Bounding box is too large")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_polygon(coordinates: List[List[float]]) -> Tuple[bool, List[str]]:
        """Validate polygon coordinates"""
        errors = []
        
        if not isinstance(coordinates, list):
            errors.append("Polygon coordinates must be a list")
            return False, errors
        
        if len(coordinates) < 3:
            errors.append("Polygon must have at least 3 vertices")
            return False, errors
        
        # Validate each coordinate pair
        for i, coord in enumerate(coordinates):
            if not isinstance(coord, list) or len(coord) != 2:
                errors.append(f"Coordinate {i} must be [lon, lat] pair")
            else:
                lon, lat = coord
                if not GeospatialValidator.validate_coordinates(lat, lon):
                    errors.append(f"Invalid coordinates at index {i}: [{lon}, {lat}]")
        
        # Check if polygon is closed (first and last points should be the same)
        if len(coordinates) > 2 and coordinates[0] != coordinates[-1]:
            errors.append("Polygon must be closed (first and last coordinates must be the same)")
        
        return len(errors) == 0, errors

class SecurityValidator:
    """Security-related validators"""
    
    @staticmethod
    def validate_api_key(api_key: str) -> bool:
        """Validate API key format"""
        if not isinstance(api_key, str):
            return False
        
        # Basic validation: alphanumeric, minimum length
        return re.match(r'^[a-zA-Z0-9]{32,}$', api_key) is not None
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename for safe storage"""
        # Remove dangerous characters and limit length
        sanitized = re.sub(r'[^\w\-_\.]', '_', filename)
        sanitized = sanitized[:255]  # Limit filename length
        
        # Prevent directory traversal
        sanitized = sanitized.replace('..', '_')
        
        return sanitized
    
    @staticmethod
    def validate_sql_injection(query_string: str) -> bool:
        """Basic SQL injection detection"""
        # Simple patterns that might indicate SQL injection
        dangerous_patterns = [
            r'union\s+select',
            r'drop\s+table',
            r'delete\s+from',
            r'insert\s+into',
            r'update\s+.*\s+set',
            r'exec\s*\(',
            r'sp_\w+',
            r'xp_\w+',
            r'--\s*$'
        ]
        
        query_lower = query_string.lower()
        for pattern in dangerous_patterns:
            if re.search(pattern, query_lower):
                return False
        
        return True

class DataSizeValidator:
    """Validators for data size constraints"""
    
    @staticmethod
    def validate_request_size(data: Any, max_size_bytes: int = 100 * 1024 * 1024) -> Tuple[bool, int]:
        """Validate request data size"""
        try:
            if isinstance(data, (str, bytes)):
                size = len(data.encode('utf-8') if isinstance(data, str) else data)
            else:
                # Serialize to JSON to estimate size
                size = len(json.dumps(data, default=str).encode('utf-8'))
            
            return size <= max_size_bytes, size
        except (TypeError, ValueError):
            # If we can't serialize, assume it's too large
            return False, -1
    
    @staticmethod
    def validate_bulk_request_size(items: List[Any], max_items: int = 10000, 
                                 max_total_size: int = 500 * 1024 * 1024) -> Tuple[bool, List[str]]:
        """Validate bulk request constraints"""
        errors = []
        
        # Check item count
        if len(items) > max_items:
            errors.append(f"Too many items in bulk request: {len(items)} (max: {max_items})")
        
        # Estimate total size
        total_size = 0
        for item in items:
            try:
                item_size = len(json.dumps(item, default=str).encode('utf-8'))
                total_size += item_size
            except (TypeError, ValueError):
                errors.append("One or more items cannot be serialized")
                break
        
        if total_size > max_total_size:
            errors.append(f"Bulk request too large: {total_size} bytes (max: {max_total_size})")
        
        return len(errors) == 0, errors

class TimeValidator:
    """Time and date validation utilities"""
    
    @staticmethod
    def validate_timestamp(timestamp: Union[str, datetime]) -> Tuple[bool, Optional[datetime]]:
        """Validate and parse timestamp"""
        try:
            if isinstance(timestamp, str):
                # Try to parse ISO format
                if timestamp.endswith('Z'):
                    timestamp = timestamp[:-1] + '+00:00'
                parsed_time = datetime.fromisoformat(timestamp)
            elif isinstance(timestamp, datetime):
                parsed_time = timestamp
            else:
                return False, None
            
            # Validate reasonable time range (not too far in past/future)
            now = datetime.utcnow()
            min_time = now - timedelta(days=365 * 10)  # 10 years ago
            max_time = now + timedelta(days=365)       # 1 year in future
            
            if not (min_time <= parsed_time <= max_time):
                return False, None
            
            return True, parsed_time
            
        except (ValueError, TypeError):
            return False, None
    
    @staticmethod
    def validate_time_range(start_time: datetime, end_time: datetime) -> Tuple[bool, List[str]]:
        """Validate time range constraints"""
        errors = []
        
        if start_time >= end_time:
            errors.append("Start time must be before end time")
        
        # Check if range is reasonable (not too large)
        time_diff = end_time - start_time
        if time_diff > timedelta(days=365):
            errors.append("Time range too large (maximum 1 year)")
        
        return len(errors) == 0, errors

class CompositeValidator:
    """Main validator that combines all validation types"""
    
    def __init__(self):
        self.data_type_validators = {
            DataType.WEATHER: DataTypeValidator.validate_weather_data,
            DataType.SENSOR: DataTypeValidator.validate_sensor_data,
            DataType.FIRE_DETECTION: DataTypeValidator.validate_fire_detection_data,
            DataType.PREDICTIONS: DataTypeValidator.validate_prediction_data,
        }
    
    def validate_storage_request(self, request_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Comprehensive validation of storage request"""
        all_errors = []
        
        # Basic structure validation
        required_fields = ['data_type', 'data']
        for field in required_fields:
            if field not in request_data:
                all_errors.append(f"Missing required field: {field}")
        
        if all_errors:  # Don't continue if basic structure is invalid
            return False, all_errors
        
        # Validate data type
        try:
            data_type = DataType(request_data['data_type'])
        except ValueError:
            all_errors.append(f"Invalid data_type: {request_data['data_type']}")
            return False, all_errors
        
        # Validate data size
        data = request_data['data']
        size_valid, size = DataSizeValidator.validate_request_size(data)
        if not size_valid:
            all_errors.append(f"Data size too large: {size} bytes")
        
        # Validate timestamp if present
        if 'timestamp' in request_data:
            timestamp_valid, parsed_time = TimeValidator.validate_timestamp(request_data['timestamp'])
            if not timestamp_valid:
                all_errors.append("Invalid timestamp format or value")
        
        # Data type specific validation
        if data_type in self.data_type_validators:
            type_valid, type_errors = self.data_type_validators[data_type](data)
            all_errors.extend(type_errors)
        
        # Validate geospatial bounds if present
        if 'spatial_bounds' in request_data:
            bounds_valid, bounds_errors = GeospatialValidator.validate_bounding_box(
                request_data['spatial_bounds']
            )
            all_errors.extend(bounds_errors)
        
        # Validate tags if present
        if 'tags' in request_data:
            tags = request_data['tags']
            if not isinstance(tags, list):
                all_errors.append("Tags must be a list")
            else:
                for tag in tags:
                    if not isinstance(tag, str) or len(tag) > 50:
                        all_errors.append("Each tag must be a string with max 50 characters")
        
        return len(all_errors) == 0, all_errors
    
    def validate_query_request(self, request_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Comprehensive validation of query request"""
        all_errors = []
        
        # Basic validation
        if 'data_type' not in request_data:
            all_errors.append("Missing required field: data_type")
            return False, all_errors
        
        # Validate data type
        try:
            data_type = DataType(request_data['data_type'])
        except ValueError:
            all_errors.append(f"Invalid data_type: {request_data['data_type']}")
        
        # Validate time range
        start_time = request_data.get('start_time')
        end_time = request_data.get('end_time')
        
        if start_time:
            start_valid, start_parsed = TimeValidator.validate_timestamp(start_time)
            if not start_valid:
                all_errors.append("Invalid start_time format")
        else:
            start_parsed = None
        
        if end_time:
            end_valid, end_parsed = TimeValidator.validate_timestamp(end_time)
            if not end_valid:
                all_errors.append("Invalid end_time format")
        else:
            end_parsed = None
        
        if start_parsed and end_parsed:
            range_valid, range_errors = TimeValidator.validate_time_range(start_parsed, end_parsed)
            all_errors.extend(range_errors)
        
        # Validate pagination parameters
        if 'limit' in request_data:
            limit = request_data['limit']
            if not isinstance(limit, int) or not (1 <= limit <= 10000):
                all_errors.append("Limit must be an integer between 1 and 10000")
        
        if 'offset' in request_data:
            offset = request_data['offset']
            if not isinstance(offset, int) or offset < 0:
                all_errors.append("Offset must be a non-negative integer")
        
        # Validate spatial bounds
        if 'spatial_bounds' in request_data:
            bounds_valid, bounds_errors = GeospatialValidator.validate_bounding_box(
                request_data['spatial_bounds']
            )
            all_errors.extend(bounds_errors)
        
        # Validate filters
        if 'filters' in request_data:
            filters = request_data['filters']
            if not isinstance(filters, dict):
                all_errors.append("Filters must be a dictionary")
            else:
                # Validate filter values for SQL injection
                for key, value in filters.items():
                    if isinstance(value, str) and not SecurityValidator.validate_sql_injection(value):
                        all_errors.append(f"Potentially dangerous filter value for '{key}'")
        
        return len(all_errors) == 0, all_errors

# Create singleton instance
validator = CompositeValidator()

# Export main functions and classes
__all__ = [
    'DataTypeValidator', 'GeospatialValidator', 'SecurityValidator', 
    'DataSizeValidator', 'TimeValidator', 'CompositeValidator', 'validator'
]