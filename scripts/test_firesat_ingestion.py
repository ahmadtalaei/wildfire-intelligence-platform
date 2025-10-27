"""
Test FireSat Batch Ingestion
Fetches sample FireSat fire detection data for California
"""

import asyncio
import sys
import os
from datetime import datetime, date, timedelta
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'services' / 'data-ingestion-service' / 'src'))

from connectors.firesat_connector import FireSatConnector
from models.ingestion import BatchConfig
import structlog

logger = structlog.get_logger()


async def test_batch_ingestion():
    """Test FireSat batch ingestion for California"""

    print("=" * 60)
    print("FireSat Batch Ingestion Test")
    print("=" * 60)
    print()

    # Initialize connector
    print("[1/5] Initializing FireSat connector...")
    api_key = os.getenv('FIRESAT_API_KEY')

    if not api_key:
        print("  ℹ No API key found, running in MOCK MODE")
        print("  ℹ To use real data, set FIRESAT_API_KEY in .env")
    else:
        print(f"  ✓ API key configured")

    connector = FireSatConnector(api_key=api_key)
    print(f"  ✓ Connector initialized (mock_mode={connector.mock_mode})")
    print()

    # Health check
    print("[2/5] Running health check...")
    healthy = await connector.health_check()
    if healthy:
        print("  ✓ Connector is healthy")
    else:
        print("  ✗ Health check failed")
        return
    print()

    # Configure batch ingestion
    print("[3/5] Configuring batch ingestion...")

    # California bounds
    california_bounds = {
        'lat_min': 32.534156,
        'lat_max': 42.009518,
        'lon_min': -124.482003,
        'lon_max': -114.131211
    }

    # Fetch last 24 hours of data
    config = BatchConfig(
        source_id="firesat_detections",
        start_date=date.today() - timedelta(days=1),
        end_date=date.today(),
        spatial_bounds=california_bounds,
        format="json"
    )

    print(f"  • Source: {config.source_id}")
    print(f"  • Date range: {config.start_date} to {config.end_date}")
    print(f"  • Bounds: California")
    print(f"  • Format: {config.format}")
    print()

    # Fetch data
    print("[4/5] Fetching fire detections...")
    start_time = datetime.now()

    try:
        detections = await connector.fetch_batch_data(config)
        elapsed = (datetime.now() - start_time).total_seconds()

        print(f"  ✓ Fetched {len(detections)} detections in {elapsed:.2f}s")
        print()

    except Exception as e:
        print(f"  ✗ Error fetching data: {e}")
        return

    # Analyze results
    print("[5/5] Analyzing results...")

    if len(detections) == 0:
        print("  ℹ No detections found for this time period")
        print()
        return

    # Calculate statistics
    confidences = [d.get('confidence', 0) for d in detections]
    frps = [d.get('fire_radiative_power', 0) for d in detections if d.get('fire_radiative_power')]
    quality_scores = [d.get('data_quality', 0) for d in detections if d.get('data_quality')]

    avg_confidence = sum(confidences) / len(confidences) if confidences else 0
    avg_frp = sum(frps) / len(frps) if frps else 0
    avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0

    high_confidence = sum(1 for c in confidences if c >= 0.8)
    low_quality = sum(1 for q in quality_scores if q < 0.7)

    with_anomalies = sum(1 for d in detections if d.get('anomaly_flags'))

    print(f"  • Total detections: {len(detections)}")
    print(f"  • Average confidence: {avg_confidence:.2%}")
    print(f"  • Average FRP: {avg_frp:.1f} MW")
    print(f"  • Average quality score: {avg_quality:.2%}")
    print(f"  • High confidence (≥80%): {high_confidence}")
    print(f"  • Low quality (<70%): {low_quality}")
    print(f"  • With anomaly flags: {with_anomalies}")
    print()

    # Show sample detections
    print("Sample detections:")
    for i, detection in enumerate(detections[:5], 1):
        print(f"\n  Detection {i}:")
        print(f"    Timestamp: {detection.get('timestamp')}")
        print(f"    Location: {detection.get('latitude'):.4f}, {detection.get('longitude'):.4f}")
        print(f"    Brightness: {detection.get('brightness_kelvin', 'N/A')} K")
        print(f"    FRP: {detection.get('fire_radiative_power', 'N/A')} MW")
        print(f"    Confidence: {detection.get('confidence', 0):.1%}")
        print(f"    Satellite: {detection.get('satellite_id', 'Unknown')}")
        print(f"    Quality: {detection.get('data_quality', 0):.1%}")
        if detection.get('anomaly_flags'):
            print(f"    Anomalies: {', '.join(detection.get('anomaly_flags', []))}")

    print()
    print("=" * 60)
    print("Test Complete!")
    print("=" * 60)
    print()

    # Next steps
    if connector.mock_mode:
        print("Next steps (MOCK MODE):")
        print("  1. Apply for FireSat Early Adopter access")
        print("  2. Add FIRESAT_API_KEY to .env")
        print("  3. Re-run this script to test with real data")
    else:
        print("Next steps:")
        print("  1. Store data in database: python scripts/store_firesat_data.py")
        print("  2. Start streaming: python scripts/start_firesat_streaming.py")
        print("  3. View in dashboard")

    print()


async def test_perimeters_ingestion():
    """Test FireSat perimeters batch ingestion"""

    print("=" * 60)
    print("FireSat Perimeters Ingestion Test")
    print("=" * 60)
    print()

    connector = FireSatConnector(api_key=os.getenv('FIRESAT_API_KEY'))

    california_bounds = {
        'lat_min': 32.534156,
        'lat_max': 42.009518,
        'lon_min': -124.482003,
        'lon_max': -114.131211
    }

    config = BatchConfig(
        source_id="firesat_perimeters",
        start_date=date.today() - timedelta(days=1),
        end_date=date.today(),
        spatial_bounds=california_bounds,
        format="geojson"
    )

    print("Fetching fire perimeters...")
    perimeters = await connector.fetch_batch_data(config)

    print(f"✓ Fetched {len(perimeters)} perimeters")
    print()

    if perimeters:
        print("Sample perimeter:")
        p = perimeters[0]
        print(f"  Fire ID: {p.get('fire_id')}")
        print(f"  Area: {p.get('area_hectares', 0):.2f} hectares")
        print(f"  Perimeter: {p.get('perimeter_km', 0):.2f} km")
        print(f"  Confidence: {p.get('confidence', 0):.1%}")
    print()


def main():
    """Run batch ingestion tests"""

    # Test detections
    asyncio.run(test_batch_ingestion())

    # Ask user if they want to test perimeters
    print()
    response = input("Test fire perimeters ingestion? (y/n): ")
    if response.lower() == 'y':
        asyncio.run(test_perimeters_ingestion())


if __name__ == "__main__":
    main()
