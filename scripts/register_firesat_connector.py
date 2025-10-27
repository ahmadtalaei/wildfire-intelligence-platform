"""
Register FireSat Connector with Data Ingestion Service
Adds FireSat data sources to the connector registry
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'services' / 'data-ingestion-service' / 'src'))

from connectors.firesat_connector import FireSatConnector
from models.ingestion import DataSource, IngestionFrequency, DataSourceType
import structlog

logger = structlog.get_logger()


def register_firesat_sources():
    """
    Register all FireSat data sources

    Returns:
        List of DataSource objects for FireSat
    """

    # California geographic bounds
    california_bounds = {
        'lat_min': 32.534156,
        'lat_max': 42.009518,
        'lon_min': -124.482003,
        'lon_max': -114.131211
    }

    sources = []

    # FireSat Fire Detections (Real-time, 5m resolution)
    firesat_detections = DataSource(
        source_id="firesat_detections",
        name="FireSat Fire Detections",
        description="Ultra-high resolution (5m) AI-powered fire detections from FireSat satellite constellation. "
                    "50+ satellites with 20-minute global refresh rate detecting fires as small as 5x5 meters.",
        provider="Earth Fire Alliance",
        data_type=DataSourceType.SATELLITE,
        endpoint="https://api.firesat.earthfirealliance.org/v1/detections",
        frequency=IngestionFrequency.STREAMING,
        format="geojson",
        spatial_bounds=california_bounds,
        active=True,
        requires_auth=True,
        auth_type="api_key",
        metadata={
            'constellation_size': 50,
            'spatial_resolution_m': 5.0,
            'revisit_time_minutes': 20,
            'sensor': 'FireSat-TIR',
            'spectral_bands': ['thermal_infrared', 'mid_infrared'],
            'ai_detection': True,
            'model_version': 'v2.1',
            'confidence_threshold': 0.7,
            'max_cloud_cover_percent': 30,
        }
    )
    sources.append(firesat_detections)

    # FireSat Fire Perimeters
    firesat_perimeters = DataSource(
        source_id="firesat_perimeters",
        name="FireSat Fire Perimeters",
        description="AI-estimated fire perimeter polygons generated from multi-spectral thermal imagery. "
                    "Updated every detection pass with sub-hectare accuracy.",
        provider="Earth Fire Alliance",
        data_type=DataSourceType.SATELLITE,
        endpoint="https://api.firesat.earthfirealliance.org/v1/perimeters",
        frequency=IngestionFrequency.HOURLY,
        format="geojson",
        spatial_bounds=california_bounds,
        active=True,
        requires_auth=True,
        auth_type="api_key",
        metadata={
            'estimation_method': 'ai_boundary_detection',
            'model_version': 'v2.1',
            'min_area_hectares': 0.1,
            'update_frequency_minutes': 20,
        }
    )
    sources.append(firesat_perimeters)

    # FireSat Thermal Imagery Metadata
    firesat_thermal = DataSource(
        source_id="firesat_thermal",
        name="FireSat Thermal Imagery",
        description="Multi-spectral thermal infrared imagery metadata. Actual imagery stored in S3, "
                    "metadata includes scene bounds, acquisition time, quality metrics.",
        provider="Earth Fire Alliance",
        data_type=DataSourceType.SATELLITE,
        endpoint="https://api.firesat.earthfirealliance.org/v1/scenes",
        frequency=IngestionFrequency.HOURLY,
        format="json",
        spatial_bounds=california_bounds,
        active=True,
        requires_auth=True,
        auth_type="api_key",
        metadata={
            'spatial_resolution_m': 5.0,
            'spectral_bands': ['TIR1', 'TIR2', 'MIR'],
            'bit_depth': 16,
            'format': 'geotiff',
            's3_bucket': os.getenv('FIRESAT_S3_BUCKET', 'wildfire-firesat-thermal'),
        }
    )
    sources.append(firesat_thermal)

    return sources


def create_connector_instance():
    """
    Create and initialize FireSat connector instance

    Returns:
        FireSatConnector instance
    """
    api_key = os.getenv('FIRESAT_API_KEY')

    if not api_key:
        logger.warning("FIRESAT_API_KEY not found in environment, connector will run in MOCK MODE")
        logger.info("To use real FireSat data:")
        logger.info("  1. Apply for Early Adopter access: https://www.earthfirealliance.org/firesat-early-adopters")
        logger.info("  2. Set FIRESAT_API_KEY in your .env file")

    connector = FireSatConnector(api_key=api_key)

    logger.info(f"FireSat connector initialized (mock_mode={connector.mock_mode})")

    return connector


def verify_connector():
    """
    Verify FireSat connector is working

    Returns:
        bool: True if connector is operational
    """
    import asyncio

    try:
        connector = create_connector_instance()

        # Run health check
        logger.info("Running FireSat connector health check...")
        healthy = asyncio.run(connector.health_check())

        if healthy:
            logger.info("✓ FireSat connector health check passed")
            return True
        else:
            logger.error("✗ FireSat connector health check failed")
            return False

    except Exception as e:
        logger.error(f"Error verifying connector: {e}")
        return False


def main():
    """Main registration script"""

    print("=" * 60)
    print("FireSat Connector Registration")
    print("=" * 60)
    print()

    # Register data sources
    print("[1/3] Registering FireSat data sources...")
    sources = register_firesat_sources()

    for source in sources:
        print(f"  ✓ {source.name} ({source.source_id})")
        print(f"    - Type: {source.data_type.value}")
        print(f"    - Frequency: {source.frequency.value}")
        print(f"    - Endpoint: {source.endpoint}")
    print()

    # Create connector instance
    print("[2/3] Creating FireSat connector instance...")
    connector = create_connector_instance()
    print(f"  ✓ Connector initialized (mock_mode={connector.mock_mode})")
    print()

    # Verify connector
    print("[3/3] Verifying connector health...")
    if verify_connector():
        print("  ✓ Health check passed")
    else:
        print("  ✗ Health check failed")
        sys.exit(1)
    print()

    print("=" * 60)
    print("FireSat Connector Registration Complete!")
    print("=" * 60)
    print()
    print("Data sources registered:")
    for source in sources:
        print(f"  - {source.source_id}")
    print()
    print("Next steps:")
    print("  1. Run test ingestion: python scripts\\test_firesat_ingestion.py")
    print("  2. Start streaming: python scripts\\start_firesat_streaming.py")
    print("  3. Monitor logs for ingestion activity")
    print()

    # Save sources to registry file (optional)
    try:
        import json
        registry_file = Path(__file__).parent.parent / 'config' / 'firesat_sources.json'
        registry_file.parent.mkdir(exist_ok=True)

        with open(registry_file, 'w') as f:
            json.dump([{
                'source_id': s.source_id,
                'name': s.name,
                'description': s.description,
                'provider': s.provider,
                'data_type': s.data_type.value,
                'frequency': s.frequency.value,
                'endpoint': s.endpoint,
                'active': s.active,
                'metadata': s.metadata,
            } for s in sources], f, indent=2)

        print(f"Registry saved to: {registry_file}")
        print()

    except Exception as e:
        logger.warning(f"Could not save registry file: {e}")


if __name__ == "__main__":
    main()
