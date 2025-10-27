"""
APIClient: Generic polling interface for data sources
Handles API requests, rate limiting, error handling, and caching
"""

import asyncio
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timezone, timedelta
import structlog
from abc import ABC, abstractmethod

logger = structlog.get_logger()


class APIClient(ABC):
    """Base class for API clients that poll data sources"""

    def __init__(
        self,
        source_id: str,
        rate_limit_per_minute: int = 60,
        timeout_seconds: float = 30.0,
        cache_ttl_seconds: int = 60
    ):
        self.source_id = source_id
        self.rate_limit_per_minute = rate_limit_per_minute
        self.timeout_seconds = timeout_seconds
        self.cache_ttl_seconds = cache_ttl_seconds

        # Rate limiting
        self.request_timestamps: List[datetime] = []
        self.requests_made = 0
        self.requests_failed = 0

        # Caching
        self._cache: Dict[str, Dict[str, Any]] = {}

        # State
        self.last_successful_fetch = None
        self.consecutive_failures = 0

    @abstractmethod
    async def fetch_data(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Fetch data from source

        Must be implemented by subclasses
        """
        pass

    async def poll(self, **kwargs) -> Dict[str, Any]:
        """
        Poll data source with rate limiting and error handling

        Returns:
            Dict with data, status, and metadata
        """
        # Check rate limit
        if not await self._check_rate_limit():
            return {
                'success': False,
                'error': 'rate_limit_exceeded',
                'data': [],
                'retry_after_seconds': await self._get_retry_after()
            }

        # Check cache
        cache_key = self._generate_cache_key(kwargs)
        cached_data = self._get_from_cache(cache_key)
        if cached_data:
            logger.debug(
                "Returning cached data",
                source_id=self.source_id,
                cache_key=cache_key
            )
            return {
                'success': True,
                'data': cached_data,
                'from_cache': True,
                'cached_at': self._cache[cache_key]['cached_at'].isoformat()
            }

        # Fetch fresh data
        try:
            start_time = datetime.now(timezone.utc)

            data = await asyncio.wait_for(
                self.fetch_data(**kwargs),
                timeout=self.timeout_seconds
            )

            fetch_duration = (datetime.now(timezone.utc) - start_time).total_seconds()

            # Record successful request
            self.request_timestamps.append(datetime.now(timezone.utc))
            self.requests_made += 1
            self.last_successful_fetch = datetime.now(timezone.utc)
            self.consecutive_failures = 0

            # Cache the result
            self._add_to_cache(cache_key, data)

            logger.info(
                "Data fetched successfully",
                source_id=self.source_id,
                records=len(data) if data else 0,
                duration_seconds=round(fetch_duration, 2)
            )

            return {
                'success': True,
                'data': data,
                'from_cache': False,
                'records_fetched': len(data) if data else 0,
                'fetch_duration_seconds': fetch_duration
            }

        except asyncio.TimeoutError:
            self.requests_failed += 1
            self.consecutive_failures += 1

            logger.error(
                "API request timeout",
                source_id=self.source_id,
                timeout_seconds=self.timeout_seconds
            )

            return {
                'success': False,
                'error': 'timeout',
                'data': [],
                'consecutive_failures': self.consecutive_failures
            }

        except Exception as e:
            self.requests_failed += 1
            self.consecutive_failures += 1

            logger.error(
                "API request failed",
                source_id=self.source_id,
                error=str(e),
                exc_info=True
            )

            return {
                'success': False,
                'error': str(e),
                'data': [],
                'consecutive_failures': self.consecutive_failures
            }

    async def _check_rate_limit(self) -> bool:
        """Check if we're within rate limit"""
        now = datetime.now(timezone.utc)
        one_minute_ago = now - timedelta(minutes=1)

        # Remove old timestamps
        self.request_timestamps = [
            ts for ts in self.request_timestamps
            if ts > one_minute_ago
        ]

        # Check limit
        return len(self.request_timestamps) < self.rate_limit_per_minute

    async def _get_retry_after(self) -> int:
        """Calculate retry-after delay in seconds"""
        if not self.request_timestamps:
            return 0

        # Find oldest timestamp in window
        oldest = min(self.request_timestamps)
        now = datetime.now(timezone.utc)
        elapsed = (now - oldest).total_seconds()

        # Wait until we're outside the 1-minute window
        return max(0, int(60 - elapsed))

    def _generate_cache_key(self, params: Dict[str, Any]) -> str:
        """Generate cache key from parameters"""
        # Simple string concatenation of sorted params
        sorted_params = sorted(params.items())
        return f"{self.source_id}_{str(sorted_params)}"

    def _get_from_cache(self, cache_key: str) -> Optional[List[Dict[str, Any]]]:
        """Get data from cache if not expired"""
        if cache_key not in self._cache:
            return None

        cached_entry = self._cache[cache_key]
        cached_at = cached_entry['cached_at']
        now = datetime.now(timezone.utc)

        # Check TTL
        if (now - cached_at).total_seconds() > self.cache_ttl_seconds:
            # Expired
            del self._cache[cache_key]
            return None

        return cached_entry['data']

    def _add_to_cache(self, cache_key: str, data: List[Dict[str, Any]]):
        """Add data to cache"""
        self._cache[cache_key] = {
            'data': data,
            'cached_at': datetime.now(timezone.utc)
        }

        # Limit cache size
        if len(self._cache) > 100:
            # Remove oldest entry
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k]['cached_at'])
            del self._cache[oldest_key]

    async def get_metrics(self) -> Dict[str, Any]:
        """Get API client metrics"""
        return {
            'source_id': self.source_id,
            'requests_made': self.requests_made,
            'requests_failed': self.requests_failed,
            'success_rate': (
                (self.requests_made - self.requests_failed) / self.requests_made
                if self.requests_made > 0 else 1.0
            ),
            'consecutive_failures': self.consecutive_failures,
            'last_successful_fetch': (
                self.last_successful_fetch.isoformat()
                if self.last_successful_fetch else None
            ),
            'cache_entries': len(self._cache),
            'rate_limit_per_minute': self.rate_limit_per_minute,
            'requests_in_last_minute': len([
                ts for ts in self.request_timestamps
                if ts > datetime.now(timezone.utc) - timedelta(minutes=1)
            ])
        }


