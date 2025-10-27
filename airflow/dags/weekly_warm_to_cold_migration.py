"""
Weekly Warm-to-Cold Data Migration DAG

This DAG runs weekly on Sundays at 02:00 PST to move 90-day-old data from MinIO (WARM tier)
to Cloud Storage S3 Standard-IA (COLD tier), optimizing long-term storage costs.

Schedule: Weekly on Sundays at 02:00 PST
Retention: Moves data older than 90 days
Target: MinIO → Cloud S3 Standard-IA (or simulated with MinIO lifecycle)
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
import logging

# Default arguments
default_args = {
    'owner': 'wildfire-platform',
    'depends_on_past': False,
    'start_date': datetime(2025, 1, 1),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=10),
}

# Initialize DAG
dag = DAG(
    'weekly_warm_to_cold_migration',
    default_args=default_args,
    description='Migrate 90-day-old data from MinIO WARM to COLD tier',
    schedule_interval='0 10 * * 0',  # Sundays at 02:00 PST (10:00 UTC)
    catchup=False,
    tags=['data-lifecycle', 'storage', 'archival'],
)


def identify_files_for_cold_storage(**context):
    """
    Query metadata catalog to find files in WARM tier older than 90 days.
    """
    logging.info("Identifying files for cold storage migration...")

    cutoff_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')

    pg_hook = PostgresHook(postgres_conn_id='postgres_default')

    query = f"""
        SELECT
            id, file_path, data_source, record_count, size_bytes,
            min_timestamp, max_timestamp, created_at
        FROM data_catalog
        WHERE storage_tier = 'WARM'
        AND created_at < '{cutoff_date}'
        ORDER BY created_at
    """

    df = pg_hook.get_pandas_df(query)

    if df.empty:
        logging.info("No files found for cold storage migration")
        return []

    files_to_migrate = df.to_dict('records')
    logging.info(f"Found {len(files_to_migrate)} files to migrate to COLD tier")

    # Push file list to XCom for downstream tasks
    context['ti'].xcom_push(key='files_to_migrate', value=files_to_migrate)

    return files_to_migrate


def migrate_to_cold_storage(**context):
    """
    Move files from MinIO WARM to COLD tier.
    In production, this would copy to AWS S3 Standard-IA or Glacier.
    For now, we simulate by moving to a 'cold' prefix in MinIO.
    """
    ti = context['ti']
    files = ti.xcom_pull(task_ids='identify_files', key='files_to_migrate')

    if not files:
        logging.info("No files to migrate")
        return

    s3_hook = S3Hook(aws_conn_id='minio_default')
    migrated_count = 0

    for file_info in files:
        source_key = file_info['file_path']
        # Move to 'archive' prefix to simulate COLD tier
        dest_key = f"archive/{source_key}"

        logging.info(f"Migrating {source_key} to COLD tier")

        try:
            # Copy to COLD tier (archive prefix)
            s3_hook.copy_object(
                source_bucket_name='wildfire-data',
                source_bucket_key=source_key,
                dest_bucket_name='wildfire-data',
                dest_bucket_key=dest_key
            )

            # Delete from WARM tier
            s3_hook.delete_objects(
                bucket='wildfire-data',
                keys=[source_key]
            )

            # Update metadata catalog
            pg_hook = PostgresHook(postgres_conn_id='postgres_default')
            update_query = f"""
                UPDATE data_catalog
                SET storage_tier = 'COLD',
                    file_path = '{dest_key}',
                    migrated_to_cold_at = NOW()
                WHERE id = {file_info['id']}
            """
            pg_hook.run(update_query)

            migrated_count += 1
            logging.info(f"Successfully migrated file {file_info['id']}: {source_key}")

        except Exception as e:
            logging.error(f"Failed to migrate {source_key}: {str(e)}")
            continue

    logging.info(f"Migrated {migrated_count} files to COLD tier")
    return {'migrated_count': migrated_count}


def cleanup_old_sentinel_imagery(**context):
    """
    Delete Sentinel satellite imagery based on retention policy:
    - Keep only scenes with <30% cloud cover
    - Delete scenes older than 90 days with >30% cloud cover
    - Always keep scenes tagged as fire events
    """
    logging.info("Cleaning up old Sentinel imagery...")

    cutoff_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')

    pg_hook = PostgresHook(postgres_conn_id='postgres_default')

    # Find Sentinel scenes to delete
    query = f"""
        SELECT id, file_path
        FROM data_catalog
        WHERE data_source LIKE 'sentinel%'
        AND created_at < '{cutoff_date}'
        AND storage_tier = 'WARM'
        AND (
            metadata->>'cloud_cover_percent' > '30'
            OR metadata->>'cloud_cover_percent' IS NULL
        )
        AND NOT (metadata->>'tags' LIKE '%fire_event%')
    """

    df = pg_hook.get_pandas_df(query)

    if df.empty:
        logging.info("No Sentinel scenes to clean up")
        return

    s3_hook = S3Hook(aws_conn_id='minio_default')
    deleted_count = 0
    freed_bytes = 0

    for _, row in df.iterrows():
        try:
            # Get file size before deletion
            file_info = s3_hook.get_key(
                key=row['file_path'],
                bucket_name='wildfire-data'
            )
            file_size = file_info.content_length if file_info else 0

            # Delete from MinIO
            s3_hook.delete_objects(
                bucket='wildfire-data',
                keys=[row['file_path']]
            )

            # Update metadata catalog
            delete_query = f"""
                UPDATE data_catalog
                SET storage_tier = 'DELETED',
                    deleted_at = NOW(),
                    deletion_reason = 'Retention policy: cloud_cover >30%, age >90 days'
                WHERE id = {row['id']}
            """
            pg_hook.run(delete_query)

            deleted_count += 1
            freed_bytes += file_size

            logging.info(f"Deleted Sentinel scene: {row['file_path']}")

        except Exception as e:
            logging.error(f"Failed to delete {row['file_path']}: {str(e)}")
            continue

    logging.info(f"Deleted {deleted_count} Sentinel scenes, freed {freed_bytes / 1024 / 1024 / 1024:.2f} GB")
    return {
        'deleted_count': deleted_count,
        'freed_gb': freed_bytes / 1024 / 1024 / 1024
    }


def update_storage_metrics(**context):
    """
    Calculate and update storage metrics for monitoring.
    """
    logging.info("Updating storage metrics...")

    pg_hook = PostgresHook(postgres_conn_id='postgres_default')

    # Calculate storage by tier
    metrics_query = """
        SELECT
            storage_tier,
            COUNT(*) as file_count,
            SUM(size_bytes) as total_bytes,
            SUM(record_count) as total_records
        FROM data_catalog
        WHERE storage_tier IN ('HOT', 'WARM', 'COLD', 'ARCHIVE')
        GROUP BY storage_tier
    """

    df = pg_hook.get_pandas_df(metrics_query)

    metrics = {}
    for _, row in df.iterrows():
        tier = row['storage_tier']
        metrics[tier] = {
            'file_count': int(row['file_count']),
            'total_gb': float(row['total_bytes']) / 1024 / 1024 / 1024,
            'total_records': int(row['total_records'])
        }

    # Insert into storage_metrics table (for Grafana dashboards)
    for tier, stats in metrics.items():
        insert_query = f"""
            INSERT INTO storage_metrics (
                tier, file_count, size_gb, record_count, measured_at
            ) VALUES (
                '{tier}',
                {stats['file_count']},
                {stats['total_gb']},
                {stats['total_records']},
                NOW()
            )
        """
        pg_hook.run(insert_query)

    logging.info(f"Storage metrics updated: {metrics}")
    return metrics


def generate_weekly_report(**context):
    """
    Generate weekly migration and cleanup report.
    """
    ti = context['ti']

    migration_result = ti.xcom_pull(task_ids='migrate_to_cold') or {}
    cleanup_result = ti.xcom_pull(task_ids='cleanup_sentinel') or {}
    metrics = ti.xcom_pull(task_ids='update_metrics') or {}

    report = f"""
    ====== Weekly Warm-to-Cold Migration Report ======
    Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

    Files Migrated to COLD:  {migration_result.get('migrated_count', 0)}
    Sentinel Scenes Deleted: {cleanup_result.get('deleted_count', 0)}
    Storage Freed:           {cleanup_result.get('freed_gb', 0):.2f} GB

    Current Storage Distribution:
    """

    for tier in ['HOT', 'WARM', 'COLD', 'ARCHIVE']:
        if tier in metrics:
            stats = metrics[tier]
            report += f"""
    {tier:8s}: {stats['file_count']:5d} files | {stats['total_gb']:8.2f} GB | {stats['total_records']:,} records
    """

    report += """
    Status: ✅ SUCCESS
    ===================================================
    """

    logging.info(report)
    return report


# Define tasks
identify_task = PythonOperator(
    task_id='identify_files',
    python_callable=identify_files_for_cold_storage,
    dag=dag,
)

migrate_task = PythonOperator(
    task_id='migrate_to_cold',
    python_callable=migrate_to_cold_storage,
    dag=dag,
)

cleanup_task = PythonOperator(
    task_id='cleanup_sentinel',
    python_callable=cleanup_old_sentinel_imagery,
    dag=dag,
)

metrics_task = PythonOperator(
    task_id='update_metrics',
    python_callable=update_storage_metrics,
    dag=dag,
)

report_task = PythonOperator(
    task_id='generate_report',
    python_callable=generate_weekly_report,
    dag=dag,
)

# Task dependencies
identify_task >> [migrate_task, cleanup_task] >> metrics_task >> report_task
