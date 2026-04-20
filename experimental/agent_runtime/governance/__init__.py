"""Governance layer — Quality, audit, and system maintenance.

Implements:
- ALIGNMENT.md → alignment.py (loyalty protocol)
- CRITIC.md → critic.py (quality review)
- AUDIT.md → audit.py (decision integrity)
- PRUNE.md → prune.py (context cleanup)
- AFTER_ACTION.md → after_action.py (learning loop)

Plus: capability tokens, killswitches, rate limiting.
"""

from .capability import CapabilityIssuer
from .alignment import (
    Alignment, ChallengeResult, InitiativeLevel, Challenge, AlignmentCheck, get_alignment
)
from .critic import Critic, ReviewResult, ReviewDimension, get_critic
from .audit import AuditService
from .prune import Prune, PruneTarget, get_prune
from .after_action import AfterAction, AfterActionReport, get_after_action

from .killswitch import KillSwitch
from .risk import classify, Approval
from .rate_limit import RateLimiter, rate_limited, RateLimitExceeded

__all__ = [
    # Core governance
    "CapabilityIssuer",
    "AuditService",
    "KillSwitch",
    "classify",
    "Approval",
    "RateLimiter",
    "rate_limited",
    "RateLimitExceeded",
    # Alignment
    "Alignment",
    "ChallengeResult",
    "InitiativeLevel",
    "Challenge",
    "AlignmentCheck",
    "get_alignment",
    # Critic
    "Critic",
    "ReviewResult",
    "ReviewDimension",
    "get_critic",
    # Prune
    "Prune",
    "PruneTarget",
    "get_prune",
    # After Action
    "AfterAction",
    "AfterActionReport",
    "get_after_action",
]