"""
Centralized Geographic Bounds Configuration
Defines geographic boundaries for data collection regions
"""

# California State Boundaries
# Source: U.S. Geological Survey (USGS)
CALIFORNIA_BOUNDS = {
    'lat_min': 32.534156,   # Southern border (Imperial County)
    'lat_max': 42.009518,   # Northern border (Modoc County)
    'lon_min': -124.482003, # Western border (Del Norte County)
    'lon_max': -114.131211  # Eastern border (Imperial County)
}

# Alternative format for APIs requiring different parameter names
CALIFORNIA_BOUNDS_BBOX = {
    'nwlng': -124.482003,  # Northwest longitude
    'nwlat': 42.009518,    # Northwest latitude
    'selng': -114.131211,  # Southeast longitude
    'selat': 32.534156     # Southeast latitude
}

# High-risk wildfire regions in California (for targeted monitoring)
# These are major population centers and historically fire-prone areas
CALIFORNIA_FIRE_REGIONS = [
    # Northern California
    {
        'name': 'North State',
        'lat_min': 39.0, 'lat_max': 42.0,
        'lon_min': -124.0, 'lon_max': -120.0,
        'priority': 'high'
    },
    # Bay Area
    {
        'name': 'Bay Area',
        'lat_min': 36.8, 'lat_max': 38.5,
        'lon_min': -123.0, 'lon_max': -121.0,
        'priority': 'high'
    },
    # Central Valley
    {
        'name': 'Central Valley',
        'lat_min': 35.5, 'lat_max': 40.0,
        'lon_min': -122.5, 'lon_max': -118.5,
        'priority': 'medium'
    },
    # Southern California
    {
        'name': 'Southern California',
        'lat_min': 32.5, 'lat_max': 35.5,
        'lon_min': -120.0, 'lon_max': -114.1,
        'priority': 'high'
    }
]


def get_california_bounds():
    """Get California geographic bounds"""
    return CALIFORNIA_BOUNDS.copy()


def get_california_bbox():
    """Get California bounding box in bbox format"""
    return CALIFORNIA_BOUNDS_BBOX.copy()


def get_fire_regions():
    """Get high-priority fire monitoring regions"""
    return CALIFORNIA_FIRE_REGIONS.copy()


def is_within_california(latitude: float, longitude: float) -> bool:
    """
    Check if coordinates are within California bounds

    Args:
        latitude: Latitude coordinate
        longitude: Longitude coordinate

    Returns:
        True if within California, False otherwise
    """
    return (
        CALIFORNIA_BOUNDS['lat_min'] <= latitude <= CALIFORNIA_BOUNDS['lat_max'] and
        CALIFORNIA_BOUNDS['lon_min'] <= longitude <= CALIFORNIA_BOUNDS['lon_max']
    )