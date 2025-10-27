"""
ProducerWrapper: Handles low-level Kafka producer interactions
Provides retries, batching, serialization, and error handling
"""

import asyncio
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import structlog

try:
    from .kafka_producer import KafkaDataProducer
    from .dead_letter_queue import DeadLetterQueue
except ImportError:
    from kafka_producer import KafkaDataProducer
    from dead_letter_queue import DeadLetterQueue

logger = structlog.get_logger()


class ProducerWrapper:
    """
    Low-level wrapper for Kafka producer with retries, batching, and DLQ
    """

    def __init__(
        self,
        kafka_producer: KafkaDataProducer,
        dlq: Optional[DeadLetterQueue] = None,
        max_retries: int = 3,
        retry_backoff_base: float = 2.0,
        batch_size: int = 500,
        batch_timeout_seconds: float = 5.0
    ):
        self.kafka_producer = kafka_producer
        self.dlq = dlq
        self.max_retries = max_retries
        self.retry_backoff_base = retry_backoff_base
        self.batch_size = batch_size
        self.batch_timeout_seconds = batch_timeout_seconds

        # Metrics
        self.total_sent = 0
        self.total_failed = 0
        self.total_retries = 0
        self.last_send_time = None

        # Internal batch buffer
        self._batch_buffer: List[Dict[str, Any]] = []
        self._batch_metadata: Dict[str, Any] = {}
        self._last_batch_time = time.time()

    async def send_with_retry(
        self,
        data: List[Dict[str, Any]],
        source_type: str,
        source_id: str,
        topic: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send data to Kafka with exponential backoff retry

        Returns:
            Dict with success status, records sent/failed, and retry count
        """
        result = {
            'success': False,
            'records_sent': 0,
            'records_failed': 0,
            'retry_count': 0,
            'error': None
        }

        if not data:
            result['success'] = True
            return result

        attempt = 0
        last_error = None

        while attempt <= self.max_retries:
            try:
                start_time = time.time()

                # Attempt to send
                success = await self.kafka_producer.send_batch_data(
                    data=data,
                    source_type=source_type,
                    source_id=source_id
                )

                send_duration = (time.time() - start_time) * 1000  # ms

                if success:
                    self.total_sent += len(data)
                    self.last_send_time = datetime.now(timezone.utc)

                    result['success'] = True
                    result['records_sent'] = len(data)
                    result['retry_count'] = attempt
                    result['send_duration_ms'] = send_duration

                    logger.info(
                        "Kafka send successful",
                        records=len(data),
                        source_id=source_id,
                        attempt=attempt,
                        duration_ms=round(send_duration, 2)
                    )

                    return result
                else:
                    raise Exception("Kafka producer returned False")

            except Exception as e:
                last_error = str(e)
                attempt += 1
                self.total_retries += 1

                if attempt <= self.max_retries:
                    # Calculate exponential backoff
                    backoff_time = self.retry_backoff_base ** attempt

                    logger.warning(
                        "Kafka send failed, retrying",
                        error=last_error,
                        attempt=attempt,
                        max_retries=self.max_retries,
                        backoff_seconds=backoff_time,
                        source_id=source_id
                    )

                    await asyncio.sleep(backoff_time)
                else:
                    # Max retries exceeded
                    logger.error(
                        "Kafka send failed after max retries",
                        error=last_error,
                        attempts=attempt,
                        records=len(data),
                        source_id=source_id
                    )

        # All retries failed - send to DLQ if available
        self.total_failed += len(data)
        result['success'] = False
        result['records_failed'] = len(data)
        result['retry_count'] = attempt - 1
        result['error'] = last_error

        if self.dlq:
            await self._send_to_dlq(data, source_id, last_error)

        return result

    async def _send_to_dlq(
        self,
        failed_data: List[Dict[str, Any]],
        source_id: str,
        error: str
    ):
        """Send failed records to Dead Letter Queue"""
        try:
            for record in failed_data:
                await self.dlq.add_failed_record(
                    source_id=source_id,
                    record_data=record,
                    error_message=error,
                    max_retries=self.max_retries
                )

            logger.info(
                "Records sent to DLQ",
                count=len(failed_data),
                source_id=source_id
            )
        except Exception as dlq_error:
            logger.error(
                "Failed to send records to DLQ",
                error=str(dlq_error),
                source_id=source_id
            )

    async def send_batched(
        self,
        record: Dict[str, Any],
        source_type: str,
        source_id: str,
        force_flush: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Add record to batch buffer and send when batch is full or timeout occurs

        Returns:
            Send result if batch was flushed, None otherwise
        """
        self._batch_buffer.append(record)
        self._batch_metadata = {
            'source_type': source_type,
            'source_id': source_id
        }

        current_time = time.time()
        batch_age = current_time - self._last_batch_time

        # Check if we should flush
        should_flush = (
            force_flush or
            len(self._batch_buffer) >= self.batch_size or
            batch_age >= self.batch_timeout_seconds
        )

        if should_flush:
            return await self.flush_batch()

        return None

    async def flush_batch(self) -> Optional[Dict[str, Any]]:
        """Flush current batch buffer"""
        if not self._batch_buffer:
            return None

        data = self._batch_buffer.copy()
        metadata = self._batch_metadata.copy()

        # Clear buffer
        self._batch_buffer.clear()
        self._last_batch_time = time.time()

        # Send with retry
        result = await self.send_with_retry(
            data=data,
            source_type=metadata.get('source_type', 'unknown'),
            source_id=metadata.get('source_id', 'unknown')
        )

        return result

    async def get_metrics(self) -> Dict[str, Any]:
        """Get producer metrics"""
        return {
            'total_sent': self.total_sent,
            'total_failed': self.total_failed,
            'total_retries': self.total_retries,
            'success_rate': (
                self.total_sent / (self.total_sent + self.total_failed)
                if (self.total_sent + self.total_failed) > 0
                else 1.0
            ),
            'last_send_time': self.last_send_time.isoformat() if self.last_send_time else None,
            'batch_buffer_size': len(self._batch_buffer),
            'batch_size_limit': self.batch_size
        }

    async def health_check(self) -> Dict[str, Any]:
        """Check producer health"""
        is_healthy = await self.kafka_producer.health_check()

        return {
            'healthy': is_healthy,
            'producer_started': self.kafka_producer.is_started,
            'metrics': await self.get_metrics()
        }
