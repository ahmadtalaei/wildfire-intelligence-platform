"""
Vectorized Data Validation System
Validates and filters data before Kafka ingestion using pandas for performance
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Tuple
import structlog

logger = structlog.get_logger()


class VectorizedDataValidator:
    """
    High-performance data validator using pandas vectorization
    Filters invalid records at the stem before Kafka ingestion
    """

    # Required fields per source type
    REQUIRED_FIELDS = {
        'noaa_stations_current': ['latitude', 'longitude', 'timestamp'],
        'noaa_stations_historical': ['latitude', 'longitude', 'timestamp'],
        'noaa_alerts_active': ['event', 'timestamp'],  # event must not be empty!
        'firms_viirs_snpp': ['latitude', 'longitude', 'timestamp', 'confidence'],
        'firms_viirs_noaa20': ['latitude', 'longitude', 'timestamp', 'confidence'],
        'firms_viirs_noaa21': ['latitude', 'longitude', 'timestamp', 'confidence'],
        'firms_modis_terra': ['latitude', 'longitude', 'timestamp', 'confidence'],
        'firms_modis_aqua': ['latitude', 'longitude', 'timestamp', 'confidence'],
        'landsat_nrt': ['latitude', 'longitude', 'timestamp', 'confidence'],
        'iot_weather_stations': ['latitude', 'longitude', 'timestamp'],
        'purpleair_california': ['latitude', 'longitude', 'timestamp'],
        'airnow': ['latitude', 'longitude', 'timestamp'],
    }

    # Fields that must not be empty strings (for string fields)
    NON_EMPTY_STRING_FIELDS = {
        'noaa_alerts_active': ['event', 'severity'],  # Critical: event cannot be empty!
        'noaa_stations_current': ['station_id'],
        'firms_viirs_snpp': ['satellite'],
        'firms_viirs_noaa20': ['satellite'],
        'firms_viirs_noaa21': ['satellite'],
        'firms_modis_terra': ['satellite'],
        'firms_modis_aqua': ['satellite'],
        'landsat_nrt': ['satellite'],
    }

    # Numeric range validations
    NUMERIC_RANGES = {
        'latitude': (-90, 90),
        'longitude': (-180, 180),
        'confidence': (0, 1.0),  # FIRMS confidence is 0-1
        'temperature_celsius': (-100, 70),  # Reasonable Earth temperatures
        'wind_speed_ms': (0, 150),  # Max wind speed
        'humidity_percent': (0, 100),
    }

    @classmethod
    def validate_and_split(cls, data: List[Dict[str, Any]],
                          source_id_field: str = 'source_id') -> Tuple[Dict[str, List[Dict]], List[Dict]]:
        """
        Vectorized validation and splitting by source_id

        Args:
            data: List of records to validate
            source_id_field: Field name containing source identifier

        Returns:
            Tuple of (valid_data_by_source, invalid_records)
            - valid_data_by_source: Dict[source_id -> List[valid_records]]
            - invalid_records: List of records that failed validation
        """
        if not data:
            return {}, []

        # Convert to DataFrame for vectorized operations
        df = pd.DataFrame(data)

        if source_id_field not in df.columns:
            logger.error(f"Missing {source_id_field} field in data")
            return {}, data

        # Track validation results
        valid_mask = pd.Series([True] * len(df))
        invalid_reasons = [''] * len(df)

        # Group by source_id for source-specific validation
        grouped = df.groupby(source_id_field)
        valid_data_by_source = {}

        for source_id, group_df in grouped:
            group_valid_mask = pd.Series([True] * len(group_df))
            group_invalid_reasons = [''] * len(group_df)

            # 1. Required field validation (vectorized NULL check)
            required_fields = cls.REQUIRED_FIELDS.get(source_id, [])
            for field in required_fields:
                if field in group_df.columns:
                    # Check for NULL/None values
                    null_mask = group_df[field].isna()
                    if null_mask.any():
                        group_valid_mask &= ~null_mask
                        group_invalid_reasons = [
                            f"{reason}; Missing {field}" if null_mask.iloc[i] else reason
                            for i, reason in enumerate(group_invalid_reasons)
                        ]
                else:
                    # Field missing entirely
                    group_valid_mask = pd.Series([False] * len(group_df))
                    group_invalid_reasons = [f"Missing required field: {field}"] * len(group_df)

            # 2. Non-empty string validation (vectorized string check)
            non_empty_fields = cls.NON_EMPTY_STRING_FIELDS.get(source_id, [])
            for field in non_empty_fields:
                if field in group_df.columns:
                    # Check for empty strings (vectorized)
                    empty_mask = group_df[field].astype(str).str.strip() == ''
                    if empty_mask.any():
                        group_valid_mask &= ~empty_mask
                        group_invalid_reasons = [
                            f"{reason}; Empty {field}" if empty_mask.iloc[i] else reason
                            for i, reason in enumerate(group_invalid_reasons)
                        ]

            # 3. Numeric range validation (vectorized comparison)
            for field, (min_val, max_val) in cls.NUMERIC_RANGES.items():
                if field in group_df.columns:
                    # Vectorized range check
                    numeric_values = pd.to_numeric(group_df[field], errors='coerce')
                    out_of_range = (numeric_values < min_val) | (numeric_values > max_val)
                    # Don't flag NaN as out of range (already caught by required fields)
                    out_of_range = out_of_range & ~numeric_values.isna()

                    if out_of_range.any():
                        group_valid_mask &= ~out_of_range
                        group_invalid_reasons = [
                            f"{reason}; {field} out of range ({min_val}-{max_val})" if out_of_range.iloc[i] else reason
                            for i, reason in enumerate(group_invalid_reasons)
                        ]

            # 4. California geographic boundary check (for wildfire relevance)
            if 'latitude' in group_df.columns and 'longitude' in group_df.columns:
                # California approximate bounds: 32.5°N to 42°N, -124.5°W to -114°W
                ca_lat_mask = (group_df['latitude'] >= 32.0) & (group_df['latitude'] <= 42.5)
                ca_lon_mask = (group_df['longitude'] >= -125.0) & (group_df['longitude'] <= -114.0)

                # Allow data slightly outside CA (neighboring states matter for fires)
                # Only flag as warning if WAY outside CA
                far_outside = ~(ca_lat_mask | ca_lon_mask)
                if far_outside.any():
                    logger.debug(f"{far_outside.sum()} records outside California bounds for {source_id}")

            # Separate valid and invalid records
            valid_records = group_df[group_valid_mask].to_dict('records')
            invalid_records_group = group_df[~group_valid_mask].to_dict('records')

            # Add invalid reasons to invalid records
            invalid_idx = 0
            for i, is_valid in enumerate(group_valid_mask):
                if not is_valid:
                    if invalid_idx < len(invalid_records_group):
                        invalid_records_group[invalid_idx]['_validation_error'] = group_invalid_reasons[i]
                        invalid_idx += 1

            # Store valid records by source_id
            if valid_records:
                valid_data_by_source[source_id] = valid_records

            # Log validation summary
            if len(invalid_records_group) > 0:
                logger.warning(
                    f"Filtered {len(invalid_records_group)}/{len(group_df)} invalid records",
                    source_id=source_id,
                    sample_errors=group_invalid_reasons[:3] if group_invalid_reasons else []
                )

        # Collect all invalid records across sources
        all_invalid = []
        for source_id, group_df in grouped:
            group_valid_mask = valid_mask[group_df.index]
            invalid_records_group = group_df[~group_valid_mask].to_dict('records')
            all_invalid.extend(invalid_records_group)

        logger.info(
            f"Validation complete: {len(data) - len(all_invalid)}/{len(data)} records valid",
            valid_sources=list(valid_data_by_source.keys()),
            invalid_count=len(all_invalid)
        )

        return valid_data_by_source, all_invalid

    @classmethod
    def quick_validate(cls, data: List[Dict[str, Any]], source_id: str) -> Tuple[List[Dict], List[Dict]]:
        """
        Quick validation for single-source data (no grouping needed)

        Returns:
            Tuple of (valid_records, invalid_records)
        """
        valid_by_source, invalid = cls.validate_and_split(data, source_id_field='source_id')
        valid = valid_by_source.get(source_id, [])
        return valid, invalid

    @classmethod
    def validate_single_record(cls, record: Dict[str, Any], source_id: str) -> Tuple[bool, str]:
        """
        Validate a single record (non-vectorized, for streaming)

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Required fields check
        required_fields = cls.REQUIRED_FIELDS.get(source_id, [])
        for field in required_fields:
            if field not in record or record[field] is None:
                return False, f"Missing required field: {field}"

        # Non-empty string check
        non_empty_fields = cls.NON_EMPTY_STRING_FIELDS.get(source_id, [])
        for field in non_empty_fields:
            if field in record:
                value = str(record[field]).strip()
                if not value or value == '' or value == 'None':
                    return False, f"Empty string field: {field}"

        # Numeric range check
        for field, (min_val, max_val) in cls.NUMERIC_RANGES.items():
            if field in record and record[field] is not None:
                try:
                    value = float(record[field])
                    if value < min_val or value > max_val:
                        return False, f"{field} out of range: {value} not in [{min_val}, {max_val}]"
                except (ValueError, TypeError):
                    pass  # Non-numeric value, skip range check

        return True, ""
