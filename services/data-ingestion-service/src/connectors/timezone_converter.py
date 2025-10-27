"""
Timezone Conversion Utility for Wildfire Intelligence Platform
Centralizes all timezone conversions to Pacific Time (California)

Standard Timezone: America/Los_Angeles (Pacific Time - PST/PDT)
- PST (Pacific Standard Time): UTC-8 (November - March)
- PDT (Pacific Daylight Time): UTC-7 (March - November)

Usage:
    from .timezone_converter import utc_to_pacific, convert_to_pacific

    pacific_time = utc_to_pacific('2025-01-15T12:00:00Z')
    pacific_time = convert_to_pacific(datetime.utcnow())
"""

from datetime import datetime
from typing import Optional, Union
import pytz


class TimezoneConverter:
    """Centralized timezone conversion utility for all data sources"""

    # Pacific timezone (California)
    PACIFIC_TZ = pytz.timezone('America/Los_Angeles')
    UTC_TZ = pytz.UTC

    @staticmethod
    def utc_to_pacific(utc_time_str: Optional[str]) -> Optional[str]:
        """
        Convert UTC timestamp string to Pacific Time (PST/PDT)

        Args:
            utc_time_str: ISO format timestamp string in UTC
                         Accepted formats:
                         - '2025-01-15T12:00:00Z'
                         - '2025-01-15T12:00:00+00:00'
                         - '2025-01-15T12:00:00'
                         - '2025-01-15 12:00:00'

        Returns:
            ISO format timestamp string in Pacific Time (e.g., '2025-01-15T04:00:00-08:00')
            or None if input is None
        """
        if utc_time_str is None:
            return None

        try:
            # Handle 'Z' suffix (Zulu time = UTC)
            if utc_time_str.endswith('Z'):
                utc_time_str = utc_time_str[:-1] + '+00:00'

            # Try parsing with timezone info
            try:
                utc_dt = datetime.fromisoformat(utc_time_str.replace('Z', '+00:00'))
            except:
                # Try parsing without timezone and assume UTC
                utc_dt = datetime.fromisoformat(utc_time_str.replace(' ', 'T'))
                if utc_dt.tzinfo is None:
                    utc_dt = TimezoneConverter.UTC_TZ.localize(utc_dt)

            # Convert to Pacific Time
            pacific_dt = utc_dt.astimezone(TimezoneConverter.PACIFIC_TZ)
            return pacific_dt.isoformat()

        except Exception as e:
            raise ValueError(f"Failed to convert timestamp '{utc_time_str}' to Pacific Time: {e}")

    @staticmethod
    def datetime_to_pacific(dt: Optional[datetime]) -> Optional[datetime]:
        """
        Convert datetime object to Pacific Time

        Args:
            dt: datetime object (can be naive or timezone-aware)

        Returns:
            datetime object in Pacific Time, or None if input is None
        """
        if dt is None:
            return None

        # If naive datetime, assume UTC
        if dt.tzinfo is None:
            dt = TimezoneConverter.UTC_TZ.localize(dt)

        # Convert to Pacific Time
        return dt.astimezone(TimezoneConverter.PACIFIC_TZ)

    @staticmethod
    def datetime_to_pacific_str(dt: Optional[datetime]) -> Optional[str]:
        """
        Convert datetime object to Pacific Time ISO string

        Args:
            dt: datetime object (can be naive or timezone-aware)

        Returns:
            ISO format timestamp string in Pacific Time, or None if input is None
        """
        pacific_dt = TimezoneConverter.datetime_to_pacific(dt)
        return pacific_dt.isoformat() if pacific_dt else None

    @staticmethod
    def utcnow_pacific() -> str:
        """
        Get current time in Pacific Time as ISO string

        Returns:
            Current time in Pacific Time (ISO format)
        """
        return TimezoneConverter.datetime_to_pacific_str(datetime.utcnow())

    @staticmethod
    def convert_record_timestamps(record: dict,
                                  timestamp_fields: list = None) -> dict:
        """
        Convert all timestamp fields in a record to Pacific Time

        Args:
            record: Dictionary containing data fields
            timestamp_fields: List of field names containing timestamps
                            If None, will auto-detect fields with 'time' or 'timestamp' in name

        Returns:
            Record with all timestamp fields converted to Pacific Time
        """
        converted = record.copy()

        # Auto-detect timestamp fields if not specified
        if timestamp_fields is None:
            timestamp_fields = [
                key for key in record.keys()
                if any(t in key.lower() for t in ['time', 'timestamp', 'date', '_at'])
            ]

        # Convert each timestamp field
        for field in timestamp_fields:
            if field in converted and converted[field] is not None:
                try:
                    if isinstance(converted[field], str):
                        converted[field] = TimezoneConverter.utc_to_pacific(converted[field])
                    elif isinstance(converted[field], datetime):
                        converted[field] = TimezoneConverter.datetime_to_pacific_str(converted[field])
                except Exception as e:
                    # Log error but don't fail the conversion
                    print(f"Warning: Failed to convert field '{field}': {e}")

        return converted

    @staticmethod
    def get_timezone_offset() -> str:
        """
        Get current Pacific Time offset from UTC

        Returns:
            Timezone offset string (e.g., '-08:00' for PST, '-07:00' for PDT)
        """
        pacific_now = datetime.now(TimezoneConverter.PACIFIC_TZ)
        return pacific_now.strftime('%z')

    @staticmethod
    def is_dst() -> bool:
        """
        Check if Pacific Time is currently in Daylight Saving Time

        Returns:
            True if PDT (Daylight Saving Time), False if PST
        """
        pacific_now = datetime.now(TimezoneConverter.PACIFIC_TZ)
        return bool(pacific_now.dst())


