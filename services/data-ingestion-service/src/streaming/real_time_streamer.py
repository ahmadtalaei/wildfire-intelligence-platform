"""
Real-time streaming service that actively polls APIs and sends data to Kafka
Includes both streaming and batch processing capabilities
"""

import asyncio
import json
import os
import sys
from datetime import datetime, date, timedelta, timezone
from typing import Dict, List, Any, Optional
import structlog
import aiohttp
import psycopg2
from psycopg2.extras import RealDictCursor

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from connectors.nasa_firms_connector import NASAFirmsConnector
from connectors.noaa_weather_connector import NOAAWeatherConnector
from connectors.iot_mqtt_connector import IoTMQTTConnector
from streaming.kafka_producer import KafkaDataProducer
from models.ingestion import BatchConfig, StreamingConfig

logger = structlog.get_logger()


class RealTimeStreamer:
    """
    Real-time data streaming service that:
    1. Actively polls APIs for new data
    2. Sends data to Kafka topics
    3. Stores data in PostgreSQL for persistence
    """

    def __init__(self):
        self.is_running = False
        self.kafka_producer = None
        self.db_conn = None
        self.connectors = {}
        self.polling_tasks = []

    async def initialize(self):
        """Initialize all components"""
        try:
            # Initialize Kafka producer
            kafka_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
            self.kafka_producer = KafkaDataProducer(kafka_servers)
            await self.kafka_producer.start()
            logger.info("Kafka producer initialized", servers=kafka_servers)

            # Initialize PostgreSQL connection
            self.db_conn = psycopg2.connect(
                host=os.getenv("POSTGRES_HOST", "postgres"),
                port=int(os.getenv("POSTGRES_PORT", 5432)),
                database=os.getenv("POSTGRES_DB", "wildfire_db"),
                user=os.getenv("POSTGRES_USER", "wildfire_user"),
                password=os.getenv("POSTGRES_PASSWORD", "wildfire_password")
            )
            logger.info("PostgreSQL connection established")

            # Create tables if they don't exist
            self._create_tables()

            # Initialize connectors
            self.connectors['nasa_firms'] = NASAFirmsConnector(
                kafka_producer=self.kafka_producer
            )
            self.connectors['noaa_weather'] = NOAAWeatherConnector(
                kafka_producer=self.kafka_producer
            )
            self.connectors['iot_mqtt'] = IoTMQTTConnector(
                broker_host=os.getenv("MQTT_BROKER_HOST", "mosquitto"),
                broker_port=int(os.getenv("MQTT_BROKER_PORT", 1883)),
                kafka_producer=self.kafka_producer
            )

            logger.info("All connectors initialized successfully")
            return True

        except Exception as e:
            logger.error("Failed to initialize streamer", error=str(e))
            return False

    def _create_tables(self):
        """Create database tables if they don't exist"""
        cursor = self.db_conn.cursor()

        # Create fire detections table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fire_detections (
                id SERIAL PRIMARY KEY,
                source VARCHAR(50),
                satellite VARCHAR(50),
                latitude DECIMAL(10, 6),
                longitude DECIMAL(10, 6),
                brightness DECIMAL(10, 2),
                bright_t31 DECIMAL(10, 2),
                frp DECIMAL(10, 2),
                confidence VARCHAR(20),
                scan DECIMAL(5, 2),
                track DECIMAL(5, 2),
                acq_date DATE,
                acq_time TIME,
                version VARCHAR(20),
                daynight CHAR(1),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                kafka_topic VARCHAR(100),
                kafka_offset BIGINT
            );

            CREATE INDEX IF NOT EXISTS idx_fire_detections_location
            ON fire_detections(latitude, longitude);

            CREATE INDEX IF NOT EXISTS idx_fire_detections_date
            ON fire_detections(acq_date);
        """)

        # Create weather observations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS weather_observations (
                id SERIAL PRIMARY KEY,
                station_id VARCHAR(20),
                station_name VARCHAR(200),
                latitude DECIMAL(10, 6),
                longitude DECIMAL(10, 6),
                elevation_m DECIMAL(10, 2),
                observation_time TIMESTAMP,
                temperature_c DECIMAL(5, 2),
                dewpoint_c DECIMAL(5, 2),
                humidity_percent INTEGER,
                wind_speed_kmh DECIMAL(5, 2),
                wind_direction INTEGER,
                wind_gust_kmh DECIMAL(5, 2),
                pressure_mb DECIMAL(7, 2),
                visibility_km DECIMAL(5, 2),
                cloud_coverage_percent INTEGER,
                weather_conditions TEXT,
                raw_metar TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                kafka_topic VARCHAR(100),
                kafka_offset BIGINT
            );

            CREATE INDEX IF NOT EXISTS idx_weather_observations_station
            ON weather_observations(station_id);

            CREATE INDEX IF NOT EXISTS idx_weather_observations_time
            ON weather_observations(observation_time);
        """)

        # Create IoT sensor data table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS iot_sensor_data (
                id SERIAL PRIMARY KEY,
                sensor_id VARCHAR(50),
                sensor_type VARCHAR(50),
                latitude DECIMAL(10, 6),
                longitude DECIMAL(10, 6),
                measurement_type VARCHAR(50),
                measurement_value DECIMAL(15, 6),
                unit VARCHAR(20),
                quality_score DECIMAL(3, 2),
                timestamp TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                kafka_topic VARCHAR(100),
                kafka_offset BIGINT
            );

            CREATE INDEX IF NOT EXISTS idx_iot_sensor_data_sensor
            ON iot_sensor_data(sensor_id);

            CREATE INDEX IF NOT EXISTS idx_iot_sensor_data_time
            ON iot_sensor_data(timestamp);
        """)

        # Create batch ingestion log
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ingestion_log (
                id SERIAL PRIMARY KEY,
                source VARCHAR(50),
                batch_id VARCHAR(100),
                records_processed INTEGER,
                records_failed INTEGER,
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                status VARCHAR(20),
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        self.db_conn.commit()
        logger.info("Database tables created/verified successfully")

    async def poll_nasa_firms(self):
        """Poll NASA FIRMS API for fire detections"""
        while self.is_running:
            try:
                logger.info("Polling NASA FIRMS for fire detections")

                # Fetch data from NASA FIRMS
                config = BatchConfig(
                    source_id="firms_viirs_snpp",
                    start_date=date.today() - timedelta(days=1),
                    end_date=date.today()
                )

                data = await self.connectors['nasa_firms'].fetch_batch_data(config)

                if data:
                    logger.info(f"Received {len(data)} fire detections from NASA FIRMS")

                    # Send to Kafka
                    for record in data:
                        await self.kafka_producer.send_fire_detection(
                            record,
                            source_id="nasa_firms"
                        )

                    # Store in PostgreSQL
                    self._store_fire_detections(data)

                    logger.info(f"Stored {len(data)} fire detections in database")

                # Poll every 5 minutes
                await asyncio.sleep(300)

            except Exception as e:
                logger.error("Error polling NASA FIRMS", error=str(e))
                await asyncio.sleep(60)  # Wait 1 minute on error

    async def poll_noaa_weather(self):
        """Poll NOAA weather API for observations"""
        while self.is_running:
            try:
                logger.info("Polling NOAA for weather observations")

                # Fetch current weather data
                data = await self.connectors['noaa_weather'].fetch_data()

                if data:
                    logger.info(f"Received {len(data)} weather observations from NOAA")

                    # Send to Kafka
                    for record in data:
                        await self.kafka_producer.send_weather_data(
                            record,
                            source_id="noaa_weather"
                        )

                    # Store in PostgreSQL
                    self._store_weather_observations(data)

                    logger.info(f"Stored {len(data)} weather observations in database")

                # Poll every 30 seconds
                await asyncio.sleep(30)

            except Exception as e:
                logger.error("Error polling NOAA weather", error=str(e))
                await asyncio.sleep(30)

    async def stream_iot_mqtt(self):
        """Stream IoT sensor data from MQTT broker"""
        try:
            logger.info("Starting IoT MQTT streaming")

            # Connect to MQTT broker
            await self.connectors['iot_mqtt'].connect()

            # Subscribe to sensor topics
            await self.connectors['iot_mqtt'].subscribe_to_sensors()

            # Start streaming (this runs continuously)
            config = StreamingConfig(source_id="iot_sensors")
            await self.connectors['iot_mqtt'].start_streaming(config)

        except Exception as e:
            logger.error("Error streaming IoT MQTT data", error=str(e))

    def _store_fire_detections(self, data: List[Dict]):
        """Store fire detection data in PostgreSQL"""
        cursor = self.db_conn.cursor()

        for record in data:
            try:
                cursor.execute("""
                    INSERT INTO fire_detections (
                        source, satellite, latitude, longitude,
                        brightness, bright_t31, frp, confidence,
                        scan, track, acq_date, acq_time, version, daynight,
                        kafka_topic, kafka_offset
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    record.get('source', 'NASA_FIRMS'),
                    record.get('satellite'),
                    record.get('latitude'),
                    record.get('longitude'),
                    record.get('brightness'),
                    record.get('bright_t31'),
                    record.get('frp'),
                    record.get('confidence'),
                    record.get('scan'),
                    record.get('track'),
                    record.get('acq_date'),
                    record.get('acq_time'),
                    record.get('version'),
                    record.get('daynight'),
                    'wildfire-nasa-firms',
                    0  # Kafka offset placeholder
                ))
            except Exception as e:
                logger.error("Error storing fire detection", error=str(e), record=record)

        self.db_conn.commit()

    def _store_weather_observations(self, data: List[Dict]):
        """Store weather observation data in PostgreSQL"""
        cursor = self.db_conn.cursor()

        for record in data:
            try:
                cursor.execute("""
                    INSERT INTO weather_observations (
                        station_id, station_name, latitude, longitude,
                        elevation_m, observation_time, temperature_c, dewpoint_c,
                        humidity_percent, wind_speed_kmh, wind_direction, wind_gust_kmh,
                        pressure_mb, visibility_km, cloud_coverage_percent,
                        weather_conditions, raw_metar, kafka_topic, kafka_offset
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    record.get('station_id'),
                    record.get('station_name'),
                    record.get('latitude'),
                    record.get('longitude'),
                    record.get('elevation_m'),
                    record.get('observation_time'),
                    record.get('temperature_c'),
                    record.get('dewpoint_c'),
                    record.get('humidity_percent'),
                    record.get('wind_speed_kmh'),
                    record.get('wind_direction'),
                    record.get('wind_gust_kmh'),
                    record.get('pressure_mb'),
                    record.get('visibility_km'),
                    record.get('cloud_coverage_percent'),
                    record.get('weather_conditions'),
                    record.get('raw_metar'),
                    'wildfire-weather-data',
                    0  # Kafka offset placeholder
                ))
            except Exception as e:
                logger.error("Error storing weather observation", error=str(e), record=record)

        self.db_conn.commit()

    async def process_batch(self, source: str, file_path: str = None, data: List[Dict] = None):
        """Process batch data from file or direct input"""
        try:
            logger.info(f"Processing batch data from {source}")

            if file_path:
                # Load data from file (CSV, JSON, etc.)
                with open(file_path, 'r') as f:
                    if file_path.endswith('.json'):
                        data = json.load(f)
                    # Add more file format handlers as needed

            if data:
                # Send to Kafka
                for record in data:
                    if source == 'fire_detections':
                        await self.kafka_producer.send_fire_detection(record, source_id="batch")
                        self._store_fire_detections([record])
                    elif source == 'weather':
                        await self.kafka_producer.send_weather_data(record, source_id="batch")
                        self._store_weather_observations([record])
                    # Add more source handlers as needed

                # Log batch processing
                cursor = self.db_conn.cursor()
                cursor.execute("""
                    INSERT INTO ingestion_log (
                        source, batch_id, records_processed, records_failed,
                        start_time, end_time, status
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    source,
                    f"batch_{datetime.now().timestamp()}",
                    len(data),
                    0,
                    datetime.now(timezone.utc),
                    datetime.now(timezone.utc),
                    'SUCCESS'
                ))
                self.db_conn.commit()

                logger.info(f"Successfully processed {len(data)} records from {source}")
                return True

        except Exception as e:
            logger.error(f"Error processing batch from {source}", error=str(e))
            return False

    async def start(self):
        """Start all streaming services"""
        try:
            if not await self.initialize():
                raise RuntimeError("Failed to initialize streamer")

            self.is_running = True

            # Start polling tasks
            self.polling_tasks = [
                asyncio.create_task(self.poll_nasa_firms()),
                asyncio.create_task(self.poll_noaa_weather()),
                # asyncio.create_task(self.stream_iot_mqtt())  # Enable when MQTT broker is running
            ]

            logger.info("Real-time streaming started successfully")

            # Keep running
            await asyncio.gather(*self.polling_tasks)

        except Exception as e:
            logger.error("Error in streaming service", error=str(e))
            await self.stop()

    async def stop(self):
        """Stop all streaming services"""
        logger.info("Stopping real-time streaming service")
        self.is_running = False

        # Cancel all polling tasks
        for task in self.polling_tasks:
            task.cancel()

        # Close connections
        if self.kafka_producer:
            await self.kafka_producer.stop()

        if self.db_conn:
            self.db_conn.close()

        logger.info("Real-time streaming service stopped")


async def main():
    """Main entry point"""
    streamer = RealTimeStreamer()

    try:
        await streamer.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    finally:
        await streamer.stop()


if __name__ == "__main__":
    # Configure logging
    import logging
    logging.basicConfig(level=logging.INFO)

    # Run the streamer
    asyncio.run(main())