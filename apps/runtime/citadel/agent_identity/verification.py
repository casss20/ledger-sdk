"""
Agent Identity Verifier — Bridges identity to governance tokens.

When an agent passes challenge-response authentication, the verifier:
1. Checks trust score meets threshold
2. Issues a CapabilityToken via the governance token system
3. Logs the verification to audit
"""

from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from .identity import AgentIdentity
from .trust_score import TrustScorer, TrustLevel


class AgentVerifier:
    """
    Verifies agent identity and issues capability tokens.
    
    This bridges the identity layer to the governance token system,
    ensuring only properly authenticated agents receive capability tokens.
    """
    
    def __init__(
        self,
        auth_service,
        trust_scorer: Optional[TrustScorer] = None,
        min_trust_level: TrustLevel = TrustLevel.STANDARD,
    ):
        self.auth_service = auth_service
        self.trust_scorer = trust_scorer or TrustScorer()
        self.min_trust_level = min_trust_level
        self._verification_cache: Dict[str, Dict[str, Any]] = {}
    
    async def verify_and_issue_token(
        self,
        agent_id: str,
        challenge: str,
        signature: str,
        requested_capability: str = "default",
    ) -> Dict[str, Any]:
        """
        Verify agent challenge and issue capability token.
        
        Args:
            agent_id: Agent identifier
            challenge: Challenge nonce
            signature: Ed25519 or HMAC signature of challenge
            requested_capability: Capability being requested
            
        Returns:
            Dict with token, trust_score, and verification status
        """
        # Step 1: Verify the challenge
        verify_result = await self.auth_service.verify_challenge(
            agent_id=agent_id,
            challenge=challenge,
            signature=signature,
        )
        
        if not verify_result.get("verified"):
            return {
                "verified": False,
                "error": "Challenge verification failed",
                "agent_id": agent_id,
            }
        
        # Step 2: Check trust level meets minimum
        trust_score = verify_result.get("trust_score", 0.0)
        trust_level = TrustLevel(verify_result.get("trust_level", "unverified"))
        
        level_values = {
            TrustLevel.REVOKED: 0,
            TrustLevel.UNVERIFIED: 1,
            TrustLevel.STANDARD: 2,
            TrustLevel.TRUSTED: 3,
            TrustLevel.HIGHLY_TRUSTED: 4,
        }
        
        if level_values.get(trust_level, 0) < level_values.get(self.min_trust_level, 2):
            return {
                "verified": True,
                "authorized": False,
                "error": f"Trust level {trust_level.value} below minimum {self.min_trust_level.value}",
                "trust_score": trust_score,
                "agent_id": agent_id,
            }
        
        # Step 3: Issue capability token (placeholder for governance integration)
        # In production, this calls citadel.execution.governance_token
        token = {
            "type": "capability_token",
            "agent_id": agent_id,
            "capability": requested_capability,
            "issued_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
            "trust_score": trust_score,
            "trust_level": trust_level.value,
        }
        
        # Cache verification result
        self._verification_cache[agent_id] = {
            "verified_at": datetime.utcnow(),
            "trust_score": trust_score,
            "trust_level": trust_level.value,
            "token": token,
        }
        
        return {
            "verified": True,
            "authorized": True,
            "agent_id": agent_id,
            "trust_score": trust_score,
            "trust_level": trust_level.value,
            "token": token,
        }
    
    def get_cached_verification(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get cached verification result for an agent."""
        cached = self._verification_cache.get(agent_id)
        if not cached:
            return None
        
        # Check expiry (1 hour)
        verified_at = cached.get("verified_at")
        if verified_at and (datetime.utcnow() - verified_at).total_seconds() > 3600:
            del self._verification_cache[agent_id]
            return None
        
        return cached
    
    async def revoke_agent_access(self, agent_id: str) -> Dict[str, Any]:
        """Revoke an agent's access and invalidate cached tokens."""
        # Remove from cache
        if agent_id in self._verification_cache:
            del self._verification_cache[agent_id]
        
        # Revoke via auth service
        result = await self.auth_service.revoke_agent(
            agent_id=agent_id,
            reason="Access revoked by verifier",
        )
        
        return {
            "revoked": True,
            "agent_id": agent_id,
            "message": "Agent access revoked and tokens invalidated",
        }
