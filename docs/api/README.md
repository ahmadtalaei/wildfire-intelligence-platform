# API Documentation

Comprehensive API documentation for the Wildfire Intelligence Platform. All APIs follow RESTful conventions and use JSON for request/response payloads.

## Base URL
- **Development**: `http://localhost:8080/api/v1`
- **Production**: `https://api.wildfire-intelligence.com/api/v1`

## Authentication

### Overview
All API endpoints require authentication using Bearer tokens. The platform supports multiple authentication methods:

- **OAuth2 Bearer Tokens**: Primary authentication method
- **API Keys**: For service-to-service communication
- **JWT Tokens**: For web application authentication

### Getting Access Tokens

#### OAuth2 Flow
```http
POST /auth/oauth2/token
Content-Type: application/x-www-form-urlencoded

grant_type=client_credentials&
client_id=your_client_id&
client_secret=your_client_secret&
scope=read write
```

#### Username/Password Authentication
```http
POST /auth/login
Content-Type: application/json

{
  "username": "your_username",
  "password": "your_password"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "Bearer",
    "expires_in": 3600,
    "scope": "read write"
  }
}
```

### Using Tokens
Include the access token in the Authorization header:

```http
GET /dashboard/metrics
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

## API Endpoints

### Authentication Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/login` | User login |
| POST | `/auth/refresh` | Refresh access token |
| POST | `/auth/logout` | User logout |
| GET | `/auth/profile` | Get user profile |
| PUT | `/auth/profile` | Update user profile |

### Dashboard Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/dashboard/metrics` | Get dashboard metrics |
| GET | `/dashboard/fire-risk` | Get current fire risk data |
| GET | `/dashboard/incidents` | Get active incidents |
| GET | `/dashboard/resources` | Get resource status |
| GET | `/dashboard/alerts` | Get active alerts |

### Incident Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/incidents` | List all incidents |
| POST | `/incidents` | Create new incident |
| GET | `/incidents/{id}` | Get incident details |
| PUT | `/incidents/{id}` | Update incident |
| DELETE | `/incidents/{id}` | Delete incident |
| GET | `/incidents/{id}/resources` | Get incident resources |
| POST | `/incidents/{id}/resources` | Assign resources |

### Fire Risk Assessment

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/fire-risk/current` | Current fire risk levels |
| GET | `/fire-risk/forecast` | Fire risk forecast |
| GET | `/fire-risk/historical` | Historical fire risk data |
| POST | `/fire-risk/predict` | Predict fire risk for location |
| GET | `/fire-risk/zones` | Fire risk zone boundaries |

### Weather Data

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/weather/current` | Current weather conditions |
| GET | `/weather/forecast` | Weather forecast |
| GET | `/weather/historical` | Historical weather data |
| GET | `/weather/stations` | Weather station list |
| GET | `/weather/alerts` | Weather alerts |

### Resource Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/resources` | List all resources |
| POST | `/resources` | Create new resource |
| GET | `/resources/{id}` | Get resource details |
| PUT | `/resources/{id}` | Update resource |
| DELETE | `/resources/{id}` | Delete resource |
| GET | `/resources/{id}/location` | Get resource location |
| PUT | `/resources/{id}/location` | Update resource location |

### Analytics & Reporting

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/analytics/incidents` | Incident analytics |
| GET | `/analytics/performance` | Performance metrics |
| GET | `/analytics/trends` | Trend analysis |
| POST | `/analytics/query` | Custom analytics query |
| GET | `/analytics/reports` | Available reports |
| POST | `/analytics/reports` | Generate report |

### Data Ingestion

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/ingest/batch` | Batch data upload |
| POST | `/ingest/stream` | Stream data ingestion |
| GET | `/ingest/status` | Ingestion job status |
| GET | `/ingest/sources` | Available data sources |
| POST | `/ingest/sources` | Configure data source |

### Machine Learning

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/ml/models` | List available models |
| GET | `/ml/models/{id}` | Get model details |
| POST | `/ml/models/{id}/predict` | Make prediction |
| GET | `/ml/experiments` | List experiments |
| POST | `/ml/experiments` | Create experiment |
| GET | `/ml/experiments/{id}` | Get experiment details |

### Administration

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/admin/users` | List users |
| POST | `/admin/users` | Create user |
| GET | `/admin/users/{id}` | Get user details |
| PUT | `/admin/users/{id}` | Update user |
| DELETE | `/admin/users/{id}` | Delete user |
| GET | `/admin/system/health` | System health check |
| GET | `/admin/system/metrics` | System metrics |

## Data Models

### Common Response Format
All API responses follow this standard format:

```json
{
  "success": boolean,
  "data": object | array,
  "message": "string (optional)",
  "timestamp": "ISO 8601 datetime",
  "pagination": {
    "page": number,
    "limit": number,
    "total": number,
    "totalPages": number
  }
}
```

