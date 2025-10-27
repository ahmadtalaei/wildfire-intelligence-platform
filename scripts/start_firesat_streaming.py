"""
Start FireSat Real-Time Streaming
Continuously monitors FireSat for new fire detections in California
"""

import asyncio
import sys
import os
import signal
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'services' / 'data-ingestion-service' / 'src'))

from connectors.firesat_connector import FireSatConnector
from models.ingestion import StreamingConfig
import structlog

logger = structlog.get_logger()

# Global flag for graceful shutdown
shutdown_flag = False


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    global shutdown_flag
    print("\n\nReceived shutdown signal, stopping streams...")
    shutdown_flag = True


async def start_streaming():
    """Start FireSat real-time streaming"""

    global shutdown_flag

    print("=" * 60)
    print("FireSat Real-Time Streaming")
    print("=" * 60)
    print()

    # Initialize connector
    print("[1/3] Initializing FireSat connector...")
    api_key = os.getenv('FIRESAT_API_KEY')

    if not api_key:
        print("  ℹ No API key found, running in MOCK MODE")
        print("  ℹ Mock mode will generate simulated detections")
    else:
        print(f"  ✓ API key configured")

    connector = FireSatConnector(api_key=api_key)
    print(f"  ✓ Connector initialized (mock_mode={connector.mock_mode})")
    print()

    # Health check
    print("[2/3] Running health check...")
    healthy = await connector.health_check()
    if not healthy:
        print("  ✗ Health check failed")
        return
    print("  ✓ Connector is healthy")
    print()

    # Configure streaming
    print("[3/3] Starting real-time streams...")

    # California bounds
    california_bounds = {
        'lat_min': 32.534156,
        'lat_max': 42.009518,
        'lon_min': -124.482003,
        'lon_max': -114.131211
    }

    # Stream configuration
    polling_interval = int(os.getenv('FIRESAT_STREAMING_INTERVAL_SECONDS', 60))

    # Start detection stream
    detections_config = StreamingConfig(
        source_id="firesat_detections",
        polling_interval_seconds=polling_interval,
        spatial_bounds=california_bounds
    )

    print(f"  • Source: {detections_config.source_id}")
    print(f"  • Polling interval: {polling_interval} seconds")
    print(f"  • Region: California")
    print()

    try:
        stream_id = await connector.start_streaming(detections_config)
        print(f"  ✓ Stream started: {stream_id}")
        print()

    except Exception as e:
        print(f"  ✗ Error starting stream: {e}")
        return

    # Monitor streams
    print("=" * 60)
    print("Monitoring FireSat Streams (Press Ctrl+C to stop)")
    print("=" * 60)
    print()

    detection_count = 0
    last_detection_time = None

    try:
        while not shutdown_flag:
            # Check stream status
            active_streams = await connector.get_active_streams()

            for stream in active_streams:
                if stream['stream_id'] == stream_id:
                    records = stream.get('records_received', 0)

                    if records > detection_count:
                        new_detections = records - detection_count
                        detection_count = records
                        last_detection_time = datetime.now()

                        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                              f"New detections: +{new_detections} (Total: {detection_count})")

                        # Log stream status
                        print(f"  Stream: {stream['source_id']}")
                        print(f"  Status: {stream['status']}")
                        print(f"  Last update: {stream.get('last_poll_time', 'N/A')}")
                        print()

            # Wait before next check
            await asyncio.sleep(10)

            # Show heartbeat every minute if no new detections
            if last_detection_time:
                idle_seconds = (datetime.now() - last_detection_time).total_seconds()
                if idle_seconds >= 60 and idle_seconds % 60 < 10:
                    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                          f"Stream active, no new detections ({int(idle_seconds/60)}m idle)")

    except KeyboardInterrupt:
        print("\n\nKeyboard interrupt received")
        shutdown_flag = True

    finally:
        # Stop streams
        print()
        print("Stopping streams...")

        try:
            stopped = await connector.stop_streaming(stream_id)
            if stopped:
                print(f"  ✓ Stream stopped: {stream_id}")
            else:
                print(f"  ✗ Failed to stop stream: {stream_id}")

        except Exception as e:
            print(f"  ✗ Error stopping stream: {e}")

        print()
        print("=" * 60)
        print("Streaming Session Summary")
        print("=" * 60)
        print(f"  • Total detections: {detection_count}")
        if last_detection_time:
            duration = (datetime.now() - (last_detection_time -
                        asyncio.get_event_loop().time() * 0)).total_seconds() / 60
            print(f"  • Session duration: {duration:.1f} minutes")
        print()


async def start_multiple_streams():
    """Start multiple FireSat streams (detections + perimeters)"""

    print("=" * 60)
    print("FireSat Multi-Stream Mode")
    print("=" * 60)
    print()

    connector = FireSatConnector(api_key=os.getenv('FIRESAT_API_KEY'))

    california_bounds = {
        'lat_min': 32.534156,
        'lat_max': 42.009518,
        'lon_min': -124.482003,
        'lon_max': -114.131211
    }

    polling_interval = int(os.getenv('FIRESAT_STREAMING_INTERVAL_SECONDS', 60))

    # Start detection stream
    detections_config = StreamingConfig(
        source_id="firesat_detections",
        polling_interval_seconds=polling_interval,
        spatial_bounds=california_bounds
    )

    # Start perimeter stream (less frequent)
    perimeters_config = StreamingConfig(
        source_id="firesat_perimeters",
        polling_interval_seconds=polling_interval * 5,  # 5x less frequent
        spatial_bounds=california_bounds
    )

    stream_ids = []

    try:
        # Start both streams
        print("Starting streams...")
        det_stream = await connector.start_streaming(detections_config)
        stream_ids.append(det_stream)
        print(f"  ✓ Detections stream: {det_stream}")

        per_stream = await connector.start_streaming(perimeters_config)
        stream_ids.append(per_stream)
        print(f"  ✓ Perimeters stream: {per_stream}")
        print()

        print("Monitoring both streams (Press Ctrl+C to stop)...")
        print()

        # Monitor
        while not shutdown_flag:
            active_streams = await connector.get_active_streams()

            for stream in active_streams:
                if stream['stream_id'] in stream_ids:
                    print(f"[{stream['source_id']}] "
                          f"Records: {stream.get('records_received', 0)}, "
                          f"Status: {stream['status']}")

            await asyncio.sleep(30)
            print()

    except KeyboardInterrupt:
        print("\n\nStopping streams...")

    finally:
        # Stop all streams
        for stream_id in stream_ids:
            await connector.stop_streaming(stream_id)
        print("All streams stopped")


def main():
    """Main entry point"""

    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Ask user for streaming mode
    print("FireSat Streaming Options:")
    print("  1. Detections only (default)")
    print("  2. Detections + Perimeters")
    print()

    choice = input("Select mode (1 or 2): ").strip() or "1"

    if choice == "2":
        asyncio.run(start_multiple_streams())
    else:
        asyncio.run(start_streaming())


if __name__ == "__main__":
    main()
