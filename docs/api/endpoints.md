# API Endpoints Reference

Detailed reference for all API endpoints in the Wildfire Intelligence Platform.

## Authentication Endpoints

### POST /auth/login
Authenticate user with username/password.

**Request:**
```json
{
  "username": "string",
  "password": "string"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "access_token": "string",
    "refresh_token": "string",
    "token_type": "Bearer",
    "expires_in": 3600,
    "user": {
      "id": "string",
      "username": "string",
      "email": "string",
      "role": "string",
      "firstName": "string",
      "lastName": "string"
    }
  }
}
```

### POST /auth/refresh
Refresh access token using refresh token.

**Request:**
```json
{
  "refresh_token": "string"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "access_token": "string",
    "expires_in": 3600
  }
}
```

### GET /auth/profile
Get current user profile information.

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "string",
    "username": "string",
    "email": "string",
    "firstName": "string",
    "lastName": "string",
    "role": "string",
    "department": "string",
    "permissions": ["string"],
    "lastLogin": "datetime",
    "createdAt": "datetime"
  }
}
```

## Dashboard Endpoints

### GET /dashboard/metrics
Get key dashboard metrics.

**Query Parameters:**
- `timeRange`: Time range for metrics (`1h`, `24h`, `7d`, `30d`)

**Response:**
```json
{
  "success": true,
  "data": {
    "activeIncidents": 5,
    "highRiskAreas": 12,
    "resourcesDeployed": 45,
    "weatherAlerts": 3,
    "timestamp": "datetime"
  }
}
```

### GET /dashboard/fire-risk
Get current fire risk assessment.

**Query Parameters:**
- `latitude`: Latitude for location-specific risk
- `longitude`: Longitude for location-specific risk
- `radius`: Radius in kilometers (default: 50)

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "location": {
        "latitude": 37.7749,
        "longitude": -122.4194,
        "name": "San Francisco"
      },
      "riskLevel": "moderate",
      "riskScore": 65,
      "factors": {
        "temperature": 75,
        "humidity": 45,
        "windSpeed": 12,
        "vegetationMoisture": 30,
        "droughtIndex": 2.5
      },
      "timestamp": "datetime"
    }
  ]
}
```

### GET /dashboard/incidents
Get current active incidents.

**Query Parameters:**
- `status`: Filter by status (`active`, `contained`, `controlled`, `extinguished`)
- `priority`: Filter by priority (`low`, `medium`, `high`, `critical`)
- `limit`: Number of incidents to return (default: 10)

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": "inc_123",
      "name": "Creek Fire",
      "status": "active",
      "priority": "high",
      "location": {
        "latitude": 37.0902,
        "longitude": -119.1167,
        "address": "Fresno County, CA"
      },
      "startTime": "datetime",
      "acresBurned": 1500,
      "threatLevel": 8,
      "resourcesAssigned": 12
    }
  ]
}
```

## Fire Risk Endpoints

### GET /fire-risk/current
Get current fire risk levels for specified areas.

**Query Parameters:**
- `bbox`: Bounding box (format: `minLon,minLat,maxLon,maxLat`)
- `resolution`: Grid resolution in kilometers (default: 1)

**Response:**
```json
{
  "success": true,
  "data": {
    "gridData": [
      {
        "latitude": 37.7749,
        "longitude": -122.4194,
        "riskLevel": "moderate",
        "riskScore": 65
      }
    ],
    "timestamp": "datetime",
    "validUntil": "datetime"
  }
}
```

### POST /fire-risk/predict
Predict fire risk for specific location and conditions.

**Request:**
```json
{
  "location": {
    "latitude": 37.7749,
    "longitude": -122.4194
  },
  "weather": {
    "temperature": 85,
    "humidity": 25,
    "windSpeed": 20,
    "windDirection": 225
  },
  "vegetation": {
    "moistureContent": 15,
    "fuelLoad": "heavy"
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "prediction": {
      "riskLevel": "high",
      "riskScore": 78,
      "ignitionProbability": 0.15,
      "spreadRate": "moderate",
      "intensity": "high"
    },
    "confidence": 0.89,
    "modelVersion": "v2.1.0"
  }
}
```

## Incident Management Endpoints

### GET /incidents
List all incidents with filtering options.

**Query Parameters:**
- `page`: Page number (default: 1)
- `limit`: Items per page (default: 25)
- `status`: Filter by status
- `startDate`: Filter by start date (ISO 8601)
- `endDate`: Filter by end date (ISO 8601)
- `county`: Filter by county
- `search`: Text search

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": "inc_123",
      "name": "Creek Fire",
      "status": "active",
      "priority": "high",
      "location": {
        "latitude": 37.0902,
        "longitude": -119.1167,
        "address": "Fresno County, CA",
        "county": "Fresno"
      },
      "startTime": "datetime",
      "containmentTime": null,
      "acresBurned": 1500,
      "threatLevel": 8,
      "resourcesAssigned": 12,
      "description": "Wildfire in mountainous terrain",
      "weatherConditions": {
        "temperature": 92,
        "humidity": 18,
        "windSpeed": 25,
        "windDirection": 270
      }
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 25,
    "total": 150,
    "totalPages": 6
  }
}
```

