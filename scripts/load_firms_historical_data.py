"""
Load Historical FIRMS Fire Detection Data

This script loads the last 10 days of FIRMS fire detection data into the database.
Run this to populate historical fire data when the database is empty.

Usage:
    cd C:/dev/wildfire
    python scripts/load_firms_historical_data.py
"""

import asyncio
import sys
import os
from datetime import date, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'services', 'data-ingestion-service', 'src'))

from connectors.nasa_firms_connector import NASAFirmsConnector
from models.ingestion import BatchConfig
import structlog
import psycopg2
from psycopg2.extras import execute_batch

logger = structlog.get_logger()

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'wildfire_db',
    'user': 'wildfire_user',
    'password': 'wildfire_password'
}

# Table mapping for each FIRMS source
TABLE_MAP = {
    'firms_viirs_snpp': 'firms_viirs_snpp_detections',
    'firms_viirs_noaa20': 'firms_viirs_noaa20_detections',
    'firms_viirs_noaa21': 'firms_viirs_noaa21_detections',
    'firms_modis_terra': 'firms_modis_terra_detections',
    'firms_modis_aqua': 'firms_modis_aqua_detections',
    'landsat_nrt': 'landsat_nrt_detections'
}

async def load_historical_firms_data(days_back=10):
    """Load historical FIRMS data for the specified number of days"""

    print("")
    print("=" * 80)
    print(f"Loading Historical FIRMS Fire Detection Data (Last {days_back} Days)")
    print("=" * 80)
    print("")

    # Initialize FIRMS connector
    firms_key = os.getenv('FIRMS_MAP_KEY', '75ced0840b668216396df605281f8ab5')
    connector = NASAFirmsConnector(map_key=firms_key)

    # Connect to database
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False

    try:
        # Calculate date range
        end_date = date.today()
        start_date = end_date - timedelta(days=days_back)

        print(f"Date Range: {start_date} to {end_date}")
        print(f"FIRMS API Key: {firms_key[:20]}...")
        print("")

        total_records = 0

        # Process each FIRMS source
        for source_id, table_name in TABLE_MAP.items():
            print(f"\nProcessing {source_id}...")
            print(f"   Table: {table_name}")

            # Fetch data
            config = BatchConfig(
                source_id=source_id,
                start_date=start_date,
                end_date=end_date
            )

            data = await connector.fetch_batch_data(config)

            if not data:
                print(f"   WARNING: No data available")
                continue

            print(f"   SUCCESS: Fetched {len(data):,} fire detections")

            # Insert into database
            cursor = conn.cursor()

            # Prepare insert query - map API fields to database columns
            mapped_data = []
            for row in data:
                mapped_row = {
                    'timestamp': row['timestamp'],
                    'latitude': row['latitude'],
                    'longitude': row['longitude'],
                    'brightness_kelvin': row.get('bright_ti4', 0),
                    'brightness_temperature_i4': row.get('bright_ti4', 0),
                    'brightness_temperature_i5': row.get('bright_ti5', 0),
                    'fire_radiative_power_mw': row.get('frp', 0),
                    'confidence': row.get('confidence', 0.5),
                    'scan_angle': row.get('scan', 0),
                    'track_degrees': row.get('track', 0),
                    'daynight': row.get('daynight', 'D'),
                    'satellite': row.get('satellite', 'Unknown'),
                    'instrument': row.get('instrument', 'Unknown'),
                    'version': row.get('version', '1.0'),
                    'source': row.get('source', 'NASA FIRMS'),
                    'provider': row.get('provider', 'NASA LANCE')
                }
                mapped_data.append(mapped_row)

            insert_query = f"""
                INSERT INTO {table_name} (
                    timestamp, latitude, longitude, brightness_kelvin,
                    brightness_temperature_i4, brightness_temperature_i5,
                    fire_radiative_power_mw, confidence, scan_angle, track_degrees,
                    daynight, satellite, instrument, version, source, provider
                ) VALUES (
                    %(timestamp)s, %(latitude)s, %(longitude)s, %(brightness_kelvin)s,
                    %(brightness_temperature_i4)s, %(brightness_temperature_i5)s,
                    %(fire_radiative_power_mw)s, %(confidence)s, %(scan_angle)s, %(track_degrees)s,
                    %(daynight)s, %(satellite)s, %(instrument)s, %(version)s, %(source)s, %(provider)s
                )
            """

            # Batch insert
            execute_batch(cursor, insert_query, mapped_data, page_size=1000)
            inserted = cursor.rowcount

            conn.commit()
            cursor.close()

            total_records += inserted
            print(f"   DATABASE: Inserted {inserted:,} records")

        print("")
        print("=" * 80)
        print(f"SUCCESS: Loaded {total_records:,} total fire detections")
        print("=" * 80)
        print("")

        # Display summary
        cursor = conn.cursor()
        for source_id, table_name in TABLE_MAP.items():
            cursor.execute(f"SELECT COUNT(*), MIN(timestamp), MAX(timestamp) FROM {table_name}")
            count, min_time, max_time = cursor.fetchone()
            if count > 0:
                print(f"{table_name}:")
                print(f"  Records: {count:,}")
                print(f"  Date Range: {min_time} to {max_time}")
        cursor.close()

    except Exception as e:
        conn.rollback()
        print(f"\nERROR: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    print("\nNASA FIRMS Historical Data Loader")
    asyncio.run(load_historical_firms_data(days_back=10))
