"""
Framework-agnostic rate limiter — three-tier token bucket.

Usage:
    limiter = RateLimiter()
    
    # Check if allowed
    allowed, remaining = await limiter.check("user:123", tier="standard")
    
    # Or use decorator
    @rate_limited(tier="sensitive")
    async def my_function():
        pass
"""

import time
import asyncio
from typing import Dict, Optional, Tuple, Callable, Awaitable
from functools import wraps
from dataclasses import dataclass


@dataclass
class RateLimitConfig:
    """Configuration for a rate limit tier."""
    rate: float        # tokens per second
    capacity: int      # bucket capacity (burst)
    block_seconds: int = 60  # how long to block after exceeding


class TokenBucket:
    """Async token bucket for rate limiting."""
    
    def __init__(self, rate: float, capacity: int):
        self.rate = rate
        self.capacity = capacity
        self.tokens = float(capacity)
        self.last_update = time.time()
        self._lock = asyncio.Lock()
    
    async def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens from bucket."""
        async with self._lock:
            now = time.time()
            elapsed = now - self.last_update
            
            # Add tokens based on elapsed time
            self.tokens = min(
                float(self.capacity),
                self.tokens + elapsed * self.rate
            )
            self.last_update = now
            
            # Check if we can consume
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
    
    async def wait_time(self, tokens: int = 1) -> float:
        """Calculate wait time until tokens available."""
        async with self._lock:
            if self.tokens >= tokens:
                return 0.0
            needed = tokens - self.tokens
            return needed / self.rate


class RateLimiter:
    """
    Three-tier rate limiter: public, standard, sensitive.
    
    Tiers:
        public    → 10 req/sec, burst 20    (unauthenticated)
        standard  → 50 req/sec, burst 100   (normal users)
        sensitive → 10 req/sec, burst 20    (admin, destructive)
    """
    
    DEFAULT_TIERS = {
        "public": RateLimitConfig(rate=10, capacity=20),
        "standard": RateLimitConfig(rate=50, capacity=100),
        "sensitive": RateLimitConfig(rate=10, capacity=20),
    }
    
    def __init__(self, tiers: Optional[Dict[str, RateLimitConfig]] = None):
        self.tiers = tiers or self.DEFAULT_TIERS.copy()
        self._buckets: Dict[str, TokenBucket] = {}
        self._blocked: Dict[str, float] = {}  # key -> unblock_time
    
    def _get_bucket(self, key: str, tier: str) -> TokenBucket:
        """Get or create bucket for key."""
        bucket_key = f"{tier}:{key}"
        if bucket_key not in self._buckets:
            config = self.tiers.get(tier, self.tiers["standard"])
            self._buckets[bucket_key] = TokenBucket(config.rate, config.capacity)
        return self._buckets[bucket_key]
    
    def _is_blocked(self, key: str) -> bool:
        """Check if key is currently blocked."""
        if key in self._blocked:
            if time.time() < self._blocked[key]:
                return True
            del self._blocked[key]
        return False
    
    async def check(self, key: str, tier: str = "standard") -> Tuple[bool, int]:
        """
        Check if request is allowed.
        
        Returns: (allowed, remaining_requests)
        """
        if self._is_blocked(key):
            return False, 0
        
        bucket = self._get_bucket(key, tier)
        config = self.tiers.get(tier, self.tiers["standard"])
        
        if await bucket.consume():
            remaining = int(bucket.tokens)
            return True, remaining
        
        # Block for configured time
        self._blocked[key] = time.time() + config.block_seconds
        return False, 0
    
    async def get_retry_after(self, key: str) -> int:
        """Get seconds until key is unblocked."""
        if key not in self._blocked:
            return 0
        remaining = int(self._blocked[key] - time.time())
        return max(0, remaining)
    
    async def cleanup(self, max_idle_seconds: int = 3600):
        """Remove old buckets to prevent memory leak."""
        now = time.time()
        to_remove = []
        
        for key, bucket in self._buckets.items():
            # Check if bucket has been idle
            if now - bucket.last_update > max_idle_seconds:
                to_remove.append(key)
        
        for key in to_remove:
            del self._buckets[key]
        
        # Clean up expired blocks
        expired_blocks = [
            k for k, unblock_time in self._blocked.items()
            if now > unblock_time
        ]
        for k in expired_blocks:
            del self._blocked[k]
        
        return len(to_remove), len(expired_blocks)


def rate_limited(limiter: RateLimiter, tier: str = "standard", key_fn=None):
    """
    Decorator to rate limit a function.
    
    Args:
        limiter: RateLimiter instance
        tier: Rate limit tier to use
        key_fn: Function to extract key from args (default: uses first arg)
    
    Usage:
        @rate_limited(limiter, tier="sensitive")
        async def delete_user(user_id: str):
            pass
    """
    def decorator(func: Callable[..., Awaitable]) -> Callable[..., Awaitable]:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Determine key
            if key_fn:
                key = key_fn(*args, **kwargs)
            elif args:
                key = str(args[0])
            else:
                key = "default"
            
            allowed, remaining = await limiter.check(key, tier)
            if not allowed:
                retry_after = await limiter.get_retry_after(key)
                raise RateLimitExceeded(retry_after)
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded."""
    def __init__(self, retry_after: int = 60):
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded. Retry after {retry_after} seconds.")
