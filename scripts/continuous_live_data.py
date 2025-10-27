#!/usr/bin/env python3
"""
Continuous live data generation script - runs every 5 minutes
"""

import asyncio
import asyncpg
import aiohttp
import random
from datetime import datetime
import logging
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))
from load_env import load_env_file, get_database_url

# Load environment variables
load_env_file()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = get_database_url()

async def add_new_fire_incidents():
    """Add 1-3 new fire incidents"""
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        # California fire-prone areas
        fire_zones = [
            (37.7749, -122.4194),  # San Francisco Bay Area
            (34.0522, -118.2437),  # Los Angeles  
            (38.5816, -121.4944),  # Sacramento Valley
            (32.7157, -117.1611),  # San Diego
            (36.7378, -119.7871),  # Central Valley
        ]
        
        new_fires = random.randint(1, 3)
        for i in range(new_fires):
            base_lat, base_lon = random.choice(fire_zones)
            lat = base_lat + random.uniform(-0.3, 0.3)
            lon = base_lon + random.uniform(-0.3, 0.3)
            
            confidence = random.uniform(80.0, 98.0)
            temperature = random.uniform(320.0, 420.0)
            source = random.choice(['nasa_modis', 'nasa_viirs'])
            
            await conn.execute("""
                INSERT INTO fire_incidents (
                    incident_id, latitude, longitude, confidence, temperature, source, created_at
                ) VALUES (gen_random_uuid(), $1, $2, $3, $4, $5, NOW())
            """, lat, lon, confidence, temperature, source)
            
        logger.info(f"Added {new_fires} new fire incidents")
        return new_fires
        
    finally:
        await conn.close()

async def add_sensor_readings():
    """Add 2-4 new sensor readings"""
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        sensors = ['FIRE_STATION_01', 'WEATHER_TOWER_02', 'SMOKE_DETECTOR_03', 'FUEL_MOISTURE_04', 'WIND_SENSOR_05', 'TEMP_SENSOR_06']
        
        new_readings = random.randint(2, 4)
        for i in range(new_readings):
            sensor_id = random.choice(sensors)
            latitude = random.uniform(32.0, 42.0)
            longitude = random.uniform(-124.0, -114.0)
            temperature = random.uniform(15.0, 45.0)
            humidity = random.uniform(20.0, 90.0)
            smoke_level = random.uniform(0.0, 100.0)
            
            await conn.execute("""
                INSERT INTO sensor_readings (
                    sensor_id, latitude, longitude, temperature, humidity, smoke_level
                ) VALUES ($1, $2, $3, $4, $5, $6)
            """, sensor_id, latitude, longitude, temperature, humidity, smoke_level)
            
        logger.info(f"Added {new_readings} sensor readings")
        return new_readings
        
    finally:
        await conn.close()

async def add_weather_data():
    """Add 1-2 new weather station readings"""
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        # California weather stations
        stations = [
            (37.6213, -122.3790),  # SFO
            (34.0522, -118.2437),  # LAX
            (38.5816, -121.4944),  # Sacramento
            (32.7335, -117.1897),  # San Diego
            (36.9741, -122.0308),  # Santa Cruz
        ]
        
        new_weather = random.randint(1, 2)
        for i in range(new_weather):
            lat, lon = random.choice(stations)
            # Add slight variation for different readings from same area
            lat += random.uniform(-0.1, 0.1)
            lon += random.uniform(-0.1, 0.1)
            
            temperature = random.uniform(10.0, 40.0)
            humidity = random.uniform(30.0, 95.0)
            wind_speed = random.uniform(0.0, 15.0)
            wind_direction = random.uniform(0.0, 360.0)
            
            await conn.execute("""
                INSERT INTO weather_data (
                    latitude, longitude, temperature, humidity, wind_speed, wind_direction
                ) VALUES ($1, $2, $3, $4, $5, $6)
            """, lat, lon, temperature, humidity, wind_speed, wind_direction)
            
        logger.info(f"Added {new_weather} weather readings")
        return new_weather
        
    finally:
        await conn.close()

async def run_continuous_updates():
    """Run continuous data updates"""
    logger.info("🔄 Starting continuous live data updates...")
    logger.info("⏰ New data will be added every 5 minutes")
    
    iteration = 0
    while True:
        try:
            iteration += 1
            logger.info(f"[FIRE] Update cycle #{iteration} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Add new data
            fires = await add_new_fire_incidents()
            sensors = await add_sensor_readings()
            weather = await add_weather_data()
            
            total = fires + sensors + weather
            logger.info(f"[CHECK] Added {total} new records ({fires} fires, {sensors} sensors, {weather} weather)")
            
            # Show current totals
            conn = await asyncpg.connect(DATABASE_URL)
            try:
                fire_count = await conn.fetchval("SELECT COUNT(*) FROM fire_incidents")
                weather_count = await conn.fetchval("SELECT COUNT(*) FROM weather_data") 
                sensor_count = await conn.fetchval("SELECT COUNT(*) FROM sensor_readings")
                
                logger.info(f"[BAR_CHART] Database totals: {fire_count} fires, {weather_count} weather, {sensor_count} sensors")
                
            finally:
                await conn.close()
            
            logger.info("⏳ Waiting 5 minutes for next update...")
            await asyncio.sleep(300)  # 5 minutes
            
        except Exception as e:
            logger.error(f"Error in update cycle: {e}")
            logger.info("⏳ Waiting 1 minute before retry...")
            await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(run_continuous_updates())