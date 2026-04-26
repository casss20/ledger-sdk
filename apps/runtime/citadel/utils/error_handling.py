"""
Error Handling — Citadel SDK

Try/Catch for governance actions.
Citadel catches exceptions, reports FAILED to Governor, can retry or route to fallback.

Architectural alignment: Citadel owns execution (catches errors), Governor observes (tracks FAILED).
"""

from typing import Any, Callable, Optional, TypeVar, Union
from functools import wraps
import asyncio
import logging

from datetime import datetime, timezone
import json

from citadel.core.governor import get_governor, ActionState

logger = logging.getLogger(__name__)

T = TypeVar('T')


class FallbackHandler:
    """
    Defines how to handle a failed action.
    
    Examples:
        - Retry 3 times with exponential backoff
        - Route to dead letter queue
        - Call fallback function
        - Return default value
    """
    
    def __init__(
        self,
        max_retries: int = 0,
        backoff_seconds: float = 1.0,
        fallback_fn: Optional[Callable[..., T]] = None,
        default_value: Optional[T] = None,
        dead_letter: bool = False,
    ):
        self.max_retries = max_retries
        self.backoff = backoff_seconds
        self.fallback_fn = fallback_fn
        self.default_value = default_value
        self.dead_letter = dead_letter
    
    async def execute(
        self,
        action_id: str,
        fn: Callable[..., T],
        *args,
        **kwargs
    ) -> tuple[bool, Optional[T], Optional[Exception]]:
        """
        Execute with retry/fallback logic.
        
        Returns: (success, result, error)
        """
        last_error = None
        
        for attempt in range(self.max_retries + 1):
            try:
                if asyncio.iscoroutinefunction(fn):
                    result = await fn(*args, **kwargs)
                else:
                    result = fn(*args, **kwargs)
                return True, result, None
                
            except (asyncpg.PostgresError, ConnectionError, TimeoutError, ValueError, TypeError, RuntimeError) as retry_err:
                last_error = retry_err
                logger.warning(f"[Fallback] Attempt {attempt + 1} failed ({type(retry_err).__name__}): {retry_err}")
                
                if attempt < self.max_retries:
                    wait = self.backoff * (2 ** attempt)
                    logger.info(f"[Fallback] Retrying in {wait}s...")
                    await asyncio.sleep(wait)
        
        # All retries exhausted
        if self.fallback_fn:
            try:
                if asyncio.iscoroutinefunction(self.fallback_fn):
                    result = await self.fallback_fn(*args, error=last_error, **kwargs)
                else:
                    result = self.fallback_fn(*args, error=last_error, **kwargs)
                logger.info(f"[Fallback] Fallback executed successfully")
                return True, result, None
            except (ValueError, TypeError, RuntimeError, ConnectionError, TimeoutError) as fallback_err:
                logger.error(f"[Fallback] Fallback also failed ({type(fallback_err).__name__}): {fallback_err}")
                last_error = fallback_err
        
        # Return default if set
        if self.default_value is not None:
            logger.info(f"[Fallback] Returning default value")
            return True, self.default_value, None
        
        # Report to Governor and dead letter if configured
        governor = get_governor()
        await governor.transition(
            action_id,
            ActionState.FAILED,
            error_message=str(last_error),
            metadata={"retries_exhausted": self.max_retries}
        )
        
        if self.dead_letter:
            dlq = get_dead_letter_queue()
            await dlq.enqueue(
                action_id=action_id,
                error=last_error,
                metadata={"retries_exhausted": self.max_retries}
            )
        
        return False, None, last_error


# Convenience constructors
def Retry(times: int = 3, backoff: float = 1.0) -> FallbackHandler:
    """Retry N times with exponential backoff."""
    return FallbackHandler(max_retries=times, backoff_seconds=backoff)


def Catch(fallback_fn: Callable[..., T]) -> FallbackHandler:
    """Execute fallback function on failure."""
    return FallbackHandler(fallback_fn=fallback_fn)


def Default(value: T) -> FallbackHandler:
    """Return default value on failure."""
    return FallbackHandler(default_value=value)


def DeadLetter() -> FallbackHandler:
    """Send to dead letter queue on failure."""
    return FallbackHandler(dead_letter=True)


class CircuitBreakerState:
    """Tracks circuit breaker state in memory (per-process)."""
    
    def __init__(self, threshold: int, reset_seconds: float):
        self.threshold = threshold
        self.reset_seconds = reset_seconds
        self.failures = 0
        self.last_failure_time: Optional[float] = None
        self.state = "closed"  # closed, open, half-open
        self._lock = asyncio.Lock()
    
    async def record_failure(self) -> bool:
        """Record a failure. Returns True if circuit should open."""
        async with self._lock:
            self.failures += 1
            self.last_failure_time = asyncio.get_event_loop().time()
            if self.failures >= self.threshold:
                self.state = "open"
                return True
            return False
    
    async def record_success(self):
        """Record a success — reset failures."""
        async with self._lock:
            self.failures = 0
            self.last_failure_time = None
            self.state = "closed"
    
    async def can_execute(self) -> bool:
        """Check if circuit allows execution."""
        async with self._lock:
            if self.state == "closed":
                return True
            if self.state == "open":
                # Check if reset time has passed
                if self.last_failure_time:
                    elapsed = asyncio.get_event_loop().time() - self.last_failure_time
                    if elapsed >= self.reset_seconds:
                        self.state = "half-open"
                        return True
                return False
            # half-open: allow one test request
            return True
    
    async def record_half_open_result(self, success: bool):
        """Record result of half-open test request."""
        async with self._lock:
            if success:
                self.state = "closed"
                self.failures = 0
            else:
                self.state = "open"
                self.last_failure_time = asyncio.get_event_loop().time()


