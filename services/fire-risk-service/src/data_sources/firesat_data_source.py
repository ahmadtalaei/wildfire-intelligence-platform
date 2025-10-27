"""
FireSat Data Source Integration
Integrates high-resolution 5m FireSat satellite data into fire risk prediction models
"""

import asyncio
import httpx
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import structlog
import numpy as np
from scipy.spatial import cKDTree

logger = structlog.get_logger()


class FireSatDataSource:
    """
    FireSat data source for fire risk prediction

    Integrates 5m resolution FireSat detections into risk models by:
    - Querying recent FireSat detections near prediction location
    - Analyzing fire radiative power trends
    - Detecting fire spread patterns
    - Providing proximity-based risk escalation
    """

    def __init__(self, data_consumption_api_url: str = "http://localhost:8004"):
        self.api_url = data_consumption_api_url
        self.client = httpx.AsyncClient(timeout=30.0)

        # FireSat parameters
        self.proximity_radius_km = 50.0  # Radius for nearby fire search
        self.high_confidence_threshold = 0.8
        self.high_frp_threshold = 50.0  # MW - significant fire
        self.time_window_hours = 24

    async def get_nearby_firesat_detections(
        self,
        latitude: float,
        longitude: float,
        radius_km: float = None,
        time_window_hours: int = None
    ) -> List[Dict[str, Any]]:
        """
        Get FireSat detections near a specific location

        Args:
            latitude: Location latitude
            longitude: Location longitude
            radius_km: Search radius in kilometers (default: 50km)
            time_window_hours: Time window for recent detections (default: 24h)

        Returns:
            List of FireSat detection dictionaries
        """
        radius_km = radius_km or self.proximity_radius_km
        time_window_hours = time_window_hours or self.time_window_hours

        try:
            # Calculate bounding box for spatial query
            # Approximate: 1 degree latitude ≈ 111 km
            # 1 degree longitude varies by latitude
            lat_delta = radius_km / 111.0
            lon_delta = radius_km / (111.0 * np.cos(np.radians(latitude)))

            bounds = f"{longitude-lon_delta},{latitude-lat_delta},{longitude+lon_delta},{latitude+lat_delta}"

            # Query FireSat detections from data consumption service
            response = await self.client.get(
                f"{self.api_url}/consume/latest/firesat_detections",
                params={
                    "limit": 1000,
                    "spatial_bounds": bounds
                }
            )

            if response.status_code != 200:
                logger.warning("Failed to fetch FireSat data",
                             status_code=response.status_code,
                             response=response.text)
                return []

            data = response.json()
            detections = data.get('data', [])

            # Filter by time window
            cutoff_time = datetime.utcnow() - timedelta(hours=time_window_hours)
            recent_detections = []

            for detection in detections:
                try:
                    detection_time = datetime.fromisoformat(detection['timestamp'].replace('Z', '+00:00'))
                    if detection_time >= cutoff_time:
                        # Calculate actual distance
                        distance_km = self._haversine_distance(
                            latitude, longitude,
                            detection['latitude'], detection['longitude']
                        )

                        if distance_km <= radius_km:
                            detection['distance_km'] = distance_km
                            recent_detections.append(detection)
                except Exception as e:
                    logger.warning("Error processing detection", error=str(e))
                    continue

            logger.info("FireSat detections retrieved",
                       total=len(recent_detections),
                       location=f"{latitude},{longitude}",
                       radius_km=radius_km)

            return recent_detections

        except Exception as e:
            logger.error("Failed to get FireSat detections", error=str(e))
            return []

    async def calculate_firesat_risk_factors(
        self,
        latitude: float,
        longitude: float
    ) -> Dict[str, Any]:
        """
        Calculate risk factors from FireSat detections

        Returns comprehensive risk analysis including:
        - Nearby fire count
        - Average Fire Radiative Power (FRP)
        - High-confidence detection count
        - Fire spread indicators
        - Proximity risk score
        """
        detections = await self.get_nearby_firesat_detections(latitude, longitude)

        if not detections:
            return {
                'nearby_fires_count': 0,
                'high_confidence_count': 0,
                'average_frp': 0.0,
                'max_frp': 0.0,
                'closest_fire_distance_km': None,
                'proximity_risk_score': 0.0,
                'fire_spread_rate': 0.0,
                'fire_intensity_trend': 'none',
                'firesat_confidence': 0.0
            }

        # Basic statistics
        nearby_count = len(detections)
        high_conf_count = sum(1 for d in detections if d.get('confidence', 0) >= self.high_confidence_threshold)

        # FRP analysis
        frp_values = [d.get('fire_radiative_power', 0) for d in detections]
        avg_frp = np.mean(frp_values) if frp_values else 0.0
        max_frp = np.max(frp_values) if frp_values else 0.0

        # Distance analysis
        distances = [d['distance_km'] for d in detections if 'distance_km' in d]
        closest_distance = min(distances) if distances else None

        # Proximity risk score (inverse distance weighting)
        proximity_risk = self._calculate_proximity_risk(detections)

        # Fire spread analysis
        spread_rate = await self._estimate_fire_spread_rate(detections)

        # Intensity trend
        intensity_trend = self._analyze_intensity_trend(detections)

        # Overall FireSat confidence
        avg_confidence = np.mean([d.get('confidence', 0) for d in detections])

        return {
            'nearby_fires_count': nearby_count,
            'high_confidence_count': high_conf_count,
            'average_frp': float(avg_frp),
            'max_frp': float(max_frp),
            'closest_fire_distance_km': float(closest_distance) if closest_distance else None,
            'proximity_risk_score': float(proximity_risk),
            'fire_spread_rate': float(spread_rate),
            'fire_intensity_trend': intensity_trend,
            'firesat_confidence': float(avg_confidence)
        }

    def _calculate_proximity_risk(self, detections: List[Dict[str, Any]]) -> float:
        """
        Calculate proximity-based risk score using inverse distance weighting

        Closer fires with higher FRP contribute more to risk
        """
        if not detections:
            return 0.0

        total_risk = 0.0

        for detection in detections:
            distance_km = detection.get('distance_km', 50.0)
            frp = detection.get('fire_radiative_power', 0)
            confidence = detection.get('confidence', 0.5)

            # Inverse distance weight (closer = higher risk)
            distance_weight = 1.0 / (1.0 + distance_km)

            # FRP weight (higher intensity = higher risk)
            frp_weight = min(frp / 100.0, 1.0)  # Normalize to 0-1

            # Combined risk contribution
            risk_contribution = distance_weight * frp_weight * confidence
            total_risk += risk_contribution

        # Normalize to 0-1 scale
        normalized_risk = min(total_risk / 5.0, 1.0)

        return normalized_risk

    async def _estimate_fire_spread_rate(self, detections: List[Dict[str, Any]]) -> float:
        """
        Estimate fire spread rate by analyzing detection patterns over time

        Returns estimated spread rate in km/hour
        """
        if len(detections) < 2:
            return 0.0

        try:
            # Sort by timestamp
            sorted_detections = sorted(
                detections,
                key=lambda d: datetime.fromisoformat(d['timestamp'].replace('Z', '+00:00'))
            )

            # If we have detections spanning multiple hours, calculate spread
            first_time = datetime.fromisoformat(sorted_detections[0]['timestamp'].replace('Z', '+00:00'))
            last_time = datetime.fromisoformat(sorted_detections[-1]['timestamp'].replace('Z', '+00:00'))

            time_diff_hours = (last_time - first_time).total_seconds() / 3600.0

            if time_diff_hours < 0.5:  # Need at least 30 minutes
                return 0.0

            # Calculate spatial extent
            lats = [d['latitude'] for d in sorted_detections]
            lons = [d['longitude'] for d in sorted_detections]

            # Distance between earliest and latest detection clusters
            first_centroid = (np.mean(lats[:len(lats)//3]), np.mean(lons[:len(lons)//3]))
            last_centroid = (np.mean(lats[-len(lats)//3:]), np.mean(lons[-len(lons)//3:]))

            spread_distance_km = self._haversine_distance(
                first_centroid[0], first_centroid[1],
                last_centroid[0], last_centroid[1]
            )

            spread_rate = spread_distance_km / time_diff_hours

            # Cap at reasonable maximum (wildfires typically spread 0.1 - 10 km/h)
            spread_rate = min(spread_rate, 20.0)

            return spread_rate

        except Exception as e:
            logger.warning("Error estimating fire spread rate", error=str(e))
            return 0.0

    def _analyze_intensity_trend(self, detections: List[Dict[str, Any]]) -> str:
        """
        Analyze fire intensity trend from FRP values over time

        Returns: 'increasing', 'decreasing', 'stable', or 'none'
        """
        if len(detections) < 3:
            return 'none'

        try:
            # Sort by timestamp and extract FRP
            sorted_detections = sorted(
                detections,
                key=lambda d: datetime.fromisoformat(d['timestamp'].replace('Z', '+00:00'))
            )

            frp_values = [d.get('fire_radiative_power', 0) for d in sorted_detections]

            # Split into early and late periods
            mid_point = len(frp_values) // 2
            early_avg = np.mean(frp_values[:mid_point])
            late_avg = np.mean(frp_values[mid_point:])

            # Calculate trend
            change_ratio = (late_avg - early_avg) / (early_avg + 1.0)  # Avoid division by zero

            if change_ratio > 0.2:
                return 'increasing'
            elif change_ratio < -0.2:
                return 'decreasing'
            else:
                return 'stable'

        except Exception as e:
            logger.warning("Error analyzing intensity trend", error=str(e))
            return 'none'

    @staticmethod
    def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate great circle distance between two points in kilometers

        Uses Haversine formula for accurate distance on Earth's surface
        """
        R = 6371.0  # Earth's radius in kilometers

        lat1_rad = np.radians(lat1)
        lat2_rad = np.radians(lat2)
        delta_lat = np.radians(lat2 - lat1)
        delta_lon = np.radians(lon2 - lon1)

        a = np.sin(delta_lat / 2)**2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(delta_lon / 2)**2
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

        distance = R * c
        return distance

    async def close(self):
        """Close HTTP client connection"""
        await self.client.aclose()
