"""
Comprehensive data validation for wildfire intelligence platform

It provides structured ways to validate incoming data from multiple sources (satellite, weather, IoT sensors, fire incidents) before ingestion or analysis.

Key Features:\
1. Source Type Rules
- Different validation rules for:
    - satellite (e.g., MODIS, VIIRS, fire radiative power)
    - weather (temperature, humidity, wind)
    - iot_sensor (air quality, temperature, coordinates)
    - fire_incident (acres burned, containment, fire name)

- Each type defines:
    - Required and optional fields
    - Valid numeric ranges for key metrics

2. Batch Validation
- validate_batch(data, config):
    - Validates each record individually
    - Aggregates errors/warnings
    - Computes batch-level quality metrics (validity rate)

3. Record Validation
- validate_record(record, source_type):
    - Checks required fields
    - Checks numeric ranges, types, and patterns
    - Validates timestamps (within last 5 years and 24h into future)
    - Checks geospatial coordinates and precision
    - Applies source-specific rules (e.g., FRP, PM2.5 vs PM10, fire containment)
    - Checks if data is relevant to California

4. File-Based Validation
- validate_file_data(data, filename):
- Infers source type from filename
- Checks data consistency across records
- Validates the batch and merges results

5. Geospatial Validation
- Ensures latitude and longitude are numeric and within valid ranges.
- Warns about “null island” (0,0) or excessive decimal precision.
- Checks if the point lies within or near California.

6. Source-Specific Validations
- Satellite: Sensors, confidence vs brightness, Fire Radiative Power (FRP)
- Weather: Temperature/humidity extremes, wind speed/direction
- IoT Sensors: PM2.5 vs PM10, hazardous air quality warnings, sensor ID format
- Fire Incidents: Acres burned, containment percent, fire name length

7. Timestamp Parsing
_parse_timestamp() handles strings, Unix timestamps, and datetime objects.
Supports multiple formats (ISO, %Y-%m-%d, %Y%m%d_%H%M%S, etc.).

8. California Relevance
- Warns if data is outside California.
- Gives extra buffer warnings for points near but outside California.

9. Metadata and Metrics
get_quality_metrics() returns supported source types, California bounds, timestamp, and validator info.


10. Has Asynchronous Design
- Many methods are async:
    - validate_batch
    - validate_record
    - validate_file_data
Allows integration with asynchronous data ingestion pipelines for large-scale wildfire datasets.
"""

import logging
import re
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Union, Tuple
import math

try:
    import numpy as np
except ImportError:
    np = None

try:
    from shapely.geometry import Point, Polygon
    from shapely.ops import contains
except ImportError:
    Point = None
    Polygon = None

try:
    from ..geo_config.geographic_bounds import CALIFORNIA_BOUNDS_MINMAX
except ImportError:
    try:
        from geo_config.geographic_bounds import CALIFORNIA_BOUNDS_MINMAX
    except ImportError:
        # Fallback bounds if config is not available
        CALIFORNIA_BOUNDS_MINMAX = {
            'lat_min': 32.0, 'lat_max': 42.0,
            'lon_min': -124.0, 'lon_max': -114.0
        }

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ValidationError:
    """Represents a validation error"""
    
    def __init__(self, field: str, message: str, severity: str = 'error', value: Any = None):
        self.field = field
        self.message = message
        self.severity = severity  # 'error', 'warning', 'info'
        self.value = value
        self.timestamp = datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'field': self.field,
            'message': self.message,
            'severity': self.severity,
            'value': self.value,
            'timestamp': self.timestamp.isoformat()
        }

