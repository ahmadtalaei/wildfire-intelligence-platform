"""
Advanced Backpressure Management for Kafka Streaming
Implements flow control, dynamic throttling, and circuit breakers
Prevents system overload during traffic spikes
"""

import os
import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import statistics

from kafka import KafkaConsumer, KafkaProducer, TopicPartition
from kafka.errors import KafkaError
import aiokafka
from prometheus_client import Gauge, Counter, Histogram, start_http_server
import redis
import psutil
import aiohttp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Metrics
CONSUMER_LAG = Gauge('backpressure_consumer_lag', 'Consumer lag', ['consumer_group', 'topic'])
PROCESSING_RATE = Gauge('backpressure_processing_rate', 'Messages per second', ['consumer_group'])
THROTTLE_LEVEL = Gauge('backpressure_throttle_level', 'Current throttle level (0-1)', ['consumer_group'])
PAUSED_PARTITIONS = Gauge('backpressure_paused_partitions', 'Number of paused partitions', ['topic'])
CIRCUIT_BREAKER_STATE = Gauge('backpressure_circuit_breaker', 'Circuit breaker state', ['service'])
DROPPED_MESSAGES = Counter('backpressure_dropped_messages', 'Messages dropped due to overload', ['topic'])
BACKPRESSURE_EVENTS = Counter('backpressure_events', 'Backpressure events triggered', ['type'])

class BackpressureState(Enum):
    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"
    OVERLOAD = "overload"

class CircuitBreakerState(Enum):
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Rejecting requests
    HALF_OPEN = "half_open"  # Testing recovery

@dataclass
class BackpressurePolicy:
    """Policy for backpressure management"""
    lag_warning_threshold: int = 5000
    lag_critical_threshold: int = 10000
    lag_overload_threshold: int = 50000
    cpu_threshold_percent: float = 80.0
    memory_threshold_percent: float = 85.0
    processing_rate_min: int = 100  # Min messages/sec before throttling
    throttle_factor_min: float = 0.1  # Maximum throttling (90% reduction)
    throttle_factor_max: float = 1.0  # No throttling
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_timeout_seconds: int = 60
    pause_partition_threshold: int = 20000  # Pause partition if lag exceeds this

@dataclass
class ConsumerMetrics:
    """Metrics for a consumer group"""
    group_id: str
    lag: int
    processing_rate: float
    cpu_percent: float
    memory_percent: float
    error_rate: float
    last_updated: datetime = field(default_factory=datetime.now)

@dataclass
class CircuitBreaker:
    """Circuit breaker for a service"""
    service_name: str
    state: CircuitBreakerState = CircuitBreakerState.CLOSED
    failure_count: int = 0
    last_failure: Optional[datetime] = None
    last_state_change: datetime = field(default_factory=datetime.now)

