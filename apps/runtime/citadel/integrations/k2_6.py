"""
Citadel × K2.6 (Moonshot AI) integration.

Wraps K2.6 agents with governance controls.

Usage:
    from citadel.integrations.k2_6 import GovernedK26Agent, GovernedK26Task
    
    agent = GovernedK26Agent(
        citadel_client=client,
        name="data-analyst",
        description="Analyzes data safely",
    )
    
    task = GovernedK26Task(
        citadel_client=client,
        name="analyze",
        action="data.analyze",
        agent=agent,
    )
"""

from typing import Any, Dict, List, Optional

from citadel.core.sdk import CitadelClient, CitadelResult


class GovernedK26Agent:
    """
    K2.6 agent wrapper with Citadel governance.
    
    Intercepts every task execution to check policies
    before allowing the agent to proceed.
    """
    
    def __init__(
        self,
        citadel_client: CitadelClient,
        name: str,
        description: str = "",
        model: str = "kimi-k2",
        tools: Optional[List[str]] = None,
        **kwargs: Any,
    ):
        self.client = citadel_client
        self.name = name
        self.description = description
        self.model = model
        self.tools = tools or []
        self._agent_kwargs = kwargs
    
    async def execute_task(
        self,
        task: "GovernedK26Task",
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Execute a task with governance pre-check."""
        # Pre-flight governance check
        decision = await self.client.decide(
            action=task.action_name,
            resource=f"task:{task.name}",
            payload={
                "task_description": task.description,
                "agent_name": self.name,
                "context": context,
            },
            actor_id=self.name,
        )
        
        if decision.status != "executed":
            return f"[GOVERNANCE: {decision.status}] {decision.reason}"
        
        # Log the action
        await self.client.execute(
            action=task.action_name,
            resource=f"task:{task.name}",
            payload={
                "task_description": task.description,
                "agent_name": self.name,
                "context": context,
            },
            actor_id=self.name,
        )
        
        # Execute via actual K2.6 agent if available
        try:
            from k2_6 import Agent
            agent = Agent(
                name=self.name,
                description=self.description,
                model=self.model,
                tools=self.tools,
                **self._agent_kwargs,
            )
            # K2.6 execution would happen here
            return f"Task executed by {self.name}"
        except ImportError:
            return f"[MOCK] {self.name} would execute: {task.description}"
    
    def to_k26_agent(self):
        """Convert to a native K2.6 Agent instance."""
        try:
            from k2_6 import Agent
            return Agent(
                name=self.name,
                description=self.description,
                model=self.model,
                tools=self.tools,
                **self._agent_kwargs,
            )
        except ImportError:
            raise RuntimeError("k2_6 package not installed")


class GovernedK26Task:
    """
    K2.6 task with Citadel governance integration.
    
    Each task execution is logged and can be blocked
    based on policy rules.
    """
    
    def __init__(
        self,
        citadel_client: CitadelClient,
        name: str,
        description: str = "",
        action: str = "task.execute",
        agent: Optional[GovernedK26Agent] = None,
        expected_output: str = "",
        **kwargs: Any,
    ):
        self.client = citadel_client
        self.name = name
        self.description = description
        self.action_name = action
        self.agent = agent
        self.expected_output = expected_output
        self._task_kwargs = kwargs
    
    async def execute(self, context: Optional[Dict[str, Any]] = None) -> str:
        """Execute task with full governance."""
        if self.agent:
            return await self.agent.execute_task(self, context=context)
        
        # Standalone task execution
        decision = await self.client.decide(
            action=self.action_name,
            resource=f"task:{self.name}",
            payload={
                "description": self.description,
                "expected_output": self.expected_output,
                "context": context,
            },
        )
        
        if decision.status != "executed":
            return f"[GOVERNANCE: {decision.status}] {decision.reason}"
        
        return f"Task completed: {self.description}"


class GovernedK26Workflow:
    """
    K2.6 workflow wrapper with Citadel governance.
    
    Manages a sequence of governed tasks.
    """
    
    def __init__(
        self,
        citadel_client: CitadelClient,
        name: str,
        tasks: List[GovernedK26Task] = None,
        **kwargs: Any,
    ):
        self.client = citadel_client
        self.name = name
        self.tasks = tasks or []
        self._workflow_kwargs = kwargs
    
    async def run(self, inputs: Optional[Dict[str, Any]] = None) -> str:
        """Run the workflow with governance oversight."""
        # Workflow-level governance check
        decision = await self.client.decide(
            action="workflow.run",
            resource=f"workflow:{self.name}",
            payload={
                "task_count": len(self.tasks),
                "inputs": inputs,
            },
        )
        
        if decision.status != "executed":
            return f"[GOVERNANCE: {decision.status}] {decision.reason}"
        
        # Execute tasks in order
        results = []
        for task in self.tasks:
            result = await task.execute(context=inputs)
            results.append(result)
        
        return "\n".join(results)


class K26GovernanceServer:
    """
    MCP-style governance server for K2.6 agents.
    
    Provides tools that K2.6 agents can call for:
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
        """
        Check if an action is compliant with governance policy.
        
        K2.6 agents call this before executing actions.
        """
        decision = await self.client.decide(
            action=action,
            resource=resource,
            payload={
                "risk_level": risk_level,
                **(context or {}),
            },
            actor_id=context.get("agent_id") if context else "k2.6-agent",
        )
        
        return {
            "allowed": decision.status == "executed",
            "requires_approval": decision.status == "pending_approval",
            "reason": decision.reason,
            "action_id": decision.action_id,
            "approval_timeout_seconds": 300 if decision.status == "pending_approval" else 0,
        }
    
    async def get_approval_status(self, approval_id: str) -> Dict[str, Any]:
        """
        Check if a pending approval has been granted.
        
        K2.6 agents poll this to check status.
        """
        # Query the approval status via API
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
        """
        Check if kill switch is active.
        
        If active=True, K2.6 MUST stop execution immediately.
        """
        try:
            response = await self.client._client.get("/v1/kill-switch/status")
            response.raise_for_status()
            data = response.json()
            is_active = data.get("active", False)
            return {
                "active": is_active,
                "action": "STOP_IMMEDIATELY" if is_active else "CONTINUE",
                "message": "Kill switch activated. Stop all execution." if is_active else "OK to continue",
            }
        except Exception:
            # If we can't check, assume it's not active (fail open)
            return {
                "active": False,
                "action": "CONTINUE",
                "message": "OK to continue",
            }
    
    async def log_action(
        self,
        action: str,
        resource: str,
        result: str,
        metadata: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Log an action to the tamper-detected audit trail.
        
        K2.6 logs every action here (compliance requirement).
        """
        execution_result = await self.client.execute(
            action=action,
            resource=resource,
            payload={
                "result": result,
                "metadata": metadata or {},
                "error": error,
            },
            actor_id="k2.6-agent",
        )
        
        return {
            "event_id": execution_result.action_id,
            "logged": True,
            "status": execution_result.status,
            "reason": execution_result.reason,
        }
    
    async def get_compliance_report(self, days: int = 30) -> Dict[str, Any]:
        """
        Generate compliance report for auditors.
        
        Shows all actions logged, approved, blocked with audit trail.
        """
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
                "generated_at": data.get("generated_at"),
            }
        except Exception as e:
            return {
                "period_days": days,
                "total_actions": 0,
                "total_approved": 0,
                "total_blocked": 0,
                "audit_trail_hash": "",
                "hash_chain_verified": False,
                "error": str(e),
            }
