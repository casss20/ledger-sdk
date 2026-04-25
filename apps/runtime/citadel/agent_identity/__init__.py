"""
Agent Identity Trust Package

Provides cryptographic agent identity verification:
- Agent keypair generation and management
- JWT-based agent authentication (real endpoints)
- HMAC request signing for agent-to-agent auth
- Trust scoring based on behavior
- Identity registry with verification status

This replaces the fantasy CITADEL.agents.authenticate() with real FastAPI endpoints.
"""

from .identity import AgentIdentity, IdentityManager
from .trust_score import TrustScorer, TrustLevel
from .auth import AgentAuthService
from .verification import AgentVerifier

__all__ = [
    "AgentIdentity",
    "IdentityManager",
    "TrustScorer",
    "TrustLevel",
    "AgentAuthService",
    "AgentVerifier",
]