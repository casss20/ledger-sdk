"""
Backward compatibility shim — re-exports from citadel.services.capability_service.

CapabilityService was moved to citadel.services.capability_service during the package refactor.
This shim ensures all existing imports continue to work.
"""

from citadel.services.capability_service import CapabilityService

__all__ = ["CapabilityService"]
