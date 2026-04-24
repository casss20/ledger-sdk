"""
Backward compatibility shim — re-exports from citadel.utils.precedence.

Precedence was moved to citadel.utils.precedence during the package refactor.
This shim ensures all existing imports continue to work.
"""

from citadel.utils.precedence import Precedence, PrecedenceResult

__all__ = ["Precedence", "PrecedenceResult"]
