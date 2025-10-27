"""
Data Quality Assurance Framework for Challenge 3
CAL FIRE Wildfire Intelligence Platform

This module implements comprehensive data quality assurance framework
as required by Challenge 3 specifications for ensuring data integrity,
accuracy, and reliability across all wildfire data sources.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
import json
import uuid
import statistics
import re
from pathlib import Path


class QualityRuleType(Enum):
    """Types of data quality rules"""
    COMPLETENESS = "completeness"
    ACCURACY = "accuracy"
    CONSISTENCY = "consistency"
    VALIDITY = "validity"
    UNIQUENESS = "uniqueness"
    TIMELINESS = "timeliness"
    INTEGRITY = "integrity"
    CONFORMITY = "conformity"


class QualitySeverity(Enum):
    """Severity levels for quality issues"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class QualityStatus(Enum):
    """Status of quality checks"""
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"


@dataclass
class QualityRule:
    """Definition of a data quality rule"""
    rule_id: str
    name: str
    description: str
    rule_type: QualityRuleType
    severity: QualitySeverity
    dataset_id: str
    field_name: Optional[str] = None
    logic: Dict[str, Any] = field(default_factory=dict)
    threshold: float = 95.0  # Quality threshold percentage
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = "system"


@dataclass
class QualityIssue:
    """Individual data quality issue"""
    issue_id: str
    rule_id: str
    dataset_id: str
    field_name: Optional[str]
    issue_type: QualityRuleType
    severity: QualitySeverity
    description: str
    record_count: int = 0
    sample_values: List[Any] = field(default_factory=list)
    detected_at: datetime = field(default_factory=datetime.utcnow)
    status: str = "open"  # open, in_progress, resolved, ignored
    resolution_notes: Optional[str] = None


@dataclass
class QualityCheckResult:
    """Result of a quality check execution"""
    check_id: str
    rule_id: str
    dataset_id: str
    status: QualityStatus
    score: float  # 0-100
    records_checked: int = 0
    issues_found: int = 0
    execution_time_ms: float = 0.0
    executed_at: datetime = field(default_factory=datetime.utcnow)
    details: Dict[str, Any] = field(default_factory=dict)
    issues: List[QualityIssue] = field(default_factory=list)


@dataclass
class QualityAssessment:
    """Comprehensive quality assessment for a dataset"""
    assessment_id: str
    dataset_id: str
    overall_score: float = 0.0
    completeness_score: float = 0.0
    accuracy_score: float = 0.0
    consistency_score: float = 0.0
    validity_score: float = 0.0
    uniqueness_score: float = 0.0
    timeliness_score: float = 0.0
    total_records: int = 0
    total_issues: int = 0
    critical_issues: int = 0
    check_results: List[QualityCheckResult] = field(default_factory=list)
    executed_at: datetime = field(default_factory=datetime.utcnow)
    execution_time_ms: float = 0.0


@dataclass
class QualityReport:
    """Quality report for multiple datasets"""
    report_id: str
    report_type: str
    period_start: datetime
    period_end: datetime
    datasets_assessed: List[str]
    overall_quality_score: float = 0.0
    assessments: List[QualityAssessment] = field(default_factory=list)
    trends: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.utcnow)


