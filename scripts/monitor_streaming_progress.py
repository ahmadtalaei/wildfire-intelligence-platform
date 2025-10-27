#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Live Streaming Progress Monitor
Displays current data counts versus 6 hours ago across all tables
"""

import sys
import psycopg2
from datetime import datetime, timedelta, timezone
from tabulate import tabulate
import time
import os
from dotenv import load_dotenv

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Load environment variables
load_dotenv()

# Database connection
DB_CONFIG = {
    'dbname': os.getenv('POSTGRES_DB', 'wildfire_db'),
    'user': os.getenv('POSTGRES_USER', 'wildfire_user'),
    'password': os.getenv('POSTGRES_PASSWORD', 'wildfire_password'),
    'host': 'localhost',
    'port': 5432
}

# All tables to monitor (24 specialized tables)
TABLES = [
    # Weather Station Observations (2)
    'metar_observations',
    'noaa_station_observations',

    # Weather Model Forecasts (4)
    'era5_land_reanalysis',
    'era5_reanalysis',
    'gfs_forecasts',
    'nam_forecasts',

    # Weather Alerts & Forecasts (2)
    'noaa_weather_alerts',
    'noaa_gridpoint_forecast',

    # Fire Detection Satellites (6)
    'firms_viirs_snpp_detections',
    'firms_viirs_noaa20_detections',
    'firms_viirs_noaa21_detections',
    'firms_modis_terra_detections',
    'firms_modis_aqua_detections',
    'landsat_nrt_detections',

    # Satellite Imagery Metadata (3)
    'landsat_thermal_imagery',
    'sentinel2_msi_imagery',
    'sentinel3_slstr_imagery',

    # IoT Sensors (2)
    'iot_weather_stations',
    'iot_soil_moisture_sensors',

    # Air Quality (2)
    'sensor_readings',
    'airnow_observations',

    # Fire Incidents (1)
    'fire_incidents',
]


def get_table_counts(conn, one_hour_ago):
    """Get current count vs count from 1 hour ago for all tables"""
    cursor = conn.cursor()
    results = []

    for table in TABLES:
        try:
            # Check if table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = %s
                );
            """, (table,))

            if not cursor.fetchone()[0]:
                results.append({
                    'table': table,
                    'current_total': 0,
                    'one_hour_ago': 0,
                    'new_records': 0,
                    'latest_timestamp': None,
                    'status': '[!] NOT EXISTS'
                })
                continue

            # Get total count
            cursor.execute(f"SELECT COUNT(*) FROM {table};")
            current_total = cursor.fetchone()[0]

            # Get count from 1 hour ago
            cursor.execute(f"""
                SELECT COUNT(*) FROM {table}
                WHERE timestamp <= %s;
            """, (one_hour_ago,))
            count_1h_ago = cursor.fetchone()[0]

            # Get latest timestamp
            cursor.execute(f"""
                SELECT MAX(timestamp) FROM {table};
            """)
            latest_ts = cursor.fetchone()[0]

            # Get records in last 15 minutes
            fifteen_min_ago = datetime.now(timezone.utc) - timedelta(minutes=15)
            cursor.execute(f"""
                SELECT COUNT(*) FROM {table}
                WHERE timestamp > %s;
            """, (fifteen_min_ago,))
            last_15min_count = cursor.fetchone()[0]

            new_records = current_total - count_1h_ago

            # Determine status
            if new_records > 0:
                status = '[OK] ACTIVE'
            elif current_total > 0:
                status = '[--] STALE'
            else:
                status = '[ ] EMPTY'

            results.append({
                'table': table,
                'current_total': current_total,
                'one_hour_ago': count_1h_ago,
                'new_records': new_records,
                'last_15min': last_15min_count,
                'latest_timestamp': latest_ts,
                'status': status
            })

        except Exception as e:
            results.append({
                'table': table,
                'current_total': 0,
                'one_hour_ago': 0,
                'new_records': 0,
                'last_15min': 0,
                'latest_timestamp': None,
                'status': f'[X] ERROR: {str(e)[:20]}'
            })

    cursor.close()
    return results


def format_timestamp(ts):
    """Format timestamp for display"""
    if ts is None:
        return 'N/A'

    # Calculate time ago
    now = datetime.now(timezone.utc)
    if ts.tzinfo is not None:
        now = datetime.now(ts.tzinfo)

    delta = now - ts

    if delta.total_seconds() < 60:
        ago = f"{int(delta.total_seconds())}s ago"
    elif delta.total_seconds() < 3600:
        ago = f"{int(delta.total_seconds() / 60)}m ago"
    elif delta.total_seconds() < 86400:
        ago = f"{int(delta.total_seconds() / 3600)}h ago"
    else:
        ago = f"{int(delta.total_seconds() / 86400)}d ago"

    return f"{ts.strftime('%Y-%m-%d %H:%M:%S')} ({ago})"


