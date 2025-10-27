# Centralized Unit and Timezone Conversion Utilities

This directory contains centralized conversion utilities for ensuring all data sources use consistent SI units and Pacific Time timezone.

## Files

- **`unit_converter.py`**: Centralized unit conversion to SI standards
- **`timezone_converter.py`**: Centralized timezone conversion to Pacific Time (California)

---

## Unit Converter (`unit_converter.py`)

### Purpose
Converts all measurements to SI (International System) standards:
- **Temperature**: Celsius (°C)
- **Pressure**: Pascals (Pa)
- **Wind Speed**: meters per second (m/s)
- **Distance**: meters (m)
- **Precipitation**: millimeters (mm)

### Basic Usage

```python
from .unit_converter import convert_temperature, convert_pressure, convert_wind_speed

# Temperature conversions
temp_celsius = convert_temperature(75, from_unit='F')      # 75°F → 23.89°C
temp_celsius = convert_temperature(300, from_unit='K')     # 300K → 26.85°C

# Pressure conversions
pressure_pa = convert_pressure(1013.25, from_unit='hPa')   # 1013.25 hPa → 101325 Pa
pressure_pa = convert_pressure(29.92, from_unit='inHg')    # 29.92 inHg → 101325.01 Pa

# Wind speed conversions
wind_ms = convert_wind_speed(10, from_unit='mph')          # 10 mph → 4.47 m/s
wind_ms = convert_wind_speed(20, from_unit='knots')        # 20 knots → 10.29 m/s
```

### Auto-Detection

The `auto_convert()` function automatically detects the field type and source unit from the field name:

```python
from .unit_converter import auto_convert

# Auto-detects temperature in Fahrenheit
temp = auto_convert(75, 'temperature_f')           # → 23.89°C

# Auto-detects pressure in hPa
pressure = auto_convert(1013.25, 'pressure_hpa')   # → 101325 Pa

# Auto-detects wind speed in mph
wind = auto_convert(10, 'wind_speed_mph')          # → 4.47 m/s
```

### Batch Conversion

Convert multiple fields in a record at once:

```python
from .unit_converter import convert_record

record = {
    'temperature': 75,
    'pressure': 1013.25,
    'wind_speed': 10,
    'humidity': 65
}

field_mappings = {
    'temperature': 'F',
    'pressure': 'hPa',
    'wind_speed': 'mph'
}

converted = convert_record(record, field_mappings)
# Result: {'temperature': 23.89, 'pressure': 101325, 'wind_speed': 4.47, 'humidity': 65}
```

### Supported Units

#### Temperature
- `'C'` - Celsius (SI standard)
- `'F'` - Fahrenheit
- `'K'` - Kelvin

#### Pressure
- `'Pa'` - Pascals (SI standard)
- `'hPa'` - Hectopascals
- `'mb'` / `'mbar'` - Millibars
- `'inHg'` - Inches of mercury
- `'mmHg'` - Millimeters of mercury
- `'atm'` - Atmospheres
- `'psi'` - Pounds per square inch
- `'kPa'` - Kilopascals

#### Wind Speed
- `'m/s'` / `'ms'` - Meters per second (SI standard)
- `'mph'` - Miles per hour
- `'km/h'` / `'kmh'` - Kilometers per hour
- `'knots'` / `'kt'` - Knots
- `'ft/s'` / `'fps'` - Feet per second

#### Distance
- `'m'` - Meters (SI standard)
- `'km'` - Kilometers
- `'ft'` - Feet
- `'mi'` - Miles
- `'nm'` - Nautical miles
- `'cm'` - Centimeters
- `'mm'` - Millimeters

#### Precipitation
- `'mm'` - Millimeters (meteorology standard)
- `'cm'` - Centimeters
- `'in'` - Inches
- `'m'` - Meters

---

## Timezone Converter (`timezone_converter.py`)

### Purpose
Converts all timestamps to Pacific Time (America/Los_Angeles) for California wildfire monitoring:
- **PST (Pacific Standard Time)**: UTC-8 (November - March)
- **PDT (Pacific Daylight Time)**: UTC-7 (March - November)

