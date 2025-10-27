"""
Security and Governance Framework for Challenge 3
CAL FIRE Wildfire Intelligence Platform

This module implements the security and governance artifacts required by
Challenge 3 specifications including access control, audit logs, and compliance.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import json
import uuid
import hashlib
import logging
from pathlib import Path


class AccessLevel(Enum):
    """Data access levels in the governance framework"""
    PUBLIC = "public"
    INTERNAL = "internal"
    RESTRICTED = "restricted"
    CONFIDENTIAL = "confidential"
    SECRET = "secret"


class UserRole(Enum):
    """User roles in the system"""
    VIEWER = "viewer"
    ANALYST = "analyst"
    DATA_SCIENTIST = "data_scientist"
    FIRE_CHIEF = "fire_chief"
    OPERATIONS_MANAGER = "operations_manager"
    SYSTEM_ADMIN = "system_admin"
    SUPER_ADMIN = "super_admin"


class DataClassification(Enum):
    """Data classification categories"""
    OPERATIONAL = "operational"
    TACTICAL = "tactical"
    STRATEGIC = "strategic"
    EMERGENCY = "emergency"
    HISTORICAL = "historical"
    REAL_TIME = "real_time"
    PREDICTIVE = "predictive"


class AuditEventType(Enum):
    """Types of auditable events"""
    LOGIN = "login"
    LOGOUT = "logout"
    DATA_ACCESS = "data_access"
    QUERY_EXECUTION = "query_execution"
    DATA_EXPORT = "data_export"
    CONFIGURATION_CHANGE = "configuration_change"
    USER_MANAGEMENT = "user_management"
    POLICY_VIOLATION = "policy_violation"
    SYSTEM_ERROR = "system_error"
    UNAUTHORIZED_ACCESS = "unauthorized_access"


@dataclass
class SecurityPolicy:
    """Security policy definition"""
    policy_id: str
    name: str
    description: str
    classification: DataClassification
    access_level: AccessLevel
    allowed_roles: Set[UserRole]
    time_restrictions: Optional[Dict[str, Any]] = None
    geographic_restrictions: Optional[Dict[str, float]] = None
    data_retention_days: int = 365
    encryption_required: bool = True
    audit_level: str = "detailed"
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    is_active: bool = True


@dataclass
class UserPermission:
    """User permission definition"""
    permission_id: str
    user_id: str
    resource_type: str
    resource_id: str
    access_level: AccessLevel
    granted_by: str
    granted_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    conditions: Optional[Dict[str, Any]] = None
    is_active: bool = True


@dataclass
class AuditLogEntry:
    """Audit log entry"""
    log_id: str
    event_type: AuditEventType
    user_id: str
    resource_type: Optional[str]
    resource_id: Optional[str]
    action: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    session_id: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    risk_score: int = 0  # 0-100 risk assessment
    success: bool = True
    error_message: Optional[str] = None


@dataclass
class ComplianceReport:
    """Compliance audit report"""
    report_id: str
    report_type: str
    period_start: datetime
    period_end: datetime
    generated_at: datetime = field(default_factory=datetime.utcnow)
    generated_by: str = "system"
    findings: List[Dict[str, Any]] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    compliance_score: int = 100
    risk_level: str = "low"


class AccessControlManager:
    """Manages access control and permissions"""

    def __init__(self):
        self.policies: Dict[str, SecurityPolicy] = {}
        self.user_permissions: Dict[str, List[UserPermission]] = {}
        self.role_permissions: Dict[UserRole, Set[str]] = {}
        self.active_sessions: Dict[str, Dict[str, Any]] = {}

        self._initialize_default_policies()
        self._initialize_role_permissions()

    def _initialize_default_policies(self):
        """Initialize default security policies"""
        policies = [
            SecurityPolicy(
                policy_id="fire-data-policy",
                name="Fire Data Access Policy",
                description="Policy for accessing fire incident data",
                classification=DataClassification.OPERATIONAL,
                access_level=AccessLevel.INTERNAL,
                allowed_roles={UserRole.FIRE_CHIEF, UserRole.ANALYST, UserRole.OPERATIONS_MANAGER},
                time_restrictions={"business_hours_only": False},
                data_retention_days=2555  # 7 years
            ),
            SecurityPolicy(
                policy_id="weather-data-policy",
                name="Weather Data Access Policy",
                description="Policy for accessing weather and meteorological data",
                classification=DataClassification.OPERATIONAL,
                access_level=AccessLevel.PUBLIC,
                allowed_roles={role for role in UserRole},
                data_retention_days=1095  # 3 years
            ),
            SecurityPolicy(
                policy_id="predictive-models-policy",
                name="Predictive Models Access Policy",
                description="Policy for accessing AI/ML predictive models and outputs",
                classification=DataClassification.STRATEGIC,
                access_level=AccessLevel.RESTRICTED,
                allowed_roles={UserRole.DATA_SCIENTIST, UserRole.FIRE_CHIEF, UserRole.SYSTEM_ADMIN},
                data_retention_days=1825  # 5 years
            ),
            SecurityPolicy(
                policy_id="emergency-response-policy",
                name="Emergency Response Data Policy",
                description="Policy for emergency response and real-time operations data",
                classification=DataClassification.EMERGENCY,
                access_level=AccessLevel.CONFIDENTIAL,
                allowed_roles={UserRole.FIRE_CHIEF, UserRole.OPERATIONS_MANAGER, UserRole.SYSTEM_ADMIN},
                time_restrictions={"emergency_override": True}
            )
        ]

        for policy in policies:
            self.policies[policy.policy_id] = policy

    def _initialize_role_permissions(self):
        """Initialize role-based permissions"""
        self.role_permissions = {
            UserRole.VIEWER: {"read:public_data"},
            UserRole.ANALYST: {"read:public_data", "read:internal_data", "create:reports", "export:csv"},
            UserRole.DATA_SCIENTIST: {
                "read:public_data", "read:internal_data", "read:restricted_data",
                "create:models", "execute:analytics", "export:all_formats"
            },
            UserRole.FIRE_CHIEF: {
                "read:all_data", "create:incidents", "update:incidents",
                "approve:responses", "override:emergency"
            },
            UserRole.OPERATIONS_MANAGER: {
                "read:operational_data", "create:operations", "manage:resources",
                "coordinate:response"
            },
            UserRole.SYSTEM_ADMIN: {
                "read:system_data", "manage:users", "configure:system",
                "access:audit_logs", "manage:security"
            },
            UserRole.SUPER_ADMIN: {"*"}  # All permissions
        }

    def authenticate_user(self, user_id: str, session_id: str, ip_address: str) -> bool:
        """Authenticate user and create session"""
        # Simulate authentication logic
        if user_id and session_id:
            session_data = {
                "user_id": user_id,
                "session_id": session_id,
                "ip_address": ip_address,
                "login_time": datetime.utcnow(),
                "last_activity": datetime.utcnow(),
                "is_active": True
            }
            self.active_sessions[session_id] = session_data
            return True
        return False

    def check_permission(self, user_id: str, user_role: UserRole, resource_type: str,
                        resource_id: str, action: str) -> bool:
        """Check if user has permission for specific action"""
        # Check role-based permissions
        user_perms = self.role_permissions.get(user_role, set())
        if "*" in user_perms:  # Super admin
            return True

        # Check specific permission patterns
        required_permission = f"{action}:{resource_type}"
        generic_permission = f"{action}:all_data"

        if required_permission in user_perms or generic_permission in user_perms:
            return True

        # Check user-specific permissions
        user_permissions = self.user_permissions.get(user_id, [])
        for perm in user_permissions:
            if (perm.resource_type == resource_type and
                perm.resource_id == resource_id and
                perm.is_active):

                # Check expiration
                if perm.expires_at and perm.expires_at < datetime.utcnow():
                    perm.is_active = False
                    continue

                return True

        return False

    def grant_permission(self, user_id: str, resource_type: str, resource_id: str,
                        access_level: AccessLevel, granted_by: str,
                        expires_in_days: Optional[int] = None) -> UserPermission:
        """Grant specific permission to user"""
        permission = UserPermission(
            permission_id=str(uuid.uuid4()),
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            access_level=access_level,
            granted_by=granted_by,
            expires_at=datetime.utcnow() + timedelta(days=expires_in_days) if expires_in_days else None
        )

        if user_id not in self.user_permissions:
            self.user_permissions[user_id] = []

        self.user_permissions[user_id].append(permission)
        return permission

    def revoke_permission(self, permission_id: str) -> bool:
        """Revoke a specific permission"""
        for user_id, permissions in self.user_permissions.items():
            for perm in permissions:
                if perm.permission_id == permission_id:
                    perm.is_active = False
                    return True
        return False

    def validate_session(self, session_id: str) -> bool:
        """Validate active session"""
        session = self.active_sessions.get(session_id)
        if not session:
            return False

        # Check if session expired (24 hour timeout)
        if datetime.utcnow() - session["last_activity"] > timedelta(hours=24):
            session["is_active"] = False
            return False

        # Update last activity
        session["last_activity"] = datetime.utcnow()
        return session["is_active"]


class AuditLogger:
    """Comprehensive audit logging system"""

    def __init__(self, log_directory: str = "audit_logs"):
        self.log_directory = Path(log_directory)
        self.log_directory.mkdir(exist_ok=True)
        self.audit_entries: List[AuditLogEntry] = []

        # Configure file logging
        log_file = self.log_directory / f"audit_{datetime.now().strftime('%Y%m%d')}.log"
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger("audit")

    def log_event(self, event_type: AuditEventType, user_id: str, action: str,
                  resource_type: Optional[str] = None, resource_id: Optional[str] = None,
                  ip_address: Optional[str] = None, session_id: Optional[str] = None,
                  success: bool = True, error_message: Optional[str] = None,
                  details: Optional[Dict[str, Any]] = None) -> AuditLogEntry:
        """Log an audit event"""

        # Calculate risk score
        risk_score = self._calculate_risk_score(event_type, success, details)

        entry = AuditLogEntry(
            log_id=str(uuid.uuid4()),
            event_type=event_type,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            ip_address=ip_address,
            session_id=session_id,
            success=success,
            error_message=error_message,
            details=details or {},
            risk_score=risk_score
        )

        self.audit_entries.append(entry)

        # Log to file
        log_message = (
            f"USER:{user_id} ACTION:{action} TYPE:{event_type.value} "
            f"SUCCESS:{success} RISK:{risk_score} "
            f"RESOURCE:{resource_type}:{resource_id} "
            f"DETAILS:{json.dumps(details) if details else '{}'}"
        )

        if success:
            self.logger.info(log_message)
        else:
            self.logger.error(f"{log_message} ERROR:{error_message}")

        # Alert on high-risk events
        if risk_score >= 80:
            self._send_security_alert(entry)

        return entry

    def _calculate_risk_score(self, event_type: AuditEventType, success: bool,
                             details: Optional[Dict[str, Any]]) -> int:
        """Calculate risk score for audit event"""
        base_scores = {
            AuditEventType.LOGIN: 10,
            AuditEventType.LOGOUT: 5,
            AuditEventType.DATA_ACCESS: 20,
            AuditEventType.QUERY_EXECUTION: 15,
            AuditEventType.DATA_EXPORT: 40,
            AuditEventType.CONFIGURATION_CHANGE: 60,
            AuditEventType.USER_MANAGEMENT: 70,
            AuditEventType.POLICY_VIOLATION: 90,
            AuditEventType.UNAUTHORIZED_ACCESS: 95,
            AuditEventType.SYSTEM_ERROR: 30
        }

        score = base_scores.get(event_type, 25)

        # Increase score for failures
        if not success:
            score += 30

        # Adjust based on details
        if details:
            if details.get("sensitive_data"):
                score += 20
            if details.get("bulk_operation"):
                score += 15
            if details.get("after_hours"):
                score += 10

        return min(score, 100)

    def _send_security_alert(self, entry: AuditLogEntry):
        """Send security alert for high-risk events"""
        alert_message = (
            f"🚨 HIGH RISK SECURITY EVENT DETECTED\n"
            f"Event: {entry.event_type.value}\n"
            f"User: {entry.user_id}\n"
            f"Risk Score: {entry.risk_score}/100\n"
            f"Time: {entry.timestamp}\n"
            f"Action: {entry.action}\n"
            f"Success: {entry.success}\n"
        )

        if entry.error_message:
            alert_message += f"Error: {entry.error_message}\n"

        print(alert_message)
        # In production, this would send to security team via email/Slack/etc.

    def search_audit_logs(self, start_date: datetime, end_date: datetime,
                         user_id: Optional[str] = None, event_type: Optional[AuditEventType] = None,
                         min_risk_score: int = 0) -> List[AuditLogEntry]:
        """Search audit logs with filters"""
        filtered_logs = []

        for entry in self.audit_entries:
            # Date filter
            if not (start_date <= entry.timestamp <= end_date):
                continue

            # User filter
            if user_id and entry.user_id != user_id:
                continue

            # Event type filter
            if event_type and entry.event_type != event_type:
                continue

            # Risk score filter
            if entry.risk_score < min_risk_score:
                continue

            filtered_logs.append(entry)

        return sorted(filtered_logs, key=lambda x: x.timestamp, reverse=True)

    def generate_audit_summary(self, days: int = 7) -> Dict[str, Any]:
        """Generate audit summary for specified period"""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        period_logs = self.search_audit_logs(start_date, end_date)

        summary = {
            "period": f"{start_date.date()} to {end_date.date()}",
            "total_events": len(period_logs),
            "unique_users": len(set(log.user_id for log in period_logs)),
            "event_types": {},
            "risk_distribution": {"low": 0, "medium": 0, "high": 0, "critical": 0},
            "failed_events": len([log for log in period_logs if not log.success]),
            "top_users": {},
            "high_risk_events": []
        }

        # Analyze event types
        for log in period_logs:
            event_type = log.event_type.value
            summary["event_types"][event_type] = summary["event_types"].get(event_type, 0) + 1

        # Risk distribution
        for log in period_logs:
            if log.risk_score < 25:
                summary["risk_distribution"]["low"] += 1
            elif log.risk_score < 50:
                summary["risk_distribution"]["medium"] += 1
            elif log.risk_score < 75:
                summary["risk_distribution"]["high"] += 1
            else:
                summary["risk_distribution"]["critical"] += 1

        # Top users by activity
        user_counts = {}
        for log in period_logs:
            user_counts[log.user_id] = user_counts.get(log.user_id, 0) + 1

        summary["top_users"] = dict(sorted(user_counts.items(), key=lambda x: x[1], reverse=True)[:10])

        # High risk events
        summary["high_risk_events"] = [
            {
                "timestamp": log.timestamp.isoformat(),
                "user": log.user_id,
                "event": log.event_type.value,
                "risk_score": log.risk_score,
                "action": log.action
            }
            for log in period_logs if log.risk_score >= 75
        ][:20]  # Top 20 high-risk events

        return summary


class ComplianceManager:
    """Manages compliance reporting and monitoring"""

    def __init__(self, audit_logger: AuditLogger):
        self.audit_logger = audit_logger
        self.compliance_reports: Dict[str, ComplianceReport] = {}

    def generate_compliance_report(self, report_type: str, days: int = 30) -> ComplianceReport:
        """Generate compliance report"""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        report = ComplianceReport(
            report_id=str(uuid.uuid4()),
            report_type=report_type,
            period_start=start_date,
            period_end=end_date
        )

        # Get audit data for period
        audit_logs = self.audit_logger.search_audit_logs(start_date, end_date)

        # Analyze compliance based on report type
        if report_type == "data_access_compliance":
            self._analyze_data_access_compliance(report, audit_logs)
        elif report_type == "user_activity_compliance":
            self._analyze_user_activity_compliance(report, audit_logs)
        elif report_type == "security_incidents":
            self._analyze_security_incidents(report, audit_logs)
        elif report_type == "data_retention_compliance":
            self._analyze_data_retention_compliance(report)

        # Calculate overall compliance score
        self._calculate_compliance_score(report)

        self.compliance_reports[report.report_id] = report
        return report

    def _analyze_data_access_compliance(self, report: ComplianceReport, logs: List[AuditLogEntry]):
        """Analyze data access compliance"""
        data_access_logs = [log for log in logs if log.event_type == AuditEventType.DATA_ACCESS]

        findings = []

        # Check for unauthorized access attempts
        unauthorized_attempts = [log for log in data_access_logs if not log.success]
        if unauthorized_attempts:
            findings.append({
                "type": "unauthorized_access_attempts",
                "severity": "high",
                "count": len(unauthorized_attempts),
                "description": f"Found {len(unauthorized_attempts)} unauthorized data access attempts"
            })

        # Check for after-hours access
        after_hours_access = [
            log for log in data_access_logs
            if log.timestamp.hour < 6 or log.timestamp.hour > 22
        ]
        if len(after_hours_access) > 10:  # Threshold
            findings.append({
                "type": "after_hours_access",
                "severity": "medium",
                "count": len(after_hours_access),
                "description": f"High volume of after-hours data access: {len(after_hours_access)} events"
            })

        report.findings.extend(findings)

        if unauthorized_attempts:
            report.recommendations.append("Review and strengthen access controls")
            report.recommendations.append("Implement additional authentication factors for sensitive data")

    def _analyze_user_activity_compliance(self, report: ComplianceReport, logs: List[AuditLogEntry]):
        """Analyze user activity compliance"""
        user_activity = {}
        for log in logs:
            if log.user_id not in user_activity:
                user_activity[log.user_id] = {"total": 0, "failed": 0, "high_risk": 0}

            user_activity[log.user_id]["total"] += 1
            if not log.success:
                user_activity[log.user_id]["failed"] += 1
            if log.risk_score >= 75:
                user_activity[log.user_id]["high_risk"] += 1

        findings = []

        # Check for users with high failure rates
        for user_id, activity in user_activity.items():
            if activity["total"] > 10 and activity["failed"] / activity["total"] > 0.2:
                findings.append({
                    "type": "high_failure_rate",
                    "severity": "medium",
                    "user": user_id,
                    "failure_rate": activity["failed"] / activity["total"],
                    "description": f"User {user_id} has high failure rate: {activity['failed']}/{activity['total']}"
                })

        report.findings.extend(findings)

    def _analyze_security_incidents(self, report: ComplianceReport, logs: List[AuditLogEntry]):
        """Analyze security incidents"""
        security_logs = [
            log for log in logs
            if log.event_type in [AuditEventType.POLICY_VIOLATION, AuditEventType.UNAUTHORIZED_ACCESS]
        ]

        if security_logs:
            report.findings.append({
                "type": "security_incidents",
                "severity": "critical",
                "count": len(security_logs),
                "description": f"Found {len(security_logs)} security incidents requiring investigation"
            })

            report.recommendations.append("Investigate all security incidents")
            report.recommendations.append("Review and update security policies")

    def _analyze_data_retention_compliance(self, report: ComplianceReport):
        """Analyze data retention compliance"""
        # This would check actual data retention against policies
        # For demo purposes, we'll simulate some findings
        report.findings.append({
            "type": "data_retention",
            "severity": "low",
            "description": "All data retention policies are being followed"
        })

    def _calculate_compliance_score(self, report: ComplianceReport):
        """Calculate overall compliance score"""
        if not report.findings:
            report.compliance_score = 100
            report.risk_level = "low"
            return

        # Deduct points based on findings severity
        deductions = 0
        for finding in report.findings:
            severity = finding.get("severity", "low")
            if severity == "critical":
                deductions += 25
            elif severity == "high":
                deductions += 15
            elif severity == "medium":
                deductions += 8
            else:  # low
                deductions += 3

        report.compliance_score = max(0, 100 - deductions)

        # Set risk level
        if report.compliance_score >= 90:
            report.risk_level = "low"
        elif report.compliance_score >= 70:
            report.risk_level = "medium"
        elif report.compliance_score >= 50:
            report.risk_level = "high"
        else:
            report.risk_level = "critical"


class GovernanceFramework:
    """Main governance framework orchestrating all security components"""

    def __init__(self):
        self.access_control = AccessControlManager()
        self.audit_logger = AuditLogger()
        self.compliance_manager = ComplianceManager(self.audit_logger)

    def authorize_request(self, user_id: str, user_role: UserRole, session_id: str,
                         resource_type: str, resource_id: str, action: str,
                         ip_address: Optional[str] = None) -> bool:
        """Authorize a user request with full audit logging"""

        # Validate session
        if not self.access_control.validate_session(session_id):
            self.audit_logger.log_event(
                AuditEventType.UNAUTHORIZED_ACCESS,
                user_id,
                action,
                resource_type,
                resource_id,
                ip_address,
                session_id,
                success=False,
                error_message="Invalid session"
            )
            return False

        # Check permissions
        has_permission = self.access_control.check_permission(
            user_id, user_role, resource_type, resource_id, action
        )

        # Log the authorization attempt
        event_type = AuditEventType.DATA_ACCESS if "read" in action.lower() else AuditEventType.QUERY_EXECUTION

        self.audit_logger.log_event(
            event_type,
            user_id,
            action,
            resource_type,
            resource_id,
            ip_address,
            session_id,
            success=has_permission,
            error_message="Insufficient permissions" if not has_permission else None,
            details={
                "user_role": user_role.value,
                "requested_action": action,
                "authorization_result": has_permission
            }
        )

        return has_permission

    def get_governance_dashboard_data(self) -> Dict[str, Any]:
        """Get data for governance dashboard"""
        # Recent audit summary
        audit_summary = self.audit_logger.generate_audit_summary(7)

        # Active sessions
        active_sessions = len([s for s in self.access_control.active_sessions.values() if s["is_active"]])

        # Recent compliance report
        compliance_report = self.compliance_manager.generate_compliance_report("security_incidents", 7)

        return {
            "audit_summary": audit_summary,
            "active_sessions": active_sessions,
            "security_policies": len(self.access_control.policies),
            "compliance_score": compliance_report.compliance_score,
            "risk_level": compliance_report.risk_level,
            "recent_findings": len(compliance_report.findings),
            "system_health": "healthy"  # Would be calculated from various metrics
        }


def demo_governance_framework():
    """Demonstrate the governance framework"""
    print("🔒 CAL FIRE Security and Governance Framework Demo")
    print("=" * 60)

    # Initialize framework
    governance = GovernanceFramework()

    # Demo 1: User authentication and authorization
    print("\n🔐 Demo 1: User Authentication and Authorization")
    user_id = "fire_chief_001"
    session_id = str(uuid.uuid4())
    ip_address = "192.168.1.100"

    # Authenticate user
    auth_success = governance.access_control.authenticate_user(user_id, session_id, ip_address)
    print(f"✅ User authentication: {auth_success}")

    # Test authorization
    authorized = governance.authorize_request(
        user_id,
        UserRole.FIRE_CHIEF,
        session_id,
        "fire_incidents",
        "incident_001",
        "read",
        ip_address
    )
    print(f"✅ Authorization for fire data access: {authorized}")

    # Test unauthorized access
    unauthorized = governance.authorize_request(
        user_id,
        UserRole.VIEWER,  # Wrong role
        session_id,
        "confidential_reports",
        "report_001",
        "read",
        ip_address
    )
    print(f"✅ Unauthorized access attempt blocked: {not unauthorized}")

    # Demo 2: Audit logging
    print("\n📊 Demo 2: Audit Logging")

    # Simulate various events
    governance.audit_logger.log_event(
        AuditEventType.DATA_EXPORT,
        user_id,
        "export_fire_data",
        "fire_incidents",
        "all",
        ip_address,
        session_id,
        success=True,
        details={"format": "csv", "record_count": 1500, "sensitive_data": True}
    )

    # Simulate failed login
    governance.audit_logger.log_event(
        AuditEventType.LOGIN,
        "unknown_user",
        "login_attempt",
        success=False,
        error_message="Invalid credentials",
        details={"login_method": "password", "attempts": 3}
    )

    audit_summary = governance.audit_logger.generate_audit_summary(1)
    print(f"✅ Audit events logged: {audit_summary['total_events']}")
    print(f"✅ Failed events: {audit_summary['failed_events']}")

    # Demo 3: Permission management
    print("\n🛡️ Demo 3: Permission Management")

    # Grant temporary permission
    permission = governance.access_control.grant_permission(
        "analyst_001",
        "emergency_data",
        "incident_001",
        AccessLevel.RESTRICTED,
        "fire_chief_001",
        expires_in_days=1
    )
    print(f"✅ Temporary permission granted: {permission.permission_id}")

    # Check the new permission
    has_perm = governance.access_control.check_permission(
        "analyst_001",
        UserRole.ANALYST,
        "emergency_data",
        "incident_001",
        "read"
    )
    print(f"✅ Permission check passed: {has_perm}")

    # Demo 4: Compliance reporting
    print("\n📋 Demo 4: Compliance Reporting")

    compliance_report = governance.compliance_manager.generate_compliance_report(
        "data_access_compliance",
        7
    )
    print(f"✅ Compliance report generated: {compliance_report.report_id}")
    print(f"✅ Compliance score: {compliance_report.compliance_score}/100")
    print(f"✅ Risk level: {compliance_report.risk_level}")
    print(f"✅ Findings: {len(compliance_report.findings)}")

    # Demo 5: Governance dashboard
    print("\n📈 Demo 5: Governance Dashboard")

    dashboard_data = governance.get_governance_dashboard_data()
    print(f"✅ Active sessions: {dashboard_data['active_sessions']}")
    print(f"✅ Security policies: {dashboard_data['security_policies']}")
    print(f"✅ System compliance: {dashboard_data['compliance_score']}/100")
    print(f"✅ Risk level: {dashboard_data['risk_level']}")

    print("\n🎯 Security and Governance Framework Demo Completed!")
    print(f"🔒 Total security policies: {len(governance.access_control.policies)}")
    print(f"📊 Total audit entries: {len(governance.audit_logger.audit_entries)}")
    print(f"📋 Total compliance reports: {len(governance.compliance_manager.compliance_reports)}")


if __name__ == "__main__":
    demo_governance_framework()