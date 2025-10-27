"""
Intelligent Table Routing System
Routes data sources to their specialized PostgreSQL tables
"""

from typing import Dict, Optional
import structlog

logger = structlog.get_logger()


class TableRouter:
    """
    Routes incoming data to appropriate specialized tables based on source_id

    This eliminates complex conditional logic in kafka_consumer.py
    Each data source gets its own optimized table with source-specific fields
    """

    # Master routing table: source_id -> table_name
    ROUTING_MAP = {
        # Weather Stations
        'wx_station_metar': 'metar_observations',
        'noaa_stations_current': 'noaa_station_observations',
        'noaa_stations_historical': 'noaa_station_observations',  # Same schema

        # Weather Model Forecasts
        'wx_era5_land': 'era5_land_reanalysis',
        'wx_era5_reanalysis': 'era5_reanalysis',
        'wx_gfs_forecast': 'gfs_forecasts',
        'wx_nam_forecast': 'nam_forecasts',

        # Weather Alerts & Forecasts
        'noaa_alerts_active': 'noaa_weather_alerts',
        'noaa_gridpoints_forecast': 'noaa_gridpoint_forecast',

        # Fire Detection Satellites
        'firms_viirs_snpp': 'firms_viirs_snpp_detections',
        'firms_viirs_noaa20': 'firms_viirs_noaa20_detections',
        'firms_viirs_noaa21': 'firms_viirs_noaa21_detections',
        'firms_modis_terra': 'firms_modis_terra_detections',
        'firms_modis_aqua': 'firms_modis_aqua_detections',
        'landsat_nrt': 'landsat_nrt_detections',

        # Satellite Imagery Metadata
        'sat_landsat_thermal': 'landsat_thermal_imagery',
        'sat_sentinel2_msi': 'sentinel2_msi_imagery',
        'sat_sentinel3_slstr': 'sentinel3_slstr_imagery',

        # IoT Sensors
        'iot_weather_stations': 'iot_weather_stations',
        'iot_soil_moisture_sensors': 'iot_soil_moisture_sensors',
        'iot_air_quality_sensors': 'sensor_readings',

        # Air Quality
        'purpleair_california': 'sensor_readings',
        'airnow': 'airnow_observations',

        # Fire Incidents (keep existing)
        'fire_incidents': 'fire_incidents',

        # FireSat Ultra-High Resolution Fire Detection
        'firesat_detections': 'firesat_detections',
        'firesat_perimeters': 'firesat_perimeters',
        'firesat_thermal': 'firesat_thermal_scenes',
    }

    # Field mapping: standardized_field -> table_specific_field
    # This handles when connectors use different field names than tables expect
    FIELD_MAPPINGS = {
        'metar_observations': {
            'temperature': 'temperature_celsius',
            'dewpoint': 'dewpoint_celsius',
            'humidity': 'relative_humidity_percent',
            'wind_speed': 'wind_speed_ms',
            'wind_gust': 'wind_gust_ms',
            'wind_direction': 'wind_direction_degrees',
            'pressure': 'altimeter_setting_pa',
        },
        'noaa_station_observations': {
            'temperature': 'temperature_celsius',
            'dewpoint': 'dewpoint_celsius',
            'humidity': 'relative_humidity_percent',
            'wind_speed': 'wind_speed_ms',
            'wind_gust': 'wind_gust_ms',
            'wind_direction': 'wind_direction_degrees',
            'pressure': 'barometric_pressure_pa',
        },
        'era5_land_reanalysis': {
            'temperature': 'temperature_2m_celsius',
            'dewpoint': 'dewpoint_2m_celsius',
            'u_wind': 'u_wind_10m_ms',
            'v_wind': 'v_wind_10m_ms',
            'wind_speed': 'wind_speed_10m_ms',
            'wind_direction': 'wind_direction_10m_degrees',
            'pressure': 'surface_pressure_pa',
            'precipitation': 'total_precipitation_mm',
        },
        'era5_reanalysis': {
            'temperature': 'temperature_celsius',
            'humidity': 'relative_humidity_percent',
            'u_wind': 'u_wind_ms',
            'v_wind': 'v_wind_ms',
            'wind_speed': 'wind_speed_ms',
            'wind_direction': 'wind_direction_degrees',
            'pressure': 'surface_pressure_pa',
        },
        'gfs_forecasts': {
            'temperature': 'temperature_celsius',
            'dewpoint': 'dewpoint_celsius',
            'u_wind': 'u_wind_10m_ms',
            'v_wind': 'v_wind_10m_ms',
            'wind_speed': 'wind_speed_10m_ms',
            'wind_direction': 'wind_direction_10m_degrees',
            'pressure': 'surface_pressure_pa',
            'precipitation': 'total_precipitation_mm',
        },
        'nam_forecasts': {
            'temperature': 'temperature_celsius',
            'dewpoint': 'dewpoint_celsius',
            'u_wind': 'u_wind_10m_ms',
            'v_wind': 'v_wind_10m_ms',
            'wind_speed': 'wind_speed_10m_ms',
            'wind_direction': 'wind_direction_10m_degrees',
            'pressure': 'surface_pressure_pa',
            'precipitation': 'total_precipitation_mm',
        },
        'noaa_weather_alerts': {
            'id': 'alert_id',
            'description': 'description',
            'area': 'area_description',
        },
        # FIRMS fire detections - all use same schema
        'firms_viirs_snpp_detections': {
            'brightness': 'brightness_kelvin',
            'frp': 'fire_radiative_power_mw',
            'scan': 'scan_angle',
            'track': 'track_degrees',
        },
        'firms_viirs_noaa20_detections': {
            'brightness': 'brightness_kelvin',
            'frp': 'fire_radiative_power_mw',
            'scan': 'scan_angle',
            'track': 'track_degrees',
        },
        'firms_viirs_noaa21_detections': {
            'brightness': 'brightness_kelvin',
            'frp': 'fire_radiative_power_mw',
            'scan': 'scan_angle',
            'track': 'track_degrees',
        },
        'firms_modis_terra_detections': {
            'brightness': 'brightness_kelvin',
            'frp': 'fire_radiative_power_mw',
            'scan': 'scan_angle',
            'track': 'track_degrees',
        },
        'firms_modis_aqua_detections': {
            'brightness': 'brightness_kelvin',
            'frp': 'fire_radiative_power_mw',
            'scan': 'scan_angle',
            'track': 'track_degrees',
        },
        'landsat_nrt_detections': {
            'brightness': 'brightness_kelvin',
            'frp': 'fire_radiative_power_mw',
        },
        'iot_weather_stations': {
            'temperature': 'temperature_celsius',
            'humidity': 'humidity_percent',
            'dewpoint': 'dewpoint_celsius',
            'wind_speed': 'wind_speed_ms',
            'wind_gust': 'wind_gust_ms',
            'wind_direction': 'wind_direction_degrees',
            'pressure': 'pressure_pa',
            'rainfall': 'rainfall_mm',
        },
        'iot_soil_moisture_sensors': {
            'soil_temp': 'soil_temp_5cm_celsius',
        },
        'airnow_observations': {
            'pm25': 'pm25_ugm3',
            'pm10': 'pm10_ugm3',
            'ozone': 'ozone_ppm',
        },
    }

    @classmethod
    def get_table_name(cls, source_id: str) -> str:
        """
        Get the target table name for a given source_id

        Args:
            source_id: Source identifier (e.g., 'wx_station_metar', 'firms_viirs_snpp')

        Returns:
            Table name (e.g., 'metar_observations', 'firms_viirs_snpp_detections')

        Raises:
            ValueError: If source_id is not recognized
        """
        table_name = cls.ROUTING_MAP.get(source_id)

        if not table_name:
            # Fallback for unknown sources
            logger.warning(f"Unknown source_id '{source_id}', using weather_data_legacy")
            return 'weather_data_legacy'

        logger.debug(f"Routing {source_id} -> {table_name}")
        return table_name

    @classmethod
    def map_fields(cls, source_id: str, data: Dict) -> Dict:
        """
        Map standardized field names to table-specific field names

        Args:
            source_id: Source identifier
            data: Input data dictionary with standardized field names

        Returns:
            Data dictionary with table-specific field names
        """
        table_name = cls.get_table_name(source_id)
        field_map = cls.FIELD_MAPPINGS.get(table_name, {})

        if not field_map:
            # No field mapping needed for this table
            return data

        # Create new dict with mapped field names
        mapped_data = {}
        for key, value in data.items():
            mapped_key = field_map.get(key, key)  # Use mapping or keep original
            mapped_data[mapped_key] = value

        return mapped_data

    @classmethod
    def get_all_sources(cls) -> Dict[str, str]:
        """Get all registered source_id -> table_name mappings"""
        return cls.ROUTING_MAP.copy()

    @classmethod
    def get_sources_for_table(cls, table_name: str) -> list:
        """Get all source_ids that route to a specific table"""
        return [
            source_id
            for source_id, tbl in cls.ROUTING_MAP.items()
            if tbl == table_name
        ]

    @classmethod
    def is_registered(cls, source_id: str) -> bool:
        """Check if source_id is registered in routing table"""
        return source_id in cls.ROUTING_MAP

    @classmethod
    def get_table_info(cls, source_id: str) -> Dict[str, any]:
        """
        Get comprehensive routing information for a source

        Returns:
            {
                'source_id': str,
                'table_name': str,
                'field_mapping': dict,
                'has_custom_mapping': bool
            }
        """
        table_name = cls.get_table_name(source_id)
        field_mapping = cls.FIELD_MAPPINGS.get(table_name, {})

        return {
            'source_id': source_id,
            'table_name': table_name,
            'field_mapping': field_mapping,
            'has_custom_mapping': len(field_mapping) > 0
        }


# Convenience function for quick routing
def route_to_table(source_id: str) -> str:
    """Quick helper to get table name for a source_id"""
    return TableRouter.get_table_name(source_id)


# Convenience function for field mapping
def map_data_fields(source_id: str, data: Dict) -> Dict:
    """Quick helper to map data fields for a source_id"""
    return TableRouter.map_fields(source_id, data)
