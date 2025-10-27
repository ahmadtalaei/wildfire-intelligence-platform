"""
Unit Conversion Utility for Wildfire Intelligence Platform
Centralizes all unit conversions to SI (International System) standards

SI Standards Applied:
- Temperature: Celsius (°C)
- Pressure: Pascals (Pa)
- Wind Speed: meters per second (m/s)
- Distance: meters (m)
- Precipitation: millimeters (mm)

Usage:
    from .unit_converter import convert_temperature, convert_pressure, convert_wind_speed

    temp_celsius = convert_temperature(75, from_unit='F')
    pressure_pa = convert_pressure(1013.25, from_unit='hPa')
    wind_ms = convert_wind_speed(10, from_unit='mph')
"""

from typing import Optional, Union


class UnitConverter:
    """Centralized unit conversion utility for all data sources"""

    # ==================== Temperature Conversions ====================

    @staticmethod
    def convert_temperature(value: Optional[Union[int, float]],
                          from_unit: str = 'C') -> Optional[float]:
        """
        Convert temperature to Celsius (SI standard)

        Args:
            value: Temperature value
            from_unit: Source unit ('C', 'F', 'K')

        Returns:
            Temperature in Celsius, or None if value is None
        """
        if value is None:
            return None

        value = float(value)
        from_unit = from_unit.upper()

        if from_unit == 'C':
            return value
        elif from_unit == 'F':
            # Fahrenheit to Celsius
            return (value - 32) * 5/9
        elif from_unit == 'K':
            # Kelvin to Celsius
            return value - 273.15
        else:
            raise ValueError(f"Unknown temperature unit: {from_unit}")

    # ==================== Pressure Conversions ====================

    @staticmethod
    def convert_pressure(value: Optional[Union[int, float]],
                        from_unit: str = 'Pa') -> Optional[float]:
        """
        Convert pressure to Pascals (SI standard)

        Args:
            value: Pressure value
            from_unit: Source unit ('Pa', 'hPa', 'mb', 'mbar', 'inHg', 'mmHg', 'atm', 'psi')

        Returns:
            Pressure in Pascals, or None if value is None
        """
        if value is None:
            return None

        value = float(value)
        from_unit = from_unit.lower()

        conversions = {
            'pa': 1.0,                    # Pascals (SI standard)
            'hpa': 100.0,                 # Hectopascals (1 hPa = 100 Pa)
            'mb': 100.0,                  # Millibars (same as hPa)
            'mbar': 100.0,                # Millibars
            'inhg': 3386.39,              # Inches of mercury
            'mmhg': 133.322,              # Millimeters of mercury
            'atm': 101325.0,              # Atmospheres
            'psi': 6894.76,               # Pounds per square inch
            'kpa': 1000.0,                # Kilopascals
        }

        if from_unit in conversions:
            return value * conversions[from_unit]
        else:
            raise ValueError(f"Unknown pressure unit: {from_unit}")

    # ==================== Wind Speed Conversions ====================

    @staticmethod
    def convert_wind_speed(value: Optional[Union[int, float]],
                          from_unit: str = 'm/s') -> Optional[float]:
        """
        Convert wind speed to meters per second (SI standard)

        Args:
            value: Wind speed value
            from_unit: Source unit ('m/s', 'mph', 'km/h', 'knots', 'ft/s')

        Returns:
            Wind speed in m/s, or None if value is None
        """
        if value is None:
            return None

        value = float(value)
        from_unit = from_unit.lower().replace(' ', '')

        conversions = {
            'm/s': 1.0,                   # Meters per second (SI standard)
            'ms': 1.0,                    # Meters per second (alternative)
            'mph': 0.44704,               # Miles per hour
            'km/h': 0.277778,             # Kilometers per hour
            'kmh': 0.277778,              # Kilometers per hour (alternative)
            'knots': 0.514444,            # Knots (nautical miles per hour)
            'kt': 0.514444,               # Knots (alternative)
            'ft/s': 0.3048,               # Feet per second
            'fps': 0.3048,                # Feet per second (alternative)
        }

        if from_unit in conversions:
            return value * conversions[from_unit]
        else:
            raise ValueError(f"Unknown wind speed unit: {from_unit}")

    # ==================== Distance Conversions ====================

    @staticmethod
    def convert_distance(value: Optional[Union[int, float]],
                        from_unit: str = 'm') -> Optional[float]:
        """
        Convert distance to meters (SI standard)

        Args:
            value: Distance value
            from_unit: Source unit ('m', 'km', 'ft', 'mi', 'nm')

        Returns:
            Distance in meters, or None if value is None
        """
        if value is None:
            return None

        value = float(value)
        from_unit = from_unit.lower()

        conversions = {
            'm': 1.0,                     # Meters (SI standard)
            'km': 1000.0,                 # Kilometers
            'ft': 0.3048,                 # Feet
            'mi': 1609.34,                # Miles
            'nm': 1852.0,                 # Nautical miles
            'cm': 0.01,                   # Centimeters
            'mm': 0.001,                  # Millimeters
        }

        if from_unit in conversions:
            return value * conversions[from_unit]
        else:
            raise ValueError(f"Unknown distance unit: {from_unit}")

    # ==================== Precipitation Conversions ====================

    @staticmethod
    def convert_precipitation(value: Optional[Union[int, float]],
                             from_unit: str = 'mm') -> Optional[float]:
        """
        Convert precipitation to millimeters (meteorology standard)

        Args:
            value: Precipitation value
            from_unit: Source unit ('mm', 'cm', 'in', 'm')

        Returns:
            Precipitation in millimeters, or None if value is None
        """
        if value is None:
            return None

        value = float(value)
        from_unit = from_unit.lower()

        conversions = {
            'mm': 1.0,                    # Millimeters (meteorology standard)
            'cm': 10.0,                   # Centimeters
            'in': 25.4,                   # Inches
            'm': 1000.0,                  # Meters
        }

        if from_unit in conversions:
            return value * conversions[from_unit]
        else:
            raise ValueError(f"Unknown precipitation unit: {from_unit}")

    # ==================== Auto-Detection and Conversion ====================

    @staticmethod
    def auto_convert(value: Optional[Union[int, float]],
                    field_name: str,
                    source_unit: Optional[str] = None) -> Optional[float]:
        """
        Automatically detect field type and apply appropriate conversion

        Args:
            value: Value to convert
            field_name: Name of the field (e.g., 'temperature', 'pressure_hpa', 'wind_speed_mph')
            source_unit: Explicit source unit (if None, will try to detect from field_name)

        Returns:
            Converted value in SI units, or None if value is None
        """
        if value is None:
            return None

        field_lower = field_name.lower()

        # Detect unit from field name if not explicitly provided
        if source_unit is None:
            # Temperature detection
            if 'fahrenheit' in field_lower or field_lower.endswith('_f'):
                source_unit = 'F'
            elif 'kelvin' in field_lower or field_lower.endswith('_k'):
                source_unit = 'K'

            # Pressure detection
            elif 'hpa' in field_lower or 'hectopascal' in field_lower:
                source_unit = 'hPa'
            elif 'inhg' in field_lower or 'inches_hg' in field_lower:
                source_unit = 'inHg'
            elif 'mbar' in field_lower or 'millibar' in field_lower:
                source_unit = 'mbar'

            # Wind speed detection
            elif 'mph' in field_lower or 'miles_per_hour' in field_lower:
                source_unit = 'mph'
            elif 'kmh' in field_lower or 'km/h' in field_lower or 'kilometers_per_hour' in field_lower:
                source_unit = 'km/h'
            elif 'knot' in field_lower or field_lower.endswith('_kt'):
                source_unit = 'knots'

            # Distance detection
            elif 'feet' in field_lower or field_lower.endswith('_ft'):
                source_unit = 'ft'
            elif 'mile' in field_lower and 'wind' not in field_lower:
                source_unit = 'mi'

            # Precipitation detection
            elif 'precip' in field_lower and ('in' in field_lower or 'inch' in field_lower):
                source_unit = 'in'

        # Apply appropriate conversion based on field type
        if 'temp' in field_lower or 'temperature' in field_lower:
            return UnitConverter.convert_temperature(value, source_unit or 'C')
        elif 'pressure' in field_lower or 'atm_pressure' in field_lower or 'barometric' in field_lower:
            return UnitConverter.convert_pressure(value, source_unit or 'Pa')
        elif 'wind' in field_lower and 'speed' in field_lower:
            return UnitConverter.convert_wind_speed(value, source_unit or 'm/s')
        elif 'wind' in field_lower and 'direction' not in field_lower:
            return UnitConverter.convert_wind_speed(value, source_unit or 'm/s')
        elif 'precip' in field_lower or 'rain' in field_lower:
            return UnitConverter.convert_precipitation(value, source_unit or 'mm')
        elif 'distance' in field_lower or 'altitude' in field_lower or 'elevation' in field_lower:
            return UnitConverter.convert_distance(value, source_unit or 'm')
        else:
            # No conversion needed - return as is
            return float(value)

    # ==================== Batch Conversion ====================

    @staticmethod
    def convert_record(record: dict, field_mappings: dict) -> dict:
        """
        Convert multiple fields in a data record using field mappings

        Args:
            record: Dictionary containing data fields
            field_mappings: Dictionary mapping field names to their source units
                           Example: {'temperature': 'F', 'pressure': 'hPa', 'wind_speed': 'mph'}

        Returns:
            Record with all specified fields converted to SI units
        """
        converted = record.copy()

        for field_name, source_unit in field_mappings.items():
            if field_name in converted:
                converted[field_name] = UnitConverter.auto_convert(
                    converted[field_name],
                    field_name,
                    source_unit
                )

        return converted


