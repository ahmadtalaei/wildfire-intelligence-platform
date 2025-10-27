"""
Data Lifecycle Management Library

Configuration-driven lifecycle automation based on retention_policies.yaml.
This library eliminates hardcoded retention rules in DAGs and enables
policy changes without code modifications.
"""

import hashlib
import yaml
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from io import BytesIO
import logging

logger = logging.getLogger(__name__)


class RetentionPolicyManager:
    """
    Manages retention policies loaded from YAML configuration.
    """

    def __init__(self, config_path: str = "/opt/airflow/config/retention_policies.yaml"):
        """Initialize with path to retention policies YAML file."""
        self.config_path = config_path
        self.policies = self._load_policies()

    def _load_policies(self) -> Dict:
        """Load retention policies from YAML file."""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            logger.info(f"Loaded retention policies from {self.config_path}")
            return config['policies']
        except Exception as e:
            logger.error(f"Failed to load retention policies: {str(e)}")
            raise

    def get_policy(self, data_source: str, data_type: str) -> Optional[Dict]:
        """
        Get retention policy for a specific data source.

        Args:
            data_source: Top-level category (e.g., 'fire_detections')
            data_type: Specific type (e.g., 'firms_viirs_noaa20')

        Returns:
            Dictionary with retention policy or None if not found
        """
        try:
            return self.policies[data_source][data_type]
        except KeyError:
            logger.warning(f"No policy found for {data_source}.{data_type}")
            return None

    def get_tier_cutoff_date(self, policy: Dict, tier: str) -> datetime:
        """
        Calculate cutoff date for a specific tier transition.

        Args:
            policy: Retention policy dictionary
            tier: Target tier ('warm', 'cold', 'archive')

        Returns:
            Datetime cutoff for migration
        """
        tier_key = f"{tier}_tier_days"
        days = policy.get(tier_key, 7)
        return datetime.now() - timedelta(days=days)

    def should_delete(self, policy: Dict, file_metadata: Dict) -> bool:
        """
        Determine if a file should be deleted based on policy rules.

        Args:
            policy: Retention policy
            file_metadata: File metadata from catalog

        Returns:
            True if file should be deleted
        """
        deletion_rule = policy.get('deletion_rule', 'never')

        if deletion_rule == 'never':
            return False

        if deletion_rule == 'after_archive':
            # Delete only after archival period
            archive_days = policy.get('archive_tier_days', float('inf'))
            age = (datetime.now() - file_metadata['created_at']).days
            return age > archive_days

        if deletion_rule == 'conditional':
            # Check deletion criteria
            criteria = policy.get('deletion_criteria', {})
            return self._check_deletion_criteria(file_metadata, criteria)

        return False

    def _check_deletion_criteria(self, metadata: Dict, criteria: Dict) -> bool:
        """
        Check if file meets deletion criteria.

        Args:
            metadata: File metadata
            criteria: Deletion criteria from policy

        Returns:
            True if all criteria are met
        """
        # Check cloud cover threshold
        if 'cloud_cover_gt' in criteria:
            cloud_cover = metadata.get('metadata', {}).get('cloud_cover_percent', 0)
            if cloud_cover <= criteria['cloud_cover_gt']:
                return False

        # Check age threshold
        if 'age_gt_days' in criteria:
            age = (datetime.now() - metadata['created_at']).days
            if age <= criteria['age_gt_days']:
                return False

        # Check tags (e.g., don't delete fire_event tags)
        if 'not_tagged_as' in criteria:
            tags = metadata.get('metadata', {}).get('tags', [])
            if criteria['not_tagged_as'] in tags:
                return False

        return True


