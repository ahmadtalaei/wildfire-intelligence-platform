"""
Data Storage Service - Security Middleware
Comprehensive security middleware for authentication, authorization, and threat protection
"""

import hashlib
import hmac
import json
import time
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
from ipaddress import ip_address, ip_network
from urllib.parse import urlparse

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import structlog

logger = structlog.get_logger()

class SecurityConfig:
    """Security configuration settings"""
    
    def __init__(self):
        # Rate limiting configuration
        self.rate_limit_requests = 100  # requests per window
        self.rate_limit_window = 60     # window in seconds
        self.rate_limit_burst = 20      # burst allowance
        
        # Request size limits
        self.max_request_size = 100 * 1024 * 1024  # 100MB
        self.max_bulk_items = 10000
        
        # Security headers
        self.security_headers = {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
            'Content-Security-Policy': "default-src 'self'",
            'Referrer-Policy': 'strict-origin-when-cross-origin'
        }
        
        # Allowed IP ranges (CIDR notation)
        self.allowed_ip_ranges = [
            '10.0.0.0/8',      # Private networks
            '172.16.0.0/12',   # Private networks
            '192.168.0.0/16',  # Private networks
            '127.0.0.0/8'      # Localhost
        ]
        
        # Blocked user agents (security scanners, bots)
        self.blocked_user_agents = [
            'sqlmap',
            'nikto',
            'nessus',
            'acunetix',
            'nuclei',
            'burpsuite'
        ]
        
        # API key configuration
        self.api_key_header = 'X-API-Key'
        self.api_key_query_param = 'api_key'
        self.require_api_key = True
        
        # JWT configuration
        self.jwt_secret_key = 'your-secret-key-here'  # Should come from environment
        self.jwt_algorithm = 'HS256'
        self.jwt_expiry_hours = 24


class RateLimiter:
    """Token bucket rate limiter with IP-based tracking"""
    
    def __init__(self, config: SecurityConfig):
        self.config = config
        self.buckets: Dict[str, Dict] = {}
        self.cleanup_interval = 300  # 5 minutes
        self.last_cleanup = time.time()
    
    def is_allowed(self, client_ip: str) -> bool:
        """Check if request is allowed based on rate limits"""
        current_time = time.time()
        
        # Cleanup old entries periodically
        if current_time - self.last_cleanup > self.cleanup_interval:
            self._cleanup_expired_buckets(current_time)
            self.last_cleanup = current_time
        
        # Get or create bucket for this IP
        if client_ip not in self.buckets:
            self.buckets[client_ip] = {
                'tokens': self.config.rate_limit_requests,
                'last_refill': current_time,
                'requests_this_window': 0,
                'window_start': current_time
            }
        
        bucket = self.buckets[client_ip]
        
        # Check if we need to start a new window
        if current_time - bucket['window_start'] >= self.config.rate_limit_window:
            bucket['requests_this_window'] = 0
            bucket['window_start'] = current_time
            bucket['tokens'] = self.config.rate_limit_requests
        
        # Refill tokens based on time elapsed
        time_elapsed = current_time - bucket['last_refill']
        tokens_to_add = time_elapsed * (self.config.rate_limit_requests / self.config.rate_limit_window)
        bucket['tokens'] = min(
            self.config.rate_limit_requests + self.config.rate_limit_burst,
            bucket['tokens'] + tokens_to_add
        )
        bucket['last_refill'] = current_time
        
        # Check if request is allowed
        if bucket['tokens'] >= 1:
            bucket['tokens'] -= 1
            bucket['requests_this_window'] += 1
            return True
        
        return False
    
    def _cleanup_expired_buckets(self, current_time: float):
        """Remove expired bucket entries to prevent memory leaks"""
        expired_keys = []
        for ip, bucket in self.buckets.items():
            if current_time - bucket['last_refill'] > self.config.rate_limit_window * 2:
                expired_keys.append(ip)
        
        for key in expired_keys:
            del self.buckets[key]


