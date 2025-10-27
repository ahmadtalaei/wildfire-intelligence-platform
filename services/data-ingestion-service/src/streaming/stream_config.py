"""
Stream Configuration Management
YAML/JSON-based configuration for streams, topics, modes, and policies
"""

import yaml
import json
from typing import Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass, asdict, field
import structlog

logger = structlog.get_logger()


@dataclass
class KafkaConfig:
    """Kafka connection and producer configuration"""
    bootstrap_servers: str = "localhost:9092"
    client_id: Optional[str] = None
    compression_type: str = "gzip"
    batch_size: int = 500
    linger_ms: int = 100
    max_retries: int = 3
    retry_backoff_base: float = 2.0


@dataclass
class TopicConfig:
    """Kafka topic configuration"""
    name: str
    partitions: int = 4
    replication_factor: int = 1
    retention_ms: int = 604800000  # 7 days
    compression_type: str = "gzip"


@dataclass
class IngestionConfig:
    """Ingestion mode configuration"""
    mode: str = "real_time"  # batch, real_time, continuous_streaming
    polling_interval_seconds: int = 30
    batch_size: int = 1000
    buffer_size: int = 100
    buffer_flush_interval_seconds: int = 5
    max_records_per_poll: int = 500


@dataclass
class ThrottlingConfig:
    """Throttling and backpressure configuration"""
    enabled: bool = True
    min_send_rate: float = 1.0
    max_send_rate: float = 1000.0
    target_consumer_lag: int = 1000
    critical_consumer_lag: int = 5000
    adjustment_factor: float = 1.5


@dataclass
class SourceConfig:
    """Individual source configuration"""
    source_id: str
    source_type: str  # nasa_firms, noaa_weather, iot_sensor, etc.
    enabled: bool = True
    ingestion: IngestionConfig = field(default_factory=IngestionConfig)
    topic: Optional[str] = None
    rate_limit_per_minute: int = 60
    timeout_seconds: float = 30.0
    cache_ttl_seconds: int = 60
    custom_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StreamManagerConfig:
    """Complete StreamManager configuration"""
    kafka: KafkaConfig = field(default_factory=KafkaConfig)
    throttling: ThrottlingConfig = field(default_factory=ThrottlingConfig)
    queue_max_size: int = 10000
    queue_overflow_strategy: str = "drop_oldest"
    enable_dlq: bool = True
    enable_metrics: bool = True
    metrics_interval_seconds: int = 60
    sources: Dict[str, SourceConfig] = field(default_factory=dict)
    topics: Dict[str, TopicConfig] = field(default_factory=dict)