class ConnectorAPIClient(APIClient):
    """
    API Client that wraps existing connector interfaces
    Provides standardized polling for any connector
    """

    def __init__(
        self,
        source_id: str,
        connector: Any,
        fetch_method: str = 'fetch_data',
        **kwargs
    ):
        super().__init__(source_id, **kwargs)
        self.connector = connector
        self.fetch_method = fetch_method

    async def fetch_data(self, **kwargs) -> List[Dict[str, Any]]:
        """Fetch data using connector's method"""
        if not hasattr(self.connector, self.fetch_method):
            raise AttributeError(
                f"Connector does not have method '{self.fetch_method}'"
            )

        method = getattr(self.connector, self.fetch_method)

        # Call the method
        result = await method(**kwargs)

        # Handle various return types
        if isinstance(result, list):
            return result
        elif isinstance(result, dict):
            # Check for common data keys
            if 'data' in result:
                return result['data']
            elif 'records' in result:
                return result['records']
            else:
                return [result]
        elif result is None:
            return []
        else:
            return [result]


class BatchAPIClient(APIClient):
    """
    API Client for batch data fetching
    Tracks last fetch timestamp to get only new data
    """

    def __init__(self, source_id: str, connector: Any, **kwargs):
        super().__init__(source_id, **kwargs)
        self.connector = connector
        self.last_fetch_timestamp = None

    async def fetch_data(self, **kwargs) -> List[Dict[str, Any]]:
        """Fetch data since last fetch"""
        # Add since parameter if available
        if self.last_fetch_timestamp and 'since' not in kwargs:
            kwargs['since'] = self.last_fetch_timestamp

        # Fetch using connector
        if hasattr(self.connector, 'fetch_batch_data'):
            data = await self.connector.fetch_batch_data(**kwargs)
        elif hasattr(self.connector, 'fetch_data'):
            data = await self.connector.fetch_data(**kwargs)
        else:
            raise NotImplementedError(
                f"Connector {type(self.connector).__name__} "
                f"does not implement fetch_batch_data or fetch_data"
            )

        # Update last fetch timestamp
        if data:
            self.last_fetch_timestamp = datetime.now(timezone.utc)

        return data if isinstance(data, list) else []
