"""
Backward compatibility shim — re-exports from citadel.services.audit_service.

AuditService was moved to citadel.services.audit_service during the package refactor.
This shim ensures all existing imports continue to work.
"""

from citadel.services.audit_service import AuditService

__all__ = ["AuditService"]
