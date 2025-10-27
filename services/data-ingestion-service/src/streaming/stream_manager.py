"""
Integrated Stream Manager with Refactored Architecture
Backward-compatible API using modular components internally

This implementation integrates all 8 refactoring requirements:
1. Separate Concerns - 7 composable components
2. Plug-and-Play Ingestion Modes - Strategy pattern
3. Improved Backpressure - Exponential backoff + sliding window
4. Separate Polling from Sending - Queue decoupling
5. Monitoring & Metrics - Comprehensive observability
6. Configuration Management - YAML/JSON support
7. Error Handling - Robust retry + DLQ
8. Future Scalability - Horizontal scaling ready
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import asdict
import structlog

# Import existing dependencies
try:
    from .kafka_producer import KafkaDataProducer
    from ..models.ingestion import StreamingConfig
except ImportError:
    from kafka_producer import KafkaDataProducer
    from models.ingestion import StreamingConfig

# Import refactored components
try:
    from .producer_wrapper import ProducerWrapper
    from .queue_manager import QueueManager, PriorityQueueConsumer, MessagePriority
    from .throttling_manager import ThrottlingManager
    from .ingestion_modes import IngestionModeFactory
    from .api_client import ConnectorAPIClient
    from .topic_resolver import TopicResolver
    from .stream_config import ConfigManager, StreamManagerConfig, KafkaConfig, ThrottlingConfig
    from .critical_alert_handler import CriticalAlertHandler
except ImportError:
    # Fallback if refactored components not available
    ProducerWrapper = None
    QueueManager = None
    PriorityQueueConsumer = None
    MessagePriority = None
    ThrottlingManager = None
    IngestionModeFactory = None
    ConnectorAPIClient = None
    TopicResolver = None
    ConfigManager = None
    StreamManagerConfig = None
    KafkaConfig = None
    ThrottlingConfig = None
    CriticalAlertHandler = None

logger = structlog.get_logger()


class KafkaProcessor:
    """Processes messages from queue and sends to Kafka via ProducerWrapper"""

    def __init__(self, stream_manager):
        self.manager = stream_manager

    async def process(self, data_batch: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Process batch of messages from queue
        Called by PriorityQueueConsumer
        """
        if not data_batch:
            return {'success': True, 'records': 0}

        try:
            # Extract source_id and source_type from first message
            first_msg = data_batch[0]
            source_id = first_msg.get('source_id', 'unknown')
            source_type = first_msg.get('source_type', 'data')

            # Resolve topic using TopicResolver
            topic = self.manager.topic_resolver.resolve_topic(source_id=source_id, data=first_msg)

            # Send via ProducerWrapper with retry
            result = await self.manager.producer_wrapper.send_with_retry(
                data=data_batch,
                source_type=source_type,
                source_id=source_id,
                topic=topic
            )

            # Update metrics (thread-safe)
            if result['success']:
                async with self.manager._metrics_lock:
                    self.manager.metrics['messages_sent'] += result['records_sent']
                    self.manager.metrics['messages_failed'] += result.get('records_failed', 0)

            return result

        except Exception as e:
            logger.error("Batch processing failed", error=str(e), batch_size=len(data_batch))
            return {'success': False, 'error': str(e), 'records_failed': len(data_batch)}


