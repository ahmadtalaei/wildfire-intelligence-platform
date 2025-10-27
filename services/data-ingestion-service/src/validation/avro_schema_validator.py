"""
Avro Schema Validation for Wildfire Intelligence Platform

Enforces strict schema validation for streaming data using Apache Avro.
Provides schema evolution support and compatibility checking.
"""

import io
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import json

try:
    import avro.schema
    import avro.io
    from avro.datafile import DataFileWriter, DataFileReader
except ImportError:
    avro = None

logger = logging.getLogger(__name__)


class AvroSchemaValidator:
    """Validates streaming data against Avro schemas with schema evolution support"""

    def __init__(self):
        self.schemas = self._load_schemas()
        self.parsed_schemas = {}

        if avro:
            for source_type, schema_def in self.schemas.items():
                try:
                    self.parsed_schemas[source_type] = avro.schema.parse(json.dumps(schema_def))
                except Exception as e:
                    logger.error(f"Failed to parse Avro schema for {source_type}: {e}")

    def _load_schemas(self) -> Dict[str, Dict]:
        """Load Avro schemas for all data sources"""
        return {
            "fire_detection": {
                "type": "record",
                "name": "FireDetection",
                "namespace": "com.wildfire.streaming",
                "fields": [
                    {"name": "detection_id", "type": "string"},
                    {"name": "latitude", "type": "double"},
                    {"name": "longitude", "type": "double"},
                    {"name": "timestamp", "type": "long", "logicalType": "timestamp-millis"},
                    {"name": "confidence", "type": ["null", "int"], "default": None},
                    {"name": "brightness", "type": ["null", "double"], "default": None},
                    {"name": "frp", "type": ["null", "double"], "default": None},
                    {"name": "satellite", "type": "string"},
                    {"name": "sensor", "type": ["null", "string"], "default": None},
                    {"name": "scan_track", "type": ["null", "double"], "default": None},
                    {"name": "acq_date", "type": "string"},
                    {"name": "acq_time", "type": "string"},
                    {"name": "bright_t31", "type": ["null", "double"], "default": None},
                    {"name": "daynight", "type": "string"},
                    {"name": "version", "type": ["null", "string"], "default": None}
                ]
            },

            "weather_observation": {
                "type": "record",
                "name": "WeatherObservation",
                "namespace": "com.wildfire.streaming",
                "fields": [
                    {"name": "observation_id", "type": "string"},
                    {"name": "station_id", "type": ["null", "string"], "default": None},
                    {"name": "latitude", "type": "double"},
                    {"name": "longitude", "type": "double"},
                    {"name": "timestamp", "type": "long", "logicalType": "timestamp-millis"},
                    {"name": "temperature", "type": ["null", "double"], "default": None},
                    {"name": "relative_humidity", "type": ["null", "double"], "default": None},
                    {"name": "wind_speed", "type": ["null", "double"], "default": None},
                    {"name": "wind_direction", "type": ["null", "double"], "default": None},
                    {"name": "pressure", "type": ["null", "double"], "default": None},
                    {"name": "precipitation", "type": ["null", "double"], "default": None},
                    {"name": "visibility", "type": ["null", "double"], "default": None},
                    {"name": "cloud_cover", "type": ["null", "int"], "default": None},
                    {"name": "dewpoint", "type": ["null", "double"], "default": None}
                ]
            },

            "iot_sensor_reading": {
                "type": "record",
                "name": "IoTSensorReading",
                "namespace": "com.wildfire.streaming",
                "fields": [
                    {"name": "reading_id", "type": "string"},
                    {"name": "sensor_id", "type": "string"},
                    {"name": "sensor_type", "type": "string"},
                    {"name": "latitude", "type": ["null", "double"], "default": None},
                    {"name": "longitude", "type": ["null", "double"], "default": None},
                    {"name": "timestamp", "type": "long", "logicalType": "timestamp-millis"},
                    {"name": "pm25", "type": ["null", "double"], "default": None},
                    {"name": "pm10", "type": ["null", "double"], "default": None},
                    {"name": "temperature", "type": ["null", "double"], "default": None},
                    {"name": "humidity", "type": ["null", "double"], "default": None},
                    {"name": "co2", "type": ["null", "double"], "default": None},
                    {"name": "co", "type": ["null", "double"], "default": None},
                    {"name": "battery_level", "type": ["null", "int"], "default": None},
                    {"name": "signal_strength", "type": ["null", "int"], "default": None}
                ]
            },

            "satellite_image_metadata": {
                "type": "record",
                "name": "SatelliteImageMetadata",
                "namespace": "com.wildfire.streaming",
                "fields": [
                    {"name": "scene_id", "type": "string"},
                    {"name": "satellite", "type": "string"},
                    {"name": "sensor", "type": "string"},
                    {"name": "acquisition_date", "type": "long", "logicalType": "timestamp-millis"},
                    {"name": "cloud_cover_percent", "type": ["null", "double"], "default": None},
                    {"name": "bbox_north", "type": "double"},
                    {"name": "bbox_south", "type": "double"},
                    {"name": "bbox_east", "type": "double"},
                    {"name": "bbox_west", "type": "double"},
                    {"name": "center_lat", "type": "double"},
                    {"name": "center_lon", "type": "double"},
                    {"name": "processing_level", "type": "string"},
                    {"name": "file_size_mb", "type": ["null", "double"], "default": None},
                    {"name": "file_format", "type": "string"},
                    {"name": "storage_path", "type": "string"},
                    {"name": "image_hash", "type": ["null", "string"], "default": None},
                    {"name": "has_fire_signature", "type": ["null", "boolean"], "default": None}
                ]
            }
        }

    async def validate(self, data: Dict[str, Any], source_type: str) -> Dict[str, Any]:
        """Validate data against Avro schema"""
        result = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "schema_version": "1.0"
        }

        if not avro:
            result["warnings"].append("Avro library not available - schema validation skipped")
            return result

        if source_type not in self.parsed_schemas:
            result["warnings"].append(f"No Avro schema defined for source_type: {source_type}")
            return result

        try:
            schema = self.parsed_schemas[source_type]

            # Validate record against schema
            datum_writer = avro.io.DatumWriter(schema)
            bytes_writer = io.BytesIO()
            encoder = avro.io.BinaryEncoder(bytes_writer)

            # Convert timestamp fields to milliseconds if they're datetime objects
            validated_data = self._prepare_data_for_avro(data, schema)

            # This will raise an exception if validation fails
            datum_writer.write(validated_data, encoder)

            logger.debug(f"Successfully validated {source_type} record against Avro schema")

        except avro.io.AvroTypeException as e:
            result["is_valid"] = False
            result["errors"].append(f"Schema validation failed: {str(e)}")
            logger.error(f"Avro validation error for {source_type}: {e}")

        except Exception as e:
            result["is_valid"] = False
            result["errors"].append(f"Validation error: {str(e)}")
            logger.error(f"Unexpected validation error for {source_type}: {e}")

        return result

    async def validate_batch(self, records: List[Dict[str, Any]], source_type: str) -> Dict[str, Any]:
        """Validate batch of records against schema"""
        results = {
            "total_records": len(records),
            "valid_records": 0,
            "invalid_records": 0,
            "errors": [],
            "validation_results": []
        }

        for i, record in enumerate(records):
            validation = await self.validate(record, source_type)
            results["validation_results"].append(validation)

            if validation["is_valid"]:
                results["valid_records"] += 1
            else:
                results["invalid_records"] += 1
                results["errors"].append({
                    "record_index": i,
                    "errors": validation["errors"]
                })

        results["validation_rate"] = results["valid_records"] / results["total_records"] if results["total_records"] > 0 else 0

        return results

    def _prepare_data_for_avro(self, data: Dict[str, Any], schema: Any) -> Dict[str, Any]:
        """Prepare data for Avro validation by converting types"""
        prepared = {}

        for field in schema.fields:
            field_name = field.name

            if field_name in data:
                value = data[field_name]

                # Convert datetime to timestamp-millis
                if field.type.props.get('logicalType') == 'timestamp-millis':
                    if isinstance(value, datetime):
                        prepared[field_name] = int(value.timestamp() * 1000)
                    elif isinstance(value, str):
                        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
                        prepared[field_name] = int(dt.timestamp() * 1000)
                    else:
                        prepared[field_name] = int(value)
                else:
                    prepared[field_name] = value
            else:
                # Use default value if field not present
                if hasattr(field, 'default'):
                    prepared[field_name] = field.default

        return prepared

    def serialize_to_avro(self, data: Dict[str, Any], source_type: str) -> Optional[bytes]:
        """Serialize data to Avro binary format"""
        if not avro or source_type not in self.parsed_schemas:
            return None

        try:
            schema = self.parsed_schemas[source_type]
            datum_writer = avro.io.DatumWriter(schema)
            bytes_writer = io.BytesIO()
            encoder = avro.io.BinaryEncoder(bytes_writer)

            prepared_data = self._prepare_data_for_avro(data, schema)
            datum_writer.write(prepared_data, encoder)

            return bytes_writer.getvalue()

        except Exception as e:
            logger.error(f"Failed to serialize to Avro: {e}")
            return None

    def deserialize_from_avro(self, avro_bytes: bytes, source_type: str) -> Optional[Dict[str, Any]]:
        """Deserialize Avro binary data to dict"""
        if not avro or source_type not in self.parsed_schemas:
            return None

        try:
            schema = self.parsed_schemas[source_type]
            bytes_reader = io.BytesIO(avro_bytes)
            decoder = avro.io.BinaryDecoder(bytes_reader)
            datum_reader = avro.io.DatumReader(schema)

            return datum_reader.read(decoder)

        except Exception as e:
            logger.error(f"Failed to deserialize from Avro: {e}")
            return None

    def get_schema(self, source_type: str) -> Optional[str]:
        """Get Avro schema as JSON string"""
        if source_type in self.schemas:
            return json.dumps(self.schemas[source_type], indent=2)
        return None

    async def check_schema_compatibility(self, new_schema: Dict, source_type: str) -> Dict[str, Any]:
        """Check if new schema is compatible with existing schema (for schema evolution)"""
        result = {
            "compatible": True,
            "compatibility_type": None,
            "issues": []
        }

        if not avro or source_type not in self.schemas:
            result["compatible"] = False
            result["issues"].append("Cannot check compatibility - schema not found")
            return result

        try:
            old_schema = self.schemas[source_type]

            # Check backward compatibility (new schema can read old data)
            # Check forward compatibility (old schema can read new data)

            old_fields = {f["name"]: f for f in old_schema["fields"]}
            new_fields = {f["name"]: f for f in new_schema["fields"]}

            # Check for removed required fields (breaks backward compatibility)
            for old_field_name, old_field in old_fields.items():
                if old_field_name not in new_fields:
                    if "default" not in old_field and old_field.get("type") not in ["null", ["null", "string"]]:
                        result["compatible"] = False
                        result["issues"].append(f"Required field '{old_field_name}' removed")

            # Check for new required fields without defaults (breaks forward compatibility)
            for new_field_name, new_field in new_fields.items():
                if new_field_name not in old_fields:
                    if "default" not in new_field and new_field.get("type") not in ["null", ["null", "string"]]:
                        result["issues"].append(f"New required field '{new_field_name}' added without default")

            if result["compatible"]:
                result["compatibility_type"] = "FULL"  # Both backward and forward compatible

        except Exception as e:
            result["compatible"] = False
            result["issues"].append(f"Compatibility check failed: {str(e)}")

        return result
