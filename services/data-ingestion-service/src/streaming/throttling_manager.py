"""
ThrottlingManager: Advanced throttling with consumer lag monitoring
Implements exponential backoff, sliding window metrics, and dynamic rate adjustment
"""

import asyncio
from typing import Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from collections import deque
import statistics
import structlog

logger = structlog.get_logger()


class ThrottlingManager:
    """
    Monitors Kafka consumer lag and dynamically adjusts send rates
    Uses exponential backoff and sliding window metrics
    """

    def __init__(
        self,
        min_send_rate: float = 1.0,  # messages/second
        max_send_rate: float = 1000.0,
        target_consumer_lag: int = 1000,  # target max lag
        critical_consumer_lag: int = 5000,
        adjustment_factor: float = 1.5,  # exponential factor
        window_size_seconds: int = 60,
        metric_sample_size: int = 100
    ):
        self.min_send_rate = min_send_rate
        self.max_send_rate = max_send_rate
        self.current_send_rate = max_send_rate  # Start optimistic
        self.target_consumer_lag = target_consumer_lag
        self.critical_consumer_lag = critical_consumer_lag
        self.adjustment_factor = adjustment_factor
        self.window_size_seconds = window_size_seconds

        # Sliding window metrics
        self.lag_samples = deque(maxlen=metric_sample_size)
        self.send_timestamps = deque(maxlen=10000)

        # State tracking
        self.consecutive_high_lag = 0
        self.consecutive_low_lag = 0
        self.last_adjustment_time = datetime.now(timezone.utc)
        self.total_throttles = 0
        self.total_rate_increases = 0
        self.total_rate_decreases = 0

        # Backoff state
        self.is_backing_off = False
        self.backoff_level = 0
        self.max_backoff_level = 5

    async def check_and_throttle(
        self,
        consumer_lag: int,
        source_id: str
    ) -> Dict[str, Any]:
        """
        Check if we should throttle based on consumer lag

        Returns:
            Dict with throttle decision and timing
        """
        now = datetime.now(timezone.utc)

        # Record lag sample
        self.lag_samples.append({
            'lag': consumer_lag,
            'timestamp': now
        })

        # Calculate average lag over window
        avg_lag = self._calculate_average_lag()

        # Determine action
        action = 'allow'
        delay_seconds = 0
        should_adjust_rate = False

        if avg_lag >= self.critical_consumer_lag:
            # Critical lag - aggressive backoff
            action = 'throttle_critical'
            self.consecutive_high_lag += 1
            self.consecutive_low_lag = 0
            should_adjust_rate = True

            # Exponential backoff
            if not self.is_backing_off:
                self.is_backing_off = True
                self.backoff_level = 1
            else:
                self.backoff_level = min(self.backoff_level + 1, self.max_backoff_level)

            delay_seconds = self._calculate_backoff_delay()
            self.total_throttles += 1

            logger.warning(
                "CRITICAL consumer lag - aggressive throttle",
                source_id=source_id,
                avg_lag=avg_lag,
                current_lag=consumer_lag,
                backoff_level=self.backoff_level,
                delay_seconds=delay_seconds
            )

        elif avg_lag >= self.target_consumer_lag:
            # High lag - moderate throttle
            action = 'throttle_moderate'
            self.consecutive_high_lag += 1
            self.consecutive_low_lag = 0
            should_adjust_rate = True

            delay_seconds = 1.0  # Fixed moderate delay
            self.total_throttles += 1

            logger.info(
                "High consumer lag - moderate throttle",
                source_id=source_id,
                avg_lag=avg_lag,
                current_lag=consumer_lag,
                delay_seconds=delay_seconds
            )

        else:
            # Lag is acceptable
            self.consecutive_low_lag += 1
            self.consecutive_high_lag = 0

            # Reset backoff if sustained low lag
            if self.consecutive_low_lag >= 10 and self.is_backing_off:
                self.is_backing_off = False
                self.backoff_level = 0
                should_adjust_rate = True
                logger.info(
                    "Consumer lag recovered - resetting backoff",
                    source_id=source_id,
                    avg_lag=avg_lag
                )

        # Adjust send rate if needed
        if should_adjust_rate:
            await self._adjust_send_rate(avg_lag)

        # Record send time if allowed
        if action == 'allow':
            self.send_timestamps.append(now)

        return {
            'action': action,
            'delay_seconds': delay_seconds,
            'current_send_rate': self.current_send_rate,
            'consumer_lag': consumer_lag,
            'avg_consumer_lag': avg_lag,
            'backoff_level': self.backoff_level,
            'is_backing_off': self.is_backing_off
        }

    def _calculate_average_lag(self) -> float:
        """Calculate average lag over sliding window"""
        if not self.lag_samples:
            return 0.0

        now = datetime.now(timezone.utc)
        window_start = now - timedelta(seconds=self.window_size_seconds)

        # Filter to window
        recent_lags = [
            sample['lag'] for sample in self.lag_samples
            if sample['timestamp'] >= window_start
        ]

        if not recent_lags:
            return 0.0

        return statistics.mean(recent_lags)

    def _calculate_backoff_delay(self) -> float:
        """Calculate exponential backoff delay"""
        base_delay = 1.0  # 1 second base
        return base_delay * (self.adjustment_factor ** self.backoff_level)

    async def _adjust_send_rate(self, avg_lag: float):
        """Dynamically adjust send rate based on lag"""
        old_rate = self.current_send_rate

        if avg_lag >= self.critical_consumer_lag:
            # Aggressive decrease
            self.current_send_rate = max(
                self.min_send_rate,
                self.current_send_rate / (self.adjustment_factor ** 2)
            )
            self.total_rate_decreases += 1

            logger.warning(
                "Send rate decreased (critical lag)",
                old_rate=round(old_rate, 2),
                new_rate=round(self.current_send_rate, 2),
                avg_lag=avg_lag
            )

        elif avg_lag >= self.target_consumer_lag:
            # Moderate decrease
            self.current_send_rate = max(
                self.min_send_rate,
                self.current_send_rate / self.adjustment_factor
            )
            self.total_rate_decreases += 1

            logger.info(
                "Send rate decreased (high lag)",
                old_rate=round(old_rate, 2),
                new_rate=round(self.current_send_rate, 2),
                avg_lag=avg_lag
            )

        elif avg_lag < self.target_consumer_lag / 2 and self.consecutive_low_lag >= 10:
            # Gradual increase when lag is sustainably low
            self.current_send_rate = min(
                self.max_send_rate,
                self.current_send_rate * 1.2  # 20% increase
            )
            self.total_rate_increases += 1

            logger.info(
                "Send rate increased (low lag)",
                old_rate=round(old_rate, 2),
                new_rate=round(self.current_send_rate, 2),
                avg_lag=avg_lag
            )

        self.last_adjustment_time = datetime.now(timezone.utc)

    async def get_current_rate(self) -> float:
        """Get current actual send rate (messages/second)"""
        if not self.send_timestamps:
            return 0.0

        now = datetime.now(timezone.utc)
        window_start = now - timedelta(seconds=self.window_size_seconds)

        recent_sends = [
            ts for ts in self.send_timestamps
            if ts >= window_start
        ]

        if not recent_sends:
            return 0.0

        return len(recent_sends) / self.window_size_seconds

    async def get_metrics(self) -> Dict[str, Any]:
        """Get throttling metrics"""
        current_actual_rate = await self.get_current_rate()
        avg_lag = self._calculate_average_lag()

        metrics = {
            'target_send_rate': round(self.current_send_rate, 2),
            'actual_send_rate': round(current_actual_rate, 2),
            'rate_utilization_percent': round(
                (current_actual_rate / self.current_send_rate * 100)
                if self.current_send_rate > 0 else 0,
                2
            ),
            'avg_consumer_lag': round(avg_lag, 2),
            'target_consumer_lag': self.target_consumer_lag,
            'critical_consumer_lag': self.critical_consumer_lag,
            'is_backing_off': self.is_backing_off,
            'backoff_level': self.backoff_level,
            'consecutive_high_lag': self.consecutive_high_lag,
            'consecutive_low_lag': self.consecutive_low_lag,
            'total_throttles': self.total_throttles,
            'total_rate_increases': self.total_rate_increases,
            'total_rate_decreases': self.total_rate_decreases,
            'last_adjustment_time': self.last_adjustment_time.isoformat()
        }

        # Add lag percentiles if we have samples
        if len(self.lag_samples) >= 10:
            lags = [s['lag'] for s in self.lag_samples]
            sorted_lags = sorted(lags)
            metrics['lag_p50'] = sorted_lags[len(sorted_lags) // 2]
            metrics['lag_p95'] = sorted_lags[int(len(sorted_lags) * 0.95)]
            metrics['lag_p99'] = sorted_lags[int(len(sorted_lags) * 0.99)]

        return metrics

    async def reset(self):
        """Reset throttling state"""
        self.current_send_rate = self.max_send_rate
        self.is_backing_off = False
        self.backoff_level = 0
        self.consecutive_high_lag = 0
        self.consecutive_low_lag = 0

        logger.info("Throttling manager reset", send_rate=self.current_send_rate)