class StreamManager:
    """
    Universal stream manager with refactored architecture
    Backward-compatible API for existing code
    """

    def __init__(
        self,
        kafka_producer: KafkaDataProducer,
        config_file: Optional[str] = None,
        buffer_manager=None,
        critical_alert_handler=None
    ):
        """
        Initialize StreamManager with refactored components

        Args:
            kafka_producer: Existing KafkaDataProducer instance
            config_file: Optional path to YAML/JSON configuration
            buffer_manager: Optional BufferManager instance for offline buffering
            critical_alert_handler: Optional CriticalAlertHandler instance for <100ms latency alerts
        """
        self.kafka_producer = kafka_producer
        self.active_streams: Dict[str, Dict[str, Any]] = {}

        # Thread-safe metrics with lock
        self._metrics_lock = asyncio.Lock()
        self.metrics = {
            'messages_sent': 0,
            'messages_failed': 0,
            'streams_started': 0,
            'streams_failed': 0
        }

        # Background task tracking
        self._background_tasks: List[asyncio.Task] = []

        # Load configuration
        self.config = self._load_config(config_file)

        # Initialize refactored components
        self._initialize_components()

        # Set buffer manager and critical alert handler (passed from main.py)
        self.buffer_manager = buffer_manager
        self.critical_alert_handler = critical_alert_handler
        self.critical_alert_sources = [
            'evacuation_alerts',
            'first_responder_updates',
            'imminent_threat_detection',
            'emergency_broadcast_system',
            'critical_fire_alerts',
            'life_safety_warnings'
        ]

        logger.info("StreamManager initialized with refactored architecture",
                   throttling_enabled=self.config.throttling.enabled if hasattr(self.config, 'throttling') else False,
                   queue_size=self.config.queue_max_size if hasattr(self.config, 'queue_max_size') else 10000,
                   critical_sources=len(self.critical_alert_sources),
                   buffer_manager_enabled=buffer_manager is not None,
                   critical_alert_handler_enabled=critical_alert_handler is not None)

    def _load_config(self, config_file: Optional[str]) -> StreamManagerConfig:
        """Load configuration from file or use defaults"""
        if config_file and ConfigManager:
            try:
                config_manager = ConfigManager()
                config = config_manager.load_from_file(config_file)
                validation = config_manager.validate()
                if not validation['valid']:
                    logger.warning("Configuration validation warnings", errors=validation['errors'])
                logger.info("Configuration loaded from file", config_file=config_file)
                return config
            except Exception as e:
                logger.warning("Failed to load config file, using defaults", error=str(e))

        # Default configuration for backward compatibility
        if StreamManagerConfig and KafkaConfig and ThrottlingConfig:
            return StreamManagerConfig(
                kafka=KafkaConfig(
                    bootstrap_servers="localhost:9092",
                    batch_size=500,
                    max_retries=3
                ),
                throttling=ThrottlingConfig(
                    enabled=False  # Disabled by default for backward compat
                ),
                queue_max_size=10000,
                enable_dlq=True,
                sources={}
            )
        else:
            # Minimal fallback if refactored components unavailable
            class SimpleConfig:
                def __init__(self):
                    self.queue_max_size = 10000
                    self.enable_dlq = True
            return SimpleConfig()

    def _initialize_components(self):
        """Initialize all refactored components"""
        try:
            # 1. Initialize ProducerWrapper
            if ProducerWrapper:
                self.producer_wrapper = ProducerWrapper(
                    kafka_producer=self.kafka_producer,
                    dlq=None,  # DLQ initialized separately if enabled
                    max_retries=getattr(self.config.kafka, 'max_retries', 3) if hasattr(self.config, 'kafka') else 3,
                    retry_backoff_base=getattr(self.config.kafka, 'retry_backoff_base', 2.0) if hasattr(self.config, 'kafka') else 2.0,
                    batch_size=getattr(self.config.kafka, 'batch_size', 500) if hasattr(self.config, 'kafka') else 500
                )
                logger.info("ProducerWrapper initialized")
            else:
                self.producer_wrapper = None
                logger.warning("ProducerWrapper not available, using fallback")

            # 2. Initialize ThrottlingManager (if enabled)
            if ThrottlingManager and hasattr(self.config, 'throttling') and self.config.throttling.enabled:
                self.throttle_manager = ThrottlingManager(
                    min_send_rate=self.config.throttling.min_send_rate,
                    max_send_rate=self.config.throttling.max_send_rate,
                    target_consumer_lag=self.config.throttling.target_consumer_lag,
                    critical_consumer_lag=self.config.throttling.critical_consumer_lag,
                    adjustment_factor=self.config.throttling.adjustment_factor,
                    window_size_seconds=getattr(self.config.throttling, 'window_size_seconds', 60)
                )
                logger.info("ThrottlingManager initialized and enabled")
            else:
                self.throttle_manager = None
                logger.info("ThrottlingManager disabled")

            # 3. Initialize QueueManager
            if QueueManager:
                queue_max_size = getattr(self.config, 'queue_max_size', 10000)
                queue_overflow = getattr(self.config, 'queue_overflow_strategy', 'drop_oldest')
                self.queue_manager = QueueManager(
                    max_size=queue_max_size,
                    overflow_strategy=queue_overflow,
                    enable_priorities=True
                )
                logger.info("QueueManager initialized", max_size=queue_max_size)
            else:
                self.queue_manager = None
                logger.warning("QueueManager not available")

            # 4. Initialize TopicResolver
            if TopicResolver:
                custom_mappings = getattr(self.config, 'custom_topic_mappings', {})
                self.topic_resolver = TopicResolver(
                    custom_mappings=custom_mappings
                )
                logger.info("TopicResolver initialized")
            else:
                self.topic_resolver = None
                logger.warning("TopicResolver not available, using fallback")

            # 5. Start Queue Consumer
            if PriorityQueueConsumer and self.queue_manager:
                processor = KafkaProcessor(self)
                self.queue_consumer = PriorityQueueConsumer(
                    queue_manager=self.queue_manager,
                    processor=processor,
                    batch_size=getattr(self.config.kafka, 'batch_size', 500) if hasattr(self.config, 'kafka') else 500,
                    batch_timeout=5.0
                )
                # Store task reference for lifecycle management
                consumer_task = asyncio.create_task(self.queue_consumer.start())
                self._background_tasks.append(consumer_task)
                logger.info("Queue consumer started")
            else:
                self.queue_consumer = None
                logger.warning("Queue consumer not available")

        except Exception as e:
            logger.error("Failed to initialize components", error=str(e), exc_info=True)
            # Continue with degraded functionality

    async def start_streaming(self, connector, config: StreamingConfig) -> str:
        """
        Start streaming for ANY connector with Kafka integration
        Uses refactored components internally while maintaining API compatibility
        Routes critical sources to direct handler for <1s latency
        """
        stream_id = f"{config.source_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        logger.info("Starting stream with refactored architecture",
                   stream_id=stream_id,
                   source_id=config.source_id,
                   connector_type=type(connector).__name__)

        try:
            # Check if this is a critical alert source requiring <1s latency
            if self._is_critical_alert_source(config.source_id):
                # Route to critical alert handler for direct WebSocket → Kafka
                return await self._start_critical_alert_stream(stream_id, connector, config)

            # Configure Kafka producer for connector if it has set_kafka_producer method
            if hasattr(connector, 'set_kafka_producer') and callable(getattr(connector, 'set_kafka_producer')):
                connector.set_kafka_producer(self.kafka_producer)

            # If refactored components available, use them
            if IngestionModeFactory and ConnectorAPIClient and self.queue_manager:
                await self._start_stream_with_components(stream_id, connector, config)
            else:
                # Fallback to original implementation
                await self._start_stream_fallback(stream_id, connector, config)

            async with self._metrics_lock:
                self.metrics['streams_started'] += 1
            logger.info("Stream started successfully", stream_id=stream_id)
            return stream_id

        except Exception as e:
            async with self._metrics_lock:
                self.metrics['streams_failed'] += 1
            logger.error("Failed to start stream", stream_id=stream_id, error=str(e), exc_info=True)
            raise

    async def _start_stream_with_components(self, stream_id: str, connector, config: StreamingConfig):
        """Start stream using refactored components"""
        # Determine ingestion mode
        mode_type = self._determine_ingestion_mode(config)
        mode_config = self._build_mode_config(config, mode_type)

        # Create ingestion mode
        ingestion_mode = IngestionModeFactory.create_mode(mode_type, mode_config)

        # Create APIClient wrapper
        api_client = ConnectorAPIClient(
            source_id=config.source_id,
            connector=connector,
            fetch_method='fetch_data',  # Try fetch_data first
            rate_limit_per_minute=getattr(config, 'rate_limit_per_minute', 60),
            timeout_seconds=getattr(config, 'timeout_seconds', 30.0),
            cache_ttl_seconds=getattr(config, 'cache_ttl_seconds', 300)
        )

        # Define data fetching function
        async def data_fetcher(**kwargs):
            """Fetch data from API client"""
            try:
                result = await api_client.poll(**kwargs)
                return result.get('data', []) if result.get('success') else []
            except Exception as e:
                logger.error("Data fetcher error", source_id=config.source_id, error=str(e))
                return []

        # Define data processing function with throttling
        async def data_processor(data: List[Dict[str, Any]]):
            """Process and enqueue data with throttling"""
            if not data:
                return {'success': True, 'records': 0}

            try:
                # Throttling check (Requirement 3)
                if self.throttle_manager:
                    consumer_lag = await self._estimate_consumer_lag()
                    throttle_result = await self.throttle_manager.check_and_throttle(
                        consumer_lag=consumer_lag,
                        source_id=config.source_id
                    )

                    if throttle_result['action'] in ['throttle_moderate', 'throttle_critical']:
                        logger.info("Throttling applied",
                                   source_id=config.source_id,
                                   action=throttle_result['action'],
                                   delay=throttle_result['delay_seconds'])
                        await asyncio.sleep(throttle_result['delay_seconds'])

                # Determine priority
                priority = self._determine_priority(config.source_id)

                # Add metadata to all records at once
                source_type = self._extract_source_type(config.source_id)
                timestamp = datetime.now().isoformat()

                for record in data:
                    record['source_id'] = config.source_id
                    record['source_type'] = source_type
                    record['ingestion_timestamp'] = timestamp

                # OPTIMIZATION: Batch enqueue for ultra-low latency (Requirement 4)
                result = await self.queue_manager.enqueue_batch(
                    data_list=data,
                    priority=priority,
                    source_id=config.source_id
                )

                return {'success': result['success'], 'records': result['enqueued']}

            except Exception as e:
                logger.error("Data processor error", source_id=config.source_id, error=str(e))
                return {'success': False, 'error': str(e)}

        # Start ingestion mode (Requirement 2)
        mode_id = await ingestion_mode.start(
            data_fetcher=data_fetcher,
            data_processor=data_processor,
            mode_id=stream_id,
            source_id=config.source_id,
            source_type=self._extract_source_type(config.source_id)
        )

        # Resolve topic
        topic = self.topic_resolver.resolve_topic(config.source_id) if self.topic_resolver else self._determine_kafka_topic(config.source_id)

        # Store stream metadata
        self.active_streams[stream_id] = {
            'stream_id': stream_id,
            'source_id': config.source_id,
            'mode': ingestion_mode,
            'mode_id': mode_id,
            'api_client': api_client,
            'config': config,
            'status': 'active',
            'start_time': datetime.now(),
            'kafka_topic': topic
        }

        logger.info("Stream using refactored components",
                   stream_id=stream_id,
                   mode=mode_type,
                   topic=topic)

    async def _start_stream_fallback(self, stream_id: str, connector, config: StreamingConfig):
        """Fallback to original implementation if components unavailable"""
        # Start connector's native streaming
        connector_stream_id = await connector.start_streaming(config)

        # Create stream metadata
        stream_meta = {
            'stream_id': stream_id,
            'connector_stream_id': connector_stream_id,
            'source_id': config.source_id,
            'connector': connector,
            'config': config,
            'status': 'active',
            'start_time': datetime.now(),
            'kafka_topic': self._determine_kafka_topic(config.source_id)
        }

        self.active_streams[stream_id] = stream_meta

        # Start Kafka bridge task
        asyncio.create_task(self._bridge_to_kafka_fallback(stream_meta))

    async def _bridge_to_kafka_fallback(self, stream_meta: Dict[str, Any]):
        """Fallback bridge implementation"""
        stream_id = stream_meta['stream_id']
        connector = stream_meta['connector']
        config = stream_meta['config']
        source_id = stream_meta['source_id']

        polling_interval = getattr(config, 'polling_interval_seconds', None) or self._get_polling_interval(source_id)

        try:
            while stream_meta['status'] == 'active':
                data_batch = None

                # Try different connector methods
                if hasattr(connector, 'get_stream_data'):
                    try:
                        data_batch = await connector.get_stream_data(stream_meta.get('connector_stream_id'))
                    except Exception:
                        pass

                if not data_batch and hasattr(connector, 'fetch_data'):
                    try:
                        data_batch = await connector.fetch_data(config)
                    except Exception:
                        pass

                # Send data to Kafka
                if data_batch and len(data_batch) > 0:
                    try:
                        success = await self.kafka_producer.send_batch_data(
                            data_batch,
                            source_type=self._extract_source_type(source_id),
                            source_id=source_id
                        )

                        if success:
                            stream_meta['last_data_time'] = datetime.now()
                            stream_meta['total_records'] = stream_meta.get('total_records', 0) + len(data_batch)
                            async with self._metrics_lock:
                                self.metrics['messages_sent'] += len(data_batch)
                    except Exception as e:
                        logger.error("Error sending data to Kafka", stream_id=stream_id, error=str(e))
                        async with self._metrics_lock:
                            self.metrics['messages_failed'] += len(data_batch)

                await asyncio.sleep(polling_interval)

        except Exception as e:
            logger.error("Stream bridge error", stream_id=stream_id, error=str(e))
            stream_meta['status'] = 'error'

    def _determine_ingestion_mode(self, config: StreamingConfig) -> str:
        """Determine ingestion mode from config"""
        # Check if mode specified in config
        if hasattr(config, 'ingestion_mode'):
            return config.ingestion_mode

        # Check polling interval to determine mode
        polling_interval = getattr(config, 'polling_interval_seconds', 60)

        if polling_interval <= 30:
            return 'continuous_streaming'
        elif polling_interval <= 300:
            return 'real_time'
        else:
            return 'batch'

    def _build_mode_config(self, config: StreamingConfig, mode_type: str) -> Dict[str, Any]:
        """Build configuration for ingestion mode"""
        polling_interval = getattr(config, 'polling_interval_seconds', None) or self._get_polling_interval(config.source_id)

        if mode_type == 'batch':
            return {
                'batch_size': getattr(config, 'batch_size', 1000),
                'schedule_interval_seconds': polling_interval
            }
        elif mode_type == 'real_time':
            return {
                'polling_interval_seconds': polling_interval,
                'max_records_per_poll': getattr(config, 'max_records_per_poll', 500)
            }
        elif mode_type == 'continuous_streaming':
            return {
                'polling_interval_seconds': polling_interval,
                'buffer_size': getattr(config, 'buffer_size', 100),
                'buffer_flush_interval_seconds': getattr(config, 'buffer_flush_interval_seconds', 5)
            }
        else:
            return {'polling_interval_seconds': polling_interval}

    def _determine_priority(self, source_id: str) -> 'MessagePriority':
        """Determine message priority based on source"""
        if not MessagePriority:
            return None

        source_lower = source_id.lower()

        # Critical: Alerts and emergencies
        if 'alert' in source_lower or 'emergency' in source_lower or 'warning' in source_lower:
            return MessagePriority.CRITICAL

        # High: Fire detection, weather
        elif source_lower.startswith(('firms_', 'landsat_nrt', 'noaa_', 'wx_')):
            return MessagePriority.HIGH

        # Normal: IoT sensors
        elif source_lower.startswith('iot_'):
            return MessagePriority.NORMAL

        # Low: Everything else
        else:
            return MessagePriority.LOW

    async def _estimate_consumer_lag(self) -> int:
        """Estimate consumer lag based on queue utilization"""
        if not self.queue_manager:
            return 0

        try:
            queue_size = await self.queue_manager.size()
            queue_max = getattr(self.config, 'queue_max_size', 10000)
            utilization = queue_size / queue_max

            # Map utilization to estimated lag
            if utilization > 0.9:
                return 5000  # Critical
            elif utilization > 0.7:
                return 2000  # High
            elif utilization > 0.5:
                return 800   # Moderate
            else:
                return 100   # Low
        except Exception:
            return 0

    async def stop_stream(self, stream_id: str) -> bool:
        """Stop universal stream"""
        if stream_id not in self.active_streams:
            return False

        stream_meta = self.active_streams[stream_id]
        stream_meta['status'] = 'stopped'

        try:
            # Stop ingestion mode if available
            if 'mode' in stream_meta and hasattr(stream_meta['mode'], 'stop'):
                await stream_meta['mode'].stop()

            # Stop connector stream if available
            if 'connector' in stream_meta:
                connector = stream_meta['connector']
                if hasattr(connector, 'stop_streaming'):
                    await connector.stop_streaming(stream_meta.get('connector_stream_id'))
        except Exception as e:
            logger.error("Error stopping stream", stream_id=stream_id, error=str(e))

        # Remove from active streams
        del self.active_streams[stream_id]

        logger.info("Stream stopped", stream_id=stream_id)
        return True

    def _determine_kafka_topic(self, source_id: str) -> str:
        """Determine Kafka topic based on source type"""
        source_lower = source_id.lower()

        # NASA FIRMS
        if source_lower.startswith(('firms_', 'landsat_nrt')):
            return 'wildfire-nasa-firms'
        # Satellite
        elif source_lower.startswith('sat_'):
            return 'wildfire-satellite-data'
        # NOAA/Weather
        elif source_lower.startswith(('noaa_', 'wx_')):
            if 'alert' in source_lower:
                return 'wildfire-weather-alerts'
            return 'wildfire-weather-data'
        # IoT
        elif source_lower.startswith('iot_'):
            return 'wildfire-iot-sensors'
        else:
            return f'wildfire-{source_id.replace("_", "-")}'

    def _extract_source_type(self, source_id: str) -> str:
        """Extract source type from source ID"""
        source_lower = source_id.lower()

        if source_lower.startswith(('firms_', 'landsat_nrt')):
            return 'nasa_firms'
        elif source_lower.startswith('sat_'):
            return 'satellite'
        elif source_lower.startswith(('noaa_', 'wx_')):
            return 'weather'
        elif source_lower.startswith('iot_'):
            return 'sensor'
        else:
            return 'data'

    def _get_polling_interval(self, source_id: str) -> int:
        """Get appropriate polling interval for source"""
        source_lower = source_id.lower()

        # IoT: high frequency
        if source_lower.startswith('iot_'):
            return 30
        # FIRMS: moderate frequency
        elif source_lower.startswith(('firms_', 'landsat_nrt')):
            return 30
        # NOAA alerts: high frequency
        elif source_lower.startswith('noaa_alerts_'):
            return 30
        # NOAA weather: moderate frequency
        elif source_lower.startswith('noaa_'):
            return 30
        # Weather: moderate frequency
        elif source_lower.startswith('wx_'):
            return 30
        # Satellite: low frequency
        elif source_lower.startswith('sat_'):
            return 30
        else:
            return 30  # Default

    def get_active_streams(self) -> Dict[str, Any]:
        """Get all active streams"""
        return {
            stream_id: {
                'source_id': meta['source_id'],
                'status': meta['status'],
                'start_time': meta['start_time'].isoformat(),
                'kafka_topic': meta['kafka_topic'],
                'total_records': meta.get('total_records', 0),
                'last_data_time': meta.get('last_data_time').isoformat() if meta.get('last_data_time') else None
            }
            for stream_id, meta in self.active_streams.items()
        }

    async def start_all_available_streams(self, connectors: Dict[str, Any]) -> Dict[str, Any]:
        """Discover and start streams from all provided connectors"""
        results = {
            'started_streams': [],
            'failed_streams': [],
            'total_sources': 0,
            'successful_streams': 0
        }

        logger.info("Starting streaming from all connectors", connector_count=len(connectors))

        for connector_type, connector in connectors.items():
            try:
                if hasattr(connector, 'get_sources'):
                    sources = await connector.get_sources()
                    results['total_sources'] += len(sources)

                    for source in sources:
                        try:
                            config = StreamingConfig(
                                source_id=source.id,
                                stream_type="real_time",
                                buffer_size=500,
                                batch_interval_seconds=60,
                                polling_interval_seconds=self._get_polling_interval(source.id),
                                max_retries=3,
                                retry_delay_seconds=30
                            )

                            stream_id = await self.start_streaming(connector, config)

                            results['started_streams'].append({
                                'stream_id': stream_id,
                                'source_id': source.id,
                                'source_name': source.name,
                                'connector_type': connector_type,
                                'provider': getattr(source, 'provider', 'Unknown'),
                                'polling_interval': self._get_polling_interval(source.id)
                            })

                            results['successful_streams'] += 1

                        except Exception as e:
                            results['failed_streams'].append({
                                'source_id': source.id,
                                'source_name': source.name,
                                'connector_type': connector_type,
                                'error': str(e)
                            })
                            logger.error("Failed to start stream", source_id=source.id, error=str(e))

            except Exception as e:
                logger.error("Failed to process connector", connector_type=connector_type, error=str(e))

        success_rate = (results['successful_streams'] / results['total_sources'] * 100) if results['total_sources'] > 0 else 0

        logger.info("Stream startup completed",
                   total=results['total_sources'],
                   successful=results['successful_streams'],
                   failed=len(results['failed_streams']),
                   success_rate=f"{success_rate:.1f}%")

        return results

    async def stop_all_streams(self) -> int:
        """Stop all active streams"""
        stopped_count = 0
        stream_ids = list(self.active_streams.keys())

        for stream_id in stream_ids:
            try:
                if await self.stop_stream(stream_id):
                    stopped_count += 1
            except Exception as e:
                logger.error("Error stopping stream", stream_id=stream_id, error=str(e))

        logger.info("Stopped all streams", stopped_count=stopped_count)
        return stopped_count

    async def get_metrics(self) -> Dict[str, Any]:
        """Get comprehensive metrics from all components"""
        metrics = {
            'stream_manager': {
                'active_streams': len(self.active_streams),
                'messages_sent': self.metrics['messages_sent'],
                'messages_failed': self.metrics['messages_failed'],
                'streams_started': self.metrics['streams_started'],
                'streams_failed': self.metrics['streams_failed']
            }
        }

        # Add component metrics if available
        if self.producer_wrapper and hasattr(self.producer_wrapper, 'get_metrics'):
            try:
                metrics['producer_wrapper'] = await self.producer_wrapper.get_metrics()
            except Exception:
                pass

        if self.throttle_manager and hasattr(self.throttle_manager, 'get_metrics'):
            try:
                metrics['throttle_manager'] = await self.throttle_manager.get_metrics()
            except Exception:
                pass

        if self.queue_manager and hasattr(self.queue_manager, 'get_metrics'):
            try:
                metrics['queue_manager'] = await self.queue_manager.get_metrics()
            except Exception:
                pass

        if self.queue_consumer and hasattr(self.queue_consumer, 'get_metrics'):
            try:
                metrics['queue_consumer'] = await self.queue_consumer.get_metrics()
            except Exception:
                pass

        if self.topic_resolver and hasattr(self.topic_resolver, 'get_metrics'):
            try:
                metrics['topic_resolver'] = self.topic_resolver.get_metrics()
            except Exception:
                pass

        return metrics

    async def get_health(self) -> Dict[str, Any]:
        """Get health status of all components"""
        health = {
            'status': 'healthy',
            'components': {}
        }

        all_healthy = True

        # Check ProducerWrapper
        if self.producer_wrapper and hasattr(self.producer_wrapper, 'health_check'):
            try:
                producer_healthy = await self.producer_wrapper.health_check()
                health['components']['producer_wrapper'] = 'healthy' if producer_healthy else 'unhealthy'
                all_healthy = all_healthy and producer_healthy
            except Exception:
                health['components']['producer_wrapper'] = 'unknown'

        # Check QueueManager
        if self.queue_manager:
            try:
                queue_size = await self.queue_manager.size()
                queue_full = await self.queue_manager.is_full()
                health['components']['queue_manager'] = 'unhealthy' if queue_full else 'healthy'
                all_healthy = all_healthy and not queue_full
            except Exception:
                health['components']['queue_manager'] = 'unknown'

        # Check ThrottleManager
        if self.throttle_manager and hasattr(self.throttle_manager, 'is_healthy'):
            try:
                throttle_healthy = self.throttle_manager.is_healthy()
                health['components']['throttle_manager'] = 'healthy' if throttle_healthy else 'unhealthy'
                all_healthy = all_healthy and throttle_healthy
            except Exception:
                health['components']['throttle_manager'] = 'unknown'

        # Check CriticalAlertHandler
        if self.critical_alert_handler and hasattr(self.critical_alert_handler, 'is_healthy'):
            try:
                critical_healthy = self.critical_alert_handler.is_healthy()
                health['components']['critical_alert_handler'] = 'healthy' if critical_healthy else 'unhealthy'
                all_healthy = all_healthy and critical_healthy
            except Exception:
                health['components']['critical_alert_handler'] = 'unknown'

        health['status'] = 'healthy' if all_healthy else 'degraded'
        return health

    def _is_critical_alert_source(self, source_id: str) -> bool:
        """Check if source requires <1s latency critical alert handling"""
        source_lower = source_id.lower()

        # Check against configured critical sources
        for critical_source in self.critical_alert_sources:
            if critical_source.lower() in source_lower:
                return True

        # Check for critical keywords
        critical_keywords = ['evacuation', 'emergency', 'critical', 'life_safety', 'imminent']
        return any(keyword in source_lower for keyword in critical_keywords)

    async def _start_critical_alert_stream(self, stream_id: str, connector, config: StreamingConfig) -> str:
        """
        Start critical alert stream with direct WebSocket → Kafka path
        Bypasses queue for <1s latency
        """
        try:
            # Initialize critical alert handler if not already done
            if not self.critical_alert_handler:
                if not CriticalAlertHandler:
                    logger.warning("CriticalAlertHandler not available, falling back to normal stream")
                    # Fall back to normal streaming
                    return await self.start_streaming(connector, config)

                self.critical_alert_handler = CriticalAlertHandler(
                    kafka_bootstrap_servers=getattr(self.config.kafka, 'bootstrap_servers', 'kafka:29092') if hasattr(self.config, 'kafka') else 'kafka:29092',
                    alert_topic='wildfire-critical-alerts',
                    max_latency_ms=100,
                    heartbeat_interval=30
                )
                await self.critical_alert_handler.start()
                logger.info("Critical alert handler initialized for <1s latency")

            # Check if connector supports WebSocket streaming
            ws_url = None
            if hasattr(connector, 'get_websocket_url'):
                ws_url = await connector.get_websocket_url(config.source_id)
            elif hasattr(config, 'websocket_url'):
                ws_url = config.websocket_url

            if ws_url:
                # Connect WebSocket for real-time streaming
                success = await self.critical_alert_handler.connect_websocket(
                    source_id=config.source_id,
                    ws_url=ws_url,
                    headers=getattr(config, 'websocket_headers', None)
                )

                if success:
                    logger.info(
                        "Critical alert stream started with WebSocket",
                        stream_id=stream_id,
                        source_id=config.source_id,
                        ws_url=ws_url
                    )
                else:
                    logger.warning(
                        "Failed to connect WebSocket, using polling fallback",
                        source_id=config.source_id
                    )
                    # Fall back to polling with direct Kafka send
                    asyncio.create_task(
                        self._poll_critical_alerts(stream_id, connector, config)
                    )
            else:
                # No WebSocket support, use polling with direct Kafka send
                logger.info(
                    "No WebSocket URL available, using polling for critical alerts",
                    source_id=config.source_id
                )
                asyncio.create_task(
                    self._poll_critical_alerts(stream_id, connector, config)
                )

            # Store in active streams
            self.active_streams[stream_id] = {
                'stream_id': stream_id,
                'source_id': config.source_id,
                'type': 'critical_alert',
                'handler': self.critical_alert_handler,
                'config': config,
                'status': 'active',
                'start_time': datetime.now(),
                'kafka_topic': 'wildfire-critical-alerts'
            }

            async with self._metrics_lock:
                self.metrics['streams_started'] += 1

            logger.info(
                "Critical alert stream started successfully",
                stream_id=stream_id,
                source_id=config.source_id
            )

            return stream_id

        except Exception as e:
            logger.error(
                "Failed to start critical alert stream",
                stream_id=stream_id,
                error=str(e),
                exc_info=True
            )
            # Fall back to normal streaming
            return await self.start_streaming(connector, config)

    async def _poll_critical_alerts(self, stream_id: str, connector, config: StreamingConfig):
        """Poll connector for critical alerts and send directly to Kafka"""
        polling_interval = getattr(config, 'polling_interval_seconds', 5)  # Fast polling for critical

        stream_meta = self.active_streams.get(stream_id)
        if not stream_meta:
            return

        while stream_meta['status'] == 'active':
            try:
                # Fetch data from connector
                data = None
                if hasattr(connector, 'fetch_critical_alerts'):
                    data = await connector.fetch_critical_alerts(config)
                elif hasattr(connector, 'fetch_data'):
                    data = await connector.fetch_data(config)

                if data:
                    # Send each alert directly
                    for alert in data:
                        if isinstance(alert, dict):
                            # Add critical metadata
                            alert['stream_id'] = stream_id
                            alert['source_id'] = config.source_id

                            # Send via critical alert handler (bypass queue)
                            success = await self.critical_alert_handler.send_critical_alert(
                                alert_data=alert,
                                source_id=config.source_id
                            )

                            if success:
                                async with self._metrics_lock:
                                    self.metrics['messages_sent'] += 1
                            else:
                                async with self._metrics_lock:
                                    self.metrics['messages_failed'] += 1

                await asyncio.sleep(polling_interval)

            except Exception as e:
                logger.error(
                    "Error polling critical alerts",
                    stream_id=stream_id,
                    error=str(e)
                )
                await asyncio.sleep(polling_interval)

    async def close(self):
        """
        Graceful shutdown - stop all streams and background tasks
        Call this before application shutdown for clean resource cleanup
        """
        logger.info("StreamManager shutdown initiated")

        try:
            # Stop all active streams
            stopped = await self.stop_all_streams()
            logger.info(f"Stopped {stopped} active streams")

            # Stop critical alert handler
            if self.critical_alert_handler:
                try:
                    await self.critical_alert_handler.stop()
                    logger.info("Critical alert handler stopped")
                except Exception as e:
                    logger.error("Error stopping critical alert handler", error=str(e))

            # Stop queue consumer
            if self.queue_consumer:
                await self.queue_consumer.stop()
                logger.info("Queue consumer stopped")

            # Wait for background tasks with timeout
            if self._background_tasks:
                logger.info(f"Waiting for {len(self._background_tasks)} background tasks")
                try:
                    await asyncio.wait_for(
                        asyncio.gather(*self._background_tasks, return_exceptions=True),
                        timeout=30.0
                    )
                    logger.info("All background tasks completed")
                except asyncio.TimeoutError:
                    logger.warning("Background tasks did not complete within timeout")
                    # Cancel remaining tasks
                    for task in self._background_tasks:
                        if not task.done():
                            task.cancel()

            # Clear queue
            if self.queue_manager:
                remaining = await self.queue_manager.size()
                if remaining > 0:
                    logger.warning(f"Clearing {remaining} remaining messages from queue")
                    await self.queue_manager.clear()

            logger.info("StreamManager shutdown complete")

        except Exception as e:
            logger.error("Error during shutdown", error=str(e), exc_info=True)