class QualityRuleEngine:
    """Engine for defining and executing quality rules"""

    def __init__(self):
        self.rules: Dict[str, QualityRule] = {}
        self._initialize_default_rules()

    def _initialize_default_rules(self):
        """Initialize default quality rules for wildfire data"""

        # NASA FIRMS data quality rules
        firms_rules = [
            QualityRule(
                rule_id="firms_lat_lon_completeness",
                name="Fire Location Completeness",
                description="Latitude and longitude must be present for all fire detections",
                rule_type=QualityRuleType.COMPLETENESS,
                severity=QualitySeverity.CRITICAL,
                dataset_id="nasa_firms_fire_data",
                field_name="latitude,longitude",
                logic={"required_fields": ["latitude", "longitude"]},
                threshold=99.5
            ),
            QualityRule(
                rule_id="firms_lat_validity",
                name="Latitude Range Validity",
                description="Latitude values must be between -90 and 90",
                rule_type=QualityRuleType.VALIDITY,
                severity=QualitySeverity.HIGH,
                dataset_id="nasa_firms_fire_data",
                field_name="latitude",
                logic={"min_value": -90.0, "max_value": 90.0},
                threshold=99.9
            ),
            QualityRule(
                rule_id="firms_lon_validity",
                name="Longitude Range Validity",
                description="Longitude values must be between -180 and 180",
                rule_type=QualityRuleType.VALIDITY,
                severity=QualitySeverity.HIGH,
                dataset_id="nasa_firms_fire_data",
                field_name="longitude",
                logic={"min_value": -180.0, "max_value": 180.0},
                threshold=99.9
            ),
            QualityRule(
                rule_id="firms_confidence_validity",
                name="Confidence Level Validity",
                description="Confidence values must be between 0 and 100",
                rule_type=QualityRuleType.VALIDITY,
                severity=QualitySeverity.MEDIUM,
                dataset_id="nasa_firms_fire_data",
                field_name="confidence",
                logic={"min_value": 0, "max_value": 100, "allow_null": True},
                threshold=95.0
            ),
            QualityRule(
                rule_id="firms_brightness_validity",
                name="Brightness Temperature Validity",
                description="Brightness temperature should be reasonable for fire detection",
                rule_type=QualityRuleType.VALIDITY,
                severity=QualitySeverity.MEDIUM,
                dataset_id="nasa_firms_fire_data",
                field_name="brightness",
                logic={"min_value": 250.0, "max_value": 500.0, "allow_null": True},
                threshold=90.0
            ),
            QualityRule(
                rule_id="firms_duplicates",
                name="Fire Detection Uniqueness",
                description="No duplicate fire detections at same location and time",
                rule_type=QualityRuleType.UNIQUENESS,
                severity=QualitySeverity.HIGH,
                dataset_id="nasa_firms_fire_data",
                logic={"unique_fields": ["latitude", "longitude", "acq_date", "acq_time"]},
                threshold=98.0
            ),
            QualityRule(
                rule_id="firms_timeliness",
                name="Fire Data Timeliness",
                description="Fire detections should be processed within 4 hours",
                rule_type=QualityRuleType.TIMELINESS,
                severity=QualitySeverity.HIGH,
                dataset_id="nasa_firms_fire_data",
                field_name="acq_date",
                logic={"max_age_hours": 4},
                threshold=95.0
            )
        ]

        # NOAA Weather data quality rules
        weather_rules = [
            QualityRule(
                rule_id="weather_station_completeness",
                name="Weather Station ID Completeness",
                description="Station ID must be present for all observations",
                rule_type=QualityRuleType.COMPLETENESS,
                severity=QualitySeverity.CRITICAL,
                dataset_id="noaa_weather_observations",
                field_name="station_id",
                logic={"required_fields": ["station_id"]},
                threshold=100.0
            ),
            QualityRule(
                rule_id="weather_temp_validity",
                name="Temperature Range Validity",
                description="Temperature should be within reasonable range for California",
                rule_type=QualityRuleType.VALIDITY,
                severity=QualitySeverity.MEDIUM,
                dataset_id="noaa_weather_observations",
                field_name="temperature_f",
                logic={"min_value": -10.0, "max_value": 130.0, "allow_null": True},
                threshold=98.0
            ),
            QualityRule(
                rule_id="weather_humidity_validity",
                name="Humidity Range Validity",
                description="Humidity must be between 0 and 100 percent",
                rule_type=QualityRuleType.VALIDITY,
                severity=QualitySeverity.HIGH,
                dataset_id="noaa_weather_observations",
                field_name="humidity",
                logic={"min_value": 0.0, "max_value": 100.0, "allow_null": True},
                threshold=99.0
            ),
            QualityRule(
                rule_id="weather_wind_validity",
                name="Wind Speed Validity",
                description="Wind speed should be reasonable (0-200 mph)",
                rule_type=QualityRuleType.VALIDITY,
                severity=QualitySeverity.MEDIUM,
                dataset_id="noaa_weather_observations",
                field_name="wind_speed_mph",
                logic={"min_value": 0.0, "max_value": 200.0, "allow_null": True},
                threshold=97.0
            ),
            QualityRule(
                rule_id="weather_consistency",
                name="Weather Data Consistency",
                description="Check for impossible weather combinations",
                rule_type=QualityRuleType.CONSISTENCY,
                severity=QualitySeverity.MEDIUM,
                dataset_id="noaa_weather_observations",
                logic={
                    "consistency_checks": [
                        {"condition": "humidity > 95 AND precipitation = 0", "severity": "warning"},
                        {"condition": "temperature_f > 100 AND humidity > 80", "severity": "warning"}
                    ]
                },
                threshold=92.0
            )
        ]

        # CAL FIRE Incidents quality rules
        incident_rules = [
            QualityRule(
                rule_id="incident_id_completeness",
                name="Incident ID Completeness",
                description="Every incident must have a unique identifier",
                rule_type=QualityRuleType.COMPLETENESS,
                severity=QualitySeverity.CRITICAL,
                dataset_id="calfire_incidents",
                field_name="incident_id",
                logic={"required_fields": ["incident_id"]},
                threshold=100.0
            ),
            QualityRule(
                rule_id="incident_acres_validity",
                name="Acres Burned Validity",
                description="Acres burned should be a positive number",
                rule_type=QualityRuleType.VALIDITY,
                severity=QualitySeverity.HIGH,
                dataset_id="calfire_incidents",
                field_name="acres_burned",
                logic={"min_value": 0.0, "max_value": 2000000.0, "allow_null": True},
                threshold=95.0
            ),
            QualityRule(
                rule_id="incident_containment_validity",
                name="Containment Percentage Validity",
                description="Containment must be between 0 and 100 percent",
                rule_type=QualityRuleType.VALIDITY,
                severity=QualitySeverity.HIGH,
                dataset_id="calfire_incidents",
                field_name="percent_contained",
                logic={"min_value": 0.0, "max_value": 100.0, "allow_null": True},
                threshold=98.0
            ),
            QualityRule(
                rule_id="incident_date_consistency",
                name="Incident Date Consistency",
                description="Start date should not be in the future",
                rule_type=QualityRuleType.CONSISTENCY,
                severity=QualitySeverity.HIGH,
                dataset_id="calfire_incidents",
                field_name="start_date",
                logic={"max_date": "now", "allow_null": True},
                threshold=99.0
            )
        ]

        # Store all rules
        all_rules = firms_rules + weather_rules + incident_rules
        for rule in all_rules:
            self.rules[rule.rule_id] = rule

    def add_rule(self, rule: QualityRule) -> bool:
        """Add a new quality rule"""
        try:
            self.rules[rule.rule_id] = rule
            print(f"✅ Quality rule added: {rule.name}")
            return True
        except Exception as e:
            print(f"❌ Failed to add rule {rule.rule_id}: {str(e)}")
            return False

    def get_rules_for_dataset(self, dataset_id: str) -> List[QualityRule]:
        """Get all active rules for a dataset"""
        return [rule for rule in self.rules.values()
                if rule.dataset_id == dataset_id and rule.is_active]

    def execute_rule(self, rule: QualityRule, data: List[Dict[str, Any]]) -> QualityCheckResult:
        """Execute a quality rule against data"""
        start_time = datetime.utcnow()

        check_result = QualityCheckResult(
            check_id=str(uuid.uuid4()),
            rule_id=rule.rule_id,
            dataset_id=rule.dataset_id,
            status=QualityStatus.PASSED,
            score=100.0,
            records_checked=len(data)
        )

        try:
            if rule.rule_type == QualityRuleType.COMPLETENESS:
                check_result = self._check_completeness(rule, data, check_result)
            elif rule.rule_type == QualityRuleType.VALIDITY:
                check_result = self._check_validity(rule, data, check_result)
            elif rule.rule_type == QualityRuleType.UNIQUENESS:
                check_result = self._check_uniqueness(rule, data, check_result)
            elif rule.rule_type == QualityRuleType.CONSISTENCY:
                check_result = self._check_consistency(rule, data, check_result)
            elif rule.rule_type == QualityRuleType.TIMELINESS:
                check_result = self._check_timeliness(rule, data, check_result)
            else:
                check_result.status = QualityStatus.SKIPPED
                check_result.score = 0.0

            # Determine overall status based on score and threshold
            if check_result.score >= rule.threshold:
                check_result.status = QualityStatus.PASSED
            elif check_result.score >= rule.threshold * 0.8:
                check_result.status = QualityStatus.WARNING
            else:
                check_result.status = QualityStatus.FAILED

        except Exception as e:
            check_result.status = QualityStatus.FAILED
            check_result.score = 0.0
            check_result.details["error"] = str(e)

        # Calculate execution time
        end_time = datetime.utcnow()
        check_result.execution_time_ms = (end_time - start_time).total_seconds() * 1000

        return check_result

    def _check_completeness(self, rule: QualityRule, data: List[Dict[str, Any]],
                          result: QualityCheckResult) -> QualityCheckResult:
        """Check data completeness"""
        if not data:
            result.score = 0.0
            return result

        required_fields = rule.logic.get("required_fields", [])
        if not required_fields and rule.field_name:
            required_fields = rule.field_name.split(',')

        total_checks = len(data) * len(required_fields)
        missing_count = 0
        sample_missing = []

        for record in data:
            for field in required_fields:
                if field not in record or record[field] is None or record[field] == "":
                    missing_count += 1
                    if len(sample_missing) < 5:
                        sample_missing.append(f"Missing {field} in record")

        if missing_count > 0:
            issue = QualityIssue(
                issue_id=str(uuid.uuid4()),
                rule_id=rule.rule_id,
                dataset_id=rule.dataset_id,
                field_name=rule.field_name,
                issue_type=rule.rule_type,
                severity=rule.severity,
                description=f"Missing values in required fields: {', '.join(required_fields)}",
                record_count=missing_count,
                sample_values=sample_missing[:5]
            )
            result.issues.append(issue)
            result.issues_found = missing_count

        result.score = ((total_checks - missing_count) / total_checks * 100) if total_checks > 0 else 100.0
        result.details = {"total_checks": total_checks, "missing_count": missing_count}

        return result

    def _check_validity(self, rule: QualityRule, data: List[Dict[str, Any]],
                       result: QualityCheckResult) -> QualityCheckResult:
        """Check data validity (range, format, etc.)"""
        if not data or not rule.field_name:
            return result

        field_name = rule.field_name
        logic = rule.logic
        invalid_count = 0
        sample_invalid = []

        for record in data:
            if field_name not in record:
                continue

            value = record[field_name]

            # Allow null values if specified
            if value is None and logic.get("allow_null", False):
                continue

            if value is None and not logic.get("allow_null", False):
                invalid_count += 1
                if len(sample_invalid) < 5:
                    sample_invalid.append(f"Null value in {field_name}")
                continue

            # Range checks
            if "min_value" in logic and value < logic["min_value"]:
                invalid_count += 1
                if len(sample_invalid) < 5:
                    sample_invalid.append(f"{field_name}={value} below minimum {logic['min_value']}")

            if "max_value" in logic and value > logic["max_value"]:
                invalid_count += 1
                if len(sample_invalid) < 5:
                    sample_invalid.append(f"{field_name}={value} above maximum {logic['max_value']}")

            # Pattern matching for strings
            if "pattern" in logic and isinstance(value, str):
                if not re.match(logic["pattern"], value):
                    invalid_count += 1
                    if len(sample_invalid) < 5:
                        sample_invalid.append(f"{field_name}='{value}' doesn't match pattern")

        if invalid_count > 0:
            issue = QualityIssue(
                issue_id=str(uuid.uuid4()),
                rule_id=rule.rule_id,
                dataset_id=rule.dataset_id,
                field_name=field_name,
                issue_type=rule.rule_type,
                severity=rule.severity,
                description=f"Invalid values in field {field_name}",
                record_count=invalid_count,
                sample_values=sample_invalid[:5]
            )
            result.issues.append(issue)
            result.issues_found = invalid_count

        result.score = ((len(data) - invalid_count) / len(data) * 100) if len(data) > 0 else 100.0
        result.details = {"total_records": len(data), "invalid_count": invalid_count}

        return result

    def _check_uniqueness(self, rule: QualityRule, data: List[Dict[str, Any]],
                         result: QualityCheckResult) -> QualityCheckResult:
        """Check data uniqueness"""
        if not data:
            return result

        unique_fields = rule.logic.get("unique_fields", [])
        if not unique_fields and rule.field_name:
            unique_fields = rule.field_name.split(',')

        seen_combinations = set()
        duplicate_count = 0
        sample_duplicates = []

        for record in data:
            # Create combination key
            key_parts = []
            for field in unique_fields:
                key_parts.append(str(record.get(field, "")))
            combination_key = "|".join(key_parts)

            if combination_key in seen_combinations:
                duplicate_count += 1
                if len(sample_duplicates) < 5:
                    sample_duplicates.append(f"Duplicate: {combination_key}")
            else:
                seen_combinations.add(combination_key)

        if duplicate_count > 0:
            issue = QualityIssue(
                issue_id=str(uuid.uuid4()),
                rule_id=rule.rule_id,
                dataset_id=rule.dataset_id,
                field_name=rule.field_name,
                issue_type=rule.rule_type,
                severity=rule.severity,
                description=f"Duplicate records found for fields: {', '.join(unique_fields)}",
                record_count=duplicate_count,
                sample_values=sample_duplicates[:5]
            )
            result.issues.append(issue)
            result.issues_found = duplicate_count

        result.score = ((len(data) - duplicate_count) / len(data) * 100) if len(data) > 0 else 100.0
        result.details = {"total_records": len(data), "duplicate_count": duplicate_count}

        return result

    def _check_consistency(self, rule: QualityRule, data: List[Dict[str, Any]],
                          result: QualityCheckResult) -> QualityCheckResult:
        """Check data consistency"""
        if not data:
            return result

        consistency_checks = rule.logic.get("consistency_checks", [])
        inconsistent_count = 0
        sample_issues = []

        for record in data:
            for check in consistency_checks:
                condition = check.get("condition", "")
                if self._evaluate_consistency_condition(condition, record):
                    inconsistent_count += 1
                    if len(sample_issues) < 5:
                        sample_issues.append(f"Inconsistency: {condition}")

        if inconsistent_count > 0:
            issue = QualityIssue(
                issue_id=str(uuid.uuid4()),
                rule_id=rule.rule_id,
                dataset_id=rule.dataset_id,
                field_name=rule.field_name,
                issue_type=rule.rule_type,
                severity=rule.severity,
                description="Data consistency violations found",
                record_count=inconsistent_count,
                sample_values=sample_issues[:5]
            )
            result.issues.append(issue)
            result.issues_found = inconsistent_count

        result.score = ((len(data) - inconsistent_count) / len(data) * 100) if len(data) > 0 else 100.0
        result.details = {"total_records": len(data), "inconsistent_count": inconsistent_count}

        return result

    def _check_timeliness(self, rule: QualityRule, data: List[Dict[str, Any]],
                         result: QualityCheckResult) -> QualityCheckResult:
        """Check data timeliness"""
        if not data or not rule.field_name:
            return result

        field_name = rule.field_name
        max_age_hours = rule.logic.get("max_age_hours", 24)
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)

        late_count = 0
        sample_late = []

        for record in data:
            if field_name not in record:
                continue

            # Parse date (simplified for demo)
            record_date = record.get(field_name)
            if isinstance(record_date, str):
                try:
                    # Assume ISO format or similar
                    if 'T' in record_date:
                        record_date = datetime.fromisoformat(record_date.replace('Z', '+00:00'))
                    else:
                        record_date = datetime.strptime(record_date, '%Y-%m-%d')
                except:
                    record_date = None

            if record_date and record_date < cutoff_time:
                late_count += 1
                if len(sample_late) < 5:
                    sample_late.append(f"Late data: {field_name}={record_date}")

        if late_count > 0:
            issue = QualityIssue(
                issue_id=str(uuid.uuid4()),
                rule_id=rule.rule_id,
                dataset_id=rule.dataset_id,
                field_name=field_name,
                issue_type=rule.rule_type,
                severity=rule.severity,
                description=f"Data older than {max_age_hours} hours",
                record_count=late_count,
                sample_values=sample_late[:5]
            )
            result.issues.append(issue)
            result.issues_found = late_count

        result.score = ((len(data) - late_count) / len(data) * 100) if len(data) > 0 else 100.0
        result.details = {"total_records": len(data), "late_count": late_count}

        return result

    def _evaluate_consistency_condition(self, condition: str, record: Dict[str, Any]) -> bool:
        """Evaluate a consistency condition (simplified)"""
        try:
            # Replace field names with actual values
            for field_name, value in record.items():
                if isinstance(value, (int, float)):
                    condition = condition.replace(field_name, str(value))
                else:
                    condition = condition.replace(field_name, f"'{value}'")

            # Simple evaluation (in production, use safer expression evaluator)
            condition = condition.replace(" AND ", " and ").replace(" OR ", " or ")
            condition = condition.replace("=", "==")

            return eval(condition)
        except:
            return False


