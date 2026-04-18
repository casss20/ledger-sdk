"""
Error Handling — Ledger SDK

Try/Catch for governance actions.
Ledger catches exceptions, reports FAILED to Governor, can retry or route to fallback.

Architectural alignment: Ledger owns execution (catches errors), Governor observes (tracks FAILED).
"""

from typing import Any, Callable, Optional, TypeVar, Union
from functools import wraps
import asyncio
import logging

from .governor import get_governor, ActionState

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
                
            except Exception as e:
                last_error = e
                logger.warning(f"[Fallback] Attempt {attempt + 1} failed: {e}")
                
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
            except Exception as e:
                logger.error(f"[Fallback] Fallback also failed: {e}")
                last_error = e
        
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
            # TODO: Implement dead letter queue
            logger.error(f"[DeadLetter] Action {action_id} moved to dead letter: {last_error}")
        
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


def CircuitBreaker(
    threshold: int = 5,
    reset_seconds: float = 60.0
) -> FallbackHandler:
    """
    Circuit breaker pattern — stop after N failures, retry after cooldown.
    
    TODO: Implement circuit breaker state tracking
    """
    return FallbackHandler(
        max_retries=0,
        dead_letter=True  # Fail fast for now
    )


def try_governed(
    fallback: FallbackHandler,
    action_id: Optional[str] = None
):
    """
    Decorator that wraps governed actions with error handling.
    
    Usage:
        from ledger.error_handling import try_governed, Retry, Catch
        
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
