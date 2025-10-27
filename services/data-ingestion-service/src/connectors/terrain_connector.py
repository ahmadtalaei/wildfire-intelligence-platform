"""
USGS Digital Elevation Model (DEM) Terrain Data Connector
Fetches elevation, slope, and aspect data for fire risk modeling
"""

import asyncio
import httpx
import numpy as np
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import structlog

logger = structlog.get_logger()


class TerrainConnector:
    """
    Connector for USGS National Elevation Dataset (NED) and 3DEP

    Provides:
    - Elevation data (meters above sea level)
    - Slope calculation (degrees)
    - Aspect calculation (compass direction)
    - Topographic Position Index (TPI)
    """

    def __init__(self, kafka_producer=None):
        self.kafka_producer = kafka_producer
        self.topic = "terrain.elevation"

        # USGS Elevation API endpoint
        self.api_url = "https://epqs.nationalmap.gov/v1/json"
        self.client = httpx.AsyncClient(timeout=30.0)

        # Terrain parameters
        self.sample_resolution_m = 30  # 30m resolution (1 arc-second)

    async def fetch_elevation_point(
        self,
        latitude: float,
        longitude: float
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch elevation for a single point

        Args:
            latitude: Point latitude
            longitude: Point longitude

        Returns:
            Elevation data dictionary
        """
        try:
            response = await self.client.get(
                self.api_url,
                params={
                    "x": longitude,
                    "y": latitude,
                    "units": "Meters",
                    "output": "json"
                }
            )

            if response.status_code != 200:
                logger.warning("USGS elevation API error",
                             status=response.status_code,
                             lat=latitude,
                             lon=longitude)
                return None

            data = response.json()
            elevation_m = data.get("value")

            if elevation_m is None or elevation_m == -1000000:
                # No data available for this location
                return None

            terrain_data = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "latitude": latitude,
                "longitude": longitude,
                "elevation_m": float(elevation_m),
                "data_source": "usgs_ned",
                "resolution_m": self.sample_resolution_m
            }

            logger.info("Elevation fetched",
                       lat=latitude,
                       lon=longitude,
                       elevation=elevation_m)

            return terrain_data

        except Exception as e:
            logger.error("Failed to fetch elevation", error=str(e))
            return None

    async def fetch_elevation_grid(
        self,
        center_lat: float,
        center_lon: float,
        grid_size_km: float = 5.0
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch elevation grid around a center point for slope/aspect calculation

        Args:
            center_lat: Center latitude
            center_lon: Center longitude
            grid_size_km: Grid size in kilometers (default 5km)

        Returns:
            Grid data with elevation, slope, aspect
        """
        try:
            # Calculate grid points (3x3 grid)
            # Approximate: 1 degree latitude = 111 km
            km_per_degree_lat = 111.0
            km_per_degree_lon = 111.0 * np.cos(np.radians(center_lat))

            lat_step = grid_size_km / km_per_degree_lat
            lon_step = grid_size_km / km_per_degree_lon

            # Create 3x3 grid
            grid_points = []
            elevations = []

            for i in range(-1, 2):
                for j in range(-1, 2):
                    lat = center_lat + (i * lat_step)
                    lon = center_lon + (j * lon_step)
                    grid_points.append((lat, lon))

            # Fetch elevations for all grid points
            tasks = [self.fetch_elevation_point(lat, lon) for lat, lon in grid_points]
            results = await asyncio.gather(*tasks)

            elevations = [r['elevation_m'] if r else 0.0 for r in results]

            # Reshape to 3x3 grid
            elevation_grid = np.array(elevations).reshape(3, 3)

            # Calculate slope (using central difference)
            # Slope = sqrt((dz/dx)^2 + (dz/dy)^2)
            dz_dx = (elevation_grid[1, 2] - elevation_grid[1, 0]) / (2 * grid_size_km * 1000)
            dz_dy = (elevation_grid[2, 1] - elevation_grid[0, 1]) / (2 * grid_size_km * 1000)

            slope_radians = np.arctan(np.sqrt(dz_dx**2 + dz_dy**2))
            slope_degrees = np.degrees(slope_radians)

            # Calculate aspect (compass direction of slope)
            aspect_radians = np.arctan2(-dz_dy, -dz_dx)
            aspect_degrees = np.degrees(aspect_radians)

            # Convert to compass bearing (0-360)
            if aspect_degrees < 0:
                aspect_degrees += 360

            # Calculate Topographic Position Index (TPI)
            # TPI = center elevation - mean of surrounding elevations
            surrounding_elevations = [elevation_grid[i, j]
                                     for i in range(3)
                                     for j in range(3)
                                     if not (i == 1 and j == 1)]
            tpi = elevation_grid[1, 1] - np.mean(surrounding_elevations)

            terrain_data = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "latitude": center_lat,
                "longitude": center_lon,
                "elevation_m": float(elevation_grid[1, 1]),
                "slope_degrees": float(slope_degrees),
                "aspect_degrees": float(aspect_degrees),
                "tpi": float(tpi),
                "data_source": "usgs_ned",
                "grid_size_km": grid_size_km
            }

            logger.info("Terrain grid calculated",
                       lat=center_lat,
                       lon=center_lon,
                       slope=slope_degrees,
                       aspect=aspect_degrees)

            # Publish to Kafka if configured
            if self.kafka_producer:
                await self._publish_to_kafka(terrain_data)

            return terrain_data

        except Exception as e:
            logger.error("Failed to fetch elevation grid", error=str(e))
            return None

    async def _publish_to_kafka(self, terrain_data: Dict[str, Any]):
        """Publish terrain data to Kafka topic"""
        try:
            if self.kafka_producer:
                await self.kafka_producer.send(
                    self.topic,
                    value=terrain_data
                )
                logger.debug("Terrain data published to Kafka", topic=self.topic)
        except Exception as e:
            logger.error("Failed to publish terrain data to Kafka", error=str(e))

    async def close(self):
        """Close HTTP client connection"""
        await self.client.aclose()
