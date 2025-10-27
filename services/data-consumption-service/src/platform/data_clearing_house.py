"""
Challenge 3 Deliverable: Data Clearing House Platform
Comprehensive data clearing house for secure access to wildfire intelligence data
"""

from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, asdict
from enum import Enum
import json
from datetime import datetime, timezone
import hashlib
import uuid

class UserRole(Enum):
    """User roles for the data clearing house"""
    DATA_SCIENTIST = "data_scientist"
    ANALYST = "analyst"
    BUSINESS_USER = "business_user"
    ADMINISTRATOR = "administrator"
    PARTNER_AGENCY = "partner_agency"
    EXTERNAL_RESEARCHER = "external_researcher"

class DatasetCategory(Enum):
    """Dataset categories in the clearing house"""
    FIRE_DETECTION = "fire_detection"
    WEATHER_DATA = "weather_data"
    SATELLITE_IMAGERY = "satellite_imagery"
    IOT_SENSORS = "iot_sensors"
    HISTORICAL_ANALYSIS = "historical_analysis"
    REAL_TIME_STREAMS = "real_time_streams"

class AccessLevel(Enum):
    """Data access levels"""
    PUBLIC = "public"
    INTERNAL = "internal"
    RESTRICTED = "restricted"
    CONFIDENTIAL = "confidential"

@dataclass
class DatasetMetadata:
    """Comprehensive dataset metadata"""
    dataset_id: str
    name: str
    description: str
    category: DatasetCategory
    access_level: AccessLevel
    data_source: str
    schema_version: str
    last_updated: str
    record_count: int
    file_size_mb: float
    geographic_extent: Dict[str, float]
    temporal_coverage: Dict[str, str]
    keywords: List[str]
    lineage: List[str]
    quality_score: float
    contact_person: str
    license_type: str
    update_frequency: str

@dataclass
class UserProfile:
    """User profile for role-based access"""
    user_id: str
    username: str
    email: str
    role: UserRole
    organization: str
    access_permissions: List[str]
    datasets_accessed: List[str]
    last_login: str
    account_status: str
    security_clearance: Optional[str] = None

@dataclass
class DataRequest:
    """Data access request tracking"""
    request_id: str
    user_id: str
    dataset_id: str
    request_type: str
    justification: str
    requested_at: str
    status: str
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    access_expires: Optional[str] = None

class DataClearingHouse:
    """Comprehensive data clearing house platform"""

    def __init__(self):
        self.datasets: Dict[str, DatasetMetadata] = {}
        self.users: Dict[str, UserProfile] = {}
        self.data_requests: Dict[str, DataRequest] = {}
        self.access_logs: List[Dict[str, Any]] = []
        self.initialize_sample_data()

    def initialize_sample_data(self):
        """Initialize with sample datasets and users"""

        # Sample datasets
        sample_datasets = [
            DatasetMetadata(
                dataset_id="fire_detections_2024",
                name="NASA FIRMS Fire Detections 2024",
                description="Real-time fire detection data from MODIS and VIIRS satellites covering California",
                category=DatasetCategory.FIRE_DETECTION,
                access_level=AccessLevel.INTERNAL,
                data_source="NASA FIRMS",
                schema_version="v6.1",
                last_updated=datetime.now(timezone.utc).isoformat(),
                record_count=45623,
                file_size_mb=123.5,
                geographic_extent={
                    "lat_min": 32.0, "lat_max": 42.0,
                    "lon_min": -124.0, "lon_max": -114.0
                },
                temporal_coverage={
                    "start_date": "2024-01-01",
                    "end_date": "2024-12-31"
                },
                keywords=["fire", "detection", "satellite", "real-time", "california"],
                lineage=["NASA FIRMS API", "Data Ingestion Service", "Quality Validation"],
                quality_score=96.8,
                contact_person="sarah.chen@fire.ca.gov",
                license_type="Government Use",
                update_frequency="Every 3 hours"
            ),

            DatasetMetadata(
                dataset_id="weather_stations_ca",
                name="California Weather Station Network",
                description="Comprehensive weather observations from NOAA and RAWS stations across California",
                category=DatasetCategory.WEATHER_DATA,
                access_level=AccessLevel.PUBLIC,
                data_source="NOAA/RAWS",
                schema_version="v2.1",
                last_updated=datetime.now(timezone.utc).isoformat(),
                record_count=1245789,
                file_size_mb=567.2,
                geographic_extent={
                    "lat_min": 32.0, "lat_max": 42.0,
                    "lon_min": -124.0, "lon_max": -114.0
                },
                temporal_coverage={
                    "start_date": "2020-01-01",
                    "end_date": "2024-12-31"
                },
                keywords=["weather", "temperature", "humidity", "wind", "stations"],
                lineage=["NOAA API", "RAWS Network", "Weather Service"],
                quality_score=94.2,
                contact_person="michael.rodriguez@fire.ca.gov",
                license_type="Public Domain",
                update_frequency="Hourly"
            ),

            DatasetMetadata(
                dataset_id="iot_sensor_network",
                name="CAL FIRE IoT Sensor Network",
                description="Environmental monitoring data from deployed IoT sensors in fire-prone areas",
                category=DatasetCategory.IOT_SENSORS,
                access_level=AccessLevel.RESTRICTED,
                data_source="CAL FIRE IoT Network",
                schema_version="v1.3",
                last_updated=datetime.now(timezone.utc).isoformat(),
                record_count=892341,
                file_size_mb=234.8,
                geographic_extent={
                    "lat_min": 33.0, "lat_max": 41.0,
                    "lon_min": -123.0, "lon_max": -115.0
                },
                temporal_coverage={
                    "start_date": "2023-06-01",
                    "end_date": "2024-12-31"
                },
                keywords=["iot", "sensors", "smoke", "temperature", "real-time"],
                lineage=["IoT MQTT Connector", "Device Management System"],
                quality_score=91.5,
                contact_person="jessica.park@fire.ca.gov",
                license_type="Restricted Use",
                update_frequency="Every 15 minutes"
            ),

            DatasetMetadata(
                dataset_id="landsat_fire_analysis",
                name="Landsat Fire Impact Analysis",
                description="Multi-temporal analysis of fire impacts using Landsat imagery",
                category=DatasetCategory.SATELLITE_IMAGERY,
                access_level=AccessLevel.INTERNAL,
                data_source="USGS Landsat",
                schema_version="v3.0",
                last_updated=datetime.now(timezone.utc).isoformat(),
                record_count=15847,
                file_size_mb=2456.7,
                geographic_extent={
                    "lat_min": 32.0, "lat_max": 42.0,
                    "lon_min": -124.0, "lon_max": -114.0
                },
                temporal_coverage={
                    "start_date": "2020-01-01",
                    "end_date": "2024-12-31"
                },
                keywords=["landsat", "satellite", "fire", "impact", "analysis"],
                lineage=["USGS Earth Explorer", "Satellite Connector", "Analysis Pipeline"],
                quality_score=98.1,
                contact_person="robert.kim@fire.ca.gov",
                license_type="Government Use",
                update_frequency="Weekly"
            ),

            DatasetMetadata(
                dataset_id="historical_fire_patterns",
                name="Historical Fire Pattern Analysis (1990-2024)",
                description="Comprehensive analysis of fire patterns, trends, and impacts over 30+ years",
                category=DatasetCategory.HISTORICAL_ANALYSIS,
                access_level=AccessLevel.PUBLIC,
                data_source="CAL FIRE Historical Database",
                schema_version="v4.2",
                last_updated=datetime.now(timezone.utc).isoformat(),
                record_count=234567,
                file_size_mb=1876.3,
                geographic_extent={
                    "lat_min": 32.0, "lat_max": 42.0,
                    "lon_min": -124.0, "lon_max": -114.0
                },
                temporal_coverage={
                    "start_date": "1990-01-01",
                    "end_date": "2024-12-31"
                },
                keywords=["historical", "patterns", "trends", "analysis", "long-term"],
                lineage=["CAL FIRE Archives", "Research Division", "Statistical Analysis"],
                quality_score=97.3,
                contact_person="research@fire.ca.gov",
                license_type="Creative Commons",
                update_frequency="Annually"
            )
        ]

        for dataset in sample_datasets:
            self.datasets[dataset.dataset_id] = dataset

        # Sample users
        sample_users = [
            UserProfile(
                user_id="user_001",
                username="alice_scientist",
                email="alice.johnson@fire.ca.gov",
                role=UserRole.DATA_SCIENTIST,
                organization="CAL FIRE Research Division",
                access_permissions=["fire_detection", "weather_data", "satellite_imagery", "historical_analysis"],
                datasets_accessed=["fire_detections_2024", "weather_stations_ca"],
                last_login=datetime.now(timezone.utc).isoformat(),
                account_status="active",
                security_clearance="internal"
            ),

            UserProfile(
                user_id="user_002",
                username="bob_analyst",
                email="bob.smith@fire.ca.gov",
                role=UserRole.ANALYST,
                organization="CAL FIRE Operations",
                access_permissions=["fire_detection", "weather_data", "iot_sensors"],
                datasets_accessed=["fire_detections_2024", "iot_sensor_network"],
                last_login=datetime.now(timezone.utc).isoformat(),
                account_status="active",
                security_clearance="restricted"
            ),

            UserProfile(
                user_id="user_003",
                username="carol_manager",
                email="carol.davis@fire.ca.gov",
                role=UserRole.BUSINESS_USER,
                organization="CAL FIRE Management",
                access_permissions=["fire_detection", "historical_analysis"],
                datasets_accessed=["historical_fire_patterns"],
                last_login=datetime.now(timezone.utc).isoformat(),
                account_status="active"
            ),

            UserProfile(
                user_id="user_004",
                username="david_partner",
                email="david.wilson@usfs.gov",
                role=UserRole.PARTNER_AGENCY,
                organization="US Forest Service",
                access_permissions=["fire_detection", "weather_data"],
                datasets_accessed=["fire_detections_2024"],
                last_login=datetime.now(timezone.utc).isoformat(),
                account_status="active"
            ),

            UserProfile(
                user_id="user_005",
                username="eve_researcher",
                email="eve.brown@university.edu",
                role=UserRole.EXTERNAL_RESEARCHER,
                organization="UC Berkeley",
                access_permissions=["historical_analysis"],
                datasets_accessed=[],
                last_login=datetime.now(timezone.utc).isoformat(),
                account_status="pending_approval"
            )
        ]

        for user in sample_users:
            self.users[user.user_id] = user

    def register_dataset(self, metadata: DatasetMetadata) -> str:
        """Register a new dataset in the clearing house"""
        dataset_id = metadata.dataset_id
        self.datasets[dataset_id] = metadata

        self._log_activity("dataset_registered", {
            "dataset_id": dataset_id,
            "name": metadata.name,
            "category": metadata.category.value,
            "access_level": metadata.access_level.value
        })

        return dataset_id

    def create_user(self, user_profile: UserProfile) -> str:
        """Create a new user account"""
        user_id = user_profile.user_id
        self.users[user_id] = user_profile

        self._log_activity("user_created", {
            "user_id": user_id,
            "username": user_profile.username,
            "role": user_profile.role.value,
            "organization": user_profile.organization
        })

        return user_id

    def request_data_access(self, user_id: str, dataset_id: str,
                           justification: str, request_type: str = "read") -> str:
        """Submit a data access request"""
        request_id = f"req_{uuid.uuid4().hex[:8]}"

        request = DataRequest(
            request_id=request_id,
            user_id=user_id,
            dataset_id=dataset_id,
            request_type=request_type,
            justification=justification,
            requested_at=datetime.now(timezone.utc).isoformat(),
            status="pending"
        )

        self.data_requests[request_id] = request

        self._log_activity("access_requested", {
            "request_id": request_id,
            "user_id": user_id,
            "dataset_id": dataset_id,
            "request_type": request_type
        })

        return request_id

    def approve_data_access(self, request_id: str, approver_id: str,
                           access_duration_days: int = 30) -> bool:
        """Approve a data access request"""
        if request_id not in self.data_requests:
            return False

        request = self.data_requests[request_id]
        request.status = "approved"
        request.approved_by = approver_id
        request.approved_at = datetime.now(timezone.utc).isoformat()

        # Set access expiration
        from datetime import timedelta
        expires = datetime.now(timezone.utc) + timedelta(days=access_duration_days)
        request.access_expires = expires.isoformat()

        # Add dataset to user's accessible datasets
        user = self.users[request.user_id]
        if request.dataset_id not in user.datasets_accessed:
            user.datasets_accessed.append(request.dataset_id)

        self._log_activity("access_approved", {
            "request_id": request_id,
            "approver_id": approver_id,
            "user_id": request.user_id,
            "dataset_id": request.dataset_id,
            "expires": request.access_expires
        })

        return True

    def search_datasets(self, query: str, user_id: str,
                       category: Optional[DatasetCategory] = None,
                       access_level: Optional[AccessLevel] = None) -> List[DatasetMetadata]:
        """Search datasets based on query and user permissions"""
        user = self.users.get(user_id)
        if not user:
            return []

        results = []
        query_lower = query.lower()

        for dataset in self.datasets.values():
            # Check access permissions
            if not self._user_can_access_dataset(user, dataset):
                continue

            # Apply filters
            if category and dataset.category != category:
                continue

            if access_level and dataset.access_level != access_level:
                continue

            # Search in text fields
            searchable_text = f"{dataset.name} {dataset.description} {' '.join(dataset.keywords)}".lower()
            if query_lower in searchable_text:
                results.append(dataset)

        self._log_activity("dataset_search", {
            "user_id": user_id,
            "query": query,
            "results_count": len(results)
        })

        return results

    def get_user_datasets(self, user_id: str) -> List[DatasetMetadata]:
        """Get all datasets accessible to a user"""
        user = self.users.get(user_id)
        if not user:
            return []

        accessible_datasets = []
        for dataset in self.datasets.values():
            if self._user_can_access_dataset(user, dataset):
                accessible_datasets.append(dataset)

        return accessible_datasets

    def get_dataset_lineage(self, dataset_id: str) -> Dict[str, Any]:
        """Get dataset lineage and provenance information"""
        dataset = self.datasets.get(dataset_id)
        if not dataset:
            return {}

        return {
            "dataset_id": dataset_id,
            "lineage": dataset.lineage,
            "data_source": dataset.data_source,
            "schema_version": dataset.schema_version,
            "last_updated": dataset.last_updated,
            "quality_score": dataset.quality_score,
            "contact_person": dataset.contact_person
        }

    def _user_can_access_dataset(self, user: UserProfile, dataset: DatasetMetadata) -> bool:
        """Check if user can access a specific dataset"""
        # Public datasets are accessible to all
        if dataset.access_level == AccessLevel.PUBLIC:
            return True

        # Check role-based access
        if dataset.access_level == AccessLevel.INTERNAL:
            return user.role in [UserRole.DATA_SCIENTIST, UserRole.ANALYST,
                               UserRole.BUSINESS_USER, UserRole.ADMINISTRATOR]

        if dataset.access_level == AccessLevel.RESTRICTED:
            return user.role in [UserRole.DATA_SCIENTIST, UserRole.ANALYST,
                               UserRole.ADMINISTRATOR] and user.security_clearance == "restricted"

        if dataset.access_level == AccessLevel.CONFIDENTIAL:
            return user.role == UserRole.ADMINISTRATOR and user.security_clearance == "confidential"

        return False

    def _log_activity(self, action: str, details: Dict[str, Any]):
        """Log user activity for audit purposes"""
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "details": details,
            "session_id": hashlib.md5(f"{action}{datetime.now()}".encode()).hexdigest()[:8]
        }

        self.access_logs.append(log_entry)

        # Keep only last 10000 log entries
        if len(self.access_logs) > 10000:
            self.access_logs = self.access_logs[-10000:]

    def get_clearing_house_summary(self) -> Dict[str, Any]:
        """Generate comprehensive clearing house summary"""
        return {
            "platform_overview": {
                "total_datasets": len(self.datasets),
                "total_users": len(self.users),
                "pending_requests": len([r for r in self.data_requests.values() if r.status == "pending"]),
                "total_access_logs": len(self.access_logs)
            },
            "datasets_by_category": {
                category.value: len([d for d in self.datasets.values() if d.category == category])
                for category in DatasetCategory
            },
            "datasets_by_access_level": {
                level.value: len([d for d in self.datasets.values() if d.access_level == level])
                for level in AccessLevel
            },
            "users_by_role": {
                role.value: len([u for u in self.users.values() if u.role == role])
                for role in UserRole
            },
            "data_volume_statistics": {
                "total_records": sum(d.record_count for d in self.datasets.values()),
                "total_size_gb": sum(d.file_size_mb for d in self.datasets.values()) / 1024,
                "average_quality_score": sum(d.quality_score for d in self.datasets.values()) / len(self.datasets) if self.datasets else 0
            },
            "recent_activity": self.access_logs[-10:] if self.access_logs else []
        }

    def export_catalog(self, filepath: str):
        """Export data catalog to JSON file"""
        catalog = {
            "data_clearing_house_catalog": {
                "datasets": {d.dataset_id: asdict(d) for d in self.datasets.values()},
                "summary": self.get_clearing_house_summary()
            },
            "generated_at": datetime.now().isoformat(),
            "version": "3.0.0",
            "challenge": "CAL FIRE Challenge 3 - Data Consumption and Analytics"
        }

        with open(filepath, 'w') as f:
            json.dump(catalog, f, indent=2, default=str)

        print(f"📚 Data clearing house catalog exported to: {filepath}")

# Global data clearing house instance
data_clearing_house = DataClearingHouse()

def get_data_clearing_house() -> DataClearingHouse:
    """Get the global data clearing house instance"""
    return data_clearing_house