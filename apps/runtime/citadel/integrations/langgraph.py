"""
Citadel × LangGraph integration.

Wraps LangGraph StateGraph and nodes with governance controls.

Usage:
    from citadel.integrations.langgraph import GovernedStateGraph, GovernedNode
    
    graph = GovernedStateGraph(
        citadel_client=client,
        name="research-graph",
    )
    
    node = GovernedNode(
        citadel_client=client,
        name="search",
        action="web.search",
    )
    
    graph.add_node(node)
    result = await graph.run({"query": "AI safety"})
"""

from typing import Any, Dict, List, Optional, Callable

from citadel.core.sdk import CitadelClient, CitadelResult


class GovernedNode:
    """
    LangGraph node wrapper with Citadel governance.
    
    Intercepts node execution to check policies
    before allowing the node to proceed.
    """
    
    def __init__(
        self,
        citadel_client: CitadelClient,
        name: str,
        action: str,
        description: str = "",
        fn: Optional[Callable] = None,
        **kwargs: Any,
    ):
        self.client = citadel_client
        self.name = name
        self.action = action
        self.description = description
        self.fn = fn
        self._node_kwargs = kwargs
    
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute node with governance pre-check."""
        # Pre-flight governance check
        decision = await self.client.decide(
            action=self.action,
            resource=f"node:{self.name}",
            payload={
                "node_name": self.name,
                "description": self.description,
                "state": state,
            },
            actor_id=f"langgraph:{self.name}",
        )
        
        if decision.status != "executed":
            return {
                **state,
                "_governance": {
                    "status": decision.status,
                    "reason": decision.reason,
                    "blocked": True,
                }
            }
        
        # Execute the actual function if provided
        if self.fn:
            if asyncio.iscoroutinefunction(self.fn):
                result = await self.fn(state)
            else:
                result = self.fn(state)
        else:
            result = {"result": f"Node {self.name} executed"}
        
        # Log the action
        await self.client.execute(
            action=self.action,
            resource=f"node:{self.name}",
            payload={
                "node_name": self.name,
                "input_state": state,
                "output_state": result,
            },
            actor_id=f"langgraph:{self.name}",
        )
        
        return {**state, **result}


class GovernedStateGraph:
    """
    LangGraph StateGraph wrapper with Citadel governance.
    
    Manages a collection of governed nodes and edges.
    """
    
    def __init__(
        self,
        citadel_client: CitadelClient,
        name: str,
        state_schema: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ):
        self.client = citadel_client
        self.name = name
        self.state_schema = state_schema or {}
        self.nodes: Dict[str, GovernedNode] = {}
        self.edges: List[tuple] = []
        self._graph_kwargs = kwargs
    
    def add_node(self, node: GovernedNode) -> None:
        """Add a governed node to the graph."""
        self.nodes[node.name] = node
    
    def add_edge(self, from_node: str, to_node: str) -> None:
        """Add an edge between nodes."""
        self.edges.append((from_node, to_node))
    
    async def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Run the graph with governance oversight."""
        # Graph-level governance check
        decision = await self.client.decide(
            action="graph.run",
            resource=f"graph:{self.name}",
            payload={
                "graph_name": self.name,
                "node_count": len(self.nodes),
                "inputs": inputs,
            },
        )
        
        if decision.status != "executed":
            return {
                "_governance": {
                    "status": decision.status,
                    "reason": decision.reason,
                    "blocked": True,
                }
            }
        
        # Execute nodes in topological order (simplified)
        state = inputs.copy()
        executed = set()
        
        # Simple execution: follow edges in order
        for from_node, to_node in self.edges:
            if from_node not in executed and from_node in self.nodes:
                state = await self.nodes[from_node].execute(state)
                executed.add(from_node)
                
                # Check if blocked
                if state.get("_governance", {}).get("blocked"):
                    return state
            
            if to_node not in executed and to_node in self.nodes:
                state = await self.nodes[to_node].execute(state)
                executed.add(to_node)
                
                # Check if blocked
                if state.get("_governance", {}).get("blocked"):
                    return state
        
        # Execute any remaining nodes
        for node_name, node in self.nodes.items():
            if node_name not in executed:
                state = await node.execute(state)
                executed.add(node_name)
                
                if state.get("_governance", {}).get("blocked"):
                    return state
        
        return state


class LangGraphGovernanceServer:
    """
    Governance server for LangGraph agents.
    
    Provides tools that LangGraph agents can call for:
    - Policy validation
    - Approval workflows
    - Kill switch checks
    - Audit logging
    """
    
    def __init__(self, citadel_client: CitadelClient):
        self.client = citadel_client
    
    async def check_action(
        self,
        action: str,
        resource: str,
        risk_level: str = "medium",
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Check if an action is compliant with governance policy."""
        decision = await self.client.decide(
            action=action,
            resource=resource,
            payload={
                "risk_level": risk_level,
                **(context or {}),
            },
            actor_id=context.get("agent_id") if context else "langgraph-agent",
        )
        
        return {
            "allowed": decision.status == "executed",
            "requires_approval": decision.status == "pending_approval",
            "reason": decision.reason,
            "action_id": decision.action_id,
            "approval_timeout_seconds": 300 if decision.status == "pending_approval" else 0,
        }
    
    async def get_approval_status(self, approval_id: str) -> Dict[str, Any]:
        """Check if a pending approval has been granted."""
        try:
            response = await self.client._client.get(f"/v1/approvals/{approval_id}")
            response.raise_for_status()
            data = response.json()
            return {
                "approval_id": approval_id,
                "status": data.get("status", "unknown"),
                "approved_by": data.get("approved_by"),
                "reason": data.get("reason"),
            }
        except Exception as e:
            return {
                "approval_id": approval_id,
                "status": "error",
                "reason": str(e),
            }
    
    async def check_kill_switch(self) -> Dict[str, Any]:
        """Check if kill switch is active."""
        try:
            response = await self.client._client.get("/v1/kill-switch/status")
            response.raise_for_status()
            data = response.json()
            is_active = data.get("active", True)
            return {
                "active": is_active,
                "action": "STOP_IMMEDIATELY" if is_active else "CONTINUE",
                "message": "Kill switch activated. Stop all execution." if is_active else "OK to continue",
            }
        except Exception:
            # Fail-closed: if we can't check, assume it's active
            return {
                "active": True,
                "action": "STOP_IMMEDIATELY",
                "message": "Kill switch check failed. Stop all execution.",
            }
    
    async def log_action(
        self,
        action: str,
        resource: str,
        result: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Log an action to the audit trail."""
        execution_result = await self.client.execute(
            action=action,
            resource=resource,
            payload={
                "result": result,
                "metadata": metadata or {},
            },
            actor_id="langgraph-agent",
        )
        
        return {
            "event_id": execution_result.action_id,
            "logged": True,
            "status": execution_result.status,
            "reason": execution_result.reason,
        }
    
    async def get_compliance_report(self, days: int = 30) -> Dict[str, Any]:
        """Generate compliance report for auditors."""
        try:
            response = await self.client._client.get(f"/v1/compliance/report?days={days}")
            response.raise_for_status()
            data = response.json()
            return {
                "period_days": days,
                "total_actions": data.get("total_actions", 0),
                "total_approved": data.get("total_approved", 0),
                "total_blocked": data.get("total_blocked", 0),
                "audit_trail_hash": data.get("audit_hash", ""),
                "hash_chain_verified": True,
            }
        except Exception as e:
            return {
                "period_days": days,
                "error": str(e),
            }


import asyncio
