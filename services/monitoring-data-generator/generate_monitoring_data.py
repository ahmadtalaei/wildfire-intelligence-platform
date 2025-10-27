#!/usr/bin/env python3
"""
Continuous Monitoring Data Generator
Generates realistic monitoring data for Challenge 2 Storage Dashboard
"""

import os
import time
import random
import psycopg2
from datetime import datetime
from psycopg2.extras import execute_batch

# Database connection parameters
DB_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'postgres'),
    'port': int(os.getenv('POSTGRES_PORT', 5432)),
    'database': os.getenv('POSTGRES_DB', 'wildfire_db'),
    'user': os.getenv('POSTGRES_USER', 'wildfire_user'),
    'password': os.getenv('POSTGRES_PASSWORD', 'wildfire_password')
}

def get_db_connection():
    """Establish database connection with retry logic"""
    max_retries = 5
    retry_delay = 5

    for attempt in range(max_retries):
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            print(f"✓ Connected to PostgreSQL at {DB_CONFIG['host']}")
            return conn
        except psycopg2.OperationalError as e:
            if attempt < max_retries - 1:
                print(f"Database connection failed (attempt {attempt + 1}/{max_retries}), retrying in {retry_delay}s...")
                time.sleep(retry_delay)
            else:
                print(f"✗ Failed to connect to database after {max_retries} attempts")
                raise

def generate_query_performance_data(conn):
    """Generate query performance logs for HOT, WARM, COLD tiers"""
    cursor = conn.cursor()

    # HOT tier: 90% fast (20-80ms), 5% medium (80-110ms), 5% outliers (110-150ms)
    hot_queries = []
    for _ in range(5):  # 5 queries per cycle
        rand = random.random()
        if rand < 0.90:
            duration = random.uniform(20, 80)
        elif rand < 0.95:
            duration = random.uniform(80, 110)
        else:
            duration = random.uniform(110, 150)

        hot_queries.append((
            'HOT',
            random.choice(['SELECT', 'INSERT', 'UPDATE']),
            round(duration, 2),
            random.randint(1, 1000),
            True
        ))

    # WARM tier: 90% fast (200-400ms), 10% slower (400-600ms)
    warm_queries = []
    for _ in range(3):  # 3 queries per cycle
        rand = random.random()
        if rand < 0.90:
            duration = random.uniform(200, 400)
        else:
            duration = random.uniform(400, 600)

        warm_queries.append((
            'WARM',
            'SELECT',
            round(duration, 2),
            random.randint(100, 10000),
            True
        ))

    # COLD tier: 85% fast (1000-3000ms), 15% slower (3000-5000ms)
    cold_queries = []
    for _ in range(2):  # 2 queries per cycle
        rand = random.random()
        if rand < 0.85:
            duration = random.uniform(1000, 3000)
        else:
            duration = random.uniform(3000, 5000)

        cold_queries.append((
            'COLD',
            'SELECT',
            round(duration, 2),
            random.randint(10, 1000),
            True
        ))

    all_queries = hot_queries + warm_queries + cold_queries

    execute_batch(cursor, """
        INSERT INTO query_performance_log
        (storage_tier, query_type, duration_ms, rows_affected, success, executed_at)
        VALUES (%s, %s, %s, %s, %s, NOW())
    """, all_queries)

    conn.commit()
    cursor.close()
    print(f"  → Generated {len(all_queries)} query performance records")

def generate_backup_data(conn):
    """Generate backup job records (runs every 10 cycles)"""
    cursor = conn.cursor()

    # Generate 1-2 backup jobs
    backup_count = random.randint(1, 2)

    for _ in range(backup_count):
        job_type = random.choice(['FULL', 'INCREMENTAL', 'DIFFERENTIAL'])
        storage_tier = random.choice(['HOT', 'WARM', 'COLD', 'ARCHIVE'])
        backup_size = random.randint(100000000, 10000000000)  # 100MB to 10GB
        duration = random.randint(300, 3600)  # 5 min to 1 hour

        # 98% success rate
        status = 'SUCCESS' if random.random() < 0.98 else 'FAILED'
        success_rate = 100.0 if status == 'SUCCESS' else random.uniform(85, 95)

        cursor.execute("""
            INSERT INTO backup_log
            (job_name, job_type, storage_tier, backup_size_bytes, compressed_size_bytes,
             started_at, completed_at, duration_seconds, status, success_rate,
             files_total, files_backed_up, files_failed)
            VALUES (%s, %s, %s, %s, %s,
                    NOW() - INTERVAL '%s seconds', NOW(), %s, %s, %s,
                    %s, %s, %s)
        """, (
            f"{storage_tier}_Backup_{job_type}",
            job_type,
            storage_tier,
            backup_size,
            int(backup_size * random.uniform(0.6, 0.8)),  # 60-80% compression
            duration,
            duration,
            status,
            round(success_rate, 2),
            random.randint(100, 10000),
            random.randint(100, 10000) if status == 'SUCCESS' else random.randint(85, 9500),
            0 if status == 'SUCCESS' else random.randint(1, 100)
        ))

    conn.commit()
    cursor.close()
    print(f"  → Generated {backup_count} backup records")

