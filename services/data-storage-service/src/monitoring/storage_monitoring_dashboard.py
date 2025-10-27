"""
Challenge 2 Deliverable: Monitoring & Alerting Dashboard
Unified visibility into data flows, security alerts, storage consumption, SLA tracking, and incident response
"""

import asyncio
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import json
import statistics

class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"

class SLAMetricType(Enum):
    """SLA metric types"""
    AVAILABILITY = "availability"
    LATENCY = "latency"
    THROUGHPUT = "throughput"
    ERROR_RATE = "error_rate"
    RECOVERY_TIME = "recovery_time"

@dataclass
class StorageMetrics:
    """Storage consumption and performance metrics"""
    timestamp: str
    storage_tier: str
    total_capacity_gb: float
    used_capacity_gb: float
    available_capacity_gb: float
    utilization_percent: float
    iops_current: int
    throughput_mbps: float
    response_time_ms: float

@dataclass
class SecurityAlert:
    """Security alert information"""
    alert_id: str
    timestamp: str
    severity: AlertSeverity
    alert_type: str
    source_system: str
    description: str
    affected_resources: List[str]
    response_actions: List[str]
    status: str

@dataclass
class SLAMetric:
    """SLA performance metric"""
    metric_id: str
    metric_type: SLAMetricType
    target_value: float
    actual_value: float
    measurement_period: str
    compliance_status: str
    timestamp: str

@dataclass
class DataFlowMetrics:
    """Data flow monitoring metrics"""
    flow_id: str
    source_system: str
    destination_system: str
    records_processed: int
    data_volume_gb: float
    processing_time_ms: float
    error_count: int
    success_rate: float
    timestamp: str

