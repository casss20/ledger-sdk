"""
Executor - Runs allowed actions.

Only job: Execute the action function.
No governance logic here - that's all done before we get here.
"""

from typing import Any, Callable, Awaitable

from ledger.kernel import Action


class Executor:
    """
    Executes actions that have passed all governance checks.
    
    Simple wrapper around the actual action function.
    Handles:
    - Timing
    - Error catching
    - Result wrapping
    """
    
    async def run(
        self,
        action: Action,
        func: Callable[..., Awaitable[Any]],
        *args,
        **kwargs
    ) -> Any:
        """
        Execute the governed action.
        
        All governance checks already passed. Just run it.
        """
        # Could add: timing, circuit breakers, timeouts here
        # But keep it simple for MVP
        
        result = await func(*args, **kwargs)
        return result
    
    async def run_with_fallback(
        self,
        action: Action,
        func: Callable[..., Awaitable[Any]],
        fallback: Callable[..., Awaitable[Any]],
        *args,
        **kwargs
    ) -> Any:
        """
        Execute with fallback on failure.
        
        From FAILURE.md patterns.
        """
        try:
            return await func(*args, **kwargs)
        except Exception:
            return await fallback(*args, **kwargs)
