"""
Data Quality Assurance Framework
Challenge 3 Deliverable: Validation rules, anomaly detection, data profiling
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from scipy import stats
from sklearn.ensemble import IsolationForest


class RuleType(str, Enum):
    """Validation rule types"""
    NOT_NULL = "not_null"
    RANGE = "range"
    REGEX = "regex"
    UNIQUE = "unique"
    FOREIGN_KEY = "foreign_key"
    CUSTOM = "custom"
    TEMPORAL = "temporal"
    SPATIAL = "spatial"


class Severity(str, Enum):
    """Issue severity levels"""
    ERROR = "error"  # Critical - blocks data usage
    WARNING = "warning"  # Important - review recommended
    INFO = "info"  # Informational only


@dataclass
class ValidationRule:
    """Data validation rule definition"""
    rule_id: str
    rule_name: str
    rule_type: RuleType
    field: str
    parameters: Dict[str, Any]
    severity: Severity
    enabled: bool = True
    description: Optional[str] = None


@dataclass
class QualityIssue:
    """Quality validation issue"""
    rule_id: str
    severity: Severity
    field: str
    issue_type: str
    message: str
    affected_rows: int
    examples: List[Any]


@dataclass
class QualityCheckResult:
    """Result of quality validation"""
    dataset_id: str
    timestamp: datetime
    total_rows: int
    rules_checked: int
    rules_passed: int
    rules_failed: int
    issues: List[QualityIssue]
    overall_quality_score: float
    pass_rate: float


@dataclass
class DataProfile:
    """Statistical profile of a column"""
    column_name: str
    data_type: str
    row_count: int
    null_count: int
    null_percentage: float
    unique_count: int
    min_value: Any
    max_value: Any
    mean_value: Optional[float]
    median_value: Optional[float]
    std_dev: Optional[float]
    percentiles: Dict[int, float]
    most_common: List[tuple]


class DataQualityValidator:
    """
    Comprehensive data quality validation and profiling

    Challenge 3 Deliverable Features:
    - Configurable validation rules
    - Statistical anomaly detection
    - Data profiling and statistics
    - Quality scoring
    - Issue tracking and reporting
    """

    def __init__(self):
        self.validation_rules: Dict[str, List[ValidationRule]] = {}
        self.quality_history: List[QualityCheckResult] = []
        self._initialize_default_rules()

    def _initialize_default_rules(self):
        """Initialize default validation rules for common datasets"""

        # Fire detection rules
        fire_detection_rules = [
            ValidationRule(
                rule_id="fire_lat_range",
                rule_name="Valid Latitude Range",
                rule_type=RuleType.RANGE,
                field="latitude",
                parameters={"min": -90.0, "max": 90.0},
                severity=Severity.ERROR,
                description="Latitude must be between -90 and 90"
            ),
            ValidationRule(
                rule_id="fire_lon_range",
                rule_name="Valid Longitude Range",
                rule_type=RuleType.RANGE,
                field="longitude",
                parameters={"min": -180.0, "max": 180.0},
                severity=Severity.ERROR,
                description="Longitude must be between -180 and 180"
            ),
            ValidationRule(
                rule_id="fire_confidence_range",
                rule_name="Valid Confidence Score",
                rule_type=RuleType.RANGE,
                field="confidence",
                parameters={"min": 0.0, "max": 1.0},
                severity=Severity.WARNING,
                description="Confidence must be between 0 and 1"
            ),
            ValidationRule(
                rule_id="fire_timestamp_not_null",
                rule_name="Timestamp Required",
                rule_type=RuleType.NOT_NULL,
                field="timestamp",
                parameters={},
                severity=Severity.ERROR,
                description="Timestamp is required for all fire detections"
            ),
            ValidationRule(
                rule_id="fire_frp_positive",
                rule_name="Positive Fire Radiative Power",
                rule_type=RuleType.RANGE,
                field="fire_radiative_power",
                parameters={"min": 0.0, "max": 10000.0},
                severity=Severity.WARNING,
                description="FRP should be positive and reasonable"
            )
        ]

        self.validation_rules["fire_detections"] = fire_detection_rules

        # Weather data rules
        weather_rules = [
            ValidationRule(
                rule_id="weather_temp_range",
                rule_name="Valid Temperature Range",
                rule_type=RuleType.RANGE,
                field="temperature_c",
                parameters={"min": -50.0, "max": 60.0},
                severity=Severity.WARNING,
                description="Temperature should be within reasonable range"
            ),
            ValidationRule(
                rule_id="weather_humidity_range",
                rule_name="Valid Humidity Range",
                rule_type=RuleType.RANGE,
                field="relative_humidity",
                parameters={"min": 0.0, "max": 100.0},
                severity=Severity.ERROR,
                description="Humidity must be 0-100%"
            ),
            ValidationRule(
                rule_id="weather_wind_positive",
                rule_name="Positive Wind Speed",
                rule_type=RuleType.RANGE,
                field="wind_speed",
                parameters={"min": 0.0, "max": 200.0},
                severity=Severity.WARNING,
                description="Wind speed should be positive and reasonable"
            )
        ]

        self.validation_rules["weather_data"] = weather_rules

    def add_validation_rule(self, dataset_type: str, rule: ValidationRule):
        """
        Add custom validation rule

        Args:
            dataset_type: Type of dataset (fire_detections, weather_data, etc.)
            rule: Validation rule to add
        """
        if dataset_type not in self.validation_rules:
            self.validation_rules[dataset_type] = []

        self.validation_rules[dataset_type].append(rule)

    def validate_dataset(
        self,
        dataset_id: str,
        data: pd.DataFrame,
        rule_set: str = "fire_detections"
    ) -> QualityCheckResult:
        """
        Validate dataset against defined rules

        Args:
            dataset_id: Dataset identifier
            data: DataFrame to validate
            rule_set: Which rule set to apply

        Returns:
            Quality check result with issues
        """
        rules = self.validation_rules.get(rule_set, [])
        issues = []
        rules_passed = 0
        rules_failed = 0

        for rule in rules:
            if not rule.enabled:
                continue

            if rule.field not in data.columns:
                continue

            issue = self._apply_rule(data, rule)

            if issue:
                issues.append(issue)
                rules_failed += 1
            else:
                rules_passed += 1

        # Calculate overall quality score
        total_rules = rules_passed + rules_failed
        pass_rate = rules_passed / total_rules if total_rules > 0 else 1.0

        # Weight by severity
        error_count = sum(1 for i in issues if i.severity == Severity.ERROR)
        warning_count = sum(1 for i in issues if i.severity == Severity.WARNING)

        quality_score = max(0.0, 1.0 - (error_count * 0.15) - (warning_count * 0.05))

        result = QualityCheckResult(
            dataset_id=dataset_id,
            timestamp=datetime.utcnow(),
            total_rows=len(data),
            rules_checked=total_rules,
            rules_passed=rules_passed,
            rules_failed=rules_failed,
            issues=issues,
            overall_quality_score=quality_score,
            pass_rate=pass_rate
        )

        self.quality_history.append(result)

        return result

    def _apply_rule(
        self,
        data: pd.DataFrame,
        rule: ValidationRule
    ) -> Optional[QualityIssue]:
        """
        Apply single validation rule

        Args:
            data: DataFrame
            rule: Validation rule

        Returns:
            QualityIssue if validation fails, None if passes
        """
        column = data[rule.field]

        if rule.rule_type == RuleType.NOT_NULL:
            null_count = column.isnull().sum()
            if null_count > 0:
                return QualityIssue(
                    rule_id=rule.rule_id,
                    severity=rule.severity,
                    field=rule.field,
                    issue_type="null_values",
                    message=f"{null_count} null values found in {rule.field}",
                    affected_rows=null_count,
                    examples=[]
                )

        elif rule.rule_type == RuleType.RANGE:
            min_val = rule.parameters.get("min")
            max_val = rule.parameters.get("max")

            out_of_range = column[(column < min_val) | (column > max_val)]

            if len(out_of_range) > 0:
                return QualityIssue(
                    rule_id=rule.rule_id,
                    severity=rule.severity,
                    field=rule.field,
                    issue_type="out_of_range",
                    message=f"{len(out_of_range)} values out of range [{min_val}, {max_val}]",
                    affected_rows=len(out_of_range),
                    examples=out_of_range.head(5).tolist()
                )

        elif rule.rule_type == RuleType.UNIQUE:
            duplicates = column[column.duplicated()]
            if len(duplicates) > 0:
                return QualityIssue(
                    rule_id=rule.rule_id,
                    severity=rule.severity,
                    field=rule.field,
                    issue_type="duplicate_values",
                    message=f"{len(duplicates)} duplicate values found",
                    affected_rows=len(duplicates),
                    examples=duplicates.head(5).tolist()
                )

        return None

    def detect_anomalies(
        self,
        data: pd.DataFrame,
        column: str,
        method: str = "zscore",  # or "iqr", "isolation_forest"
        threshold: float = 3.0
    ) -> Dict[str, Any]:
        """
        Detect statistical anomalies in data

        Args:
            data: DataFrame
            column: Column to analyze
            method: Detection method (zscore, iqr, isolation_forest)
            threshold: Sensitivity threshold

        Returns:
            Anomaly detection results
        """
        values = data[column].dropna()

        if method == "zscore":
            z_scores = np.abs(stats.zscore(values))
            anomalies = values[z_scores > threshold]

            return {
                "method": "zscore",
                "threshold": threshold,
                "anomalies_count": len(anomalies),
                "anomalies_percentage": (len(anomalies) / len(values)) * 100,
                "anomaly_values": anomalies.head(10).tolist(),
                "mean": float(values.mean()),
                "std_dev": float(values.std())
            }

        elif method == "iqr":
            q1 = values.quantile(0.25)
            q3 = values.quantile(0.75)
            iqr = q3 - q1
            lower_bound = q1 - (threshold * iqr)
            upper_bound = q3 + (threshold * iqr)

            anomalies = values[(values < lower_bound) | (values > upper_bound)]

            return {
                "method": "iqr",
                "threshold": threshold,
                "anomalies_count": len(anomalies),
                "anomalies_percentage": (len(anomalies) / len(values)) * 100,
                "anomaly_values": anomalies.head(10).tolist(),
                "q1": float(q1),
                "q3": float(q3),
                "iqr": float(iqr),
                "lower_bound": float(lower_bound),
                "upper_bound": float(upper_bound)
            }

        elif method == "isolation_forest":
            # Reshape for sklearn
            X = values.values.reshape(-1, 1)

            iso_forest = IsolationForest(contamination=0.1, random_state=42)
            predictions = iso_forest.fit_predict(X)

            anomaly_indices = np.where(predictions == -1)[0]
            anomalies = values.iloc[anomaly_indices]

            return {
                "method": "isolation_forest",
                "anomalies_count": len(anomalies),
                "anomalies_percentage": (len(anomalies) / len(values)) * 100,
                "anomaly_values": anomalies.head(10).tolist()
            }

        else:
            raise ValueError(f"Unknown anomaly detection method: {method}")

    def profile_dataset(
        self,
        data: pd.DataFrame,
        dataset_id: str
    ) -> List[DataProfile]:
        """
        Generate comprehensive statistical profile

        Args:
            data: DataFrame to profile
            dataset_id: Dataset identifier

        Returns:
            List of column profiles
        """
        profiles = []

        for column in data.columns:
            values = data[column]
            non_null_values = values.dropna()

            profile = DataProfile(
                column_name=column,
                data_type=str(values.dtype),
                row_count=len(values),
                null_count=values.isnull().sum(),
                null_percentage=(values.isnull().sum() / len(values)) * 100,
                unique_count=values.nunique(),
                min_value=non_null_values.min() if len(non_null_values) > 0 else None,
                max_value=non_null_values.max() if len(non_null_values) > 0 else None,
                mean_value=float(non_null_values.mean()) if pd.api.types.is_numeric_dtype(values) else None,
                median_value=float(non_null_values.median()) if pd.api.types.is_numeric_dtype(values) else None,
                std_dev=float(non_null_values.std()) if pd.api.types.is_numeric_dtype(values) else None,
                percentiles={
                    25: float(non_null_values.quantile(0.25)) if pd.api.types.is_numeric_dtype(values) else None,
                    50: float(non_null_values.quantile(0.50)) if pd.api.types.is_numeric_dtype(values) else None,
                    75: float(non_null_values.quantile(0.75)) if pd.api.types.is_numeric_dtype(values) else None,
                    95: float(non_null_values.quantile(0.95)) if pd.api.types.is_numeric_dtype(values) else None,
                },
                most_common=values.value_counts().head(5).items() if not pd.api.types.is_numeric_dtype(values) else []
            )

            profiles.append(profile)

        return profiles

    def get_quality_trends(
        self,
        dataset_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get quality trends over time

        Args:
            dataset_id: Dataset identifier
            days: Number of days to analyze

        Returns:
            Quality trend analysis
        """
        relevant_results = [
            r for r in self.quality_history
            if r.dataset_id == dataset_id
            and (datetime.utcnow() - r.timestamp).days <= days
        ]

        if not relevant_results:
            return {"message": "No quality data available"}

        return {
            "dataset_id": dataset_id,
            "period_days": days,
            "total_checks": len(relevant_results),
            "average_quality_score": sum(r.overall_quality_score for r in relevant_results) / len(relevant_results),
            "average_pass_rate": sum(r.pass_rate for r in relevant_results) / len(relevant_results),
            "trend": "improving" if relevant_results[-1].overall_quality_score > relevant_results[0].overall_quality_score else "declining",
            "recent_issues": relevant_results[-1].issues if relevant_results else []
        }

    def generate_quality_report(
        self,
        result: QualityCheckResult
    ) -> Dict[str, Any]:
        """
        Generate comprehensive quality report

        Args:
            result: Quality check result

        Returns:
            Formatted quality report
        """
        return {
            "dataset_id": result.dataset_id,
            "timestamp": result.timestamp.isoformat(),
            "summary": {
                "total_rows": result.total_rows,
                "overall_quality_score": result.overall_quality_score,
                "pass_rate": result.pass_rate,
                "quality_grade": self._get_quality_grade(result.overall_quality_score)
            },
            "validation": {
                "rules_checked": result.rules_checked,
                "rules_passed": result.rules_passed,
                "rules_failed": result.rules_failed
            },
            "issues": {
                "total_issues": len(result.issues),
                "errors": sum(1 for i in result.issues if i.severity == Severity.ERROR),
                "warnings": sum(1 for i in result.issues if i.severity == Severity.WARNING),
                "details": [
                    {
                        "severity": i.severity.value,
                        "field": i.field,
                        "type": i.issue_type,
                        "message": i.message,
                        "affected_rows": i.affected_rows
                    }
                    for i in result.issues
                ]
            },
            "recommendations": self._generate_recommendations(result)
        }

    def _get_quality_grade(self, score: float) -> str:
        """Convert quality score to letter grade"""
        if score >= 0.95:
            return "A (Excellent)"
        elif score >= 0.85:
            return "B (Good)"
        elif score >= 0.75:
            return "C (Acceptable)"
        elif score >= 0.60:
            return "D (Poor)"
        else:
            return "F (Critical Issues)"

    def _generate_recommendations(self, result: QualityCheckResult) -> List[str]:
        """Generate recommendations based on issues found"""
        recommendations = []

        error_count = sum(1 for i in result.issues if i.severity == Severity.ERROR)
        if error_count > 0:
            recommendations.append(f"Fix {error_count} critical errors before using this data")

        null_issues = [i for i in result.issues if i.issue_type == "null_values"]
        if null_issues:
            recommendations.append("Review and handle null values in affected fields")

        range_issues = [i for i in result.issues if i.issue_type == "out_of_range"]
        if range_issues:
            recommendations.append("Investigate out-of-range values - may indicate data collection issues")

        if result.overall_quality_score < 0.75:
            recommendations.append("Quality score is low - consider re-ingesting or validating data source")

        return recommendations
