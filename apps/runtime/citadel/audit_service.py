"""
Backward compatibility shim â€” re-exports from citadel.services.audit_service.

AuditService was moved to Citadel.services.audit_service during the package refactor.
This shim ensures all existing imports continue to work.
"""

from citadel.services.audit_service import AuditService

__all__ = ["AuditService"]
