"""
Backward compatibility shim — re-exports Repository from its new location.

Repository was moved to citadel.core.repository during the package refactor.
This module ensures all existing imports of `from citadel.repository import Repository`
continue to work without requiring a mass-rename across every file.
"""

from citadel.core.repository import Repository

__all__ = ["Repository"]
