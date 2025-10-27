"""
Self-Service Data Access Portal for Challenge 3
CAL FIRE Wildfire Intelligence Platform

This module implements the self-service data access portal with query builder
functionality as required by Challenge 3 specifications.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import json
import uuid


class QueryType(Enum):
    """Types of queries supported by the portal"""
    FIRE_DATA = "fire_data"
    WEATHER_DATA = "weather_data"
    SATELLITE_DATA = "satellite_data"
    SENSOR_DATA = "sensor_data"
    COMBINED = "combined"


class FilterOperator(Enum):
    """Filter operators for query building"""
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    BETWEEN = "between"
    CONTAINS = "contains"
    IN_LIST = "in_list"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"


@dataclass
class QueryFilter:
    """Individual filter for query building"""
    field: str
    operator: FilterOperator
    value: Any
    data_type: str = "string"  # string, number, date, boolean


@dataclass
class QueryConfiguration:
    """Configuration for a data query"""
    query_id: str
    query_type: QueryType
    title: str
    description: str
    filters: List[QueryFilter]
    selected_fields: List[str]
    sort_fields: List[Dict[str, str]]  # [{"field": "name", "direction": "asc"}]
    limit: Optional[int] = 1000
    offset: int = 0
    time_range: Optional[Dict[str, datetime]] = None
    geographic_bounds: Optional[Dict[str, float]] = None  # lat_min, lat_max, lon_min, lon_max
    created_by: str = ""
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()


@dataclass
class SavedQuery:
    """Saved query template"""
    query_id: str
    name: str
    description: str
    configuration: QueryConfiguration
    user_id: str
    is_public: bool = False
    usage_count: int = 0
    created_at: datetime = None
    updated_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()


@dataclass
class DataExportRequest:
    """Data export request configuration"""
    export_id: str
    query_configuration: QueryConfiguration
    export_format: str  # csv, json, parquet, excel
    user_id: str
    email_notification: bool = True
    compression: bool = False
    status: str = "pending"  # pending, processing, completed, failed
    file_path: Optional[str] = None
    created_at: datetime = None
    completed_at: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()


class QueryBuilder:
    """Visual query builder for creating data queries"""

    def __init__(self):
        self.available_fields = self._initialize_field_catalog()

    def _initialize_field_catalog(self) -> Dict[QueryType, List[Dict[str, Any]]]:
        """Initialize the catalog of available fields for each data type"""
        return {
            QueryType.FIRE_DATA: [
                {"name": "fire_id", "type": "string", "description": "Unique fire identifier"},
                {"name": "incident_name", "type": "string", "description": "Fire incident name"},
                {"name": "latitude", "type": "number", "description": "Fire location latitude"},
                {"name": "longitude", "type": "number", "description": "Fire location longitude"},
                {"name": "brightness", "type": "number", "description": "Fire brightness temperature"},
                {"name": "confidence", "type": "number", "description": "Detection confidence level"},
                {"name": "detected_at", "type": "date", "description": "Fire detection timestamp"},
                {"name": "acres_burned", "type": "number", "description": "Total acres burned"},
                {"name": "containment_percent", "type": "number", "description": "Fire containment percentage"},
                {"name": "fire_cause", "type": "string", "description": "Cause of fire ignition"}
            ],
            QueryType.WEATHER_DATA: [
                {"name": "station_id", "type": "string", "description": "Weather station identifier"},
                {"name": "temperature", "type": "number", "description": "Temperature in Fahrenheit"},
                {"name": "humidity", "type": "number", "description": "Relative humidity percentage"},
                {"name": "wind_speed", "type": "number", "description": "Wind speed in mph"},
                {"name": "wind_direction", "type": "number", "description": "Wind direction in degrees"},
                {"name": "precipitation", "type": "number", "description": "Precipitation amount"},
                {"name": "pressure", "type": "number", "description": "Atmospheric pressure"},
                {"name": "recorded_at", "type": "date", "description": "Weather observation timestamp"},
                {"name": "latitude", "type": "number", "description": "Station latitude"},
                {"name": "longitude", "type": "number", "description": "Station longitude"}
            ],
            QueryType.SATELLITE_DATA: [
                {"name": "satellite_id", "type": "string", "description": "Satellite identifier"},
                {"name": "image_id", "type": "string", "description": "Satellite image identifier"},
                {"name": "acquisition_date", "type": "date", "description": "Image acquisition date"},
                {"name": "cloud_coverage", "type": "number", "description": "Cloud coverage percentage"},
                {"name": "spatial_resolution", "type": "number", "description": "Image spatial resolution"},
                {"name": "spectral_bands", "type": "string", "description": "Available spectral bands"},
                {"name": "scene_bounds", "type": "string", "description": "Geographic scene boundaries"},
                {"name": "processing_level", "type": "string", "description": "Data processing level"}
            ],
            QueryType.SENSOR_DATA: [
                {"name": "sensor_id", "type": "string", "description": "Sensor device identifier"},
                {"name": "sensor_type", "type": "string", "description": "Type of sensor"},
                {"name": "measurement_value", "type": "number", "description": "Sensor measurement value"},
                {"name": "measurement_unit", "type": "string", "description": "Unit of measurement"},
                {"name": "battery_level", "type": "number", "description": "Sensor battery level"},
                {"name": "signal_strength", "type": "number", "description": "Communication signal strength"},
                {"name": "timestamp", "type": "date", "description": "Measurement timestamp"},
                {"name": "latitude", "type": "number", "description": "Sensor latitude"},
                {"name": "longitude", "type": "number", "description": "Sensor longitude"}
            ]
        }

    def create_query(self, query_type: QueryType, title: str, description: str) -> QueryConfiguration:
        """Create a new query configuration"""
        query_id = str(uuid.uuid4())
        return QueryConfiguration(
            query_id=query_id,
            query_type=query_type,
            title=title,
            description=description,
            filters=[],
            selected_fields=[],
            sort_fields=[]
        )

    def add_filter(self, query: QueryConfiguration, field: str, operator: FilterOperator,
                   value: Any, data_type: str = "string") -> QueryConfiguration:
        """Add a filter to the query"""
        filter_obj = QueryFilter(
            field=field,
            operator=operator,
            value=value,
            data_type=data_type
        )
        query.filters.append(filter_obj)
        return query

    def set_fields(self, query: QueryConfiguration, fields: List[str]) -> QueryConfiguration:
        """Set the fields to be returned in the query results"""
        query.selected_fields = fields
        return query

    def set_time_range(self, query: QueryConfiguration, start_time: datetime,
                      end_time: datetime) -> QueryConfiguration:
        """Set the time range filter for the query"""
        query.time_range = {
            "start": start_time,
            "end": end_time
        }
        return query

    def set_geographic_bounds(self, query: QueryConfiguration, lat_min: float, lat_max: float,
                            lon_min: float, lon_max: float) -> QueryConfiguration:
        """Set geographic bounding box for the query"""
        query.geographic_bounds = {
            "lat_min": lat_min,
            "lat_max": lat_max,
            "lon_min": lon_min,
            "lon_max": lon_max
        }
        return query

    def validate_query(self, query: QueryConfiguration) -> Tuple[bool, List[str]]:
        """Validate query configuration"""
        errors = []

        # Check if fields are valid for the query type
        available_field_names = [f["name"] for f in self.available_fields.get(query.query_type, [])]
        for field in query.selected_fields:
            if field not in available_field_names:
                errors.append(f"Invalid field: {field} for query type {query.query_type.value}")

        # Validate filters
        for filter_obj in query.filters:
            if filter_obj.field not in available_field_names:
                errors.append(f"Invalid filter field: {filter_obj.field}")

        # Check required fields
        if not query.selected_fields:
            errors.append("At least one field must be selected")

        # Validate geographic bounds
        if query.geographic_bounds:
            bounds = query.geographic_bounds
            if bounds["lat_min"] >= bounds["lat_max"]:
                errors.append("Invalid latitude bounds")
            if bounds["lon_min"] >= bounds["lon_max"]:
                errors.append("Invalid longitude bounds")

        return len(errors) == 0, errors


class SelfServicePortal:
    """Main self-service data access portal"""

    def __init__(self):
        self.query_builder = QueryBuilder()
        self.saved_queries: Dict[str, SavedQuery] = {}
        self.export_requests: Dict[str, DataExportRequest] = {}
        self.query_history: List[Dict[str, Any]] = []

        # Initialize with sample saved queries
        self._initialize_sample_queries()

    def _initialize_sample_queries(self):
        """Initialize sample saved queries for demonstration"""
        # Fire perimeter query
        fire_query = self.query_builder.create_query(
            QueryType.FIRE_DATA,
            "Recent Large Fires",
            "Query for fires larger than 1000 acres in the last 30 days"
        )
        fire_query = self.query_builder.add_filter(
            fire_query, "acres_burned", FilterOperator.GREATER_THAN, 1000, "number"
        )
        fire_query = self.query_builder.set_time_range(
            fire_query,
            datetime.utcnow() - timedelta(days=30),
            datetime.utcnow()
        )
        fire_query = self.query_builder.set_fields(
            fire_query,
            ["fire_id", "incident_name", "latitude", "longitude", "acres_burned", "containment_percent"]
        )

        saved_fire_query = SavedQuery(
            query_id=str(uuid.uuid4()),
            name="Large Active Fires",
            description="Monitor large fires with low containment",
            configuration=fire_query,
            user_id="system",
            is_public=True
        )
        self.saved_queries[saved_fire_query.query_id] = saved_fire_query

        # Weather conditions query
        weather_query = self.query_builder.create_query(
            QueryType.WEATHER_DATA,
            "High Fire Risk Weather",
            "Weather conditions indicating high fire risk"
        )
        weather_query = self.query_builder.add_filter(
            weather_query, "humidity", FilterOperator.LESS_THAN, 30, "number"
        )
        weather_query = self.query_builder.add_filter(
            weather_query, "wind_speed", FilterOperator.GREATER_THAN, 20, "number"
        )
        weather_query = self.query_builder.set_fields(
            weather_query,
            ["station_id", "temperature", "humidity", "wind_speed", "wind_direction", "recorded_at"]
        )

        saved_weather_query = SavedQuery(
            query_id=str(uuid.uuid4()),
            name="Fire Risk Weather Conditions",
            description="Weather stations reporting high fire risk conditions",
            configuration=weather_query,
            user_id="system",
            is_public=True
        )
        self.saved_queries[saved_weather_query.query_id] = saved_weather_query

    def execute_query(self, query: QueryConfiguration) -> Dict[str, Any]:
        """Execute a query and return results"""
        # Validate query first
        is_valid, errors = self.query_builder.validate_query(query)
        if not is_valid:
            return {
                "success": False,
                "errors": errors,
                "data": None
            }

        # Log query execution
        self.query_history.append({
            "query_id": query.query_id,
            "query_type": query.query_type.value,
            "executed_at": datetime.utcnow(),
            "user": query.created_by
        })

        # Simulate query execution with sample data
        sample_data = self._generate_sample_data(query)

        return {
            "success": True,
            "query_id": query.query_id,
            "total_records": len(sample_data),
            "data": sample_data[:query.limit] if query.limit else sample_data,
            "execution_time": "0.245s",
            "metadata": {
                "query_type": query.query_type.value,
                "filters_applied": len(query.filters),
                "fields_returned": len(query.selected_fields)
            }
        }

    def _generate_sample_data(self, query: QueryConfiguration) -> List[Dict[str, Any]]:
        """Generate sample data based on query configuration"""
        import random
        from datetime import timedelta

        sample_data = []
        num_records = min(query.limit or 100, 100)

        if query.query_type == QueryType.FIRE_DATA:
            for i in range(num_records):
                record = {
                    "fire_id": f"CA-{2024}-{1000 + i}",
                    "incident_name": f"Sample Fire {i + 1}",
                    "latitude": 36.0 + random.uniform(-2, 2),
                    "longitude": -119.0 + random.uniform(-2, 2),
                    "brightness": random.uniform(300, 400),
                    "confidence": random.uniform(70, 95),
                    "detected_at": datetime.utcnow() - timedelta(days=random.randint(1, 30)),
                    "acres_burned": random.randint(500, 10000),
                    "containment_percent": random.randint(0, 100),
                    "fire_cause": random.choice(["Lightning", "Human", "Equipment", "Unknown"])
                }
                sample_data.append(record)

        elif query.query_type == QueryType.WEATHER_DATA:
            for i in range(num_records):
                record = {
                    "station_id": f"NOAA-{1000 + i}",
                    "temperature": random.uniform(60, 105),
                    "humidity": random.uniform(10, 80),
                    "wind_speed": random.uniform(5, 35),
                    "wind_direction": random.uniform(0, 360),
                    "precipitation": random.uniform(0, 0.5),
                    "pressure": random.uniform(29.5, 30.5),
                    "recorded_at": datetime.utcnow() - timedelta(hours=random.randint(1, 24)),
                    "latitude": 36.0 + random.uniform(-2, 2),
                    "longitude": -119.0 + random.uniform(-2, 2)
                }
                sample_data.append(record)

        # Filter data to only include selected fields
        if query.selected_fields:
            filtered_data = []
            for record in sample_data:
                filtered_record = {field: record.get(field) for field in query.selected_fields}
                filtered_data.append(filtered_record)
            return filtered_data

        return sample_data

    def save_query(self, query: QueryConfiguration, name: str, description: str,
                   user_id: str, is_public: bool = False) -> SavedQuery:
        """Save a query for future use"""
        saved_query = SavedQuery(
            query_id=str(uuid.uuid4()),
            name=name,
            description=description,
            configuration=query,
            user_id=user_id,
            is_public=is_public
        )

        self.saved_queries[saved_query.query_id] = saved_query
        return saved_query

    def get_saved_queries(self, user_id: str) -> List[SavedQuery]:
        """Get saved queries for a user"""
        user_queries = []
        for query in self.saved_queries.values():
            if query.user_id == user_id or query.is_public:
                user_queries.append(query)

        return sorted(user_queries, key=lambda q: q.updated_at, reverse=True)

    def request_data_export(self, query: QueryConfiguration, export_format: str,
                           user_id: str, email_notification: bool = True) -> DataExportRequest:
        """Request data export in specified format"""
        export_request = DataExportRequest(
            export_id=str(uuid.uuid4()),
            query_configuration=query,
            export_format=export_format,
            user_id=user_id,
            email_notification=email_notification
        )

        self.export_requests[export_request.export_id] = export_request

        # Simulate async processing
        asyncio.create_task(self._process_export_request(export_request))

        return export_request

    async def _process_export_request(self, export_request: DataExportRequest):
        """Process export request asynchronously"""
        try:
            # Simulate processing time
            await asyncio.sleep(2)

            export_request.status = "processing"

            # Execute query to get data
            results = self.execute_query(export_request.query_configuration)

            if results["success"]:
                # Simulate file generation
                file_path = f"/exports/{export_request.export_id}.{export_request.export_format}"
                export_request.file_path = file_path
                export_request.status = "completed"
                export_request.completed_at = datetime.utcnow()

                if export_request.email_notification:
                    # Simulate email notification
                    print(f"📧 Export completed: {file_path}")
            else:
                export_request.status = "failed"

        except Exception as e:
            export_request.status = "failed"
            print(f"Export failed: {str(e)}")

    def get_export_status(self, export_id: str) -> Optional[DataExportRequest]:
        """Get the status of an export request"""
        return self.export_requests.get(export_id)

    def get_query_history(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get query execution history for a user"""
        user_history = [
            h for h in self.query_history
            if h.get("user") == user_id
        ]

        return sorted(user_history, key=lambda h: h["executed_at"], reverse=True)[:limit]


