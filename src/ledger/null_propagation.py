"""
Null Propagation — Ledger SDK

Like Weft's null propagation: when upstream produces nothing, 
downstream skips gracefully. No try/catch ceremony.

Principles:
- Required inputs refuse to run on null
- Null cascades through the graph until hitting something that handles it
- Optional ports (marked with ?) opt into receiving null
"""

from typing import Any, Optional, TypeVar, Generic, Callable
from functools import wraps
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


class SkipExecution(Exception):
    """
    Graceful skip — not an error.
    Like Weft's null propagation through the graph.
    """
    pass


class NullValue:
    """
    Sentinel for explicit null (distinct from None).
    Allows None to be a valid value while still propagating skips.
    """
    pass


class Required:
    """
    Wrapper for required inputs. Raises SkipExecution if null.
    Like Weft's required ports.
    """
    
    @staticmethod
    def check(value: Any, name: str, context: dict = None) -> Any:
        """
        Validate required input. Raises SkipExecution if null/empty.
        
        Args:
            value: The input value to check
            name: Name of the input (for error messages)
            context: Additional context for logging
            
        Returns:
            The value if valid
            
        Raises:
            SkipExecution: If value is null/empty
        """
        if value is None or value == "" or value == [] or value == {}:
            ctx_str = f" | context: {context}" if context else ""
            logger.info(f"[NullProp] Required input '{name}' is null — skipping execution{ctx_str}")
            raise SkipExecution(f"Required input '{name}' is null")
        return value
    
    @staticmethod
    def all(**kwargs) -> dict:
        """
        Check multiple required inputs at once.
        
        Returns:
            Dict of validated values
            
        Raises:
            SkipExecution: If any value is null
        """
        results = {}
        for name, value in kwargs.items():
            results[name] = Required.check(value, name)
        return results


class Optional:
    """
    Wrapper for optional inputs. Returns None if null, doesn't skip.
    Like Weft's optional ports (marked with ?).
    """
    
    @staticmethod
    def check(value: Any) -> Optional[Any]:
        """
        Return value if present, None if null/empty.
        Never raises SkipExecution.
        """
        if value is None or value == "" or value == [] or value == {}:
            return None
        return value
    
    @staticmethod
    def with_default(value: Any, default: T) -> T:
        """
        Return value if present, default otherwise.
        """
        if value is None or value == "" or value == [] or value == {}:
            return default
        return value


class NullPropagator:
    """
    Main entry point for null propagation.
    Like Weft's null propagation through the execution graph.
    """
    
    @staticmethod
    def required(value: Any, name: str) -> Any:
        """Alias for Required.check"""
        return Required.check(value, name)
    
    @staticmethod
    def optional(value: Any) -> Optional[Any]:
        """Alias for Optional.check"""
        return Optional.check(value)
    
    @staticmethod
    def default(value: Any, default: T) -> T:
        """Alias for Optional.with_default"""
        return Optional.with_default(value, default)


def null_safe(fn: Callable) -> Callable:
    """
    Decorator that makes a function null-safe.
    If any required argument is null, execution skips gracefully.
    
    Like Weft's automatic null propagation through connected nodes.
    """
    @wraps(fn)
    async def async_wrapper(*args, **kwargs):
        try:
            return await fn(*args, **kwargs)
        except SkipExecution as e:
            logger.info(f"[NullSafe] Skipped {fn.__name__}: {e}")
            return NullValue  # Propagate skip
    
    @wraps(fn)
    def sync_wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except SkipExecution as e:
            logger.info(f"[NullSafe] Skipped {fn.__name__}: {e}")
            return NullValue  # Propagate skip
    
    import asyncio
    if asyncio.iscoroutinefunction(fn):
        return async_wrapper
    return sync_wrapper


class Pipeline:
    """
    Pipeline that handles null propagation automatically.
    Like Weft's graph execution with null propagation.
    """
    
    def __init__(self, name: str = "pipeline"):
        self.name = name
        self.steps: list[Callable] = []
        self.results: list[Any] = []
    
    def add(self, step: Callable, required_inputs: list[str] = None):
        """
        Add a step to the pipeline.
        
        Args:
            step: Function to execute
            required_inputs: List of required input names
        """
        self.steps.append((step, required_inputs or []))
        return self
    
    async def execute(self, initial_input: Any = None) -> Any:
        """
        Execute pipeline with null propagation.
        If any step returns NullValue or raises SkipExecution,
        remaining steps are skipped gracefully.
        """
        current = initial_input
        
        for i, (step, required_names) in enumerate(self.steps):
            try:
                # Check required inputs
                for name in required_names:
                    if current is None or current == NullValue:
                        logger.info(f"[Pipeline] Step {i} skipped: required input '{name}' is null")
                        return NullValue
                
                # Execute step
                if current is NullValue:
                    logger.info(f"[Pipeline] Step {i} skipped: upstream produced null")
                    return NullValue
                
                if callable(step):
                    if current is not None:
                        current = await step(current) if asyncio.iscoroutinefunction(step) else step(current)
                    else:
                        current = await step() if asyncio.iscoroutinefunction(step) else step()
                
                self.results.append(current)
                
                # Check if step produced null
                if current is NullValue:
                    logger.info(f"[Pipeline] Stopping at step {i}: produced null")
                    break
                    
            except SkipExecution as e:
                logger.info(f"[Pipeline] Step {i} skipped: {e}")
                return NullValue
        
        return current
    
    def reset(self):
        """Reset pipeline for re-execution."""
        self.results = []
        return self


# Convenience aliases for import
req = Required.check
opt = Optional.check
default = Optional.with_default
prop = NullPropagator

__all__ = [
    'SkipExecution',
    'NullValue',
    'Required',
    'Optional',
    'NullPropagator',
    'null_safe',
    'Pipeline',
    'req',
    'opt',
    'default',
    'prop',
]