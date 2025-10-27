"""
Refactored StreamManager v2.0
Integrates all modular components: ProducerWrapper, IngestionModes, ThrottlingManager,
APIClient, QueueManager, TopicResolver, and Configuration Management
"""

import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from dataclasses import asdict
import structlog

try:
    from .kafka_producer import KafkaDataProducer
    from .producer_wrapper import ProducerWrapper
    from .ingestion_modes import IngestionModeFactory, IngestionMode
    from .throttling_manager import ThrottlingManager
    from .api_client import ConnectorAPIClient, BatchAPIClient
    from .queue_manager import QueueManager, MessagePriority, PriorityQueueConsumer
    from .topic_resolver import TopicResolver
    from .stream_config import StreamManagerConfig, ConfigManager
    from .dead_letter_queue import DeadLetterQueue
    from .backpressure_manager import BackpressureManager
except ImportError:
    from kafka_producer import KafkaDataProducer
    from producer_wrapper import ProducerWrapper
    from ingestion_modes import IngestionModeFactory, IngestionMode
    from throttling_manager import ThrottlingManager
    from api_client import ConnectorAPIClient, BatchAPIClient
    from queue_manager import QueueManager, MessagePriority, PriorityQueueConsumer
    from topic_resolver import TopicResolver
    from stream_config import StreamManagerConfig, ConfigManager
    from dead_letter_queue import DeadLetterQueue
    from backpressure_manager import BackpressureManager

logger = structlog.get_logger()


