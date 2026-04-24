"""
Backward compatibility shim â€” re-exports from citadel.execution.executor.

Executor was moved to Citadel.execution.executor during the package refactor.
This shim ensures all existing imports continue to work.
"""

from citadel.execution.executor import Executor

__all__ = ["Executor"]
