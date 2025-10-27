# Authentication Guide

Complete guide to authentication methods and security in the Wildfire Intelligence Platform API.

## Overview

The Wildfire Intelligence Platform uses multiple authentication methods to ensure secure access to resources while supporting various integration patterns:

- **OAuth2 with Bearer Tokens**: Primary method for web applications
- **API Keys**: For service-to-service communication
- **JWT Tokens**: For stateless authentication
- **Multi-Factor Authentication**: For enhanced security

## Authentication Methods

### 1. OAuth2 Bearer Tokens

OAuth2 is the primary authentication method for interactive applications.

#### Supported Grant Types

##### Authorization Code Flow (Web Applications)
```http
# Step 1: Redirect user to authorization endpoint
GET /auth/oauth2/authorize?
  response_type=code&
  client_id=your_client_id&
  redirect_uri=https://yourapp.com/callback&
  scope=read write&
  state=random_state_string

# Step 2: Exchange authorization code for tokens
POST /auth/oauth2/token
Content-Type: application/x-www-form-urlencoded

grant_type=authorization_code&
client_id=your_client_id&
client_secret=your_client_secret&
code=received_auth_code&
redirect_uri=https://yourapp.com/callback
```

##### Client Credentials Flow (Service-to-Service)
```http
POST /auth/oauth2/token
Content-Type: application/x-www-form-urlencoded

grant_type=client_credentials&
client_id=your_client_id&
client_secret=your_client_secret&
scope=read write
```

##### Resource Owner Password Credentials (Testing Only)
```http
POST /auth/oauth2/token
Content-Type: application/x-www-form-urlencoded

grant_type=password&
username=user@example.com&
password=user_password&
client_id=your_client_id&
client_secret=your_client_secret&
scope=read write
```

#### Token Response Format
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "scope": "read write"
}
```

#### Using Bearer Tokens
```http
GET /api/v1/dashboard/metrics
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### 2. API Keys

API Keys provide simple authentication for service-to-service communication.

#### Obtaining API Keys
API keys are generated through the Admin Console or API:

```http
POST /admin/api-keys
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "name": "Data Ingestion Service",
  "scopes": ["fire-risk:read", "incidents:write"],
  "expiresIn": "365d"
}
```

Response:
```json
{
  "success": true,
  "data": {
    "id": "api_key_123",
    "name": "Data Ingestion Service", 
    "key": "wip_1234567890abcdef1234567890abcdef",
    "scopes": ["fire-risk:read", "incidents:write"],
    "createdAt": "2024-01-15T10:30:00Z",
    "expiresAt": "2025-01-15T10:30:00Z"
  }
}
```

#### Using API Keys

##### Header Method (Recommended)
```http
GET /api/v1/fire-risk/current
X-API-Key: wip_1234567890abcdef1234567890abcdef
```

##### Query Parameter Method
```http
GET /api/v1/fire-risk/current?api_key=wip_1234567890abcdef1234567890abcdef
```

### 3. Username/Password Authentication

Simple authentication for development and testing.

```http
POST /auth/login
Content-Type: application/json

{
  "username": "john.smith@calfire.ca.gov",
  "password": "secure_password123"
}
```

Response:
```json
{
  "success": true,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "Bearer",
    "expires_in": 3600,
    "user": {
      "id": "user_123",
      "username": "john.smith",
      "email": "john.smith@calfire.ca.gov",
      "role": "fire-chief",
      "firstName": "John",
      "lastName": "Smith"
    }
  }
}
```

## Token Management

### Token Refresh
Access tokens expire for security. Use refresh tokens to obtain new access tokens:

```http
POST /auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

Response:
```json
{
  "success": true,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "Bearer",
    "expires_in": 3600
  }
}
```

### Token Introspection
Validate token status and get token information:

```http
POST /auth/introspect
Content-Type: application/x-www-form-urlencoded

token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

Response:
```json
{
  "active": true,
  "client_id": "your_client_id",
  "username": "john.smith",
  "scope": "read write",
  "exp": 1640995200,
  "iat": 1640991600,
  "sub": "user_123"
}
```

### Token Revocation
Revoke tokens when no longer needed:

```http
POST /auth/revoke
Content-Type: application/x-www-form-urlencoded

token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...&
token_type_hint=access_token
```

## Scopes and Permissions

### Available Scopes

#### Read Scopes
- `dashboard:read`: Access dashboard data
- `incidents:read`: Read incident information
- `fire-risk:read`: Access fire risk data
- `weather:read`: Read weather information
- `resources:read`: View resource information
- `analytics:read`: Access analytics data

#### Write Scopes
- `incidents:write`: Create/update incidents
- `resources:write`: Manage resources
- `alerts:write`: Create alerts and notifications
- `users:write`: Manage user accounts (admin only)

#### Admin Scopes
- `admin:read`: Read system administration data
- `admin:write`: Perform system administration tasks
- `system:monitor`: Access system monitoring data

### Scope Usage
```http
# Request specific scopes
POST /auth/oauth2/token
Content-Type: application/x-www-form-urlencoded

grant_type=client_credentials&
client_id=your_client_id&
client_secret=your_client_secret&
scope=incidents:read fire-risk:read weather:read
```

## Multi-Factor Authentication (MFA)

### Enabling MFA
MFA can be enabled through the user profile or enforced by administrators:

