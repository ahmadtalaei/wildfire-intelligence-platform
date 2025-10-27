"""
Geographic Partitioner for Kafka
Optimizes data locality by partitioning based on geographic grid cells
Ensures fire data from the same region goes to the same partition for better cache locality
"""

import hashlib
from typing import List, Optional, Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)


class GeographicPartitioner:
    """
    Custom Kafka partitioner that uses geographic location to determine partition.
    This ensures data from the same geographic region is processed together,
    improving cache locality and enabling region-based parallel processing.
    """

    def __init__(self, grid_size: float = 1.0, california_optimized: bool = True):
        """
        Initialize geographic partitioner

        Args:
            grid_size: Size of geographic grid cells in degrees (default 1.0)
            california_optimized: Use California-specific grid optimization
        """
        self.grid_size = grid_size
        self.california_optimized = california_optimized

        # California bounds for optimized partitioning
        self.ca_bounds = {
            'lat_min': 32.534156,   # Southern border (Imperial County)
            'lat_max': 42.009518,   # Northern border (Modoc County)
            'lon_min': -124.482003,  # Western border (Del Norte County)
            'lon_max': -114.131211   # Eastern border (Imperial County)
        }

        # High-risk fire zones in California (for priority partitioning)
        self.high_risk_zones = [
            {'name': 'Northern_Sierra', 'lat': 39.5, 'lon': -121.0, 'radius': 1.5},
            {'name': 'Bay_Area_Hills', 'lat': 37.8, 'lon': -122.3, 'radius': 1.0},
            {'name': 'Central_Coast', 'lat': 35.5, 'lon': -120.5, 'radius': 1.5},
            {'name': 'Southern_Mountains', 'lat': 34.2, 'lon': -117.5, 'radius': 1.5},
            {'name': 'San_Diego_Backcountry', 'lat': 33.0, 'lon': -116.5, 'radius': 1.0}
        ]

        # California counties mapping for administrative partitioning
        self.county_grid_map = self._generate_county_grid_map()

    def _generate_county_grid_map(self) -> Dict[str, int]:
        """Generate mapping of county regions to partition hints"""
        # Major California regions for balanced partitioning
        regions = {
            'Northern': 0,      # Del Norte, Siskiyou, Modoc, etc.
            'Sacramento': 1,    # Sacramento Valley
            'BayArea': 2,       # SF Bay Area counties
            'Central': 3,       # Central Valley
            'CentralCoast': 4,  # Monterey, San Luis Obispo
            'Sierra': 5,        # Sierra Nevada counties
            'Southern': 6,      # LA, Orange, San Diego
            'Inland': 7         # San Bernardino, Riverside
        }
        return regions

    def partition(
        self,
        key: Any,
        all_partitions: List[int],
        available_partitions: Optional[List[int]] = None
    ) -> int:
        """
        Determine partition based on geographic location

        Args:
            key: Partition key (can be dict with lat/lon or string)
            all_partitions: All partition IDs
            available_partitions: Currently available partitions

        Returns:
            Selected partition number
        """
        partitions = available_partitions if available_partitions else all_partitions
        num_partitions = len(partitions)

        if num_partitions == 0:
            return 0

        # Extract geographic coordinates
        lat, lon = self._extract_coordinates(key)

        if lat is not None and lon is not None:
            # Use geographic partitioning
            partition_idx = self._geographic_partition(lat, lon, num_partitions)
        else:
            # Fallback to hash-based partitioning
            partition_idx = self._hash_partition(key, num_partitions)

        return partitions[partition_idx]

    def _extract_coordinates(self, key: Any) -> Tuple[Optional[float], Optional[float]]:
        """Extract latitude and longitude from partition key"""
        try:
            if isinstance(key, dict):
                lat = key.get('latitude') or key.get('lat')
                lon = key.get('longitude') or key.get('lon')
                return float(lat) if lat else None, float(lon) if lon else None

            elif isinstance(key, str):
                # Try to parse geo-encoded keys (e.g., "geo_37.5_-122.3")
                if key.startswith('geo_'):
                    parts = key.split('_')
                    if len(parts) >= 3:
                        return float(parts[1]), float(parts[2])

            return None, None

        except (ValueError, TypeError):
            return None, None

    def _geographic_partition(self, lat: float, lon: float, num_partitions: int) -> int:
        """
        Calculate partition based on geographic grid cell

        Uses a geographic grid system to ensure data from the same region
        is consistently routed to the same partition.
        """
        if self.california_optimized and self._is_california(lat, lon):
            # Use California-optimized partitioning
            return self._california_partition(lat, lon, num_partitions)

        # Global geographic grid partitioning
        # Create grid cell ID based on coordinates
        lat_cell = int((lat + 90) / self.grid_size)  # 0-180 for -90 to 90
        lon_cell = int((lon + 180) / self.grid_size)  # 0-360 for -180 to 180

        # Combine cells into a unique grid ID
        # Use prime multiplication to avoid collisions
        grid_id = (lat_cell * 997) + lon_cell

        return grid_id % num_partitions

    def _california_partition(self, lat: float, lon: float, num_partitions: int) -> int:
        """
        California-specific partitioning for optimal fire data distribution

        Assigns partitions based on:
        1. High-risk fire zones (priority)
        2. Geographic regions (counties/areas)
        3. Grid cells within California
        """
        # Check if in high-risk zone
        for i, zone in enumerate(self.high_risk_zones):
            if self._in_zone(lat, lon, zone):
                # Assign high-risk zones to lower partition numbers for priority
                return i % num_partitions

        # Use regional partitioning for California
        region_id = self._get_california_region(lat, lon)

        # Distribute regions across available partitions
        # Start from partition 5 (after high-risk zones)
        base_partition = 5 if num_partitions > 5 else 0
        return (base_partition + region_id) % num_partitions

    def _is_california(self, lat: float, lon: float) -> bool:
        """Check if coordinates are within California bounds"""
        return (self.ca_bounds['lat_min'] <= lat <= self.ca_bounds['lat_max'] and
                self.ca_bounds['lon_min'] <= lon <= self.ca_bounds['lon_max'])

    def _in_zone(self, lat: float, lon: float, zone: Dict[str, Any]) -> bool:
        """Check if coordinates are within a specific zone"""
        dlat = abs(lat - zone['lat'])
        dlon = abs(lon - zone['lon'])
        return dlat <= zone['radius'] and dlon <= zone['radius']

    def _get_california_region(self, lat: float, lon: float) -> int:
        """
        Determine California region based on coordinates

        Returns region ID (0-7) for major California regions
        """
        # Northern California (above 38.5°N)
        if lat > 38.5:
            if lon < -122:
                return 0  # North Coast
            else:
                return 1  # Northern Interior

        # Bay Area (37-38.5°N, west of -121.5°W)
        elif 37 <= lat <= 38.5 and lon < -121.5:
            return 2

        # Central Valley (35-38°N, -121.5 to -119°W)
        elif 35 <= lat <= 38 and -121.5 <= lon <= -119:
            return 3

        # Central Coast (35-37°N, west of -121°W)
        elif 35 <= lat <= 37 and lon < -121:
            return 4

        # Sierra Nevada (east of -120°W, north of 35°N)
        elif lon > -120 and lat > 35:
            return 5

        # Southern California (south of 35°N)
        elif lat < 35:
            if lon < -117:
                return 6  # LA/San Diego Coast
            else:
                return 7  # Inland Empire/Desert

        # Default fallback
        return self._hash_partition(f"{lat}_{lon}", 8)

    def _hash_partition(self, key: Any, num_partitions: int) -> int:
        """Fallback hash-based partitioning"""
        key_str = str(key)
        hash_value = int(hashlib.md5(key_str.encode()).hexdigest(), 16)
        return hash_value % num_partitions

    def get_partition_stats(self, records: List[Dict[str, Any]], num_partitions: int) -> Dict[int, int]:
        """
        Analyze partition distribution for a set of records

        Useful for monitoring partition balance and hot spots
        """
        partition_counts = {i: 0 for i in range(num_partitions)}

        for record in records:
            lat = record.get('latitude') or record.get('lat')
            lon = record.get('longitude') or record.get('lon')

            if lat and lon:
                partition = self._geographic_partition(float(lat), float(lon), num_partitions)
                partition_counts[partition] += 1

        return partition_counts

    def optimize_partitions(self, historical_data: List[Dict[str, Any]], target_partitions: int) -> Dict[str, Any]:
        """
        Analyze historical data to recommend optimal partition configuration

        Returns recommendations for:
        - Optimal number of partitions
        - Grid size adjustments
        - Regional weighting
        """
        stats = self.get_partition_stats(historical_data, target_partitions)

        # Calculate partition imbalance
        avg_records = sum(stats.values()) / len(stats)
        max_imbalance = max(abs(count - avg_records) for count in stats.values())
        imbalance_ratio = max_imbalance / avg_records if avg_records > 0 else 0

        # Identify hot partitions
        hot_partitions = [p for p, count in stats.items() if count > avg_records * 1.5]

        recommendations = {
            'current_partitions': target_partitions,
            'partition_distribution': stats,
            'imbalance_ratio': imbalance_ratio,
            'hot_partitions': hot_partitions,
            'recommendations': []
        }

        # Generate recommendations
        if imbalance_ratio > 0.3:
            recommendations['recommendations'].append(
                f"High imbalance detected ({imbalance_ratio:.2%}). Consider adjusting grid size."
            )

        if len(hot_partitions) > target_partitions * 0.2:
            recommendations['recommendations'].append(
                f"Multiple hot partitions ({len(hot_partitions)}). Increase partition count or refine geographic grid."
            )

        if target_partitions < 12 and len(historical_data) > 10000:
            recommendations['recommendations'].append(
                "High data volume with low partition count. Consider increasing to 12-16 partitions."
            )

        return recommendations


