"""
Backward compatibility shim — re-exports from ledger.services.approval_service.

ApprovalService was moved to ledger.services.approval_service during the package refactor.
This shim ensures all existing imports continue to work.
"""

from ledger.services.approval_service import ApprovalService

__all__ = ["ApprovalService"]
