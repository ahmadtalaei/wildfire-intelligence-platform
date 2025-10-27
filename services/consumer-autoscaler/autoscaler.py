"""
Kafka Consumer Autoscaler
Dynamically scales consumer instances based on lag and throughput
Implements Kubernetes HPA-like functionality for Kafka consumers
"""

import os
import json
import logging
import asyncio
import docker
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from kafka import KafkaAdminClient, KafkaConsumer
from kafka.structs import TopicPartition
from prometheus_client import Gauge, Counter, Histogram, start_http_server
import redis
import kubernetes
from kubernetes import client, config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Metrics
CONSUMER_INSTANCES = Gauge('kafka_autoscaler_consumer_instances', 'Current consumer instances', ['group'])
CONSUMER_LAG = Gauge('kafka_autoscaler_consumer_lag', 'Consumer lag', ['group', 'topic'])
SCALING_EVENTS = Counter('kafka_autoscaler_scaling_events', 'Scaling events', ['group', 'direction'])
TARGET_REPLICAS = Gauge('kafka_autoscaler_target_replicas', 'Target replicas', ['group'])
CPU_UTILIZATION = Gauge('kafka_autoscaler_cpu_utilization', 'CPU utilization', ['group'])
MEMORY_UTILIZATION = Gauge('kafka_autoscaler_memory_utilization', 'Memory utilization', ['group'])

class ScalingDirection(Enum):
    UP = "up"
    DOWN = "down"
    NONE = "none"

@dataclass
class ScalingPolicy:
    """Autoscaling policy configuration"""
    min_replicas: int = 1
    max_replicas: int = 20
    target_lag_per_instance: int = 10000  # Target lag per consumer instance
    scale_up_threshold: float = 0.8  # Scale up at 80% of target
    scale_down_threshold: float = 0.2  # Scale down at 20% of target
    cpu_threshold_percent: int = 70  # Scale up if CPU > 70%
    memory_threshold_percent: int = 80  # Scale up if memory > 80%
    cooldown_seconds: int = 300  # 5-minute cooldown between scaling events
    messages_per_sec_per_instance: int = 1000  # Expected throughput

@dataclass
class ConsumerGroupMetrics:
    """Metrics for a consumer group"""
    group_id: str
    total_lag: int
    lag_per_topic: Dict[str, int]
    active_consumers: int
    messages_per_sec: float
    cpu_percent: float
    memory_percent: float
    last_scaled: datetime