class DataQualityManager:
    """Main data quality management system"""

    def __init__(self):
        self.rule_engine = QualityRuleEngine()
        self.assessments: Dict[str, QualityAssessment] = {}
        self.quality_reports: Dict[str, QualityReport] = {}
        self.quality_history: List[QualityAssessment] = []

    async def assess_dataset_quality(self, dataset_id: str, data: List[Dict[str, Any]]) -> QualityAssessment:
        """Perform comprehensive quality assessment of a dataset"""
        start_time = datetime.utcnow()

        assessment = QualityAssessment(
            assessment_id=str(uuid.uuid4()),
            dataset_id=dataset_id,
            total_records=len(data)
        )

        # Get all rules for this dataset
        rules = self.rule_engine.get_rules_for_dataset(dataset_id)

        print(f"🔍 Assessing quality for {dataset_id} with {len(rules)} rules...")

        # Execute each rule
        for rule in rules:
            check_result = self.rule_engine.execute_rule(rule, data)
            assessment.check_results.append(check_result)

            # Count issues by severity
            for issue in check_result.issues:
                if issue.severity == QualitySeverity.CRITICAL:
                    assessment.critical_issues += 1
                assessment.total_issues += 1

        # Calculate dimension scores
        assessment = self._calculate_dimension_scores(assessment)

        # Calculate overall score
        scores = [
            assessment.completeness_score,
            assessment.accuracy_score,
            assessment.consistency_score,
            assessment.validity_score,
            assessment.uniqueness_score,
            assessment.timeliness_score
        ]
        valid_scores = [s for s in scores if s > 0]
        assessment.overall_score = statistics.mean(valid_scores) if valid_scores else 0.0

        # Calculate execution time
        end_time = datetime.utcnow()
        assessment.execution_time_ms = (end_time - start_time).total_seconds() * 1000

        # Store assessment
        self.assessments[assessment.assessment_id] = assessment
        self.quality_history.append(assessment)

        print(f"✅ Quality assessment completed: {assessment.overall_score:.1f}/100")
        return assessment

    def _calculate_dimension_scores(self, assessment: QualityAssessment) -> QualityAssessment:
        """Calculate scores for each quality dimension"""
        dimension_scores = {}

        for result in assessment.check_results:
            rule = self.rule_engine.rules[result.rule_id]
            dimension = rule.rule_type.value

            if dimension not in dimension_scores:
                dimension_scores[dimension] = []
            dimension_scores[dimension].append(result.score)

        # Calculate average score for each dimension
        assessment.completeness_score = statistics.mean(
            dimension_scores.get("completeness", [0])
        ) if "completeness" in dimension_scores else 0.0

        assessment.accuracy_score = statistics.mean(
            dimension_scores.get("accuracy", [0])
        ) if "accuracy" in dimension_scores else 0.0

        assessment.consistency_score = statistics.mean(
            dimension_scores.get("consistency", [0])
        ) if "consistency" in dimension_scores else 0.0

        assessment.validity_score = statistics.mean(
            dimension_scores.get("validity", [0])
        ) if "validity" in dimension_scores else 0.0

        assessment.uniqueness_score = statistics.mean(
            dimension_scores.get("uniqueness", [0])
        ) if "uniqueness" in dimension_scores else 0.0

        assessment.timeliness_score = statistics.mean(
            dimension_scores.get("timeliness", [0])
        ) if "timeliness" in dimension_scores else 0.0

        return assessment

    def generate_quality_report(self, dataset_ids: List[str], days: int = 30) -> QualityReport:
        """Generate comprehensive quality report"""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        report = QualityReport(
            report_id=str(uuid.uuid4()),
            report_type="comprehensive_quality_report",
            period_start=start_date,
            period_end=end_date,
            datasets_assessed=dataset_ids
        )

        # Get recent assessments for specified datasets
        recent_assessments = [
            a for a in self.quality_history
            if a.dataset_id in dataset_ids and a.executed_at >= start_date
        ]

        # Get latest assessment for each dataset
        latest_assessments = {}
        for assessment in recent_assessments:
            dataset_id = assessment.dataset_id
            if (dataset_id not in latest_assessments or
                assessment.executed_at > latest_assessments[dataset_id].executed_at):
                latest_assessments[dataset_id] = assessment

        report.assessments = list(latest_assessments.values())

        # Calculate overall quality score
        if report.assessments:
            report.overall_quality_score = statistics.mean(
                [a.overall_score for a in report.assessments]
            )

        # Analyze trends
        report.trends = self._analyze_quality_trends(recent_assessments, days)

        # Generate recommendations
        report.recommendations = self._generate_quality_recommendations(report.assessments)

        self.quality_reports[report.report_id] = report
        return report

    def _analyze_quality_trends(self, assessments: List[QualityAssessment], days: int) -> Dict[str, Any]:
        """Analyze quality trends over time"""
        if not assessments:
            return {}

        # Group assessments by dataset
        dataset_assessments = {}
        for assessment in assessments:
            if assessment.dataset_id not in dataset_assessments:
                dataset_assessments[assessment.dataset_id] = []
            dataset_assessments[assessment.dataset_id].append(assessment)

        trends = {}
        for dataset_id, dataset_assessments_list in dataset_assessments.items():
            if len(dataset_assessments_list) < 2:
                continue

            # Sort by time
            sorted_assessments = sorted(dataset_assessments_list, key=lambda x: x.executed_at)

            # Calculate trend
            first_score = sorted_assessments[0].overall_score
            last_score = sorted_assessments[-1].overall_score
            trend_direction = "improving" if last_score > first_score else "declining"
            trend_magnitude = abs(last_score - first_score)

            trends[dataset_id] = {
                "direction": trend_direction,
                "magnitude": trend_magnitude,
                "first_score": first_score,
                "last_score": last_score,
                "assessments_count": len(sorted_assessments)
            }

        return trends

    def _generate_quality_recommendations(self, assessments: List[QualityAssessment]) -> List[str]:
        """Generate quality improvement recommendations"""
        recommendations = []

        for assessment in assessments:
            dataset_id = assessment.dataset_id

            # Critical issues
            if assessment.critical_issues > 0:
                recommendations.append(
                    f"Address {assessment.critical_issues} critical quality issues in {dataset_id}"
                )

            # Low dimension scores
            if assessment.completeness_score < 90:
                recommendations.append(
                    f"Improve data completeness for {dataset_id} (current: {assessment.completeness_score:.1f}%)"
                )

            if assessment.validity_score < 85:
                recommendations.append(
                    f"Implement stronger validation rules for {dataset_id} (current: {assessment.validity_score:.1f}%)"
                )

            if assessment.uniqueness_score < 95:
                recommendations.append(
                    f"Address duplicate records in {dataset_id} (current: {assessment.uniqueness_score:.1f}%)"
                )

            if assessment.timeliness_score < 90:
                recommendations.append(
                    f"Improve data ingestion timeliness for {dataset_id} (current: {assessment.timeliness_score:.1f}%)"
                )

        # Remove duplicates and limit
        recommendations = list(set(recommendations))[:10]

        return recommendations

    def get_quality_dashboard_data(self) -> Dict[str, Any]:
        """Get data for quality dashboard"""
        recent_assessments = self.quality_history[-10:] if self.quality_history else []

        if not recent_assessments:
            return {"message": "No quality assessments available"}

        # Calculate overall metrics
        avg_quality_score = statistics.mean([a.overall_score for a in recent_assessments])
        total_issues = sum([a.total_issues for a in recent_assessments])
        critical_issues = sum([a.critical_issues for a in recent_assessments])

        # Quality distribution
        excellent_count = len([a for a in recent_assessments if a.overall_score >= 90])
        good_count = len([a for a in recent_assessments if 75 <= a.overall_score < 90])
        fair_count = len([a for a in recent_assessments if 60 <= a.overall_score < 75])
        poor_count = len([a for a in recent_assessments if a.overall_score < 60])

        return {
            "summary": {
                "avg_quality_score": avg_quality_score,
                "total_assessments": len(recent_assessments),
                "total_issues": total_issues,
                "critical_issues": critical_issues
            },
            "quality_distribution": {
                "excellent": excellent_count,
                "good": good_count,
                "fair": fair_count,
                "poor": poor_count
            },
            "recent_assessments": [
                {
                    "assessment_id": a.assessment_id,
                    "dataset_id": a.dataset_id,
                    "overall_score": a.overall_score,
                    "total_issues": a.total_issues,
                    "executed_at": a.executed_at.isoformat()
                }
                for a in sorted(recent_assessments, key=lambda x: x.executed_at, reverse=True)[:5]
            ],
            "dimension_averages": {
                "completeness": statistics.mean([a.completeness_score for a in recent_assessments]),
                "validity": statistics.mean([a.validity_score for a in recent_assessments]),
                "uniqueness": statistics.mean([a.uniqueness_score for a in recent_assessments]),
                "consistency": statistics.mean([a.consistency_score for a in recent_assessments]),
                "timeliness": statistics.mean([a.timeliness_score for a in recent_assessments])
            }
        }


