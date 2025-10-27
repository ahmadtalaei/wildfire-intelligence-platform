#!/usr/bin/env python3
"""
Challenge 3 Analytics Platform Data Generator
Generates realistic user activity, queries, sessions, reports, and exports for Challenge 3 dashboard
"""

import os
import time
import random
import psycopg2
from datetime import datetime, timedelta
from psycopg2.extras import execute_batch
import uuid

# Database connection parameters
DB_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'postgres'),
    'port': int(os.getenv('POSTGRES_PORT', 5432)),
    'database': os.getenv('POSTGRES_DB', 'wildfire_db'),
    'user': os.getenv('POSTGRES_USER', 'wildfire_user'),
    'password': os.getenv('POSTGRES_PASSWORD', 'wildfire_password')
}

# User roles and their typical behavior patterns
USER_ROLES = {
    'fire_chief': {
        'dashboards': ['fire-chief'],
        'query_types': ['rest_api', 'visualization'],
        'avg_queries_per_cycle': 3,
        'report_types': ['summary', 'geospatial'],
        'export_types': ['pdf', 'csv']
    },
    'data_analyst': {
        'dashboards': ['analyst'],
        'query_types': ['sql', 'rest_api', 'visualization'],
        'avg_queries_per_cycle': 5,
        'report_types': ['detailed', 'statistical', 'summary'],
        'export_types': ['excel', 'csv', 'json']
    },
    'data_scientist': {
        'dashboards': ['scientist'],
        'query_types': ['sql', 'graphql', 'rest_api'],
        'avg_queries_per_cycle': 8,
        'report_types': ['ml_model', 'statistical', 'detailed'],
        'export_types': ['csv', 'json', 'parquet']
    },
    'admin': {
        'dashboards': ['admin'],
        'query_types': ['sql', 'rest_api'],
        'avg_queries_per_cycle': 2,
        'report_types': ['summary'],
        'export_types': ['csv', 'json']
    },
    'field_responder': {
        'dashboards': ['fire-chief'],
        'query_types': ['rest_api'],
        'avg_queries_per_cycle': 1,
        'report_types': ['summary'],
        'export_types': ['pdf']
    }
}

API_ENDPOINTS = [
    '/api/v1/fires/active',
    '/api/v1/fires/history',
    '/api/v1/weather/current',
    '/api/v1/sensors/data',
    '/api/v1/analytics/query',
    '/api/v1/reports/generate',
    '/api/v1/exports/download',
    '/api/v1/datasets/list',
    '/api/v1/datasets/metadata',
    '/api/v1/visualizations/create'
]

DATASET_NAMES = [
    'firms_modis_terra_detections',
    'noaa_weather_stations',
    'iot_air_quality_sensors',
    'copernicus_era5_reanalysis',
    'landsat_thermal_imagery',
    'fire_perimeter_history',
    'weather_forecast_data'
]

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

def manage_user_sessions(conn):
    """Create and manage active user sessions"""
    cursor = conn.cursor()

    # Create 2-5 new sessions per cycle
    new_sessions = random.randint(2, 5)

    for _ in range(new_sessions):
        user_role = random.choice(list(USER_ROLES.keys()))
        user_id = f"{user_role}_user_{random.randint(1, 20)}"
        dashboard = random.choice(USER_ROLES[user_role]['dashboards'])

        cursor.execute("""
            INSERT INTO user_sessions
            (user_id, user_role, dashboard_accessed, ip_address, user_agent, is_active, last_activity)
            VALUES (%s, %s, %s, %s, %s, TRUE, NOW())
            RETURNING session_id
        """, (
            user_id,
            user_role,
            dashboard,
            f"10.0.{random.randint(0, 255)}.{random.randint(1, 255)}",
            random.choice(['Mozilla/5.0', 'Chrome/120.0', 'Safari/17.0'])
        ))

        session_id = cursor.fetchone()[0]

    # Update existing sessions (mark some as inactive, update last_activity)
    cursor.execute("""
        UPDATE user_sessions
        SET is_active = FALSE,
            session_end = NOW()
        WHERE is_active = TRUE
          AND last_activity < NOW() - INTERVAL '15 minutes'
          AND random() < 0.3
    """)

    cursor.execute("""
        UPDATE user_sessions
        SET last_activity = NOW()
        WHERE is_active = TRUE
          AND random() < 0.5
    """)

    conn.commit()
    cursor.close()
    print(f"  → Managed user sessions ({new_sessions} new)")