# Convenience functions for direct imports
utc_to_pacific = TimezoneConverter.utc_to_pacific
datetime_to_pacific = TimezoneConverter.datetime_to_pacific
datetime_to_pacific_str = TimezoneConverter.datetime_to_pacific_str
utcnow_pacific = TimezoneConverter.utcnow_pacific
convert_record_timestamps = TimezoneConverter.convert_record_timestamps


# Example usage and testing
if __name__ == "__main__":
    print("=== Timezone Converter Testing ===\n")

    # String conversions
    print("UTC to Pacific Time Conversions:")
    test_times = [
        '2025-01-15T12:00:00Z',
        '2025-07-15T12:00:00Z',  # Summer (PDT)
        '2025-01-15T12:00:00+00:00',
        '2025-01-15T12:00:00',
    ]
    for utc_time in test_times:
        pacific = utc_to_pacific(utc_time)
        print(f"  {utc_time} → {pacific}")

    # datetime conversions
    print("\nDatetime Object Conversions:")
    utc_now = datetime.utcnow()
    pacific_now = datetime_to_pacific_str(utc_now)
    print(f"  UTC now: {utc_now.isoformat()}")
    print(f"  Pacific now: {pacific_now}")

    # Current time in Pacific
    print("\nCurrent Pacific Time:")
    print(f"  {utcnow_pacific()}")

    # Timezone info
    print("\nPacific Time Info:")
    print(f"  Current offset: {TimezoneConverter.get_timezone_offset()}")
    print(f"  Is DST (PDT): {TimezoneConverter.is_dst()}")

    # Batch conversion
    print("\nBatch Timestamp Conversion:")
    sample_record = {
        'timestamp': '2025-01-15T12:00:00Z',
        'created_at': '2025-01-15T10:00:00Z',
        'temperature': 25.5,
        'updated_at': datetime.utcnow()
    }
    converted = convert_record_timestamps(sample_record)
    print(f"  Original: timestamp={sample_record['timestamp']}")
    print(f"  Converted: timestamp={converted['timestamp']}")
