"""
Challenge 3 Deliverable: Data Quality Assurance Framework
Validation rules, anomaly detection, and data profiling
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timezone
import pandas as pd
import numpy as np
from scipy import stats
import structlog

logger = structlog.get_logger()


@dataclass
class ValidationRule:
    """Data validation rule definition"""
    rule_id: str
    rule_name: str
    rule_type: str  # not_null, range, regex, custom
    field: str
    parameters: Dict[str, Any]
    severity: str  # error, warning, info
    enabled: bool = True


@dataclass
class QualityCheckResult:
    """Result of a quality check"""
    check_id: str
    check_name: str
    dataset_id: str
    timestamp: str
    passed: bool
    pass_rate: float
    failed_records: int
    total_records: int
    issues: List[Dict[str, Any]]
    recommendations: List[str]


@dataclass
class DataProfile:
    """Statistical profile of dataset"""
    dataset_id: str
    column_name: str
    data_type: str
    record_count: int
    null_count: int
    null_percentage: float
    unique_count: int
    unique_percentage: float
    min_value: Any
    max_value: Any
    mean_value: Optional[float]
    median_value: Optional[float]
    std_dev: Optional[float]
    percentiles: Dict[int, float]
    most_frequent: List[tuple]
    sample_values: List[Any]


class DataQualityValidator:
    """Comprehensive data quality validation and profiling"""

    def __init__(self):
        self.rules: Dict[str, List[ValidationRule]] = {}
        self.quality_history: List[QualityCheckResult] = []
        self._initialize_default_rules()

    def _initialize_default_rules(self):
        """Initialize standard validation rules"""

        # Fire detection data rules
        self.rules["fire_detections"] = [
            ValidationRule(
                rule_id="lat_range",
                rule_name="Latitude Range Check",
                rule_type="range",
                field="latitude",
                parameters={"min": -90, "max": 90},
                severity="error"
            ),
            ValidationRule(
                rule_id="lon_range",
                rule_name="Longitude Range Check",
                rule_type="range",
                field="longitude",
                parameters={"min": -180, "max": 180},
                severity="error"
            ),
            ValidationRule(
                rule_id="conf_range",
                rule_name="Confidence Range Check",
                rule_type="range",
                field="confidence",
                parameters={"min": 0, "max": 100},
                severity="error"
            ),
            ValidationRule(
                rule_id="frp_positive",
                rule_name="FRP Positive Check",
                rule_type="range",
                field="fire_radiative_power",
                parameters={"min": 0},
                severity="warning"
            ),
            ValidationRule(
                rule_id="timestamp_not_null",
                rule_name="Timestamp Required",
                rule_type="not_null",
                field="timestamp",
                parameters={},
                severity="error"
            ),
            ValidationRule(
                rule_id="timestamp_recent",
                rule_name="Timestamp Recency Check",
                rule_type="custom",
                field="timestamp",
                parameters={"max_age_days": 90},
                severity="warning"
            )
        ]

        # Weather data rules
        self.rules["weather_data"] = [
            ValidationRule(
                rule_id="temp_range",
                rule_name="Temperature Range Check",
                rule_type="range",
                field="temperature_c",
                parameters={"min": -50, "max": 60},
                severity="error"
            ),
            ValidationRule(
                rule_id="humidity_range",
                rule_name="Humidity Range Check",
                rule_type="range",
                field="relative_humidity",
                parameters={"min": 0, "max": 100},
                severity="error"
            ),
            ValidationRule(
                rule_id="wind_positive",
                rule_name="Wind Speed Positive",
                rule_type="range",
                field="wind_speed",
                parameters={"min": 0},
                severity="error"
            )
        ]

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
            Quality check result with pass/fail and issues
        """
        rules = self.rules.get(rule_set, [])
        total_records = len(data)
        all_issues = []
        failed_records_set = set()

        logger.info("Starting data quality validation",
                   dataset_id=dataset_id,
                   records=total_records,
                   rules=len(rules))

        for rule in rules:
            if not rule.enabled:
                continue

            issues = self._apply_rule(data, rule)
            all_issues.extend(issues)

            for issue in issues:
                if issue.get("row_index") is not None:
                    failed_records_set.add(issue["row_index"])

        failed_records = len(failed_records_set)
        pass_rate = ((total_records - failed_records) / total_records * 100) if total_records > 0 else 0

        result = QualityCheckResult(
            check_id=f"qc_{datetime.utcnow().timestamp()}",
            check_name=f"{dataset_id} Validation",
            dataset_id=dataset_id,
            timestamp=datetime.utcnow().isoformat(),
            passed=failed_records == 0,
            pass_rate=pass_rate,
            failed_records=failed_records,
            total_records=total_records,
            issues=all_issues,
            recommendations=self._generate_recommendations(all_issues)
        )

        self.quality_history.append(result)

        logger.info("Quality validation completed",
                   dataset_id=dataset_id,
                   passed=result.passed,
                   pass_rate=pass_rate,
                   issues_found=len(all_issues))

        return result

    def _apply_rule(self, data: pd.DataFrame, rule: ValidationRule) -> List[Dict[str, Any]]:
        """Apply a validation rule to data"""
        issues = []

        if rule.rule_type == "not_null":
            # Check for null values
            null_mask = data[rule.field].isnull()
            if null_mask.any():
                null_indices = data[null_mask].index.tolist()
                for idx in null_indices:
                    issues.append({
                        "rule_id": rule.rule_id,
                        "rule_name": rule.rule_name,
                        "severity": rule.severity,
                        "field": rule.field,
                        "row_index": idx,
                        "issue": "Null value detected",
                        "expected": "Non-null value"
                    })

        elif rule.rule_type == "range":
            # Check value range
            field_data = data[rule.field].dropna()

            min_val = rule.parameters.get("min")
            max_val = rule.parameters.get("max")

            if min_val is not None:
                below_min = field_data < min_val
                if below_min.any():
                    indices = data[below_min].index.tolist()
                    for idx in indices:
                        issues.append({
                            "rule_id": rule.rule_id,
                            "rule_name": rule.rule_name,
                            "severity": rule.severity,
                            "field": rule.field,
                            "row_index": idx,
                            "issue": f"Value below minimum",
                            "actual_value": float(data.loc[idx, rule.field]),
                            "expected": f">= {min_val}"
                        })

            if max_val is not None:
                above_max = field_data > max_val
                if above_max.any():
                    indices = data[above_max].index.tolist()
                    for idx in indices:
                        issues.append({
                            "rule_id": rule.rule_id,
                            "rule_name": rule.rule_name,
                            "severity": rule.severity,
                            "field": rule.field,
                            "row_index": idx,
                            "issue": f"Value above maximum",
                            "actual_value": float(data.loc[idx, rule.field]),
                            "expected": f"<= {max_val}"
                        })

        elif rule.rule_type == "regex":
            # Check regex pattern
            import re
            pattern = rule.parameters.get("pattern")
            field_data = data[rule.field].dropna().astype(str)

            non_matching = ~field_data.str.match(pattern)
            if non_matching.any():
                indices = data[non_matching].index.tolist()
                for idx in indices:
                    issues.append({
                        "rule_id": rule.rule_id,
                        "rule_name": rule.rule_name,
                        "severity": rule.severity,
                        "field": rule.field,
                        "row_index": idx,
                        "issue": "Pattern mismatch",
                        "actual_value": str(data.loc[idx, rule.field]),
                        "expected_pattern": pattern
                    })

        elif rule.rule_type == "custom":
            # Custom validation logic
            if rule.rule_id == "timestamp_recent":
                max_age_days = rule.parameters.get("max_age_days", 90)
                cutoff = pd.Timestamp.now(tz='UTC') - pd.Timedelta(days=max_age_days)

                old_records = data[pd.to_datetime(data[rule.field]) < cutoff]
                for idx in old_records.index:
                    issues.append({
                        "rule_id": rule.rule_id,
                        "rule_name": rule.rule_name,
                        "severity": rule.severity,
                        "field": rule.field,
                        "row_index": idx,
                        "issue": "Timestamp too old",
                        "actual_value": str(data.loc[idx, rule.field]),
                        "expected": f"Within last {max_age_days} days"
                    })

        return issues

    def detect_anomalies(
        self,
        data: pd.DataFrame,
        column: str,
        method: str = "zscore",
        threshold: float = 3.0
    ) -> Dict[str, Any]:
        """
        **Challenge 3 Deliverable: Anomaly Detection**

        Detect statistical anomalies in data

        Methods:
        - zscore: Standard deviation-based (Z-score > threshold)
        - iqr: Interquartile range method
        - isolation_forest: ML-based anomaly detection
        """
        logger.info("Detecting anomalies",
                   column=column,
                   method=method,
                   threshold=threshold)

        if method == "zscore":
            # Z-score method
            z_scores = np.abs(stats.zscore(data[column].dropna()))
            anomalies = z_scores > threshold
            anomaly_indices = data[anomalies].index.tolist()

        elif method == "iqr":
            # IQR method
            Q1 = data[column].quantile(0.25)
            Q3 = data[column].quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR

            anomalies = (data[column] < lower_bound) | (data[column] > upper_bound)
            anomaly_indices = data[anomalies].index.tolist()

        elif method == "isolation_forest":
            # Isolation Forest (ML-based)
            from sklearn.ensemble import IsolationForest

            model = IsolationForest(contamination=0.1, random_state=42)
            predictions = model.fit_predict(data[[column]].dropna())
            anomalies = predictions == -1
            anomaly_indices = data[anomalies].index.tolist()

        else:
            raise ValueError(f"Unknown anomaly detection method: {method}")

        anomaly_count = len(anomaly_indices)
        anomaly_rate = (anomaly_count / len(data) * 100) if len(data) > 0 else 0

        result = {
            "column": column,
            "method": method,
            "threshold": threshold,
            "total_records": len(data),
            "anomaly_count": anomaly_count,
            "anomaly_rate": anomaly_rate,
            "anomaly_indices": anomaly_indices[:100],  # First 100
            "anomaly_values": data.loc[anomaly_indices, column].tolist()[:100]
        }

        logger.info("Anomaly detection completed",
                   column=column,
                   anomalies_found=anomaly_count,
                   rate=anomaly_rate)

        return result

    def profile_dataset(self, data: pd.DataFrame, dataset_id: str) -> List[DataProfile]:
        """
        **Challenge 3 Deliverable: Data Profiling Reports**

        Generate comprehensive statistical profile of dataset

        Provides:
        - Data types and null counts
        - Unique value counts
        - Statistical summaries (min, max, mean, median, std)
        - Percentile distributions
        - Most frequent values
        - Sample data
        """
        profiles = []

        logger.info("Profiling dataset",
                   dataset_id=dataset_id,
                   columns=len(data.columns),
                   records=len(data))

        for column in data.columns:
            column_data = data[column]
            data_type = str(column_data.dtype)

            # Basic statistics
            record_count = len(column_data)
            null_count = column_data.isnull().sum()
            null_percentage = (null_count / record_count * 100) if record_count > 0 else 0
            unique_count = column_data.nunique()
            unique_percentage = (unique_count / record_count * 100) if record_count > 0 else 0

            # Statistical measures (for numeric columns)
            mean_value = None
            median_value = None
            std_dev = None
            percentiles = {}

            if pd.api.types.is_numeric_dtype(column_data):
                non_null = column_data.dropna()
                if len(non_null) > 0:
                    mean_value = float(non_null.mean())
                    median_value = float(non_null.median())
                    std_dev = float(non_null.std())
                    percentiles = {
                        5: float(non_null.quantile(0.05)),
                        25: float(non_null.quantile(0.25)),
                        50: float(non_null.quantile(0.50)),
                        75: float(non_null.quantile(0.75)),
                        95: float(non_null.quantile(0.95))
                    }

            # Most frequent values
            value_counts = column_data.value_counts().head(10)
            most_frequent = [(val, int(count)) for val, count in value_counts.items()]

            # Sample values
            sample_values = column_data.dropna().head(5).tolist()

            profile = DataProfile(
                dataset_id=dataset_id,
                column_name=column,
                data_type=data_type,
                record_count=record_count,
                null_count=int(null_count),
                null_percentage=float(null_percentage),
                unique_count=int(unique_count),
                unique_percentage=float(unique_percentage),
                min_value=column_data.min() if pd.api.types.is_numeric_dtype(column_data) else None,
                max_value=column_data.max() if pd.api.types.is_numeric_dtype(column_data) else None,
                mean_value=mean_value,
                median_value=median_value,
                std_dev=std_dev,
                percentiles=percentiles,
                most_frequent=most_frequent,
                sample_values=sample_values
            )

            profiles.append(profile)

        logger.info("Dataset profiling completed",
                   dataset_id=dataset_id,
                   columns_profiled=len(profiles))

        return profiles

    def _generate_recommendations(self, issues: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations based on quality issues"""
        recommendations = []

        # Group issues by type
        issue_types = {}
        for issue in issues:
            issue_type = issue.get("rule_id")
            issue_types[issue_type] = issue_types.get(issue_type, 0) + 1

        # Generate recommendations
        if "lat_range" in issue_types or "lon_range" in issue_types:
            recommendations.append(
                "Review coordinate validation in data source. "
                "Consider adding coordinate system transformation."
            )

        if "timestamp_not_null" in issue_types:
            recommendations.append(
                "Ensure timestamp is captured at data source. "
                "Add timestamp generation in ETL pipeline if missing."
            )

        if "timestamp_recent" in issue_types:
            recommendations.append(
                "Old data detected. Review data retention policy. "
                "Consider archiving historical data."
            )

        if len(issues) > 1000:
            recommendations.append(
                "High volume of quality issues detected. "
                "Review data source configuration and ETL processes."
            )

        return recommendations

    def generate_quality_report(
        self,
        dataset_id: str
    ) -> Dict[str, Any]:
        """
        Generate comprehensive data quality report

        Includes:
        - Validation results
        - Anomaly detection
        - Data profiling
        - Quality trends
        - Recommendations
        """
        # Get recent quality checks
        recent_checks = [
            check for check in self.quality_history
            if check.dataset_id == dataset_id
        ][-10:]  # Last 10 checks

        # Calculate overall quality score
        if recent_checks:
            avg_pass_rate = sum(c.pass_rate for c in recent_checks) / len(recent_checks)
        else:
            avg_pass_rate = 0.0

        # Determine quality grade
        if avg_pass_rate >= 95:
            quality_grade = "A - Excellent"
        elif avg_pass_rate >= 85:
            quality_grade = "B - Good"
        elif avg_pass_rate >= 75:
            quality_grade = "C - Fair"
        else:
            quality_grade = "D - Needs Improvement"

        report = {
            "dataset_id": dataset_id,
            "report_generated_at": datetime.utcnow().isoformat(),
            "overall_quality_score": avg_pass_rate,
            "quality_grade": quality_grade,
            "recent_checks": [
                {
                    "timestamp": c.timestamp,
                    "pass_rate": c.pass_rate,
                    "issues_count": len(c.issues)
                }
                for c in recent_checks
            ],
            "quality_trend": "improving" if len(recent_checks) > 1 and recent_checks[-1].pass_rate > recent_checks[0].pass_rate else "stable",
            "recommendations": recent_checks[-1].recommendations if recent_checks else []
        }

        return report


# Global validator instance
data_quality_validator = DataQualityValidator()


def get_data_quality_validator() -> DataQualityValidator:
    """Get global data quality validator instance"""
    return data_quality_validator
