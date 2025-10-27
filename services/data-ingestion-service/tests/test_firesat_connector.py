"""
Tests for FireSat Connector
Comprehensive test suite for FireSat data ingestion
"""

import pytest
import asyncio
from datetime import datetime, date, timedelta
from unittest.mock import Mock, patch, AsyncMock
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from connectors.firesat_connector import FireSatConnector, FireSatSimulator
from connectors.firesat_client import FireSatTestbedClient
from models.ingestion import BatchConfig, StreamingConfig


class TestFireSatConnector:
    """Test FireSat connector functionality"""

    @pytest.fixture
    def connector(self):
        """Create FireSat connector instance"""
        return FireSatConnector()

    @pytest.fixture
    def california_bounds(self):
        """California geographic bounds"""
        return {
            'lat_min': 32.534156,
            'lat_max': 42.009518,
            'lon_min': -124.482003,
            'lon_max': -114.131211
        }

    @pytest.mark.asyncio
    async def test_health_check_mock_mode(self, connector):
        """Test health check in mock mode"""
        assert connector.mock_mode is True
        healthy = await connector.health_check()
        assert healthy is True

    @pytest.mark.asyncio
    async def test_fetch_fire_detections_mock(self, connector, california_bounds):
        """Test fetching fire detections in mock mode"""
        config = BatchConfig(
            source_id="firesat_detections",
            start_date=date.today() - timedelta(days=1),
            end_date=date.today(),
            spatial_bounds=california_bounds,
            format="json"
        )

        detections = await connector.fetch_batch_data(config)

        # Should return mock data
        assert len(detections) > 0
        assert all('latitude' in d for d in detections)
        assert all('longitude' in d for d in detections)
        assert all('confidence' in d for d in detections)
        assert all('fire_radiative_power' in d for d in detections)

        # Verify data is within California bounds
        for detection in detections:
            assert california_bounds['lat_min'] <= detection['latitude'] <= california_bounds['lat_max']
            assert california_bounds['lon_min'] <= detection['longitude'] <= california_bounds['lon_max']

    @pytest.mark.asyncio
    async def test_fetch_fire_perimeters_mock(self, connector, california_bounds):
        """Test fetching fire perimeters in mock mode"""
        config = BatchConfig(
            source_id="firesat_perimeters",
            start_date=date.today() - timedelta(days=1),
            end_date=date.today(),
            spatial_bounds=california_bounds,
            format="geojson"
        )

        perimeters = await connector.fetch_batch_data(config)

        assert len(perimeters) > 0
        assert all('fire_id' in p for p in perimeters)
        assert all('perimeter_geometry' in p for p in perimeters)
        assert all('area_hectares' in p for p in perimeters)

    def test_parse_detection(self, connector):
        """Test detection parsing"""
        raw_detection = {
            'geometry': {
                'type': 'Point',
                'coordinates': [-120.5, 38.5]
            },
            'properties': {
                'detection_time': '2025-03-15T10:30:00Z',
                'brightness_temp': 450,
                'frp': 125.5,
                'confidence_score': 0.92,
                'satellite_id': 'FIRESAT-15',
                'id': 'DET-12345'
            }
        }

        parsed = connector._parse_detection(raw_detection)

        assert parsed is not None
        assert parsed['latitude'] == 38.5
        assert parsed['longitude'] == -120.5
        assert parsed['brightness_kelvin'] == 450
        assert parsed['fire_radiative_power'] == 125.5
        assert parsed['confidence'] == 0.92
        assert parsed['source'] == 'FireSat'
        assert parsed['source_id'] == 'firesat_detections'

    def test_calculate_detection_quality(self, connector):
        """Test quality score calculation"""
        # High quality detection
        high_quality = {
            'confidence_score': 0.95,
            'frp': 200,
            'fire_area': 500,
            'scan_angle': 10
        }
        quality = connector._calculate_detection_quality(high_quality)
        assert quality >= 0.9

        # Low quality detection
        low_quality = {
            'confidence_score': 0.65,
            'scan_angle': 50
        }
        quality = connector._calculate_detection_quality(low_quality)
        assert quality < 0.7

    def test_check_anomalies(self, connector):
        """Test anomaly detection"""
        # Normal detection
        normal = {
            'brightness_temp': 450,
            'frp': 150,
            'fire_area': 500,
            'confidence_score': 0.9
        }
        anomalies = connector._check_anomalies(normal)
        assert len(anomalies) == 0

        # Anomalous detection
        anomalous = {
            'brightness_temp': 1200,  # Very high
            'frp': 12000,  # Extreme
            'fire_area': 2000000,  # Large
            'confidence_score': 0.65  # Low
        }
        anomalies = connector._check_anomalies(anomalous)
        assert len(anomalies) > 0
        assert 'unusual_brightness' in anomalies
        assert 'extreme_frp' in anomalies

    @pytest.mark.asyncio
    async def test_streaming_start_stop(self, connector):
        """Test streaming functionality"""
        config = StreamingConfig(
            source_id="firesat_detections",
            polling_interval_seconds=60
        )

        # Start stream
        stream_id = await connector.start_streaming(config)
        assert stream_id is not None
        assert stream_id in connector.active_streams

        # Check stream status
        streams = await connector.get_active_streams()
        assert len(streams) >= 1
        assert any(s['stream_id'] == stream_id for s in streams)

        # Stop stream
        stopped = await connector.stop_streaming(stream_id)
        assert stopped is True
        assert stream_id not in connector.active_streams


