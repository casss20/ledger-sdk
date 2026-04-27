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
from .trust_score import TrustSnapshotEngine, TrustScorer, TrustLevel, TrustScore
from .trust_bands import TrustBand, BandConstraints, BAND_CONSTRAINTS
from .trust_policy import TrustPolicyEngine, TrustPolicyResult, TrustPolicyContext
from .trust_audit import TrustAuditLogger
from .auth import AgentAuthService
from .verification import AgentVerifier

__all__ = [
    "AgentIdentity",
    "IdentityManager",
    "TrustSnapshotEngine",
    "TrustScorer",
    "TrustLevel",
    "TrustScore",
    "TrustBand",
    "BandConstraints",
    "BAND_CONSTRAINTS",
    "TrustPolicyEngine",
    "TrustPolicyResult",
    "TrustPolicyContext",
    "TrustAuditLogger",
    "AgentAuthService",
    "AgentVerifier",
]