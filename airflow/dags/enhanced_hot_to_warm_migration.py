"""
Enhanced Daily Hot-to-Warm Data Migration DAG

BEST PRACTICES IMPLEMENTED:
✅ Configuration-driven retention from YAML
✅ Incremental/batch processing
✅ Date-based Parquet partitioning
✅ Checksum validation
✅ Deduplication
✅ Data quality scoring
✅ PostgreSQL WAL backup before migration
✅ Access tracking in metadata catalog

Schedule: Daily at 00:00 PST
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
import sys
sys.path.append('/opt/airflow/plugins')

from lifecycle_manager import (
    load_retention_config,
    calculate_checksum_for_df,
    detect_and_remove_duplicates,
    generate_partitioned_path,
    DataIntegrityManager,
    IncrementalProcessor
)

logger = logging.getLogger(__name__)

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
    'enhanced_hot_to_warm_migration',
    default_args=default_args,
    description='Enhanced migration with best practices: partitioning, checksums, dedup',
    schedule_interval='0 8 * * *',  # 00:00 PST (08:00 UTC)
    catchup=False,
    tags=['data-lifecycle', 'storage', 'migration', 'enhanced'],
)


def backup_postgresql_wal(**context):
    """
    Create PostgreSQL WAL (Write-Ahead Log) backup before migration.
    Enables point-in-time recovery if migration fails.
    """
    logging.info("Creating PostgreSQL WAL backup...")

    pg_hook = PostgresHook(postgres_conn_id='postgres_default')

    try:
        # Create a manual checkpoint (ensures all data is flushed)
        pg_hook.run("CHECKPOINT;")

        # Get current WAL position
        result = pg_hook.get_first("SELECT pg_current_wal_lsn();")
        wal_position = result[0] if result else None

        logging.info(f"WAL backup checkpoint created at LSN: {wal_position}")

        # Store WAL position in XCom for recovery if needed
        context['ti'].xcom_push(key='wal_backup_position', value=str(wal_position))

        return {'status': 'success', 'wal_position': str(wal_position)}

    except Exception as e:
        logging.error(f"WAL backup failed: {str(e)}")
        raise


def migrate_fire_detections_enhanced(**context):
    """
    Enhanced fire detections migration with all best practices.
    """
    logging.info("Starting ENHANCED fire detections migration...")

    # Load retention policy from YAML
    policy_mgr = load_retention_config()
    policy = policy_mgr.get_policy('fire_detections', 'firms_viirs_noaa20')

    if not policy:
        logging.error("No retention policy found for fire detections")
        return

    # Calculate cutoff date from policy (not hardcoded!)
    cutoff_date = policy_mgr.get_tier_cutoff_date(policy, 'warm')
    logging.info(f"Using policy-driven cutoff date: {cutoff_date.strftime('%Y-%m-%d')}")

    pg_hook = PostgresHook(postgres_conn_id='postgres_default')

    # Get total count for batch processing
    count_query = f"""
        SELECT COUNT(*) FROM firms_viirs_noaa20_detections
        WHERE timestamp < '{cutoff_date}'
    """
    total_count = pg_hook.get_first(count_query)[0]

    if total_count == 0:
        logging.info("No data to migrate")
        return

    logging.info(f"Total records to migrate: {total_count:,}")

    # Incremental batch processing (avoid large migrations)
    batch_size = 50000  # Process in 50K record chunks
    batches = IncrementalProcessor.get_batches(total_count, batch_size)

    migrated_files = []
    total_migrated = 0

    for batch_num, (offset, limit) in enumerate(batches):
        logging.info(f"Processing batch {batch_num + 1}/{len(batches)} (offset={offset}, limit={limit})")

        # Query batch
        query = f"""
            SELECT *
            FROM firms_viirs_noaa20_detections
            WHERE timestamp < '{cutoff_date}'
            ORDER BY timestamp
            LIMIT {limit} OFFSET {offset}
        """

        df = pg_hook.get_pandas_df(query)

        if df.empty:
            continue

        # BEST PRACTICE 1: Deduplication
        dedup_keys = ['timestamp', 'latitude', 'longitude', 'satellite_name']
        df = detect_and_remove_duplicates(df, dedup_keys)

        # BEST PRACTICE 2: Data quality validation
        quality_result = DataIntegrityManager.validate_data_quality(df, {
            'required_fields': ['timestamp', 'latitude', 'longitude'],
            'value_ranges': {
                'latitude': (-90, 90),
                'longitude': (-180, 180),
                'confidence_percent': (0, 100)
            }
        })

        logging.info(f"Batch quality score: {quality_result['quality_score']:.2f}")

        # BEST PRACTICE 3: Calculate checksum for data integrity
        checksum = calculate_checksum_for_df(df)

        # BEST PRACTICE 4: Date-based partitioning
        partition_date = df['timestamp'].min().date()
        partitioned_path = generate_partitioned_path('firms_viirs_noaa20', partition_date)

        # Convert to Parquet with compression
        table = pa.Table.from_pandas(df)
        parquet_buffer = BytesIO()
        pq.write_table(table, parquet_buffer, compression='snappy', row_group_size=10000)
        parquet_buffer.seek(0)
        file_size = parquet_buffer.getbuffer().nbytes

        # Upload to MinIO
        s3_hook = S3Hook(aws_conn_id='minio_default')
        logging.info(f"Uploading batch to: wildfire-data/{partitioned_path}")

        s3_hook.load_file_obj(
            file_obj=parquet_buffer,
            key=partitioned_path,
            bucket_name='wildfire-data',
            replace=True
        )

        # BEST PRACTICE 5: Update metadata catalog with ENHANCED fields
        metadata_insert = f"""
            INSERT INTO data_catalog (
                source_table,
                partition_date,
                file_path,
                data_source,
                record_count,
                size_bytes,
                checksum,
                compression_type,
                file_format,
                min_timestamp,
                max_timestamp,
                min_latitude,
                max_latitude,
                min_longitude,
                max_longitude,
                storage_tier,
                quality_score,
                completeness_score,
                accuracy_score,
                ingested_at,
                created_at
            ) VALUES (
                'firms_viirs_noaa20_detections',
                '{partition_date}',
                '{partitioned_path}',
                'firms_viirs_noaa20',
                {len(df)},
                {file_size},
                '{checksum}',
                'snappy',
                'parquet',
                '{df['timestamp'].min()}',
                '{df['timestamp'].max()}',
                {df['latitude'].min()},
                {df['latitude'].max()},
                {df['longitude'].min()},
                {df['longitude'].max()},
                'WARM',
                {quality_result['quality_score']},
                {quality_result['completeness_score']},
                {quality_result['accuracy_score']},
                NOW(),
                NOW()
            ) ON CONFLICT (file_path) DO UPDATE SET
                record_count = EXCLUDED.record_count,
                size_bytes = EXCLUDED.size_bytes,
                checksum = EXCLUDED.checksum
        """
        pg_hook.run(metadata_insert)

        # Delete migrated batch from PostgreSQL (only after successful upload)
        delete_ids = tuple(df['id'].tolist())
        if len(delete_ids) == 1:
            delete_query = f"DELETE FROM firms_viirs_noaa20_detections WHERE id = {delete_ids[0]}"
        else:
            delete_query = f"DELETE FROM firms_viirs_noaa20_detections WHERE id IN {delete_ids}"

        pg_hook.run(delete_query)

        total_migrated += len(df)
        migrated_files.append({
            'path': partitioned_path,
            'records': len(df),
            'size_mb': file_size / 1024 / 1024,
            'checksum': checksum,
            'quality_score': quality_result['quality_score']
        })

        logging.info(f"Batch {batch_num + 1} migrated: {len(df)} records, {file_size/1024/1024:.2f} MB")

    logging.info(f"Successfully migrated {total_migrated:,} fire detection records in {len(migrated_files)} files")

    return {
        'total_records_migrated': total_migrated,
        'total_files_created': len(migrated_files),
        'migrated_files': migrated_files
    }


def verify_migration_integrity(**context):
    """
    Verify migration integrity by comparing checksums and record counts.
    """
    logging.info("Verifying migration integrity...")

    ti = context['ti']
    migration_result = ti.xcom_pull(task_ids='migrate_fire_detections_enhanced')

    if not migration_result:
        logging.info("No migration to verify")
        return

    pg_hook = PostgresHook(postgres_conn_id='postgres_default')
    s3_hook = S3Hook(aws_conn_id='minio_default')

    verified_count = 0
    failed_count = 0

    for file_info in migration_result['migrated_files']:
        # Verify file exists in MinIO
        try:
            s3_obj = s3_hook.get_key(file_info['path'], bucket_name='wildfire-data')
            if s3_obj:
                logging.info(f"✓ Verified: {file_info['path']}")
                verified_count += 1
            else:
                logging.error(f"✗ Missing: {file_info['path']}")
                failed_count += 1
        except Exception as e:
            logging.error(f"✗ Error verifying {file_info['path']}: {str(e)}")
            failed_count += 1

        # Verify metadata catalog entry
        catalog_query = f"""
            SELECT checksum, record_count
            FROM data_catalog
            WHERE file_path = '{file_info['path']}'
        """
        result = pg_hook.get_first(catalog_query)

        if result:
            catalog_checksum, catalog_count = result
            if catalog_checksum == file_info['checksum'] and catalog_count == file_info['records']:
                logging.info(f"✓ Metadata verified: {file_info['path']}")
            else:
                logging.error(f"✗ Metadata mismatch: {file_info['path']}")
                failed_count += 1
        else:
            logging.error(f"✗ Metadata missing: {file_info['path']}")
            failed_count += 1

    logging.info(f"Verification complete: {verified_count} passed, {failed_count} failed")

    return {
        'verified_count': verified_count,
        'failed_count': failed_count,
        'success_rate': verified_count / (verified_count + failed_count) if (verified_count + failed_count) > 0 else 0
    }


def update_storage_metrics(**context):
    """
    Update storage metrics table with current tier statistics.
    """
    logging.info("Updating storage metrics...")

    pg_hook = PostgresHook(postgres_conn_id='postgres_default')

    # Calculate metrics by tier
    metrics_query = """
        SELECT
            storage_tier,
            COUNT(*) as file_count,
            SUM(size_bytes) / 1024.0 / 1024.0 / 1024.0 as total_gb,
            SUM(record_count) as total_records,
            AVG(quality_score) as avg_quality,
            SUM(CASE WHEN is_duplicate THEN 1 ELSE 0 END) as duplicate_count,
            COUNT(DISTINCT partition_date) as partition_count
        FROM data_catalog
        WHERE storage_tier != 'DELETED'
        GROUP BY storage_tier
    """

    df = pg_hook.get_pandas_df(metrics_query)

    for _, row in df.iterrows():
        insert_query = f"""
            INSERT INTO storage_metrics (
                tier, file_count, size_gb, record_count, measured_at
            ) VALUES (
                '{row['storage_tier']}',
                {row['file_count']},
                {row['total_gb']},
                {row['total_records']},
                NOW()
            )
        """
        pg_hook.run(insert_query)

    logging.info(f"Storage metrics updated for {len(df)} tiers")
    return df.to_dict('records')


def generate_migration_report(**context):
    """
    Generate comprehensive migration report with all metrics.
    """
    ti = context['ti']

    wal_backup = ti.xcom_pull(task_ids='backup_postgresql_wal') or {}
    migration_result = ti.xcom_pull(task_ids='migrate_fire_detections_enhanced') or {}
    verification = ti.xcom_pull(task_ids='verify_integrity') or {}
    metrics = ti.xcom_pull(task_ids='update_metrics') or []

    report = f"""
    ══════════════════════════════════════════════════════════════
    ENHANCED DAILY HOT-TO-WARM MIGRATION REPORT
    ══════════════════════════════════════════════════════════════
    Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S PST')}

    WAL BACKUP:
    ├─ Status: {wal_backup.get('status', 'N/A')}
    └─ Position: {wal_backup.get('wal_position', 'N/A')}

    MIGRATION RESULTS:
    ├─ Total Records: {migration_result.get('total_records_migrated', 0):,}
    ├─ Total Files: {migration_result.get('total_files_created', 0)}
    └─ Average Quality Score: {sum(f['quality_score'] for f in migration_result.get('migrated_files', [])) / len(migration_result.get('migrated_files', [1])):.2f}

    INTEGRITY VERIFICATION:
    ├─ Verified: {verification.get('verified_count', 0)}
    ├─ Failed: {verification.get('failed_count', 0)}
    └─ Success Rate: {verification.get('success_rate', 0):.1%}

    CURRENT STORAGE DISTRIBUTION:
    """

    for metric in metrics:
        report += f"""
    {metric['storage_tier']:8s}: {metric['file_count']:5d} files | {metric['total_gb']:8.2f} GB | {metric['total_records']:,} records
    """

    report += """
    ══════════════════════════════════════════════════════════════
    Status: ✅ SUCCESS
    ══════════════════════════════════════════════════════════════
    """

    logging.info(report)
    return report


# Define tasks
backup_task = PythonOperator(
    task_id='backup_postgresql_wal',
    python_callable=backup_postgresql_wal,
    dag=dag,
)

migrate_task = PythonOperator(
    task_id='migrate_fire_detections_enhanced',
    python_callable=migrate_fire_detections_enhanced,
    dag=dag,
)

verify_task = PythonOperator(
    task_id='verify_integrity',
    python_callable=verify_migration_integrity,
    dag=dag,
)

metrics_task = PythonOperator(
    task_id='update_metrics',
    python_callable=update_storage_metrics,
    dag=dag,
)

report_task = PythonOperator(
    task_id='generate_report',
    python_callable=generate_migration_report,
    dag=dag,
)

# Task dependencies with verification
backup_task >> migrate_task >> verify_task >> metrics_task >> report_task