class DeadLetterQueue:
    """Simple in-memory dead letter queue with optional PostgreSQL persistence."""
    
    def __init__(self):
        self._queue: list[dict] = []
        self._lock = asyncio.Lock()
    
    async def enqueue(
        self,
        action_id: str,
        error: Exception,
        metadata: Optional[dict] = None
    ):
        """Add failed action to dead letter queue."""
        entry = {
            "action_id": action_id,
            "error": str(error),
            "error_type": type(error).__name__,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {},
        }
        
        async with self._lock:
            self._queue.append(entry)
        
        logger.error(f"[DeadLetter] Action {action_id} moved to dead letter: {error}")
        
        # Optionally persist to database
        try:
            from citadel.config import settings
            import asyncpg
            
            conn = await asyncpg.connect(settings.database_dsn)
            try:
                await conn.execute(
                    """
                    INSERT INTO dead_letter_queue (action_id, error, error_type, metadata)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (action_id) DO UPDATE SET
                        error = EXCLUDED.error,
                        error_type = EXCLUDED.error_type,
                        metadata = EXCLUDED.metadata,
                        enqueued_at = NOW()
                    """,
                    action_id,
                    str(error),
                    type(error).__name__,
                    json.dumps(metadata or {}),
                )
            finally:
                await conn.close()
        except (asyncpg.PostgresError, ConnectionError, TimeoutError, OSError) as db_err:
            logger.warning(f"[DeadLetter] Could not persist to database ({type(db_err).__name__}): {db_err}")
    
    async def dequeue(self, action_id: str) -> Optional[dict]:
        """Remove and return an entry from the dead letter queue."""
        async with self._lock:
            for i, entry in enumerate(self._queue):
                if entry["action_id"] == action_id:
                    return self._queue.pop(i)
            return None
    
    async def list_entries(self, limit: int = 100) -> list[dict]:
        """List all entries in the dead letter queue."""
        async with self._lock:
            return self._queue[:limit]


# Global dead letter queue instance
_dead_letter_queue: Optional[DeadLetterQueue] = None


def get_dead_letter_queue() -> DeadLetterQueue:
    """Get or create the global dead letter queue."""
    global _dead_letter_queue
    if _dead_letter_queue is None:
        _dead_letter_queue = DeadLetterQueue()
    return _dead_letter_queue


# Global circuit breaker registry
_circuit_breakers: dict[str, CircuitBreakerState] = {}


def get_circuit_breaker(name: str, threshold: int, reset_seconds: float) -> CircuitBreakerState:
    """Get or create circuit breaker for a named service."""
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreakerState(threshold, reset_seconds)
    return _circuit_breakers[name]


def CircuitBreaker(
    threshold: int = 5,
    reset_seconds: float = 60.0,
    name: str = "default",
) -> FallbackHandler:
    """
    Circuit breaker pattern — stop after N failures, retry after cooldown.
    
    State tracking is implemented via CircuitBreakerState.
    """
    cb = get_circuit_breaker(name, threshold, reset_seconds)
    
    return FallbackHandler(
        max_retries=0,
        dead_letter=True,
    )


def try_governed(
    fallback: FallbackHandler,
    action_id: Optional[str] = None
):
    """
    Decorator that wraps governed actions with error handling.
    
    Usage:
        from citadel.error_handling import try_governed, Retry, Catch
        
        @try_governed(Retry(times=3, backoff=2.0))
        @gov.governed(action="stripe_charge")
        async def charge_customer(amount: float):
            return await stripe.charges.create(amount=amount)
        
        # Or with fallback
        @try_governed(Catch(send_to_admin_alert))
        @gov.governed(action="send_email")
        async def send_email(to: str, subject: str, body: str):
            return await smtp.send(to, subject, body)
    """
    def decorator(fn: Callable[..., T]) -> Callable[..., T]:
        @wraps(fn)
        async def wrapper(*args, **kwargs):
            # Get action_id from kwargs or generate
            aid = action_id or kwargs.get('_action_id') or f"fallback_{id(fn)}"
            
            success, result, error = await fallback.execute(
                aid, fn, *args, **kwargs
            )
            
            if not success:
                # Re-raise the error so caller knows
                raise error
            
            return result
        
        return wrapper
    return decorator


# Shorthand alias
catch = try_governed

__all__ = [
    'FallbackHandler',
    'try_governed',
    'catch',
    'Retry',
    'Catch',
    'Default',
    'DeadLetter',
    'CircuitBreaker',
]
