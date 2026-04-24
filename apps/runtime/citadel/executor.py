"""
Backward compatibility shim — re-exports from citadel.execution.executor.

Executor was moved to citadel.execution.executor during the package refactor.
This shim ensures all existing imports continue to work.
"""

from citadel.execution.executor import Executor

__all__ = ["Executor"]
