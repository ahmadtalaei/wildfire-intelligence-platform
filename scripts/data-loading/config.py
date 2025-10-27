#!/usr/bin/env python3
"""
Production Configuration for Wildfire Intelligence Platform
Centralized configuration management for all data collectors
"""

import os

# ==============================================================================
# PRODUCTION USER-AGENT (Unified across all collectors)
# ==============================================================================
USER_AGENT = "WildfireIntelligence/1.0 (ahmad.talei@gmail.com)"

# ==============================================================================
# PLATFORM ENDPOINTS (Production URLs)
# ==============================================================================
PLATFORM_BASE_URL = os.getenv("PLATFORM_BASE_URL", "http://localhost:8001")
PLATFORM_API_VERSION = "v1"

# Platform API Endpoints
PLATFORM_API_FIRES = f"{PLATFORM_BASE_URL}/api/{PLATFORM_API_VERSION}/fires"
PLATFORM_API_WEATHER = f"{PLATFORM_BASE_URL}/api/{PLATFORM_API_VERSION}/weather"
PLATFORM_API_SENSORS = f"{PLATFORM_BASE_URL}/api/{PLATFORM_API_VERSION}/sensors"
PLATFORM_API_STATS = f"{PLATFORM_BASE_URL}/api/{PLATFORM_API_VERSION}/stats"
PLATFORM_API_HEALTH = f"{PLATFORM_BASE_URL}/health"

# ==============================================================================
# EXTERNAL API CREDENTIALS (Production)
# ==============================================================================

# NASA FIRMS API
NASA_FIRMS_MAP_KEY = os.getenv("NASA_FIRMS_MAP_KEY", "75ced0840b668216396df605281f8ab5")

# NOAA API Configuration
NOAA_TOKEN = os.getenv("NOAA_TOKEN")  # Optional: Set if you have NOAA token
NOAA_BASE_URL = "https://api.weather.gov"

# CAL FIRE API (if available)
CALFIRE_API_KEY = os.getenv("CALFIRE_API_KEY")
CALFIRE_BASE_URL = "https://www.fire.ca.gov/incidents"

# ==============================================================================
# IOT SENSOR NETWORKS (Production Configurations)
# ==============================================================================

# Real IoT sensor networks (replace demo endpoints with production)
IOT_SENSOR_NETWORKS = [
    {
        "network_id": "california_fire_sensors",
        "name": "California Fire Monitoring Network",
        "protocol": "http",
        # TODO: Replace with real API endpoint when available
        "endpoint": "https://api.calfire.ca.gov/v1/sensors",
        "auth_type": "api_key", 
        "auth_key": os.getenv("CALFIRE_SENSOR_API_KEY"),
        "region": "California",
        "sensor_types": ["smoke", "temperature", "humidity", "air_quality"],
        "enabled": bool(os.getenv("CALFIRE_SENSOR_API_KEY"))
    },
    {
        "network_id": "alertwildfire_cameras",
        "name": "ALERTWildfire Camera Network",
        "protocol": "http",
        "endpoint": "https://api.alertwildfire.org/v1/cameras",
        "auth_type": "api_key",
        "auth_key": os.getenv("ALERTWILDFIRE_API_KEY"),
        "region": "California", 
        "sensor_types": ["visual", "thermal", "smoke_detection"],
        "enabled": bool(os.getenv("ALERTWILDFIRE_API_KEY"))
    },
    {
        "network_id": "usfs_weather_stations",
        "name": "US Forest Service Weather Stations",
        "protocol": "http",
        "endpoint": "https://fam.nwcg.gov/fam-web/weatherfirecd/state",
        "auth_type": "none",
        "region": "California",
        "sensor_types": ["temperature", "humidity", "wind_speed", "wind_direction", "pressure"],
        "enabled": True  # Public API
    },
    {
        "network_id": "raws_weather_network",
        "name": "Remote Automated Weather Station (RAWS)",
        "protocol": "http",
        "endpoint": "https://raws.dri.edu/cgi-bin/rawMAIN.pl",
        "auth_type": "none",
        "region": "California",
        "sensor_types": ["temperature", "humidity", "wind_speed", "wind_direction", "fuel_moisture"],
        "enabled": True  # Public data
    }
]

# ==============================================================================
# COLLECTION INTERVALS (Production Settings)
# ==============================================================================
NASA_FIRMS_POLL_INTERVAL = 300  # 5 minutes (NASA updates every ~3 hours)
NOAA_WEATHER_POLL_INTERVAL = 600  # 10 minutes
IOT_SENSORS_POLL_INTERVAL = 120   # 2 minutes
CALFIRE_INCIDENTS_POLL_INTERVAL = 600  # 10 minutes

# ==============================================================================
# RETRY AND TIMEOUT CONFIGURATION
# ==============================================================================
MAX_RETRIES = 3
REQUEST_TIMEOUT = 30  # seconds
BACKOFF_FACTOR = 2    # exponential backoff multiplier

# ==============================================================================
# DATA QUALITY THRESHOLDS
# ==============================================================================
FIRE_CONFIDENCE_THRESHOLD = 75.0  # Minimum confidence for fire incidents
WEATHER_DATA_MAX_AGE_HOURS = 6     # Maximum age for weather data
SENSOR_OFFLINE_THRESHOLD_MINUTES = 30  # Consider sensor offline after this time

# ==============================================================================
# LOGGING CONFIGURATION
# ==============================================================================
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# ==============================================================================
# GEOGRAPHIC BOUNDARIES (California focus)
# ==============================================================================
CALIFORNIA_BOUNDS = {
    "min_lat": 32.5,   # Southern border
    "max_lat": 42.0,   # Northern border  
    "min_lon": -124.5, # Western border
    "max_lon": -114.0  # Eastern border
}

# Fire-prone regions for enhanced monitoring
FIRE_RISK_REGIONS = [
    {"name": "Bay Area", "lat": 37.7749, "lon": -122.4194, "radius_km": 100},
    {"name": "Los Angeles", "lat": 34.0522, "lon": -118.2437, "radius_km": 150},
    {"name": "Sacramento Valley", "lat": 38.5816, "lon": -121.4944, "radius_km": 80},
    {"name": "San Diego", "lat": 32.7157, "lon": -117.1611, "radius_km": 100},
    {"name": "Central Valley", "lat": 36.7378, "lon": -119.7871, "radius_km": 200},
]

# ==============================================================================
# FEATURE FLAGS
# ==============================================================================
ENABLE_REAL_TIME_COLLECTION = True
ENABLE_DATA_VALIDATION = True
ENABLE_ALERTS = True
ENABLE_PERFORMANCE_MONITORING = True
SIMULATE_WHEN_API_UNAVAILABLE = True  # Fallback to simulation if real APIs fail