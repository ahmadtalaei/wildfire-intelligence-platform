#!/usr/bin/env python3
"""
Auto-generate database tables based on discovered connectors
This script scans the connectors directory and creates appropriate tables
"""

import os
import re
import json
from pathlib import Path
from typing import Dict, List, Any

class TableGenerator:
    """Generate SQL tables based on connector discovery"""

    def __init__(self, connectors_dir: str = "/app/src/connectors"):
        self.connectors_dir = Path(connectors_dir)
        self.tables = {}

    def discover_connectors(self) -> List[str]:
        """Discover all connector files"""
        connectors = []
        if self.connectors_dir.exists():
            for file in self.connectors_dir.glob("*_connector.py"):
                if file.name != "__init__.py":
                    connectors.append(file.stem)
        return connectors

    def generate_table_schema(self, connector_name: str) -> str:
        """Generate SQL CREATE TABLE statement based on connector type"""

        # Map connector names to table configurations
        table_configs = {
            "nasa_firms": {
                "tables": [
                    {
                        "name": "firms_viirs_snpp_detections",
                        "columns": """
                            id SERIAL PRIMARY KEY,
                            timestamp TIMESTAMPTZ NOT NULL,
                            latitude DOUBLE PRECISION NOT NULL,
                            longitude DOUBLE PRECISION NOT NULL,
                            brightness_kelvin DOUBLE PRECISION,
                            brightness_temperature_i4 DOUBLE PRECISION,
                            brightness_temperature_i5 DOUBLE PRECISION,
                            fire_radiative_power_mw DOUBLE PRECISION,
                            confidence VARCHAR(10),
                            confidence_percent INTEGER,
                            scan_angle DOUBLE PRECISION,
                            track_degrees DOUBLE PRECISION,
                            daynight VARCHAR(1),
                            satellite VARCHAR(20) DEFAULT 'Suomi-NPP',
                            instrument VARCHAR(20) DEFAULT 'VIIRS',
                            version VARCHAR(10),
                            source VARCHAR(50) DEFAULT 'firms_viirs_snpp',
                            provider VARCHAR(100) DEFAULT 'NASA FIRMS',
                            created_at TIMESTAMPTZ DEFAULT NOW()
                        """
                    },
                    {
                        "name": "firms_viirs_noaa20_detections",
                        "columns": """
                            id SERIAL PRIMARY KEY,
                            timestamp TIMESTAMPTZ NOT NULL,
                            latitude DOUBLE PRECISION NOT NULL,
                            longitude DOUBLE PRECISION NOT NULL,
                            brightness_kelvin DOUBLE PRECISION,
                            brightness_temperature_i4 DOUBLE PRECISION,
                            brightness_temperature_i5 DOUBLE PRECISION,
                            fire_radiative_power_mw DOUBLE PRECISION,
                            confidence VARCHAR(10),
                            confidence_percent INTEGER,
                            scan_angle DOUBLE PRECISION,
                            track_degrees DOUBLE PRECISION,
                            daynight VARCHAR(1),
                            satellite VARCHAR(20) DEFAULT 'NOAA-20',
                            instrument VARCHAR(20) DEFAULT 'VIIRS',
                            version VARCHAR(10),
                            source VARCHAR(50) DEFAULT 'firms_viirs_noaa20',
                            provider VARCHAR(100) DEFAULT 'NASA FIRMS',
                            created_at TIMESTAMPTZ DEFAULT NOW()
                        """
                    },
                    {
                        "name": "firms_modis_terra_detections",
                        "columns": """
                            id SERIAL PRIMARY KEY,
                            timestamp TIMESTAMPTZ NOT NULL,
                            latitude DOUBLE PRECISION NOT NULL,
                            longitude DOUBLE PRECISION NOT NULL,
                            brightness_kelvin DOUBLE PRECISION,
                            fire_radiative_power_mw DOUBLE PRECISION,
                            confidence INTEGER,
                            scan_angle DOUBLE PRECISION,
                            track_degrees DOUBLE PRECISION,
                            daynight VARCHAR(1),
                            type INTEGER,
                            satellite VARCHAR(20) DEFAULT 'Terra',
                            instrument VARCHAR(20) DEFAULT 'MODIS',
                            version VARCHAR(10),
                            source VARCHAR(50) DEFAULT 'firms_modis_terra',
                            provider VARCHAR(100) DEFAULT 'NASA FIRMS',
                            created_at TIMESTAMPTZ DEFAULT NOW()
                        """
                    },
                    {
                        "name": "firms_modis_aqua_detections",
                        "columns": """
                            id SERIAL PRIMARY KEY,
                            timestamp TIMESTAMPTZ NOT NULL,
                            latitude DOUBLE PRECISION NOT NULL,
                            longitude DOUBLE PRECISION NOT NULL,
                            brightness_kelvin DOUBLE PRECISION,
                            fire_radiative_power_mw DOUBLE PRECISION,
                            confidence INTEGER,
                            scan_angle DOUBLE PRECISION,
                            track_degrees DOUBLE PRECISION,
                            daynight VARCHAR(1),
                            type INTEGER,
                            satellite VARCHAR(20) DEFAULT 'Aqua',
                            instrument VARCHAR(20) DEFAULT 'MODIS',
                            version VARCHAR(10),
                            source VARCHAR(50) DEFAULT 'firms_modis_aqua',
                            provider VARCHAR(100) DEFAULT 'NASA FIRMS',
                            created_at TIMESTAMPTZ DEFAULT NOW()
                        """
                    }
                ]
            },
            "noaa_weather": {
                "tables": [
                    {
                        "name": "noaa_station_observations",
                        "columns": """
                            id SERIAL PRIMARY KEY,
                            timestamp TIMESTAMPTZ NOT NULL,
                            station_id VARCHAR(20) NOT NULL,
                            station_name VARCHAR(255),
                            latitude DOUBLE PRECISION,
                            longitude DOUBLE PRECISION,
                            elevation_m DOUBLE PRECISION,
                            temperature_celsius DOUBLE PRECISION,
                            dewpoint_celsius DOUBLE PRECISION,
                            relative_humidity_percent DOUBLE PRECISION,
                            wind_speed_ms DOUBLE PRECISION,
                            wind_direction_degrees INTEGER,
                            pressure_pa DOUBLE PRECISION,
                            visibility_m DOUBLE PRECISION,
                            weather_description TEXT,
                            source VARCHAR(50) DEFAULT 'noaa_stations',
                            created_at TIMESTAMPTZ DEFAULT NOW()
                        """
                    },
                    {
                        "name": "noaa_weather_alerts",
                        "columns": """
                            id SERIAL PRIMARY KEY,
                            timestamp TIMESTAMPTZ NOT NULL,
                            alert_id VARCHAR(255) UNIQUE NOT NULL,
                            event VARCHAR(255) NOT NULL,
                            headline TEXT,
                            description TEXT,
                            severity VARCHAR(50),
                            urgency VARCHAR(50),
                            certainty VARCHAR(50),
                            effective TIMESTAMPTZ,
                            expires TIMESTAMPTZ,
                            area_description TEXT,
                            source VARCHAR(50) DEFAULT 'noaa_alerts',
                            created_at TIMESTAMPTZ DEFAULT NOW()
                        """
                    }
                ]
            },
            "purpleair": {
                "tables": [
                    {
                        "name": "purpleair_sensors",
                        "columns": """
                            id SERIAL PRIMARY KEY,
                            timestamp TIMESTAMPTZ NOT NULL,
                            sensor_id VARCHAR(100) NOT NULL,
                            sensor_name VARCHAR(255),
                            latitude DOUBLE PRECISION,
                            longitude DOUBLE PRECISION,
                            pm25_ugm3 DOUBLE PRECISION,
                            pm10_ugm3 DOUBLE PRECISION,
                            temperature_celsius DOUBLE PRECISION,
                            humidity_percent DOUBLE PRECISION,
                            pressure_pa DOUBLE PRECISION,
                            voc_ppb DOUBLE PRECISION,
                            ozone_ppb DOUBLE PRECISION,
                            confidence DOUBLE PRECISION,
                            source VARCHAR(50) DEFAULT 'purpleair',
                            created_at TIMESTAMPTZ DEFAULT NOW()
                        """
                    }
                ]
            },
            "airnow": {
                "tables": [
                    {
                        "name": "airnow_observations",
                        "columns": """
                            id SERIAL PRIMARY KEY,
                            timestamp TIMESTAMPTZ NOT NULL,
                            station_id VARCHAR(100),
                            station_name VARCHAR(255),
                            latitude DOUBLE PRECISION,
                            longitude DOUBLE PRECISION,
                            aqi INTEGER,
                            aqi_category VARCHAR(50),
                            primary_pollutant VARCHAR(20),
                            pm25_ugm3 DOUBLE PRECISION,
                            pm10_ugm3 DOUBLE PRECISION,
                            ozone_ppm DOUBLE PRECISION,
                            co_ppm DOUBLE PRECISION,
                            no2_ppb DOUBLE PRECISION,
                            so2_ppb DOUBLE PRECISION,
                            source VARCHAR(50) DEFAULT 'airnow',
                            created_at TIMESTAMPTZ DEFAULT NOW()
                        """
                    }
                ]
            },
            "iot_mqtt": {
                "tables": [
                    {
                        "name": "iot_weather_stations",
                        "columns": """
                            id SERIAL PRIMARY KEY,
                            timestamp TIMESTAMPTZ NOT NULL,
                            device_id VARCHAR(100) NOT NULL,
                            device_name VARCHAR(255),
                            latitude DOUBLE PRECISION,
                            longitude DOUBLE PRECISION,
                            temperature_celsius DOUBLE PRECISION,
                            humidity_percent DOUBLE PRECISION,
                            wind_speed_ms DOUBLE PRECISION,
                            wind_direction_degrees INTEGER,
                            pressure_pa DOUBLE PRECISION,
                            rainfall_mm DOUBLE PRECISION,
                            solar_radiation_wm2 DOUBLE PRECISION,
                            battery_voltage DOUBLE PRECISION,
                            source VARCHAR(50) DEFAULT 'iot_mqtt',
                            created_at TIMESTAMPTZ DEFAULT NOW()
                        """
                    }
                ]
            },
            "satellite": {
                "tables": [
                    {
                        "name": "satellite_imagery_metadata",
                        "columns": """
                            id SERIAL PRIMARY KEY,
                            timestamp TIMESTAMPTZ NOT NULL,
                            scene_id VARCHAR(255) UNIQUE NOT NULL,
                            satellite VARCHAR(50),
                            sensor VARCHAR(50),
                            center_latitude DOUBLE PRECISION,
                            center_longitude DOUBLE PRECISION,
                            cloud_cover_percent DOUBLE PRECISION,
                            processing_level VARCHAR(20),
                            thumbnail_url TEXT,
                            download_url TEXT,
                            file_size_mb DOUBLE PRECISION,
                            source VARCHAR(50) DEFAULT 'satellite',
                            created_at TIMESTAMPTZ DEFAULT NOW()
                        """
                    }
                ]
            }
        }

        # Clean connector name (remove _connector suffix)
        base_name = connector_name.replace("_connector", "")

        # Check if we have a configuration for this connector
        if base_name in table_configs:
            return self._generate_sql_for_tables(table_configs[base_name]["tables"])

        # Default generic table if connector not mapped
        return self._generate_generic_table(base_name)

    def _generate_sql_for_tables(self, tables: List[Dict[str, str]]) -> str:
        """Generate SQL for multiple tables"""
        sql_statements = []

        for table in tables:
            sql = f"""
-- Table: {table['name']}
CREATE TABLE IF NOT EXISTS {table['name']} (
{table['columns']}
);

-- Indexes for {table['name']}
CREATE INDEX IF NOT EXISTS idx_{table['name']}_timestamp ON {table['name']}(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_{table['name']}_location ON {table['name']}(latitude, longitude) WHERE latitude IS NOT NULL AND longitude IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_{table['name']}_created ON {table['name']}(created_at DESC);
"""
            sql_statements.append(sql)

        return "\n".join(sql_statements)

    def _generate_generic_table(self, connector_name: str) -> str:
        """Generate a generic table for unknown connectors"""
        table_name = f"{connector_name}_data"
        return f"""
-- Generic table for {connector_name}
CREATE TABLE IF NOT EXISTS {table_name} (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    data JSONB NOT NULL,
    source VARCHAR(50) DEFAULT '{connector_name}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_{table_name}_timestamp ON {table_name}(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_{table_name}_created ON {table_name}(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_{table_name}_data ON {table_name} USING GIN(data);
"""

    def generate_all_tables(self) -> str:
        """Generate SQL for all discovered connectors"""
        sql_statements = ["""
-- ============================================================================
-- AUTO-GENERATED TABLES BASED ON DISCOVERED CONNECTORS
-- Generated at runtime based on available connectors
-- ============================================================================
"""]

        connectors = self.discover_connectors()

        if not connectors:
            print("No connectors found, using default configuration")
            # Use default connectors if discovery fails
            connectors = [
                "nasa_firms_connector",
                "noaa_weather_connector",
                "purpleair_connector",
                "airnow_connector",
                "iot_mqtt_connector",
                "satellite_connector"
            ]

        for connector in connectors:
            print(f"Generating tables for connector: {connector}")
            sql_statements.append(f"\n-- ============== Tables for {connector} ==============")
            sql_statements.append(self.generate_table_schema(connector))

        # Add data source routing table
        sql_statements.append("""
-- ============================================================================
-- DATA SOURCE ROUTING TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS data_source_routing (
    source_id VARCHAR(100) PRIMARY KEY,
    table_name VARCHAR(100) NOT NULL,
    connector_name VARCHAR(100),
    description TEXT,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO wildfire_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO wildfire_user;
""")

        return "\n".join(sql_statements)


if __name__ == "__main__":
    # This can be called during container initialization
    import sys
    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

    # Check if we should generate and execute
    if len(sys.argv) > 1 and sys.argv[1] == "execute":
        try:
            # Connect to database
            conn = psycopg2.connect(
                host=os.environ.get("POSTGRES_HOST", "postgres"),
                port=os.environ.get("POSTGRES_PORT", 5432),
                database=os.environ.get("POSTGRES_DB", "wildfire_db"),
                user=os.environ.get("POSTGRES_USER", "wildfire_user"),
                password=os.environ.get("POSTGRES_PASSWORD", "wildfire_password")
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()

            # Generate SQL
            generator = TableGenerator("/app/src/connectors")
            sql = generator.generate_all_tables()

            # Execute SQL
            cursor.execute(sql)
            print("Tables created successfully based on discovered connectors")

            cursor.close()
            conn.close()
        except Exception as e:
            print(f"Error creating tables: {e}")
            sys.exit(1)
    else:
        # Just print the SQL
        generator = TableGenerator()
        print(generator.generate_all_tables())