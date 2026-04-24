"""
Citadel SDK - Universal client for the governance kernel.

One primitive: execute an action under control.

Usage:
    import citadel
    
    result = await citadel.execute(
        action="email.send",
        resource="user:123",
        payload={"to": "external@gmail.com"},
        actor_id="agent-1",
    )
    
    if result.status == "executed":
        return result.result
    elif result.status == "pending_approval":
        return "Waiting for approval"
    else:
        return f"Blocked: {result.reason}"
"""

import os
from typing import Optional, Dict, Any, Callable, Awaitable
from dataclasses import dataclass

import httpx


@dataclass
class CitadelResult:
    """Result of an action through Citadel governance."""
    action_id: str
    status: str  # executed, blocked, pending_approval, failed_execution, etc.
    winning_rule: str
    reason: str
    executed: bool
    result: Optional[Any] = None
    error: Optional[str] = None


class CitadelClient:
    """
    Universal SDK client for Citadel governance.
    
    Works with:
    - Python
    - Any HTTP-capable language (via API)
    - Agents and APIs
    """
    
    def __init__(
        self,
        base_url: str = None,
        api_key: str = None,
        actor_id: str = None,
        actor_type: str = "agent",
    ):
        self.base_url = (base_url or os.getenv("CITADEL_URL", "http://localhost:8000")).rstrip("/")
        self.api_key = api_key or os.getenv("CITADEL_API_KEY", "")
        self.actor_id = actor_id or os.getenv("CITADEL_ACTOR_ID", "default")
        self.actor_type = actor_type
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"X-API-Key": self.api_key} if self.api_key else {},
            timeout=30.0,
        )
    
    # =====================================================================
    # CORE PRIMITIVE: execute
    # =====================================================================
    
    async def execute(
        self,
        action: str,
        resource: str,
        payload: Dict[str, Any] = None,
        context: Dict[str, Any] = None,
        actor_id: str = None,
        actor_type: str = None,
        idempotency_key: str = None,
        capability_token: str = None,
    ) -> CitadelResult:
        """
        Execute an action under governance control.
        
        The ONE entry point. Everything funnels through here.
        """
        request = {
            "actor_id": actor_id or self.actor_id,
            "actor_type": actor_type or self.actor_type,
            "action_name": action,
            "resource": resource,
            "payload": payload or {},
            "context": context or {},
        }
        
        if idempotency_key:
            request["idempotency_key"] = idempotency_key
        if capability_token:
            request["capability_token"] = capability_token
        
        response = await self._client.post("/v1/actions/execute", json=request)
        response.raise_for_status()
        
        data = response.json()
        return CitadelResult(
            action_id=data["action_id"],
            status=data["status"],
            winning_rule=data["winning_rule"],
            reason=data["reason"],
            executed=data["executed"],
            result=data.get("result"),
            error=data.get("error"),
        )
    
    # =====================================================================
    # DECISION (no execution)
    # =====================================================================
    
    async def decide(
        self,
        action: str,
        resource: str,
        payload: Dict[str, Any] = None,
        context: Dict[str, Any] = None,
        actor_id: str = None,
        actor_type: str = None,
    ) -> CitadelResult:
        """
        Get a decision without executing the action.
        
        Useful for: pre-flight checks, dry runs, policy debugging.
        """
        return await self.execute(
            action=action,
            resource=resource,
            payload=payload,
            context=context,
            actor_id=actor_id,
            actor_type=actor_type,
        )
    
    # =====================================================================
    # GUARD (decorator / wrapper)
    # =====================================================================
    
    def guard(
        self,
        action: str = None,
        resource: str = None,
    ) -> Callable:
        """
        Decorator: wrap an async function with governance.
        
        Usage:
            @citadel.guard(action="email.send", resource="user:{user_id}")
            async def send_email(user_id: str, body: str):
                ...
        """
        def decorator(fn: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
            async def wrapper(*args, **kwargs):
                # Resolve action/resource with optional formatting
                resolved_action = action or fn.__name__
                resolved_resource = resource or resolved_action
                
                # Try to format resource with kwargs
                try:
                    resolved_resource = resolved_resource.format(**kwargs)
                except (KeyError, IndexError):
                    pass
                
                result = await self.execute(
                    action=resolved_action,
                    resource=resolved_resource,
                    payload={"args": args, "kwargs": kwargs},
                )
                
                if result.status == "executed":
                    return await fn(*args, **kwargs)
                elif result.status == "pending_approval":
                    raise ApprovalRequired(f"Action pending approval: {result.reason}")
                else:
                    raise ActionBlocked(f"Action blocked: {result.reason} (rule: {result.winning_rule})")
            
            return wrapper
        return decorator
    
    def wrap(self, fn: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        """
        Wrap an existing function with governance.
        
        Usage:
            governed_send = citadel.wrap(send_email)
        """
        return self.guard()(fn)
    
    # =====================================================================
    # APPROVALS
    # =====================================================================
    
    async def approve(self, approval_id: str, reviewed_by: str, reason: str = "Approved") -> Dict:
        """Approve a pending request."""
        response = await self._client.post(
            f"/v1/approvals/{approval_id}/approve",
            json={"reviewed_by": reviewed_by, "reason": reason},
        )
        response.raise_for_status()
        return response.json()
    
    async def reject(self, approval_id: str, reviewed_by: str, reason: str = "Rejected") -> Dict:
        """Reject a pending request."""
        response = await self._client.post(
            f"/v1/approvals/{approval_id}/reject",
            json={"reviewed_by": reviewed_by, "reason": reason},
        )
        response.raise_for_status()
        return response.json()
    
    # =====================================================================
    # AUDIT
    # =====================================================================
    
    async def verify_audit(self) -> Dict:
        """Verify audit chain integrity."""
        response = await self._client.get("/v1/audit/verify")
        response.raise_for_status()
        return response.json()
    
    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, *args):
        await self.close()


# =====================================================================
# Exceptions
# =====================================================================

class ActionBlocked(Exception):
    """Raised when an action is blocked by governance."""
    pass


class ApprovalRequired(Exception):
    """Raised when an action requires human approval."""
    pass


# =====================================================================
# Module-level convenience
# =====================================================================

_default_client: Optional[CitadelClient] = None


def configure(
    base_url: str = None,
    api_key: str = None,
    actor_id: str = None,
    actor_type: str = "agent",
):
    """Configure the default Citadel client."""
    global _default_client
    _default_client = CitadelClient(
        base_url=base_url,
        api_key=api_key,
        actor_id=actor_id,
        actor_type=actor_type,
    )


async def execute(*args, **kwargs) -> CitadelResult:
    """Execute an action using the default client."""
    global _default_client
    if _default_client is None:
        configure()
    return await _default_client.execute(*args, **kwargs)


async def decide(*args, **kwargs) -> CitadelResult:
    """Get a decision using the default client."""
    global _default_client
    if _default_client is None:
        configure()
    return await _default_client.decide(*args, **kwargs)


async def approve(*args, **kwargs) -> Dict:
    """Approve a request using the default client."""
    global _default_client
    if _default_client is None:
        configure()
    return await _default_client.approve(*args, **kwargs)


async def reject(*args, **kwargs) -> Dict:
    """Reject a request using the default client."""
    global _default_client
    if _default_client is None:
        configure()
    return await _default_client.reject(*args, **kwargs)


def guard(*args, **kwargs) -> Callable:
    """Guard decorator using the default client."""
    global _default_client
    if _default_client is None:
        configure()
    return _default_client.guard(*args, **kwargs)


def wrap(fn: Callable) -> Callable:
    """Wrap a function using the default client."""
    global _default_client
    if _default_client is None:
        configure()
    return _default_client.wrap(fn)


async def verify_audit() -> Dict:
    """Verify audit chain using the default client."""
    global _default_client
    if _default_client is None:
        configure()
    return await _default_client.verify_audit()
