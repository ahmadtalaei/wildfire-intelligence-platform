"""
Dynamic Partition Monitor for Kafka
Monitors consumer lag and triggers automatic partition scaling
Implements date/region-based topic sharding for optimal throughput
"""

import os
import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
import re

from kafka import KafkaAdminClient, KafkaConsumer
from kafka.admin import NewTopic, NewPartitions, ConfigResource, ConfigResourceType
from kafka.errors import KafkaError, TopicAlreadyExistsError
from prometheus_client import Gauge, Counter, Histogram, start_http_server
import redis
import aiokafka
from aiokafka.admin import AIOKafkaAdminClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Metrics
PARTITION_COUNT = Gauge('kafka_dynamic_partition_count', 'Current partition count', ['topic'])
CONSUMER_LAG = Gauge('kafka_dynamic_consumer_lag', 'Consumer lag', ['group', 'topic', 'partition'])
PARTITIONS_CREATED = Counter('kafka_dynamic_partitions_created', 'Partitions created', ['topic'])
TOPICS_CREATED = Counter('kafka_dynamic_topics_created', 'Topics created dynamically')
PARTITION_REBALANCE = Counter('kafka_dynamic_rebalances', 'Partition rebalances triggered')
HOTSPOT_DETECTED = Counter('kafka_dynamic_hotspots', 'Hotspot partitions detected', ['topic'])

@dataclass
class PartitionConfig:
    """Configuration for dynamic partition management"""
    min_partitions: int = 3
    max_partitions: int = 100
    lag_threshold: int = 5000
    scale_up_threshold: float = 0.8  # 80% of lag threshold
    scale_down_threshold: float = 0.2  # 20% of lag threshold
    cooldown_minutes: int = 5
    enable_date_sharding: bool = True
    enable_region_sharding: bool = True

@dataclass
class TopicMetrics:
    """Metrics for a specific topic"""
    topic: str
    total_lag: int
    partition_lags: Dict[int, int]
    messages_per_sec: float
    avg_message_size: int
    hotspot_partitions: List[int]
    last_scaled: datetime