### POST /incidents
Create a new incident.

**Request:**
```json
{
  "name": "New Fire",
  "location": {
    "latitude": 37.0902,
    "longitude": -119.1167,
    "address": "County Road 123, CA"
  },
  "priority": "medium",
  "description": "Reported wildfire near residential area",
  "reportedBy": "Public Report"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "inc_456",
    "name": "New Fire",
    "status": "active",
    "priority": "medium",
    "location": {
      "latitude": 37.0902,
      "longitude": -119.1167,
      "address": "County Road 123, CA"
    },
    "startTime": "datetime",
    "createdBy": "user_123"
  }
}
```

### GET /incidents/{id}
Get detailed information about a specific incident.

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "inc_123",
    "name": "Creek Fire",
    "status": "active",
    "priority": "high",
    "location": {
      "latitude": 37.0902,
      "longitude": -119.1167,
      "address": "Fresno County, CA",
      "county": "Fresno"
    },
    "startTime": "datetime",
    "acresBurned": 1500,
    "threatLevel": 8,
    "resources": [
      {
        "id": "res_789",
        "type": "fire-engine",
        "name": "Engine 15",
        "status": "deployed",
        "assignedTime": "datetime"
      }
    ],
    "timeline": [
      {
        "timestamp": "datetime",
        "event": "Incident Created",
        "description": "Initial fire report received"
      }
    ]
  }
}
```

## Weather Endpoints

### GET /weather/current
Get current weather conditions.

**Query Parameters:**
- `latitude`: Latitude
- `longitude`: Longitude
- `stations`: Comma-separated list of station IDs
- `radius`: Radius in kilometers for area weather

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "stationId": "KMRY",
      "location": {
        "latitude": 36.6069,
        "longitude": -121.8969,
        "name": "Monterey Airport"
      },
      "temperature": 68,
      "humidity": 75,
      "windSpeed": 8,
      "windDirection": 270,
      "pressure": 30.15,
      "visibility": 10,
      "conditions": "Partly Cloudy",
      "timestamp": "datetime"
    }
  ]
}
```

### GET /weather/forecast
Get weather forecast data.

**Query Parameters:**
- `latitude`: Latitude
- `longitude`: Longitude
- `hours`: Forecast hours (default: 48, max: 168)
- `includeAlerts`: Include weather alerts (default: true)

**Response:**
```json
{
  "success": true,
  "data": {
    "location": {
      "latitude": 37.7749,
      "longitude": -122.4194
    },
    "forecast": [
      {
        "timestamp": "datetime",
        "temperature": 72,
        "humidity": 65,
        "windSpeed": 12,
        "windDirection": 225,
        "precipitation": 0,
        "conditions": "Sunny"
      }
    ],
    "alerts": [
      {
        "id": "alert_123",
        "type": "Red Flag Warning",
        "severity": "warning",
        "startTime": "datetime",
        "endTime": "datetime",
        "description": "Critical fire weather conditions expected"
      }
    ]
  }
}
```

## Resource Management Endpoints

### GET /resources
List all resources.