class ThreatDetector:
    """Detects potential security threats in requests"""
    
    def __init__(self):
        # SQL injection patterns
        self.sql_patterns = [
            r"union\s+select",
            r"select\s+.*\s+from",
            r"drop\s+table",
            r"delete\s+from",
            r"insert\s+into",
            r"update\s+.*\s+set",
            r"--\s*$",
            r"/\*.*\*/"
        ]
        
        # XSS patterns
        self.xss_patterns = [
            r"<script[^>]*>",
            r"javascript:",
            r"on\w+\s*=",
            r"<iframe[^>]*>",
            r"<object[^>]*>",
            r"<embed[^>]*>"
        ]
        
        # Path traversal patterns
        self.path_traversal_patterns = [
            r"\.\./",
            r"\.\.\\",
            r"%2e%2e/",
            r"%2e%2e%2f",
            r"%252e%252e/"
        ]
        
        # Command injection patterns
        self.command_patterns = [
            r";\s*\w+",
            r"\|\s*\w+",
            r"&&\s*\w+",
            r"`\w+`",
            r"\$\(\w+\)"
        ]
    
    def analyze_request(self, request: Request, body_content: str = "") -> List[str]:
        """Analyze request for potential threats"""
        threats = []
        
        # Check URL for threats
        threats.extend(self._check_patterns(str(request.url), "url"))
        
        # Check headers for threats
        for name, value in request.headers.items():
            threats.extend(self._check_patterns(f"{name}:{value}", "header"))
        
        # Check body content for threats
        if body_content:
            threats.extend(self._check_patterns(body_content, "body"))
        
        return threats
    
    def _check_patterns(self, content: str, location: str) -> List[str]:
        """Check content against threat patterns"""
        import re
        
        threats = []
        content_lower = content.lower()
        
        # Check SQL injection
        for pattern in self.sql_patterns:
            if re.search(pattern, content_lower, re.IGNORECASE):
                threats.append(f"SQL injection attempt in {location}")
                break
        
        # Check XSS
        for pattern in self.xss_patterns:
            if re.search(pattern, content_lower, re.IGNORECASE):
                threats.append(f"XSS attempt in {location}")
                break
        
        # Check path traversal
        for pattern in self.path_traversal_patterns:
            if re.search(pattern, content_lower, re.IGNORECASE):
                threats.append(f"Path traversal attempt in {location}")
                break
        
        # Check command injection
        for pattern in self.command_patterns:
            if re.search(pattern, content_lower, re.IGNORECASE):
                threats.append(f"Command injection attempt in {location}")
                break
        
        return threats


