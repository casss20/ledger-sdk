"""
Log all tenant context operations for security audit.
"""

import logging
import json
from datetime import datetime, timezone

logger = logging.getLogger("ledger.security")

def log_tenant_access(
    operation: str,
    tenant_id: str,
    user_id: str | None,
    resource_type: str,
    resource_id: str,
    result: str,  # "allowed" or "blocked"
):
    """Log each tenant access for audit trail"""
    logger.info(
        json.dumps({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "operation": operation,
            "tenant_id": tenant_id,
            "user_id": user_id,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "result": result,
        })
    )

def alert_on_missing_context(path: str):
    """Alert when request tries to access without tenant context"""
    logger.critical(
        f"SECURITY: Request to {path} missing tenant context. "
        f"This is a data isolation violation."
    )

def alert_on_admin_bypass(operation: str, tenant_id: str, user_id: str | None):
    """Alert when admin bypass is used"""
    logger.warning(
        f"SECURITY: Admin bypass used for {operation} on tenant {tenant_id} "
        f"by {user_id}. Verify this was authorized."
    )