class ConfigManager:
    """
    Manages configuration loading, validation, and runtime updates
    Supports YAML, JSON, and environment-specific overrides
    """

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path
        self.config: Optional[StreamManagerConfig] = None
        self.env_overrides: Dict[str, Any] = {}

    def load_from_file(self, file_path: str) -> StreamManagerConfig:
        """Load configuration from YAML or JSON file"""
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {file_path}")

        # Determine file type
        suffix = path.suffix.lower()

        if suffix in ['.yaml', '.yml']:
            with open(path, 'r') as f:
                data = yaml.safe_load(f)
        elif suffix == '.json':
            with open(path, 'r') as f:
                data = json.load(f)
        else:
            raise ValueError(f"Unsupported config file type: {suffix}")

        # Parse configuration
        self.config = self._parse_config(data)
        logger.info("Configuration loaded from file", file_path=file_path)

        return self.config

    def load_from_dict(self, data: Dict[str, Any]) -> StreamManagerConfig:
        """Load configuration from dictionary"""
        self.config = self._parse_config(data)
        logger.info("Configuration loaded from dict")
        return self.config

    def _parse_config(self, data: Dict[str, Any]) -> StreamManagerConfig:
        """Parse configuration dictionary into dataclass"""
        # Parse Kafka config
        kafka_data = data.get('kafka', {})
        kafka_config = KafkaConfig(**kafka_data)

        # Parse throttling config
        throttling_data = data.get('throttling', {})
        throttling_config = ThrottlingConfig(**throttling_data)

        # Parse topics
        topics = {}
        for topic_name, topic_data in data.get('topics', {}).items():
            topics[topic_name] = TopicConfig(name=topic_name, **topic_data)

        # Parse sources
        sources = {}
        for source_id, source_data in data.get('sources', {}).items():
            # Parse ingestion config
            ingestion_data = source_data.pop('ingestion', {})
            ingestion_config = IngestionConfig(**ingestion_data)

            sources[source_id] = SourceConfig(
                source_id=source_id,
                ingestion=ingestion_config,
                **source_data
            )

        # Create main config
        config = StreamManagerConfig(
            kafka=kafka_config,
            throttling=throttling_config,
            topics=topics,
            sources=sources,
            queue_max_size=data.get('queue_max_size', 10000),
            queue_overflow_strategy=data.get('queue_overflow_strategy', 'drop_oldest'),
            enable_dlq=data.get('enable_dlq', True),
            enable_metrics=data.get('enable_metrics', True),
            metrics_interval_seconds=data.get('metrics_interval_seconds', 60)
        )

        return config

    def save_to_file(self, file_path: str, format: str = 'yaml'):
        """Save current configuration to file"""
        if not self.config:
            raise ValueError("No configuration loaded")

        # Convert to dict
        config_dict = asdict(self.config)

        path = Path(file_path)

        if format == 'yaml':
            with open(path, 'w') as f:
                yaml.dump(config_dict, f, default_flow_style=False, indent=2)
        elif format == 'json':
            with open(path, 'w') as f:
                json.dump(config_dict, f, indent=2)
        else:
            raise ValueError(f"Unsupported format: {format}")

        logger.info("Configuration saved to file", file_path=file_path, format=format)

    def get_source_config(self, source_id: str) -> Optional[SourceConfig]:
        """Get configuration for specific source"""
        if not self.config:
            return None

        return self.config.sources.get(source_id)

    def update_source_config(self, source_id: str, updates: Dict[str, Any]):
        """Update source configuration at runtime"""
        if not self.config or source_id not in self.config.sources:
            raise ValueError(f"Source not found: {source_id}")

        source_config = self.config.sources[source_id]

        # Update fields
        for key, value in updates.items():
            if hasattr(source_config, key):
                setattr(source_config, key, value)

        logger.info("Source config updated", source_id=source_id, updates=updates)

    def add_env_override(self, key: str, value: Any):
        """Add environment-specific override"""
        self.env_overrides[key] = value
        logger.debug("Environment override added", key=key)

    def apply_env_overrides(self):
        """Apply environment overrides to configuration"""
        if not self.config:
            return

        # Apply overrides based on key path
        for key, value in self.env_overrides.items():
            parts = key.split('.')

            if parts[0] == 'kafka' and hasattr(self.config.kafka, parts[1]):
                setattr(self.config.kafka, parts[1], value)
            elif parts[0] == 'throttling' and hasattr(self.config.throttling, parts[1]):
                setattr(self.config.throttling, parts[1], value)

        logger.info("Environment overrides applied", count=len(self.env_overrides))

    def validate(self) -> Dict[str, Any]:
        """Validate configuration"""
        errors = []
        warnings = []

        if not self.config:
            errors.append("No configuration loaded")
            return {'valid': False, 'errors': errors}

        # Validate Kafka
        if not self.config.kafka.bootstrap_servers:
            errors.append("Kafka bootstrap_servers is required")

        # Validate throttling
        if self.config.throttling.min_send_rate > self.config.throttling.max_send_rate:
            errors.append("min_send_rate cannot be greater than max_send_rate")

        # Validate sources
        if not self.config.sources:
            warnings.append("No sources configured")

        for source_id, source in self.config.sources.items():
            if source.ingestion.mode not in ['batch', 'real_time', 'continuous_streaming']:
                errors.append(f"Invalid ingestion mode for {source_id}: {source.ingestion.mode}")

        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }

    def get_default_config(self) -> StreamManagerConfig:
        """Get default configuration"""
        return StreamManagerConfig()

    def export_example_config(self, file_path: str):
        """Export example configuration file"""
        example_config = {
            'kafka': {
                'bootstrap_servers': 'localhost:9092',
                'compression_type': 'gzip',
                'batch_size': 500
            },
            'throttling': {
                'enabled': True,
                'target_consumer_lag': 1000,
                'critical_consumer_lag': 5000
            },
            'queue_max_size': 10000,
            'queue_overflow_strategy': 'drop_oldest',
            'enable_dlq': True,
            'topics': {
                'wildfire-weather-data': {
                    'partitions': 8,
                    'retention_ms': 259200000  # 3 days
                },
                'wildfire-iot-sensors': {
                    'partitions': 12,
                    'retention_ms': 604800000  # 7 days
                }
            },
            'sources': {
                'noaa_stations_california': {
                    'source_type': 'noaa_weather',
                    'enabled': True,
                    'topic': 'wildfire-weather-data',
                    'ingestion': {
                        'mode': 'continuous_streaming',
                        'polling_interval_seconds': 30,
                        'buffer_size': 100
                    }
                },
                'iot_purpleair_network': {
                    'source_type': 'iot_sensor',
                    'enabled': True,
                    'topic': 'wildfire-iot-sensors',
                    'ingestion': {
                        'mode': 'continuous_streaming',
                        'polling_interval_seconds': 60,
                        'buffer_size': 200
                    }
                }
            }
        }

        path = Path(file_path)
        suffix = path.suffix.lower()

        if suffix in ['.yaml', '.yml']:
            with open(path, 'w') as f:
                yaml.dump(example_config, f, default_flow_style=False, indent=2)
        else:
            with open(path, 'w') as f:
                json.dump(example_config, f, indent=2)

        logger.info("Example configuration exported", file_path=file_path)
