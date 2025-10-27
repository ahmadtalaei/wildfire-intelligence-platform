"""
Security & Governance Layer - Access Control
Challenge 3 Deliverable: RBAC, Authentication, Authorization
"""

from fastapi import HTTPException, Header, Depends
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import jwt
import hashlib
import secrets
from enum import Enum


class UserRole(str, Enum):
    """User roles for RBAC"""
    ADMINISTRATOR = "administrator"
    DATA_SCIENTIST = "data_scientist"
    ANALYST = "analyst"
    BUSINESS_USER = "business_user"
    PARTNER_AGENCY = "partner_agency"
    EXTERNAL_RESEARCHER = "external_researcher"


class AccessLevel(str, Enum):
    """Data access levels"""
    PUBLIC = "public"
    INTERNAL = "internal"
    SENSITIVE = "sensitive"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class Permission(str, Enum):
    """Granular permissions"""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    EXPORT = "export"
    SHARE = "share"
    ADMIN = "admin"


# Role-based permissions matrix
ROLE_PERMISSIONS = {
    UserRole.ADMINISTRATOR: [
        Permission.READ, Permission.WRITE, Permission.DELETE,
        Permission.EXPORT, Permission.SHARE, Permission.ADMIN
    ],
    UserRole.DATA_SCIENTIST: [
        Permission.READ, Permission.EXPORT
    ],
    UserRole.ANALYST: [
        Permission.READ, Permission.EXPORT
    ],
    UserRole.BUSINESS_USER: [
        Permission.READ
    ],
    UserRole.PARTNER_AGENCY: [
        Permission.READ, Permission.EXPORT, Permission.SHARE
    ],
    UserRole.EXTERNAL_RESEARCHER: [
        Permission.READ
    ]
}

# Role-based dataset access
ROLE_ACCESS_LEVELS = {
    UserRole.ADMINISTRATOR: [
        AccessLevel.PUBLIC, AccessLevel.INTERNAL,
        AccessLevel.SENSITIVE, AccessLevel.CONFIDENTIAL, AccessLevel.RESTRICTED
    ],
    UserRole.DATA_SCIENTIST: [
        AccessLevel.PUBLIC, AccessLevel.INTERNAL, AccessLevel.SENSITIVE
    ],
    UserRole.ANALYST: [
        AccessLevel.PUBLIC, AccessLevel.INTERNAL
    ],
    UserRole.BUSINESS_USER: [
        AccessLevel.PUBLIC
    ],
    UserRole.PARTNER_AGENCY: [
        AccessLevel.PUBLIC, AccessLevel.INTERNAL
    ],
    UserRole.EXTERNAL_RESEARCHER: [
        AccessLevel.PUBLIC
    ]
}


