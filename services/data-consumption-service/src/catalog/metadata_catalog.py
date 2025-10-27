"""
Metadata Catalog and Data Integration Pipelines for Challenge 3
CAL FIRE Wildfire Intelligence Platform

This module implements the metadata catalog and data integration pipelines
as required by Challenge 3 specifications for backend processing deliverables.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field, asdict
from enum import Enum
import json
import uuid
import hashlib
from pathlib import Path


class DataSource(Enum):
    """Available data sources in the system"""
    NASA_FIRMS = "nasa_firms"
    NOAA_WEATHER = "noaa_weather"
    USGS_LANDSAT = "usgs_landsat"
    SENTINEL_SAR = "sentinel_sar"
    CAL_FIRE_INCIDENTS = "calfire_incidents"
    WEATHER_STATIONS = "weather_stations"
    SENSOR_NETWORK = "sensor_network"
    EXTERNAL_API = "external_api"


class DataType(Enum):
    """Data type classifications"""
    GEOSPATIAL = "geospatial"
    TIME_SERIES = "time_series"
    TABULAR = "tabular"
    IMAGERY = "imagery"
    STREAMING = "streaming"
    BATCH = "batch"
    DOCUMENT = "document"


class DataFormat(Enum):
    """Supported data formats"""
    JSON = "json"
    CSV = "csv"
    PARQUET = "parquet"
    GEOTIFF = "geotiff"
    SHAPEFILE = "shapefile"
    NETCDF = "netcdf"
    HDF5 = "hdf5"
    XML = "xml"
    AVRO = "avro"


class UpdateFrequency(Enum):
    """Data update frequencies"""
    REAL_TIME = "real_time"
    MINUTELY = "minutely"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"
    IRREGULAR = "irregular"


@dataclass
class DataSchema:
    """Schema definition for a dataset"""
    schema_id: str
    fields: List[Dict[str, Any]]
    primary_key: Optional[str] = None
    foreign_keys: List[Dict[str, str]] = field(default_factory=list)
    indexes: List[str] = field(default_factory=list)
    constraints: List[Dict[str, Any]] = field(default_factory=list)
    version: str = "1.0"
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class DataLineage:
    """Data lineage information"""
    lineage_id: str
    source_datasets: List[str]
    transformation_steps: List[Dict[str, Any]]
    target_datasets: List[str]
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = "system"


@dataclass
class QualityMetrics:
    """Data quality metrics"""
    completeness: float  # 0-100%
    accuracy: float  # 0-100%
    consistency: float  # 0-100%
    timeliness: float  # 0-100%
    validity: float  # 0-100%
    uniqueness: float  # 0-100%
    overall_score: float = 0.0
    last_assessed: datetime = field(default_factory=datetime.utcnow)
    issues_found: List[str] = field(default_factory=list)

    def __post_init__(self):
        # Calculate overall quality score
        metrics = [self.completeness, self.accuracy, self.consistency,
                  self.timeliness, self.validity, self.uniqueness]
        self.overall_score = sum(metrics) / len(metrics)


@dataclass
class DatasetMetadata:
    """Comprehensive dataset metadata"""
    dataset_id: str
    name: str
    description: str
    source: DataSource
    data_type: DataType
    format: DataFormat
    schema: DataSchema
    location: str  # Storage location/path
    size_bytes: int = 0
    record_count: int = 0
    update_frequency: UpdateFrequency = UpdateFrequency.DAILY
    last_updated: datetime = field(default_factory=datetime.utcnow)
    created_at: datetime = field(default_factory=datetime.utcnow)
    tags: Set[str] = field(default_factory=set)
    owner: str = "system"
    access_level: str = "internal"
    retention_period_days: int = 365
    quality_metrics: Optional[QualityMetrics] = None
    lineage: Optional[DataLineage] = None
    usage_stats: Dict[str, Any] = field(default_factory=dict)
    is_active: bool = True


@dataclass
class TransformationRule:
    """Data transformation rule definition"""
    rule_id: str
    name: str
    description: str
    source_dataset: str
    target_dataset: str
    transformation_type: str  # filter, aggregate, join, enrich, etc.
    logic: Dict[str, Any]  # Transformation logic configuration
    schedule: str = "0 */1 * * *"  # Cron expression
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_executed: Optional[datetime] = None
    execution_count: int = 0
    success_count: int = 0


@dataclass
class PipelineExecution:
    """Pipeline execution record"""
    execution_id: str
    pipeline_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: str = "running"  # running, completed, failed
    records_processed: int = 0
    errors: List[str] = field(default_factory=list)
    execution_time_seconds: Optional[float] = None
    resource_usage: Dict[str, Any] = field(default_factory=dict)


class MetadataCatalog:
    """Central metadata catalog for all datasets"""

    def __init__(self):
        self.datasets: Dict[str, DatasetMetadata] = {}
        self.schemas: Dict[str, DataSchema] = {}
        self.lineages: Dict[str, DataLineage] = {}
        self.catalog_stats = {
            "total_datasets": 0,
            "total_size_gb": 0.0,
            "last_updated": datetime.utcnow()
        }

        self._initialize_sample_datasets()

    def _initialize_sample_datasets(self):
        """Initialize with sample dataset metadata"""

        # NASA FIRMS Fire Data
        firms_schema = DataSchema(
            schema_id="firms_fire_schema_v1",
            fields=[
                {"name": "latitude", "type": "float", "nullable": False, "description": "Fire latitude"},
                {"name": "longitude", "type": "float", "nullable": False, "description": "Fire longitude"},
                {"name": "brightness", "type": "float", "nullable": True, "description": "Fire brightness temperature"},
                {"name": "scan", "type": "float", "nullable": True, "description": "Pixel scan angle"},
                {"name": "track", "type": "float", "nullable": True, "description": "Pixel track angle"},
                {"name": "acq_date", "type": "date", "nullable": False, "description": "Acquisition date"},
                {"name": "acq_time", "type": "string", "nullable": False, "description": "Acquisition time (HHMM)"},
                {"name": "satellite", "type": "string", "nullable": False, "description": "Satellite identifier"},
                {"name": "instrument", "type": "string", "nullable": False, "description": "Instrument name"},
                {"name": "confidence", "type": "int", "nullable": True, "description": "Detection confidence"},
                {"name": "version", "type": "string", "nullable": True, "description": "Data version"},
                {"name": "bright_t31", "type": "float", "nullable": True, "description": "Brightness T31"},
                {"name": "frp", "type": "float", "nullable": True, "description": "Fire radiative power"}
            ],
            primary_key="latitude,longitude,acq_date,acq_time",
            indexes=["acq_date", "satellite", "confidence"]
        )

        firms_quality = QualityMetrics(
            completeness=95.2,
            accuracy=88.7,
            consistency=92.1,
            timeliness=96.8,
            validity=94.3,
            uniqueness=87.5,
            issues_found=["Some duplicate records", "Missing FRP values for older data"]
        )

        firms_metadata = DatasetMetadata(
            dataset_id="nasa_firms_fire_data",
            name="NASA FIRMS Fire Detection Data",
            description="Real-time fire detection data from NASA FIRMS using MODIS and VIIRS satellites",
            source=DataSource.NASA_FIRMS,
            data_type=DataType.GEOSPATIAL,
            format=DataFormat.JSON,
            schema=firms_schema,
            location="kafka://fire_detection_topic",
            size_bytes=2_500_000_000,  # 2.5GB
            record_count=1_250_000,
            update_frequency=UpdateFrequency.REAL_TIME,
            tags={"fire", "satellite", "real-time", "geospatial", "nasa"},
            owner="data_ingestion_service",
            quality_metrics=firms_quality,
            usage_stats={
                "daily_queries": 450,
                "avg_response_time_ms": 234,
                "top_users": ["fire_chief_001", "analyst_002", "data_scientist_001"]
            }
        )

        # NOAA Weather Data
        weather_schema = DataSchema(
            schema_id="noaa_weather_schema_v1",
            fields=[
                {"name": "station_id", "type": "string", "nullable": False, "description": "Weather station ID"},
                {"name": "timestamp", "type": "timestamp", "nullable": False, "description": "Observation time"},
                {"name": "temperature_f", "type": "float", "nullable": True, "description": "Temperature in Fahrenheit"},
                {"name": "humidity", "type": "float", "nullable": True, "description": "Relative humidity %"},
                {"name": "wind_speed_mph", "type": "float", "nullable": True, "description": "Wind speed in MPH"},
                {"name": "wind_direction", "type": "float", "nullable": True, "description": "Wind direction degrees"},
                {"name": "precipitation", "type": "float", "nullable": True, "description": "Precipitation inches"},
                {"name": "pressure", "type": "float", "nullable": True, "description": "Atmospheric pressure"},
                {"name": "visibility", "type": "float", "nullable": True, "description": "Visibility miles"},
                {"name": "conditions", "type": "string", "nullable": True, "description": "Weather conditions"},
                {"name": "latitude", "type": "float", "nullable": False, "description": "Station latitude"},
                {"name": "longitude", "type": "float", "nullable": False, "description": "Station longitude"}
            ],
            primary_key="station_id,timestamp",
            indexes=["timestamp", "station_id"]
        )

        weather_quality = QualityMetrics(
            completeness=92.8,
            accuracy=96.2,
            consistency=94.7,
            timeliness=98.1,
            validity=95.9,
            uniqueness=99.2,
            issues_found=["Occasional sensor outages", "Some stations report intermittently"]
        )

        weather_metadata = DatasetMetadata(
            dataset_id="noaa_weather_observations",
            name="NOAA Weather Station Observations",
            description="Real-time weather observations from NOAA weather stations across California",
            source=DataSource.NOAA_WEATHER,
            data_type=DataType.TIME_SERIES,
            format=DataFormat.JSON,
            schema=weather_schema,
            location="kafka://weather_data_topic",
            size_bytes=1_800_000_000,  # 1.8GB
            record_count=3_600_000,
            update_frequency=UpdateFrequency.HOURLY,
            tags={"weather", "noaa", "real-time", "time-series"},
            owner="data_ingestion_service",
            quality_metrics=weather_quality
        )

        # CAL FIRE Incidents
        incident_schema = DataSchema(
            schema_id="calfire_incident_schema_v1",
            fields=[
                {"name": "incident_id", "type": "string", "nullable": False, "description": "Unique incident ID"},
                {"name": "incident_name", "type": "string", "nullable": False, "description": "Fire incident name"},
                {"name": "county", "type": "string", "nullable": True, "description": "County location"},
                {"name": "acres_burned", "type": "float", "nullable": True, "description": "Total acres burned"},
                {"name": "percent_contained", "type": "float", "nullable": True, "description": "Containment percentage"},
                {"name": "start_date", "type": "date", "nullable": True, "description": "Fire start date"},
                {"name": "latitude", "type": "float", "nullable": True, "description": "Incident latitude"},
                {"name": "longitude", "type": "float", "nullable": True, "description": "Incident longitude"},
                {"name": "cause", "type": "string", "nullable": True, "description": "Fire cause"},
                {"name": "structures_destroyed", "type": "int", "nullable": True, "description": "Structures destroyed"},
                {"name": "fatalities", "type": "int", "nullable": True, "description": "Number of fatalities"},
                {"name": "injuries", "type": "int", "nullable": True, "description": "Number of injuries"},
                {"name": "cooperating_agencies", "type": "string", "nullable": True, "description": "Cooperating agencies"},
                {"name": "last_updated", "type": "timestamp", "nullable": False, "description": "Last update time"}
            ],
            primary_key="incident_id",
            indexes=["start_date", "county", "acres_burned"]
        )

        incident_quality = QualityMetrics(
            completeness=88.5,
            accuracy=94.3,
            consistency=91.2,
            timeliness=85.7,
            validity=96.1,
            uniqueness=99.8,
            issues_found=["Some historical records incomplete", "Manual data entry delays"]
        )

        incident_metadata = DatasetMetadata(
            dataset_id="calfire_incidents",
            name="CAL FIRE Incident Data",
            description="Historical and current fire incidents tracked by CAL FIRE",
            source=DataSource.CAL_FIRE_INCIDENTS,
            data_type=DataType.TABULAR,
            format=DataFormat.JSON,
            schema=incident_schema,
            location="postgres://wildfiredb/incidents",
            size_bytes=450_000_000,  # 450MB
            record_count=25_000,
            update_frequency=UpdateFrequency.DAILY,
            tags={"calfire", "incidents", "historical", "official"},
            owner="fire_operations_team",
            quality_metrics=incident_quality
        )

        # Store datasets in catalog
        self.register_dataset(firms_metadata)
        self.register_dataset(weather_metadata)
        self.register_dataset(incident_metadata)

        # Create sample data lineage
        self._create_sample_lineage()

    def _create_sample_lineage(self):
        """Create sample data lineage relationships"""
        # Fire risk assessment lineage
        fire_risk_lineage = DataLineage(
            lineage_id="fire_risk_assessment_lineage",
            source_datasets=["nasa_firms_fire_data", "noaa_weather_observations", "calfire_incidents"],
            transformation_steps=[
                {
                    "step": 1,
                    "operation": "spatial_join",
                    "description": "Join weather data to fire locations within 10km radius"
                },
                {
                    "step": 2,
                    "operation": "temporal_aggregation",
                    "description": "Aggregate weather conditions for 24-hour periods"
                },
                {
                    "step": 3,
                    "operation": "risk_calculation",
                    "description": "Calculate fire risk score using ML model"
                }
            ],
            target_datasets=["fire_risk_assessment", "risk_prediction_model"],
            created_by="data_scientist_001"
        )

        self.lineages[fire_risk_lineage.lineage_id] = fire_risk_lineage

    def register_dataset(self, metadata: DatasetMetadata) -> bool:
        """Register a new dataset in the catalog"""
        try:
            # Store dataset metadata
            self.datasets[metadata.dataset_id] = metadata

            # Store schema separately for reuse
            self.schemas[metadata.schema.schema_id] = metadata.schema

            # Update catalog statistics
            self._update_catalog_stats()

            print(f"📊 Dataset registered: {metadata.name} ({metadata.dataset_id})")
            return True

        except Exception as e:
            print(f"❌ Failed to register dataset {metadata.dataset_id}: {str(e)}")
            return False

    def update_dataset(self, dataset_id: str, updates: Dict[str, Any]) -> bool:
        """Update existing dataset metadata"""
        if dataset_id not in self.datasets:
            return False

        try:
            dataset = self.datasets[dataset_id]
            for key, value in updates.items():
                if hasattr(dataset, key):
                    setattr(dataset, key, value)

            dataset.last_updated = datetime.utcnow()
            self._update_catalog_stats()
            return True

        except Exception as e:
            print(f"❌ Failed to update dataset {dataset_id}: {str(e)}")
            return False

    def search_datasets(self, query: Optional[str] = None, tags: Optional[Set[str]] = None,
                       source: Optional[DataSource] = None, data_type: Optional[DataType] = None) -> List[DatasetMetadata]:
        """Search datasets by various criteria"""
        results = []

        for dataset in self.datasets.values():
            # Text query search
            if query:
                query_lower = query.lower()
                if not (query_lower in dataset.name.lower() or
                       query_lower in dataset.description.lower()):
                    continue

            # Tag filter
            if tags:
                if not tags.intersection(dataset.tags):
                    continue

            # Source filter
            if source and dataset.source != source:
                continue

            # Data type filter
            if data_type and dataset.data_type != data_type:
                continue

            results.append(dataset)

        return sorted(results, key=lambda d: d.last_updated, reverse=True)

    def get_dataset_lineage(self, dataset_id: str) -> List[DataLineage]:
        """Get lineage information for a dataset"""
        lineages = []
        for lineage in self.lineages.values():
            if (dataset_id in lineage.source_datasets or
                dataset_id in lineage.target_datasets):
                lineages.append(lineage)
        return lineages

    def get_usage_statistics(self, dataset_id: str, days: int = 30) -> Dict[str, Any]:
        """Get usage statistics for a dataset"""
        if dataset_id not in self.datasets:
            return {}

        dataset = self.datasets[dataset_id]

        # Simulate usage statistics
        return {
            "dataset_id": dataset_id,
            "period_days": days,
            "total_queries": dataset.usage_stats.get("daily_queries", 0) * days,
            "unique_users": len(dataset.usage_stats.get("top_users", [])),
            "avg_response_time_ms": dataset.usage_stats.get("avg_response_time_ms", 0),
            "data_exported_gb": dataset.size_bytes / (1024**3) * 0.1,  # Estimate
            "quality_score": dataset.quality_metrics.overall_score if dataset.quality_metrics else 0,
            "last_accessed": dataset.last_updated
        }

    def _update_catalog_stats(self):
        """Update catalog-wide statistics"""
        total_size = sum(d.size_bytes for d in self.datasets.values())
        self.catalog_stats.update({
            "total_datasets": len(self.datasets),
            "total_size_gb": total_size / (1024**3),
            "last_updated": datetime.utcnow(),
            "active_datasets": len([d for d in self.datasets.values() if d.is_active]),
            "sources": len(set(d.source for d in self.datasets.values())),
            "avg_quality_score": sum(d.quality_metrics.overall_score for d in self.datasets.values()
                                   if d.quality_metrics) / len(self.datasets)
        })

    def generate_catalog_report(self) -> Dict[str, Any]:
        """Generate comprehensive catalog report"""
        datasets_by_source = {}
        datasets_by_type = {}
        quality_distribution = {"excellent": 0, "good": 0, "fair": 0, "poor": 0}

        for dataset in self.datasets.values():
            # By source
            source = dataset.source.value
            datasets_by_source[source] = datasets_by_source.get(source, 0) + 1

            # By type
            data_type = dataset.data_type.value
            datasets_by_type[data_type] = datasets_by_type.get(data_type, 0) + 1

            # Quality distribution
            if dataset.quality_metrics:
                score = dataset.quality_metrics.overall_score
                if score >= 90:
                    quality_distribution["excellent"] += 1
                elif score >= 75:
                    quality_distribution["good"] += 1
                elif score >= 60:
                    quality_distribution["fair"] += 1
                else:
                    quality_distribution["poor"] += 1

        return {
            "catalog_overview": self.catalog_stats,
            "datasets_by_source": datasets_by_source,
            "datasets_by_type": datasets_by_type,
            "quality_distribution": quality_distribution,
            "recent_updates": [
                {
                    "dataset_id": d.dataset_id,
                    "name": d.name,
                    "last_updated": d.last_updated.isoformat()
                }
                for d in sorted(self.datasets.values(), key=lambda x: x.last_updated, reverse=True)[:10]
            ],
            "top_datasets_by_size": [
                {
                    "dataset_id": d.dataset_id,
                    "name": d.name,
                    "size_gb": d.size_bytes / (1024**3)
                }
                for d in sorted(self.datasets.values(), key=lambda x: x.size_bytes, reverse=True)[:10]
            ]
        }


class DataIntegrationPipeline:
    """Data integration and transformation pipeline manager"""

    def __init__(self, catalog: MetadataCatalog):
        self.catalog = catalog
        self.transformation_rules: Dict[str, TransformationRule] = {}
        self.pipeline_executions: List[PipelineExecution] = []
        self.active_pipelines: Dict[str, Dict[str, Any]] = {}

        self._initialize_sample_pipelines()

    def _initialize_sample_pipelines(self):
        """Initialize sample transformation pipelines"""

        # Fire-Weather Correlation Pipeline
        fire_weather_rule = TransformationRule(
            rule_id="fire_weather_correlation",
            name="Fire-Weather Data Correlation",
            description="Correlate fire detection data with weather conditions",
            source_dataset="nasa_firms_fire_data",
            target_dataset="fire_weather_correlation",
            transformation_type="spatial_temporal_join",
            logic={
                "spatial_buffer_km": 10,
                "temporal_window_hours": 3,
                "weather_fields": ["temperature_f", "humidity", "wind_speed_mph", "wind_direction"],
                "aggregation": "avg"
            },
            schedule="0 */2 * * *"  # Every 2 hours
        )

        # Risk Assessment Aggregation Pipeline
        risk_assessment_rule = TransformationRule(
            rule_id="daily_risk_assessment",
            name="Daily Fire Risk Assessment",
            description="Aggregate daily fire risk metrics by region",
            source_dataset="fire_weather_correlation",
            target_dataset="daily_fire_risk_assessment",
            transformation_type="aggregate",
            logic={
                "group_by": ["county", "date"],
                "aggregations": {
                    "avg_temperature": "avg(temperature_f)",
                    "min_humidity": "min(humidity)",
                    "max_wind_speed": "max(wind_speed_mph)",
                    "fire_count": "count(fire_id)",
                    "total_frp": "sum(frp)"
                },
                "filters": ["confidence >= 50"]
            },
            schedule="0 2 * * *"  # Daily at 2 AM
        )

        # Historical Trend Analysis Pipeline
        trend_analysis_rule = TransformationRule(
            rule_id="historical_trend_analysis",
            name="Historical Fire Trend Analysis",
            description="Analyze historical fire patterns and trends",
            source_dataset="calfire_incidents",
            target_dataset="fire_trend_analysis",
            transformation_type="time_series_analysis",
            logic={
                "time_grouping": "monthly",
                "metrics": ["total_fires", "avg_acres_burned", "avg_containment_time"],
                "trend_analysis": True,
                "seasonal_decomposition": True,
                "forecast_periods": 12
            },
            schedule="0 3 1 * *"  # Monthly on the 1st at 3 AM
        )

        self.transformation_rules[fire_weather_rule.rule_id] = fire_weather_rule
        self.transformation_rules[risk_assessment_rule.rule_id] = risk_assessment_rule
        self.transformation_rules[trend_analysis_rule.rule_id] = trend_analysis_rule

    async def execute_pipeline(self, rule_id: str) -> PipelineExecution:
        """Execute a transformation pipeline"""
        if rule_id not in self.transformation_rules:
            raise ValueError(f"Unknown transformation rule: {rule_id}")

        rule = self.transformation_rules[rule_id]
        execution = PipelineExecution(
            execution_id=str(uuid.uuid4()),
            pipeline_id=rule_id,
            started_at=datetime.utcnow()
        )

        try:
            print(f"🔄 Starting pipeline execution: {rule.name}")

            # Simulate pipeline execution
            await self._execute_transformation(rule, execution)

            execution.status = "completed"
            execution.completed_at = datetime.utcnow()
            execution.execution_time_seconds = (
                execution.completed_at - execution.started_at
            ).total_seconds()

            # Update rule statistics
            rule.last_executed = execution.completed_at
            rule.execution_count += 1
            rule.success_count += 1

            print(f"✅ Pipeline completed: {rule.name} ({execution.records_processed} records)")

        except Exception as e:
            execution.status = "failed"
            execution.completed_at = datetime.utcnow()
            execution.errors.append(str(e))

            print(f"❌ Pipeline failed: {rule.name} - {str(e)}")

        self.pipeline_executions.append(execution)
        return execution

    async def _execute_transformation(self, rule: TransformationRule, execution: PipelineExecution):
        """Execute the actual transformation logic"""

        # Simulate processing time based on transformation type
        processing_times = {
            "spatial_temporal_join": 15,
            "aggregate": 8,
            "time_series_analysis": 25,
            "enrich": 12,
            "filter": 5
        }

        processing_time = processing_times.get(rule.transformation_type, 10)

        # Simulate processing
        for i in range(processing_time):
            await asyncio.sleep(0.1)  # Simulate work
            execution.records_processed = int((i + 1) / processing_time * 10000)  # Simulate progress

        # Simulate resource usage
        execution.resource_usage = {
            "cpu_percent": 45.2,
            "memory_mb": 512,
            "disk_io_mb": 234,
            "network_io_mb": 89
        }

    def schedule_pipeline(self, rule_id: str, enabled: bool = True) -> bool:
        """Enable/disable scheduled execution of a pipeline"""
        if rule_id not in self.transformation_rules:
            return False

        self.transformation_rules[rule_id].is_active = enabled

        if enabled:
            self.active_pipelines[rule_id] = {
                "rule": self.transformation_rules[rule_id],
                "next_execution": self._calculate_next_execution(self.transformation_rules[rule_id]),
                "enabled": True
            }
        else:
            self.active_pipelines.pop(rule_id, None)

        return True

    def _calculate_next_execution(self, rule: TransformationRule) -> datetime:
        """Calculate next execution time based on cron schedule"""
        # Simplified calculation - in production would use proper cron parsing
        now = datetime.utcnow()

        if "*/2 * * *" in rule.schedule:  # Every 2 hours
            return now + timedelta(hours=2)
        elif "2 * * *" in rule.schedule:  # Daily at 2 AM
            return now + timedelta(days=1)
        elif "3 1 * *" in rule.schedule:  # Monthly
            return now + timedelta(days=30)
        else:
            return now + timedelta(hours=1)  # Default: hourly

    def get_pipeline_status(self, rule_id: str) -> Dict[str, Any]:
        """Get current status of a pipeline"""
        if rule_id not in self.transformation_rules:
            return {}

        rule = self.transformation_rules[rule_id]
        recent_executions = [
            e for e in self.pipeline_executions
            if e.pipeline_id == rule_id
        ][-5:]  # Last 5 executions

        success_rate = rule.success_count / rule.execution_count if rule.execution_count > 0 else 0

        return {
            "rule_id": rule_id,
            "name": rule.name,
            "is_active": rule.is_active,
            "last_executed": rule.last_executed.isoformat() if rule.last_executed else None,
            "execution_count": rule.execution_count,
            "success_rate": success_rate,
            "next_scheduled": self.active_pipelines.get(rule_id, {}).get("next_execution"),
            "recent_executions": [
                {
                    "execution_id": e.execution_id,
                    "started_at": e.started_at.isoformat(),
                    "status": e.status,
                    "records_processed": e.records_processed,
                    "execution_time_seconds": e.execution_time_seconds
                }
                for e in recent_executions
            ]
        }

    def get_integration_dashboard(self) -> Dict[str, Any]:
        """Get data integration dashboard information"""
        total_pipelines = len(self.transformation_rules)
        active_pipelines = len([r for r in self.transformation_rules.values() if r.is_active])
        total_executions = len(self.pipeline_executions)
        successful_executions = len([e for e in self.pipeline_executions if e.status == "completed"])

        success_rate = successful_executions / total_executions if total_executions > 0 else 0

        return {
            "pipeline_summary": {
                "total_pipelines": total_pipelines,
                "active_pipelines": active_pipelines,
                "total_executions": total_executions,
                "success_rate": success_rate
            },
            "recent_executions": [
                {
                    "execution_id": e.execution_id,
                    "pipeline_id": e.pipeline_id,
                    "status": e.status,
                    "started_at": e.started_at.isoformat(),
                    "records_processed": e.records_processed
                }
                for e in sorted(self.pipeline_executions, key=lambda x: x.started_at, reverse=True)[:10]
            ],
            "pipeline_performance": [
                {
                    "rule_id": rule_id,
                    "name": rule.name,
                    "execution_count": rule.execution_count,
                    "success_count": rule.success_count,
                    "last_executed": rule.last_executed.isoformat() if rule.last_executed else None
                }
                for rule_id, rule in self.transformation_rules.items()
            ]
        }


async def demo_metadata_catalog_and_pipelines():
    """Demonstrate the metadata catalog and integration pipelines"""
    print("📊 CAL FIRE Metadata Catalog and Data Integration Demo")
    print("=" * 60)

    # Initialize catalog
    catalog = MetadataCatalog()
    pipelines = DataIntegrationPipeline(catalog)

    # Demo 1: Catalog search and discovery
    print("\n🔍 Demo 1: Dataset Discovery")

    # Search by tag
    fire_datasets = catalog.search_datasets(tags={"fire"})
    print(f"✅ Found {len(fire_datasets)} fire-related datasets")

    # Search by source
    nasa_datasets = catalog.search_datasets(source=DataSource.NASA_FIRMS)
    print(f"✅ Found {len(nasa_datasets)} NASA FIRMS datasets")

    # Search by text
    weather_datasets = catalog.search_datasets(query="weather")
    print(f"✅ Found {len(weather_datasets)} weather-related datasets")

    # Demo 2: Dataset metadata and quality
    print("\n📈 Demo 2: Dataset Quality and Metadata")

    firms_dataset = catalog.datasets["nasa_firms_fire_data"]
    print(f"✅ Dataset: {firms_dataset.name}")
    print(f"   Size: {firms_dataset.size_bytes / (1024**3):.2f} GB")
    print(f"   Records: {firms_dataset.record_count:,}")
    print(f"   Quality Score: {firms_dataset.quality_metrics.overall_score:.1f}/100")
    print(f"   Schema Fields: {len(firms_dataset.schema.fields)}")

    # Demo 3: Usage statistics
    print("\n📊 Demo 3: Usage Statistics")

    usage_stats = catalog.get_usage_statistics("nasa_firms_fire_data", 30)
    print(f"✅ Usage Statistics (30 days):")
    print(f"   Total Queries: {usage_stats['total_queries']}")
    print(f"   Unique Users: {usage_stats['unique_users']}")
    print(f"   Avg Response Time: {usage_stats['avg_response_time_ms']}ms")

    # Demo 4: Data lineage
    print("\n🔄 Demo 4: Data Lineage")

    lineages = catalog.get_dataset_lineage("nasa_firms_fire_data")
    print(f"✅ Found {len(lineages)} lineage relationships")

    if lineages:
        lineage = lineages[0]
        print(f"   Lineage: {lineage.lineage_id}")
        print(f"   Sources: {', '.join(lineage.source_datasets)}")
        print(f"   Targets: {', '.join(lineage.target_datasets)}")
        print(f"   Steps: {len(lineage.transformation_steps)}")

    # Demo 5: Pipeline execution
    print("\n⚙️ Demo 5: Data Integration Pipelines")

    # Execute fire-weather correlation pipeline
    execution = await pipelines.execute_pipeline("fire_weather_correlation")
    print(f"✅ Pipeline Execution: {execution.execution_id}")
    print(f"   Status: {execution.status}")
    print(f"   Records Processed: {execution.records_processed:,}")
    print(f"   Execution Time: {execution.execution_time_seconds:.2f}s")

    # Execute risk assessment pipeline
    execution2 = await pipelines.execute_pipeline("daily_risk_assessment")
    print(f"✅ Pipeline Execution: {execution2.execution_id}")
    print(f"   Status: {execution2.status}")
    print(f"   Records Processed: {execution2.records_processed:,}")

    # Demo 6: Pipeline scheduling
    print("\n⏰ Demo 6: Pipeline Scheduling")

    # Enable scheduling for all pipelines
    for rule_id in pipelines.transformation_rules:
        pipelines.schedule_pipeline(rule_id, enabled=True)

    print(f"✅ Enabled scheduling for {len(pipelines.active_pipelines)} pipelines")

    # Show pipeline status
    for rule_id in list(pipelines.transformation_rules.keys())[:2]:
        status = pipelines.get_pipeline_status(rule_id)
        print(f"   Pipeline: {status['name']}")
        print(f"     Success Rate: {status['success_rate']:.1%}")
        print(f"     Executions: {status['execution_count']}")

    # Demo 7: Catalog reporting
    print("\n📋 Demo 7: Catalog Reporting")

    catalog_report = catalog.generate_catalog_report()
    print(f"✅ Catalog Overview:")
    print(f"   Total Datasets: {catalog_report['catalog_overview']['total_datasets']}")
    print(f"   Total Size: {catalog_report['catalog_overview']['total_size_gb']:.2f} GB")
    print(f"   Average Quality: {catalog_report['catalog_overview']['avg_quality_score']:.1f}/100")

    print(f"✅ Quality Distribution:")
    for quality, count in catalog_report['quality_distribution'].items():
        print(f"   {quality.title()}: {count} datasets")

    # Demo 8: Integration dashboard
    print("\n📈 Demo 8: Integration Dashboard")

    dashboard = pipelines.get_integration_dashboard()
    pipeline_summary = dashboard['pipeline_summary']
    print(f"✅ Pipeline Summary:")
    print(f"   Active Pipelines: {pipeline_summary['active_pipelines']}")
    print(f"   Total Executions: {pipeline_summary['total_executions']}")
    print(f"   Success Rate: {pipeline_summary['success_rate']:.1%}")

    print("\n🎯 Metadata Catalog and Integration Demo Completed!")
    print(f"📊 Catalog contains {len(catalog.datasets)} datasets")
    print(f"⚙️ {len(pipelines.transformation_rules)} integration pipelines configured")
    print(f"🔄 {len(pipelines.pipeline_executions)} pipeline executions recorded")


if __name__ == "__main__":
    asyncio.run(demo_metadata_catalog_and_pipelines())