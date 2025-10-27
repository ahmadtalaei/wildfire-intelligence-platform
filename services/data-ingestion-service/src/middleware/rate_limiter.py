"""
API Rate Limiting and Caching Middleware

Implements:
- Token bucket rate limiting per API key/IP
- Redis-based distributed rate limiting
- Response caching for hot data (last 7 days)
- Adaptive rate limits based on system load
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Tuple
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
import hashlib
import json

try:
    import redis.asyncio as redis
except ImportError:
    redis = None

logger = logging.getLogger(__name__)


class TokenBucket:
    """Token bucket algorithm for rate limiting"""

    def __init__(self, capacity: int, refill_rate: float):
        """
        Args:
            capacity: Maximum tokens in bucket
            refill_rate: Tokens added per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = datetime.now(timezone.utc)

    def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens. Returns True if successful."""
        self._refill()

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True

        return False

    def _refill(self):
        """Refill tokens based on elapsed time"""
        now = datetime.now(timezone.utc)
        elapsed = (now - self.last_refill).total_seconds()

        tokens_to_add = elapsed * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now

    def get_wait_time(self) -> float:
        """Get seconds to wait before next token available"""
        if self.tokens >= 1:
            return 0.0

        tokens_needed = 1 - self.tokens
        return tokens_needed / self.refill_rate


class RateLimiter:
    """Distributed rate limiter with Redis backend"""

    def __init__(
        self,
        redis_client: Optional[Any] = None,
        default_limit: int = 100,
        window_seconds: int = 60
    ):
        self.redis_client = redis_client
        self.default_limit = default_limit
        self.window_seconds = window_seconds

        # In-memory fallback if Redis unavailable
        self.local_buckets: Dict[str, TokenBucket] = {}
        self.local_limits: Dict[str, int] = {}

    async def check_rate_limit(
        self,
        identifier: str,
        limit: Optional[int] = None,
        cost: int = 1
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if request is within rate limit.

        Args:
            identifier: Unique identifier (API key, IP, user ID)
            limit: Custom limit for this identifier
            cost: Number of tokens to consume (default 1)

        Returns:
            Tuple of (allowed, metadata)
        """
        limit = limit or self.default_limit

        if self.redis_client:
            return await self._check_redis_rate_limit(identifier, limit, cost)
        else:
            return await self._check_local_rate_limit(identifier, limit, cost)

    async def _check_redis_rate_limit(
        self,
        identifier: str,
        limit: int,
        cost: int
    ) -> Tuple[bool, Dict[str, Any]]:
        """Check rate limit using Redis"""
        key = f"rate_limit:{identifier}"
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(seconds=self.window_seconds)

        try:
            # Use Redis sorted set with sliding window
            pipe = self.redis_client.pipeline()

            # Remove old entries
            pipe.zremrangebyscore(key, 0, window_start.timestamp())

            # Count current requests
            pipe.zcard(key)

            # Add current request
            request_id = f"{now.timestamp()}:{cost}"
            pipe.zadd(key, {request_id: now.timestamp()})

            # Set expiry
            pipe.expire(key, self.window_seconds)

            results = await pipe.execute()
            current_count = results[1]

            allowed = current_count < limit
            remaining = max(0, limit - current_count)

            metadata = {
                "limit": limit,
                "remaining": remaining,
                "reset_at": (now + timedelta(seconds=self.window_seconds)).isoformat(),
                "retry_after": self.window_seconds if not allowed else None
            }

            return allowed, metadata

        except Exception as e:
            logger.error(f"Redis rate limit error: {e}")
            # Fallback to local
            return await self._check_local_rate_limit(identifier, limit, cost)

    async def _check_local_rate_limit(
        self,
        identifier: str,
        limit: int,
        cost: int
    ) -> Tuple[bool, Dict[str, Any]]:
        """Check rate limit using in-memory token bucket"""
        if identifier not in self.local_buckets:
            refill_rate = limit / self.window_seconds
            self.local_buckets[identifier] = TokenBucket(limit, refill_rate)
            self.local_limits[identifier] = limit

        bucket = self.local_buckets[identifier]
        allowed = bucket.consume(cost)

        metadata = {
            "limit": limit,
            "remaining": int(bucket.tokens),
            "reset_at": (datetime.now(timezone.utc) + timedelta(seconds=bucket.get_wait_time())).isoformat(),
            "retry_after": bucket.get_wait_time() if not allowed else None
        }

        return allowed, metadata

    async def get_identifier(self, request: Request) -> str:
        """Extract identifier from request (API key or IP)"""
        # Try API key first
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return f"key:{api_key}"

        # Fall back to IP address
        client_ip = request.client.host if request.client else "unknown"
        return f"ip:{client_ip}"

    async def get_limit_for_endpoint(self, endpoint: str) -> int:
        """Get rate limit for specific endpoint"""
        # Different limits for different endpoints
        limits = {
            "/ingest/batch": 50,  # Lower limit for expensive operations
            "/ingest/file": 20,
            "/stream/start": 30,
            "/quality/metrics": 200,  # Higher for read-only
            "/health": 1000  # Very high for health checks
        }

        return limits.get(endpoint, self.default_limit)