### Error Response Format
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable error message",
    "details": "Additional error details (optional)"
  },
  "timestamp": "ISO 8601 datetime"
}
```

### Fire Incident Model
```json
{
  "id": "string",
  "name": "string",
  "status": "active | contained | controlled | extinguished",
  "priority": "low | medium | high | critical",
  "location": {
    "latitude": number,
    "longitude": number,
    "address": "string",
    "county": "string"
  },
  "startTime": "ISO 8601 datetime",
  "containmentTime": "ISO 8601 datetime (optional)",
  "acresBurned": number,
  "threatLevel": number,
  "resourcesAssigned": number,
  "description": "string",
  "weatherConditions": {
    "temperature": number,
    "humidity": number,
    "windSpeed": number,
    "windDirection": number
  }
}
```

### Fire Risk Data Model
```json
{
  "location": {
    "latitude": number,
    "longitude": number,
    "name": "string (optional)"
  },
  "riskLevel": "low | moderate | high | very-high | extreme",
  "riskScore": number,
  "factors": {
    "temperature": number,
    "humidity": number,
    "windSpeed": number,
    "vegetationMoisture": number,
    "droughtIndex": number
  },
  "timestamp": "ISO 8601 datetime",
  "validUntil": "ISO 8601 datetime"
}
```

### Resource Model
```json
{
  "id": "string",
  "type": "fire-engine | water-tender | aircraft | crew | dozer",
  "name": "string",
  "status": "available | deployed | maintenance | offline",
  "location": {
    "latitude": number,
    "longitude": number
  },
  "assignedIncident": "string (optional)",
  "capacity": number,
  "currentLoad": number,
  "lastUpdate": "ISO 8601 datetime"
}
```

### User Model
```json
{
  "id": "string",
  "username": "string",
  "email": "string",
  "firstName": "string",
  "lastName": "string",
  "role": "fire-chief | analyst | scientist | admin",
  "department": "string",
  "permissions": ["string"],
  "lastLogin": "ISO 8601 datetime",
  "isActive": boolean,
  "createdAt": "ISO 8601 datetime"
}
```

## Query Parameters

### Pagination
Most list endpoints support pagination:

- `page`: Page number (default: 1)
- `limit`: Items per page (default: 25, max: 100)

Example:
```http
GET /incidents?page=2&limit=50
```

### Filtering
Many endpoints support filtering parameters:

- `startDate`: Filter by start date (ISO 8601)
- `endDate`: Filter by end date (ISO 8601)
- `status`: Filter by status
- `location`: Filter by geographic area
- `search`: Text search across relevant fields

Example:
```http
GET /incidents?status=active&startDate=2024-01-01&search=wildfire
```

### Sorting
List endpoints support sorting:

- `sort`: Field to sort by
- `order`: Sort order (`asc` or `desc`)

Example:
```http
GET /incidents?sort=startTime&order=desc
```

## Rate Limiting

API requests are rate limited to ensure fair usage:

- **Authenticated requests**: 1000 requests per hour
- **Public endpoints**: 100 requests per hour
- **Burst limit**: 50 requests per minute

Rate limit headers are included in responses:
```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1640995200
```

## Error Codes

### HTTP Status Codes
- `200`: Success
- `201`: Created
- `400`: Bad Request
- `401`: Unauthorized
- `403`: Forbidden
- `404`: Not Found
- `422`: Validation Error
- `429`: Rate Limited
- `500`: Internal Server Error

### Application Error Codes
- `AUTH_INVALID_CREDENTIALS`: Invalid login credentials
- `AUTH_TOKEN_EXPIRED`: Access token has expired
- `AUTH_INSUFFICIENT_PERMISSIONS`: User lacks required permissions
- `VALIDATION_ERROR`: Request validation failed
- `RESOURCE_NOT_FOUND`: Requested resource not found
- `RESOURCE_CONFLICT`: Resource already exists
- `RATE_LIMIT_EXCEEDED`: Too many requests
- `SERVICE_UNAVAILABLE`: Service temporarily unavailable

## SDK and Libraries

### Official SDKs
- **Python**: `pip install wildfire-intelligence-sdk`
- **JavaScript/Node.js**: `npm install wildfire-intelligence-sdk`
- **R**: `install.packages("wildfire.intelligence")`

### Python SDK Example
```python
from wildfire_intelligence import WildfireAPI

# Initialize client
client = WildfireAPI(
    base_url="https://api.wildfire-intelligence.com/api/v1",
    api_key="your_api_key"
)

# Get current fire risk
fire_risk = client.fire_risk.get_current(
    latitude=37.7749,
    longitude=-122.4194
)

print(f"Current fire risk: {fire_risk.risk_level}")
```

### JavaScript SDK Example
```javascript
import { WildfireAPI } from 'wildfire-intelligence-sdk';

const client = new WildfireAPI({
  baseURL: 'https://api.wildfire-intelligence.com/api/v1',
  apiKey: 'your_api_key'
});

// Get active incidents
const incidents = await client.incidents.list({
  status: 'active',
  limit: 10
});

console.log(`Active incidents: ${incidents.data.length}`);
```

## Webhooks

### Webhook Events
The platform supports webhooks for real-time notifications:

- `incident.created`: New fire incident detected
- `incident.updated`: Fire incident status changed
- `alert.created`: New alert generated
- `fire_risk.updated`: Fire risk level changed
- `resource.deployed`: Resource deployed to incident
- `weather.alert`: Weather alert issued

### Webhook Configuration
Configure webhooks in the Admin Console or via API:

```http
POST /admin/webhooks
Content-Type: application/json

{
  "url": "https://your-app.com/webhooks/wildfire",
  "events": ["incident.created", "alert.created"],
  "secret": "your_webhook_secret"
}
```

### Webhook Payload Example
```json
{
  "event": "incident.created",
  "timestamp": "2024-01-15T10:30:00Z",
  "data": {
    "id": "incident_123",
    "name": "Creek Fire",
    "location": {
      "latitude": 37.0902,
      "longitude": -119.1167
    },
    "status": "active",
    "priority": "high"
  }
}
```

## Interactive Documentation

### Swagger/OpenAPI
Interactive API documentation is available at:
- **Development**: http://localhost:8080/docs
- **Production**: https://api.wildfire-intelligence.com/docs

### Postman Collection
Import our Postman collection for easy testing:
- [Download Collection](./wildfire-intelligence-postman-collection.json)

---

## Support
- **API Support**: api-support@wildfire-intelligence.com
- **Documentation Issues**: Report on GitHub Issues
- **Rate Limit Increases**: Contact support with usage details
- **SLA & Support Plans**: Available for enterprise customers