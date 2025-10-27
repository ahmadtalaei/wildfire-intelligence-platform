"""
OpenStreetMap Infrastructure Data Connector
Fetches critical infrastructure for fire evacuation and resource planning
"""

import asyncio
import httpx
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import structlog

logger = structlog.get_logger()


class InfrastructureConnector:
    """
    Connector for OpenStreetMap Overpass API

    Fetches infrastructure data:
    - Roads and highways (evacuation routes)
    - Buildings and residential areas
    - Emergency services (fire stations, hospitals)
    - Power infrastructure
    - Water sources
    """

    def __init__(self, kafka_producer=None):
        self.kafka_producer = kafka_producer
        self.topic = "infrastructure.osm"

        # Overpass API endpoint
        self.api_url = "https://overpass-api.de/api/interpreter"
        self.client = httpx.AsyncClient(timeout=60.0)

    async def fetch_infrastructure(
        self,
        latitude: float,
        longitude: float,
        radius_km: float = 10.0
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch infrastructure data within radius of a point

        Args:
            latitude: Center latitude
            longitude: Center longitude
            radius_km: Search radius in kilometers

        Returns:
            Infrastructure data dictionary
        """
        try:
            radius_m = radius_km * 1000

            # Overpass QL query for critical infrastructure
            query = f"""
            [out:json][timeout:30];
            (
              // Emergency services
              node["amenity"="fire_station"](around:{radius_m},{latitude},{longitude});
              node["amenity"="hospital"](around:{radius_m},{latitude},{longitude});
              node["emergency"="water_tank"](around:{radius_m},{latitude},{longitude});

              // Major roads (evacuation routes)
              way["highway"~"motorway|trunk|primary"](around:{radius_m},{latitude},{longitude});

              // Residential areas
              way["landuse"="residential"](around:{radius_m},{latitude},{longitude});
              node["place"~"village|town|city"](around:{radius_m},{latitude},{longitude});

              // Power infrastructure
              way["power"="line"](around:{radius_m},{latitude},{longitude});
              node["power"="tower"](around:{radius_m},{latitude},{longitude});
            );
            out center;
            """

            response = await self.client.post(
                self.api_url,
                data={"data": query}
            )

            if response.status_code != 200:
                logger.warning("Overpass API error",
                             status=response.status_code,
                             lat=latitude,
                             lon=longitude)
                return None

            data = response.json()
            elements = data.get("elements", [])

            # Categorize infrastructure
            fire_stations = []
            hospitals = []
            water_sources = []
            evacuation_routes = []
            residential_areas = []
            power_infrastructure = []

            for element in elements:
                tags = element.get("tags", {})
                elem_type = element.get("type")

                # Determine location
                if elem_type == "node":
                    elem_lat = element.get("lat")
                    elem_lon = element.get("lon")
                elif elem_type == "way":
                    center = element.get("center", {})
                    elem_lat = center.get("lat")
                    elem_lon = center.get("lon")
                else:
                    continue

                if not elem_lat or not elem_lon:
                    continue

                # Categorize by tags
                if tags.get("amenity") == "fire_station":
                    fire_stations.append({
                        "name": tags.get("name", "Unknown"),
                        "latitude": elem_lat,
                        "longitude": elem_lon
                    })
                elif tags.get("amenity") == "hospital":
                    hospitals.append({
                        "name": tags.get("name", "Unknown"),
                        "latitude": elem_lat,
                        "longitude": elem_lon
                    })
                elif tags.get("emergency") == "water_tank":
                    water_sources.append({
                        "type": "water_tank",
                        "latitude": elem_lat,
                        "longitude": elem_lon
                    })
                elif tags.get("highway") in ["motorway", "trunk", "primary"]:
                    evacuation_routes.append({
                        "name": tags.get("name", "Unnamed road"),
                        "type": tags.get("highway"),
                        "latitude": elem_lat,
                        "longitude": elem_lon
                    })
                elif tags.get("landuse") == "residential" or tags.get("place") in ["village", "town", "city"]:
                    residential_areas.append({
                        "name": tags.get("name", "Unknown"),
                        "type": tags.get("place", "residential"),
                        "latitude": elem_lat,
                        "longitude": elem_lon
                    })
                elif tags.get("power") in ["line", "tower"]:
                    power_infrastructure.append({
                        "type": tags.get("power"),
                        "latitude": elem_lat,
                        "longitude": elem_lon
                    })

            infrastructure_data = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "query_location": {
                    "latitude": latitude,
                    "longitude": longitude,
                    "radius_km": radius_km
                },
                "fire_stations": fire_stations,
                "hospitals": hospitals,
                "water_sources": water_sources,
                "evacuation_routes": evacuation_routes,
                "residential_areas": residential_areas,
                "power_infrastructure": power_infrastructure,
                "summary": {
                    "fire_stations_count": len(fire_stations),
                    "hospitals_count": len(hospitals),
                    "water_sources_count": len(water_sources),
                    "evacuation_routes_count": len(evacuation_routes),
                    "residential_areas_count": len(residential_areas),
                    "power_infrastructure_count": len(power_infrastructure)
                },
                "data_source": "openstreetmap_overpass"
            }

            logger.info("Infrastructure data fetched",
                       lat=latitude,
                       lon=longitude,
                       fire_stations=len(fire_stations),
                       hospitals=len(hospitals),
                       residential=len(residential_areas))

            # Publish to Kafka if configured
            if self.kafka_producer:
                await self._publish_to_kafka(infrastructure_data)

            return infrastructure_data

        except Exception as e:
            logger.error("Failed to fetch infrastructure data", error=str(e))
            return None

    async def _publish_to_kafka(self, infrastructure_data: Dict[str, Any]):
        """Publish infrastructure data to Kafka topic"""
        try:
            if self.kafka_producer:
                await self.kafka_producer.send(
                    self.topic,
                    value=infrastructure_data
                )
                logger.debug("Infrastructure data published to Kafka", topic=self.topic)
        except Exception as e:
            logger.error("Failed to publish infrastructure data to Kafka", error=str(e))

    async def close(self):
        """Close HTTP client connection"""
        await self.client.aclose()