class KafkaConsumerAutoscaler:
    """
    Autoscales Kafka consumer deployments based on lag and resource utilization
    Supports both Docker and Kubernetes environments
    """

    def __init__(self, policy: ScalingPolicy = None):
        self.policy = policy or ScalingPolicy()
        self.bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:29092')

        # Admin client for monitoring
        self.admin_client = KafkaAdminClient(
            bootstrap_servers=self.bootstrap_servers,
            client_id='consumer-autoscaler'
        )

        # Redis for coordination
        self.redis_client = redis.Redis(
            host=os.getenv('REDIS_HOST', 'redis'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            decode_responses=True
        )

        # Container orchestration clients
        self.orchestrator = self._detect_orchestrator()
        self.scaling_history: Dict[str, datetime] = {}

        # Consumer group configurations
        self.consumer_groups = self._load_consumer_groups()

    def _detect_orchestrator(self):
        """Detect container orchestration platform"""
        # Check for Kubernetes
        try:
            config.load_incluster_config()  # In-cluster config
            return KubernetesOrchestrator()
        except:
            try:
                config.load_kube_config()  # Local kubeconfig
                return KubernetesOrchestrator()
            except:
                pass

        # Check for Docker
        try:
            docker_client = docker.from_env()
            docker_client.ping()
            return DockerOrchestrator(docker_client)
        except:
            pass

        logger.warning("No orchestrator detected, using mock orchestrator")
        return MockOrchestrator()

    def _load_consumer_groups(self) -> List[Dict]:
        """Load consumer group configurations"""
        # In production, load from config file or service discovery
        return [
            {
                'group_id': 'wildfire-fire-processor',
                'deployment_name': 'fire-processor',
                'topics': ['wildfire-satellite-raw', 'wildfire-satellite-processed'],
                'container_image': 'wildfire/fire-processor:latest'
            },
            {
                'group_id': 'wildfire-weather-processor',
                'deployment_name': 'weather-processor',
                'topics': ['wildfire-weather-raw', 'wildfire-weather-processed'],
                'container_image': 'wildfire/weather-processor:latest'
            },
            {
                'group_id': 'wildfire-analytics-processor',
                'deployment_name': 'analytics-processor',
                'topics': ['wildfire-analytics-input'],
                'container_image': 'wildfire/analytics-processor:latest'
            }
        ]

    async def monitor_and_scale(self):
        """Main monitoring and scaling loop"""
        logger.info("Starting consumer autoscaler...")

        # Start metrics server
        start_http_server(9093)

        while True:
            try:
                for group_config in self.consumer_groups:
                    group_id = group_config['group_id']

                    # Collect metrics
                    metrics = await self.collect_consumer_metrics(group_id, group_config['topics'])

                    # Update Prometheus metrics
                    self.update_metrics(metrics)

                    # Check if scaling is needed
                    scaling_decision = self.calculate_scaling_decision(metrics)

                    if scaling_decision != ScalingDirection.NONE:
                        # Check cooldown
                        if self.is_in_cooldown(group_id):
                            logger.info(f"Group {group_id} in cooldown, skipping scaling")
                            continue

                        # Calculate target replicas
                        target_replicas = self.calculate_target_replicas(metrics, scaling_decision)

                        # Execute scaling
                        await self.scale_consumer_group(group_config, target_replicas)

                        # Update scaling history
                        self.scaling_history[group_id] = datetime.now()
                        SCALING_EVENTS.labels(group=group_id, direction=scaling_decision.value).inc()

                # Sleep before next check
                await asyncio.sleep(30)  # Check every 30 seconds

            except Exception as e:
                logger.error(f"Error in autoscaler loop: {e}")
                await asyncio.sleep(60)

    async def collect_consumer_metrics(self, group_id: str, topics: List[str]) -> ConsumerGroupMetrics:
        """Collect metrics for a consumer group"""
        # Create consumer for metadata
        consumer = KafkaConsumer(
            bootstrap_servers=self.bootstrap_servers,
            group_id=f"{group_id}-monitor",
            enable_auto_commit=False
        )

        total_lag = 0
        lag_per_topic = {}

        for topic in topics:
            try:
                # Get partitions for topic
                partitions = consumer.partitions_for_topic(topic)
                if not partitions:
                    continue

                topic_lag = 0

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
                    topic_lag += lag

                lag_per_topic[topic] = topic_lag
                total_lag += topic_lag

            except Exception as e:
                logger.error(f"Error getting lag for {topic}: {e}")

        consumer.close()

        # Get active consumer count from Redis
        active_consumers = int(self.redis_client.get(f"consumers:{group_id}:count") or 1)

        # Get throughput from Redis (populated by consumers)
        messages_per_sec = float(self.redis_client.get(f"throughput:{group_id}") or 0)

        # Get resource metrics from orchestrator
        cpu_percent, memory_percent = await self.orchestrator.get_resource_metrics(group_id)

        # Get last scaling time
        last_scaled_str = self.redis_client.get(f"last_scaled:{group_id}")
        last_scaled = datetime.fromisoformat(last_scaled_str) if last_scaled_str else datetime.min

        return ConsumerGroupMetrics(
            group_id=group_id,
            total_lag=total_lag,
            lag_per_topic=lag_per_topic,
            active_consumers=active_consumers,
            messages_per_sec=messages_per_sec,
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            last_scaled=last_scaled
        )

    def calculate_scaling_decision(self, metrics: ConsumerGroupMetrics) -> ScalingDirection:
        """Determine if scaling is needed"""
        # Lag-based scaling
        lag_per_instance = metrics.total_lag / max(metrics.active_consumers, 1)
        target_lag = self.policy.target_lag_per_instance

        # Scale up conditions
        if (lag_per_instance > target_lag * self.policy.scale_up_threshold or
            metrics.cpu_percent > self.policy.cpu_threshold_percent or
            metrics.memory_percent > self.policy.memory_threshold_percent):
            return ScalingDirection.UP

        # Scale down conditions
        if (lag_per_instance < target_lag * self.policy.scale_down_threshold and
            metrics.cpu_percent < 50 and
            metrics.memory_percent < 50):
            return ScalingDirection.DOWN

        return ScalingDirection.NONE

    def calculate_target_replicas(self, metrics: ConsumerGroupMetrics, direction: ScalingDirection) -> int:
        """Calculate target number of replicas"""
        current = metrics.active_consumers

        if direction == ScalingDirection.UP:
            # Lag-based calculation
            if metrics.total_lag > 0:
                lag_based = int(metrics.total_lag / self.policy.target_lag_per_instance) + 1
            else:
                lag_based = current

            # Throughput-based calculation
            if metrics.messages_per_sec > 0:
                throughput_based = int(metrics.messages_per_sec / self.policy.messages_per_sec_per_instance) + 1
            else:
                throughput_based = current

            # Take maximum
            target = max(lag_based, throughput_based, current + 1)

        elif direction == ScalingDirection.DOWN:
            # Scale down by 1 instance at a time (conservative)
            target = current - 1

        else:
            target = current

        # Apply limits
        target = max(self.policy.min_replicas, min(target, self.policy.max_replicas))

        return target

    def is_in_cooldown(self, group_id: str) -> bool:
        """Check if group is in cooldown period"""
        if group_id not in self.scaling_history:
            return False

        elapsed = (datetime.now() - self.scaling_history[group_id]).total_seconds()
        return elapsed < self.policy.cooldown_seconds

    async def scale_consumer_group(self, group_config: Dict, target_replicas: int):
        """Scale consumer group to target replicas"""
        group_id = group_config['group_id']
        deployment_name = group_config['deployment_name']

        logger.info(f"Scaling {group_id} to {target_replicas} replicas")

        try:
            # Scale using orchestrator
            await self.orchestrator.scale_deployment(deployment_name, target_replicas)

            # Update Redis
            self.redis_client.set(f"consumers:{group_id}:count", target_replicas)
            self.redis_client.set(f"last_scaled:{group_id}", datetime.now().isoformat())

            # Update metrics
            TARGET_REPLICAS.labels(group=group_id).set(target_replicas)
            CONSUMER_INSTANCES.labels(group=group_id).set(target_replicas)

            logger.info(f"Successfully scaled {group_id} to {target_replicas} replicas")

        except Exception as e:
            logger.error(f"Failed to scale {group_id}: {e}")

    def update_metrics(self, metrics: ConsumerGroupMetrics):
        """Update Prometheus metrics"""
        # Lag metrics
        CONSUMER_LAG.labels(group=metrics.group_id, topic='total').set(metrics.total_lag)
        for topic, lag in metrics.lag_per_topic.items():
            CONSUMER_LAG.labels(group=metrics.group_id, topic=topic).set(lag)

        # Resource metrics
        CPU_UTILIZATION.labels(group=metrics.group_id).set(metrics.cpu_percent)
        MEMORY_UTILIZATION.labels(group=metrics.group_id).set(metrics.memory_percent)

        # Instance count
        CONSUMER_INSTANCES.labels(group=metrics.group_id).set(metrics.active_consumers)

# Orchestrator implementations
class KubernetesOrchestrator:
    """Kubernetes-based scaling"""

    def __init__(self):
        try:
            config.load_incluster_config()
        except:
            config.load_kube_config()

        self.apps_v1 = client.AppsV1Api()
        self.core_v1 = client.CoreV1Api()
        self.namespace = os.getenv('K8S_NAMESPACE', 'default')

    async def scale_deployment(self, deployment_name: str, replicas: int):
        """Scale Kubernetes deployment"""
        # Update deployment replicas
        body = {'spec': {'replicas': replicas}}
        self.apps_v1.patch_namespaced_deployment_scale(
            name=deployment_name,
            namespace=self.namespace,
            body=body
        )

    async def get_resource_metrics(self, deployment_name: str) -> Tuple[float, float]:
        """Get CPU and memory metrics from Kubernetes"""
        # In production, use metrics-server API
        # For now, return mock values
        return 60.0, 70.0

class DockerOrchestrator:
    """Docker-based scaling"""

    def __init__(self, docker_client):
        self.docker_client = docker_client

    async def scale_deployment(self, service_name: str, replicas: int):
        """Scale Docker service"""
        try:
            # For Docker Swarm
            service = self.docker_client.services.get(service_name)
            service.update(replicas=replicas)
        except:
            # For Docker Compose, we can't directly scale
            # Would need to use docker-compose scale command
            logger.warning(f"Docker Compose scaling not implemented, would scale {service_name} to {replicas}")

    async def get_resource_metrics(self, service_name: str) -> Tuple[float, float]:
        """Get container resource metrics"""
        try:
            containers = self.docker_client.containers.list(filters={'label': f'com.docker.compose.service={service_name}'})
            if containers:
                stats = containers[0].stats(stream=False)
                # Calculate CPU percentage
                cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - stats['precpu_stats']['cpu_usage']['total_usage']
                system_delta = stats['cpu_stats']['system_cpu_usage'] - stats['precpu_stats']['system_cpu_usage']
                cpu_percent = (cpu_delta / system_delta) * 100.0 if system_delta > 0 else 0

                # Calculate memory percentage
                memory_usage = stats['memory_stats']['usage']
                memory_limit = stats['memory_stats']['limit']
                memory_percent = (memory_usage / memory_limit) * 100.0 if memory_limit > 0 else 0

                return cpu_percent, memory_percent
        except:
            return 0.0, 0.0

class MockOrchestrator:
    """Mock orchestrator for testing"""

    async def scale_deployment(self, deployment_name: str, replicas: int):
        logger.info(f"[MOCK] Would scale {deployment_name} to {replicas} replicas")

    async def get_resource_metrics(self, deployment_name: str) -> Tuple[float, float]:
        # Return mock metrics
        import random
        return random.uniform(40, 80), random.uniform(30, 70)

# Predictive scaling based on historical patterns
class PredictiveScaler:
    """Predictive scaling using historical lag patterns"""

    def __init__(self, autoscaler: KafkaConsumerAutoscaler):
        self.autoscaler = autoscaler
        self.history_window_hours = 168  # 1 week

    async def predict_scaling_needs(self, group_id: str) -> int:
        """Predict future scaling needs based on historical patterns"""
        # Get historical lag data from Redis
        history_key = f"lag_history:{group_id}"
        history = self.autoscaler.redis_client.lrange(history_key, 0, -1)

        if len(history) < 24:  # Need at least 24 hours of data
            return 0

        # Convert to numeric values
        lag_values = [int(h) for h in history[-168:]]  # Last week

        # Simple prediction: find pattern at same time yesterday/last week
        current_hour = datetime.now().hour
        same_time_yesterday = lag_values[-24 + current_hour] if len(lag_values) > 24 else 0
        same_time_last_week = lag_values[-168 + current_hour] if len(lag_values) > 168 else 0

        # Weighted average
        predicted_lag = (same_time_yesterday * 0.7 + same_time_last_week * 0.3)

        # Calculate required replicas
        required_replicas = int(predicted_lag / self.autoscaler.policy.target_lag_per_instance) + 1

        return max(self.autoscaler.policy.min_replicas, min(required_replicas, self.autoscaler.policy.max_replicas))

async def main():
    """Main entry point"""
    # Initialize autoscaler
    policy = ScalingPolicy(
        min_replicas=1,
        max_replicas=20,
        target_lag_per_instance=10000,
        cpu_threshold_percent=70,
        memory_threshold_percent=80,
        cooldown_seconds=300
    )

    autoscaler = KafkaConsumerAutoscaler(policy)

    logger.info("Starting Kafka Consumer Autoscaler")
    logger.info(f"Monitoring consumer groups: {[g['group_id'] for g in autoscaler.consumer_groups]}")
    logger.info("Metrics available at http://localhost:9093/metrics")

    # Start monitoring and scaling
    await autoscaler.monitor_and_scale()

if __name__ == "__main__":
    asyncio.run(main())