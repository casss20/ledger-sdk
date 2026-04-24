"""
Backward compatibility shim â€” re-exports from citadel.utils.precedence.

Precedence was moved to Citadel.utils.precedence during the package refactor.
This shim ensures all existing imports continue to work.
"""

from citadel.utils.precedence import Precedence, PrecedenceResult

__all__ = ["Precedence", "PrecedenceResult"]