def generate_analytics_queries(conn):
    """Generate analytics query logs"""
    cursor = conn.cursor()

    # Get active sessions
    cursor.execute("""
        SELECT session_id, user_id, user_role
        FROM user_sessions
        WHERE is_active = TRUE
          AND last_activity > NOW() - INTERVAL '30 minutes'
        ORDER BY random()
        LIMIT 10
    """)

    active_sessions = cursor.fetchall()

    if not active_sessions:
        print("  → No active sessions for queries")
        cursor.close()
        return

    queries = []
    for session_id, user_id, user_role in active_sessions:
        role_config = USER_ROLES.get(user_role, USER_ROLES['data_analyst'])
        num_queries = random.randint(1, role_config['avg_queries_per_cycle'])

        for _ in range(num_queries):
            query_type = random.choice(role_config['query_types'])

            # Realistic response times based on query type
            if query_type == 'sql':
                response_time = random.randint(100, 2000)
            elif query_type == 'rest_api':
                response_time = random.randint(50, 500)
            elif query_type == 'graphql':
                response_time = random.randint(80, 800)
            else:  # visualization, export
                response_time = random.randint(200, 1500)

            # 95% success rate
            query_status = 'success' if random.random() < 0.95 else random.choice(['failed', 'timeout'])

            queries.append((
                session_id,
                user_id,
                user_role,
                query_type,
                f"SELECT * FROM {random.choice(DATASET_NAMES)} WHERE timestamp > NOW() - INTERVAL '24 hours'",
                query_status,
                response_time,
                random.randint(10, 10000) if query_status == 'success' else 0,
                random.choice(['postgresql', 'minio', 's3', 'cache'])
            ))

    execute_batch(cursor, """
        INSERT INTO analytics_queries
        (session_id, user_id, user_role, query_type, query_text, query_status,
         response_time_ms, rows_returned, data_source, executed_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
    """, queries)

    conn.commit()
    cursor.close()
    print(f"  → Generated {len(queries)} analytics queries")

def generate_reports(conn):
    """Generate report activity (less frequent)"""
    cursor = conn.cursor()

    # Generate reports only 30% of the time
    if random.random() > 0.3:
        cursor.close()
        return

    # Get active sessions
    cursor.execute("""
        SELECT session_id, user_id, user_role
        FROM user_sessions
        WHERE is_active = TRUE
        ORDER BY random()
        LIMIT 3
    """)

    active_sessions = cursor.fetchall()

    reports = []
    for session_id, user_id, user_role in active_sessions:
        role_config = USER_ROLES.get(user_role, USER_ROLES['data_analyst'])

        report_type = random.choice(role_config['report_types'])
        output_format = random.choice(role_config['export_types'])

        # Report generation time based on type
        if report_type == 'ml_model':
            gen_time = random.randint(5000, 30000)
        elif report_type == 'detailed':
            gen_time = random.randint(2000, 10000)
        else:
            gen_time = random.randint(500, 3000)

        reports.append((
            session_id,
            user_id,
            user_role,
            f"{report_type.replace('_', ' ').title()} Report - {datetime.now().strftime('%Y%m%d')}",
            report_type,
            output_format,
            random.randint(100000, 10000000),  # file size
            gen_time
        ))

    if reports:
        execute_batch(cursor, """
            INSERT INTO reports_generated
            (session_id, user_id, user_role, report_name, report_type,
             output_format, file_size_bytes, generation_time_ms, generated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """, reports)

        conn.commit()
        print(f"  → Generated {len(reports)} reports")

    cursor.close()

def generate_data_exports(conn):
    """Generate data export activity"""
    cursor = conn.cursor()

    # Generate exports only 40% of the time
    if random.random() > 0.4:
        cursor.close()
        return

    # Get active sessions
    cursor.execute("""
        SELECT session_id, user_id, user_role
        FROM user_sessions
        WHERE is_active = TRUE
        ORDER BY random()
        LIMIT 4
    """)

    active_sessions = cursor.fetchall()

    exports = []
    for session_id, user_id, user_role in active_sessions:
        role_config = USER_ROLES.get(user_role, USER_ROLES['data_analyst'])

        export_type = random.choice(role_config['export_types'])
        dataset = random.choice(DATASET_NAMES)
        row_count = random.randint(100, 50000)

        # File size based on format and row count
        if export_type == 'parquet':
            file_size = row_count * random.randint(50, 100)
        elif export_type == 'csv':
            file_size = row_count * random.randint(200, 400)
        elif export_type == 'json':
            file_size = row_count * random.randint(300, 600)
        else:
            file_size = row_count * random.randint(150, 300)

        exports.append((
            session_id,
            user_id,
            user_role,
            export_type,
            dataset,
            row_count,
            file_size,
            'completed',
            random.randint(500, 5000)
        ))

    if exports:
        execute_batch(cursor, """
            INSERT INTO data_exports
            (session_id, user_id, user_role, export_type, dataset_name,
             row_count, file_size_bytes, export_status, export_time_ms, exported_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """, exports)

        conn.commit()
        print(f"  → Generated {len(exports)} data exports")

    cursor.close()

