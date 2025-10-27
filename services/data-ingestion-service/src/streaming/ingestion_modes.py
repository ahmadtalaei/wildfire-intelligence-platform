"""
Ingestion Mode Strategies: Plug-and-play ingestion modes using Strategy Pattern
Supports batch, real-time polling, and continuous streaming
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timezone
import structlog

logger = structlog.get_logger()


class IngestionMode(ABC):
    """Base class for ingestion mode strategies"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.is_running = False
        self.records_processed = 0
        self.errors = 0

    @abstractmethod
    async def start(
        self,
        data_fetcher: Callable,
        data_processor: Callable,
        **kwargs
    ) -> str:
        """
        Start ingestion in this mode

        Args:
            data_fetcher: Async function to fetch data
            data_processor: Async function to process fetched data
            **kwargs: Additional mode-specific arguments
        """
        pass

    @abstractmethod
    async def stop(self):
        """Stop ingestion"""
        pass

    @abstractmethod
    async def get_metrics(self) -> Dict[str, Any]:
        """Get mode-specific metrics"""
        pass


class BatchMode(IngestionMode):
    """
    Batch ingestion mode - fetch large datasets at scheduled intervals
    Best for: Historical data, daily summaries, bulk imports
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.batch_size = config.get('batch_size', 1000)
        self.schedule_interval = config.get('schedule_interval_seconds', 3600)  # 1 hour default
        self.last_batch_time = None

    async def start(
        self,
        data_fetcher: Callable,
        data_processor: Callable,
        **kwargs
    ) -> str:
        """Start batch processing loop"""
        self.is_running = True
        mode_id = kwargs.get('mode_id', 'batch_' + datetime.now().strftime('%Y%m%d_%H%M%S'))

        logger.info(
            "Batch mode starting",
            mode_id=mode_id,
            batch_size=self.batch_size,
            schedule_interval=self.schedule_interval
        )

        # Store the task to prevent garbage collection
        self._task = asyncio.create_task(self._batch_loop(data_fetcher, data_processor, mode_id))

        return mode_id

    async def _batch_loop(
        self,
        data_fetcher: Callable,
        data_processor: Callable,
        mode_id: str
    ):
        """Continuous batch processing loop"""
        while self.is_running:
            try:
                start_time = datetime.now(timezone.utc)

                # Fetch batch
                data = await data_fetcher(batch_size=self.batch_size)

                if data:
                    # Process batch
                    result = await data_processor(data)

                    self.records_processed += len(data)
                    self.last_batch_time = datetime.now(timezone.utc)

                    batch_duration = (datetime.now(timezone.utc) - start_time).total_seconds()

                    logger.info(
                        "Batch processed",
                        mode_id=mode_id,
                        records=len(data),
                        duration_seconds=round(batch_duration, 2),
                        success=result.get('success', False)
                    )
                else:
                    logger.debug("No data available in batch", mode_id=mode_id)

            except Exception as e:
                self.errors += 1
                logger.error(
                    "Batch processing error",
                    mode_id=mode_id,
                    error=str(e),
                    exc_info=True
                )

            # Wait for next batch interval
            await asyncio.sleep(self.schedule_interval)

    async def stop(self):
        """Stop batch mode"""
        self.is_running = False
        logger.info("Batch mode stopped", records_processed=self.records_processed)

    async def get_metrics(self) -> Dict[str, Any]:
        return {
            'mode': 'batch',
            'is_running': self.is_running,
            'records_processed': self.records_processed,
            'errors': self.errors,
            'batch_size': self.batch_size,
            'schedule_interval_seconds': self.schedule_interval,
            'last_batch_time': self.last_batch_time.isoformat() if self.last_batch_time else None
        }


class RealTimeMode(IngestionMode):
    """
    Real-time polling mode - fetch data at frequent intervals
    Best for: API polling, periodic checks, near-real-time updates
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.polling_interval = config.get('polling_interval_seconds', 30)
        self.max_records_per_poll = config.get('max_records_per_poll', 500)
        self.last_poll_time = None
        self.empty_polls = 0

    async def start(
        self,
        data_fetcher: Callable,
        data_processor: Callable,
        **kwargs
    ) -> str:
        """Start real-time polling loop"""
        self.is_running = True
        mode_id = kwargs.get('mode_id', 'realtime_' + datetime.now().strftime('%Y%m%d_%H%M%S'))

        logger.info(
            "Real-time mode starting",
            mode_id=mode_id,
            polling_interval=self.polling_interval
        )

        # Store the task to prevent garbage collection
        self._task = asyncio.create_task(self._polling_loop(data_fetcher, data_processor, mode_id))

        return mode_id

    async def _polling_loop(
        self,
        data_fetcher: Callable,
        data_processor: Callable,
        mode_id: str
    ):
        """Continuous polling loop"""
        while self.is_running:
            try:
                poll_start = datetime.now(timezone.utc)

                # Fetch data
                data = await data_fetcher(max_records=self.max_records_per_poll)

                if data:
                    # Process data
                    result = await data_processor(data)

                    self.records_processed += len(data)
                    self.last_poll_time = datetime.now(timezone.utc)
                    self.empty_polls = 0

                    poll_duration = (datetime.now(timezone.utc) - poll_start).total_seconds()

                    logger.info(
                        "Real-time poll completed",
                        mode_id=mode_id,
                        records=len(data),
                        duration_seconds=round(poll_duration, 2)
                    )
                else:
                    self.empty_polls += 1
                    if self.empty_polls % 10 == 0:
                        logger.debug(
                            "No new data available",
                            mode_id=mode_id,
                            empty_polls=self.empty_polls
                        )

            except Exception as e:
                self.errors += 1
                logger.error(
                    "Real-time polling error",
                    mode_id=mode_id,
                    error=str(e),
                    exc_info=True
                )

            # Wait for next poll
            await asyncio.sleep(self.polling_interval)

    async def stop(self):
        """Stop real-time mode"""
        self.is_running = False
        logger.info("Real-time mode stopped", records_processed=self.records_processed)

    async def get_metrics(self) -> Dict[str, Any]:
        return {
            'mode': 'real_time',
            'is_running': self.is_running,
            'records_processed': self.records_processed,
            'errors': self.errors,
            'polling_interval_seconds': self.polling_interval,
            'last_poll_time': self.last_poll_time.isoformat() if self.last_poll_time else None,
            'empty_polls': self.empty_polls
        }


