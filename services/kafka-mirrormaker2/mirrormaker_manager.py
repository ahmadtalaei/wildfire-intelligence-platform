"""
MirrorMaker 2 Manager for Multi-Cluster Kafka Setup
Manages geo-replication between California regional Kafka clusters
Provides intelligent routing and failover capabilities
"""

import os
import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from enum import Enum

from kafka import KafkaAdminClient, KafkaProducer, KafkaConsumer
from kafka.admin import ConfigResource, ConfigResourceType
from prometheus_client import Gauge, Counter, Histogram, start_http_server
import redis
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Metrics
REPLICATION_LAG = Gauge('mm2_replication_lag_ms', 'Replication lag in milliseconds', ['source', 'target', 'topic'])
MESSAGES_REPLICATED = Counter('mm2_messages_replicated', 'Messages replicated', ['source', 'target'])
REPLICATION_ERRORS = Counter('mm2_replication_errors', 'Replication errors', ['source', 'target'])
CLUSTER_HEALTH = Gauge('mm2_cluster_health', 'Cluster health (1=healthy, 0=unhealthy)', ['cluster'])
FAILOVER_EVENTS = Counter('mm2_failover_events', 'Failover events triggered')
ACTIVE_TOPICS = Gauge('mm2_active_topics', 'Active topics being replicated', ['cluster'])