class SecurityMiddleware(BaseHTTPMiddleware):
    """
    Comprehensive security middleware providing:
    - Rate limiting with token bucket algorithm
    - IP allowlisting/blocklisting
    - Request size validation
    - Threat detection (SQL injection, XSS, etc.)
    - Security headers
    - API key validation
    - JWT token validation
    - User agent filtering
    """
    
    def __init__(self, app):
        super().__init__(app)
        self.config = SecurityConfig()
        self.rate_limiter = RateLimiter(self.config)
        self.threat_detector = ThreatDetector()
        
        # Compile allowed IP networks for faster checking
        self.allowed_networks = [
            ip_network(cidr) for cidr in self.config.allowed_ip_ranges
        ]
        
        # Security event tracking
        self.security_events: Dict[str, int] = {}
        
        # Exempt paths from certain security checks
        self.exempt_paths = {'/health', '/metrics', '/info', '/stats', '/api/v1/stats', '/api/v1/recent-fires', '/docs', '/openapi.json', '/redoc'}
        
    async def dispatch(self, request: Request, call_next):
        """Main security processing pipeline"""
        start_time = time.time()
        client_ip = self._get_client_ip(request)

        try:
            # Skip security checks for exempt paths
            if request.url.path in self.exempt_paths:
                response = await call_next(request)
                # Add relaxed headers for documentation pages (allow CDN resources)
                if request.url.path in ['/docs', '/openapi.json', '/redoc']:
                    self._add_docs_headers(response)
                else:
                    self._add_security_headers(response)
                return response
            
            # 1. IP allowlist check
            if not self._is_ip_allowed(client_ip):
                logger.warning("Blocked request from disallowed IP", 
                             client_ip=client_ip, 
                             path=request.url.path)
                return self._create_error_response("Access denied", 403)
            
            # 2. Rate limiting check
            if not self.rate_limiter.is_allowed(client_ip):
                logger.warning("Rate limit exceeded", 
                             client_ip=client_ip,
                             path=request.url.path)
                self._record_security_event("rate_limit_exceeded", client_ip)
                return self._create_error_response("Rate limit exceeded", 429)
            
            # 3. User agent check
            user_agent = request.headers.get('user-agent', '').lower()
            if self._is_blocked_user_agent(user_agent):
                logger.warning("Blocked malicious user agent",
                             client_ip=client_ip,
                             user_agent=user_agent)
                self._record_security_event("blocked_user_agent", client_ip)
                return self._create_error_response("Access denied", 403)
            
            # 4. Request size validation
            content_length = int(request.headers.get('content-length', 0))
            if content_length > self.config.max_request_size:
                logger.warning("Request too large",
                             client_ip=client_ip,
                             size=content_length,
                             max_size=self.config.max_request_size)
                return self._create_error_response("Request too large", 413)
            
            # 5. Read request body for threat detection
            body_content = ""
            if content_length > 0 and request.method in ['POST', 'PUT', 'PATCH']:
                try:
                    body = await request.body()
                    body_content = body.decode('utf-8', errors='ignore')
                    
                    # Store body for later use in request processing
                    request.state.raw_body = body
                    
                    # Validate JSON structure if content-type suggests JSON
                    content_type = request.headers.get('content-type', '')
                    if 'application/json' in content_type:
                        try:
                            parsed_json = json.loads(body_content)
                            request.state.json_body = parsed_json
                            
                            # Additional validation for bulk requests
                            if hasattr(parsed_json, 'get'):
                                if 'data_items' in parsed_json:
                                    items_count = len(parsed_json.get('data_items', []))
                                    if items_count > self.config.max_bulk_items:
                                        return self._create_error_response(
                                            f"Too many items in bulk request: {items_count}", 400)
                                        
                        except json.JSONDecodeError:
                            logger.warning("Invalid JSON in request body", client_ip=client_ip)
                            return self._create_error_response("Invalid JSON", 400)
                
                except Exception as e:
                    logger.error("Error reading request body", error=str(e))
                    return self._create_error_response("Bad request", 400)
            
            # 6. Threat detection
            threats = self.threat_detector.analyze_request(request, body_content)
            if threats:
                logger.error("Security threats detected",
                           client_ip=client_ip,
                           threats=threats,
                           path=request.url.path)
                
                for threat in threats:
                    self._record_security_event("threat_detected", client_ip)
                
                return self._create_error_response("Security violation detected", 403)
            
            # 7. API key validation (if required)
            if self.config.require_api_key and not self._validate_api_key(request):
                logger.warning("Invalid or missing API key",
                             client_ip=client_ip,
                             path=request.url.path)
                self._record_security_event("invalid_api_key", client_ip)
                return self._create_error_response("Invalid API key", 401)
            
            # Process request
            response = await call_next(request)
            
            # Add security headers to response
            self._add_security_headers(response)
            
            # Log successful request
            processing_time = time.time() - start_time
            if processing_time > 5.0:  # Log slow requests
                logger.info("Slow request processed",
                           client_ip=client_ip,
                           path=request.url.path,
                           duration=processing_time)
            
            return response
            
        except Exception as e:
            logger.error("Security middleware error", 
                        error=str(e),
                        client_ip=client_ip)
            return self._create_error_response("Internal security error", 500)
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract real client IP from request headers"""
        # Check common proxy headers in order of preference
        headers_to_check = [
            'X-Forwarded-For',
            'X-Real-IP',
            'X-Client-IP',
            'CF-Connecting-IP'  # Cloudflare
        ]
        
        for header in headers_to_check:
            if header in request.headers:
                # X-Forwarded-For can contain multiple IPs, take the first one
                ip = request.headers[header].split(',')[0].strip()
                try:
                    ip_address(ip)  # Validate IP format
                    return ip
                except ValueError:
                    continue
        
        # Fallback to direct connection IP
        return request.client.host if request.client else '0.0.0.0'
    
    def _is_ip_allowed(self, client_ip: str) -> bool:
        """Check if client IP is in allowed ranges"""
        try:
            client_addr = ip_address(client_ip)
            for network in self.allowed_networks:
                if client_addr in network:
                    return True
            return False
        except ValueError:
            # Invalid IP format
            logger.error("Invalid IP address format", ip=client_ip)
            return False
    
    def _is_blocked_user_agent(self, user_agent: str) -> bool:
        """Check if user agent is in blocked list"""
        for blocked_agent in self.config.blocked_user_agents:
            if blocked_agent in user_agent:
                return True
        return False
    
    def _validate_api_key(self, request: Request) -> bool:
        """Validate API key from header or query parameter"""
        # Check header first
        api_key = request.headers.get(self.config.api_key_header)
        
        # Check query parameter if not in header
        if not api_key:
            api_key = request.query_params.get(self.config.api_key_query_param)
        
        if not api_key:
            return False
        
        # In a real implementation, you would validate against a database
        # or external service. For now, we'll use a simple check.
        # TODO: Implement proper API key validation
        return len(api_key) >= 32  # Basic validation - require minimum length
    
    def _add_security_headers(self, response):
        """Add security headers to response"""
        for header, value in self.config.security_headers.items():
            response.headers[header] = value

    def _add_docs_headers(self, response):
        """Add relaxed security headers for API documentation pages"""
        # Relaxed CSP to allow Swagger UI CDN resources
        relaxed_headers = {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
            'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; img-src 'self' data: https://cdn.jsdelivr.net",
            'Referrer-Policy': 'strict-origin-when-cross-origin'
        }
        for header, value in relaxed_headers.items():
            response.headers[header] = value

    def _create_error_response(self, message: str, status_code: int) -> JSONResponse:
        """Create standardized error response"""
        return JSONResponse(
            status_code=status_code,
            content={
                "detail": message,
                "status_code": status_code,
                "timestamp": datetime.utcnow().isoformat(),
                "error_type": "security_violation"
            }
        )
    
    def _record_security_event(self, event_type: str, client_ip: str):
        """Record security events for monitoring"""
        event_key = f"{event_type}:{client_ip}"
        self.security_events[event_key] = self.security_events.get(event_key, 0) + 1
        
        # Log significant events
        if self.security_events[event_key] > 10:  # Multiple violations from same IP
            logger.error("Repeated security violations",
                        event_type=event_type,
                        client_ip=client_ip,
                        violation_count=self.security_events[event_key])


def create_api_key_hash(api_key: str, secret: str) -> str:
    """Create secure hash of API key for storage"""
    return hashlib.pbkdf2_hex(
        api_key.encode('utf-8'),
        secret.encode('utf-8'),
        100000,  # iterations
        32       # key length
    )


def verify_jwt_token(token: str, secret_key: str) -> Optional[Dict]:
    """Verify JWT token and return payload if valid"""
    try:
        import jwt
        payload = jwt.decode(token, secret_key, algorithms=['HS256'])
        return payload
    except jwt.InvalidTokenError:
        return None
    except ImportError:
        logger.error("JWT library not available")
        return None


# Export main components
__all__ = [
    'SecurityMiddleware',
    'SecurityConfig', 
    'RateLimiter',
    'ThreatDetector',
    'create_api_key_hash',
    'verify_jwt_token'
]