**Query Parameters:**
- `type`: Filter by resource type
- `status`: Filter by status
- `assignedIncident`: Filter by assigned incident
- `location`: Filter by location (latitude,longitude,radius)

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": "res_123",
      "type": "fire-engine",
      "name": "Engine 15",
      "status": "available",
      "location": {
        "latitude": 37.4419,
        "longitude": -122.1430
      },
      "capacity": 1000,
      "currentLoad": 0,
      "lastUpdate": "datetime",
      "crew": [
        {
          "name": "John Smith",
          "role": "Captain",
          "certification": "Fire Officer I"
        }
      ]
    }
  ]
}
```

### POST /resources/{id}/deploy
Deploy resource to an incident.

**Request:**
```json
{
  "incidentId": "inc_123",
  "priority": "high",
  "estimatedArrival": "datetime",
  "instructions": "Proceed to staging area Alpha"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "deploymentId": "dep_456",
    "resourceId": "res_123",
    "incidentId": "inc_123",
    "status": "en_route",
    "deployedAt": "datetime",
    "estimatedArrival": "datetime"
  }
}
```

## Analytics Endpoints

### POST /analytics/query
Execute custom analytics query.

**Request:**
```json
{
  "query": "SELECT COUNT(*) as incident_count FROM incidents WHERE status = 'active' AND start_time >= '2024-01-01'",
  "format": "json",
  "limit": 1000
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "columns": ["incident_count"],
    "rows": [[42]],
    "executionTime": 0.15,
    "rowCount": 1
  }
}
```

### GET /analytics/incidents
Get incident analytics.

**Query Parameters:**
- `startDate`: Start date for analysis
- `endDate`: End date for analysis
- `groupBy`: Group by field (`county`, `month`, `cause`)
- `metrics`: Metrics to calculate (`count`, `avg_size`, `total_cost`)

**Response:**
```json
{
  "success": true,
  "data": {
    "summary": {
      "totalIncidents": 245,
      "averageSize": 156.7,
      "totalCost": 15400000
    },
    "groups": [
      {
        "key": "Fresno",
        "incidentCount": 45,
        "averageSize": 234.2,
        "totalCost": 3200000
      }
    ]
  }
}
```

## Machine Learning Endpoints

### GET /ml/models
List available ML models.

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": "model_fire_risk_v2",
      "name": "Fire Risk Prediction Model v2.0",
      "type": "classification",
      "status": "production",
      "accuracy": 0.94,
      "lastTrained": "datetime",
      "features": [
        "temperature",
        "humidity",
        "wind_speed",
        "vegetation_index"
      ]
    }
  ]
}
```

### POST /ml/models/{id}/predict
Make prediction using specified model.

**Request:**
```json
{
  "features": {
    "temperature": 85,
    "humidity": 25,
    "wind_speed": 20,
    "vegetation_index": 0.3,
    "elevation": 1200
  },
  "location": {
    "latitude": 37.7749,
    "longitude": -122.4194
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "prediction": {
      "class": "high_risk",
      "probability": 0.78,
      "riskScore": 85
    },
    "confidence": 0.92,
    "modelVersion": "v2.0",
    "features_used": [
      "temperature",
      "humidity", 
      "wind_speed",
      "vegetation_index"
    ]
  }
}
```

## System Administration Endpoints

### GET /admin/system/health
Get system health status.

**Response:**
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "services": [
      {
        "name": "fire-risk-service",
        "status": "healthy",
        "uptime": "5d 12h 34m",
        "version": "1.0.0",
        "replicas": {
          "desired": 3,
          "available": 3
        }
      }
    ],
    "metrics": {
      "cpu": 45.2,
      "memory": 67.8,
      "disk": 23.1
    },
    "timestamp": "datetime"
  }
}
```

### GET /admin/users
List all users.

**Query Parameters:**
- `role`: Filter by user role
- `active`: Filter by active status
- `department`: Filter by department

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": "user_123",
      "username": "john.smith",
      "email": "john.smith@calfire.ca.gov",
      "firstName": "John",
      "lastName": "Smith",
      "role": "fire-chief",
      "department": "CAL FIRE",
      "isActive": true,
      "lastLogin": "datetime",
      "createdAt": "datetime"
    }
  ]
}
```

## Error Responses

All endpoints may return error responses in this format:

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request parameters",
    "details": {
      "field": "latitude",
      "reason": "must be between -90 and 90"
    }
  },
  "timestamp": "datetime"
}
```

### Common Error Codes
- `AUTH_TOKEN_INVALID`: Invalid or expired authentication token
- `AUTH_INSUFFICIENT_PERMISSIONS`: User lacks required permissions
- `VALIDATION_ERROR`: Request validation failed
- `RESOURCE_NOT_FOUND`: Requested resource does not exist
- `RATE_LIMIT_EXCEEDED`: Too many requests
- `SERVICE_UNAVAILABLE`: Service temporarily unavailable

---

For more detailed examples and interactive testing, visit the [API Documentation Portal](./)