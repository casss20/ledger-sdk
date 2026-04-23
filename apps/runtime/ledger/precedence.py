"""
Backward compatibility shim — re-exports from ledger.utils.precedence.

Precedence was moved to ledger.utils.precedence during the package refactor.
This shim ensures all existing imports continue to work.
"""

from ledger.utils.precedence import Precedence, PrecedenceResult

__all__ = ["Precedence", "PrecedenceResult"]