def display_summary(results):
    """Display formatted summary"""
    print("\n" + "="*120)
    print("WILDFIRE INTELLIGENCE PLATFORM - LIVE STREAMING MONITOR")
    print("="*120)
    print(f"Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"Comparing: Current data vs 1 hour ago")
    print("="*120 + "\n")

    # Prepare table data
    table_data = []
    total_current = 0
    total_one_hour_ago = 0
    total_new = 0
    total_last_15min = 0
    active_streams = 0
    stale_streams = 0
    empty_streams = 0

    for r in results:
        table_data.append([
            r['table'],
            r['status'],
            f"{r['current_total']:,}",
            f"{r['one_hour_ago']:,}",
            f"{r['new_records']:,}" if r['new_records'] >= 0 else "N/A",
            f"{r['last_15min']:,}" if 'last_15min' in r else "0",
            format_timestamp(r['latest_timestamp'])
        ])

        total_current += r['current_total']
        total_one_hour_ago += r['one_hour_ago']
        total_new += max(0, r['new_records'])
        total_last_15min += r.get('last_15min', 0)

        if r['status'] == '[OK] ACTIVE':
            active_streams += 1
        elif r['status'] == '[--] STALE':
            stale_streams += 1
        elif r['status'] == '[ ] EMPTY':
            empty_streams += 1

    # Display table
    headers = ['Table Name', 'Status', 'Current Total', '1h Ago Total', 'New (1h)', 'Last 15min', 'Latest Record']
    print(tabulate(table_data, headers=headers, tablefmt='grid'))

    # Summary statistics
    print("\n" + "="*120)
    print("SUMMARY STATISTICS")
    print("="*120)
    print(f"[OK] Active Streams:     {active_streams:2d} / {len(TABLES)}")
    print(f"[--] Stale Streams:      {stale_streams:2d} / {len(TABLES)}")
    print(f"[ ] Empty Streams:      {empty_streams:2d} / {len(TABLES)}")
    print(f"\nTotal Records:      {total_current:,}")
    print(f"Records (1h ago):   {total_one_hour_ago:,}")
    print(f"New Records (1h):   {total_new:,}")
    print(f"Records (15min):    {total_last_15min:,}")

    if total_one_hour_ago > 0:
        growth_rate = ((total_current - total_one_hour_ago) / total_one_hour_ago) * 100
        print(f"Growth Rate (1h):   {growth_rate:.2f}%")

    if total_new > 0:
        records_per_minute = total_new / 60
        records_per_second = records_per_minute / 60
        print(f"\nIngestion Rate:")
        print(f"   {total_new:,} records/hour")
        print(f"   {records_per_minute:.1f} records/minute")
        print(f"   {records_per_second:.1f} records/second")

    print("="*120 + "\n")


def get_kafka_status():
    """Check Kafka consumer lag"""
    try:
        import subprocess
        result = subprocess.run(
            ['docker', 'exec', 'kafka', 'kafka-consumer-groups', '--bootstrap-server', 'localhost:9092', '--group', 'data-storage-consumer', '--describe'],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0:
            print("KAFKA CONSUMER STATUS")
            print("="*120)
            print(result.stdout)
        else:
            print("[!] Kafka consumer group not found or not active")
    except Exception as e:
        print(f"[!] Could not retrieve Kafka status: {e}")


def main():
    """Main monitoring function"""
    try:
        # Connect to database
        conn = psycopg2.connect(**DB_CONFIG)

        # Calculate 1 hour ago
        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)

        # Get data
        results = get_table_counts(conn, one_hour_ago)

        # Display results
        display_summary(results)

        # Show Kafka status
        get_kafka_status()

        # Close connection
        conn.close()

        print(f"\nTIP: Run this script periodically to monitor live streaming progress")
        print(f"   Example: watch -n 30 python scripts/monitor_streaming_progress.py\n")

    except psycopg2.OperationalError as e:
        print(f"[X] Database connection error: {e}")
        print(f"   Make sure PostgreSQL is running and accessible at localhost:5432")
        return 1
    except Exception as e:
        print(f"[X] Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == '__main__':
    exit(main())