# Integration with Kafka producer
def create_geographic_partitioner() -> GeographicPartitioner:
    """Factory function to create geographic partitioner with defaults"""
    return GeographicPartitioner(grid_size=1.0, california_optimized=True)


# Example usage for testing
if __name__ == "__main__":
    partitioner = create_geographic_partitioner()

    # Test data points
    test_points = [
        {'lat': 37.7749, 'lon': -122.4194, 'name': 'San Francisco'},
        {'lat': 34.0522, 'lon': -118.2437, 'name': 'Los Angeles'},
        {'lat': 38.5816, 'lon': -121.4944, 'name': 'Sacramento'},
        {'lat': 32.7157, 'lon': -117.1611, 'name': 'San Diego'},
        {'lat': 39.5296, 'lon': -119.8138, 'name': 'Reno (outside CA)'}
    ]

    num_partitions = 12
    partitions = list(range(num_partitions))

    print("Geographic Partitioning Test Results:")
    print("=" * 50)

    for point in test_points:
        partition = partitioner.partition(point, partitions)
        in_ca = partitioner._is_california(point['lat'], point['lon'])
        print(f"{point['name']:20} -> Partition {partition:2} (CA: {in_ca})")

    # Test partition distribution
    print("\nPartition Distribution Analysis:")
    print("=" * 50)

    # Generate synthetic data
    import random
    synthetic_data = []
    for _ in range(1000):
        lat = random.uniform(32.5, 42.0)
        lon = random.uniform(-124.5, -114.0)
        synthetic_data.append({'lat': lat, 'lon': lon})

    stats = partitioner.get_partition_stats(synthetic_data, num_partitions)
    for partition, count in sorted(stats.items()):
        bar = '█' * (count // 10)
        print(f"Partition {partition:2}: {count:4} records {bar}")

    # Get optimization recommendations
    recommendations = partitioner.optimize_partitions(synthetic_data, num_partitions)
    print("\nOptimization Recommendations:")
    print("=" * 50)
    print(f"Imbalance Ratio: {recommendations['imbalance_ratio']:.2%}")
    print(f"Hot Partitions: {recommendations['hot_partitions']}")
    for rec in recommendations['recommendations']:
        print(f"• {rec}")