### Basic Usage

```python
from .timezone_converter import utc_to_pacific, utcnow_pacific

# Convert UTC string to Pacific Time
pacific = utc_to_pacific('2025-01-15T12:00:00Z')
# Result: '2025-01-15T04:00:00-08:00' (PST in January)

pacific = utc_to_pacific('2025-07-15T12:00:00Z')
# Result: '2025-07-15T05:00:00-07:00' (PDT in July)

# Get current time in Pacific
current_pacific = utcnow_pacific()
# Result: '2025-10-02T10:30:00-07:00'
```

### Datetime Object Conversion

```python
from .timezone_converter import datetime_to_pacific, datetime_to_pacific_str
from datetime import datetime

# Convert datetime object to Pacific Time
utc_dt = datetime.utcnow()
pacific_dt = datetime_to_pacific(utc_dt)        # Returns datetime object
pacific_str = datetime_to_pacific_str(utc_dt)   # Returns ISO string
```

### Batch Timestamp Conversion

Convert all timestamp fields in a record:

```python
from .timezone_converter import convert_record_timestamps

record = {
    'timestamp': '2025-01-15T12:00:00Z',
    'created_at': '2025-01-15T10:00:00Z',
    'temperature': 25.5,
    'updated_at': datetime.utcnow()
}

converted = convert_record_timestamps(record)
# All timestamp fields converted to Pacific Time
```

### Accepted Timestamp Formats

The converter accepts various UTC timestamp formats:
- `'2025-01-15T12:00:00Z'` (ISO with Z suffix)
- `'2025-01-15T12:00:00+00:00'` (ISO with timezone)
- `'2025-01-15T12:00:00'` (ISO without timezone - assumes UTC)
- `'2025-01-15 12:00:00'` (Space-separated - assumes UTC)

---

## Integration Examples

### Example 1: PurpleAir Connector

```python
from .timezone_converter import utc_to_pacific
from .unit_converter import convert_temperature, convert_pressure

# Inside _parse_sensor_reading method
reading = {
    'sensor_id': sensor_dict.get('sensor_index'),
    'latitude': sensor_dict.get('latitude'),
    'longitude': sensor_dict.get('longitude'),
    'timestamp': utc_to_pacific(datetime.utcnow().isoformat() + 'Z'),

    # Convert temperature from Fahrenheit to Celsius
    'temperature': convert_temperature(sensor_dict.get('temperature'), from_unit='F'),
    'humidity': sensor_dict.get('humidity'),

    # Convert pressure from hPa to Pascals
    'pressure': convert_pressure(sensor_dict.get('pressure'), from_unit='hPa'),
}
```

### Example 2: IoT MQTT Connector

```python
from .timezone_converter import utc_to_pacific
from .unit_converter import convert_wind_speed, convert_pressure

# Inside _extract_sensor_measurements method
if standard_name == 'wind_speed' and 'mph' in key.lower():
    value = convert_wind_speed(value, from_unit='mph')
elif standard_name == 'pressure' and 'hpa' in key.lower():
    value = convert_pressure(value, from_unit='hPa')

# For timestamp
standardized_record = {
    'timestamp': utc_to_pacific(datetime.utcnow().isoformat() + 'Z'),
    'device_id': device_id,
    # ... other fields
}
```

### Example 3: METAR Weather Connector

```python
from .timezone_converter import utc_to_pacific
from .unit_converter import convert_wind_speed, convert_pressure

# Inside _parse_metar_observation method
record = {
    'timestamp': utc_to_pacific(obs.get('reportTime')),
    'station_id': station_id,
    'temperature': float(obs['temp']),  # Already in Celsius
    'wind_speed': convert_wind_speed(obs['wspd'], from_unit='knots'),
    'pressure': convert_pressure(obs['altim'], from_unit='inHg'),
}
```

---

## Data Source-Specific Conversions

### Current Active Conversions

