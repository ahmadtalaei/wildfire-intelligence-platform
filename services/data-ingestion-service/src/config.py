"""Configuration settings"""
import os
from pydantic import ConfigDict
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    model_config = ConfigDict(
        env_file="../../.env",
        env_file_encoding='utf-8',
        extra='ignore'
    )

    kafka_bootstrap_servers: str = "localhost:9092"
    allowed_origins: list = ["*"]
    firms_map_key: str = ""
    noaa_user_agent: str = ""

    # MQTT Configuration
    mqtt_broker_host: str = "localhost"
    mqtt_broker_port: int = 1883
    mqtt_username: str = "wildfire_iot"
    mqtt_password: str = "SecurePassword2025!"
    mqtt_use_ssl: bool = False

    # PurpleAir API Configuration
    purpleair_api_key: str = ""
    purpleair_api_base_url: str = "https://api.purpleair.com/v1"

    # AirNow API Configuration (U.S. EPA)
    airnow_api_key: str = ""
    airnow_api_base_url: str = "https://www.airnowapi.org/aq"

    # Redis Configuration
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/1")

    # Geographic bounds configuration - Use config/geographic_bounds.py instead
    # These are maintained for backward compatibility but should not be used
    # Import from geo_config.geographic_bounds.CALIFORNIA_BOUNDS for precise USGS values

    # Streaming configuration
    weather_alerts_polling_interval_seconds: int = 30  # Time-critical alerts every 30s
    weather_polling_interval_seconds: int = 30  # Weather data continuous streaming (changed from 3600 for live streaming)
    default_polling_interval_seconds: int = 3600  # Default: hourly
    default_quality_threshold: float = 0.7

    # Server configuration
    server_host: str = "0.0.0.0"
    server_port: int = 8000
    server_reload: bool = True
    server_log_level: str = "info"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Load from main .env file if not set
        if not self.firms_map_key:
            self.firms_map_key = os.getenv("FIRMS_MAP_KEY", "")
        if not self.noaa_user_agent:
            self.noaa_user_agent = os.getenv("NOAA_USER_AGENT", "")
        if not self.kafka_bootstrap_servers or self.kafka_bootstrap_servers == "kafka:29092":
            self.kafka_bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        if not self.purpleair_api_key:
            self.purpleair_api_key = os.getenv("PURPLEAIR_API_KEY", "")
        if not self.airnow_api_key:
            self.airnow_api_key = os.getenv("AIRNOW_API_KEY", "")

def get_settings():
    return Settings()