def generate_sample_data(dataset_id: str, count: int = 100) -> List[Dict[str, Any]]:
    """Generate sample data for quality testing"""
    import random

    if dataset_id == "nasa_firms_fire_data":
        data = []
        for i in range(count):
            # Introduce some quality issues intentionally
            lat = 36.0 + random.uniform(-2, 2)
            lon = -119.0 + random.uniform(-2, 2)

            # Some invalid coordinates (5% of data)
            if random.random() < 0.05:
                lat = random.uniform(-200, 200)  # Invalid latitude
            if random.random() < 0.05:
                lon = random.uniform(-300, 300)  # Invalid longitude

            record = {
                "latitude": lat if random.random() > 0.02 else None,  # 2% missing
                "longitude": lon if random.random() > 0.02 else None,  # 2% missing
                "brightness": random.uniform(280, 450) if random.random() > 0.1 else None,
                "confidence": random.randint(20, 100) if random.random() > 0.15 else None,
                "acq_date": f"2024-01-{random.randint(1, 28):02d}",
                "acq_time": f"{random.randint(0, 23):02d}{random.randint(0, 59):02d}",
                "satellite": random.choice(["Terra", "Aqua", "NOAA-20"]),
                "frp": random.uniform(10, 500) if random.random() > 0.2 else None
            }
            data.append(record)

        # Add some duplicates (2% of data)
        duplicates_count = int(count * 0.02)
        for _ in range(duplicates_count):
            data.append(data[random.randint(0, len(data)-1)])

        return data

    elif dataset_id == "noaa_weather_observations":
        data = []
        for i in range(count):
            # Some invalid values
            temp = random.uniform(30, 110)
            if random.random() < 0.03:  # 3% invalid temperatures
                temp = random.uniform(-50, 150)

            humidity = random.uniform(10, 100)
            if random.random() < 0.02:  # 2% invalid humidity
                humidity = random.uniform(-10, 120)

            record = {
                "station_id": f"CA{random.randint(1000, 9999)}" if random.random() > 0.01 else None,
                "temperature_f": temp if random.random() > 0.05 else None,
                "humidity": humidity if random.random() > 0.08 else None,
                "wind_speed_mph": random.uniform(0, 45) if random.random() > 0.1 else None,
                "wind_direction": random.uniform(0, 360),
                "precipitation": random.uniform(0, 2.0),
                "timestamp": datetime.utcnow() - timedelta(hours=random.randint(0, 48))
            }
            data.append(record)
        return data

    elif dataset_id == "calfire_incidents":
        data = []
        for i in range(count):
            record = {
                "incident_id": f"CA-2024-{i+1000}" if random.random() > 0.005 else None,  # 0.5% missing IDs
                "incident_name": f"Fire {i+1}",
                "acres_burned": random.uniform(1, 50000) if random.random() > 0.1 else None,
                "percent_contained": random.uniform(0, 100) if random.random() > 0.15 else None,
                "start_date": f"2024-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
                "county": random.choice(["Los Angeles", "Orange", "Riverside", "San Bernardino"])
            }

            # Some invalid containment percentages
            if random.random() < 0.02:
                record["percent_contained"] = random.uniform(-10, 150)

            data.append(record)
        return data

    return []


