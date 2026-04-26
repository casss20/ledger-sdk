"""
Rate Limiting Middleware — Token Bucket with Redis

Protects against:
- Brute force on auth endpoints
- API abuse per tenant
- DDoS / resource exhaustion

Uses Redis for distributed state (works across multiple server instances).
Falls back to in-memory dict if Redis unavailable (single-instance only).
"""

import time
import asyncio
import logging
from typing import Optional, Dict, Tuple
from dataclasses import dataclass

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RateLimitConfig:
    """Rate limit configuration per endpoint category"""
    requests: int      # Max requests in window
    window: int        # Window in seconds
    burst: int         # Max burst (bucket capacity)


# Default configurations per endpoint category
DEFAULT_LIMITS = {
    "auth": RateLimitConfig(requests=5, window=60, burst=3),      # 5 login attempts per minute
    "api": RateLimitConfig(requests=100, window=60, burst=20),   # 100 API calls per minute
    "webhook": RateLimitConfig(requests=1000, window=60, burst=100), # Webhooks are high-volume
    "default": RateLimitConfig(requests=60, window=60, burst=10),
}

# Path prefixes mapped to categories
PATH_CATEGORIES = {
    "/auth/": "auth",
    "/v1/billing/webhooks": "webhook",
    "/api/": "api",
    "/v1/": "api",
    "/dashboard/": "api",
}


class TokenBucket:
    """In-memory token bucket (fallback when Redis unavailable)"""
    
    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.tokens = float(capacity)
        self.refill_rate = refill_rate  # tokens per second
        self.last_refill = time.time()
        self._lock = asyncio.Lock()
    
    async def consume(self, tokens: int = 1) -> Tuple[bool, Dict]:
        """Try to consume tokens. Returns (allowed, headers)"""
        async with self._lock:
            now = time.time()
            elapsed = now - self.last_refill
            self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
            self.last_refill = now
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True, self._headers()
            else:
                retry_after = int((tokens - self.tokens) / self.refill_rate) + 1
                return False, self._headers(retry_after=retry_after)
    
    def _headers(self, retry_after: Optional[int] = None) -> Dict:
        headers = {
            "X-RateLimit-Limit": str(self.capacity),
            "X-RateLimit-Remaining": str(int(self.tokens)),
        }
        if retry_after:
            headers["Retry-After"] = str(retry_after)
        return headers


