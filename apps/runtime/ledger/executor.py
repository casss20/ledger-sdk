"""
Backward compatibility shim — re-exports from ledger.execution.executor.

Executor was moved to ledger.execution.executor during the package refactor.
This shim ensures all existing imports continue to work.
"""

from ledger.execution.executor import Executor

__all__ = ["Executor"]