class AccessControlManager:
    """
    Comprehensive access control and RBAC management

    Challenge 3 Deliverable Features:
    - Role-based access control (RBAC)
    - API key management
    - Session management
    - Audit logging
    """

    def __init__(self, secret_key: str = None):
        self.secret_key = secret_key or secrets.token_urlsafe(32)
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.api_keys: Dict[str, Dict[str, Any]] = {}
        self.audit_log: List[Dict[str, Any]] = []

    def generate_api_key(
        self,
        user_id: str,
        role: UserRole,
        expires_days: int = 90
    ) -> str:
        """
        Generate API key for user authentication

        Args:
            user_id: Unique user identifier
            role: User role for permissions
            expires_days: API key expiration in days

        Returns:
            Generated API key string
        """
        # Generate secure API key
        raw_key = secrets.token_urlsafe(32)
        api_key = f"wip_{role.value[:3]}_{raw_key}"

        # Store API key metadata
        self.api_keys[api_key] = {
            "user_id": user_id,
            "role": role,
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(days=expires_days),
            "last_used": None,
            "usage_count": 0
        }

        self._log_audit("api_key_generated", user_id, {"role": role.value})

        return api_key

    def validate_api_key(self, api_key: str) -> Dict[str, Any]:
        """
        Validate API key and return user metadata

        Args:
            api_key: API key to validate

        Returns:
            User metadata if valid

        Raises:
            HTTPException: If API key is invalid or expired
        """
        if api_key not in self.api_keys:
            raise HTTPException(status_code=401, detail="Invalid API key")

        key_data = self.api_keys[api_key]

        # Check expiration
        if datetime.utcnow() > key_data["expires_at"]:
            raise HTTPException(status_code=401, detail="API key expired")

        # Update usage statistics
        key_data["last_used"] = datetime.utcnow()
        key_data["usage_count"] += 1

        return key_data

    def check_permission(
        self,
        role: UserRole,
        required_permission: Permission
    ) -> bool:
        """
        Check if role has required permission

        Args:
            role: User role
            required_permission: Permission to check

        Returns:
            True if permission granted
        """
        return required_permission in ROLE_PERMISSIONS.get(role, [])

    def check_dataset_access(
        self,
        role: UserRole,
        dataset_access_level: AccessLevel
    ) -> bool:
        """
        Check if role can access dataset based on classification

        Args:
            role: User role
            dataset_access_level: Dataset classification level

        Returns:
            True if access granted
        """
        allowed_levels = ROLE_ACCESS_LEVELS.get(role, [])
        return dataset_access_level in allowed_levels

    def create_session(
        self,
        user_id: str,
        role: UserRole,
        mfa_verified: bool = False
    ) -> str:
        """
        Create authenticated session

        Args:
            user_id: User identifier
            role: User role
            mfa_verified: Whether MFA was completed

        Returns:
            Session token
        """
        session_token = secrets.token_urlsafe(32)

        self.active_sessions[session_token] = {
            "user_id": user_id,
            "role": role,
            "mfa_verified": mfa_verified,
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(hours=24),
            "ip_address": None,  # Would be populated from request
            "user_agent": None
        }

        self._log_audit("session_created", user_id, {
            "role": role.value,
            "mfa": mfa_verified
        })

        return session_token

    def validate_session(self, session_token: str) -> Dict[str, Any]:
        """
        Validate session token

        Args:
            session_token: Session token to validate

        Returns:
            Session metadata

        Raises:
            HTTPException: If session invalid or expired
        """
        if session_token not in self.active_sessions:
            raise HTTPException(status_code=401, detail="Invalid session")

        session = self.active_sessions[session_token]

        if datetime.utcnow() > session["expires_at"]:
            del self.active_sessions[session_token]
            raise HTTPException(status_code=401, detail="Session expired")

        return session

    def require_mfa(self, session_token: str) -> bool:
        """
        Check if session requires MFA for sensitive operations

        Args:
            session_token: Session token

        Returns:
            True if MFA verified

        Raises:
            HTTPException: If MFA required but not verified
        """
        session = self.validate_session(session_token)

        if not session["mfa_verified"]:
            raise HTTPException(
                status_code=403,
                detail="Multi-factor authentication required for this operation"
            )

        return True

    def _log_audit(
        self,
        action: str,
        user_id: str,
        details: Dict[str, Any]
    ):
        """
        Log audit event

        Args:
            action: Action type
            user_id: User performing action
            details: Additional details
        """
        self.audit_log.append({
            "timestamp": datetime.utcnow().isoformat(),
            "action": action,
            "user_id": user_id,
            "details": details
        })

    def get_audit_log(
        self,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Query audit log

        Args:
            user_id: Filter by user
            action: Filter by action type
            start_date: Filter by start date
            end_date: Filter by end date
            limit: Maximum results

        Returns:
            Filtered audit log entries
        """
        filtered_log = self.audit_log

        if user_id:
            filtered_log = [e for e in filtered_log if e["user_id"] == user_id]

        if action:
            filtered_log = [e for e in filtered_log if e["action"] == action]

        if start_date:
            filtered_log = [
                e for e in filtered_log
                if datetime.fromisoformat(e["timestamp"]) >= start_date
            ]

        if end_date:
            filtered_log = [
                e for e in filtered_log
                if datetime.fromisoformat(e["timestamp"]) <= end_date
            ]

        return filtered_log[:limit]

    def get_user_activity_summary(self, user_id: str) -> Dict[str, Any]:
        """
        Get user activity summary

        Args:
            user_id: User identifier

        Returns:
            Activity summary
        """
        user_events = [e for e in self.audit_log if e["user_id"] == user_id]

        return {
            "user_id": user_id,
            "total_actions": len(user_events),
            "recent_actions": user_events[-10:],
            "action_types": list(set(e["action"] for e in user_events)),
            "first_activity": user_events[0]["timestamp"] if user_events else None,
            "last_activity": user_events[-1]["timestamp"] if user_events else None
        }


# Dependency for FastAPI routes
async def verify_api_key(
    x_api_key: str = Header(..., description="API key for authentication")
) -> Dict[str, Any]:
    """
    FastAPI dependency for API key authentication

    Usage in route:
    @app.get("/protected")
    async def protected_route(user: Dict = Depends(verify_api_key)):
        return {"user": user["user_id"]}
    """
    # This would use a global instance in production
    acm = AccessControlManager()
    return acm.validate_api_key(x_api_key)


async def verify_session(
    authorization: str = Header(..., description="Bearer session token")
) -> Dict[str, Any]:
    """
    FastAPI dependency for session authentication

    Usage in route:
    @app.get("/dashboard")
    async def dashboard(session: Dict = Depends(verify_session)):
        return {"user": session["user_id"]}
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    session_token = authorization.replace("Bearer ", "")
    acm = AccessControlManager()
    return acm.validate_session(session_token)


def require_permission(required_permission: Permission):
    """
    Decorator to require specific permission

    Usage:
    @app.post("/dataset")
    @require_permission(Permission.WRITE)
    async def create_dataset(user: Dict = Depends(verify_api_key)):
        pass
    """
    def decorator(func):
        async def wrapper(*args, user: Dict = Depends(verify_api_key), **kwargs):
            acm = AccessControlManager()
            role = UserRole(user["role"])

            if not acm.check_permission(role, required_permission):
                raise HTTPException(
                    status_code=403,
                    detail=f"Permission denied: {required_permission.value} required"
                )

            return await func(*args, user=user, **kwargs)
        return wrapper
    return decorator