class StreamManagerV2:
    """
    Refactored StreamManager with modular components
    Orchestrates all streaming components with clear separation of concerns
    """

    def __init__(
        self,
        config: StreamManagerConfig,
        connectors: Optional[Dict[str, Any]] = None
    ):
        self.config = config
        self.connectors = connectors or {}
        self.is_started = False

        # Core components (initialized in start())
        self.kafka_producer: Optional[KafkaDataProducer] = None
        self.producer_wrapper: Optional[ProducerWrapper] = None
        self.throttle_manager: Optional[ThrottlingManager] = None
        self.queue_manager: Optional[QueueManager] = None
        self.queue_consumer: Optional[PriorityQueueConsumer] = None
        self.topic_resolver: Optional[TopicResolver] = None
        self.dlq: Optional[DeadLetterQueue] = None
        self.backpressure_manager: Optional[BackpressureManager] = None

        # Stream management
        self.api_clients: Dict[str, Any] = {}
        self.ingestion_modes: Dict[str, IngestionMode] = {}
        self.active_streams: Dict[str, Dict[str, Any]] = {}

        # Metrics
        self.start_time: Optional[datetime] = None
        self.total_messages_processed = 0
        self.total_messages_failed = 0

        logger.info(
            "StreamManager V2 initialized",
            sources_configured=len(config.sources),
            throttling_enabled=config.throttling.enabled
        )

    async def start(self):
        """Initialize and start all components"""
        if self.is_started:
            logger.warning("StreamManager already started")
            return

        logger.info("Starting StreamManager V2 with all components")

        # 1. Initialize Kafka Producer
        self.kafka_producer = KafkaDataProducer(
            bootstrap_servers=self.config.kafka.bootstrap_servers,
            client_id=self.config.kafka.client_id
        )
        await self.kafka_producer.start()
        logger.info("✅ Kafka producer started")

        # 2. Initialize Dead Letter Queue
        if self.config.enable_dlq:
            self.dlq = DeadLetterQueue()
            logger.info("✅ DLQ initialized")

        # 3. Initialize ProducerWrapper
        self.producer_wrapper = ProducerWrapper(
            kafka_producer=self.kafka_producer,
            dlq=self.dlq,
            max_retries=self.config.kafka.max_retries,
            retry_backoff_base=self.config.kafka.retry_backoff_base,
            batch_size=self.config.kafka.batch_size
        )
        logger.info("✅ ProducerWrapper initialized")

        # 4. Initialize ThrottlingManager
        if self.config.throttling.enabled:
            self.throttle_manager = ThrottlingManager(
                min_send_rate=self.config.throttling.min_send_rate,
                max_send_rate=self.config.throttling.max_send_rate,
                target_consumer_lag=self.config.throttling.target_consumer_lag,
                critical_consumer_lag=self.config.throttling.critical_consumer_lag,
                adjustment_factor=self.config.throttling.adjustment_factor
            )
            logger.info("✅ ThrottlingManager initialized")

        # 5. Initialize BackpressureManager (for compatibility)
        self.backpressure_manager = BackpressureManager()
        logger.info("✅ BackpressureManager initialized")

        # 6. Initialize QueueManager
        self.queue_manager = QueueManager(
            max_size=self.config.queue_max_size,
            overflow_strategy=self.config.queue_overflow_strategy,
            enable_priorities=True
        )
        logger.info("✅ QueueManager initialized")

        # 7. Initialize TopicResolver
        self.topic_resolver = TopicResolver()

        # Add custom topic mappings from config
        for source_id, source_config in self.config.sources.items():
            if source_config.topic:
                self.topic_resolver.add_custom_mapping(source_id, source_config.topic)

        logger.info("✅ TopicResolver initialized")

        # 8. Start Queue Consumer
        self.queue_consumer = PriorityQueueConsumer(
            queue_manager=self.queue_manager,
            processor=self,  # StreamManager implements process() method
            batch_size=self.config.kafka.batch_size,
            batch_timeout=5.0
        )
        await self.queue_consumer.start()
        logger.info("✅ Queue consumer started")

        self.is_started = True
        self.start_time = datetime.now(timezone.utc)

        logger.info(
            "🚀 StreamManager V2 fully started",
            components_active=8
        )

    async def stop(self):
        """Stop all components gracefully"""
        logger.info("Stopping StreamManager V2")

        # Stop queue consumer
        if self.queue_consumer:
            await self.queue_consumer.stop()

        # Stop all active streams
        for source_id in list(self.active_streams.keys()):
            await self.stop_stream(source_id)

        # Stop ingestion modes
        for mode in self.ingestion_modes.values():
            await mode.stop()

        # Flush queue
        if self.queue_manager:
            remaining = await self.queue_manager.size()
            if remaining > 0:
                logger.warning(f"Flushing {remaining} remaining messages")
                # Process remaining messages with timeout
                timeout = 30
                start = asyncio.get_event_loop().time()
                while await self.queue_manager.size() > 0:
                    if asyncio.get_event_loop().time() - start > timeout:
                        logger.error("Timeout while flushing queue")
                        break
                    await asyncio.sleep(0.5)

        # Stop Kafka producer
        if self.kafka_producer:
            await self.kafka_producer.stop()

        self.is_started = False
        logger.info("StreamManager V2 stopped")

    async def start_stream(
        self,
        source_id: str,
        connector: Optional[Any] = None
    ) -> str:
        """
        Start streaming for a configured source

        Args:
            source_id: Source identifier from config
            connector: Connector instance (optional, uses self.connectors if not provided)
        """
        if not self.is_started:
            raise RuntimeError("StreamManager not started. Call start() first.")

        if source_id not in self.config.sources:
            raise ValueError(f"Source not configured: {source_id}")

        if source_id in self.active_streams:
            logger.warning(f"Stream already active: {source_id}")
            return self.active_streams[source_id]['stream_id']

        source_config = self.config.sources[source_id]

        if not source_config.enabled:
            raise ValueError(f"Source is disabled: {source_id}")

        # Get connector
        if connector is None:
            connector = self.connectors.get(source_config.source_type)
            if connector is None:
                raise ValueError(f"No connector available for source type: {source_config.source_type}")

        logger.info(
            "Starting stream",
            source_id=source_id,
            mode=source_config.ingestion.mode,
            topic=source_config.topic
        )

        # Create API Client
        api_client = ConnectorAPIClient(
            source_id=source_id,
            connector=connector,
            rate_limit_per_minute=source_config.rate_limit_per_minute,
            timeout_seconds=source_config.timeout_seconds,
            cache_ttl_seconds=source_config.cache_ttl_seconds
        )
        self.api_clients[source_id] = api_client

        # Create Ingestion Mode
        mode_config = asdict(source_config.ingestion)
        ingestion_mode = IngestionModeFactory.create_mode(
            source_config.ingestion.mode,
            mode_config
        )

        # Define data fetcher
        async def fetch_data(**kwargs):
            """Fetch data via API client"""
            result = await api_client.poll(**kwargs)
            if result['success']:
                return result['data']
            return []

        # Define data processor with throttling integration
        async def process_data(data: List[Dict[str, Any]]):
            """Process data with throttling and queueing"""
            if not data:
                return {'success': True, 'records': 0}

            # Check throttling
            if self.throttle_manager:
                # Get current consumer lag (mock for now - should query Kafka)
                consumer_lag = await self._get_consumer_lag(source_id)

                throttle_result = await self.throttle_manager.check_and_throttle(
                    consumer_lag=consumer_lag,
                    source_id=source_id
                )

                if throttle_result['action'] in ['throttle_moderate', 'throttle_critical']:
                    logger.info(
                        "Throttling applied",
                        source_id=source_id,
                        action=throttle_result['action'],
                        delay=throttle_result['delay_seconds'],
                        consumer_lag=consumer_lag
                    )
                    await asyncio.sleep(throttle_result['delay_seconds'])

            # Enqueue messages with priority
            priority = self._determine_priority(source_id)
            enqueued_count = 0
            failed_count = 0

            for record in data:
                result = await self.queue_manager.enqueue(
                    data=record,
                    priority=priority,
                    source_id=source_id
                )
                if result['success']:
                    enqueued_count += 1
                else:
                    failed_count += 1

            logger.debug(
                "Data enqueued",
                source_id=source_id,
                enqueued=enqueued_count,
                failed=failed_count
            )

            return {
                'success': failed_count == 0,
                'records': enqueued_count,
                'failed': failed_count
            }

        # Start ingestion mode
        stream_id = await ingestion_mode.start(
            data_fetcher=fetch_data,
            data_processor=process_data,
            mode_id=source_id
        )

        # Store stream metadata
        self.active_streams[source_id] = {
            'stream_id': stream_id,
            'source_id': source_id,
            'source_type': source_config.source_type,
            'mode': source_config.ingestion.mode,
            'topic': source_config.topic or self.topic_resolver.resolve_topic(source_id),
            'started_at': datetime.now(timezone.utc),
            'api_client': api_client,
            'ingestion_mode': ingestion_mode
        }

        self.ingestion_modes[source_id] = ingestion_mode

        logger.info(
            "✅ Stream started successfully",
            source_id=source_id,
            stream_id=stream_id
        )

        return stream_id

    async def stop_stream(self, source_id: str) -> bool:
        """Stop a specific stream"""
        if source_id not in self.active_streams:
            logger.warning(f"Stream not active: {source_id}")
            return False

        # Stop ingestion mode
        if source_id in self.ingestion_modes:
            await self.ingestion_modes[source_id].stop()
            del self.ingestion_modes[source_id]

        # Remove from active streams
        del self.active_streams[source_id]
        if source_id in self.api_clients:
            del self.api_clients[source_id]

        logger.info("Stream stopped", source_id=source_id)
        return True

    async def process(self, data_batch: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Process batch from queue (called by PriorityQueueConsumer)
        Integrates with ProducerWrapper and ThrottlingManager
        """
        if not data_batch:
            return {'success': True, 'records': 0}

        # Extract source info from first message
        first_message = data_batch[0] if data_batch else {}
        source_id = first_message.get('source_id', 'unknown')

        # Resolve topic
        topic = self.topic_resolver.resolve_topic(
            source_id=source_id,
            data=first_message
        )

        # Determine source type
        source_type = self._extract_source_type(source_id)

        # Send with retry via ProducerWrapper
        result = await self.producer_wrapper.send_with_retry(
            data=data_batch,
            source_type=source_type,
            source_id=source_id,
            topic=topic
        )

        # Update metrics
        if result['success']:
            self.total_messages_processed += result['records_sent']
        else:
            self.total_messages_failed += result['records_failed']

        return result

    def _determine_priority(self, source_id: str) -> MessagePriority:
        """Determine message priority based on source"""
        source_lower = source_id.lower()

        # Critical: alerts and emergency data
        if 'alert' in source_lower or 'emergency' in source_lower:
            return MessagePriority.CRITICAL

        # High: real-time fire detection
        if 'firms' in source_lower or 'fire' in source_lower:
            return MessagePriority.HIGH

        # Normal: weather and IoT
        if 'weather' in source_lower or 'iot' in source_lower or 'sensor' in source_lower:
            return MessagePriority.NORMAL

        # Low: batch and historical data
        return MessagePriority.LOW

    def _extract_source_type(self, source_id: str) -> str:
        """Extract source type from source ID"""
        source_lower = source_id.lower()

        if source_lower.startswith(('firms_', 'landsat_nrt')):
            return 'nasa_firms'
        elif source_lower.startswith(('noaa_', 'wx_')):
            return 'weather'
        elif source_lower.startswith('iot_'):
            return 'sensor'
        elif source_lower.startswith('sat_'):
            return 'satellite'
        else:
            return 'data'

    async def _get_consumer_lag(self, source_id: str) -> int:
        """
        Get consumer lag for source topic

        TODO: Implement actual Kafka consumer lag monitoring
        For now, returns mock value based on queue size
        """
        queue_size = await self.queue_manager.size()

        # Estimate lag based on queue utilization
        utilization = queue_size / self.config.queue_max_size

        if utilization > 0.9:
            return 5000  # Critical
        elif utilization > 0.7:
            return 2000  # High
        elif utilization > 0.5:
            return 800   # Moderate
        else:
            return 100   # Low

    async def get_all_metrics(self) -> Dict[str, Any]:
        """Get comprehensive metrics from all components"""
        metrics = {
            'stream_manager': {
                'is_started': self.is_started,
                'start_time': self.start_time.isoformat() if self.start_time else None,
                'uptime_seconds': (
                    (datetime.now(timezone.utc) - self.start_time).total_seconds()
                    if self.start_time else 0
                ),
                'active_streams': len(self.active_streams),
                'total_messages_processed': self.total_messages_processed,
                'total_messages_failed': self.total_messages_failed,
                'success_rate': (
                    self.total_messages_processed /
                    (self.total_messages_processed + self.total_messages_failed)
                    if (self.total_messages_processed + self.total_messages_failed) > 0
                    else 1.0
                )
            },
            'producer_wrapper': await self.producer_wrapper.get_metrics() if self.producer_wrapper else {},
            'throttle_manager': await self.throttle_manager.get_metrics() if self.throttle_manager else {},
            'queue_manager': await self.queue_manager.get_metrics() if self.queue_manager else {},
            'queue_consumer': await self.queue_consumer.get_metrics() if self.queue_consumer else {},
            'topic_resolver': self.topic_resolver.get_metrics() if self.topic_resolver else {},
            'active_streams': {
                source_id: {
                    'stream_id': stream['stream_id'],
                    'mode': stream['mode'],
                    'topic': stream['topic'],
                    'uptime_seconds': (
                        (datetime.now(timezone.utc) - stream['started_at']).total_seconds()
                    )
                }
                for source_id, stream in self.active_streams.items()
            }
        }

        # Add per-mode metrics
        metrics['ingestion_modes'] = {}
        for source_id, mode in self.ingestion_modes.items():
            metrics['ingestion_modes'][source_id] = await mode.get_metrics()

        # Add per-client metrics
        metrics['api_clients'] = {}
        for source_id, client in self.api_clients.items():
            metrics['api_clients'][source_id] = await client.get_metrics()

        return metrics

    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check"""
        health = {
            'healthy': True,
            'components': {},
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

        # Check Kafka producer
        if self.kafka_producer:
            kafka_health = await self.kafka_producer.health_check()
            health['components']['kafka_producer'] = {
                'healthy': kafka_health,
                'status': 'healthy' if kafka_health else 'unhealthy'
            }
            if not kafka_health:
                health['healthy'] = False

        # Check queue
        if self.queue_manager:
            queue_size = await self.queue_manager.size()
            queue_full = await self.queue_manager.is_full()
            health['components']['queue_manager'] = {
                'healthy': not queue_full,
                'size': queue_size,
                'utilization': queue_size / self.config.queue_max_size
            }
            if queue_full:
                health['healthy'] = False

        # Check active streams
        health['components']['streams'] = {
            'count': len(self.active_streams),
            'healthy': len(self.active_streams) > 0
        }

        return health

    def add_connector(self, source_type: str, connector: Any):
        """Add a connector for a source type"""
        self.connectors[source_type] = connector
        logger.info("Connector added", source_type=source_type)

    def get_active_streams(self) -> Dict[str, Any]:
        """Get info about active streams"""
        return {
            source_id: {
                'stream_id': stream['stream_id'],
                'source_type': stream['source_type'],
                'mode': stream['mode'],
                'topic': stream['topic'],
                'started_at': stream['started_at'].isoformat()
            }
            for source_id, stream in self.active_streams.items()
        }