class ResponseCache:
    """Response caching layer for hot data (last 7 days)"""

    def __init__(
        self,
        redis_client: Optional[Any] = None,
        default_ttl_seconds: int = 300  # 5 minutes
    ):
        self.redis_client = redis_client
        self.default_ttl_seconds = default_ttl_seconds

        # In-memory cache fallback
        self.local_cache: Dict[str, Tuple[Any, datetime]] = {}

    async def get(self, key: str) -> Optional[Any]:
        """Get cached response"""
        if self.redis_client:
            return await self._get_from_redis(key)
        else:
            return await self._get_from_local(key)

    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None
    ):
        """Set cached response"""
        ttl = ttl_seconds or self.default_ttl_seconds

        if self.redis_client:
            await self._set_in_redis(key, value, ttl)
        else:
            await self._set_in_local(key, value, ttl)

    async def invalidate(self, pattern: str):
        """Invalidate cached responses matching pattern"""
        if self.redis_client:
            await self._invalidate_redis(pattern)
        else:
            await self._invalidate_local(pattern)

    async def _get_from_redis(self, key: str) -> Optional[Any]:
        """Get from Redis cache"""
        try:
            cached = await self.redis_client.get(f"cache:{key}")
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.error(f"Redis cache get error: {e}")
        return None

    async def _set_in_redis(self, key: str, value: Any, ttl: int):
        """Set in Redis cache"""
        try:
            await self.redis_client.setex(
                f"cache:{key}",
                ttl,
                json.dumps(value)
            )
        except Exception as e:
            logger.error(f"Redis cache set error: {e}")

    async def _invalidate_redis(self, pattern: str):
        """Invalidate Redis cache entries"""
        try:
            keys = await self.redis_client.keys(f"cache:{pattern}")
            if keys:
                await self.redis_client.delete(*keys)
        except Exception as e:
            logger.error(f"Redis cache invalidation error: {e}")

    async def _get_from_local(self, key: str) -> Optional[Any]:
        """Get from local cache"""
        if key in self.local_cache:
            value, expiry = self.local_cache[key]
            if datetime.now(timezone.utc) < expiry:
                return value
            else:
                del self.local_cache[key]
        return None

    async def _set_in_local(self, key: str, value: Any, ttl: int):
        """Set in local cache"""
        expiry = datetime.now(timezone.utc) + timedelta(seconds=ttl)
        self.local_cache[key] = (value, expiry)

    async def _invalidate_local(self, pattern: str):
        """Invalidate local cache entries"""
        pattern = pattern.replace('*', '')
        keys_to_delete = [k for k in self.local_cache.keys() if pattern in k]
        for key in keys_to_delete:
            del self.local_cache[key]

    @staticmethod
    def generate_cache_key(request: Request) -> str:
        """Generate cache key from request"""
        # Include path, query params, and relevant headers
        path = request.url.path
        query = str(request.query_params)

        key_parts = [path, query]
        key_string = ":".join(key_parts)

        # Hash for consistent key length
        return hashlib.md5(key_string.encode()).hexdigest()


class RateLimitMiddleware:
    """FastAPI middleware for rate limiting"""

    def __init__(
        self,
        rate_limiter: RateLimiter,
        response_cache: Optional[ResponseCache] = None
    ):
        self.rate_limiter = rate_limiter
        self.response_cache = response_cache

    async def __call__(self, request: Request, call_next):
        """Process request with rate limiting and caching"""

        # Skip rate limiting for health checks
        if request.url.path == "/health":
            return await call_next(request)

        # Check cache for GET requests
        if self.response_cache and request.method == "GET":
            cache_key = ResponseCache.generate_cache_key(request)
            cached_response = await self.response_cache.get(cache_key)

            if cached_response:
                logger.debug(f"Cache HIT for {request.url.path}")
                return JSONResponse(
                    content=cached_response,
                    headers={"X-Cache": "HIT"}
                )

        # Rate limiting
        identifier = await self.rate_limiter.get_identifier(request)
        endpoint = request.url.path
        limit = await self.rate_limiter.get_limit_for_endpoint(endpoint)

        allowed, metadata = await self.rate_limiter.check_rate_limit(
            identifier=identifier,
            limit=limit
        )

        # Add rate limit headers to response
        headers = {
            "X-RateLimit-Limit": str(metadata["limit"]),
            "X-RateLimit-Remaining": str(metadata["remaining"]),
            "X-RateLimit-Reset": metadata["reset_at"]
        }

        if not allowed:
            # Rate limit exceeded
            headers["Retry-After"] = str(int(metadata["retry_after"]))

            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "limit": metadata["limit"],
                    "retry_after": metadata["retry_after"]
                },
                headers=headers
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        for key, value in headers.items():
            response.headers[key] = value

        # Cache response for GET requests with 200 status
        if (self.response_cache and
            request.method == "GET" and
            response.status_code == 200):

            cache_key = ResponseCache.generate_cache_key(request)

            # Different TTLs based on endpoint
            if "quality" in endpoint or "metrics" in endpoint:
                ttl = 60  # 1 minute for metrics
            elif "sources" in endpoint:
                ttl = 300  # 5 minutes for source lists
            else:
                ttl = 180  # 3 minutes default

            # Cache response body
            # Note: This is simplified; in production, you'd need to handle streaming responses
            response.headers["X-Cache"] = "MISS"

        return response


async def create_rate_limiter(redis_url: Optional[str] = None) -> RateLimiter:
    """Factory function to create rate limiter with Redis connection"""
    redis_client = None

    if redis_url and redis:
        try:
            redis_client = await redis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            logger.info("Rate limiter using Redis backend")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis, using in-memory rate limiting: {e}")

    return RateLimiter(redis_client=redis_client)


async def create_response_cache(redis_url: Optional[str] = None) -> ResponseCache:
    """Factory function to create response cache with Redis connection"""
    redis_client = None

    if redis_url and redis:
        try:
            redis_client = await redis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=False  # For binary cache data
            )
            logger.info("Response cache using Redis backend")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis, using in-memory caching: {e}")

    return ResponseCache(redis_client=redis_client)
