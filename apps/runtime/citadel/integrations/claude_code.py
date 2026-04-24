"""
Citadel × Anthropic Claude Code integration.

Wraps Claude Code with governance controls.

Usage:
    from citadel.integrations.claude_code import GovernedClaudeCode
    
    claude = GovernedClaudeCode(
        citadel_client=client,
        api_key="sk-ant-...",
    )
    
    result = await claude.execute(
        prompt="Refactor this function",
        files=["src/utils.py"],
    )
"""

from typing import Any, Dict, List, Optional

from citadel.core.sdk import CitadelClient, CitadelResult


class GovernedClaudeCode:
    """
    Anthropic Claude Code wrapper with Citadel governance.
    
    All code modifications and commands are logged and governed.
    """
    
    def __init__(
        self,
        citadel_client: CitadelClient,
        api_key: Optional[str] = None,
        model: str = "claude-3-opus-20240229",
        **kwargs: Any,
    ):
        self.client = citadel_client
        self.api_key = api_key
        self.model = model
        self._claude_kwargs = kwargs
    
    async def execute(
        self,
        prompt: str,
        files: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Execute a Claude Code command with governance pre-check.
        
        All file modifications require approval.
        """
        # Pre-flight governance check
        decision = await self.client.decide(
            action="claude.execute",
            resource=f"files:{','.join(files or [])}",
            payload={
                "prompt": prompt,
                "files": files or [],
                "context": context,
            },
            actor_id="claude-code-agent",
        )
        
        if decision.status != "executed":
            return f"[GOVERNANCE: {decision.status}] {decision.reason}"
        
        # Log the command
        await self.client.execute(
            action="claude.execute",
            resource=f"files:{','.join(files or [])}",
            payload={
                "prompt": prompt,
                "files": files or [],
            },
            actor_id="claude-code-agent",
        )
        
        # Mock or actual Claude Code call
        try:
            # Actual Claude Code API call would go here
            return f"# Claude Code execution for: {prompt}\n# (Actual Anthropic integration would call Claude API)"
        except ImportError:
            return f"[MOCK] Claude Code execution for: {prompt}"
    
    async def edit_file(
        self,
        file_path: str,
        edit_description: str,
        search_pattern: Optional[str] = None,
        replacement: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Edit a file with governance controls.
        
        File modifications are HIGH RISK and always require approval.
        """
        # File edits always require explicit approval
        decision = await self.client.decide(
            action="claude.edit",
            resource=f"file:{file_path}",
            payload={
                "file_path": file_path,
                "edit_description": edit_description,
            },
            actor_id="claude-code-agent",
        )
        
        if decision.status != "executed":
            return {
                "success": False,
                "error": f"[GOVERNANCE: {decision.status}] {decision.reason}",
                "governance_status": decision.status,
            }
        
        # Log the edit
        await self.client.execute(
            action="claude.edit",
            resource=f"file:{file_path}",
            payload={
                "file_path": file_path,
                "edit_description": edit_description,
            },
            actor_id="claude-code-agent",
        )
        
        return {
            "success": True,
            "file_path": file_path,
            "message": f"File {file_path} edited successfully (mock)",
        }
    
    async def run_tests(
        self,
        test_command: str = "pytest",
    ) -> Dict[str, Any]:
        """
        Run tests with governance logging.
        
        Test execution is logged for audit purposes.
        """
        # Log test execution
        await self.client.execute(
            action="claude.test",
            resource="tests",
            payload={
                "test_command": test_command,
            },
            actor_id="claude-code-agent",
        )
        
        return {
            "success": True,
            "command": test_command,
            "output": "Tests passed (mock)",
        }


class ClaudeCodeGovernanceServer:
    """
    Governance server for Claude Code agents.
    
    Provides tools for:
    - Code modification validation
    - Execution approval
    - Audit logging
    """
    
    def __init__(self, citadel_client: CitadelClient):
        self.client = citadel_client
    
    async def check_action(
        self,
        action: str,
        resource: str,
        risk_level: str = "high",
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Check if a Claude Code action is compliant."""
        decision = await self.client.decide(
            action=action,
            resource=resource,
            payload={
                "risk_level": risk_level,
                **(context or {}),
            },
            actor_id=context.get("agent_id") if context else "claude-code-agent",
        )
        
        return {
            "allowed": decision.status == "executed",
            "requires_approval": True,  # Code changes always require approval
            "reason": decision.reason,
            "action_id": decision.action_id,
            "approval_timeout_seconds": 600,
        }
    
    async def log_edit(
        self,
        file_path: str,
        description: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Log file edit to audit trail."""
        execution_result = await self.client.execute(
            action="claude.edit",
            resource=f"file:{file_path}",
            payload={
                "file_path": file_path,
                "description": description,
                "metadata": metadata or {},
            },
            actor_id="claude-code-agent",
        )
        
        return {
            "event_id": execution_result.action_id,
            "logged": True,
            "status": execution_result.status,
        }
