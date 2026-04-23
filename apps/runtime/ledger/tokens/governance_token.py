"""
Governance Token — Optional scoped capability proof derived from a decision.

Why: Tokens are NOT the primary artifact. GovernanceDecision is.
A token is a portable proof that a decision was made and is still valid.
Verification resolves the linked decision and checks constraints.
"""

import hashlib
import secrets
import string
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from .governance_decision import GovernanceDecision, DecisionType

# Base62 alphabet for URL-safe encoding
_BASE62 = string.ascii_letters + string.digits


def _base62_encode(data: bytes) -> str:
    """URL-safe base62 encoding (alphanumeric only)."""
    num = int.from_bytes(data, byteorder="big")
    if num == 0:
        return _BASE62[0]
    result = []
    while num > 0:
        num, rem = divmod(num, 62)
        result.append(_BASE62[rem])
    return "".join(reversed(result))


def _canonical_json(data: dict) -> str:
    """JSON Canonicalization Scheme (JCS/RFC 8785 simplified)."""
    import json
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


@dataclass
class CapabilityToken:
    """
    Optional scoped capability proof derived from a GovernanceDecision.

    Format: gt_<type>_<base62_32byte_random>
    
    Verification flow:
    1. Resolve token → get decision_id
    2. Resolve decision → check expiry, revocation, scope, kill switch
    3. Return verification result
    """

    token_id: str
    decision_id: str  # links to GovernanceDecision
    tenant_id: str
    actor_id: str
    scope_actions: list[str] = field(default_factory=list)
    scope_resources: list[str] = field(default_factory=list)
    expiry: Optional[datetime] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    chain_hash: Optional[str] = None

    @classmethod
    def derive(
        cls,
        decision: GovernanceDecision,
        previous_hash: Optional[str] = None,
    ) -> "CapabilityToken":
        """
        Derive a capability token from an approved decision.

        Why: Only ALLOW decisions can produce tokens.
        """
        if decision.decision_type != DecisionType.ALLOW:
            raise ValueError(
                f"Cannot derive token from {decision.decision_type.value} decision"
            )

        random_bytes = secrets.token_bytes(32)
        random_b62 = _base62_encode(random_bytes)
        token_id = f"gt_cap_{random_b62}"

        # Content hash = hash of decision reference
        content = {
            "decision_id": decision.decision_id,
            "tenant_id": decision.tenant_id,
            "actor_id": decision.actor_id,
            "actions": decision.scope.actions,
            "expiry": decision.expiry.isoformat() if decision.expiry else None,
        }
        content_hash = hashlib.sha256(_canonical_json(content).encode()).hexdigest()

        # Chain hash
        if previous_hash:
            chain_data = f"{content_hash}||{previous_hash}"
            chain_hash = hashlib.sha256(chain_data.encode()).hexdigest()
        else:
            chain_hash = content_hash

        return cls(
            token_id=token_id,
            decision_id=decision.decision_id,
            tenant_id=decision.tenant_id,
            actor_id=decision.actor_id,
            scope_actions=decision.scope.actions,
            scope_resources=decision.scope.resources,
            expiry=decision.expiry,
            chain_hash=chain_hash,
        )

    def to_public_dict(self) -> dict:
        """Public representation — safe to expose externally."""
        return {
            "token_id": self.token_id,
            "decision_id": self.decision_id,
            "tenant_id": self.tenant_id,
            "actor_id": self.actor_id,
            "scope_actions": self.scope_actions,
            "scope_resources": self.scope_resources,
            "expiry": self.expiry.isoformat() if self.expiry else None,
            "created_at": self.created_at.isoformat(),
            "chain_hash": self.chain_hash,
        }
