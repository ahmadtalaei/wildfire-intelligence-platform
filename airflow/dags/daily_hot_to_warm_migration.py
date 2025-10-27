"""
Daily Hot-to-Warm Data Migration DAG

This DAG runs daily at midnight PST to move 7-day-old data from PostgreSQL (HOT tier)
to MinIO Parquet files (WARM tier), preventing database bloat and optimizing costs.

Schedule: Daily at 00:00 PST
Retention: Moves data older than 7 days
Target: PostgreSQL → MinIO (Parquet format, date-partitioned)
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from io import BytesIO
import logging

# Default arguments
default_args = {
    'owner': 'wildfire-platform',
    'depends_on_past': False,
    'start_date': datetime(2025, 1, 1),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
}

# Initialize DAG
dag = DAG(
    'daily_hot_to_warm_migration',
    default_args=default_args,
    description='Migrate 7-day-old data from PostgreSQL to MinIO Parquet',
    schedule_interval='0 8 * * *',  # 00:00 PST (8:00 UTC)
    catchup=False,
    tags=['data-lifecycle', 'storage', 'migration'],
)


def migrate_fire_detections(**context):
    """
    Migrate fire detection records from PostgreSQL to MinIO Parquet.
    Moves data older than 7 days.
    """
    logging.info("Starting fire detections migration...")

    # Calculate cutoff date (7 days ago)
    cutoff_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    target_date = (datetime.now() - timedelta(days=7))

    # Connect to PostgreSQL
    pg_hook = PostgresHook(postgres_conn_id='postgres_default')

    # Query old data
    query = f"""
        SELECT
            id, timestamp, satellite_name, latitude, longitude,
            brightness_kelvin, confidence_percent, frp_megawatts,
            fire_radiative_power, scan_pixel_size_km, track_pixel_size_km,
            data_quality_flag, data_source
        FROM firms_viirs_noaa20_detections
        WHERE timestamp < '{cutoff_date}'
        ORDER BY timestamp
    """

    logging.info(f"Querying fire detections older than {cutoff_date}")
    df = pg_hook.get_pandas_df(query)

    if df.empty:
        logging.info("No data to migrate for fire detections")
        return

    logging.info(f"Found {len(df)} records to migrate")

    # Convert to Parquet
    table = pa.Table.from_pandas(df)
    parquet_buffer = BytesIO()
    pq.write_table(table, parquet_buffer, compression='snappy')
    parquet_buffer.seek(0)

    # Upload to MinIO
    s3_hook = S3Hook(aws_conn_id='minio_default')
    s3_key = f"fires/viirs/{target_date.year}/{target_date.month:02d}/{target_date.day:02d}/viirs_{target_date.strftime('%Y%m%d')}.parquet"

    logging.info(f"Uploading to MinIO: wildfire-data/{s3_key}")
    s3_hook.load_file_obj(
        file_obj=parquet_buffer,
        key=s3_key,
        bucket_name='wildfire-data',
        replace=True
    )

    # Verify upload and delete from PostgreSQL
    delete_query = f"""
        DELETE FROM firms_viirs_noaa20_detections
        WHERE timestamp < '{cutoff_date}'
    """

    logging.info(f"Deleting {len(df)} migrated records from PostgreSQL")
    pg_hook.run(delete_query)

    # Log to metadata catalog
    metadata_insert = f"""
        INSERT INTO data_catalog (
            file_path, data_source, record_count, size_bytes,
            min_timestamp, max_timestamp, storage_tier, created_at
        ) VALUES (
            '{s3_key}',
            'firms_viirs_noaa20',
            {len(df)},
            {parquet_buffer.getbuffer().nbytes},
            '{df['timestamp'].min()}',
            '{df['timestamp'].max()}',
            'WARM',
            NOW()
        )
    """
    pg_hook.run(metadata_insert)

    logging.info(f"Successfully migrated {len(df)} fire detection records")
    return {
        'records_migrated': len(df),
        's3_path': s3_key,
        'size_bytes': parquet_buffer.getbuffer().nbytes
    }


def migrate_weather_data(**context):
    """
    Migrate weather observation records from PostgreSQL to MinIO Parquet.
    Moves data older than 7 days.
    """
    logging.info("Starting weather data migration...")

    cutoff_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    target_date = (datetime.now() - timedelta(days=7))

    pg_hook = PostgresHook(postgres_conn_id='postgres_default')

    # Migrate ERA5 reanalysis data
    query = f"""
        SELECT * FROM era5_reanalysis
        WHERE timestamp < '{cutoff_date}'
        ORDER BY timestamp
    """

    logging.info(f"Querying ERA5 data older than {cutoff_date}")
    df = pg_hook.get_pandas_df(query)

    if df.empty:
        logging.info("No ERA5 data to migrate")
        return

    logging.info(f"Found {len(df)} ERA5 records to migrate")

    # Convert to Parquet with compression
    table = pa.Table.from_pandas(df)
    parquet_buffer = BytesIO()
    pq.write_table(table, parquet_buffer, compression='snappy')
    parquet_buffer.seek(0)

    # Upload to MinIO
    s3_hook = S3Hook(aws_conn_id='minio_default')
    s3_key = f"weather/era5/{target_date.year}/{target_date.month:02d}/{target_date.day:02d}/era5_{target_date.strftime('%Y%m%d')}.parquet"

    logging.info(f"Uploading to MinIO: wildfire-data/{s3_key}")
    s3_hook.load_file_obj(
        file_obj=parquet_buffer,
        key=s3_key,
        bucket_name='wildfire-data',
        replace=True
    )

    # Delete from PostgreSQL
    delete_query = f"DELETE FROM era5_reanalysis WHERE timestamp < '{cutoff_date}'"
    logging.info(f"Deleting {len(df)} migrated ERA5 records from PostgreSQL")
    pg_hook.run(delete_query)

    # Log to metadata catalog
    metadata_insert = f"""
        INSERT INTO data_catalog (
            file_path, data_source, record_count, size_bytes,
            min_timestamp, max_timestamp, storage_tier, created_at
        ) VALUES (
            '{s3_key}',
            'era5_reanalysis',
            {len(df)},
            {parquet_buffer.getbuffer().nbytes},
            '{df['timestamp'].min()}',
            '{df['timestamp'].max()}',
            'WARM',
            NOW()
        )
    """
    pg_hook.run(metadata_insert)

    logging.info(f"Successfully migrated {len(df)} ERA5 records")
    return {
        'records_migrated': len(df),
        's3_path': s3_key,
        'size_bytes': parquet_buffer.getbuffer().nbytes
    }


def migrate_sensor_data(**context):
    """
    Migrate IoT sensor readings from PostgreSQL to MinIO Parquet.
    Moves data older than 7 days.
    """
    logging.info("Starting sensor data migration...")

    cutoff_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    target_date = (datetime.now() - timedelta(days=7))

    pg_hook = PostgresHook(postgres_conn_id='postgres_default')

    query = f"""
        SELECT * FROM sensor_readings
        WHERE timestamp < '{cutoff_date}'
        ORDER BY timestamp
    """

    logging.info(f"Querying sensor data older than {cutoff_date}")
    df = pg_hook.get_pandas_df(query)

    if df.empty:
        logging.info("No sensor data to migrate")
        return

    logging.info(f"Found {len(df)} sensor records to migrate")

    # Convert to Parquet
    table = pa.Table.from_pandas(df)
    parquet_buffer = BytesIO()
    pq.write_table(table, parquet_buffer, compression='snappy')
    parquet_buffer.seek(0)

    # Upload to MinIO
    s3_hook = S3Hook(aws_conn_id='minio_default')
    s3_key = f"sensors/iot/{target_date.year}/{target_date.month:02d}/{target_date.day:02d}/sensors_{target_date.strftime('%Y%m%d')}.parquet"

    logging.info(f"Uploading to MinIO: wildfire-data/{s3_key}")
    s3_hook.load_file_obj(
        file_obj=parquet_buffer,
        key=s3_key,
        bucket_name='wildfire-data',
        replace=True
    )

    # Delete from PostgreSQL
    delete_query = f"DELETE FROM sensor_readings WHERE timestamp < '{cutoff_date}'"
    logging.info(f"Deleting {len(df)} migrated sensor records from PostgreSQL")
    pg_hook.run(delete_query)

    # Log to metadata catalog
    metadata_insert = f"""
        INSERT INTO data_catalog (
            file_path, data_source, record_count, size_bytes,
            min_timestamp, max_timestamp, storage_tier, created_at
        ) VALUES (
            '{s3_key}',
            'sensor_readings',
            {len(df)},
            {parquet_buffer.getbuffer().nbytes},
            '{df['timestamp'].min()}',
            '{df['timestamp'].max()}',
            'WARM',
            NOW()
        )
    """
    pg_hook.run(metadata_insert)

    logging.info(f"Successfully migrated {len(df)} sensor records")
    return {
        'records_migrated': len(df),
        's3_path': s3_key,
        'size_bytes': parquet_buffer.getbuffer().nbytes
    }


def generate_migration_report(**context):
    """
    Generate a summary report of the migration job.
    """
    ti = context['ti']

    fire_result = ti.xcom_pull(task_ids='migrate_fire_detections') or {}
    weather_result = ti.xcom_pull(task_ids='migrate_weather_data') or {}
    sensor_result = ti.xcom_pull(task_ids='migrate_sensor_data') or {}

    total_records = (
        fire_result.get('records_migrated', 0) +
        weather_result.get('records_migrated', 0) +
        sensor_result.get('records_migrated', 0)
    )

    total_bytes = (
        fire_result.get('size_bytes', 0) +
        weather_result.get('size_bytes', 0) +
        sensor_result.get('size_bytes', 0)
    )

    report = f"""
    ====== Daily Hot-to-Warm Migration Report ======
    Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

    Fire Detections:  {fire_result.get('records_migrated', 0):,} records
    Weather Data:     {weather_result.get('records_migrated', 0):,} records
    Sensor Readings:  {sensor_result.get('records_migrated', 0):,} records

    Total Migrated:   {total_records:,} records
    Total Size:       {total_bytes / 1024 / 1024:.2f} MB

    Status: ✅ SUCCESS
    ================================================
    """

    logging.info(report)
    return report


# Define task dependencies
migrate_fires_task = PythonOperator(
    task_id='migrate_fire_detections',
    python_callable=migrate_fire_detections,
    dag=dag,
)

migrate_weather_task = PythonOperator(
    task_id='migrate_weather_data',
    python_callable=migrate_weather_data,
    dag=dag,
)

migrate_sensors_task = PythonOperator(
    task_id='migrate_sensor_data',
    python_callable=migrate_sensor_data,
    dag=dag,
)

report_task = PythonOperator(
    task_id='generate_report',
    python_callable=generate_migration_report,
    dag=dag,
)

# Set task dependencies - run migrations in parallel, then generate report
[migrate_fires_task, migrate_weather_task, migrate_sensors_task] >> report_task
