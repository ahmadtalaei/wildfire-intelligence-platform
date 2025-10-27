"""Geographic configuration package for data ingestion service"""

from .geographic_bounds import (
    CALIFORNIA_BOUNDS,
    CALIFORNIA_BOUNDS_BBOX,
    CALIFORNIA_FIRE_REGIONS,
    get_california_bounds,
    get_california_bbox,
    get_fire_regions,
    is_within_california
)

__all__ = [
    'CALIFORNIA_BOUNDS',
    'CALIFORNIA_BOUNDS_BBOX',
    'CALIFORNIA_FIRE_REGIONS',
    'get_california_bounds',
    'get_california_bbox',
    'get_fire_regions',
    'is_within_california'
]
