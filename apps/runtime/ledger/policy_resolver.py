"""
Backward compatibility shim — re-exports from ledger.services.policy_resolver.

PolicyResolver, PolicyEvaluator, etc. were moved to ledger.services.policy_resolver
during the package refactor. This shim ensures all existing imports continue to work.
"""

from ledger.services.policy_resolver import (
    PolicyResolver,
    PolicyEvaluator,
    PolicyEvaluationResult,
    PolicySnapshot,
)

__all__ = ["PolicyResolver", "PolicyEvaluator", "PolicyEvaluationResult", "PolicySnapshot"]
