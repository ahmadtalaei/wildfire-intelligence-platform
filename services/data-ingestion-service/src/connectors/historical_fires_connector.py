"""
CAL FIRE Historical Fire Perimeters Connector
Fetches historical wildfire data for pattern analysis and risk modeling
"""

import asyncio
import httpx
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
import structlog
import json

logger = structlog.get_logger()


class HistoricalFiresConnector:
    """
    Connector for CAL FIRE Historical Fire Perimeters

    Provides:
    - Historical fire perimeter data
    - Fire frequency analysis
    - Seasonal fire patterns
    - Historical burn severity
    """

    def __init__(self, kafka_producer=None):
        self.kafka_producer = kafka_producer
        self.topic = "fires.historical"

        # CAL FIRE ArcGIS REST API
        self.api_url = "https://services1.arcgis.com/jUJYIo9tSA7EHvfZ/arcgis/rest/services/California_Fire_Perimeters_all/FeatureServer/0/query"
        self.client = httpx.AsyncClient(timeout=60.0)

    async def fetch_historical_fires(
        self,
        latitude: float,
        longitude: float,
        radius_km: float = 50.0,
        years_back: int = 10
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch historical fire perimeters near a location

        Args:
            latitude: Center latitude
            longitude: Center longitude
            radius_km: Search radius in kilometers
            years_back: Number of years to look back

        Returns:
            Historical fire data dictionary
        """
        try:
            # Calculate bounding box
            # Approximate: 1 degree latitude = 111 km
            lat_delta = radius_km / 111.0
            lon_delta = radius_km / (111.0 * np.cos(np.radians(latitude)))

            min_lat = latitude - lat_delta
            max_lat = latitude + lat_delta
            min_lon = longitude - lon_delta
            max_lon = longitude + lon_delta

            # Calculate date range
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=years_back * 365)

            # ArcGIS query parameters
            params = {
                "where": f"YEAR_ >= {start_date.year}",
                "geometry": f"{min_lon},{min_lat},{max_lon},{max_lat}",
                "geometryType": "esriGeometryEnvelope",
                "spatialRel": "esriSpatialRelIntersects",
                "outFields": "YEAR_,FIRE_NAME,GIS_ACRES,CAUSE,ALARM_DATE,CONT_DATE,C_METHOD",
                "returnGeometry": "false",
                "f": "json"
            }

            response = await self.client.get(self.api_url, params=params)

            if response.status_code != 200:
                logger.warning("CAL FIRE API error",
                             status=response.status_code,
                             lat=latitude,
                             lon=longitude)
                return None

            data = response.json()
            features = data.get("features", [])

            # Process historical fires
            fires = []
            total_acres_burned = 0.0
            fire_causes = {}

            for feature in features:
                attrs = feature.get("attributes", {})

                year = attrs.get("YEAR_")
                fire_name = attrs.get("FIRE_NAME", "Unknown")
                acres = attrs.get("GIS_ACRES", 0.0)
                cause = attrs.get("CAUSE", "Unknown")
                alarm_date = attrs.get("ALARM_DATE")
                contained_date = attrs.get("CONT_DATE")

                if year and acres:
                    fires.append({
                        "year": int(year),
                        "name": fire_name,
                        "acres": float(acres),
                        "cause": cause,
                        "alarm_date": alarm_date,
                        "contained_date": contained_date
                    })

                    total_acres_burned += float(acres)

                    # Track causes
                    fire_causes[cause] = fire_causes.get(cause, 0) + 1

            # Calculate statistics
            fire_frequency = len(fires) / years_back if years_back > 0 else 0
            avg_fire_size = total_acres_burned / len(fires) if fires else 0

            # Seasonal analysis
            fires_by_month = [0] * 12
            for fire in fires:
                if fire.get("alarm_date"):
                    try:
                        # Parse alarm date (Unix timestamp in milliseconds)
                        alarm_ts = fire["alarm_date"] / 1000
                        alarm_dt = datetime.fromtimestamp(alarm_ts, tz=timezone.utc)
                        fires_by_month[alarm_dt.month - 1] += 1
                    except:
                        pass

            historical_data = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "query_location": {
                    "latitude": latitude,
                    "longitude": longitude,
                    "radius_km": radius_km
                },
                "time_range": {
                    "years_back": years_back,
                    "start_year": start_date.year,
                    "end_year": end_date.year
                },
                "fires": fires,
                "statistics": {
                    "total_fires": len(fires),
                    "total_acres_burned": total_acres_burned,
                    "fire_frequency_per_year": fire_frequency,
                    "average_fire_size_acres": avg_fire_size,
                    "fires_by_cause": fire_causes,
                    "fires_by_month": fires_by_month
                },
                "data_source": "cal_fire_perimeters"
            }

            logger.info("Historical fire data fetched",
                       lat=latitude,
                       lon=longitude,
                       total_fires=len(fires),
                       years=years_back)

            # Publish to Kafka if configured
            if self.kafka_producer:
                await self._publish_to_kafka(historical_data)

            return historical_data

        except Exception as e:
            logger.error("Failed to fetch historical fire data", error=str(e))
            return None

    async def get_fire_frequency_grid(
        self,
        bounds: Dict[str, float],
        grid_resolution_km: float = 10.0,
        years_back: int = 10
    ) -> Optional[Dict[str, Any]]:
        """
        Calculate fire frequency for a grid of points

        Args:
            bounds: Dictionary with min_lat, max_lat, min_lon, max_lon
            grid_resolution_km: Grid cell size in kilometers
            years_back: Number of years to analyze

        Returns:
            Fire frequency grid data
        """
        # This would create a heatmap of fire frequency
        # Implementation would sample grid points and fetch historical data
        pass

    async def _publish_to_kafka(self, historical_data: Dict[str, Any]):
        """Publish historical fire data to Kafka topic"""
        try:
            if self.kafka_producer:
                await self.kafka_producer.send(
                    self.topic,
                    value=historical_data
                )
                logger.debug("Historical fire data published to Kafka", topic=self.topic)
        except Exception as e:
            logger.error("Failed to publish historical fire data to Kafka", error=str(e))

    async def close(self):
        """Close HTTP client connection"""
        await self.client.aclose()


# Import numpy for calculations
import numpy as np