async def demo_data_quality_framework():
    """Demonstrate the data quality framework"""
    print("🔍 CAL FIRE Data Quality Assurance Framework Demo")
    print("=" * 60)

    # Initialize quality manager
    quality_manager = DataQualityManager()

    # Demo 1: Quality assessment for NASA FIRMS data
    print("\n📊 Demo 1: NASA FIRMS Data Quality Assessment")
    firms_data = generate_sample_data("nasa_firms_fire_data", 500)

    firms_assessment = await quality_manager.assess_dataset_quality("nasa_firms_fire_data", firms_data)
    print(f"✅ Overall Quality Score: {firms_assessment.overall_score:.1f}/100")
    print(f"   Completeness: {firms_assessment.completeness_score:.1f}/100")
    print(f"   Validity: {firms_assessment.validity_score:.1f}/100")
    print(f"   Uniqueness: {firms_assessment.uniqueness_score:.1f}/100")
    print(f"   Total Issues: {firms_assessment.total_issues}")
    print(f"   Critical Issues: {firms_assessment.critical_issues}")

    # Demo 2: Quality assessment for NOAA weather data
    print("\n🌦️ Demo 2: NOAA Weather Data Quality Assessment")
    weather_data = generate_sample_data("noaa_weather_observations", 300)

    weather_assessment = await quality_manager.assess_dataset_quality("noaa_weather_observations", weather_data)
    print(f"✅ Overall Quality Score: {weather_assessment.overall_score:.1f}/100")
    print(f"   Completeness: {weather_assessment.completeness_score:.1f}/100")
    print(f"   Validity: {weather_assessment.validity_score:.1f}/100")
    print(f"   Consistency: {weather_assessment.consistency_score:.1f}/100")
    print(f"   Total Issues: {weather_assessment.total_issues}")

    # Demo 3: Quality assessment for CAL FIRE incidents
    print("\n🔥 Demo 3: CAL FIRE Incidents Quality Assessment")
    incidents_data = generate_sample_data("calfire_incidents", 200)

    incidents_assessment = await quality_manager.assess_dataset_quality("calfire_incidents", incidents_data)
    print(f"✅ Overall Quality Score: {incidents_assessment.overall_score:.1f}/100")
    print(f"   Completeness: {incidents_assessment.completeness_score:.1f}/100")
    print(f"   Validity: {incidents_assessment.validity_score:.1f}/100")
    print(f"   Consistency: {incidents_assessment.consistency_score:.1f}/100")
    print(f"   Total Issues: {incidents_assessment.total_issues}")

    # Demo 4: Quality issues analysis
    print("\n🔍 Demo 4: Quality Issues Analysis")
    all_issues = []
    for assessment in [firms_assessment, weather_assessment, incidents_assessment]:
        for result in assessment.check_results:
            all_issues.extend(result.issues)

    critical_issues = [i for i in all_issues if i.severity == QualitySeverity.CRITICAL]
    high_issues = [i for i in all_issues if i.severity == QualitySeverity.HIGH]

    print(f"✅ Total Quality Issues Found: {len(all_issues)}")
    print(f"   Critical: {len(critical_issues)}")
    print(f"   High: {len(high_issues)}")

    if critical_issues:
        print(f"\n🚨 Sample Critical Issue:")
        issue = critical_issues[0]
        print(f"   Dataset: {issue.dataset_id}")
        print(f"   Description: {issue.description}")
        print(f"   Affected Records: {issue.record_count}")

    # Demo 5: Quality report generation
    print("\n📋 Demo 5: Comprehensive Quality Report")

    dataset_ids = ["nasa_firms_fire_data", "noaa_weather_observations", "calfire_incidents"]
    quality_report = quality_manager.generate_quality_report(dataset_ids, 30)

    print(f"✅ Quality Report Generated: {quality_report.report_id}")
    print(f"   Overall Quality Score: {quality_report.overall_quality_score:.1f}/100")
    print(f"   Datasets Assessed: {len(quality_report.datasets_assessed)}")
    print(f"   Recommendations: {len(quality_report.recommendations)}")

    if quality_report.recommendations:
        print(f"\n💡 Top Recommendations:")
        for i, rec in enumerate(quality_report.recommendations[:3], 1):
            print(f"   {i}. {rec}")

    # Demo 6: Quality dashboard
    print("\n📈 Demo 6: Quality Dashboard")

    dashboard_data = quality_manager.get_quality_dashboard_data()
    summary = dashboard_data["summary"]

    print(f"✅ Quality Dashboard Summary:")
    print(f"   Average Quality Score: {summary['avg_quality_score']:.1f}/100")
    print(f"   Total Assessments: {summary['total_assessments']}")
    print(f"   Total Issues Found: {summary['total_issues']}")
    print(f"   Critical Issues: {summary['critical_issues']}")

    distribution = dashboard_data["quality_distribution"]
    print(f"\n📊 Quality Distribution:")
    print(f"   Excellent (90+): {distribution['excellent']} datasets")
    print(f"   Good (75-89): {distribution['good']} datasets")
    print(f"   Fair (60-74): {distribution['fair']} datasets")
    print(f"   Poor (<60): {distribution['poor']} datasets")

    # Demo 7: Custom quality rule
    print("\n⚙️ Demo 7: Custom Quality Rule")

    custom_rule = QualityRule(
        rule_id="custom_fire_intensity_rule",
        name="Fire Intensity Validation",
        description="Fire radiative power should correlate with brightness",
        rule_type=QualityRuleType.CONSISTENCY,
        severity=QualitySeverity.MEDIUM,
        dataset_id="nasa_firms_fire_data",
        logic={
            "consistency_checks": [
                {"condition": "brightness > 400 AND frp < 50", "severity": "medium"}
            ]
        },
        threshold=90.0
    )

    quality_manager.rule_engine.add_rule(custom_rule)
    print(f"✅ Custom rule added: {custom_rule.name}")

    # Re-assess with new rule
    updated_assessment = await quality_manager.assess_dataset_quality("nasa_firms_fire_data", firms_data)
    print(f"✅ Updated assessment with custom rule:")
    print(f"   Overall Score: {updated_assessment.overall_score:.1f}/100")
    print(f"   Total Rules Executed: {len(updated_assessment.check_results)}")

    print("\n🎯 Data Quality Framework Demo Completed!")
    print(f"🔍 Quality rules configured: {len(quality_manager.rule_engine.rules)}")
    print(f"📊 Quality assessments performed: {len(quality_manager.quality_history)}")
    print(f"📋 Quality reports generated: {len(quality_manager.quality_reports)}")


if __name__ == "__main__":
    asyncio.run(demo_data_quality_framework())