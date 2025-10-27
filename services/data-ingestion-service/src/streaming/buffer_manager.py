"""
Centralized Buffer Manager for Edge Resilience
Manages offline buffering across all connectors for network disconnection scenarios
Provides unified monitoring and health checks for buffer status
"""

import asyncio
import json
import pickle
from pathlib import Path
from collections import deque
from typing import Dict, Any, Optional, List, Deque, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
import structlog

logger = structlog.get_logger()


@dataclass
class BufferConfig:
    """Configuration for a buffer instance"""
    buffer_id: str
    connector_type: str
    max_size: int = 10000
    persist_path: Optional[Path] = None
    flush_batch_size: int = 100
    persist_interval: int = 100  # Persist every N messages
    ttl_hours: int = 24  # Time to live for buffered messages
    priority: int = 0  # Higher priority buffers flush first


class BufferInstance:
    """Individual buffer instance for a connector"""

    def __init__(self, config: BufferConfig):
        self.config = config
        self.buffer: Deque[Dict[str, Any]] = deque(maxlen=config.max_size)
        self.metrics = {
            'messages_buffered': 0,
            'messages_dropped': 0,
            'messages_flushed': 0,
            'buffer_flushes': 0,
            'max_size_reached': 0,
            'oldest_message_age': None,
            'newest_message_age': None
        }
        self.is_active = True
        self.last_persist_time = datetime.now()

        # Load persisted buffer if exists
        self._load_from_disk()

    def add_message(self, message: Dict[str, Any]) -> bool:
        """Add a message to the buffer"""
        try:
            # Add metadata
            message['buffered_at'] = datetime.now().isoformat()
            message['buffer_id'] = self.config.buffer_id

            # Check if buffer is full
            if len(self.buffer) >= self.config.max_size:
                self.metrics['messages_dropped'] += 1
                self.metrics['max_size_reached'] += 1
                logger.warning(
                    "Buffer full, dropping oldest message",
                    buffer_id=self.config.buffer_id,
                    size=len(self.buffer)
                )

            self.buffer.append(message)
            self.metrics['messages_buffered'] += 1

            # Update age metrics
            if self.buffer:
                self.metrics['oldest_message_age'] = self.buffer[0].get('buffered_at')
                self.metrics['newest_message_age'] = self.buffer[-1].get('buffered_at')

            # Persist if interval reached
            if len(self.buffer) % self.config.persist_interval == 0:
                self._persist_to_disk()

            return True

        except Exception as e:
            logger.error(
                "Failed to buffer message",
                buffer_id=self.config.buffer_id,
                error=str(e)
            )
            return False

    def get_batch(self, batch_size: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get a batch of messages for flushing"""
        size = batch_size or self.config.flush_batch_size
        batch = []

        for _ in range(min(size, len(self.buffer))):
            if self.buffer:
                message = self.buffer.popleft()

                # Check TTL
                buffered_at = datetime.fromisoformat(message.get('buffered_at', datetime.now().isoformat()))
                age_hours = (datetime.now() - buffered_at).total_seconds() / 3600

                if age_hours > self.config.ttl_hours:
                    self.metrics['messages_dropped'] += 1
                    logger.warning(
                        "Dropping expired message",
                        buffer_id=self.config.buffer_id,
                        age_hours=age_hours,
                        ttl_hours=self.config.ttl_hours
                    )
                    continue

                batch.append(message)

        if batch:
            self.metrics['messages_flushed'] += len(batch)
            self.metrics['buffer_flushes'] += 1

        return batch

    def return_batch(self, batch: List[Dict[str, Any]]):
        """Return messages to buffer if flush failed"""
        for message in reversed(batch):
            self.buffer.appendleft(message)
        self.metrics['messages_flushed'] -= len(batch)

    def _persist_to_disk(self):
        """Persist buffer to disk"""
        if not self.config.persist_path:
            return

        try:
            buffer_data = list(self.buffer)
            with open(self.config.persist_path, 'wb') as f:
                pickle.dump({
                    'buffer_id': self.config.buffer_id,
                    'data': buffer_data,
                    'metrics': self.metrics,
                    'timestamp': datetime.now().isoformat()
                }, f)
            self.last_persist_time = datetime.now()
            logger.debug(
                "Buffer persisted to disk",
                buffer_id=self.config.buffer_id,
                messages=len(buffer_data)
            )
        except Exception as e:
            logger.error(
                "Failed to persist buffer",
                buffer_id=self.config.buffer_id,
                error=str(e)
            )

    def _load_from_disk(self):
        """Load buffer from disk if exists"""
        if not self.config.persist_path or not self.config.persist_path.exists():
            return

        try:
            with open(self.config.persist_path, 'rb') as f:
                data = pickle.load(f)

            if data.get('buffer_id') == self.config.buffer_id:
                buffer_data = data.get('data', [])
                restore_count = min(len(buffer_data), self.config.max_size)
                self.buffer = deque(buffer_data[:restore_count], maxlen=self.config.max_size)

                # Restore metrics
                if 'metrics' in data:
                    self.metrics.update(data['metrics'])

                logger.info(
                    "Buffer restored from disk",
                    buffer_id=self.config.buffer_id,
                    messages_restored=restore_count,
                    timestamp=data.get('timestamp')
                )
        except Exception as e:
            logger.error(
                "Failed to load buffer from disk",
                buffer_id=self.config.buffer_id,
                error=str(e)
            )

    def clear(self):
        """Clear the buffer and remove persisted file"""
        self.buffer.clear()
        if self.config.persist_path and self.config.persist_path.exists():
            try:
                self.config.persist_path.unlink()
            except Exception:
                pass

    def get_metrics(self) -> Dict[str, Any]:
        """Get buffer metrics"""
        return {
            **self.metrics,
            'current_size': len(self.buffer),
            'max_size': self.config.max_size,
            'utilization': len(self.buffer) / self.config.max_size if self.config.max_size > 0 else 0,
            'is_active': self.is_active
        }


class BufferManager:
    """
    Centralized buffer manager for all connectors
    Provides unified monitoring and management of offline buffers
    """

    def __init__(self, buffer_dir: Path = Path("./buffers")):
        self.buffer_dir = buffer_dir
        self.buffer_dir.mkdir(exist_ok=True)

        self.buffers: Dict[str, BufferInstance] = {}
        self.flush_callbacks: Dict[str, Callable] = {}

        # Global metrics
        self.global_metrics = {
            'total_buffers': 0,
            'total_messages_buffered': 0,
            'total_messages_dropped': 0,
            'total_messages_flushed': 0,
            'total_buffer_size': 0,
            'last_health_check': None
        }

        # Start background tasks
        self._background_tasks = []
        self.is_running = True

    def create_buffer(
        self,
        connector_id: str,
        connector_type: str,
        max_size: int = 10000,
        flush_callback: Optional[Callable] = None,
        **kwargs
    ) -> str:
        """Create a new buffer for a connector"""
        buffer_id = f"{connector_type}_{connector_id}_{datetime.now().timestamp()}"

        config = BufferConfig(
            buffer_id=buffer_id,
            connector_type=connector_type,
            max_size=max_size,
            persist_path=self.buffer_dir / f"{buffer_id}.pkl",
            **kwargs
        )

        buffer_instance = BufferInstance(config)
        self.buffers[buffer_id] = buffer_instance

        if flush_callback:
            self.flush_callbacks[buffer_id] = flush_callback

        self.global_metrics['total_buffers'] = len(self.buffers)

        logger.info(
            "Buffer created",
            buffer_id=buffer_id,
            connector_type=connector_type,
            max_size=max_size
        )

        return buffer_id

    def add_message(self, buffer_id: str, message: Dict[str, Any]) -> bool:
        """Add a message to a specific buffer"""
        if buffer_id not in self.buffers:
            logger.error("Buffer not found", buffer_id=buffer_id)
            return False

        success = self.buffers[buffer_id].add_message(message)
        if success:
            self.global_metrics['total_messages_buffered'] += 1

        return success

    async def flush_buffer(self, buffer_id: str, batch_size: Optional[int] = None) -> int:
        """Flush messages from a specific buffer"""
        if buffer_id not in self.buffers:
            logger.error("Buffer not found", buffer_id=buffer_id)
            return 0

        buffer = self.buffers[buffer_id]
        callback = self.flush_callbacks.get(buffer_id)

        if not callback:
            logger.warning("No flush callback registered", buffer_id=buffer_id)
            return 0

        flushed_count = 0

        while buffer.buffer:
            batch = buffer.get_batch(batch_size)
            if not batch:
                break

            try:
                # Call the flush callback
                success = await callback(batch)

                if success:
                    flushed_count += len(batch)
                    self.global_metrics['total_messages_flushed'] += len(batch)
                else:
                    # Return messages to buffer if flush failed
                    buffer.return_batch(batch)
                    break

            except Exception as e:
                logger.error(
                    "Flush callback failed",
                    buffer_id=buffer_id,
                    error=str(e)
                )
                buffer.return_batch(batch)
                break

        return flushed_count

    async def flush_all_buffers(self, priority_only: bool = False) -> Dict[str, int]:
        """Flush all buffers, optionally only high-priority ones"""
        results = {}

        # Sort buffers by priority
        sorted_buffers = sorted(
            self.buffers.items(),
            key=lambda x: x[1].config.priority,
            reverse=True
        )

        for buffer_id, buffer_instance in sorted_buffers:
            if priority_only and buffer_instance.config.priority <= 0:
                continue

            count = await self.flush_buffer(buffer_id)
            results[buffer_id] = count

            logger.info(
                "Buffer flushed",
                buffer_id=buffer_id,
                messages_flushed=count,
                remaining=len(buffer_instance.buffer)
            )

        return results

    def remove_buffer(self, buffer_id: str):
        """Remove a buffer and clean up its resources"""
        if buffer_id not in self.buffers:
            return

        buffer = self.buffers[buffer_id]
        buffer.clear()

        del self.buffers[buffer_id]
        if buffer_id in self.flush_callbacks:
            del self.flush_callbacks[buffer_id]

        self.global_metrics['total_buffers'] = len(self.buffers)

        logger.info("Buffer removed", buffer_id=buffer_id)

    def get_buffer_metrics(self, buffer_id: str) -> Optional[Dict[str, Any]]:
        """Get metrics for a specific buffer"""
        if buffer_id not in self.buffers:
            return None

        return self.buffers[buffer_id].get_metrics()

    def get_all_metrics(self) -> Dict[str, Any]:
        """Get metrics for all buffers and global stats"""
        # Update global metrics
        total_size = sum(len(b.buffer) for b in self.buffers.values())
        total_dropped = sum(b.metrics['messages_dropped'] for b in self.buffers.values())

        self.global_metrics.update({
            'total_buffer_size': total_size,
            'total_messages_dropped': total_dropped,
            'last_health_check': datetime.now().isoformat()
        })

        return {
            'global': self.global_metrics,
            'buffers': {
                buffer_id: buffer.get_metrics()
                for buffer_id, buffer in self.buffers.items()
            }
        }

    def is_healthy(self) -> bool:
        """Check overall buffer health"""
        if not self.buffers:
            return True  # No buffers = healthy

        unhealthy_count = 0

        for buffer_id, buffer in self.buffers.items():
            metrics = buffer.get_metrics()

            # Check utilization
            if metrics['utilization'] > 0.9:
                unhealthy_count += 1
                logger.warning(
                    "Buffer near capacity",
                    buffer_id=buffer_id,
                    utilization=metrics['utilization']
                )

            # Check drop rate
            total = metrics['messages_buffered'] + metrics['messages_dropped']
            if total > 100:
                drop_rate = metrics['messages_dropped'] / total
                if drop_rate > 0.1:
                    unhealthy_count += 1
                    logger.warning(
                        "High drop rate",
                        buffer_id=buffer_id,
                        drop_rate=drop_rate
                    )

        return unhealthy_count < len(self.buffers) * 0.5  # Healthy if less than 50% unhealthy

    async def start_monitoring(self, interval_seconds: int = 60):
        """Start background monitoring task"""
        while self.is_running:
            try:
                await asyncio.sleep(interval_seconds)

                # Persist all buffers periodically
                for buffer in self.buffers.values():
                    buffer._persist_to_disk()

                # Log health status
                metrics = self.get_all_metrics()
                logger.info(
                    "Buffer manager health check",
                    total_buffers=metrics['global']['total_buffers'],
                    total_messages=metrics['global']['total_buffer_size'],
                    is_healthy=self.is_healthy()
                )

            except Exception as e:
                logger.error("Monitoring task error", error=str(e))

    async def start(self):
        """Start the buffer manager"""
        logger.info("Buffer manager starting")

        # Start monitoring
        monitor_task = asyncio.create_task(self.start_monitoring())
        self._background_tasks.append(monitor_task)

        logger.info("Buffer manager started")

    async def stop(self):
        """Stop the buffer manager gracefully"""
        logger.info("Buffer manager stopping")
        self.is_running = False

        # Persist all buffers
        for buffer in self.buffers.values():
            buffer._persist_to_disk()

        # Cancel background tasks
        for task in self._background_tasks:
            task.cancel()

        await asyncio.gather(*self._background_tasks, return_exceptions=True)

        logger.info(
            "Buffer manager stopped",
            total_messages_buffered=self.global_metrics['total_messages_buffered'],
            total_messages_flushed=self.global_metrics['total_messages_flushed']
        )


# Singleton instance
_buffer_manager: Optional[BufferManager] = None


def get_buffer_manager() -> BufferManager:
    """Get or create the singleton buffer manager instance"""
    global _buffer_manager
    if _buffer_manager is None:
        _buffer_manager = BufferManager()
    return _buffer_manager


# Example usage
async def test_buffer_manager():
    """Test the buffer manager"""
    manager = get_buffer_manager()
    await manager.start()

    # Create a buffer for IoT connector
    async def flush_callback(messages):
        print(f"Flushing {len(messages)} messages to Kafka")
        return True  # Simulate successful flush

    buffer_id = manager.create_buffer(
        connector_id="iot_001",
        connector_type="mqtt",
        max_size=1000,
        flush_callback=flush_callback,
        priority=10  # High priority for critical IoT data
    )

    # Add some messages
    for i in range(100):
        manager.add_message(buffer_id, {
            'data': f'Message {i}',
            'timestamp': datetime.now().isoformat()
        })

    # Flush the buffer
    flushed = await manager.flush_buffer(buffer_id)
    print(f"Flushed {flushed} messages")

    # Get metrics
    metrics = manager.get_all_metrics()
    print(f"Metrics: {json.dumps(metrics, indent=2)}")

    await manager.stop()


if __name__ == "__main__":
    asyncio.run(test_buffer_manager())