class BackpressureController:
    """
    Advanced backpressure controller for Kafka consumers
    Implements multiple strategies to prevent system overload
    """

    def __init__(self, policy: BackpressurePolicy = None):
        self.policy = policy or BackpressurePolicy()
        self.bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:29092')

        # Redis for state management
        self.redis_client = redis.Redis(
            host=os.getenv('REDIS_HOST', 'redis'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            decode_responses=True
        )

        # Track consumer states
        self.consumer_states: Dict[str, BackpressureState] = {}
        self.throttle_levels: Dict[str, float] = {}
        self.paused_partitions: Dict[str, Set[TopicPartition]] = {}
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}

        # Performance tracking
        self.processing_rates: Dict[str, List[float]] = {}
        self.error_rates: Dict[str, List[float]] = {}

    async def monitor_and_control(self):
        """Main monitoring and control loop"""
        logger.info("Starting Backpressure Controller...")

        # Start metrics server
        start_http_server(9095)

        while True:
            try:
                # Get all active consumer groups
                consumer_groups = await self.get_active_consumer_groups()

                for group_id in consumer_groups:
                    # Collect metrics
                    metrics = await self.collect_consumer_metrics(group_id)

                    # Determine backpressure state
                    state = self.calculate_backpressure_state(metrics)

                    # Apply backpressure strategies
                    await self.apply_backpressure_strategies(group_id, metrics, state)

                    # Update metrics
                    self.update_metrics(group_id, metrics, state)

                # Check circuit breakers
                await self.check_circuit_breakers()

                # Sleep before next iteration
                await asyncio.sleep(5)  # Check every 5 seconds for quick response

            except Exception as e:
                logger.error(f"Error in backpressure control loop: {e}")
                await asyncio.sleep(10)

    async def get_active_consumer_groups(self) -> List[str]:
        """Get list of active consumer groups"""
        # Get from Redis (populated by consumers)
        groups = self.redis_client.smembers('active_consumer_groups')
        return list(groups)

    async def collect_consumer_metrics(self, group_id: str) -> ConsumerMetrics:
        """Collect metrics for a consumer group"""
        # Get lag from Kafka
        lag = await self.get_consumer_lag(group_id)

        # Get processing rate from Redis
        rate_key = f"processing_rate:{group_id}"
        processing_rate = float(self.redis_client.get(rate_key) or 0)

        # Get system metrics
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory_percent = psutil.virtual_memory().percent

        # Get error rate
        error_key = f"error_rate:{group_id}"
        error_rate = float(self.redis_client.get(error_key) or 0)

        return ConsumerMetrics(
            group_id=group_id,
            lag=lag,
            processing_rate=processing_rate,
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            error_rate=error_rate
        )

    async def get_consumer_lag(self, group_id: str) -> int:
        """Get total lag for consumer group"""
        consumer = KafkaConsumer(
            bootstrap_servers=self.bootstrap_servers,
            group_id=f"{group_id}-monitor",
            enable_auto_commit=False
        )

        try:
            # Get all topics for group
            topics = self.redis_client.smembers(f"consumer_group:{group_id}:topics")
            total_lag = 0

            for topic in topics:
                partitions = consumer.partitions_for_topic(topic)
                if not partitions:
                    continue

                for partition in partitions:
                    tp = TopicPartition(topic, partition)

                    # Get committed offset
                    committed = consumer.committed(tp)
                    if committed is None:
                        committed = 0

                    # Get latest offset
                    consumer.assign([tp])
                    consumer.seek_to_end(tp)
                    end_offset = consumer.position(tp)

                    # Calculate lag
                    lag = end_offset - committed
                    total_lag += lag

            return total_lag

        finally:
            consumer.close()

    def calculate_backpressure_state(self, metrics: ConsumerMetrics) -> BackpressureState:
        """Calculate backpressure state based on metrics"""
        # Check lag thresholds
        if metrics.lag > self.policy.lag_overload_threshold:
            return BackpressureState.OVERLOAD
        elif metrics.lag > self.policy.lag_critical_threshold:
            return BackpressureState.CRITICAL
        elif metrics.lag > self.policy.lag_warning_threshold:
            return BackpressureState.WARNING

        # Check resource thresholds
        if (metrics.cpu_percent > self.policy.cpu_threshold_percent or
            metrics.memory_percent > self.policy.memory_threshold_percent):
            return BackpressureState.WARNING

        # Check error rate
        if metrics.error_rate > 0.1:  # More than 10% errors
            return BackpressureState.WARNING

        return BackpressureState.NORMAL

    async def apply_backpressure_strategies(self, group_id: str, metrics: ConsumerMetrics, state: BackpressureState):
        """Apply appropriate backpressure strategies"""
        logger.info(f"Consumer {group_id} state: {state.value}, lag: {metrics.lag}")

        # Update state
        self.consumer_states[group_id] = state

        # Apply strategies based on state
        if state == BackpressureState.NORMAL:
            await self.remove_backpressure(group_id)

        elif state == BackpressureState.WARNING:
            # Mild throttling
            throttle_level = 0.7  # 30% reduction
            await self.apply_throttling(group_id, throttle_level)
            BACKPRESSURE_EVENTS.labels(type='throttle_warning').inc()

        elif state == BackpressureState.CRITICAL:
            # Aggressive throttling
            throttle_level = 0.3  # 70% reduction
            await self.apply_throttling(group_id, throttle_level)

            # Consider pausing some partitions
            await self.selective_partition_pause(group_id, metrics)
            BACKPRESSURE_EVENTS.labels(type='throttle_critical').inc()

        elif state == BackpressureState.OVERLOAD:
            # Emergency measures
            throttle_level = 0.1  # 90% reduction
            await self.apply_throttling(group_id, throttle_level)

            # Pause high-lag partitions
            await self.pause_high_lag_partitions(group_id)

            # Activate circuit breaker
            await self.activate_circuit_breaker(group_id)

            # Consider dropping non-critical messages
            await self.drop_non_critical_messages(group_id)
            BACKPRESSURE_EVENTS.labels(type='overload').inc()

    async def apply_throttling(self, group_id: str, throttle_level: float):
        """Apply throttling to consumer group"""
        throttle_level = max(self.policy.throttle_factor_min,
                            min(throttle_level, self.policy.throttle_factor_max))

        self.throttle_levels[group_id] = throttle_level

        # Store in Redis for consumers to read
        self.redis_client.set(f"throttle:{group_id}", throttle_level)
        self.redis_client.expire(f"throttle:{group_id}", 60)  # Expire in 1 minute

        logger.info(f"Applied throttle level {throttle_level} to {group_id}")

    async def remove_backpressure(self, group_id: str):
        """Remove backpressure measures"""
        # Reset throttling
        self.throttle_levels[group_id] = 1.0
        self.redis_client.delete(f"throttle:{group_id}")

        # Resume paused partitions
        if group_id in self.paused_partitions:
            await self.resume_partitions(group_id)

        # Reset circuit breaker
        if group_id in self.circuit_breakers:
            self.circuit_breakers[group_id].state = CircuitBreakerState.CLOSED
            self.circuit_breakers[group_id].failure_count = 0

    async def selective_partition_pause(self, group_id: str, metrics: ConsumerMetrics):
        """Selectively pause partitions with highest lag"""
        consumer = KafkaConsumer(
            bootstrap_servers=self.bootstrap_servers,
            group_id=f"{group_id}-controller",
            enable_auto_commit=False
        )

        try:
            topics = self.redis_client.smembers(f"consumer_group:{group_id}:topics")
            partition_lags = []

            for topic in topics:
                partitions = consumer.partitions_for_topic(topic)
                if not partitions:
                    continue

                for partition in partitions:
                    tp = TopicPartition(topic, partition)

                    # Get lag for this partition
                    committed = consumer.committed(tp)
                    if committed is None:
                        committed = 0

                    consumer.assign([tp])
                    consumer.seek_to_end(tp)
                    end_offset = consumer.position(tp)
                    lag = end_offset - committed

                    partition_lags.append((tp, lag))

            # Sort by lag and pause top 20%
            partition_lags.sort(key=lambda x: x[1], reverse=True)
            num_to_pause = max(1, len(partition_lags) // 5)

            partitions_to_pause = [tp for tp, _ in partition_lags[:num_to_pause]]

            if partitions_to_pause:
                # Store paused partitions
                self.paused_partitions[group_id] = set(partitions_to_pause)

                # Notify consumers via Redis
                pause_data = [(tp.topic, tp.partition) for tp in partitions_to_pause]
                self.redis_client.set(f"pause:{group_id}", json.dumps(pause_data))
                self.redis_client.expire(f"pause:{group_id}", 60)

                logger.info(f"Paused {len(partitions_to_pause)} partitions for {group_id}")

        finally:
            consumer.close()

    async def pause_high_lag_partitions(self, group_id: str):
        """Pause all partitions with lag above threshold"""
        consumer = KafkaConsumer(
            bootstrap_servers=self.bootstrap_servers,
            group_id=f"{group_id}-controller",
            enable_auto_commit=False
        )

        try:
            topics = self.redis_client.smembers(f"consumer_group:{group_id}:topics")
            partitions_to_pause = []

            for topic in topics:
                partitions = consumer.partitions_for_topic(topic)
                if not partitions:
                    continue

                for partition in partitions:
                    tp = TopicPartition(topic, partition)

                    # Get lag
                    committed = consumer.committed(tp)
                    if committed is None:
                        committed = 0

                    consumer.assign([tp])
                    consumer.seek_to_end(tp)
                    end_offset = consumer.position(tp)
                    lag = end_offset - committed

                    if lag > self.policy.pause_partition_threshold:
                        partitions_to_pause.append(tp)

            if partitions_to_pause:
                self.paused_partitions[group_id] = set(partitions_to_pause)

                pause_data = [(tp.topic, tp.partition) for tp in partitions_to_pause]
                self.redis_client.set(f"pause:{group_id}", json.dumps(pause_data))
                self.redis_client.expire(f"pause:{group_id}", 60)

                logger.warning(f"Paused {len(partitions_to_pause)} high-lag partitions for {group_id}")

        finally:
            consumer.close()

    async def resume_partitions(self, group_id: str):
        """Resume paused partitions"""
        if group_id in self.paused_partitions:
            del self.paused_partitions[group_id]
            self.redis_client.delete(f"pause:{group_id}")
            logger.info(f"Resumed all partitions for {group_id}")

    async def activate_circuit_breaker(self, group_id: str):
        """Activate circuit breaker for consumer group"""
        if group_id not in self.circuit_breakers:
            self.circuit_breakers[group_id] = CircuitBreaker(service_name=group_id)

        cb = self.circuit_breakers[group_id]
        cb.state = CircuitBreakerState.OPEN
        cb.last_state_change = datetime.now()

        # Notify via Redis
        self.redis_client.set(f"circuit_breaker:{group_id}", "open")
        self.redis_client.expire(f"circuit_breaker:{group_id}", self.policy.circuit_breaker_timeout_seconds)

        logger.critical(f"Circuit breaker OPEN for {group_id}")
        CIRCUIT_BREAKER_STATE.labels(service=group_id).set(2)  # 2 = open

    async def drop_non_critical_messages(self, group_id: str):
        """Drop non-critical messages to reduce load"""
        # Define critical message patterns
        critical_patterns = [
            'wildfire-critical-',
            'wildfire-alerts-',
            'wildfire-evacuations-'
        ]

        # Store drop policy in Redis
        drop_policy = {
            'enabled': True,
            'keep_patterns': critical_patterns,
            'drop_percentage': 50  # Drop 50% of non-critical messages
        }

        self.redis_client.set(f"drop_policy:{group_id}", json.dumps(drop_policy))
        self.redis_client.expire(f"drop_policy:{group_id}", 60)

        logger.warning(f"Activated message dropping for {group_id}")

    async def check_circuit_breakers(self):
        """Check and update circuit breaker states"""
        for group_id, cb in self.circuit_breakers.items():
            if cb.state == CircuitBreakerState.OPEN:
                # Check if timeout has passed
                elapsed = (datetime.now() - cb.last_state_change).total_seconds()
                if elapsed > self.policy.circuit_breaker_timeout_seconds:
                    # Move to half-open
                    cb.state = CircuitBreakerState.HALF_OPEN
                    cb.last_state_change = datetime.now()
                    self.redis_client.set(f"circuit_breaker:{group_id}", "half_open")
                    logger.info(f"Circuit breaker HALF-OPEN for {group_id}")
                    CIRCUIT_BREAKER_STATE.labels(service=group_id).set(1)  # 1 = half-open

            elif cb.state == CircuitBreakerState.HALF_OPEN:
                # Check if service has recovered
                metrics = await self.collect_consumer_metrics(group_id)
                if metrics.lag < self.policy.lag_warning_threshold:
                    # Close circuit breaker
                    cb.state = CircuitBreakerState.CLOSED
                    cb.failure_count = 0
                    cb.last_state_change = datetime.now()
                    self.redis_client.delete(f"circuit_breaker:{group_id}")
                    logger.info(f"Circuit breaker CLOSED for {group_id}")
                    CIRCUIT_BREAKER_STATE.labels(service=group_id).set(0)  # 0 = closed

    def update_metrics(self, group_id: str, metrics: ConsumerMetrics, state: BackpressureState):
        """Update Prometheus metrics"""
        CONSUMER_LAG.labels(consumer_group=group_id, topic='all').set(metrics.lag)
        PROCESSING_RATE.labels(consumer_group=group_id).set(metrics.processing_rate)

        throttle = self.throttle_levels.get(group_id, 1.0)
        THROTTLE_LEVEL.labels(consumer_group=group_id).set(throttle)

        paused = len(self.paused_partitions.get(group_id, set()))
        PAUSED_PARTITIONS.labels(topic='all').set(paused)

# Smart consumer wrapper with backpressure awareness
class BackpressureAwareConsumer:
    """Kafka consumer that respects backpressure signals"""

    def __init__(self, topics: List[str], group_id: str, controller: BackpressureController):
        self.topics = topics
        self.group_id = group_id
        self.controller = controller
        self.consumer = None
        self.paused_partitions = set()
        self.last_throttle_check = datetime.now()

    async def consume_with_backpressure(self):
        """Consume messages with backpressure control"""
        self.consumer = aiokafka.AIOKafkaConsumer(
            *self.topics,
            bootstrap_servers=self.controller.bootstrap_servers,
            group_id=self.group_id,
            enable_auto_commit=True,
            auto_offset_reset='latest'
        )

        await self.consumer.start()

        # Register with controller
        self.controller.redis_client.sadd('active_consumer_groups', self.group_id)
        for topic in self.topics:
            self.controller.redis_client.sadd(f"consumer_group:{self.group_id}:topics", topic)

        try:
            message_count = 0
            start_time = datetime.now()

            async for msg in self.consumer:
                # Check throttling
                if await self.should_throttle():
                    await asyncio.sleep(0.1)  # Add delay

                # Check if partition is paused
                tp = TopicPartition(msg.topic, msg.partition)
                if tp in self.paused_partitions:
                    continue

                # Check if message should be dropped
                if await self.should_drop_message(msg):
                    DROPPED_MESSAGES.labels(topic=msg.topic).inc()
                    continue

                # Process message
                yield msg

                # Update metrics
                message_count += 1
                if (datetime.now() - start_time).total_seconds() > 1:
                    rate = message_count / (datetime.now() - start_time).total_seconds()
                    self.controller.redis_client.set(f"processing_rate:{self.group_id}", rate)
                    message_count = 0
                    start_time = datetime.now()

                # Periodically check for pause/resume signals
                if (datetime.now() - self.last_throttle_check).total_seconds() > 5:
                    await self.check_backpressure_signals()
                    self.last_throttle_check = datetime.now()

        finally:
            await self.consumer.stop()
            self.controller.redis_client.srem('active_consumer_groups', self.group_id)

    async def should_throttle(self) -> bool:
        """Check if should throttle based on controller signals"""
        throttle_level = float(self.controller.redis_client.get(f"throttle:{self.group_id}") or 1.0)
        if throttle_level < 1.0:
            import random
            return random.random() > throttle_level
        return False

    async def should_drop_message(self, msg) -> bool:
        """Check if message should be dropped"""
        drop_policy_str = self.controller.redis_client.get(f"drop_policy:{self.group_id}")
        if not drop_policy_str:
            return False

        drop_policy = json.loads(drop_policy_str)
        if not drop_policy.get('enabled'):
            return False

        # Check if critical message
        for pattern in drop_policy.get('keep_patterns', []):
            if msg.topic.startswith(pattern):
                return False

        # Drop based on percentage
        import random
        drop_pct = drop_policy.get('drop_percentage', 0) / 100.0
        return random.random() < drop_pct

    async def check_backpressure_signals(self):
        """Check for pause/resume signals from controller"""
        # Check for paused partitions
        pause_data = self.controller.redis_client.get(f"pause:{self.group_id}")
        if pause_data:
            partitions = json.loads(pause_data)
            new_paused = {TopicPartition(topic, partition) for topic, partition in partitions}

            # Pause new partitions
            to_pause = new_paused - self.paused_partitions
            if to_pause:
                self.consumer.pause(*to_pause)
                logger.info(f"Paused {len(to_pause)} partitions")

            # Resume removed partitions
            to_resume = self.paused_partitions - new_paused
            if to_resume:
                self.consumer.resume(*to_resume)
                logger.info(f"Resumed {len(to_resume)} partitions")

            self.paused_partitions = new_paused
        else:
            # Resume all if no pause signal
            if self.paused_partitions:
                self.consumer.resume(*self.paused_partitions)
                self.paused_partitions = set()

async def main():
    """Main entry point"""
    policy = BackpressurePolicy(
        lag_warning_threshold=5000,
        lag_critical_threshold=10000,
        lag_overload_threshold=50000,
        cpu_threshold_percent=80.0,
        memory_threshold_percent=85.0
    )

    controller = BackpressureController(policy)

    logger.info("Starting Backpressure Controller")
    logger.info("Monitoring consumer groups for overload conditions")
    logger.info("Metrics available at http://localhost:9095/metrics")

    await controller.monitor_and_control()

if __name__ == "__main__":
    asyncio.run(main())