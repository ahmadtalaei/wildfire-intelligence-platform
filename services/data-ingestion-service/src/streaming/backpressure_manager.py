"""
Backpressure Management for High-Volume Streaming

Handles traffic spikes during fire season by implementing:
- Adaptive rate limiting
- Queue depth monitoring
- Dynamic throttling
- Circuit breaker pattern
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from collections import deque
from enum import Enum
import statistics

logger = logging.getLogger(__name__)


class BackpressureState(Enum):
    """Backpressure states"""
    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"
    SHEDDING = "load_shedding"


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


class BackpressureManager:
    """Manages backpressure during high ingestion periods"""

    def __init__(
        self,
        max_queue_depth: int = 10000,
        warning_threshold: float = 0.7,  # 70% of max
        critical_threshold: float = 0.9,  # 90% of max
        target_latency_ms: float = 1000,  # 1 second target
        window_size_seconds: int = 60
    ):
        self.max_queue_depth = max_queue_depth
        self.warning_threshold = int(max_queue_depth * warning_threshold)
        self.critical_threshold = int(max_queue_depth * critical_threshold)
        self.target_latency_ms = target_latency_ms
        self.window_size_seconds = window_size_seconds

        # Current state
        self.state = BackpressureState.NORMAL
        self.circuit_state = CircuitState.CLOSED

        # Metrics tracking
        self.queue_depth = 0
        self.processing_times = deque(maxlen=1000)  # Last 1000 processing times
        self.rejection_count = 0
        self.total_processed = 0

        # Sliding window for rate calculation
        self.request_timestamps = deque(maxlen=10000)

        # Throttling
        self.throttle_percentage = 0  # 0-100, percentage of requests to reject
        self.last_throttle_update = datetime.now(timezone.utc)

        # Circuit breaker
        self.failure_count = 0
        self.failure_threshold = 10
        self.circuit_opened_at = None
        self.circuit_timeout_seconds = 60

    async def check_capacity(self, source_id: str) -> Dict[str, Any]:
        """Check if system can accept new messages"""
        now = datetime.now(timezone.utc)

        # Update metrics
        self._update_state()

        # Circuit breaker check
        if self.circuit_state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.circuit_state = CircuitState.HALF_OPEN
                logger.info(f"Circuit breaker entering HALF_OPEN state for {source_id}")
            else:
                return {
                    "allowed": False,
                    "reason": "circuit_breaker_open",
                    "state": self.state.value,
                    "retry_after_seconds": self._get_retry_after()
                }

        # Check queue depth
        if self.queue_depth >= self.max_queue_depth:
            self.rejection_count += 1
            return {
                "allowed": False,
                "reason": "queue_full",
                "queue_depth": self.queue_depth,
                "max_depth": self.max_queue_depth,
                "state": self.state.value
            }

        # Adaptive throttling based on state
        if self._should_throttle():
            self.rejection_count += 1
            return {
                "allowed": False,
                "reason": "throttled",
                "throttle_percentage": self.throttle_percentage,
                "state": self.state.value,
                "retry_after_seconds": self._calculate_retry_delay()
            }

        # Allow request
        self.queue_depth += 1
        self.request_timestamps.append(now)

        return {
            "allowed": True,
            "state": self.state.value,
            "queue_depth": self.queue_depth,
            "estimated_latency_ms": self._estimate_latency()
        }

    async def release_capacity(self, processing_time_ms: float, success: bool = True):
        """Release capacity after processing message"""
        self.queue_depth = max(0, self.queue_depth - 1)
        self.total_processed += 1

        if success:
            self.processing_times.append(processing_time_ms)
            self.failure_count = max(0, self.failure_count - 1)

            # If in HALF_OPEN and success, close circuit
            if self.circuit_state == CircuitState.HALF_OPEN:
                self.circuit_state = CircuitState.CLOSED
                logger.info("Circuit breaker CLOSED - system recovered")

        else:
            self.failure_count += 1

            # Trip circuit breaker if too many failures
            if self.failure_count >= self.failure_threshold:
                self._trip_circuit_breaker()

    def _update_state(self):
        """Update backpressure state based on metrics"""
        old_state = self.state

        if self.queue_depth >= self.critical_threshold:
            self.state = BackpressureState.CRITICAL
            self.throttle_percentage = 90  # Reject 90% of requests
        elif self.queue_depth >= self.warning_threshold:
            self.state = BackpressureState.WARNING
            self.throttle_percentage = 50  # Reject 50% of requests
        else:
            self.state = BackpressureState.NORMAL
            self.throttle_percentage = 0

        # Adjust based on latency
        if self.processing_times:
            avg_latency = statistics.mean(self.processing_times)
            if avg_latency > self.target_latency_ms * 2:
                # Latency is very high, increase throttling
                self.throttle_percentage = min(100, self.throttle_percentage + 20)
                if self.state == BackpressureState.NORMAL:
                    self.state = BackpressureState.WARNING

        if old_state != self.state:
            logger.warning(
                f"Backpressure state changed: {old_state.value} → {self.state.value} "
                f"(queue: {self.queue_depth}/{self.max_queue_depth}, "
                f"throttle: {self.throttle_percentage}%)"
            )

    def _should_throttle(self) -> bool:
        """Determine if request should be throttled"""
        if self.throttle_percentage == 0:
            return False

        # Use deterministic throttling based on percentage
        import random
        return random.randint(1, 100) <= self.throttle_percentage

    def _trip_circuit_breaker(self):
        """Trip circuit breaker due to excessive failures"""
        self.circuit_state = CircuitState.OPEN
        self.circuit_opened_at = datetime.now(timezone.utc)
        logger.error(
            f"Circuit breaker OPENED due to {self.failure_count} failures. "
            f"Will retry in {self.circuit_timeout_seconds} seconds"
        )

    def _should_attempt_reset(self) -> bool:
        """Check if circuit breaker should attempt reset"""
        if self.circuit_state != CircuitState.OPEN:
            return False

        if not self.circuit_opened_at:
            return True

        elapsed = (datetime.now(timezone.utc) - self.circuit_opened_at).total_seconds()
        return elapsed >= self.circuit_timeout_seconds

    def _get_retry_after(self) -> int:
        """Get retry-after delay in seconds"""
        if self.circuit_opened_at:
            elapsed = (datetime.now(timezone.utc) - self.circuit_opened_at).total_seconds()
            remaining = max(0, self.circuit_timeout_seconds - elapsed)
            return int(remaining)
        return self.circuit_timeout_seconds

    def _calculate_retry_delay(self) -> int:
        """Calculate retry delay based on current state"""
        if self.state == BackpressureState.CRITICAL:
            return 60  # 1 minute for critical
        elif self.state == BackpressureState.WARNING:
            return 30  # 30 seconds for warning
        return 10  # 10 seconds for normal throttling

    def _estimate_latency(self) -> float:
        """Estimate current processing latency"""
        if not self.processing_times:
            return self.target_latency_ms

        # Use P95 latency for estimation
        sorted_times = sorted(self.processing_times)
        p95_index = int(len(sorted_times) * 0.95)
        return sorted_times[p95_index] if p95_index < len(sorted_times) else sorted_times[-1]

    async def get_current_rate(self) -> float:
        """Calculate current ingestion rate (requests/second)"""
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(seconds=self.window_size_seconds)

        # Count requests in window
        recent_requests = [
            ts for ts in self.request_timestamps
            if ts >= window_start
        ]

        if not recent_requests:
            return 0.0

        return len(recent_requests) / self.window_size_seconds

    async def get_metrics(self) -> Dict[str, Any]:
        """Get backpressure metrics"""
        current_rate = await self.get_current_rate()

        metrics = {
            "state": self.state.value,
            "circuit_state": self.circuit_state.value,
            "queue_depth": self.queue_depth,
            "max_queue_depth": self.max_queue_depth,
            "utilization_percent": (self.queue_depth / self.max_queue_depth * 100) if self.max_queue_depth > 0 else 0,
            "throttle_percentage": self.throttle_percentage,
            "rejection_count": self.rejection_count,
            "total_processed": self.total_processed,
            "current_rate_per_sec": round(current_rate, 2),
            "failure_count": self.failure_count
        }

        if self.processing_times:
            metrics["avg_latency_ms"] = round(statistics.mean(self.processing_times), 2)
            metrics["p95_latency_ms"] = round(self._estimate_latency(), 2)
            metrics["p99_latency_ms"] = round(sorted(self.processing_times)[int(len(self.processing_times) * 0.99)], 2)

        if self.circuit_opened_at:
            metrics["circuit_opened_at"] = self.circuit_opened_at.isoformat()
            metrics["retry_after_seconds"] = self._get_retry_after()

        return metrics

    async def adjust_for_peak_season(self, is_fire_season: bool):
        """Adjust thresholds for fire season peaks"""
        if is_fire_season:
            # During fire season, be more lenient to accept more data
            self.max_queue_depth = 20000  # Double capacity
            self.warning_threshold = int(self.max_queue_depth * 0.8)
            self.critical_threshold = int(self.max_queue_depth * 0.95)
            logger.info("Backpressure adjusted for FIRE SEASON - increased capacity")
        else:
            # Normal season, conservative thresholds
            self.max_queue_depth = 10000
            self.warning_threshold = int(self.max_queue_depth * 0.7)
            self.critical_threshold = int(self.max_queue_depth * 0.9)
            logger.info("Backpressure adjusted for NORMAL SEASON - standard capacity")


class EventTimeWatermarkManager:
    """
    Manages event-time watermarks for late-arriving data.

    Watermarks ensure that late-arriving fire/weather data is processed correctly
    even if it arrives out-of-order or delayed.
    """

    def __init__(self, max_out_of_orderness_seconds: int = 300):
        """
        Initialize watermark manager.

        Args:
            max_out_of_orderness_seconds: Maximum expected delay for late data (default 5 minutes)
        """
        self.max_out_of_orderness = timedelta(seconds=max_out_of_orderness_seconds)
        self.watermarks: Dict[str, datetime] = {}  # Per-source watermarks
        self.late_events: Dict[str, int] = {}  # Count of late events per source

    async def update_watermark(self, source_id: str, event_time: datetime) -> datetime:
        """
        Update watermark based on event time.

        Returns the current watermark for the source.
        """
        current_watermark = self.watermarks.get(source_id, datetime.min.replace(tzinfo=timezone.utc))

        # Calculate new watermark: max observed event time - max out-of-orderness
        new_watermark = event_time - self.max_out_of_orderness

        # Watermarks can only advance, never go backward
        if new_watermark > current_watermark:
            self.watermarks[source_id] = new_watermark
            logger.debug(f"Watermark advanced for {source_id}: {new_watermark.isoformat()}")

        return self.watermarks[source_id]

    async def is_late(self, source_id: str, event_time: datetime) -> bool:
        """
        Check if event is late (arrived after watermark passed).

        Returns True if event is late and should be handled specially.
        """
        watermark = self.watermarks.get(source_id, datetime.min.replace(tzinfo=timezone.utc))

        if event_time < watermark:
            # Event is late - arrived after watermark passed
            self.late_events[source_id] = self.late_events.get(source_id, 0) + 1
            logger.warning(
                f"Late event detected for {source_id}: "
                f"event_time={event_time.isoformat()}, watermark={watermark.isoformat()}, "
                f"delay={int((watermark - event_time).total_seconds())} seconds"
            )
            return True

        return False

    async def handle_late_event(self, source_id: str, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle late-arriving event with special processing.

        Options:
        1. Re-trigger aggregations that this event should have been part of
        2. Send to late-events topic for special handling
        3. Append to existing time windows if still open
        """
        event_time = event_data.get('timestamp')
        watermark = self.watermarks.get(source_id, datetime.min.replace(tzinfo=timezone.utc))

        result = {
            "is_late": True,
            "event_time": event_time.isoformat() if isinstance(event_time, datetime) else event_time,
            "watermark": watermark.isoformat(),
            "delay_seconds": int((watermark - event_time).total_seconds()) if isinstance(event_time, datetime) else 0,
            "action": "re_aggregate"  # Default action
        }

        # Determine action based on how late the event is
        if isinstance(event_time, datetime):
            delay = watermark - event_time

            if delay > timedelta(hours=24):
                # Very late event - probably historical data, send to special topic
                result["action"] = "send_to_historical_topic"
            elif delay > timedelta(hours=1):
                # Moderately late - trigger re-aggregation
                result["action"] = "re_aggregate_window"
            else:
                # Slightly late - try to append to existing window
                result["action"] = "append_to_window"

        return result

    async def get_watermark_metrics(self) -> Dict[str, Any]:
        """Get watermark metrics for monitoring"""
        return {
            "sources": {
                source_id: {
                    "watermark": watermark.isoformat(),
                    "late_event_count": self.late_events.get(source_id, 0)
                }
                for source_id, watermark in self.watermarks.items()
            },
            "total_late_events": sum(self.late_events.values())
        }
