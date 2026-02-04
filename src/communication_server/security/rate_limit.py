"""
Rate limiting middleware for API protection.

Implements token bucket algorithm for rate limiting with
sliding window to prevent abuse and ensure fair usage.
"""

import asyncio
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from functools import wraps

from fastapi import HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


@dataclass
class RateLimitBucket:
    """Token bucket for rate limiting."""

    tokens: float
    max_tokens: int
    refill_rate: float  # tokens per second
    last_refill: float
    window_duration: int = 60  # seconds
    window_requests: deque = field(default_factory=deque)

    def refill(self) -> None:
        """Refill tokens based on time elapsed."""
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(self.max_tokens, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now

    def consume(self, tokens: int = 1) -> bool:
        """Consume tokens if available."""
        self.refill()
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False


class RateLimiter:
    """
    Rate limiter using token bucket algorithm.

    Limits requests per client based on IP address or API key.
    """

    def __init__(
        self,
        requests_per_minute: int = 60,
        burst: int = 10,
    ) -> None:
        """
        Initialize the rate limiter.

        Args:
            requests_per_minute: Maximum requests per minute
            burst: Maximum burst size (initial tokens)
        """
        self.requests_per_minute = requests_per_minute
        self.refill_rate = requests_per_minute / 60.0  # tokens per second
        self.burst = burst
        self.buckets: dict[str, RateLimitBucket] = {}
        self._lock = asyncio.Lock()

    def _get_bucket(self, key: str) -> RateLimitBucket:
        """Get or create a rate limit bucket for a key."""
        if key not in self.buckets:
            self.buckets[key] = RateLimitBucket(
                tokens=float(self.burst),
                max_tokens=self.requests_per_minute,
                refill_rate=self.refill_rate,
                last_refill=time.time(),
            )
        return self.buckets[key]

    async def is_allowed(self, key: str, tokens: int = 1) -> bool:
        """
        Check if a request is allowed under rate limit.

        Args:
            key: Unique identifier (IP address, API key, etc.)
            tokens: Number of tokens to consume

        Returns:
            True if request is allowed, False otherwise
        """
        async with self._lock:
            bucket = self._get_bucket(key)
            return bucket.consume(tokens)

    async def get_remaining_tokens(self, key: str) -> int:
        """
        Get remaining tokens for a key.

        Args:
            key: Unique identifier

        Returns:
            Number of remaining tokens
        """
        async with self._lock:
            bucket = self._get_bucket(key)
            bucket.refill()
            return int(bucket.tokens)

    async def reset(self, key: str) -> None:
        """Reset rate limit for a key."""
        async with self._lock:
            if key in self.buckets:
                del self.buckets[key]

    def cleanup_old_buckets(self, max_age_seconds: int = 3600) -> None:
        """Remove inactive buckets to prevent memory leaks."""
        now = time.time()
        keys_to_remove = []
        for key, bucket in self.buckets.items():
            if now - bucket.last_refill > max_age_seconds:
                keys_to_remove.append(key)
        for key in keys_to_remove:
            del self.buckets[key]


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for rate limiting.

    Applies rate limiting based on client IP address.
    """

    def __init__(
        self,
        app,
        rate_limiter: RateLimiter,
        exclude_paths: set[str] | None = None,
    ) -> None:
        """
        Initialize the middleware.

        Args:
            app: FastAPI application
            rate_limiter: Rate limiter instance
            exclude_paths: Paths to exclude from rate limiting
        """
        super().__init__(app)
        self.rate_limiter = rate_limiter
        self.exclude_paths = exclude_paths or {"/health", "/metrics"}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with rate limiting.

        Args:
            request: Incoming request
            call_next: Next middleware/handler

        Returns:
            Response or raises HTTPException if rate limited
        """
        # Skip rate limiting for excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)

        # Get client identifier (IP address or API key)
        client_id = self._get_client_id(request)

        # Check rate limit
        allowed = await self.rate_limiter.is_allowed(client_id)

        if not allowed:
            remaining = await self.rate_limiter.get_remaining_tokens(client_id)
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "Rate limit exceeded",
                    "retry_after": 60,
                    "remaining_tokens": remaining,
                },
                headers={
                    "Retry-After": "60",
                    "X-RateLimit-Limit": str(self.rate_limiter.requests_per_minute),
                    "X-RateLimit-Remaining": str(remaining),
                    "X-RateLimit-Reset": str(int(time.time()) + 60),
                },
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        remaining = await self.rate_limiter.get_remaining_tokens(client_id)
        response.headers["X-RateLimit-Limit"] = str(self.rate_limiter.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(time.time()) + 60)

        return response

    def _get_client_id(self, request: Request) -> str:
        """Get unique client identifier from request."""
        # Try API key first
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return f"apikey:{api_key}"

        # Fall back to IP address
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return f"ip:{forwarded_for.split(',')[0].strip()}"

        client_host = request.client.host if request.client else "unknown"
        return f"ip:{client_host}"


def rate_limit(
    requests_per_minute: int = 60,
    burst: int = 10,
):
    """
    Decorator for rate limiting specific endpoints.

    Args:
        requests_per_minute: Maximum requests per minute
        burst: Maximum burst size

    Example:
        @app.get("/api/expensive")
        @rate_limit(requests_per_minute=10, burst=2)
        async def expensive_operation():
            ...
    """

    def decorator(func: Callable) -> Callable:
        # Shared rate limiter instance for decorated endpoints
        rate_limiter = RateLimiter(
            requests_per_minute=requests_per_minute,
            burst=burst,
        )

        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request from kwargs (FastAPI dependency)
            request: Request | None = kwargs.get("request")
            if not request:
                # Try to get request from args
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break

            if request:
                client_id = rate_limiter._get_client_id(request)
                allowed = await rate_limiter.is_allowed(client_id)

                if not allowed:
                    raise HTTPException(
                        status_code=429,
                        detail="Rate limit exceeded for this endpoint",
                    )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


# Global rate limiter instance
_global_rate_limiter: RateLimiter | None = None


def get_global_rate_limiter() -> RateLimiter:
    """Get or create global rate limiter instance."""
    global _global_rate_limiter
    if _global_rate_limiter is None:
        _global_rate_limiter = RateLimiter(
            requests_per_minute=60,
            burst=10,
        )
    return _global_rate_limiter
