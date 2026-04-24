"""
Backward compatibility shim â€” re-exports from citadel.services.approval_service.

ApprovalService was moved to Citadel.services.approval_service during the package refactor.
This shim ensures all existing imports continue to work.
"""

from citadel.services.approval_service import ApprovalService

__all__ = ["ApprovalService"]