class StorageMonitoringDashboard:
    """Comprehensive monitoring and alerting dashboard for hybrid storage"""

    def __init__(self):
        self.storage_metrics_history: List[StorageMetrics] = []
        self.security_alerts: List[SecurityAlert] = []
        self.sla_metrics: List[SLAMetric] = []
        self.data_flows: List[DataFlowMetrics] = []
        self.alert_thresholds = self._define_alert_thresholds()
        self.sla_targets = self._define_sla_targets()

    def _define_alert_thresholds(self) -> Dict[str, Dict[str, float]]:
        """Define alerting thresholds for monitoring"""
        return {
            "storage_utilization": {
                "warning_percent": 80.0,
                "critical_percent": 90.0,
                "emergency_percent": 95.0
            },
            "performance": {
                "latency_warning_ms": 1000.0,
                "latency_critical_ms": 5000.0,
                "throughput_warning_mbps": 100.0,
                "iops_warning": 1000
            },
            "security": {
                "failed_logins_warning": 5,
                "data_access_anomaly_threshold": 3.0,  # Standard deviations
                "privilege_escalation_immediate": 1
            },
            "data_flows": {
                "error_rate_warning_percent": 5.0,
                "error_rate_critical_percent": 10.0,
                "processing_delay_warning_minutes": 30
            }
        }

    def _define_sla_targets(self) -> Dict[str, Dict[str, float]]:
        """Define SLA targets for different services"""
        return {
            "real_time_operations": {
                "availability_percent": 99.99,
                "latency_ms": 100.0,
                "throughput_mbps": 1000.0,
                "error_rate_percent": 0.01
            },
            "analytical_processing": {
                "availability_percent": 99.9,
                "latency_ms": 1000.0,
                "throughput_mbps": 500.0,
                "error_rate_percent": 0.1
            },
            "compliance_reporting": {
                "availability_percent": 99.5,
                "latency_ms": 10000.0,
                "throughput_mbps": 100.0,
                "error_rate_percent": 0.5
            },
            "disaster_recovery": {
                "rto_minutes": 60.0,
                "rpo_minutes": 15.0,
                "availability_percent": 99.999
            }
        }

    def record_storage_metrics(self, storage_tier: str, total_capacity_gb: float,
                             used_capacity_gb: float, iops_current: int,
                             throughput_mbps: float, response_time_ms: float) -> StorageMetrics:
        """Record storage consumption and performance metrics"""

        available_capacity_gb = total_capacity_gb - used_capacity_gb
        utilization_percent = (used_capacity_gb / total_capacity_gb) * 100.0

        metrics = StorageMetrics(
            timestamp=datetime.now(timezone.utc).isoformat(),
            storage_tier=storage_tier,
            total_capacity_gb=total_capacity_gb,
            used_capacity_gb=used_capacity_gb,
            available_capacity_gb=available_capacity_gb,
            utilization_percent=utilization_percent,
            iops_current=iops_current,
            throughput_mbps=throughput_mbps,
            response_time_ms=response_time_ms
        )

        self.storage_metrics_history.append(metrics)

        # Check for alert conditions
        self._check_storage_alerts(metrics)

        # Keep only last 1000 metrics entries
        if len(self.storage_metrics_history) > 1000:
            self.storage_metrics_history = self.storage_metrics_history[-1000:]

        return metrics

    def create_security_alert(self, alert_type: str, severity: AlertSeverity,
                            description: str, affected_resources: List[str],
                            source_system: str = "Security Monitoring") -> SecurityAlert:
        """Create a security alert"""

        alert = SecurityAlert(
            alert_id=f"SEC-{int(time.time())}-{len(self.security_alerts)}",
            timestamp=datetime.now(timezone.utc).isoformat(),
            severity=severity,
            alert_type=alert_type,
            source_system=source_system,
            description=description,
            affected_resources=affected_resources,
            response_actions=self._get_security_response_actions(alert_type, severity),
            status="active"
        )

        self.security_alerts.append(alert)
        print(f"🚨 SECURITY ALERT [{severity.value.upper()}]: {description}")

        return alert

    def record_sla_metric(self, metric_type: SLAMetricType, actual_value: float,
                         service_type: str = "real_time_operations") -> SLAMetric:
        """Record SLA performance metric"""

        target_value = self._get_sla_target(metric_type, service_type)
        compliance_status = "compliant" if self._check_sla_compliance(metric_type, actual_value, target_value) else "non_compliant"

        metric = SLAMetric(
            metric_id=f"SLA-{metric_type.value}-{int(time.time())}",
            metric_type=metric_type,
            target_value=target_value,
            actual_value=actual_value,
            measurement_period="current",
            compliance_status=compliance_status,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

        self.sla_metrics.append(metric)

        if compliance_status == "non_compliant":
            self._create_sla_violation_alert(metric)

        return metric

    def record_data_flow(self, source_system: str, destination_system: str,
                        records_processed: int, data_volume_gb: float,
                        processing_time_ms: float, error_count: int) -> DataFlowMetrics:
        """Record data flow processing metrics"""

        success_rate = ((records_processed - error_count) / records_processed * 100.0) if records_processed > 0 else 0.0

        flow = DataFlowMetrics(
            flow_id=f"FLOW-{source_system}-{destination_system}-{int(time.time())}",
            source_system=source_system,
            destination_system=destination_system,
            records_processed=records_processed,
            data_volume_gb=data_volume_gb,
            processing_time_ms=processing_time_ms,
            error_count=error_count,
            success_rate=success_rate,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

        self.data_flows.append(flow)

        # Check for data flow alerts
        self._check_data_flow_alerts(flow)

        return flow

    def _check_storage_alerts(self, metrics: StorageMetrics):
        """Check storage metrics against alert thresholds"""
        thresholds = self.alert_thresholds["storage_utilization"]

        if metrics.utilization_percent >= thresholds["emergency_percent"]:
            self.create_security_alert(
                "storage_capacity_emergency",
                AlertSeverity.EMERGENCY,
                f"Storage tier {metrics.storage_tier} at {metrics.utilization_percent:.1f}% capacity",
                [metrics.storage_tier]
            )
        elif metrics.utilization_percent >= thresholds["critical_percent"]:
            self.create_security_alert(
                "storage_capacity_critical",
                AlertSeverity.CRITICAL,
                f"Storage tier {metrics.storage_tier} at {metrics.utilization_percent:.1f}% capacity",
                [metrics.storage_tier]
            )
        elif metrics.utilization_percent >= thresholds["warning_percent"]:
            self.create_security_alert(
                "storage_capacity_warning",
                AlertSeverity.WARNING,
                f"Storage tier {metrics.storage_tier} at {metrics.utilization_percent:.1f}% capacity",
                [metrics.storage_tier]
            )

        # Performance alerts
        perf_thresholds = self.alert_thresholds["performance"]
        if metrics.response_time_ms >= perf_thresholds["latency_critical_ms"]:
            self.create_security_alert(
                "storage_performance_critical",
                AlertSeverity.CRITICAL,
                f"Storage latency {metrics.response_time_ms:.1f}ms exceeds critical threshold",
                [metrics.storage_tier]
            )

    def _check_data_flow_alerts(self, flow: DataFlowMetrics):
        """Check data flow metrics against alert thresholds"""
        thresholds = self.alert_thresholds["data_flows"]
        error_rate = (flow.error_count / flow.records_processed * 100.0) if flow.records_processed > 0 else 0.0

        if error_rate >= thresholds["error_rate_critical_percent"]:
            self.create_security_alert(
                "data_flow_error_critical",
                AlertSeverity.CRITICAL,
                f"Data flow {flow.source_system}→{flow.destination_system} error rate {error_rate:.1f}%",
                [flow.source_system, flow.destination_system]
            )
        elif error_rate >= thresholds["error_rate_warning_percent"]:
            self.create_security_alert(
                "data_flow_error_warning",
                AlertSeverity.WARNING,
                f"Data flow {flow.source_system}→{flow.destination_system} error rate {error_rate:.1f}%",
                [flow.source_system, flow.destination_system]
            )

    def _get_security_response_actions(self, alert_type: str, severity: AlertSeverity) -> List[str]:
        """Get recommended response actions for security alerts"""

        response_actions = {
            "storage_capacity_emergency": [
                "Immediately provision additional storage capacity",
                "Initiate emergency data archival process",
                "Notify storage administrators and management",
                "Implement temporary data retention reduction"
            ],
            "storage_capacity_critical": [
                "Plan storage expansion within 24 hours",
                "Review and optimize storage utilization",
                "Archive non-critical data to cold storage",
                "Monitor storage growth trends"
            ],
            "storage_performance_critical": [
                "Investigate storage system performance",
                "Check for hardware issues or bottlenecks",
                "Consider load balancing or traffic redirection",
                "Review storage tier allocation"
            ],
            "data_flow_error_critical": [
                "Investigate data flow processing errors",
                "Check source and destination system health",
                "Review data quality and format issues",
                "Implement error recovery procedures"
            ]
        }

        return response_actions.get(alert_type, [
            "Investigate alert condition",
            "Review system logs and metrics",
            "Escalate to appropriate technical team",
            "Document findings and resolution steps"
        ])

    def _get_sla_target(self, metric_type: SLAMetricType, service_type: str) -> float:
        """Get SLA target value for metric type and service"""
        service_targets = self.sla_targets.get(service_type, self.sla_targets["real_time_operations"])

        mapping = {
            SLAMetricType.AVAILABILITY: "availability_percent",
            SLAMetricType.LATENCY: "latency_ms",
            SLAMetricType.THROUGHPUT: "throughput_mbps",
            SLAMetricType.ERROR_RATE: "error_rate_percent",
            SLAMetricType.RECOVERY_TIME: "rto_minutes"
        }

        return service_targets.get(mapping.get(metric_type, "availability_percent"), 99.9)

    def _check_sla_compliance(self, metric_type: SLAMetricType, actual: float, target: float) -> bool:
        """Check if actual metric meets SLA target"""
        if metric_type in [SLAMetricType.AVAILABILITY, SLAMetricType.THROUGHPUT]:
            return actual >= target  # Higher is better
        else:
            return actual <= target  # Lower is better

    def _create_sla_violation_alert(self, metric: SLAMetric):
        """Create alert for SLA violation"""
        severity = AlertSeverity.CRITICAL if metric.metric_type == SLAMetricType.AVAILABILITY else AlertSeverity.WARNING

        self.create_security_alert(
            f"sla_violation_{metric.metric_type.value}",
            severity,
            f"SLA violation: {metric.metric_type.value} {metric.actual_value} vs target {metric.target_value}",
            ["SLA_MONITORING"],
            "SLA Monitoring System"
        )

    def get_dashboard_summary(self) -> Dict[str, Any]:
        """Generate comprehensive monitoring dashboard summary"""

        # Recent storage metrics (last 24 hours)
        recent_storage = [m for m in self.storage_metrics_history
                         if datetime.fromisoformat(m.timestamp.replace('Z', '+00:00')) > datetime.now(timezone.utc) - timedelta(hours=24)]

        # Active alerts
        active_alerts = [a for a in self.security_alerts if a.status == "active"]

        # Recent SLA metrics
        recent_sla = [m for m in self.sla_metrics
                     if datetime.fromisoformat(m.timestamp.replace('Z', '+00:00')) > datetime.now(timezone.utc) - timedelta(hours=24)]

        # Recent data flows
        recent_flows = [f for f in self.data_flows
                       if datetime.fromisoformat(f.timestamp.replace('Z', '+00:00')) > datetime.now(timezone.utc) - timedelta(hours=24)]

        return {
            "dashboard_generated_at": datetime.now(timezone.utc).isoformat(),
            "overview": {
                "active_alerts": len(active_alerts),
                "critical_alerts": len([a for a in active_alerts if a.severity == AlertSeverity.CRITICAL]),
                "storage_tiers_monitored": len(set(m.storage_tier for m in recent_storage)),
                "data_flows_processed": len(recent_flows),
                "sla_compliance_rate": len([m for m in recent_sla if m.compliance_status == "compliant"]) / len(recent_sla) * 100.0 if recent_sla else 100.0
            },

            "storage_summary": {
                "by_tier": self._summarize_storage_by_tier(recent_storage),
                "overall_utilization": statistics.mean([m.utilization_percent for m in recent_storage]) if recent_storage else 0.0,
                "performance_trends": {
                    "avg_latency_ms": statistics.mean([m.response_time_ms for m in recent_storage]) if recent_storage else 0.0,
                    "avg_throughput_mbps": statistics.mean([m.throughput_mbps for m in recent_storage]) if recent_storage else 0.0,
                    "avg_iops": statistics.mean([m.iops_current for m in recent_storage]) if recent_storage else 0.0
                }
            },

            "security_alerts": {
                "active_by_severity": {
                    severity.value: len([a for a in active_alerts if a.severity == severity])
                    for severity in AlertSeverity
                },
                "recent_alerts": [asdict(alert) for alert in active_alerts[-10:]]  # Last 10 alerts
            },

            "sla_performance": {
                "compliance_by_metric": {
                    metric_type.value: {
                        "compliant": len([m for m in recent_sla if m.metric_type == metric_type and m.compliance_status == "compliant"]),
                        "non_compliant": len([m for m in recent_sla if m.metric_type == metric_type and m.compliance_status == "non_compliant"])
                    }
                    for metric_type in SLAMetricType
                }
            },

            "data_flows": {
                "total_records_processed": sum(f.records_processed for f in recent_flows),
                "total_data_volume_gb": sum(f.data_volume_gb for f in recent_flows),
                "overall_success_rate": statistics.mean([f.success_rate for f in recent_flows]) if recent_flows else 100.0,
                "flows_by_source": self._summarize_flows_by_source(recent_flows)
            },

            "incident_response": {
                "open_incidents": len([a for a in active_alerts if a.severity in [AlertSeverity.CRITICAL, AlertSeverity.EMERGENCY]]),
                "response_procedures": {
                    "emergency": "Immediate escalation to on-call team",
                    "critical": "4-hour response SLA",
                    "warning": "Next business day response",
                    "info": "Weekly review process"
                }
            }
        }

    def _summarize_storage_by_tier(self, storage_metrics: List[StorageMetrics]) -> Dict[str, Dict[str, float]]:
        """Summarize storage metrics by tier"""
        summary = {}
        for tier in set(m.storage_tier for m in storage_metrics):
            tier_metrics = [m for m in storage_metrics if m.storage_tier == tier]
            if tier_metrics:
                latest = max(tier_metrics, key=lambda x: x.timestamp)
                summary[tier] = {
                    "total_capacity_gb": latest.total_capacity_gb,
                    "used_capacity_gb": latest.used_capacity_gb,
                    "utilization_percent": latest.utilization_percent,
                    "avg_response_time_ms": statistics.mean([m.response_time_ms for m in tier_metrics])
                }
        return summary

    def _summarize_flows_by_source(self, flows: List[DataFlowMetrics]) -> Dict[str, Dict[str, Any]]:
        """Summarize data flows by source system"""
        summary = {}
        for source in set(f.source_system for f in flows):
            source_flows = [f for f in flows if f.source_system == source]
            summary[source] = {
                "total_records": sum(f.records_processed for f in source_flows),
                "total_volume_gb": sum(f.data_volume_gb for f in source_flows),
                "avg_success_rate": statistics.mean([f.success_rate for f in source_flows]),
                "flow_count": len(source_flows)
            }
        return summary

    def print_dashboard(self):
        """Print formatted monitoring dashboard"""
        summary = self.get_dashboard_summary()

        print("\n" + "="*80)
        print("🖥️  CHALLENGE 2: HYBRID STORAGE MONITORING DASHBOARD")
        print("="*80)

        overview = summary["overview"]
        print(f"📊 SYSTEM OVERVIEW:")
        print(f"   Active Alerts: {overview['active_alerts']} (Critical: {overview['critical_alerts']})")
        print(f"   SLA Compliance: {overview['sla_compliance_rate']:.1f}%")
        print(f"   Storage Tiers: {overview['storage_tiers_monitored']}")
        print(f"   Data Flows: {overview['data_flows_processed']}")

        storage = summary["storage_summary"]
        print(f"\n💾 STORAGE PERFORMANCE:")
        print(f"   Overall Utilization: {storage['overall_utilization']:.1f}%")
        print(f"   Avg Latency: {storage['performance_trends']['avg_latency_ms']:.1f}ms")
        print(f"   Avg Throughput: {storage['performance_trends']['avg_throughput_mbps']:.1f} MB/s")

        alerts = summary["security_alerts"]
        print(f"\n🚨 SECURITY ALERTS:")
        for severity, count in alerts["active_by_severity"].items():
            if count > 0:
                print(f"   {severity.upper()}: {count}")

        flows = summary["data_flows"]
        print(f"\n📊 DATA FLOWS:")
        print(f"   Records Processed: {flows['total_records_processed']:,}")
        print(f"   Data Volume: {flows['total_data_volume_gb']:.2f} GB")
        print(f"   Success Rate: {flows['overall_success_rate']:.1f}%")

        print("="*80)

    def export_dashboard(self, filepath: str):
        """Export dashboard summary to JSON file"""
        dashboard_data = {
            "monitoring_dashboard": self.get_dashboard_summary(),
            "alert_thresholds": self.alert_thresholds,
            "sla_targets": self.sla_targets,
            "generated_at": datetime.now().isoformat(),
            "version": "2.0.0",
            "challenge": "CAL FIRE Challenge 2 - Data Storage Monitoring"
        }

        with open(filepath, 'w') as f:
            json.dump(dashboard_data, f, indent=2, default=str)

        print(f"📈 Monitoring dashboard exported to: {filepath}")

# Global monitoring dashboard instance
monitoring_dashboard = StorageMonitoringDashboard()

def get_monitoring_dashboard() -> StorageMonitoringDashboard:
    """Get the global monitoring dashboard instance"""
    return monitoring_dashboard