class RateLimiter:
    """Rate limiter with Redis or in-memory fallback"""
    
    def __init__(self, redis_client=None):
        self.redis = redis_client
        self._memory_buckets: Dict[str, TokenBucket] = {}
        self._memory_lock = asyncio.Lock()
    
    def _get_category(self, path: str) -> str:
        """Determine rate limit category from path"""
        for prefix, category in PATH_CATEGORIES.items():
            if path.startswith(prefix):
                return category
        return "default"
    
    def _get_key(self, request: Request, category: str) -> str:
        """Build rate limit key: prefer tenant, fallback to IP"""
        tenant_id = getattr(request.state, "tenant_id", None)
        if tenant_id:
            return f"ratelimit:{category}:tenant:{tenant_id}"
        
        # Fallback to IP address
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"
        
        return f"ratelimit:{category}:ip:{client_ip}"
    
    async def check(self, request: Request) -> Tuple[bool, Dict, Optional[int]]:
        """
        Check if request is allowed.
        Returns: (allowed, headers_to_add, status_code_if_blocked)
        """
        category = self._get_category(request.url.path)
        config = DEFAULT_LIMITS.get(category, DEFAULT_LIMITS["default"])
        key = self._get_key(request, category)
        
        if self.redis:
            return await self._check_redis(key, config)
        else:
            return await self._check_memory(key, config)
    
    async def _check_redis(self, key: str, config: RateLimitConfig) -> Tuple[bool, Dict, Optional[int]]:
        """Redis-backed token bucket using sliding window"""
        try:
            now = time.time()
            window_start = now - config.window
            
            # Use Redis sorted set for sliding window
            pipe = self.redis.pipeline()
            
            # Remove old entries
            pipe.zremrangebyscore(key, 0, window_start)
            
            # Count current entries
            pipe.zcard(key)
            
            # Add current request
            pipe.zadd(key, {str(now): now})
            
            # Set expiry on the key
            pipe.expire(key, config.window)
            
            results = await pipe.execute()
            current_count = results[1]
            
            if current_count > config.requests:
                retry_after = int(window_start + config.window - now)
                headers = {
                    "X-RateLimit-Limit": str(config.requests),
                    "X-RateLimit-Remaining": "0",
                    "Retry-After": str(max(1, retry_after)),
                }
                return False, headers, 429
            
            remaining = max(0, config.requests - current_count - 1)
            headers = {
                "X-RateLimit-Limit": str(config.requests),
                "X-RateLimit-Remaining": str(remaining),
            }
            return True, headers, None
            
        except (ConnectionError, TimeoutError) as redis_err:
            logger.warning(f"Redis rate limit failed ({type(redis_err).__name__}), falling back to in-memory limiter")
            logger.debug(f"Redis error details: {redis_err}", exc_info=True)
            return await self._check_memory(key, config)
    
    async def _check_memory(self, key: str, config: RateLimitConfig) -> Tuple[bool, Dict, Optional[int]]:
        """In-memory token bucket fallback"""
        async with self._memory_lock:
            if key not in self._memory_buckets:
                refill_rate = config.requests / config.window
                self._memory_buckets[key] = TokenBucket(
                    capacity=config.burst,
                    refill_rate=refill_rate,
                )
        
        bucket = self._memory_buckets[key]
        allowed, headers = await bucket.consume()
        
        if not allowed:
            return False, headers, 429
        
        return True, headers, None
    
    async def close(self):
        """Cleanup"""
        self._memory_buckets.clear()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Token bucket rate limiting middleware.
    
    Per-tenant limits for API calls.
    Per-IP limits for auth endpoints (before tenant is known).
    
    Exempt paths:
      - /health, /healthz (load balancers need these)
      - /docs, /openapi.json, /redoc
    """
    
    EXEMPT_PATHS = {
        "/health",
        "/healthz",
        "/v1/health",
        "/v1/health/ready",
        "/v1/health/live",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/metrics",
    }
    
    def __init__(self, app, redis_client=None):
        super().__init__(app)
        self.limiter = RateLimiter(redis_client)
    
    async def dispatch(self, request: Request, call_next):
        if request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)
        
        allowed, headers, status = await self.limiter.check(request)
        
        if not allowed:
            logger.warning(
                f"Rate limit exceeded: {request.method} {request.url.path} "
                f"key={self.limiter._get_key(request, self.limiter._get_category(request.url.path))}"
            )
            return JSONResponse(
                status_code=status or 429,
                content={
                    "error": "rate_limit_exceeded",
                    "message": "Too many requests. Please slow down.",
                    "retry_after": int(headers.get("Retry-After", 60)),
                },
                headers=headers,
            )
        
        response = await call_next(request)
        
        # Add rate limit headers to response
        for header, value in headers.items():
            response.headers[header] = str(value)
        
        return response


class AuthRateLimitMiddleware(BaseHTTPMiddleware):
    """
    Strict rate limiting for authentication endpoints.
    
    Separate middleware with stricter limits:
      - Login: 5 attempts per 5 minutes per IP
      - API key creation: 3 per hour per tenant
      - Token refresh: 10 per minute per user
    
    This runs BEFORE auth middleware so unauthenticated requests are still limited.
    """
    
    AUTH_LIMITS = {
        "/auth/login": RateLimitConfig(requests=5, window=300, burst=3),        # 5 per 5 min
        "/auth/refresh": RateLimitConfig(requests=10, window=60, burst=5),      # 10 per min
        "/auth/keys": RateLimitConfig(requests=3, window=3600, burst=2),         # 3 per hour
    }
    
    def __init__(self, app, redis_client=None):
        super().__init__(app)
        self.limiter = RateLimiter(redis_client)
    
    async def dispatch(self, request: Request, call_next):
        if request.method != "POST":
            return await call_next(request)
        
        path = request.url.path
        if path not in self.AUTH_LIMITS:
            return await call_next(request)
        
        config = self.AUTH_LIMITS[path]
        
        # Auth endpoints use IP (tenant not known yet)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"
        
        key = f"ratelimit:auth:{path}:ip:{client_ip}"
        
        if self.limiter.redis:
            allowed, headers, status = await self.limiter._check_redis(key, config)
        else:
            allowed, headers, status = await self.limiter._check_memory(key, config)
        
        if not allowed:
            logger.warning(
                f"Auth rate limit exceeded: {path} from {client_ip}"
            )
            return JSONResponse(
                status_code=429,
                content={
                    "error": "auth_rate_limit_exceeded",
                    "message": "Too many authentication attempts. Please try again later.",
                    "retry_after": int(headers.get("Retry-After", 300)),
                },
                headers=headers,
            )
        
        response = await call_next(request)
        for header, value in headers.items():
            response.headers[header] = str(value)
        return response
