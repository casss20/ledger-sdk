"""Backward-compatibility shim — service moved to citadel.commercial.entitlement_service."""
from citadel.commercial.entitlement_service import EntitlementService
__all__ = ["EntitlementService"]
