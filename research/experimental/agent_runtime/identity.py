"""Identity â€” Agent Identity & Attestation

The Identity module provides verified identities for AI agents.
Every governed action is tied to a specific agent identity, enabling:
- Audit trails: "Which agent did this?"
- Accountability: "Who owns this agent?"
- Version control: "What model version was used?"
- Capability restrictions: "What is this agent allowed to do?"

Usage:
    from CITADEL import CITADEL, AgentIdentity
    
    # Register an agent
    agent = AgentIdentity(
        agent_id="support-bot-v2",
        owner="acme-corp",
        model="gpt-4",
        version="2024-01-15",
        capabilities=["read", "send_email"]
    )
    
    gov = CITADEL()
    gov.register_agent(agent)
    
    # All actions now tagged with agent identity
    @agent.governed(action="send_email")
    async def send_email(to: str, body: str):
        ...
"""

from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import hashlib
import uuid


class AgentStatus(Enum):
    """Lifecycle status of an agent."""
    PENDING = "pending"       # Registered but not verified
    ACTIVE = "active"         # Verified and running
    SUSPENDED = "suspended"   # Temporarily paused
    REVOKED = "revoked"       # Permanently disabled


@dataclass
class AgentIdentity:
    """Verified identity for an AI agent.
    
    Think of this like a driver's license for AI:
    - Who you are (agent_id)
    - Who vouches for you (owner)
    - What you're allowed to do (capabilities)
    - When you were certified (created_at)
    """
    
    # Required fields
    agent_id: str
    owner: str
    
    # Optional metadata
    name: Optional[str] = None
    description: Optional[str] = None
    model: Optional[str] = None  # "gpt-4", "claude-3", etc.
    version: Optional[str] = None  # Model version or agent version
    training_hash: Optional[str] = None  # Hash of training data/config
    
    # Permissions
    capabilities: List[str] = field(default_factory=list)
    
    # State
    status: AgentStatus = AgentStatus.ACTIVE
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_seen: Optional[datetime] = None
    
    # Internal
    _internal_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    def __post_init__(self):
        """Validate identity on creation."""
        if not self.agent_id:
            raise ValueError("agent_id is required")
        if not self.owner:
            raise ValueError("owner is required")
    
    @property
    def fingerprint(self) -> str:
        """Unique fingerprint of this agent identity.
        
        Used for attestation and audit trails.
        """
        content = f"{self.agent_id}:{self.owner}:{self.model}:{self.version}"
        return hashlib.sha256(content.encode()).hexdigest()[:32]
    
    @property
    def attestation(self) -> Dict[str, Any]:
        """Attestation document for this agent.
        
        Can be cryptographically signed to prove identity.
        """
        return {
            "agent_id": self.agent_id,
            "owner": self.owner,
            "model": self.model,
            "version": self.version,
            "training_hash": self.training_hash,
            "fingerprint": self.fingerprint,
            "capabilities": self.capabilities,
            "status": self.status.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
    
    def can(self, action: str) -> bool:
        """Check if agent has capability for an action."""
        return action in self.capabilities
    
    def has_capability(self, capability: str) -> bool:
        """Alias for can()."""
        return self.can(capability)
    
    def grant(self, capability: str) -> "AgentIdentity":
        """Grant a capability to this agent."""
        if capability not in self.capabilities:
            self.capabilities.append(capability)
        return self
    
    def revoke(self, capability: str) -> "AgentIdentity":
        """Revoke a capability from this agent."""
        if capability in self.capabilities:
            self.capabilities.remove(capability)
        return self
    
    def suspend(self) -> "AgentIdentity":
        """Suspend this agent."""
        self.status = AgentStatus.SUSPENDED
        return self
    
    def activate(self) -> "AgentIdentity":
        """Activate this agent."""
        self.status = AgentStatus.ACTIVE
        self.last_seen = datetime.utcnow()
        return self
    
    def update_seen(self) -> "AgentIdentity":
        """Update last seen timestamp."""
        self.last_seen = datetime.utcnow()
        return self
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        return {
            "agent_id": self.agent_id,
            "owner": self.owner,
            "name": self.name,
            "description": self.description,
            "model": self.model,
            "version": self.version,
            "training_hash": self.training_hash,
            "fingerprint": self.fingerprint,
            "capabilities": self.capabilities,
            "status": self.status.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentIdentity":
        """Deserialize from dict."""
        return cls(
            agent_id=data["agent_id"],
            owner=data["owner"],
            name=data.get("name"),
            description=data.get("description"),
            model=data.get("model"),
            version=data.get("version"),
            training_hash=data.get("training_hash"),
            capabilities=data.get("capabilities", []),
            status=AgentStatus(data.get("status", "active")),
        )


@dataclass
class AgentRegistry:
    """Registry of all agent identities.
    
    Central directory for tracking who is allowed to do what.
    """
    
    agents: Dict[str, AgentIdentity] = field(default_factory=dict)
    
    def register(self, agent: AgentIdentity) -> "AgentRegistry":
        """Register a new agent."""
        self.agents[agent.agent_id] = agent
        return self
    
    def get(self, agent_id: str) -> Optional[AgentIdentity]:
        """Get an agent by ID."""
        return self.agents.get(agent_id)
    
    def get_by_owner(self, owner: str) -> List[AgentIdentity]:
        """Get all agents for an owner."""
        return [a for a in self.agents.values() if a.owner == owner]
    
    def suspend(self, agent_id: str) -> Optional[AgentIdentity]:
        """Suspend an agent."""
        agent = self.agents.get(agent_id)
        if agent:
            agent.suspend()
        return agent
    
    def revoke(self, agent_id: str) -> Optional[AgentIdentity]:
        """Permanently revoke an agent."""
        agent = self.agents.get(agent_id)
        if agent:
            agent.status = AgentStatus.REVOKED
        return agent
    
    def list_active(self) -> List[AgentIdentity]:
        """List all active agents."""
        return [a for a in self.agents.values() if a.status == AgentStatus.ACTIVE]
    
    def verify(self, agent_id: str, required_capabilities: List[str]) -> bool:
        """Verify an agent has required capabilities."""
        agent = self.agents.get(agent_id)
        if not agent:
            return False
        if agent.status != AgentStatus.ACTIVE:
            return False
        return all(agent.can(cap) for cap in required_capabilities)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize registry to dict."""
        return {
            "count": len(self.agents),
            "agents": {aid: a.to_dict() for aid, a in self.agents.items()}
        }


# Singleton registry (can be replaced with DB-backed version)
_default_registry: Optional[AgentRegistry] = None


def get_registry() -> AgentRegistry:
    """Get the default agent registry."""
    global _default_registry
    if _default_registry is None:
        _default_registry = AgentRegistry()
    return _default_registry


def register_agent(agent: AgentIdentity) -> AgentIdentity:
    """Register an agent in the default registry."""
    get_registry().register(agent)
    return agent


def get_agent(agent_id: str) -> Optional[AgentIdentity]:
    """Get an agent from the default registry."""
    return get_registry().get(agent_id)
