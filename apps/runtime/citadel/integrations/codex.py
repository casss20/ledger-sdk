"""
Citadel × OpenAI Codex integration.

Wraps Codex code generation and execution with governance controls.

Usage:
    from citadel.integrations.codex import GovernedCodex
    
    codex = GovernedCodex(
        citadel_client=client,
        api_key="sk-...",
    )
    
    result = await codex.generate_code(
        prompt="Write a function to sort a list",
        language="python",
    )
"""

from typing import Any, Dict, List, Optional

from citadel.core.sdk import CitadelClient, CitadelResult


class GovernedCodex:
    """
    OpenAI Codex wrapper with Citadel governance.
    
    All code generation and execution is logged and governed.
    """
    
    def __init__(
        self,
        citadel_client: CitadelClient,
        api_key: Optional[str] = None,
        model: str = "codex-latest",
        **kwargs: Any,
    ):
        self.client = citadel_client
        self.api_key = api_key
        self.model = model
        self._codex_kwargs = kwargs
    
    async def generate_code(
        self,
        prompt: str,
        language: str = "python",
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Generate code with governance pre-check.
        
        All code generation requires approval due to high risk.
        """
        # Pre-flight governance check
        decision = await self.client.decide(
            action="codex.generate",
            resource=f"code:{language}",
            payload={
                "prompt": prompt,
                "language": language,
                "context": context,
            },
            actor_id="codex-agent",
        )
        
        if decision.status != "executed":
            return f"[GOVERNANCE: {decision.status}] {decision.reason}"
        
        # Log the generation attempt
        await self.client.execute(
            action="codex.generate",
            resource=f"code:{language}",
            payload={
                "prompt": prompt,
                "language": language,
            },
            actor_id="codex-agent",
        )
        
        # Mock or actual Codex call
        try:
            # Actual OpenAI Codex API call would go here
            return f"# Generated {language} code for: {prompt}\n# (Actual Codex integration would call OpenAI API)"
        except ImportError:
            return f"[MOCK] Code generation for: {prompt}"
    
    async def execute_code(
        self,
        code: str,
        language: str = "python",
        timeout: int = 30,
    ) -> Dict[str, Any]:
        """
        Execute generated code with governance controls.
        
        Code execution is HIGH RISK and always requires approval.
        """
        # Code execution always requires explicit approval
        decision = await self.client.decide(
            action="codex.execute",
            resource=f"execution:{language}",
            payload={
                "code": code,
                "language": language,
                "timeout": timeout,
            },
            actor_id="codex-agent",
        )
        
        if decision.status != "executed":
            return {
                "success": False,
                "output": "",
                "error": f"[GOVERNANCE: {decision.status}] {decision.reason}",
                "governance_status": decision.status,
            }
        
        # Log execution
        await self.client.execute(
            action="codex.execute",
            resource=f"execution:{language}",
            payload={
                "code": code[:500],  # Truncate for logging
                "language": language,
            },
            actor_id="codex-agent",
        )
        
        return {
            "success": True,
            "output": "Code executed successfully (mock)",
            "error": None,
        }
    
    async def review_code(
        self,
        code: str,
        language: str = "python",
    ) -> Dict[str, Any]:
        """
        Review code for security issues before execution.
        
        Returns risk assessment and recommendations.
        """
        # Check for dangerous patterns
        risk_patterns = [
            "eval(",
            "exec(",
            "__import__",
            "subprocess",
            "os.system",
            "open(",
        ]
        
        found_patterns = []
        for pattern in risk_patterns:
            if pattern in code:
                found_patterns.append(pattern)
        
        risk_level = "high" if found_patterns else "low"
        
        return {
            "safe_to_execute": len(found_patterns) == 0,
            "risk_level": risk_level,
            "found_patterns": found_patterns,
            "recommendations": [
                "Avoid using eval/exec",
                "Use safe parsing libraries",
                "Validate all inputs",
            ] if found_patterns else ["No dangerous patterns found"],
        }


class CodexGovernanceServer:
    """
    Governance server for Codex agents.
    
    Provides tools for:
    - Code generation validation
    - Execution approval
    - Security review
    - Audit logging
    """
    
    def __init__(self, citadel_client: CitadelClient):
        self.client = citadel_client
    
    async def check_action(
        self,
        action: str,
        resource: str,
        risk_level: str = "high",  # Default to high for code
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Check if a code action is compliant."""
        decision = await self.client.decide(
            action=action,
            resource=resource,
            payload={
                "risk_level": risk_level,
                **(context or {}),
            },
            actor_id=context.get("agent_id") if context else "codex-agent",
        )
        
        return {
            "allowed": decision.status == "executed",
            "requires_approval": True,  # Code always requires approval
            "reason": decision.reason,
            "action_id": decision.action_id,
            "approval_timeout_seconds": 600,  # Longer timeout for code review
        }
    
    async def review_code(self, code: str, language: str = "python") -> Dict[str, Any]:
        """Review code for security issues."""
        reviewer = GovernedCodex(self.client)
        return await reviewer.review_code(code, language)
    
    async def log_execution(
        self,
        code: str,
        result: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Log code execution to audit trail."""
        execution_result = await self.client.execute(
            action="codex.execute",
            resource="code:execution",
            payload={
                "code": code[:1000],
                "result": result,
                "metadata": metadata or {},
            },
            actor_id="codex-agent",
        )
        
        return {
            "event_id": execution_result.action_id,
            "logged": True,
            "status": execution_result.status,
        }
