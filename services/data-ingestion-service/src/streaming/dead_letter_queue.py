"""
Dead Letter Queue (DLQ) Implementation for Failed Messages

Handles failed ingestion messages with retry logic, exponential backoff,
and permanent failure storage for later analysis.
"""

import asyncio
import logging
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from enum import Enum
import uuid

try:
    from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
except ImportError:
    AIOKafkaProducer = None
    AIOKafkaConsumer = None

logger = logging.getLogger(__name__)


class FailureReason(Enum):
    """Enumeration of failure reasons"""
    SCHEMA_VALIDATION = "schema_validation_failed"
    NETWORK_ERROR = "network_error"
    API_ERROR = "api_error"
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit_exceeded"
    PARSING_ERROR = "parsing_error"
    INVALID_DATA = "invalid_data"
    UNKNOWN = "unknown_error"


class DeadLetterQueue:
    """Manages dead letter queue for failed ingestion messages"""

    def __init__(
        self,
        kafka_bootstrap_servers: str,
        postgres_connection=None,
        max_retries: int = 3,
        retry_delay_seconds: int = 60
    ):
        self.kafka_bootstrap_servers = kafka_bootstrap_servers
        self.postgres_connection = postgres_connection
        self.max_retries = max_retries
        self.retry_delay_seconds = retry_delay_seconds

        # DLQ topics
        self.dlq_topic = "wildfire-dlq-failed-messages"
        self.retry_topic = "wildfire-dlq-retry-queue"

        # Kafka producers
        self.dlq_producer = None
        self.retry_producer = None

        # In-memory retry queue (for immediate retries)
        self.retry_queue = asyncio.Queue()

        # Statistics
        self.stats = {
            "total_failures": 0,
            "retry_successes": 0,
            "permanent_failures": 0,
            "active_retries": 0
        }

    async def start(self):
        """Start DLQ producers"""
        if not AIOKafkaProducer:
            logger.warning("aiokafka not available - DLQ will use PostgreSQL only")
            return

        try:
            # DLQ producer for permanent failures
            self.dlq_producer = AIOKafkaProducer(
                bootstrap_servers=self.kafka_bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                compression_type='gzip'
            )
            await self.dlq_producer.start()

            # Retry producer for temporary failures
            self.retry_producer = AIOKafkaProducer(
                bootstrap_servers=self.kafka_bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                compression_type='gzip'
            )
            await self.retry_producer.start()

            logger.info("Dead Letter Queue started successfully")

        except Exception as e:
            logger.error(f"Failed to start DLQ: {e}")

    async def stop(self):
        """Stop DLQ producers"""
        try:
            if self.dlq_producer:
                await self.dlq_producer.stop()
            if self.retry_producer:
                await self.retry_producer.stop()
            logger.info("Dead Letter Queue stopped")
        except Exception as e:
            logger.error(f"Error stopping DLQ: {e}")

    async def handle_failed_message(
        self,
        original_message: Dict[str, Any],
        failure_reason: FailureReason,
        error_details: str,
        source_topic: str,
        retry_count: int = 0
    ):
        """Handle a failed message with retry logic"""
        self.stats["total_failures"] += 1

        failed_message = {
            "message_id": str(uuid.uuid4()),
            "original_message": original_message,
            "source_topic": source_topic,
            "failure_reason": failure_reason.value,
            "error_details": error_details,
            "retry_count": retry_count,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "pending_retry" if retry_count < self.max_retries else "permanent_failure"
        }

        # Determine if message should be retried or sent to DLQ
        if retry_count < self.max_retries and self._is_retriable(failure_reason):
            await self._queue_for_retry(failed_message)
        else:
            await self._send_to_dlq(failed_message)

    def _is_retriable(self, failure_reason: FailureReason) -> bool:
        """Determine if failure is retriable"""
        retriable_reasons = [
            FailureReason.NETWORK_ERROR,
            FailureReason.TIMEOUT,
            FailureReason.RATE_LIMIT,
            FailureReason.API_ERROR
        ]
        return failure_reason in retriable_reasons

    async def _queue_for_retry(self, failed_message: Dict[str, Any]):
        """Queue message for retry with exponential backoff"""
        retry_count = failed_message["retry_count"]

        # Calculate exponential backoff delay
        delay = self.retry_delay_seconds * (2 ** retry_count)  # Exponential backoff
        retry_at = datetime.now(timezone.utc) + timedelta(seconds=delay)

        failed_message["retry_at"] = retry_at.isoformat()
        failed_message["status"] = "queued_for_retry"

        logger.info(
            f"Queueing message for retry {retry_count + 1}/{self.max_retries} "
            f"in {delay} seconds: {failed_message['message_id']}"
        )

        # Send to retry topic
        if self.retry_producer:
            try:
                await self.retry_producer.send(
                    topic=self.retry_topic,
                    value=failed_message,
                    key=failed_message["message_id"]
                )
                self.stats["active_retries"] += 1
            except Exception as e:
                logger.error(f"Failed to send to retry queue: {e}")
                # Fallback to DLQ
                await self._send_to_dlq(failed_message)

        # Store in PostgreSQL for tracking
        await self._store_failed_message(failed_message)

    async def _send_to_dlq(self, failed_message: Dict[str, Any]):
        """Send message to permanent dead letter queue"""
        failed_message["status"] = "permanent_failure"
        failed_message["dlq_timestamp"] = datetime.now(timezone.utc).isoformat()

        logger.warning(
            f"Sending message to DLQ after {failed_message['retry_count']} retries: "
            f"{failed_message['message_id']} - Reason: {failed_message['failure_reason']}"
        )

        # Send to DLQ topic
        if self.dlq_producer:
            try:
                await self.dlq_producer.send(
                    topic=self.dlq_topic,
                    value=failed_message,
                    key=failed_message["message_id"]
                )
            except Exception as e:
                logger.error(f"Failed to send to DLQ topic: {e}")

        # Store in PostgreSQL for analysis
        await self._store_failed_message(failed_message)
        self.stats["permanent_failures"] += 1

    async def _store_failed_message(self, failed_message: Dict[str, Any]):
        """Store failed message in PostgreSQL for tracking and analysis"""
        if not self.postgres_connection:
            return

        try:
            # Store in failed_messages table
            insert_query = """
                INSERT INTO failed_messages (
                    message_id,
                    source_topic,
                    failure_reason,
                    error_details,
                    retry_count,
                    status,
                    original_message,
                    retry_at,
                    created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                ON CONFLICT (message_id) DO UPDATE SET
                    retry_count = EXCLUDED.retry_count,
                    status = EXCLUDED.status,
                    error_details = EXCLUDED.error_details,
                    retry_at = EXCLUDED.retry_at
            """

            await self.postgres_connection.execute(
                insert_query,
                failed_message["message_id"],
                failed_message["source_topic"],
                failed_message["failure_reason"],
                failed_message["error_details"],
                failed_message["retry_count"],
                failed_message["status"],
                json.dumps(failed_message["original_message"]),
                failed_message.get("retry_at"),
                failed_message["timestamp"]
            )

            logger.debug(f"Stored failed message in PostgreSQL: {failed_message['message_id']}")

        except Exception as e:
            logger.error(f"Failed to store message in PostgreSQL: {e}")

    async def retry_failed_messages(self):
        """Background task to retry failed messages"""
        logger.info("Starting DLQ retry worker")

        while True:
            try:
                # Check PostgreSQL for messages ready to retry
                if self.postgres_connection:
                    retry_messages = await self._get_messages_ready_for_retry()

                    for message in retry_messages:
                        await self._attempt_retry(message)

                # Wait before next check
                await asyncio.sleep(30)  # Check every 30 seconds

            except asyncio.CancelledError:
                logger.info("DLQ retry worker cancelled")
                break
            except Exception as e:
                logger.error(f"Error in retry worker: {e}")
                await asyncio.sleep(60)

    async def _get_messages_ready_for_retry(self) -> List[Dict[str, Any]]:
        """Get messages from PostgreSQL that are ready for retry"""
        try:
            query = """
                SELECT
                    message_id,
                    source_topic,
                    original_message,
                    failure_reason,
                    error_details,
                    retry_count
                FROM failed_messages
                WHERE status = 'queued_for_retry'
                  AND retry_at <= NOW()
                  AND retry_count < $1
                ORDER BY retry_at
                LIMIT 100
            """

            rows = await self.postgres_connection.fetch(query, self.max_retries)

            return [
                {
                    "message_id": row["message_id"],
                    "source_topic": row["source_topic"],
                    "original_message": json.loads(row["original_message"]),
                    "failure_reason": row["failure_reason"],
                    "error_details": row["error_details"],
                    "retry_count": row["retry_count"]
                }
                for row in rows
            ]

        except Exception as e:
            logger.error(f"Failed to fetch retry messages: {e}")
            return []

    async def _attempt_retry(self, message: Dict[str, Any]):
        """Attempt to retry a failed message"""
        self.stats["active_retries"] -= 1

        try:
            # Import here to avoid circular dependency
            from ..streaming.kafka_producer import KafkaDataProducer

            # Attempt to re-send message
            producer = KafkaDataProducer(self.kafka_bootstrap_servers)
            await producer.start()

            success = await producer.send_real_time_data(
                record=message["original_message"],
                source_type=message.get("source_type", "unknown"),
                source_id=message.get("source_id", "unknown")
            )

            await producer.stop()

            if success:
                # Mark as successfully retried
                await self._mark_retry_success(message["message_id"])
                self.stats["retry_successes"] += 1
                logger.info(f"Successfully retried message: {message['message_id']}")
            else:
                # Retry failed, queue for next retry or DLQ
                await self.handle_failed_message(
                    original_message=message["original_message"],
                    failure_reason=FailureReason.UNKNOWN,
                    error_details="Retry attempt failed",
                    source_topic=message["source_topic"],
                    retry_count=message["retry_count"] + 1
                )

        except Exception as e:
            logger.error(f"Error retrying message {message['message_id']}: {e}")
            await self.handle_failed_message(
                original_message=message["original_message"],
                failure_reason=FailureReason.UNKNOWN,
                error_details=str(e),
                source_topic=message["source_topic"],
                retry_count=message["retry_count"] + 1
            )

    async def _mark_retry_success(self, message_id: str):
        """Mark message as successfully retried in PostgreSQL"""
        if not self.postgres_connection:
            return

        try:
            update_query = """
                UPDATE failed_messages
                SET status = 'retry_success',
                    retry_success_at = NOW()
                WHERE message_id = $1
            """
            await self.postgres_connection.execute(update_query, message_id)
        except Exception as e:
            logger.error(f"Failed to mark retry success: {e}")

    async def get_dlq_statistics(self) -> Dict[str, Any]:
        """Get DLQ statistics"""
        stats = self.stats.copy()

        if self.postgres_connection:
            try:
                # Get detailed stats from PostgreSQL
                query = """
                    SELECT
                        status,
                        failure_reason,
                        COUNT(*) as count
                    FROM failed_messages
                    WHERE created_at > NOW() - INTERVAL '24 hours'
                    GROUP BY status, failure_reason
                    ORDER BY count DESC
                """

                rows = await self.postgres_connection.fetch(query)
                stats["last_24h_breakdown"] = [
                    {
                        "status": row["status"],
                        "failure_reason": row["failure_reason"],
                        "count": row["count"]
                    }
                    for row in rows
                ]

            except Exception as e:
                logger.error(f"Failed to fetch DLQ statistics: {e}")

        return stats

    async def replay_dlq_messages(
        self,
        failure_reason: Optional[FailureReason] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """Manually replay messages from DLQ (for fixing and reprocessing)"""
        result = {
            "attempted": 0,
            "successful": 0,
            "failed": 0
        }

        if not self.postgres_connection:
            return result

        try:
            # Get messages from DLQ
            query = """
                SELECT
                    message_id,
                    source_topic,
                    original_message,
                    failure_reason
                FROM failed_messages
                WHERE status = 'permanent_failure'
            """

            if failure_reason:
                query += f" AND failure_reason = '{failure_reason.value}'"

            query += f" LIMIT {limit}"

            rows = await self.postgres_connection.fetch(query)

            for row in rows:
                result["attempted"] += 1

                # Attempt to replay message
                try:
                    from ..streaming.kafka_producer import KafkaDataProducer

                    producer = KafkaDataProducer(self.kafka_bootstrap_servers)
                    await producer.start()

                    success = await producer.send_real_time_data(
                        record=json.loads(row["original_message"]),
                        source_type="unknown",
                        source_id="dlq_replay"
                    )

                    await producer.stop()

                    if success:
                        result["successful"] += 1
                        # Mark as replayed
                        await self.postgres_connection.execute(
                            "UPDATE failed_messages SET status = 'replayed' WHERE message_id = $1",
                            row["message_id"]
                        )
                    else:
                        result["failed"] += 1

                except Exception as e:
                    logger.error(f"Failed to replay message {row['message_id']}: {e}")
                    result["failed"] += 1

        except Exception as e:
            logger.error(f"Error replaying DLQ messages: {e}")

        return result
