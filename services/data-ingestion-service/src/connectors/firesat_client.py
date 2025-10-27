"""
FireSat+ NOS Testbed Client
Simulation and evaluation client for FireSat constellation testing

This module integrates with the FireSat+ NOS (NIST Open Systems) Testbed
for satellite constellation simulation and fire detection algorithm evaluation.

Documentation: https://nost-tools.readthedocs.io/en/stable/examples/firesat/

The testbed provides:
- Satellite constellation orbit simulation
- Fire detection algorithm testing
- Performance evaluation metrics
- Data validation tools
"""

import asyncio
import aiohttp
from typing import List, Dict, Any, Optional
import structlog
from datetime import datetime, timedelta

logger = structlog.get_logger()


class FireSatTestbedClient:
    """
    Client for FireSat+ NOS Testbed simulation environment

    Provides access to simulation data for development and testing
    before production FireSat API is fully available.
    """

    def __init__(self, testbed_url: Optional[str] = None):
        """
        Initialize FireSat testbed client

        Args:
            testbed_url: URL to NOS testbed instance (default: local simulation)
        """
        self.testbed_url = testbed_url or "http://localhost:8080/firesat"
        self.session = None

    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    async def get_constellation_status(self) -> Dict[str, Any]:
        """
        Get current FireSat constellation status from testbed

        Returns:
            Constellation configuration and satellite states
        """
        try:
            async with self.session.get(f"{self.testbed_url}/constellation/status") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.warning("Failed to get constellation status",
                                 status=response.status)
                    return {}
        except Exception as e:
            logger.error("Error getting constellation status", error=str(e))
            return {}

    async def simulate_detections(
        self,
        start_time: datetime,
        duration_hours: int,
        bounds: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """
        Run FireSat detection simulation for specified time period

        Args:
            start_time: Simulation start time
            duration_hours: How many hours to simulate
            bounds: Geographic bounds for simulation area

        Returns:
            List of simulated fire detections
        """
        try:
            params = {
                'start_time': start_time.isoformat(),
                'duration_hours': duration_hours,
                'bbox': f"{bounds['lon_min']},{bounds['lat_min']},{bounds['lon_max']},{bounds['lat_max']}"
            }

            async with self.session.post(
                f"{self.testbed_url}/simulate/detections",
                json=params
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('detections', [])
                else:
                    logger.error("Simulation failed", status=response.status)
                    return []

        except Exception as e:
            logger.error("Error running simulation", error=str(e))
            return []

    async def evaluate_coverage(
        self,
        constellation_config: Dict[str, Any],
        target_region: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Evaluate FireSat constellation coverage for target region

        Args:
            constellation_config: Satellite constellation parameters
            target_region: Geographic region to evaluate

        Returns:
            Coverage metrics (revisit time, coverage %, gaps)
        """
        try:
            payload = {
                'constellation': constellation_config,
                'region': target_region
            }

            async with self.session.post(
                f"{self.testbed_url}/evaluate/coverage",
                json=payload
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {}

        except Exception as e:
            logger.error("Error evaluating coverage", error=str(e))
            return {}

    async def validate_detection_algorithm(
        self,
        algorithm_config: Dict[str, Any],
        test_dataset: str
    ) -> Dict[str, Any]:
        """
        Validate fire detection algorithm against test dataset

        Args:
            algorithm_config: Algorithm configuration parameters
            test_dataset: Name of test dataset to use

        Returns:
            Validation metrics (accuracy, precision, recall, F1)
        """
        try:
            payload = {
                'algorithm': algorithm_config,
                'dataset': test_dataset
            }

            async with self.session.post(
                f"{self.testbed_url}/validate/algorithm",
                json=payload
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {}

        except Exception as e:
            logger.error("Error validating algorithm", error=str(e))
            return {}


class FireSatSimulator:
    """
    Local FireSat simulation for offline development

    Generates realistic fire detection data based on FireSat specifications
    without requiring network connectivity or API access.
    """

    def __init__(self, seed: int = 42):
        """
        Initialize simulator

        Args:
            seed: Random seed for reproducible simulations
        """
        import numpy as np
        self.seed = seed
        self.np = np
        self.np.random.seed(seed)

        # FireSat constellation parameters
        self.num_satellites = 50  # Full constellation
        self.orbit_altitude_km = 500
        self.revisit_time_minutes = 20
        self.swath_width_km = 100
        self.spatial_resolution_m = 5.0

    def generate_satellite_passes(
        self,
        start_time: datetime,
        end_time: datetime,
        bounds: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """
        Simulate satellite passes over target region

        Args:
            start_time: Start of simulation period
            end_time: End of simulation period
            bounds: Geographic bounds

        Returns:
            List of satellite pass events
        """
        passes = []
        current_time = start_time

        while current_time < end_time:
            # Simulate pass every ~20 minutes (FireSat revisit time)
            for sat_id in range(1, min(self.num_satellites, 10) + 1):  # First 10 sats
                pass_data = {
                    'satellite_id': f'FIRESAT-{sat_id:02d}',
                    'pass_start_time': current_time.isoformat(),
                    'pass_duration_seconds': self.np.random.uniform(120, 300),
                    'max_elevation_deg': self.np.random.uniform(30, 90),
                    'orbit_number': int((current_time - start_time).total_seconds() / 5400),
                }
                passes.append(pass_data)

            current_time += timedelta(minutes=self.revisit_time_minutes)

        return passes

    def simulate_fire_detections(
        self,
        satellite_passes: List[Dict[str, Any]],
        fire_probability: float = 0.1,
        bounds: Dict[str, float] = None
    ) -> List[Dict[str, Any]]:
        """
        Simulate fire detections during satellite passes

        Args:
            satellite_passes: List of satellite pass events
            fire_probability: Probability of detecting fire per pass
            bounds: Geographic bounds for detections

        Returns:
            List of simulated fire detections
        """
        from .timezone_converter import utcnow_pacific

        if bounds is None:
            # Default to California
            bounds = {
                'lat_min': 32.5,
                'lat_max': 42.0,
                'lon_min': -124.5,
                'lon_max': -114.1
            }

        detections = []

        for pass_event in satellite_passes:
            if self.np.random.random() < fire_probability:
                # Generate 1-5 detections per pass
                num_detections = self.np.random.randint(1, 6)

                for _ in range(num_detections):
                    lat = self.np.random.uniform(bounds['lat_min'], bounds['lat_max'])
                    lon = self.np.random.uniform(bounds['lon_min'], bounds['lon_max'])

                    detection = {
                        'timestamp': pass_event['pass_start_time'],
                        'latitude': lat,
                        'longitude': lon,
                        'brightness_kelvin': self.np.random.uniform(350, 800),
                        'fire_radiative_power': self.np.random.uniform(5, 500),
                        'fire_area_m2': self.np.random.uniform(25, 2500),
                        'confidence': self.np.random.uniform(0.75, 0.99),
                        'satellite_id': pass_event['satellite_id'],
                        'sensor': 'FireSat-TIR',
                        'spatial_resolution_m': self.spatial_resolution_m,
                        'source': 'FireSat-Simulation',
                        'source_id': 'firesat_detections',
                    }

                    detections.append(detection)

        return detections

    def calculate_coverage_metrics(
        self,
        satellite_passes: List[Dict[str, Any]],
        time_window_hours: int = 24
    ) -> Dict[str, Any]:
        """
        Calculate constellation coverage metrics

        Args:
            satellite_passes: List of satellite passes
            time_window_hours: Time window for analysis

        Returns:
            Coverage statistics
        """
        if not satellite_passes:
            return {}

        # Calculate time gaps between passes
        pass_times = [datetime.fromisoformat(p['pass_start_time']) for p in satellite_passes]
        pass_times.sort()

        gaps = [(pass_times[i+1] - pass_times[i]).total_seconds() / 60
                for i in range(len(pass_times) - 1)]

        return {
            'total_passes': len(satellite_passes),
            'avg_revisit_time_min': self.np.mean(gaps) if gaps else 0,
            'max_gap_min': max(gaps) if gaps else 0,
            'min_gap_min': min(gaps) if gaps else 0,
            'coverage_percentage': min(100, len(satellite_passes) * 100 / (time_window_hours * 3)),
            'satellites_active': len(set(p['satellite_id'] for p in satellite_passes))
        }


# Example usage
async def example_testbed_usage():
    """Example of using FireSat testbed client"""
    async with FireSatTestbedClient() as client:
        # Get constellation status
        status = await client.get_constellation_status()
        print("Constellation Status:", status)

        # Run simulation
        california_bounds = {
            'lat_min': 32.5,
            'lat_max': 42.0,
            'lon_min': -124.5,
            'lon_max': -114.1
        }

        detections = await client.simulate_detections(
            start_time=datetime.now(),
            duration_hours=24,
            bounds=california_bounds
        )

        print(f"Simulated {len(detections)} detections")


def example_local_simulation():
    """Example of local simulation without network"""
    simulator = FireSatSimulator(seed=42)

    # Generate satellite passes for 24 hours
    start_time = datetime.now()
    end_time = start_time + timedelta(hours=24)

    california_bounds = {
        'lat_min': 32.5,
        'lat_max': 42.0,
        'lon_min': -124.5,
        'lon_max': -114.1
    }

    passes = simulator.generate_satellite_passes(start_time, end_time, california_bounds)
    print(f"Generated {len(passes)} satellite passes")

    # Simulate fire detections
    detections = simulator.simulate_fire_detections(passes, fire_probability=0.15, bounds=california_bounds)
    print(f"Simulated {len(detections)} fire detections")

    # Calculate coverage
    metrics = simulator.calculate_coverage_metrics(passes, time_window_hours=24)
    print("Coverage Metrics:", metrics)


if __name__ == "__main__":
    print("=== FireSat+ NOS Testbed Client ===")
    print("\nRunning local simulation...")
    example_local_simulation()

    print("\n\nFor testbed integration, run:")
    print("asyncio.run(example_testbed_usage())")