```http
POST /auth/mfa/enable
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "method": "totp",
  "phone": "+1-555-0123"
}
```

### MFA Challenge Flow
When MFA is required:

```http
POST /auth/login
Content-Type: application/json

{
  "username": "john.smith@calfire.ca.gov",
  "password": "secure_password123"
}
```

Response when MFA is required:
```json
{
  "success": false,
  "error": {
    "code": "MFA_REQUIRED",
    "message": "Multi-factor authentication required",
    "challenge_token": "mfa_challenge_xyz789"
  }
}
```

Complete MFA challenge:
```http
POST /auth/mfa/verify
Content-Type: application/json

{
  "challenge_token": "mfa_challenge_xyz789",
  "method": "totp",
  "code": "123456"
}
```

## Security Best Practices

### Token Storage
- **Web Applications**: Store tokens in httpOnly cookies
- **Mobile Apps**: Use secure keychain/keystore
- **Server Applications**: Use environment variables or secure vaults

### Token Rotation
- Implement automatic token refresh before expiration
- Rotate API keys regularly (recommended: every 90 days)
- Use short-lived access tokens (recommended: 1 hour)

### Error Handling
```javascript
// Example token refresh implementation
async function apiRequest(url, options = {}) {
  let token = getAccessToken();
  
  let response = await fetch(url, {
    ...options,
    headers: {
      'Authorization': `Bearer ${token}`,
      ...options.headers
    }
  });
  
  // If token expired, refresh and retry
  if (response.status === 401) {
    token = await refreshAccessToken();
    response = await fetch(url, {
      ...options,
      headers: {
        'Authorization': `Bearer ${token}`,
        ...options.headers
      }
    });
  }
  
  return response;
}
```

## CORS and CSRF Protection

### CORS Configuration
The API supports Cross-Origin Resource Sharing (CORS):

```http
# Preflight request
OPTIONS /api/v1/dashboard/metrics
Origin: https://your-app.com
Access-Control-Request-Method: GET
Access-Control-Request-Headers: Authorization

# Response
Access-Control-Allow-Origin: https://your-app.com
Access-Control-Allow-Methods: GET, POST, PUT, DELETE
Access-Control-Allow-Headers: Authorization, Content-Type
Access-Control-Max-Age: 86400
```

### CSRF Protection
For web applications using cookies:

```http
GET /auth/csrf-token
Authorization: Bearer {access_token}

# Response
{
  "csrf_token": "csrf_abc123xyz"
}

# Use token in requests
POST /api/v1/incidents
Authorization: Bearer {access_token}
X-CSRF-Token: csrf_abc123xyz
Content-Type: application/json
```

## Rate Limiting by Authentication Method

Different authentication methods have different rate limits:

### Bearer Tokens (Authenticated Users)
- **Rate Limit**: 1000 requests per hour
- **Burst Limit**: 100 requests per minute
- **Headers**: `X-RateLimit-*` headers included in responses

### API Keys
- **Rate Limit**: Varies by key configuration (default: 5000/hour)
- **Burst Limit**: 200 requests per minute
- **Custom Limits**: Available for enterprise customers

### Public Endpoints (No Authentication)
- **Rate Limit**: 100 requests per hour
- **Burst Limit**: 10 requests per minute
- **IP-based**: Limits applied per source IP

## Error Responses

### Authentication Errors
```json
{
  "success": false,
  "error": {
    "code": "AUTH_TOKEN_INVALID",
    "message": "Invalid or expired authentication token"
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Authorization Errors
```json
{
  "success": false,
  "error": {
    "code": "AUTH_INSUFFICIENT_PERMISSIONS",
    "message": "User lacks required permissions for this resource",
    "required_scopes": ["incidents:write"]
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Rate Limit Errors
```json
{
  "success": false,
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests",
    "retry_after": 300
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## SDK Examples

### Python SDK Authentication
```python
from wildfire_intelligence import WildfireAPI

# OAuth2 Client Credentials
client = WildfireAPI(
    base_url="https://api.wildfire-intelligence.com/api/v1",
    client_id="your_client_id",
    client_secret="your_client_secret"
)

# API Key
client = WildfireAPI(
    base_url="https://api.wildfire-intelligence.com/api/v1",
    api_key="wip_1234567890abcdef1234567890abcdef"
)

# Username/Password
client = WildfireAPI(
    base_url="https://api.wildfire-intelligence.com/api/v1",
    username="john.smith@calfire.ca.gov",
    password="secure_password123"
)
```

### JavaScript SDK Authentication
```javascript
import { WildfireAPI } from 'wildfire-intelligence-sdk';

// OAuth2 Client Credentials
const client = new WildfireAPI({
  baseURL: 'https://api.wildfire-intelligence.com/api/v1',
  auth: {
    type: 'oauth2',
    clientId: 'your_client_id',
    clientSecret: 'your_client_secret'
  }
});

// API Key
const client = new WildfireAPI({
  baseURL: 'https://api.wildfire-intelligence.com/api/v1',
  auth: {
    type: 'apiKey',
    apiKey: 'wip_1234567890abcdef1234567890abcdef'
  }
});

// Bearer Token
const client = new WildfireAPI({
  baseURL: 'https://api.wildfire-intelligence.com/api/v1',
  auth: {
    type: 'bearer',
    token: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'
  }
});
```

---

For additional security questions or to report security issues, contact: security@wildfire-intelligence.com