| Data Source | Field | Original Unit | Conversion | SI Unit |
|------------|-------|---------------|------------|---------|
| **purpleair_california** | temperature | °F | `convert_temperature(val, 'F')` | °C |
| **purpleair_california** | pressure | hPa | `convert_pressure(val, 'hPa')` | Pa |
| **iot_weather_stations** | wind_speed | mph | `convert_wind_speed(val, 'mph')` | m/s |
| **iot_weather_stations** | pressure | hPa | `convert_pressure(val, 'hPa')` | Pa |
| **wx_station_metar** | wind_speed | knots | `convert_wind_speed(val, 'knots')` | m/s |
| **wx_station_metar** | pressure | inHg | `convert_pressure(val, 'inHg')` | Pa |

### Optional Conversions (Not Yet Implemented)

| Data Source | Field | Original Unit | Suggested Conversion | SI Unit |
|------------|-------|---------------|----------------------|---------|
| **firms_viirs_***  | brightness | K | `convert_temperature(val, 'K')` | °C |
| **firms_modis_***  | brightness | K | `convert_temperature(val, 'K')` | °C |
| **sat_landsat_thermal** | thermal_band | K | `convert_temperature(val, 'K')` | °C |
| **sat_sentinel3_slstr** | brightness_temp | K | `convert_temperature(val, 'K')` | °C |

---

## Testing

Both utilities include test code. Run them directly to verify functionality:

```bash
# Test unit converter
python -m src.connectors.unit_converter

# Test timezone converter
python -m src.connectors.timezone_converter
```

---

## Migration Checklist

When adding conversion to a new data source:

- [ ] Import the conversion utilities at the top of the connector file
- [ ] Identify fields that need unit conversion
- [ ] Apply appropriate conversion functions when extracting data
- [ ] Convert timestamps to Pacific Time using `utc_to_pacific()`
- [ ] Test with real data to verify conversions
- [ ] Update this README with the data source-specific conversions

---

## Benefits of Centralized Conversion

1. **Consistency**: All data sources use the same conversion logic
2. **Maintainability**: Fix once, apply everywhere
3. **Testability**: Single place to test conversion accuracy
4. **Documentation**: Clear reference for all unit standards
5. **Extensibility**: Easy to add new unit types or conversion methods
6. **Error Handling**: Centralized error handling for invalid units
7. **Type Safety**: Handles None values gracefully

---

## Common Issues and Solutions

### Issue: Import Error in Standalone Scripts

**Problem**: Connectors run as standalone scripts can't import relative modules

**Solution**: Use try/except blocks with fallback implementations (see `nasa_firms_connector.py` for example)

```python
try:
    from .timezone_converter import utc_to_pacific
    from .unit_converter import convert_temperature
except ImportError:
    # Fallback for standalone execution
    utc_to_pacific = lambda x: x
    convert_temperature = lambda x, **kwargs: x
```

### Issue: Field Name Not Auto-Detected

**Problem**: `auto_convert()` doesn't recognize a custom field name

**Solution**: Either:
1. Explicitly specify the source unit: `convert_temperature(value, from_unit='F')`
2. Add the field name pattern to the auto-detection logic in `unit_converter.py`

### Issue: Timezone Conversion Fails

**Problem**: Timestamp string format not recognized

**Solution**: The converter supports multiple formats. If your format isn't supported:
1. Pre-process the timestamp to ISO format
2. Add format handling to `utc_to_pacific()` in `timezone_converter.py`

---

## Future Enhancements

Planned improvements:

- [ ] Add support for more specialized units (radiation, spectral bands, etc.)
- [ ] Implement batch processing for large datasets
- [ ] Add validation functions to check if values are already in SI units
- [ ] Create conversion history logging for debugging
- [ ] Add performance optimization for bulk conversions
- [ ] Implement caching for repeated conversions

---

## Questions or Issues?

If you encounter issues with conversions or need to add support for new units:

1. Check this README first
2. Review the test code in the utility files
3. Consult the data source API documentation for unit specifications
4. Update the conversion utilities and this README with your changes