class ContinuousStreamingMode(IngestionMode):
    """
    Continuous streaming mode - process data as soon as it arrives
    Best for: MQTT, WebSocket, Kafka consumers, high-frequency sensors
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.buffer_size = config.get('buffer_size', 100)
        self.buffer_flush_interval = config.get('buffer_flush_interval_seconds', 5)
        self.last_record_time = None
        self._buffer = []
        self._last_flush = datetime.now(timezone.utc)

    async def start(
        self,
        data_fetcher: Callable,
        data_processor: Callable,
        **kwargs
    ) -> str:
        """Start continuous streaming"""
        self.is_running = True
        mode_id = kwargs.get('mode_id', 'streaming_' + datetime.now().strftime('%Y%m%d_%H%M%S'))

        logger.info(
            "Continuous streaming mode starting",
            mode_id=mode_id,
            buffer_size=self.buffer_size
        )

        # Store tasks to prevent garbage collection
        self._streaming_task = asyncio.create_task(self._streaming_loop(data_fetcher, data_processor, mode_id))
        self._flush_task = asyncio.create_task(self._buffer_flush_loop(data_processor, mode_id))

        return mode_id

    async def _streaming_loop(
        self,
        data_fetcher: Callable,
        data_processor: Callable,
        mode_id: str
    ):
        """Continuous data fetching loop"""
        while self.is_running:
            try:
                # Fetch single record or small batch
                data = await data_fetcher(max_records=1)

                if data:
                    for record in data:
                        self._buffer.append(record)
                        self.last_record_time = datetime.now(timezone.utc)

                        # Flush if buffer is full
                        if len(self._buffer) >= self.buffer_size:
                            await self._flush_buffer(data_processor, mode_id)
                else:
                    # Small sleep to avoid tight loop when no data
                    await asyncio.sleep(0.1)

            except Exception as e:
                self.errors += 1
                logger.error(
                    "Streaming loop error",
                    mode_id=mode_id,
                    error=str(e),
                    exc_info=True
                )
                await asyncio.sleep(1)  # Backoff on error

    async def _buffer_flush_loop(
        self,
        data_processor: Callable,
        mode_id: str
    ):
        """Periodically flush buffer even if not full"""
        while self.is_running:
            await asyncio.sleep(self.buffer_flush_interval)

            if self._buffer:
                elapsed = (datetime.now(timezone.utc) - self._last_flush).total_seconds()
                if elapsed >= self.buffer_flush_interval:
                    await self._flush_buffer(data_processor, mode_id)

    async def _flush_buffer(
        self,
        data_processor: Callable,
        mode_id: str
    ):
        """Flush buffered records"""
        if not self._buffer:
            return

        data = self._buffer.copy()
        self._buffer.clear()
        self._last_flush = datetime.now(timezone.utc)

        try:
            result = await data_processor(data)
            self.records_processed += len(data)

            logger.debug(
                "Streaming buffer flushed",
                mode_id=mode_id,
                records=len(data),
                success=result.get('success', False)
            )

        except Exception as e:
            self.errors += 1
            logger.error(
                "Buffer flush error",
                mode_id=mode_id,
                error=str(e)
            )

    async def stop(self):
        """Stop streaming mode and flush remaining buffer"""
        self.is_running = False

        if self._buffer:
            logger.info(
                "Flushing remaining buffer on stop",
                buffered_records=len(self._buffer)
            )

        logger.info("Streaming mode stopped", records_processed=self.records_processed)

    async def get_metrics(self) -> Dict[str, Any]:
        return {
            'mode': 'continuous_streaming',
            'is_running': self.is_running,
            'records_processed': self.records_processed,
            'errors': self.errors,
            'buffer_size': self.buffer_size,
            'buffered_records': len(self._buffer),
            'last_record_time': self.last_record_time.isoformat() if self.last_record_time else None
        }


class IngestionModeFactory:
    """Factory for creating ingestion mode instances"""

    @staticmethod
    def create_mode(mode_type: str, config: Dict[str, Any]) -> IngestionMode:
        """
        Create ingestion mode instance

        Args:
            mode_type: One of 'batch', 'real_time', 'continuous_streaming'
            config: Mode-specific configuration

        Returns:
            IngestionMode instance
        """
        modes = {
            'batch': BatchMode,
            'real_time': RealTimeMode,
            'continuous_streaming': ContinuousStreamingMode
        }

        mode_class = modes.get(mode_type)
        if not mode_class:
            raise ValueError(
                f"Unknown ingestion mode: {mode_type}. "
                f"Available modes: {list(modes.keys())}"
            )

        return mode_class(config)