def generate_security_events(conn):
    """Generate authentication and API violation events"""
    cursor = conn.cursor()

    # Generate 0-2 failed auth attempts per cycle (to average ~8-12 per hour)
    failed_auth_count = random.choices([0, 1, 2], weights=[0.7, 0.2, 0.1])[0]

    for _ in range(failed_auth_count):
        cursor.execute("""
            INSERT INTO audit_log
            (event_type, event_category, severity, username, source_ip,
             resource_accessed, action_performed, result, error_code, event_timestamp)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """, (
            'AUTH_FAILURE',
            'AUTHENTICATION',
            'WARNING',
            f"analyst_{random.randint(1, 50)}",
            f"10.0.{random.randint(0, 255)}.{random.randint(0, 255)}",
            '/api/auth/login',
            'LOGIN',
            'FAILURE',
            random.choice(['AUTH_INVALID_PASSWORD', 'AUTH_INVALID_USERNAME', 'AUTH_ACCOUNT_LOCKED'])
        ))

    # Generate 0-1 API violations per cycle (to average ~2-3 per hour)
    api_violation_count = random.choices([0, 1], weights=[0.9, 0.1])[0]

    for _ in range(api_violation_count):
        cursor.execute("""
            INSERT INTO audit_log
            (event_type, event_category, severity, username, source_ip,
             resource_accessed, action_performed, result, error_code, error_message, event_timestamp)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """, (
            'API_VIOLATION',
            'API',
            'WARNING',
            f"analyst_{random.randint(1, 10)}",
            f"10.0.{random.randint(0, 255)}.{random.randint(0, 255)}",
            '/api/v1/data/export',
            'EXPORT',
            'BLOCKED',
            'RATE_LIMIT_EXCEEDED',
            'API rate limit exceeded: 1000 requests per hour'
        ))

    # Generate 5-10 successful auth events per cycle
    success_auth_count = random.randint(5, 10)

    for _ in range(success_auth_count):
        cursor.execute("""
            INSERT INTO audit_log
            (event_type, event_category, severity, username, source_ip,
             resource_accessed, action_performed, result, event_timestamp)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """, (
            'AUTH_SUCCESS',
            'AUTHENTICATION',
            'INFO',
            f"analyst_{random.randint(1, 100)}",
            f"10.0.{random.randint(0, 255)}.{random.randint(0, 255)}",
            '/api/auth/login',
            'LOGIN',
            'SUCCESS'
        ))

    conn.commit()
    cursor.close()

    total_events = failed_auth_count + api_violation_count + success_auth_count
    print(f"  → Generated {total_events} security events ({failed_auth_count} failures, {api_violation_count} violations)")

def generate_replication_lag_data(conn):
    """Generate PostgreSQL replication lag measurements"""
    cursor = conn.cursor()

    # Generate realistic replication lag (15-35 seconds normal, occasional spikes to 50s)
    if random.random() < 0.95:
        lag_seconds = random.uniform(15, 35)
    else:
        lag_seconds = random.uniform(35, 50)

    cursor.execute("""
        INSERT INTO replication_lag_log
        (primary_host, replica_host, replication_lag_seconds,
         replay_lag_seconds, write_lag_seconds, flush_lag_seconds,
         sync_state, replica_status, measured_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
    """, (
        'wildfire-postgres-primary',
        'wildfire-postgres-replica-1',
        round(lag_seconds, 2),
        round(lag_seconds + random.uniform(0, 2), 2),
        round(lag_seconds - random.uniform(0, 5), 2),
        round(lag_seconds - random.uniform(0, 3), 2),
        'async',
        'STREAMING'
    ))

    conn.commit()
    cursor.close()
    print(f"  → Generated replication lag record ({round(lag_seconds, 1)}s)")

