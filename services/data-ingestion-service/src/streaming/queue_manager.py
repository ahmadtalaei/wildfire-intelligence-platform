"""
QueueManager: Async queue for decoupling API polling from Kafka sending
Provides buffering, priority handling, and backpressure management
"""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from collections import deque
from enum import Enum
import structlog

logger = structlog.get_logger()


class MessagePriority(Enum):
    """Message priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class QueueManager:
    """
    Async queue manager for decoupling data fetching from sending
    Provides buffering, priority handling, and overflow protection
    """

    def __init__(
        self,
        max_size: int = 10000,
        overflow_strategy: str = 'drop_oldest',  # 'drop_oldest', 'drop_newest', 'block'
        enable_priorities: bool = True
    ):
        self.max_size = max_size
        self.overflow_strategy = overflow_strategy
        self.enable_priorities = enable_priorities

        # Queues
        if enable_priorities:
            self.queues = {
                MessagePriority.CRITICAL: asyncio.Queue(),
                MessagePriority.HIGH: asyncio.Queue(),
                MessagePriority.NORMAL: asyncio.Queue(),
                MessagePriority.LOW: asyncio.Queue()
            }
        else:
            self.queue = asyncio.Queue(maxsize=max_size)

        # Overflow buffer (for drop_oldest strategy)
        self._overflow_buffer: deque = deque(maxlen=1000)

        # Metrics
        self.enqueued_count = 0
        self.dequeued_count = 0
        self.dropped_count = 0
        self.blocked_count = 0

        # Size tracking for priority queues
        self._size_by_priority = {p: 0 for p in MessagePriority}

    async def enqueue(
        self,
        data: Dict[str, Any],
        priority: MessagePriority = MessagePriority.NORMAL,
        source_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Add data to queue with priority

        Returns:
            Dict with success status and queue state
        """
        # Check total size
        current_size = await self.size()

        if current_size >= self.max_size:
            return await self._handle_overflow(data, priority, source_id)

        # Add metadata
        message = {
            'data': data,
            'priority': priority.value,
            'source_id': source_id,
            'enqueued_at': datetime.now(timezone.utc).isoformat(),
            'message_id': f"{source_id}_{datetime.now().timestamp()}" if source_id else None
        }

        # Enqueue based on priority
        if self.enable_priorities:
            await self.queues[priority].put(message)
            self._size_by_priority[priority] += 1
        else:
            await self.queue.put(message)

        self.enqueued_count += 1

        logger.debug(
            "Message enqueued",
            source_id=source_id,
            priority=priority.name,
            queue_size=current_size + 1
        )

        return {
            'success': True,
            'queue_size': current_size + 1,
            'priority': priority.name
        }

    async def enqueue_batch(
        self,
        data_list: List[Dict[str, Any]],
        priority: MessagePriority = MessagePriority.NORMAL,
        source_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Batch enqueue for ultra-low latency
        Optimized for high-throughput scenarios

        Args:
            data_list: List of data dictionaries to enqueue
            priority: Priority level for all messages
            source_id: Source identifier

        Returns:
            Dict with success status and counts
        """
        if not data_list:
            return {'success': True, 'enqueued': 0, 'failed': 0}

        current_size = await self.size()
        enqueued = 0
        failed = 0
        timestamp = datetime.now(timezone.utc).isoformat()

        for data in data_list:
            # Check capacity before each enqueue
            if current_size + enqueued >= self.max_size:
                # Handle overflow for remaining messages
                result = await self._handle_overflow(data, priority, source_id)
                if result['success']:
                    enqueued += 1
                else:
                    failed += 1
                continue

            # Build message
            message = {
                'data': data,
                'priority': priority.value,
                'source_id': source_id,
                'enqueued_at': timestamp,
                'message_id': f"{source_id}_{datetime.now().timestamp()}" if source_id else None
            }

            # Fast path enqueue
            try:
                if self.enable_priorities:
                    await self.queues[priority].put(message)
                    self._size_by_priority[priority] += 1
                else:
                    await self.queue.put(message)

                enqueued += 1
                self.enqueued_count += 1

            except Exception as e:
                logger.error("Batch enqueue error", error=str(e), source_id=source_id)
                failed += 1

        logger.debug(
            "Batch enqueued",
            source_id=source_id,
            priority=priority.name,
            enqueued=enqueued,
            failed=failed,
            queue_size=current_size + enqueued
        )

        return {
            'success': failed == 0,
            'enqueued': enqueued,
            'failed': failed,
            'queue_size': current_size + enqueued
        }

    async def dequeue(self, timeout: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """
        Get next message from queue, respecting priorities

        Returns:
            Message dict or None if queue is empty and timeout reached
        """
        try:
            if self.enable_priorities:
                # Check queues in priority order
                for priority in [MessagePriority.CRITICAL, MessagePriority.HIGH,
                                MessagePriority.NORMAL, MessagePriority.LOW]:
                    if self._size_by_priority[priority] > 0:
                        message = await asyncio.wait_for(
                            self.queues[priority].get(),
                            timeout=timeout if timeout else 0.001
                        )
                        self._size_by_priority[priority] -= 1
                        self.dequeued_count += 1
                        return message
                return None
            else:
                message = await asyncio.wait_for(
                    self.queue.get(),
                    timeout=timeout
                )
                self.dequeued_count += 1
                return message

        except asyncio.TimeoutError:
            return None

    async def dequeue_batch(
        self,
        batch_size: int = 100,
        timeout: float = 1.0
    ) -> List[Dict[str, Any]]:
        """
        Dequeue multiple messages at once for efficient batch processing

        Returns:
            List of messages (may be less than batch_size)
        """
        batch = []
        start_time = asyncio.get_event_loop().time()

        while len(batch) < batch_size:
            # Calculate remaining timeout
            elapsed = asyncio.get_event_loop().time() - start_time
            remaining_timeout = max(0, timeout - elapsed)

            if remaining_timeout <= 0:
                break

            message = await self.dequeue(timeout=remaining_timeout)
            if message:
                batch.append(message)
            else:
                break

        if batch:
            logger.debug(
                "Batch dequeued",
                batch_size=len(batch),
                requested_size=batch_size
            )

        return batch

    async def _handle_overflow(
        self,
        data: Dict[str, Any],
        priority: MessagePriority,
        source_id: Optional[str]
    ) -> Dict[str, Any]:
        """Handle queue overflow based on strategy"""

        if self.overflow_strategy == 'drop_oldest':
            # Remove oldest low-priority message
            if self.enable_priorities and self._size_by_priority[MessagePriority.LOW] > 0:
                try:
                    dropped = await asyncio.wait_for(
                        self.queues[MessagePriority.LOW].get(),
                        timeout=0.1
                    )
                    self._size_by_priority[MessagePriority.LOW] -= 1
                    self._overflow_buffer.append(dropped)
                    self.dropped_count += 1

                    logger.warning(
                        "Dropped oldest low-priority message due to overflow",
                        dropped_source_id=dropped.get('source_id'),
                        new_source_id=source_id
                    )

                    # Now enqueue the new message
                    return await self.enqueue(data, priority, source_id)
                except asyncio.TimeoutError:
                    pass

        elif self.overflow_strategy == 'drop_newest':
            # Drop the new message
            self.dropped_count += 1
            logger.warning(
                "Dropped new message due to overflow",
                source_id=source_id,
                priority=priority.name
            )
            return {
                'success': False,
                'reason': 'queue_full_drop_newest',
                'queue_size': await self.size()
            }

        elif self.overflow_strategy == 'block':
            # Block until space is available
            self.blocked_count += 1
            logger.info(
                "Blocking due to full queue",
                source_id=source_id,
                queue_size=await self.size()
            )

            # Wait for space (with timeout)
            for _ in range(10):  # Max 10 second wait
                await asyncio.sleep(1)
                if await self.size() < self.max_size:
                    return await self.enqueue(data, priority, source_id)

        # Failed to handle overflow
        self.dropped_count += 1
        return {
            'success': False,
            'reason': 'queue_full',
            'queue_size': await self.size(),
            'overflow_strategy': self.overflow_strategy
        }

    async def size(self) -> int:
        """Get total queue size"""
        if self.enable_priorities:
            return sum(self._size_by_priority.values())
        else:
            return self.queue.qsize()

    async def is_empty(self) -> bool:
        """Check if queue is empty"""
        return await self.size() == 0

    async def is_full(self) -> bool:
        """Check if queue is full"""
        return await self.size() >= self.max_size

    async def clear(self):
        """Clear all messages from queue"""
        if self.enable_priorities:
            for priority in MessagePriority:
                while not self.queues[priority].empty():
                    try:
                        await asyncio.wait_for(self.queues[priority].get(), timeout=0.01)
                        self._size_by_priority[priority] -= 1
                    except asyncio.TimeoutError:
                        break
        else:
            while not self.queue.empty():
                try:
                    await asyncio.wait_for(self.queue.get(), timeout=0.01)
                except asyncio.TimeoutError:
                    break

        logger.info("Queue cleared")

    async def get_metrics(self) -> Dict[str, Any]:
        """Get queue metrics"""
        metrics = {
            'total_size': await self.size(),
            'max_size': self.max_size,
            'utilization_percent': round(
                (await self.size() / self.max_size * 100) if self.max_size > 0 else 0,
                2
            ),
            'enqueued_count': self.enqueued_count,
            'dequeued_count': self.dequeued_count,
            'dropped_count': self.dropped_count,
            'blocked_count': self.blocked_count,
            'overflow_strategy': self.overflow_strategy,
            'enable_priorities': self.enable_priorities
        }

        if self.enable_priorities:
            metrics['size_by_priority'] = {
                priority.name: self._size_by_priority[priority]
                for priority in MessagePriority
            }

        return metrics


class PriorityQueueConsumer:
    """
    Consumer that continuously processes messages from QueueManager
    """

    def __init__(
        self,
        queue_manager: QueueManager,
        processor: Any,  # Object with process() method
        batch_size: int = 100,
        batch_timeout: float = 5.0
    ):
        self.queue_manager = queue_manager
        self.processor = processor
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout

        self.is_running = False
        self.processed_count = 0
        self.failed_count = 0

    async def start(self):
        """Start consuming messages"""
        self.is_running = True
        logger.info(
            "Queue consumer starting",
            batch_size=self.batch_size,
            batch_timeout=self.batch_timeout
        )

        asyncio.create_task(self._consume_loop())

    async def stop(self):
        """Stop consuming messages"""
        self.is_running = False
        logger.info(
            "Queue consumer stopped",
            processed_count=self.processed_count,
            failed_count=self.failed_count
        )

    async def _consume_loop(self):
        """Continuous message consumption loop"""
        while self.is_running:
            try:
                # Dequeue batch
                batch = await self.queue_manager.dequeue_batch(
                    batch_size=self.batch_size,
                    timeout=self.batch_timeout
                )

                if batch:
                    # Extract data from messages
                    data_batch = [msg['data'] for msg in batch]

                    # Process batch
                    result = await self.processor.process(data_batch)

                    if result.get('success', False):
                        self.processed_count += len(batch)
                    else:
                        self.failed_count += len(batch)

                    logger.debug(
                        "Batch processed",
                        batch_size=len(batch),
                        success=result.get('success', False)
                    )
                else:
                    # No messages, brief sleep
                    await asyncio.sleep(0.1)

            except Exception as e:
                self.failed_count += len(batch) if batch else 0
                logger.error(
                    "Batch processing error",
                    error=str(e),
                    exc_info=True
                )
                await asyncio.sleep(1)  # Backoff on error

    async def get_metrics(self) -> Dict[str, Any]:
        """Get consumer metrics"""
        return {
            'is_running': self.is_running,
            'processed_count': self.processed_count,
            'failed_count': self.failed_count,
            'success_rate': (
                self.processed_count / (self.processed_count + self.failed_count)
                if (self.processed_count + self.failed_count) > 0
                else 1.0
            ),
            'batch_size': self.batch_size,
            'batch_timeout': self.batch_timeout
        }