def generate_api_usage(conn):
    """Generate API usage logs"""
    cursor = conn.cursor()

    # Generate 5-15 API calls per cycle
    api_calls = []
    num_calls = random.randint(5, 15)

    for _ in range(num_calls):
        endpoint = random.choice(API_ENDPOINTS)
        http_method = random.choice(['GET', 'GET', 'GET', 'POST', 'PUT'])  # GET weighted higher

        # 97% success rate
        if random.random() < 0.97:
            status_code = random.choice([200, 200, 200, 201, 204])
        else:
            status_code = random.choice([400, 401, 403, 404, 500, 503])

        response_time = random.randint(50, 800)

        api_calls.append((
            None,  # session_id
            None,  # user_id
            None,  # user_role
            endpoint,
            http_method,
            status_code,
            response_time,
            random.randint(100, 5000),
            random.randint(500, 50000)
        ))

    execute_batch(cursor, """
        INSERT INTO api_usage
        (session_id, user_id, user_role, endpoint, http_method, status_code,
         response_time_ms, request_size_bytes, response_size_bytes, requested_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
    """, api_calls)

    conn.commit()
    cursor.close()
    print(f"  → Generated {len(api_calls)} API usage logs")

def generate_dashboard_interactions(conn):
    """Generate dashboard interaction logs"""
    cursor = conn.cursor()

    # Get active sessions
    cursor.execute("""
        SELECT session_id, user_id, user_role, dashboard_accessed
        FROM user_sessions
        WHERE is_active = TRUE
        ORDER BY random()
        LIMIT 8
    """)

    active_sessions = cursor.fetchall()

    interactions = []
    for session_id, user_id, user_role, dashboard in active_sessions:
        # Generate 1-3 interactions per session
        num_interactions = random.randint(1, 3)

        for _ in range(num_interactions):
            widget_name = random.choice([
                'Active Fires Map',
                'Weather Overlay',
                'Sensor Data',
                'Historical Trends',
                'Risk Prediction',
                'Resource Status',
                'Query Builder',
                'Data Explorer'
            ])

            interaction_type = random.choice([
                'view', 'view', 'view',  # view weighted higher
                'filter', 'drill_down', 'export', 'refresh'
            ])

            interactions.append((
                session_id,
                user_id,
                user_role,
                dashboard,
                widget_name,
                interaction_type
            ))

    if interactions:
        execute_batch(cursor, """
            INSERT INTO dashboard_interactions
            (session_id, user_id, user_role, dashboard_name, widget_name,
             interaction_type, interaction_timestamp)
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
        """, interactions)

        conn.commit()
        print(f"  → Generated {len(interactions)} dashboard interactions")

    cursor.close()

def cleanup_old_data(conn):
    """Remove data older than 6 hours to prevent table bloat"""
    cursor = conn.cursor()

    cursor.execute("DELETE FROM analytics_queries WHERE executed_at < NOW() - INTERVAL '6 hours'")
    deleted_queries = cursor.rowcount

    cursor.execute("DELETE FROM api_usage WHERE requested_at < NOW() - INTERVAL '6 hours'")
    deleted_api = cursor.rowcount

    cursor.execute("DELETE FROM dashboard_interactions WHERE interaction_timestamp < NOW() - INTERVAL '6 hours'")
    deleted_interactions = cursor.rowcount

    cursor.execute("DELETE FROM user_sessions WHERE session_start < NOW() - INTERVAL '12 hours' AND is_active = FALSE")
    deleted_sessions = cursor.rowcount

    conn.commit()
    cursor.close()

    if deleted_queries + deleted_api + deleted_interactions + deleted_sessions > 0:
        print(f"  → Cleaned up old data (queries: {deleted_queries}, api: {deleted_api}, interactions: {deleted_interactions}, sessions: {deleted_sessions})")

def main():
    """Main loop - continuously generate Challenge 3 analytics data"""
    print("=" * 70)
    print("Challenge 3 Analytics Platform Data Generator")
    print("=" * 70)
    print(f"Database: {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}")
    print("Generating live analytics data for Grafana dashboard...")
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

            # Generate user sessions (every cycle)
            manage_user_sessions(conn)

            # Generate analytics queries (every cycle)
            generate_analytics_queries(conn)

            # Generate API usage (every cycle)
            generate_api_usage(conn)

            # Generate dashboard interactions (every cycle)
            generate_dashboard_interactions(conn)

            # Generate reports (occasionally)
            generate_reports(conn)

            # Generate data exports (occasionally)
            generate_data_exports(conn)

            # Cleanup old data every 20 cycles (~10 minutes)
            if cycle % 20 == 0:
                cleanup_old_data(conn)

            # Sleep 30 seconds between cycles
            time.sleep(30)

    except KeyboardInterrupt:
        print("\n\nShutting down Challenge 3 data generator...")
        conn.close()
        print("✓ Stopped")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        conn.close()
        raise

if __name__ == '__main__':
    main()