class TestFireSatSimulator:
    """Test FireSat simulation functionality"""

    @pytest.fixture
    def simulator(self):
        """Create simulator instance"""
        return FireSatSimulator(seed=42)

    def test_generate_satellite_passes(self, simulator):
        """Test satellite pass generation"""
        start_time = datetime(2025, 3, 15, 0, 0, 0)
        end_time = start_time + timedelta(hours=24)

        california_bounds = {
            'lat_min': 32.5,
            'lat_max': 42.0,
            'lon_min': -124.5,
            'lon_max': -114.1
        }

        passes = simulator.generate_satellite_passes(start_time, end_time, california_bounds)

        # Should have multiple passes over 24 hours (20-minute revisit time)
        assert len(passes) > 50
        assert all('satellite_id' in p for p in passes)
        assert all('pass_start_time' in p for p in passes)

    def test_simulate_fire_detections(self, simulator):
        """Test fire detection simulation"""
        # Create satellite passes
        start_time = datetime(2025, 3, 15, 0, 0, 0)
        end_time = start_time + timedelta(hours=6)

        california_bounds = {
            'lat_min': 32.5,
            'lat_max': 42.0,
            'lon_min': -124.5,
            'lon_max': -114.1
        }

        passes = simulator.generate_satellite_passes(start_time, end_time, california_bounds)

        # Simulate detections
        detections = simulator.simulate_fire_detections(
            passes,
            fire_probability=0.2,
            bounds=california_bounds
        )

        # Should have some detections
        assert len(detections) > 0
        assert all('latitude' in d for d in detections)
        assert all('confidence' in d for d in detections)
        assert all('source_id' in d for d in detections)

    def test_calculate_coverage_metrics(self, simulator):
        """Test coverage metrics calculation"""
        start_time = datetime(2025, 3, 15, 0, 0, 0)
        end_time = start_time + timedelta(hours=24)

        california_bounds = {
            'lat_min': 32.5,
            'lat_max': 42.0,
            'lon_min': -124.5,
            'lon_max': -114.1
        }

        passes = simulator.generate_satellite_passes(start_time, end_time, california_bounds)
        metrics = simulator.calculate_coverage_metrics(passes, time_window_hours=24)

        assert 'total_passes' in metrics
        assert 'avg_revisit_time_min' in metrics
        assert 'coverage_percentage' in metrics
        assert metrics['total_passes'] > 0


class TestFireSatTestbedClient:
    """Test FireSat+ NOS Testbed client"""

    @pytest.mark.asyncio
    async def test_client_creation(self):
        """Test client instantiation"""
        async with FireSatTestbedClient() as client:
            assert client.testbed_url is not None


@pytest.mark.integration
class TestFireSatIntegration:
    """Integration tests (require actual API or testbed)"""

    @pytest.mark.asyncio
    @pytest.mark.skipif(not os.getenv('FIRESAT_API_KEY'), reason="No API key configured")
    async def test_real_api_health_check(self):
        """Test with real FireSat API (if available)"""
        connector = FireSatConnector(api_key=os.getenv('FIRESAT_API_KEY'))
        healthy = await connector.health_check()
        # If API is available, should pass
        # If not available yet, will get connection error (expected)
        assert healthy is not None


def test_firesat_data_schema():
    """Test that FireSat data matches expected schema"""
    connector = FireSatConnector()

    # Generate mock data
    config = BatchConfig(
        source_id="firesat_detections",
        start_date=date.today(),
        end_date=date.today(),
        format="json"
    )

    detections = asyncio.run(connector.fetch_batch_data(config))

    # Verify schema
    required_fields = [
        'timestamp', 'latitude', 'longitude', 'confidence',
        'source', 'source_id', 'provider', 'data_quality'
    ]

    for detection in detections:
        for field in required_fields:
            assert field in detection, f"Missing required field: {field}"

        # Verify types
        assert isinstance(detection['latitude'], (int, float))
        assert isinstance(detection['longitude'], (int, float))
        assert 0 <= detection['confidence'] <= 1
        assert 0 <= detection['data_quality'] <= 1


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
