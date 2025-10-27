#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix Stale Data Streams
Restarts streaming for stale data sources and verifies data flow
"""

import sys
import asyncio
import aiohttp
from datetime import datetime, timezone
import psycopg2
from tabulate import tabulate
import os
from dotenv import load_dotenv

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Load environment variables
load_dotenv()

# Configuration
DATA_INGESTION_URL = "http://localhost:8003"
DB_CONFIG = {
    'dbname': os.getenv('POSTGRES_DB', 'wildfire_db'),
    'user': os.getenv('POSTGRES_USER', 'wildfire_user'),
    'password': os.getenv('POSTGRES_PASSWORD', 'wildfire_password'),
    'host': 'localhost',
    'port': 5432
}

# Stale sources to fix with appropriate polling intervals
SOURCES_TO_FIX = {
    # Fire Detection Satellites - poll more frequently as they pass over
    'firms_viirs_snpp': {'interval': 1800, 'description': 'VIIRS SNPP Fire Detection'},  # 30 min
    'firms_viirs_noaa20': {'interval': 1800, 'description': 'VIIRS NOAA-20 Fire Detection'},  # 30 min
    'firms_viirs_noaa21': {'interval': 1800, 'description': 'VIIRS NOAA-21 Fire Detection'},  # 30 min
    'firms_modis_aqua': {'interval': 1800, 'description': 'MODIS Aqua Fire Detection'},  # 30 min

    # Air Quality Sources - more frequent polling for realtime data
    'purpleair_california': {'interval': 300, 'description': 'PurpleAir Air Quality Sensors'},  # 5 min
    'airnow_california': {'interval': 3600, 'description': 'EPA AirNow Air Quality'},  # 1 hour

    # Satellite Imagery - less frequent as images are large and updated daily
    'sat_sentinel2_msi': {'interval': 86400, 'description': 'Sentinel-2 MSI Imagery'},  # 24 hours
    'sat_sentinel3_slstr': {'interval': 86400, 'description': 'Sentinel-3 SLSTR Imagery'},  # 24 hours
    'sat_landsat_thermal': {'interval': 86400, 'description': 'Landsat Thermal Imagery'},  # 24 hours
    'landsat_nrt': {'interval': 86400, 'description': 'Landsat NRT Fire Detection'},  # 24 hours

    # ERA5 Reanalysis - updated periodically
    'wx_era5_land': {'interval': 21600, 'description': 'ERA5-Land Reanalysis'},  # 6 hours
    'wx_era5_reanalysis': {'interval': 21600, 'description': 'ERA5 Reanalysis'},  # 6 hours

    # IoT Sources (if configured)
    'iot_weather_stations': {'interval': 300, 'description': 'IoT Weather Stations'},  # 5 min
    'iot_soil_moisture_sensors': {'interval': 600, 'description': 'IoT Soil Moisture Sensors'},  # 10 min
}


async def check_ingestion_service_health():
    """Check if data ingestion service is running"""
    print("\n[1/5] Checking Data Ingestion Service health...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{DATA_INGESTION_URL}/health", timeout=aiohttp.ClientTimeout(total=5)) as response:
                if response.status == 200:
                    health_data = await response.json()
                    print(f"   [OK] Data Ingestion Service is {health_data.get('status', 'unknown')}")

                    # Show connector status
                    connectors = health_data.get('connectors', {})
                    print(f"\n   Connector Status:")
                    for name, status in connectors.items():
                        status_icon = "[OK]" if status else "[!]"
                        print(f"   {status_icon} {name}: {'healthy' if status else 'unhealthy'}")

                    return True
                else:
                    print(f"   [!] Service returned status {response.status}")
                    return False
    except Exception as e:
        print(f"   [X] Cannot connect to Data Ingestion Service: {e}")
        print(f"   [!] Make sure the service is running at {DATA_INGESTION_URL}")
        return False


async def stop_existing_streams():
    """Stop all existing streams to clean state"""
    print("\n[2/5] Stopping existing streams...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{DATA_INGESTION_URL}/streaming/live/stop", timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"   [OK] Stopped {result.get('stopped_count', 0)} existing streams")
                    return True
                else:
                    print(f"   [!] Failed to stop streams: {response.status}")
                    return False
    except Exception as e:
        print(f"   [!] Error stopping streams: {e}")
        return False


async def start_stream(source_id: str, config: dict):
    """Start streaming for a specific source"""
    try:
        payload = {
            "source_id": source_id,
            "source_type": "auto",
            "polling_interval_seconds": config['interval'],
            "spatial_bounds": {
                "lat_min": 32.534156,
                "lat_max": 42.009518,
                "lon_min": -124.482003,
                "lon_max": -114.131211
            },
            "quality_threshold": 0.7
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{DATA_INGESTION_URL}/stream/start",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return {
                        'success': True,
                        'stream_id': result.get('stream_id'),
                        'message': result.get('message')
                    }
                else:
                    error_text = await response.text()
                    return {
                        'success': False,
                        'error': f"HTTP {response.status}: {error_text[:100]}"
                    }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


async def restart_stale_streams():
    """Restart all stale streams"""
    print(f"\n[3/5] Restarting {len(SOURCES_TO_FIX)} stale data streams...")
    print(f"   This may take a few minutes...\n")

    results = []

    for source_id, config in SOURCES_TO_FIX.items():
        print(f"   Starting: {config['description']} ({source_id})...")
        print(f"             Polling interval: {config['interval']}s ({config['interval']/60:.0f} min)")

        result = await start_stream(source_id, config)

        if result['success']:
            print(f"   [OK] Started successfully - Stream ID: {result['stream_id']}")
            results.append({
                'source_id': source_id,
                'description': config['description'],
                'status': 'Started',
                'interval': f"{config['interval']/60:.0f} min",
                'stream_id': result['stream_id']
            })
        else:
            print(f"   [X] Failed: {result['error']}")
            results.append({
                'source_id': source_id,
                'description': config['description'],
                'status': 'Failed',
                'interval': f"{config['interval']/60:.0f} min",
                'stream_id': result.get('error', 'N/A')[:50]
            })

        # Small delay between requests
        await asyncio.sleep(1)

    # Summary
    print(f"\n   Restart Summary:")
    successful = sum(1 for r in results if r['status'] == 'Started')
    failed = len(results) - successful
    print(f"   [OK] Started: {successful}")
    if failed > 0:
        print(f"   [X] Failed:  {failed}")

    return results


def check_database_connectivity():
    """Check database connectivity"""
    print("\n[4/5] Checking database connectivity...")
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';")
        table_count = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        print(f"   [OK] Database connected - {table_count} tables found")
        return True
    except Exception as e:
        print(f"   [X] Database connection failed: {e}")
        return False


async def verify_stream_status():
    """Verify that streams are actively running"""
    print("\n[5/5] Verifying stream status...")

    # Wait a moment for streams to initialize
    print("   Waiting 5 seconds for streams to initialize...")
    await asyncio.sleep(5)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{DATA_INGESTION_URL}/stream/status", timeout=aiohttp.ClientTimeout(total=5)) as response:
                if response.status == 200:
                    status = await response.json()
                    active_count = status.get('total_streams', 0)
                    print(f"   [OK] {active_count} streams are currently active")

                    if active_count > 0:
                        print(f"\n   Active Streams:")
                        for stream in status.get('active_streams', [])[:10]:  # Show first 10
                            print(f"   - {stream.get('source_id', 'unknown')}: {stream.get('status', 'unknown')}")

                        if len(status.get('active_streams', [])) > 10:
                            print(f"   ... and {len(status['active_streams']) - 10} more")

                    return True
                else:
                    print(f"   [!] Could not get stream status: HTTP {response.status}")
                    return False
    except Exception as e:
        print(f"   [!] Error checking stream status: {e}")
        return False


async def main():
    """Main execution function"""
    print("="*100)
    print("WILDFIRE INTELLIGENCE PLATFORM - FIX STALE DATA STREAMS")
    print("="*100)
    print(f"Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"\nThis script will:")
    print(f"  1. Check Data Ingestion Service health")
    print(f"  2. Stop existing streams")
    print(f"  3. Restart {len(SOURCES_TO_FIX)} stale data streams with optimized intervals")
    print(f"  4. Check database connectivity")
    print(f"  5. Verify stream status")
    print("\n" + "="*100)

    # Step 1: Check service health
    if not await check_ingestion_service_health():
        print("\n[X] FAILED: Data Ingestion Service is not available")
        print("    Please start the service with: docker-compose up -d data-ingestion-service")
        return 1

    # Step 2: Stop existing streams
    await stop_existing_streams()

    # Step 3: Restart stale streams
    results = await restart_stale_streams()

    # Step 4: Check database
    db_ok = check_database_connectivity()

    # Step 5: Verify streams
    await verify_stream_status()

    # Final summary
    print("\n" + "="*100)
    print("SUMMARY")
    print("="*100)

    successful = sum(1 for r in results if r['status'] == 'Started')
    failed = len(results) - successful

    print(f"\nStreams Restarted:  {successful} / {len(SOURCES_TO_FIX)}")
    print(f"Database Status:    {'[OK] Connected' if db_ok else '[X] Failed'}")

    if successful > 0:
        print(f"\n[OK] Successfully restarted {successful} data streams!")
        print(f"\nNext steps:")
        print(f"  1. Wait 5-10 minutes for data to be collected")
        print(f"  2. Run: python scripts/monitor_streaming_progress.py")
        print(f"  3. Verify that stale sources are now showing new records")

    if failed > 0:
        print(f"\n[!] {failed} streams failed to start. Check the errors above.")
        print(f"    Common issues:")
        print(f"    - Missing API keys in .env file")
        print(f"    - Authentication failures (Sentinel, Landsat)")
        print(f"    - Network connectivity issues")

    print("\n" + "="*100 + "\n")

    return 0 if failed == 0 else 1


if __name__ == '__main__':
    try:
        exit(asyncio.run(main()))
    except KeyboardInterrupt:
        print("\n\n[!] Operation cancelled by user")
        exit(1)
    except Exception as e:
        print(f"\n[X] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
