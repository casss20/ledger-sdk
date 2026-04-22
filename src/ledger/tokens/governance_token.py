"""
Governance Token System (gt_)

Why: Every governance decision creates a non-portable token.
Tokens accumulate over time, creating data gravity.
Customer migrating away from Ledger loses ability to
resolve historical compliance evidence.

Pattern: Stripe's pm_ PaymentMethod (open to store,
proprietary to resolve)
"""

import hashlib
import json
import secrets
import string
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class TokenType(Enum):
    """Types of governance decisions that create tokens."""

    POLICY_DECISION = "policy"  # gt_pol_xxx
    APPROVAL = "approval"  # gt_apr_xxx
    AUDIT_EVENT = "audit"  # gt_aud_xxx
    KILL_SWITCH = "kill"  # gt_kil_xxx
    AUTHORITY_DELEGATION = "auth"  # gt_del_xxx


# Base62 alphabet for URL-safe encoding
_BASE62 = string.ascii_letters + string.digits


def _base62_encode(data: bytes) -> str:
    """URL-safe base62 encoding (alphanumeric only)."""
    # Convert bytes to integer
    num = int.from_bytes(data, byteorder="big")
    if num == 0:
        return _BASE62[0]

    result = []
    while num > 0:
        num, rem = divmod(num, 62)
        result.append(_BASE62[rem])
    return "".join(reversed(result))


def _canonical_json(data: dict) -> str:
    """
    JSON Canonicalization Scheme (JCS/RFC 8785 simplified).

    Produces deterministic byte sequence for hashing.
    Rules: sort keys, no whitespace, shortest representation.
    """
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


@dataclass
class GovernanceToken:
    """
    Opaque governance token. Open to store, proprietary to resolve.
    Only Ledger's infrastructure can map gt_xxx to full decision trace.
    """

    token_id: str  # gt_<type>_<32_byte_random>
    token_type: TokenType
    created_at: datetime
    tenant_id: str
    agent_id: Optional[str] = None
    chain_hash: Optional[str] = None  # SHA-256 link to previous token

    # Private resolution data (not exposed outside Ledger)
    _decision_trace: dict = field(default_factory=dict, repr=False)
    _policy_version: Optional[str] = field(default=None, repr=False)
    _content_hash: Optional[str] = field(default=None, repr=False)

    @classmethod
    def generate(
        cls,
        token_type: TokenType,
        tenant_id: str,
        decision_trace: dict,
        previous_hash: Optional[str] = None,
        agent_id: Optional[str] = None,
    ) -> "GovernanceToken":
        """
        Generate cryptographically random gt_ token.

        Why: 32 bytes of entropy = 256 bits = impossible to guess.
        Format: gt_<type_prefix>_<base62_encoded_random>
        """
        random_bytes = secrets.token_bytes(32)
        random_b62 = _base62_encode(random_bytes)

        type_prefix = {
            TokenType.POLICY_DECISION: "pol",
            TokenType.APPROVAL: "apr",
            TokenType.AUDIT_EVENT: "aud",
            TokenType.KILL_SWITCH: "kil",
            TokenType.AUTHORITY_DELEGATION: "del",
        }[token_type]

        token_id = f"gt_{type_prefix}_{random_b62}"

        # Compute content hash (proves payload not modified)
        content_hash = hashlib.sha256(_canonical_json(decision_trace).encode()).hexdigest()

        # Compute chain hash (links to previous token)
        if previous_hash:
            chain_data = f"{content_hash}||{previous_hash}"
            chain_hash = hashlib.sha256(chain_data.encode()).hexdigest()
        else:
            chain_hash = content_hash  # First token

        return cls(
            token_id=token_id,
            token_type=token_type,
            created_at=datetime.now(timezone.utc),
            tenant_id=tenant_id,
            agent_id=agent_id,
            chain_hash=chain_hash,
            _decision_trace=decision_trace,
            _policy_version=None,
            _content_hash=content_hash,
        )

    def to_public_dict(self) -> dict:
        """
        Public representation (safe to expose).
        Does NOT include _decision_trace (proprietary).
        """
        return {
            "token_id": self.token_id,
            "token_type": self.token_type.value,
            "created_at": self.created_at.isoformat(),
            "tenant_id": self.tenant_id,
            "agent_id": self.agent_id,
            "chain_hash": self.chain_hash,
        }

    @property
    def content_hash(self) -> Optional[str]:
        """Read-only access to content hash."""
        return self._content_hash

    @property
    def decision_trace(self) -> dict:
        """Read-only access to decision trace."""
        return dict(self._decision_trace)
