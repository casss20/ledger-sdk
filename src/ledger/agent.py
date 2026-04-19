"""Agent — Agent Lifecycle Management

High-level agent management that combines Identity, Constitution, and Governance.

This is the main interface developers use to create and manage AI agents
with full governance, identity, and constitutional constraints.

Usage:
    from ledger import Agent
    
    # Create a governed agent
    agent = Agent(
        agent_id="support-bot-v2",
        owner="acme-corp",
        model="gpt-4",
        constitution=[
            "Never impersonate a human",
            "Always disclose when acting as AI"
        ],
        capabilities=["read", "send_email"]
    )
    
    # Define governed actions
    @agent.action("send_email")
    async def send_email(to: str, body: str):
        return await smtp.send(to, body)
    
    # Run with full governance
    result = await agent.run(send_email, to="user@example.com", body="Hello")
"""

from typing import List, Dict, Any, Optional, Callable, TypeVar, ParamSpec
from dataclasses import dataclass, field
from functools import wraps
import asyncio

from .identity import AgentIdentity, AgentRegistry, get_registry, register_agent
from .constitution import Constitution, ConstitutionViolation, DEFAULT_CONSTITUTION
from .sdk import Ledger
from .governor import get_governor, ActionState


P = ParamSpec('P')
T = TypeVar('T')