class ClusterRole(Enum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    DR = "disaster_recovery"

@dataclass
class KafkaCluster:
    """Kafka cluster configuration"""
    name: str
    bootstrap_servers: str
    region: str
    role: ClusterRole
    health_check_url: Optional[str] = None
    is_healthy: bool = True
    last_heartbeat: Optional[datetime] = None

@dataclass
class ReplicationFlow:
    """Replication flow between clusters"""
    source: str
    target: str
    topics: List[str]
    enabled: bool = True
    lag_ms: int = 0
    messages_per_sec: float = 0

class MirrorMakerManager:
    """
    Manages MirrorMaker 2 for multi-cluster Kafka setup
    Handles geo-replication, failover, and intelligent routing
    """

    def __init__(self):
        # Cluster configurations
        self.clusters = self._initialize_clusters()
        self.replication_flows = self._initialize_flows()

        # Redis for coordination
        self.redis_client = redis.Redis(
            host=os.getenv('REDIS_HOST', 'redis'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            decode_responses=True
        )

        # Admin clients per cluster
        self.admin_clients = {}
        for cluster in self.clusters.values():
            try:
                self.admin_clients[cluster.name] = KafkaAdminClient(
                    bootstrap_servers=cluster.bootstrap_servers,
                    client_id=f'mm2-manager-{cluster.name}'
                )
            except Exception as e:
                logger.error(f"Failed to connect to {cluster.name}: {e}")

    def _initialize_clusters(self) -> Dict[str, KafkaCluster]:
        """Initialize California regional Kafka clusters"""
        return {
            'norcal': KafkaCluster(
                name='norcal',
                bootstrap_servers=os.getenv('KAFKA_NORCAL', 'kafka-norcal:29092'),
                region='Northern California',
                role=ClusterRole.PRIMARY,
                health_check_url='http://kafka-norcal:8080/health'
            ),
            'socal': KafkaCluster(
                name='socal',
                bootstrap_servers=os.getenv('KAFKA_SOCAL', 'kafka-socal:29092'),
                region='Southern California',
                role=ClusterRole.SECONDARY,
                health_check_url='http://kafka-socal:8080/health'
            ),
            'central': KafkaCluster(
                name='central',
                bootstrap_servers=os.getenv('KAFKA_CENTRAL', 'kafka-central:29092'),
                region='Central California',
                role=ClusterRole.DR,
                health_check_url='http://kafka-central:8080/health'
            )
        }

    def _initialize_flows(self) -> List[ReplicationFlow]:
        """Initialize replication flows between clusters"""
        return [
            # Primary replication flows
            ReplicationFlow(
                source='norcal',
                target='socal',
                topics=['wildfire-detections-.*', 'wildfire-weather-.*', 'wildfire-sensors-.*']
            ),
            ReplicationFlow(
                source='socal',
                target='norcal',
                topics=['wildfire-detections-.*', 'wildfire-weather-.*', 'wildfire-sensors-.*']
            ),
            # DR replication (critical data only)
            ReplicationFlow(
                source='norcal',
                target='central',
                topics=['wildfire-critical-.*', 'wildfire-alerts-.*']
            ),
            ReplicationFlow(
                source='socal',
                target='central',
                topics=['wildfire-critical-.*', 'wildfire-alerts-.*']
            )
        ]

    async def monitor_and_manage(self):
        """Main monitoring and management loop"""
        logger.info("Starting MirrorMaker 2 Manager...")

        # Start metrics server
        start_http_server(9094)

        while True:
            try:
                # Health check all clusters
                await self.health_check_clusters()

                # Monitor replication lag
                await self.monitor_replication_lag()

                # Check for failover conditions
                await self.check_failover_conditions()

                # Optimize topic placement
                await self.optimize_topic_placement()

                # Update metrics
                self.update_metrics()

                # Sleep before next iteration
                await asyncio.sleep(30)

            except Exception as e:
                logger.error(f"Error in manager loop: {e}")
                await asyncio.sleep(60)

    async def health_check_clusters(self):
        """Health check all Kafka clusters"""
        for cluster in self.clusters.values():
            try:
                # Try to list topics as health check
                admin = self.admin_clients.get(cluster.name)
                if admin:
                    topics = admin.list_topics(timeout=5)
                    cluster.is_healthy = True
                    cluster.last_heartbeat = datetime.now()
                    CLUSTER_HEALTH.labels(cluster=cluster.name).set(1)
                else:
                    cluster.is_healthy = False
                    CLUSTER_HEALTH.labels(cluster=cluster.name).set(0)

                # Store in Redis
                self.redis_client.set(f"cluster:{cluster.name}:healthy", str(cluster.is_healthy))
                if cluster.last_heartbeat:
                    self.redis_client.set(f"cluster:{cluster.name}:heartbeat", cluster.last_heartbeat.isoformat())

            except Exception as e:
                logger.error(f"Health check failed for {cluster.name}: {e}")
                cluster.is_healthy = False
                CLUSTER_HEALTH.labels(cluster=cluster.name).set(0)

    async def monitor_replication_lag(self):
        """Monitor replication lag between clusters"""
        for flow in self.replication_flows:
            if not flow.enabled:
                continue

            try:
                source_cluster = self.clusters[flow.source]
                target_cluster = self.clusters[flow.target]

                if not (source_cluster.is_healthy and target_cluster.is_healthy):
                    continue

                # Get checkpoint topics to measure lag
                source_consumer = KafkaConsumer(
                    bootstrap_servers=source_cluster.bootstrap_servers,
                    group_id='mm2-lag-monitor',
                    enable_auto_commit=False
                )

                target_consumer = KafkaConsumer(
                    bootstrap_servers=target_cluster.bootstrap_servers,
                    group_id='mm2-lag-monitor',
                    enable_auto_commit=False
                )

                # Calculate average lag across topics
                total_lag = 0
                topic_count = 0

                for topic_pattern in flow.topics:
                    # Get actual topics matching pattern
                    source_topics = source_consumer.topics()
                    matching_topics = [t for t in source_topics if self._matches_pattern(t, topic_pattern)]

                    for topic in matching_topics:
                        try:
                            # Get latest offset in source
                            source_partitions = source_consumer.partitions_for_topic(topic)
                            if not source_partitions:
                                continue

                            source_latest = 0
                            for partition in source_partitions:
                                source_consumer.assign([(topic, partition)])
                                source_consumer.seek_to_end()
                                source_latest += source_consumer.position((topic, partition))

                            # Get latest offset in target (with MM2 prefix)
                            target_topic = f"{flow.source}.{topic}"
                            target_partitions = target_consumer.partitions_for_topic(target_topic)
                            if not target_partitions:
                                continue

                            target_latest = 0
                            for partition in target_partitions:
                                target_consumer.assign([(target_topic, partition)])
                                target_consumer.seek_to_end()
                                target_latest += target_consumer.position((target_topic, partition))

                            # Calculate lag
                            lag = source_latest - target_latest
                            total_lag += max(0, lag)  # Ensure non-negative
                            topic_count += 1

                            # Update metric
                            REPLICATION_LAG.labels(
                                source=flow.source,
                                target=flow.target,
                                topic=topic
                            ).set(lag)

                        except Exception as e:
                            logger.debug(f"Error checking lag for {topic}: {e}")

                source_consumer.close()
                target_consumer.close()

                # Calculate average lag
                if topic_count > 0:
                    flow.lag_ms = total_lag / topic_count

                # Store in Redis
                self.redis_client.set(f"replication:{flow.source}:{flow.target}:lag", flow.lag_ms)

            except Exception as e:
                logger.error(f"Error monitoring lag for {flow.source}->{flow.target}: {e}")

    async def check_failover_conditions(self):
        """Check if failover is needed and trigger if necessary"""
        primary = self.clusters.get('norcal')
        secondary = self.clusters.get('socal')
        dr = self.clusters.get('central')

        # Check if primary is down
        if not primary.is_healthy and secondary.is_healthy:
            logger.warning("Primary cluster (NorCal) is down, initiating failover to SoCal")
            await self.initiate_failover('norcal', 'socal')
            FAILOVER_EVENTS.inc()

        # Check if both primary and secondary are down
        if not primary.is_healthy and not secondary.is_healthy and dr.is_healthy:
            logger.critical("Both primary and secondary clusters down, failing over to DR (Central)")
            await self.initiate_failover('norcal', 'central')
            await self.initiate_failover('socal', 'central')
            FAILOVER_EVENTS.inc()

    async def initiate_failover(self, failed_cluster: str, target_cluster: str):
        """Initiate failover from failed cluster to target"""
        logger.info(f"Initiating failover from {failed_cluster} to {target_cluster}")

        # Update cluster roles
        self.clusters[target_cluster].role = ClusterRole.PRIMARY

        # Redirect producers
        self.redis_client.set('kafka:active_cluster', target_cluster)

        # Update DNS or load balancer (in production)
        # This would update Route53, HAProxy, or other routing layer

        # Disable replication from failed cluster
        for flow in self.replication_flows:
            if flow.source == failed_cluster:
                flow.enabled = False
                logger.info(f"Disabled replication flow {flow.source}->{flow.target}")

        # Enable reverse replication when cluster comes back
        # This will be handled in recovery logic

        # Send alert
        await self.send_failover_alert(failed_cluster, target_cluster)

    async def send_failover_alert(self, failed_cluster: str, target_cluster: str):
        """Send alert about failover event"""
        alert = {
            'timestamp': datetime.now().isoformat(),
            'event': 'kafka_failover',
            'failed_cluster': failed_cluster,
            'target_cluster': target_cluster,
            'severity': 'critical'
        }

        # Send to alerting system
        self.redis_client.lpush('alerts:kafka', json.dumps(alert))
        logger.critical(f"FAILOVER ALERT: {alert}")

    async def optimize_topic_placement(self):
        """Optimize topic placement based on access patterns"""
        # Analyze access patterns from Redis
        access_patterns = {}

        for cluster_name in self.clusters.keys():
            pattern_key = f"access_pattern:{cluster_name}:*"
            patterns = self.redis_client.keys(pattern_key)

            for pattern in patterns:
                topic = pattern.split(':')[-1]
                count = int(self.redis_client.get(pattern) or 0)

                if topic not in access_patterns:
                    access_patterns[topic] = {}
                access_patterns[topic][cluster_name] = count

        # Recommend topic placement
        for topic, cluster_access in access_patterns.items():
            if not cluster_access:
                continue

            # Find cluster with most access
            primary_cluster = max(cluster_access, key=cluster_access.get)

            # Check if topic should be replicated to other clusters
            total_access = sum(cluster_access.values())
            for cluster, count in cluster_access.items():
                if cluster != primary_cluster and count > total_access * 0.3:
                    # Significant access from other cluster, ensure replication
                    await self.ensure_replication(topic, primary_cluster, cluster)

    async def ensure_replication(self, topic: str, source: str, target: str):
        """Ensure topic is replicated from source to target"""
        # Check if flow exists
        flow_exists = False
        for flow in self.replication_flows:
            if flow.source == source and flow.target == target:
                if topic not in flow.topics:
                    flow.topics.append(topic)
                    logger.info(f"Added {topic} to replication flow {source}->{target}")
                flow_exists = True
                break

        if not flow_exists:
            # Create new flow
            new_flow = ReplicationFlow(
                source=source,
                target=target,
                topics=[topic]
            )
            self.replication_flows.append(new_flow)
            logger.info(f"Created new replication flow {source}->{target} for {topic}")

    def _matches_pattern(self, topic: str, pattern: str) -> bool:
        """Check if topic matches pattern"""
        import re
        # Convert wildcard pattern to regex
        regex_pattern = pattern.replace('.', r'\.').replace('*', '.*')
        return bool(re.match(f'^{regex_pattern}$', topic))

    def update_metrics(self):
        """Update Prometheus metrics"""
        for cluster in self.clusters.values():
            # Count active topics
            try:
                admin = self.admin_clients.get(cluster.name)
                if admin:
                    topics = admin.list_topics()
                    wildfire_topics = [t for t in topics if t.startswith('wildfire-')]
                    ACTIVE_TOPICS.labels(cluster=cluster.name).set(len(wildfire_topics))
            except:
                pass

        # Update flow metrics
        for flow in self.replication_flows:
            if flow.enabled:
                # Get throughput from Redis
                throughput_key = f"replication:{flow.source}:{flow.target}:throughput"
                throughput = float(self.redis_client.get(throughput_key) or 0)
                flow.messages_per_sec = throughput

# Intelligent topic router for multi-cluster
class MultiClusterRouter:
    """Routes messages to appropriate cluster based on data locality"""

    def __init__(self, manager: MirrorMakerManager):
        self.manager = manager

    def get_target_cluster(self, message: Dict) -> str:
        """Determine target cluster for message"""
        # Extract location from message
        lat = message.get('latitude') or message.get('lat')
        lon = message.get('longitude') or message.get('lon')

        if lat and lon:
            # Route based on California geography
            if float(lat) > 37:  # Northern California
                return 'norcal' if self.manager.clusters['norcal'].is_healthy else 'socal'
            else:  # Southern California
                return 'socal' if self.manager.clusters['socal'].is_healthy else 'norcal'

        # Default to primary cluster
        for cluster in self.manager.clusters.values():
            if cluster.role == ClusterRole.PRIMARY and cluster.is_healthy:
                return cluster.name

        # Fallback to any healthy cluster
        for cluster in self.manager.clusters.values():
            if cluster.is_healthy:
                return cluster.name

        raise Exception("No healthy clusters available")

    async def produce_with_routing(self, topic: str, key: bytes, value: bytes, message_dict: Dict):
        """Produce message to appropriate cluster"""
        target_cluster = self.get_target_cluster(message_dict)
        cluster = self.manager.clusters[target_cluster]

        producer = KafkaProducer(
            bootstrap_servers=cluster.bootstrap_servers,
            compression_type='zstd',
            acks='all'
        )

        future = producer.send(topic, key=key, value=value)
        producer.flush()

        # Track access pattern
        access_key = f"access_pattern:{target_cluster}:{topic}"
        self.manager.redis_client.incr(access_key)

        return target_cluster

async def main():
    """Main entry point"""
    manager = MirrorMakerManager()

    logger.info("Starting MirrorMaker 2 Manager")
    logger.info(f"Managing clusters: {list(manager.clusters.keys())}")
    logger.info(f"Replication flows: {len(manager.replication_flows)}")
    logger.info("Metrics available at http://localhost:9094/metrics")

    await manager.monitor_and_manage()

if __name__ == "__main__":
    asyncio.run(main())