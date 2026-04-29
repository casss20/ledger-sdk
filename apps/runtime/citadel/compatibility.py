"""Compatibility-only runtime exports.

The active Citadel surface is intentionally small. Symbols in this module remain
available for existing callers and tests, but they are not the wedge product
story and should not be used for new public examples.
"""

from citadel.execution.orchestration import (
    DelegationResult,
    GatherResult,
    HandoffResult,
    IntrospectionStatus,
    OrchestrationRuntime,
)

__all__ = [
    "DelegationResult",
    "GatherResult",
    "HandoffResult",
    "IntrospectionStatus",
    "OrchestrationRuntime",
]
