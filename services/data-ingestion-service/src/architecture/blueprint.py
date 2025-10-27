"""
Challenge 1 Deliverable: Architectural Blueprint
Comprehensive architecture design for wildfire intelligence data ingestion system
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import json
from datetime import datetime

class IngestionMode(Enum):
    """Data ingestion operational modes"""
    BATCH = "batch"
    REAL_TIME = "real_time"
    STREAMING = "streaming"
    HYBRID = "hybrid"

class DataSourceType(Enum):
    """Supported data source types"""
    NASA_FIRMS = "nasa_firms"
    NOAA_WEATHER = "noaa_weather"
    IOT_SENSORS = "iot_sensors"
    SATELLITE_IMAGERY = "satellite_imagery"
    WEATHER_STATIONS = "weather_stations"
    FIRE_CAMERAS = "fire_cameras"

@dataclass
class DataSourceSpec:
    """Specification for a data source"""
    source_type: DataSourceType
    name: str
    description: str
    ingestion_modes: List[IngestionMode]
    data_format: str
    update_frequency: str
    expected_volume: str
    api_endpoint: Optional[str] = None
    authentication_required: bool = False
    geographic_coverage: str = "California"
    data_retention_days: int = 365

@dataclass
class IngestionPipeline:
    """Data ingestion pipeline specification"""
    pipeline_id: str
    name: str
    data_sources: List[DataSourceType]
    ingestion_mode: IngestionMode
    processing_steps: List[str]
    validation_rules: List[str]
    error_handling: str
    output_destination: str
    latency_target_ms: int
    throughput_target: str

class WildfireDataArchitecture:
    """Comprehensive architectural blueprint for wildfire data ingestion"""

    def __init__(self):
        self.data_sources = self._define_data_sources()
        self.ingestion_pipelines = self._define_ingestion_pipelines()
        self.system_components = self._define_system_components()

    def _define_data_sources(self) -> Dict[DataSourceType, DataSourceSpec]:
        """Define all supported data sources with specifications"""
        return {
            DataSourceType.NASA_FIRMS: DataSourceSpec(
                source_type=DataSourceType.NASA_FIRMS,
                name="NASA FIRMS Fire Detection",
                description="Near real-time fire detection data from MODIS and VIIRS satellites",
                ingestion_modes=[IngestionMode.REAL_TIME, IngestionMode.BATCH],
                data_format="CSV/JSON",
                update_frequency="Every 3-6 hours",
                expected_volume="1000-5000 records/day",
                api_endpoint="https://firms.modaps.eosdis.nasa.gov/api/",
                authentication_required=True,
                data_retention_days=90
            ),

            DataSourceType.NOAA_WEATHER: DataSourceSpec(
                source_type=DataSourceType.NOAA_WEATHER,
                name="NOAA Weather Data",
                description="Live-streaming weather observations from NOAA weather stations",
                ingestion_modes=[IngestionMode.STREAMING, IngestionMode.REAL_TIME],  # Default: STREAMING
                data_format="JSON/XML",
                update_frequency="Continuous streaming",
                expected_volume="2000-8000 records/hour",
                api_endpoint="https://api.weather.gov/",
                authentication_required=False,
                data_retention_days=365
            ),

            DataSourceType.IOT_SENSORS: DataSourceSpec(
                source_type=DataSourceType.IOT_SENSORS,
                name="IoT Environmental Sensors",
                description="Live-streaming environmental data from deployed IoT sensors",
                ingestion_modes=[IngestionMode.STREAMING, IngestionMode.REAL_TIME],  # Default: STREAMING
                data_format="JSON/MQTT",
                update_frequency="Continuous streaming (every 1-5 minutes)",
                expected_volume="50000+ records/day",
                authentication_required=True,
                data_retention_days=730
            ),

            DataSourceType.SATELLITE_IMAGERY: DataSourceSpec(
                source_type=DataSourceType.SATELLITE_IMAGERY,
                name="Satellite Imagery Metadata",
                description="Landsat, Sentinel, and MODIS satellite imagery metadata",
                ingestion_modes=[IngestionMode.BATCH, IngestionMode.REAL_TIME],
                data_format="JSON/GeoJSON",
                update_frequency="Daily",
                expected_volume="50-200 scenes/day",
                api_endpoint="https://earthexplorer.usgs.gov/",
                authentication_required=True,
                data_retention_days=365
            ),

            DataSourceType.WEATHER_STATIONS: DataSourceSpec(
                source_type=DataSourceType.WEATHER_STATIONS,
                name="Weather Station Networks",
                description="Data from RAWS and other weather station networks",
                ingestion_modes=[IngestionMode.REAL_TIME, IngestionMode.BATCH],
                data_format="JSON/CSV",
                update_frequency="Every 10-60 minutes",
                expected_volume="2000-8000 records/day",
                authentication_required=False,
                data_retention_days=365
            ),

            DataSourceType.FIRE_CAMERAS: DataSourceSpec(
                source_type=DataSourceType.FIRE_CAMERAS,
                name="Fire Detection Cameras",
                description="Automated fire detection from camera networks",
                ingestion_modes=[IngestionMode.STREAMING, IngestionMode.REAL_TIME],
                data_format="JSON/Image Metadata",
                update_frequency="Continuous",
                expected_volume="1000+ detections/day",
                authentication_required=True,
                data_retention_days=180
            )
        }

    def _define_ingestion_pipelines(self) -> List[IngestionPipeline]:
        """Define data ingestion pipelines"""
        return [
            IngestionPipeline(
                pipeline_id="fire_detection_realtime",
                name="Real-time Fire Detection Pipeline",
                data_sources=[DataSourceType.NASA_FIRMS, DataSourceType.FIRE_CAMERAS],
                ingestion_mode=IngestionMode.REAL_TIME,
                processing_steps=[
                    "Data validation and schema checking",
                    "Geographic bounds filtering (California)",
                    "Deduplication based on coordinates and timestamp",
                    "Confidence score validation",
                    "Format standardization"
                ],
                validation_rules=[
                    "Latitude: -90 to 90",
                    "Longitude: -180 to 180",
                    "Confidence: 0 to 100",
                    "Required fields: lat, lon, timestamp"
                ],
                error_handling="Retry with exponential backoff, dead letter queue",
                output_destination="Kafka Topic: fire-detections",
                latency_target_ms=5000,
                throughput_target="1000 records/minute"
            ),

            IngestionPipeline(
                pipeline_id="weather_streaming",
                name="Weather Data Streaming Pipeline",
                data_sources=[DataSourceType.NOAA_WEATHER, DataSourceType.WEATHER_STATIONS],
                ingestion_mode=IngestionMode.STREAMING,
                processing_steps=[
                    "Real-time data validation",
                    "Unit conversion and standardization",
                    "Geographic filtering",
                    "Data enrichment with calculated indices",
                    "Stream aggregation"
                ],
                validation_rules=[
                    "Temperature: -50 to 60 Celsius",
                    "Humidity: 0 to 100%",
                    "Wind speed: 0 to 200 m/s",
                    "Pressure: 800 to 1100 hPa"
                ],
                error_handling="Circuit breaker pattern, graceful degradation",
                output_destination="Kafka Topic: weather-stream",
                latency_target_ms=2000,
                throughput_target="500 records/minute"
            ),

            IngestionPipeline(
                pipeline_id="iot_sensor_stream",
                name="IoT Sensor Data Pipeline",
                data_sources=[DataSourceType.IOT_SENSORS],
                ingestion_mode=IngestionMode.STREAMING,
                processing_steps=[
                    "MQTT message processing",
                    "Device authentication verification",
                    "Sensor data validation",
                    "Anomaly detection",
                    "Data aggregation and buffering"
                ],
                validation_rules=[
                    "Sensor ID format validation",
                    "Battery level: 0 to 100%",
                    "Signal strength: -100 to 0 dBm",
                    "Environmental readings within expected ranges"
                ],
                error_handling="Message queuing, device offline handling",
                output_destination="Kafka Topic: iot-sensors",
                latency_target_ms=1000,
                throughput_target="2000 records/minute"
            ),

            IngestionPipeline(
                pipeline_id="satellite_batch",
                name="Satellite Data Batch Pipeline",
                data_sources=[DataSourceType.SATELLITE_IMAGERY],
                ingestion_mode=IngestionMode.BATCH,
                processing_steps=[
                    "Scene metadata extraction",
                    "Cloud cover filtering",
                    "Geographic relevance checking",
                    "Quality assessment",
                    "Catalog indexing"
                ],
                validation_rules=[
                    "Cloud cover < 30%",
                    "Image quality >= 7",
                    "Geographic intersection with California",
                    "Processing level validation"
                ],
                error_handling="Batch retry, partial success handling",
                output_destination="PostgreSQL: satellite_metadata",
                latency_target_ms=60000,
                throughput_target="100 scenes/hour"
            )
        ]

    def _define_system_components(self) -> Dict[str, Dict[str, Any]]:
        """Define system architecture components"""
        return {
            "data_ingestion_layer": {
                "connectors": [
                    "NASA FIRMS Connector",
                    "NOAA Weather Connector",
                    "IoT MQTT Connector",
                    "Satellite API Connector",
                    "Fire Camera Connector"
                ],
                "protocols": ["HTTP/HTTPS", "MQTT", "WebSocket", "FTP"],
                "authentication": ["API Keys", "OAuth 2.0", "Certificate-based"]
            },

            "stream_processing": {
                "kafka_clusters": {
                    "primary_cluster": {
                        "topics": ["fire-detections", "weather-stream", "iot-sensors", "satellite-metadata"],
                        "partitions": 12,
                        "replication_factor": 3,
                        "retention_ms": 604800000  # 7 days
                    }
                },
                "processing_frameworks": ["Kafka Streams", "Apache Flink"],
                "serialization": ["JSON", "Avro", "Protobuf"]
            },

            "validation_framework": {
                "schema_validation": "JSON Schema + Custom validators",
                "data_quality_checks": [
                    "Completeness validation",
                    "Format validation",
                    "Range validation",
                    "Business rule validation"
                ],
                "error_handling": [
                    "Retry mechanisms",
                    "Dead letter queues",
                    "Circuit breakers",
                    "Fallback strategies"
                ]
            },

            "monitoring_observability": {
                "metrics_collection": "Prometheus + Custom metrics",
                "logging": "Structured logging with correlation IDs",
                "tracing": "Distributed tracing for request flows",
                "alerting": "Alert manager with PagerDuty integration",
                "dashboards": "Grafana dashboards for real-time monitoring"
            },

            "storage_layer": {
                "operational_database": "PostgreSQL with TimescaleDB",
                "message_broker": "Apache Kafka",
                "cache_layer": "Redis for session management",
                "file_storage": "MinIO for large file handling"
            }
        }

    def get_architecture_summary(self) -> Dict[str, Any]:
        """Generate comprehensive architecture summary"""
        return {
            "architecture_overview": {
                "total_data_sources": len(self.data_sources),
                "supported_ingestion_modes": [mode.value for mode in IngestionMode],
                "total_pipelines": len(self.ingestion_pipelines),
                "geographic_focus": "California wildfire zones"
            },
            "data_sources": {
                source_type.value: asdict(spec)
                for source_type, spec in self.data_sources.items()
            },
            "ingestion_pipelines": [asdict(pipeline) for pipeline in self.ingestion_pipelines],
            "system_components": self.system_components,
            "performance_targets": {
                "total_daily_volume": "50,000+ records/day",
                "peak_throughput": "5,000 records/minute",
                "availability_target": "99.9%",
                "latency_targets": {
                    "real_time": "< 5 seconds",
                    "streaming": "< 2 seconds",
                    "batch": "< 60 seconds"
                }
            },
            "compliance_security": {
                "data_encryption": "In-transit and at-rest",
                "access_control": "Role-based access control (RBAC)",
                "audit_logging": "Comprehensive audit trails",
                "data_retention": "Configurable per data source",
                "privacy_protection": "PII detection and handling"
            },
            "scalability_resilience": {
                "horizontal_scaling": "Kubernetes-based auto-scaling",
                "fault_tolerance": "Multi-AZ deployment with failover",
                "disaster_recovery": "Cross-region backup and replication",
                "load_balancing": "Application and database load balancing"
            }
        }

    def export_blueprint(self, filepath: str):
        """Export architectural blueprint to JSON file"""
        blueprint = {
            "wildfire_data_ingestion_architecture": self.get_architecture_summary(),
            "generated_at": datetime.now().isoformat(),
            "version": "1.0.0",
            "challenge": "CAL FIRE Challenge 1 - Data Sources and Ingestion Mechanisms"
        }

        with open(filepath, 'w') as f:
            json.dump(blueprint, f, indent=2, default=str)

        print(f"🏗️ Architectural blueprint exported to: {filepath}")

# Global architecture instance
architecture = WildfireDataArchitecture()

def get_architecture() -> WildfireDataArchitecture:
    """Get the global architecture instance"""
    return architecture