@dataclass
class Agent:
    """A governed AI agent with identity, constitution, and capabilities.
    
    This is the main developer-facing class for creating AI agents that:
    - Have verified identity (who they are)
    - Follow constitutional rules (behavioral constraints)
    - Are governed for risky actions (risk classification)
    - Can be audited and controlled (visibility)
    
    Example:
        agent = Agent(
            agent_id="my-bot",
            owner="my-org",
            constitution=["Never lie", "Always be helpful"],
            capabilities=["search", "summarize"]
        )
        
        @agent.action("search", resource="web_search")
        async def search(query: str):
            return await web_search(query)
    """
    
    # Identity
    agent_id: str
    owner: str
    
    # Optional
    name: Optional[str] = None
    description: Optional[str] = None
    model: Optional[str] = None
    version: Optional[str] = None
    
    # Governance
    constitution: Optional[Constitution] = None
    capabilities: List[str] = field(default_factory=list)
    
    # Internal
    _identity: Optional[AgentIdentity] = field(default=None, repr=False)
    _ledger: Optional[Ledger] = field(default=None, repr=False)
    _registered: bool = field(default=False, repr=False)
    
    def __post_init__(self):
        """Initialize agent with identity and governance."""
        # Create or use provided constitution
        if self.constitution is None:
            self.constitution = DEFAULT_CONSTITUTION
        
        # Create identity
        self._identity = AgentIdentity(
            agent_id=self.agent_id,
            owner=self.owner,
            name=self.name,
            description=self.description,
            model=self.model,
            version=self.version,
            capabilities=self.capabilities.copy()
        )
        
        # Create ledger for this agent
        self._ledger = Ledger(
            agent=self.agent_id,
            constitution=self.constitution
        )
        
        # Register with global registry
        if not self._registered:
            register_agent(self._identity)
            self._registered = True
    
    @property
    def identity(self) -> AgentIdentity:
        """Get agent identity."""
        return self._identity
    
    @property
    def ledger(self) -> Ledger:
        """Get agent's ledger instance."""
        return self._ledger
    
    @property
    def fingerprint(self) -> str:
        """Get agent fingerprint."""
        return self._identity.fingerprint
    
    @property
    def is_active(self) -> bool:
        """Check if agent is active."""
        return self._identity.status.value == "active"
    
    def can(self, action: str) -> bool:
        """Check if agent can perform an action."""
        return self._identity.can(action)
    
    def grant(self, capability: str) -> "Agent":
        """Grant a capability to this agent."""
        self._identity.grant(capability)
        self.capabilities = self._identity.capabilities.copy()
        return self
    
    def revoke(self, capability: str) -> "Agent":
        """Revoke a capability from this agent."""
        self._identity.revoke(capability)
        self.capabilities = self._identity.capabilities.copy()
        return self
    
    def suspend(self) -> "Agent":
        """Suspend this agent."""
        self._identity.suspend()
        return self
    
    def activate(self) -> "Agent":
        """Activate this agent."""
        self._identity.activate()
        return self
    
    def action(
        self,
        action: str,
        resource: Optional[str] = None,
        flag: Optional[str] = None,
        risk: Optional[str] = None
    ) -> Callable:
        """Decorator for governed agent actions.
        
        This is the main way to define what an agent can do.
        
        Example:
            @agent.action("send_email", resource="outbound_email")
            async def send_email(to: str, body: str):
                return await smtp.send(to, body)
        """
        def decorator(func: Callable[P, T]) -> Callable[P, T]:
            # First apply ledger governance
            governed_func = self._ledger.governed(
                action=action,
                resource=resource or action,
                flag=flag
            )(func)
            
            @wraps(func)
            async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
                # Check agent is active
                if not self.is_active:
                    raise RuntimeError(f"Agent {self.agent_id} is not active")
                
                # Check capability
                if not self.can(action):
                    raise PermissionError(
                        f"Agent {self.agent_id} lacks capability: {action}"
                    )
                
                # Update last seen
                self._identity.update_seen()
                
                # Execute governed function
                return await governed_func(*args, **kwargs)
            
            # Attach metadata
            wrapper._agent = self
            wrapper._action = action
            wrapper._is_agent_action = True
            
            return wrapper
        
        return decorator
    
    async def run(
        self,
        action_func: Callable[..., T],
        *args,
        **kwargs
    ) -> T:
        """Run an action with full governance.
        
        Alternative to decorator for dynamic action execution.
        
        Example:
            result = await agent.run(send_email, to="user@example.com", body="Hi")
        """
        # Check agent is active
        if not self.is_active:
            raise RuntimeError(f"Agent {self.agent_id} is not active")
        
        # Get action metadata
        action = getattr(action_func, '_action', 'unknown')
        
        # Check capability
        if not self.can(action):
            raise PermissionError(
                f"Agent {self.agent_id} lacks capability: {action}"
            )
        
        # Update last seen
        self._identity.update_seen()
        
        # Execute
        return await action_func(*args, **kwargs)
    
    def check_constitution(self, output: str) -> List[str]:
        """Check if output violates constitution.
        
        Returns list of violated rules (empty if clean).
        """
        violations = self.constitution.check(
            action="generate",
            context={"output": output}
        )
        return [v.text for v in violations]
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize agent to dict."""
        return {
            "agent_id": self.agent_id,
            "owner": self.owner,
            "name": self.name,
            "description": self.description,
            "model": self.model,
            "version": self.version,
            "fingerprint": self.fingerprint,
            "is_active": self.is_active,
            "capabilities": self.capabilities.copy(),
            "constitution": self.constitution.to_dict() if self.constitution else None,
            "identity": self._identity.to_dict() if self._identity else None,
        }
    
    def __repr__(self) -> str:
        return f"Agent({self.agent_id}, owner={self.owner}, active={self.is_active})"


# Convenience function for quick agent creation

def create_agent(
    agent_id: str,
    owner: str,
    constitution: Optional[List[str]] = None,
    capabilities: Optional[List[str]] = None,
    **kwargs
) -> Agent:
    """Quickly create a governed agent.
    
    Example:
        agent = create_agent(
            agent_id="support-bot",
            owner="acme-corp",
            constitution=["Never impersonate a human"],
            capabilities=["read", "send_email"]
        )
    """
    const = Constitution(constitution) if constitution else None
    
    return Agent(
        agent_id=agent_id,
        owner=owner,
        constitution=const,
        capabilities=capabilities or [],
        **kwargs
    )