# Convenience functions for direct imports
convert_temperature = UnitConverter.convert_temperature
convert_pressure = UnitConverter.convert_pressure
convert_wind_speed = UnitConverter.convert_wind_speed
convert_distance = UnitConverter.convert_distance
convert_precipitation = UnitConverter.convert_precipitation
auto_convert = UnitConverter.auto_convert
convert_record = UnitConverter.convert_record


# Example usage and testing
if __name__ == "__main__":
    print("=== Unit Converter Testing ===\n")

    # Temperature conversions
    print("Temperature Conversions:")
    print(f"  75°F = {convert_temperature(75, 'F'):.2f}°C")
    print(f"  300K = {convert_temperature(300, 'K'):.2f}°C")
    print(f"  25°C = {convert_temperature(25, 'C'):.2f}°C")

    # Pressure conversions
    print("\nPressure Conversions:")
    print(f"  1013.25 hPa = {convert_pressure(1013.25, 'hPa'):.2f} Pa")
    print(f"  29.92 inHg = {convert_pressure(29.92, 'inHg'):.2f} Pa")
    print(f"  1 atm = {convert_pressure(1, 'atm'):.2f} Pa")

    # Wind speed conversions
    print("\nWind Speed Conversions:")
    print(f"  10 mph = {convert_wind_speed(10, 'mph'):.2f} m/s")
    print(f"  50 km/h = {convert_wind_speed(50, 'km/h'):.2f} m/s")
    print(f"  20 knots = {convert_wind_speed(20, 'knots'):.2f} m/s")

    # Auto-detection
    print("\nAuto-Detection:")
    print(f"  temperature_f: 75 = {auto_convert(75, 'temperature_f'):.2f}°C")
    print(f"  pressure_hpa: 1013.25 = {auto_convert(1013.25, 'pressure_hpa'):.2f} Pa")
    print(f"  wind_speed_mph: 10 = {auto_convert(10, 'wind_speed_mph'):.2f} m/s")

    # Batch conversion
    print("\nBatch Conversion:")
    sample_record = {
        'temperature': 75,
        'pressure': 1013.25,
        'wind_speed': 10,
        'humidity': 65
    }
    mappings = {
        'temperature': 'F',
        'pressure': 'hPa',
        'wind_speed': 'mph'
    }
    converted = convert_record(sample_record, mappings)
    print(f"  Original: {sample_record}")
    print(f"  Converted: {converted}")