class DynamicPartitionManager:
    """
    Manages dynamic partitioning and topic sharding for Kafka
    Automatically scales partitions based on lag and load
    """

    def __init__(self, config: PartitionConfig = None):
        self.config = config or PartitionConfig()
        self.bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:29092')

        # Admin client for partition management
        self.admin_client = KafkaAdminClient(
            bootstrap_servers=self.bootstrap_servers,
            client_id='dynamic-partition-manager'
        )

        # Redis for coordination and state
        self.redis_client = redis.Redis(
            host=os.getenv('REDIS_HOST', 'redis'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            decode_responses=True
        )

        # Track scaling history
        self.scaling_history: Dict[str, datetime] = {}

        # California regions for geographic sharding
        self.ca_regions = [
            'norcal', 'bay-area', 'central-valley',
            'central-coast', 'sierra', 'socal', 'inland-empire'
        ]

    async def initialize(self):
        """Initialize async components"""
        self.async_admin = AIOKafkaAdminClient(
            bootstrap_servers=self.bootstrap_servers,
            client_id='dynamic-partition-manager-async'
        )
        await self.async_admin.start()

    async def monitor_and_scale(self):
        """Main monitoring loop"""
        logger.info("Starting dynamic partition monitoring...")

        # Start metrics server
        start_http_server(9091)

        while True:
            try:
                # Get all topics
                topics = await self.get_monitored_topics()

                for topic in topics:
                    metrics = await self.collect_topic_metrics(topic)

                    # Update Prometheus metrics
                    self.update_metrics(metrics)

                    # Check if scaling is needed
                    if await self.should_scale(metrics):
                        await self.scale_topic(metrics)

                    # Check for date/region sharding opportunities
                    if self.config.enable_date_sharding:
                        await self.manage_date_sharding(topic)

                    if self.config.enable_region_sharding:
                        await self.manage_region_sharding(topic)

                # Sleep before next iteration
                await asyncio.sleep(30)  # Check every 30 seconds

            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(60)

    async def get_monitored_topics(self) -> List[str]:
        """Get list of topics to monitor"""
        # Get all topics
        metadata = self.admin_client.describe_topics()

        # Filter for wildfire topics (exclude internal topics)
        wildfire_topics = [
            topic for topic in metadata
            if topic.startswith('wildfire-') and not topic.startswith('wildfire-__')
        ]

        return wildfire_topics

    async def collect_topic_metrics(self, topic: str) -> TopicMetrics:
        """Collect metrics for a specific topic"""
        consumer = KafkaConsumer(
            bootstrap_servers=self.bootstrap_servers,
            group_id='lag-monitor',
            enable_auto_commit=False
        )

        # Get partition info
        partitions = consumer.partitions_for_topic(topic)
        if not partitions:
            return None

        # Get consumer group lag
        partition_lags = {}
        total_lag = 0
        hotspot_partitions = []

        for partition in partitions:
            # Get lag for partition
            lag = await self.get_partition_lag(topic, partition)
            partition_lags[partition] = lag
            total_lag += lag

            # Detect hotspots (partitions with significantly higher lag)
            if lag > self.config.lag_threshold:
                hotspot_partitions.append(partition)
                HOTSPOT_DETECTED.labels(topic=topic).inc()

        # Calculate throughput
        messages_per_sec = await self.calculate_throughput(topic)

        # Get last scaling time
        last_scaled_key = f"last_scaled:{topic}"
        last_scaled_str = self.redis_client.get(last_scaled_key)
        last_scaled = datetime.fromisoformat(last_scaled_str) if last_scaled_str else datetime.min

        consumer.close()

        return TopicMetrics(
            topic=topic,
            total_lag=total_lag,
            partition_lags=partition_lags,
            messages_per_sec=messages_per_sec,
            avg_message_size=1024,  # Estimate
            hotspot_partitions=hotspot_partitions,
            last_scaled=last_scaled
        )

    async def get_partition_lag(self, topic: str, partition: int) -> int:
        """Get lag for a specific partition"""
        # In production, this would query consumer group offsets
        # For now, simulate with Redis-stored values
        lag_key = f"lag:{topic}:{partition}"
        lag = self.redis_client.get(lag_key)
        return int(lag) if lag else 0

    async def calculate_throughput(self, topic: str) -> float:
        """Calculate messages per second for topic"""
        # Get from Redis (would be populated by actual consumers)
        throughput_key = f"throughput:{topic}"
        throughput = self.redis_client.get(throughput_key)
        return float(throughput) if throughput else 0.0

    async def should_scale(self, metrics: TopicMetrics) -> bool:
        """Determine if topic needs scaling"""
        if not metrics:
            return False

        # Check cooldown period
        now = datetime.utcnow()
        if (now - metrics.last_scaled).total_seconds() < self.config.cooldown_minutes * 60:
            return False

        # Check if any partition has high lag
        max_lag = max(metrics.partition_lags.values()) if metrics.partition_lags else 0

        # Scale up if lag is too high
        if max_lag > self.config.lag_threshold * self.config.scale_up_threshold:
            return True

        # Check for hotspots
        if len(metrics.hotspot_partitions) > 0:
            return True

        return False

    async def scale_topic(self, metrics: TopicMetrics):
        """Scale partitions for a topic"""
        current_partitions = len(metrics.partition_lags)

        # Calculate target partitions
        target_partitions = self.calculate_target_partitions(metrics)

        if target_partitions > current_partitions:
            logger.info(f"Scaling {metrics.topic} from {current_partitions} to {target_partitions} partitions")

            try:
                # Add partitions
                partition_update = {metrics.topic: NewPartitions(total_count=target_partitions)}
                self.admin_client.create_partitions(partition_update)

                # Update metrics
                PARTITIONS_CREATED.labels(topic=metrics.topic).inc(target_partitions - current_partitions)
                PARTITION_COUNT.labels(topic=metrics.topic).set(target_partitions)
                PARTITION_REBALANCE.inc()

                # Update last scaled time
                last_scaled_key = f"last_scaled:{metrics.topic}"
                self.redis_client.set(last_scaled_key, datetime.utcnow().isoformat())

                logger.info(f"Successfully scaled {metrics.topic} to {target_partitions} partitions")

            except Exception as e:
                logger.error(f"Failed to scale {metrics.topic}: {e}")

    def calculate_target_partitions(self, metrics: TopicMetrics) -> int:
        """Calculate optimal number of partitions"""
        current_partitions = len(metrics.partition_lags)

        # Base calculation on throughput and lag
        if metrics.messages_per_sec > 0:
            # Aim for ~1000 messages/sec per partition
            throughput_based = int(metrics.messages_per_sec / 1000) + 1
        else:
            throughput_based = current_partitions

        # Consider lag
        if metrics.total_lag > 0:
            # Add partition for every lag_threshold messages
            lag_based = current_partitions + int(metrics.total_lag / self.config.lag_threshold)
        else:
            lag_based = current_partitions

        # Take the maximum
        target = max(throughput_based, lag_based)

        # Consider hotspots (add 20% more partitions)
        if metrics.hotspot_partitions:
            target = int(target * 1.2)

        # Apply limits
        target = max(self.config.min_partitions, min(target, self.config.max_partitions))

        return target

    async def manage_date_sharding(self, base_topic: str):
        """Create date-based topic shards"""
        if not base_topic.startswith('wildfire-'):
            return

        today = datetime.utcnow().date()

        # Create topics for next 7 days
        for days_ahead in range(7):
            date = today + timedelta(days=days_ahead)
            date_str = date.strftime('%Y-%m-%d')

            # Create sharded topic name
            sharded_topic = f"{base_topic}-{date_str}"

            # Check if topic exists
            if not await self.topic_exists(sharded_topic):
                await self.create_sharded_topic(sharded_topic, date=date_str)

    async def manage_region_sharding(self, base_topic: str):
        """Create region-based topic shards"""
        if not base_topic.startswith('wildfire-'):
            return

        # Create regional topics
        for region in self.ca_regions:
            regional_topic = f"{base_topic}-{region}"

            if not await self.topic_exists(regional_topic):
                # Calculate partitions based on region size
                partitions = self.get_region_partitions(region)
                await self.create_sharded_topic(regional_topic, region=region, partitions=partitions)

    async def topic_exists(self, topic: str) -> bool:
        """Check if topic exists"""
        try:
            metadata = self.admin_client.describe_topics([topic])
            return topic in metadata
        except:
            return False

    async def create_sharded_topic(self, topic: str, date: str = None, region: str = None, partitions: int = None):
        """Create a sharded topic"""
        if not partitions:
            # Default partitions based on shard type
            if date:
                partitions = 6  # Date shards get fewer partitions
            elif region:
                partitions = self.get_region_partitions(region)
            else:
                partitions = self.config.min_partitions

        try:
            new_topic = NewTopic(
                name=topic,
                num_partitions=partitions,
                replication_factor=1,
                topic_configs={
                    'retention.ms': '604800000',  # 7 days
                    'compression.type': 'zstd',
                    'min.insync.replicas': '1'
                }
            )

            self.admin_client.create_topics([new_topic])

            TOPICS_CREATED.inc()
            PARTITION_COUNT.labels(topic=topic).set(partitions)

            logger.info(f"Created sharded topic {topic} with {partitions} partitions")

            # Store metadata
            metadata_key = f"topic_metadata:{topic}"
            metadata = {
                'created': datetime.utcnow().isoformat(),
                'date_shard': date,
                'region_shard': region,
                'partitions': partitions
            }
            self.redis_client.set(metadata_key, json.dumps(metadata))

        except TopicAlreadyExistsError:
            logger.debug(f"Topic {topic} already exists")
        except Exception as e:
            logger.error(f"Failed to create topic {topic}: {e}")

    def get_region_partitions(self, region: str) -> int:
        """Get optimal partition count for region"""
        # High-fire-risk regions get more partitions
        region_partitions = {
            'norcal': 12,
            'bay-area': 8,
            'central-valley': 10,
            'central-coast': 6,
            'sierra': 12,
            'socal': 16,
            'inland-empire': 10
        }
        return region_partitions.get(region, 8)

    def update_metrics(self, metrics: TopicMetrics):
        """Update Prometheus metrics"""
        if not metrics:
            return

        # Update lag metrics
        for partition, lag in metrics.partition_lags.items():
            CONSUMER_LAG.labels(
                group='wildfire-consumers',
                topic=metrics.topic,
                partition=str(partition)
            ).set(lag)

    async def cleanup_old_shards(self):
        """Clean up old date-based shards"""
        cutoff_date = datetime.utcnow().date() - timedelta(days=30)

        # Get all topics
        topics = await self.get_monitored_topics()

        for topic in topics:
            # Check if it's a date shard
            match = re.match(r'(.+)-(\d{4}-\d{2}-\d{2})$', topic)
            if match:
                base_topic, date_str = match.groups()
                topic_date = datetime.strptime(date_str, '%Y-%m-%d').date()

                if topic_date < cutoff_date:
                    logger.info(f"Deleting old shard {topic} (date: {date_str})")
                    try:
                        self.admin_client.delete_topics([topic])
                    except Exception as e:
                        logger.error(f"Failed to delete topic {topic}: {e}")

    async def run(self):
        """Main entry point"""
        await self.initialize()

        # Start monitoring
        monitor_task = asyncio.create_task(self.monitor_and_scale())

        # Start cleanup task (runs daily)
        cleanup_task = asyncio.create_task(self.cleanup_loop())

        await asyncio.gather(monitor_task, cleanup_task)

    async def cleanup_loop(self):
        """Periodic cleanup of old shards"""
        while True:
            await asyncio.sleep(86400)  # Run daily
            await self.cleanup_old_shards()

# Smart topic router for producers
class ShardedTopicRouter:
    """Routes messages to appropriate sharded topics based on date/region"""

    def __init__(self):
        self.redis_client = redis.Redis(
            host=os.getenv('REDIS_HOST', 'redis'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            decode_responses=True
        )

    def get_target_topic(self, base_topic: str, message: Dict) -> str:
        """Determine which topic shard to use"""

        # Extract date and location
        timestamp = message.get('timestamp', datetime.utcnow().isoformat())
        date = datetime.fromisoformat(timestamp).date()

        lat = message.get('latitude') or message.get('lat')
        lon = message.get('longitude') or message.get('lon')

        # Try date-based shard first
        date_topic = f"{base_topic}-{date.strftime('%Y-%m-%d')}"
        if self.topic_exists(date_topic):
            return date_topic

        # Try region-based shard
        if lat and lon:
            region = self.get_california_region(float(lat), float(lon))
            if region:
                region_topic = f"{base_topic}-{region}"
                if self.topic_exists(region_topic):
                    return region_topic

        # Fall back to base topic
        return base_topic

    def topic_exists(self, topic: str) -> bool:
        """Check if topic exists (cached in Redis)"""
        return self.redis_client.exists(f"topic_metadata:{topic}")

    def get_california_region(self, lat: float, lon: float) -> Optional[str]:
        """Determine California region from coordinates"""
        # Simplified region detection
        if lat > 38.5:
            return 'norcal' if lon < -122 else 'sierra'
        elif 37 <= lat <= 38.5 and lon < -121.5:
            return 'bay-area'
        elif 35 <= lat <= 38 and -121.5 <= lon <= -119:
            return 'central-valley'
        elif 35 <= lat <= 37 and lon < -121:
            return 'central-coast'
        elif lat < 35:
            return 'socal' if lon < -117 else 'inland-empire'
        return None

if __name__ == "__main__":
    # Run the dynamic partition manager
    manager = DynamicPartitionManager()
    asyncio.run(manager.run())