class DataIntegrityManager:
    """
    Manages data integrity checks: checksums, deduplication, validation.
    """

    @staticmethod
    def calculate_checksum(data: bytes) -> str:
        """
        Calculate SHA256 checksum of data.

        Args:
            data: Binary data

        Returns:
            Hexadecimal checksum string
        """
        return hashlib.sha256(data).hexdigest()

    @staticmethod
    def calculate_dataframe_checksum(df: pd.DataFrame) -> str:
        """
        Calculate checksum of DataFrame contents.

        Args:
            df: Pandas DataFrame

        Returns:
            Hexadecimal checksum string
        """
        # Convert to bytes via Parquet (deterministic)
        buffer = BytesIO()
        table = pa.Table.from_pandas(df)
        pq.write_table(table, buffer, compression='none')
        buffer.seek(0)
        return DataIntegrityManager.calculate_checksum(buffer.getvalue())

    @staticmethod
    def detect_duplicates(df: pd.DataFrame, key_fields: List[str]) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Detect duplicate records based on key fields.

        Args:
            df: DataFrame to check
            key_fields: List of column names to use as deduplication key

        Returns:
            Tuple of (unique_df, duplicate_df)
        """
        # Mark duplicates
        df['is_duplicate'] = df.duplicated(subset=key_fields, keep='first')

        unique_df = df[~df['is_duplicate']].copy()
        duplicate_df = df[df['is_duplicate']].copy()

        logger.info(f"Found {len(duplicate_df)} duplicates out of {len(df)} records")

        return unique_df, duplicate_df

    @staticmethod
    def validate_data_quality(df: pd.DataFrame, source_schema: Dict) -> Dict:
        """
        Validate DataFrame against expected schema and quality rules.

        Args:
            df: DataFrame to validate
            source_schema: Expected schema and validation rules

        Returns:
            Dictionary with quality scores and validation errors
        """
        errors = []
        total_checks = 0
        passed_checks = 0

        # Completeness: Check for missing required fields
        if 'required_fields' in source_schema:
            for field in source_schema['required_fields']:
                total_checks += 1
                if field in df.columns:
                    null_count = df[field].isnull().sum()
                    if null_count == 0:
                        passed_checks += 1
                    else:
                        errors.append(f"Field '{field}' has {null_count} null values")
                else:
                    errors.append(f"Required field '{field}' is missing")

        # Accuracy: Check value ranges
        if 'value_ranges' in source_schema:
            for field, range_spec in source_schema['value_ranges'].items():
                if field in df.columns:
                    total_checks += 1
                    min_val, max_val = range_spec
                    out_of_range = ((df[field] < min_val) | (df[field] > max_val)).sum()
                    if out_of_range == 0:
                        passed_checks += 1
                    else:
                        errors.append(f"Field '{field}' has {out_of_range} out-of-range values")

        # Calculate quality scores
        completeness_score = len(df) / (len(df) + df.isnull().sum().sum()) if len(df) > 0 else 0
        accuracy_score = passed_checks / total_checks if total_checks > 0 else 1.0
        overall_quality = (completeness_score + accuracy_score) / 2

        return {
            'quality_score': overall_quality,
            'completeness_score': completeness_score,
            'accuracy_score': accuracy_score,
            'validation_errors': errors,
            'total_checks': total_checks,
            'passed_checks': passed_checks
        }


class PartitionManager:
    """
    Manages date-based partitioning for Parquet files.
    """

    @staticmethod
    def generate_partition_path(base_path: str, partition_date: datetime, data_source: str) -> str:
        """
        Generate partitioned path with date-based structure.

        Args:
            base_path: Base S3/MinIO path (e.g., 'fires/viirs')
            partition_date: Date for partitioning
            data_source: Data source identifier

        Returns:
            Full partitioned path (e.g., 'fires/viirs/year=2025/month=10/day=08/viirs_20251008.parquet')
        """
        year = partition_date.year
        month = partition_date.month
        day = partition_date.day

        filename = f"{data_source}_{partition_date.strftime('%Y%m%d')}.parquet"
        partition_path = f"{base_path}/year={year}/month={month:02d}/day={day:02d}/{filename}"

        return partition_path

    @staticmethod
    def extract_partition_date(file_path: str) -> Optional[datetime]:
        """
        Extract partition date from file path.

        Args:
            file_path: Partitioned file path

        Returns:
            Extracted datetime or None if not partitioned
        """
        try:
            # Parse Hive-style partitions: /year=2025/month=10/day=08/
            parts = Path(file_path).parts
            year = month = day = None

            for part in parts:
                if part.startswith('year='):
                    year = int(part.split('=')[1])
                elif part.startswith('month='):
                    month = int(part.split('=')[1])
                elif part.startswith('day='):
                    day = int(part.split('=')[1])

            if year and month and day:
                return datetime(year, month, day)

            return None
        except Exception as e:
            logger.warning(f"Failed to extract partition date from {file_path}: {str(e)}")
            return None


class IncrementalProcessor:
    """
    Handles incremental/batch processing to avoid large migrations in one job.
    """

    @staticmethod
    def get_batches(total_count: int, batch_size: int = 10000) -> List[Tuple[int, int]]:
        """
        Generate batch ranges for incremental processing.

        Args:
            total_count: Total number of records
            batch_size: Records per batch

        Returns:
            List of (offset, limit) tuples
        """
        batches = []
        for offset in range(0, total_count, batch_size):
            limit = min(batch_size, total_count - offset)
            batches.append((offset, limit))

        logger.info(f"Generated {len(batches)} batches for {total_count} records (batch_size={batch_size})")
        return batches

    @staticmethod
    def should_process_batch(batch_num: int, total_batches: int, max_duration_minutes: int = 30) -> bool:
        """
        Determine if batch should be processed based on time constraints.

        Args:
            batch_num: Current batch number
            total_batches: Total number of batches
            max_duration_minutes: Maximum allowed processing time

        Returns:
            True if batch should be processed
        """
        # Estimate time per batch (assuming linear scaling)
        estimated_time = (batch_num + 1) * (max_duration_minutes / total_batches)

        if estimated_time > max_duration_minutes:
            logger.warning(f"Skipping batch {batch_num} - would exceed time limit")
            return False

        return True


# Utility functions for DAGs
def load_retention_config() -> RetentionPolicyManager:
    """Load retention policy manager (convenience function for DAGs)."""
    return RetentionPolicyManager()


def calculate_checksum_for_df(df: pd.DataFrame) -> str:
    """Calculate checksum for DataFrame (convenience function for DAGs)."""
    return DataIntegrityManager.calculate_dataframe_checksum(df)


def detect_and_remove_duplicates(df: pd.DataFrame, key_fields: List[str]) -> pd.DataFrame:
    """Detect and remove duplicates (convenience function for DAGs)."""
    unique_df, duplicate_df = DataIntegrityManager.detect_duplicates(df, key_fields)

    if len(duplicate_df) > 0:
        logger.warning(f"Removed {len(duplicate_df)} duplicate records")

    return unique_df


def generate_partitioned_path(data_source: str, partition_date: datetime) -> str:
    """Generate partitioned S3 path (convenience function for DAGs)."""
    # Map data source to base path
    base_paths = {
        'firms_viirs_noaa20': 'fires/viirs',
        'firms_viirs_snpp': 'fires/viirs',
        'firms_modis_terra': 'fires/modis',
        'era5_reanalysis': 'weather/era5',
        'era5_land_reanalysis': 'weather/era5-land',
        'gfs_forecasts': 'weather/gfs',
        'nam_forecasts': 'weather/nam',
        'sensor_readings': 'sensors/iot',
    }

    base_path = base_paths.get(data_source, f'data/{data_source}')
    return PartitionManager.generate_partition_path(base_path, partition_date, data_source)
