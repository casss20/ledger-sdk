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
from typing import Optional, Dict, Any, Callable, Awaitable, List
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
        Get a governance decision for an action.

        **WARNING**: This is NOT a dry-run. It creates a real Action, runs it
        through the kernel, persists the Decision, and returns the result.
        If you need a true dry-run evaluation without side effects, use
        `dry_run=True` on `delegate()`, `handoff()`, or `gather()` instead.
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
    # ORCHESTRATION
    # =====================================================================
    
    async def delegate(
        self,
        parent_decision_id: str,
        child_actor_id: str,
        action: str,
        resource: str,
        scope: Dict[str, Any] = None,
        payload: Dict[str, Any] = None,
        context: Dict[str, Any] = None,
        tenant_id: str = None,
        trace_id: str = None,
        workflow_id: str = None,
        dry_run: bool = False,
    ) -> CitadelResult:
        """
        Delegate authority from a parent decision to a child agent.
        """
        request = {
            "parent_decision_id": parent_decision_id,
            "child_actor_id": child_actor_id,
            "action_name": action,
            "resource": resource,
            "scope": scope or {"actions": [action], "resources": [resource]},
            "payload": payload or {},
            "context": context or {},
            "dry_run": dry_run,
        }
        if tenant_id:
            request["tenant_id"] = tenant_id
        if trace_id:
            request["trace_id"] = trace_id
        if workflow_id:
            request["workflow_id"] = workflow_id
        
        response = await self._client.post("/v1/orchestrate/delegate", json=request)
        response.raise_for_status()
        data = response.json()
        return CitadelResult(
            action_id=data.get("child_action_id", ""),
            status="delegated" if data["success"] else "blocked",
            winning_rule="delegate",
            reason=data["reason"],
            executed=data["success"],
            error=data.get("error"),
        )
    
    async def handoff(
        self,
        current_decision_id: str,
        new_actor_id: str,
        action: str,
        resource: str,
        scope: Dict[str, Any] = None,
        payload: Dict[str, Any] = None,
        context: Dict[str, Any] = None,
        tenant_id: str = None,
        trace_id: str = None,
        workflow_id: str = None,
        reason: str = "",
        dry_run: bool = False,
    ) -> CitadelResult:
        """
        Transfer active authority from one agent to another.
        """
        request = {
            "current_decision_id": current_decision_id,
            "new_actor_id": new_actor_id,
            "action_name": action,
            "resource": resource,
            "scope": scope or {"actions": [action], "resources": [resource]},
            "payload": payload or {},
            "context": context or {},
            "reason": reason,
            "dry_run": dry_run,
        }
        if tenant_id:
            request["tenant_id"] = tenant_id
        if trace_id:
            request["trace_id"] = trace_id
        if workflow_id:
            request["workflow_id"] = workflow_id
        
        response = await self._client.post("/v1/orchestrate/handoff", json=request)
        response.raise_for_status()
        data = response.json()
        return CitadelResult(
            action_id=data.get("new_decision_id", ""),
            status="handed_off" if data["success"] else "blocked",
            winning_rule="handoff",
            reason=data["reason"],
            executed=data["success"],
            error=data.get("error"),
        )
    
    async def gather(
        self,
        parent_decision_id: str,
        branches: List[Dict[str, Any]],
        tenant_id: str = None,
        trace_id: str = None,
        workflow_id: str = None,
        dry_run: bool = False,
    ) -> CitadelResult:
        """
        Run parallel child branches under one parent orchestration scope.
        """
        request = {
            "parent_decision_id": parent_decision_id,
            "branches": branches,
            "dry_run": dry_run,
        }
        if tenant_id:
            request["tenant_id"] = tenant_id
        if trace_id:
            request["trace_id"] = trace_id
        if workflow_id:
            request["workflow_id"] = workflow_id
        
        response = await self._client.post("/v1/orchestrate/gather", json=request)
        response.raise_for_status()
        data = response.json()
        return CitadelResult(
            action_id=parent_decision_id,
            status="gathered" if data["success"] else "partial_failure",
            winning_rule="gather",
            reason=data["reason"],
            executed=data["success"],
            result=data.get("branches"),
            error=data.get("error"),
        )
    
    async def introspect(
        self,
        token_id: str = None,
        decision_id: str = None,
        required_action: str = "",
        required_resource: str = None,
        workspace_id: str = None,
        tenant_id: str = None,
    ) -> Dict[str, Any]:
        """
        Runtime safety check for any grant or decision.
        """
        request = {
            "required_action": required_action,
        }
        if token_id:
            request["token_id"] = token_id
        if decision_id:
            request["decision_id"] = decision_id
        if required_resource:
            request["required_resource"] = required_resource
        if workspace_id:
            request["workspace_id"] = workspace_id
        if tenant_id:
            request["tenant_id"] = tenant_id
        
        response = await self._client.post("/v1/orchestrate/introspect", json=request)
        response.raise_for_status()
        return response.json()
    
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


async def delegate(*args, **kwargs) -> CitadelResult:
    """Delegate authority to a child agent using the default client."""
    global _default_client
    if _default_client is None:
        configure()
    return await _default_client.delegate(*args, **kwargs)


async def handoff(*args, **kwargs) -> CitadelResult:
    """Transfer active authority to another agent using the default client."""
    global _default_client
    if _default_client is None:
        configure()
    return await _default_client.handoff(*args, **kwargs)


async def gather(*args, **kwargs) -> CitadelResult:
    """Run parallel child branches under one parent scope using the default client."""
    global _default_client
    if _default_client is None:
        configure()
    return await _default_client.gather(*args, **kwargs)


async def introspect(*args, **kwargs) -> Dict[str, Any]:
    """Runtime safety check for any grant or decision using the default client."""
    global _default_client
    if _default_client is None:
        configure()
    return await _default_client.introspect(*args, **kwargs)