class PortalAPIEndpoints:
    """API endpoints for the self-service portal"""

    def __init__(self, portal: SelfServicePortal):
        self.portal = portal

    async def create_query_endpoint(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """API endpoint to create a new query"""
        try:
            query_type = QueryType(request_data["query_type"])
            query = self.portal.query_builder.create_query(
                query_type,
                request_data["title"],
                request_data["description"]
            )

            # Add filters
            for filter_data in request_data.get("filters", []):
                self.portal.query_builder.add_filter(
                    query,
                    filter_data["field"],
                    FilterOperator(filter_data["operator"]),
                    filter_data["value"],
                    filter_data.get("data_type", "string")
                )

            # Set fields and other options
            if "selected_fields" in request_data:
                query.selected_fields = request_data["selected_fields"]

            if "limit" in request_data:
                query.limit = request_data["limit"]

            return {
                "success": True,
                "query": asdict(query)
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def execute_query_endpoint(self, query_data: Dict[str, Any]) -> Dict[str, Any]:
        """API endpoint to execute a query"""
        try:
            # Reconstruct query from data
            query = QueryConfiguration(**query_data)
            results = self.portal.execute_query(query)
            return results

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def get_field_catalog_endpoint(self, query_type: str) -> Dict[str, Any]:
        """API endpoint to get available fields for a query type"""
        try:
            query_type_enum = QueryType(query_type)
            fields = self.portal.query_builder.available_fields.get(query_type_enum, [])
            return {
                "success": True,
                "fields": fields
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


def demo_self_service_portal():
    """Demonstrate the self-service portal functionality"""
    print("🚀 CAL FIRE Self-Service Data Access Portal Demo")
    print("=" * 60)

    # Initialize portal
    portal = SelfServicePortal()

    # Demo 1: Create and execute a fire data query
    print("\n📊 Demo 1: Creating Fire Data Query")
    fire_query = portal.query_builder.create_query(
        QueryType.FIRE_DATA,
        "Active Large Fires",
        "Find active fires larger than 5000 acres"
    )

    # Add filters
    fire_query = portal.query_builder.add_filter(
        fire_query, "acres_burned", FilterOperator.GREATER_THAN, 5000, "number"
    )
    fire_query = portal.query_builder.add_filter(
        fire_query, "containment_percent", FilterOperator.LESS_THAN, 50, "number"
    )

    # Set fields to return
    fire_query = portal.query_builder.set_fields(
        fire_query,
        ["fire_id", "incident_name", "acres_burned", "containment_percent", "latitude", "longitude"]
    )

    # Set time range (last 7 days)
    fire_query = portal.query_builder.set_time_range(
        fire_query,
        datetime.utcnow() - timedelta(days=7),
        datetime.utcnow()
    )

    fire_query.created_by = "fire_chief_001"

    # Execute query
    results = portal.execute_query(fire_query)
    print(f"✅ Query executed: {results['total_records']} records found")
    print(f"   First record: {results['data'][0] if results['data'] else 'No data'}")

    # Demo 2: Save and retrieve queries
    print("\n💾 Demo 2: Saving and Retrieving Queries")
    saved_query = portal.save_query(
        fire_query,
        "Emergency Active Fires",
        "Critical fires requiring immediate attention",
        "fire_chief_001",
        is_public=True
    )
    print(f"✅ Query saved: {saved_query.name}")

    user_queries = portal.get_saved_queries("fire_chief_001")
    print(f"✅ User has {len(user_queries)} saved queries")

    # Demo 3: Weather data query with geographic bounds
    print("\n🌦️ Demo 3: Weather Data Query with Geographic Bounds")
    weather_query = portal.query_builder.create_query(
        QueryType.WEATHER_DATA,
        "High Risk Weather Conditions",
        "Weather conditions indicating high fire risk in northern California"
    )

    # Add weather-specific filters
    weather_query = portal.query_builder.add_filter(
        weather_query, "humidity", FilterOperator.LESS_THAN, 25, "number"
    )
    weather_query = portal.query_builder.add_filter(
        weather_query, "wind_speed", FilterOperator.GREATER_THAN, 25, "number"
    )

    # Set geographic bounds (northern California)
    weather_query = portal.query_builder.set_geographic_bounds(
        weather_query, 37.0, 42.0, -125.0, -119.0
    )

    weather_query = portal.query_builder.set_fields(
        weather_query,
        ["station_id", "temperature", "humidity", "wind_speed", "recorded_at"]
    )

    weather_query.created_by = "meteorologist_001"

    # Execute weather query
    weather_results = portal.execute_query(weather_query)
    print(f"✅ Weather query executed: {weather_results['total_records']} stations found")

    # Demo 4: Data export request
    print("\n📤 Demo 4: Data Export Request")
    export_request = portal.request_data_export(
        fire_query,
        "csv",
        "fire_chief_001",
        email_notification=True
    )
    print(f"✅ Export requested: {export_request.export_id}")
    print(f"   Format: {export_request.export_format}")
    print(f"   Status: {export_request.status}")

    # Check export status after a short delay
    import time
    time.sleep(3)
    updated_export = portal.get_export_status(export_request.export_id)
    print(f"✅ Export status updated: {updated_export.status}")

    # Demo 5: Query validation
    print("\n✅ Demo 5: Query Validation")
    invalid_query = portal.query_builder.create_query(
        QueryType.FIRE_DATA,
        "Invalid Query",
        "Query with invalid field"
    )
    invalid_query.selected_fields = ["invalid_field", "another_invalid_field"]

    is_valid, errors = portal.query_builder.validate_query(invalid_query)
    print(f"✅ Query validation: {is_valid}")
    if not is_valid:
        print(f"   Errors: {errors}")

    print("\n🎯 Self-Service Portal Demo Completed!")
    print(f"📈 Total queries in history: {len(portal.query_history)}")
    print(f"💾 Total saved queries: {len(portal.saved_queries)}")
    print(f"📤 Total export requests: {len(portal.export_requests)}")


if __name__ == "__main__":
    demo_self_service_portal()