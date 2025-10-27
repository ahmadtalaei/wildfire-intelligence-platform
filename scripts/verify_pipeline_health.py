#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pipeline Health Verification
Checks the entire data pipeline from sources to storage
"""

import sys
import psycopg2
from datetime import datetime, timedelta, timezone
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


def check_data_freshness(conn):
    """Check how fresh the data is in each table"""
    cursor = conn.cursor()

    print("\n" + "="*100)
    print("DATA FRESHNESS CHECK")
    print("="*100)

    critical_tables = {
        'metar_observations': 'Weather Stations (METAR)',
        'noaa_station_observations': 'NOAA Weather Stations',
        'gfs_forecasts': 'GFS Weather Forecasts',
        'nam_forecasts': 'NAM Weather Forecasts',
        'noaa_gridpoint_forecast': 'NOAA Gridpoint Forecasts',
        'firms_modis_terra_detections': 'MODIS Terra Fire Detections',
        'firms_viirs_snpp_detections': 'VIIRS SNPP Fire Detections',
        'firms_viirs_noaa20_detections': 'VIIRS NOAA-20 Fire Detections',
    }

    for table, description in critical_tables.items():
        try:
            cursor.execute(f"""
                SELECT
                    COUNT(*) as total_records,
                    MAX(timestamp) as latest,
                    COUNT(*) FILTER (WHERE timestamp > NOW() - INTERVAL '1 hour') as last_hour,
                    COUNT(*) FILTER (WHERE timestamp > NOW() - INTERVAL '6 hours') as last_6_hours,
                    COUNT(*) FILTER (WHERE timestamp > NOW() - INTERVAL '24 hours') as last_24_hours
                FROM {table};
            """)

            result = cursor.fetchone()
            total, latest, last_hour, last_6h, last_24h = result

            # Calculate freshness status
            if latest:
                now = datetime.now(timezone.utc)
                if latest.tzinfo is not None:
                    now = datetime.now(latest.tzinfo)
                age_seconds = (now - latest).total_seconds()

                if age_seconds < 3600:  # < 1 hour
                    status = "[EXCELLENT]"
                elif age_seconds < 21600:  # < 6 hours
                    status = "[GOOD]     "
                elif age_seconds < 86400:  # < 24 hours
                    status = "[STALE]    "
                else:
                    status = "[CRITICAL] "

                age_str = f"{int(age_seconds / 3600)}h {int((age_seconds % 3600) / 60)}m ago"
            else:
                status = "[NO DATA]  "
                age_str = "N/A"

            print(f"\n{status} {description}")
            print(f"  Total Records:    {total:,}")
            print(f"  Latest Record:    {age_str}")
            print(f"  Last Hour:        {last_hour:,} records")
            print(f"  Last 6 Hours:     {last_6h:,} records")
            print(f"  Last 24 Hours:    {last_24h:,} records")

        except Exception as e:
            print(f"\n[ERROR] {description}")
            print(f"  Error: {str(e)[:80]}")

    cursor.close()


def check_streaming_sources(conn):
    """Check which sources are actively streaming"""
    cursor = conn.cursor()

    print("\n" + "="*100)
    print("STREAMING SOURCE STATUS")
    print("="*100)

    # Check if data_sources table exists
    try:
        cursor.execute("""
            SELECT
                source_id,
                name,
                source_type,
                is_active,
                last_successful_fetch
            FROM data_sources
            ORDER BY source_type, source_id;
        """)

        sources = cursor.fetchall()

        current_type = None
        for source in sources:
            source_id, name, source_type, is_active, last_fetch = source

            if source_type != current_type:
                print(f"\n[{source_type.upper()}]")
                current_type = source_type

            status = "[ACTIVE]" if is_active else "[INACTIVE]"

            if last_fetch:
                now = datetime.now(timezone.utc)
                if last_fetch.tzinfo is not None:
                    now = datetime.now(last_fetch.tzinfo)
                age = (now - last_fetch).total_seconds()

                if age < 3600:
                    fetch_status = f"(Last fetch: {int(age/60)}m ago)"
                else:
                    fetch_status = f"(Last fetch: {int(age/3600)}h ago)"
            else:
                fetch_status = "(Never fetched)"

            print(f"  {status} {source_id:30s} - {name:40s} {fetch_status}")

    except Exception as e:
        print(f"[!] Could not retrieve data sources: {e}")
        print("    The data_sources table may not exist yet.")

    cursor.close()


def check_kafka_topics():
    """Check Kafka topic status"""
    print("\n" + "="*100)
    print("KAFKA TOPIC STATUS")
    print("="*100)

    try:
        import subprocess

        # List topics
        result = subprocess.run(
            ['docker', 'exec', 'kafka', 'kafka-topics', '--bootstrap-server', 'localhost:9092', '--list'],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0:
            topics = [t.strip() for t in result.stdout.split('\n') if t.strip() and 'wildfire' in t]

            print(f"\nFound {len(topics)} wildfire topics:")
            for topic in topics:
                # Get topic details
                detail_result = subprocess.run(
                    ['docker', 'exec', 'kafka', 'kafka-run-class', 'kafka.tools.GetOffsetShell',
                     '--broker-list', 'localhost:9092', '--topic', topic, '--time', '-1'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )

                if detail_result.returncode == 0:
                    # Parse offset (total messages)
                    total_messages = sum(int(line.split(':')[-1]) for line in detail_result.stdout.split('\n') if ':' in line)
                    print(f"  [OK] {topic:40s} - {total_messages:,} messages")
                else:
                    print(f"  [!] {topic:40s} - Could not get offset")
        else:
            print("[!] Could not list Kafka topics")

    except Exception as e:
        print(f"[!] Kafka not accessible: {e}")


def check_docker_services():
    """Check if Docker services are running"""
    print("\n" + "="*100)
    print("DOCKER SERVICES STATUS")
    print("="*100)

    try:
        import subprocess

        result = subprocess.run(
            ['docker', 'ps', '--filter', 'name=wildfire', '--format', '{{.Names}}\t{{.Status}}'],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0:
            services = result.stdout.strip().split('\n')
            for service in services:
                if service:
                    parts = service.split('\t')
                    if len(parts) >= 2:
                        name, status = parts[0], parts[1]
                        if 'Up' in status:
                            print(f"  [RUNNING] {name:40s} - {status}")
                        else:
                            print(f"  [DOWN]    {name:40s} - {status}")
        else:
            print("[!] Could not check Docker services")

    except Exception as e:
        print(f"[!] Docker not accessible: {e}")


def main():
    """Main function"""
    print("\n" + "="*100)
    print("WILDFIRE INTELLIGENCE PLATFORM - PIPELINE HEALTH CHECK")
    print("="*100)
    print(f"Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC")

    try:
        # Check Docker services
        check_docker_services()

        # Check Kafka topics
        check_kafka_topics()

        # Connect to database
        conn = psycopg2.connect(**DB_CONFIG)

        # Check data freshness
        check_data_freshness(conn)

        # Check streaming sources
        check_streaming_sources(conn)

        # Close connection
        conn.close()

        print("\n" + "="*100)
        print("HEALTH CHECK COMPLETE")
        print("="*100 + "\n")

    except psycopg2.OperationalError as e:
        print(f"\n[X] Database connection error: {e}")
        print(f"    Make sure PostgreSQL is running at localhost:5432\n")
        return 1
    except Exception as e:
        print(f"\n[X] Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == '__main__':
    exit(main())