class ValidationResult:
    """Enhanced validation result with detailed error tracking"""
    
    def __init__(self):
        self.is_valid = True
        self.errors: List[ValidationError] = []
        self.warnings: List[ValidationError] = []
        self.quality_score = 1.0
        self.validation_metadata = {}
        
    def add_error(self, field: str, message: str, value: Any = None):
        """Add validation error"""
        error = ValidationError(field, message, 'error', value)
        self.errors.append(error)
        self.is_valid = False
        self._update_quality_score()
    
    def add_warning(self, field: str, message: str, value: Any = None):
        """Add validation warning"""
        warning = ValidationError(field, message, 'warning', value)
        self.warnings.append(warning)
        self._update_quality_score()
    
    def _update_quality_score(self):
        """Update quality score based on errors and warnings"""
        error_penalty = len(self.errors) * 0.2
        warning_penalty = len(self.warnings) * 0.05
        self.quality_score = max(0.0, 1.0 - error_penalty - warning_penalty)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get validation summary"""
        return {
            'is_valid': self.is_valid,
            'quality_score': self.quality_score,
            'error_count': len(self.errors),
            'warning_count': len(self.warnings),
            'total_issues': len(self.errors) + len(self.warnings)
        }
    
    def get_all_issues(self) -> List[Dict[str, Any]]:
        """Get all validation issues"""
        all_issues = []
        all_issues.extend([error.to_dict() for error in self.errors])
        all_issues.extend([warning.to_dict() for warning in self.warnings])
        return sorted(all_issues, key=lambda x: x['timestamp'])

class DataValidator:
    """Comprehensive data validator for wildfire intelligence platform"""
    
    def __init__(self):
        self.california_bounds = CALIFORNIA_BOUNDS_MINMAX
        
        # Define validation rules for different data types
        self.validation_rules = {
            'satellite': {
                'required_fields': ['latitude', 'longitude', 'timestamp'],
                'optional_fields': ['sensor', 'confidence', 'brightness', 'frp'],
                'latitude_range': (-90, 90),
                'longitude_range': (-180, 180),
                'confidence_range': (0, 100),
                'brightness_range': (0, 500),  # Kelvin brightness temperature
                'frp_range': (0, 10000)  # Fire Radiative Power in MW
            },
            'weather': {
                'required_fields': ['latitude', 'longitude', 'timestamp'],
                'optional_fields': ['temperature', 'humidity', 'wind_speed', 'pressure'],
                'latitude_range': (-90, 90),
                'longitude_range': (-180, 180),
                'temperature_range': (-50, 70),  # Celsius
                'humidity_range': (0, 100),  # Percentage
                'wind_speed_range': (0, 200),  # m/s
                'pressure_range': (800, 1100)  # hPa
            },
            'iot_sensor': {
                'required_fields': ['sensor_id', 'timestamp'],
                'optional_fields': ['latitude', 'longitude', 'pm25', 'pm10', 'temperature'],
                'latitude_range': (-90, 90),
                'longitude_range': (-180, 180),
                'pm25_range': (0, 1000),  # mug/m³
                'pm10_range': (0, 2000),  # mug/m³
                'temperature_range': (-40, 80)  # Celsius
            },
            'fire_incident': {
                'required_fields': ['incident_id', 'latitude', 'longitude', 'timestamp'],
                'optional_fields': ['fire_name', 'acres_burned', 'containment_percent'],
                'latitude_range': (-90, 90),
                'longitude_range': (-180, 180),
                'acres_burned_range': (0, 1000000),  # Acres
                'containment_percent_range': (0, 100)
            }
        }
        
        # Time validation settings
        self.max_future_hours = 24  # Allow data up to 24 hours in future
        self.max_past_years = 5  # Allow data up to 5 years old
    
    async def validate_batch(self, data: List[Dict[str, Any]], config) -> ValidationResult:
        """Validate batch of records"""
        result = ValidationResult()
        
        try:
            source_type = getattr(config, 'source_type', 'unknown')
            
            if not data:
                result.add_error('batch', 'Empty data batch provided')
                return result
            
            valid_records = 0
            for i, record in enumerate(data):
                record_result = await self.validate_record(record, source_type)
                
                if record_result.is_valid:
                    valid_records += 1
                
                # Aggregate errors and warnings
                for error in record_result.errors:
                    result.add_error(f"record_{i}.{error.field}", error.message, error.value)
                
                for warning in record_result.warnings:
                    result.add_warning(f"record_{i}.{warning.field}", warning.message, warning.value)
            
            # Calculate batch-level quality metrics
            batch_validity_rate = valid_records / len(data)
            result.validation_metadata = {
                'total_records': len(data),
                'valid_records': valid_records,
                'validity_rate': batch_validity_rate,
                'source_type': source_type
            }
            
            # Adjust quality score based on batch validity
            result.quality_score = min(result.quality_score, batch_validity_rate)
            
            logger.info(f"Validated batch: {valid_records}/{len(data)} records valid")
            
        except Exception as e:
            result.add_error('validation', f'Batch validation failed: {str(e)}')
            logger.error(f"Batch validation error: {e}")
        
        return result
    
    async def validate_record(self, record: Dict[str, Any], source_type: str) -> ValidationResult:
        """Validate individual record"""
        result = ValidationResult()
        
        try:
            # Get validation rules for source type
            rules = self.validation_rules.get(source_type, self.validation_rules.get('satellite', {}))
            
            # Validate required fields
            await self._validate_required_fields(record, rules, result)
            
            # Validate data types and ranges
            await self._validate_field_values(record, rules, result, source_type)
            
            # Validate timestamps
            await self._validate_timestamp(record, result)
            
            # Validate geospatial data
            await self._validate_geospatial(record, result)
            
            # Validate source-specific fields
            if source_type == 'satellite':
                await self._validate_satellite_specific(record, result)
            elif source_type == 'weather':
                await self._validate_weather_specific(record, result)
            elif source_type in ['iot', 'sensor', 'iot_sensor']:
                await self._validate_iot_specific(record, result)
            elif source_type in ['fire', 'fire_incident']:
                await self._validate_fire_specific(record, result)
            
            # Validate California relevance
            await self._validate_california_relevance(record, result)
            
        except Exception as e:
            result.add_error('validation', f'Record validation failed: {str(e)}')
            logger.error(f"Record validation error: {e}")
        
        return result
    
    async def validate_file_data(self, data: List[Dict[str, Any]], filename: str = None) -> ValidationResult:
        """Validate file-based data"""
        result = ValidationResult()
        
        try:
            # Infer source type from filename
            source_type = self._infer_source_type_from_filename(filename) if filename else 'unknown'
            
            # Validate file structure
            if not data:
                result.add_error('file', 'File contains no data')
                return result
            
            # Check for consistent data structure
            if len(data) > 1:
                first_keys = set(data[0].keys())
                inconsistent_records = 0
                
                for i, record in enumerate(data[1:], 1):
                    record_keys = set(record.keys())
                    if record_keys != first_keys:
                        inconsistent_records += 1
                        if inconsistent_records <= 5:  # Limit warning spam
                            result.add_warning(
                                f'record_{i}', 
                                f'Inconsistent field structure: expected {first_keys}, got {record_keys}'
                            )
                
                if inconsistent_records > 0:
                    result.add_warning('file_structure', f'{inconsistent_records} records have inconsistent structure')
            
            # Validate individual records
            batch_config = type('Config', (), {'source_type': source_type})()
            batch_result = await self.validate_batch(data, batch_config)
            
            # Merge results
            result.errors.extend(batch_result.errors)
            result.warnings.extend(batch_result.warnings)
            result.is_valid = batch_result.is_valid and result.is_valid
            result.quality_score = min(result.quality_score, batch_result.quality_score)
            
            # Add file-specific metadata
            result.validation_metadata.update({
                'filename': filename,
                'inferred_source_type': source_type,
                **batch_result.validation_metadata
            })
            
        except Exception as e:
            result.add_error('file_validation', f'File validation failed: {str(e)}')
            logger.error(f"File validation error: {e}")
        
        return result
    
    async def _validate_required_fields(self, record: Dict[str, Any], rules: Dict[str, Any], result: ValidationResult):
        """Validate that required fields are present"""
        required_fields = rules.get('required_fields', [])
        
        for field in required_fields:
            if field not in record or record[field] is None:
                result.add_error(field, f'Required field "{field}" is missing or null')
    
    async def _validate_field_values(self, record: Dict[str, Any], rules: Dict[str, Any], result: ValidationResult, source_type: str):
        """Validate field values against expected ranges and types"""
        
        for field, value in record.items():
            if value is None:
                continue
                
            # Validate numeric ranges
            range_key = f'{field}_range'
            if range_key in rules:
                try:
                    num_value = float(value)
                    min_val, max_val = rules[range_key]
                    if not (min_val <= num_value <= max_val):
                        result.add_error(
                            field, 
                            f'{field} value {num_value} outside valid range [{min_val}, {max_val}]',
                            num_value
                        )
                except (ValueError, TypeError):
                    result.add_error(field, f'{field} should be numeric but got {type(value).__name__}: {value}', value)
            
            # Validate specific field patterns
            if field in ['sensor_id', 'incident_id', 'device_id']:
                if not isinstance(value, str) or len(str(value).strip()) == 0:
                    result.add_error(field, f'{field} must be a non-empty string', value)
    
    async def _validate_timestamp(self, record: Dict[str, Any], result: ValidationResult):
        """Validate timestamp fields"""
        timestamp_fields = ['timestamp', 'acquisition_date', 'valid_time', 'start_date']
        
        for field in timestamp_fields:
            if field not in record or record[field] is None:
                continue
            
            try:
                # Try to parse timestamp
                timestamp = self._parse_timestamp(record[field])
                
                # Check if timestamp is reasonable
                now = datetime.now(timezone.utc)
                future_limit = now + timedelta(hours=self.max_future_hours)
                past_limit = now - timedelta(days=365 * self.max_past_years)
                
                if timestamp > future_limit:
                    result.add_warning(
                        field, 
                        f'Timestamp is too far in the future: {timestamp.isoformat()}',
                        timestamp.isoformat()
                    )
                elif timestamp < past_limit:
                    result.add_warning(
                        field,
                        f'Timestamp is very old: {timestamp.isoformat()}',
                        timestamp.isoformat()
                    )
                
            except Exception as e:
                result.add_error(field, f'Invalid timestamp format: {str(e)}', record[field])
    
    async def _validate_geospatial(self, record: Dict[str, Any], result: ValidationResult):
        """Validate geospatial coordinates"""
        lat_fields = ['latitude', 'lat']
        lon_fields = ['longitude', 'lon', 'long']
        
        latitude = None
        longitude = None
        
        # Find latitude
        for field in lat_fields:
            if field in record and record[field] is not None:
                latitude = record[field]
                lat_field = field
                break
        
        # Find longitude
        for field in lon_fields:
            if field in record and record[field] is not None:
                longitude = record[field]
                lon_field = field
                break
        
        if latitude is not None and longitude is not None:
            try:
                lat_val = float(latitude)
                lon_val = float(longitude)
                
                # Check coordinate ranges
                if not (-90 <= lat_val <= 90):
                    result.add_error(lat_field, f'Latitude {lat_val} outside valid range [-90, 90]', lat_val)
                
                if not (-180 <= lon_val <= 180):
                    result.add_error(lon_field, f'Longitude {lon_val} outside valid range [-180, 180]', lon_val)
                
                # Check for common coordinate errors
                if lat_val == 0 and lon_val == 0:
                    result.add_warning('coordinates', 'Coordinates are (0,0) - possible null island error')
                
                # Check coordinate precision (too many decimal places might indicate error)
                lat_str = str(latitude)
                lon_str = str(longitude)
                if '.' in lat_str and len(lat_str.split('.')[1]) > 6:
                    result.add_warning(lat_field, 'Latitude has excessive decimal precision')
                if '.' in lon_str and len(lon_str.split('.')[1]) > 6:
                    result.add_warning(lon_field, 'Longitude has excessive decimal precision')
                
            except (ValueError, TypeError):
                if latitude is not None:
                    result.add_error(lat_field, f'Latitude must be numeric, got {type(latitude).__name__}: {latitude}', latitude)
                if longitude is not None:
                    result.add_error(lon_field, f'Longitude must be numeric, got {type(longitude).__name__}: {longitude}', longitude)
    
    async def _validate_satellite_specific(self, record: Dict[str, Any], result: ValidationResult):
        """Validate satellite-specific fields"""
        
        # Validate sensor field
        if 'sensor' in record and record['sensor']:
            sensor = str(record['sensor']).lower()
            valid_sensors = ['modis', 'viirs', 'landsat', 'sentinel', 'goes', 'noaa']
            if not any(valid_sensor in sensor for valid_sensor in valid_sensors):
                result.add_warning('sensor', f'Unknown sensor type: {record["sensor"]}')
        
        # Validate confidence and brightness correlation for MODIS/VIIRS
        if all(field in record for field in ['confidence', 'brightness', 'bright_t31']):
            try:
                confidence = float(record['confidence'])
                brightness = float(record['brightness'])
                bright_t31 = float(record['bright_t31'])
                
                # High confidence should correlate with higher brightness
                if confidence > 80 and brightness < 320:
                    result.add_warning(
                        'fire_detection',
                        f'High confidence ({confidence}) with low brightness ({brightness}) - verify detection'
                    )
                
                # Check brightness temperature difference
                temp_diff = brightness - bright_t31
                if temp_diff < 0:
                    result.add_warning('brightness', 'Brightness T21 higher than T31 - unusual fire signature')
                    
            except (ValueError, TypeError):
                pass  # Already handled by field validation
        
        # Validate FRP (Fire Radiative Power)
        if 'frp' in record and record['frp'] is not None:
            try:
                frp = float(record['frp'])
                if frp > 1000:
                    result.add_warning('frp', f'Very high Fire Radiative Power: {frp} MW - verify detection')
                elif frp < 0:
                    result.add_error('frp', f'Fire Radiative Power cannot be negative: {frp}', frp)
            except (ValueError, TypeError):
                pass
    
    async def _validate_weather_specific(self, record: Dict[str, Any], result: ValidationResult):
        """Validate weather-specific fields"""
        
        # Validate temperature and humidity relationship
        if all(field in record and record[field] is not None for field in ['temperature', 'relative_humidity']):
            try:
                temp = float(record['temperature'])
                rh = float(record['relative_humidity'])
                
                # Extreme combinations
                if temp > 40 and rh > 80:
                    result.add_warning('weather', f'Unusual combination: high temperature ({temp}degC) with high humidity ({rh}%)')
                elif temp < -10 and rh < 20:
                    result.add_warning('weather', f'Unusual combination: very low temperature ({temp}degC) with very low humidity ({rh}%)')
                    
            except (ValueError, TypeError):
                pass
        
        # Validate wind speed and direction
        if 'wind_speed' in record and record['wind_speed'] is not None:
            try:
                wind_speed = float(record['wind_speed'])
                if wind_speed > 50:  # Very high wind speed
                    result.add_warning('wind_speed', f'Very high wind speed: {wind_speed} m/s - verify measurement')
                
                # Check if wind direction is provided with wind speed
                if wind_speed > 1 and 'wind_direction' not in record:
                    result.add_warning('wind_direction', 'Wind speed provided without wind direction')
                    
            except (ValueError, TypeError):
                pass
        
        # Validate wind direction
        if 'wind_direction' in record and record['wind_direction'] is not None:
            try:
                wind_dir = float(record['wind_direction'])
                if not (0 <= wind_dir <= 360):
                    result.add_error('wind_direction', f'Wind direction {wind_dir} outside range [0, 360]', wind_dir)
            except (ValueError, TypeError):
                result.add_error('wind_direction', f'Wind direction must be numeric', record['wind_direction'])
    
    async def _validate_iot_specific(self, record: Dict[str, Any], result: ValidationResult):
        """Validate IoT sensor-specific fields"""
        
        # Validate PM2.5 and PM10 relationship
        if all(field in record and record[field] is not None for field in ['pm25', 'pm10']):
            try:
                pm25 = float(record['pm25'])
                pm10 = float(record['pm10'])
                
                if pm25 > pm10:
                    result.add_error('particulates', f'PM2.5 ({pm25}) cannot be greater than PM10 ({pm10})', {'pm25': pm25, 'pm10': pm10})
                
                # Check for smoke conditions
                if pm25 > 150:
                    result.add_warning('air_quality', f'Very hazardous PM2.5 levels detected: {pm25} mug/m³')
                    
            except (ValueError, TypeError):
                pass
        
        # Validate sensor ID format
        if 'sensor_id' in record and record['sensor_id']:
            sensor_id = str(record['sensor_id'])
            if len(sensor_id) < 3:
                result.add_warning('sensor_id', f'Sensor ID seems too short: {sensor_id}')
            elif not re.match(r'^[A-Za-z0-9_-]+$', sensor_id):
                result.add_warning('sensor_id', f'Sensor ID contains unusual characters: {sensor_id}')
    
    async def _validate_fire_specific(self, record: Dict[str, Any], result: ValidationResult):
        """Validate fire incident-specific fields"""
        
        # Validate acres burned
        if 'acres_burned' in record and record['acres_burned'] is not None:
            try:
                acres = float(record['acres_burned'])
                if acres > 100000:  # Very large fire
                    result.add_warning('fire_size', f'Extremely large fire reported: {acres} acres')
                elif acres < 0.1:  # Very small fire
                    result.add_warning('fire_size', f'Very small fire reported: {acres} acres')
            except (ValueError, TypeError):
                pass
        
        # Validate containment percentage
        if 'containment_percent' in record and record['containment_percent'] is not None:
            try:
                containment = float(record['containment_percent'])
                if containment > 100:
                    result.add_error('containment_percent', f'Containment cannot exceed 100%: {containment}%', containment)
                elif containment < 0:
                    result.add_error('containment_percent', f'Containment cannot be negative: {containment}%', containment)
            except (ValueError, TypeError):
                pass
        
        # Validate fire name
        if 'fire_name' in record and record['fire_name']:
            fire_name = str(record['fire_name']).strip()
            if len(fire_name) < 2:
                result.add_warning('fire_name', f'Fire name seems too short: "{fire_name}"')
    
    async def _validate_california_relevance(self, record: Dict[str, Any], result: ValidationResult):
        """Validate that data is relevant to California wildfires"""
        
        # Check if coordinates are in California
        lat_fields = ['latitude', 'lat']
        lon_fields = ['longitude', 'lon', 'long']
        
        latitude = None
        longitude = None
        
        for field in lat_fields:
            if field in record and record[field] is not None:
                try:
                    latitude = float(record[field])
                    break
                except (ValueError, TypeError):
                    pass
        
        for field in lon_fields:
            if field in record and record[field] is not None:
                try:
                    longitude = float(record[field])
                    break
                except (ValueError, TypeError):
                    pass
        
        if latitude is not None and longitude is not None:
            in_california = (
                self.california_bounds['min_lat'] <= latitude <= self.california_bounds['max_lat'] and
                self.california_bounds['min_lon'] <= longitude <= self.california_bounds['max_lon']
            )
            
            if not in_california:
                # Check if it's close to California (might be relevant)
                lat_buffer = 1.0  # 1 degree buffer
                lon_buffer = 1.0
                
                near_california = (
                    (self.california_bounds['min_lat'] - lat_buffer) <= latitude <= (self.california_bounds['max_lat'] + lat_buffer) and
                    (self.california_bounds['min_lon'] - lon_buffer) <= longitude <= (self.california_bounds['max_lon'] + lon_buffer)
                )
                
                if near_california:
                    result.add_warning(
                        'location', 
                        f'Data point near but outside California: ({latitude:.3f}, {longitude:.3f})'
                    )
                else:
                    result.add_warning(
                        'location',
                        f'Data point far from California: ({latitude:.3f}, {longitude:.3f}) - may not be relevant for wildfire monitoring'
                    )
    
    def _parse_timestamp(self, timestamp_str: Union[str, datetime, int, float]) -> datetime:
        """Parse various timestamp formats"""
        if isinstance(timestamp_str, datetime):
            return timestamp_str.replace(tzinfo=timezone.utc) if timestamp_str.tzinfo is None else timestamp_str
        
        if isinstance(timestamp_str, (int, float)):
            return datetime.fromtimestamp(timestamp_str, tz=timezone.utc)
        
        if not isinstance(timestamp_str, str):
            raise ValueError(f"Timestamp must be string, datetime, or number, got {type(timestamp_str)}")
        
        # Try common formats
        formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M:%SZ',
            '%Y-%m-%dT%H:%M:%S.%fZ',
            '%Y-%m-%d',
            '%Y%m%d_%H%M%S',
            '%Y%m%d %H:%M:%S',
            '%Y/%m/%d %H:%M:%S'
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(timestamp_str, fmt).replace(tzinfo=timezone.utc)
            except ValueError:
                continue
        
        # Try parsing as Unix timestamp
        try:
            return datetime.fromtimestamp(float(timestamp_str), tz=timezone.utc)
        except (ValueError, TypeError):
            pass
        
        raise ValueError(f"Unable to parse timestamp: {timestamp_str}")
    
    def _infer_source_type_from_filename(self, filename: str) -> str:
        """Infer data source type from filename"""
        if not filename:
            return 'unknown'
        
        filename_lower = filename.lower()
        
        # Satellite data patterns
        if any(sat in filename_lower for sat in ['modis', 'viirs', 'landsat', 'sentinel', 'firms']):
            return 'satellite'
        
        # Weather data patterns
        if any(weather in filename_lower for weather in ['gfs', 'weather', 'nws', 'era5', 'grib']):
            return 'weather'
        
        # Fire incident patterns
        if any(fire in filename_lower for fire in ['fire', 'incident', 'wildfire', 'calfire']):
            return 'fire_incident'
        
        # IoT sensor patterns
        if any(iot in filename_lower for iot in ['sensor', 'iot', 'mqtt', 'air_quality', 'pm25']):
            return 'iot_sensor'
        
        return 'unknown'
    
    async def get_quality_metrics(self) -> Dict[str, Any]:
        """Get validation quality metrics"""
        # This would typically track validation statistics over time
        # For now, return basic metrics
        return {
            "validation_engine": "wildfire_intelligence_validator",
            "version": "1.0.0",
            "supported_source_types": list(self.validation_rules.keys()),
            "california_bounds": self.california_bounds,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }