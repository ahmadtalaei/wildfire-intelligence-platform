"""
Challenge 2 Deliverable: Hybrid Storage Architecture Design
Solution architecture document for hybrid on-premises and cloud storage solution
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import json
from datetime import datetime

class StorageTier(Enum):
    """Storage tier classifications"""
    HOT = "hot"       # Frequently accessed data
    WARM = "warm"     # Occasionally accessed data
    COLD = "cold"     # Rarely accessed data
    ARCHIVE = "archive"  # Long-term retention

class StorageLocation(Enum):
    """Storage location types"""
    ON_PREMISES = "on_premises"
    CLOUD_PRIMARY = "cloud_primary"
    CLOUD_SECONDARY = "cloud_secondary"
    HYBRID = "hybrid"

class DataClassification(Enum):
    """Data classification levels"""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"

@dataclass
class StorageComponent:
    """Individual storage component specification"""
    component_id: str
    name: str
    storage_type: str
    location: StorageLocation
    tier: StorageTier
    capacity_gb: int
    performance_iops: int
    encryption_enabled: bool
    backup_enabled: bool
    replication_enabled: bool
    cost_per_gb_month: float

@dataclass
class DataLifecyclePolicy:
    """Data lifecycle management policy"""
    policy_id: str
    data_type: str
    classification: DataClassification
    hot_retention_days: int
    warm_retention_days: int
    cold_retention_days: int
    archive_retention_years: int
    deletion_policy: str
    compliance_requirements: List[str]

class HybridStorageArchitecture:
    """Comprehensive hybrid storage solution architecture"""

    def __init__(self):
        self.storage_components = self._define_storage_components()
        self.lifecycle_policies = self._define_lifecycle_policies()
        self.integration_layers = self._define_integration_layers()
        self.access_patterns = self._define_access_patterns()

    def _define_storage_components(self) -> Dict[str, StorageComponent]:
        """Define all storage components in the hybrid architecture"""
        return {
            # On-Premises Hot Storage
            "on_prem_primary_ssd": StorageComponent(
                component_id="on_prem_primary_ssd",
                name="On-Premises Primary SSD Array",
                storage_type="NVMe SSD",
                location=StorageLocation.ON_PREMISES,
                tier=StorageTier.HOT,
                capacity_gb=50000,  # 50TB
                performance_iops=100000,
                encryption_enabled=True,
                backup_enabled=True,
                replication_enabled=True,
                cost_per_gb_month=0.50
            ),

            # On-Premises Warm Storage
            "on_prem_secondary_hdd": StorageComponent(
                component_id="on_prem_secondary_hdd",
                name="On-Premises Secondary HDD Array",
                storage_type="Enterprise HDD",
                location=StorageLocation.ON_PREMISES,
                tier=StorageTier.WARM,
                capacity_gb=200000,  # 200TB
                performance_iops=5000,
                encryption_enabled=True,
                backup_enabled=True,
                replication_enabled=False,
                cost_per_gb_month=0.15
            ),

            # Cloud Hot Storage
            "cloud_s3_standard": StorageComponent(
                component_id="cloud_s3_standard",
                name="AWS S3 Standard Storage",
                storage_type="Object Storage",
                location=StorageLocation.CLOUD_PRIMARY,
                tier=StorageTier.HOT,
                capacity_gb=1000000,  # 1PB
                performance_iops=50000,
                encryption_enabled=True,
                backup_enabled=True,
                replication_enabled=True,
                cost_per_gb_month=0.023
            ),

            # Cloud Warm Storage
            "cloud_s3_ia": StorageComponent(
                component_id="cloud_s3_ia",
                name="AWS S3 Infrequent Access",
                storage_type="Object Storage",
                location=StorageLocation.CLOUD_PRIMARY,
                tier=StorageTier.WARM,
                capacity_gb=5000000,  # 5PB
                performance_iops=10000,
                encryption_enabled=True,
                backup_enabled=True,
                replication_enabled=True,
                cost_per_gb_month=0.0125
            ),

            # Cloud Cold Storage
            "cloud_glacier": StorageComponent(
                component_id="cloud_glacier",
                name="AWS S3 Glacier",
                storage_type="Archive Storage",
                location=StorageLocation.CLOUD_PRIMARY,
                tier=StorageTier.COLD,
                capacity_gb=50000000,  # 50PB
                performance_iops=100,
                encryption_enabled=True,
                backup_enabled=False,
                replication_enabled=True,
                cost_per_gb_month=0.004
            ),

            # Cloud Archive Storage
            "cloud_deep_archive": StorageComponent(
                component_id="cloud_deep_archive",
                name="AWS S3 Glacier Deep Archive",
                storage_type="Deep Archive Storage",
                location=StorageLocation.CLOUD_PRIMARY,
                tier=StorageTier.ARCHIVE,
                capacity_gb=100000000,  # 100PB
                performance_iops=10,
                encryption_enabled=True,
                backup_enabled=False,
                replication_enabled=False,
                cost_per_gb_month=0.00099
            ),

            # Multi-Cloud Backup
            "azure_backup": StorageComponent(
                component_id="azure_backup",
                name="Azure Blob Storage Backup",
                storage_type="Object Storage",
                location=StorageLocation.CLOUD_SECONDARY,
                tier=StorageTier.COLD,
                capacity_gb=10000000,  # 10PB
                performance_iops=5000,
                encryption_enabled=True,
                backup_enabled=False,
                replication_enabled=True,
                cost_per_gb_month=0.018
            )
        }

    def _define_lifecycle_policies(self) -> List[DataLifecyclePolicy]:
        """Define data lifecycle management policies"""
        return [
            DataLifecyclePolicy(
                policy_id="fire_detection_policy",
                data_type="fire_detection",
                classification=DataClassification.INTERNAL,
                hot_retention_days=30,
                warm_retention_days=90,
                cold_retention_days=365,
                archive_retention_years=7,
                deletion_policy="automatic_after_retention",
                compliance_requirements=["CAL FIRE Records Retention", "NIST SP 800-53"]
            ),

            DataLifecyclePolicy(
                policy_id="weather_data_policy",
                data_type="weather_data",
                classification=DataClassification.PUBLIC,
                hot_retention_days=7,
                warm_retention_days=30,
                cold_retention_days=365,
                archive_retention_years=10,
                deletion_policy="automatic_after_retention",
                compliance_requirements=["NOAA Data Policy", "Open Data Standards"]
            ),

            DataLifecyclePolicy(
                policy_id="iot_sensor_policy",
                data_type="iot_sensor",
                classification=DataClassification.CONFIDENTIAL,
                hot_retention_days=14,
                warm_retention_days=60,
                cold_retention_days=730,
                archive_retention_years=5,
                deletion_policy="manual_review_required",
                compliance_requirements=["IoT Security Guidelines", "GDPR"]
            ),

            DataLifecyclePolicy(
                policy_id="satellite_imagery_policy",
                data_type="satellite_imagery",
                classification=DataClassification.INTERNAL,
                hot_retention_days=60,
                warm_retention_days=180,
                cold_retention_days=1095,
                archive_retention_years=15,
                deletion_policy="permanent_retention",
                compliance_requirements=["Satellite Data Policy", "Scientific Data Standards"]
            ),

            DataLifecyclePolicy(
                policy_id="operational_logs_policy",
                data_type="operational_logs",
                classification=DataClassification.RESTRICTED,
                hot_retention_days=30,
                warm_retention_days=90,
                cold_retention_days=2555,  # 7 years
                archive_retention_years=10,
                deletion_policy="automatic_after_retention",
                compliance_requirements=["SOX Compliance", "Audit Standards", "NIST Cybersecurity Framework"]
            )
        ]

    def _define_integration_layers(self) -> Dict[str, Dict[str, Any]]:
        """Define integration layers between on-premises and cloud"""
        return {
            "data_orchestration": {
                "platform": "Apache Airflow",
                "deployment": "Kubernetes on-premises + AWS ECS",
                "features": [
                    "Automated data movement between tiers",
                    "Lifecycle policy enforcement",
                    "Data validation and integrity checks",
                    "Performance monitoring and optimization"
                ],
                "integration_points": [
                    "PostgreSQL → S3 sync",
                    "On-premises → Cloud replication",
                    "Multi-cloud backup coordination"
                ]
            },

            "api_gateway": {
                "platform": "Kong Gateway",
                "deployment": "Hybrid on-premises + AWS API Gateway",
                "features": [
                    "Unified data access API",
                    "Authentication and authorization",
                    "Rate limiting and throttling",
                    "Request routing and load balancing"
                ],
                "security": [
                    "OAuth 2.0 / OpenID Connect",
                    "API key management",
                    "TLS 1.3 encryption",
                    "Request/response logging"
                ]
            },

            "message_broker": {
                "platform": "Apache Kafka",
                "deployment": "On-premises cluster + AWS MSK",
                "features": [
                    "Real-time data streaming",
                    "Cross-region replication",
                    "Event-driven architecture",
                    "Schema registry and versioning"
                ],
                "topics": [
                    "fire-detections",
                    "weather-data",
                    "iot-sensors",
                    "storage-events",
                    "lifecycle-transitions"
                ]
            },

            "backup_replication": {
                "platform": "Veeam Backup + AWS DataSync",
                "deployment": "On-premises agents + Cloud native",
                "features": [
                    "Cross-platform backup and restore",
                    "Incremental and differential backups",
                    "Point-in-time recovery",
                    "Disaster recovery automation"
                ],
                "schedules": [
                    "Critical data: Every 4 hours",
                    "Standard data: Daily",
                    "Archive data: Weekly"
                ]
            }
        }

    def _define_access_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Define data access patterns and performance requirements"""
        return {
            "real_time_operations": {
                "description": "Active wildfire monitoring and response",
                "data_types": ["fire_detection", "weather_data", "iot_sensor"],
                "storage_locations": ["on_prem_primary_ssd", "cloud_s3_standard"],
                "performance_requirements": {
                    "latency_ms": "< 100",
                    "throughput_mbps": "> 1000",
                    "availability": "99.99%"
                },
                "access_frequency": "Continuous"
            },

            "analytical_processing": {
                "description": "Historical analysis and trend identification",
                "data_types": ["all_historical_data"],
                "storage_locations": ["on_prem_secondary_hdd", "cloud_s3_ia"],
                "performance_requirements": {
                    "latency_ms": "< 1000",
                    "throughput_mbps": "> 500",
                    "availability": "99.9%"
                },
                "access_frequency": "Daily to Weekly"
            },

            "compliance_reporting": {
                "description": "Regulatory and audit reporting",
                "data_types": ["operational_logs", "fire_detection", "satellite_imagery"],
                "storage_locations": ["cloud_glacier", "azure_backup"],
                "performance_requirements": {
                    "latency_ms": "< 10000",
                    "throughput_mbps": "> 100",
                    "availability": "99.5%"
                },
                "access_frequency": "Monthly to Quarterly"
            },

            "disaster_recovery": {
                "description": "Business continuity and disaster recovery",
                "data_types": ["all_critical_data"],
                "storage_locations": ["azure_backup", "cloud_s3_standard"],
                "performance_requirements": {
                    "rto_minutes": "< 60",
                    "rpo_minutes": "< 15",
                    "availability": "99.999%"
                },
                "access_frequency": "Emergency only"
            }
        }

    def get_hybrid_justification(self) -> Dict[str, Any]:
        """Generate justification for hybrid model choices"""
        return {
            "latency_optimization": {
                "rationale": "On-premises storage for ultra-low latency access to critical real-time data",
                "benefits": [
                    "Sub-100ms response times for emergency operations",
                    "Reduced dependency on internet connectivity",
                    "Local processing capabilities for time-sensitive analysis"
                ],
                "use_cases": ["Active fire detection", "Emergency response coordination"]
            },

            "compliance_requirements": {
                "rationale": "Hybrid approach satisfies data sovereignty and regulatory requirements",
                "benefits": [
                    "Critical data remains on-premises for regulatory compliance",
                    "Cloud storage for non-sensitive data and backup",
                    "Audit trail across both environments"
                ],
                "compliance_frameworks": ["NIST SP 800-53", "FISMA", "CAL FIRE Data Policies"]
            },

            "cost_optimization": {
                "rationale": "Tiered storage strategy minimizes total cost of ownership",
                "benefits": [
                    "Hot data on fast, expensive storage (on-prem + cloud)",
                    "Warm data on cost-effective storage (cloud IA)",
                    "Cold/archive data on lowest-cost storage (Glacier)",
                    "Pay-as-you-scale cloud model for variable workloads"
                ],
                "estimated_savings": "40-60% compared to all on-premises solution"
            },

            "scalability_flexibility": {
                "rationale": "Cloud resources provide unlimited scalability for peak demands",
                "benefits": [
                    "Elastic scaling during wildfire season peaks",
                    "Geographic distribution for disaster recovery",
                    "Integration with cloud-native analytics services"
                ],
                "scenarios": ["Peak wildfire season", "Large-scale incident response"]
            },

            "risk_mitigation": {
                "rationale": "Multi-cloud and hybrid approach reduces single points of failure",
                "benefits": [
                    "Geographic redundancy across multiple data centers",
                    "Vendor diversification reduces lock-in risk",
                    "Multiple backup and recovery options"
                ],
                "resilience_features": ["Cross-region replication", "Multi-cloud backup", "Automated failover"]
            }
        }

    def get_architecture_summary(self) -> Dict[str, Any]:
        """Generate comprehensive architecture summary"""
        total_capacity = sum(comp.capacity_gb for comp in self.storage_components.values())
        total_monthly_cost = sum(comp.capacity_gb * comp.cost_per_gb_month for comp in self.storage_components.values())

        return {
            "architecture_overview": {
                "total_storage_capacity_tb": total_capacity / 1000,
                "total_monthly_cost_usd": total_monthly_cost,
                "storage_locations": len(set(comp.location for comp in self.storage_components.values())),
                "storage_tiers": len(set(comp.tier for comp in self.storage_components.values())),
                "lifecycle_policies": len(self.lifecycle_policies)
            },
            "storage_components": {
                comp_id: asdict(comp) for comp_id, comp in self.storage_components.items()
            },
            "lifecycle_policies": [asdict(policy) for policy in self.lifecycle_policies],
            "integration_layers": self.integration_layers,
            "access_patterns": self.access_patterns,
            "hybrid_justification": self.get_hybrid_justification(),
            "capacity_by_tier": {
                tier.value: sum(comp.capacity_gb for comp in self.storage_components.values()
                               if comp.tier == tier) / 1000  # Convert to TB
                for tier in StorageTier
            },
            "cost_by_location": {
                location.value: sum(comp.capacity_gb * comp.cost_per_gb_month
                                  for comp in self.storage_components.values()
                                  if comp.location == location)
                for location in StorageLocation
            }
        }

    def export_architecture(self, filepath: str):
        """Export hybrid storage architecture to JSON file"""
        architecture = {
            "hybrid_storage_architecture": self.get_architecture_summary(),
            "generated_at": datetime.now().isoformat(),
            "version": "2.0.0",
            "challenge": "CAL FIRE Challenge 2 - Data Storage"
        }

        with open(filepath, 'w') as f:
            json.dump(architecture, f, indent=2, default=str)

        print(f"🏗️ Hybrid storage architecture exported to: {filepath}")

# Global hybrid storage architecture instance
hybrid_storage = HybridStorageArchitecture()

def get_hybrid_storage() -> HybridStorageArchitecture:
    """Get the global hybrid storage architecture instance"""
    return hybrid_storage