def generate_data_catalog_entries(conn):
    """Generate new data_catalog entries to simulate live data ingestion"""
    cursor = conn.cursor()

    # Generate 1-3 new files per cycle to simulate continuous ingestion
    file_count = random.randint(1, 3)

    for _ in range(file_count):
        storage_tier = random.choices(
            ['HOT', 'WARM', 'COLD', 'ARCHIVE'],
            weights=[0.70, 0.20, 0.08, 0.02]  # Most new data goes to HOT
        )[0]

        file_format = 'postgresql' if storage_tier == 'HOT' else 'parquet'
        compression = 'none' if storage_tier == 'HOT' else 'snappy'

        # Random file size (1MB to 2GB)
        size_bytes = random.randint(1000000, 2000000000)

        # Quality score (95-100%)
        quality_score = random.uniform(0.95, 1.0)

        timestamp = int(time.time())
        cursor.execute("""
            INSERT INTO data_catalog
            (source_table, partition_date, file_path, data_source, storage_tier,
             file_format, compression_type, size_bytes, record_count, quality_score, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """, (
            'firms_modis_terra_detections',
            datetime.now().date(),
            f"/data/{storage_tier.lower()}/fire_detection_{timestamp}_{random.randint(1000, 9999)}.{file_format}",
            random.choice(['NASA_FIRMS', 'NOAA_WEATHER', 'IOT_SENSORS']),
            storage_tier,
            file_format,
            compression,
            size_bytes,
            random.randint(100, 100000),
            round(quality_score, 4)
        ))

    conn.commit()
    cursor.close()
    print(f"  → Generated {file_count} new data_catalog entries")

def cleanup_old_data(conn):
    """Remove data older than 2 hours to prevent table bloat"""
    cursor = conn.cursor()

    cursor.execute("DELETE FROM query_performance_log WHERE executed_at < NOW() - INTERVAL '2 hours'")
    deleted_queries = cursor.rowcount

    cursor.execute("DELETE FROM audit_log WHERE event_timestamp < NOW() - INTERVAL '2 hours'")
    deleted_audit = cursor.rowcount

    cursor.execute("DELETE FROM replication_lag_log WHERE measured_at < NOW() - INTERVAL '2 hours'")
    deleted_replication = cursor.rowcount

    # Also cleanup old data_catalog entries (keep last 6 hours)
    cursor.execute("DELETE FROM data_catalog WHERE created_at < NOW() - INTERVAL '6 hours' AND id NOT IN (SELECT id FROM data_catalog ORDER BY created_at DESC LIMIT 100)")
    deleted_catalog = cursor.rowcount

    conn.commit()
    cursor.close()

    if deleted_queries + deleted_audit + deleted_replication + deleted_catalog > 0:
        print(f"  → Cleaned up old data (queries: {deleted_queries}, audit: {deleted_audit}, replication: {deleted_replication}, catalog: {deleted_catalog})")

def main():
    """Main loop - continuously generate monitoring data"""
    print("=" * 70)
    print("Challenge 2 Storage Monitoring Data Generator")
    print("=" * 70)
    print(f"Database: {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}")
    print("Generating live monitoring data for Grafana dashboard...")
    print("Press Ctrl+C to stop")
    print("=" * 70)

    # Wait for database to be ready
    time.sleep(10)

    conn = get_db_connection()

    cycle = 0

    try:
        while True:
            cycle += 1
            print(f"\n[Cycle {cycle}] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

            # Generate query performance data every cycle (every 30 seconds)
            generate_query_performance_data(conn)

            # Generate replication lag data every cycle
            generate_replication_lag_data(conn)

            # Generate security events every cycle
            generate_security_events(conn)

            # Generate new data_catalog entries every cycle (simulate live ingestion)
            generate_data_catalog_entries(conn)

            # Generate backup data every 10 cycles (~5 minutes)
            if cycle % 10 == 0:
                generate_backup_data(conn)

            # Cleanup old data every 20 cycles (~10 minutes)
            if cycle % 20 == 0:
                cleanup_old_data(conn)

            # Sleep 30 seconds between cycles
            time.sleep(30)

    except KeyboardInterrupt:
        print("\n\nShutting down monitoring data generator...")
        conn.close()
        print("✓ Stopped")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        conn.close()
        raise

if __name__ == '__main__':
    main()
