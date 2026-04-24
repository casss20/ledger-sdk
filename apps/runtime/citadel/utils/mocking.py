"""
Native Mocking — Citadel SDK

Like Weft's mocking: any node can be replaced with "return this data instead".
Type-checked against real ports. Build top-down (define interfaces first).
"""

from typing import Any, Callable, Dict, Optional, TypeVar, Generic
from functools import wraps
from dataclasses import dataclass, asdict
import copy
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class MockDefinition:
    """
    Definition of a mock response.
    Like Weft's mock metadata.
    """
    action: str
    mock_fn: Callable[..., Any]
    return_type: Optional[type] = None
    validate_against_real: bool = True  # Type-check against real signature
    
    def execute(self, *args, **kwargs) -> Any:
        """Execute the mock function."""
        try:
            result = self.mock_fn(*args, **kwargs)
            logger.debug(f"[Mock] Executed mock for {self.action}")
            return result
        except Exception as e:
            logger.error(f"[Mock] Mock execution failed for {self.action}: {e}")
            raise MockExecutionError(f"Mock failed: {e}") from e


class MockExecutionError(Exception):
    """Error during mock execution."""
    pass


class MockValidationError(Exception):
    """Mock doesn't match expected signature/type."""
    pass


class MockRegistry:
    """
    Registry for managing mocks.
    Like Weft's mock registry at the language level.
    """
    
    _mocks: Dict[str, MockDefinition] = {}
    _active: bool = False
    _real_impls: Dict[str, Callable] = {}  # Store real implementations
    
    @classmethod
    def register(
        cls,
        action: str,
        mock_fn: Callable[..., T],
        return_type: Optional[type] = None,
        validate: bool = True
    ) -> MockDefinition:
        """
        Register a mock for an action.
        
        Args:
            action: The action to mock (e.g., "send_email")
            mock_fn: Function that returns mock data
            return_type: Expected return type for validation
            validate: Whether to validate against real signature
            
        Returns:
            MockDefinition for the registered mock
        """
        mock_def = MockDefinition(
            action=action,
            mock_fn=mock_fn,
            return_type=return_type,
            validate_against_real=validate,
        )
        cls._mocks[action] = mock_def
        cls._active = True
        logger.info(f"[MockRegistry] Registered mock for {action}")
        return mock_def
    
    @classmethod
    def unregister(cls, action: str) -> bool:
        """Remove a mock."""
        if action in cls._mocks:
            del cls._mocks[action]
            logger.info(f"[MockRegistry] Unregistered mock for {action}")
            if not cls._mocks:
                cls._active = False
            return True
        return False
    
    @classmethod
    def clear(cls):
        """Clear all mocks."""
        cls._mocks.clear()
        cls._real_impls.clear()
        cls._active = False
        logger.info("[MockRegistry] Cleared all mocks")
    
    @classmethod
    def get(cls, action: str) -> Optional[MockDefinition]:
        """Get mock definition for an action."""
        return cls._mocks.get(action)
    
    @classmethod
    def is_mocked(cls, action: str) -> bool:
        """Check if an action has a mock registered."""
        return action in cls._mocks
    
    @classmethod
    def is_active(cls) -> bool:
        """Check if mocking is globally active."""
        return cls._active
    
    @classmethod
    def list_mocked(cls) -> list[str]:
        """List all mocked actions."""
        return list(cls._mocks.keys())
    
    @classmethod
    def store_real_impl(cls, action: str, impl: Callable):
        """Store the real implementation for restoration."""
        cls._real_impls[action] = impl
    
    @classmethod
    def get_real_impl(cls, action: str) -> Optional[Callable]:
        """Get the real implementation for an action."""
        return cls._real_impls.get(action)


class MockContext:
    """
    Context manager for temporary mocking.
    Like Weft's "mock this node for this execution".
    """
    
    def __init__(self, mocks: Dict[str, Callable]):
        """
        Args:
            mocks: Dict of {action: mock_fn}
        """
        self.mocks = mocks
        self._registered: list[str] = []
    
    def __enter__(self):
        for action, mock_fn in self.mocks.items():
            MockRegistry.register(action, mock_fn)
            self._registered.append(action)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        for action in self._registered:
            MockRegistry.unregister(action)
        return False


def mockable(
    action: str,
    return_type: Optional[type] = None,
    validate: bool = True
):
    """
    Decorator that enables mocking for any governed function.
    
    Like Weft's native mocking — any node can be replaced with mock data.
    
    Usage:
        @mockable("send_email")
        @gov.governed(action="send_email")
        async def send_email(to: str, subject: str, body: str):
            # Real implementation
            return await smtp.send(to, subject, body)
        
        # Later, in tests:
        MockRegistry.register(
            "send_email",
            lambda **kwargs: {"message_id": "mock_123", "status": "sent"}
        )
        
        # Now send_email() returns mock data, never hitting SMTP
    """
    def decorator(fn: Callable[..., T]) -> Callable[..., T]:
        # Store real implementation
        MockRegistry.store_real_impl(action, fn)
        
        @wraps(fn)
        async def async_wrapper(*args, **kwargs) -> T:
            # Check if mocked
            mock_def = MockRegistry.get(action)
            if mock_def and MockRegistry.is_active():
                logger.info(f"[Mockable] Using mock for {action}")
                
                # Validate if requested
                if validate and return_type:
                    result = mock_def.execute(*args, **kwargs)
                    if not isinstance(result, return_type):
                        raise MockValidationError(
                            f"Mock for {action} returned {type(result)}, "
                            f"expected {return_type}"
                        )
                    return result
                
                return mock_def.execute(*args, **kwargs)
            
            # Use real implementation
            return await fn(*args, **kwargs)
        
        @wraps(fn)
        def sync_wrapper(*args, **kwargs) -> T:
            mock_def = MockRegistry.get(action)
            if mock_def and MockRegistry.is_active():
                logger.info(f"[Mockable] Using mock for {action}")
                
                if validate and return_type:
                    result = mock_def.execute(*args, **kwargs)
                    if not isinstance(result, return_type):
                        raise MockValidationError(
                            f"Mock for {action} returned {type(result)}, "
                            f"expected {return_type}"
                        )
                    return result
                
                return mock_def.execute(*args, **kwargs)
            
            return fn(*args, **kwargs)
        
        import asyncio
        if asyncio.iscoroutinefunction(fn):
            return async_wrapper
        return sync_wrapper
    
    return decorator


def mock(
    action: str,
    return_value: Any = None,
    side_effect: Optional[Callable] = None
) -> MockDefinition:
    """
    Quick mock registration with static return value.
    
    Usage:
        mock("send_email", {"message_id": "mock_123", "status": "sent"})
        mock("stripe_charge", side_effect=lambda amount: {"charged": amount * 0.95})
    """
    if side_effect:
        return MockRegistry.register(action, side_effect)
    
    return MockRegistry.register(action, lambda *args, **kwargs: return_value)


# Convenience aliases
register_mock = MockRegistry.register
unregister_mock = MockRegistry.unregister
clear_mocks = MockRegistry.clear
is_mocked = MockRegistry.is_mocked
Mock = MockContext  # Shorthand

__all__ = [
    'MockDefinition',
    'MockExecutionError',
    'MockValidationError',
    'MockRegistry',
    'MockContext',
    'mockable',
    'mock',
    'register_mock',
    'unregister_mock',
    'clear_mocks',
    'is_mocked',
    'Mock',
]