"""
Challenge 2 Deliverable: Data Governance Framework
Comprehensive data governance policies, ownership, stewardship, metadata, and classification
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import json
from datetime import datetime, timedelta

class DataOwnershipRole(Enum):
    """Data ownership roles"""
    DATA_OWNER = "data_owner"
    DATA_STEWARD = "data_steward"
    DATA_CUSTODIAN = "data_custodian"
    DATA_USER = "data_user"

class DataClassification(Enum):
    """Data classification levels"""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"

class RetentionAction(Enum):
    """Actions to take when retention period expires"""
    DELETE = "delete"
    ARCHIVE = "archive"
    REVIEW = "review"
    PERMANENT = "permanent"

@dataclass
class DataOwner:
    """Data ownership assignment"""
    owner_id: str
    name: str
    email: str
    role: DataOwnershipRole
    department: str
    responsibilities: List[str]
    contact_info: Dict[str, str]

@dataclass
class DataClassificationRule:
    """Data classification rule"""
    rule_id: str
    data_type: str
    classification: DataClassification
    criteria: List[str]
    justification: str
    created_by: str
    created_date: str
    last_reviewed: str

@dataclass
class RetentionSchedule:
    """Data retention schedule"""
    schedule_id: str
    data_type: str
    classification: DataClassification
    retention_period_days: int
    action_on_expiry: RetentionAction
    legal_hold_exempt: bool
    business_justification: str
    regulatory_requirements: List[str]

@dataclass
class MetadataSchema:
    """Metadata schema definition"""
    schema_id: str
    data_type: str
    required_fields: List[str]
    optional_fields: List[str]
    field_types: Dict[str, str]
    validation_rules: List[str]
    version: str

class DataGovernanceFramework:
    """Comprehensive data governance framework"""

    def __init__(self):
        self.data_owners = self._define_data_owners()
        self.classification_rules = self._define_classification_rules()
        self.retention_schedules = self._define_retention_schedules()
        self.metadata_schemas = self._define_metadata_schemas()
        self.governance_policies = self._define_governance_policies()

    def _define_data_owners(self) -> Dict[str, DataOwner]:
        """Define data ownership structure"""
        return {
            "fire_detection_owner": DataOwner(
                owner_id="fire_detection_owner",
                name="Sarah Chen",
                email="sarah.chen@fire.ca.gov",
                role=DataOwnershipRole.DATA_OWNER,
                department="CAL FIRE Operations",
                responsibilities=[
                    "Define data quality standards for fire detection data",
                    "Approve access requests for fire detection systems",
                    "Ensure compliance with fire safety regulations",
                    "Coordinate with NASA FIRMS data providers"
                ],
                contact_info={
                    "phone": "+1-916-555-0101",
                    "office": "Sacramento Operations Center",
                    "backup_contact": "fire.operations@fire.ca.gov"
                }
            ),

            "weather_data_steward": DataOwner(
                owner_id="weather_data_steward",
                name="Michael Rodriguez",
                email="michael.rodriguez@fire.ca.gov",
                role=DataOwnershipRole.DATA_STEWARD,
                department="CAL FIRE Meteorology",
                responsibilities=[
                    "Validate weather data quality and accuracy",
                    "Maintain relationships with NOAA data sources",
                    "Define weather data integration standards",
                    "Monitor data freshness and availability"
                ],
                contact_info={
                    "phone": "+1-916-555-0102",
                    "office": "Weather Coordination Center",
                    "backup_contact": "weather.team@fire.ca.gov"
                }
            ),

            "iot_sensor_custodian": DataOwner(
                owner_id="iot_sensor_custodian",
                name="Jessica Park",
                email="jessica.park@fire.ca.gov",
                role=DataOwnershipRole.DATA_CUSTODIAN,
                department="CAL FIRE Technology Services",
                responsibilities=[
                    "Manage IoT sensor network infrastructure",
                    "Ensure sensor data security and encryption",
                    "Coordinate sensor deployment and maintenance",
                    "Handle technical data access requests"
                ],
                contact_info={
                    "phone": "+1-916-555-0103",
                    "office": "Technology Operations Center",
                    "backup_contact": "tech.services@fire.ca.gov"
                }
            ),

            "satellite_data_owner": DataOwner(
                owner_id="satellite_data_owner",
                name="Dr. Robert Kim",
                email="robert.kim@fire.ca.gov",
                role=DataOwnershipRole.DATA_OWNER,
                department="CAL FIRE Research Division",
                responsibilities=[
                    "Oversee satellite imagery acquisition and processing",
                    "Define satellite data quality standards",
                    "Coordinate with external satellite data providers",
                    "Approve research data sharing agreements"
                ],
                contact_info={
                    "phone": "+1-916-555-0104",
                    "office": "Research and Development Center",
                    "backup_contact": "research.division@fire.ca.gov"
                }
            ),

            "compliance_officer": DataOwner(
                owner_id="compliance_officer",
                name="Amanda Thompson",
                email="amanda.thompson@fire.ca.gov",
                role=DataOwnershipRole.DATA_STEWARD,
                department="CAL FIRE Legal and Compliance",
                responsibilities=[
                    "Ensure data governance compliance",
                    "Manage legal hold procedures",
                    "Coordinate audit and regulatory responses",
                    "Oversee data privacy and security policies"
                ],
                contact_info={
                    "phone": "+1-916-555-0105",
                    "office": "Legal and Compliance Office",
                    "backup_contact": "legal.compliance@fire.ca.gov"
                }
            )
        }

    def _define_classification_rules(self) -> List[DataClassificationRule]:
        """Define data classification rules"""
        return [
            DataClassificationRule(
                rule_id="fire_detection_classification",
                data_type="fire_detection",
                classification=DataClassification.INTERNAL,
                criteria=[
                    "Real-time fire detection data from satellite sources",
                    "Contains location and timing information",
                    "Used for operational response decisions"
                ],
                justification="Contains sensitive operational information but not personal data",
                created_by="fire_detection_owner",
                created_date="2024-01-15",
                last_reviewed="2024-06-15"
            ),

            DataClassificationRule(
                rule_id="weather_data_classification",
                data_type="weather_data",
                classification=DataClassification.PUBLIC,
                criteria=[
                    "Weather observations from public sources",
                    "No personal or sensitive information",
                    "Publicly available from NOAA"
                ],
                justification="Public weather data available from government sources",
                created_by="weather_data_steward",
                created_date="2024-01-15",
                last_reviewed="2024-06-15"
            ),

            DataClassificationRule(
                rule_id="iot_sensor_classification",
                data_type="iot_sensor",
                classification=DataClassification.CONFIDENTIAL,
                criteria=[
                    "Contains precise sensor locations",
                    "Could reveal security infrastructure details",
                    "Includes device identifiers and network information"
                ],
                justification="Sensor locations and network details could compromise security",
                created_by="iot_sensor_custodian",
                created_date="2024-01-15",
                last_reviewed="2024-06-15"
            ),

            DataClassificationRule(
                rule_id="satellite_imagery_classification",
                data_type="satellite_imagery",
                classification=DataClassification.INTERNAL,
                criteria=[
                    "High-resolution imagery of California",
                    "Contains metadata about acquisition details",
                    "Used for scientific and operational analysis"
                ],
                justification="Internal use for operational and research purposes",
                created_by="satellite_data_owner",
                created_date="2024-01-15",
                last_reviewed="2024-06-15"
            ),

            DataClassificationRule(
                rule_id="operational_logs_classification",
                data_type="operational_logs",
                classification=DataClassification.RESTRICTED,
                criteria=[
                    "Contains system access logs and user activities",
                    "Includes authentication and authorization events",
                    "May contain personally identifiable information"
                ],
                justification="Contains sensitive security information and potential PII",
                created_by="compliance_officer",
                created_date="2024-01-15",
                last_reviewed="2024-06-15"
            )
        ]

    def _define_retention_schedules(self) -> List[RetentionSchedule]:
        """Define data retention schedules"""
        return [
            RetentionSchedule(
                schedule_id="fire_detection_retention",
                data_type="fire_detection",
                classification=DataClassification.INTERNAL,
                retention_period_days=2555,  # 7 years
                action_on_expiry=RetentionAction.ARCHIVE,
                legal_hold_exempt=False,
                business_justification="Required for historical analysis and legal compliance",
                regulatory_requirements=["CAL FIRE Records Retention Policy", "Public Records Act"]
            ),

            RetentionSchedule(
                schedule_id="weather_data_retention",
                data_type="weather_data",
                classification=DataClassification.PUBLIC,
                retention_period_days=3650,  # 10 years
                action_on_expiry=RetentionAction.ARCHIVE,
                legal_hold_exempt=True,
                business_justification="Long-term climate and weather pattern analysis",
                regulatory_requirements=["NOAA Data Retention Guidelines"]
            ),

            RetentionSchedule(
                schedule_id="iot_sensor_retention",
                data_type="iot_sensor",
                classification=DataClassification.CONFIDENTIAL,
                retention_period_days=1825,  # 5 years
                action_on_expiry=RetentionAction.DELETE,
                legal_hold_exempt=False,
                business_justification="Sensor performance analysis and maintenance planning",
                regulatory_requirements=["IoT Security Standards", "Privacy Protection Guidelines"]
            ),

            RetentionSchedule(
                schedule_id="satellite_imagery_retention",
                data_type="satellite_imagery",
                classification=DataClassification.INTERNAL,
                retention_period_days=5475,  # 15 years
                action_on_expiry=RetentionAction.PERMANENT,
                legal_hold_exempt=False,
                business_justification="Long-term environmental monitoring and research",
                regulatory_requirements=["Scientific Data Preservation Standards"]
            ),

            RetentionSchedule(
                schedule_id="operational_logs_retention",
                data_type="operational_logs",
                classification=DataClassification.RESTRICTED,
                retention_period_days=2555,  # 7 years
                action_on_expiry=RetentionAction.DELETE,
                legal_hold_exempt=False,
                business_justification="Audit and compliance requirements",
                regulatory_requirements=["SOX Compliance", "Cybersecurity Framework", "Audit Standards"]
            )
        ]

    def _define_metadata_schemas(self) -> Dict[str, MetadataSchema]:
        """Define metadata schemas for different data types"""
        return {
            "fire_detection_metadata": MetadataSchema(
                schema_id="fire_detection_metadata",
                data_type="fire_detection",
                required_fields=[
                    "record_id", "timestamp", "latitude", "longitude",
                    "data_source", "confidence_level", "created_date"
                ],
                optional_fields=[
                    "brightness", "satellite", "processing_version",
                    "quality_flags", "validation_status"
                ],
                field_types={
                    "record_id": "UUID",
                    "timestamp": "ISO8601_DATETIME",
                    "latitude": "FLOAT",
                    "longitude": "FLOAT",
                    "confidence_level": "INTEGER",
                    "data_source": "STRING"
                },
                validation_rules=[
                    "latitude BETWEEN -90 AND 90",
                    "longitude BETWEEN -180 AND 180",
                    "confidence_level BETWEEN 0 AND 100",
                    "timestamp NOT NULL"
                ],
                version="1.2.0"
            ),

            "weather_data_metadata": MetadataSchema(
                schema_id="weather_data_metadata",
                data_type="weather_data",
                required_fields=[
                    "record_id", "station_id", "timestamp", "latitude", "longitude",
                    "data_source", "created_date"
                ],
                optional_fields=[
                    "temperature", "humidity", "wind_speed", "wind_direction",
                    "pressure", "precipitation", "quality_code"
                ],
                field_types={
                    "record_id": "UUID",
                    "station_id": "STRING",
                    "timestamp": "ISO8601_DATETIME",
                    "temperature": "FLOAT",
                    "humidity": "FLOAT"
                },
                validation_rules=[
                    "temperature BETWEEN -50 AND 60",
                    "humidity BETWEEN 0 AND 100",
                    "station_id LENGTH BETWEEN 3 AND 10"
                ],
                version="1.1.0"
            ),

            "iot_sensor_metadata": MetadataSchema(
                schema_id="iot_sensor_metadata",
                data_type="iot_sensor",
                required_fields=[
                    "record_id", "sensor_id", "timestamp", "latitude", "longitude",
                    "created_date", "encryption_status"
                ],
                optional_fields=[
                    "temperature", "humidity", "smoke_level", "pm25",
                    "battery_level", "signal_strength", "device_status"
                ],
                field_types={
                    "record_id": "UUID",
                    "sensor_id": "STRING",
                    "encryption_status": "BOOLEAN",
                    "battery_level": "FLOAT",
                    "signal_strength": "INTEGER"
                },
                validation_rules=[
                    "sensor_id MATCHES '^[A-Z0-9]{8,16}$'",
                    "battery_level BETWEEN 0 AND 100",
                    "encryption_status = TRUE"
                ],
                version="1.3.0"
            )
        }

    def _define_governance_policies(self) -> Dict[str, Dict[str, Any]]:
        """Define comprehensive governance policies"""
        return {
            "data_quality_policy": {
                "policy_id": "DQ-001",
                "title": "Data Quality Standards and Procedures",
                "scope": "All wildfire intelligence data",
                "principles": [
                    "Accuracy: Data must be correct and error-free",
                    "Completeness: All required fields must be populated",
                    "Consistency: Data format must be standardized",
                    "Timeliness: Data must be current and up-to-date",
                    "Validity: Data must conform to defined rules and constraints"
                ],
                "quality_metrics": {
                    "accuracy_threshold": "99.5%",
                    "completeness_threshold": "98.0%",
                    "timeliness_sla": "< 5 minutes for real-time data"
                },
                "monitoring_procedures": [
                    "Automated data validation on ingestion",
                    "Daily quality reports for all data sources",
                    "Monthly quality reviews with data stewards",
                    "Quarterly quality assessments and improvements"
                ]
            },

            "access_control_policy": {
                "policy_id": "AC-001",
                "title": "Data Access Control and Authorization",
                "scope": "All system users and data access",
                "principles": [
                    "Least Privilege: Minimum access required for job function",
                    "Need to Know: Access based on business necessity",
                    "Regular Review: Periodic access rights validation",
                    "Audit Trail: Complete logging of all access activities"
                ],
                "access_levels": {
                    "public": "Read access to public data sources",
                    "internal": "Read access to internal operational data",
                    "confidential": "Limited read access with approval",
                    "restricted": "Admin access with dual authorization"
                },
                "approval_process": [
                    "Manager approval for internal data access",
                    "Data owner approval for confidential data",
                    "Security team approval for restricted data",
                    "Annual access rights recertification"
                ]
            },

            "privacy_protection_policy": {
                "policy_id": "PP-001",
                "title": "Privacy Protection and PII Handling",
                "scope": "All data containing personal information",
                "principles": [
                    "Data Minimization: Collect only necessary information",
                    "Purpose Limitation: Use data only for stated purposes",
                    "Consent Management: Obtain appropriate consent",
                    "Security by Design: Built-in privacy protections"
                ],
                "pii_categories": [
                    "Direct identifiers: Names, addresses, phone numbers",
                    "Indirect identifiers: IP addresses, device IDs",
                    "Sensitive data: Location tracks, behavior patterns"
                ],
                "protection_measures": [
                    "Data anonymization and pseudonymization",
                    "Encryption of PII at rest and in transit",
                    "Access controls and audit logging",
                    "Regular privacy impact assessments"
                ]
            },

            "legal_hold_policy": {
                "policy_id": "LH-001",
                "title": "Legal Hold and Litigation Support",
                "scope": "All data subject to legal proceedings",
                "procedures": [
                    "Legal hold notification and acknowledgment",
                    "Data preservation and isolation",
                    "Access restriction and monitoring",
                    "Regular hold status review and updates"
                ],
                "hold_triggers": [
                    "Litigation or potential litigation",
                    "Regulatory investigation or audit",
                    "Internal investigation procedures",
                    "FOIA or public records requests"
                ],
                "hold_management": [
                    "Centralized hold tracking system",
                    "Automated preservation workflows",
                    "Custodian training and responsibilities",
                    "Regular compliance monitoring"
                ]
            }
        }

    def get_governance_summary(self) -> Dict[str, Any]:
        """Generate comprehensive governance framework summary"""
        return {
            "framework_overview": {
                "total_data_owners": len(self.data_owners),
                "classification_rules": len(self.classification_rules),
                "retention_schedules": len(self.retention_schedules),
                "metadata_schemas": len(self.metadata_schemas),
                "governance_policies": len(self.governance_policies)
            },
            "data_ownership": {
                owner_id: asdict(owner) for owner_id, owner in self.data_owners.items()
            },
            "classification_framework": [asdict(rule) for rule in self.classification_rules],
            "retention_management": [asdict(schedule) for schedule in self.retention_schedules],
            "metadata_standards": {
                schema_id: asdict(schema) for schema_id, schema in self.metadata_schemas.items()
            },
            "governance_policies": self.governance_policies,
            "compliance_matrix": {
                "regulations_covered": [
                    "CAL FIRE Records Retention Policy",
                    "Public Records Act",
                    "NIST SP 800-53",
                    "FISMA",
                    "SOX Compliance",
                    "GDPR (for applicable data)",
                    "CCPA (California Consumer Privacy Act)"
                ],
                "security_frameworks": [
                    "NIST Cybersecurity Framework",
                    "ISO 27001",
                    "SOC 2 Type II"
                ]
            }
        }

    def export_governance_framework(self, filepath: str):
        """Export governance framework to JSON file"""
        framework = {
            "data_governance_framework": self.get_governance_summary(),
            "generated_at": datetime.now().isoformat(),
            "version": "2.0.0",
            "challenge": "CAL FIRE Challenge 2 - Data Storage Governance"
        }

        with open(filepath, 'w') as f:
            json.dump(framework, f, indent=2, default=str)

        print(f"📋 Data governance framework exported to: {filepath}")

# Global data governance framework instance
governance_framework = DataGovernanceFramework()

def get_governance_framework() -> DataGovernanceFramework:
    """Get the global data governance framework instance"""
    return governance_framework