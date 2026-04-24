"""
Backward compatibility shim â€” re-exports from citadel.services.policy_resolver.

PolicyResolver, PolicyEvaluator, etc. were moved to Citadel.services.policy_resolver
during the package refactor. This shim ensures all existing imports continue to work.
"""

from citadel.services.policy_resolver import (
    PolicyResolver,
    PolicyEvaluator,
    PolicyEvaluationResult,
    PolicySnapshot,
)

__all__ = ["PolicyResolver", "PolicyEvaluator", "PolicyEvaluationResult", "PolicySnapshot"]
