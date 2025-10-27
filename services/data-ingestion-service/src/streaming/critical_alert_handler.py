"""
Critical Alert Handler for Ultra-Low Latency (<1s) Fire Alerts
Bypasses queue system for life-critical notifications
Direct path: Source → WebSocket → Kafka (no batching)
"""

import asyncio
import json
import time
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timezone
import websockets
from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaError
import structlog

logger = structlog.get_logger()


class CriticalAlertHandler:
    """
    Handles critical fire alerts requiring <1s end-to-end latency.
    Bypasses standard queue system for direct WebSocket → Kafka streaming.

    Use cases:
    - Evacuation orders
    - First responder alerts
    - Imminent threat warnings
    - Life safety notifications
    """

    def __init__(
        self,
        kafka_bootstrap_servers: str = "kafka:9092",
        alert_topic: str = "wildfire-critical-alerts",
        max_latency_ms: int = 100,
        heartbeat_interval: int = 30
    ):
        self.kafka_servers = kafka_bootstrap_servers
        self.alert_topic = alert_topic
        self.max_latency_ms = max_latency_ms
        self.heartbeat_interval = heartbeat_interval

        # Direct Kafka producer (no batching)
        self.producer: Optional[AIOKafkaProducer] = None

        # WebSocket connections
        self.ws_connections: Dict[str, websockets.WebSocketClientProtocol] = {}

        # Metrics
        self.metrics = {
            'alerts_sent': 0,
            'alerts_failed': 0,
            'avg_latency_ms': 0,
            'max_latency_ms': 0,
            'min_latency_ms': float('inf'),
            'last_alert_time': None,
            'connections_active': 0,
            'reconnection_count': 0
        }

        # Latency tracking
        self._latency_buffer: List[float] = []
        self._latency_buffer_size = 100

        # Alert callbacks
        self.alert_callbacks: List[Callable] = []

        # Running state
        self.is_running = False
        self._tasks: List[asyncio.Task] = []

    async def initialize(self) -> bool:
        """Initialize Kafka producer for direct streaming"""
        try:
            # Create producer with minimal latency settings
            # Note: enable_idempotence requires acks='all' in aiokafka 0.11.0
            self.producer = AIOKafkaProducer(
                bootstrap_servers=self.kafka_servers,
                compression_type=None,  # No compression for speed
                acks='all',  # Wait for all in-sync replicas (required for idempotence)
                linger_ms=0,  # Send immediately, no batching
                max_batch_size=1,  # One message at a time
                enable_idempotence=True,  # Prevent duplicate messages
                value_serializer=lambda v: json.dumps(v).encode('utf-8')
            )

            await self.producer.start()

            logger.info(
                "Critical alert handler initialized",
                kafka_servers=self.kafka_servers,
                topic=self.alert_topic,
                max_latency_ms=self.max_latency_ms
            )

            return True

        except Exception as e:
            logger.error(
                "Failed to initialize critical alert handler",
                error=str(e),
                exc_info=True
            )
            return False

    async def connect_websocket(
        self,
        source_id: str,
        ws_url: str,
        headers: Optional[Dict[str, str]] = None
    ) -> bool:
        """Connect to WebSocket source for real-time alerts"""
        try:
            # Connect with automatic reconnection
            ws = await websockets.connect(
                ws_url,
                extra_headers=headers,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=10
            )

            self.ws_connections[source_id] = ws
            self.metrics['connections_active'] += 1

            # Start listening task
            task = asyncio.create_task(
                self._listen_websocket(source_id, ws)
            )
            self._tasks.append(task)

            logger.info(
                "WebSocket connected for critical alerts",
                source_id=source_id,
                url=ws_url
            )

            return True

        except Exception as e:
            logger.error(
                "Failed to connect WebSocket",
                source_id=source_id,
                error=str(e)
            )
            return False

    async def _listen_websocket(
        self,
        source_id: str,
        ws: websockets.WebSocketClientProtocol
    ):
        """Listen for critical alerts from WebSocket"""
        reconnect_delay = 1

        while self.is_running:
            try:
                async for message in ws:
                    # Track receive time immediately
                    receive_time = time.time() * 1000  # milliseconds

                    # Parse alert
                    try:
                        alert_data = json.loads(message)
                    except json.JSONDecodeError:
                        alert_data = {'raw_message': message}

                    # Add critical metadata
                    alert_data.update({
                        'source_id': source_id,
                        'received_at': receive_time,
                        'alert_type': 'CRITICAL',
                        'handler': 'direct_websocket'
                    })

                    # Send directly to Kafka (bypass all queues)
                    await self._send_critical_alert(alert_data)

                    # Reset reconnect delay on success
                    reconnect_delay = 1

            except websockets.exceptions.ConnectionClosed:
                logger.warning(
                    "WebSocket connection closed, reconnecting",
                    source_id=source_id,
                    delay=reconnect_delay
                )

                # Exponential backoff for reconnection
                await asyncio.sleep(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 2, 60)

                # Attempt reconnection
                if source_id in self.ws_connections:
                    try:
                        ws = await websockets.connect(ws.host + ws.path)
                        self.ws_connections[source_id] = ws
                        self.metrics['reconnection_count'] += 1
                    except Exception as e:
                        logger.error(
                            "Reconnection failed",
                            source_id=source_id,
                            error=str(e)
                        )

            except Exception as e:
                logger.error(
                    "WebSocket listener error",
                    source_id=source_id,
                    error=str(e),
                    exc_info=True
                )
                await asyncio.sleep(5)

    async def send_critical_alert(
        self,
        alert_data: Dict[str, Any],
        source_id: str = "manual"
    ) -> bool:
        """
        Public method to send a critical alert directly to Kafka.
        Used for programmatic alert generation.
        """
        alert_data.update({
            'source_id': source_id,
            'received_at': time.time() * 1000,
            'alert_type': 'CRITICAL',
            'handler': 'direct_api'
        })

        return await self._send_critical_alert(alert_data)

    async def _send_critical_alert(self, alert_data: Dict[str, Any]) -> bool:
        """Internal method to send alert to Kafka with latency tracking"""
        send_start = time.time() * 1000

        try:
            # Extract location for partition key (ensure geographic locality)
            partition_key = None
            if 'latitude' in alert_data and 'longitude' in alert_data:
                # Use geohash or grid cell as partition key
                partition_key = f"{alert_data['latitude']:.2f},{alert_data['longitude']:.2f}"

            # Add send timestamp
            alert_data['sent_at'] = send_start
            alert_data['timestamp'] = datetime.now(timezone.utc).isoformat()

            # Send to Kafka immediately
            future = await self.producer.send(
                self.alert_topic,
                value=alert_data,
                key=partition_key.encode() if partition_key else None
            )

            # Wait for acknowledgment
            await future

            # Calculate latency
            send_end = time.time() * 1000
            total_latency = send_end - alert_data.get('received_at', send_start)
            kafka_latency = send_end - send_start

            # Update metrics
            self._update_latency_metrics(total_latency)
            self.metrics['alerts_sent'] += 1
            self.metrics['last_alert_time'] = datetime.now(timezone.utc).isoformat()

            # Trigger callbacks
            for callback in self.alert_callbacks:
                asyncio.create_task(callback(alert_data))

            # Log if latency exceeds threshold
            if total_latency > self.max_latency_ms:
                logger.warning(
                    "Critical alert latency exceeded threshold",
                    total_latency_ms=total_latency,
                    kafka_latency_ms=kafka_latency,
                    threshold_ms=self.max_latency_ms,
                    source_id=alert_data.get('source_id')
                )
            else:
                logger.debug(
                    "Critical alert sent successfully",
                    latency_ms=total_latency,
                    source_id=alert_data.get('source_id')
                )

            return True

        except KafkaError as e:
            self.metrics['alerts_failed'] += 1
            logger.error(
                "Failed to send critical alert to Kafka",
                error=str(e),
                source_id=alert_data.get('source_id'),
                exc_info=True
            )
            return False

        except Exception as e:
            self.metrics['alerts_failed'] += 1
            logger.error(
                "Unexpected error sending critical alert",
                error=str(e),
                exc_info=True
            )
            return False

    def _update_latency_metrics(self, latency_ms: float):
        """Update latency metrics with new measurement"""
        # Add to buffer
        self._latency_buffer.append(latency_ms)
        if len(self._latency_buffer) > self._latency_buffer_size:
            self._latency_buffer.pop(0)

        # Update metrics
        if self._latency_buffer:
            self.metrics['avg_latency_ms'] = sum(self._latency_buffer) / len(self._latency_buffer)
            self.metrics['max_latency_ms'] = max(self.metrics['max_latency_ms'], latency_ms)
            self.metrics['min_latency_ms'] = min(self.metrics['min_latency_ms'], latency_ms)

    async def start_heartbeat(self):
        """Start heartbeat monitoring for all connections"""
        while self.is_running:
            try:
                # Send heartbeat to all WebSocket connections
                for source_id, ws in list(self.ws_connections.items()):
                    try:
                        await ws.ping()
                    except Exception:
                        logger.warning(
                            "Heartbeat failed for WebSocket",
                            source_id=source_id
                        )
                        # Connection likely dead, will be handled by listener

                # Log metrics periodically
                if self.metrics['alerts_sent'] > 0:
                    logger.info(
                        "Critical alert handler metrics",
                        alerts_sent=self.metrics['alerts_sent'],
                        avg_latency_ms=round(self.metrics['avg_latency_ms'], 2),
                        max_latency_ms=round(self.metrics['max_latency_ms'], 2),
                        active_connections=self.metrics['connections_active']
                    )

                await asyncio.sleep(self.heartbeat_interval)

            except Exception as e:
                logger.error(
                    "Heartbeat error",
                    error=str(e)
                )
                await asyncio.sleep(self.heartbeat_interval)

    def add_alert_callback(self, callback: Callable):
        """Add callback to be triggered on each alert"""
        self.alert_callbacks.append(callback)

    async def start(self):
        """Start the critical alert handler"""
        if self.is_running:
            logger.warning("Critical alert handler already running")
            return

        self.is_running = True

        # Initialize Kafka producer
        if not await self.initialize():
            self.is_running = False
            raise RuntimeError("Failed to initialize critical alert handler")

        # Start heartbeat
        heartbeat_task = asyncio.create_task(self.start_heartbeat())
        self._tasks.append(heartbeat_task)

        logger.info("Critical alert handler started")

    async def stop(self):
        """Stop the critical alert handler gracefully"""
        logger.info("Stopping critical alert handler")
        self.is_running = False

        # Close WebSocket connections
        for source_id, ws in self.ws_connections.items():
            try:
                await ws.close()
            except Exception as e:
                logger.error(
                    "Error closing WebSocket",
                    source_id=source_id,
                    error=str(e)
                )

        # Cancel all tasks
        for task in self._tasks:
            task.cancel()

        # Wait for tasks to complete
        await asyncio.gather(*self._tasks, return_exceptions=True)

        # Close Kafka producer
        if self.producer:
            await self.producer.stop()

        logger.info(
            "Critical alert handler stopped",
            total_alerts_sent=self.metrics['alerts_sent'],
            total_alerts_failed=self.metrics['alerts_failed']
        )

    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics"""
        return {
            **self.metrics,
            'latency_percentiles': self._calculate_percentiles() if self._latency_buffer else {}
        }

    def _calculate_percentiles(self) -> Dict[str, float]:
        """Calculate latency percentiles"""
        sorted_latencies = sorted(self._latency_buffer)
        n = len(sorted_latencies)

        return {
            'p50': sorted_latencies[n // 2] if n > 0 else 0,
            'p95': sorted_latencies[int(n * 0.95)] if n > 0 else 0,
            'p99': sorted_latencies[int(n * 0.99)] if n > 0 else 0
        }

    def is_healthy(self) -> bool:
        """Check if handler is healthy"""
        if not self.is_running:
            return False

        if not self.producer:
            return False

        # Check if latency is acceptable
        if self.metrics['avg_latency_ms'] > self.max_latency_ms * 2:
            return False

        # Check if we've sent alerts recently (if we have connections)
        if self.metrics['connections_active'] > 0:
            if self.metrics['last_alert_time']:
                last_alert = datetime.fromisoformat(self.metrics['last_alert_time'].replace('Z', '+00:00'))
                time_since_last = (datetime.now(timezone.utc) - last_alert).total_seconds()
                if time_since_last > 300:  # 5 minutes without alerts
                    logger.warning("No alerts sent in 5 minutes despite active connections")

        return True


# Example usage for testing
async def test_critical_alerts():
    """Test function for critical alert handler"""
    handler = CriticalAlertHandler(
        kafka_bootstrap_servers="localhost:9092",
        max_latency_ms=100
    )

    await handler.start()

    # Send test alert
    test_alert = {
        'alert_type': 'EVACUATION_ORDER',
        'severity': 'CRITICAL',
        'location': 'Paradise, CA',
        'latitude': 39.7596,
        'longitude': -121.6219,
        'message': 'Immediate evacuation ordered for Paradise area',
        'affected_population': 26000,
        'fire_name': 'Camp Fire',
        'timestamp': datetime.now(timezone.utc).isoformat()
    }

    success = await handler.send_critical_alert(test_alert, source_id="test")
    print(f"Alert sent: {success}")

    # Get metrics
    metrics = handler.get_metrics()
    print(f"Metrics: {json.dumps(metrics, indent=2)}")

    await handler.stop()


if __name__ == "__main__":
    asyncio.run(test_critical_alerts())